import asyncio
from typing import Any, Dict, List, Optional

import ray
import structlog

from src.models.content import ProcessedContent
from src.models.scoring import ScoringResult
from src.tasks.ray_tasks import (
    process_document_task,
    score_document_task,
    batch_processing_task,
    batch_scoring_task,
    batch_aggregation_task,
    create_processing_batches,
    create_scoring_batches
)
from src.config import settings

logger = structlog.get_logger()


class TaskManager:
    """Manage Ray task distribution and monitoring."""
    
    def __init__(self):
        self.max_concurrent_tasks = 20
        self.processing_batch_size = 50
        self.scoring_batch_size = 20
    
    async def process_documents_parallel(
        self, 
        file_paths: List[str],
        progress_callback: Optional[callable] = None
    ) -> List[ProcessedContent]:
        """Process documents in parallel using Ray tasks."""
        try:
            logger.info("Starting parallel document processing", 
                       file_count=len(file_paths))
            
            if len(file_paths) <= self.processing_batch_size:
                # Small batch - process directly
                return await self._process_small_batch(file_paths, progress_callback)
            else:
                # Large batch - use parallel batching
                return await self._process_large_batch(file_paths, progress_callback)
            
        except Exception as e:
            logger.error("Parallel document processing failed", error=str(e))
            raise
    
    async def score_documents_parallel(
        self,
        documents: List[ProcessedContent],
        context: Dict[str, Any],
        progress_callback: Optional[callable] = None
    ) -> List[ScoringResult]:
        """Score documents in parallel using Ray tasks."""
        try:
            logger.info("Starting parallel document scoring", 
                       document_count=len(documents))
            
            if len(documents) <= self.scoring_batch_size:
                # Small batch - score directly
                return await self._score_small_batch(documents, context, progress_callback)
            else:
                # Large batch - use parallel batching
                return await self._score_large_batch(documents, context, progress_callback)
            
        except Exception as e:
            logger.error("Parallel document scoring failed", error=str(e))
            raise
    
    async def _process_small_batch(
        self, 
        file_paths: List[str],
        progress_callback: Optional[callable] = None
    ) -> List[ProcessedContent]:
        """Process small batch of documents."""
        tasks = []
        
        # Create individual Ray tasks
        for i, file_path in enumerate(file_paths):
            doc_id = f"doc_{i:03d}"
            task = process_document_task.remote(file_path, doc_id)
            tasks.append(task)
        
        # Execute tasks with progress tracking
        results = []
        completed = 0
        
        while tasks:
            # Wait for at least one task to complete
            ready_tasks, remaining_tasks = ray.wait(
                tasks, 
                num_returns=min(len(tasks), 5),  # Get up to 5 results at once
                timeout=30.0
            )
            
            # Get results from completed tasks
            for task in ready_tasks:
                try:
                    result = ray.get(task)
                    results.append(result)
                    completed += 1
                    
                    # Update progress
                    if progress_callback:
                        progress = completed / len(file_paths) * 100
                        await progress_callback(completed, len(file_paths), progress)
                
                except Exception as e:
                    logger.warning("Document processing task failed", error=str(e))
                    completed += 1
            
            tasks = remaining_tasks
        
        logger.info("Small batch processing completed", 
                   processed=len(results),
                   total=len(file_paths))
        
        return results
    
    async def _process_large_batch(
        self, 
        file_paths: List[str],
        progress_callback: Optional[callable] = None
    ) -> List[ProcessedContent]:
        """Process large batch using batch tasks."""
        # Create batches
        batches = create_processing_batches(file_paths, self.processing_batch_size)
        
        # Create batch tasks
        batch_tasks = []
        for i, batch in enumerate(batches):
            start_index = i * self.processing_batch_size
            task = batch_processing_task.remote(batch, start_index)
            batch_tasks.append(task)
        
        # Execute batch tasks
        all_results = []
        completed_batches = 0
        
        while batch_tasks:
            # Wait for batch completion
            ready_tasks, remaining_tasks = ray.wait(
                batch_tasks,
                num_returns=min(len(batch_tasks), 3),  # Process up to 3 batches at once
                timeout=60.0
            )
            
            # Get results from completed batches
            for task in ready_tasks:
                try:
                    batch_results = ray.get(task)
                    all_results.extend(batch_results)
                    completed_batches += 1
                    
                    # Update progress
                    if progress_callback:
                        progress = completed_batches / len(batches) * 100
                        await progress_callback(
                            len(all_results), 
                            len(file_paths), 
                            progress
                        )
                
                except Exception as e:
                    logger.warning("Batch processing task failed", error=str(e))
                    completed_batches += 1
            
            batch_tasks = remaining_tasks
        
        logger.info("Large batch processing completed", 
                   processed=len(all_results),
                   total=len(file_paths),
                   batches=len(batches))
        
        return all_results
    
    async def _score_small_batch(
        self,
        documents: List[ProcessedContent],
        context: Dict[str, Any],
        progress_callback: Optional[callable] = None
    ) -> List[ScoringResult]:
        """Score small batch of documents."""
        tasks = []
        
        # Create individual Ray tasks
        for document in documents:
            task = score_document_task.remote(document, context)
            tasks.append(task)
        
        # Execute tasks with progress tracking
        results = []
        completed = 0
        
        while tasks:
            # Wait for tasks to complete
            ready_tasks, remaining_tasks = ray.wait(
                tasks,
                num_returns=min(len(tasks), 5),
                timeout=30.0
            )
            
            # Get results
            for task in ready_tasks:
                try:
                    result = ray.get(task)
                    results.append(result)
                    completed += 1
                    
                    # Update progress
                    if progress_callback:
                        progress = completed / len(documents) * 100
                        await progress_callback(completed, len(documents), progress)
                
                except Exception as e:
                    logger.warning("Document scoring task failed", error=str(e))
                    completed += 1
            
            tasks = remaining_tasks
        
        logger.info("Small batch scoring completed", 
                   scored=len(results),
                   total=len(documents))
        
        return results
    
    async def _score_large_batch(
        self,
        documents: List[ProcessedContent],
        context: Dict[str, Any],
        progress_callback: Optional[callable] = None
    ) -> List[ScoringResult]:
        """Score large batch using batch tasks."""
        # Create batches
        batches = create_scoring_batches(documents, self.scoring_batch_size)
        
        # Create batch tasks
        batch_tasks = []
        for batch in batches:
            task = batch_scoring_task.remote(batch, context)
            batch_tasks.append(task)
        
        # Execute batch tasks
        all_results = []
        completed_batches = 0
        
        while batch_tasks:
            # Wait for batch completion
            ready_tasks, remaining_tasks = ray.wait(
                batch_tasks,
                num_returns=min(len(batch_tasks), 3),
                timeout=60.0
            )
            
            # Get results from completed batches
            for task in ready_tasks:
                try:
                    batch_results = ray.get(task)
                    all_results.extend(batch_results)
                    completed_batches += 1
                    
                    # Update progress
                    if progress_callback:
                        progress = completed_batches / len(batches) * 100
                        await progress_callback(
                            len(all_results), 
                            len(documents), 
                            progress
                        )
                
                except Exception as e:
                    logger.warning("Batch scoring task failed", error=str(e))
                    completed_batches += 1
            
            batch_tasks = remaining_tasks
        
        logger.info("Large batch scoring completed", 
                   scored=len(all_results),
                   total=len(documents),
                   batches=len(batches))
        
        return all_results
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get Ray cluster status information."""
        try:
            cluster_resources = ray.cluster_resources()
            available_resources = ray.available_resources()
            
            return {
                "cluster_resources": cluster_resources,
                "available_resources": available_resources,
                "nodes": len(ray.nodes()),
                "tasks_running": len(ray.util.list_tasks(filters=[("state", "=", "RUNNING")])),
                "memory_usage": {
                    "total_gb": cluster_resources.get("memory", 0) / (1024**3),
                    "available_gb": available_resources.get("memory", 0) / (1024**3)
                }
            }
        
        except Exception as e:
            logger.warning("Could not get cluster status", error=str(e))
            return {"error": str(e)}
    
    def optimize_batch_sizes(self, total_items: int, available_cpus: int) -> tuple[int, int]:
        """Optimize batch sizes based on cluster resources."""
        # Adjust batch sizes based on available resources
        if available_cpus >= 16:
            processing_batch_size = 30
            scoring_batch_size = 15
        elif available_cpus >= 8:
            processing_batch_size = 40
            scoring_batch_size = 20
        else:
            processing_batch_size = 50
            scoring_batch_size = 25
        
        # Ensure we don't create too many small batches
        if total_items < processing_batch_size:
            processing_batch_size = max(1, total_items // max(1, available_cpus))
            scoring_batch_size = max(1, total_items // max(1, available_cpus))
        
        return processing_batch_size, scoring_batch_size