"""Shared utilities for Claude Agent SDK integration.

This module provides:
- Hooks for observability (LangWatch) and reflection patterns
- Context management for multi-turn conversations
- Tool result validation and confidence scoring
"""

from .sdk_hooks import (
    create_langwatch_hooks,
    create_enhanced_hooks,
    parse_tool_result_for_tracking,
    validate_tool_result,
    TOOL_RESULT_VALIDATORS,
)
from .context_manager import SDKContextManager, sdk_context_manager

__all__ = [
    # Basic hooks
    "create_langwatch_hooks",
    "parse_tool_result_for_tracking",
    # Enhanced hooks with reflection
    "create_enhanced_hooks",
    "validate_tool_result",
    "TOOL_RESULT_VALIDATORS",
    # Context management
    "SDKContextManager",
    "sdk_context_manager",
]
