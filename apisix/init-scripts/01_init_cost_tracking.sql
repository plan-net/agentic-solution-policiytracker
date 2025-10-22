--
-- TimescaleDB Initialization Script for LLM Cost Tracking
-- Policy Tracker - v0.2.0
--
-- This script creates the schema for tracking LLM API requests with agent-level granularity
--

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Main LLM requests table with agent-level tracking
CREATE TABLE IF NOT EXISTS llm_requests (
    id BIGSERIAL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Provider & Model Information
    provider VARCHAR(50) NOT NULL,          -- 'openai', 'anthropic'
    model VARCHAR(100) NOT NULL,            -- 'gpt-4', 'claude-3-5-sonnet', etc.
    endpoint VARCHAR(200),                  -- API endpoint called

    -- Agent-Level Tracking
    agent_type VARCHAR(50),                 -- 'kodosumi_flow', 'chat_agent', 'etl_processor'
    agent_name VARCHAR(100),                -- Specific agent identifier
    flow_name VARCHAR(100),                 -- For Kodosumi: 'data_ingestion', 'context_analysis', etc.
    chat_agent_name VARCHAR(100),           -- For Chat: 'query_understanding', 'tool_planning', etc.
    session_id VARCHAR(100),                -- Track conversation/processing sessions
    trace_id VARCHAR(100),                  -- For distributed tracing

    -- User & Project Information
    user_id VARCHAR(100),
    project_id VARCHAR(100) DEFAULT 'political_monitoring_v2',

    -- Token & Cost Information
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    cost_usd DECIMAL(12, 8),                -- Cost in USD (8 decimal places for precision)

    -- Performance Metrics
    latency_ms INTEGER,                     -- Request latency in milliseconds
    status_code INTEGER,                    -- HTTP status code
    error_message TEXT,                     -- Error details if request failed

    -- Request Metadata
    request_size_bytes INTEGER,             -- Size of request payload
    response_size_bytes INTEGER,            -- Size of response payload
    request_headers JSONB,                  -- Store important headers as JSON

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (id, timestamp)
);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('llm_requests', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Indexes for efficient querying

-- Agent-level queries
CREATE INDEX IF NOT EXISTS idx_agent_type_timestamp
    ON llm_requests (agent_type, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_agent_name_timestamp
    ON llm_requests (agent_name, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_flow_name_timestamp
    ON llm_requests (flow_name, timestamp DESC)
    WHERE flow_name IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_chat_agent_timestamp
    ON llm_requests (chat_agent_name, timestamp DESC)
    WHERE chat_agent_name IS NOT NULL;

-- Session tracking
CREATE INDEX IF NOT EXISTS idx_session_id
    ON llm_requests (session_id, timestamp DESC)
    WHERE session_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_trace_id
    ON llm_requests (trace_id)
    WHERE trace_id IS NOT NULL;

-- Provider and model queries
CREATE INDEX IF NOT EXISTS idx_provider_model_timestamp
    ON llm_requests (provider, model, timestamp DESC);

-- Cost queries
CREATE INDEX IF NOT EXISTS idx_cost_timestamp
    ON llm_requests (cost_usd, timestamp DESC);

-- Error tracking
CREATE INDEX IF NOT EXISTS idx_status_code_timestamp
    ON llm_requests (status_code, timestamp DESC)
    WHERE status_code >= 400;

-- Continuous aggregates for better query performance

-- Hourly agent costs
CREATE MATERIALIZED VIEW IF NOT EXISTS llm_costs_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', timestamp) AS bucket,
    provider,
    model,
    agent_type,
    agent_name,
    flow_name,
    chat_agent_name,
    COUNT(*) as request_count,
    SUM(total_tokens) as total_tokens,
    SUM(cost_usd) as total_cost,
    AVG(latency_ms) as avg_latency,
    SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as error_count
FROM llm_requests
GROUP BY bucket, provider, model, agent_type, agent_name, flow_name, chat_agent_name;

-- Refresh policy for continuous aggregate (refresh every 5 minutes)
SELECT add_continuous_aggregate_policy('llm_costs_hourly',
    start_offset => INTERVAL '1 day',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '5 minutes',
    if_not_exists => TRUE
);

-- Daily agent costs
CREATE MATERIALIZED VIEW IF NOT EXISTS llm_costs_daily
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', timestamp) AS bucket,
    provider,
    model,
    agent_type,
    agent_name,
    flow_name,
    chat_agent_name,
    COUNT(*) as request_count,
    SUM(total_tokens) as total_tokens,
    SUM(cost_usd) as total_cost,
    AVG(latency_ms) as avg_latency,
    SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as error_count,
    AVG(cost_usd) as avg_cost_per_request
FROM llm_requests
GROUP BY bucket, provider, model, agent_type, agent_name, flow_name, chat_agent_name;

-- Refresh policy for daily aggregate
SELECT add_continuous_aggregate_policy('llm_costs_daily',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- Retention policy: Keep raw data for 90 days
SELECT add_retention_policy('llm_requests',
    INTERVAL '90 days',
    if_not_exists => TRUE
);

-- Create a simple view for current day costs by agent
CREATE OR REPLACE VIEW today_costs_by_agent AS
SELECT
    agent_type,
    agent_name,
    flow_name,
    chat_agent_name,
    COUNT(*) as requests,
    SUM(total_tokens) as tokens,
    SUM(cost_usd) as cost,
    AVG(latency_ms) as avg_latency_ms
FROM llm_requests
WHERE timestamp >= CURRENT_DATE
GROUP BY agent_type, agent_name, flow_name, chat_agent_name
ORDER BY cost DESC;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO timescale;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO timescale;

-- Insert a test record
INSERT INTO llm_requests (
    provider, model, endpoint,
    agent_type, agent_name,
    total_tokens, cost_usd, latency_ms, status_code
) VALUES (
    'test', 'test-model', '/test',
    'system', 'initialization',
    0, 0.0, 0, 200
);

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'TimescaleDB cost tracking schema initialized successfully!';
    RAISE NOTICE 'Tables: llm_requests';
    RAISE NOTICE 'Views: llm_costs_hourly, llm_costs_daily, today_costs_by_agent';
END $$;
