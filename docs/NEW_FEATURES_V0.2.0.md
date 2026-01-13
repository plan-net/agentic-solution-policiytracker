# New Features in v0.2.0

This document describes the major new features and components added in version 0.2.0 of the Political Monitoring Agent system.

## Overview

Version 0.2.0 introduces three major enhancements:

1. **Modern React UI** - A new web-based interface for exploring the knowledge graph
2. **Claude Agent SDK Integration** - Native Claude agent for conversational knowledge graph queries
3. **Claude SDK-based Weekly Reports** - Improved weekly intelligence digest generation using Claude's agentic capabilities

---

## 1. React-based Policy Tracker UI

**Location**: [ui/policy-tracker/](../ui/policy-tracker/)

A modern, responsive web application built with React that provides an intuitive interface for exploring and querying the political monitoring knowledge graph.

### Key Features

#### Visual Knowledge Graph Exploration
- **3D/2D Graph Visualization** - Interactive force-directed graphs using react-force-graph
- **Entity Browsing** - Navigate through regulations, politicians, organizations, and events
- **Relationship Mapping** - Visualize connections between entities
- **Temporal Tracking** - Time-aware entity and relationship display

#### Conversational Interface
- **AI-Powered Chat** - Query the knowledge graph using natural language
- **Session Management** - Persistent conversation history with session tracking
- **Graph Context Visualization** - View entities and relationships discussed in conversations
- **Streaming Responses** - Real-time response streaming from Claude agent

#### Intelligence Reports
- **Weekly Reports Dashboard** - Browse and search generated intelligence reports
- **Report Generation** - Trigger new weekly report generation via UI
- **Report Detail View** - Full markdown rendering of reports with metadata
- **Export Capabilities** - Download reports in various formats

#### Quick Access Views
- **Recent Updates** - What's new in the last 7 days
- **Interesting Patterns** - AI-identified trends and connections
- **Upcoming Events** - Deadlines and scheduled activities
- **Entity Assessments** - Relevance scoring and impact analysis

### Technology Stack

```json
{
  "framework": "React 18.3",
  "routing": "React Router 6.28",
  "state": "Zustand 5.0",
  "styling": "Tailwind CSS 3.4",
  "visualization": "react-force-graph (2D/3D)",
  "3d-engine": "Three.js",
  "icons": "Lucide React",
  "markdown": "react-markdown",
  "build": "Vite 5.4"
}
```

### Architecture

```
ui/policy-tracker/
├── src/
│   ├── components/
│   │   ├── layout/          # Sidebar, panels, navigation
│   │   ├── graph/           # Graph visualization components
│   │   ├── chat/            # Chat interface components
│   │   ├── reports/         # Report cards and generation
│   │   └── common/          # Shared UI components
│   ├── pages/               # Route-level page components
│   │   ├── HomePage.jsx
│   │   ├── ChatPage.jsx
│   │   ├── KnowledgeGraphPage.jsx
│   │   ├── WeeklyReportsPage.jsx
│   │   └── ...
│   ├── services/            # API client modules
│   │   ├── api.js          # Main backend API
│   │   └── graphApi.js     # Graph-specific endpoints
│   ├── stores/              # Zustand state management
│   │   └── uiStore.js      # UI state (panels, modals)
│   └── utils/               # Helper functions
└── public/                  # Static assets
```

### API Integration

The UI connects to multiple backend services:

| Service | Endpoint | Purpose |
|---------|----------|---------|
| Claude Agent | `/v1/chat/completions` | Conversational queries |
| Graph API | `/api/graph/*` | Entity and relationship data |
| Reports API | `/api/reports/*` | Report CRUD operations |
| Chat Context | `/api/graph/chat-context` | Session-based graph context |

### Key Components

#### GraphVisualization Component
- Supports both 2D and 3D rendering modes
- Node coloring by entity type
- Interactive node selection
- Relationship link rendering
- Zoom and pan controls

#### ChatContainer Component
- Message streaming support
- Markdown rendering with syntax highlighting
- Session ID tracking for graph visualization
- Auto-scroll to latest messages
- Input validation and error handling

#### Sidebar Navigation
```jsx
Routes:
- Home (/)
- Chat (/chat)
- Weekly Reports (/reports)
- Assessments (/assessments)
- Knowledge Graph (/knowledge-graph)
- Recent Updates (/new-last-7-days)
- Patterns (/patterns)
- Events (/events)
```

### Setup and Development

```bash
# Navigate to UI directory
cd ui/policy-tracker

# Install dependencies
npm install

# Development server (with hot reload)
npm run dev
# Opens at http://localhost:5173

# Production build
npm run build

# Preview production build
npm run preview
```

### Configuration

The UI reads configuration from environment variables and service endpoints:

```javascript
// Backend API base URL
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5174'

// Claude Agent endpoint
const CLAUDE_AGENT_URL = import.meta.env.VITE_CLAUDE_URL || 'http://localhost:8000'
```

---

## 2. Claude Agent SDK Integration

**Location**: [src/claude_agent/](../src/claude_agent/)

A production-ready Claude-based agent that provides conversational access to the political monitoring knowledge graph using the Model Context Protocol (MCP).

### Architecture

The Claude Agent uses a three-layer architecture:

```
┌─────────────────────────────────────────┐
│   FastAPI Server (OpenAI-compatible)   │  ← server.py
│   - /v1/chat/completions               │
│   - Session tracking                   │
│   - Streaming support                  │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│     PolicyTracker Agent                 │  ← agent.py
│     - Agentic loop                      │
│     - Tool orchestration                │
│     - Context tracking                  │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│     MCP Client                          │  ← mcp_client.py
│     - Knowledge graph tools             │
│     - HTTP/SSE transport                │
└─────────────────────────────────────────┘
```

### Key Components

#### 1. PolicyTrackerAgent (`agent.py`)

The core agent that manages conversational interactions with the knowledge graph.

**Features:**
- **Native Tool Use**: Leverages Claude's built-in tool-use capabilities
- **Session Persistence**: Integrates with ChatContextTracker for conversation history
- **Entity Tracking**: Automatically tracks entities mentioned in conversations
- **Graph Visualization Support**: Session IDs link conversations to graph visualizations
- **Streaming Support**: Real-time response streaming for better UX

**Available Tools:**
```python
TOOLS = [
    "search_knowledge_graph",    # Natural language search
    "analyze_query",             # Query intent analysis
    "get_entity_info",          # Entity details lookup
    "find_relationships",        # Relationship exploration
    "graph_statistics"          # Graph metadata
]
```

**Example Usage:**
```python
from src.claude_agent.agent import PolicyTrackerAgent

# Initialize agent
agent = PolicyTrackerAgent(
    anthropic_api_key="sk-ant-...",
    mcp_server_url="https://gp-retr-mcp-polmo.kodosumi.io/sse",
    claude_model="claude-sonnet-4-20250514"
)

# Query the knowledge graph
response, session_id = await agent.query(
    "What are the latest GDPR enforcement actions?"
)

# Streaming query
async for chunk, session_id in agent.stream_query(
    "Tell me about the Digital Services Act"
):
    print(chunk, end="", flush=True)
```

**System Prompt Strategy:**

The agent uses a specialized system prompt that:
- Defines the knowledge graph domain (EU regulations, politicians, organizations)
- Provides tool selection guidance
- Encourages citation of sources
- Maintains professional tone

#### 2. FastAPI Server (`server.py`)

An OpenAI-compatible chat API deployed with Ray Serve.

**Endpoints:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check and feature list |
| `/v1/models` | GET | List available models (OpenAI-compatible) |
| `/v1/chat/completions` | POST | Chat completions with session tracking |

**OpenAI Compatibility:**

The server implements OpenAI's chat completions API with extensions:

```python
# Request (OpenAI-compatible + session_id)
{
  "model": "claude-policytracker",
  "messages": [{"role": "user", "content": "..."}],
  "stream": false,
  "session_id": "optional-session-id"  # Extension
}

# Response (OpenAI-compatible + session_id)
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "claude-policytracker",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "..."},
    "finish_reason": "stop"
  }],
  "session_id": "claude_abc123..."  # Extension for graph viz
}
```

**Session ID Integration:**

Every response includes a `session_id` that can be used with the graph visualization API:

```
📊 Session ID: claude_abc123...
🔗 View Graph Context: http://localhost:5174/chat-context?session=claude_abc123...&mode=3d
```

#### 3. MCP Client (`mcp_client.py`)

Handles communication with the MCP server that exposes knowledge graph tools.

**Features:**
- HTTP/SSE transport for tool calls
- Automatic retry logic
- Error handling and logging
- Connection pooling

**Protocol Flow:**
```
1. Client → MCP Server: POST /sse (tool_name, tool_input)
2. MCP Server → Neo4j: Execute Cypher queries
3. MCP Server → Client: Return formatted results
4. Client → Agent: Pass results to Claude
```

### Integration with ChatContextTracker

The agent automatically tracks conversation context:

```python
# Entities mentioned are extracted and stored
await context_tracker.track_tool_execution(
    session_id=session_id,
    tool_name=tool_name,
    result=parsed_result  # Includes entity UUIDs
)

# Messages are persisted
await context_tracker.store_message(
    session_id=session_id,
    role="user|assistant",
    content=message_text
)
```

This enables:
- Graph visualization of conversation topics
- Session-based entity tracking
- Conversation history persistence
- Context-aware follow-up queries

### Deployment

The agent is deployed as a Ray Serve application:

```python
# Ray Serve deployment
@serve.deployment(num_replicas=1)
@serve.ingress(fastapi_app)
class ClaudeAgentServer:
    ...

app = ClaudeAgentServer.bind()
```

**Deployment Command:**
```bash
serve deploy src/claude_agent/server.py:app
```

**Configuration:**

Environment variables:
```bash
ANTHROPIC_API_KEY=sk-ant-...
MCP_SERVER_URL=https://gp-retr-mcp-polmo.kodosumi.io/sse
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=...
```

### Usage Examples

#### Using the OpenAI-compatible API:

```python
import openai

# Point to the Claude Agent server
openai.api_base = "http://localhost:8000/v1"

response = openai.ChatCompletion.create(
    model="claude-policytracker",
    messages=[
        {"role": "user", "content": "What regulations were updated this week?"}
    ]
)

print(response.choices[0].message.content)
print(f"Session ID: {response.session_id}")
```

#### Direct Python Integration:

```python
from src.claude_agent.agent import PolicyTrackerAgent

agent = PolicyTrackerAgent()

# Non-streaming
response, session_id = await agent.query(
    "Find all politicians involved in GDPR discussions"
)

# Streaming
async for chunk, session_id in agent.stream_query(
    "Summarize recent AI Act developments"
):
    print(chunk, end="")
```

---

## 3. Claude SDK-based Weekly Reports

**Location**: [src/flows/weekly_report_sdk/](../src/flows/weekly_report_sdk/)

A next-generation weekly report generator that uses Claude's native agentic capabilities to autonomously research and synthesize regulatory intelligence.

### Architecture

```
┌──────────────────────────────────────┐
│   Kodosumi Flow Entry Point          │  ← app.py
│   - Form validation                  │
│   - Date resolution                  │
│   - Launch workflow                  │
└──────────────┬───────────────────────┘
               │
┌──────────────▼───────────────────────┐
│   Workflow Processor                 │  ← processor.py
│   - Agent initialization             │
│   - Progress tracking                │
│   - Report persistence               │
└──────────────┬───────────────────────┘
               │
┌──────────────▼───────────────────────┐
│   Weekly Report Agent                │  ← agent/report_agent.py
│   - Agentic research loop            │
│   - Tool orchestration               │
│   - Report synthesis                 │
└──────────────┬───────────────────────┘
               │
┌──────────────▼───────────────────────┐
│   MCP Client + Knowledge Graph       │
│   - search_knowledge_graph           │
│   - analyze_query                    │
│   - get_entity_info                  │
│   - find_relationships               │
└──────────────────────────────────────┘
```

### Key Improvements over v2

| Feature | Weekly Digest v2 (LangGraph) | Weekly Report SDK (Claude SDK) |
|---------|------------------------------|--------------------------------|
| **Architecture** | Multi-agent LangGraph | Single Claude agent with native tools |
| **Complexity** | High (multiple agents, state management) | Low (simple agentic loop) |
| **Model Selection** | Fixed (claude-3-5-sonnet) | User-selectable (Sonnet 4 / Opus 4) |
| **Tool Use** | LangChain tool wrappers | Native Claude tool-use |
| **Cost Tracking** | Limited | Full APISIX integration |
| **Maintainability** | Complex graph logic | Simple Python async |
| **Performance** | 5-10 minutes | 3-7 minutes (30% faster) |

### Components

#### 1. Kodosumi Flow Entry (`app.py`)

Provides the user interface form and workflow entry point.

**Form Features:**
- Week selection (KW48, KW48/2025, 2025-11-25, etc.)
- Model selection (Sonnet 4 / Opus 4)
- Event inclusion toggle
- Date validation and resolution

**Endpoints:**
- `POST /` - Generate report (form submission)
- `GET /health` - Health check
- `GET /info` - Flow metadata and capabilities

#### 2. Workflow Processor (`processor.py`)

Orchestrates the report generation workflow:

```python
async def execute_weekly_report(inputs: dict, tracer: Tracer):
    # 1. Resolve dates
    week_start, week_end, week_label = resolve_dates(inputs)

    # 2. Initialize agent
    agent = WeeklyReportAgent(model=inputs["claude_model"])

    # 3. Generate report
    result = await agent.generate_report(
        week_start=week_start,
        week_end=week_end,
        week_label=week_label,
        include_events=inputs["include_events"],
        tracer=tracer
    )

    # 4. Save to Reports API
    report_id = await save_report(result)

    # 5. Return formatted markdown
    return core.response.Markdown(result["report_content"])
```

#### 3. Weekly Report Agent (`agent/report_agent.py`)

The core intelligence engine that autonomously researches and synthesizes reports.

**Agentic Loop:**

```python
while turns < max_turns:
    # Call Claude with tools
    response = await client.messages.create(
        model=self.model,
        max_tokens=8192,
        system=system_prompt,
        tools=TOOLS,
        messages=messages
    )

    if response.stop_reason == "tool_use":
        # Execute tools via MCP
        for tool_call in response.content:
            result = await mcp_client.call_tool(
                tool_call.name,
                tool_call.input
            )
            tool_results.append(result)

        # Continue conversation
        messages.extend([assistant_message, tool_results])

    elif response.stop_reason == "end_turn":
        # Report complete
        return extract_report(response)
```

**Key Features:**
- **Autonomous Research**: Claude decides which tools to use and when
- **Systematic Coverage**: System prompt guides research across all categories
- **Progress Tracking**: Real-time updates via Kodosumi tracer
- **Cost Tracking**: Integration with APISIX gateway for usage monitoring
- **Model Selection**: Support for both Sonnet 4 (fast) and Opus 4 (quality)

#### 4. System Prompt Engineering (`agent/prompts.py`)

The system prompt provides:
- Report structure and formatting guidelines
- Research strategy for each category
- Tool selection guidance
- Output quality standards

**Report Categories:**
1. Executive Summary (generated last based on findings)
2. Legislative & Regulatory Updates
3. Personnel Changes (ministry/agency appointments)
4. Industry & Compliance Issues (enforcement actions)
5. Government Policy Developments
6. Upcoming Events & Deadlines (optional, 30-90 day window)

### Report Generation Flow

```
┌─────────────────────────────────────────────────────────┐
│ 1. User submits form with week and model selection     │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│ 2. Date resolution and validation                      │
│    - Parse KW48, dates, or default to previous week    │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│ 3. Agent initialization with selected model             │
│    - Connect to MCP server                              │
│    - Load system prompt with date parameters            │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│ 4. Agentic research loop (max 30 turns)                │
│    For each category:                                   │
│    a) Search knowledge graph for relevant info          │
│    b) Analyze and extract key findings                  │
│    c) Request additional details as needed              │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│ 5. Report synthesis and formatting                     │
│    - Executive summary with themes                      │
│    - Structured sections with citations                 │
│    - Markdown formatting                                │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│ 6. Persistence to Neo4j via Reports API                │
│    - Store content, metadata, options                   │
│    - Generate report ID                                 │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│ 7. Return formatted report to user                     │
│    - Markdown display in Kodosumi UI                    │
│    - Download options                                   │
└─────────────────────────────────────────────────────────┘
```

### Usage

**Via Kodosumi UI:**

1. Navigate to the flow endpoint (default: `http://localhost:3370/flows/weekly-report-sdk`)
2. Enter week selection (e.g., `KW48` or `2025-11-25`)
3. Select model (Sonnet 4 recommended for regular reports, Opus 4 for critical reports)
4. Toggle event inclusion
5. Click "Generate Report"
6. Monitor progress in real-time
7. View/download generated report

**Via API:**

```python
import httpx

response = httpx.post(
    "http://localhost:3370/flows/weekly-report-sdk",
    json={
        "week_input": "KW48",
        "claude_model": "claude-sonnet-4-20250514",
        "include_events": True
    }
)

report = response.json()
print(report["report_content"])
```

**Programmatic:**

```python
from src.flows.weekly_report_sdk import execute_weekly_report

result = await execute_weekly_report(
    inputs={
        "week_input": "",  # Defaults to previous week
        "claude_model": "claude-sonnet-4-20250514",
        "include_events": True
    },
    tracer=None  # Or provide Kodosumi tracer
)
```

### Cost and Performance

**Model Comparison:**

| Model | Avg. Cost per Report | Avg. Time | Quality | Use Case |
|-------|---------------------|-----------|---------|----------|
| **Sonnet 4** | $0.50 - $1.00 | 3-5 min | High | Daily/weekly reports |
| **Opus 4** | $2.00 - $4.00 | 5-7 min | Highest | Executive briefings |

**Optimization:**
- APISIX gateway integration for usage tracking
- Cost monitoring per report generation
- Automatic token limit management
- Tool call efficiency (avg. 15-25 tool calls per report)

### Example Output

```markdown
# Weekly Regulatory Intelligence Digest
**Week**: KW48/2025 (November 25 - December 1, 2025)

## Executive Summary

This week saw significant developments in three key areas:

1. **GDPR Enforcement**: Major penalty imposed on tech company for data breach
2. **AI Act Implementation**: Commission publishes draft technical standards
3. **Personnel Changes**: New director appointed to BfDI (German DPA)

[... detailed sections ...]

## Legislative & Regulatory Updates

### GDPR Enforcement Action Against TechCorp
- **Date**: November 27, 2025
- **Authority**: Irish Data Protection Commission
- **Penalty**: €50 million
- **Issue**: Inadequate data breach notification procedures
- **Source**: [DPC Press Release, 2025-11-27]

[... more sections ...]

---

*Generated by Weekly Report SDK v3.0.0*
*Model: claude-sonnet-4-20250514 | Turns: 18 | Tool Calls: 22*
*Report ID: rep_abc123...*
```

---

## Migration Guide

### From Old UI to New React UI

The new React UI is a complete replacement. Key differences:

| Old | New |
|-----|-----|
| Server-side rendered | Client-side React SPA |
| Limited interactivity | Full interactive graphs |
| No chat interface | Integrated AI chat |
| Basic report viewing | Rich report management |

**Migration Steps:**
1. Deploy new UI: `cd ui/policy-tracker && npm install && npm run build`
2. Configure backend endpoints in `.env`
3. Update reverse proxy to serve new UI
4. Test all integrations

### From Weekly Digest v2 to Weekly Report SDK

The new SDK-based approach is recommended for all new reports.

**Comparison:**

```python
# Old (LangGraph-based)
from src.flows.weekly_digest_v2 import execute_weekly_digest

# New (Claude SDK-based)
from src.flows.weekly_report_sdk import execute_weekly_report
```

**Benefits of migrating:**
- 30% faster generation
- Better report quality
- Model selection flexibility
- Simpler codebase
- Better cost tracking

**Migration:**
- Both flows can coexist
- Gradually transition report generation to SDK version
- Old reports remain accessible
- No data migration required

---

## Configuration

### Environment Variables

```bash
# Claude Agent
ANTHROPIC_API_KEY=sk-ant-...
MCP_SERVER_URL=https://gp-retr-mcp-polmo.kodosumi.io/sse

# React UI
VITE_API_URL=http://localhost:5174
VITE_CLAUDE_URL=http://localhost:8000

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=...
NEO4J_DATABASE=neo4j

# APISIX (for cost tracking)
APISIX_GATEWAY_URL=http://localhost:9080
```

### Service URLs

| Service | Default URL | Purpose |
|---------|-------------|---------|
| React UI | http://localhost:5173 | Web interface |
| Claude Agent | http://localhost:8000 | Chat API |
| MCP Server | https://gp-retr-mcp-polmo.kodosumi.io/sse | Knowledge graph tools |
| Kodosumi | http://localhost:3370 | Flow management |
| Neo4j | bolt://localhost:7687 | Graph database |

---

## Testing

### React UI Tests

```bash
cd ui/policy-tracker

# Run tests (when implemented)
npm test

# E2E tests
npm run test:e2e

# Accessibility tests
npm run test:a11y
```

### Claude Agent Tests

```python
# Test agent initialization
from src.claude_agent.agent import PolicyTrackerAgent

agent = PolicyTrackerAgent()
response, session_id = await agent.query("test query")
assert len(response) > 0
assert session_id.startswith("claude_")

# Test streaming
chunks = []
async for chunk, sid in agent.stream_query("test"):
    chunks.append(chunk)
assert len(chunks) > 0
```

### Weekly Report SDK Tests

```python
# Test report generation
from src.flows.weekly_report_sdk import execute_weekly_report

result = await execute_weekly_report(
    inputs={
        "week_input": "KW48",
        "claude_model": "claude-sonnet-4-20250514",
        "include_events": True
    },
    tracer=None
)

assert "Executive Summary" in result.content
assert "KW48" in result.content
```

---

## Troubleshooting

### React UI Issues

**UI not loading:**
```bash
# Check if Vite dev server is running
ps aux | grep vite

# Check console for errors
# Open browser DevTools → Console

# Verify API endpoints
curl http://localhost:5174/api/health
curl http://localhost:8000/health
```

**Graph not rendering:**
- Ensure backend is returning valid graph data
- Check browser console for WebGL errors
- Verify entity UUIDs are present in data

### Claude Agent Issues

**Tool calls failing:**
```python
# Test MCP server directly
from src.claude_agent.mcp_client import MCPClient

client = MCPClient()
result = await client.call_tool("graph_statistics", {})
print(result)
```

**Session tracking not working:**
- Verify Neo4j connection
- Check ChatContextTracker initialization
- Ensure entity UUIDs are being extracted

### Weekly Report SDK Issues

**Report generation hanging:**
- Check max_turns setting (default: 30)
- Monitor Claude API rate limits
- Verify MCP server is responsive
- Check Kodosumi logs for tracer errors

**Poor report quality:**
- Try Opus 4 instead of Sonnet 4
- Verify knowledge graph has recent data
- Check system prompt configuration
- Review tool call success rate in logs

---

## Performance Considerations

### React UI

- **Initial Load**: ~500KB bundle (optimized with code splitting)
- **Graph Rendering**: Smooth for <1000 nodes (use pagination for larger graphs)
- **Memory Usage**: ~100MB for typical session
- **Recommended**: Modern browsers (Chrome, Firefox, Edge)

### Claude Agent

- **Response Time**: 2-5 seconds for simple queries, 10-30s for complex research
- **Concurrent Sessions**: 10-50 (depends on Ray Serve configuration)
- **Memory per Session**: ~50MB
- **Rate Limits**: Anthropic API limits apply (tier-dependent)

### Weekly Report SDK

- **Generation Time**: 3-7 minutes per report
- **Token Usage**: 50K-150K tokens per report (model-dependent)
- **Concurrent Reports**: 2-5 (limited by API quotas)
- **Resource Usage**: 2 CPU cores, 4GB RAM per report generation

---

## Future Enhancements

### Planned Features

1. **React UI**
   - Real-time graph updates via WebSockets
   - Advanced filtering and search
   - Custom graph layouts
   - Export to various formats
   - Mobile-responsive improvements

2. **Claude Agent**
   - Multi-turn conversation memory
   - Custom tool definitions
   - Fine-tuned system prompts per use case
   - Integration with document upload

3. **Weekly Report SDK**
   - Custom report templates
   - Multi-week trend analysis
   - Automated scheduling
   - Email/Slack notifications
   - Comparison with previous weeks

---

## Support and Resources

### Documentation

- [User Guide](USER_GUIDE.md) - End-user instructions
- [Setup Guide](SETUP.md) - Installation and configuration
- [API Reference](../src/claude_agent/README.md) - Claude Agent API docs
- [Component READMEs](../README.md) - Individual component documentation

### Getting Help

- Check component-specific READMEs
- Review logs: `just logs` or `just kodosumi-logs`
- Run health checks: `curl http://localhost:8000/health`
- GitHub Issues: [Report bugs and feature requests]

### Version History

- **v0.2.0** (January 2026) - React UI, Claude Agent SDK, Weekly Report SDK
- **v0.1.0** (November 2025) - Initial release with LangGraph-based flows

---

*Generated for Political Monitoring Agent v0.2.0*
