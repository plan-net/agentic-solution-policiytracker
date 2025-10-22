"""Integration tests for LangWatch observability."""

import os

import pytest

from src.chat.observability.langwatch_config import LangWatchConfig, langwatch_config


class TestLangWatchIntegration:
    """Test LangWatch integration."""

    def test_langwatch_config_initialization(self) -> None:
        """Test that LangWatch config can be initialized."""
        assert langwatch_config is not None
        assert hasattr(langwatch_config, "enabled")
        assert hasattr(langwatch_config, "initialize")
        assert hasattr(langwatch_config, "trace")

    def test_langwatch_config_attributes(self) -> None:
        """Test LangWatch config attributes."""
        config = LangWatchConfig()
        assert isinstance(config.enabled, bool)
        assert isinstance(config._initialized, bool)
        assert config.endpoint is not None

    @pytest.mark.skipif(
        os.getenv("ENABLE_LANGWATCH") != "true", reason="LangWatch not enabled in environment"
    )
    def test_langwatch_initialization_enabled(self) -> None:
        """Test LangWatch initialization when enabled."""
        config = LangWatchConfig()
        result = config.initialize()
        if config.api_key:
            assert result is True
            assert config._initialized is True
        else:
            # Without API key, initialization should fail gracefully
            assert result is False

    def test_langwatch_initialization_disabled(self) -> None:
        """Test LangWatch initialization when disabled."""
        # Temporarily disable
        original = os.getenv("ENABLE_LANGWATCH")
        os.environ["ENABLE_LANGWATCH"] = "false"

        config = LangWatchConfig()
        result = config.initialize()
        assert result is False
        assert config._initialized is False

        # Restore
        if original:
            os.environ["ENABLE_LANGWATCH"] = original
        else:
            del os.environ["ENABLE_LANGWATCH"]

    def test_langwatch_trace_decorator_passthrough(self) -> None:
        """Test that trace decorator works as passthrough when disabled."""

        @langwatch_config.trace(name="test_function")
        def test_func() -> str:
            return "success"

        result = test_func()
        assert result == "success"

    def test_langwatch_trace_decorator_with_metadata(self) -> None:
        """Test trace decorator with metadata."""

        @langwatch_config.trace(name="test_function", metadata={"test": "value"})
        async def async_test_func() -> str:
            return "success"

        import asyncio

        result = asyncio.run(async_test_func())
        assert result == "success"

    def test_langwatch_config_environment_variables(self) -> None:
        """Test that config reads environment variables correctly."""
        # Set test environment variables
        os.environ["ENABLE_LANGWATCH"] = "true"
        os.environ["LANGWATCH_API_KEY"] = "test-key"
        os.environ["LANGWATCH_ENDPOINT"] = "http://test-endpoint:5560"

        config = LangWatchConfig()

        assert config.enabled is True
        assert config.api_key == "test-key"
        assert config.endpoint == "http://test-endpoint:5560"

        # Cleanup
        del os.environ["ENABLE_LANGWATCH"]
        del os.environ["LANGWATCH_API_KEY"]
        del os.environ["LANGWATCH_ENDPOINT"]

    def test_multiple_initialization_calls(self) -> None:
        """Test that multiple initialization calls are handled correctly."""
        config = LangWatchConfig()

        # First call
        result1 = config.initialize()

        # Second call should return quickly if already initialized
        result2 = config.initialize()

        # Both should have same result
        assert result1 == result2


class TestLangWatchTracing:
    """Test LangWatch tracing functionality."""

    def test_trace_sync_function(self) -> None:
        """Test tracing synchronous functions."""

        @langwatch_config.trace(name="sync_test")
        def sync_func(x: int, y: int) -> int:
            return x + y

        result = sync_func(2, 3)
        assert result == 5

    def test_trace_async_function(self) -> None:
        """Test tracing asynchronous functions."""

        @langwatch_config.trace(name="async_test")
        async def async_func(x: int, y: int) -> int:
            return x + y

        import asyncio

        result = asyncio.run(async_func(2, 3))
        assert result == 5

    def test_trace_with_exception(self) -> None:
        """Test that traced functions can raise exceptions."""

        @langwatch_config.trace(name="exception_test")
        def func_with_exception() -> None:
            raise ValueError("Test exception")

        with pytest.raises(ValueError, match="Test exception"):
            func_with_exception()

    def test_trace_nested_calls(self) -> None:
        """Test nested traced function calls."""

        @langwatch_config.trace(name="outer_function")
        def outer() -> str:
            return inner()

        @langwatch_config.trace(name="inner_function")
        def inner() -> str:
            return "nested_result"

        result = outer()
        assert result == "nested_result"
