# Temporal Tools Implementation

## Overview

This document describes the implementation of 5 temporal analysis tools added to the Graph Retrieval MCP Server. These tools enable time-based queries, historical tracking, and policy evolution analysis for the PolicyTracker system.

**Implementation Date**: January 2025
**MCP Server Port**: 8003
**Total Tools**: 11 (6 existing + 5 temporal)

---

## Problem Statement

### Gap Analysis

The knowledge graph retrieval system had temporal awareness built into its query analysis layer, but:

1. **Temporal tools existed but were NOT exposed via MCP** - The 5 temporal tools in `src/chat/tools/temporal.py` (LangChain-based) were not accessible to the Claude Agent SDK
2. **Claude Agent couldn't use temporal queries** - Without MCP exposure, temporal filtering was unavailable
3. **System prompts lacked temporal guidance** - No explicit instructions for when to use temporal tools

### Solution

Add 5 temporal tools to the existing Graph Retrieval MCP server (port 8003), making them available to all Claude Agent SDK consumers.

---

## New Tools

| Tool | Description | Use Case |
|------|-------------|----------|
| `search_by_date_range` | Search within specific date ranges | "What happened between 2024-01-01 and 2024-06-30?" |
| `get_entity_history` | Track entity evolution over time | "How has GDPR changed over the past year?" |
| `find_concurrent_events` | Find events around a reference date | "What else happened around March 2024?" |
| `compare_timelines` | Compare timelines of multiple entities | "Compare DSA and DMA development" |
| `track_policy_evolution` | Track policy lifecycle phases | "How has the AI Act evolved?" |

---

## Tool Specifications

### 1. search_by_date_range

**Purpose**: Search for events, policies, or regulatory changes within a specific date range.

**Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query |
| `start_date` | string | Yes | - | Start date (YYYY-MM-DD) |
| `end_date` | string | Yes | - | End date (YYYY-MM-DD) |
| `max_results` | integer | No | 10 | Maximum results |

**Example**:
```json
{
  "query": "AI regulation enforcement",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "max_results": 15
}
```

**Response**: Results scored by temporal relevance (0.0-1.0), with high-relevance items (>0.7) flagged.

---

### 2. get_entity_history

**Purpose**: Track the historical evolution of an entity over time.

**Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `entity_name` | string | Yes | - | Entity to track |
| `days_back` | integer | No | 365 | Days of history |
| `event_types` | array[string] | No | null | Filter by event types |

**Event Types**:
- `regulatory` - Regulations, rules, compliance, enforcement
- `policy` - Laws, acts, directives, legislation
- `business` - Mergers, acquisitions, partnerships
- `product` - Launches, releases, updates
- `legal` - Lawsuits, rulings, settlements

**Example**:
```json
{
  "entity_name": "DSGVO",
  "days_back": 730,
  "event_types": ["regulatory", "enforcement"]
}
```

---

### 3. find_concurrent_events

**Purpose**: Find events that occurred around a specific reference date.

**Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `reference_date` | string | Yes | - | Reference date (YYYY-MM-DD) |
| `window_days` | integer | No | 30 | Days before/after |
| `event_context` | string | No | null | Context filter |

**Example**:
```json
{
  "reference_date": "2024-03-15",
  "window_days": 45,
  "event_context": "data protection"
}
```

---

### 4. compare_timelines

**Purpose**: Compare the timelines of multiple entities to see parallel evolution.

**Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `entities` | array[string] | Yes | - | 2-5 entity names |
| `time_period` | integer | No | 365 | Comparison period (days) |
| `comparison_focus` | string | No | null | Aspect to compare |

**Example**:
```json
{
  "entities": ["DSA", "DMA", "AI Act"],
  "time_period": 730,
  "comparison_focus": "enforcement"
}
```

**Constraints**: Minimum 2 entities, maximum 5 entities.

---

### 5. track_policy_evolution

**Purpose**: Track how a policy or regulation has evolved through lifecycle phases.

**Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `policy_name` | string | Yes | - | Policy to track |
| `evolution_period` | integer | No | 730 | Period in days (~2 years) |
| `evolution_aspects` | array[string] | No | null | Aspects to track |

**Evolution Phases**:
- `proposal` - Draft, suggestion, recommendation
- `amendment` - Revision, modification, update
- `implementation` - Enacted, effective, came into force
- `enforcement` - Penalties, fines, violations
- `review` - Evaluation, assessment, reconsideration

**Evolution Types**:
- `amendment` - Changes to existing provisions
- `expansion` - Scope extensions
- `restriction` - Scope limitations
- `clarification` - Definitional updates
- `enforcement` - Enforcement actions

**Example**:
```json
{
  "policy_name": "KI-Verordnung",
  "evolution_period": 1095,
  "evolution_aspects": ["enforcement", "compliance"]
}
```

---

## Files Modified

### 1. MCP Server (`src/mcp/graph_retrieval/server.py`)

**Changes**:
- Added 5 `Tool` definitions to `list_tools()` (lines 159-281)
- Implemented 5 handler functions (lines 566-1040)
- Added helper functions for temporal analysis (lines 400-563)
- Updated `call_tool()` dispatch (lines 310-340)
- Updated server info endpoint (lines 509-522)

**New Functions**:
```python
# Helper functions
_calculate_temporal_relevance(content, start_year, end_year) -> float
_extract_event_info(content, entity_name) -> dict
_analyze_policy_evolution(content, policy_name) -> dict

# Tool handlers
handle_search_by_date_range(query, start_date, end_date, max_results) -> list[TextContent]
handle_get_entity_history(entity_name, days_back, event_types) -> list[TextContent]
handle_find_concurrent_events(reference_date, window_days, event_context) -> list[TextContent]
handle_compare_timelines(entities, time_period, comparison_focus) -> list[TextContent]
handle_track_policy_evolution(policy_name, evolution_period, evolution_aspects) -> list[TextContent]
```

### 2. Agent Configuration (`src/claude_agent/agent_sdk.py`)

**Changes**:
- Updated `KNOWLEDGE_GRAPH_TOOLS` list (lines 99-112)

```python
KNOWLEDGE_GRAPH_TOOLS = [
    "search_knowledge_graph",
    "search_documents",
    "analyze_query",
    "get_entity_info",
    "find_relationships",
    "graph_statistics",
    # Temporal tools
    "search_by_date_range",
    "get_entity_history",
    "find_concurrent_events",
    "compare_timelines",
    "track_policy_evolution",
]
```

### 3. System Prompt (`src/prompts/sdk_agents/policy_tracker_system.md`)

**Changes**:
- Added "Temporal Analysis Tools" section (tools 19-23, lines 154-185)
- Added temporal best practice #8 (lines 199-205)

### 4. Weekly Report Prompts (`src/flows/weekly_report_sdk/agent/prompts.py`)

**Changes**:
- Updated `KNOWLEDGE_GRAPH_TOOLS` (lines 17-29)
- Added "Temporal Analysis Tools" section (lines 80-86)
- Updated research strategy sections 5 & 6 (lines 128-141)

---

## Files Created

### Unit Tests (`tests/unit/test_temporal_tools.py`)

**22 test cases** covering:

| Test Class | Tests | Coverage |
|------------|-------|----------|
| `TestTemporalToolsDefinitions` | 1 | Tool definitions in MCP |
| `TestTemporalRelevanceCalculation` | 3 | Relevance scoring |
| `TestEventInfoExtraction` | 4 | Event classification |
| `TestPolicyEvolutionAnalysis` | 4 | Evolution phase detection |
| `TestSearchByDateRangeHandler` | 2 | Date range search |
| `TestGetEntityHistoryHandler` | 1 | Entity history |
| `TestFindConcurrentEventsHandler` | 2 | Concurrent events |
| `TestCompareTimelinesHandler` | 2 | Timeline comparison |
| `TestTrackPolicyEvolutionHandler` | 1 | Policy evolution |
| `TestCallToolDispatch` | 2 | Tool dispatch |

**Run tests**:
```bash
python -m pytest tests/unit/test_temporal_tools.py -v
```

---

## Technical Implementation

### Temporal Relevance Scoring

The `_calculate_temporal_relevance()` function scores content based on:

1. **Temporal keywords** (+0.2 each): announced, published, enacted, implemented, released, updated, changed, effective, deadline, commenced

2. **Date patterns** (+0.3):
   - ISO format: `YYYY-MM-DD`
   - US format: `MM/DD/YYYY`
   - Written: `January 15, 2024`

3. **Year mentions** (+0.3): Years within the search range

**Maximum score**: 1.0

### Event Classification

The `_extract_event_info()` function classifies events into types:

```python
event_types = {
    "regulatory": ["regulation", "rule", "compliance", "enforcement", "fine", "penalty"],
    "policy": ["policy", "law", "act", "directive", "legislation", "amendment"],
    "business": ["merger", "acquisition", "partnership", "investment", "funding"],
    "product": ["launch", "release", "announcement", "update", "version"],
    "legal": ["lawsuit", "court", "ruling", "judgment", "settlement", "litigation"],
    "general": ["news", "report", "statement", "comment", "response"],
}
```

### Importance Scoring

Events are scored for importance:

- **High importance** (+0.3): major, significant, important, critical, breakthrough, landmark
- **Medium importance** (+0.2): notable, substantial, considerable, meaningful
- **Temporal markers** (+0.1): announced, released, published, enacted, implemented

**Base score**: 0.3

---

## Usage Examples

### Example 1: Date Range Search

```
User: "What regulatory changes happened in Q4 2024?"

Tool Call: search_by_date_range
Parameters:
  query: "regulatory changes"
  start_date: "2024-10-01"
  end_date: "2024-12-31"
```

### Example 2: Policy Evolution

```
User: "How has the AI Act evolved since its proposal?"

Tool Call: track_policy_evolution
Parameters:
  policy_name: "KI-Verordnung"
  evolution_period: 1095
  evolution_aspects: ["proposal", "amendment", "implementation"]
```

### Example 3: Concurrent Events

```
User: "What else was happening in EU regulation when GDPR enforcement began?"

Tool Call: find_concurrent_events
Parameters:
  reference_date: "2018-05-25"
  window_days: 60
  event_context: "EU regulation data protection"
```

### Example 4: Timeline Comparison

```
User: "Compare how DSA and DMA have developed"

Tool Call: compare_timelines
Parameters:
  entities: ["DSA", "DMA"]
  time_period: 730
  comparison_focus: "implementation"
```

---

## Best Practices

### When to Use Each Tool

| Question Type | Tool |
|---------------|------|
| "What happened between X and Y?" | `search_by_date_range` |
| "How has X changed?" | `get_entity_history` |
| "What else happened around X date?" | `find_concurrent_events` |
| "Compare X and Y development" | `compare_timelines` |
| "How has policy X evolved?" | `track_policy_evolution` |

### German Language Considerations

For German data sources, use German terminology:

| English | German |
|---------|--------|
| AI Act | KI-Verordnung |
| GDPR | DSGVO |
| NIS2 Directive | NIS2-Richtlinie |
| Digital Services Act | DSA |
| Digital Markets Act | DMA |

---

## Verification

### 1. Check Tool Availability

```bash
curl http://localhost:8003/health
curl http://localhost:8003/ | jq '.tools'
```

Expected: 11 tools listed

### 2. Run Unit Tests

```bash
python -m pytest tests/unit/test_temporal_tools.py -v
```

Expected: 22 tests passed

### 3. Integration Test

```python
# Test via Claude Agent
response, session_id, metadata = await agent.query(
    "What regulatory changes happened in 2024?"
)
# Check metadata for temporal tool usage
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Claude Agent SDK                        │
│                   (agent_sdk.py)                            │
│                                                             │
│  KNOWLEDGE_GRAPH_TOOLS = [                                  │
│    "search_knowledge_graph",                                │
│    "search_by_date_range",    ← NEW                         │
│    "get_entity_history",      ← NEW                         │
│    "find_concurrent_events",  ← NEW                         │
│    "compare_timelines",       ← NEW                         │
│    "track_policy_evolution",  ← NEW                         │
│    ...                                                      │
│  ]                                                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Graph Retrieval MCP Server                      │
│                   (port 8003)                               │
│                                                             │
│  list_tools() → 11 tools                                    │
│  call_tool() → dispatches to handlers                       │
│                                                             │
│  Temporal Handlers:                                         │
│  ├── handle_search_by_date_range()                         │
│  ├── handle_get_entity_history()                           │
│  ├── handle_find_concurrent_events()                       │
│  ├── handle_compare_timelines()                            │
│  └── handle_track_policy_evolution()                       │
│                                                             │
│  Helper Functions:                                          │
│  ├── _calculate_temporal_relevance()                       │
│  ├── _extract_event_info()                                 │
│  └── _analyze_policy_evolution()                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  Neo4j Knowledge Graph                       │
│              (politicalmonitoring.v3)                       │
│                                                             │
│  Entities with temporal properties:                         │
│  - valid_at                                                 │
│  - created_at                                               │
│  - updated_at                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Related Files

| File | Purpose |
|------|---------|
| `src/mcp/graph_retrieval/server.py` | MCP server with temporal tools |
| `src/mcp/graph_retrieval/retriever.py` | Underlying retriever with temporal intent detection |
| `src/chat/tools/temporal.py` | Original LangChain temporal tools (reference) |
| `src/claude_agent/agent_sdk.py` | Agent configuration |
| `src/prompts/sdk_agents/policy_tracker_system.md` | System prompt |
| `src/flows/weekly_report_sdk/agent/prompts.py` | Weekly report configuration |
| `tests/unit/test_temporal_tools.py` | Unit tests |

---

## Changelog

### v1.0.0 (January 2025)

- Added 5 temporal tools to Graph Retrieval MCP Server
- Implemented temporal relevance scoring
- Added event classification and importance scoring
- Added policy evolution phase detection
- Updated Claude Agent SDK tool configuration
- Updated system prompts with temporal tool guidance
- Added 22 unit tests
