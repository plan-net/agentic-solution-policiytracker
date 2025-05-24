# Political Monitoring Agent - High-Level Architecture

## Document Metadata

| Field | Value |
|-------|-------|
| **Project Name** | Political Monitoring Agent |
| **Document Type** | High-Level Architecture |
| **Version** | 4.0 |
| **Date** | 23.05.2025 |
| **Status** | Final |
| **Target Runtime** | Kodosumi on Ray |

---

## 1. System Overview & Boundaries

### System Purpose
The Political Monitoring Agent must process batches of political documents and generate relevance-scored markdown reports for Public Affairs analysts.

### System Boundaries
```
Inside System Boundary:
- Document batch processing from filesystem
- Multi-dimensional relevance scoring
- Topic clustering and prioritization
- Markdown report generation
- Feedback incorporation

Outside System Boundary:
- Document collection and placement
- Manual trigger via Kodosumi UI
- Human review of output reports
- Strategic decision making
```

### Execution Model
```
Trigger: Manual via Kodosumi web form
Processing: Single batch per job submission
Input: Pre-staged documents in filesystem folder
Output: Comprehensive markdown report
Feedback: Optional scoring adjustments
```

---

## 2. Component Architecture

### Component Structure
```
Political Monitoring Service
├── API Layer
│   ├── Job Submission Handler      # Receives form submissions
│   ├── Status Tracker              # Provides job progress
│   └── Result Delivery             # Serves completed reports
│
├── Processing Pipeline
│   ├── Document Processor          # Extracts content from files
│   ├── Relevance Analyzer          # Multi-dimensional scoring
│   ├── Topic Organizer             # Clusters related content
│   └── Report Compiler             # Generates markdown output
│
├── Core Services
│   ├── Context Manager             # Maintains client profile
│   ├── Scoring Engine              # Implements scoring logic
│   ├── Confidence Calculator       # Assesses result reliability
│   └── Justification Generator     # Explains scoring decisions
│
└── Infrastructure
    ├── Task Distributor            # Ray task management
    ├── State Manager               # Job and workflow state
    └── File Handler                # Filesystem operations
```

### Component Responsibilities

**API Layer Components:**
```
Job Submission Handler:
  Purpose: Accept and validate job requests from Kodosumi form
  Responsibilities:
    - Validate input parameters
    - Create job records
    - Queue jobs for processing
    - Return job identifiers

Status Tracker:
  Purpose: Provide real-time job progress information
  Responsibilities:
    - Track processing stages
    - Calculate completion percentage
    - Report errors and warnings
    - Provide time estimates

Result Delivery:
  Purpose: Serve completed analysis reports
  Responsibilities:
    - Validate job completion
    - Retrieve report files
    - Handle download requests
    - Manage result retention
```

**Processing Pipeline Components:**
```
Document Processor:
  Purpose: Extract structured content from various file formats
  Capabilities:
    - Parse markdown, PDF, DOCX, TXT, HTML files
    - Extract metadata (author, date, source)
    - Handle corrupted files gracefully
    - Enforce size limits (50MB max)

Relevance Analyzer:
  Purpose: Score documents across multiple dimensions
  Capabilities:
    - Apply 5-dimensional scoring model
    - Generate evidence snippets
    - Calculate confidence scores
    - Produce scoring justifications

Topic Organizer:
  Purpose: Group documents by thematic relevance
  Capabilities:
    - Identify topic patterns
    - Cluster related documents
    - Extract key themes
    - Calculate cluster statistics

Report Compiler:
  Purpose: Generate comprehensive markdown reports
  Capabilities:
    - Apply report templates
    - Structure content by priority
    - Include visual formatting
    - Generate executive summary
```

---

## 3. Data Flow Architecture

### Primary Data Flow
```
1. Job Submission
   Input: Form parameters (job_name, folders, thresholds)
   Process: Validation and job creation
   Output: Job ID and status URL

2. Document Loading
   Input: Folder path from job request
   Process: File discovery and validation
   Output: List of processable documents

3. Content Extraction
   Input: Document file paths
   Process: Format-specific parsing
   Output: Structured content objects

4. Relevance Scoring
   Input: Content + client context
   Process: Multi-dimensional analysis
   Output: Scored document set

5. Result Organization
   Input: Scored documents
   Process: Clustering and prioritization
   Output: Organized result structure

6. Report Generation
   Input: Organized results
   Process: Template rendering
   Output: Markdown report file
```

### Data Transformations
```
Raw Files → Parsed Content → Scored Content → Clustered Results → Markdown Report

Each transformation must:
- Preserve data lineage
- Handle errors gracefully
- Log processing metrics
- Update job progress
```

---

## 4. Integration Architecture

### Integration Points
```
Kodosumi Platform:
  Type: Native integration
  Interface: FastAPI service registration
  Requirements:
    - Expose form-compatible endpoints
    - Provide health checks
    - Support async job execution

Ray Cluster:
  Type: Runtime dependency
  Interface: Ray serve and tasks
  Requirements:
    - Distribute processing tasks
    - Manage resource allocation
    - Handle task failures

Filesystem:
  Type: I/O interface
  Interface: Standard file operations
  Requirements:
    - Read from input folders
    - Write to output folders
    - Handle permissions properly
```

### External Dependencies
```
Required Services:
- Ray cluster (computation)
- Filesystem (storage)
- Kodosumi runtime (execution)

Optional Services:
- Feedback store (improvement)
- Metrics collector (monitoring)
```

---

## 5. Technology Stack

### Core Technologies
```
Runtime Platform:
  Technology: Kodosumi on Ray
  Justification: Provides distributed processing and service management
  Constraints: Must use Ray 2.46.0+

Programming Language:
  Technology: Python 3.11+
  Justification: Ray/Kodosumi requirement, AI/ML ecosystem
  Constraints: Async support required

Workflow Orchestration:
  Technology: LangGraph
  Justification: Native AI workflow support with state management
  Constraints: Version 0.2.3+ for stability

Document Processing:
  Technology: Python libraries (PyPDF2, python-docx, etc.)
  Justification: Comprehensive format support
  Constraints: Must handle corrupted files
```

### Architectural Patterns
```
Batch Processing Pattern:
  When: All document processing
  Why: Optimize resource utilization
  How: Group documents into Ray task batches

Pipeline Pattern:
  When: End-to-end processing flow
  Why: Clear stage separation
  How: Sequential stages with error boundaries

Strategy Pattern:
  When: Document parsing by type
  Why: Extensible format support
  How: Parser selection based on file extension

Observer Pattern:
  When: Progress tracking
  Why: Real-time status updates
  How: Progress callbacks from Ray tasks
```

---

## 6. Non-Functional Requirements Implementation

### Performance Architecture
```
Requirement: <10 minute processing for 1000 documents

Architectural Decisions:
- Parallel document processing via Ray
- Batch sizes optimized for memory usage
- Lazy loading for large documents
- Progress streaming for user feedback

Implementation Strategy:
- Maximum 20 concurrent Ray tasks
- 50-document processing batches
- Streaming report generation
- Resource pooling for parsers
```

### Scalability Architecture
```
Requirement: Handle 1-1000 documents per job

Architectural Decisions:
- Dynamic batch sizing
- Elastic Ray worker allocation
- Memory-aware task distribution
- Graceful degradation for overload

Implementation Strategy:
- Batch size = min(50, total_docs/num_workers)
- Worker count based on document count
- Memory limits per worker (2GB)
- Queue overflow to sequential processing
```

### Reliability Architecture
```
Requirement: >70% relevance accuracy

Architectural Decisions:
- Multi-dimensional scoring model
- Confidence-based filtering
- Evidence-based justifications
- Feedback-driven improvements

Implementation Strategy:
- 5 independent scoring dimensions
- Weighted score aggregation
- Confidence thresholds for filtering
- Feedback storage for model updates
```

---

## 7. State Management Architecture

### State Hierarchy
```
Application State
├── Job State (persistent)
│   ├── Job metadata
│   ├── Processing status
│   └── Result location
│
├── Workflow State (transient)
│   ├── Current stage
│   ├── Document queue
│   └── Progress metrics
│
└── Context State (cached)
    ├── Client profile
    ├── Scoring parameters
    └── Topic patterns
```

### State Storage Strategy
```
Job State:
  Storage: In-memory with periodic persistence
  Scope: Job lifetime + retention period
  Recovery: Restore from persistence on restart

Workflow State:
  Storage: LangGraph checkpoints
  Scope: Job execution duration
  Recovery: Resume from last checkpoint

Context State:
  Storage: Memory cache with file backing
  Scope: Service lifetime
  Recovery: Reload from context files
```

---

## 8. Error Handling Architecture

### Error Categories & Strategies
```
Document Errors:
  Examples: Corrupt file, unsupported format
  Strategy: Log and skip, continue processing
  User Impact: Listed in report as failed

Processing Errors:
  Examples: Parsing failure, scoring error
  Strategy: Retry with fallback, mark low confidence
  User Impact: Included with warning

System Errors:
  Examples: Ray failure, filesystem error
  Strategy: Job-level retry, then fail
  User Impact: Job marked as failed

Configuration Errors:
  Examples: Missing context, invalid settings
  Strategy: Fail fast with clear message
  User Impact: Job rejected at submission
```

### Error Propagation Rules
```
Document Level: Isolated, no propagation
Batch Level: Affect batch only, warn user
Job Level: Fail job, provide detailed error
System Level: Reject new jobs, alert operators
```

---

## 9. Security Architecture

### Security Layers
```
Access Control:
  - Kodosumi authentication for UI
  - Role-based job submission
  - Secure result retrieval

Data Protection:
  - Input validation on all paths
  - Sandboxed file operations
  - No external network calls

Audit Trail:
  - Job submission logging
  - Access attempt tracking
  - Result retrieval records
```

### Security Constraints
```
Path Traversal: Blocked via validation
File Types: Whitelist enforcement
Size Limits: Strict enforcement
Execution: No arbitrary code execution
```

---

## 10. Monitoring & Observability Architecture

### Monitoring Layers
```
Service Monitoring:
  - Health endpoint status
  - Job queue depth
  - Error rates

Performance Monitoring:
  - Document processing time
  - Memory usage per job
  - Ray task distribution

Business Monitoring:
  - Documents processed
  - Score distributions
  - Topic frequencies
```

### Observability Strategy
```
Logging:
  - Structured JSON logs
  - Request correlation IDs
  - Error stack traces

Metrics:
  - Prometheus-compatible
  - Real-time dashboards
  - Alert thresholds

Tracing:
  - Job execution timeline
  - Stage duration tracking
  - Bottleneck identification
```

---

## 11. Deployment Architecture

### Deployment Structure
```
Kodosumi Service:
  - Single service deployment
  - Ray cluster integration
  - Environment-based config

Resource Allocation:
  - Service: 1 CPU, 2GB RAM
  - Workers: 1 CPU, 2GB RAM each
  - Scaling: 1-10 workers

Configuration:
  - YAML-based deployment
  - Environment variables
  - Secret management
```

### Deployment Constraints
```
Must Have:
- Ray cluster access
- Filesystem permissions
- Kodosumi registration

Should Have:
- Persistent storage
- Monitoring endpoint
- Backup capability
```

---

## 12. Architecture Decisions Record

### Key Decisions

```
Decision: Use filesystem instead of API for input
Rationale: Simplifies integration, handles large files better
Trade-offs: Less real-time, requires file management
Alternatives: S3 bucket, REST upload, streaming

Decision: Single markdown report output
Rationale: Human-readable, version-controllable, portable
Trade-offs: No structured query, larger files
Alternatives: JSON output, database storage, multiple files

Decision: Manual trigger only
Rationale: Predictable resource usage, clear job boundaries
Trade-offs: No continuous monitoring, manual overhead
Alternatives: Scheduled runs, folder watching, event-driven

Decision: Ray for distribution
Rationale: Proven scale, Kodosumi integration, Python native
Trade-offs: Cluster dependency, resource overhead
Alternatives: Multiprocessing, Celery, custom threading
```

---

## 13. Architecture Validation Checklist

### Completeness
- [x] All components have clear responsibilities
- [x] Data flow is fully specified
- [x] Integration points are defined
- [x] Error handling is comprehensive

### Feasibility
- [x] Technology choices are compatible
- [x] Performance targets are achievable
- [x] Resource requirements are reasonable
- [x] Security requirements are met

### Quality Attributes
- [x] Scalability path is clear
- [x] Reliability mechanisms in place
- [x] Monitoring strategy defined
- [x] Deployment model specified

### Risks
- [x] Technical risks identified
- [x] Mitigation strategies defined
- [x] Decision rationale documented
- [x] Trade-offs acknowledged

---

## Implementation Notes

### Critical Success Factors
1. Ray task distribution efficiency
2. Document parsing reliability
3. Scoring algorithm accuracy
4. Report generation performance

### Recommended Proof of Concepts
1. Ray task scaling with 1000 documents
2. Multi-format document parsing
3. Scoring algorithm validation
4. Report template rendering

### Architecture Constraints for Implementation
- Must maintain job isolation
- Cannot modify input documents
- Must handle partial failures
- Should minimize memory footprint