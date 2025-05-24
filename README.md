# Political Monitoring Agent

A sophisticated AI-powered document analysis system for political and regulatory monitoring. Built on **Kodosumi v0.9.2** with Ray distributed processing, LangGraph workflows, and Azure Storage integration.

> **📖 For Business Users**: See the [User Guide](USER_GUIDE.md) for a comprehensive explanation of how the system works, what inputs are needed, and how to interpret results.

## 🚀 Features

### Core Capabilities
- **Multi-format Document Processing**: PDF, DOCX, Markdown, HTML, and text files
- **AI-Enhanced Scoring**: Hybrid rule-based + LLM semantic analysis 
- **5-Dimensional Relevance Model**: Comprehensive scoring across multiple factors
- **Intelligent Clustering**: Automatic topic grouping and priority classification
- **Distributed Processing**: Ray-powered parallel computation for scalability
- **Rich Reporting**: Detailed markdown reports with AI-generated insights

### Kodosumi Platform Features
- **Rich Web Interface**: Beautiful forms with real-time progress tracking
- **Distributed Processing**: Ray-powered horizontal scaling across clusters
- **Real-time Streaming**: Live progress updates via Kodosumi Tracer
- **Admin Dashboard**: Comprehensive monitoring at http://localhost:3370

### Cloud-Native Architecture
- **Azure Storage Integration**: Seamless local development with Azurite, production-ready Azure Blob Storage
- **LangGraph Workflows**: State-persistent workflows with checkpoint recovery
- **Hybrid Storage**: Automatic switching between local filesystem and Azure Storage
- **Intelligent Caching**: Azure-based caching for processed content

### AI & LLM Integration
- **LangChain Integration**: Standardized LLM interfaces with provider flexibility
- **Multi-LLM Support**: OpenAI GPT-4, Anthropic Claude, with automatic fallbacks
- **Langfuse Observability**: Complete LLM operation tracing and monitoring
- **Semantic Analysis**: AI-powered document understanding and relevance scoring

## 🏗️ Kodosumi Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Kodosumi      │    │   Political      │    │   LangGraph     │
│   Web Interface │───▶│   Analyzer       │───▶│   Workflows     │
│   (Forms + UI)  │    │   (Entrypoint)   │    │   + Ray Tasks   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Ray Serve     │    │   Azure Storage  │    │   Langfuse      │
│   (HTTP/gRPC)   │    │   (Azurite)      │    │   (Observability)│
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Two-Part Kodosumi Design
- **Endpoint** (`app.py`): Rich web forms, validation, and HTTP interface
- **Entrypoint** (`political_analyzer.py`): Core business logic with distributed Ray processing

## 🚀 Complete First-Time Setup Guide

This guide walks you through setting up the Political Monitoring Agent from a fresh clone to running your first analysis.

### Prerequisites

- **Python 3.11+** (system installation)
- **UV package manager** (for dependency management)
- **Docker** and **Docker Compose** (for supporting services)
- **Just** task runner (for automation)
- **Optional**: OpenAI/Anthropic API keys for LLM features

> **💡 Note**: Kodosumi and all Python dependencies are installed automatically during setup.

### Install Required Tools

1. **Install UV package manager**:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. **Install Just task runner**:
```bash
# macOS with Homebrew
brew install just

# Or with Cargo
cargo install just
```

> **💡 Note**: Kodosumi and all Python dependencies are automatically installed during project setup via UV.

### Step-by-Step First-Time Setup

#### Step 1: Clone and Basic Setup
```bash
git clone <repository-url>
cd policiytracker
just setup
```

This installs all dependencies (including Kodosumi), creates `.env` file, and sets up directories.

#### Step 2: Configure Your Organization Context
```bash
just setup-context
```

This guides you to edit `data/context/client.yaml` with your organization's information:

**Edit the following sections**:
- **company_terms**: Your company names, brands, ticker symbols
- **core_industries**: Your business sectors (affects 25% of relevance scoring)
- **primary_markets**: Your main geographic markets (affects 15% of scoring)  
- **strategic_themes**: Your business priorities (affects 10% of scoring)

**Example customization**:
```yaml
company_terms:
  - acme-corp
  - acme
  - acme-inc

core_industries:
  - fintech
  - digital-payments
  - financial-services

primary_markets:
  - united-states
  - canada
  - european-union
```

💡 **Quick Start**: The example context is pre-configured for e-commerce. You can test immediately or customize later.

#### Step 3: Start First-Time Setup
```bash
just first-run
```

This will:
1. Start all required services (Azurite, PostgreSQL, Langfuse)
2. Guide you through Langfuse configuration

#### Step 4: Configure Langfuse (One-Time Only)

When prompted, **open Langfuse** at http://localhost:3001:

**First-time setup**:
1. If this is a fresh Langfuse installation, try these default credentials:
   - **Email**: `admin@policiytracker.local`
   - **Password**: `admin123`

2. If the default credentials don't work, **create a new account**:
   - Click **"Sign up"**
   - Use any email (e.g., `admin@policiytracker.local`)
   - Set your own password
   - Complete the registration

**Get your API keys**:
1. Once logged in, go to **Settings** → **API Keys**
2. Click **"Create new API key"**
3. Copy the **Public Key** (starts with `pk-lf-`)
4. Copy the **Secret Key** (starts with `sk-lf-`)

**Update your `.env` file** with the real keys:
```bash
LANGFUSE_PUBLIC_KEY=pk-lf-your-actual-public-key-here
LANGFUSE_SECRET_KEY=sk-lf-your-actual-secret-key-here
```

#### Step 5: Complete Setup
```bash
just complete-setup
```

This will:
1. Upload prompts to Langfuse for centralized management
2. Import sample documents to Azurite for testing
3. Start the full Kodosumi development environment

### 🎉 Ready to Go!

After setup completion:

**Access Points**:
- **📊 Kodosumi Admin Panel**: http://localhost:3370 (admin/admin)
- **🎯 Your App Interface**: http://localhost:8001/political-analysis
- **📈 Ray Dashboard**: http://localhost:8265
- **🔍 Langfuse Observability**: http://localhost:3001

**Test with Sample Data**:
- Sample documents are in `data/input/examples/`
  - `eu_digital_services_act_update.md` - DSA implementation guidelines 
  - `gdpr_enforcement_report_2024.txt` - Data protection enforcement report
- Run an analysis via the admin panel to test everything works
- Check Langfuse for LLM traces and prompt usage

**Sample Analysis Results** (with default e-commerce context):
- DSA document: High relevance (85-95 score) - directly affects e-commerce platforms
- GDPR report: Medium relevance (65-75 score) - compliance implications for data processing

### Quick Commands Reference

```bash
# Complete first-time setup (run these in order)
just setup          # Install dependencies & create .env
just setup-context  # Guide for editing client context  
just first-run      # Start services & setup Langfuse
# → Complete Langfuse setup, then:
just complete-setup # Upload prompts, import data, start dev

# Daily development workflow
just dev            # Start everything for development
just dev-quick      # Quick redeploy after code changes
just dev-watch      # Show development tips and URLs

# Management commands
just services-up    # Start only the supporting services
just kodosumi-logs  # View application logs
just kodosumi-status # Check deployment health
```

### Alternative Manual Setup

If you prefer manual control over each step:

```bash
just setup                    # Basic project setup
just services-up             # Start services
# → Manually configure Langfuse at http://localhost:3001
# → Update .env with API keys
just upload-prompts          # Upload prompts to Langfuse
just azure-import            # Import sample data to Azurite
just dev                     # Start development environment
```

### Development Workflow

**Primary Development** (Kodosumi-First):
```bash
# Start full development environment
just dev
```

This command:
1. Starts supporting services (Azurite, PostgreSQL, Langfuse)
2. Initializes Ray cluster
3. Deploys your app to Kodosumi
4. Registers with Kodosumi admin panel

**Development Iteration Cycle**:
```bash
# Make code changes to app.py or political_analyzer.py
# Then quickly redeploy:
just dev-quick

# Or watch development tips:
just dev-watch
```

**Access the Kodosumi platform**:
- **Admin Panel**: http://localhost:3370 (admin/admin)
- **Ray Dashboard**: http://localhost:8265
- **Your App**: http://localhost:8001/political-analysis
- **Supporting Services**:
  - Azurite: http://localhost:10000 (Azure Storage Emulator)
  - PostgreSQL: localhost:5432 (used by Langfuse)
  - Langfuse: http://localhost:3001 (LLM Observability)

### Development Commands

```bash
# Essential Development Commands
just setup-langfuse    # First-time Langfuse setup guide
just upload-prompts    # Upload prompts to Langfuse (optional)
just dev               # Start full Kodosumi development environment
just dev-quick         # Quick app redeploy after code changes
just dev-watch         # Display development tips and URLs

# Kodosumi Management
just kodosumi-status    # Check deployment status
just kodosumi-logs      # View real-time logs
just kodosumi-restart   # Restart entire stack
just kodosumi-stop      # Stop everything

# Service Management
just services-up        # Start supporting services only
just services-down      # Stop supporting services
just services-status    # Check service health
```

### Development Tips

**Efficient Development Loop**:
1. Run `just dev` once to start everything
2. Edit `app.py` (forms/endpoint) or `political_analyzer.py` (business logic)
3. Run `just dev-quick` to redeploy changes
4. Test in Kodosumi admin panel at http://localhost:3370

**Debugging**:
- Use `just kodosumi-logs` for real-time application logs
- Check Ray dashboard at http://localhost:8265 for distributed task monitoring
- View Kodosumi admin panel for execution timeline and results
- Check Langfuse at http://localhost:3001 for LLM operation traces

### Troubleshooting

**Langfuse Issues**:
```bash
# If login credentials don't work:
just reset-langfuse    # Resets to fresh installation
just services-up       # Restart services
# Then try login again or create new account

# If API keys don't work:
# 1. Check you copied the full keys (including pk-lf- and sk-lf- prefixes)
# 2. Restart after updating .env: just kodosumi-restart
# 3. Check Langfuse logs: just logs langfuse-server

# If Langfuse won't start at all:
just services-down
docker volume rm policiytracker_postgres_data policiytracker_langfuse_data
just services-up
```

**Service Connection Issues**:
```bash
# Check all services are running:
just services-status

# Check specific service logs:
just logs azurite
just logs langfuse-server
just logs postgres
```


### Quick Commands

```bash
# Full development setup
just setup && just services-up && just dev

# Run tests
just test

# Code quality checks
just check

# View all available commands
just
```

## 🛠️ Available Commands

### Essential Commands
```bash
just setup                   # One-time development setup
just dev                     # Start development server  
just services-up             # Start PostgreSQL, Redis, Azurite
just services-down           # Stop all services
just test                    # Run all tests
just check                   # Format code + type check
```

### Testing
```bash
just test                    # All tests
just test-coverage           # With coverage report
just test-unit               # Unit tests only
just test-integration        # Integration tests only
just test-azure              # Azure Storage tests only
```

### Azure Storage Development
```bash
just azure-import            # Import local data to Azurite
just azure-import-job ID     # Import with specific job ID
just azure-import-dry        # Preview import (dry run)
just azure-verify            # Test Azurite connection
```

### Utilities
```bash
just health                  # System health check
just logs [service]          # View service logs
just clean                   # Clean temp files
just clean-all               # Full cleanup + stop services
```

## 🔧 Configuration

### Environment Setup

1. **Copy environment template**:
```bash
cp .env.template .env
```

2. **Basic configuration** (services run in Docker):
```bash
# Database (PostgreSQL in Docker)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/policiytracker

# Azure Storage (Azurite Emulator)
USE_AZURE_STORAGE=false  # Set to true for Azure mode
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://localhost:10000/devstoreaccount1

# Langfuse (Optional - for LLM observability)
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key-here
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key-here
LANGFUSE_HOST=http://localhost:3001
```

3. **Add LLM API keys** (optional):
```bash
# Enable AI features
LLM_ENABLED=true

# OpenAI
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-4

# Anthropic
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here
ANTHROPIC_MODEL=claude-3-sonnet-20240229
```

### Storage Modes

**Local Development** (default):
```bash
USE_AZURE_STORAGE=false
```
- Documents stored in local `data/` folders
- Fast development and testing
- No cloud dependencies

**Azure Storage Mode**:
```bash
USE_AZURE_STORAGE=true
```
- Documents stored in Azurite (local) or Azure Blob Storage (production)
- Automatic caching of processed content
- Workflow checkpoints persisted to Azure
- Production-ready architecture

### Client Context Configuration

The system uses a client context file to customize document scoring for your organization. This file defines the terms, industries, markets, and themes that are most relevant to your business.

**Location**: `data/context/client.yaml`

**Required Structure**:
```yaml
# Your organization's identifiers
company_terms:
  - your-company-name
  - brand-name
  - company-ticker
  - subsidiary-names

# Your business sectors (used for Industry Relevance scoring - 25% weight)
core_industries:
  - technology
  - fintech
  - digital-services
  - e-commerce

# Geographic markets where you operate
primary_markets:        # Higher scoring weight
  - european-union
  - united-states
  - germany
  
secondary_markets:      # Moderate scoring weight
  - uk
  - switzerland
  - asia-pacific

# Your strategic priorities (used for Strategic Alignment scoring - 10% weight)
strategic_themes:
  - digital-transformation
  - regulatory-compliance
  - sustainability
  - data-privacy
  - customer-experience

# Optional: Organized keyword groups for better matching
topic_patterns:
  data-protection:
    - gdpr
    - data privacy
    - personal information
  
  compliance:
    - regulatory compliance
    - legal requirement
    - enforcement action

# Optional: Keywords that indicate direct regulatory impact
direct_impact_keywords:
  - must comply
  - required to
  - penalty
  - enforcement

# Optional: Terms to filter out irrelevant content
exclusion_terms:
  - sports
  - automotive
  - agriculture
```

**How It Works**:
- **Direct Impact** (40% weight): Uses `company_terms` and `direct_impact_keywords`
- **Industry Relevance** (25% weight): Matches against `core_industries`
- **Geographic Relevance** (15% weight): Scores `primary_markets` higher than `secondary_markets`
- **Strategic Alignment** (10% weight): Uses `strategic_themes`
- **Temporal Urgency** (10% weight): Time-based scoring (doesn't use context)

**Getting Started**:
1. **Test with defaults**: Use the pre-configured e-commerce context and sample documents
2. **Customize**: Copy `data/context/client.yaml` to `my-company.yaml` and edit
3. **Add your data**: Place documents in `data/input/` directories for analysis

**Quick Test with Sample Data**:
```bash
# The setup process includes sample documents in data/input/examples/
# Test these with the default e-commerce context via the admin panel:
# → http://localhost:3370 (admin/admin)
# → Select "data/input/examples" as input folder
# → Use default context settings
```

**Custom Context Usage**:
```bash
# Use default context
curl -X POST "http://localhost:8000/analyze" \
  -F "job_name=analysis" \
  -F "input_folder=/data/input/examples"

# Use custom context  
curl -X POST "http://localhost:8000/analyze" \
  -F "job_name=analysis" \
  -F "input_folder=/data/input/examples" \
  -F "context_file=/data/context/my-company.yaml"
```

## 🎯 API Usage

### Core Endpoints

- `POST /analyze` - Submit analysis job
- `GET /jobs/{job_id}/status` - Check job status
- `GET /jobs/{job_id}/result` - Download markdown report
- `GET /jobs` - List all jobs with pagination
- `DELETE /jobs/{job_id}` - Cancel running job
- `GET /health` - Service health check

### Example: Submit Analysis

```bash
curl -X POST "http://localhost:8000/analyze" \
  -F "job_name=q4_regulatory_review" \
  -F "input_folder=/data/input/q4_docs" \
  -F "context_file=/data/context/client.yaml" \
  -F "priority_threshold=70.0" \
  -F "clustering_enabled=true"
```

## 🧠 AI-Enhanced Scoring Model

### Hybrid Scoring Architecture

The system combines **rule-based analysis** with **LLM semantic understanding**:

1. **Rule-Based Scoring**: Fast, consistent baseline scoring
2. **LLM Semantic Analysis**: AI-powered document understanding  
3. **Hybrid Combination**: Weighted integration of both approaches
4. **Confidence Assessment**: Reliability scoring for all results

### 5-Dimensional Scoring Framework

#### 1. Direct Impact (40% weight)
- Company/brand mentions and relevance
- Regulatory requirements affecting business
- Compliance obligations and deadlines
- *AI Enhancement*: Semantic understanding of business impact

#### 2. Industry Relevance (25% weight)
- Core industry sector alignment
- Adjacent industry connections
- Business model and value chain relevance
- *AI Enhancement*: Industry classification and trend analysis

#### 3. Geographic Relevance (15% weight)
- Primary market coverage and jurisdiction
- Secondary market presence
- Global vs. regional scope indicators
- *AI Enhancement*: Geographic entity recognition and scope analysis

#### 4. Temporal Urgency (10% weight)
- Immediate deadlines and requirements
- Short-term implementation needs
- Long-term strategic planning horizon
- *AI Enhancement*: Timeline extraction and urgency assessment

#### 5. Strategic Alignment (10% weight)
- Strategic theme and keyword matching
- Business priority correlation
- Investment and growth area relevance
- *AI Enhancement*: Strategic context understanding

## 🛠️ Development

### Project Structure

```
political-monitoring-agent/
├── src/
│   ├── serve.py                 # FastAPI Kodosumi entry point
│   ├── config.py                # Pydantic configuration
│   ├── models/                  # Data models and validation
│   ├── workflow/                # LangGraph workflows
│   │   ├── graph.py            # Workflow definition
│   │   ├── nodes.py            # Workflow nodes
│   │   └── state.py            # Workflow state
│   ├── integrations/            # Azure Storage & checkpointing
│   │   ├── azure_storage.py    # Azure Storage client
│   │   └── azure_checkpoint.py # LangGraph checkpointer
│   ├── processors/              # Document processing
│   │   ├── batch_loader.py     # Azure/local file discovery
│   │   ├── content_processor.py # Content processing + caching
│   │   └── document_reader.py  # Multi-format document reading
│   ├── scoring/                 # Hybrid scoring engine
│   ├── tasks/                   # Ray remote functions
│   └── utils/                   # Utilities and helpers
├── tests/
│   ├── unit/
│   │   ├── test_azure_integration.py  # Azure Storage tests
│   │   ├── test_workflow_nodes.py     # Workflow tests (local + Azure)
│   │   └── test_*.py                  # Other unit tests
│   └── integration/
│       └── test_workflow_execution.py # Full workflow tests
├── scripts/
│   └── import_data_to_azurite.py      # Data import utility
├── docker-compose.yml           # Supporting services
├── justfile                     # Task automation (simplified)
├── requirements.md              # Technical requirements
└── README.md                    # This file
```

### Development Workflow

**Daily development**:
```bash
# Start everything
just services-up && just dev

# Make changes and test
just test
just check

# Work with Azure Storage
just azure-import  # Import test data
just test-azure    # Test Azure integration
```

**Working with Azure Storage**:
```bash
# Import local data to Azurite for testing
just azure-import

# Test Azure Storage integration
just test-azure

# Switch to Azure mode
# Edit .env: USE_AZURE_STORAGE=true
just dev
```

## 🚀 Deployment

### Local Testing

```bash
# Test with Azure Storage mode
echo "USE_AZURE_STORAGE=true" >> .env
just services-up && just dev
```

### Production (Azure)

**Environment Configuration**:
```bash
# Production Azure Storage
USE_AZURE_STORAGE=true
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=yourprodaccount;AccountKey=...;EndpointSuffix=core.windows.net

# Production database
DATABASE_URL=postgresql://user:password@prod-db:5432/policiytracker

# Production Langfuse
LANGFUSE_HOST=https://your-langfuse-instance.com
```

**Kodosumi Deployment**:
```yaml
# config.yaml
ray_actor_options:
  num_cpus: 2
  memory: 4000000000  # 4GB

autoscaling_config:
  min_replicas: 1
  max_replicas: 10
```

## 🔍 Troubleshooting

### Common Issues

**1. Services won't start**:
```bash
# Check Docker status
docker ps

# Restart services
just services-down && just services-up

# Check logs
just logs [service-name]
```

**2. Azure Storage issues**:
```bash
# Verify Azurite connection
just azure-verify

# Check Azurite logs
just logs azurite

# Reset and reimport data
just azure-import
```

**3. Ray/workflow issues**:
```bash
# Start Ray manually
just ray-start

# Check Ray dashboard
open http://localhost:8265

# Test without Ray
RAY_LOCAL_MODE=1 just test
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
just dev
```

### Getting Help

```bash
# Show all commands
just

# Check system health
just health

# Run diagnostics
just test && just check
```

## 🤝 Contributing

### Quick Contribution Workflow

1. **Fork and clone** the repository
2. **Setup development environment**:
   ```bash
   just setup
   just services-up
   ```

3. **Make changes** with proper testing:
   ```bash
   # Test your changes
   just test
   just check
   ```

4. **Submit pull request** with clear description

### Code Standards

- **Type hints** on all functions and methods
- **Comprehensive docstrings** with examples
- **Unit tests** for all new functionality
- **Azure Storage integration** for new storage-related features
- **Both local and Azure modes** tested

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

**Getting Help**:
- 📖 Check this README and run `just` for available commands
- 🔍 Run `just health` to check system status  
- 🐛 Submit issues via the project repository

**Key Resources**:
- [Just Command Runner](https://github.com/casey/just)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Ray Documentation](https://docs.ray.io/)
- [Azure Storage Documentation](https://docs.microsoft.com/en-us/azure/storage/)
- [Langfuse Observability](https://langfuse.com/docs)

---

**Built with ❤️ using LangGraph, Ray, Azure Storage, and Kodosumi • Automated with Just**