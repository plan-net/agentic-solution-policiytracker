--
-- LLM Model Pricing Calculator
-- Calculates costs based on token usage and model pricing
--
-- Prices are per 1 MILLION tokens (industry standard as of 2024)
--
-- Cache Token Pricing (Anthropic):
-- - cache_creation: 1.25x base input price (25% premium for writing to cache)
-- - cache_read: 0.10x base input price (90% discount for reading from cache!)
--

local core = require("apisix.core")

local _M = {}

-- Cache token pricing multipliers (Anthropic prompt caching)
local CACHE_WRITE_MULTIPLIER = 1.25  -- 25% premium for cache creation
local CACHE_READ_MULTIPLIER = 0.10   -- 90% discount for cache reads

--
-- Default pricing table (prices per 1M tokens in USD)
-- Updated: December 2024 (added GPT-4.1 family)
--
local DEFAULT_PRICES = {
    -- OpenAI Models
    ["gpt-4o"] = { input = 2.50, output = 10.00 },
    ["gpt-4o-2024-11-20"] = { input = 2.50, output = 10.00 },
    ["gpt-4o-2024-08-06"] = { input = 2.50, output = 10.00 },
    ["gpt-4o-2024-05-13"] = { input = 5.00, output = 15.00 },

    ["gpt-4o-mini"] = { input = 0.15, output = 0.60 },
    ["gpt-4o-mini-2024-07-18"] = { input = 0.15, output = 0.60 },

    -- OpenAI GPT-4.1 Models (April 2025)
    ["gpt-4.1"] = { input = 2.00, output = 8.00 },
    ["gpt-4.1-2025-04-14"] = { input = 2.00, output = 8.00 },
    ["gpt-4.1-mini"] = { input = 0.40, output = 1.60 },
    ["gpt-4.1-mini-2025-04-14"] = { input = 0.40, output = 1.60 },
    ["gpt-4.1-nano"] = { input = 0.10, output = 0.40 },
    ["gpt-4.1-nano-2025-04-14"] = { input = 0.10, output = 0.40 },

    ["gpt-4-turbo"] = { input = 10.00, output = 30.00 },
    ["gpt-4-turbo-2024-04-09"] = { input = 10.00, output = 30.00 },
    ["gpt-4-turbo-preview"] = { input = 10.00, output = 30.00 },

    ["gpt-4"] = { input = 30.00, output = 60.00 },
    ["gpt-4-0613"] = { input = 30.00, output = 60.00 },
    ["gpt-4-32k"] = { input = 60.00, output = 120.00 },

    ["gpt-3.5-turbo"] = { input = 0.50, output = 1.50 },
    ["gpt-3.5-turbo-0125"] = { input = 0.50, output = 1.50 },
    ["gpt-3.5-turbo-1106"] = { input = 1.00, output = 2.00 },
    ["gpt-3.5-turbo-instruct"] = { input = 1.50, output = 2.00 },

    -- OpenAI o1 Models (reasoning)
    ["o1-preview"] = { input = 15.00, output = 60.00 },
    ["o1-preview-2024-09-12"] = { input = 15.00, output = 60.00 },
    ["o1-mini"] = { input = 3.00, output = 12.00 },
    ["o1-mini-2024-09-12"] = { input = 3.00, output = 12.00 },

    -- OpenAI Embeddings
    ["text-embedding-3-small"] = { input = 0.02, output = 0.0 },
    ["text-embedding-3-large"] = { input = 0.13, output = 0.0 },
    ["text-embedding-ada-002"] = { input = 0.10, output = 0.0 },

    -- Anthropic Claude 4 Models (2025)
    ["claude-sonnet-4-20250514"] = { input = 3.00, output = 15.00 },
    ["claude-sonnet-4-latest"] = { input = 3.00, output = 15.00 },
    ["claude-opus-4-20250514"] = { input = 15.00, output = 75.00 },
    ["claude-opus-4-latest"] = { input = 15.00, output = 75.00 },
    ["claude-haiku-4-20250514"] = { input = 0.80, output = 4.00 },
    ["claude-haiku-4-latest"] = { input = 0.80, output = 4.00 },

    -- Anthropic Claude 3.5 Models
    ["claude-3-5-sonnet-20241022"] = { input = 3.00, output = 15.00 },
    ["claude-3-5-sonnet-latest"] = { input = 3.00, output = 15.00 },
    ["claude-3-5-haiku-20241022"] = { input = 1.00, output = 5.00 },
    ["claude-3-5-haiku-latest"] = { input = 1.00, output = 5.00 },

    -- Anthropic Claude 3 Models
    ["claude-3-opus-20240229"] = { input = 15.00, output = 75.00 },
    ["claude-3-opus-latest"] = { input = 15.00, output = 75.00 },
    ["claude-3-sonnet-20240229"] = { input = 3.00, output = 15.00 },
    ["claude-3-haiku-20240307"] = { input = 0.25, output = 1.25 },

    -- Claude 2 Legacy
    ["claude-2.1"] = { input = 8.00, output = 24.00 },
    ["claude-2.0"] = { input = 8.00, output = 24.00 },
    ["claude-instant-1.2"] = { input = 0.80, output = 2.40 },
}

-- Fallback pricing for unknown models
local FALLBACK_PRICES = { input = 1.00, output = 3.00 }

--
-- Get pricing for a model
-- Supports fuzzy matching (e.g., "gpt-4o-mini-2024-07-18" matches "gpt-4o-mini")
--
-- @param model string The model name
-- @return table {input, output} prices per 1M tokens
--
function _M.get_model_pricing(model)
    if not model or model == "" then
        return FALLBACK_PRICES
    end

    -- Direct match
    if DEFAULT_PRICES[model] then
        return DEFAULT_PRICES[model]
    end

    -- Try prefix matching for versioned models
    for known_model, prices in pairs(DEFAULT_PRICES) do
        if string.sub(model, 1, #known_model) == known_model then
            return prices
        end
        -- Also try if known_model is a prefix of model
        if string.sub(known_model, 1, #model) == model then
            return prices
        end
    end

    -- Try base model matching (remove date suffixes)
    local base_model = model:gsub("-20%d%d%-%d%d%-%d%d$", "")
    if DEFAULT_PRICES[base_model] then
        return DEFAULT_PRICES[base_model]
    end

    -- Log warning for unknown model
    core.log.warn("LLM Cost Tracker: Unknown model '", model, "', using fallback pricing")

    return FALLBACK_PRICES
end

--
-- Calculate cost for token usage
--
-- @param model string The model name
-- @param usage table {prompt_tokens, completion_tokens, total_tokens,
--                     cache_creation_tokens, cache_read_tokens}
-- @return number Cost in USD
--
-- Cache Token Pricing:
-- - cache_creation_tokens: 1.25x base input price
-- - cache_read_tokens: 0.10x base input price (90% discount!)
--
function _M.calculate_cost(model, usage)
    if not usage then
        return 0
    end

    local prices = _M.get_model_pricing(model)

    local prompt_tokens = usage.prompt_tokens or 0
    local completion_tokens = usage.completion_tokens or 0
    local cache_creation_tokens = usage.cache_creation_tokens or 0
    local cache_read_tokens = usage.cache_read_tokens or 0

    -- Calculate cost (prices are per 1M tokens)
    local input_cost = (prompt_tokens / 1000000) * prices.input
    local output_cost = (completion_tokens / 1000000) * prices.output

    -- Cache token costs (Anthropic prompt caching)
    local cache_creation_cost = (cache_creation_tokens / 1000000) * prices.input * CACHE_WRITE_MULTIPLIER
    local cache_read_cost = (cache_read_tokens / 1000000) * prices.input * CACHE_READ_MULTIPLIER

    return input_cost + output_cost + cache_creation_cost + cache_read_cost
end

--
-- Get cache pricing multipliers (for debugging/admin purposes)
--
function _M.get_cache_multipliers()
    return {
        cache_write = CACHE_WRITE_MULTIPLIER,
        cache_read = CACHE_READ_MULTIPLIER,
    }
end

--
-- Get all known model prices (for debugging/admin purposes)
--
function _M.get_all_prices()
    return DEFAULT_PRICES
end

--
-- Get fallback prices
--
function _M.get_fallback_prices()
    return FALLBACK_PRICES
end

return _M
