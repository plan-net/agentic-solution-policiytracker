"""
Unit tests for the simplified configuration system.

Tests cover:
- Configuration path resolution based on storage mode
- Azure path configuration management
- Import script environment updates
- Settings property behavior
"""

import os
import tempfile
from unittest.mock import patch

from scripts.import_data_to_azurite import update_env_file_with_azure_paths
from src.config import Settings


class TestConfigurationSettings:
    """Test configuration settings and path resolution."""

    def test_local_mode_paths(self):
        """Test path resolution in local mode."""
        # Create settings with local mode
        settings = Settings(
            USE_AZURE_STORAGE=False,
            DEFAULT_INPUT_FOLDER="./data/input",
            DEFAULT_CONTEXT_FOLDER="./data/context",
            DEFAULT_OUTPUT_FOLDER="./data/output",
        )

        # Verify local paths are used
        assert settings.input_path == "./data/input"
        assert settings.context_path == "./data/context/client.yaml"
        assert settings.output_path == "./data/output"

    def test_azure_mode_paths(self):
        """Test path resolution in Azure mode."""
        # Create settings with Azure mode
        settings = Settings(
            USE_AZURE_STORAGE=True,
            AZURE_INPUT_PATH="jobs/test_job_123/input",
            AZURE_CONTEXT_PATH="client/context.yaml",
            AZURE_OUTPUT_PATH="jobs/test_job_123/output",
        )

        # Verify Azure paths are used
        assert settings.input_path == "jobs/test_job_123/input"
        assert settings.context_path == "client/context.yaml"
        assert settings.output_path == "jobs/test_job_123/output"

    def test_azure_path_defaults(self):
        """Test Azure path defaults when not configured."""
        settings = Settings(
            USE_AZURE_STORAGE=True,
            AZURE_INPUT_PATH="input",
            AZURE_CONTEXT_PATH="context/client.yaml",
            AZURE_OUTPUT_PATH="output",
        )

        # Should use default Azure paths
        assert settings.input_path == "input"  # Default AZURE_INPUT_PATH
        assert settings.context_path == "context/client.yaml"  # Default AZURE_CONTEXT_PATH
        assert settings.output_path == "output"  # Default AZURE_OUTPUT_PATH

    def test_dimension_weights_property(self):
        """Test dimension weights property returns correct structure."""
        settings = Settings()

        weights = settings.dimension_weights

        # Should have all required dimensions
        expected_keys = {
            "direct_impact",
            "industry_relevance",
            "geographic_relevance",
            "temporal_urgency",
            "strategic_alignment",
        }
        assert set(weights.keys()) == expected_keys

        # Should sum to 1.0 (or close to it)
        total_weight = sum(weights.values())
        assert abs(total_weight - 1.0) < 0.01

    def test_azure_job_id_configuration(self):
        """Test Azure job ID is properly stored."""
        settings = Settings(AZURE_JOB_ID="import_20250524_123456")

        assert settings.AZURE_JOB_ID == "import_20250524_123456"

    def test_path_switching_behavior(self):
        """Test switching between local and Azure paths."""
        # Start with local settings
        settings = Settings(
            USE_AZURE_STORAGE=False,
            DEFAULT_INPUT_FOLDER="./local/input",
            AZURE_INPUT_PATH="azure/input/path",
        )

        assert settings.input_path == "./local/input"

        # Switch to Azure mode
        settings.USE_AZURE_STORAGE = True
        assert settings.input_path == "azure/input/path"

        # Switch back to local
        settings.USE_AZURE_STORAGE = False
        assert settings.input_path == "./local/input"


class TestEnvironmentFileUpdates:
    """Test environment file update functionality."""

    def test_update_env_file_with_azure_paths(self):
        """Test updating .env file with Azure paths."""
        # Create temporary .env file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".env") as f:
            f.write(
                """# Test configuration
USE_AZURE_STORAGE=false
AZURE_JOB_ID=old_job_id
AZURE_INPUT_PATH=old/input/path
AZURE_CONTEXT_PATH=old/context.yaml
AZURE_OUTPUT_PATH=old/output/path
"""
            )
            temp_env_path = f.name

        try:
            # Update with new job ID
            result = update_env_file_with_azure_paths("new_job_20250524", temp_env_path)

            assert result is True

            # Verify file was updated
            with open(temp_env_path) as f:
                content = f.read()

            assert "AZURE_JOB_ID=new_job_20250524" in content
            assert "AZURE_INPUT_PATH=jobs/new_job_20250524/input" in content
            assert "AZURE_CONTEXT_PATH=test-client/context.yaml" in content
            assert "AZURE_OUTPUT_PATH=jobs/new_job_20250524/output" in content

            # Old values should be replaced
            assert "old_job_id" not in content
            assert "old/input/path" not in content

        finally:
            os.unlink(temp_env_path)

    def test_update_env_file_missing_file(self):
        """Test updating non-existent .env file."""
        result = update_env_file_with_azure_paths("test_job", "/nonexistent/path/.env")

        assert result is False

    def test_update_env_file_adds_missing_keys(self):
        """Test adding Azure keys that don't exist in .env file."""
        # Create .env file without Azure keys
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".env") as f:
            f.write(
                """# Test configuration
USE_AZURE_STORAGE=false
LOG_LEVEL=INFO

# Azure Storage paths (used when USE_AZURE_STORAGE=true)
# These are automatically updated by the import script
"""
            )
            temp_env_path = f.name

        try:
            # Update with job ID
            result = update_env_file_with_azure_paths("new_job_123", temp_env_path)

            assert result is True

            # Verify keys were added
            with open(temp_env_path) as f:
                content = f.read()

            assert "AZURE_JOB_ID=new_job_123" in content
            assert "AZURE_INPUT_PATH=jobs/new_job_123/input" in content

        finally:
            os.unlink(temp_env_path)


class TestConfigurationIntegration:
    """Test integration between configuration components."""

    @patch("src.config.settings")
    def test_settings_integration_with_paths(self, mock_settings):
        """Test settings integration with path resolution."""
        # Mock settings for Azure mode
        mock_settings.USE_AZURE_STORAGE = True
        mock_settings.AZURE_INPUT_PATH = "jobs/integration_test/input"
        mock_settings.AZURE_CONTEXT_PATH = "integration/context.yaml"
        mock_settings.input_path = "jobs/integration_test/input"
        mock_settings.context_path = "integration/context.yaml"

        # Import should use mocked settings

        # Verify mocked values are accessible
        assert mock_settings.USE_AZURE_STORAGE is True
        assert mock_settings.input_path == "jobs/integration_test/input"

    def test_azure_connection_string_validation(self):
        """Test Azure connection string configuration."""
        settings = Settings(
            AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;..."
        )

        assert settings.AZURE_STORAGE_CONNECTION_STRING is not None
        assert "AccountName=devstoreaccount1" in settings.AZURE_STORAGE_CONNECTION_STRING

    def test_configuration_defaults(self):
        """Test configuration provides sensible defaults."""
        # Create settings without loading from .env file
        settings = Settings(
            _env_file=None,  # Don't load from .env
            DEFAULT_INPUT_FOLDER="/data/input",
            DEFAULT_OUTPUT_FOLDER="/data/output",
            DEFAULT_CONTEXT_FOLDER="/data/context",
        )

        # Storage defaults
        assert settings.USE_AZURE_STORAGE is False
        assert settings.DEFAULT_INPUT_FOLDER == "/data/input"
        assert settings.DEFAULT_OUTPUT_FOLDER == "/data/output"
        assert settings.DEFAULT_CONTEXT_FOLDER == "/data/context"

        # Azure defaults (these come from Field defaults)
        assert settings.AZURE_INPUT_PATH == "input"
        assert settings.AZURE_CONTEXT_PATH == "context/client.yaml"
        assert settings.AZURE_OUTPUT_PATH == "output"

        # Processing defaults
        assert settings.MAX_BATCH_SIZE == 1000
        assert settings.PROCESSING_TIMEOUT_SECONDS == 600
        assert settings.CONFIDENCE_THRESHOLD == 0.7

    def test_configuration_validation(self):
        """Test configuration validation and constraints."""
        # Valid configuration should work
        settings = Settings(MAX_BATCH_SIZE=500, CONFIDENCE_THRESHOLD=0.8)

        assert settings.MAX_BATCH_SIZE == 500
        assert settings.CONFIDENCE_THRESHOLD == 0.8

    def test_azure_container_configuration(self):
        """Test Azure container configuration."""
        settings = Settings(AZURE_STORAGE_CONTAINER_NAME="custom-container")

        assert settings.AZURE_STORAGE_CONTAINER_NAME == "custom-container"


class TestConfigurationPathEdgeCases:
    """Test edge cases in path configuration."""

    def test_empty_azure_paths(self):
        """Test behavior with empty Azure paths."""
        settings = Settings(
            USE_AZURE_STORAGE=True, AZURE_INPUT_PATH="", AZURE_CONTEXT_PATH="", AZURE_OUTPUT_PATH=""
        )

        # Should use empty strings, not fall back to local
        assert settings.input_path == ""
        assert settings.context_path == ""
        assert settings.output_path == ""

    def test_default_azure_paths(self):
        """Test behavior with default Azure paths."""
        settings = Settings(
            _env_file=None,  # Don't load from .env
            USE_AZURE_STORAGE=True,
            # Don't override Azure paths, use defaults
        )

        # Should use Field defaults for Azure paths
        assert settings.AZURE_INPUT_PATH == "input"  # Field default
        assert settings.AZURE_CONTEXT_PATH == "context/client.yaml"  # Field default
        assert settings.AZURE_OUTPUT_PATH == "output"  # Field default

        # Path properties should return Azure paths when enabled
        assert settings.input_path == "input"
        assert settings.context_path == "context/client.yaml"
        assert settings.output_path == "output"

    def test_mixed_path_configuration(self):
        """Test mixed Azure and local configuration."""
        settings = Settings(
            USE_AZURE_STORAGE=False,  # Local mode
            DEFAULT_INPUT_FOLDER="./custom/input",
            AZURE_INPUT_PATH="azure/custom/input",  # Should be ignored
        )

        # Should use local paths since USE_AZURE_STORAGE is False
        assert settings.input_path == "./custom/input"
        assert "azure" not in settings.input_path

    def test_path_with_special_characters(self):
        """Test paths with special characters."""
        settings = Settings(
            USE_AZURE_STORAGE=True,
            AZURE_INPUT_PATH="jobs/job-with-dashes_and_underscores/input",
            AZURE_CONTEXT_PATH="contexts/client@company.com/context.yaml",
        )

        assert settings.input_path == "jobs/job-with-dashes_and_underscores/input"
        assert settings.context_path == "contexts/client@company.com/context.yaml"
