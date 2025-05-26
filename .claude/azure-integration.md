# Azure Storage Integration Patterns

## Client Implementation
Always use async BlobServiceClient with this container structure:
- `input-documents` - Raw input files
- `reports` - Generated analysis reports  
- `checkpoints` - LangGraph state checkpoints
- `contexts` - Client context files
- `cache` - Temporary cache data
- `job-artifacts` - Job execution artifacts

## Key Patterns
```python
# Always use async methods
async def upload_json(self, container_type: str, blob_name: str, data: dict)
async def download_json(self, container_type: str, blob_name: str)

# Error handling pattern
try:
    # Azure operation
except Exception as e:
    logger.error(f"Azure operation failed: {e}")
    return None  # or False for uploads
```

## Development Setup
- Use Azurite locally: `just services-up`
- Connection string in .env for local dev (DefaultEndpointsProtocol=http...)
- Import test data: `just azure-import`
- Verify connection: `just azure-verify`

## LangGraph Checkpointing
Implement BaseCheckpointSaver with Azure backend for workflow state persistence.
Store checkpoints as: `threads/{thread_id}/checkpoints/{checkpoint_id}.json`