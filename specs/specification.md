# Political Monitoring Agent - Technical Specification for AI Implementation

## Document Metadata

| Field | Value |
|-------|-------|
| **Project Name** | Political Monitoring Agent |
| **Specification Version** | 1.0 |
| **Date** | 23.05.2025 |
| **Target Implementation** | Claude Code |
| **Runtime Environment** | Kodosumi on Ray |
| **Architecture Version** | 3.0 (Manual Trigger) |

---

## 1. Complete Project Structure Definition

Create the following directory structure exactly as specified:

```
political-monitoring-agent/
├── src/
│   ├── __init__.py                    # Empty file for Python package
│   ├── serve.py                       # Main Kodosumi FastAPI entry point
│   ├── config.py                      # Configuration management using pydantic-settings
│   ├── models/
│   │   ├── __init__.py
│   │   ├── job.py                     # Job request and status models
│   │   ├── content.py                 # Document and content models
│   │   ├── scoring.py                 # Scoring result models
│   │   └── report.py                  # Report generation models
│   ├── workflow/
│   │   ├── __init__.py
│   │   ├── graph.py                   # LangGraph workflow definition
│   │   ├── nodes.py                   # Individual workflow nodes
│   │   └── state.py                   # Workflow state management
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── document_reader.py         # Multi-format document parsing
│   │   ├── content_processor.py       # Content extraction and normalization
│   │   ├── context_manager.py         # Client context file loading
│   │   └── batch_loader.py            # Batch document loading from filesystem
│   ├── scoring/
│   │   ├── __init__.py
│   │   ├── relevance_engine.py        # Main scoring orchestration
│   │   ├── dimensions.py              # Five dimension scorer implementations
│   │   ├── confidence.py              # Confidence calculation logic
│   │   └── justification.py           # Score justification generation
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── topic_clusterer.py         # Document clustering by topic
│   │   ├── priority_classifier.py     # Priority level assignment
│   │   └── aggregator.py              # Result aggregation for reporting
│   ├── output/
│   │   ├── __init__.py
│   │   ├── report_generator.py        # Markdown report generation
│   │   ├── templates/
│   │   │   ├── report.md.j2           # Main report Jinja2 template
│   │   │   ├── summary.md.j2          # Executive summary template
│   │   │   └── cluster.md.j2          # Topic cluster section template
│   │   └── formatter.py               # Markdown formatting utilities
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── ray_tasks.py               # Ray remote task decorators
│   │   └── task_manager.py            # Task distribution and monitoring
│   └── utils/
│       ├── __init__.py
│       ├── logging.py                 # Structured logging setup
│       ├── validators.py              # Input validation functions
│       └── exceptions.py              # Custom exception classes
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # Pytest fixtures and configuration
│   ├── fixtures/
│   │   ├── __init__.py
│   │   ├── documents.py               # Sample document fixtures
│   │   ├── contexts.py                # Sample context fixtures
│   │   └── expected_outputs.py        # Expected result fixtures
│   ├── unit/                          # Unit tests for each module
│   ├── integration/                   # Integration tests
│   └── test_data/                     # Test documents and contexts
├── config.yaml                        # Kodosumi deployment configuration
├── requirements.txt                   # Python dependencies with exact versions
├── .env.template                      # Environment variable template
├── Dockerfile                         # Container definition
├── docker-compose.yml                 # Local development setup
└── README.md                          # Project documentation
```

---

## 2. Exact Dependencies & Environment Setup

### requirements.txt (exact versions required)
```
# Core Framework
kodosumi==0.1.0
ray[serve]==2.46.0
fastapi==0.104.1
uvicorn==0.24.0

# Workflow & State Management  
langgraph==0.2.3
pydantic==2.5.0
pydantic-settings==2.1.0

# Document Processing
pypdf2==3.0.1
python-docx==1.1.0
markdown==3.5.1
beautifulsoup4==4.12.2
lxml==4.9.3

# AI/ML Components
numpy==1.26.2
scikit-learn==1.3.2
tiktoken==0.5.2

# Output Generation
jinja2==3.1.2
tabulate==0.9.0

# Utilities
python-dotenv==1.0.0
pyyaml==6.0.1
aiofiles==23.2.1
httpx==0.25.2

# Monitoring & Logging
structlog==23.2.0
prometheus-client==0.19.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-mock==3.12.0
faker==20.1.0
```

### .env.template
```bash
# Kodosumi Configuration
KODOSUMI_SERVICE_NAME=political-monitoring
KODOSUMI_SERVICE_PORT=8000

# Ray Configuration
RAY_ADDRESS=auto
RAY_NUM_CPUS=8
RAY_TASK_MAX_RETRIES=3

# Application Settings
DEFAULT_INPUT_FOLDER=/data/input
DEFAULT_OUTPUT_FOLDER=/data/output
DEFAULT_CONTEXT_FOLDER=/data/context
MAX_BATCH_SIZE=1000
PROCESSING_TIMEOUT_SECONDS=600
MAX_DOCUMENT_SIZE_MB=50

# Scoring Configuration
CONFIDENCE_THRESHOLD=0.7
MIN_RELEVANCE_SCORE=0
MAX_RELEVANCE_SCORE=100

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
ENABLE_PERFORMANCE_LOGGING=true
```

---

## 3. Complete Data Models with Validation Rules

### Job Models (src/models/job.py)

```python
# Define these exact Pydantic models with all validation:

JobStatus enum:
- PENDING, RUNNING, COMPLETED, FAILED, CANCELLED

JobRequest model fields:
- job_name: str (1-100 chars, required)
- input_folder: str (default="/data/input", no path traversal)
- context_file: str (default="/data/context/client.yaml", no path traversal)
- priority_threshold: float (0-100, default=70.0)
- include_low_confidence: bool (default=False)
- clustering_enabled: bool (default=True)

Job model fields:
- id: str (format: "job_YYYYMMDD_HHMMSS_XXXXXX")
- request: JobRequest
- status: JobStatus
- created_at, started_at, completed_at: datetime
- error_message: Optional[str]
- result_file: Optional[str]
- metrics: Dict[str, Any]

Validation rules:
- Path validation to prevent traversal attacks (no ".." or "~")
- Threshold values must be 0-100
- Job ID format validation
```

### Content Models (src/models/content.py)

```python
DocumentType enum:
- MARKDOWN, PDF, DOCX, TXT, HTML

DocumentMetadata fields:
- source: str (required)
- type: DocumentType (required)
- file_path: str (required)
- file_size_bytes: int (required)
- created_at, modified_at: Optional[datetime]
- author: Optional[str]
- tags: List[str]
- extraction_metadata: Dict[str, Any]

ProcessedContent fields:
- id: str (format: "doc_XXX")
- raw_text: str (non-empty, trimmed)
- metadata: DocumentMetadata
- processing_timestamp: datetime
- word_count: int (auto-calculated)
- language: str (default="en")
- sections: List[Dict[str, str]]
- extraction_errors: List[str]

ContentBatch fields:
- batch_id: str
- job_id: str
- documents: List[ProcessedContent]
- total_documents: int (auto-calculated)
- created_at: datetime
```

### Scoring Models (src/models/scoring.py)

```python
ConfidenceLevel enum:
- HIGH (>=0.8), MEDIUM (0.6-0.8), LOW (<0.6)

PriorityLevel enum:
- CRITICAL (>=90), HIGH (75-90), MEDIUM (50-75), LOW (25-50), INFORMATIONAL (<25)

DimensionScore fields:
- dimension_name: str
- score: float (0-100)
- weight: float (0-1)
- justification: str
- evidence_snippets: List[str] (max 3)

ScoringResult fields:
- document_id: str
- master_score: float (0-100)
- dimension_scores: Dict[str, DimensionScore]
- confidence_score: float (0-1)
- confidence_level: ConfidenceLevel (auto-calculated)
- priority_level: PriorityLevel (auto-calculated)
- topic_clusters: List[str] (max 5)
- scoring_timestamp: datetime
- processing_time_ms: float
- overall_justification: str
- key_factors: List[str]

BatchScoringResults fields:
- job_id: str
- total_documents, scored_documents, failed_documents: int
- results: List[ScoringResult]
- average_score: float
- score_distribution: Dict[str, int]
- topic_distribution: Dict[str, int]
- total_processing_time_seconds: float
- average_processing_time_ms: float
```

### Report Models (src/models/report.py)

```python
TopicCluster fields:
- topic_name: str
- topic_description: str
- document_count: int
- average_score: float
- documents: List[ScoringResult]
- key_themes: List[str]

PriorityQueue fields:
- priority_level: PriorityLevel
- document_count: int
- documents: List[ScoringResult]

ReportSummary fields:
- total_documents_analyzed: int
- high_priority_count: int
- key_findings: List[str]
- recommended_actions: List[str]
- processing_time_minutes: float
- confidence_overview: Dict[str, int]

ReportData fields:
- job_id: str
- job_name: str
- generation_timestamp: datetime
- summary: ReportSummary
- priority_queues: List[PriorityQueue]
- topic_clusters: List[TopicCluster]
- all_results: List[ScoringResult]
- failed_documents: List[Dict[str, str]]
- context_file_used: str
- parameters_used: Dict[str, Any]
- performance_metrics: Dict[str, float]
```

---

## 4. API Endpoint Specifications

### Kodosumi Service Endpoints (src/serve.py)

```python
# Implement these exact endpoints with FastAPI:

POST /analyze
- Purpose: Submit new analysis job
- Form fields:
  - job_name: str (required)
  - input_folder: str (optional)
  - context_file: str (optional)
  - priority_threshold: float (optional)
  - include_low_confidence: bool (optional)
  - clustering_enabled: bool (optional)
- Response: {"job_id": str, "status": str, "message": str, "status_url": str, "estimated_completion_minutes": int}
- Background task: Trigger workflow execution

GET /jobs/{job_id}/status
- Purpose: Get job status and progress
- Response varies by status:
  - Pending: basic info
  - Running: includes progress metrics
  - Completed: includes result URL and summary
  - Failed: includes error message

GET /jobs/{job_id}/result
- Purpose: Download markdown report
- Returns: File download (text/markdown)
- Only available for completed jobs

GET /jobs
- Purpose: List all jobs with pagination
- Query params: limit (default=20), offset (default=0)
- Response: {"total": int, "limit": int, "offset": int, "jobs": List[JobInfo]}

DELETE /jobs/{job_id}
- Purpose: Cancel pending/running job
- Response: {"job_id": str, "status": "cancelled", "message": str}

GET /health
- Purpose: Health check
- Response: {"status": "healthy", "service": str, "version": str, "timestamp": str}
```

---

## 5. Workflow Implementation Specifications

### LangGraph Workflow (src/workflow/graph.py)

```python
# Define workflow with these exact nodes and edges:

Workflow State:
- job_id: str
- job_request: JobRequest
- documents: List[ProcessedContent]
- scoring_results: List[ScoringResult]
- report_data: ReportData
- errors: List[str]
- current_progress: Dict[str, Any]

Workflow Nodes:
1. load_documents
   - Input: job_request
   - Output: documents list
   - Error handling: Skip corrupted files, log errors

2. load_context
   - Input: context_file path
   - Output: context dictionary
   - Must include: company_terms, industries, markets, strategic_themes

3. process_documents
   - Input: documents
   - Output: processed_content list
   - Parallel processing using Ray tasks

4. score_documents
   - Input: processed_content, context
   - Output: scoring_results
   - Parallel scoring across 5 dimensions

5. cluster_results
   - Input: scoring_results
   - Output: topic_clusters
   - Group by identified topics

6. generate_report
   - Input: all previous outputs
   - Output: markdown file path

Node Connections:
START -> load_documents -> load_context -> process_documents -> score_documents -> cluster_results -> generate_report -> END

Error Handling:
- Each node must handle and log errors
- Failed documents recorded but don't stop pipeline
- Minimum 50% success rate to continue
```

### Workflow Nodes Implementation (src/workflow/nodes.py)

```python
# Implement each node as async function:

async def load_documents(state: WorkflowState) -> WorkflowState:
    """
    1. List all files in input_folder
    2. Filter by supported extensions
    3. Sort by size (process smaller first)
    4. Return file paths list
    """

async def load_context(state: WorkflowState) -> WorkflowState:
    """
    1. Read YAML context file
    2. Validate required fields exist
    3. Parse into context dictionary
    4. Add to workflow state
    """

async def process_documents(state: WorkflowState) -> WorkflowState:
    """
    1. Create Ray tasks for each document
    2. Process in batches of 50
    3. Handle different file types
    4. Extract text and metadata
    5. Update progress metrics
    """

async def score_documents(state: WorkflowState) -> WorkflowState:
    """
    1. Create Ray tasks for scoring
    2. Apply 5-dimensional scoring
    3. Calculate confidence levels
    4. Generate justifications
    5. Update progress
    """

async def cluster_results(state: WorkflowState) -> WorkflowState:
    """
    1. Group by topic clusters
    2. Group by priority levels
    3. Calculate aggregate statistics
    4. Identify key themes
    """

async def generate_report(state: WorkflowState) -> WorkflowState:
    """
    1. Load Jinja2 templates
    2. Compile report data
    3. Render markdown
    4. Save to output folder
    5. Return file path
    """
```

---

## 6. Scoring Algorithm Specifications

### Master Score Calculation

```
Master Score = (Direct_Impact × 0.40) + (Industry_Relevance × 0.25) + 
               (Geographic_Relevance × 0.15) + (Temporal_Urgency × 0.10) + 
               (Strategic_Alignment × 0.10)

All dimension scores: 0-100
Final score: 0-100 (rounded to 1 decimal)
```

### Dimension Scoring Rules

#### Direct Impact Score (40% weight)
```
Score 80-100: Document directly mentions company/brand
- Base 80 + (number_of_mentions × 5, max 20)

Score 60-79: High-impact regulatory language
- Count keywords: "must comply", "required", "mandate", "penalty"
- Base 60 + (keyword_matches × 3, max 19)

Score 40-59: Some impact indicators
- Base 40 + (keyword_matches × 10, max 19)

Score 0-39: Minimal direct relevance
- Default 20 if no matches
```

#### Industry Relevance Score (25% weight)
```
Score 90-100: Core industry focus
- Keywords: "e-commerce", "online retail", "fashion", "apparel"
- 3+ matches: Base 90 + ((matches-3) × 3, max 10)

Score 70-89: Some core industry relevance
- 1-2 core matches: Base 70 + (matches × 10, max 19)

Score 50-69: Adjacent industry relevance
- Keywords: "retail", "consumer goods", "technology"
- 2+ matches: Base 50 + (matches × 5, max 19)

Score 30-49: Minimal industry relevance
- 1 adjacent match: Base 30 + (matches × 10, max 19)

Score 0-29: No industry relevance
- Default 10
```

#### Geographic Relevance Score (15% weight)
```
Score 85-100: Primary markets
- Keywords: "EU", "Germany", "Poland", "France", etc.
- 2+ matches: Base 85 + (matches × 5, max 15)

Score 70-84: Single primary market
- 1 primary match: Base 70 + (secondary_matches × 5, max 14)

Score 50-69: Secondary markets
- Keywords: "UK", "Switzerland", "Austria", etc.
- 2+ matches: Base 50 + (matches × 5, max 19)

Score 40-49: Global scope
- Keywords: "global", "worldwide", "international"
- Base 40 + (matches × 5, max 9)

Score 0-39: No geographic relevance
- Default 15
```

#### Temporal Urgency Score (10% weight)
```
Score 90-100: Immediate action required
- Keywords: "immediate", "urgent", "within days", "this week"
- Use highest matching keyword score

Score 70-89: Short-term deadline (< 3 months)
- Keywords: "this month", "next month", "within 3 months"
- Date extraction showing < 3 month deadline

Score 50-69: Medium-term deadline (3-12 months)
- Keywords: "within 6 months", "this year"
- Date extraction showing 3-12 month deadline

Score 30-49: Long-term deadline (> 12 months)
- Keywords: "next year", "2026", "long-term"

Score 0-29: No urgency
- Default 20
```

#### Strategic Alignment Score (10% weight)
```
Score 85-100: Strong strategic alignment
- 3+ strategic theme matches
- Themes from context file

Score 60-79: Moderate alignment
- 1-2 strategic theme matches

Score 45-59: Keyword-based alignment
- 3+ strategic keywords without theme match

Score 30-44: Minimal alignment
- 1-2 strategic keyword matches

Score 0-29: No strategic relevance
- Default 15
```

### Confidence Score Calculation

```python
confidence_factors = {
    "text_length": 0.2,      # Longer documents = higher confidence
    "keyword_density": 0.3,  # More relevant keywords = higher confidence
    "score_variance": 0.2,   # Lower variance across dimensions = higher confidence
    "evidence_quality": 0.3  # More evidence snippets = higher confidence
}

Calculate each factor (0-1):
- text_length: min(word_count / 500, 1.0)
- keyword_density: matched_keywords / total_keywords
- score_variance: 1 - (std_dev(dimension_scores) / 50)
- evidence_quality: total_evidence_snippets / 15

Final confidence = weighted sum of factors
```

---

## 7. Document Processing Specifications

### Supported File Types and Parsing Rules

```python
File Type Handlers:

.md, .markdown:
- Use markdown library
- Extract raw text
- Preserve heading structure

.pdf:
- Use PyPDF2
- Extract text page by page
- Handle encrypted PDFs (skip with error)
- Max 500 pages

.docx:
- Use python-docx
- Extract paragraphs and tables
- Preserve section headers

.txt:
- Direct text reading
- Handle various encodings (UTF-8, Latin-1)

.html:
- Use BeautifulSoup4
- Extract text from body
- Remove script/style tags
- Preserve semantic structure

Error Handling:
- Log extraction errors
- Return partial content if possible
- Mark document as "partially processed"
- Continue with next document
```

### Content Normalization Rules

```python
1. Text Cleaning:
   - Strip excessive whitespace
   - Normalize unicode characters
   - Remove null bytes
   - Fix common encoding issues

2. Structure Preservation:
   - Keep paragraph boundaries
   - Preserve bullet points as "- "
   - Maintain heading hierarchy

3. Metadata Extraction:
   - File creation/modification dates
   - Author (if available)
   - Page count (PDFs)
   - Word count

4. Size Limits:
   - Max 1MB text per document
   - Truncate with warning if larger
   - Sample evenly from document
```

---

## 8. Report Generation Specifications

### Main Report Template (src/output/templates/report.md.j2)

```markdown
# Political Monitoring Report: {{ job_name }}

Generated: {{ generation_timestamp }}  
Job ID: {{ job_id }}

## Executive Summary

**Documents Analyzed:** {{ total_documents }}  
**High Priority Items:** {{ high_priority_count }}  
**Processing Time:** {{ processing_time_minutes }} minutes

### Key Findings
{% for finding in key_findings %}
- {{ finding }}
{% endfor %}

### Recommended Actions
{% for action in recommended_actions %}
1. {{ action }}
{% endfor %}

## Priority Analysis

{% for queue in priority_queues %}
### {{ queue.priority_level }} Priority ({{ queue.document_count }} items)

{% for doc in queue.documents[:10] %}
#### {{ loop.index }}. {{ doc.metadata.source }}
- **Score:** {{ doc.master_score }}/100
- **Confidence:** {{ doc.confidence_level }}
- **Topics:** {{ doc.topic_clusters|join(", ") }}
- **Key Factor:** {{ doc.overall_justification }}

{% endfor %}
{% if queue.document_count > 10 %}
*... and {{ queue.document_count - 10 }} more items*
{% endif %}

{% endfor %}

## Topic Clusters

{% for cluster in topic_clusters %}
### {{ cluster.topic_name }} ({{ cluster.document_count }} documents)

**Average Score:** {{ cluster.average_score }}  
**Key Themes:** {{ cluster.key_themes|join(", ") }}

Top documents in this cluster:
{% for doc in cluster.documents[:5] %}
1. {{ doc.metadata.source }} (Score: {{ doc.master_score }})
{% endfor %}

{% endfor %}

## Performance Metrics

- Total Processing Time: {{ performance_metrics.total_time_seconds }}s
- Average per Document: {{ performance_metrics.avg_time_per_doc_ms }}ms
- Documents Failed: {{ failed_documents|length }}

## Configuration Used

- Input Folder: {{ parameters_used.input_folder }}
- Context File: {{ context_file_used }}
- Priority Threshold: {{ parameters_used.priority_threshold }}
- Include Low Confidence: {{ parameters_used.include_low_confidence }}
```

---

## 9. Ray Task Specifications

### Task Definitions (src/tasks/ray_tasks.py)

```python
# Define these Ray remote tasks:

@ray.remote(max_retries=3)
def process_document_task(file_path: str, doc_id: str) -> ProcessedContent:
    """
    1. Read file based on extension
    2. Extract text content
    3. Extract metadata
    4. Return ProcessedContent object
    5. Handle errors gracefully
    """

@ray.remote(max_retries=2)
def score_document_task(content: ProcessedContent, context: Dict) -> ScoringResult:
    """
    1. Initialize RelevanceEngine with context
    2. Score across 5 dimensions
    3. Calculate confidence
    4. Generate justifications
    5. Return ScoringResult
    """

@ray.remote
def batch_aggregation_task(results: List[ScoringResult]) -> Dict[str, Any]:
    """
    1. Calculate statistics
    2. Group by priority
    3. Group by topic
    4. Return aggregated data
    """

Task Management Pattern:
- Submit tasks in batches
- Use ray.wait() for partial results
- Update progress as tasks complete
- Handle failed tasks gracefully
- Maximum 20 concurrent tasks
```

---

## 10. Configuration Management Specifications

### Settings Class (src/config.py)

```python
# Use pydantic-settings BaseSettings

Required Settings Groups:

1. Kodosumi Settings:
   - SERVICE_NAME (default: "political-monitoring")
   - SERVICE_PORT (default: 8000)

2. Ray Settings:
   - RAY_ADDRESS (default: "auto")
   - NUM_CPUS (default: 8)
   - MAX_RETRIES (default: 3)

3. Path Settings:
   - DEFAULT_INPUT_FOLDER
   - DEFAULT_OUTPUT_FOLDER
   - DEFAULT_CONTEXT_FOLDER

4. Processing Limits:
   - MAX_BATCH_SIZE (default: 1000)
   - TIMEOUT_SECONDS (default: 600)
   - MAX_DOCUMENT_SIZE_MB (default: 50)

5. Scoring Settings:
   - CONFIDENCE_THRESHOLD (default: 0.7)
   - All dimension weights

Loading Order:
1. Default values
2. .env file
3. Environment variables
4. config.yaml overrides
```

### Context File Format (YAML)

```yaml
# Client context file structure
company_terms:
  - zalando
  - zln
  
core_industries:
  - e-commerce
  - online retail
  - fashion
  - apparel
  
primary_markets:
  - european union
  - eu
  - germany
  - poland
  
strategic_themes:
  - digital transformation
  - sustainability
  - customer experience
  - data privacy
  
topic_patterns:
  data-protection:
    - gdpr
    - data privacy
    - personal information
  compliance:
    - regulatory compliance
    - legal requirement
    - enforcement action
    
direct_impact_keywords:
  - must comply
  - required to
  - obligation
  - penalty
```

---

## 11. Error Handling Specifications

### Custom Exceptions (src/utils/exceptions.py)

```python
Define these exception classes:

DocumentProcessingError:
- Used when document cannot be parsed
- Include file path and error details

ScoringError:
- Used when scoring fails
- Include document ID and dimension

WorkflowError:
- Used for workflow-level failures
- Include job ID and node name

ConfigurationError:
- Used for invalid configuration
- Include setting name and validation error

BatchProcessingError:
- Used when batch fails
- Include failed document count
```

### Error Handling Patterns

```python
Document Level:
- Try to extract partial content
- Log error with document ID
- Add to failed_documents list
- Continue processing

Scoring Level:
- Fallback to zero scores
- Mark confidence as LOW
- Include error in justification

Workflow Level:
- Checkpoint before each node
- Allow resume from checkpoint
- Fail job if >50% documents fail

API Level:
- Return appropriate HTTP status
- Include error details in response
- Log full stack trace
```

---

## 12. Testing Specifications

### Test Data Requirements

```python
Create test fixtures:

1. Sample Documents (tests/test_data/):
   - valid_markdown.md (500 words)
   - valid_pdf.pdf (3 pages)
   - corrupt_pdf.pdf (invalid)
   - large_document.pdf (>50MB)
   - empty_document.txt

2. Sample Contexts:
   - minimal_context.yaml (required fields only)
   - full_context.yaml (all features)
   - invalid_context.yaml (missing fields)

3. Expected Outputs:
   - For each sample document
   - Include all scoring dimensions
   - Include confidence levels
```

### Test Coverage Requirements

```python
Unit Tests (>90% coverage):
- Each scorer dimension
- Document parsers for each type
- Model validation
- Error handling

Integration Tests:
- Full workflow execution
- Ray task distribution
- Report generation
- API endpoints

Performance Tests:
- 100 document batch
- Verify <10 minute completion
- Memory usage limits
```

---

## 13. Deployment Configuration

### Kodosumi config.yaml

```yaml
applications:
  - name: political-monitoring
    route_prefix: /political-monitoring
    import_path: src.serve:app
    runtime_env:
      pip:
        - -r requirements.txt
      env_vars:
        PYTHONPATH: .
        DEFAULT_INPUT_FOLDER: ${DEFAULT_INPUT_FOLDER}
        DEFAULT_OUTPUT_FOLDER: ${DEFAULT_OUTPUT_FOLDER}
        DEFAULT_CONTEXT_FOLDER: ${DEFAULT_CONTEXT_FOLDER}
      working_dir: .
    num_replicas: 1
    ray_actor_options:
      num_cpus: 1
      memory: 2000000000  # 2GB
```

### Docker Configuration

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config.yaml .

# Create data directories
RUN mkdir -p /data/input /data/output /data/context

# Set environment variables
ENV PYTHONPATH=/app
ENV RAY_ADDRESS=auto

# Expose Kodosumi service port
EXPOSE 8000

# Start command handled by Kodosumi
CMD ["echo", "Use Kodosumi to start this service"]
```

---

## 14. Implementation Checklist

Before implementation is complete, verify:

### Code Structure ✓
- [ ] All directories and files created as specified
- [ ] All Python packages have __init__.py files
- [ ] All imports use absolute paths from src/

### Dependencies ✓
- [ ] All dependencies installed with exact versions
- [ ] No additional dependencies added
- [ ] Environment variables loaded from .env

### Data Models ✓
- [ ] All Pydantic models implemented with validation
- [ ] All enums defined as specified
- [ ] Auto-calculated fields working correctly

### API Endpoints ✓
- [ ] All 6 endpoints implemented
- [ ] Form validation working
- [ ] Background tasks executing
- [ ] Proper error responses

### Workflow ✓
- [ ] All 6 nodes implemented
- [ ] State management working
- [ ] Progress updates functioning
- [ ] Error handling at each stage

### Scoring ✓
- [ ] All 5 dimensions implemented
- [ ] Master score calculation correct
- [ ] Confidence calculation working
- [ ] Evidence extraction functioning

### Document Processing ✓
- [ ] All file types supported
- [ ] Size limits enforced
- [ ] Corruption handled gracefully
- [ ] Metadata extracted

### Report Generation ✓
- [ ] Templates rendering correctly
- [ ] All sections populated
- [ ] Markdown formatting valid
- [ ] File saved to output folder

### Ray Integration ✓
- [ ] Tasks defined with decorators
- [ ] Parallel execution working
- [ ] Progress tracking accurate
- [ ] Resource limits enforced

### Testing ✓
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Test data created
- [ ] Coverage >90%

### Deployment ✓
- [ ] Kodosumi config valid
- [ ] Docker image builds
- [ ] Service starts successfully
- [ ] Health endpoint responding

---

## 15. Performance Requirements

The system must meet these performance criteria:

1. **Processing Time**: < 10 minutes for 1000 documents
2. **Memory Usage**: < 4GB RAM per worker
3. **Concurrent Tasks**: Support 20 parallel Ray tasks
4. **Response Time**: API responses < 500ms
5. **File Size**: Handle documents up to 50MB
6. **Batch Size**: Process batches up to 1000 documents
7. **Startup Time**: Service ready < 30 seconds

---

## Implementation Notes for AI Agent

1. **Start with**: Project structure and dependencies
2. **Then implement**: Models, then API, then workflow
3. **Test as you go**: Write tests for each component
4. **Use exact specifications**: Don't deviate from this spec
5. **Handle all errors**: Never let exceptions crash the service
6. **Log everything**: Use structured logging throughout
7. **Validate inputs**: Check all user inputs thoroughly
8. **Document code**: Add docstrings to all functions

This specification is complete and ready for implementation. Follow it exactly to create a working Political Monitoring Agent for Kodosumi.