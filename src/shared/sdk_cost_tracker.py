"""SDK Cost Tracker - sends Claude Agent SDK costs to TimescaleDB.

This module provides unified cost tracking for Claude Agent SDK sessions,
enabling a single pane of glass for all LLM cost analysis alongside
APISIX-tracked costs.

The SDK bypasses APISIX gateway (uses internal CLI), so this tracker
sends cost records directly to the cost-analytics service.
"""

import aiohttp
import os
import structlog
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

logger = structlog.get_logger()


@dataclass
class SDKCostRecord:
    """Cost record from Claude Agent SDK session.

    Attributes:
        provider: LLM provider (default: "anthropic")
        model: Model identifier (e.g., "claude-sonnet-4-20250514")
        agent_type: Type of agent ("chat_agent" or "kodosumi_flow")
        agent_name: Specific agent name (e.g., "PolicyTrackerSDKAgent")
        session_id: Session identifier for correlation with LangFuse/LangWatch
        prompt_tokens: Number of input tokens (non-cached)
        completion_tokens: Number of output tokens
        total_tokens: Total tokens (all types combined)
        cost_usd: Total cost in USD from SDK
        latency_ms: Request latency in milliseconds
        flow_name: Optional flow name for Kodosumi flows
        trace_id: Optional trace ID for distributed tracing
        cache_creation_tokens: Tokens used for creating prompt cache
        cache_read_tokens: Tokens read from prompt cache (discounted pricing)
        web_search_requests: Number of web searches ($0.01 each)
        web_fetch_requests: Number of web fetches (free, tokens only)
    """

    provider: str = "anthropic"
    model: str = ""
    agent_type: str = "chat_agent"  # or "kodosumi_flow"
    agent_name: str = ""
    session_id: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    flow_name: Optional[str] = None
    trace_id: Optional[str] = None
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    web_search_requests: int = 0
    web_fetch_requests: int = 0


class SDKCostTracker:
    """Sends SDK cost records to cost-analytics service for TimescaleDB storage.

    This tracker enables unified cost tracking by sending Claude Agent SDK
    costs to the same TimescaleDB table used by APISIX llm-cost-tracker plugin.

    Environment Variables:
        COST_ANALYTICS_URL: Base URL for cost-analytics service (default: http://localhost:8090)
        SDK_COST_TRACKING_ENABLED: Enable/disable tracking (default: true)

    Note: Environment variables are read lazily at request time to support
    Ray Serve runtime_env configuration.
    """

    def __init__(self):
        """Initialize the SDK cost tracker."""
        # Don't read env vars here - they may not be set yet in Ray Serve
        self._analytics_url = None
        self._enabled = None
        self._initialized = False

    def _lazy_init(self):
        """Lazily initialize from environment variables."""
        if self._initialized:
            return

        self._analytics_url = os.getenv(
            "COST_ANALYTICS_URL", "http://localhost:8090"
        )
        self._enabled = (
            os.getenv("SDK_COST_TRACKING_ENABLED", "true").lower() == "true"
        )
        self._initialized = True

        if self._enabled:
            logger.info(
                "SDK cost tracker initialized",
                analytics_url=self._analytics_url,
            )
        else:
            logger.info("SDK cost tracking is disabled")

    @property
    def analytics_url(self) -> str:
        """Get the analytics URL, initializing lazily if needed."""
        self._lazy_init()
        return self._analytics_url

    @property
    def enabled(self) -> bool:
        """Check if tracking is enabled, initializing lazily if needed."""
        self._lazy_init()
        return self._enabled

    async def record_cost(self, record: SDKCostRecord) -> bool:
        """Send cost record to TimescaleDB via analytics service.

        Args:
            record: SDK cost record with session details and usage metrics

        Returns:
            True if record was successfully sent, False otherwise
        """
        # Lazy init ensures env vars are read at request time
        if not self.enabled:
            logger.debug("SDK cost tracking disabled, skipping record")
            return False

        # Get URL at request time (after Ray Serve env is available)
        analytics_url = self.analytics_url

        # Store extended usage details in request_headers JSONB field
        # This avoids schema migration while preserving full token/tool breakdown
        extended_metadata = None
        has_cache = record.cache_creation_tokens > 0 or record.cache_read_tokens > 0
        has_web_tools = record.web_search_requests > 0 or record.web_fetch_requests > 0

        if has_cache or has_web_tools:
            extended_metadata = {
                "sdk_source": "claude_agent_sdk",
            }
            # Cache token breakdown
            if has_cache:
                extended_metadata["cache_creation_tokens"] = record.cache_creation_tokens
                extended_metadata["cache_read_tokens"] = record.cache_read_tokens
                extended_metadata["non_cached_input_tokens"] = record.prompt_tokens
            # Server tool usage (web search costs $0.01/search, web fetch is free)
            if has_web_tools:
                extended_metadata["web_search_requests"] = record.web_search_requests
                extended_metadata["web_fetch_requests"] = record.web_fetch_requests
                extended_metadata["web_search_cost_usd"] = record.web_search_requests * 0.01

        payload = {
            "records": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "provider": record.provider,
                    "model": record.model,
                    "agent_type": record.agent_type,
                    "agent_name": record.agent_name,
                    "session_id": record.session_id,
                    "prompt_tokens": record.prompt_tokens,
                    "completion_tokens": record.completion_tokens,
                    "total_tokens": record.total_tokens,
                    "cost_usd": record.cost_usd,
                    "latency_ms": record.latency_ms,
                    "flow_name": record.flow_name,
                    "trace_id": record.trace_id,
                    "project_id": "political_monitoring_v2",
                    "request_headers": extended_metadata,
                }
            ]
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{analytics_url}/api/ingest/costs",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    if response.status == 200:
                        logger.info(
                            "SDK cost recorded to TimescaleDB",
                            agent=record.agent_name,
                            session_id=record.session_id,
                            cost_usd=record.cost_usd,
                            total_tokens=record.total_tokens,
                            prompt_tokens=record.prompt_tokens,
                            completion_tokens=record.completion_tokens,
                            cache_creation=record.cache_creation_tokens,
                            cache_read=record.cache_read_tokens,
                            web_searches=record.web_search_requests,
                            web_fetches=record.web_fetch_requests,
                            model=record.model,
                        )
                        return True
                    else:
                        error_text = await response.text()
                        logger.warning(
                            "Failed to record SDK cost",
                            status=response.status,
                            error=error_text,
                        )
                        return False
        except aiohttp.ClientError as e:
            logger.error(
                "Network error recording SDK cost",
                error=str(e),
                analytics_url=analytics_url,
            )
            return False
        except Exception as e:
            logger.error(
                "Unexpected error recording SDK cost",
                error=str(e),
                error_type=type(e).__name__,
            )
            return False


# Singleton instance for easy import
sdk_cost_tracker = SDKCostTracker()
