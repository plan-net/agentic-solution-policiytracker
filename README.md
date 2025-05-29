# Political Monitoring Agent v0.2.0

A sophisticated AI-powered document analysis system for political and regulatory monitoring with **advanced chat interface** and **automated data collection**. Built on **Kodosumi v0.9.2** with Graphiti temporal knowledge graphs, Ray distributed processing, LangGraph workflows, Apache Airflow ETL, and Azure Storage integration.

## 🔥 NEW: Advanced Chat Interface

**Experience next-generation political monitoring through our sophisticated chat interface powered by Graphiti temporal knowledge graphs:**

- **🧠 15 Specialized Tools**: Entity analysis, network traversal, temporal tracking, community detection
- **🕸️ Multi-hop Reasoning**: Discover hidden connections through knowledge graph traversal
- **⏰ Temporal Intelligence**: Track policy evolution and entity changes over time
- **📊 Network Analysis**: Identify key influencers and community structures
- **🔍 Advanced Search**: Semantic search with reranking strategies (RRF, MMR, cross-encoder)
- **💭 Context Awareness**: Session memory and conversation continuity

**Access the Chat Interface**: via Open WebUI at http://localhost:3000 (after setup)

## 🚀 Quick Start

**Get up and running in 5 minutes:**

```bash
# 1. Clone and setup dependencies
git clone <repository-url>
cd policiytracker
just setup

# 2. Start services (Docker required)
just services-up

# 3. Start the application
just dev

# 4. Access the application
# → Chat Interface: http://localhost:3000 (Open WebUI)
# → Kodosumi Admin: http://localhost:3370 (admin/admin)
# → Document Analysis: http://localhost:8001/political-analysis
# → Airflow ETL: http://localhost:8080 (admin/admin)
```

**Test with sample data**: Sample documents are included in `data/input/examples/` - upload these via the web interface to see the system in action.

**Automated data collection**: Set up [ETL pipeline](#-automated-data-collection-etl) to automatically collect and process news articles daily.

**Next steps**: Configure [Langfuse observability](#step-4-configure-langfuse-one-time-only) and customize the [context file](#client-context-configuration) for your organization.

> **📖 For Business Users**: See the [User Guide](docs/USER_GUIDE.md) for a comprehensive explanation of how the system works, what inputs are needed, and how to interpret results.

## 🚀 Features

### 🤖 Advanced Chat Interface (NEW v0.2.0)
- **🔍 Sophisticated Search**: 15 specialized tools for knowledge graph exploration
- **🧠 Multi-hop Reasoning**: Discover hidden connections between entities and policies
- **⏰ Temporal Analysis**: Track entity evolution and policy changes over time
- **🕸️ Network Traversal**: Identify influence patterns and impact cascades
- **👥 Community Detection**: Find natural groupings and policy clusters
- **💡 Graph-Powered Insights**: Leverage unique advantages of temporal knowledge graphs
- **🗣️ Natural Language**: Ask complex questions in plain English
- **🧵 Context Awareness**: Maintains conversation history and builds on previous queries

### Core Capabilities
- **Multi-format Document Processing**: PDF, DOCX, Markdown, HTML, and text files
- **AI-Enhanced Scoring**: Hybrid rule-based + LLM semantic analysis 
- **5-Dimensional Relevance Model**: Comprehensive scoring across multiple factors
- **Intelligent Clustering**: Automatic topic grouping and priority classification
- **Distributed Processing**: Ray-powered parallel computation for scalability
- **Rich Reporting**: Detailed markdown reports with AI-generated insights

### 🔄 Automated Data Collection (ETL)
- **Dual Collection Flows**: Flow 1 (Policy Landscape) + Flow 2 (Client News)
- **Policy Collection**: Weekly regulatory document gathering via Exa.ai
- **News Collection**: Daily client-specific news from multiple sources
- **Apache Airflow Orchestration**: Reliable scheduling and monitoring
- **Smart Query Generation**: Context-aware search queries from client YAML
- **Initialization Tracking**: Historical data collection on first run
- **Smart Deduplication**: URL-based filtering to avoid duplicate articles

### Kodosumi Platform Features
- **Rich Web Interface**: Beautiful forms with real-time progress tracking
- **Distributed Processing**: Ray-powered horizontal scaling across clusters
- **Real-time Streaming**: Live progress updates via Kodosumi Tracer
- **Admin Dashboard**: Comprehensive monitoring at http://localhost:3370

### Cloud-Native Architecture
- **Simplified Azure Storage**: Automatic path management with environment-based configuration
- **LangGraph Workflows**: State-persistent workflows with checkpoint recovery
- **Smart Storage Switching**: Seamless local development with Azurite, production-ready Azure Blob Storage
- **Zero-Configuration Paths**: Import script automatically updates configuration paths

### AI & LLM Integration
- **LangChain Integration**: Standardized LLM interfaces with provider flexibility
- **Multi-LLM Support**: OpenAI GPT-4, Anthropic Claude, with automatic fallbacks
- **Langfuse Observability**: Complete LLM operation tracing and monitoring
- **Semantic Analysis**: AI-powered document understanding and relevance scoring

## 🏗️ Complete System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Chat Interface│    │   Apache         │    │   Kodosumi      │
│   (Advanced Q&A)│    │   Airflow        │    │   Web Interface │
│   + 15 Tools    │    │   (ETL)          │    │   (Forms + UI)  │
└─────────┬───────┘    └─────────┬────────┘    └─────────┬───────┘
          │                      │                       │
          ▼                      ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Graphiti      │◀───│   Document       │───▶│   Political     │
│   Temporal      │    │   Processing     │    │   Analyzer      │
│   Knowledge     │    │   Pipeline       │    │   (Entrypoint)  │
│   Graph         │    │                  │    │                 │
└─────────┬───────┘    └──────────────────┘    └─────────────────┘
          │                      │                       │
          ▼                      ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Neo4j         │    │   Exa.ai API     │    │   LangGraph     │
│   Database      │    │   (News Data)    │    │   Workflows     │
│   (Graph Store) │    │                  │    │   + Ray Tasks   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Local Storage │    │   Azure Storage  │    │   Langfuse      │
│   (data/input/) │    │   (Azurite)      │    │   (Observability)│
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Enhanced Chat Interface (v0.2.0)
- **LangGraph Workflow**: 4-node pipeline (understand → plan → execute → synthesize)
- **15 Specialized Tools**: Entity analysis, network traversal, temporal queries, community detection
- **Streaming with Thinking**: Real-time thought process via Open WebUI `<think>` tags
- **LangChain Memory**: Conversation context with 10-exchange history
- **External Prompts**: Modular prompt system with YAML frontmatter
- **Strategic Tool Selection**: LLM-driven tool planning based on query complexity
- **OpenAI-Compatible API**: Standard chat completions interface for integration

### Two-Part Kodosumi Design
- **Endpoint** (`app.py`): Rich web forms, validation, and HTTP interface
- **Entrypoint** (`political_analyzer.py`): Core business logic with distributed Ray processing

## 🔄 Automated Data Collection (ETL)

The system includes a **dual-flow ETL pipeline** for comprehensive document collection:

### 📊 Two Collection Flows

**Flow 1: Policy Landscape Collection**
- **Weekly Schedule**: Sundays at 2 AM UTC
- **Content**: Regulatory documents, policy changes, enforcement actions
- **Sources**: Exa.ai with intelligent query generation
- **Scope**: EU regulations (GDPR, DSA, DMA), sustainability, competition law
- **Storage**: `data/input/policy/YYYY-MM/`

**Flow 2: Client News Collection**  
- **Daily Schedule**: Configurable timing
- **Content**: Company-specific news and industry developments
- **Sources**: Exa.ai, Apify news aggregators
- **Scope**: Based on your client context (company terms, markets)
- **Storage**: `data/input/news/YYYY-MM/`

### How It Works
1. **Smart Query Generation**: Automatic queries from `client.yaml` context
2. **Initialization Mode**: Historical data collection (30-90 days) on first run
3. **Regular Collection**: Daily/weekly incremental updates
4. **Deduplication**: URL-based filtering across all sources
5. **Markdown Conversion**: Structured documents ready for analysis
6. **Auto-Processing**: Triggers analysis workflows for new documents

### Getting Started with ETL

**Setup Requirements:**
```bash
# Add API keys to .env
EXA_API_KEY=your_exa_api_key_here           # Primary source (recommended)
APIFY_API_TOKEN=your_apify_api_token_here   # Optional fallback
```

**Start ETL Services:**
```bash
# Start Airflow alongside other services
just services-up
just airflow-up

# Access Airflow UI
open http://localhost:8080  # Login: admin/admin
```

**Test Collection Systems:**
```bash
# Test policy collection (Flow 1)
just policy-test
just policy-queries  # See generated queries

# Test news collection (Flow 2) 
just etl-status      # Check initialization status
```

**Manual Triggers:**
```bash
# Trigger policy collection (weekly)
just airflow-trigger policy_collection_dag

# Trigger news collection (daily)
just airflow-trigger news_collection_dag
```

**Monitor Collection:**
- **Airflow UI**: http://localhost:8080 - View DAG runs and logs
- **Policy Documents**: `data/input/policy/YYYY-MM/` - Regulatory documents
- **News Articles**: `data/input/news/YYYY-MM/` - Client-specific news
- **Processing Logs**: Track collection success/failure rates

### ETL Configuration

The ETL pipeline uses your existing `data/context/client.yaml` to generate intelligent search queries:

**For Policy Collection (Flow 1):**
```yaml
topic_patterns:
  data-protection:    # GDPR, privacy regulations
    - gdpr
    - data privacy
  ecommerce-regulation:   # DSA, DMA, platform rules
    - digital services act
    - marketplace regulation
  sustainability:     # ESG, environmental laws
    - esg
    - carbon footprint

primary_markets:      # Geographic focus
  - european union
  - germany
  - france
```

**For News Collection (Flow 2):**
```yaml
company_terms:        # Your organization
  - zalando
  - zln
  
core_industries:      # Business sectors  
  - e-commerce
  - fashion
  - marketplace

exclusion_terms:      # Filter out irrelevant content
  - sports
  - automotive
```

**File Structure Created:**
```
data/input/
├── policy/           # Flow 1: Regulatory landscape
│   ├── 2025-05/
│   │   ├── 20250527_europa-eu_dsa-implementation-guidelines.md
│   │   └── 20250527_edpb_gdpr-enforcement-update.md
│   └── 2025-04/...
└── news/             # Flow 2: Client-specific news
    ├── 2025-05/
    │   ├── 20250527_techcrunch_zalando-announces-new-feature.md
    │   └── 20250527_reuters_eu-ecommerce-regulation-update.md
    └── 2025-04/...
```

### ETL Commands Reference

```bash
# Airflow Management
just airflow-up              # Start Airflow services
just airflow-down            # Stop Airflow services  
just airflow-logs            # View Airflow logs
just airflow-reset           # Reset Airflow database

# Policy Collection (Flow 1)
just policy-test             # Test policy collection system
just policy-queries          # View generated policy queries
just policy-test-full        # Full test (requires EXA_API_KEY)

# ETL Status & Management
just etl-status              # Check initialization status
just etl-reset <collector>   # Reset specific collector
just etl-reset-all          # Reset all collectors

# Manual DAG Triggers (via Airflow UI)
# - policy_collection_dag    # Weekly policy collection
# - news_collection_dag      # Daily news collection  

# Status & Monitoring
just services-status         # Check all services including Airflow
just logs airflow-scheduler  # View scheduler logs
just logs airflow-webserver  # View webserver logs
```

> **💡 Pro Tip**: Use the Airflow UI at http://localhost:8080 to monitor DAG runs, view logs, and manually trigger collections. Policy collection runs weekly (Sundays), news collection runs daily.

## 🤖 Advanced Chat Interface & Knowledge Graph Search

### What Makes Our Chat Interface Special

Unlike typical LLM + web search solutions, our chat interface leverages **Graphiti temporal knowledge graphs** to provide unique insights impossible with traditional approaches:

**🧠 Graph-Powered Intelligence**:
- **Multi-hop reasoning** through relationship networks
- **Temporal analysis** tracking entity evolution over time
- **Network centrality** identifying key influencers and connectors
- **Impact cascade analysis** showing how changes propagate
- **Community detection** revealing natural groupings and clusters

### 16 Specialized Search Tools

#### 🔍 Entity Tools (4 tools)
- **Entity Details**: Comprehensive information about specific entities
- **Entity Relationships**: Network of connections and relationships
- **Entity Timeline**: Evolution and changes over time
- **Similar Entities**: Find entities with similar characteristics

#### 🕸️ Network Traversal Tools (4 tools)
- **Traverse from Entity**: Multi-hop relationship exploration
- **Find Paths**: Connection routes between entities
- **Get Neighbors**: Immediate network neighborhood
- **Impact Analysis**: Impact cascades and influence patterns

#### ⏰ Temporal Tools (4 tools)
- **Date Range Search**: Time-bounded content searches
- **Entity History**: Track entity changes over time
- **Concurrent Events**: What happened simultaneously
- **Policy Evolution**: Track regulatory development over time

#### 👥 Community Tools (3 tools)
- **Detect Communities**: Find natural entity groupings
- **Policy Clusters**: Analyze policy area relationships
- **Organization Networks**: Map organizational relationship patterns

#### 🔍 Enhanced Search (1 tool)
- **Advanced Search**: Semantic search with sophisticated reranking strategies

### Example Chat Capabilities

**Entity Exploration**:
```
"Tell me about the EU Digital Services Act"
→ Entity details + relationships + timeline + impact analysis
```

**Network Analysis**:
```
"How is Meta connected to EU privacy regulations?"
→ Multi-hop path finding + relationship traversal + impact cascade
```

**Temporal Intelligence**:
```
"What has changed in GDPR enforcement this year?"
→ Timeline analysis + concurrent events + policy evolution tracking
```

**Community Detection**:
```
"What organizations are working on AI regulation?"
→ Community detection + organization networks + policy clusters
```

### Advanced Search Configurations

Our chat interface uses **Graphiti's advanced search capabilities**:

- **RRF (Reciprocal Rank Fusion)**: Combines multiple ranking strategies
- **MMR (Maximal Marginal Relevance)**: Balances relevance and diversity
- **Cross-encoder Reranking**: Deep semantic understanding
- **Temporal Weighting**: Recent information prioritized
- **Entity-focused Search**: Optimized for entity vs. relationship queries

### Source Attribution & Citations

Every chat response includes proper source attribution:
- **Original article URLs** extracted from document metadata
- **Publication dates** for temporal context
- **Source quality indicators** for reliability assessment
- **Direct quotes** with proper attribution

### Getting Started with Chat

1. **Start the system**: `just dev`
2. **Access chat interface**: http://localhost:8001/chat
3. **Try example queries**:
   - "What policies affect e-commerce platforms?"
   - "Show me the relationship between GDPR and the Digital Services Act"
   - "What has changed in data protection law recently?"
   - "Which organizations are most connected to AI regulation?"

### Chat Interface Benefits

**For Policy Analysts**:
- Discover hidden connections between regulations
- Track policy evolution and implementation timelines
- Identify key stakeholders and influence networks
- Analyze impact cascades across jurisdictions

**For Compliance Teams**:
- Understand relationship between different regulatory requirements
- Find all policies affecting specific business areas
- Track changes in enforcement patterns
- Identify emerging compliance risks

**For Strategic Planning**:
- Map competitive regulatory landscapes
- Identify influential policy makers and organizations
- Understand market dynamics through regulatory networks
- Plan strategic responses to regulatory changes

> **🎯 Unique Value**: Our chat interface provides insights that would take hours of manual research through traditional search methods, by leveraging the power of temporal knowledge graphs to reveal patterns and connections that are invisible to conventional approaches.

## 🚀 Complete First-Time Setup Guide

This guide walks you through setting up the Political Monitoring Agent from a fresh clone to running your first analysis.

### Prerequisites

- **Python 3.12.6** (system installation)
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

**Complete Langfuse Setup**:
1. **Create a new account**:
   - Click **"Sign up"**
   - Use any email (e.g., `admin@policiytracker.local`)
   - Set your own password
   - Complete the registration

2. **Create an organization**:
   - After login, you'll be prompted to create an organization
   - Name: `Political Monitoring` (or any name you prefer)
   - Complete organization setup

3. **Create a project**:
   - You'll be prompted to create your first project
   - Name: `political-monitoring-agent` (or any name you prefer)
   - Complete project creation

4. **Get your API keys**:
   - Once in the project, go to **Settings** → **API Keys**
   - Click **"Create new API key"**
   - Copy the **Public Key** (starts with `pk-lf-`)
   - Copy the **Secret Key** (starts with `sk-lf-`)

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
- **🤖 Chat Interface**: http://localhost:8001/chat (NEW - Advanced Q&A)
- **📊 Kodosumi Admin Panel**: http://localhost:3370 (admin/admin)
- **🎯 Document Analysis**: http://localhost:8001/political-analysis
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
# → Go to http://localhost:3001
# → Sign up → Create organization → Create project → Get API keys
# → Update .env with API keys
just upload-prompts          # Upload prompts to Langfuse
just azure-import            # Import sample data to Azurite
just dev                     # Start development environment
```

### Development Workflow

**🎯 Simplified Storage Configuration**

The system now automatically manages storage paths! No manual path configuration needed:

```bash
# For Local Development (default)
just dev                    # Uses ./data/input automatically

# For Azure Development  
just azure-import          # Auto-updates .env with Azure paths
echo "USE_AZURE_STORAGE=true" >> .env
just dev                   # Uses Azure Storage automatically
```

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
- **Chat Interface**: http://localhost:8001/chat (NEW - Advanced Q&A)
- **Admin Panel**: http://localhost:3370 (login: `admin` / `admin`)
- **Ray Dashboard**: http://localhost:8265
- **Document Analysis**: http://localhost:8001/political-analysis
- **Supporting Services**:
  - Azurite: http://localhost:10000 (Azure Storage Emulator)
  - PostgreSQL: localhost:5432 (used by Langfuse)
  - Langfuse: http://localhost:3001 (LLM Observability)

📝 **New to the analysis form?** See the comprehensive [Form Guide in USER_GUIDE.md](USER_GUIDE.md#starting-your-first-analysis-form-guide) for detailed field explanations and examples.

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
# If you need to start over with Langfuse setup:
just reset-langfuse    # Resets to fresh installation
just services-up       # Restart services
# Then go through signup → organization → project → API keys

# If API keys don't work:
# 1. Check you copied the full keys (including pk-lf- and sk-lf- prefixes)
# 2. Ensure you created the keys within a PROJECT (not organization level)
# 3. Restart after updating .env: just kodosumi-restart
# 4. Check Langfuse logs: just logs langfuse-server

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
just format && just typecheck

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
just format                  # Format code with ruff
just typecheck               # Type check with mypy
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

### ⚠️ Critical: Configuration Management System

**Important**: This project uses a two-tier configuration system for security and Ray worker compatibility:

#### 🎯 Configuration Files
- **`.env`** - Your personal secrets (gitignored)
- **`config.yaml.template`** - Safe template (committed to git)  
- **`config.yaml`** - Runtime config with secrets (gitignored)

#### 🔄 Automatic Configuration Sync

Our system **automatically manages** config.yaml creation and synchronization:

```bash
just setup            # Creates config.yaml from template (first time)
just dev              # Auto-syncs .env variables to config.yaml
just dev-quick        # Auto-syncs on quick redeploy
just sync-config      # Manual sync when needed
```

**What this solves**:
- ✅ **Security**: Secrets never committed to git
- ✅ **Ray Workers**: Environment variables available to distributed tasks
- ✅ **Team Setup**: Consistent config across developers
- ✅ **Production**: Easy deployment with different secrets

#### 📋 How It Works
1. **First Run**: `config.yaml` created from `config.yaml.template`
2. **Sync Process**: Script reads `.env` and updates `config.yaml` runtime_env
3. **Ray Deployment**: Workers get all environment variables via `config.yaml`
4. **Security**: `config.yaml` with secrets stays local (gitignored)

#### 🔧 Configuration Commands
```bash
just sync-config      # Create/update config.yaml from .env
just validate-config  # Check for placeholder values  
just reset-config     # Reset config.yaml from template
```

**Pro tip**: After updating `.env` with new API keys, run `just dev-quick` to sync and redeploy.

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
│   ├── app.py                   # Kodosumi FastAPI entry point
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
just format && just typecheck

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

### Quick Diagnostics

```bash
# Check system health
just health

# Verify all services are running  
just services-status

# Test core functionality
just test
```

### Common Setup Issues

**1. "Command not found: just"**
```bash
# Install Just task runner
brew install just  # macOS
# or
cargo install just
```

**2. "Permission denied" during setup**
```bash
# Fix Docker permissions (Linux)
sudo usermod -aG docker $USER
# Then logout and login again

# Alternative: run with sudo (not recommended)
sudo just services-up
```

**3. "Port already in use" errors**
```bash
# Check what's using the ports
lsof -i :3370  # Kodosumi admin
lsof -i :8001  # Your app
lsof -i :5432  # PostgreSQL
lsof -i :3001  # Langfuse

# Stop conflicting services
just services-down
# Kill any remaining processes if needed
```

### Application Issues

**4. "Module not found" errors**
```bash
# Reinstall dependencies
just setup

# Check Python version (needs 3.11+)
python --version

# Check UV installation
uv --version
```

**5. Langfuse setup issues**
```bash
# Reset Langfuse completely
just services-down
docker volume rm policiytracker_postgres_data
just services-up

# Then redo setup at http://localhost:3001
```

**6. Azure Storage connection failed**
```bash
# Check Azurite is running
docker ps | grep azurite

# Test connection
just azure-verify

# Reset and reimport data
just azure-import
```

**7. Analysis jobs fail with errors**
```bash
# Check Ray status
just kodosumi-status

# View application logs
just kodosumi-logs

# Check for configuration issues
grep -E "(ERROR|CRITICAL)" .env
```

### Performance Issues

**8. Slow document processing**
```bash
# Check available resources
docker stats

# Increase Ray CPU allocation
# Edit .env: RAY_NUM_CPUS=8

# Monitor processing in Ray dashboard
open http://localhost:8265
```

### Advanced Troubleshooting

**9. Complete reset (last resort)**
```bash
# Stop everything
just kodosumi-stop
just services-down

# Remove all Docker volumes
docker volume prune -f

# Clean and restart
just clean-all
just setup
just services-up
just dev
```

**10. Debug mode**
```bash
# Enable detailed logging
export LOG_LEVEL=DEBUG
just dev

# Check logs
just kodosumi-logs
```

### Getting Help

If these solutions don't work:

1. **Check logs**: `just kodosumi-logs` and `just logs [service-name]`
2. **Search issues**: Look for similar problems in the repository issues  
3. **System info**: Include output of `just health` when reporting issues
4. **Configuration**: Share your `.env` file (remove sensitive keys)
5. **Available commands**: Run `just` to see all available commands

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
   just format && just typecheck
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