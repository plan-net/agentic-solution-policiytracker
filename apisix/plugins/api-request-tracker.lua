--
-- APISIX External API Request Tracker Plugin
-- Policy Tracker - v0.1.0
--
-- This plugin intercepts external API responses, captures metrics,
-- and writes to TimescaleDB asynchronously.
--
-- Tracks: exa-search, exa-contents, dpa-articles, bundestag-vorgang, bundestag-drucksache
--

local core = require("apisix.core")
local ngx = ngx
local ngx_now = ngx.now
local ngx_timer_at = ngx.timer.at
local cjson = require("cjson.safe")
local http = require("resty.http")

local plugin_name = "api-request-tracker"

-- Batch queue (module-level state)
local batch_queue = {}
local timer_running = false
local MAX_QUEUE_SIZE = 1000

local schema = {
    type = "object",
    properties = {
        -- API identification
        api_name = { type = "string", default = "unknown" },

        -- Analytics service configuration
        analytics_host = { type = "string", default = "cost-analytics" },
        analytics_port = { type = "integer", default = 8000 },

        -- Batching configuration
        batch_size = { type = "integer", default = 10, minimum = 1, maximum = 100 },
        flush_interval = { type = "number", default = 5.0, minimum = 1.0, maximum = 60.0 },

        -- Feature flags
        enabled = { type = "boolean", default = true },
        log_debug = { type = "boolean", default = false },

        -- Default project
        default_project_id = { type = "string", default = "political_monitoring_v2" },
    },
}

local _M = {
    version = 0.1,
    priority = 398,  -- Run after most plugins but before logging
    name = plugin_name,
    schema = schema,
}

function _M.check_schema(conf)
    return core.schema.check(schema, conf)
end

--
-- Write records to database via HTTP (using the cost-analytics service)
--
local function write_via_http(records, conf)
    local httpc = http.new()

    if #records == 0 then
        return true
    end

    local body = cjson.encode({
        records = records,
        table_name = "external_api_requests"
    })

    local analytics_host = conf.analytics_host or "cost-analytics"
    local analytics_port = conf.analytics_port or 8000
    local url = string.format("http://%s:%d/api/ingest/external-api", analytics_host, analytics_port)

    httpc:set_timeout(5000)

    local res, err = httpc:request_uri(url, {
        method = "POST",
        body = body,
        headers = {
            ["Content-Type"] = "application/json",
        },
    })

    if not res then
        core.log.error("API Request Tracker HTTP: Failed to send records: ", err)
        return false, err
    end

    if res.status ~= 200 then
        core.log.error("API Request Tracker HTTP: Non-200 response: ", res.status, " body: ", res.body)
        return false, "HTTP error: " .. res.status
    end

    local response = cjson.decode(res.body)
    if response and response.success then
        core.log.info("API Request Tracker HTTP: Successfully inserted ", response.records_inserted, " records")
        return true
    else
        core.log.error("API Request Tracker HTTP: Insert failed: ", res.body)
        return false, "Insert failed"
    end
end

--
-- Flush the batch queue to database
--
local function flush_batch(premature, conf)
    if premature then
        return
    end

    local records_to_flush = {}
    local count = 0
    local batch_size = conf.batch_size or 10

    while #batch_queue > 0 and count < batch_size do
        local record = table.remove(batch_queue, 1)
        table.insert(records_to_flush, record)
        count = count + 1
    end

    if #records_to_flush > 0 then
        local ok, err = write_via_http(records_to_flush, conf)

        if not ok then
            core.log.error("API Request Tracker: Failed to write batch: ", err)
            -- Log records as fallback
            for _, record in ipairs(records_to_flush) do
                core.log.info("API_REQUEST_RECORD: ", cjson.encode(record))
            end
        end
    end

    -- Schedule next flush if there are more records
    if #batch_queue > 0 then
        local interval = conf.flush_interval or 5.0
        local timer_ok, timer_err = ngx_timer_at(interval, flush_batch, conf)
        if not timer_ok then
            core.log.error("API Request Tracker: Failed to schedule next flush: ", timer_err)
            timer_running = false
        end
    else
        timer_running = false
    end
end

--
-- Enqueue a record for async writing
--
local function enqueue(record, conf)
    if #batch_queue >= MAX_QUEUE_SIZE then
        core.log.warn("API Request Tracker: Queue full, dropping oldest record")
        table.remove(batch_queue, 1)
    end

    table.insert(batch_queue, record)

    if not timer_running then
        timer_running = true
        local batch_size = conf.batch_size or 10
        local flush_interval = conf.flush_interval or 5.0

        local delay = (#batch_queue >= batch_size) and 0 or flush_interval

        local ok, err = ngx_timer_at(delay, flush_batch, conf)
        if not ok then
            core.log.error("API Request Tracker: Failed to start flush timer: ", err)
            timer_running = false
        end
    end
end

--
-- ACCESS PHASE: Capture request metadata
--
function _M.access(conf, ctx)
    if not conf.enabled then
        return
    end

    -- Start timing
    ctx.api_start_time = ngx_now()

    -- Capture agent headers for tracking
    ctx.api_tracking_data = {
        agent_type = core.request.header(ctx, "X-Agent-Type"),
        agent_name = core.request.header(ctx, "X-Agent-Name"),
        flow_name = core.request.header(ctx, "X-Flow-Name"),
        session_id = core.request.header(ctx, "X-Session-ID"),
        trace_id = core.request.header(ctx, "X-Trace-ID"),
        user_id = core.request.header(ctx, "X-User-ID"),
        project_id = core.request.header(ctx, "X-Project-ID") or conf.default_project_id,
    }

    ctx.api_name = conf.api_name
    ctx.api_endpoint = ngx.var.uri
    ctx.api_method = ngx.var.request_method

    -- Capture request size
    local body = core.request.get_body()
    if body then
        ctx.api_request_size = #body
    else
        ctx.api_request_size = 0
    end

    if conf.log_debug then
        core.log.info("API Request Tracker [access]: api=", conf.api_name,
                      ", endpoint=", ctx.api_endpoint,
                      ", method=", ctx.api_method)
    end
end

--
-- HEADER FILTER PHASE: Capture response metadata
--
function _M.header_filter(conf, ctx)
    if not conf.enabled or not ctx.api_start_time then
        return
    end

    ctx.api_status_code = ngx.status

    -- Initialize response tracking
    ctx.api_response_body = {}
    ctx.api_response_size = 0
end

--
-- BODY FILTER PHASE: Accumulate response body size
--
function _M.body_filter(conf, ctx)
    if not conf.enabled or not ctx.api_start_time then
        return
    end

    local chunk = ngx.arg[1]
    local eof = ngx.arg[2]

    if chunk and #chunk > 0 then
        ctx.api_response_size = (ctx.api_response_size or 0) + #chunk
    end
end

--
-- LOG PHASE: Write metrics to database
--
function _M.log(conf, ctx)
    if not conf.enabled or not ctx.api_start_time then
        return
    end

    -- Calculate latency
    local latency_ms = math.floor((ngx_now() - ctx.api_start_time) * 1000)

    -- Prepare record for database
    local record = {
        timestamp = ngx.localtime(),
        api_name = ctx.api_name,
        endpoint = ctx.api_endpoint,
        method = ctx.api_method,

        -- Agent tracking
        agent_type = ctx.api_tracking_data.agent_type,
        agent_name = ctx.api_tracking_data.agent_name,
        flow_name = ctx.api_tracking_data.flow_name,
        session_id = ctx.api_tracking_data.session_id,
        trace_id = ctx.api_tracking_data.trace_id,
        user_id = ctx.api_tracking_data.user_id,
        project_id = ctx.api_tracking_data.project_id,

        -- Performance
        latency_ms = latency_ms,
        status_code = ctx.api_status_code or ngx.status,
        request_size_bytes = ctx.api_request_size,
        response_size_bytes = ctx.api_response_size,
    }

    -- Enqueue for async write
    enqueue(record, conf)

    if conf.log_debug then
        core.log.info("API Request Tracker [log]: ",
                      "api=", record.api_name,
                      ", endpoint=", record.endpoint,
                      ", status=", record.status_code,
                      ", latency=", record.latency_ms, "ms")
    end
end

return _M
