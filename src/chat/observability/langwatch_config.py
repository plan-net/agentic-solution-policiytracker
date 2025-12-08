"""LangWatch observability configuration."""

import logging
from collections.abc import Callable
from typing import Any, Optional

logger = logging.getLogger(__name__)


class LangWatchConfig:
    """LangWatch observability configuration manager."""

    def __init__(self) -> None:
        # Import settings lazily to avoid circular imports
        from src.config import settings

        self.enabled = settings.ENABLE_LANGWATCH
        self.api_key = settings.LANGWATCH_API_KEY
        self.endpoint = settings.LANGWATCH_ENDPOINT
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
                api_key=self.api_key,
                endpoint_url=self.endpoint,
                instrumentors=[LangChainInstrumentor()],
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
        """Decorator for tracing functions with LangWatch.

        Note: This decorator defers the initialization check to runtime,
        allowing decorators to be applied at import time before initialize() is called.
        """
        import functools

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                # Check initialization at runtime, not decoration time
                if not self.enabled or not self._initialized:
                    return await func(*args, **kwargs)

                try:
                    import langwatch

                    # Use langwatch.trace as a context manager for async functions
                    with langwatch.trace(name=name, metadata=metadata or {}):
                        return await func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"LangWatch trace failed for {name}: {e}")
                    return await func(*args, **kwargs)

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                # Check initialization at runtime, not decoration time
                if not self.enabled or not self._initialized:
                    return func(*args, **kwargs)

                try:
                    import langwatch

                    # Use langwatch.trace as a context manager for sync functions
                    with langwatch.trace(name=name, metadata=metadata or {}):
                        return func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"LangWatch trace failed for {name}: {e}")
                    return func(*args, **kwargs)

            # Return appropriate wrapper based on function type
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper

        return decorator

    def capture_tool_execution(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_output: Any,
        execution_time: float,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """Capture a tool execution as a LangWatch span.

        Use this to explicitly log tool executions with full metadata.
        """
        if not self.enabled or not self._initialized:
            return

        try:
            import langwatch

            # Create span with tool metadata
            with langwatch.trace(
                name=f"tool:{tool_name}",
                metadata={
                    "tool_name": tool_name,
                    "tool_input": tool_input,
                    "execution_time_seconds": execution_time,
                    "success": success,
                    "error": error,
                },
            ) as span:
                # Set span attributes for better visibility
                if hasattr(span, "set_attribute"):
                    span.set_attribute("tool.name", tool_name)
                    span.set_attribute("tool.success", success)
                    span.set_attribute("tool.execution_time", execution_time)
                    if error:
                        span.set_attribute("tool.error", error)

        except Exception as e:
            logger.warning(f"Failed to capture tool execution for {tool_name}: {e}")


# Global configuration instance
langwatch_config = LangWatchConfig()
