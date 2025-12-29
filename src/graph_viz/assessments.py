"""Assessments management for the Policy Tracker UI."""

import json
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from src.config import settings

logger = logging.getLogger(__name__)


class AssessmentStatus(str, Enum):
    """Assessment processing status."""
    PENDING = "pending"
    WORKING = "working"
    COMPLETE = "complete"
    FAILED = "failed"
    READY = "ready"


class AssessmentType(str, Enum):
    """Type of assessment."""
    MONITORING = "monitoring"
    DAILY_FOCUS = "daily_focus"
    DEEP_DIVE = "deep_dive"
    SPOTLIGHT = "spotlight"
    CUSTOM = "custom"


class AssessmentSummary(BaseModel):
    """Summary of an assessment for listing."""

    assessment_id: str
    title: str
    assessment_type: AssessmentType = AssessmentType.CUSTOM
    status: AssessmentStatus = AssessmentStatus.PENDING
    created_at: str
    updated_at: str
    prompt: Optional[str] = None


class AssessmentInsight(BaseModel):
    """A single insight within an assessment."""

    id: str
    title: str
    paragraphs: list[str] = Field(default_factory=list)
    entity_uuids: list[str] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)


class RelatedEntity(BaseModel):
    """Entity related to an assessment."""

    uuid: Optional[str] = None
    name: str
    type: str
    description: Optional[str] = None
    region: Optional[str] = None
    focus_areas: list[str] = Field(default_factory=list)
    closest_entities: list[dict[str, str]] = Field(default_factory=list)


class AssessmentDetail(BaseModel):
    """Detailed assessment information."""

    assessment_id: str
    title: str
    assessment_type: AssessmentType = AssessmentType.CUSTOM
    status: AssessmentStatus = AssessmentStatus.PENDING
    created_at: str
    updated_at: str
    prompt: Optional[str] = None
    include_web_research: bool = False
    insights: list[AssessmentInsight] = Field(default_factory=list)
    related_entity: Optional[RelatedEntity] = None
    entity_uuids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    messages: list[dict[str, Any]] = Field(default_factory=list)


class CreateAssessmentRequest(BaseModel):
    """Request to create a new assessment."""

    title: str
    prompt: str
    assessment_type: AssessmentType = AssessmentType.CUSTOM
    include_web_research: bool = False
    options: dict[str, Any] = Field(default_factory=dict)


class UpdateAssessmentRequest(BaseModel):
    """Request to update an assessment."""

    title: Optional[str] = None
    status: Optional[AssessmentStatus] = None
    insights: Optional[list[dict[str, Any]]] = None
    related_entity: Optional[dict[str, Any]] = None


class ChatMessageRequest(BaseModel):
    """Request for assessment chat follow-up."""

    message: str


class AssessmentsService:
    """Service for managing assessments in Neo4j."""

    def __init__(self, driver):
        self.driver = driver

    def _generate_assessment_id(self) -> str:
        """Generate a unique assessment ID."""
        return f"assess_{uuid.uuid4().hex[:16]}"

    def _generate_insight_id(self) -> str:
        """Generate a unique insight ID."""
        return f"insight_{uuid.uuid4().hex[:8]}"

    async def list_assessments(
        self,
        limit: int = 50,
        status: Optional[AssessmentStatus] = None,
        assessment_type: Optional[AssessmentType] = None
    ) -> list[AssessmentSummary]:
        """List assessments with optional filters.

        Args:
            limit: Maximum number of assessments to return
            status: Filter by status
            assessment_type: Filter by assessment type

        Returns:
            List of assessment summaries
        """
        assessments = []

        try:
            async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                # Build query with optional filters
                where_clauses = []
                params = {"limit": limit}

                if status:
                    where_clauses.append("a.status = $status")
                    params["status"] = status.value

                if assessment_type:
                    where_clauses.append("a.assessment_type = $assessment_type")
                    params["assessment_type"] = assessment_type.value

                where_clause = ""
                if where_clauses:
                    where_clause = "WHERE " + " AND ".join(where_clauses)

                query = f"""
                    MATCH (a:Assessment)
                    {where_clause}
                    RETURN a.assessment_id AS assessment_id,
                           a.title AS title,
                           a.assessment_type AS assessment_type,
                           a.status AS status,
                           a.created_at AS created_at,
                           a.updated_at AS updated_at,
                           a.prompt AS prompt
                    ORDER BY a.updated_at DESC
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

                    assessments.append(AssessmentSummary(
                        assessment_id=record["assessment_id"],
                        title=record.get("title") or "Untitled Assessment",
                        assessment_type=AssessmentType(record.get("assessment_type", "custom")),
                        status=AssessmentStatus(record.get("status", "pending")),
                        created_at=str(created_at),
                        updated_at=str(updated_at),
                        prompt=record.get("prompt"),
                    ))

        except Exception as e:
            logger.error(f"Error listing assessments: {e}", exc_info=True)

        return assessments

    async def get_assessment(self, assessment_id: str) -> Optional[AssessmentDetail]:
        """Get detailed information about an assessment.

        Args:
            assessment_id: The assessment ID to retrieve

        Returns:
            Assessment details or None if not found
        """
        try:
            async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                result = await session.run(
                    """
                    MATCH (a:Assessment {assessment_id: $assessment_id})
                    RETURN a.assessment_id AS assessment_id,
                           a.title AS title,
                           a.assessment_type AS assessment_type,
                           a.status AS status,
                           a.created_at AS created_at,
                           a.updated_at AS updated_at,
                           a.prompt AS prompt,
                           a.include_web_research AS include_web_research,
                           a.insights_json AS insights_json,
                           a.related_entity_json AS related_entity_json,
                           a.entity_uuids AS entity_uuids,
                           a.metadata_json AS metadata_json,
                           a.messages_json AS messages_json
                    """,
                    assessment_id=assessment_id
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

                # Parse JSON fields
                insights_json = record.get("insights_json") or "[]"
                try:
                    insights_data = json.loads(insights_json)
                    insights = [AssessmentInsight(**i) for i in insights_data]
                except (json.JSONDecodeError, TypeError):
                    insights = []

                related_entity_json = record.get("related_entity_json") or "{}"
                try:
                    related_entity_data = json.loads(related_entity_json)
                    related_entity = RelatedEntity(**related_entity_data) if related_entity_data else None
                except (json.JSONDecodeError, TypeError):
                    related_entity = None

                metadata_json = record.get("metadata_json") or "{}"
                try:
                    metadata = json.loads(metadata_json)
                except json.JSONDecodeError:
                    metadata = {}

                messages_json = record.get("messages_json") or "[]"
                try:
                    messages = json.loads(messages_json)
                except json.JSONDecodeError:
                    messages = []

                return AssessmentDetail(
                    assessment_id=record["assessment_id"],
                    title=record.get("title") or "Untitled Assessment",
                    assessment_type=AssessmentType(record.get("assessment_type", "custom")),
                    status=AssessmentStatus(record.get("status", "pending")),
                    created_at=str(created_at or datetime.now().isoformat()),
                    updated_at=str(updated_at or created_at or datetime.now().isoformat()),
                    prompt=record.get("prompt"),
                    include_web_research=record.get("include_web_research") or False,
                    insights=insights,
                    related_entity=related_entity,
                    entity_uuids=record.get("entity_uuids") or [],
                    metadata=metadata,
                    messages=messages,
                )

        except Exception as e:
            logger.error(f"Error getting assessment {assessment_id}: {e}", exc_info=True)
            return None

    async def create_assessment(self, request: CreateAssessmentRequest) -> Optional[AssessmentDetail]:
        """Create a new assessment.

        Args:
            request: Assessment creation request

        Returns:
            Created assessment details or None on error
        """
        assessment_id = self._generate_assessment_id()

        try:
            async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                await session.run(
                    """
                    CREATE (a:Assessment {
                        assessment_id: $assessment_id,
                        title: $title,
                        prompt: $prompt,
                        assessment_type: $assessment_type,
                        status: $status,
                        include_web_research: $include_web_research,
                        created_at: datetime(),
                        updated_at: datetime(),
                        insights_json: '[]',
                        related_entity_json: '{}',
                        entity_uuids: [],
                        metadata_json: $metadata_json,
                        messages_json: '[]'
                    })
                    """,
                    assessment_id=assessment_id,
                    title=request.title,
                    prompt=request.prompt,
                    assessment_type=request.assessment_type.value,
                    status=AssessmentStatus.PENDING.value,
                    include_web_research=request.include_web_research,
                    metadata_json=json.dumps(request.options),
                )

                logger.info(f"Created assessment {assessment_id}: {request.title}")

                # Return the created assessment
                return await self.get_assessment(assessment_id)

        except Exception as e:
            logger.error(f"Error creating assessment: {e}", exc_info=True)
            return None

    async def update_assessment(
        self,
        assessment_id: str,
        request: UpdateAssessmentRequest
    ) -> Optional[AssessmentDetail]:
        """Update an assessment.

        Args:
            assessment_id: The assessment ID to update
            request: Update request

        Returns:
            Updated assessment details or None if not found
        """
        try:
            async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                # Build dynamic SET clause
                set_parts = ["a.updated_at = datetime()"]
                params = {"assessment_id": assessment_id}

                if request.title is not None:
                    set_parts.append("a.title = $title")
                    params["title"] = request.title

                if request.status is not None:
                    set_parts.append("a.status = $status")
                    params["status"] = request.status.value

                if request.insights is not None:
                    set_parts.append("a.insights_json = $insights_json")
                    params["insights_json"] = json.dumps(request.insights)

                if request.related_entity is not None:
                    set_parts.append("a.related_entity_json = $related_entity_json")
                    params["related_entity_json"] = json.dumps(request.related_entity)

                set_clause = ", ".join(set_parts)

                result = await session.run(
                    f"""
                    MATCH (a:Assessment {{assessment_id: $assessment_id}})
                    SET {set_clause}
                    RETURN count(a) AS updated
                    """,
                    **params
                )

                record = await result.single()

                if not record or record["updated"] == 0:
                    return None

                return await self.get_assessment(assessment_id)

        except Exception as e:
            logger.error(f"Error updating assessment {assessment_id}: {e}", exc_info=True)
            return None

    async def delete_assessment(self, assessment_id: str) -> bool:
        """Delete an assessment.

        Args:
            assessment_id: The assessment ID to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                result = await session.run(
                    """
                    MATCH (a:Assessment {assessment_id: $assessment_id})
                    DELETE a
                    RETURN count(a) AS deleted
                    """,
                    assessment_id=assessment_id
                )

                record = await result.single()
                return record and record["deleted"] > 0

        except Exception as e:
            logger.error(f"Error deleting assessment {assessment_id}: {e}", exc_info=True)
            return False

    async def run_assessment(self, assessment_id: str) -> bool:
        """Start running an assessment (placeholder for agent integration).

        This will eventually trigger the assessment agent flow.
        For now, it just sets the status to 'working'.

        Args:
            assessment_id: The assessment ID to run

        Returns:
            True if started successfully
        """
        try:
            # Update status to working
            update_result = await self.update_assessment(
                assessment_id,
                UpdateAssessmentRequest(status=AssessmentStatus.WORKING)
            )

            if not update_result:
                return False

            # TODO: Trigger actual assessment agent flow
            # This would integrate with an assessment agent
            logger.info(f"Assessment started for {assessment_id}")

            return True

        except Exception as e:
            logger.error(f"Error starting assessment {assessment_id}: {e}", exc_info=True)
            return False

    async def add_chat_message(
        self,
        assessment_id: str,
        role: str,
        content: str
    ) -> Optional[AssessmentDetail]:
        """Add a chat message to an assessment.

        Args:
            assessment_id: The assessment ID
            role: Message role (user or assistant)
            content: Message content

        Returns:
            Updated assessment details or None if not found
        """
        try:
            # Get current assessment
            assessment = await self.get_assessment(assessment_id)
            if not assessment:
                return None

            # Add new message
            new_message = {
                "id": f"msg_{uuid.uuid4().hex[:8]}",
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
            }
            messages = assessment.messages + [new_message]

            async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                await session.run(
                    """
                    MATCH (a:Assessment {assessment_id: $assessment_id})
                    SET a.messages_json = $messages_json,
                        a.updated_at = datetime()
                    """,
                    assessment_id=assessment_id,
                    messages_json=json.dumps(messages),
                )

            return await self.get_assessment(assessment_id)

        except Exception as e:
            logger.error(f"Error adding chat message to assessment {assessment_id}: {e}", exc_info=True)
            return None

    async def process_chat_followup(
        self,
        assessment_id: str,
        request: ChatMessageRequest
    ) -> Optional[dict]:
        """Process a chat follow-up message for an assessment.

        Args:
            assessment_id: The assessment ID
            request: Chat message request

        Returns:
            Response with assistant message or None on error
        """
        try:
            # Add user message
            await self.add_chat_message(assessment_id, "user", request.message)

            # TODO: Integrate with actual Claude agent for responses
            # For now, return a placeholder response
            assistant_response = (
                "Thank you for your question. I'm analyzing the assessment context "
                "and will provide a detailed response based on the available insights. "
                "(Note: Full agent integration coming soon)"
            )

            # Add assistant response
            updated_assessment = await self.add_chat_message(
                assessment_id, "assistant", assistant_response
            )

            if not updated_assessment:
                return None

            return {
                "assessment_id": assessment_id,
                "response": assistant_response,
                "messages": updated_assessment.messages,
            }

        except Exception as e:
            logger.error(f"Error processing chat followup for {assessment_id}: {e}", exc_info=True)
            return None
