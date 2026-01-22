"""LangFuse observability with native Claude Agent SDK support.

This module provides LangFuse integration using the native auto-instrumentation
for Claude Agent SDK via LangSmith's OpenTelemetry integration.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_initialized = False
_langfuse_client = None


def initialize_langfuse() -> bool:
    """Initialize LangFuse with Claude Agent SDK auto-instrumentation.

    This function:
    1. Sets up environment variables for OTEL integration
    2. Configures Claude Agent SDK auto-instrumentation via LangSmith
    3. Initializes the LangFuse client for manual enrichment

    Returns:
        True if initialization successful, False otherwise.
    """
    global _initialized, _langfuse_client

    if _initialized:
        return True

    from src.config import settings

    if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
        logger.info("LangFuse disabled (missing credentials)")
        return False

    if not settings.LANGFUSE_ENABLE_TRACING:
        logger.info("LangFuse tracing disabled via LANGFUSE_ENABLE_TRACING")
        return False

    try:
        # Set environment variables for OTEL integration
        os.environ["LANGFUSE_PUBLIC_KEY"] = settings.LANGFUSE_PUBLIC_KEY
        os.environ["LANGFUSE_SECRET_KEY"] = settings.LANGFUSE_SECRET_KEY
        os.environ["LANGFUSE_HOST"] = settings.LANGFUSE_HOST

        # Enable LangSmith OTEL integration (routes to LangFuse)
        os.environ["LANGSMITH_OTEL_ENABLED"] = "true"
        os.environ["LANGSMITH_OTEL_ONLY"] = "true"
        os.environ["LANGSMITH_TRACING"] = "true"

        # Configure Claude Agent SDK auto-instrumentation
        try:
            from langsmith.integrations.claude_agent_sdk import configure_claude_agent_sdk

            configure_claude_agent_sdk()
            logger.info("Claude Agent SDK auto-instrumentation configured")
        except ImportError:
            logger.warning(
                "langsmith[claude-agent-sdk] not installed, "
                "auto-instrumentation not available"
            )
        except Exception as e:
            logger.warning(f"Failed to configure Claude Agent SDK instrumentation: {e}")

        # Initialize LangFuse client for manual enrichment
        from langfuse import Langfuse

        _langfuse_client = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )

        # Verify connection
        _langfuse_client.auth_check()

        _initialized = True
        logger.info(
            f"LangFuse initialized with Claude Agent SDK instrumentation at {settings.LANGFUSE_HOST}"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to initialize LangFuse: {e}")
        return False


def get_langfuse_client() -> Optional["Langfuse"]:
    """Get the LangFuse client for manual trace enrichment.

    Returns:
        The LangFuse client instance if initialized, None otherwise.
    """
    return _langfuse_client


def is_initialized() -> bool:
    """Check if LangFuse is initialized.

    Returns:
        True if LangFuse is initialized, False otherwise.
    """
    return _initialized


def shutdown() -> None:
    """Flush and shutdown LangFuse client gracefully."""
    global _langfuse_client
    if _langfuse_client:
        try:
            _langfuse_client.flush()
            _langfuse_client.shutdown()
            logger.info("LangFuse shutdown complete")
        except Exception as e:
            logger.warning(f"LangFuse shutdown error: {e}")


def create_trace_context(
    name: str,
    session_id: str,
    user_message: str,
    metadata: Optional[dict] = None,
):
    """Create a LangFuse trace context manager for agent execution.

    Args:
        name: Name of the trace (e.g., "policy_tracker_query")
        session_id: Session ID for correlation
        user_message: User's input message
        metadata: Optional additional metadata

    Returns:
        Context manager for LangFuse tracing, or None if not initialized.
    """
    if not _initialized or not _langfuse_client:
        return None

    try:
        return _langfuse_client.start_as_current_span(
            name=name,
            input={"user_message": user_message, "session_id": session_id},
            metadata=metadata or {},
        )
    except Exception as e:
        logger.warning(f"Failed to create LangFuse trace context: {e}")
        return None


def update_trace(
    output: Optional[str] = None,
    metadata: Optional[dict] = None,
    tags: Optional[list] = None,
) -> None:
    """Update the current LangFuse trace with output and metadata.

    Args:
        output: Response output text
        metadata: Additional metadata to add
        tags: Tags to add to the trace
    """
    if not _initialized or not _langfuse_client:
        return

    try:
        if output or metadata:
            _langfuse_client.update_current_span(
                output=output,
                metadata=metadata,
            )
        if tags:
            _langfuse_client.update_current_trace(tags=tags)
    except Exception as e:
        logger.debug(f"Failed to update LangFuse trace: {e}")


def capture_generation(
    name: str,
    model: str,
    input_text: str,
    output_text: str,
    metadata: Optional[dict] = None,
) -> None:
    """Capture an LLM generation in LangFuse.

    Args:
        name: Name of the generation (e.g., "claude_response")
        model: Model name (e.g., "claude-3-5-sonnet")
        input_text: Input prompt/message
        output_text: Model output
        metadata: Optional additional metadata
    """
    if not _initialized or not _langfuse_client:
        return

    try:
        with _langfuse_client.start_as_current_observation(
            name=name,
            as_type="generation",
            input=input_text,
            output=output_text,
            model=model,
            metadata=metadata or {},
        ):
            pass  # Auto-ends on exit
    except Exception as e:
        logger.debug(f"Failed to capture LangFuse generation: {e}")


def capture_tool_call(
    tool_name: str,
    tool_input: dict,
    tool_output: str,
    execution_time: float,
    success: bool = True,
) -> None:
    """Capture a tool call in LangFuse.

    Args:
        tool_name: Name of the tool
        tool_input: Tool input parameters
        tool_output: Tool output/result
        execution_time: Execution time in seconds
        success: Whether the tool call was successful
    """
    if not _initialized or not _langfuse_client:
        return

    try:
        with _langfuse_client.start_as_current_span(
            name=f"tool:{tool_name}",
            input=tool_input,
            output=tool_output,
            metadata={
                "execution_time_seconds": execution_time,
                "success": success,
            },
        ):
            pass  # Auto-ends on exit
    except Exception as e:
        logger.debug(f"Failed to capture LangFuse tool call: {e}")
