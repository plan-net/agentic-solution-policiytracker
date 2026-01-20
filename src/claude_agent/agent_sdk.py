"""Claude Agent for PolicyTracker using Claude Agent SDK.

This agent uses the Claude Agent SDK for automatic agentic loop management
and native MCP support, with advanced agentic patterns:
- LangWatch observability via SDK hooks
- Neo4j/ChatContextTracker for session persistence and graph visualization
- Reflection pattern with confidence scoring
- Multi-turn context management
- External prompt management via PromptManager
- Streaming responses
"""

import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Any, AsyncGenerator, Optional

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    HookMatcher,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ResultMessage,
)
from neo4j import AsyncGraphDatabase

from src.chat.observability.langwatch_config import langwatch_config
from src.config import settings
from src.graph_viz.context_tracker import ChatContextTracker
from src.prompts.prompt_manager import prompt_manager
from src.shared.sdk_hooks import create_langwatch_hooks, create_enhanced_hooks
from src.shared.context_manager import SDKContextManager

logger = logging.getLogger(__name__)

# Default MCP server URL - can be overridden via MCP_SERVER_URL env var
DEFAULT_MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8003/sse")

# Fallback system prompt (used when PromptManager is unavailable)
FALLBACK_SYSTEM_PROMPT = """You are a Political Monitoring Assistant with access to a knowledge graph containing information about EU regulations, policies, politicians, organizations, and legislative activities.

Your knowledge graph contains information about:
- Regulations: GDPR, DSA, DMA, AI Act, and other EU/German legislation
- Politicians: EU Commissioners, MEPs, Bundestag members
- Organizations: EU institutions, regulatory bodies, industry groups
- Legislative processes: Votes, committees, debates, amendments

Available Tools:
1. search_knowledge_graph - Use this for general queries about regulations, policies, or entities
2. search_documents - Use this to search source documents (episodic nodes) using semantic similarity
3. analyze_query - Use this to understand complex queries before searching
4. get_entity_info - Use this to get detailed information about a specific entity
5. find_relationships - Use this to explore connections between entities
6. graph_statistics - Use this to understand the scope of available data

Best Practices:
- For simple factual questions, use search_knowledge_graph directly
- For finding specific passages or quotes from source documents, use search_documents
- For complex questions, first use analyze_query to understand the query structure
- When asked about relationships, use find_relationships
- When asked for specific entity details, use get_entity_info
- Always cite your sources from the knowledge graph

Language Instructions:
IMPORTANT: Always respond in the same language as the user's query. If the user asks a question in German, respond in German. If the user asks in English, respond in English. Match the language of your response to the language of the user's input.

Respond in a helpful, professional manner. If the knowledge graph doesn't have information on a topic, say so clearly."""

# MCP tool names that are available on the server
MCP_TOOLS = [
    "search_knowledge_graph",
    "search_documents",
    "analyze_query",
    "get_entity_info",
    "find_relationships",
    "graph_statistics",
]


class PolicyTrackerSDKAgent:
    """Claude-based agent using Claude Agent SDK for PolicyTracker.

    Features:
    - Uses ClaudeSDKClient with automatic agentic loop
    - Native MCP support via mcp_servers config (SSE transport)
    - Reflection pattern with confidence scoring
    - Multi-turn context management
    - External prompt management via PromptManager
    - LangWatch observability via enhanced hooks

    Integrates with ChatContextTracker for session persistence and
    graph visualization support.
    """

    def __init__(
        self,
        mcp_server_url: Optional[str] = None,
        claude_model: Optional[str] = None,
        enable_reflection: bool = True,
        enable_multi_turn: bool = True,
        max_turns: int = 15,
    ):
        """Initialize the PolicyTracker SDK agent.

        Args:
            mcp_server_url: MCP server URL (defaults to DEFAULT_MCP_SERVER_URL)
            claude_model: Claude model to use (defaults to claude-sonnet-4-20250514)
            enable_reflection: Enable reflection pattern with confidence scoring
            enable_multi_turn: Enable multi-turn context management
            max_turns: Maximum turns for the agentic loop
        """
        self.mcp_server_url = mcp_server_url or DEFAULT_MCP_SERVER_URL
        self.model = claude_model or "claude-sonnet-4-20250514"
        self.enable_reflection = enable_reflection
        self.enable_multi_turn = enable_multi_turn
        self.max_turns = max_turns

        # Neo4j driver and context tracker (initialized lazily)
        self._neo4j_driver = None
        self._context_tracker = None
        self._sdk_context_manager: Optional[SDKContextManager] = None

        # Initialize LangWatch in manual mode
        langwatch_config.initialize(instrumentation_mode="manual")

        logger.info(
            f"PolicyTrackerSDKAgent initialized with model: {self.model}, "
            f"MCP server: {self.mcp_server_url}, "
            f"reflection: {enable_reflection}, multi_turn: {enable_multi_turn}"
        )

    async def _get_neo4j_driver(self):
        """Lazy initialization of Neo4j driver."""
        if self._neo4j_driver is None:
            self._neo4j_driver = AsyncGraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
            )
            logger.info("Neo4j driver initialized")
        return self._neo4j_driver

    async def _get_context_tracker(self) -> ChatContextTracker:
        """Lazy initialization of context tracker."""
        if self._context_tracker is None:
            driver = await self._get_neo4j_driver()
            self._context_tracker = ChatContextTracker(driver=driver, ttl_minutes=60)
            logger.info("Context tracker initialized")
        return self._context_tracker

    async def _get_sdk_context_manager(self) -> SDKContextManager:
        """Lazy initialization of SDK context manager for multi-turn support."""
        if self._sdk_context_manager is None:
            driver = await self._get_neo4j_driver()
            self._sdk_context_manager = SDKContextManager(neo4j_driver=driver)
            logger.info("SDK context manager initialized")
        return self._sdk_context_manager

    async def _get_system_prompt(self) -> str:
        """Load system prompt from PromptManager with fallback.

        Tries to load from external prompt files first, falls back to
        inline prompt if unavailable.
        """
        try:
            base_prompt = await prompt_manager.get_prompt("sdk_agents/policy_tracker_system")
            logger.debug("Loaded system prompt from PromptManager")
            return base_prompt
        except Exception as e:
            logger.warning(f"Failed to load prompt from PromptManager: {e}, using fallback")
            return FALLBACK_SYSTEM_PROMPT

    async def _get_reflection_prompt(self) -> str:
        """Load reflection/tool selection strategy prompt."""
        try:
            return await prompt_manager.get_prompt("sdk_agents/tool_selection_strategy")
        except Exception as e:
            logger.warning(f"Failed to load reflection prompt: {e}")
            return ""

    async def _get_response_synthesis_prompt(self) -> str:
        """Load response synthesis prompt with Public Affairs perspective."""
        try:
            return await prompt_manager.get_prompt("sdk_agents/response_synthesis")
        except Exception as e:
            logger.warning(f"Failed to load response synthesis prompt: {e}")
            return ""

    async def _build_system_prompt_with_context(self, session_id: str) -> str:
        """Build complete system prompt with reflection and conversation context.

        Combines:
        1. Base system prompt (from PromptManager or fallback)
        2. Response synthesis guidelines (Public Affairs perspective)
        3. Reflection/tool selection strategy (if enabled)
        4. Conversation context (if multi-turn enabled and continuing session)
        """
        # Get base prompt
        base_prompt = await self._get_system_prompt()

        # Add response synthesis guidelines (Public Affairs perspective)
        response_synthesis_prompt = await self._get_response_synthesis_prompt()
        if response_synthesis_prompt:
            base_prompt = f"{base_prompt}\n\n{response_synthesis_prompt}"

        # Add reflection instructions if enabled
        if self.enable_reflection:
            reflection_prompt = await self._get_reflection_prompt()
            if reflection_prompt:
                base_prompt = f"{base_prompt}\n\n{reflection_prompt}"

        # Add conversation context if multi-turn enabled
        if self.enable_multi_turn:
            context_manager = await self._get_sdk_context_manager()
            context = await context_manager.get_session_context(session_id)
            context_prompt = context_manager.build_context_prompt(context)
            if context_prompt:
                base_prompt = f"{base_prompt}\n\n{context_prompt}"

        return base_prompt

    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return f"claude_{uuid.uuid4().hex[:16]}"

    def _build_mcp_config(self) -> dict:
        """Build MCP server configuration for SSE transport."""
        return {
            "knowledge_graph": {
                "type": "sse",
                "url": self.mcp_server_url,
            }
        }

    def _get_allowed_tools(self) -> list[str]:
        """Get list of allowed MCP tools in SDK format.

        SDK tool naming convention: mcp__<server_name>__<tool_name>
        """
        return [f"mcp__knowledge_graph__{tool}" for tool in MCP_TOOLS]

    async def _init_session_context(
        self, context_tracker: ChatContextTracker, session_id: str, query_text: str
    ) -> None:
        """Initialize context for a new session."""
        if session_id not in context_tracker.context_cache:
            context_tracker.context_cache[session_id] = {
                "created_at": datetime.now(UTC),
                "entity_uuids": set(),
                "relationship_data": [],
                "tools_used": [],
                "query_text": query_text,
            }
        else:
            context_tracker.context_cache[session_id]["query_text"] = query_text

    def _finalize_langwatch(self, session_id: str, response_text: str) -> None:
        """Finalize LangWatch session and send trace."""
        langwatch_config.set_session_response(session_id, response_text)
        session_data = langwatch_config.finalize_session(session_id)
        if session_data:
            success = langwatch_config.send_trace_via_rest_api(session_data)
            if success:
                logger.info(f"Trace sent via REST API for session: {session_id}")
            else:
                logger.warning(f"Failed to send trace for session: {session_id}")

    @langwatch_config.trace(
        name="policy_tracker_sdk_query",
        metadata={"agent": "PolicyTrackerSDKAgent"},
    )
    async def query(
        self,
        user_message: str,
        session_id: Optional[str] = None,
    ) -> tuple[str, str, dict[str, Any]]:
        """Process a user query and return the response with session ID and metadata.

        The SDK handles the full agentic loop automatically:
        1. Send user message to Claude via SDK
        2. SDK automatically executes tools when Claude requests them
        3. Enhanced hooks capture tool execution with reflection
        4. SDK returns final response when Claude is done

        Features:
        - Reflection pattern: Validates tool results and suggests alternatives
        - Multi-turn context: Loads conversation history for continuations
        - External prompts: Loads system prompt from PromptManager

        Args:
            user_message: The user's query
            session_id: Optional session ID (generated if not provided)

        Returns:
            Tuple of (response_text, session_id, metadata)
            metadata includes: reflection summary, confidence scores, session info
        """
        # Generate or use provided session ID
        if not session_id:
            session_id = self._generate_session_id()

        # Set thread_id for LangWatch trace grouping
        langwatch_config.set_thread_id(session_id)
        langwatch_config.set_session_query(session_id, user_message)

        # Get context tracker and initialize session
        context_tracker = await self._get_context_tracker()
        await self._init_session_context(context_tracker, session_id, user_message)
        await context_tracker.store_message(session_id, "user", user_message)

        # Update SDK context manager if multi-turn enabled
        if self.enable_multi_turn:
            sdk_context_manager = await self._get_sdk_context_manager()
            await sdk_context_manager.update_context(
                session_id,
                {"role": "user", "content": user_message}
            )

        # Get Neo4j driver for entity name lookups in hooks
        neo4j_driver = await self._get_neo4j_driver()

        # Build context-aware system prompt
        system_prompt = await self._build_system_prompt_with_context(session_id)

        # Create hooks - use enhanced hooks if reflection is enabled
        if self.enable_reflection:
            pre_hook, post_hook, increment_turn, get_reflection = await create_enhanced_hooks(
                session_id=session_id,
                langwatch_config=langwatch_config,
                context_tracker=context_tracker,
                neo4j_driver=neo4j_driver,
                enable_reflection=True,
                enable_retry=True,
            )
        else:
            pre_hook, post_hook, increment_turn = await create_langwatch_hooks(
                session_id=session_id,
                langwatch_config=langwatch_config,
                context_tracker=context_tracker,
                neo4j_driver=neo4j_driver,
            )
            get_reflection = lambda: {"total_tools": 0, "avg_confidence": 1.0, "low_confidence_tools": [], "turns": 0}

        # Build SDK options with hooks
        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            mcp_servers=self._build_mcp_config(),
            allowed_tools=self._get_allowed_tools(),
            model=self.model,
            max_turns=self.max_turns,
            hooks={
                "PreToolUse": [HookMatcher(hooks=[pre_hook])],
                "PostToolUse": [HookMatcher(hooks=[post_hook])],
            },
        )

        # Execute with SDK - automatic agentic loop!
        response_text = ""
        turn_count = 0
        entities_found: list[str] = []

        try:
            async with ClaudeSDKClient(options=options) as client:
                await client.query(user_message)

                async for message in client.receive_response():
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                response_text += block.text
                            elif isinstance(block, ToolUseBlock):
                                increment_turn()
                                turn_count += 1

                    elif isinstance(message, ResultMessage):
                        # Capture final metrics
                        usage = getattr(message, "usage", None)
                        langwatch_config.capture_agentic_turn(
                            turn_number=turn_count,
                            session_id=session_id,
                            stop_reason=getattr(message, "subtype", "end_turn"),
                            tool_calls=[],
                            input_tokens=usage.get("input_tokens", 0) if usage else 0,
                            output_tokens=usage.get("output_tokens", 0) if usage else 0,
                            model=self.model,
                        )
                        break

        except Exception as e:
            logger.error(f"Error in SDK query: {e}", exc_info=True)
            response_text = f"Error processing query: {str(e)}"

        # Store assistant response
        await context_tracker.store_message(session_id, "assistant", response_text)

        # Update SDK context manager with response if multi-turn enabled
        if self.enable_multi_turn:
            sdk_context_manager = await self._get_sdk_context_manager()
            await sdk_context_manager.update_context(
                session_id,
                {"role": "assistant", "content": response_text},
                entities=entities_found,
            )

        self._finalize_langwatch(session_id, response_text)

        # Build metadata with reflection summary
        reflection_summary = get_reflection()
        metadata: dict[str, Any] = {
            "session_id": session_id,
            "turns": turn_count,
            "model": self.model,
            "reflection": reflection_summary,
            "avg_confidence": reflection_summary.get("avg_confidence", 1.0),
            "entities_tracked": len(context_tracker.context_cache.get(session_id, {}).get("entity_uuids", [])),
        }

        # Add multi-turn session info if enabled
        if self.enable_multi_turn:
            sdk_context_manager = await self._get_sdk_context_manager()
            session_meta = sdk_context_manager.get_session_metadata(session_id)
            metadata.update({
                "is_continuation": session_meta.get("is_continuation", False),
                "message_count": session_meta.get("message_count", 0),
            })

        logger.info(
            f"Session {session_id} completed: {turn_count} turns, "
            f"confidence: {reflection_summary.get('avg_confidence', 1.0):.2f}, "
            f"{metadata['entities_tracked']} entities"
        )

        return response_text, session_id, metadata

    @langwatch_config.trace(
        name="policy_tracker_sdk_stream_query",
        metadata={"agent": "PolicyTrackerSDKAgent"},
    )
    async def stream_query(
        self,
        user_message: str,
        session_id: Optional[str] = None,
    ) -> AsyncGenerator[tuple[str, str, dict[str, Any]], None]:
        """Process a user query with streaming response.

        Yields text chunks as they are generated, with session ID and metadata
        included in the final yield.

        Features:
        - Reflection pattern: Validates tool results and suggests alternatives
        - Multi-turn context: Loads conversation history for continuations
        - External prompts: Loads system prompt from PromptManager

        Args:
            user_message: The user's query
            session_id: Optional session ID (generated if not provided)

        Yields:
            Tuples of (text_chunk, session_id, metadata)
            - session_id and metadata are populated in final yield
        """
        # Generate or use provided session ID
        if not session_id:
            session_id = self._generate_session_id()

        # Set thread_id for LangWatch trace grouping
        langwatch_config.set_thread_id(session_id)
        langwatch_config.set_session_query(session_id, user_message)

        # Get context tracker and initialize session
        context_tracker = await self._get_context_tracker()
        await self._init_session_context(context_tracker, session_id, user_message)
        await context_tracker.store_message(session_id, "user", user_message)

        # Update SDK context manager if multi-turn enabled
        if self.enable_multi_turn:
            sdk_context_manager = await self._get_sdk_context_manager()
            await sdk_context_manager.update_context(
                session_id,
                {"role": "user", "content": user_message}
            )

        # Get Neo4j driver for entity name lookups
        neo4j_driver = await self._get_neo4j_driver()

        # Build context-aware system prompt
        system_prompt = await self._build_system_prompt_with_context(session_id)

        # Create hooks - use enhanced hooks if reflection is enabled
        if self.enable_reflection:
            pre_hook, post_hook, increment_turn, get_reflection = await create_enhanced_hooks(
                session_id=session_id,
                langwatch_config=langwatch_config,
                context_tracker=context_tracker,
                neo4j_driver=neo4j_driver,
                enable_reflection=True,
                enable_retry=True,
            )
        else:
            pre_hook, post_hook, increment_turn = await create_langwatch_hooks(
                session_id=session_id,
                langwatch_config=langwatch_config,
                context_tracker=context_tracker,
                neo4j_driver=neo4j_driver,
            )
            get_reflection = lambda: {"total_tools": 0, "avg_confidence": 1.0, "low_confidence_tools": [], "turns": 0}

        # Build SDK options with hooks
        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            mcp_servers=self._build_mcp_config(),
            allowed_tools=self._get_allowed_tools(),
            model=self.model,
            max_turns=self.max_turns,
            hooks={
                "PreToolUse": [HookMatcher(hooks=[pre_hook])],
                "PostToolUse": [HookMatcher(hooks=[post_hook])],
            },
        )

        # Accumulate full response for storage
        full_response = ""
        turn_count = 0
        entities_found: list[str] = []

        try:
            async with ClaudeSDKClient(options=options) as client:
                await client.query(user_message)

                async for message in client.receive_response():
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                full_response += block.text
                                yield block.text, "", {}
                            elif isinstance(block, ToolUseBlock):
                                increment_turn()
                                turn_count += 1
                                # Extract tool name from SDK format
                                tool_name = block.name
                                if tool_name.startswith("mcp__knowledge_graph__"):
                                    tool_name = tool_name.replace(
                                        "mcp__knowledge_graph__", ""
                                    )
                                yield f"\n\n*Using {tool_name}...*\n", "", {}

                    elif isinstance(message, ResultMessage):
                        break

        except Exception as e:
            logger.error(f"Error in SDK stream_query: {e}", exc_info=True)
            yield f"\n\nError: {str(e)}", "", {}

        # Store assistant response
        if full_response:
            await context_tracker.store_message(session_id, "assistant", full_response)

        # Update SDK context manager with response if multi-turn enabled
        if self.enable_multi_turn:
            sdk_context_manager = await self._get_sdk_context_manager()
            await sdk_context_manager.update_context(
                session_id,
                {"role": "assistant", "content": full_response},
                entities=entities_found,
            )

        self._finalize_langwatch(session_id, full_response)

        # Build metadata with reflection summary
        reflection_summary = get_reflection()
        metadata: dict[str, Any] = {
            "session_id": session_id,
            "turns": turn_count,
            "model": self.model,
            "reflection": reflection_summary,
            "avg_confidence": reflection_summary.get("avg_confidence", 1.0),
            "entities_tracked": len(context_tracker.context_cache.get(session_id, {}).get("entity_uuids", [])),
        }

        # Add multi-turn session info if enabled
        if self.enable_multi_turn:
            sdk_context_manager = await self._get_sdk_context_manager()
            session_meta = sdk_context_manager.get_session_metadata(session_id)
            metadata.update({
                "is_continuation": session_meta.get("is_continuation", False),
                "message_count": session_meta.get("message_count", 0),
            })

        logger.info(
            f"Streaming session {session_id} completed: {turn_count} turns, "
            f"confidence: {reflection_summary.get('avg_confidence', 1.0):.2f}"
        )

        # Final yield with session_id and metadata
        yield "", session_id, metadata

    async def close(self):
        """Clean up resources."""
        if self._neo4j_driver:
            await self._neo4j_driver.close()
            logger.info("Neo4j driver closed")
