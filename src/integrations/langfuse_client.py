"""
Langfuse integration client with fallback handling.
Provides observability for LLM operations with graceful degradation.
"""

import asyncio
import structlog
from typing import Any, Dict, Optional, Callable, TypeVar, Union
from functools import wraps

from src.config import settings

logger = structlog.get_logger()

# Type for functions that can be traced
F = TypeVar("F", bound=Callable[..., Any])


class LangfuseClient:
    """Langfuse client with fallback support."""

    def __init__(self):
        self._client: Optional[Any] = None
        self._available = False
        self._initialization_attempted = False

    async def _initialize(self) -> None:
        """Initialize Langfuse client if available."""
        if self._initialization_attempted:
            return

        self._initialization_attempted = True

        try:
            # Only try to import and initialize if Langfuse is configured
            if not all(
                [settings.LANGFUSE_SECRET_KEY, settings.LANGFUSE_PUBLIC_KEY, settings.LANGFUSE_HOST]
            ):
                logger.info("Langfuse not configured, using fallback mode")
                return

            from langfuse import Langfuse

            self._client = Langfuse(
                secret_key=settings.LANGFUSE_SECRET_KEY,
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                host=settings.LANGFUSE_HOST,
            )

            # Test connection
            await asyncio.to_thread(self._client.auth_check)
            self._available = True
            logger.info("Langfuse client initialized successfully")

        except ImportError:
            logger.info("Langfuse not installed, using fallback mode")
        except Exception as e:
            logger.warning(f"Failed to initialize Langfuse: {e}, using fallback mode")

    @property
    def available(self) -> bool:
        """Check if Langfuse is available."""
        return self._available

    async def trace(
        self,
        name: str,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[list[str]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        version: Optional[str] = None,
        release: Optional[str] = None,
        public: Optional[bool] = None,
    ) -> "TraceContext":
        """Create a trace context."""
        await self._initialize()

        return TraceContext(
            client=self._client if self._available else None,
            name=name,
            input_data=input_data,
            output_data=output_data,
            metadata=metadata,
            tags=tags,
            user_id=user_id,
            session_id=session_id,
            version=version,
            release=release,
            public=public,
        )

    async def generation(
        self,
        name: str,
        model: Optional[str] = None,
        input_data: Optional[Union[str, Dict[str, Any]]] = None,
        output_data: Optional[Union[str, Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        usage: Optional[Dict[str, int]] = None,
        prompt_name: Optional[str] = None,
        prompt_version: Optional[str] = None,
    ) -> "GenerationContext":
        """Create a generation context for LLM calls."""
        await self._initialize()

        return GenerationContext(
            client=self._client if self._available else None,
            name=name,
            model=model,
            input_data=input_data,
            output_data=output_data,
            metadata=metadata,
            usage=usage,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
        )

    async def get_prompt(
        self,
        name: str,
        version: Optional[Union[int, str]] = None,
        fallback_prompt: Optional[str] = None,
    ) -> str:
        """Get prompt from Langfuse with fallback to local prompt."""
        await self._initialize()

        if not self._available:
            if fallback_prompt:
                return fallback_prompt
            raise ValueError(f"Langfuse not available and no fallback prompt provided for '{name}'")

        try:
            prompt = await asyncio.to_thread(self._client.get_prompt, name=name, version=version)
            return prompt.prompt
        except Exception as e:
            logger.warning(f"Failed to get prompt '{name}' from Langfuse: {e}")
            if fallback_prompt:
                logger.info(f"Using fallback prompt for '{name}'")
                return fallback_prompt
            raise

    async def score(
        self,
        trace_id: str,
        name: str,
        value: Union[int, float],
        comment: Optional[str] = None,
    ) -> None:
        """Add a score to a trace."""
        await self._initialize()

        if not self._available:
            logger.debug(f"Score '{name}' not recorded (Langfuse unavailable): {value}")
            return

        try:
            await asyncio.to_thread(
                self._client.score,
                trace_id=trace_id,
                name=name,
                value=value,
                comment=comment,
            )
        except Exception as e:
            logger.warning(f"Failed to record score: {e}")


class TraceContext:
    """Context manager for Langfuse traces."""

    def __init__(
        self,
        client: Optional[Any],
        name: str,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[list[str]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        version: Optional[str] = None,
        release: Optional[str] = None,
        public: Optional[bool] = None,
    ):
        self.client = client
        self.name = name
        self.input_data = input_data or {}
        self.output_data = output_data or {}
        self.metadata = metadata or {}
        self.tags = tags or []
        self.user_id = user_id
        self.session_id = session_id
        self.version = version
        self.release = release
        self.public = public
        self._trace = None
        self.trace_id: Optional[str] = None

    async def __aenter__(self):
        if self.client:
            try:
                self._trace = await asyncio.to_thread(
                    self.client.trace,
                    name=self.name,
                    input=self.input_data,
                    metadata=self.metadata,
                    tags=self.tags,
                    user_id=self.user_id,
                    session_id=self.session_id,
                    version=self.version,
                    release=self.release,
                    public=self.public,
                )
                self.trace_id = self._trace.id
            except Exception as e:
                logger.warning(f"Failed to create trace '{self.name}': {e}")

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._trace:
            try:
                await asyncio.to_thread(
                    self._trace.update,
                    output=self.output_data,
                    level="ERROR" if exc_type else "DEFAULT",
                )
            except Exception as e:
                logger.warning(f"Failed to update trace '{self.name}': {e}")

    def update_output(self, output_data: Dict[str, Any]) -> None:
        """Update the output data for this trace."""
        self.output_data.update(output_data)


class GenerationContext:
    """Context manager for Langfuse generations."""

    def __init__(
        self,
        client: Optional[Any],
        name: str,
        model: Optional[str] = None,
        input_data: Optional[Union[str, Dict[str, Any]]] = None,
        output_data: Optional[Union[str, Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        usage: Optional[Dict[str, int]] = None,
        prompt_name: Optional[str] = None,
        prompt_version: Optional[str] = None,
    ):
        self.client = client
        self.name = name
        self.model = model
        self.input_data = input_data
        self.output_data = output_data
        self.metadata = metadata or {}
        self.usage = usage
        self.prompt_name = prompt_name
        self.prompt_version = prompt_version
        self._generation = None

    async def __aenter__(self):
        if self.client:
            try:
                self._generation = await asyncio.to_thread(
                    self.client.generation,
                    name=self.name,
                    model=self.model,
                    input=self.input_data,
                    metadata=self.metadata,
                    usage=self.usage,
                    prompt_name=self.prompt_name,
                    prompt_version=self.prompt_version,
                )
            except Exception as e:
                logger.warning(f"Failed to create generation '{self.name}': {e}")

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._generation:
            try:
                await asyncio.to_thread(
                    self._generation.update,
                    output=self.output_data,
                    level="ERROR" if exc_type else "DEFAULT",
                    usage=self.usage,
                )
            except Exception as e:
                logger.warning(f"Failed to update generation '{self.name}': {e}")

    def update_output(self, output_data: Union[str, Dict[str, Any]]) -> None:
        """Update the output data for this generation."""
        self.output_data = output_data

    def update_usage(self, usage: Dict[str, int]) -> None:
        """Update the usage data for this generation."""
        self.usage = usage


# Global client instance
langfuse_client = LangfuseClient()


def trace(
    name: Optional[str] = None,
    input_keys: Optional[list[str]] = None,
    output_keys: Optional[list[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    tags: Optional[list[str]] = None,
) -> Callable[[F], F]:
    """Decorator to trace function calls with Langfuse."""

    def decorator(func: F) -> F:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            trace_name = name or func.__name__

            # Extract input data
            input_data = {}
            if input_keys:
                # Get from kwargs
                for key in input_keys:
                    if key in kwargs:
                        input_data[key] = kwargs[key]
                # Get from args if we know parameter names
                import inspect

                sig = inspect.signature(func)
                param_names = list(sig.parameters.keys())
                for i, arg in enumerate(args):
                    if i < len(param_names) and param_names[i] in input_keys:
                        input_data[param_names[i]] = arg

            async with langfuse_client.trace(
                name=trace_name,
                input_data=input_data,
                metadata=metadata,
                tags=tags,
            ) as trace_ctx:
                try:
                    result = await func(*args, **kwargs)

                    # Extract output data
                    output_data = {}
                    if output_keys and isinstance(result, dict):
                        for key in output_keys:
                            if key in result:
                                output_data[key] = result[key]
                    elif result is not None:
                        output_data["result"] = result

                    trace_ctx.update_output(output_data)
                    return result

                except Exception as e:
                    trace_ctx.update_output({"error": str(e)})
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, run the async trace wrapper
            return asyncio.run(async_wrapper(*args, **kwargs))

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
