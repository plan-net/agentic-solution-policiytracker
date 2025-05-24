"""
Unit tests for Azure Storage integration components.

Tests cover:
- Azure Storage client functionality
- Batch loader with Azure Storage
- Content processor with Azure caching
- Document reader with Azure Storage
- Azure checkpoint saver
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import json
import tempfile
from pathlib import Path

from src.integrations.azure_storage import AzureStorageClient
from src.integrations.azure_checkpoint import AzureCheckpointSaver
from src.processors.batch_loader import BatchDocumentLoader
from src.processors.content_processor import ContentProcessor
from src.processors.document_reader import DocumentReader
from src.models.content import ProcessedContent, DocumentMetadata, DocumentType


class TestAzureStorageClient:
    """Test Azure Storage client functionality."""
    
    @pytest.fixture
    def azure_client(self, mock_azure_storage_client):
        """Get mocked Azure Storage client."""
        return mock_azure_storage_client
    
    @pytest.mark.asyncio
    async def test_upload_blob(self, azure_client):
        """Test blob upload functionality."""
        # Test data upload
        test_data = b"test blob content"
        result = await azure_client.upload_blob('test-container', 'test-blob.txt', test_data)
        
        assert result is True
        
        # Verify blob was stored
        downloaded = await azure_client.download_blob('test-container', 'test-blob.txt')
        assert downloaded == test_data
    
    @pytest.mark.asyncio
    async def test_upload_json(self, azure_client):
        """Test JSON upload functionality."""
        test_data = {"key": "value", "number": 42}
        result = await azure_client.upload_json('test-container', 'test-data.json', test_data)
        
        assert result is True
        
        # Verify JSON was stored correctly
        downloaded = await azure_client.download_json('test-container', 'test-data.json')
        assert downloaded == test_data
    
    @pytest.mark.asyncio
    async def test_list_blobs_with_prefix(self, azure_client):
        """Test blob listing with prefix filtering."""
        # Upload test blobs
        await azure_client.upload_blob('test-container', 'jobs/job1/input/doc1.txt', b"content1")
        await azure_client.upload_blob('test-container', 'jobs/job1/input/doc2.txt', b"content2")
        await azure_client.upload_blob('test-container', 'jobs/job2/input/doc3.txt', b"content3")
        
        # List blobs with prefix
        blobs = await azure_client.list_blobs('test-container', prefix='jobs/job1/')
        blob_names = [blob.name for blob in blobs]
        
        assert len(blob_names) == 2
        assert 'jobs/job1/input/doc1.txt' in blob_names
        assert 'jobs/job1/input/doc2.txt' in blob_names
        assert 'jobs/job2/input/doc3.txt' not in blob_names
    
    @pytest.mark.asyncio
    async def test_blob_properties(self, azure_client):
        """Test blob properties retrieval."""
        test_data = b"test content for properties"
        await azure_client.upload_blob('test-container', 'test-props.txt', test_data)
        
        properties = await azure_client.get_blob_properties('test-container', 'test-props.txt')
        
        assert properties is not None
        assert properties['size'] == len(test_data)
        assert 'last_modified' in properties
    
    @pytest.mark.asyncio
    async def test_delete_blob(self, azure_client):
        """Test blob deletion."""
        # Upload a blob
        await azure_client.upload_blob('test-container', 'to-delete.txt', b"will be deleted")
        
        # Verify it exists
        content = await azure_client.download_blob('test-container', 'to-delete.txt')
        assert content is not None
        
        # Delete it
        result = await azure_client.delete_blob('test-container', 'to-delete.txt')
        assert result is True
        
        # Verify it's gone
        content = await azure_client.download_blob('test-container', 'to-delete.txt')
        assert content is None


class TestBatchDocumentLoaderAzure:
    """Test BatchDocumentLoader with Azure Storage integration."""
    
    @pytest.mark.asyncio
    @patch('src.processors.batch_loader.AzureStorageClient')
    async def test_discover_files_azure(self, mock_azure_client_class, mock_azure_storage_client):
        """Test file discovery with Azure Storage."""
        # Setup mock
        mock_azure_client_class.return_value = mock_azure_storage_client
        
        # Setup mock blobs
        mock_blob1 = MagicMock()
        mock_blob1.name = "jobs/test_job/input/doc1.txt"
        mock_blob1.size = 1024
        
        mock_blob2 = MagicMock()
        mock_blob2.name = "jobs/test_job/input/doc2.md"
        mock_blob2.size = 2048
        
        mock_azure_storage_client.list_blobs.return_value = [mock_blob1, mock_blob2]
        
        # Create loader with Azure enabled
        loader = BatchDocumentLoader(use_azure=True)
        
        # Discover files
        files = await loader.discover_files("test_job", job_id="test_job")
        
        # Verify results
        assert len(files) == 2
        assert "jobs/test_job/input/doc1.txt" in files
        assert "jobs/test_job/input/doc2.md" in files
        
        # Verify Azure client was called correctly
        mock_azure_storage_client.list_blobs.assert_called_once_with('input-documents', prefix='jobs/test_job/input/')
    
    @pytest.mark.asyncio
    @patch('src.processors.batch_loader.AzureStorageClient')
    async def test_filter_by_size_azure(self, mock_azure_client_class, mock_azure_storage_client):
        """Test size filtering with Azure Storage."""
        # Setup mock
        mock_azure_client_class.return_value = mock_azure_storage_client
        
        # Mock blob properties
        async def mock_get_blob_properties(container_type, blob_name):
            sizes = {
                "small.txt": {"size": 1024},  # 1KB - should pass
                "large.txt": {"size": 100 * 1024 * 1024}  # 100MB - should be filtered
            }
            return sizes.get(blob_name.split('/')[-1])
        
        mock_azure_storage_client.get_blob_properties = mock_get_blob_properties
        
        # Create loader
        loader = BatchDocumentLoader(use_azure=True)
        
        # Test filtering
        blob_names = ["jobs/test/input/small.txt", "jobs/test/input/large.txt"]
        filtered = await loader.filter_by_size(blob_names, max_size_mb=50)
        
        # Should only keep the small file
        assert len(filtered) == 1
        assert "jobs/test/input/small.txt" in filtered
    
    @pytest.mark.asyncio
    @patch('src.processors.batch_loader.AzureStorageClient')
    async def test_get_file_stats_azure(self, mock_azure_client_class, mock_azure_storage_client):
        """Test file statistics with Azure Storage."""
        # Setup mock
        mock_azure_client_class.return_value = mock_azure_storage_client
        
        # Mock blob properties
        async def mock_get_blob_properties(container_type, blob_name):
            sizes = {
                "doc1.txt": {"size": 1024},
                "doc2.md": {"size": 2048},
                "doc3.pdf": {"size": 5 * 1024 * 1024}  # 5MB
            }
            filename = blob_name.split('/')[-1]
            return sizes.get(filename)
        
        mock_azure_storage_client.get_blob_properties = mock_get_blob_properties
        
        # Create loader
        loader = BatchDocumentLoader(use_azure=True)
        
        # Get stats
        blob_names = ["jobs/test/input/doc1.txt", "jobs/test/input/doc2.md", "jobs/test/input/doc3.pdf"]
        stats = await loader.get_file_stats(blob_names)
        
        # Verify stats
        assert stats["total_files"] == 3
        assert stats["total_size_mb"] > 5.0  # At least 5MB from doc3.pdf
        assert ".txt" in stats["by_extension"]
        assert ".md" in stats["by_extension"]
        assert ".pdf" in stats["by_extension"]
        assert stats["size_distribution"]["large"] >= 1  # doc3.pdf should be large


class TestContentProcessorAzure:
    """Test ContentProcessor with Azure Storage caching."""
    
    @pytest.fixture
    def sample_processed_content(self):
        """Create sample processed content for testing."""
        metadata = DocumentMetadata(
            source="test.txt",
            type=DocumentType.TXT,
            file_path="jobs/test/input/test.txt",
            file_size_bytes=1024
        )
        
        return ProcessedContent(
            id="test_doc",
            raw_text="Test document content",
            metadata=metadata,
            processing_timestamp=datetime.now(),
            word_count=3,
            language="en",
            sections=[],
            extraction_errors=[]
        )
    
    @pytest.mark.asyncio
    @patch('src.processors.content_processor.AzureStorageClient')
    async def test_cache_content_azure(self, mock_azure_client_class, mock_azure_storage_client, sample_processed_content):
        """Test content caching with Azure Storage."""
        # Setup mock
        mock_azure_client_class.return_value = mock_azure_storage_client
        mock_azure_storage_client.upload_json.return_value = True
        
        # Create processor with Azure
        processor = ContentProcessor(use_azure=True)
        
        # Cache content
        result = await processor._cache_content("test_file.txt", "test_doc", sample_processed_content, "test_job")
        
        assert result is True
        mock_azure_storage_client.upload_json.assert_called_once()
        
        # Verify the call arguments
        call_args = mock_azure_storage_client.upload_json.call_args
        assert call_args[0][0] == 'cache'  # container type
        assert call_args[0][1].startswith('processed/')  # blob name starts with processed/
        assert 'job_id' in call_args[1]['metadata']  # metadata contains job_id
    
    @pytest.mark.asyncio
    @patch('src.processors.content_processor.AzureStorageClient')
    async def test_get_cached_content_azure(self, mock_azure_client_class, mock_azure_storage_client, sample_processed_content):
        """Test cached content retrieval with Azure Storage."""
        # Setup mock
        mock_azure_client_class.return_value = mock_azure_storage_client
        
        # Mock cached data
        cached_data = sample_processed_content.dict()
        cached_data['processing_timestamp'] = cached_data['processing_timestamp'].isoformat()
        cached_data['metadata']['created_at'] = cached_data['metadata']['created_at'].isoformat()
        cached_data['metadata']['modified_at'] = cached_data['metadata']['modified_at'].isoformat()
        
        mock_azure_storage_client.download_json.return_value = cached_data
        
        # Create processor with Azure
        processor = ContentProcessor(use_azure=True)
        
        # Get cached content
        result = await processor._get_cached_content("test_file.txt", "test_doc")
        
        assert result is not None
        assert result.id == "test_doc"
        assert result.raw_text == "Test document content"
        mock_azure_storage_client.download_json.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.processors.content_processor.AzureStorageClient')
    async def test_clear_cache_azure(self, mock_azure_client_class, mock_azure_storage_client):
        """Test cache clearing with Azure Storage."""
        # Setup mock
        mock_azure_client_class.return_value = mock_azure_storage_client
        
        # Mock cached blobs
        mock_blob1 = MagicMock()
        mock_blob1.name = "processed/cache1.json"
        mock_blob2 = MagicMock()
        mock_blob2.name = "processed/cache2.json"
        
        mock_azure_storage_client.list_blobs.return_value = [mock_blob1, mock_blob2]
        mock_azure_storage_client.delete_blob.return_value = True
        
        # Create processor with Azure
        processor = ContentProcessor(use_azure=True)
        
        # Clear cache
        deleted_count = await processor.clear_cache()
        
        assert deleted_count == 2
        assert mock_azure_storage_client.delete_blob.call_count == 2


class TestDocumentReaderAzure:
    """Test DocumentReader with Azure Storage integration."""
    
    @pytest.mark.asyncio
    @patch('src.processors.document_reader.AzureStorageClient')
    async def test_read_document_azure_text(self, mock_azure_client_class):
        """Test reading text document from Azure Storage."""
        # Setup mock
        mock_client = AsyncMock()
        mock_azure_client_class.return_value = mock_client
        
        # Mock blob content
        test_content = b"This is test document content from Azure Storage."
        mock_client.download_blob.return_value = test_content
        
        # Mock blob properties
        mock_client.get_blob_properties.return_value = {
            "size": len(test_content),
            "last_modified": datetime.now(),
            "content_type": "text/plain"
        }
        
        # Create reader
        reader = DocumentReader()
        
        # Read document
        text, metadata = await reader._read_document_azure("jobs/test/input/test.txt")
        
        # Verify results
        assert text == test_content.decode('utf-8')
        assert metadata.source == "test.txt"
        assert metadata.type == DocumentType.TXT
        assert metadata.file_path == "jobs/test/input/test.txt"
        assert metadata.file_size_bytes == len(test_content)
    
    @pytest.mark.asyncio
    @patch('src.processors.document_reader.AzureStorageClient')
    @patch('tempfile.NamedTemporaryFile')
    async def test_read_document_azure_pdf(self, mock_tempfile, mock_azure_client_class):
        """Test reading PDF document from Azure Storage."""
        # Setup mock
        mock_client = AsyncMock()
        mock_azure_client_class.return_value = mock_client
        
        # Mock PDF content (simplified)
        pdf_content = b"Mock PDF content"
        mock_client.download_blob.return_value = pdf_content
        mock_client.get_blob_properties.return_value = {
            "size": len(pdf_content),
            "last_modified": datetime.now()
        }
        
        # Mock temporary file
        mock_temp_file = MagicMock()
        mock_temp_file.name = "/tmp/test.pdf"
        mock_temp_file.__enter__ = MagicMock(return_value=mock_temp_file)
        mock_temp_file.__exit__ = MagicMock(return_value=False)
        mock_tempfile.return_value = mock_temp_file
        
        # Mock PDF reading
        with patch('src.processors.document_reader.DocumentReader._read_pdf') as mock_read_pdf:
            mock_read_pdf.return_value = ("Extracted PDF text", {"pages": 1})
            
            # Create reader
            reader = DocumentReader()
            
            # Read document
            text, metadata = await reader._read_document_azure("jobs/test/input/test.pdf")
            
            # Verify results
            assert text == "Extracted PDF text"
            assert metadata.type == DocumentType.PDF
            mock_temp_file.write.assert_called_once_with(pdf_content)


class TestAzureCheckpointSaver:
    """Test Azure checkpoint saver for LangGraph."""
    
    @pytest.fixture
    def checkpoint_saver(self, mock_azure_storage_client):
        """Create checkpoint saver with mocked Azure client."""
        with patch('src.integrations.azure_checkpoint.AzureStorageClient') as mock_class:
            mock_class.return_value = mock_azure_storage_client
            return AzureCheckpointSaver()
    
    @pytest.mark.asyncio
    async def test_save_checkpoint(self, checkpoint_saver, mock_azure_storage_client):
        """Test checkpoint saving."""
        config = {"configurable": {"thread_id": "test_thread"}}
        checkpoint = {"state_key": "state_value", "step": 1}
        metadata = {"timestamp": datetime.now().isoformat()}
        new_versions = {"state": 1}
        
        mock_azure_storage_client.upload_json.return_value = True
        
        # Save checkpoint
        new_config = await checkpoint_saver.aput(config, checkpoint, metadata, new_versions)
        
        # Verify new config contains checkpoint ID
        assert "checkpoint_id" in new_config["configurable"]
        assert new_config["configurable"]["thread_id"] == "test_thread"
        
        # Verify Azure client was called
        mock_azure_storage_client.upload_json.assert_called_once()
        call_args = mock_azure_storage_client.upload_json.call_args
        assert call_args[0][0] == 'checkpoints'  # container type
        assert call_args[0][1].startswith('threads/test_thread/checkpoints/')  # blob path
    
    @pytest.mark.asyncio
    async def test_load_checkpoint(self, checkpoint_saver, mock_azure_storage_client):
        """Test checkpoint loading."""
        # Mock stored checkpoint data
        stored_data = {
            "checkpoint_id": "test_checkpoint",
            "thread_id": "test_thread",
            "checkpoint": {"state_key": "state_value"},
            "metadata": {"timestamp": "2024-01-01T00:00:00"},
            "parent_config": None
        }
        
        mock_azure_storage_client.download_json.return_value = stored_data
        
        # Mock latest checkpoint ID lookup
        mock_blob = MagicMock()
        mock_blob.name = "threads/test_thread/checkpoints/test_checkpoint.json"
        mock_blob.last_modified = datetime.now()
        mock_azure_storage_client.list_blobs.return_value = [mock_blob]
        
        config = {"configurable": {"thread_id": "test_thread"}}
        
        # Load checkpoint
        result = await checkpoint_saver.aget(config)
        
        assert result is not None
        checkpoint, metadata, parent_config = result
        assert checkpoint["state_key"] == "state_value"
        assert metadata["timestamp"] == "2024-01-01T00:00:00"
    
    @pytest.mark.asyncio
    async def test_cleanup_old_checkpoints(self, checkpoint_saver, mock_azure_storage_client):
        """Test cleanup of old checkpoints."""
        # Mock multiple checkpoints
        old_blob1 = MagicMock()
        old_blob1.name = "threads/test_thread/checkpoints/old1.json"
        old_blob1.last_modified = datetime(2024, 1, 1)
        
        old_blob2 = MagicMock()
        old_blob2.name = "threads/test_thread/checkpoints/old2.json"
        old_blob2.last_modified = datetime(2024, 1, 2)
        
        recent_blob = MagicMock()
        recent_blob.name = "threads/test_thread/checkpoints/recent.json"
        recent_blob.last_modified = datetime(2024, 1, 10)
        
        mock_azure_storage_client.list_blobs.return_value = [old_blob1, old_blob2, recent_blob]
        mock_azure_storage_client.delete_blob.return_value = True
        
        # Cleanup keeping only 1 checkpoint
        deleted_count = await checkpoint_saver.cleanup_old_checkpoints("test_thread", keep_last=1)
        
        # Should delete 2 old checkpoints
        assert deleted_count == 2
        assert mock_azure_storage_client.delete_blob.call_count == 2


class TestAzureSettingsIntegration:
    """Test configuration integration for Azure Storage."""
    
    def test_azure_settings_enabled(self, mock_azure_settings):
        """Test Azure Storage settings when enabled."""
        assert mock_azure_settings.USE_AZURE_STORAGE is True
        assert mock_azure_settings.AZURE_STORAGE_CONNECTION_STRING is not None
        assert mock_azure_settings.AZURE_STORAGE_ACCOUNT_NAME == "devstoreaccount1"
    
    def test_local_settings_disabled(self, local_settings):
        """Test settings when Azure Storage is disabled."""
        assert local_settings.USE_AZURE_STORAGE is False
        assert local_settings.AZURE_STORAGE_CONNECTION_STRING is None
        assert local_settings.DEFAULT_INPUT_FOLDER == "/tmp/test_input"


@pytest.mark.integration
class TestAzureIntegrationPatterns:
    """Test integration patterns between Azure components."""
    
    @pytest.mark.asyncio
    @patch('src.processors.batch_loader.AzureStorageClient')
    @patch('src.processors.content_processor.AzureStorageClient')
    async def test_full_azure_processing_pipeline(self, mock_content_azure, mock_batch_azure):
        """Test full processing pipeline with Azure Storage."""
        # Mock both Azure clients
        mock_batch_client = AsyncMock()
        mock_content_client = AsyncMock()
        mock_batch_azure.return_value = mock_batch_client
        mock_content_azure.return_value = mock_content_client
        
        # Mock document discovery
        mock_blob = MagicMock()
        mock_blob.name = "jobs/test/input/doc.txt"
        mock_blob.size = 1024
        mock_batch_client.list_blobs.return_value = [mock_blob]
        
        # Mock document download
        mock_batch_client.download_blob.return_value = b"Test document content"
        
        # Mock cache operations
        mock_content_client.download_json.return_value = None  # No cache hit
        mock_content_client.upload_json.return_value = True   # Cache save success
        
        # Create components
        loader = BatchDocumentLoader(use_azure=True)
        processor = ContentProcessor(use_azure=True)
        
        # Test pipeline
        files = await loader.discover_files("test", job_id="test")
        assert len(files) == 1
        
        # Verify Azure clients were used
        mock_batch_client.list_blobs.assert_called_once()
        
        # Note: Full document processing would require more mocking
        # This test demonstrates the integration pattern
    
    @pytest.mark.asyncio
    async def test_azure_error_handling_patterns(self, mock_azure_storage_client):
        """Test error handling patterns in Azure integration."""
        # Mock Azure client to raise exceptions
        mock_azure_storage_client.download_blob.side_effect = Exception("Azure connection failed")
        
        # Test that components handle Azure errors gracefully
        loader = BatchDocumentLoader(use_azure=True)
        
        # Should handle exceptions and provide meaningful error messages
        with pytest.raises(Exception) as exc_info:
            await loader._discover_files_azure("nonexistent", "test_job")
        
        assert "Azure Storage file discovery failed" in str(exc_info.value)