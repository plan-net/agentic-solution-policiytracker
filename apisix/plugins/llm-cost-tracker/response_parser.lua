--
-- LLM Response Parser
-- Extracts token usage from OpenAI and Anthropic API responses
--

local cjson = require("cjson.safe")
local core = require("apisix.core")

local _M = {}

--
-- Parse OpenAI Chat Completion Response
--
-- Response format:
-- {
--   "id": "chatcmpl-xxx",
--   "object": "chat.completion",
--   "model": "gpt-4o-mini-2024-07-18",
--   "usage": {
--     "prompt_tokens": 10,
--     "completion_tokens": 20,
--     "total_tokens": 30
--   }
-- }
--
function _M.parse_openai(response_body)
    if not response_body or response_body == "" then
        return nil
    end

    local parsed, err = cjson.decode(response_body)
    if not parsed then
        core.log.warn("LLM Cost Tracker: Failed to parse OpenAI response: ", err)
        return nil
    end

    local result = {
        model = parsed.model,
        usage = {
            prompt_tokens = 0,
            completion_tokens = 0,
            total_tokens = 0,
        }
    }

    if parsed.usage then
        result.usage.prompt_tokens = parsed.usage.prompt_tokens or 0
        result.usage.completion_tokens = parsed.usage.completion_tokens or 0
        result.usage.total_tokens = parsed.usage.total_tokens or 0
    end

    return result
end

--
-- Parse OpenAI Embeddings Response
--
-- Response format:
-- {
--   "object": "list",
--   "model": "text-embedding-3-small",
--   "usage": {
--     "prompt_tokens": 8,
--     "total_tokens": 8
--   }
-- }
--
function _M.parse_openai_embeddings(response_body)
    if not response_body or response_body == "" then
        return nil
    end

    local parsed, err = cjson.decode(response_body)
    if not parsed then
        core.log.warn("LLM Cost Tracker: Failed to parse OpenAI embeddings response: ", err)
        return nil
    end

    local result = {
        model = parsed.model,
        usage = {
            prompt_tokens = 0,
            completion_tokens = 0,  -- Embeddings don't have completion tokens
            total_tokens = 0,
        }
    }

    if parsed.usage then
        result.usage.prompt_tokens = parsed.usage.prompt_tokens or 0
        result.usage.total_tokens = parsed.usage.total_tokens or parsed.usage.prompt_tokens or 0
    end

    return result
end

--
-- Parse Anthropic Messages Response
--
-- Response format:
-- {
--   "id": "msg_xxx",
--   "type": "message",
--   "model": "claude-3-5-sonnet-20241022",
--   "usage": {
--     "input_tokens": 10,
--     "output_tokens": 20
--   }
-- }
--
function _M.parse_anthropic(response_body)
    if not response_body or response_body == "" then
        return nil
    end

    local parsed, err = cjson.decode(response_body)
    if not parsed then
        core.log.warn("LLM Cost Tracker: Failed to parse Anthropic response: ", err)
        return nil
    end

    local result = {
        model = parsed.model,
        usage = {
            prompt_tokens = 0,
            completion_tokens = 0,
            total_tokens = 0,
        }
    }

    if parsed.usage then
        -- Anthropic uses input_tokens and output_tokens
        result.usage.prompt_tokens = parsed.usage.input_tokens or 0
        result.usage.completion_tokens = parsed.usage.output_tokens or 0
        result.usage.total_tokens = (parsed.usage.input_tokens or 0) + (parsed.usage.output_tokens or 0)
    end

    return result
end

--
-- Extract usage from response based on provider
--
-- @param response_body string The raw response body
-- @param provider string "openai" or "anthropic"
-- @return table {model, usage} or nil
--
function _M.extract_usage(response_body, provider)
    if not response_body or response_body == "" then
        return {
            model = nil,
            usage = {
                prompt_tokens = 0,
                completion_tokens = 0,
                total_tokens = 0,
            }
        }
    end

    if provider == "anthropic" then
        return _M.parse_anthropic(response_body)
    elseif provider == "openai" then
        -- Try to detect if it's an embeddings response
        if string.find(response_body, '"object":"list"') or string.find(response_body, '"object": "list"') then
            return _M.parse_openai_embeddings(response_body)
        end
        return _M.parse_openai(response_body)
    else
        -- Default to OpenAI format
        return _M.parse_openai(response_body)
    end
end

return _M
