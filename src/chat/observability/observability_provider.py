"""Unified observability provider with feature flag support.

This module provides a unified interface for observability that can route
to LangWatch, LangFuse, or both providers based on the OBSERVABILITY_PROVIDER
setting. This enables gradual migration from LangWatch to LangFuse.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ObservabilityProvider:
    """Manages observability initialization based on OBSERVABILITY_PROVIDER setting.

    Supported providers:
    - "langwatch": Use LangWatch only (current default)
    - "langfuse": Use LangFuse only (with Claude Agent SDK auto-instrumentation)
    - "both": Use both providers simultaneously (for migration/validation)
    """

    def __init__(self) -> None:
        self._initialized = False
        self._provider: Optional[str] = None
        self._langwatch_enabled = False
        self._langfuse_enabled = False

    def initialize(self, instrumentation_mode: str = "manual") -> bool:
        """Initialize the configured observability provider(s).

        Args:
            instrumentation_mode: Mode for LangWatch initialization
                ("manual", "langchain", "anthropic", "both", "auto")

        Returns:
            True if at least one provider was successfully initialized.
        """
        if self._initialized:
            return True

        from src.config import settings

        self._provider = getattr(settings, "OBSERVABILITY_PROVIDER", "langwatch")
        success = False

        # Initialize LangWatch if configured
        if self._provider in ("langwatch", "both"):
            try:
                from src.chat.observability.langwatch_config import langwatch_config

                if langwatch_config.initialize(instrumentation_mode):
                    self._langwatch_enabled = True
                    success = True
                    logger.info("LangWatch initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize LangWatch: {e}")

        # Initialize LangFuse if configured
        if self._provider in ("langfuse", "both"):
            try:
                from src.chat.observability.langfuse_config import initialize_langfuse

                if initialize_langfuse():
                    self._langfuse_enabled = True
                    success = True
                    logger.info("LangFuse initialized with Claude Agent SDK auto-instrumentation")
            except Exception as e:
                logger.warning(f"Failed to initialize LangFuse: {e}")

        self._initialized = success

        if not success:
            logger.warning(
                f"No observability providers initialized (provider={self._provider})"
            )

        return success

    @property
    def enabled(self) -> bool:
        """Check if any observability provider is enabled."""
        return self._initialized

    @property
    def provider(self) -> Optional[str]:
        """Get the configured provider name."""
        return self._provider

    @property
    def langwatch_enabled(self) -> bool:
        """Check if LangWatch is enabled."""
        return self._langwatch_enabled

    @property
    def langfuse_enabled(self) -> bool:
        """Check if LangFuse is enabled."""
        return self._langfuse_enabled

    def shutdown(self) -> None:
        """Shutdown all active providers."""
        if self._langfuse_enabled:
            try:
                from src.chat.observability.langfuse_config import shutdown

                shutdown()
                logger.info("LangFuse shutdown complete")
            except Exception as e:
                logger.warning(f"LangFuse shutdown error: {e}")

        # LangWatch doesn't have a shutdown method

    def get_status(self) -> dict:
        """Get status of all observability providers.

        Returns:
            Dict with provider status information.
        """
        return {
            "provider": self._provider,
            "initialized": self._initialized,
            "langwatch_enabled": self._langwatch_enabled,
            "langfuse_enabled": self._langfuse_enabled,
        }


# Global instance
observability_provider = ObservabilityProvider()
