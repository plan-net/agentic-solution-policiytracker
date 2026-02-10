--
-- APISIX LLM Cost Tracker Plugin
-- Policy Tracker - v0.2.0
--
-- This plugin intercepts LLM API responses, extracts token usage,
-- calculates costs, and writes to TimescaleDB asynchronously.
--

local core = require("apisix.core")
local ngx = ngx
local ngx_now = ngx.now
local ngx_timer_at = ngx.timer.at
local cjson = require("cjson.safe")

-- Load sub-modules
local response_parser = require("apisix.plugins.llm-cost-tracker.response_parser")
local model_pricing = require("apisix.plugins.llm-cost-tracker.model_pricing")
local db_writer = require("apisix.plugins.llm-cost-tracker.db_writer")

local plugin_name = "llm-cost-tracker"

local schema = {
    type = "object",
    properties = {
        -- Database configuration
        db_host = { type = "string", default = "timescaledb" },
        db_port = { type = "integer", default = 5432 },
        db_name = { type = "string", default = "llm_costs" },
        db_user = { type = "string", default = "timescale" },
        db_password = { type = "string", default = "timescale_secure_password" },

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
    priority = 399,  -- Run after most plugins but before logging plugins
    name = plugin_name,
    schema = schema,
}

function _M.check_schema(conf)
    return core.schema.check(schema, conf)
end

--
-- ACCESS PHASE: Capture request metadata
--
function _M.access(conf, ctx)
    if not conf.enabled then
        return
    end

    -- Start timing
    ctx.llm_start_time = ngx_now()

    -- Capture agent headers for cost attribution
    local agent_type = core.request.header(ctx, "X-Agent-Type")
    local agent_name = core.request.header(ctx, "X-Agent-Name")
    local flow_name = core.request.header(ctx, "X-Flow-Name")

    -- Inject default agent values if not provided (for SDK calls without custom headers)
    local user_agent = core.request.header(ctx, "User-Agent") or ""
    local uri = ngx.var.uri or ""

    if not agent_type and (string.find(user_agent, "OpenAI") or string.find(user_agent, "python")) then
        agent_type = "kodosumi_flow"
        -- Differentiate between embeddings and chat completions
        if string.find(uri, "embeddings") then
            agent_name = "graphiti_embedder"
        else
            agent_name = "graphiti_document_processor"
        end
        flow_name = "data_ingestion"

        if conf.log_debug then
            core.log.info("LLM Cost Tracker: Injected default agent headers for ", uri)
        end
    end

    ctx.llm_agent_data = {
        agent_type = agent_type,
        agent_name = agent_name,
        flow_name = flow_name,
        chat_agent_name = core.request.header(ctx, "X-Chat-Agent-Name"),
        session_id = core.request.header(ctx, "X-Session-ID"),
        trace_id = core.request.header(ctx, "X-Trace-ID"),
        user_id = core.request.header(ctx, "X-User-ID"),
        project_id = core.request.header(ctx, "X-Project-ID") or conf.default_project_id,
        request_id = core.request.header(ctx, "X-Request-ID"),
    }

    -- Determine provider from URI
    if string.find(uri, "messages") then
        ctx.llm_provider = "anthropic"
    else
        ctx.llm_provider = "openai"
    end

    ctx.llm_endpoint = uri

    -- Try to extract model from request body
    local body, err = core.request.get_body()
    if body then
        local parsed_body = cjson.decode(body)
        if parsed_body then
            ctx.llm_model = parsed_body.model
            ctx.llm_is_streaming = parsed_body.stream or false
        end
        ctx.llm_request_size = #body
    end

    if conf.log_debug then
        core.log.info("LLM Cost Tracker [access]: provider=", ctx.llm_provider,
                      ", model=", ctx.llm_model or "unknown",
                      ", agent_type=", ctx.llm_agent_data.agent_type or "unknown")
    end
end

--
-- HEADER FILTER PHASE: Detect response type
--
function _M.header_filter(conf, ctx)
    if not conf.enabled or not ctx.llm_start_time then
        return
    end

    -- Check if this is a streaming response
    -- Note: Only treat as streaming if content-type is event-stream
    -- (chunked transfer encoding is normal for HTTP/1.1 responses)
    local content_type = ngx.header["Content-Type"] or ""

    ctx.llm_is_streaming_response = (
        string.find(content_type, "text/event-stream") ~= nil
    )

    -- Capture status code
    ctx.llm_status_code = ngx.status

    -- Initialize response buffer
    ctx.llm_response_body = {}
    ctx.llm_response_size = 0
end

--
-- BODY FILTER PHASE: Accumulate response body
--
function _M.body_filter(conf, ctx)
    if not conf.enabled or not ctx.llm_start_time then
        return
    end

    -- Skip streaming responses for now (per user requirement)
    if ctx.llm_is_streaming_response then
        return
    end

    local chunk = ngx.arg[1]
    local eof = ngx.arg[2]

    -- Accumulate response chunks
    if chunk and #chunk > 0 then
        table.insert(ctx.llm_response_body, chunk)
        ctx.llm_response_size = ctx.llm_response_size + #chunk
    end

    -- On final chunk, concatenate the full response
    if eof then
        ctx.llm_full_response = table.concat(ctx.llm_response_body)
        ctx.llm_response_body = nil  -- Free memory
    end
end

--
-- LOG PHASE: Parse usage, calculate cost, write to database
--
function _M.log(conf, ctx)
    if not conf.enabled or not ctx.llm_start_time then
        return
    end

    -- Skip streaming responses for now
    if ctx.llm_is_streaming_response then
        if conf.log_debug then
            core.log.info("LLM Cost Tracker [log]: Skipping streaming response")
        end
        return
    end

    -- Calculate latency
    local latency_ms = math.floor((ngx_now() - ctx.llm_start_time) * 1000)

    -- Parse token usage from response
    local usage = { prompt_tokens = 0, completion_tokens = 0, total_tokens = 0 }
    local model_from_response = nil

    if ctx.llm_full_response and #ctx.llm_full_response > 0 then
        local parse_result = response_parser.extract_usage(ctx.llm_full_response, ctx.llm_provider)
        if parse_result then
            usage = parse_result.usage or usage
            model_from_response = parse_result.model
        end
    end

    -- Use model from response if not in request (Anthropic pattern)
    local model = ctx.llm_model or model_from_response or "unknown"

    -- Calculate cost
    local cost_usd = model_pricing.calculate_cost(model, usage)

    -- Prepare record for database
    local record = {
        timestamp = ngx.localtime(),
        provider = ctx.llm_provider,
        model = model,
        endpoint = ctx.llm_endpoint,

        -- Agent tracking
        agent_type = ctx.llm_agent_data.agent_type,
        agent_name = ctx.llm_agent_data.agent_name,
        flow_name = ctx.llm_agent_data.flow_name,
        chat_agent_name = ctx.llm_agent_data.chat_agent_name,
        session_id = ctx.llm_agent_data.session_id,
        trace_id = ctx.llm_agent_data.trace_id,
        user_id = ctx.llm_agent_data.user_id,
        project_id = ctx.llm_agent_data.project_id,

        -- Token usage
        prompt_tokens = usage.prompt_tokens,
        completion_tokens = usage.completion_tokens,
        total_tokens = usage.total_tokens,
        cost_usd = cost_usd,

        -- Performance
        latency_ms = latency_ms,
        status_code = ctx.llm_status_code or ngx.status,
        request_size_bytes = ctx.llm_request_size,
        response_size_bytes = ctx.llm_response_size,

        -- Request metadata
        request_id = ctx.llm_agent_data.request_id,
    }

    -- Enqueue for async write
    db_writer.enqueue(record, conf)

    if conf.log_debug then
        core.log.info("LLM Cost Tracker [log]: ",
                      "provider=", record.provider,
                      ", model=", record.model,
                      ", tokens=", record.total_tokens,
                      ", cost=$", string.format("%.8f", record.cost_usd),
                      ", latency=", record.latency_ms, "ms",
                      ", agent=", record.agent_name or "unknown")
    end
end

return _M
