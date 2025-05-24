"""
Azure Storage Client for Political Monitoring Agent.
Provides unified interface for Azure Blob Storage operations.
"""

import asyncio
import json
import os
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Union, BinaryIO

import structlog
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.storage.blob.aio import BlobServiceClient as AsyncBlobServiceClient

from src.config import settings

logger = structlog.get_logger()


class AzureStorageClient:
    """Azure Blob Storage client with async support and local development fallback."""
    
    def __init__(self):
        """Initialize Azure Storage client."""
        self.connection_string = getattr(settings, 'AZURE_STORAGE_CONNECTION_STRING', None)
        self.container_name = getattr(settings, 'AZURE_STORAGE_CONTAINER_NAME', 'default-container')
        
        # Initialize both sync and async clients if connection string is available
        if self.connection_string:
            try:
                self.blob_service = BlobServiceClient.from_connection_string(self.connection_string)
            except Exception as e:
                logger.warning(f"Failed to initialize Azure Storage client: {e}")
                self.blob_service = None
        else:
            self.blob_service = None
        self.async_blob_service = None  # Will be initialized when needed
        
        # Container mappings for different data types
        self.containers = {
            'input-documents': 'input-documents',
            'reports': 'reports', 
            'checkpoints': 'checkpoints',
            'contexts': 'contexts',
            'cache': 'cache',
            'job-artifacts': 'job-artifacts',
            'default': self.container_name
        }
        
        logger.info("Azure Storage client initialized", 
                   account_name=settings.AZURE_STORAGE_ACCOUNT_NAME)
    
    async def _get_async_client(self) -> AsyncBlobServiceClient:
        """Get async blob service client (lazy initialization)."""
        if self.async_blob_service is None:
            self.async_blob_service = AsyncBlobServiceClient.from_connection_string(
                self.connection_string
            )
        return self.async_blob_service
    
    def _get_container_name(self, container_type: str) -> str:
        """Get container name for a specific data type."""
        return self.containers.get(container_type, self.containers['default'])
    
    async def ensure_container_exists(self, container_type: str) -> bool:
        """Ensure container exists, create if not."""
        try:
            container_name = self._get_container_name(container_type)
            container_client = self.blob_service.get_container_client(container_name)
            
            # Try to get container properties (will raise if doesn't exist)
            container_client.get_container_properties()
            return True
            
        except ResourceNotFoundError:
            try:
                container_client.create_container()
                logger.info("Created container", container_name=container_name)
                return True
            except ResourceExistsError:
                # Container was created by another process
                return True
            except Exception as e:
                logger.error("Failed to create container", 
                           container_name=container_name, error=str(e))
                return False
    
    async def upload_blob(self, 
                         container_type: str, 
                         blob_name: str, 
                         data: Union[str, bytes, BinaryIO], 
                         metadata: Optional[Dict[str, str]] = None,
                         overwrite: bool = True) -> bool:
        """Upload data to Azure Blob Storage."""
        try:
            await self.ensure_container_exists(container_type)
            container_name = self._get_container_name(container_type)
            
            blob_client = self.blob_service.get_blob_client(
                container=container_name, 
                blob=blob_name
            )
            
            # Add default metadata
            upload_metadata = {
                'uploaded_at': datetime.utcnow().isoformat(),
                'source': 'political-monitoring-agent'
            }
            if metadata:
                upload_metadata.update(metadata)
            
            blob_client.upload_blob(
                data, 
                overwrite=overwrite,
                metadata=upload_metadata
            )
            
            logger.info("Uploaded blob", 
                       container=container_name, 
                       blob_name=blob_name,
                       size=len(data) if isinstance(data, (str, bytes)) else "stream")
            return True
            
        except Exception as e:
            logger.error("Failed to upload blob", 
                        container_type=container_type,
                        blob_name=blob_name, 
                        error=str(e))
            return False
    
    async def download_blob(self, container_type: str, blob_name: str) -> Optional[bytes]:
        """Download data from Azure Blob Storage."""
        try:
            container_name = self._get_container_name(container_type)
            blob_client = self.blob_service.get_blob_client(
                container=container_name, 
                blob=blob_name
            )
            
            data = blob_client.download_blob().readall()
            logger.debug("Downloaded blob", 
                        container=container_name, 
                        blob_name=blob_name,
                        size=len(data))
            return data
            
        except ResourceNotFoundError:
            logger.warning("Blob not found", 
                          container_type=container_type,
                          blob_name=blob_name)
            return None
        except Exception as e:
            logger.error("Failed to download blob", 
                        container_type=container_type,
                        blob_name=blob_name, 
                        error=str(e))
            return None
    
    async def download_blob_text(self, container_type: str, blob_name: str, encoding: str = 'utf-8') -> Optional[str]:
        """Download blob as text."""
        data = await self.download_blob(container_type, blob_name)
        if data:
            return data.decode(encoding)
        return None
    
    async def upload_json(self, container_type: str, blob_name: str, data: Dict, **kwargs) -> bool:
        """Upload JSON data to blob storage."""
        json_str = json.dumps(data, indent=2, default=str)
        return await self.upload_blob(container_type, blob_name, json_str.encode('utf-8'), **kwargs)
    
    async def download_json(self, container_type: str, blob_name: str) -> Optional[Dict]:
        """Download and parse JSON from blob storage."""
        text = await self.download_blob_text(container_type, blob_name)
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError as e:
                logger.error("Failed to parse JSON", blob_name=blob_name, error=str(e))
        return None
    
    async def list_blobs(self, container_type: str, prefix: str = "") -> List[str]:
        """List blobs in container with optional prefix filter."""
        try:
            container_name = self._get_container_name(container_type)
            container_client = self.blob_service.get_container_client(container_name)
            
            blob_names = []
            for blob in container_client.list_blobs(name_starts_with=prefix):
                blob_names.append(blob.name)
            
            logger.debug("Listed blobs", 
                        container=container_name, 
                        prefix=prefix,
                        count=len(blob_names))
            return blob_names
            
        except Exception as e:
            logger.error("Failed to list blobs", 
                        container_type=container_type,
                        prefix=prefix, 
                        error=str(e))
            return []
    
    async def delete_blob(self, container_type: str, blob_name: str) -> bool:
        """Delete blob from storage."""
        try:
            container_name = self._get_container_name(container_type)
            blob_client = self.blob_service.get_blob_client(
                container=container_name, 
                blob=blob_name
            )
            
            blob_client.delete_blob()
            logger.info("Deleted blob", 
                       container=container_name, 
                       blob_name=blob_name)
            return True
            
        except ResourceNotFoundError:
            logger.warning("Blob not found for deletion", 
                          container_type=container_type,
                          blob_name=blob_name)
            return True  # Already deleted
        except Exception as e:
            logger.error("Failed to delete blob", 
                        container_type=container_type,
                        blob_name=blob_name, 
                        error=str(e))
            return False
    
    async def blob_exists(self, container_type: str, blob_name: str) -> bool:
        """Check if blob exists."""
        try:
            container_name = self._get_container_name(container_type)
            blob_client = self.blob_service.get_blob_client(
                container=container_name, 
                blob=blob_name
            )
            
            blob_client.get_blob_properties()
            return True
            
        except ResourceNotFoundError:
            return False
        except Exception as e:
            logger.error("Failed to check blob existence", 
                        container_type=container_type,
                        blob_name=blob_name, 
                        error=str(e))
            return False
    
    async def get_blob_url(self, container_type: str, blob_name: str) -> str:
        """Get blob URL for direct access."""
        container_name = self._get_container_name(container_type)
        blob_client = self.blob_service.get_blob_client(
            container=container_name, 
            blob=blob_name
        )
        return blob_client.url
    
    async def upload_file(self, container_type: str, blob_name: str, file_path: str, **kwargs) -> bool:
        """Upload file from local filesystem to blob storage."""
        try:
            with open(file_path, 'rb') as file_data:
                return await self.upload_blob(container_type, blob_name, file_data, **kwargs)
        except FileNotFoundError:
            logger.error("Local file not found", file_path=file_path)
            return False
        except Exception as e:
            logger.error("Failed to upload file", 
                        file_path=file_path,
                        blob_name=blob_name, 
                        error=str(e))
            return False
    
    async def download_to_file(self, container_type: str, blob_name: str, file_path: str) -> bool:
        """Download blob to local file."""
        try:
            data = await self.download_blob(container_type, blob_name)
            if data:
                # Ensure directory exists
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                with open(file_path, 'wb') as f:
                    f.write(data)
                
                logger.info("Downloaded blob to file", 
                           blob_name=blob_name,
                           file_path=file_path)
                return True
            return False
            
        except Exception as e:
            logger.error("Failed to download to file", 
                        blob_name=blob_name,
                        file_path=file_path, 
                        error=str(e))
            return False
    
    async def cleanup_old_blobs(self, container_type: str, prefix: str, max_age_days: int = 7) -> int:
        """Clean up old blobs based on age."""
        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
            
            container_name = self._get_container_name(container_type)
            container_client = self.blob_service.get_container_client(container_name)
            
            deleted_count = 0
            for blob in container_client.list_blobs(name_starts_with=prefix):
                if blob.last_modified and blob.last_modified.replace(tzinfo=None) < cutoff_date:
                    if await self.delete_blob(container_type, blob.name):
                        deleted_count += 1
            
            logger.info("Cleaned up old blobs", 
                       container=container_name,
                       prefix=prefix,
                       deleted_count=deleted_count)
            return deleted_count
            
        except Exception as e:
            logger.error("Failed to cleanup old blobs", 
                        container_type=container_type,
                        prefix=prefix, 
                        error=str(e))
            return 0


# Global client instance - lazily initialized
_azure_storage_client = None

def get_azure_storage_client() -> AzureStorageClient:
    """Get or create global Azure storage client instance."""
    global _azure_storage_client
    if _azure_storage_client is None:
        _azure_storage_client = AzureStorageClient()
    return _azure_storage_client


# Convenience functions for common operations
async def upload_document(job_id: str, filename: str, content: Union[str, bytes]) -> bool:
    """Upload document for processing."""
    blob_name = f"jobs/{job_id}/input/{filename}"
    return await get_azure_storage_client().upload_blob('input-documents', blob_name, content)


async def save_report(job_id: str, report_name: str, content: str, format_type: str = 'markdown') -> bool:
    """Save generated report."""
    blob_name = f"jobs/{job_id}/{report_name}.{format_type}"
    metadata = {'job_id': job_id, 'format': format_type}
    return await get_azure_storage_client().upload_blob('reports', blob_name, content.encode('utf-8'), metadata)


async def load_context(context_id: str) -> Optional[Dict]:
    """Load client context configuration."""
    blob_name = f"{context_id}/context.yaml"
    return await get_azure_storage_client().download_json('contexts', blob_name)


async def cache_processed_content(doc_hash: str, content: Dict) -> bool:
    """Cache processed document content."""
    blob_name = f"processed/{doc_hash}.json"
    return await get_azure_storage_client().upload_json('cache', blob_name, content)


async def get_cached_content(doc_hash: str) -> Optional[Dict]:
    """Retrieve cached processed content."""
    blob_name = f"processed/{doc_hash}.json"
    return await get_azure_storage_client().download_json('cache', blob_name)