"""Observability module for LLMOps monitoring.

Supports multiple providers via OBSERVABILITY_PROVIDER setting:
- "langwatch": Use LangWatch only (legacy)
- "langfuse": Use LangFuse only (recommended - native Claude Agent SDK support)
- "both": Use both simultaneously (for migration/validation)
"""

from .langwatch_config import LangWatchConfig, langwatch_config
from .langfuse_config import (
    initialize_langfuse,
    get_langfuse_client,
    is_initialized as langfuse_is_initialized,
    shutdown as langfuse_shutdown,
    create_trace_context as langfuse_create_trace,
    update_trace as langfuse_update_trace,
    capture_generation as langfuse_capture_generation,
    capture_tool_call as langfuse_capture_tool_call,
)
from .observability_provider import ObservabilityProvider, observability_provider

__all__ = [
    # LangWatch (legacy)
    "LangWatchConfig",
    "langwatch_config",
    # LangFuse (recommended)
    "initialize_langfuse",
    "get_langfuse_client",
    "langfuse_is_initialized",
    "langfuse_shutdown",
    "langfuse_create_trace",
    "langfuse_update_trace",
    "langfuse_capture_generation",
    "langfuse_capture_tool_call",
    # Unified provider
    "ObservabilityProvider",
    "observability_provider",
]
