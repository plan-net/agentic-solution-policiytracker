"""Claude Agent for PolicyTracker - connects to Knowledge Graph via MCP.

This agent integrates with the ChatContextTracker for session persistence
and graph visualization support.
"""

import json
import logging
import os
import re
import uuid
from datetime import UTC, datetime
from typing import AsyncGenerator, Optional

from anthropic import AsyncAnthropic
from neo4j import AsyncGraphDatabase

from src.chat.observability.langwatch_config import langwatch_config
from src.config import settings
from src.graph_viz.context_tracker import ChatContextTracker

from .mcp_client import MCPClient

logger = logging.getLogger(__name__)

# Default MCP server URL - can be overridden via MCP_SERVER_URL env var
# DEFAULT_MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "https://gp-retr-mcp-polmo.kodosumi.io/sse")
DEFAULT_MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8003/sse")

# System prompt for the policy tracker agent
SYSTEM_PROMPT = """You are a Political Monitoring Assistant with access to a knowledge graph containing information about EU regulations, policies, politicians, organizations, and legislative activities.

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

# Tool definitions matching the MCP server
TOOLS = [
    {
        "name": "search_knowledge_graph",
        "description": "Search the political monitoring knowledge graph for information about regulations, policies, politicians, organizations, and legislative activities. Supports queries about Digital Services Act, GDPR, AI Act, Bundestag activities, and more.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language query to search the knowledge graph"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "analyze_query",
        "description": "Analyze a query to understand its intent, extract entities, and determine the best retrieval strategy without executing the search.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Query to analyze"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_entity_info",
        "description": "Get detailed information about a specific entity in the knowledge graph (e.g., a regulation, person, organization, or legislative item).",
        "input_schema": {
            "type": "object",
            "properties": {
                "entity_name": {
                    "type": "string",
                    "description": "Name of the entity to look up"
                }
            },
            "required": ["entity_name"]
        }
    },
    {
        "name": "find_relationships",
        "description": "Find relationships and connections for an entity in the knowledge graph.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entity_name": {
                    "type": "string",
                    "description": "Name of the entity to find relationships for"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of relationships to return",
                    "default": 10
                }
            },
            "required": ["entity_name"]
        }
    },
    {
        "name": "graph_statistics",
        "description": "Get statistics about the knowledge graph (node counts, entity types, etc.).",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "search_documents",
        "description": "Search source documents (episodic nodes) in the knowledge graph using semantic similarity. Use this to find specific passages, quotes, or content from the original source documents that were used to build the knowledge graph.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to find relevant source documents"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of documents to return",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    }
]


class PolicyTrackerAgent:
    """Claude-based agent for querying the political monitoring knowledge graph.

    Integrates with ChatContextTracker for session persistence and
    graph visualization support.
    """

    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        mcp_server_url: Optional[str] = None,
        claude_model: Optional[str] = None,
    ):
        """Initialize the PolicyTracker agent.

        Args:
            anthropic_api_key: Anthropic API key (defaults to settings.ANTHROPIC_API_KEY)
            mcp_server_url: MCP server URL (defaults to DEFAULT_MCP_SERVER_URL)
            claude_model: Claude model to use (defaults to claude-sonnet-4-20250514)
        """
        api_key = anthropic_api_key or settings.ANTHROPIC_API_KEY
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")

        self.client = AsyncAnthropic(api_key=api_key)
        self.mcp_client = MCPClient(mcp_server_url or DEFAULT_MCP_SERVER_URL)
        self.model = claude_model or "claude-sonnet-4-20250514"

        # Neo4j driver and context tracker (initialized lazily)
        self._neo4j_driver = None
        self._context_tracker = None

        # Initialize LangWatch in manual mode - we use @langwatch_config.trace() decorator
        # to create a single trace per session (not per API call)
        langwatch_config.initialize(instrumentation_mode="manual")

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

    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return f"claude_{uuid.uuid4().hex[:16]}"

    async def _execute_tool(
        self,
        tool_name: str,
        tool_input: dict,
        tool_use_id: str = "",
        turn_number: int = 0,
        session_id: str = "",
    ) -> str:
        """Execute a tool call via the MCP server with full observability.

        Captures complete tool input and output for troubleshooting.
        Uses langwatch_config.capture_tool_call_with_response() to add events to current span.
        """
        import time

        start_time = time.time()
        logger.info(f"Executing tool: {tool_name} with input: {tool_input}")

        try:
            result = await self.mcp_client.call_tool(tool_name, tool_input)
            execution_time = time.time() - start_time

            # Capture tool call in session collector (synchronous)
            langwatch_config.capture_tool_call_with_response(
                tool_name=tool_name,
                tool_use_id=tool_use_id,
                tool_input=tool_input,
                tool_output=result,
                execution_time=execution_time,
                success=True,
                turn_number=turn_number,
                session_id=session_id,
            )

            logger.info(f"Tool result: {result[:200]}...")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            # Capture failed tool call in session collector (synchronous)
            langwatch_config.capture_tool_call_with_response(
                tool_name=tool_name,
                tool_use_id=tool_use_id,
                tool_input=tool_input,
                tool_output=None,
                execution_time=execution_time,
                success=False,
                error=str(e),
                turn_number=turn_number,
                session_id=session_id,
            )
            raise

    def _extract_uuids_from_result(self, result_text: str) -> set[str]:
        """Extract entity UUIDs from MCP tool result text.

        The MCP server returns formatted markdown text. We look for:
        - UUID patterns in the text (standard format)
        - UUID fields in text (e.g., "[UUID: abc123...]")
        """
        uuids = set()

        # Pattern for standard UUID format (8-4-4-4-12 hex digits)
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        matches = re.findall(uuid_pattern, result_text, re.IGNORECASE)
        uuids.update(matches)

        # Pattern for UUID fields in text, handles formats like:
        # "[UUID: abc123-...]", "UUID: abc123-...", "uuid: abc123-..."
        uuid_field_pattern = r'\[?(?:uuid|UUID|id|ID)[\s:]+([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})'
        field_matches = re.findall(uuid_field_pattern, result_text, re.IGNORECASE)
        uuids.update(field_matches)

        logger.debug(f"Extracted {len(uuids)} UUIDs from tool result")
        return uuids

    def _extract_entity_names_from_result(self, result_text: str) -> set[str]:
        """Extract entity names from MCP search results.

        The MCP server returns formatted markdown with entity names like:
        - **EntityName** (Entity, Type) - Description...
        """
        entity_names = set()

        # Pattern to match "- **EntityName** (Entity, Type)" format from search results
        # Matches text between ** and ** that follows a bullet point
        entity_pattern = r'- \*\*([^*]+)\*\* \([^)]+\)'
        matches = re.findall(entity_pattern, result_text)
        entity_names.update(matches)

        # Also match simpler patterns like "**EntityName**" without type info
        simple_pattern = r'\*\*([A-Za-z][A-Za-z0-9_ -]{2,})\*\*'
        simple_matches = re.findall(simple_pattern, result_text)
        # Filter out common markdown headers and generic terms
        skip_terms = {'Query Analysis', 'Intent', 'Entities', 'Strategy', 'Confidence', 'Type', 'UUID', 'Summary'}
        for name in simple_matches:
            if name not in skip_terms and len(name) > 2:
                entity_names.add(name)

        logger.debug(f"Extracted {len(entity_names)} entity names from tool result")
        return entity_names

    async def _lookup_entity_uuids_by_name(self, entity_names: set[str]) -> set[str]:
        """Look up entity UUIDs from Neo4j by entity name.

        Args:
            entity_names: Set of entity names to look up

        Returns:
            Set of UUIDs found for the given names
        """
        if not entity_names:
            return set()

        uuids = set()
        try:
            driver = await self._get_neo4j_driver()
            async with driver.session(database=settings.NEO4J_DATABASE) as session:
                # Query for entities by name (case-insensitive match)
                query = """
                    MATCH (e)
                    WHERE e.name IN $names OR toLower(e.name) IN $lower_names
                    RETURN e.uuid as uuid
                """
                names_list = list(entity_names)
                lower_names_list = [n.lower() for n in names_list]

                result = await session.run(
                    query,
                    {"names": names_list, "lower_names": lower_names_list}
                )
                records = await result.data()

                for record in records:
                    if record.get("uuid"):
                        uuids.add(record["uuid"])

                logger.info(f"Looked up {len(uuids)} UUIDs for {len(entity_names)} entity names")

        except Exception as e:
            logger.error(f"Error looking up entity UUIDs: {e}", exc_info=True)

        return uuids

    async def _parse_tool_result_for_tracking(self, tool_name: str, result_text: str) -> dict:
        """Parse tool result into a structured format for context tracking.

        Since MCP returns markdown text, we extract what we can.
        For search results that don't include UUIDs, we look up entity names in Neo4j.
        """
        parsed = {
            "tool_name": tool_name,
            "raw_text": result_text[:2000],  # Truncate for storage
        }

        # First try to extract UUIDs directly
        uuids = self._extract_uuids_from_result(result_text)

        # If no UUIDs found, extract entity names and look them up
        if not uuids:
            entity_names = self._extract_entity_names_from_result(result_text)
            if entity_names:
                logger.info(f"No UUIDs in result, looking up {len(entity_names)} entity names: {list(entity_names)[:5]}...")
                uuids = await self._lookup_entity_uuids_by_name(entity_names)

        if uuids:
            parsed["entity_uuids"] = list(uuids)

        return parsed

    @langwatch_config.trace(
        name="policy_tracker_query",
        metadata={"agent": "PolicyTrackerAgent"},
    )
    async def query(
        self,
        user_message: str,
        session_id: Optional[str] = None,
    ) -> tuple[str, str]:
        """Process a user query and return the response with session ID.

        This method handles the full agentic loop:
        1. Send user message to Claude
        2. If Claude wants to use tools, execute them
        3. Track tool results for graph visualization
        4. Send tool results back to Claude
        5. Repeat until Claude provides a final response
        6. Persist session context to Neo4j

        Args:
            user_message: The user's query
            session_id: Optional session ID (generated if not provided)

        Returns:
            Tuple of (response_text, session_id)
        """
        # Generate or use provided session ID
        if not session_id:
            session_id = self._generate_session_id()

        # Set thread_id for LangWatch trace grouping
        langwatch_config.set_thread_id(session_id)
        # Initialize session collector and store user query
        langwatch_config.set_session_query(session_id, user_message)

        # Get context tracker
        context_tracker = await self._get_context_tracker()

        # Initialize context for this session
        if session_id not in context_tracker.context_cache:
            context_tracker.context_cache[session_id] = {
                "created_at": datetime.now(UTC),
                "entity_uuids": set(),
                "relationship_data": [],
                "tools_used": [],
                "query_text": user_message,
            }
        else:
            context_tracker.context_cache[session_id]["query_text"] = user_message

        messages = [{"role": "user", "content": user_message}]

        # Store user message
        await context_tracker.store_message(session_id, "user", user_message)

        turn_number = 0
        while True:
            turn_number += 1

            # Call Claude with the current messages
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

            # Collect tool call info for metadata
            tool_calls_in_turn = []
            if response.stop_reason == "tool_use":
                for block in response.content:
                    if block.type == "tool_use":
                        tool_calls_in_turn.append({"name": block.name, "id": block.id})

            # Capture turn in session collector (synchronous)
            langwatch_config.capture_agentic_turn(
                turn_number=turn_number,
                session_id=session_id,
                stop_reason=response.stop_reason,
                tool_calls=tool_calls_in_turn,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                model=self.model,
            )

            # Check if we need to handle tool use
            if response.stop_reason == "tool_use":
                # Process all tool uses in the response
                assistant_content = response.content
                tool_results = []

                for block in assistant_content:
                    if block.type == "tool_use":
                        # Execute the tool with full observability context
                        result = await self._execute_tool(
                            tool_name=block.name,
                            tool_input=block.input,
                            tool_use_id=block.id,
                            turn_number=turn_number,
                            session_id=session_id,
                        )

                        # Parse result for context tracking (async to lookup UUIDs by name)
                        parsed_result = await self._parse_tool_result_for_tracking(block.name, result)

                        # Track tool execution for graph visualization
                        await context_tracker.track_tool_execution(
                            session_id,
                            block.name,
                            parsed_result
                        )

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result
                        })

                # Add assistant message with tool uses
                messages.append({"role": "assistant", "content": assistant_content})
                # Add tool results
                messages.append({"role": "user", "content": tool_results})

            else:
                # Claude is done - extract the text response
                text_parts = []
                for block in response.content:
                    if hasattr(block, "text"):
                        text_parts.append(block.text)

                response_text = "\n".join(text_parts)

                # Store assistant response
                await context_tracker.store_message(session_id, "assistant", response_text)

                # Finalize session and update LangWatch trace with structured data
                langwatch_config.set_session_response(session_id, response_text)
                session_data = langwatch_config.finalize_session(session_id)
                logger.info(f"Session data collected: {len(session_data.get('turns', []))} turns, {len(session_data.get('tool_calls', []))} tool calls")
                if session_data:
                    self._update_trace_with_session_data(session_data)

                # Final persistence of context
                logger.info(f"Session {session_id} completed with {len(context_tracker.context_cache.get(session_id, {}).get('entity_uuids', []))} entities tracked")

                return response_text, session_id

    def _update_trace_with_session_data(self, session_data: dict) -> None:
        """Update the current LangWatch trace with collected session data.

        Uses REST API directly to send traces (more reliable than OTEL SDK).
        """
        # Use REST API directly - this is the reliable method
        success = langwatch_config.send_trace_via_rest_api(session_data)
        if success:
            logger.info(f"Trace sent via REST API for session: {session_data.get('session_id')}")
        else:
            logger.warning(f"Failed to send trace via REST API for session: {session_data.get('session_id')}")

    @langwatch_config.trace(
        name="policy_tracker_stream_query",
        metadata={"agent": "PolicyTrackerAgent"},
    )
    async def stream_query(
        self,
        user_message: str,
        session_id: Optional[str] = None,
    ) -> AsyncGenerator[tuple[str, str], None]:
        """Process a user query with streaming response.

        Yields text chunks as they are generated, with the session ID
        included in the final yield.

        Args:
            user_message: The user's query
            session_id: Optional session ID (generated if not provided)

        Yields:
            Tuples of (text_chunk, session_id) - session_id is empty until final chunk
        """
        # Generate or use provided session ID
        if not session_id:
            session_id = self._generate_session_id()

        # Set thread_id for LangWatch trace grouping
        langwatch_config.set_thread_id(session_id)
        # Initialize session collector and store user query
        langwatch_config.set_session_query(session_id, user_message)

        # Get context tracker
        context_tracker = await self._get_context_tracker()

        # Initialize context for this session
        if session_id not in context_tracker.context_cache:
            context_tracker.context_cache[session_id] = {
                "created_at": datetime.now(UTC),
                "entity_uuids": set(),
                "relationship_data": [],
                "tools_used": [],
                "query_text": user_message,
            }
        else:
            context_tracker.context_cache[session_id]["query_text"] = user_message

        messages = [{"role": "user", "content": user_message}]

        # Store user message
        await context_tracker.store_message(session_id, "user", user_message)

        # Accumulate full response for storage
        full_response = ""
        turn_number = 0

        while True:
            turn_number += 1

            # Stream the response from Claude
            current_tool_use = None
            tool_uses = []

            async with self.client.messages.stream(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            ) as stream:
                async for event in stream:
                    if event.type == "content_block_start":
                        if event.content_block.type == "text":
                            pass  # Text block starting
                        elif event.content_block.type == "tool_use":
                            current_tool_use = {
                                "id": event.content_block.id,
                                "name": event.content_block.name,
                                "input": ""
                            }

                    elif event.type == "content_block_delta":
                        if hasattr(event.delta, "text"):
                            full_response += event.delta.text
                            yield event.delta.text, ""
                        elif hasattr(event.delta, "partial_json"):
                            if current_tool_use:
                                current_tool_use["input"] += event.delta.partial_json

                    elif event.type == "content_block_stop":
                        if current_tool_use:
                            # Parse the accumulated JSON input
                            try:
                                current_tool_use["input"] = json.loads(
                                    current_tool_use["input"]
                                )
                            except json.JSONDecodeError:
                                current_tool_use["input"] = {}
                            tool_uses.append(current_tool_use)
                            current_tool_use = None

                # Get the final message
                final_message = await stream.get_final_message()

            # Capture turn in session collector (synchronous)
            tool_calls_in_turn = [{"name": t["name"], "id": t["id"]} for t in tool_uses]
            langwatch_config.capture_agentic_turn(
                turn_number=turn_number,
                session_id=session_id,
                stop_reason=final_message.stop_reason,
                tool_calls=tool_calls_in_turn,
                input_tokens=final_message.usage.input_tokens,
                output_tokens=final_message.usage.output_tokens,
                model=self.model,
            )

            # Check if we need to handle tool use
            if final_message.stop_reason == "tool_use" and tool_uses:
                # Execute tools and continue the loop
                tool_results = []
                for tool in tool_uses:
                    yield f"\n\n*Using {tool['name']}...*\n", ""
                    result = await self._execute_tool(
                        tool_name=tool["name"],
                        tool_input=tool["input"],
                        tool_use_id=tool["id"],
                        turn_number=turn_number,
                        session_id=session_id,
                    )

                    # Parse result for context tracking (async to lookup UUIDs by name)
                    parsed_result = await self._parse_tool_result_for_tracking(tool["name"], result)

                    # Track tool execution
                    await context_tracker.track_tool_execution(
                        session_id,
                        tool["name"],
                        parsed_result
                    )

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool["id"],
                        "content": result
                    })

                # Add to messages and continue
                messages.append({"role": "assistant", "content": final_message.content})
                messages.append({"role": "user", "content": tool_results})
                tool_uses = []

            else:
                # Done - store the assistant response and yield final chunk
                if full_response:
                    await context_tracker.store_message(session_id, "assistant", full_response)

                # Finalize session and update LangWatch trace with structured data
                langwatch_config.set_session_response(session_id, full_response)
                session_data = langwatch_config.finalize_session(session_id)
                if session_data:
                    self._update_trace_with_session_data(session_data)

                logger.info(f"Streaming session {session_id} completed")
                yield "", session_id
                break

    async def close(self):
        """Clean up resources."""
        await self.mcp_client.close()
        if self._neo4j_driver:
            await self._neo4j_driver.close()
