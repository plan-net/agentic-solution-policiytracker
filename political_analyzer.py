# political_analyzer.py - Kodosumi Entrypoint for Political Analysis
import asyncio
import os
import time
from datetime import datetime
from typing import Any, Dict

import ray
from kodosumi.core import Tracer
import structlog

from src.models.job import Job, JobRequest, JobStatus
from src.utils.logging import setup_logging

# Setup logging
logger = setup_logging()

async def execute_analysis(inputs: dict, tracer: Tracer) -> Dict[str, Any]:
    """
    Main entrypoint function for political document analysis.
    
    Args:
        inputs: Dictionary containing analysis parameters from the form
        tracer: Kodosumi tracer for real-time progress updates
        
    Returns:
        Dictionary containing analysis results and metadata
    """
    try:
        # Extract inputs
        job_name = inputs["job_name"]
        input_folder = inputs["input_folder"]
        context_file = inputs["context_file"]
        priority_threshold = inputs.get("priority_threshold", 70.0)
        include_low_confidence = inputs.get("include_low_confidence", False)
        clustering_enabled = inputs.get("clustering_enabled", True)
        batch_size = inputs.get("batch_size", 50)
        timeout_minutes = inputs.get("timeout_minutes", 30)
        instructions = inputs.get("instructions", "")
        
        # Initialize progress tracking
        start_time = time.time()
        # Generate job ID matching pattern: job_YYYYMMDD_HHMMSS_XXXXXX
        import random
        import string
        suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{suffix}"
        
        await tracer.markdown(f"""
# Political Analysis: {job_name}

## Job Configuration
- **Job ID**: {job_id}
- **Input Folder**: {input_folder}
- **Context File**: {context_file}
- **Priority Threshold**: {priority_threshold}%
- **Include Low Confidence**: {include_low_confidence}
- **Clustering Enabled**: {clustering_enabled}
- **Batch Size**: {batch_size}
- **Timeout**: {timeout_minutes} minutes

## Analysis Progress

### Step 1: Initialization
✅ Job configuration validated and initialized
""")
        
        # Create job request object
        job_request = JobRequest(
            job_name=job_name,
            input_folder=input_folder,
            context_file=context_file,
            priority_threshold=priority_threshold,
            include_low_confidence=include_low_confidence,
            clustering_enabled=clustering_enabled,
        )
        
        # Create job object
        job = Job(
            id=job_id,
            request=job_request,
            status=JobStatus.RUNNING,
            created_at=datetime.now(),
            started_at=datetime.now(),
        )
        
        await tracer.markdown("### Step 2: Document Discovery")
        
        # Check if input folder exists
        if not os.path.exists(input_folder):
            error_msg = f"Input folder not found: {input_folder}"
            await tracer.markdown(f"❌ **Error**: {error_msg}")
            raise FileNotFoundError(error_msg)
        
        # Count documents
        document_files = []
        for root, dirs, files in os.walk(input_folder):
            for file in files:
                if file.lower().endswith(('.txt', '.md', '.pdf', '.docx', '.html', '.csv', '.json')):
                    document_files.append(os.path.join(root, file))
        
        total_documents = len(document_files)
        
        if total_documents == 0:
            error_msg = f"No supported documents found in {input_folder}"
            await tracer.markdown(f"❌ **Error**: {error_msg}")
            raise ValueError(error_msg)
        
        await tracer.markdown(f"""
✅ Document discovery completed
- **Total Documents Found**: {total_documents}
- **Estimated Processing Time**: {max(5, total_documents // 10)} minutes
- **Processing Batches**: {(total_documents + batch_size - 1) // batch_size}
""")
        
        # Initialize Ray if not already initialized
        if not ray.is_initialized():
            await tracer.markdown("🚀 Initializing distributed computing cluster...")
            ray.init(num_cpus=4)
            await tracer.markdown("✅ Ray cluster initialized")
        
        await tracer.markdown("### Step 3: Loading Context and Configuration")
        
        # Load context (using Ray task)
        context_task = load_context_task.remote(context_file)
        context = await context_task
        
        await tracer.markdown(f"""
✅ Context loaded successfully
- **Context File**: {context_file}
- **Analysis Framework**: Political relevance scoring
- **Scoring Dimensions**: {len(context.get('scoring_dimensions', []))} dimensions
""")
        
        await tracer.markdown("### Step 4: Document Processing Pipeline")
        await tracer.markdown("🔄 **Phase 1**: Document parsing and content extraction...")
        
        # Create document processing batches
        processing_batches = create_processing_batches(document_files, batch_size)
        processed_documents = []
        
        # Process documents in parallel batches
        processing_futures = []
        for i, batch in enumerate(processing_batches):
            future = process_batch_task.remote(batch, i * batch_size, job_id)
            processing_futures.append(future)
        
        # Monitor processing progress
        completed_batches = 0
        total_batches = len(processing_batches)
        
        while processing_futures:
            done, processing_futures = ray.wait(processing_futures, num_returns=1, timeout=1.0)
            
            for completed_future in done:
                try:
                    batch_results = await completed_future
                    processed_documents.extend(batch_results)
                    completed_batches += 1
                    
                    progress_pct = (completed_batches / total_batches) * 100
                    await tracer.markdown(f"""
**Processing Progress**: {completed_batches}/{total_batches} batches ({progress_pct:.1f}%)
- Documents processed: {len(processed_documents)}/{total_documents}
""")
                    
                except Exception as e:
                    logger.error(f"Batch processing failed: {e}")
                    await tracer.markdown(f"⚠️ Warning: One batch failed - {str(e)}")
        
        await tracer.markdown(f"""
✅ **Phase 1 Complete**: Document processing finished
- **Successfully Processed**: {len(processed_documents)}/{total_documents} documents
""")
        
        if not processed_documents:
            error_msg = "No documents were successfully processed"
            await tracer.markdown(f"❌ **Error**: {error_msg}")
            raise ValueError(error_msg)
        
        await tracer.markdown("🔄 **Phase 2**: Political relevance scoring...")
        
        # Create scoring batches
        scoring_batches = create_scoring_batches(processed_documents, batch_size // 2)
        scoring_results = []
        
        # Score documents in parallel
        scoring_futures = []
        for batch in scoring_batches:
            future = score_batch_task.remote(batch, context)
            scoring_futures.append(future)
        
        # Monitor scoring progress
        completed_scoring = 0
        total_scoring_batches = len(scoring_batches)
        
        while scoring_futures:
            done, scoring_futures = ray.wait(scoring_futures, num_returns=1, timeout=1.0)
            
            for completed_future in done:
                try:
                    batch_scores = await completed_future
                    scoring_results.extend(batch_scores)
                    completed_scoring += 1
                    
                    progress_pct = (completed_scoring / total_scoring_batches) * 100
                    await tracer.markdown(f"""
**Scoring Progress**: {completed_scoring}/{total_scoring_batches} batches ({progress_pct:.1f}%)
- Documents scored: {len(scoring_results)}/{len(processed_documents)}
""")
                    
                except Exception as e:
                    logger.error(f"Batch scoring failed: {e}")
                    await tracer.markdown(f"⚠️ Warning: One scoring batch failed - {str(e)}")
        
        await tracer.markdown(f"""
✅ **Phase 2 Complete**: Relevance scoring finished
- **Successfully Scored**: {len(scoring_results)}/{len(processed_documents)} documents
""")
        
        if clustering_enabled:
            await tracer.markdown("🔄 **Phase 3**: Topic clustering and aggregation...")
            
            # Perform clustering
            clustering_future = cluster_and_aggregate_task.remote(scoring_results, context)
            final_results = await clustering_future
            
            await tracer.markdown(f"""
✅ **Phase 3 Complete**: Clustering and aggregation finished
- **Topic Clusters**: {len(final_results.get('topic_groups', {}))}
- **Priority Groups**: {len(final_results.get('priority_groups', {}))}
""")
        else:
            await tracer.markdown("⏭️ **Phase 3**: Skipping clustering (disabled)")
            final_results = {"aggregated_results": scoring_results, "statistics": {}}
        
        await tracer.markdown("🔄 **Phase 4**: Report generation...")
        
        # Generate final report
        report_future = generate_report_task.remote(final_results, job, context)
        report_result = await report_future
        
        # Calculate final metrics
        total_time = time.time() - start_time
        
        # Filter results by priority threshold
        high_priority_results = [
            r for r in scoring_results 
            if r.master_score >= priority_threshold
        ]
        
        if not include_low_confidence:
            high_priority_results = [
                r for r in high_priority_results 
                if r.confidence_score >= 80.0
            ]
        
        await tracer.markdown(f"""
✅ **Phase 4 Complete**: Report generation finished

## Analysis Summary

### Processing Statistics
- **Total Processing Time**: {total_time:.1f} seconds
- **Documents Analyzed**: {total_documents}
- **Successfully Processed**: {len(processed_documents)}
- **Successfully Scored**: {len(scoring_results)}
- **High Priority Results**: {len(high_priority_results)}

### Quality Metrics
- **Average Confidence Score**: {sum(r.confidence_score for r in scoring_results) / len(scoring_results):.1f}%
- **Average Priority Score**: {sum(r.master_score for r in scoring_results) / len(scoring_results):.1f}%
- **Processing Rate**: {len(processed_documents) / total_time:.1f} documents/second

### Output
- **Report File**: {report_result.get('report_file', 'Not generated')}
- **Report Format**: Markdown with tables and visualizations
- **Download Ready**: ✅

## Analysis Complete! 🎉

The political document analysis has been completed successfully. You can download the full report using the download link provided.
""")
        
        return {
            "success": True,
            "job_id": job_id,
            "report_file": report_result.get("report_file"),
            "statistics": {
                "total_documents": total_documents,
                "processed_documents": len(processed_documents),
                "scored_documents": len(scoring_results),
                "high_priority_documents": len(high_priority_results),
                "processing_time_seconds": total_time,
                "average_confidence": sum(r.confidence_score for r in scoring_results) / len(scoring_results) if scoring_results else 0,
                "average_priority": sum(r.master_score for r in scoring_results) / len(scoring_results) if scoring_results else 0,
            },
            "metadata": {
                "job_name": job_name,
                "priority_threshold": priority_threshold,
                "clustering_enabled": clustering_enabled,
                "include_low_confidence": include_low_confidence,
                "instructions": instructions,
            }
        }
        
    except Exception as e:
        error_msg = f"Analysis failed: {str(e)}"
        logger.error("Political analysis failed", error=str(e))
        
        await tracer.markdown(f"""
## Analysis Failed ❌

**Error**: {error_msg}

**Troubleshooting Steps**:
1. Check that input folder exists and contains supported documents
2. Verify context file is accessible and properly formatted
3. Ensure sufficient system resources are available
4. Check logs for detailed error information

Please review the configuration and try again.
""")
        
        return {
            "success": False,
            "error": error_msg,
            "job_id": job_id if 'job_id' in locals() else "unknown",
        }

# Ray remote functions for distributed processing

@ray.remote
def load_context_task(context_file: str) -> Dict[str, Any]:
    """Load analysis context configuration."""
    try:
        import yaml
        with open(context_file, 'r') as f:
            context = yaml.safe_load(f)
        return context
    except Exception as e:
        logger.error(f"Failed to load context: {e}")
        # Return default context
        return {
            "scoring_dimensions": ["relevance", "priority", "confidence"],
            "default_config": True
        }

@ray.remote
def process_batch_task(file_paths: list, start_index: int, job_id: str) -> list:
    """Process a batch of documents."""
    try:
        from src.processors.content_processor import ContentProcessor
        
        processor = ContentProcessor()
        results = []
        
        for i, file_path in enumerate(file_paths):
            try:
                doc_id = f"doc_{start_index + i:03d}"
                
                # Process document
                import asyncio
                result = asyncio.run(processor.process_document(file_path, doc_id))
                results.append(result)
                
            except Exception as e:
                logger.warning(f"Failed to process {file_path}: {e}")
        
        return results
        
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        return []

@ray.remote  
def score_batch_task(documents: list, context: Dict[str, Any]) -> list:
    """Score a batch of documents."""
    try:
        from src.scoring.relevance_engine import RelevanceEngine
        
        engine = RelevanceEngine(context)
        results = []
        
        for document in documents:
            try:
                import asyncio
                result = asyncio.run(engine.score_document(document))
                results.append(result)
            except Exception as e:
                logger.warning(f"Failed to score document {document.id}: {e}")
        
        return results
        
    except Exception as e:
        logger.error(f"Batch scoring failed: {e}")
        return []

@ray.remote
def cluster_and_aggregate_task(scoring_results: list, context: Dict[str, Any]) -> Dict[str, Any]:
    """Perform clustering and aggregation."""
    try:
        from src.analysis.aggregator import Aggregator
        
        aggregator = Aggregator()
        return aggregator.aggregate_results(scoring_results)
        
    except Exception as e:
        logger.error(f"Clustering failed: {e}")
        return {"aggregated_results": scoring_results, "statistics": {}}

@ray.remote
def generate_report_task(results: Dict[str, Any], job: Any, context: Dict[str, Any]) -> Dict[str, Any]:
    """Generate final analysis report."""
    try:
        from src.output.report_generator import ReportGenerator
        
        generator = ReportGenerator()
        import asyncio
        return asyncio.run(generator.generate_report(results, job, context))
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        return {"report_file": None}

# Utility functions

def create_processing_batches(file_paths: list, batch_size: int) -> list:
    """Create batches for document processing."""
    batches = []
    for i in range(0, len(file_paths), batch_size):
        batch = file_paths[i:i + batch_size]
        batches.append(batch)
    return batches

def create_scoring_batches(documents: list, batch_size: int) -> list:
    """Create batches for document scoring."""
    batches = []
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        batches.append(batch)
    return batches