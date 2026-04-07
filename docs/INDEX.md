# Political Monitoring Agent - Documentation Index

## Overview

This directory contains comprehensive documentation for the Political Monitoring Agent v0.2.0 system.

---

## 📊 Cost Estimation & Budget Planning

**New!** Comprehensive cost estimation model for document ingestion pipeline.

### Cost Estimation Model
- **[Excel Assembly Guide](cost-estimation/EXCEL_ASSEMBLY_GUIDE.md)** - Complete guide to building the Excel cost estimation workbook
- **[CSV Templates](cost-estimation/csv-templates/)** - Ready-to-import CSV files for each sheet:
  - `01_Dashboard.csv` - Executive summary and quick estimator
  - `02_Input_Parameters.csv` - Configurable variables
  - `03_Pricing_Reference.csv` - API pricing reference table
  - `04_Cost_Calculator.csv` - Detailed cost breakdown with formulas
  - `05_Scenario_Comparison.csv` - Side-by-side scenario analysis
  - `06_Historical_Validation.csv` - Actual vs estimated cost tracking

### Features
- **Budget Planning**: Monthly and annual cost projections
- **Scenario Analysis**: Compare costs across different configurations
- **Interactive**: Adjust parameters and see instant cost updates
- **Validated**: Track actual costs vs estimates for accuracy improvement
- **Components Covered**:
  - ETL Collection Costs (Exa.ai, Apify)
  - LLM Processing Costs (entity extraction via Graphiti)
  - Embedding Generation Costs (episodes, entities, relationships)
  - Overhead and retry costs

---

## 🎯 Features & Capabilities

### Document Ingestion & Processing
- **[Data Ingestion Cost Reduction Strategies](features/DATA_INGESTION_COST_REDUCTION_STRATEGIES.md)** - Comprehensive cost optimization techniques
  - Chunk limiting strategy (39-85% savings)
  - Prompt caching implementation (50-90% savings)
  - Benchmark results and quality analysis

### Knowledge Graph
- **[Graphiti Integration](../agentic-solution-policiytracker/.claude/graphiti-patterns.md)** - Temporal knowledge graph patterns
- **[Political Schema](../src/graphrag/political_schema_v4.py)** - 28 entity types, 52 relationship types
- **[Episode Semantic Search](../agentic-solution-policiytracker/.claude/graphiti-patterns.md#episode-semantic-search-v021)** - Hybrid BM25 + vector search

### Multi-Agent Chat System
- **[Chat Patterns](../agentic-solution-policiytracker/.claude/chat-patterns.md)** - Multi-agent orchestration with LangGraph
- **[Tool Integration](../agentic-solution-policiytracker/.claude/tool-integration-patterns.md)** - 15 specialized knowledge graph tools

### ETL Pipeline
- **[ETL Patterns](../agentic-solution-policiytracker/.claude/etl-patterns.md)** - Automated data collection (weekly policy, daily news)
- **[Policy Landscape Collection](../src/etl/collectors/policy_landscape.py)** - EU regulations and policy changes
- **[News Collection](../src/etl/collectors/exa_news.py)** - Company-specific news articles

---

## 📈 Observability & Monitoring

### Cost Tracking
- **[Cost Analytics](observability/COST_ANALYTICS.md)** - APISIX-based LLM cost tracking
  - TimescaleDB storage
  - Grafana dashboards
  - Budget alerts
  - Cost Analytics API: `http://localhost:8090/api/costs/`

### LLM Operations
- **[Langfuse Integration](../agentic-solution-policiytracker/.claude/langfuse-prompts.md)** - Prompt management and tracing
- **[LangWatch](observability/LANGWATCH.md)** - LLM observability platform (if applicable)

### System Monitoring
- **Ray Dashboard**: `http://localhost:8265` - Service status and resource usage
- **Grafana**: `http://localhost:3002` - Visual cost trends
- **Neo4j Browser**: `http://localhost:7474` - Knowledge graph exploration

---

## 🏗️ Architecture & Patterns

### Core Architecture
- **[Project Architecture](../agentic-solution-policiytracker/.claude/project-architecture.md)** - v0.2.0 architecture overview
- **[Ray Deployment](../agentic-solution-policiytracker/.claude/ray-deployment-patterns.md)** - Distributed service deployment
- **[Kodosumi Flows](../agentic-solution-policiytracker/.claude/kodosumi-patterns.md)** - Document processing workflows

### Integration Patterns
- **[MCP Patterns](../agentic-solution-policiytracker/.claude/mcp-patterns.md)** - Model Context Protocol integration
- **[Azure Integration](../agentic-solution-policiytracker/.claude/azure-integration.md)** - Cloud storage patterns
- **[LangGraph Patterns](../agentic-solution-policiytracker/.claude/langgraph-patterns.md)** - Multi-agent workflow orchestration

---

## 🧪 Development & Testing

### Development Workflow
- **[Development Workflow](../agentic-solution-policiytracker/.claude/development-workflow.md)** - Quick development cycle
- **[Git Workflow](../agentic-solution-policiytracker/.claude/git-workflow.md)** - Branching and version control
- **[Testing Patterns](../agentic-solution-policiytracker/.claude/test-patterns.md)** - Testing best practices
- **[Testing Standards](../agentic-solution-policiytracker/.claude/testing-standards.md)** - Coverage requirements

### Quality Assurance
- Pre-commit checks: `just format && just typecheck`
- Test commands: `just test`, `just test-unit`, `just test-integration`
- Coverage requirement: 90% minimum

---

## 🚀 Operations & Deployment

### Service Management
- **Start services**: `just start` - Full stack startup
- **Deploy applications**: `just deploy-all` - Redeploy Ray services
- **Check status**: `just status` - Health check all services
- **View logs**: `just ray-logs` - Ray application logs

### Key URLs
- **Chat Interface**: `http://localhost:3000` - Open WebUI for natural language queries
- **Kodosumi Admin**: `http://localhost:3370` - Flow management (admin/admin)
- **Ray Dashboard**: `http://localhost:8265` - Service monitoring
- **Neo4j Browser**: `http://localhost:7474` - Knowledge graph (neo4j/password123)
- **Airflow**: `http://localhost:8080` - ETL pipeline monitoring (admin/admin)
- **Langfuse**: `http://localhost:3001` - LLM tracing
- **Cost Analytics**: `http://localhost:8090` - Cost tracking API

---

## 📚 Reference Materials

### Configuration Files
- **[config.yaml](../config.yaml)** - Ray Serve deployment configuration
- **[pyproject.toml](../pyproject.toml)** - Python dependencies
- **[.env.template](../.env.template)** - Environment variables template
- **[llm_pricing.yaml](../apisix/config/llm_pricing.yaml)** - LLM model pricing reference

### Scripts
- **[calculate_reembedding_cost.py](../calculate_reembedding_cost.py)** - Embedding cost calculator
- **[backfill_episode_embeddings.py](../scripts/backfill_episode_embeddings.py)** - Episode embedding backfill
- **[sync_config.py](../scripts/sync_config.py)** - Sync .env to config.yaml

---

## 📖 Getting Started

### New Developers
1. Read **[Project Architecture](../agentic-solution-policiytracker/.claude/project-architecture.md)**
2. Follow **[Development Workflow](../agentic-solution-policiytracker/.claude/development-workflow.md)**
3. Review **[Testing Standards](../agentic-solution-policiytracker/.claude/testing-standards.md)**
4. Check **[Cost Estimation Model](cost-estimation/EXCEL_ASSEMBLY_GUIDE.md)** for budget planning

### Cost Analysis
1. Review **[Cost Estimation Model](cost-estimation/EXCEL_ASSEMBLY_GUIDE.md)**
2. Import **[CSV Templates](cost-estimation/csv-templates/)** into Excel
3. Update **[Pricing Reference](cost-estimation/csv-templates/03_Pricing_Reference.csv)** with current API costs
4. Track actual costs in **[Historical Validation](cost-estimation/csv-templates/06_Historical_Validation.csv)**

### Budget Planning
1. Configure **[Input Parameters](cost-estimation/csv-templates/02_Input_Parameters.csv)** with expected volumes
2. Review **[Scenario Comparison](cost-estimation/csv-templates/05_Scenario_Comparison.csv)** for different configurations
3. Monitor monthly costs via **[Dashboard](cost-estimation/csv-templates/01_Dashboard.csv)**
4. Validate against actual costs from Cost Analytics API: `http://localhost:8090/api/costs/summary`

---

## 🔧 Troubleshooting

### Common Issues
- **Services not starting**: Check `docker compose ps` and restart with `just start`
- **Ray deployment fails**: Review logs with `just ray-logs`
- **Cost estimates inaccurate**: Update **Pricing Reference** and validate against actual costs
- **Neo4j connection issues**: Verify Neo4j is running with `docker ps | grep neo4j`

### Support Resources
- **Claude Code Help**: `/help` command
- **GitHub Issues**: Report issues at repository issues page
- **Cost Analytics API**: `curl http://localhost:8090/api/costs/summary?days=30`
- **Grafana Dashboards**: `http://localhost:3002` for visual monitoring

---

## 📄 Document History

- **2025-01-XX**: Added comprehensive cost estimation model with Excel templates
- **2025-01-14**: Added episode semantic search (v0.2.1)
- **2024-12-XX**: Initial documentation structure (v0.2.0)

---

## 🔗 Quick Links

| Resource | URL | Credentials |
|----------|-----|-------------|
| Chat Interface | http://localhost:3000 | - |
| Kodosumi Admin | http://localhost:3370 | admin/admin |
| Ray Dashboard | http://localhost:8265 | - |
| Neo4j Browser | http://localhost:7474 | neo4j/password123 |
| Airflow | http://localhost:8080 | admin/admin |
| Langfuse | http://localhost:3001 | - |
| Cost Analytics API | http://localhost:8090/api/costs/summary | - |
| Grafana | http://localhost:3002 | - |

---

**Version**: 0.2.1
**Last Updated**: 2025-01-XX
**Status**: Production Ready with Cost Estimation Model
