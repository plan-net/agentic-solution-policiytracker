--
-- TimescaleDB Initialization Script for External API Tracking
-- Policy Tracker - v0.1.0
--
-- This script creates the schema for tracking external (non-LLM) API requests
-- like Exa search, DPA articles, Bundestag API, etc.
--

-- Main external API requests table
CREATE TABLE IF NOT EXISTS external_api_requests (
    id BIGSERIAL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- API Information
    api_name VARCHAR(50) NOT NULL,              -- 'exa-search', 'exa-contents', 'dpa-articles', 'bundestag-vorgang', 'bundestag-drucksache'
    endpoint VARCHAR(200) NOT NULL,             -- Full endpoint path
    method VARCHAR(10) NOT NULL DEFAULT 'GET',  -- HTTP method

    -- Agent-Level Tracking (same as LLM tracking for consistency)
    agent_type VARCHAR(50),                     -- 'kodosumi_flow', 'chat_agent', etc.
    agent_name VARCHAR(100),                    -- Specific agent identifier
    flow_name VARCHAR(100),                     -- For Kodosumi flows
    session_id VARCHAR(100),                    -- Track conversation/processing sessions
    trace_id VARCHAR(100),                      -- For distributed tracing

    -- User & Project Information
    user_id VARCHAR(100),
    project_id VARCHAR(100) DEFAULT 'political_monitoring_v2',

    -- Performance Metrics
    latency_ms INTEGER,                         -- Request latency in milliseconds
    status_code INTEGER,                        -- HTTP status code
    error_message TEXT,                         -- Error details if request failed

    -- Request/Response Metadata
    request_size_bytes INTEGER,                 -- Size of request payload
    response_size_bytes INTEGER,                -- Size of response payload
    request_headers JSONB,                      -- Store important headers as JSON

    -- API-specific metrics (stored as JSONB for flexibility)
    api_metadata JSONB,                         -- e.g., {"results_count": 10, "query": "..."}

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (id, timestamp)
);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('external_api_requests', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Indexes for efficient querying

-- API-level queries
CREATE INDEX IF NOT EXISTS idx_ext_api_name_timestamp
    ON external_api_requests (api_name, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_ext_api_endpoint_timestamp
    ON external_api_requests (endpoint, timestamp DESC);

-- Agent-level queries
CREATE INDEX IF NOT EXISTS idx_ext_agent_type_timestamp
    ON external_api_requests (agent_type, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_ext_agent_name_timestamp
    ON external_api_requests (agent_name, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_ext_flow_name_timestamp
    ON external_api_requests (flow_name, timestamp DESC)
    WHERE flow_name IS NOT NULL;

-- Session tracking
CREATE INDEX IF NOT EXISTS idx_ext_session_id
    ON external_api_requests (session_id, timestamp DESC)
    WHERE session_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_ext_trace_id
    ON external_api_requests (trace_id)
    WHERE trace_id IS NOT NULL;

-- Error tracking
CREATE INDEX IF NOT EXISTS idx_ext_status_code_timestamp
    ON external_api_requests (status_code, timestamp DESC)
    WHERE status_code >= 400;

-- Continuous aggregates for better query performance

-- Hourly API usage stats
CREATE MATERIALIZED VIEW IF NOT EXISTS external_api_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', timestamp) AS bucket,
    api_name,
    endpoint,
    method,
    agent_type,
    agent_name,
    flow_name,
    COUNT(*) as request_count,
    AVG(latency_ms) as avg_latency_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95_latency_ms,
    SUM(request_size_bytes) as total_request_bytes,
    SUM(response_size_bytes) as total_response_bytes,
    SUM(CASE WHEN status_code >= 200 AND status_code < 300 THEN 1 ELSE 0 END) as success_count,
    SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as error_count
FROM external_api_requests
GROUP BY bucket, api_name, endpoint, method, agent_type, agent_name, flow_name;

-- Refresh policy for hourly aggregate (refresh every 5 minutes, include last minute)
SELECT add_continuous_aggregate_policy('external_api_hourly',
    start_offset => INTERVAL '1 day',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '5 minutes',
    if_not_exists => TRUE
);

-- Daily API usage stats
CREATE MATERIALIZED VIEW IF NOT EXISTS external_api_daily
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', timestamp) AS bucket,
    api_name,
    endpoint,
    method,
    agent_type,
    agent_name,
    flow_name,
    COUNT(*) as request_count,
    AVG(latency_ms) as avg_latency_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95_latency_ms,
    SUM(request_size_bytes) as total_request_bytes,
    SUM(response_size_bytes) as total_response_bytes,
    SUM(CASE WHEN status_code >= 200 AND status_code < 300 THEN 1 ELSE 0 END) as success_count,
    SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as error_count
FROM external_api_requests
GROUP BY bucket, api_name, endpoint, method, agent_type, agent_name, flow_name;

-- Refresh policy for daily aggregate (refresh every 10 minutes, include last minute)
SELECT add_continuous_aggregate_policy('external_api_daily',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '10 minutes',
    if_not_exists => TRUE
);

-- Retention policy: Keep raw data for 90 days
SELECT add_retention_policy('external_api_requests',
    INTERVAL '90 days',
    if_not_exists => TRUE
);

-- Create a simple view for current day stats by API
CREATE OR REPLACE VIEW today_external_api_stats AS
SELECT
    api_name,
    COUNT(*) as requests,
    AVG(latency_ms)::INTEGER as avg_latency_ms,
    SUM(CASE WHEN status_code >= 200 AND status_code < 300 THEN 1 ELSE 0 END) as success_count,
    SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as error_count,
    ROUND(100.0 * SUM(CASE WHEN status_code >= 200 AND status_code < 300 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) as success_rate_pct
FROM external_api_requests
WHERE timestamp >= CURRENT_DATE
GROUP BY api_name
ORDER BY requests DESC;

-- Create a view for API usage by flow
CREATE OR REPLACE VIEW today_external_api_by_flow AS
SELECT
    flow_name,
    api_name,
    COUNT(*) as requests,
    AVG(latency_ms)::INTEGER as avg_latency_ms,
    SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as error_count
FROM external_api_requests
WHERE timestamp >= CURRENT_DATE
  AND flow_name IS NOT NULL
GROUP BY flow_name, api_name
ORDER BY flow_name, requests DESC;

-- Grant permissions
GRANT ALL PRIVILEGES ON external_api_requests TO timescale;
GRANT ALL PRIVILEGES ON external_api_hourly TO timescale;
GRANT ALL PRIVILEGES ON external_api_daily TO timescale;
GRANT SELECT ON today_external_api_stats TO timescale;
GRANT SELECT ON today_external_api_by_flow TO timescale;

-- Insert a test record
INSERT INTO external_api_requests (
    api_name, endpoint, method,
    agent_type, agent_name,
    latency_ms, status_code
) VALUES (
    'test', '/test', 'GET',
    'system', 'initialization',
    0, 200
);

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'External API tracking schema initialized successfully!';
    RAISE NOTICE 'Tables: external_api_requests';
    RAISE NOTICE 'Continuous Aggregates: external_api_hourly, external_api_daily';
    RAISE NOTICE 'Views: today_external_api_stats, today_external_api_by_flow';
END $$;
