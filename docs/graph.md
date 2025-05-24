# Political Monitoring Agent - Workflow Graph & Architecture

## Overview

The Political Monitoring Agent uses a **LangGraph-based workflow** with **Ray distributed computing** for scalable document analysis. The system combines state management with distributed processing to handle large document sets efficiently.

## High-Level Architecture

```mermaid
graph TB
    subgraph "Kodosumi Layer"
        WEB[Web Form - app.py]
        ENTRY[Entrypoint - political_analyzer.py]
    end
    
    subgraph "Workflow Engine"
        LANG[LangGraph Workflow]
        STATE[WorkflowState]
        CHECK[Checkpointer]
    end
    
    subgraph "Ray Distribution Layer"
        RAY_HEAD[Ray Head Node]
        RAY_TASKS[Ray Remote Tasks]
        RAY_ACTORS[Ray Actors]
    end
    
    subgraph "Storage Layer"
        LOCAL[Local Files]
        AZURE[Azure Blob Storage]
        AZURITE[Azurite Emulator]
    end
    
    WEB --> ENTRY
    ENTRY --> LANG
    LANG --> STATE
    LANG --> CHECK
    LANG --> RAY_TASKS
    RAY_TASKS --> RAY_HEAD
    STATE --> LOCAL
    STATE --> AZURE
    CHECK --> AZURITE
```

## Detailed Workflow Graph

### 1. Kodosumi Entry Point Flow

```mermaid
sequenceDiagram
    participant User
    participant WebForm as Web Form (app.py)
    participant Analyzer as Political Analyzer
    participant Tracer as Kodosumi Tracer
    
    User->>WebForm: Submit analysis request
    WebForm->>WebForm: Validate inputs
    WebForm->>Analyzer: Launch(execute_analysis)
    Analyzer->>Tracer: Update progress markdown
    Analyzer->>Analyzer: Initialize Ray cluster
    Note over Analyzer: Ray.init() if needed
    Analyzer->>Analyzer: Create workflow
    Analyzer->>Tracer: Stream real-time updates
```

### 2. LangGraph Workflow Nodes

```mermaid
flowchart TD
    START([Workflow Start]) --> LOAD_DOCS[load_documents]
    LOAD_DOCS --> LOAD_CTX[load_context]
    LOAD_CTX --> PROCESS[process_documents]
    PROCESS --> SCORE[score_documents]
    SCORE --> CLUSTER[cluster_results]
    CLUSTER --> REPORT[generate_report]
    REPORT --> END([Workflow End])
    
    %% Error handling
    LOAD_DOCS -.->|Error| ERROR[Error Handler]
    LOAD_CTX -.->|Error| ERROR
    PROCESS -.->|Error| ERROR
    SCORE -.->|Error| ERROR
    CLUSTER -.->|Error| ERROR
    REPORT -.->|Error| ERROR
    
    %% Checkpointing
    LOAD_DOCS -.->|Save| CHECKPOINT[(Checkpointer)]
    LOAD_CTX -.->|Save| CHECKPOINT
    PROCESS -.->|Save| CHECKPOINT
    SCORE -.->|Save| CHECKPOINT
    CLUSTER -.->|Save| CHECKPOINT
    
    %% State updates
    LOAD_DOCS --> STATE[(WorkflowState)]
    LOAD_CTX --> STATE
    PROCESS --> STATE
    SCORE --> STATE
    CLUSTER --> STATE
    REPORT --> STATE
    
    classDef workflow fill:#e1f5fe
    classDef storage fill:#f3e5f5
    classDef error fill:#ffebee
    
    class LOAD_DOCS,LOAD_CTX,PROCESS,SCORE,CLUSTER,REPORT workflow
    class CHECKPOINT,STATE storage
    class ERROR error
```

## Ray Distributed Computing Integration

### 3. Ray Remote Functions & Actors

```mermaid
graph LR
    subgraph "Workflow Nodes"
        WN1[load_documents]
        WN2[process_documents]
        WN3[score_documents]
        WN4[cluster_results]
    end
    
    subgraph "Ray Tasks (ray_tasks.py)"
        RT1["@ray.remote<br/>process_document_task"]
        RT2["@ray.remote<br/>batch_processing_task"]
        RT3["@ray.remote<br/>score_document_task"]
        RT4["@ray.remote<br/>batch_scoring_task"]
        RT5["@ray.remote<br/>batch_aggregation_task"]
    end
    
    subgraph "Ray Workers"
        RW1[Ray Worker 1]
        RW2[Ray Worker 2]
        RW3[Ray Worker 3]
        RW4[Ray Worker N...]
    end
    
    WN2 --> RT1
    WN2 --> RT2
    WN3 --> RT3
    WN3 --> RT4
    WN4 --> RT5
    
    RT1 --> RW1
    RT2 --> RW2
    RT3 --> RW3
    RT4 --> RW4
    RT5 --> RW1
    
    classDef workflow fill:#e8f5e8
    classDef ray fill:#fff3e0
    classDef worker fill:#f1f8e9
    
    class WN1,WN2,WN3,WN4 workflow
    class RT1,RT2,RT3,RT4,RT5 ray
    class RW1,RW2,RW3,RW4 worker
```

### 4. Ray Task Distribution Patterns

#### Document Processing Distribution
```mermaid
flowchart TD
    DOCS[1000 Documents] --> BATCH_SPLIT[Split into 20 batches<br/>50 docs each]
    BATCH_SPLIT --> BATCH1["Batch 1 (1-50)<br/>@ray.remote<br/>batch_processing_task"]
    BATCH_SPLIT --> BATCH2["Batch 2 (51-100)<br/>@ray.remote<br/>batch_processing_task"]
    BATCH_SPLIT --> BATCH3["Batch 3 (101-150)<br/>@ray.remote<br/>batch_processing_task"]
    BATCH_SPLIT --> BATCHN["Batch N...<br/>@ray.remote<br/>batch_processing_task"]
    
    BATCH1 --> WORKER1[Ray Worker 1]
    BATCH2 --> WORKER2[Ray Worker 2]
    BATCH3 --> WORKER3[Ray Worker 3]
    BATCHN --> WORKERN[Ray Worker N]
    
    WORKER1 --> RESULT1[Processed Content 1-50]
    WORKER2 --> RESULT2[Processed Content 51-100]
    WORKER3 --> RESULT3[Processed Content 101-150]
    WORKERN --> RESULTN[Processed Content N...]
    
    RESULT1 --> AGGREGATE["@ray.remote<br/>batch_aggregation_task"]
    RESULT2 --> AGGREGATE
    RESULT3 --> AGGREGATE
    RESULTN --> AGGREGATE
    
    AGGREGATE --> FINAL[Final Aggregated Results]
```

#### Scoring Distribution
```mermaid
flowchart TD
    PROCESSED[Processed Documents] --> SCORE_SPLIT[Split into batches<br/>20 docs each]
    SCORE_SPLIT --> SCORE1["Batch 1<br/>@ray.remote<br/>batch_scoring_task"]
    SCORE_SPLIT --> SCORE2["Batch 2<br/>@ray.remote<br/>batch_scoring_task"]
    SCORE_SPLIT --> SCORE3["Batch 3<br/>@ray.remote<br/>batch_scoring_task"]
    
    SCORE1 --> SW1[Scoring Worker 1]
    SCORE2 --> SW2[Scoring Worker 2]
    SCORE3 --> SW3[Scoring Worker 3]
    
    SW1 --> SR1[Scoring Results 1]
    SW2 --> SR2[Scoring Results 2]
    SW3 --> SR3[Scoring Results 3]
    
    SR1 --> SCORE_AGG["@ray.remote<br/>batch_aggregation_task"]
    SR2 --> SCORE_AGG
    SR3 --> SCORE_AGG
    
    SCORE_AGG --> FINAL_SCORES[Final Scored Results]
```

## Ray Remote Functions Detail

### Core Ray Tasks (src/tasks/ray_tasks.py)

| Function | Decorator | Purpose | Input | Output |
|----------|-----------|---------|-------|---------|
| `process_document_task` | `@ray.remote(max_retries=3)` | Process single document | file_path, doc_id | ProcessedContent |
| `batch_processing_task` | `@ray.remote` | Process document batch | file_paths[], start_index | ProcessedContent[] |
| `score_document_task` | `@ray.remote(max_retries=2)` | Score single document | ProcessedContent, context | ScoringResult |
| `batch_scoring_task` | `@ray.remote` | Score document batch | ProcessedContent[], context | ScoringResult[] |
| `batch_aggregation_task` | `@ray.remote` | Aggregate results | ScoringResult[] | Dict[statistics] |

### Ray Task Execution Flow

```python
# Example: Batch Processing Distribution
@ray.remote
def batch_processing_task(file_paths: List[str], start_index: int) -> List[ProcessedContent]:
    """
    Ray remote function for parallel document processing
    - Runs on Ray worker nodes
    - Handles asyncio.run() for async functions
    - Includes error handling and logging
    - Returns processed content list
    """
    
# Example: Batch Scoring Distribution  
@ray.remote
def batch_scoring_task(documents: List[ProcessedContent], context: Dict[str, Any]) -> List[ScoringResult]:
    """
    Ray remote function for parallel document scoring
    - Distributes scoring across workers
    - Calculates processing time metrics
    - Includes retry logic via max_retries
    - Returns scoring results list
    """
```

## Storage Integration Patterns

### 5. Storage Mode Flow

```mermaid
flowchart TD
    START[Start Workflow] --> STORAGE_CHECK{Storage Mode?}
    
    STORAGE_CHECK -->|Local| LOCAL_PATH[Use ./data/input<br/>./data/context<br/>./data/output]
    STORAGE_CHECK -->|Azure| AZURE_PATH[Use Azure paths<br/>jobs/{job_id}/input<br/>context/client.yaml<br/>jobs/{job_id}/output]
    
    LOCAL_PATH --> LOCAL_OPS[Local File Operations]
    AZURE_PATH --> AZURE_OPS[Azure Blob Operations]
    
    LOCAL_OPS --> WORKFLOW[LangGraph Workflow]
    AZURE_OPS --> WORKFLOW
    
    WORKFLOW --> CHECKPOINT_CHECK{Checkpointing?}
    
    CHECKPOINT_CHECK -->|Local| MEMORY_CHECKPOINT[MemorySaver]
    CHECKPOINT_CHECK -->|Azure| AZURE_CHECKPOINT[AzureCheckpointSaver]
    
    MEMORY_CHECKPOINT --> EXECUTE[Execute Workflow]
    AZURE_CHECKPOINT --> EXECUTE
    
    EXECUTE --> RESULTS[Final Results]
```

### 6. Azure Storage Integration

```mermaid
sequenceDiagram
    participant WF as Workflow Node
    participant AC as AzureStorageClient
    participant BLOB as Azure Blob Storage
    participant CP as AzureCheckpointSaver
    
    Note over WF: Document Loading
    WF->>AC: download_blob('input-documents', path)
    AC->>BLOB: Download file
    BLOB->>AC: File content
    AC->>WF: ProcessedContent
    
    Note over WF: Context Loading
    WF->>AC: download_blob('contexts', 'client.yaml')
    AC->>BLOB: Download context
    BLOB->>AC: YAML content
    AC->>WF: Parsed context
    
    Note over WF: Checkpointing
    WF->>CP: Save checkpoint
    CP->>AC: upload_json('checkpoints', checkpoint)
    AC->>BLOB: Store checkpoint
    
    Note over WF: Report Generation
    WF->>AC: upload_blob('reports', report.md)
    AC->>BLOB: Store report
    BLOB->>AC: Success confirmation
    AC->>WF: Upload complete
```

## Error Handling & Recovery

### 7. Error Flow & Recovery Patterns

```mermaid
flowchart TD
    TASK_START[Ray Task Start] --> TASK_EXEC[Execute Task]
    TASK_EXEC --> SUCCESS{Success?}
    
    SUCCESS -->|Yes| TASK_COMPLETE[Task Complete]
    SUCCESS -->|No| ERROR_CHECK{Max Retries?}
    
    ERROR_CHECK -->|Not Exceeded| RETRY[Retry Task<br/>@ray.remote(max_retries=3)]
    ERROR_CHECK -->|Exceeded| FAIL_HANDLE[Fail Gracefully]
    
    RETRY --> TASK_EXEC
    FAIL_HANDLE --> LOG_ERROR[Log Error]
    LOG_ERROR --> CONTINUE[Continue with Other Tasks]
    
    TASK_COMPLETE --> WORKFLOW_CONTINUE[Continue Workflow]
    CONTINUE --> WORKFLOW_CONTINUE
    
    classDef success fill:#e8f5e8
    classDef error fill:#ffebee
    classDef retry fill:#fff3e0
    
    class TASK_COMPLETE,WORKFLOW_CONTINUE success
    class FAIL_HANDLE,LOG_ERROR error
    class RETRY,ERROR_CHECK retry
```

## Progress Tracking & Real-time Updates

### 8. Progress Streaming Flow

```mermaid
sequenceDiagram
    participant User
    participant Tracer as Kodosumi Tracer
    participant Workflow as LangGraph Workflow
    participant Ray as Ray Tasks
    participant State as WorkflowState
    
    User->>Tracer: Start analysis
    Tracer->>Workflow: Initialize workflow
    
    loop For each workflow node
        Workflow->>State: Update progress
        State->>Tracer: Stream progress update
        Tracer->>User: Display progress markdown
        
        Workflow->>Ray: Launch distributed tasks
        Ray->>Ray: Process in parallel
        Ray->>Workflow: Return results
    end
    
    Workflow->>State: Final results
    State->>Tracer: Completion update
    Tracer->>User: Final report & results
```

## Checkpointing & Resume Capability

### 9. Checkpoint Flow

```mermaid
flowchart TD
    WORKFLOW_START[Workflow Start] --> CHECKPOINT_CONFIG{Checkpointing Enabled?}
    
    CHECKPOINT_CONFIG -->|Yes| CREATE_CHECKPOINTER[Create Checkpointer]
    CHECKPOINT_CONFIG -->|No| NO_CHECKPOINT[No Checkpointing]
    
    CREATE_CHECKPOINTER --> STORAGE_TYPE{Storage Type?}
    STORAGE_TYPE -->|Local| MEMORY_SAVER[MemorySaver]
    STORAGE_TYPE -->|Azure| AZURE_SAVER[AzureCheckpointSaver]
    
    MEMORY_SAVER --> EXECUTE_WORKFLOW[Execute Workflow]
    AZURE_SAVER --> EXECUTE_WORKFLOW
    NO_CHECKPOINT --> EXECUTE_WORKFLOW
    
    EXECUTE_WORKFLOW --> NODE_COMPLETE[Node Complete]
    NODE_COMPLETE --> SAVE_CHECKPOINT[Save Checkpoint]
    
    SAVE_CHECKPOINT --> MORE_NODES{More Nodes?}
    MORE_NODES -->|Yes| NEXT_NODE[Next Node]
    MORE_NODES -->|No| WORKFLOW_END[Workflow End]
    
    NEXT_NODE --> NODE_COMPLETE
    
    WORKFLOW_END --> CLEANUP[Cleanup Old Checkpoints]
    CLEANUP --> FINAL_RESULT[Return Results]
    
    classDef checkpoint fill:#e1f5fe
    classDef storage fill:#f3e5f5
    
    class SAVE_CHECKPOINT,CLEANUP checkpoint
    class MEMORY_SAVER,AZURE_SAVER storage
```

## Performance Characteristics

### Ray Distribution Benefits

1. **Parallel Document Processing**: Documents split into batches (default: 50 per batch)
2. **Concurrent Scoring**: Scoring distributed across available workers (default: 20 per batch)
3. **Automatic Retry Logic**: Failed tasks automatically retry (max_retries=3)
4. **Resource Management**: Ray manages worker allocation and load balancing
5. **Fault Tolerance**: Individual task failures don't crash entire workflow

### Scalability Patterns

- **Horizontal Scaling**: Add more Ray workers to increase throughput
- **Batch Size Tuning**: Adjust batch sizes based on document complexity
- **Resource Allocation**: Configure CPU/memory per Ray actor
- **Storage Optimization**: Azure Blob Storage for unlimited document storage

### Monitoring & Observability

- **Ray Dashboard**: Monitor cluster resources and task execution
- **Langfuse Integration**: Track LLM usage and performance
- **Structured Logging**: Comprehensive logging throughout the pipeline
- **Real-time Progress**: Live updates via Kodosumi Tracer
- **Checkpoint Inspection**: View and resume from workflow checkpoints

This architecture provides a robust, scalable foundation for political document analysis with clear separation of concerns, fault tolerance, and comprehensive monitoring capabilities.