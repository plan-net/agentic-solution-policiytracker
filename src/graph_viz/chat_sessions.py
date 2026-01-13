"""Chat session management for the Policy Tracker UI."""

import logging
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from src.config import settings

logger = logging.getLogger(__name__)


class ChatSessionSummary(BaseModel):
    """Summary of a chat session for listing."""

    session_id: str
    title: str = Field(default="Untitled conversation")
    created_at: str
    last_updated: str
    entity_count: int = 0
    tools_used_count: int = 0


class ChatSessionDetail(BaseModel):
    """Detailed chat session information."""

    session_id: str
    title: str = Field(default="Untitled conversation")
    created_at: str
    last_updated: str
    entity_uuids: list[str] = Field(default_factory=list)
    tools_used: list[dict[str, Any]] = Field(default_factory=list)
    query_text: Optional[str] = None


class ChatMessage(BaseModel):
    """A single chat message."""

    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str


class SubmitFeedbackRequest(BaseModel):
    """Request to submit feedback for a message."""

    message_index: int  # Index of the message in the messages array
    rating: str  # "positive" or "negative"
    comment: Optional[str] = None


class FeedbackEntry(BaseModel):
    """Feedback entry for a message."""

    message_index: int
    rating: str  # "positive" or "negative"
    comment: Optional[str] = None
    timestamp: str


class ChatSessionWithMessages(BaseModel):
    """Chat session with full message history."""

    session_id: str
    title: str = Field(default="Untitled conversation")
    created_at: str
    last_updated: str
    messages: list[ChatMessage] = Field(default_factory=list)
    feedback: list[FeedbackEntry] = Field(default_factory=list)
    entity_count: int = 0


class ChatSessionService:
    """Service for managing chat sessions in Neo4j."""

    def __init__(self, driver):
        self.driver = driver

    async def list_sessions(self, limit: int = 50) -> list[ChatSessionSummary]:
        """List recent chat sessions.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of chat session summaries
        """
        sessions = []

        try:
            async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                result = await session.run(
                    """
                    MATCH (s:ChatSession)
                    RETURN s.session_id AS session_id,
                           s.title AS title,
                           s.created_at AS created_at,
                           s.last_updated AS last_updated,
                           s.entity_uuids AS entity_uuids,
                           s.tools_used_json AS tools_used_json,
                           s.query_text AS query_text
                    ORDER BY s.last_updated DESC
                    LIMIT $limit
                    """,
                    limit=limit
                )

                records = await result.data()

                for record in records:
                    # Parse dates
                    created_at = record.get("created_at")
                    last_updated = record.get("last_updated")

                    if hasattr(created_at, "isoformat"):
                        created_at = created_at.isoformat()
                    elif created_at is None:
                        created_at = datetime.now().isoformat()

                    if hasattr(last_updated, "isoformat"):
                        last_updated = last_updated.isoformat()
                    elif last_updated is None:
                        last_updated = created_at

                    # Count entities and tools
                    entity_uuids = record.get("entity_uuids") or []
                    tools_used_json = record.get("tools_used_json") or "[]"

                    import json
                    try:
                        tools_used = json.loads(tools_used_json)
                    except json.JSONDecodeError:
                        tools_used = []

                    # Generate title from first tool query or default
                    title = record.get("title")
                    if not title and tools_used:
                        # Try to extract a meaningful title from tool usage
                        # title = f"Chat with {len(entity_uuids)} entities"
                        # new title from user's chat query
                        title = record.get("query_text") 
                    if not title:
                        title = "Untitled conversation"

                    sessions.append(ChatSessionSummary(
                        session_id=record["session_id"],
                        title=title,
                        created_at=str(created_at),
                        last_updated=str(last_updated),
                        entity_count=len(entity_uuids),
                        tools_used_count=len(tools_used),
                    ))

        except Exception as e:
            logger.error(f"Error listing chat sessions: {e}", exc_info=True)

        return sessions

    async def get_session(self, session_id: str) -> Optional[ChatSessionDetail]:
        """Get detailed information about a chat session.

        Args:
            session_id: The session ID to retrieve

        Returns:
            Chat session details or None if not found
        """
        try:
            async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                result = await session.run(
                    """
                    MATCH (s:ChatSession {session_id: $session_id})
                    RETURN s.session_id AS session_id,
                           s.title AS title,
                           s.created_at AS created_at,
                           s.last_updated AS last_updated,
                           s.entity_uuids AS entity_uuids,
                           s.tools_used_json AS tools_used_json,
                           s.query_text AS query_text
                    """,
                    session_id=session_id
                )

                record = await result.single()

                if not record:
                    return None

                # Parse dates
                created_at = record.get("created_at")
                last_updated = record.get("last_updated")

                if hasattr(created_at, "isoformat"):
                    created_at = created_at.isoformat()
                if hasattr(last_updated, "isoformat"):
                    last_updated = last_updated.isoformat()

                # Parse tools
                import json
                tools_used_json = record.get("tools_used_json") or "[]"
                try:
                    tools_used = json.loads(tools_used_json)
                except json.JSONDecodeError:
                    tools_used = []

                return ChatSessionDetail(
                    session_id=record["session_id"],
                    title=record.get("title") or "Untitled conversation",
                    created_at=str(created_at or datetime.now().isoformat()),
                    last_updated=str(last_updated or created_at or datetime.now().isoformat()),
                    entity_uuids=record.get("entity_uuids") or [],
                    tools_used=tools_used,
                    query_text=record.get("query_text"),
                )

        except Exception as e:
            logger.error(f"Error getting chat session {session_id}: {e}", exc_info=True)
            return None

    async def delete_session(self, session_id: str) -> bool:
        """Delete a chat session.

        Args:
            session_id: The session ID to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                result = await session.run(
                    """
                    MATCH (s:ChatSession {session_id: $session_id})
                    DELETE s
                    RETURN count(s) AS deleted
                    """,
                    session_id=session_id
                )

                record = await result.single()
                return record and record["deleted"] > 0

        except Exception as e:
            logger.error(f"Error deleting chat session {session_id}: {e}", exc_info=True)
            return False

    async def update_session_title(self, session_id: str, title: str) -> bool:
        """Update the title of a chat session.

        Args:
            session_id: The session ID to update
            title: New title for the session

        Returns:
            True if updated, False if not found
        """
        try:
            async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                result = await session.run(
                    """
                    MATCH (s:ChatSession {session_id: $session_id})
                    SET s.title = $title,
                        s.last_updated = datetime()
                    RETURN count(s) AS updated
                    """,
                    session_id=session_id,
                    title=title
                )

                record = await result.single()
                return record and record["updated"] > 0

        except Exception as e:
            logger.error(f"Error updating chat session title {session_id}: {e}", exc_info=True)
            return False

    async def store_message(
        self,
        session_id: str,
        role: str,
        content: str
    ) -> bool:
        """Store a chat message for a session.

        Messages are stored as a JSON array in the ChatSession node.

        Args:
            session_id: The session ID
            role: Message role ('user' or 'assistant')
            content: Message content

        Returns:
            True if stored successfully
        """
        import json

        try:
            async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                # First, get existing messages
                result = await session.run(
                    """
                    MATCH (s:ChatSession {session_id: $session_id})
                    RETURN s.messages_json AS messages_json
                    """,
                    session_id=session_id
                )

                record = await result.single()

                if record:
                    messages_json = record.get("messages_json") or "[]"
                    try:
                        messages = json.loads(messages_json)
                    except json.JSONDecodeError:
                        messages = []
                else:
                    messages = []

                # Add new message
                messages.append({
                    "role": role,
                    "content": content,
                    "timestamp": datetime.now().isoformat()
                })

                # Store back
                await session.run(
                    """
                    MERGE (s:ChatSession {session_id: $session_id})
                    SET s.messages_json = $messages_json,
                        s.last_updated = datetime()
                    """,
                    session_id=session_id,
                    messages_json=json.dumps(messages)
                )

                # Auto-generate title from first user message if not set
                if role == "user" and len(messages) == 1:
                    # Generate title from first message (truncated)
                    title = content[:50] + ("..." if len(content) > 50 else "")
                    await self.update_session_title(session_id, title)

                return True

        except Exception as e:
            logger.error(f"Error storing message for session {session_id}: {e}", exc_info=True)
            return False

    async def get_session_messages(self, session_id: str) -> list[ChatMessage]:
        """Get all messages for a chat session.

        Args:
            session_id: The session ID

        Returns:
            List of chat messages
        """
        import json

        try:
            async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                result = await session.run(
                    """
                    MATCH (s:ChatSession {session_id: $session_id})
                    RETURN s.messages_json AS messages_json
                    """,
                    session_id=session_id
                )

                record = await result.single()

                if not record:
                    return []

                messages_json = record.get("messages_json") or "[]"
                try:
                    messages_data = json.loads(messages_json)
                except json.JSONDecodeError:
                    return []

                return [
                    ChatMessage(
                        role=msg.get("role", "user"),
                        content=msg.get("content", ""),
                        timestamp=msg.get("timestamp", datetime.now().isoformat())
                    )
                    for msg in messages_data
                ]

        except Exception as e:
            logger.error(f"Error getting messages for session {session_id}: {e}", exc_info=True)
            return []

    async def submit_message_feedback(
        self,
        session_id: str,
        message_index: int,
        rating: str,
        comment: Optional[str] = None
    ) -> bool:
        """Submit feedback for a specific message in a chat session.

        Feedback is stored as a separate JSON property (feedback_json) on the ChatSession node,
        keeping it separate from the actual message content.

        Args:
            session_id: The session ID
            message_index: Index of the message in the messages array
            rating: Feedback rating ("positive" or "negative")
            comment: Optional feedback comment

        Returns:
            True if feedback was stored successfully, False otherwise
        """
        import json

        if rating not in ("positive", "negative"):
            logger.error(f"Invalid feedback rating: {rating}")
            return False

        try:
            async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                # Create feedback entry
                feedback_entry = {
                    "message_index": message_index,
                    "rating": rating,
                    "comment": comment,
                    "timestamp": datetime.now().isoformat()
                }

                # First, check if session exists and get existing feedback
                result = await session.run(
                    """
                    MATCH (s:ChatSession {session_id: $session_id})
                    RETURN s.feedback_json AS feedback_json
                    """,
                    session_id=session_id
                )

                record = await result.single()

                if record:
                    # Session exists - append to existing feedback
                    feedback_json = record.get("feedback_json") or "[]"
                    try:
                        feedback_list = json.loads(feedback_json)
                    except json.JSONDecodeError:
                        feedback_list = []

                    # Check if feedback already exists for this message index
                    existing_idx = next(
                        (i for i, f in enumerate(feedback_list) if f.get("message_index") == message_index),
                        None
                    )
                    if existing_idx is not None:
                        # Update existing feedback
                        feedback_list[existing_idx] = feedback_entry
                    else:
                        # Add new feedback
                        feedback_list.append(feedback_entry)

                    # Store back
                    await session.run(
                        """
                        MATCH (s:ChatSession {session_id: $session_id})
                        SET s.feedback_json = $feedback_json,
                            s.last_updated = datetime()
                        """,
                        session_id=session_id,
                        feedback_json=json.dumps(feedback_list)
                    )
                else:
                    # Session doesn't exist - create it with feedback
                    logger.warning(f"Session {session_id} not found in Neo4j, creating with feedback")

                    await session.run(
                        """
                        MERGE (s:ChatSession {session_id: $session_id})
                        ON CREATE SET
                            s.created_at = datetime(),
                            s.last_updated = datetime(),
                            s.messages_json = '[]',
                            s.feedback_json = $feedback_json
                        ON MATCH SET
                            s.feedback_json = $feedback_json,
                            s.last_updated = datetime()
                        """,
                        session_id=session_id,
                        feedback_json=json.dumps([feedback_entry])
                    )

                logger.info(f"Feedback stored for session {session_id}, message {message_index}: {rating}")
                return True

        except Exception as e:
            logger.error(f"Error storing feedback for session {session_id}: {e}", exc_info=True)
            return False

    async def get_session_feedback(self, session_id: str) -> list[dict]:
        """Get all feedback entries for a chat session.

        Args:
            session_id: The session ID

        Returns:
            List of feedback entries
        """
        import json

        try:
            async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                result = await session.run(
                    """
                    MATCH (s:ChatSession {session_id: $session_id})
                    RETURN s.feedback_json AS feedback_json
                    """,
                    session_id=session_id
                )

                record = await result.single()

                if not record:
                    return []

                feedback_json = record.get("feedback_json") or "[]"
                try:
                    return json.loads(feedback_json)
                except json.JSONDecodeError:
                    return []

        except Exception as e:
            logger.error(f"Error getting feedback for session {session_id}: {e}", exc_info=True)
            return []
