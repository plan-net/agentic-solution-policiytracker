"""
Ingest endpoint for receiving cost records from APISIX plugin and Claude Agent SDK
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import structlog

from database import get_pool

router = APIRouter(prefix="/ingest", tags=["Ingest"])
logger = structlog.get_logger()


class CostRecord(BaseModel):
    """Cost record from APISIX plugin or Claude Agent SDK.

    For SDK records, request_headers can contain cache token metadata:
    {
        "cache_creation_tokens": int,
        "cache_read_tokens": int,
        "non_cached_input_tokens": int,
        "sdk_source": "claude_agent_sdk"
    }
    """
    timestamp: Optional[str] = None
    provider: str
    model: str
    endpoint: Optional[str] = None
    agent_type: Optional[str] = None
    agent_name: Optional[str] = None
    flow_name: Optional[str] = None
    chat_agent_name: Optional[str] = None
    session_id: Optional[str] = None
    trace_id: Optional[str] = None
    user_id: Optional[str] = None
    project_id: Optional[str] = "political_monitoring_v2"
    prompt_tokens: Optional[int] = 0
    completion_tokens: Optional[int] = 0
    total_tokens: Optional[int] = 0
    cost_usd: Optional[float] = 0.0
    latency_ms: Optional[int] = 0
    status_code: Optional[int] = None
    request_size_bytes: Optional[int] = None
    response_size_bytes: Optional[int] = None
    request_headers: Optional[Dict[str, Any]] = None  # JSONB for cache token metadata


class IngestRequest(BaseModel):
    """Batch of cost records"""
    records: List[CostRecord]


class IngestResponse(BaseModel):
    """Response from ingest endpoint"""
    success: bool
    records_inserted: int
    message: Optional[str] = None


@router.post("/costs", response_model=IngestResponse)
async def ingest_costs(request: IngestRequest):
    """
    Receive and store cost records from APISIX plugin.

    This endpoint is called by the APISIX llm-cost-tracker plugin
    to store LLM cost data in TimescaleDB.
    """
    if not request.records:
        return IngestResponse(
            success=True,
            records_inserted=0,
            message="No records to insert"
        )

    try:
        pool = await get_pool()

        # Build batch insert
        values = []
        for record in request.records:
            # Convert request_headers dict to JSON string for JSONB storage
            headers_json = json.dumps(record.request_headers) if record.request_headers else None

            values.append((
                datetime.now() if not record.timestamp else datetime.fromisoformat(record.timestamp.replace(' ', 'T')),
                record.provider,
                record.model,
                record.endpoint,
                record.agent_type,
                record.agent_name,
                record.flow_name,
                record.chat_agent_name,
                record.session_id,
                record.trace_id,
                record.user_id,
                record.project_id,
                record.prompt_tokens or 0,
                record.completion_tokens or 0,
                record.total_tokens or 0,
                record.cost_usd or 0.0,
                record.latency_ms or 0,
                record.status_code,
                record.request_size_bytes,
                record.response_size_bytes,
                headers_json,
            ))

        async with pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO llm_requests (
                    timestamp, provider, model, endpoint,
                    agent_type, agent_name, flow_name, chat_agent_name,
                    session_id, trace_id, user_id, project_id,
                    prompt_tokens, completion_tokens, total_tokens, cost_usd,
                    latency_ms, status_code,
                    request_size_bytes, response_size_bytes, request_headers
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21
                )
                """,
                values
            )

        # Log with cache token details if present
        first_record = request.records[0] if request.records else None
        cache_info = None
        if first_record and first_record.request_headers:
            cache_info = {
                "cache_creation": first_record.request_headers.get("cache_creation_tokens", 0),
                "cache_read": first_record.request_headers.get("cache_read_tokens", 0),
            }

        logger.info(
            "Ingested cost records",
            count=len(request.records),
            first_model=first_record.model if first_record else None,
            first_agent=first_record.agent_name if first_record else None,
            cache_tokens=cache_info,
        )

        return IngestResponse(
            success=True,
            records_inserted=len(request.records),
        )

    except Exception as e:
        logger.error("Failed to ingest cost records", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to ingest records: {str(e)}")
