"""Claude Agent SDK hooks for LangWatch observability and context tracking.

These hooks integrate with the Claude Agent SDK's PreToolUse and PostToolUse
events to capture tool execution for observability and graph visualization.

Enhanced with:
- Reflection pattern: Validates tool results and suggests alternatives
- Error recovery: Tracks retries and suggests fallback tools
- Confidence scoring: Computes confidence based on result quality
"""

import json
import logging
import re
import time
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# Tool result validation schemas for reflection pattern
TOOL_RESULT_VALIDATORS = {
    "search_knowledge_graph": {
        "required_fields": ["results"],
        "min_results_for_confidence": 3,
        "empty_result_fallback": "get_entity_info",
    },
    "search_documents": {
        "required_fields": ["documents"],
        "min_results_for_confidence": 2,
        "empty_result_fallback": "search_knowledge_graph",
    },
    "get_entity_info": {
        "required_fields": ["entity"],
        "min_results_for_confidence": 1,
        "empty_result_fallback": "search_knowledge_graph",
    },
    "find_relationships": {
        "required_fields": ["relationships"],
        "min_results_for_confidence": 1,
        "empty_result_fallback": "search_knowledge_graph",
    },
    "analyze_query": {
        "required_fields": ["analysis"],
        "min_results_for_confidence": 1,
        "empty_result_fallback": None,
    },
    "graph_statistics": {
        "required_fields": ["statistics"],
        "min_results_for_confidence": 1,
        "empty_result_fallback": None,
    },
}


def parse_tool_result_for_tracking(tool_name: str, result_text: str) -> dict:
    """Parse tool result into a structured format for context tracking.

    Extracts entity UUIDs from MCP tool results for graph visualization.

    Args:
        tool_name: Name of the tool that produced the result
        result_text: Raw text result from the tool

    Returns:
        Dict with tool_name, raw_text (truncated), and entity_uuids if found
    """
    parsed = {
        "tool_name": tool_name,
        "raw_text": result_text[:2000] if result_text else "",
    }

    # Extract UUIDs from result
    uuids = _extract_uuids_from_result(result_text)
    if uuids:
        parsed["entity_uuids"] = list(uuids)

    return parsed


def _extract_uuids_from_result(result_text: str) -> set[str]:
    """Extract entity UUIDs from MCP tool result text.

    The MCP server returns formatted markdown text. We look for:
    - UUID patterns in the text (standard format)
    - UUID fields in text (e.g., "[UUID: abc123...]")
    """
    if not result_text:
        return set()

    uuids = set()

    # Pattern for standard UUID format (8-4-4-4-12 hex digits)
    uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    matches = re.findall(uuid_pattern, result_text, re.IGNORECASE)
    uuids.update(matches)

    # Pattern for UUID fields in text
    uuid_field_pattern = r"\[?(?:uuid|UUID|id|ID)[\s:]+([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
    field_matches = re.findall(uuid_field_pattern, result_text, re.IGNORECASE)
    uuids.update(field_matches)

    logger.debug(f"Extracted {len(uuids)} UUIDs from tool result")
    return uuids


def _extract_entity_names_from_result(result_text: str) -> set[str]:
    """Extract entity names from MCP search results.

    The MCP server returns formatted markdown with entity names like:
    - **EntityName** (Entity, Type) - Description...
    """
    if not result_text:
        return set()

    entity_names = set()

    # Pattern to match "- **EntityName** (Entity, Type)" format
    entity_pattern = r"- \*\*([^*]+)\*\* \([^)]+\)"
    matches = re.findall(entity_pattern, result_text)
    entity_names.update(matches)

    # Also match simpler "**EntityName**" patterns
    simple_pattern = r"\*\*([A-Za-z][A-Za-z0-9_ -]{2,})\*\*"
    simple_matches = re.findall(simple_pattern, result_text)
    skip_terms = {
        "Query Analysis",
        "Intent",
        "Entities",
        "Strategy",
        "Confidence",
        "Type",
        "UUID",
        "Summary",
    }
    for name in simple_matches:
        if name not in skip_terms and len(name) > 2:
            entity_names.add(name)

    logger.debug(f"Extracted {len(entity_names)} entity names from tool result")
    return entity_names


async def create_langwatch_hooks(
    session_id: str,
    langwatch_config: Any,
    context_tracker: Optional[Any] = None,
    neo4j_driver: Optional[Any] = None,
) -> tuple[Callable, Callable, Callable]:
    """Create PreToolUse and PostToolUse hooks for Claude Agent SDK.

    These hooks capture tool execution for LangWatch observability and
    track entities for graph visualization via ChatContextTracker.

    Args:
        session_id: Current session ID for correlation
        langwatch_config: LangWatch configuration instance
        context_tracker: Optional ChatContextTracker for graph visualization
        neo4j_driver: Optional Neo4j driver for entity name lookups

    Returns:
        Tuple of (pre_tool_use_hook, post_tool_use_hook, increment_turn_fn)
    """
    turn_counter = [0]  # Mutable reference for turn tracking
    # Track start times by tool_use_id to avoid data persistence issues between hooks
    tool_start_times: dict[str, float] = {}
    tool_turn_numbers: dict[str, int] = {}

    async def pre_tool_use_hook(
        input_data: dict[str, Any],
        tool_use_id: Optional[str],
        context: Any,
    ) -> dict[str, Any]:
        """Hook called before tool execution.

        Stores start time and turn number for duration calculation.
        """
        # Increment turn counter BEFORE tool execution so turn numbers are correct
        turn_counter[0] += 1

        # Store in closure-based dict keyed by tool_use_id (reliable across hooks)
        if tool_use_id:
            tool_start_times[tool_use_id] = time.time()
            tool_turn_numbers[tool_use_id] = turn_counter[0]

        tool_name = input_data.get("tool_name", "unknown")
        logger.info(f"[PreToolUse] Tool: {tool_name}, Turn: {turn_counter[0]}, tool_use_id: {tool_use_id}")

        return {}  # Don't modify or block

    async def post_tool_use_hook(
        input_data: dict[str, Any],
        tool_use_id: Optional[str],
        context: Any,
    ) -> dict[str, Any]:
        """Hook called after tool execution.

        Captures tool call in LangWatch and tracks entities for graph visualization.
        """
        # DEBUG: Log all keys in input_data to find the correct tool output key
        logger.info(f"[PostToolUse] input_data keys: {list(input_data.keys())}")

        tool_name = input_data.get("tool_name", "unknown")
        tool_input = input_data.get("tool_input", {})

        # Try multiple possible key names for tool output
        tool_output = (
            input_data.get("tool_response")
            or input_data.get("tool_output")
            or input_data.get("output")
            or input_data.get("result")
            or input_data.get("response")
            or ""
        )

        # Retrieve start time and turn number from closure-based tracking
        start_time = tool_start_times.pop(tool_use_id, time.time()) if tool_use_id else time.time()
        turn_number = tool_turn_numbers.pop(tool_use_id, turn_counter[0]) if tool_use_id else turn_counter[0]

        execution_time = time.time() - start_time

        # Debug logging to verify tool output is being captured
        logger.info(f"[PostToolUse] tool_output type: {type(tool_output)}, len: {len(str(tool_output)) if tool_output else 0}, first 200 chars: {str(tool_output)[:200] if tool_output else 'EMPTY'}")

        logger.info(
            f"[PostToolUse] Tool: {tool_name}, Turn: {turn_number}, Duration: {execution_time:.2f}s"
        )

        # Capture in LangWatch
        try:
            logger.info(f"[LangWatch] Capturing tool call: {tool_name}, session: {session_id}")
            langwatch_config.capture_tool_call_with_response(
                tool_name=tool_name,
                tool_use_id=tool_use_id or "",
                tool_input=tool_input,
                tool_output=tool_output,
                execution_time=execution_time,
                success=True,
                turn_number=turn_number,
                session_id=session_id,
            )
            logger.info(f"[LangWatch] Successfully captured tool call: {tool_name}")
        except Exception as e:
            logger.warning(f"Failed to capture tool call in LangWatch: {e}", exc_info=True)

        # Capture in LangFuse (if enabled)
        try:
            from src.chat.observability.langfuse_config import get_langfuse_client, is_initialized

            if is_initialized():
                langfuse = get_langfuse_client()
                if langfuse:
                    # Score the current span with tool execution metadata
                    langfuse.score_current_span(
                        name="tool_execution",
                        value=1.0 if tool_output else 0.0,
                        comment=f"Tool: {tool_name}, Duration: {execution_time:.2f}s",
                    )
                    logger.debug(f"[LangFuse] Scored tool call: {tool_name}")
        except Exception as e:
            logger.debug(f"LangFuse scoring skipped: {e}")

        # Track in context for graph visualization
        if context_tracker:
            try:
                parsed_result = parse_tool_result_for_tracking(tool_name, str(tool_output))

                # If no UUIDs found directly, try to look up entity names
                if not parsed_result.get("entity_uuids") and neo4j_driver:
                    entity_names = _extract_entity_names_from_result(str(tool_output))
                    if entity_names:
                        uuids = await _lookup_entity_uuids_by_name(
                            neo4j_driver, entity_names
                        )
                        if uuids:
                            parsed_result["entity_uuids"] = list(uuids)

                await context_tracker.track_tool_execution(
                    session_id, tool_name, parsed_result
                )
            except Exception as e:
                logger.warning(f"Failed to track tool execution in context: {e}")

        return {}  # Don't modify or block

    def increment_turn() -> None:
        """Increment the turn counter.

        Note: Turn counter is now incremented automatically in pre_tool_use_hook.
        This function is kept for backward compatibility but is a no-op.
        """
        # No-op: turn counter is now incremented in pre_tool_use_hook
        pass

    return pre_tool_use_hook, post_tool_use_hook, increment_turn


async def _lookup_entity_uuids_by_name(
    driver: Any, entity_names: set[str]
) -> set[str]:
    """Look up entity UUIDs from Neo4j by entity name.

    Args:
        driver: Neo4j async driver
        entity_names: Set of entity names to look up

    Returns:
        Set of UUIDs found for the given names
    """
    if not entity_names:
        return set()

    uuids = set()
    try:
        from src.config import settings

        async with driver.session(database=settings.NEO4J_DATABASE) as session:
            query = """
                MATCH (e)
                WHERE e.name IN $names OR toLower(e.name) IN $lower_names
                RETURN e.uuid as uuid
            """
            names_list = list(entity_names)
            lower_names_list = [n.lower() for n in names_list]

            result = await session.run(
                query, {"names": names_list, "lower_names": lower_names_list}
            )
            records = await result.data()

            for record in records:
                if record.get("uuid"):
                    uuids.add(record["uuid"])

            logger.info(
                f"Looked up {len(uuids)} UUIDs for {len(entity_names)} entity names"
            )

    except Exception as e:
        logger.error(f"Error looking up entity UUIDs: {e}", exc_info=True)

    return uuids


def validate_tool_result(tool_name: str, output: Any) -> dict[str, Any]:
    """Validate tool result and compute confidence score.

    Uses TOOL_RESULT_VALIDATORS to check:
    - Required fields are present
    - Minimum result count for confidence
    - Suggests fallback tool if results are poor

    Handles multiple output formats:
    - SDK content block list: [{'type': 'text', 'text': '...'}]
    - JSON dict with results/relationships keys
    - Raw string/markdown output

    Args:
        tool_name: Name of the tool (may include mcp__knowledge_graph__ prefix)
        output: Tool output (string, list of content blocks, or dict)

    Returns:
        Dict with is_valid, confidence (0-1), and optional suggestion
    """
    # Strip MCP prefix if present
    clean_name = tool_name
    if tool_name.startswith("mcp__"):
        parts = tool_name.split("__")
        if len(parts) >= 3:
            clean_name = parts[2]

    validator = TOOL_RESULT_VALIDATORS.get(clean_name, {})

    # Handle SDK content block list format: [{'type': 'text', 'text': '...'}]
    # Extract text content from content blocks
    raw_text = ""
    if isinstance(output, list):
        for block in output:
            if isinstance(block, dict) and block.get("type") == "text":
                raw_text += block.get("text", "")
        # If we extracted content, use that for validation
        if raw_text:
            output = raw_text

    # Parse output
    result: dict = {}
    try:
        if isinstance(output, str):
            raw_text = output
            # Try to find JSON in the output
            if "{" in output:
                # Find JSON portion
                json_start = output.find("{")
                json_end = output.rfind("}") + 1
                if json_end > json_start:
                    result = json.loads(output[json_start:json_end])
                else:
                    result = {"raw": output}
            else:
                result = {"raw": output}
        elif isinstance(output, dict):
            result = output
            raw_text = str(output)
        else:
            result = {"raw": str(output)}
            raw_text = str(output)
    except json.JSONDecodeError:
        result = {"raw": str(output)}
        raw_text = str(output)

    # Check required fields
    required = validator.get("required_fields", [])
    has_required = all(field in result for field in required) if required else True

    # Check for any content indicators - this is the primary validation for SDK responses
    # Content blocks with text are valid as long as they have substantive content
    has_content = len(raw_text) > 50 and not raw_text.strip().lower().startswith("error")

    # Check result count for list-based results (dict format only)
    min_results = validator.get("min_results_for_confidence", 1)
    results_list = (
        result.get("results")
        or result.get("relationships")
        or result.get("documents")
        or result.get("entities")
        or []
    )
    has_enough = len(results_list) >= min_results if isinstance(results_list, list) else True

    # Compute confidence score
    confidence = 1.0

    # For SDK content block responses, presence of substantial text content is good
    if has_content:
        # Start with high confidence if we have content
        confidence = 0.9
    elif not has_required:
        confidence = 0.5

    # Only penalize for empty results_list if we expected structured results
    if isinstance(results_list, list) and len(results_list) == 0:
        # But don't penalize if we have raw content (markdown/text responses)
        if not has_content:
            confidence = min(confidence, 0.2)
        # If we have content but no structured results, that's still okay
    elif isinstance(results_list, list) and len(results_list) < min_results:
        confidence -= 0.2

    # Check for error indicators
    output_str = raw_text.lower()
    if output_str.startswith("error") or "error:" in output_str[:100]:
        confidence = min(confidence, 0.3)
    # "not found" and "no results" are informational, not errors - lower confidence slightly
    if "not found" in output_str or "no results" in output_str:
        confidence = min(confidence, 0.6)

    # Determine suggestion
    suggestion = None
    if confidence < 0.5:
        suggestion = validator.get("empty_result_fallback")

    return {
        "is_valid": has_content or (has_required and confidence > 0.3),
        "confidence": max(0, min(1, confidence)),
        "suggestion": suggestion,
        "result_count": len(results_list) if isinstance(results_list, list) else None,
    }


async def create_enhanced_hooks(
    session_id: str,
    langwatch_config: Any,
    context_tracker: Optional[Any] = None,
    neo4j_driver: Optional[Any] = None,
    enable_reflection: bool = True,
    enable_retry: bool = True,
    max_retries: int = 2,
) -> tuple[Callable, Callable, Callable, Callable]:
    """Create enhanced hooks with reflection and error recovery.

    These hooks extend the basic observability hooks with:
    - Tool result validation and confidence scoring
    - Reflection suggestions for low-confidence results
    - Retry tracking and fallback tool suggestions
    - Comprehensive metadata for LangWatch

    Args:
        session_id: Current session ID for correlation
        langwatch_config: LangWatch configuration instance
        context_tracker: Optional ChatContextTracker for graph visualization
        neo4j_driver: Optional Neo4j driver for entity name lookups
        enable_reflection: Whether to provide reflection suggestions
        enable_retry: Whether to track retries and suggest fallbacks
        max_retries: Maximum retries per tool before giving up

    Returns:
        Tuple of (pre_hook, post_hook, increment_turn, get_reflection_summary)
    """
    turn_counter = [0]
    retry_counts: dict[str, int] = {}
    tool_results_cache: dict[str, dict] = {}
    # Track start times and turn numbers by tool_use_id (reliable across hooks)
    tool_start_times: dict[str, float] = {}
    tool_turn_numbers: dict[str, int] = {}

    async def pre_tool_use_hook(
        input_data: dict[str, Any],
        tool_use_id: Optional[str],
        context: Any,
    ) -> dict[str, Any]:
        """Pre-execution hook: Log and prepare for potential retry."""
        # Increment turn counter BEFORE tool execution so turn numbers are correct
        turn_counter[0] += 1

        tool_name = input_data.get("tool_name", "unknown")

        # Store in closure-based dict keyed by tool_use_id
        if tool_use_id:
            tool_start_times[tool_use_id] = time.time()
            tool_turn_numbers[tool_use_id] = turn_counter[0]

        logger.info(
            f"[PreToolUse Enhanced] Tool: {tool_name}, Turn: {turn_counter[0]}, "
            f"Retry: {retry_counts.get(tool_name, 0)}, tool_use_id: {tool_use_id}"
        )

        return {}

    async def post_tool_use_hook(
        input_data: dict[str, Any],
        tool_use_id: Optional[str],
        context: Any,
    ) -> dict[str, Any]:
        """Post-execution hook: Validate, reflect, and potentially suggest retry."""
        # DEBUG: Log all keys in input_data to find the correct tool output key
        logger.info(f"[PostToolUse Enhanced] input_data keys: {list(input_data.keys())}")

        tool_name = input_data.get("tool_name", "unknown")
        tool_input = input_data.get("tool_input", {})

        # Try multiple possible key names for tool output
        output_keys = ["tool_response", "tool_output", "output", "result", "response"]
        tool_output = None
        found_key = None

        for key in output_keys:
            if key in input_data and input_data[key]:
                tool_output = input_data[key]
                found_key = key
                break

        if tool_output is None:
            # Log all available keys for debugging
            available_keys = list(input_data.keys())
            logger.warning(
                f"[PostToolUse Enhanced] Tool output not found. Tried keys: {output_keys}. "
                f"Available keys: {available_keys}. tool_name={tool_name}, tool_use_id={tool_use_id}"
            )

            # Try to extract from nested structures as fallback
            if "content" in input_data:
                tool_output = input_data["content"]
                found_key = "content"
                logger.info(f"[PostToolUse Enhanced] Found output in 'content' key")
            else:
                # Last resort: convert entire input_data to string (excluding internal fields)
                import json
                filtered = {k: v for k, v in input_data.items() if not k.startswith("_") and k not in ["tool_name", "tool_input"]}
                if filtered:
                    tool_output = json.dumps(filtered, indent=2)
                    found_key = "fallback_serialization"
                    logger.warning(f"[PostToolUse Enhanced] Using fallback serialization for tool output")
                else:
                    tool_output = ""
                    found_key = "none"
                    logger.error(f"[PostToolUse Enhanced] No tool output found at all for {tool_name}")
        else:
            logger.debug(f"[PostToolUse Enhanced] Found tool output in key: '{found_key}'")

        # Convert to string for validation
        tool_output_str = str(tool_output) if tool_output else ""

        # Retrieve start time and turn number from closure-based tracking
        start_time = tool_start_times.pop(tool_use_id, time.time()) if tool_use_id else time.time()
        turn_number = tool_turn_numbers.pop(tool_use_id, turn_counter[0]) if tool_use_id else turn_counter[0]
        retry_count = retry_counts.get(tool_name, 0)

        execution_time = time.time() - start_time

        # Debug logging to verify tool output is being captured
        logger.info(
            f"[PostToolUse Enhanced] tool_output type: {type(tool_output)}, "
            f"len: {len(tool_output_str)}, found_key: {found_key}, "
            f"first 200 chars: {tool_output_str[:200] if tool_output_str else 'EMPTY'}"
        )

        # Validate result for reflection
        validation = validate_tool_result(tool_name, tool_output_str)

        # Cache for reflection summary
        tool_results_cache[tool_name] = {
            "output": tool_output_str[:1000],
            "validation": validation,
            "execution_time": execution_time,
            "turn_number": turn_number,
            "output_key_found": found_key,
        }

        logger.info(
            f"[PostToolUse] Tool: {tool_name}, Duration: {execution_time:.2f}s, "
            f"Confidence: {validation['confidence']:.2f}, Valid: {validation['is_valid']}"
        )

        # Capture in LangWatch with enhanced metadata
        # Add confidence/reflection data to tool_input for tracking
        enhanced_input = dict(tool_input) if tool_input else {}
        enhanced_input["_reflection"] = {
            "confidence": validation["confidence"],
            "suggestion": validation.get("suggestion"),
            "retry_count": retry_count,
            "result_count": validation.get("result_count"),
        }

        try:
            logger.info(f"[LangWatch Enhanced] Capturing tool call: {tool_name}, session: {session_id}, confidence: {validation['confidence']}")
            langwatch_config.capture_tool_call_with_response(
                tool_name=tool_name,
                tool_use_id=tool_use_id or "",
                tool_input=enhanced_input,
                tool_output=tool_output,
                execution_time=execution_time,
                success=validation["is_valid"],
                turn_number=turn_number,
                session_id=session_id,
            )
            logger.info(f"[LangWatch Enhanced] Successfully captured tool call: {tool_name}")
        except Exception as e:
            logger.warning(f"Failed to capture tool call in LangWatch: {e}", exc_info=True)

        # Track in context for graph visualization
        if context_tracker:
            try:
                parsed_result = parse_tool_result_for_tracking(tool_name, str(tool_output))

                # If no UUIDs found directly, try to look up entity names
                if not parsed_result.get("entity_uuids") and neo4j_driver:
                    entity_names = _extract_entity_names_from_result(str(tool_output))
                    if entity_names:
                        uuids = await _lookup_entity_uuids_by_name(
                            neo4j_driver, entity_names
                        )
                        if uuids:
                            parsed_result["entity_uuids"] = list(uuids)

                # Add validation metadata
                parsed_result["confidence"] = validation["confidence"]

                await context_tracker.track_tool_execution(
                    session_id, tool_name, parsed_result
                )
            except Exception as e:
                logger.warning(f"Failed to track tool execution in context: {e}")

        # Prepare hook response
        response: dict[str, Any] = {}

        # Return reflection suggestion if enabled and confidence is low
        if enable_reflection and validation["confidence"] < 0.7:
            suggestion = validation.get("suggestion")
            if suggestion:
                response["hookSpecificOutput"] = {
                    "hookEventName": "PostToolUse",
                    "reflection": (
                        f"Low confidence result ({validation['confidence']:.0%}). "
                        f"Consider trying: {suggestion}"
                    ),
                }
            elif validation["confidence"] < 0.5:
                response["hookSpecificOutput"] = {
                    "hookEventName": "PostToolUse",
                    "reflection": (
                        f"Low confidence result ({validation['confidence']:.0%}). "
                        "Consider: trying different search terms, broader query, "
                        "or a different tool."
                    ),
                }

        # Track retry if needed
        if enable_retry and not validation["is_valid"]:
            retry_counts[tool_name] = retry_count + 1

        return response

    def increment_turn() -> None:
        """Increment the turn counter.

        Note: Turn counter is now incremented automatically in pre_tool_use_hook.
        This function is kept for backward compatibility but is a no-op.
        """
        # No-op: turn counter is now incremented in pre_tool_use_hook
        pass

    def get_reflection_summary() -> dict[str, Any]:
        """Get summary of all tool results for final reflection.

        Returns metadata about the quality of tool results across the session.
        """
        if not tool_results_cache:
            return {
                "total_tools": 0,
                "avg_confidence": 1.0,
                "low_confidence_tools": [],
                "turns": turn_counter[0],
            }

        confidences = [r["validation"]["confidence"] for r in tool_results_cache.values()]
        avg_confidence = sum(confidences) / len(confidences)

        low_confidence_tools = [
            tool_name
            for tool_name, data in tool_results_cache.items()
            if data["validation"]["confidence"] < 0.7
        ]

        return {
            "total_tools": len(tool_results_cache),
            "avg_confidence": avg_confidence,
            "low_confidence_tools": low_confidence_tools,
            "turns": turn_counter[0],
            "tool_confidences": {
                tool: data["validation"]["confidence"]
                for tool, data in tool_results_cache.items()
            },
        }

    return pre_tool_use_hook, post_tool_use_hook, increment_turn, get_reflection_summary
