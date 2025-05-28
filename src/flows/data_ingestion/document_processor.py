"""
Simple document processor using direct Graphiti API.

Focused on doing one thing well: processing documents into temporal knowledge graph.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import structlog

from src.flows.shared.graphiti_client import SharedGraphitiClient, generate_episode_name, extract_document_date
from src.flows.data_ingestion.document_tracker import DocumentTracker

logger = structlog.get_logger()


class SimpleDocumentProcessor:
    """Lean document processor with direct Graphiti integration."""
    
    def __init__(self, tracker: DocumentTracker, clear_mode: bool = False):
        self.tracker = tracker
        self.clear_mode = clear_mode
        self.processing_stats = {
            "total_documents": 0,
            "processed": 0,
            "skipped": 0,
            "failed": 0,
            "total_entities": 0,
            "total_relationships": 0,
            "processing_time": 0.0
        }
    
    def _read_document(self, doc_path: Path) -> str:
        """Read document content with encoding detection."""
        try:
            # Try UTF-8 first
            with open(doc_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Fallback to latin-1 for legacy documents
            logger.warning(f"UTF-8 failed for {doc_path}, trying latin-1")
            with open(doc_path, 'r', encoding='latin-1') as f:
                return f.read()
    
    async def process_document(self, doc_path: Path, graphiti_client: SharedGraphitiClient) -> Dict[str, any]:
        """Process a single document through Graphiti."""
        start_time = datetime.now()
        
        try:
            # Check if already processed (unless clear mode)
            if not self.clear_mode and self.tracker.is_processed(str(doc_path)):
                logger.debug(f"Skipping already processed document: {doc_path}")
                self.processing_stats["skipped"] += 1
                return {
                    "status": "skipped",
                    "reason": "already_processed",
                    "path": str(doc_path),
                    "processing_time": 0.0
                }
            
            # Read document content
            try:
                content = self._read_document(doc_path)
                if not content.strip():
                    raise ValueError("Document is empty")
                    
                logger.debug(f"Read document: {doc_path} ({len(content)} characters)")
            except Exception as e:
                error_msg = f"Failed to read document: {e}"
                self.tracker.mark_failed(str(doc_path), error_msg)
                self.processing_stats["failed"] += 1
                return {
                    "status": "failed",
                    "error": error_msg,
                    "path": str(doc_path),
                    "processing_time": (datetime.now() - start_time).total_seconds()
                }
            
            # Process through Graphiti
            episode_name = generate_episode_name(doc_path, datetime.now())
            # Handle both Path objects and strings for source description
            doc_name = doc_path.name if hasattr(doc_path, 'name') else Path(doc_path).name
            source_description = f"Political document: {doc_name}"
            reference_time = extract_document_date(content) or datetime.now()
            
            try:
                result = await graphiti_client.add_episode(
                    name=episode_name,
                    content=content,
                    source_description=source_description,
                    reference_time=reference_time
                )
                
                # Track successful processing
                self.tracker.mark_processed(
                    str(doc_path),
                    result["episode_id"],
                    result["entity_count"],
                    result["relationship_count"]
                )
                
                processing_time = (datetime.now() - start_time).total_seconds()
                self.processing_stats["processed"] += 1
                self.processing_stats["total_entities"] += result["entity_count"]
                self.processing_stats["total_relationships"] += result["relationship_count"]
                self.processing_stats["processing_time"] += processing_time
                
                doc_name = doc_path.name if hasattr(doc_path, 'name') else Path(doc_path).name
                logger.info(f"Processed document: {doc_name}",
                           entities=result["entity_count"],
                           relationships=result["relationship_count"],
                           time=f"{processing_time:.2f}s")
                
                return {
                    "status": "success",
                    "path": str(doc_path),
                    "episode_id": result["episode_id"],
                    "entity_count": result["entity_count"],
                    "relationship_count": result["relationship_count"],
                    "processing_time": processing_time,
                    "content_length": len(content),
                    "entities": result.get("entities", []),
                    "document_date": reference_time.strftime('%Y-%m-%d') if reference_time != datetime.now() else None,
                    "content_preview": content[:200] + "..." if len(content) > 200 else content
                }
                
            except Exception as e:
                error_msg = f"Graphiti processing failed: {e}"
                self.tracker.mark_failed(str(doc_path), error_msg)
                self.processing_stats["failed"] += 1
                
                return {
                    "status": "failed",
                    "error": error_msg,
                    "path": str(doc_path),
                    "processing_time": (datetime.now() - start_time).total_seconds()
                }
        
        except Exception as e:
            # Catch-all for unexpected errors
            error_msg = f"Unexpected error: {e}"
            logger.error(f"Unexpected error processing {doc_path}: {e}")
            self.processing_stats["failed"] += 1
            return {
                "status": "failed",
                "error": error_msg,
                "path": str(doc_path),
                "processing_time": (datetime.now() - start_time).total_seconds()
            }
    
    async def process_documents(self, source_path: Path, document_limit: int = 10, tracer=None) -> List[Dict[str, any]]:
        """Process multiple documents from source directory."""
        start_time = datetime.now()
        
        # Find documents
        if not source_path.exists():
            raise ValueError(f"Source path does not exist: {source_path}")
        
        if source_path.is_file():
            documents = [source_path]
        else:
            # Find all supported document files using same logic as find_documents
            documents = []
            for ext in get_supported_extensions():
                pattern = f"*{ext}"
                documents.extend(source_path.glob(pattern))
        
        if not documents:
            raise ValueError(f"No documents found in: {source_path}")
        
        # Apply document limit
        documents = documents[:document_limit]
        self.processing_stats["total_documents"] = len(documents)
        
        logger.info(f"Processing {len(documents)} documents from {source_path}")
        
        if tracer:
            await tracer.markdown(f"""📄 **Processing {len(documents)} documents**

Found documents:
{chr(10).join([f"• `{doc.name}`" for doc in documents])}

---
""")
        
        # Process documents
        results = []
        async with SharedGraphitiClient() as graphiti_client:
            for i, doc_path in enumerate(documents, 1):
                if tracer:
                    await tracer.markdown(f"🔍 **Processing document {i}/{len(documents)}**: `{doc_path.name}`")
                
                result = await self.process_document(doc_path, graphiti_client)
                results.append(result)
                
                # Enhanced progress updates
                if result["status"] == "success":
                    status_emoji = "✅"
                    status_details = f"**{result['entity_count']} entities**, **{result['relationship_count']} relationships**"
                elif result["status"] == "skipped":
                    status_emoji = "⏭️"
                    status_details = "Already processed"
                else:
                    status_emoji = "❌"
                    status_details = f"Failed: {result.get('error', 'Unknown error')}"
                
                if tracer:
                    await tracer.markdown(f"{status_emoji} **`{doc_path.name}`** - {status_details}")
                
                # Progress logging
                processed_so_far = len(results)
                logger.info(f"Progress: {processed_so_far}/{len(documents)} documents")
        
        total_time = (datetime.now() - start_time).total_seconds()
        self.processing_stats["total_processing_time"] = total_time
        
        # Final summary for tracer
        if tracer:
            await tracer.markdown(f"""---

🎉 **Document processing completed!**

**Summary:**
- ✅ **{self.processing_stats["processed"]} processed** 
- ⏭️ **{self.processing_stats["skipped"]} skipped**
- ❌ **{self.processing_stats["failed"]} failed**
- ⏱️ **{total_time:.1f}s total time**
- 🧠 **{self.processing_stats["total_entities"]} total entities extracted**
- 🔗 **{self.processing_stats["total_relationships"]} total relationships extracted**

---
""")
        
        logger.info(f"Batch processing completed in {total_time:.2f}s",
                   total=len(documents),
                   processed=self.processing_stats["processed"],
                   skipped=self.processing_stats["skipped"],
                   failed=self.processing_stats["failed"])
        
        return results
    
    def get_processing_stats(self) -> Dict[str, any]:
        """Get detailed processing statistics."""
        stats = self.processing_stats.copy()
        
        if stats["processed"] > 0:
            stats["avg_processing_time"] = stats["processing_time"] / stats["processed"]
            stats["avg_entities_per_doc"] = stats["total_entities"] / stats["processed"]
            stats["avg_relationships_per_doc"] = stats["total_relationships"] / stats["processed"]
        else:
            stats["avg_processing_time"] = 0.0
            stats["avg_entities_per_doc"] = 0.0
            stats["avg_relationships_per_doc"] = 0.0
        
        if stats["total_documents"] > 0:
            stats["success_rate"] = (stats["processed"] / stats["total_documents"]) * 100
        else:
            stats["success_rate"] = 0.0
        
        return stats


def get_supported_extensions() -> List[str]:
    """Get list of supported document extensions."""
    return [".txt", ".md"]


def find_documents(source_path: Path, limit: Optional[int] = None) -> List[Path]:
    """Find all supported documents in source path."""
    if not source_path.exists():
        return []
    
    if source_path.is_file():
        if source_path.suffix.lower() in get_supported_extensions():
            return [source_path]
        return []
    
    documents = []
    for ext in get_supported_extensions():
        pattern = f"*{ext}"
        documents.extend(source_path.glob(pattern))
    
    # Sort by name for consistent processing order
    documents.sort()
    
    if limit:
        documents = documents[:limit]
    
    return documents