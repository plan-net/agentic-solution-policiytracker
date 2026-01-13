# Political Monitoring Agent v0.2.0

**AI-powered political monitoring with automated data collection, temporal knowledge graphs, and intelligent chat interface**

[![Version](https://img.shields.io/badge/version-0.2.0-blue.svg)](https://github.com/your-org/policiytracker)
[![Python](https://img.shields.io/badge/python-3.12.6-green.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 🎯 What This System Does

Transform raw political documents into actionable intelligence through:

- **🤖 Chat Interface**: Query your political knowledge graph conversationally
- **📰 Automated Collection**: Daily news and policy document gathering via ETL pipelines
- **🧠 Knowledge Graph**: Temporal entity tracking with relationship mapping
- **🎯 Entity Deduplication**: Intelligent resolution prevents 60-70% duplicate entities (Phase 2)
- **📊 Intelligence Analysis**: Multi-dimensional relevance scoring and topic clustering
- **⚡ Real-time Processing**: Distributed document analysis with Ray

## 🚀 Quick Start

**Get running in 5 minutes:**

```bash
# 1. Setup
git clone <repository-url> && cd policiytracker
just setup && just services-up

# 2. Launch
just dev

# 3. Access
# → React UI: http://localhost:5173 (NEW - Modern web interface)
# → Claude Agent API: http://localhost:8000 (NEW - AI chat backend)
# → Admin Panel: http://localhost:3370 (admin/admin)
# → ETL Dashboard: http://localhost:8080 (admin/admin)
```

**Test immediately**:
- Open the React UI and explore the interactive knowledge graph
- Try the AI chat interface powered by Claude Agent SDK
- Generate a weekly report using the new SDK-based flow

> 📖 **New to the system?** Start with the [User Guide](docs/USER_GUIDE.md) for step-by-step instructions.
>
> 🆕 **What's new in v0.2.0?** See [New Features Guide](docs/NEW_FEATURES_V0.2.0.md) for detailed documentation.

## 🏗️ Architecture Overview

```mermaid
graph TB
    subgraph "Data Collection"
        ETL[ETL Pipeline<br/>Airflow + Collectors]
        NEWS[News Sources<br/>Exa.ai, Apify]
        POLICY[Policy Sources<br/>Automated Scrapers]
    end
    
    subgraph "Processing"
        FLOWS[Kodosumi Flows<br/>Document Processing]
        GRAPHRAG[GraphRAG<br/>Entity Extraction]
        GRAPHITI[Graphiti<br/>Knowledge Graph]
    end
    
    subgraph "Analysis & Access"
        CHAT[Chat Interface<br/>Multi-Agent System]
        SCORING[Intelligence Scoring<br/>5-Dimensional Framework]
        REPORTS[Automated Reports<br/>Executive Summaries]
    end
    
    NEWS --> ETL
    POLICY --> ETL
    ETL --> FLOWS
    FLOWS --> GRAPHRAG
    GRAPHRAG --> GRAPHITI
    GRAPHITI --> CHAT
    GRAPHITI --> SCORING
    SCORING --> REPORTS
```

## 📂 Component Documentation

### **New in v0.2.0**
- **[New Features Overview](docs/NEW_FEATURES_V0.2.0.md)** - Complete guide to v0.2.0 additions
- **[React UI](ui/policy-tracker/README.md)** - Modern web interface with 3D graph visualization
- **[Claude Agent SDK](src/claude_agent/README.md)** - OpenAI-compatible conversational agent
- **[Weekly Report SDK](src/flows/weekly_report_sdk/)** - Claude-powered weekly intelligence reports

### **Core Systems**
- **[ETL Pipeline](src/etl/README.md)** - Automated data collection with Airflow, collectors, and storage
- **[Document Flows](src/flows/README.md)** - Kodosumi-based document processing workflows
- **[Chat Interface](src/chat/README.md)** - Multi-agent conversational analysis system
- **[GraphRAG System](src/graphrag/README.md)** - Knowledge graph construction and temporal intelligence

### **Data Ingestion Flows**
- **[Flow 5: Bundestag Ingestion](docs/flows/bundestag_ingestion.md)** - German parliamentary data from Bundestag DIP API (8 data sources)

### **Supporting Components**
- **[Scoring Engine](src/scoring/README.md)** - 5-dimensional intelligence assessment framework
- **[Testing Suite](tests/README.md)** - Comprehensive testing strategy and execution

### **Data Quality & Optimization**
- ✅ **[Phase 2 Entity Deduplication](docs/phase2_implementation_summary.md)** - Intelligent entity resolution at ingestion time
  - 60-70% duplicate reduction target
  - Three-tier resolution: exact → alias → fuzzy matching
  - 9 optimized Neo4j indexes for 100x faster lookups
  - Canonical entity management with EntityRegistry
- **[Phase 2 Architecture Plan](docs/deduplication_phase2_plan.md)** - Complete deduplication strategy and implementation roadmap

### **Documentation**
- **[User Guide](docs/USER_GUIDE.md)** - Business user instructions and workflows
- **[Setup Guide](docs/SETUP.md)** - Complete installation and configuration
- **[Quick Reference](docs/QUICK_REFERENCE.md)** - Commands, URLs, and troubleshooting

## 🛠️ Development

### **Prerequisites**
- Python 3.12.6 (strict requirement)
- Docker & Docker Compose
- 8GB+ RAM recommended
- OpenAI API key for LLM operations

### **Common Commands**
```bash
# Development
just dev              # Start full system
just dev-quick        # Restart without rebuilding
just test             # Run test suite
just format           # Format code

# Data Operations  
just collect-news     # Manual news collection
just process-docs     # Manual document processing
just build-communities # Knowledge graph community detection

# Monitoring
just logs             # View all logs
just kodosumi-logs    # Application logs
just status           # System health check
```

### **Environment Setup**
1. Copy `.env.example` to `.env`
2. Configure API keys and storage settings
3. Run `just setup` for automated dependency installation
4. See component READMEs for detailed configuration

## 🔧 Configuration

### **Essential Settings**
- **Storage**: Azure Blob Storage or local filesystem
- **LLM Provider**: OpenAI API for analysis and chat
- **Observability**: Langfuse for prompt and performance monitoring  
- **Knowledge Graph**: Neo4j with Graphiti temporal intelligence

### **Client Context**
Configure your organization's monitoring priorities in `data/context/client.yaml`:
```yaml
company_profile:
  name: "Your Organization"
  industries: ["technology", "finance"]
  regions: ["EU", "US"]
  
priority_topics:
  - "AI regulation"
  - "data privacy"  
  - "cybersecurity"
```

> 🔧 **Detailed configuration guides** are available in each component's README.

## 📊 Use Cases

### **Compliance Teams**
- Monitor regulatory changes affecting your industry
- Track enforcement actions and policy interpretations
- Generate compliance impact assessments

### **Government Affairs**
- Track policy development across multiple jurisdictions
- Monitor stakeholder positions and influence networks
- Analyze regulatory trends and emerging issues

### **Research & Intelligence**
- Build comprehensive political knowledge bases
- Discover hidden connections between entities and events
- Generate temporal analysis of policy evolution

## 🏷️ System Tags

`#political-monitoring` `#ai-analysis` `#knowledge-graph` `#regulatory-intelligence` `#automated-etl` `#temporal-analysis` `#chat-interface` `#document-processing`

## 📞 Support & Resources

- **Documentation**: Browse component READMEs for detailed guides
- **Issues**: Check common troubleshooting in component documentation
- **Configuration**: Refer to `.env.example` and component configs
- **Performance**: See [optimization guides](docs/specs/) for production deployment

## 🤝 Contributing

1. Read component-specific development guides
2. Follow the testing standards in `tests/README.md`
3. Ensure all tests pass: `just test`
4. Format code: `just format && just typecheck`

---

**v0.2.0** - Built with Kodosumi, Graphiti, LangGraph, and Ray | [Release Notes](docs/CHANGELOG.md)