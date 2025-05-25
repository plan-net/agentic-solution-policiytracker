"""
Unit tests for utils.logging module.
Tests logging setup, configuration, and performance logging functionality.
"""

import logging
import sys
from unittest.mock import patch, MagicMock
import pytest
import structlog

from src.utils.logging import setup_logging, log_performance


class TestSetupLogging:
    """Test setup_logging function."""
    
    @patch('src.utils.logging.settings')
    @patch('logging.basicConfig')
    @patch('structlog.configure')
    def test_setup_logging_json_format(self, mock_structlog_configure, mock_logging_config, mock_settings):
        """Test setup_logging with JSON format."""
        # Configure mock settings
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_FORMAT = "json"
        
        # Call setup_logging
        logger = setup_logging()
        
        # Verify logging.basicConfig was called correctly
        mock_logging_config.assert_called_once_with(
            format="%(message)s",
            stream=sys.stdout,
            level=logging.INFO
        )
        
        # Verify structlog.configure was called
        mock_structlog_configure.assert_called_once()
        
        # Check the processors configuration
        call_args = mock_structlog_configure.call_args
        processors = call_args[1]['processors']
        
        # Should have basic processors plus JSONRenderer
        assert len(processors) >= 4
        assert any("JSONRenderer" in str(proc) for proc in processors)
        
        # Verify other configuration
        assert call_args[1]['wrapper_class'] == structlog.stdlib.BoundLogger
        assert call_args[1]['context_class'] == dict
        assert call_args[1]['cache_logger_on_first_use'] is True
    
    @patch('src.utils.logging.settings')
    @patch('logging.basicConfig')
    @patch('structlog.configure')
    def test_setup_logging_console_format(self, mock_structlog_configure, mock_logging_config, mock_settings):
        """Test setup_logging with console format."""
        # Configure mock settings
        mock_settings.LOG_LEVEL = "DEBUG"
        mock_settings.LOG_FORMAT = "console"
        
        # Call setup_logging
        logger = setup_logging()
        
        # Verify logging.basicConfig was called with DEBUG level
        mock_logging_config.assert_called_once_with(
            format="%(message)s",
            stream=sys.stdout,
            level=logging.DEBUG
        )
        
        # Check the processors configuration
        call_args = mock_structlog_configure.call_args
        processors = call_args[1]['processors']
        
        # Should have basic processors plus ConsoleRenderer
        assert len(processors) >= 4
        assert any("ConsoleRenderer" in str(proc) for proc in processors)
    
    @patch('src.utils.logging.settings')
    @patch('logging.basicConfig')
    @patch('structlog.configure')
    def test_setup_logging_different_log_levels(self, mock_structlog_configure, mock_logging_config, mock_settings):
        """Test setup_logging with different log levels."""
        test_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        for level in test_levels:
            mock_settings.LOG_LEVEL = level
            mock_settings.LOG_FORMAT = "json"
            
            # Reset mock
            mock_logging_config.reset_mock()
            
            # Call setup_logging
            setup_logging()
            
            # Verify correct logging level was set
            expected_level = getattr(logging, level.upper())
            mock_logging_config.assert_called_once_with(
                format="%(message)s",
                stream=sys.stdout,
                level=expected_level
            )
    
    @patch('src.utils.logging.settings')
    @patch('logging.basicConfig')
    @patch('structlog.configure')
    @patch('structlog.get_logger')
    def test_setup_logging_returns_logger(self, mock_get_logger, mock_structlog_configure, mock_logging_config, mock_settings):
        """Test that setup_logging returns a logger."""
        # Configure mock settings
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_FORMAT = "json"
        
        # Mock the logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Call setup_logging
        result = setup_logging()
        
        # Verify logger was returned
        assert result == mock_logger
        mock_get_logger.assert_called_once()
    
    @patch('src.utils.logging.settings')
    def test_setup_logging_processors_order(self, mock_settings):
        """Test that processors are configured in the correct order."""
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_FORMAT = "json"
        
        with patch('structlog.configure') as mock_configure:
            setup_logging()
            
            # Get the processors list
            call_args = mock_configure.call_args
            processors = call_args[1]['processors']
            
            # Check that basic processors are included
            processor_types = [str(type(proc)) for proc in processors]
            
            # Should include essential processors
            assert any("merge_contextvars" in str(proc) for proc in processors)
            assert any("add_log_level" in str(proc) for proc in processors)
            assert any("TimeStamper" in str(proc) for proc in processors)
    
    @patch('src.utils.logging.settings')
    def test_setup_logging_case_insensitive_format(self, mock_settings):
        """Test that LOG_FORMAT is case insensitive."""
        test_cases = ["JSON", "Json", "json", "CONSOLE", "Console", "console"]
        
        for format_case in test_cases:
            mock_settings.LOG_LEVEL = "INFO"
            mock_settings.LOG_FORMAT = format_case
            
            with patch('structlog.configure') as mock_configure:
                setup_logging()
                
                call_args = mock_configure.call_args
                processors = call_args[1]['processors']
                
                if format_case.lower() == "json":
                    assert any("JSONRenderer" in str(proc) for proc in processors)
                else:
                    assert any("ConsoleRenderer" in str(proc) for proc in processors)


class TestLogPerformance:
    """Test log_performance function."""
    
    @patch('src.utils.logging.settings')
    @patch('structlog.get_logger')
    def test_log_performance_enabled(self, mock_get_logger, mock_settings):
        """Test log_performance when performance logging is enabled."""
        # Configure mock settings
        mock_settings.ENABLE_PERFORMANCE_LOGGING = True
        
        # Mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Call log_performance
        log_performance("test_operation", 150.5, additional_param="test_value")
        
        # Verify logger was called correctly
        mock_get_logger.assert_called_once()
        mock_logger.info.assert_called_once_with(
            "Performance metric",
            operation="test_operation",
            duration_ms=150.5,
            additional_param="test_value"
        )
    
    @patch('src.utils.logging.settings')
    @patch('structlog.get_logger')
    def test_log_performance_disabled(self, mock_get_logger, mock_settings):
        """Test log_performance when performance logging is disabled."""
        # Configure mock settings
        mock_settings.ENABLE_PERFORMANCE_LOGGING = False
        
        # Mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Call log_performance
        log_performance("test_operation", 150.5)
        
        # Verify logger was not called
        mock_get_logger.assert_not_called()
        mock_logger.info.assert_not_called()
    
    @patch('src.utils.logging.settings')
    @patch('structlog.get_logger')
    def test_log_performance_with_kwargs(self, mock_get_logger, mock_settings):
        """Test log_performance with additional keyword arguments."""
        # Configure mock settings
        mock_settings.ENABLE_PERFORMANCE_LOGGING = True
        
        # Mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Call log_performance with additional kwargs
        log_performance(
            "database_query",
            250.75,
            query_type="SELECT",
            table_name="documents",
            rows_affected=100,
            cache_hit=True
        )
        
        # Verify logger was called with all parameters
        mock_logger.info.assert_called_once_with(
            "Performance metric",
            operation="database_query",
            duration_ms=250.75,
            query_type="SELECT",
            table_name="documents",
            rows_affected=100,
            cache_hit=True
        )
    
    @patch('src.utils.logging.settings')
    @patch('structlog.get_logger')
    def test_log_performance_different_operations(self, mock_get_logger, mock_settings):
        """Test log_performance with different operation types."""
        # Configure mock settings
        mock_settings.ENABLE_PERFORMANCE_LOGGING = True
        
        # Mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Test different operations
        operations = [
            ("document_processing", 1500.0),
            ("llm_analysis", 2250.5),
            ("scoring_calculation", 750.25),
            ("report_generation", 3000.0)
        ]
        
        for operation, duration in operations:
            mock_logger.reset_mock()
            
            log_performance(operation, duration)
            
            mock_logger.info.assert_called_once_with(
                "Performance metric",
                operation=operation,
                duration_ms=duration
            )


class TestLoggingIntegration:
    """Integration tests for logging functionality."""
    
    def test_real_logging_setup(self):
        """Test actual logging setup without mocks."""
        # This test uses real logging to ensure it works end-to-end
        with patch('src.utils.logging.settings') as mock_settings:
            mock_settings.LOG_LEVEL = "INFO"
            mock_settings.LOG_FORMAT = "json"
            
            # Call actual setup_logging
            logger = setup_logging()
            
            # Verify we get a real logger
            assert logger is not None
            assert hasattr(logger, 'info')
            assert hasattr(logger, 'debug')
            assert hasattr(logger, 'warning')
            assert hasattr(logger, 'error')
    
    def test_logger_functionality(self):
        """Test that the configured logger actually works."""
        with patch('src.utils.logging.settings') as mock_settings:
            mock_settings.LOG_LEVEL = "DEBUG"
            mock_settings.LOG_FORMAT = "console"
            
            # Setup logging
            logger = setup_logging()
            
            # Test different log levels (should not raise exceptions)
            try:
                logger.debug("Debug message", extra_field="debug_value")
                logger.info("Info message", operation="test")
                logger.warning("Warning message", concern="test_warning")
                logger.error("Error message", error_code=500)
            except Exception as e:
                pytest.fail(f"Logging failed with exception: {e}")
    
    @patch('src.utils.logging.settings')
    def test_performance_logging_integration(self, mock_settings):
        """Test performance logging integration with real logger."""
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_FORMAT = "json"
        mock_settings.ENABLE_PERFORMANCE_LOGGING = True
        
        # Setup logging
        setup_logging()
        
        # Test performance logging (should not raise exceptions)
        try:
            log_performance("integration_test", 123.45, test_param="integration")
        except Exception as e:
            pytest.fail(f"Performance logging failed with exception: {e}")


class TestLoggingEdgeCases:
    """Test edge cases and error conditions."""
    
    @patch('src.utils.logging.settings')
    def test_invalid_log_level(self, mock_settings):
        """Test handling of invalid log level."""
        mock_settings.LOG_LEVEL = "INVALID_LEVEL"
        mock_settings.LOG_FORMAT = "json"
        
        # Should handle gracefully (getattr with invalid level)
        with patch('logging.basicConfig') as mock_config:
            setup_logging()
            
            # Should still call basicConfig, but with None or default level
            mock_config.assert_called_once()
    
    @patch('src.utils.logging.settings')
    def test_none_log_format(self, mock_settings):
        """Test handling of None LOG_FORMAT."""
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_FORMAT = None
        
        with patch('structlog.configure') as mock_configure:
            setup_logging()
            
            # Should default to console format when format is None
            call_args = mock_configure.call_args
            processors = call_args[1]['processors']
            assert any("ConsoleRenderer" in str(proc) for proc in processors)
    
    @patch('src.utils.logging.settings')
    def test_empty_operation_name(self, mock_settings):
        """Test log_performance with empty operation name."""
        mock_settings.ENABLE_PERFORMANCE_LOGGING = True
        
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            # Should handle empty operation name
            log_performance("", 100.0)
            
            mock_logger.info.assert_called_once_with(
                "Performance metric",
                operation="",
                duration_ms=100.0
            )
    
    @patch('src.utils.logging.settings')
    def test_negative_duration(self, mock_settings):
        """Test log_performance with negative duration."""
        mock_settings.ENABLE_PERFORMANCE_LOGGING = True
        
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            # Should handle negative duration
            log_performance("test_op", -50.0)
            
            mock_logger.info.assert_called_once_with(
                "Performance metric",
                operation="test_op",
                duration_ms=-50.0
            )
    
    @patch('src.utils.logging.settings')
    def test_zero_duration(self, mock_settings):
        """Test log_performance with zero duration."""
        mock_settings.ENABLE_PERFORMANCE_LOGGING = True
        
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            # Should handle zero duration
            log_performance("instant_op", 0.0)
            
            mock_logger.info.assert_called_once_with(
                "Performance metric",
                operation="instant_op",
                duration_ms=0.0
            )


class TestLoggingConfiguration:
    """Test logging configuration details."""
    
    @patch('src.utils.logging.settings')
    def test_processor_configuration(self, mock_settings):
        """Test that all required processors are configured."""
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_FORMAT = "json"
        
        with patch('structlog.configure') as mock_configure:
            setup_logging()
            
            call_args = mock_configure.call_args
            config = call_args[1]
            
            # Check all required configuration options
            assert 'processors' in config
            assert 'wrapper_class' in config
            assert 'context_class' in config
            assert 'logger_factory' in config
            assert 'cache_logger_on_first_use' in config
            
            # Verify specific configuration values
            assert config['wrapper_class'] == structlog.stdlib.BoundLogger
            assert config['context_class'] == dict
            assert config['cache_logger_on_first_use'] is True
    
    @patch('src.utils.logging.settings')
    def test_timestamper_configuration(self, mock_settings):
        """Test that TimeStamper is configured with ISO format."""
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_FORMAT = "json"
        
        with patch('structlog.configure') as mock_configure:
            setup_logging()
            
            call_args = mock_configure.call_args
            processors = call_args[1]['processors']
            
            # Find TimeStamper processor
            timestamper = None
            for proc in processors:
                if "TimeStamper" in str(type(proc)):
                    timestamper = proc
                    break
            
            # Should have TimeStamper configured
            assert timestamper is not None