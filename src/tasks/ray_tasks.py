import time
from typing import Any, Dict, List

import ray
import structlog

from src.models.content import ProcessedContent
from src.models.scoring import ScoringResult
from src.processors.content_processor import ContentProcessor
from src.scoring.relevance_engine import RelevanceEngine

logger = structlog.get_logger()


@ray.remote(max_retries=3)
def process_document_task(file_path: str, doc_id: str) -> ProcessedContent:
    """Process a single document file using Ray."""
    try:
        logger.debug("Processing document task", file_path=file_path, doc_id=doc_id)
        
        processor = ContentProcessor()
        result = processor.process_document(file_path, doc_id)
        
        # Since this is a sync function called by Ray, we need to handle async properly
        # For now, we'll create a sync version or use asyncio.run
        import asyncio
        if asyncio.iscoroutine(result):
            result = asyncio.run(result)
        
        logger.debug("Document processing completed", doc_id=doc_id)
        return result
        
    except Exception as e:
        logger.error("Document processing task failed", 
                    file_path=file_path, 
                    doc_id=doc_id, 
                    error=str(e))
        raise


@ray.remote(max_retries=2)
def score_document_task(content: ProcessedContent, context: Dict[str, Any]) -> ScoringResult:
    """Score a document using Ray."""
    try:
        logger.debug("Scoring document task", document_id=content.id)
        
        start_time = time.time()
        
        engine = RelevanceEngine(context)
        result = engine.score_document(content)
        
        # Handle async result
        import asyncio
        if asyncio.iscoroutine(result):
            result = asyncio.run(result)
        
        # Add processing time
        processing_time = (time.time() - start_time) * 1000
        result.processing_time_ms = processing_time
        
        logger.debug("Document scoring completed", 
                    document_id=content.id, 
                    score=result.master_score,
                    processing_time_ms=processing_time)
        
        return result
        
    except Exception as e:
        logger.error("Document scoring task failed", 
                    document_id=content.id, 
                    error=str(e))
        raise


@ray.remote
def batch_processing_task(file_paths: List[str], start_index: int) -> List[ProcessedContent]:
    """Process a batch of documents."""
    try:
        logger.info("Starting batch processing task", 
                   batch_size=len(file_paths), 
                   start_index=start_index)
        
        processor = ContentProcessor()
        results = []
        
        for i, file_path in enumerate(file_paths):
            try:
                doc_id = f"doc_{start_index + i:03d}"
                
                # Process document synchronously
                import asyncio
                result = asyncio.run(processor.process_document(file_path, doc_id))
                results.append(result)
                
            except Exception as e:
                logger.warning("Failed to process document in batch", 
                             file_path=file_path, 
                             error=str(e))
                # Continue with other documents
        
        logger.info("Batch processing completed", 
                   processed=len(results), 
                   total=len(file_paths))
        
        return results
        
    except Exception as e:
        logger.error("Batch processing task failed", error=str(e))
        raise


@ray.remote
def batch_scoring_task(
    documents: List[ProcessedContent], 
    context: Dict[str, Any]
) -> List[ScoringResult]:
    """Score a batch of documents."""
    try:
        logger.info("Starting batch scoring task", batch_size=len(documents))
        
        engine = RelevanceEngine(context)
        results = []
        
        for document in documents:
            try:
                start_time = time.time()
                
                # Score document synchronously
                import asyncio
                result = asyncio.run(engine.score_document(document))
                
                # Add processing time
                processing_time = (time.time() - start_time) * 1000
                result.processing_time_ms = processing_time
                
                results.append(result)
                
            except Exception as e:
                logger.warning("Failed to score document in batch", 
                             document_id=document.id, 
                             error=str(e))
                # Continue with other documents
        
        logger.info("Batch scoring completed", 
                   scored=len(results), 
                   total=len(documents))
        
        return results
        
    except Exception as e:
        logger.error("Batch scoring task failed", error=str(e))
        raise


@ray.remote
def batch_aggregation_task(results: List[ScoringResult]) -> Dict[str, Any]:
    """Aggregate results from multiple batches."""
    try:
        logger.info("Starting batch aggregation task", result_count=len(results))
        
        if not results:
            return {"aggregated_results": [], "statistics": {}}
        
        # Calculate statistics
        scores = [r.master_score for r in results]
        confidence_scores = [r.confidence_score for r in results]
        processing_times = [r.processing_time_ms for r in results if r.processing_time_ms > 0]
        
        statistics = {
            "total_documents": len(results),
            "average_score": sum(scores) / len(scores) if scores else 0,
            "max_score": max(scores) if scores else 0,
            "min_score": min(scores) if scores else 0,
            "average_confidence": sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
            "total_processing_time_ms": sum(processing_times),
            "average_processing_time_ms": sum(processing_times) / len(processing_times) if processing_times else 0
        }
        
        # Group by priority
        priority_groups = {}
        for result in results:
            priority = result.priority_level.value
            if priority not in priority_groups:
                priority_groups[priority] = []
            priority_groups[priority].append(result)
        
        # Group by topic clusters (if available)
        topic_groups = {}
        for result in results:
            for topic in result.topic_clusters:
                if topic not in topic_groups:
                    topic_groups[topic] = []
                topic_groups[topic].append(result)
        
        aggregated_data = {
            "aggregated_results": results,
            "statistics": statistics,
            "priority_groups": priority_groups,
            "topic_groups": topic_groups
        }
        
        logger.info("Batch aggregation completed", 
                   total_results=len(results),
                   priority_groups=len(priority_groups),
                   topic_groups=len(topic_groups))
        
        return aggregated_data
        
    except Exception as e:
        logger.error("Batch aggregation task failed", error=str(e))
        raise


# Utility functions for task management

def create_processing_batches(file_paths: List[str], batch_size: int = 50) -> List[List[str]]:
    """Create batches of file paths for parallel processing."""
    batches = []
    for i in range(0, len(file_paths), batch_size):
        batch = file_paths[i:i + batch_size]
        batches.append(batch)
    
    logger.info("Created processing batches", 
               total_files=len(file_paths),
               batch_count=len(batches),
               batch_size=batch_size)
    
    return batches


def create_scoring_batches(documents: List[ProcessedContent], batch_size: int = 20) -> List[List[ProcessedContent]]:
    """Create batches of documents for parallel scoring."""
    batches = []
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        batches.append(batch)
    
    logger.info("Created scoring batches", 
               total_documents=len(documents),
               batch_count=len(batches),
               batch_size=batch_size)
    
    return batches