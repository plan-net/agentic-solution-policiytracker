"""Ray Data pipeline for document processing and graph population."""

import hashlib
from datetime import datetime
from typing import Any, Optional

import ray
import structlog

from src.integrations.azure_storage import AzureStorageClient
from src.processors.document_reader import DocumentReader

logger = structlog.get_logger()


@ray.remote
class DocumentProcessor:
    """Ray Data pipeline for scalable document processing."""

    def __init__(
        self,
        neo4j_config: dict[str, Any],
        embedding_config: Optional[dict[str, Any]] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        self.neo4j_config = neo4j_config
        self.embedding_config = embedding_config or {}
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.document_reader = DocumentReader()

    async def process_documents_from_azure(
        self, azure_client: AzureStorageClient, container_type: str = "input-documents"
    ) -> ray.data.Dataset:
        """Process documents from Azure Blob Storage through Ray Data pipeline."""
        try:
            # List all blobs in the container
            blobs = await azure_client.list_blobs(container_type)
            blob_paths = [blob["name"] for blob in blobs]

            logger.info(
                "Starting document processing pipeline",
                blob_count=len(blob_paths),
                container=container_type,
            )

            # Create Ray Data pipeline
            return self._create_pipeline(blob_paths, azure_client, container_type)

        except Exception as e:
            logger.error("Failed to process documents from Azure", error=str(e))
            raise

    def _create_pipeline(
        self, blob_paths: list[str], azure_client: AzureStorageClient, container_type: str
    ) -> ray.data.Dataset:
        """Create Ray Data processing pipeline."""
        # Start with list of blob paths
        return (
            ray.data.from_items(blob_paths)
            .map(lambda path: self._download_blob(path, azure_client, container_type))
            .map(self._extract_document_info)
            .map(self._extract_text)
            .flat_map(self._chunk_document)
            .map_batches(self._prepare_for_graph, batch_size=100)
        )

    def _download_blob(
        self, blob_path: str, azure_client: AzureStorageClient, container_type: str
    ) -> dict[str, Any]:
        """Download blob from Azure Storage."""
        try:
            content = ray.get(azure_client.download_blob.remote(container_type, blob_path))
            return {
                "path": blob_path,
                "content": content,
                "container": container_type,
            }
        except Exception as e:
            logger.error(f"Failed to download blob: {blob_path}", error=str(e))
            return {"path": blob_path, "error": str(e)}

    def _extract_document_info(self, blob_data: dict[str, Any]) -> dict[str, Any]:
        """Extract metadata from document."""
        if "error" in blob_data:
            return blob_data

        try:
            content = blob_data["content"]
            path = blob_data["path"]

            # Generate document ID from content hash
            doc_id = hashlib.sha256(
                content.encode() if isinstance(content, str) else content
            ).hexdigest()[:16]

            return {
                "document_id": doc_id,
                "path": path,
                "content": content,
                "extracted_at": datetime.utcnow().isoformat(),
                "size_bytes": len(content) if content else 0,
                "container": blob_data.get("container"),
            }
        except Exception as e:
            logger.error("Failed to extract document info", error=str(e))
            return {**blob_data, "error": str(e)}

    def _extract_text(self, doc_info: dict[str, Any]) -> dict[str, Any]:
        """Extract text from document content."""
        if "error" in doc_info:
            return doc_info

        try:
            # Use existing document reader
            file_extension = doc_info["path"].split(".")[-1].lower()

            if file_extension == "pdf":
                text = self.document_reader._read_pdf_content(doc_info["content"])
            elif file_extension in ["doc", "docx"]:
                text = self.document_reader._read_docx_content(doc_info["content"])
            elif file_extension == "md":
                text = self.document_reader._read_markdown_content(doc_info["content"])
            elif file_extension == "txt":
                text = (
                    doc_info["content"]
                    if isinstance(doc_info["content"], str)
                    else doc_info["content"].decode()
                )
            else:
                text = str(doc_info["content"])

            return {
                **doc_info,
                "text": text,
                "word_count": len(text.split()) if text else 0,
            }
        except Exception as e:
            logger.error(
                "Failed to extract text", document_id=doc_info.get("document_id"), error=str(e)
            )
            return {**doc_info, "error": str(e)}

    def _chunk_document(self, doc: dict[str, Any]) -> list[dict[str, Any]]:
        """Split document into semantic chunks with overlap."""
        if "error" in doc or "text" not in doc:
            return [doc]

        try:
            text = doc["text"]
            chunks = []

            # Simple sliding window chunking
            for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
                chunk_text = text[i : i + self.chunk_size]

                # Skip very small chunks at the end
                if len(chunk_text) < 50:
                    continue

                chunk_id = (
                    f"{doc['document_id']}_chunk_{i // (self.chunk_size - self.chunk_overlap)}"
                )

                chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "document_id": doc["document_id"],
                        "text": chunk_text,
                        "position": i,
                        "chunk_index": i // (self.chunk_size - self.chunk_overlap),
                        "document_path": doc["path"],
                        "metadata": {
                            "extracted_at": doc.get("extracted_at"),
                            "total_chunks": -1,  # Will be updated in post-processing
                        },
                    }
                )

            # Update total chunks count
            for chunk in chunks:
                chunk["metadata"]["total_chunks"] = len(chunks)

            logger.info(
                "Document chunked successfully",
                document_id=doc["document_id"],
                chunks_created=len(chunks),
            )

            return chunks

        except Exception as e:
            logger.error(
                "Failed to chunk document", document_id=doc.get("document_id"), error=str(e)
            )
            return [{**doc, "error": str(e)}]

    def _prepare_for_graph(self, batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Prepare batch of chunks for Neo4j insertion."""
        prepared_chunks = []

        for chunk in batch:
            if "error" in chunk:
                continue

            prepared_chunks.append(
                {
                    "chunk_id": chunk["chunk_id"],
                    "document_id": chunk["document_id"],
                    "text": chunk["text"],
                    "position": chunk["position"],
                    "chunk_index": chunk["chunk_index"],
                    "document_path": chunk["document_path"],
                    "metadata": chunk["metadata"],
                    # Placeholder for embeddings - will be generated in next phase
                    "embedding": None,
                }
            )

        return prepared_chunks


# Convenience function for creating the processor
def create_document_processor(
    neo4j_config: dict[str, Any], embedding_config: Optional[dict[str, Any]] = None, **kwargs
) -> DocumentProcessor:
    """Create a DocumentProcessor instance."""
    return DocumentProcessor.remote(neo4j_config, embedding_config, **kwargs)
