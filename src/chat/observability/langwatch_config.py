"""LangWatch observability configuration."""

import logging
import os
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class LangWatchConfig:
    """LangWatch observability configuration manager."""

    def __init__(self) -> None:
        self.enabled = os.getenv("ENABLE_LANGWATCH", "false").lower() == "true"
        self.api_key = os.getenv("LANGWATCH_API_KEY")
        self.endpoint = os.getenv("LANGWATCH_ENDPOINT", "http://langwatch-server:5560")
        self._initialized = False

    def initialize(self) -> bool:
        """Initialize LangWatch instrumentation."""
        if not self.enabled:
            logger.info("LangWatch observability disabled")
            return False

        if not self.api_key:
            logger.warning("LangWatch enabled but LANGWATCH_API_KEY not set")
            return False

        if self._initialized:
            logger.debug("LangWatch already initialized")
            return True

        try:
            # Import LangWatch SDK
            import langwatch
            from openinference.instrumentation.langchain import LangChainInstrumentor

            # Setup LangWatch with LangChain instrumentation
            langwatch.setup(
                api_key=self.api_key, endpoint=self.endpoint, instrumentors=[LangChainInstrumentor()]
            )

            self._initialized = True
            logger.info(f"LangWatch initialized successfully at {self.endpoint}")
            return True

        except ImportError as e:
            logger.error(f"Failed to import LangWatch dependencies: {e}")
            logger.error("Please install: uv sync")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize LangWatch: {e}")
            return False

    def trace(self, name: str, metadata: Optional[dict[str, Any]] = None) -> Callable:
        """Decorator for tracing functions with LangWatch."""
        if not self.enabled or not self._initialized:
            # Passthrough decorator if not enabled
            def decorator(func: Callable) -> Callable:
                return func

            return decorator

        try:
            import langwatch

            return langwatch.trace(name=name, metadata=metadata or {})
        except Exception as e:
            logger.warning(f"LangWatch trace decorator failed: {e}")

            # Return passthrough decorator on error
            def decorator(func: Callable) -> Callable:
                return func

            return decorator


# Global configuration instance
langwatch_config = LangWatchConfig()
