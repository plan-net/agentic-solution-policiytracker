"""Azure Storage checkpointer for LangGraph workflows."""

import json
import pickle
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

import structlog
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.serde.types import TASKS

from src.config import settings
from src.integrations.azure_storage import AzureStorageClient

logger = structlog.get_logger()


class AzureCheckpointSaver(BaseCheckpointSaver):
    """Azure Storage-based checkpoint saver for LangGraph workflows."""

    def __init__(self, azure_client: Optional[AzureStorageClient] = None):
        """Initialize Azure checkpoint saver.

        Args:
            azure_client: Optional Azure Storage client. If None, creates a new one.
        """
        super().__init__()
        self.azure_client = azure_client or AzureStorageClient()
        self.container_type = "checkpoints"

    def _get_checkpoint_key(self, thread_id: str, checkpoint_id: str) -> str:
        """Generate a checkpoint key for Azure Storage."""
        return f"threads/{thread_id}/checkpoints/{checkpoint_id}.json"

    def _get_writes_key(self, thread_id: str, checkpoint_id: str, task_id: str) -> str:
        """Generate a writes key for Azure Storage."""
        return f"threads/{thread_id}/checkpoints/{checkpoint_id}/writes/{task_id}.json"

    async def aget(
        self,
        config: Dict[str, Any],
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Optional[Tuple[Dict[str, Any], Dict[str, Any], Optional[str]]]:
        """Asynchronously get checkpoint data from Azure Storage."""
        try:
            thread_id = config.get("configurable", {}).get("thread_id")
            if not thread_id:
                logger.warning("No thread_id provided in config")
                return None

            # Get the latest checkpoint if no specific checkpoint ID is provided
            checkpoint_id = config.get("configurable", {}).get("checkpoint_id")
            if not checkpoint_id:
                checkpoint_id = await self._get_latest_checkpoint_id(thread_id)
                if not checkpoint_id:
                    return None

            # Load checkpoint data
            checkpoint_key = self._get_checkpoint_key(thread_id, checkpoint_id)
            checkpoint_data = await self.azure_client.download_json(
                self.container_type, checkpoint_key
            )

            if not checkpoint_data:
                logger.debug(
                    "Checkpoint not found", thread_id=thread_id, checkpoint_id=checkpoint_id
                )
                return None

            # Deserialize checkpoint
            checkpoint = self._deserialize_checkpoint(checkpoint_data.get("checkpoint", {}))
            metadata = checkpoint_data.get("metadata", {})
            parent_config = checkpoint_data.get("parent_config")

            logger.debug(
                "Retrieved checkpoint",
                thread_id=thread_id,
                checkpoint_id=checkpoint_id,
                checkpoint_keys=list(checkpoint.keys()),
            )

            return checkpoint, metadata, parent_config

        except Exception as e:
            logger.error(
                "Failed to get checkpoint",
                thread_id=thread_id,
                checkpoint_id=checkpoint_id,
                error=str(e),
            )
            return None

    async def aput(
        self,
        config: Dict[str, Any],
        checkpoint: Dict[str, Any],
        metadata: Dict[str, Any],
        new_versions: Dict[str, Union[str, int]],
    ) -> Dict[str, Any]:
        """Asynchronously save checkpoint data to Azure Storage."""
        try:
            thread_id = config.get("configurable", {}).get("thread_id")
            if not thread_id:
                thread_id = str(uuid4())
                config.setdefault("configurable", {})["thread_id"] = thread_id

            # Generate checkpoint ID based on timestamp and versions
            checkpoint_id = f"{datetime.now().isoformat()}_{str(uuid4())[:8]}"

            # Serialize checkpoint data
            serialized_checkpoint = self._serialize_checkpoint(checkpoint)

            # Prepare checkpoint document
            checkpoint_doc = {
                "checkpoint_id": checkpoint_id,
                "thread_id": thread_id,
                "checkpoint": serialized_checkpoint,
                "metadata": metadata,
                "new_versions": new_versions,
                "parent_config": config.get("configurable", {}).get("checkpoint_id"),
                "created_at": datetime.now().isoformat(),
                "versions": new_versions,
            }

            # Save to Azure Storage
            checkpoint_key = self._get_checkpoint_key(thread_id, checkpoint_id)

            blob_metadata = {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
                "created_at": datetime.now().isoformat(),
                "checkpoint_size": str(len(json.dumps(checkpoint_doc))),
            }

            success = await self.azure_client.upload_json(
                self.container_type, checkpoint_key, checkpoint_doc, metadata=blob_metadata
            )

            if not success:
                raise Exception("Failed to upload checkpoint to Azure Storage")

            # Update config with new checkpoint ID
            new_config = config.copy()
            new_config.setdefault("configurable", {})["checkpoint_id"] = checkpoint_id

            logger.debug(
                "Saved checkpoint",
                thread_id=thread_id,
                checkpoint_id=checkpoint_id,
                checkpoint_keys=list(checkpoint.keys()),
            )

            return new_config

        except Exception as e:
            logger.error("Failed to save checkpoint", thread_id=thread_id, error=str(e))
            raise

    async def aput_writes(
        self,
        config: Dict[str, Any],
        writes: List[Tuple[str, Any]],
        task_id: str,
    ) -> None:
        """Asynchronously save pending writes to Azure Storage."""
        try:
            thread_id = config.get("configurable", {}).get("thread_id")
            checkpoint_id = config.get("configurable", {}).get("checkpoint_id")

            if not thread_id or not checkpoint_id:
                logger.warning(
                    "Missing thread_id or checkpoint_id for writes",
                    thread_id=thread_id,
                    checkpoint_id=checkpoint_id,
                )
                return

            # Serialize writes
            serialized_writes = []
            for channel, value in writes:
                serialized_writes.append(
                    {"channel": channel, "value": self._serialize_value(value)}
                )

            # Prepare writes document
            writes_doc = {
                "task_id": task_id,
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
                "writes": serialized_writes,
                "created_at": datetime.now().isoformat(),
            }

            # Save to Azure Storage
            writes_key = self._get_writes_key(thread_id, checkpoint_id, task_id)

            blob_metadata = {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
                "task_id": task_id,
                "writes_count": str(len(writes)),
                "created_at": datetime.now().isoformat(),
            }

            success = await self.azure_client.upload_json(
                self.container_type, writes_key, writes_doc, metadata=blob_metadata
            )

            if not success:
                raise Exception("Failed to upload writes to Azure Storage")

            logger.debug(
                "Saved writes",
                thread_id=thread_id,
                checkpoint_id=checkpoint_id,
                task_id=task_id,
                writes_count=len(writes),
            )

        except Exception as e:
            logger.error(
                "Failed to save writes",
                thread_id=thread_id,
                checkpoint_id=checkpoint_id,
                task_id=task_id,
                error=str(e),
            )
            raise

    async def _get_latest_checkpoint_id(self, thread_id: str) -> Optional[str]:
        """Get the latest checkpoint ID for a thread."""
        try:
            # List all checkpoints for this thread
            prefix = f"threads/{thread_id}/checkpoints/"
            blobs = await self.azure_client.list_blobs(self.container_type, prefix=prefix)

            checkpoint_blobs = []
            for blob in blobs:
                if blob.name.endswith(".json") and "/writes/" not in blob.name:
                    checkpoint_blobs.append(blob)

            if not checkpoint_blobs:
                return None

            # Sort by last modified time (most recent first)
            checkpoint_blobs.sort(key=lambda b: b.last_modified, reverse=True)

            # Extract checkpoint ID from the most recent blob
            latest_blob = checkpoint_blobs[0]
            checkpoint_id = latest_blob.name.split("/")[-1].replace(".json", "")

            return checkpoint_id

        except Exception as e:
            logger.error("Failed to get latest checkpoint ID", thread_id=thread_id, error=str(e))
            return None

    def _serialize_checkpoint(self, checkpoint: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize checkpoint data for storage."""
        serialized = {}

        for key, value in checkpoint.items():
            try:
                # Try JSON serialization first
                json.dumps(value)
                serialized[key] = value
            except (TypeError, ValueError):
                # Fall back to pickle for complex objects
                try:
                    import base64

                    pickled = pickle.dumps(value)
                    serialized[key] = {
                        "_type": "pickle",
                        "_data": base64.b64encode(pickled).decode("utf-8"),
                    }
                except Exception as e:
                    logger.warning("Failed to serialize checkpoint value", key=key, error=str(e))
                    serialized[key] = None

        return serialized

    def _deserialize_checkpoint(self, checkpoint_data: Dict[str, Any]) -> Dict[str, Any]:
        """Deserialize checkpoint data from storage."""
        deserialized = {}

        for key, value in checkpoint_data.items():
            if isinstance(value, dict) and value.get("_type") == "pickle":
                try:
                    import base64

                    pickled_data = base64.b64decode(value["_data"])
                    deserialized[key] = pickle.loads(pickled_data)
                except Exception as e:
                    logger.warning("Failed to deserialize pickled value", key=key, error=str(e))
                    deserialized[key] = None
            else:
                deserialized[key] = value

        return deserialized

    def _serialize_value(self, value: Any) -> Any:
        """Serialize a single value for storage."""
        try:
            # Try JSON serialization first
            json.dumps(value)
            return value
        except (TypeError, ValueError):
            # Fall back to pickle for complex objects
            try:
                import base64

                pickled = pickle.dumps(value)
                return {"_type": "pickle", "_data": base64.b64encode(pickled).decode("utf-8")}
            except Exception as e:
                logger.warning("Failed to serialize value", error=str(e))
                return None

    async def cleanup_old_checkpoints(self, thread_id: str, keep_last: int = 10) -> int:
        """Clean up old checkpoints, keeping only the most recent ones."""
        try:
            # List all checkpoints for this thread
            prefix = f"threads/{thread_id}/checkpoints/"
            blobs = await self.azure_client.list_blobs(self.container_type, prefix=prefix)

            checkpoint_blobs = []
            for blob in blobs:
                if blob.name.endswith(".json") and "/writes/" not in blob.name:
                    checkpoint_blobs.append(blob)

            # Sort by last modified time (oldest first)
            checkpoint_blobs.sort(key=lambda b: b.last_modified)

            # Keep only the latest N checkpoints
            blobs_to_delete = (
                checkpoint_blobs[:-keep_last] if len(checkpoint_blobs) > keep_last else []
            )

            deleted_count = 0
            for blob in blobs_to_delete:
                try:
                    await self.azure_client.delete_blob(self.container_type, blob.name)

                    # Also delete associated writes
                    checkpoint_id = blob.name.split("/")[-1].replace(".json", "")
                    writes_prefix = f"threads/{thread_id}/checkpoints/{checkpoint_id}/writes/"
                    writes_blobs = await self.azure_client.list_blobs(
                        self.container_type, prefix=writes_prefix
                    )

                    for writes_blob in writes_blobs:
                        await self.azure_client.delete_blob(self.container_type, writes_blob.name)

                    deleted_count += 1

                except Exception as e:
                    logger.warning("Failed to delete checkpoint", blob_name=blob.name, error=str(e))

            logger.info(
                "Cleaned up old checkpoints",
                thread_id=thread_id,
                deleted_count=deleted_count,
                kept_count=len(checkpoint_blobs) - deleted_count,
            )

            return deleted_count

        except Exception as e:
            logger.error("Failed to cleanup old checkpoints", thread_id=thread_id, error=str(e))
            return 0

    # Synchronous methods (required by base class)
    def get(
        self, config: Dict[str, Any], **kwargs
    ) -> Optional[Tuple[Dict[str, Any], Dict[str, Any], Optional[str]]]:
        """Synchronous get method (not recommended for Azure Storage)."""
        import asyncio

        return asyncio.run(self.aget(config, **kwargs))

    def put(
        self,
        config: Dict[str, Any],
        checkpoint: Dict[str, Any],
        metadata: Dict[str, Any],
        new_versions: Dict[str, Union[str, int]],
    ) -> Dict[str, Any]:
        """Synchronous put method (not recommended for Azure Storage)."""
        import asyncio

        return asyncio.run(self.aput(config, checkpoint, metadata, new_versions))

    def put_writes(
        self, config: Dict[str, Any], writes: List[Tuple[str, Any]], task_id: str
    ) -> None:
        """Synchronous put_writes method (not recommended for Azure Storage)."""
        import asyncio

        return asyncio.run(self.aput_writes(config, writes, task_id))
