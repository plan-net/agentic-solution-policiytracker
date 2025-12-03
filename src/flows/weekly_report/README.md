# Weekly Regulatory Intelligence Digest

A Kodosumi flow that generates comprehensive weekly reports on EU and German regulatory developments using LangGraph multi-agent workflow and Graphiti temporal knowledge graph queries.

## Overview

The Weekly Report flow produces a structured intelligence briefing covering:

1. **Legislative & Regulatory Updates** - New laws, directives, and regulatory guidance
2. **Personnel Changes** - Ministry appointments and regulatory body leadership changes
3. **Industry & Compliance Issues** - Enforcement actions, fines, and compliance developments
4. **Government Policy Developments** - Initiatives, strategies, and coalition positions
5. **Upcoming Events & Deadlines** - Compliance deadlines and scheduled hearings

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Weekly Report Flow (Kodosumi)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  User Input: Calendar Week (KW48) or Monday Date (2025-11-25)               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                   LangGraph Multi-Agent Workflow                     │    │
│  │                                                                      │    │
│  │  ┌──────────────┐    ┌─────────────────┐    ┌──────────────────┐   │    │
│  │  │ DateResolver │───▶│ CategoryAgents  │───▶│ ReportSynthesizer│   │    │
│  │  │              │    │ (5 parallel)    │    │                  │   │    │
│  │  └──────────────┘    └─────────────────┘    └──────────────────┘   │    │
│  │                             │                                       │    │
│  │                             ▼                                       │    │
│  │                    ┌─────────────────┐                              │    │
│  │                    │ Graphiti Tools  │                              │    │
│  │                    │ (Temporal KG)   │                              │    │
│  │                    └─────────────────┘                              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  Output: Structured Markdown Report with 5 Category Sections                │
└─────────────────────────────────────────────────────────────────────────────┘
```

## File Structure

```
src/flows/weekly_report/
├── __init__.py                    # Package exports
├── app.py                         # Kodosumi ServeAPI endpoint
├── processor.py                   # LangGraph workflow orchestration
├── models.py                      # Pydantic state models
├── date_resolver.py               # Week input parsing
├── README.md                      # This documentation
├── agents/
│   ├── __init__.py
│   ├── category_researchers.py    # 5 category research agents
│   └── report_synthesizer.py      # Report assembly agent
├── prompts/
│   ├── __init__.py
│   └── category_prompts.py        # System prompts for agents
├── templates/
│   └── weekly_report.md.j2        # Jinja2 report template
└── tools/
    └── __init__.py
```

## Usage

### Via Kodosumi Admin UI

1. Open Kodosumi Admin at `http://localhost:3370`
2. Navigate to the "Weekly Report" flow
3. Enter a week selection:
   - `KW48` - Calendar week 48 of current year
   - `KW48/2025` - Calendar week 48 of 2025
   - `2025-11-25` - Monday date (ISO format)
   - `25.11.2025` - Monday date (German format)
   - Leave empty for previous week
4. Click "Generate Report"

### Via API

```bash
# Trigger via HTTP POST
curl -X POST http://localhost:8001/weekly-report/ \
  -H "Content-Type: application/json" \
  -d '{"week_input": "KW48"}'
```

### Via Python

```python
from src.flows.weekly_report.processor import WeeklyReportProcessor
from kodosumi import tracer

inputs = {"week_input": "KW48/2025"}
processor = WeeklyReportProcessor(tracer, inputs)

for result in processor.run():
    print(result)
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEO4J_URI` | Neo4j connection URI | `bolt://localhost:7687` |
| `NEO4J_USER` | Neo4j username | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j password | `password` |
| `NEO4J_DATABASE` | Neo4j database name | - |
| `OPENAI_API_KEY` | OpenAI API key for LLM | Required |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4o-mini` |

### Ray Serve Configuration

The flow is configured in `config.yaml`:

```yaml
- name: weekly-report
  route_prefix: /weekly-report
  import_path: src.flows.weekly_report.app:fast_app
  runtime_env:
    env_vars:
      PYTHONPATH: .
      # ... environment variables
  ray_actor_options:
    num_cpus: 2
    memory: 4000000000  # 4GB
  autoscaling_config:
    min_replicas: 1
    max_replicas: 2
```

## Components

### Date Resolver (`date_resolver.py`)

Parses user input into a week date range. Supports:

- **KW format**: `KW48`, `KW48/2025`, `KW48/25`
- **ISO date**: `2025-11-25`
- **German date**: `25.11.2025`
- **Week number only**: `48`
- **Empty input**: Defaults to previous week

```python
from src.flows.weekly_report.date_resolver import resolve_week_input

result = resolve_week_input("KW48/2025")
# Returns:
# {
#     "week_start": datetime(2025, 11, 24, 0, 0, 0),
#     "week_end": datetime(2025, 11, 30, 23, 59, 59),
#     "week_number": 48,
#     "year": 2025,
#     "week_label": "KW48/2025"
# }
```

### Category Research Agents (`agents/category_researchers.py`)

Five specialized agents that query Graphiti for category-specific findings:

| Agent | Focus Areas | Entity Types |
|-------|-------------|--------------|
| `LegislativeResearchAgent` | Laws, regulations, DSA/DMA, GDPR | REGULATION, LAW, DIRECTIVE |
| `PersonnelResearchAgent` | Appointments, resignations | PERSON, MINISTRY, COMMITTEE |
| `ComplianceResearchAgent` | Enforcement, fines, investigations | COMPANY, ENFORCEMENT_ACTION |
| `PolicyResearchAgent` | Government initiatives, strategies | MINISTRY, POLICY, STRATEGY |
| `EventsResearchAgent` | Deadlines, hearings, consultations | EVENT, DEADLINE, CONSULTATION |

### Report Synthesizer (`agents/report_synthesizer.py`)

Combines findings from all category agents:

1. Generates executive summary using LLM
2. Cross-references findings across categories
3. Orders findings by priority within sections
4. Renders final report using Jinja2 template

### Models (`models.py`)

Key data structures:

```python
class Finding(BaseModel):
    title: str           # Brief headline
    content: str         # Detailed description
    category: ReportCategory
    priority: FindingPriority  # high, medium, low
    date: Optional[datetime]
    source: Optional[str]
    entities: list[str]
    forward_looking: bool

class WeeklyReportState(BaseModel):
    week_input: str
    week_start: Optional[datetime]
    week_end: Optional[datetime]
    legislative_findings: list[Finding]
    personnel_findings: list[Finding]
    compliance_findings: list[Finding]
    policy_findings: list[Finding]
    events_findings: list[Finding]
    executive_summary: str
    final_report: str
```

## Workflow Execution

The LangGraph workflow executes in three phases:

### Phase 1: Date Resolution
```
START → resolve_dates
```
Parses user input to determine the target week.

### Phase 2: Parallel Research (Fan-out)
```
resolve_dates → research_legislative
             → research_personnel
             → research_compliance
             → research_policy
             → research_events
```
All five category agents execute concurrently, querying Graphiti for relevant findings.

### Phase 3: Synthesis (Fan-in)
```
[all research nodes] → synthesize_report → END
```
Combines all findings into the final report.

## Output Format

The generated report follows this structure:

```markdown
# Weekly Regulatory Intelligence Digest

**KW48/2025** (24 November - 30 November 2025)

---

## Executive Summary

[3-4 sentences summarizing key developments]

---

## 1. Legislative & Regulatory Updates

### 1. [Finding Title]
[Finding content with specific dates, names, provisions]
*Date: 25 November 2025 | Source: Official Journal*

---

## 2. Personnel Changes
...

## 3. Industry & Compliance Issues
...

## 4. Government Policy Developments
...

## 5. Upcoming Events & Deadlines
...

---

## Report Statistics

| Metric | Value |
|--------|-------|
| Total Findings | 23 |
| High Priority Items | 5 |
| Forward-Looking Items | 8 |

---

*Generated: 2025-12-02 10:30 UTC | Source: Graphiti Knowledge Graph*
```

## Customization

### Adding New Categories

1. Add category to `models.py`:
```python
class ReportCategory(str, Enum):
    LEGISLATIVE = "legislative"
    # ... existing
    NEW_CATEGORY = "new_category"
```

2. Create agent in `category_researchers.py`:
```python
class NewCategoryResearchAgent(BaseCategoryResearchAgent):
    def __init__(self, graphiti_client, llm):
        super().__init__(
            graphiti_client=graphiti_client,
            llm=llm,
            category=ReportCategory.NEW_CATEGORY,
            system_prompt=NEW_CATEGORY_SYSTEM_PROMPT,
        )

    def get_search_queries(self, week_start, week_end):
        return ["query 1", "query 2"]

    def get_entity_types(self):
        return ["ENTITY_TYPE_1", "ENTITY_TYPE_2"]
```

3. Add to workflow in `processor.py`
4. Update template in `templates/weekly_report.md.j2`

### Modifying System Prompts

Edit `prompts/category_prompts.py` to adjust agent behavior:

```python
LEGISLATIVE_SYSTEM_PROMPT = """
You are a Legislative & Regulatory Research Agent...

## Focus Areas
- Your custom focus areas

## Entity Types to Search
- CUSTOM_ENTITY_TYPE
"""
```

## Troubleshooting

### Common Issues

1. **"No findings in category"**
   - Check if Graphiti has relevant data for the time period
   - Verify Neo4j connection and database selection
   - Review search queries in the agent

2. **"Date resolution failed"**
   - Verify input format (KW48, KW48/2025, or YYYY-MM-DD)
   - Check that week number is valid (1-53)

3. **"Graphiti connection failed"**
   - Verify Neo4j is running: `docker ps | grep neo4j`
   - Check credentials in environment variables
   - Ensure database exists

4. **"LLM processing failed"**
   - Verify OPENAI_API_KEY is set
   - Check API rate limits
   - Review model name in OPENAI_MODEL

### Debugging

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
```

View Ray logs:
```bash
just ray-logs
```

Check specific worker logs:
```bash
tail -f /tmp/ray/session_latest/logs/worker-*.out
```

## Dependencies

- `kodosumi` - Workflow orchestration
- `langgraph` - Multi-agent workflow
- `graphiti-core` - Temporal knowledge graph
- `langchain-openai` - LLM integration
- `pydantic` - Data validation
- `jinja2` - Report templating
- `structlog` - Logging

## Related Flows

- **Flow 1 (Data Ingestion)**: Populates the knowledge graph with documents
- **Flow 1B (Bulk Auto)**: Auto-detects and processes new documents
- **Chat Server**: Interactive queries against the same knowledge graph

## Version History

- **v0.1.0** (2025-12-02): Initial implementation
  - 5 category research agents
  - LangGraph parallel execution
  - Graphiti temporal queries
  - Jinja2 report templating
