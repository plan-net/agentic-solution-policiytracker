# Temporal Filtering in Graphiti Search

This document describes the temporal filtering implementation for the Weekly Digest search functionality, which enables precise date-based filtering of knowledge graph results.

## Overview

The temporal filtering system allows searches to be filtered by date ranges using Graphiti's native `SearchFilters` API. This ensures that weekly digest reports only include information relevant to the specified time period, rather than relying on LLM-based date extraction (which was unreliable).

## Problem Statement

Previously, the weekly digest search had several limitations:

1. **Year-only filtering**: Only the year was appended to queries (e.g., "DSA regulation 2025")
2. **No week-level precision**: `week_start` and `week_end` dates were not used in Graphiti search
3. **Unreliable LLM filtering**: Date filtering was deferred to LLM extraction, which was inconsistent
4. **Missing data**: Sparse data or data with different terminology could be missed

## Solution Architecture

### Graphiti's Temporal Model

Graphiti tracks four temporal fields on edges (relationships/facts):

| Field | Meaning | Use Case |
|-------|---------|----------|
| `valid_at` | When the fact became true in the real world | "What started" |
| `invalid_at` | When the fact stopped being true | "What ended/changed" |
| `created_at` | When the fact was ingested into the graph | "New information added" |
| `expired_at` | When the fact was marked expired in the graph | "What was superseded" |

### Temporal Filter Strategies

Four configurable strategies are available for different use cases:

| Strategy | Fields Used | Best For |
|----------|-------------|----------|
| `comprehensive` | All 4 fields (OR logic) | Weekly digest - maximize results for sparse data |
| `valid_only` | `valid_at` only | Point-in-time reports - "what was true then" |
| `created_only` | `created_at` only | New information reports - "what's new in the graph" |
| `changes` | `valid_at` + `invalid_at` | Change tracking - "what changed during the period" |

### OR Logic Implementation

Graphiti's `SearchFilters` uses AND logic between different temporal fields. To achieve OR logic (capture everything that "touched" the date range), the implementation runs separate searches for each temporal field and merges/deduplicates the results.

## Implementation Details

### Files Modified

| File | Changes |
|------|---------|
| `src/chat/tools/search.py` | Added `TemporalFilterStrategy` enum, `STRATEGY_FIELDS` mapping, `_search_with_temporal_filter()` method, updated `_arun()` with date parameters |
| `src/chat/tools/__init__.py` | Exported `TemporalFilterStrategy` and `STRATEGY_FIELDS` |
| `src/core/config/category_config.py` | Added `temporal_filter_strategy` field |
| `src/flows/weekly_digest_v2/agents/base.py` | Added `temporal_filter_strategy` to `ResearchPlanEntry` TypedDict |
| `src/flows/weekly_digest_v2/agents/research_planner.py` | Include category's temporal strategy in plan entry |
| `src/flows/weekly_digest_v2/agents/tool_executor.py` | Pass `week_start`, `week_end`, and strategy to search tool |
| `src/flows/weekly_digest_v2/config/categories/general.yaml` | New catch-all category with `created_only` strategy |
| `src/flows/weekly_digest_v2/config/weekly_digest.yaml` | Added `general.yaml` to categories list |

### Key Classes and Functions

#### `TemporalFilterStrategy` Enum

```python
from src.chat.tools import TemporalFilterStrategy

class TemporalFilterStrategy(str, Enum):
    COMPREHENSIVE = "comprehensive"  # All 4 fields (OR) - maximize results
    VALID_ONLY = "valid_only"        # Only valid_at - point-in-time truth
    CREATED_ONLY = "created_only"    # Only created_at - new information
    CHANGES = "changes"              # valid_at + invalid_at - what changed
```

#### `STRATEGY_FIELDS` Mapping

```python
from src.chat.tools import STRATEGY_FIELDS

STRATEGY_FIELDS = {
    TemporalFilterStrategy.COMPREHENSIVE: ['valid_at', 'invalid_at', 'created_at', 'expired_at'],
    TemporalFilterStrategy.VALID_ONLY: ['valid_at'],
    TemporalFilterStrategy.CREATED_ONLY: ['created_at'],
    TemporalFilterStrategy.CHANGES: ['valid_at', 'invalid_at'],
}
```

#### Updated `_arun()` Method

```python
async def _arun(
    self,
    query: str,
    limit: int = 5,
    search_type: str = "comprehensive",
    output_format: str = "structured",
    date_filter_start: Optional[datetime] = None,  # NEW
    date_filter_end: Optional[datetime] = None,    # NEW
    temporal_filter_strategy: str = "comprehensive",  # NEW
    run_manager: Optional[CallbackManagerForToolRun] = None,
) -> Union[str, dict]:
```

#### `_search_with_temporal_filter()` Method

```python
async def _search_with_temporal_filter(
    self,
    query: str,
    start_date: datetime,
    end_date: datetime,
    config,
    strategy: TemporalFilterStrategy = TemporalFilterStrategy.COMPREHENSIVE,
) -> tuple[list, list]:
    """
    Run searches across temporal fields based on strategy and merge results.

    Returns:
        Tuple of (edges, nodes) - deduplicated lists of results
    """
```

## Usage

### Category Configuration

Each category can specify its own temporal filter strategy in its YAML configuration:

```yaml
# In any category YAML file (e.g., legislative.yaml)
name: legislative
display_name: "Legislative & Regulatory Updates"
search_type: comprehensive

# Optional: defaults to "comprehensive" if not specified
temporal_filter_strategy: comprehensive

search_queries:
  - "new regulation law enacted"
  - "DSA DMA Digital Services Act"
```

### General Category (Catch-All)

A special `general.yaml` category is configured with `created_only` strategy to capture ALL new data added during the week:

```yaml
name: general
display_name: "Other Regulatory Developments"
priority: 10  # Runs last

# CRITICAL: Use created_only to get ALL new data in the week
temporal_filter_strategy: created_only

search_queries:
  - "regulatory development"
  - "policy update"
  - "government announcement"
```

### Direct Search Tool Usage

When using the search tool directly:

```python
from datetime import datetime
from src.chat.tools import GraphitiSearchTool

search_tool = GraphitiSearchTool(graphiti_client=client)

# Search with temporal filtering
result = await search_tool._arun(
    query="DSA regulation",
    limit=20,
    search_type="comprehensive",
    output_format="structured",
    date_filter_start=datetime(2025, 11, 24),
    date_filter_end=datetime(2025, 11, 30),
    temporal_filter_strategy="comprehensive",
)
```

## Behavior Comparison

### Before (Year-Only Filtering)

```
User requests: KW48/2025 (Nov 24 - Nov 30, 2025)

- Query: "DSA regulation 2025" (year appended as text)
- Results: ALL facts mentioning DSA from any time in 2025
- LLM tries to filter by week (unreliable)
- May miss sparse data or data with different terminology
```

### After (Native Temporal Filtering)

```
User requests: KW48/2025 (Nov 24 - Nov 30, 2025)

- Query: "DSA regulation" (no year appending needed)
- Runs 4 searches with Graphiti's native filters:
  1. valid_at >= Nov 24 AND valid_at <= Nov 30
  2. invalid_at >= Nov 24 AND invalid_at <= Nov 30
  3. created_at >= Nov 24 AND created_at <= Nov 30
  4. expired_at >= Nov 24 AND expired_at <= Nov 30
- Merges and deduplicates results
- Returns: ALL facts that "touched" the week in any way
- General category catches anything missed by specific queries
```

## Weekly Digest Workflow

The complete workflow for a weekly digest:

1. **Legislative** category runs with `comprehensive` strategy
   - Searches: DSA, DMA, GDPR queries
   - Temporal filter: All 4 fields (valid_at, invalid_at, created_at, expired_at)
   - Results: All legislative activity that touched this week

2. **Personnel** category runs with `comprehensive` strategy

3. **Compliance** category runs with `comprehensive` strategy

4. **Policy** category runs with `comprehensive` strategy

5. **Events** category runs with `comprehensive` strategy

6. **General** category runs with `created_only` strategy (LAST)
   - Searches: Generic "regulatory development", "policy update" queries
   - Temporal filter: ONLY created_at field
   - Results: ALL new data ingested this week, regardless of topic
   - Catches anything missed by specific categories
   - Appears as "Other Regulatory Developments" section in report

## Logging

The temporal filtering implementation includes detailed logging:

```
INFO: Searching knowledge graph for: DSA regulation (type: comprehensive, format: structured)
INFO: Applying temporal filter: 2025-11-24 to 2025-11-30 (strategy: comprehensive)
INFO: Temporal search strategy: comprehensive, fields: ['valid_at', 'invalid_at', 'created_at', 'expired_at'], date range: 2025-11-24 to 2025-11-30
DEBUG: Searching with valid_at filter...
DEBUG:   valid_at: found 5 edges, 3 nodes
DEBUG: Searching with invalid_at filter...
DEBUG:   invalid_at: found 0 edges, 0 nodes
DEBUG: Searching with created_at filter...
DEBUG:   created_at: found 8 edges, 4 nodes
DEBUG: Searching with expired_at filter...
DEBUG:   expired_at: found 1 edges, 0 nodes
INFO: Temporal search complete: 12 unique edges, 6 unique nodes across 4 fields
```

## Configurable LLM Extraction

### Overview

By default, after retrieving search results from Graphiti, the system uses an LLM to extract and filter findings. This can be disabled per-category to:
- Improve performance (skip LLM API calls)
- Reduce costs
- Preserve raw results when temporal filtering already ensures relevance

### Configuration

Each category can specify whether to skip LLM extraction:

```yaml
# In any category YAML file
name: general
display_name: "Other Regulatory Developments"

# Skip LLM extraction - use raw results directly
skip_llm_extraction: true
```

### Behavior Comparison

| Setting | Processing | Best For |
|---------|------------|----------|
| `skip_llm_extraction: false` (default) | Raw results → LLM extraction → Structured findings | Categories needing intelligent filtering/summarization |
| `skip_llm_extraction: true` | Raw results → Direct conversion → Findings | Categories with strict temporal filtering, performance-critical |

### Example: General Category

The `general.yaml` category uses `skip_llm_extraction: true` because:
1. It uses `created_only` temporal strategy, which already ensures relevance
2. It's a catch-all category - we want ALL new data, not LLM-filtered data
3. Improves overall workflow performance

```yaml
name: general
display_name: "Other Regulatory Developments"
temporal_filter_strategy: created_only
skip_llm_extraction: true  # Temporal filtering ensures relevance
```

### Files Modified for LLM Extraction Control

| File | Changes |
|------|---------|
| `src/core/config/category_config.py` | Added `skip_llm_extraction` field |
| `src/flows/weekly_digest_v2/agents/base.py` | Added `skip_llm_extraction` to `ResearchPlanEntry` |
| `src/flows/weekly_digest_v2/agents/research_planner.py` | Pass `skip_llm_extraction` in plan entry |
| `src/flows/weekly_digest_v2/agents/tool_executor.py` | Added `_create_findings_from_raw()`, conditional LLM skip |
| `src/flows/weekly_digest_v2/config/categories/general.yaml` | Set `skip_llm_extraction: true` |

## Configuration Reference

### CategoryConfig Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `temporal_filter_strategy` | `str` | `"comprehensive"` | Strategy for temporal filtering |
| `skip_llm_extraction` | `bool` | `true` | If true, skip LLM-based extraction and use raw results |

Valid temporal strategy values: `"comprehensive"`, `"valid_only"`, `"created_only"`, `"changes"`

### SearchInput Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `date_filter_start` | `Optional[datetime]` | `None` | Start date for filtering (inclusive) |
| `date_filter_end` | `Optional[datetime]` | `None` | End date for filtering (inclusive) |
| `temporal_filter_strategy` | `str` | `"comprehensive"` | Which strategy to use |

## Future Enhancements

Potential future improvements:

1. **Tool Plan Configuration**: Allow strategy to be specified per tool in `comprehensive.yaml`
2. **Direct Cypher Query**: Add a method to fetch ALL data in a date range without semantic search
3. **Custom Field Selection**: Allow explicit field list instead of predefined strategies
4. **Performance Optimization**: Run temporal field searches in parallel instead of sequentially
