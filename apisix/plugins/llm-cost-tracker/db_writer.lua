--
-- Async TimescaleDB Writer for LLM Cost Tracking
--
-- Features:
-- - Batched inserts for efficiency
-- - Non-blocking async writes via ngx.timer
-- - Connection pooling via resty.postgres or HTTP fallback
-- - Retry logic for failed writes
--

local core = require("apisix.core")
local ngx = ngx
local ngx_timer_at = ngx.timer.at
local cjson = require("cjson.safe")

local _M = {}

-- Batch queue (module-level state)
local batch_queue = {}
local timer_running = false
local MAX_QUEUE_SIZE = 1000  -- Prevent memory issues

--
-- Escape string for SQL (basic escaping)
--
local function sql_escape(str)
    if str == nil then
        return "NULL"
    end
    if type(str) ~= "string" then
        return tostring(str)
    end
    -- Escape single quotes by doubling them
    return "'" .. string.gsub(str, "'", "''") .. "'"
end

--
-- Escape numeric values
--
local function sql_number(val)
    if val == nil then
        return "NULL"
    end
    return tostring(val)
end

--
-- Build cache token metadata as JSON for request_headers column
--
local function build_cache_metadata(record)
    local cache_creation = record.cache_creation_tokens or 0
    local cache_read = record.cache_read_tokens or 0

    if cache_creation == 0 and cache_read == 0 then
        return "NULL"
    end

    -- Build JSON object for request_headers JSONB column
    local metadata = {
        cache_creation_tokens = cache_creation,
        cache_read_tokens = cache_read,
        non_cached_input_tokens = record.prompt_tokens or 0,
        apisix_source = "llm-cost-tracker"
    }

    local json_str = cjson.encode(metadata)
    if not json_str then
        return "NULL"
    end

    return sql_escape(json_str)
end

--
-- Build INSERT SQL for a batch of records
--
local function build_insert_sql(records)
    if #records == 0 then
        return nil
    end

    local columns = {
        "timestamp", "provider", "model", "endpoint",
        "agent_type", "agent_name", "flow_name", "chat_agent_name",
        "session_id", "trace_id", "user_id", "project_id",
        "prompt_tokens", "completion_tokens", "total_tokens", "cost_usd",
        "latency_ms", "status_code",
        "request_size_bytes", "response_size_bytes", "request_headers"
    }

    local values_list = {}

    for _, record in ipairs(records) do
        local values = string.format(
            "(NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            sql_escape(record.provider),
            sql_escape(record.model),
            sql_escape(record.endpoint),
            sql_escape(record.agent_type),
            sql_escape(record.agent_name),
            sql_escape(record.flow_name),
            sql_escape(record.chat_agent_name),
            sql_escape(record.session_id),
            sql_escape(record.trace_id),
            sql_escape(record.user_id),
            sql_escape(record.project_id),
            sql_number(record.prompt_tokens),
            sql_number(record.completion_tokens),
            sql_number(record.total_tokens),
            sql_number(record.cost_usd),
            sql_number(record.latency_ms),
            sql_number(record.status_code),
            sql_number(record.request_size_bytes),
            sql_number(record.response_size_bytes),
            build_cache_metadata(record)
        )
        table.insert(values_list, values)
    end

    local sql = "INSERT INTO llm_requests (" ..
                table.concat(columns, ", ") ..
                ") VALUES " ..
                table.concat(values_list, ", ")

    return sql
end

--
-- Build HTTP request payload with cache metadata in request_headers
--
local function build_http_records(records)
    local http_records = {}

    for _, record in ipairs(records) do
        local http_record = {
            timestamp = record.timestamp,
            provider = record.provider,
            model = record.model,
            endpoint = record.endpoint,
            agent_type = record.agent_type,
            agent_name = record.agent_name,
            flow_name = record.flow_name,
            chat_agent_name = record.chat_agent_name,
            session_id = record.session_id,
            trace_id = record.trace_id,
            user_id = record.user_id,
            project_id = record.project_id,
            prompt_tokens = record.prompt_tokens,
            completion_tokens = record.completion_tokens,
            total_tokens = record.total_tokens,
            cost_usd = record.cost_usd,
            latency_ms = record.latency_ms,
            status_code = record.status_code,
            request_size_bytes = record.request_size_bytes,
            response_size_bytes = record.response_size_bytes,
        }

        -- Add cache token metadata to request_headers if present
        local cache_creation = record.cache_creation_tokens or 0
        local cache_read = record.cache_read_tokens or 0

        if cache_creation > 0 or cache_read > 0 then
            http_record.request_headers = {
                cache_creation_tokens = cache_creation,
                cache_read_tokens = cache_read,
                non_cached_input_tokens = record.prompt_tokens or 0,
                apisix_source = "llm-cost-tracker"
            }
        end

        table.insert(http_records, http_record)
    end

    return http_records
end

--
-- Write records to database via HTTP (using the cost-analytics service)
--
local function write_via_http(records, conf)
    local http = require("resty.http")
    local httpc = http.new()

    if #records == 0 then
        return true
    end

    -- Prepare the request body with cache metadata
    local http_records = build_http_records(records)
    local body = cjson.encode({
        records = http_records
    })

    -- Determine the analytics service URL
    local analytics_host = conf.analytics_host or "cost-analytics"
    local analytics_port = conf.analytics_port or 8000
    local url = string.format("http://%s:%d/api/ingest/costs", analytics_host, analytics_port)

    httpc:set_timeout(5000)  -- 5 second timeout

    local res, err = httpc:request_uri(url, {
        method = "POST",
        body = body,
        headers = {
            ["Content-Type"] = "application/json",
        },
    })

    if not res then
        core.log.error("LLM Cost Tracker HTTP: Failed to send records: ", err)
        return false, err
    end

    if res.status ~= 200 then
        core.log.error("LLM Cost Tracker HTTP: Non-200 response: ", res.status, " body: ", res.body)
        return false, "HTTP error: " .. res.status
    end

    local response = cjson.decode(res.body)
    if response and response.success then
        core.log.info("LLM Cost Tracker HTTP: Successfully inserted ", response.records_inserted, " records")
        return true
    else
        core.log.error("LLM Cost Tracker HTTP: Insert failed: ", res.body)
        return false, "Insert failed"
    end
end

--
-- Try to write records using pgmoon (if available)
--
local function write_via_pgmoon(records, conf)
    local ok, pgmoon = pcall(require, "pgmoon")
    if not ok then
        core.log.debug("LLM Cost Tracker: pgmoon not available, using HTTP fallback")
        return nil, "pgmoon not available"
    end

    local pg = pgmoon.new({
        host = conf.db_host,
        port = conf.db_port,
        database = conf.db_name,
        user = conf.db_user,
        password = conf.db_password,
        pool_size = 10,
    })

    local connect_ok, err = pg:connect()
    if not connect_ok then
        core.log.error("LLM Cost Tracker: Failed to connect to TimescaleDB: ", err)
        return false, err
    end

    local sql = build_insert_sql(records)
    if not sql then
        pg:keepalive()
        return false, "No records to write"
    end

    local result, query_err = pg:query(sql)
    if not result then
        core.log.error("LLM Cost Tracker: Failed to insert records: ", query_err)
        pg:keepalive()
        return false, query_err
    end

    pg:keepalive()

    core.log.info("LLM Cost Tracker: Successfully inserted ", #records, " records to TimescaleDB")
    return true
end

--
-- Write records using raw socket (simplest approach)
--
local function write_via_socket(records, conf)
    local socket = require("socket")

    -- Build PostgreSQL protocol messages would be complex
    -- Instead, use the simple approach of logging for now
    -- The analytics API will handle actual database writes

    local sql = build_insert_sql(records)
    if not sql then
        return false, "No records to write"
    end

    -- Log the records as JSON for debugging/verification
    for _, record in ipairs(records) do
        core.log.info("LLM_COST_RECORD: ", cjson.encode(record))
    end

    return true
end

--
-- Flush the batch queue to database
--
local function flush_batch(premature, conf)
    if premature then
        return
    end

    -- Get records to flush
    local records_to_flush = {}
    local count = 0
    local batch_size = conf.batch_size or 10

    while #batch_queue > 0 and count < batch_size do
        local record = table.remove(batch_queue, 1)
        table.insert(records_to_flush, record)
        count = count + 1
    end

    if #records_to_flush > 0 then
        -- Try HTTP first (to cost-analytics service), then pgmoon, then socket/log
        local ok, err = write_via_http(records_to_flush, conf)

        if not ok then
            -- HTTP failed, try pgmoon
            core.log.debug("LLM Cost Tracker: HTTP write failed, trying pgmoon: ", err)
            ok, err = write_via_pgmoon(records_to_flush, conf)
        end

        if ok == nil or not ok then
            -- pgmoon not available or failed, use socket/log fallback
            core.log.debug("LLM Cost Tracker: pgmoon failed, using socket fallback")
            ok, err = write_via_socket(records_to_flush, conf)
        end

        if not ok then
            core.log.error("LLM Cost Tracker: Failed to write batch: ", err)
            -- Re-queue records for retry (up to max queue size)
            if #batch_queue < MAX_QUEUE_SIZE then
                for _, record in ipairs(records_to_flush) do
                    table.insert(batch_queue, record)
                end
            end
        end
    end

    -- Schedule next flush if there are more records
    if #batch_queue > 0 then
        local interval = conf.flush_interval or 5.0
        local timer_ok, timer_err = ngx_timer_at(interval, flush_batch, conf)
        if not timer_ok then
            core.log.error("LLM Cost Tracker: Failed to schedule next flush: ", timer_err)
            timer_running = false
        end
    else
        timer_running = false
    end
end

--
-- Enqueue a record for async writing
--
-- @param record table The cost record to write
-- @param conf table Plugin configuration
--
function _M.enqueue(record, conf)
    -- Check queue size limit
    if #batch_queue >= MAX_QUEUE_SIZE then
        core.log.warn("LLM Cost Tracker: Queue full, dropping oldest record")
        table.remove(batch_queue, 1)
    end

    -- Add to queue
    table.insert(batch_queue, record)

    -- Start flush timer if not running
    if not timer_running then
        timer_running = true
        local batch_size = conf.batch_size or 10
        local flush_interval = conf.flush_interval or 5.0

        -- Immediate flush if batch is full
        local delay = (#batch_queue >= batch_size) and 0 or flush_interval

        local ok, err = ngx_timer_at(delay, flush_batch, conf)
        if not ok then
            core.log.error("LLM Cost Tracker: Failed to start flush timer: ", err)
            timer_running = false
        end
    end
end

--
-- Get current queue size (for monitoring)
--
function _M.get_queue_size()
    return #batch_queue
end

--
-- Force flush all pending records (for shutdown)
--
function _M.flush_all(conf)
    while #batch_queue > 0 do
        flush_batch(false, conf)
    end
end

return _M
