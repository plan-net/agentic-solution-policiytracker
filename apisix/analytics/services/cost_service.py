"""
Cost query service - handles all database queries for cost analytics
"""
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
import asyncpg
import structlog

from database import get_connection
from models.schemas import (
    CostSummary, AgentCostBreakdown, ModelCostBreakdown,
    ProviderCostBreakdown, TrendDataPoint, SessionRequest, BudgetStatus
)

logger = structlog.get_logger()


class CostService:
    """Service for querying cost data from TimescaleDB."""

    @staticmethod
    def _get_date_range(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days: int = 7
    ) -> Tuple[datetime, datetime]:
        """Calculate date range for queries."""
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=days)
        return start_date, end_date

    async def get_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days: int = 7
    ) -> Tuple[CostSummary, datetime, datetime]:
        """Get overall cost summary for a period."""
        start, end = self._get_date_range(start_date, end_date, days)

        async with get_connection() as conn:
            row = await conn.fetchrow("""
                SELECT
                    COALESCE(SUM(cost_usd), 0) as total_cost,
                    COUNT(*) as total_requests,
                    COALESCE(SUM(total_tokens), 0) as total_tokens,
                    COALESCE(AVG(latency_ms), 0) as avg_latency,
                    SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as error_count
                FROM llm_requests
                WHERE timestamp >= $1 AND timestamp < $2
            """, start, end)

            summary = CostSummary(
                total_cost_usd=float(row['total_cost'] or 0),
                total_requests=row['total_requests'] or 0,
                total_tokens=row['total_tokens'] or 0,
                avg_latency_ms=float(row['avg_latency'] or 0),
                error_count=row['error_count'] or 0,
            )

        return summary, start, end

    async def get_by_provider(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days: int = 7
    ) -> List[ProviderCostBreakdown]:
        """Get cost breakdown by provider."""
        start, end = self._get_date_range(start_date, end_date, days)

        async with get_connection() as conn:
            rows = await conn.fetch("""
                SELECT
                    provider,
                    COALESCE(SUM(cost_usd), 0) as total_cost,
                    COUNT(*) as request_count,
                    COALESCE(SUM(total_tokens), 0) as total_tokens
                FROM llm_requests
                WHERE timestamp >= $1 AND timestamp < $2
                GROUP BY provider
                ORDER BY total_cost DESC
            """, start, end)

            return [
                ProviderCostBreakdown(
                    provider=row['provider'],
                    total_cost_usd=float(row['total_cost'] or 0),
                    request_count=row['request_count'] or 0,
                    total_tokens=row['total_tokens'] or 0,
                )
                for row in rows
            ]

    async def get_by_model(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days: int = 7,
        provider: Optional[str] = None
    ) -> Tuple[List[ModelCostBreakdown], float, datetime, datetime]:
        """Get cost breakdown by model."""
        start, end = self._get_date_range(start_date, end_date, days)

        async with get_connection() as conn:
            if provider:
                rows = await conn.fetch("""
                    SELECT
                        provider,
                        model,
                        COALESCE(SUM(cost_usd), 0) as total_cost,
                        COUNT(*) as request_count,
                        COALESCE(SUM(prompt_tokens), 0) as prompt_tokens,
                        COALESCE(SUM(completion_tokens), 0) as completion_tokens
                    FROM llm_requests
                    WHERE timestamp >= $1 AND timestamp < $2 AND provider = $3
                    GROUP BY provider, model
                    ORDER BY total_cost DESC
                """, start, end, provider)
            else:
                rows = await conn.fetch("""
                    SELECT
                        provider,
                        model,
                        COALESCE(SUM(cost_usd), 0) as total_cost,
                        COUNT(*) as request_count,
                        COALESCE(SUM(prompt_tokens), 0) as prompt_tokens,
                        COALESCE(SUM(completion_tokens), 0) as completion_tokens
                    FROM llm_requests
                    WHERE timestamp >= $1 AND timestamp < $2
                    GROUP BY provider, model
                    ORDER BY total_cost DESC
                """, start, end)

            total_cost = 0.0
            models = []
            for row in rows:
                cost = float(row['total_cost'] or 0)
                count = row['request_count'] or 1
                total_cost += cost
                models.append(ModelCostBreakdown(
                    provider=row['provider'],
                    model=row['model'],
                    total_cost_usd=cost,
                    request_count=row['request_count'] or 0,
                    prompt_tokens=row['prompt_tokens'] or 0,
                    completion_tokens=row['completion_tokens'] or 0,
                    avg_cost_per_request=cost / count if count > 0 else 0,
                ))

            return models, total_cost, start, end

    async def get_by_agent(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days: int = 7,
        agent_type: Optional[str] = None,
        flow_name: Optional[str] = None
    ) -> Tuple[List[AgentCostBreakdown], float, datetime, datetime]:
        """Get cost breakdown by agent."""
        start, end = self._get_date_range(start_date, end_date, days)

        async with get_connection() as conn:
            # Build query with optional filters
            query = """
                SELECT
                    agent_type,
                    agent_name,
                    flow_name,
                    chat_agent_name,
                    COALESCE(SUM(cost_usd), 0) as total_cost,
                    COUNT(*) as request_count,
                    COALESCE(SUM(total_tokens), 0) as total_tokens,
                    COALESCE(AVG(latency_ms), 0) as avg_latency,
                    SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as error_count
                FROM llm_requests
                WHERE timestamp >= $1 AND timestamp < $2
            """
            params = [start, end]

            if agent_type:
                query += f" AND agent_type = ${len(params) + 1}"
                params.append(agent_type)

            if flow_name:
                query += f" AND flow_name = ${len(params) + 1}"
                params.append(flow_name)

            query += """
                GROUP BY agent_type, agent_name, flow_name, chat_agent_name
                ORDER BY total_cost DESC
            """

            rows = await conn.fetch(query, *params)

            total_cost = 0.0
            agents = []
            for row in rows:
                cost = float(row['total_cost'] or 0)
                total_cost += cost
                agents.append(AgentCostBreakdown(
                    agent_type=row['agent_type'],
                    agent_name=row['agent_name'],
                    flow_name=row['flow_name'],
                    chat_agent_name=row['chat_agent_name'],
                    total_cost_usd=cost,
                    request_count=row['request_count'] or 0,
                    total_tokens=row['total_tokens'] or 0,
                    avg_latency_ms=float(row['avg_latency'] or 0),
                    error_count=row['error_count'] or 0,
                ))

            return agents, total_cost, start, end

    async def get_trends(
        self,
        granularity: str = "daily",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days: int = 7,
        agent_type: Optional[str] = None
    ) -> Tuple[List[TrendDataPoint], datetime, datetime]:
        """Get cost trends over time."""
        start, end = self._get_date_range(start_date, end_date, days)

        # Use continuous aggregates for performance
        view_name = "llm_costs_hourly" if granularity == "hourly" else "llm_costs_daily"

        async with get_connection() as conn:
            if agent_type:
                rows = await conn.fetch(f"""
                    SELECT
                        bucket,
                        COALESCE(SUM(total_cost), 0) as cost_usd,
                        COALESCE(SUM(request_count), 0) as request_count,
                        COALESCE(SUM(total_tokens), 0) as total_tokens,
                        COALESCE(AVG(avg_latency), 0) as avg_latency_ms,
                        COALESCE(SUM(error_count), 0) as error_count
                    FROM {view_name}
                    WHERE bucket >= $1 AND bucket < $2 AND agent_type = $3
                    GROUP BY bucket
                    ORDER BY bucket
                """, start, end, agent_type)
            else:
                rows = await conn.fetch(f"""
                    SELECT
                        bucket,
                        COALESCE(SUM(total_cost), 0) as cost_usd,
                        COALESCE(SUM(request_count), 0) as request_count,
                        COALESCE(SUM(total_tokens), 0) as total_tokens,
                        COALESCE(AVG(avg_latency), 0) as avg_latency_ms,
                        COALESCE(SUM(error_count), 0) as error_count
                    FROM {view_name}
                    WHERE bucket >= $1 AND bucket < $2
                    GROUP BY bucket
                    ORDER BY bucket
                """, start, end)

            data_points = [
                TrendDataPoint(
                    bucket=row['bucket'],
                    cost_usd=float(row['cost_usd'] or 0),
                    request_count=row['request_count'] or 0,
                    total_tokens=row['total_tokens'] or 0,
                    avg_latency_ms=float(row['avg_latency_ms'] or 0),
                    error_count=row['error_count'] or 0,
                )
                for row in rows
            ]

            return data_points, start, end

    async def get_session_costs(self, session_id: str) -> Tuple[List[SessionRequest], float, int, int]:
        """Get cost details for a specific session."""
        async with get_connection() as conn:
            rows = await conn.fetch("""
                SELECT
                    timestamp,
                    provider,
                    model,
                    agent_name,
                    total_tokens as tokens,
                    cost_usd,
                    latency_ms,
                    status_code
                FROM llm_requests
                WHERE session_id = $1
                ORDER BY timestamp
            """, session_id)

            total_cost = 0.0
            total_tokens = 0
            requests = []

            for row in rows:
                cost = float(row['cost_usd'] or 0)
                tokens = row['tokens'] or 0
                total_cost += cost
                total_tokens += tokens

                requests.append(SessionRequest(
                    timestamp=row['timestamp'],
                    provider=row['provider'],
                    model=row['model'],
                    agent_name=row['agent_name'],
                    tokens=tokens,
                    cost_usd=cost,
                    latency_ms=row['latency_ms'] or 0,
                    status_code=row['status_code'] or 200,
                ))

            return requests, total_cost, len(requests), total_tokens

    async def check_budget(
        self,
        threshold_type: str,
        threshold_usd: float,
        scope: Optional[str] = None
    ) -> BudgetStatus:
        """Check spend against a budget threshold."""
        now = datetime.now()

        # Determine period based on type
        if threshold_type == "daily":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif threshold_type == "weekly":
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        elif threshold_type == "monthly":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start = now - timedelta(days=30)

        async with get_connection() as conn:
            if scope:
                # Scope could be agent_type or agent_name
                row = await conn.fetchrow("""
                    SELECT COALESCE(SUM(cost_usd), 0) as current_spend
                    FROM llm_requests
                    WHERE timestamp >= $1
                      AND (agent_type = $2 OR agent_name = $2)
                """, start, scope)
            else:
                row = await conn.fetchrow("""
                    SELECT COALESCE(SUM(cost_usd), 0) as current_spend
                    FROM llm_requests
                    WHERE timestamp >= $1
                """, start)

            current_spend = float(row['current_spend'] or 0)
            remaining = threshold_usd - current_spend
            percentage = (current_spend / threshold_usd * 100) if threshold_usd > 0 else 0

            return BudgetStatus(
                threshold_type=threshold_type,
                threshold_usd=threshold_usd,
                current_spend_usd=current_spend,
                remaining_usd=max(0, remaining),
                percentage_used=percentage,
                is_exceeded=current_spend > threshold_usd,
                scope=scope,
            )
