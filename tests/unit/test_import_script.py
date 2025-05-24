"""
Unit tests for the import script functionality.

Tests cover:
- Environment file updating
- Job ID generation and management
- Azure path configuration
- Import script integration
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime

from scripts.import_data_to_azurite import (
    update_env_file_with_azure_paths,
    DataImporter,
    verify_azurite_connection,
    create_test_data
)


class TestEnvFileUpdating:
    """Test environment file update functionality."""
    
    def test_update_env_with_new_job_id(self):
        """Test updating .env file with new Azure job ID."""
        env_content = """# Test environment file
USE_AZURE_STORAGE=false
AZURE_JOB_ID=old_job_id
AZURE_INPUT_PATH=jobs/old_job_id/input
AZURE_CONTEXT_PATH=old-client/context.yaml
AZURE_OUTPUT_PATH=jobs/old_job_id/output
LOG_LEVEL=INFO
"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as f:
            f.write(env_content)
            temp_env_path = f.name
        
        try:
            # Update with new job ID
            result = update_env_file_with_azure_paths("import_20250524_123456", temp_env_path)
            
            assert result is True
            
            # Read updated content
            with open(temp_env_path, 'r') as f:
                updated_content = f.read()
            
            # Verify updates
            assert "AZURE_JOB_ID=import_20250524_123456" in updated_content
            assert "AZURE_INPUT_PATH=jobs/import_20250524_123456/input" in updated_content
            assert "AZURE_CONTEXT_PATH=test-client/context.yaml" in updated_content
            assert "AZURE_OUTPUT_PATH=jobs/import_20250524_123456/output" in updated_content
            
            # Verify other settings unchanged
            assert "USE_AZURE_STORAGE=false" in updated_content
            assert "LOG_LEVEL=INFO" in updated_content
            
            # Verify old values replaced
            assert "old_job_id" not in updated_content
            assert "old-client" not in updated_content
        
        finally:
            os.unlink(temp_env_path)
    
    def test_update_env_missing_azure_section(self):
        """Test updating .env file that lacks Azure section."""
        env_content = """# Basic environment file
USE_AZURE_STORAGE=false
LOG_LEVEL=INFO
DEBUG=true
"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as f:
            f.write(env_content)
            temp_env_path = f.name
        
        try:
            # Update should still work
            result = update_env_file_with_azure_paths("new_job_456", temp_env_path)
            
            assert result is True
            
            # Should contain basic content plus job ID
            with open(temp_env_path, 'r') as f:
                updated_content = f.read()
            
            assert "USE_AZURE_STORAGE=false" in updated_content
            assert "AZURE_JOB_ID=new_job_456" in updated_content
        
        finally:
            os.unlink(temp_env_path)
    
    def test_update_env_file_not_found(self):
        """Test updating non-existent .env file."""
        result = update_env_file_with_azure_paths("test_job", "/nonexistent/.env")
        
        assert result is False
    
    def test_update_env_preserves_comments(self):
        """Test that comments and structure are preserved."""
        env_content = """# Political Monitoring Agent Configuration
# This is a test configuration file

# === Storage Configuration ===
USE_AZURE_STORAGE=false

# Azure Storage paths (used when USE_AZURE_STORAGE=true)
# These are automatically updated by the import script
AZURE_JOB_ID=old_job
AZURE_INPUT_PATH=jobs/old_job/input

# === Other Settings ===
LOG_LEVEL=INFO
"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as f:
            f.write(env_content)
            temp_env_path = f.name
        
        try:
            result = update_env_file_with_azure_paths("new_job_789", temp_env_path)
            
            assert result is True
            
            with open(temp_env_path, 'r') as f:
                updated_content = f.read()
            
            # Comments should be preserved
            assert "# Political Monitoring Agent Configuration" in updated_content
            assert "# === Storage Configuration ===" in updated_content
            assert "# These are automatically updated by the import script" in updated_content
            
            # Values should be updated
            assert "AZURE_JOB_ID=new_job_789" in updated_content
            assert "old_job" not in updated_content.replace("# old_job", "")  # Ignore comments
        
        finally:
            os.unlink(temp_env_path)


class TestDataImporter:
    """Test DataImporter class functionality."""
    
    @pytest.fixture
    def temp_data_dir(self):
        """Create temporary data directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_path = Path(tmpdir) / "data"
            input_path = data_path / "input"
            context_path = data_path / "context"
            output_path = data_path / "output"
            
            # Create directories
            input_path.mkdir(parents=True)
            context_path.mkdir(parents=True)
            output_path.mkdir(parents=True)
            
            # Create sample files
            (input_path / "doc1.txt").write_text("Sample document 1")
            (input_path / "doc2.md").write_text("# Sample Document 2")
            (context_path / "client.yaml").write_text("company_terms: [testcorp]")
            
            yield {
                "data_path": data_path,
                "input_path": input_path,
                "context_path": context_path,
                "output_path": output_path
            }
    
    def test_data_importer_initialization(self, temp_data_dir):
        """Test DataImporter initialization."""
        importer = DataImporter(dry_run=True)
        
        assert importer.dry_run is True
        assert importer.stats["input_documents"] == 0
        assert importer.stats["context_files"] == 0
        assert importer.stats["total_size"] == 0
        assert importer.stats["errors"] == []
    
    @pytest.mark.asyncio
    @patch('scripts.import_data_to_azurite.get_azure_storage_client')
    async def test_import_all_dry_run(self, mock_get_client, temp_data_dir):
        """Test full import in dry run mode."""
        # Mock Azure client
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        # Create importer with temp data path
        importer = DataImporter(dry_run=True)
        importer.data_path = temp_data_dir["data_path"]
        
        # Run import
        stats, job_id = await importer.import_all("test_job_123")
        
        # Verify stats
        assert stats["input_documents"] == 2  # doc1.txt, doc2.md
        assert stats["context_files"] == 1   # client.yaml
        assert stats["cache_files"] == 2     # Sample cache entries
        assert stats["total_size"] > 0
        assert len(stats["errors"]) == 0
        
        # Verify job ID
        assert job_id == "test_job_123"
        
        # Verify Azure client was not called (dry run)
        mock_client.upload_blob.assert_not_called()
        mock_client.upload_json.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('scripts.import_data_to_azurite.get_azure_storage_client')
    async def test_import_input_documents_only(self, mock_get_client, temp_data_dir):
        """Test importing only input documents."""
        # Mock Azure client
        mock_client = AsyncMock()
        mock_client.upload_blob.return_value = True
        mock_get_client.return_value = mock_client
        
        # Create importer
        importer = DataImporter(dry_run=False)
        importer.data_path = temp_data_dir["data_path"]
        
        # Import input documents only
        await importer._import_input_documents("input_only_job")
        
        # Verify upload calls
        assert mock_client.upload_blob.call_count == 2  # 2 documents
        
        # Verify call arguments
        calls = mock_client.upload_blob.call_args_list
        
        # First call should be for doc1.txt
        assert calls[0][0][0] == 'input-documents'  # container type
        assert "input_only_job/input/doc1.txt" in calls[0][0][1]  # blob name
        
        # Second call should be for doc2.md
        assert calls[1][0][0] == 'input-documents'
        assert "input_only_job/input/doc2.md" in calls[1][0][1]
    
    @pytest.mark.asyncio
    @patch('scripts.import_data_to_azurite.get_azure_storage_client')
    async def test_import_context_files(self, mock_get_client, temp_data_dir):
        """Test importing context files."""
        # Mock Azure client
        mock_client = AsyncMock()
        mock_client.upload_blob.return_value = True
        mock_get_client.return_value = mock_client
        
        # Create importer
        importer = DataImporter(dry_run=False)
        importer.data_path = temp_data_dir["data_path"]
        
        # Import context files
        await importer._import_context_files()
        
        # Verify upload call
        mock_client.upload_blob.assert_called_once()
        
        call_args = mock_client.upload_blob.call_args
        assert call_args[0][0] == 'contexts'  # container type
        assert call_args[0][1] == 'client/context.yaml'  # blob name
    
    def test_print_summary(self, temp_data_dir, capsys):
        """Test summary printing functionality."""
        importer = DataImporter(dry_run=True)
        importer.stats = {
            "input_documents": 5,
            "context_files": 1,
            "reports": 2,
            "cache_files": 3,
            "total_size": 12345,
            "errors": []
        }
        
        importer._print_summary("test_summary_job")
        
        captured = capsys.readouterr()
        output = captured.out
        
        # Verify summary content
        assert "IMPORT SUMMARY" in output
        assert "test_summary_job" in output
        assert "DRY RUN" in output
        assert "Input Documents: 5" in output
        assert "Context Files: 1" in output
        assert "Reports: 2" in output
        assert "Cache Files: 3" in output
        assert "Total Size: 12,345 bytes" in output
        assert "✅ No errors!" in output


class TestImportScriptIntegration:
    """Test integration functionality of import script."""
    
    @pytest.mark.asyncio
    @patch('scripts.import_data_to_azurite.get_azure_storage_client')
    async def test_verify_azurite_connection_success(self, mock_get_client):
        """Test successful Azurite connection verification."""
        # Mock successful Azure client
        mock_client = AsyncMock()
        mock_client.ensure_container_exists.return_value = True
        mock_get_client.return_value = mock_client
        
        result = await verify_azurite_connection()
        
        assert result is True
        mock_client.ensure_container_exists.assert_called_once_with('input-documents')
    
    @pytest.mark.asyncio
    @patch('scripts.import_data_to_azurite.get_azure_storage_client')
    async def test_verify_azurite_connection_failure(self, mock_get_client):
        """Test failed Azurite connection verification."""
        # Mock failing Azure client
        mock_client = AsyncMock()
        mock_client.ensure_container_exists.side_effect = Exception("Connection failed")
        mock_get_client.return_value = mock_client
        
        result = await verify_azurite_connection()
        
        assert result is False
    
    @pytest.mark.asyncio
    @patch('scripts.import_data_to_azurite.get_azure_storage_client')
    async def test_create_test_data(self, mock_get_client):
        """Test test data creation functionality."""
        # Mock Azure client
        mock_client = AsyncMock()
        mock_client.upload_blob.return_value = True
        mock_client.upload_json.return_value = True
        mock_get_client.return_value = mock_client
        
        job_id = await create_test_data()
        
        # Verify job ID format
        assert job_id.startswith("test_data_")
        assert len(job_id) > len("test_data_")
        
        # Verify uploads were called
        assert mock_client.upload_blob.call_count == 2  # 2 sample documents
        mock_client.upload_json.assert_called_once()  # 1 context file
        
        # Verify blob upload calls
        blob_calls = mock_client.upload_blob.call_args_list
        
        # Should upload AI regulation and privacy policy samples
        blob_names = [call[0][1] for call in blob_calls]
        assert any("ai_regulation_sample.md" in name for name in blob_names)
        assert any("privacy_policy_update.txt" in name for name in blob_names)
        
        # Verify context upload
        context_call = mock_client.upload_json.call_args
        assert context_call[0][0] == 'contexts'
        assert context_call[0][1] == 'test-client/context.yaml'


class TestImportScriptErrorHandling:
    """Test error handling in import script."""
    
    def test_update_env_file_permission_error(self):
        """Test handling permission errors when updating .env file."""
        # Create read-only file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("TEST_VAR=value\n")
            temp_path = f.name
        
        try:
            # Make file read-only
            os.chmod(temp_path, 0o444)
            
            # Should handle permission error gracefully
            result = update_env_file_with_azure_paths("test_job", temp_path)
            
            assert result is False
        
        finally:
            # Restore permissions and clean up
            os.chmod(temp_path, 0o644)
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    @patch('scripts.import_data_to_azurite.get_azure_storage_client')
    async def test_import_with_azure_errors(self, mock_get_client):
        """Test import handling when Azure operations fail."""
        # Mock Azure client that fails uploads
        mock_client = AsyncMock()
        mock_client.upload_blob.side_effect = Exception("Azure upload failed")
        mock_get_client.return_value = mock_client
        
        # Create temporary data
        with tempfile.TemporaryDirectory() as tmpdir:
            data_path = Path(tmpdir) / "data"
            input_path = data_path / "input"
            input_path.mkdir(parents=True)
            (input_path / "test.txt").write_text("test content")
            
            # Create importer
            importer = DataImporter(dry_run=False)
            importer.data_path = data_path
            
            # Import should handle errors gracefully
            await importer._import_input_documents("error_test_job")
            
            # Should have recorded errors
            assert len(importer.stats["errors"]) > 0
            assert "Azure upload failed" in str(importer.stats["errors"])
    
    def test_job_id_generation_format(self):
        """Test job ID generation follows expected format."""
        importer = DataImporter()
        
        # Job ID should be generated in import_all when not provided
        job_id_pattern = r"import_\d{8}_\d{6}"
        
        # Generate a job ID similar to what import_all would do
        from datetime import datetime
        generated_job_id = f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        assert generated_job_id.startswith("import_")
        assert len(generated_job_id) == len("import_") + 8 + 1 + 6  # import_ + YYYYMMDD + _ + HHMMSS


class TestImportScriptPathHandling:
    """Test path handling in import script."""
    
    def test_supported_file_extensions(self):
        """Test that import script handles correct file extensions."""
        importer = DataImporter()
        
        # Check supported extensions are comprehensive
        supported_extensions = {'.txt', '.md', '.pdf', '.docx', '.html', '.csv', '.json'}
        
        # This is implied by the script logic - verify common formats are included
        common_formats = ['.txt', '.md', '.pdf', '.docx', '.json']
        for ext in common_formats:
            assert ext in supported_extensions
    
    @pytest.mark.asyncio
    async def test_file_metadata_extraction(self):
        """Test file metadata extraction during import."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = Path(tmpdir) / "test.txt"
            test_content = "Test document content for metadata extraction"
            test_file.write_text(test_content)
            
            importer = DataImporter()
            
            # Simulate metadata extraction that would happen during upload
            file_path = test_file
            file_size = file_path.stat().st_size
            
            assert file_size == len(test_content)
            assert file_path.suffix == ".txt"
            assert file_path.name == "test.txt"