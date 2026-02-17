"""Weekly reports management for the Policy Tracker UI."""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from src.config import settings

logger = logging.getLogger(__name__)


class ReportStatus(str, Enum):
    """Report generation status."""
    PENDING = "pending"
    WORKING = "working"
    COMPLETE = "complete"
    FAILED = "failed"


class ReportType(str, Enum):
    """Type of report."""
    WEEKLY = "weekly"
    DAILY = "daily"
    DEEP_DIVE = "deep_dive"
    SPOTLIGHT = "spotlight"


class ReportSummary(BaseModel):
    """Summary of a report for listing."""

    report_id: str
    title: str
    report_type: ReportType = ReportType.WEEKLY
    status: ReportStatus = ReportStatus.PENDING
    created_at: str
    updated_at: str
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None


class ReportDetail(BaseModel):
    """Detailed report information."""

    report_id: str
    title: str
    report_type: ReportType = ReportType.WEEKLY
    status: ReportStatus = ReportStatus.PENDING
    created_at: str
    updated_at: str
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    content: Optional[str] = None
    sections: list[dict[str, Any]] = Field(default_factory=list)
    entity_uuids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClaudeModel(str, Enum):
    """Available Claude models for report generation."""
    SONNET_4 = "claude-sonnet-4-20250514"
    OPUS_4 = "claude-opus-4-20250514"


class CreateReportRequest(BaseModel):
    """Request to create a new report."""

    title: str
    report_type: ReportType = ReportType.WEEKLY
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    claude_model: ClaudeModel = ClaudeModel.SONNET_4
    include_events: bool = True
    options: dict[str, Any] = Field(default_factory=dict)


class UpdateReportRequest(BaseModel):
    """Request to update a report."""

    title: Optional[str] = None
    status: Optional[ReportStatus] = None
    content: Optional[str] = None
    sections: Optional[list[dict[str, Any]]] = None


class ReportsService:
    """Service for managing reports in Neo4j."""

    def __init__(self, driver):
        self.driver = driver

    def _generate_report_id(self) -> str:
        """Generate a unique report ID."""
        return f"report_{uuid.uuid4().hex[:16]}"

    async def list_reports(
        self,
        limit: int = 50,
        status: Optional[ReportStatus] = None,
        report_type: Optional[ReportType] = None
    ) -> list[ReportSummary]:
        """List reports with optional filters.

        Args:
            limit: Maximum number of reports to return
            status: Filter by status
            report_type: Filter by report type

        Returns:
            List of report summaries
        """
        reports = []

        try:
            async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                # Build query with optional filters
                where_clauses = []
                params = {"limit": limit}

                if status:
                    where_clauses.append("r.status = $status")
                    params["status"] = status.value

                if report_type:
                    where_clauses.append("r.report_type = $report_type")
                    params["report_type"] = report_type.value

                where_clause = ""
                if where_clauses:
                    where_clause = "WHERE " + " AND ".join(where_clauses)

                query = f"""
                    MATCH (r:Report)
                    {where_clause}
                    RETURN r.report_id AS report_id,
                           r.title AS title,
                           r.report_type AS report_type,
                           r.status AS status,
                           r.created_at AS created_at,
                           r.updated_at AS updated_at,
                           r.date_range_start AS date_range_start,
                           r.date_range_end AS date_range_end
                    ORDER BY r.updated_at DESC
                    LIMIT $limit
                """

                result = await session.run(query, **params)
                records = await result.data()

                for record in records:
                    # Parse dates
                    created_at = record.get("created_at")
                    updated_at = record.get("updated_at")

                    if hasattr(created_at, "isoformat"):
                        created_at = created_at.isoformat()
                    elif created_at is None:
                        created_at = datetime.now().isoformat()

                    if hasattr(updated_at, "isoformat"):
                        updated_at = updated_at.isoformat()
                    elif updated_at is None:
                        updated_at = created_at

                    # Parse date ranges
                    date_range_start = record.get("date_range_start")
                    date_range_end = record.get("date_range_end")

                    if hasattr(date_range_start, "isoformat"):
                        date_range_start = date_range_start.isoformat()
                    if hasattr(date_range_end, "isoformat"):
                        date_range_end = date_range_end.isoformat()

                    reports.append(ReportSummary(
                        report_id=record["report_id"],
                        title=record.get("title") or "Untitled Report",
                        report_type=ReportType(record.get("report_type", "weekly")),
                        status=ReportStatus(record.get("status", "pending")),
                        created_at=str(created_at),
                        updated_at=str(updated_at),
                        date_range_start=date_range_start,
                        date_range_end=date_range_end,
                    ))

        except Exception as e:
            logger.error(f"Error listing reports: {e}", exc_info=True)

        return reports

    async def get_report(self, report_id: str) -> Optional[ReportDetail]:
        """Get detailed information about a report.

        Args:
            report_id: The report ID to retrieve

        Returns:
            Report details or None if not found
        """
        try:
            async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                result = await session.run(
                    """
                    MATCH (r:Report {report_id: $report_id})
                    RETURN r.report_id AS report_id,
                           r.title AS title,
                           r.report_type AS report_type,
                           r.status AS status,
                           r.created_at AS created_at,
                           r.updated_at AS updated_at,
                           r.date_range_start AS date_range_start,
                           r.date_range_end AS date_range_end,
                           r.content AS content,
                           r.sections_json AS sections_json,
                           r.entity_uuids AS entity_uuids,
                           r.metadata_json AS metadata_json
                    """,
                    report_id=report_id
                )

                record = await result.single()

                if not record:
                    return None

                # Parse dates
                created_at = record.get("created_at")
                updated_at = record.get("updated_at")

                if hasattr(created_at, "isoformat"):
                    created_at = created_at.isoformat()
                if hasattr(updated_at, "isoformat"):
                    updated_at = updated_at.isoformat()

                # Parse date ranges
                date_range_start = record.get("date_range_start")
                date_range_end = record.get("date_range_end")

                if hasattr(date_range_start, "isoformat"):
                    date_range_start = date_range_start.isoformat()
                if hasattr(date_range_end, "isoformat"):
                    date_range_end = date_range_end.isoformat()

                # Parse JSON fields
                sections_json = record.get("sections_json") or "[]"
                try:
                    sections = json.loads(sections_json)
                except json.JSONDecodeError:
                    sections = []

                metadata_json = record.get("metadata_json") or "{}"
                try:
                    metadata = json.loads(metadata_json)
                except json.JSONDecodeError:
                    metadata = {}

                return ReportDetail(
                    report_id=record["report_id"],
                    title=record.get("title") or "Untitled Report",
                    report_type=ReportType(record.get("report_type", "weekly")),
                    status=ReportStatus(record.get("status", "pending")),
                    created_at=str(created_at or datetime.now().isoformat()),
                    updated_at=str(updated_at or created_at or datetime.now().isoformat()),
                    date_range_start=date_range_start,
                    date_range_end=date_range_end,
                    content=record.get("content"),
                    sections=sections,
                    entity_uuids=record.get("entity_uuids") or [],
                    metadata=metadata,
                )

        except Exception as e:
            logger.error(f"Error getting report {report_id}: {e}", exc_info=True)
            return None

    async def create_report(self, request: CreateReportRequest) -> Optional[ReportDetail]:
        """Create a new report.

        Args:
            request: Report creation request

        Returns:
            Created report details or None on error

        Raises:
            Exception: Re-raised from Neo4j errors for proper error handling
        """
        report_id = self._generate_report_id()

        # Merge model options into metadata
        metadata = {
            **request.options,
            "claude_model": request.claude_model.value,
            "include_events": request.include_events,
        }

        logger.info(
            f"Creating report {report_id}: title={request.title}, "
            f"type={request.report_type}, dates={request.date_range_start} to {request.date_range_end}"
        )

        try:
            async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                await session.run(
                    """
                    CREATE (r:Report {
                        report_id: $report_id,
                        title: $title,
                        report_type: $report_type,
                        status: $status,
                        created_at: datetime(),
                        updated_at: datetime(),
                        date_range_start: $date_range_start,
                        date_range_end: $date_range_end,
                        content: null,
                        sections_json: '[]',
                        entity_uuids: [],
                        metadata_json: $metadata_json
                    })
                    """,
                    report_id=report_id,
                    title=request.title,
                    report_type=request.report_type.value,
                    status=ReportStatus.PENDING.value,
                    date_range_start=request.date_range_start,
                    date_range_end=request.date_range_end,
                    metadata_json=json.dumps(metadata),
                )

                logger.info(f"Created report {report_id}: {request.title}")

                # Return the created report
                return await self.get_report(report_id)

        except Exception as e:
            logger.error(f"Error creating report: {e}", exc_info=True)
            # Re-raise to let the API endpoint handle it properly
            raise

    async def update_report(
        self,
        report_id: str,
        request: UpdateReportRequest
    ) -> Optional[ReportDetail]:
        """Update a report.

        Args:
            report_id: The report ID to update
            request: Update request

        Returns:
            Updated report details or None if not found
        """
        try:
            async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                # Build dynamic SET clause
                set_parts = ["r.updated_at = datetime()"]
                params = {"report_id": report_id}

                if request.title is not None:
                    set_parts.append("r.title = $title")
                    params["title"] = request.title

                if request.status is not None:
                    set_parts.append("r.status = $status")
                    params["status"] = request.status.value

                if request.content is not None:
                    set_parts.append("r.content = $content")
                    params["content"] = request.content

                if request.sections is not None:
                    set_parts.append("r.sections_json = $sections_json")
                    params["sections_json"] = json.dumps(request.sections)

                set_clause = ", ".join(set_parts)

                result = await session.run(
                    f"""
                    MATCH (r:Report {{report_id: $report_id}})
                    SET {set_clause}
                    RETURN count(r) AS updated
                    """,
                    **params
                )

                record = await result.single()

                if not record or record["updated"] == 0:
                    return None

                return await self.get_report(report_id)

        except Exception as e:
            logger.error(f"Error updating report {report_id}: {e}", exc_info=True)
            return None

    async def delete_report(self, report_id: str) -> bool:
        """Delete a report.

        Args:
            report_id: The report ID to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                result = await session.run(
                    """
                    MATCH (r:Report {report_id: $report_id})
                    DELETE r
                    RETURN count(r) AS deleted
                    """,
                    report_id=report_id
                )

                record = await result.single()
                return record and record["deleted"] > 0

        except Exception as e:
            logger.error(f"Error deleting report {report_id}: {e}", exc_info=True)
            return False

    async def generate_report(self, report_id: str) -> bool:
        """Start generating a report via the weekly_report_sdk flow.

        Triggers the Claude Agent SDK-based report generation flow
        by calling the Kodosumi endpoint via HTTP.

        Args:
            report_id: The report ID to generate

        Returns:
            True if started successfully
        """
        try:
            # Get the report to retrieve its configuration
            report = await self.get_report(report_id)
            if not report:
                logger.error(f"Report {report_id} not found")
                return False

            # Update status to working
            update_result = await self.update_report(
                report_id,
                UpdateReportRequest(status=ReportStatus.WORKING)
            )

            if not update_result:
                return False

            # Extract configuration from report metadata
            claude_model = report.metadata.get("claude_model", "claude-sonnet-4-20250514")
            include_events = report.metadata.get("include_events", True)

            # Build week input from date range
            week_input = ""
            if report.date_range_start:
                week_input = report.date_range_start  # Use start date as the Monday

            logger.info(
                f"Triggering weekly_report_sdk for report {report_id} "
                f"with model={claude_model}, week={week_input}"
            )

            # Trigger the weekly_report_sdk flow asynchronously
            asyncio.create_task(
                self._trigger_report_generation(
                    report_id=report_id,
                    week_input=week_input,
                    claude_model=claude_model,
                    include_events=include_events,
                )
            )

            return True

        except Exception as e:
            logger.error(f"Error starting report generation {report_id}: {e}", exc_info=True)
            # Mark report as failed
            await self.update_report(
                report_id,
                UpdateReportRequest(status=ReportStatus.FAILED)
            )
            return False

    async def _trigger_report_generation(
        self,
        report_id: str,
        week_input: str,
        claude_model: str,
        include_events: bool,
    ):
        """Generate the weekly report using WeeklyReportAgent directly.

        This runs as a background task to avoid blocking the API response.
        Unlike the HTTP approach, this directly invokes the agent for reliability.

        Args:
            report_id: The report ID being generated
            week_input: Week input (date or KW format)
            claude_model: Claude model to use
            include_events: Whether to include events section
        """
        try:
            # Import here to avoid circular imports
            from src.flows.weekly_digest_v2.date_resolver import DateResolver
            from src.flows.weekly_report_sdk.agent import WeeklyReportAgent

            logger.info(
                f"Starting report generation for {report_id} "
                f"with model={claude_model}, week={week_input}, include_events={include_events}"
            )

            # Resolve dates
            resolver = DateResolver()
            resolved = resolver.resolve(week_input)
            week_start = resolved["week_start"]
            week_end = resolved["week_end"]
            week_label = resolved["week_label"]

            logger.info(f"Resolved dates: {week_label} ({week_start} to {week_end})")

            # Initialize the agent
            agent = WeeklyReportAgent(
                model=claude_model,
                max_turns=50,  # Increased from 30 for comprehensive report generation
            )

            try:
                # Generate the report
                # Pass report_id as session_id for consistent tracking in LangFuse and cost analytics
                result = await agent.generate_report(
                    week_start=week_start,
                    week_end=week_end,
                    week_label=week_label,
                    include_events=include_events,
                    session_id=report_id,
                )

                report_content = result["report_content"]
                metadata = result["metadata"]
                tool_calls = result["tool_calls"]

                logger.info(
                    f"Report generated: {len(report_content)} chars, "
                    f"{metadata.get('turns', 0)} turns, {len(tool_calls)} tool calls"
                )

                # Update the report with content and mark as complete
                await self.update_report(
                    report_id,
                    UpdateReportRequest(
                        content=report_content,
                        status=ReportStatus.COMPLETE,
                        sections=[
                            {
                                "type": "metadata",
                                "model": claude_model,
                                "turns": metadata.get("turns", 0),
                                "tool_calls_count": len(tool_calls),
                                "generated_at": metadata.get("generated_at"),
                            }
                        ],
                    ),
                )

                logger.info(f"Report {report_id} completed successfully")

            finally:
                # Cleanup agent resources
                await agent.close()

        except Exception as e:
            logger.error(f"Error generating report {report_id}: {e}", exc_info=True)
            await self.update_report(
                report_id,
                UpdateReportRequest(status=ReportStatus.FAILED)
            )
