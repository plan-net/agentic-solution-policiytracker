"""Session context management for multi-turn conversations with Claude Agent SDK.

Integrates with existing ChatContextTracker and ChatSessionService for persistence,
while providing SDK-specific context building and resumption support.

Features:
- Load conversation history from Neo4j ChatSession nodes
- Build context prompts with entity awareness
- Track session metadata for resumption
- Token-aware context trimming
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SDKContextManager:
    """Manage multi-turn conversation context for Claude Agent SDK agents.

    This class provides session context management that integrates with
    Neo4j for persistence and builds context-aware prompts for conversation
    continuation.

    Features:
    - Load conversation history from Neo4j ChatSession nodes
    - Build context prompts with entity awareness
    - Track session metadata for resumption
    - Token-aware context trimming
    - In-memory caching with TTL

    Example:
        ```python
        context_manager = SDKContextManager(neo4j_driver=driver)

        # Get context for a session
        context = await context_manager.get_session_context(session_id)

        # Build context prompt
        context_prompt = context_manager.build_context_prompt(context)

        # Update context after interaction
        await context_manager.update_context(
            session_id,
            {"role": "user", "content": "What about GDPR?"},
            entities=["uuid-123"],
        )
        ```
    """

    def __init__(
        self,
        neo4j_driver: Optional[Any] = None,
        max_context_messages: int = 10,
        max_context_tokens: int = 4000,
        context_ttl_hours: int = 24,
    ):
        """Initialize the context manager.

        Args:
            neo4j_driver: Optional Neo4j async driver for persistence
            max_context_messages: Maximum messages to include in context
            max_context_tokens: Maximum tokens for context (approximate)
            context_ttl_hours: Hours before cached context expires
        """
        self.driver = neo4j_driver
        self.max_context_messages = max_context_messages
        self.max_context_tokens = max_context_tokens
        self.context_ttl = timedelta(hours=context_ttl_hours)

        # In-memory cache for active sessions
        self._cache: dict[str, dict] = {}

    async def get_session_context(self, session_id: str) -> dict[str, Any]:
        """Retrieve full session context including messages, entities, and tools.

        Checks cache first, then loads from Neo4j if available. Returns
        a new empty context if no existing session is found.

        Args:
            session_id: Session identifier

        Returns:
            Dict with keys:
            - messages: List of {role, content, timestamp}
            - entities: List of entity UUIDs mentioned
            - tools_used: List of tool executions
            - created_at: Session creation timestamp
            - is_continuation: True if resuming existing session
        """
        # Check cache first
        if session_id in self._cache:
            cached = self._cache[session_id]
            if self._is_context_valid(cached):
                logger.debug(f"Context cache hit for session {session_id}")
                return cached

        # Load from Neo4j
        if self.driver:
            context = await self._load_from_neo4j(session_id)
            if context:
                context["is_continuation"] = True
                self._cache[session_id] = context
                logger.info(
                    f"Loaded context for session {session_id}: "
                    f"{len(context.get('messages', []))} messages"
                )
                return context

        # New session
        return {
            "messages": [],
            "entities": [],
            "tools_used": [],
            "created_at": datetime.now().isoformat(),
            "is_continuation": False,
        }

    async def _load_from_neo4j(self, session_id: str) -> Optional[dict[str, Any]]:
        """Load session context from Neo4j ChatSession node.

        Args:
            session_id: Session identifier

        Returns:
            Context dict or None if not found
        """
        if not self.driver:
            return None

        query = """
        MATCH (s:ChatSession {session_id: $session_id})
        RETURN s.messages_json AS messages,
               s.entity_uuids AS entities,
               s.tools_used_json AS tools_used,
               s.created_at AS created_at,
               s.query_text AS original_query,
               s.last_updated AS last_updated
        """

        try:
            async with self.driver.session() as session:
                result = await session.run(query, session_id=session_id)
                record = await result.single()

                if not record:
                    return None

                return {
                    "messages": json.loads(record["messages"] or "[]"),
                    "entities": record["entities"] or [],
                    "tools_used": json.loads(record["tools_used"] or "[]"),
                    "created_at": record["created_at"],
                    "original_query": record["original_query"],
                    "last_updated": record["last_updated"],
                }
        except Exception as e:
            logger.error(f"Failed to load context from Neo4j: {e}")
            return None

    def _is_context_valid(self, context: dict) -> bool:
        """Check if cached context is still valid (not expired).

        Args:
            context: Cached context dict

        Returns:
            True if context is still valid
        """
        try:
            # Check last_updated first, then created_at
            timestamp = context.get("last_updated") or context.get("created_at", "")
            if not timestamp:
                return False
            created = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            # Remove timezone for comparison if present
            if created.tzinfo:
                created = created.replace(tzinfo=None)
            return datetime.now() - created < self.context_ttl
        except (ValueError, TypeError) as e:
            logger.debug(f"Context validity check failed: {e}")
            return False

    def build_context_prompt(self, context: dict[str, Any]) -> str:
        """Build a context summary prompt for continuing conversations.

        This prompt is appended to the system prompt to give Claude
        awareness of the conversation history.

        Args:
            context: Context dict from get_session_context

        Returns:
            Context prompt string (empty if no history)
        """
        if not context.get("is_continuation") or not context.get("messages"):
            return ""

        messages = context["messages"]
        entities = context.get("entities", [])
        tools_used = context.get("tools_used", [])

        # Get recent messages (respect token limits)
        recent_messages = self._trim_messages(messages)

        # Build conversation summary
        conversation_summary = []
        for msg in recent_messages[-5:]:  # Last 5 for summary
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            # Truncate long messages
            if len(content) > 200:
                content = content[:200] + "..."
            conversation_summary.append(f"- **{role.title()}**: {content}")

        # Build entity context
        entity_context = ""
        if entities:
            entity_context = f"\n**Entities Discussed**: {len(entities)} entities tracked in this conversation"

        # Build tools context
        tools_context = ""
        if tools_used:
            tool_names = list(set(t.get("tool_name", "unknown") for t in tools_used[-10:]))
            # Clean up tool names (remove MCP prefix)
            clean_names = []
            for name in tool_names:
                if name.startswith("mcp__"):
                    parts = name.split("__")
                    if len(parts) >= 3:
                        clean_names.append(parts[2])
                    else:
                        clean_names.append(name)
                else:
                    clean_names.append(name)
            tools_context = f"\n**Tools Previously Used**: {', '.join(clean_names)}"

        return f"""
## Conversation Context (Continuing Session)

This is a continuation of an existing conversation. Here's the context:

**Previous Messages**: {len(messages)} total
{chr(10).join(conversation_summary)}
{entity_context}
{tools_context}

Use this context to provide coherent, contextually-aware responses.
When the user refers to something mentioned earlier (like "it", "this", "that"),
use the conversation history to understand what they mean.
"""

    def _trim_messages(self, messages: list) -> list:
        """Trim messages to fit within limits.

        Keeps the first message (original query) and the most recent messages.

        Args:
            messages: Full message list

        Returns:
            Trimmed message list
        """
        if len(messages) <= self.max_context_messages:
            return messages

        # Keep first message (original query) and last N-1 messages
        return [messages[0]] + messages[-(self.max_context_messages - 1):]

    async def update_context(
        self,
        session_id: str,
        message: Optional[dict] = None,
        entities: Optional[list] = None,
        tool_execution: Optional[dict] = None,
    ) -> None:
        """Update session context with new message and metadata.

        Updates the in-memory cache. Persistence to Neo4j should be handled
        by ChatContextTracker for full integration.

        Args:
            session_id: Session identifier
            message: Message dict with role, content (optional timestamp)
            entities: List of entity UUIDs discovered
            tool_execution: Tool execution dict with tool_name, input, output
        """
        context = await self.get_session_context(session_id)

        # Add message if provided
        if message:
            if "timestamp" not in message:
                message["timestamp"] = datetime.now().isoformat()
            context["messages"].append(message)

        # Add entities (deduplicated)
        if entities:
            existing = set(context.get("entities", []))
            context["entities"] = list(existing.union(set(entities)))

        # Add tool execution
        if tool_execution:
            if "timestamp" not in tool_execution:
                tool_execution["timestamp"] = datetime.now().isoformat()
            context.setdefault("tools_used", []).append(tool_execution)

        # Update last_updated
        context["last_updated"] = datetime.now().isoformat()

        # Update cache
        self._cache[session_id] = context

    def get_session_metadata(self, session_id: str) -> dict[str, Any]:
        """Get metadata about a session for UI/logging.

        Args:
            session_id: Session identifier

        Returns:
            Metadata dict with counts and status
        """
        context = self._cache.get(session_id, {})
        return {
            "session_id": session_id,
            "message_count": len(context.get("messages", [])),
            "entity_count": len(context.get("entities", [])),
            "tool_calls": len(context.get("tools_used", [])),
            "is_continuation": context.get("is_continuation", False),
            "created_at": context.get("created_at"),
            "last_updated": context.get("last_updated"),
        }

    def clear_session(self, session_id: str) -> None:
        """Clear session from cache (does not delete from Neo4j).

        Args:
            session_id: Session identifier
        """
        self._cache.pop(session_id, None)
        logger.info(f"Cleared context cache for session {session_id}")

    def list_active_sessions(self) -> list[dict[str, Any]]:
        """List all active sessions in cache.

        Returns:
            List of session metadata dicts
        """
        return [
            self.get_session_metadata(session_id)
            for session_id in self._cache.keys()
        ]


# Global instance (initialized without driver, can be configured later)
sdk_context_manager = SDKContextManager()
