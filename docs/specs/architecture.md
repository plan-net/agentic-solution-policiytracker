# Political Monitoring Agent - Architecture Specification

## Document Metadata

| Field | Value |
|-------|-------|
| **Project Name** | Political Monitoring Agent |
| **Document Type** | Architecture Specification |
| **Version** | 5.0 |
| **Date** | 25.05.2025 |
| **Status** | Current Implementation |
| **Target Runtime** | Kodosumi v0.9.2 on Ray |

---

## 1. System Overview

### Architecture Pattern: Kodosumi Two-Part Design

The Political Monitoring Agent follows the Kodosumi framework pattern with clear separation between web interface and business logic:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Kodosumi      │    │   Political      │    │   LangGraph     │
│   Web Interface │───▶│   Analyzer       │───▶│   Workflows     │
│   (src/app.py)  │    │ (src/political_  │    │   + Ray Tasks   │
│                 │    │   analyzer.py)   │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Ray Serve     │    │   Azure Storage  │    │   Langfuse      │
│   (HTTP/gRPC)   │    │   (Azurite)      │    │   (Observability)│
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Core Components

1. **Endpoint** (`src/app.py`): Rich web forms, validation, and HTTP interface
2. **Entrypoint** (`src/political_analyzer.py`): Core business logic with distributed Ray processing
3. **LangGraph Workflows** (`src/workflow/`): State management and distributed processing pipeline
4. **Azure Storage Integration** (`src/integrations/`): Document storage and checkpoint persistence
5. **Langfuse Observability** (`src/prompts/`): LLM monitoring and prompt management

## 2. Technology Stack

### Runtime Environment
- **Kodosumi v0.9.2**: Web framework with Ray Serve deployment
- **Ray Serve**: Distributed HTTP serving and scaling
- **Python 3.12.6**: Runtime environment
- **UV Package Manager**: Dependency management

### Core Frameworks
- **LangGraph**: Workflow orchestration and state management
- **FastAPI**: HTTP API framework (via Kodosumi)
- **Pydantic v2**: Data validation and configuration
- **Structlog**: Structured logging

### Storage & Data
- **Azure Blob Storage**: Document storage with container organization
- **Azurite**: Local development storage emulator
- **LangGraph Checkpoints**: Workflow state persistence
- **PostgreSQL**: Langfuse observability data (Docker)

### AI & LLM Integration
- **LangChain**: LLM abstraction and integration
- **Anthropic Claude**: Primary LLM provider
- **OpenAI GPT**: Secondary LLM provider
- **Langfuse**: LLM operation monitoring and prompt management

## 3. Data Flow Architecture

### Document Processing Pipeline

```
📄 Documents → 📦 Azure Storage → 🔄 LangGraph → 📊 Analysis → 📋 Report
```

### Detailed Flow

1. **Document Ingestion**
   ```
   Input Documents (PDF, DOCX, TXT, MD, HTML)
   ↓
   Azure Blob Storage (containers: input-documents, reports, checkpoints)
   ↓
   Batch Document Loader (src/processors/batch_loader.py)
   ```

2. **Workflow Execution**
   ```
   LangGraph Workflow (src/workflow/graph.py)
   ├── load_documents() → Document discovery and validation
   ├── load_context() → Organizational context loading
   ├── process_documents() → Content extraction and processing
   ├── score_documents() → Multi-dimensional relevance scoring
   ├── cluster_results() → Topic clustering and priority classification
   └── generate_report() → Markdown report generation
   ```

3. **Distributed Processing**
   ```
   Ray Remote Tasks
   ├── Document processing (parallel)
   ├── LLM scoring (concurrent with limits)
   ├── Topic clustering (AI-enhanced)
   └── Report generation (with Azure upload)
   ```

## 4. Storage Architecture

### Azure Blob Storage Organization

```
Storage Account
├── input-documents/        # Source documents
│   ├── jobs/{job_id}/input/
│   └── examples/
├── reports/                # Generated reports
│   ├── jobs/{job_id}/reports/
│   └── markdown/
├── checkpoints/           # LangGraph state persistence
│   ├── threads/{thread_id}/checkpoints/
│   └── metadata/
├── contexts/              # Organizational context files
│   ├── {client}/context.yaml
│   └── templates/
└── cache/                 # Processed content cache
    ├── documents/
    └── embeddings/
```

### Local Development Storage

```
data/
├── input/
│   ├── examples/          # Sample documents
│   └── real/             # (gitignored)
├── output/               # Local reports (gitignored)
├── context/
│   └── client.yaml       # Organizational context
└── temp/                 # Temporary processing files
```

## 5. Configuration Management

### Two-Tier Configuration System

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   .env          │    │ config.yaml     │    │ Ray Workers     │
│   (secrets)     │───▶│ (runtime)       │───▶│ (environment)   │
│   (gitignored)  │    │ (gitignored)    │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│ .env.template   │    │config.yaml.     │
│ (safe)          │    │template (safe)  │
│ (committed)     │    │ (committed)     │
└─────────────────┘    └─────────────────┘
```

### Configuration Flow
1. **Development Setup**: `just setup` creates config.yaml from template
2. **Environment Sync**: `scripts/sync_env_to_config.py` syncs .env to config.yaml
3. **Ray Deployment**: Ray workers receive environment via config.yaml runtime_env
4. **Security**: Secrets stay local, templates are safe for git

## 6. Web Interface Architecture

### Kodosumi Form System

```python
# src/app.py - Rich Forms with Validation
analysis_form = F.Model(
    F.Markdown("# Political Document Analysis"),
    F.InputText(label="📋 Job Name", ...),
    F.InputNumber(label="🎯 Priority Threshold", ...),
    F.Checkbox(label="🔍 Include Low Confidence", ...),
    F.Checkbox(label="🗂️ Enable Topic Clustering", ...),
    F.Select(label="💾 Storage Mode", ...),
    F.Submit("Start Analysis")
)
```

### Request Flow
```
User Form Submission
↓
Input Validation (InputsError)
↓
Launch() → src.political_analyzer:execute_analysis
↓
Ray Serve Deployment
↓
Real-time Progress Updates (Kodosumi Tracer)
```

## 7. AI/LLM Integration

### Hybrid Analysis Architecture

```
Document Input
↓
Rule-Based Scoring (Fast, Consistent)
↓
LLM Semantic Analysis (AI-Enhanced)
↓
Hybrid Score Combination
↓
Confidence Assessment
```

### LLM Provider Management
- **Primary**: Anthropic Claude (document analysis, topic clustering)
- **Fallback**: OpenAI GPT (when Claude unavailable)
- **Monitoring**: Langfuse observability for all LLM operations
- **Prompts**: Centralized prompt management with local fallback

### Graceful Degradation
```
LLM Available → Hybrid Analysis (Rule-based + AI)
LLM Unavailable → Rule-based Only (System continues functioning)
```

## 8. Security Architecture

### Data Protection
- **Secrets Management**: Environment-based with gitignore protection
- **Document Security**: Secure processing without permanent storage
- **Access Control**: Kodosumi-based authentication and authorization
- **Audit Logging**: Structured logging for all operations

### Network Security
```
External Access → Kodosumi (Port 8001) → Ray Serve → Workers
Internal Services → Docker Compose Network (Isolated)
```

## 9. Observability & Monitoring

### Logging Stack
- **Application Logs**: Structlog with JSON formatting
- **LLM Operations**: Langfuse tracking and monitoring
- **Ray Operations**: Ray Dashboard (Port 8265)
- **System Health**: Health check endpoints

### Monitoring Points
- **Form Submissions**: User interaction tracking
- **Document Processing**: Success/failure rates
- **LLM Usage**: API calls, costs, latency
- **Storage Operations**: Azure Blob operations
- **Workflow Progress**: Real-time state updates

## 10. Deployment Architecture

### Development Environment
```
Docker Compose Services:
├── PostgreSQL (Langfuse data)
├── Langfuse Server (Port 3001)
└── Azurite (Azure Storage emulator, Port 10000)

Ray Local Cluster:
├── Ray Head Node
├── Ray Serve (Kodosumi app)
└── Ray Dashboard (Port 8265)

Kodosumi Admin:
└── Admin Panel (Port 3370)
```

### Production Considerations
```
Azure Resources:
├── Azure Blob Storage (Production)
├── Azure Database for PostgreSQL (Langfuse)
└── Azure Container Instances (Ray cluster)

Kodosumi Deployment:
├── Auto-scaling (1-10 replicas)
├── Load Balancing
└── Health Monitoring
```

## 11. Scalability Design

### Horizontal Scaling
- **Ray Serve**: Auto-scaling based on request load
- **Storage**: Azure Blob Storage scales automatically
- **LLM Processing**: Concurrent request limiting and queuing

### Performance Targets
- **Form Response**: <200ms (p95)
- **Document Processing**: <30s per document average
- **Batch Processing**: 1000+ documents per hour
- **Concurrent Users**: 10-100 supported

## 12. Future Architecture Evolution

### Planned Enhancements
- **Real-time Processing**: Document monitoring and alerts
- **Advanced Analytics**: Trend analysis and forecasting
- **Enterprise Integration**: SSO, Teams/Slack notifications
- **Multi-language Support**: International document processing
- **Advanced Export**: Multiple report formats (Excel, PDF, JSON)

### Scalability Roadmap
- **Database Migration**: From PostgreSQL to enterprise database
- **Microservices**: Component separation for independent scaling
- **Edge Processing**: Regional deployment for global users
- **Advanced AI**: Multi-modal analysis (images, videos, audio)

---

This architecture specification reflects the current implementation and provides a roadmap for future development while maintaining the proven Kodosumi + Ray + Azure Storage foundation.