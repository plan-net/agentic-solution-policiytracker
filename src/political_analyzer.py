# political_analyzer.py - Kodosumi Entrypoint for Political Analysis
import asyncio
import os
import time
from datetime import datetime
from typing import Any, Dict

import ray
from kodosumi.core import Tracer
import kodosumi.core as core
import structlog

from src.models.job import Job, JobRequest, JobStatus
from src.utils.logging import setup_logging
from src.config import settings

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
        priority_threshold = inputs.get("priority_threshold", 70.0)
        include_low_confidence = inputs.get("include_low_confidence", False)
        clustering_enabled = inputs.get("clustering_enabled", True)
        batch_size = inputs.get("batch_size", 50)
        timeout_minutes = inputs.get("timeout_minutes", 30)
        instructions = inputs.get("instructions", "")
        storage_mode = inputs.get("storage_mode", "local")
        
        # Determine use_azure based on storage_mode or config
        use_azure = (storage_mode == "azure") if storage_mode else settings.USE_AZURE_STORAGE
        
        # Get paths from configuration based on runtime storage mode
        if use_azure:
            input_folder = settings.AZURE_INPUT_PATH
            context_file = settings.AZURE_CONTEXT_PATH
        else:
            # Use hard-coded local paths for reliability
            input_folder = "./data/input" 
            context_file = "./data/context/client.yaml"
        
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
- **Storage Mode**: {"Azure Blob Storage" if use_azure else "Local Filesystem"}
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
        
        await tracer.markdown("### Step 2: Workflow Execution")
        
        # Import workflow functions
        from src.workflow.graph import create_workflow, execute_workflow
        from src.workflow.state import WorkflowState
        
        # Initialize Ray if not already initialized
        if not ray.is_initialized():
            await tracer.markdown("🚀 Initializing distributed computing cluster...")
            ray.init(num_cpus=4)
            await tracer.markdown("✅ Ray cluster initialized")
        
        # Create initial workflow state with runtime storage mode
        initial_state = WorkflowState(
            job_id=job_id,
            job_request=job_request,
            use_azure=use_azure  # ⭐ This is the key fix!
        )
        
        await tracer.markdown(f"""
### Step 3: Starting LangGraph Workflow
- **Storage Mode**: {"Azure Blob Storage" if use_azure else "Local Filesystem"}
- **Input Path**: {input_folder}
- **Context Path**: {context_file}
""")
        
        # Create and execute workflow
        workflow = create_workflow()
        
        try:
            result = await execute_workflow(workflow, job, resume_from_checkpoint=None, initial_state=initial_state)
            
            # Read the generated report file and return its content for Kodosumi display
            report_file_path = result['report_file']
            
            if report_file_path and os.path.exists(report_file_path):
                # Read the generated report content
                with open(report_file_path, 'r', encoding='utf-8') as f:
                    report_content = f.read()
                
                # Add execution summary at the top
                execution_summary = f"""# Political Analysis Complete! 🎉

## Execution Summary
- **Job ID**: {job_id}
- **Total Documents**: {result['metrics']['total_documents']}
- **Processed Successfully**: {result['metrics']['processed_documents']}
- **High Priority Items**: {result['metrics']['summary']['high_priority_count']}
- **Average Score**: {result['metrics']['summary']['average_score']:.1f}%
- **Processing Time**: {time.time() - start_time:.1f} seconds
- **Storage Mode**: {"Azure Blob Storage" if use_azure else "Local Filesystem"}
- **Report File**: `{report_file_path}`

---

"""
                
                # Return the complete report as a Kodosumi Markdown response for proper FINAL display
                await tracer.markdown("### ✅ Analysis Complete! Report ready for viewing.")
                
                return core.response.Markdown(execution_summary + report_content)
                
            else:
                await tracer.markdown(f"""### ⚠️ Analysis completed but report file not found

**Job ID**: {job_id}
**Status**: Analysis completed successfully but report file could not be read.
**Report Path**: {report_file_path}

Please check the output directory for the generated report.
""")
            
        except Exception as workflow_error:
            error_msg = f"Workflow execution failed: {str(workflow_error)}"
            await tracer.markdown(f"""
### ❌ Workflow Failed

**Error**: {error_msg}

Please check the configuration and try again.
""")
            logger.error(error_msg, exc_info=True)
            
    except Exception as e:
        error_msg = f"Analysis failed: {str(e)}"
        logger.error("Political analysis failed", error=str(e))
        
        return core.response.Markdown(f"""# Analysis Failed ❌

**Error**: {error_msg}

**Job ID**: {job_id if 'job_id' in locals() else "unknown"}

**Troubleshooting Steps**:
1. Check that input folder exists and contains supported documents
2. Verify context file is accessible and properly formatted
3. Ensure sufficient system resources are available
4. Check logs for detailed error information

Please review the configuration and try again.
""")