import os
from pathlib import Path
from typing import Optional

import structlog

from src.integrations.azure_storage import AzureStorageClient
from src.utils.exceptions import BatchProcessingError
from src.utils.validators import (
    get_supported_extensions,
    validate_directory_exists,
    validate_file_extension,
)

logger = structlog.get_logger()


class BatchDocumentLoader:
    """Load and discover documents from filesystem or Azure Storage."""

    def __init__(self, use_azure: bool = False):
        self.supported_extensions = get_supported_extensions()
        self.use_azure = use_azure
        self.azure_client = AzureStorageClient() if use_azure else None

    async def discover_files(self, input_source: str, job_id: Optional[str] = None) -> list[str]:
        """Discover all supported files from input source (folder or Azure Storage job)."""
        if self.use_azure:
            return await self._discover_files_azure(input_source, job_id)
        else:
            return await self._discover_files_local(input_source)

    async def _discover_files_local(self, input_folder: str) -> list[str]:
        """Discover all supported files in local input folder."""
        try:
            logger.info("Discovering local files", input_folder=input_folder)

            # Validate directory
            if not validate_directory_exists(input_folder):
                raise BatchProcessingError(0, 0, f"Input directory not accessible: {input_folder}")

            discovered_files = []

            # Walk through directory tree
            for root, dirs, files in os.walk(input_folder):
                for file in files:
                    file_path = os.path.join(root, file)

                    # Skip hidden files and system files
                    if file.startswith(".") or file.startswith("~"):
                        continue

                    # Check if file has supported extension
                    if validate_file_extension(file_path, self.supported_extensions):
                        # Check if file is readable
                        if os.access(file_path, os.R_OK):
                            discovered_files.append(file_path)
                        else:
                            logger.warning("File not readable", file_path=file_path)

            # Sort files by size (smaller first for faster processing)
            file_info = []
            for file_path in discovered_files:
                try:
                    size = os.path.getsize(file_path)
                    file_info.append((file_path, size))
                except OSError:
                    logger.warning("Could not get file size", file_path=file_path)
                    # Add with default size
                    file_info.append((file_path, 0))

            # Sort by size
            file_info.sort(key=lambda x: x[1])
            sorted_files = [file_path for file_path, _ in file_info]

            logger.info(
                f"Discovered {len(sorted_files)} local files",
                input_folder=input_folder,
                file_count=len(sorted_files),
            )

            return sorted_files

        except BatchProcessingError:
            raise
        except Exception as e:
            raise BatchProcessingError(0, 0, f"Local file discovery failed: {str(e)}")

    async def _discover_files_azure(
        self, job_prefix: str, job_id: Optional[str] = None
    ) -> list[str]:
        """Discover all supported files in Azure Storage for a job."""
        try:
            logger.info("Discovering Azure Storage files", job_prefix=job_prefix, job_id=job_id)

            if not self.azure_client:
                raise BatchProcessingError(0, 0, "Azure Storage client not initialized")

            # Construct blob prefix for job documents
            if job_id:
                blob_prefix = f"jobs/{job_id}/input/"
            else:
                blob_prefix = (
                    f"jobs/{job_prefix}/input/"
                    if not job_prefix.startswith("jobs/")
                    else job_prefix
                )

            # List blobs with the job prefix
            blobs = await self.azure_client.list_blobs("input-documents", prefix=blob_prefix)

            discovered_files = []
            file_info = []

            for blob_name in blobs:
                # Skip directories (blobs ending with /)
                if blob_name.endswith("/"):
                    continue

                # Get file extension
                blob_path = Path(blob_name)
                if blob_path.suffix.lower() in self.supported_extensions:
                    discovered_files.append(blob_name)
                    # Add with default size (we don't have size info from list_blobs)
                    file_info.append((blob_name, 0))

            # Sort by size (smaller first for faster processing)
            file_info.sort(key=lambda x: x[1])
            sorted_files = [file_path for file_path, _ in file_info]

            logger.info(
                f"Discovered {len(sorted_files)} Azure Storage files",
                job_prefix=job_prefix,
                file_count=len(sorted_files),
            )

            return sorted_files

        except Exception as e:
            raise BatchProcessingError(0, 0, f"Azure Storage file discovery failed: {str(e)}")

    async def filter_by_size(self, file_paths: list[str], max_size_mb: int) -> list[str]:
        """Filter files by maximum size."""
        if self.use_azure:
            return await self._filter_by_size_azure(file_paths, max_size_mb)
        else:
            return self._filter_by_size_local(file_paths, max_size_mb)

    def _filter_by_size_local(self, file_paths: list[str], max_size_mb: int) -> list[str]:
        """Filter local files by maximum size."""
        filtered_files = []

        for file_path in file_paths:
            try:
                size_bytes = os.path.getsize(file_path)
                size_mb = size_bytes / (1024 * 1024)

                if size_mb <= max_size_mb:
                    filtered_files.append(file_path)
                else:
                    logger.warning(
                        "File too large, skipping",
                        file_path=file_path,
                        size_mb=round(size_mb, 2),
                        max_size_mb=max_size_mb,
                    )

            except OSError:
                logger.warning("Could not check file size", file_path=file_path)
                # Skip files we can't read
                continue

        return filtered_files

    async def _filter_by_size_azure(self, blob_names: list[str], max_size_mb: int) -> list[str]:
        """Filter Azure Storage blobs by maximum size."""
        filtered_files = []

        if not self.azure_client:
            return blob_names

        for blob_name in blob_names:
            try:
                # Get blob properties to check size
                blob_properties = await self.azure_client.get_blob_properties(
                    "input-documents", blob_name
                )
                if blob_properties:
                    size_bytes = blob_properties.get("size", 0)
                    size_mb = size_bytes / (1024 * 1024)

                    if size_mb <= max_size_mb:
                        filtered_files.append(blob_name)
                    else:
                        logger.warning(
                            "Blob too large, skipping",
                            blob_name=blob_name,
                            size_mb=round(size_mb, 2),
                            max_size_mb=max_size_mb,
                        )
                else:
                    # If we can't get size, include it
                    filtered_files.append(blob_name)

            except Exception as e:
                logger.warning("Could not check blob size", blob_name=blob_name, error=str(e))
                # Skip blobs we can't read
                continue

        return filtered_files

    async def get_file_stats(self, file_paths: list[str]) -> dict:
        """Get statistics about discovered files."""
        if self.use_azure:
            return await self._get_file_stats_azure(file_paths)
        else:
            return self._get_file_stats_local(file_paths)

    def _get_file_stats_local(self, file_paths: list[str]) -> dict:
        """Get statistics about local files."""
        stats = {
            "total_files": len(file_paths),
            "total_size_mb": 0.0,
            "by_extension": {},
            "size_distribution": {"small": 0, "medium": 0, "large": 0},
        }

        for file_path in file_paths:
            try:
                # Get size
                size_bytes = os.path.getsize(file_path)
                size_mb = size_bytes / (1024 * 1024)
                stats["total_size_mb"] += size_mb

                # Categorize by size
                if size_mb < 1:
                    stats["size_distribution"]["small"] += 1
                elif size_mb < 10:
                    stats["size_distribution"]["medium"] += 1
                else:
                    stats["size_distribution"]["large"] += 1

                # Count by extension
                extension = os.path.splitext(file_path)[1].lower()
                stats["by_extension"][extension] = stats["by_extension"].get(extension, 0) + 1

            except OSError:
                continue

        stats["total_size_mb"] = round(stats["total_size_mb"], 2)
        return stats

    async def _get_file_stats_azure(self, blob_names: list[str]) -> dict:
        """Get statistics about Azure Storage blobs."""
        stats = {
            "total_files": len(blob_names),
            "total_size_mb": 0.0,
            "by_extension": {},
            "size_distribution": {"small": 0, "medium": 0, "large": 0},
        }

        if not self.azure_client:
            return stats

        for blob_name in blob_names:
            try:
                # Get blob properties for size
                blob_properties = await self.azure_client.get_blob_properties(
                    "input-documents", blob_name
                )
                if blob_properties:
                    size_bytes = blob_properties.get("size", 0)
                    size_mb = size_bytes / (1024 * 1024)
                    stats["total_size_mb"] += size_mb

                    # Categorize by size
                    if size_mb < 1:
                        stats["size_distribution"]["small"] += 1
                    elif size_mb < 10:
                        stats["size_distribution"]["medium"] += 1
                    else:
                        stats["size_distribution"]["large"] += 1

                # Count by extension (from blob name)
                extension = Path(blob_name).suffix.lower()
                stats["by_extension"][extension] = stats["by_extension"].get(extension, 0) + 1

            except Exception:
                # Count file even if we can't get properties
                extension = Path(blob_name).suffix.lower()
                stats["by_extension"][extension] = stats["by_extension"].get(extension, 0) + 1
                continue

        stats["total_size_mb"] = round(stats["total_size_mb"], 2)
        return stats

    async def download_document(self, file_path: str) -> Optional[bytes]:
        """Download document content from Azure Storage or read from local filesystem."""
        if self.use_azure:
            if not self.azure_client:
                raise BatchProcessingError(0, 0, "Azure Storage client not initialized")
            return await self.azure_client.download_blob("input-documents", file_path)
        else:
            try:
                with open(file_path, "rb") as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Failed to read local file: {file_path}", error=str(e))
                return None
