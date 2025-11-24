# Search Tool JSON Output Fix

**Date**: 2025-11-19
**Status**: ✅ Fixed and Deployed

## Problem

The search tool was returning data, but the agent wrapper showed empty fields:

```json
{
  "tool_name": "search",
  "success": true,
  "raw_output": "Found 20 facts...",  // ← Had markdown text
  "entities_found": [],  // ← EMPTY!
  "relationships_discovered": [],  // ← EMPTY!
  "source_citations": [],  // ← EMPTY!
}
```

## Root Cause

### Issue 1: Wrong Default Output Format
- **Problem**: Search tool defaulted to `output_format="text"` (markdown)
- **Impact**: Agent's extraction methods expected structured dict, got string instead
- **Location**: `src/chat/tools/search.py` line 71

### Issue 2: Wrong Key Paths in Extraction Methods
- **Problem**: Extraction methods looked for `result["nodes"]` at top level
- **Reality**: Structured output has `result["graph_data"]["nodes"]`
- **Location**: `src/chat/agent/tool_integration.py` lines 423-520

## Solution

### Fix 1: Changed Default Output Format to "structured"

**File**: `src/chat/tools/search.py`

```python
# BEFORE
output_format: str = Field(
    default="text",  # ← Returned markdown string
    description="Output format: 'text' (markdown) or 'structured' (JSON with graph data)",
)

# AFTER
output_format: str = Field(
    default="structured",  # ← Returns dict with graph data
    description="Output format: 'structured' (JSON with graph data) or 'text' (markdown)",
)
```

**Also updated** method signature default:
```python
async def _arun(
    self,
    query: str,
    limit: int = 5,
    search_type: str = "comprehensive",
    output_format: str = "structured",  # ← Changed from "text"
    run_manager: Optional[CallbackManagerForToolRun] = None,
) -> Union[str, dict]:
```

### Fix 2: Updated Extraction Methods to Handle Nested Structure

**File**: `src/chat/agent/tool_integration.py`

#### Entity Extraction (lines 423-451)
```python
def _extract_entities_from_result(self, result: Any) -> list[dict[str, str]]:
    """Extract entities from tool result."""
    entities = []

    if isinstance(result, dict):
        # NEW: Check for nodes in graph_data (structured search output)
        if "graph_data" in result and "nodes" in result["graph_data"]:
            for node in result["graph_data"]["nodes"][:10]:
                if isinstance(node, dict):
                    entities.append({
                        "name": node.get("name", "Unknown"),
                        "type": node.get("type", "Entity"),
                        "relevance": "high",
                    })
        # Fallback: Check for nodes at top level (other tools)
        elif "nodes" in result:
            for node in result["nodes"][:10]:
                # ... existing logic
```

#### Relationship Extraction (lines 453-496)
```python
def _extract_relationships_from_result(self, result: Any) -> list[dict[str, str]]:
    """Extract relationships from tool result."""
    relationships = []

    if isinstance(result, dict):
        # NEW: Check for edges in graph_data
        if "graph_data" in result and "edges" in result["graph_data"]:
            for edge in result["graph_data"]["edges"][:10]:
                if isinstance(edge, dict):
                    # NEW: Resolve source/target names from UUIDs
                    source_name = edge.get("source", "Unknown")
                    target_name = edge.get("target", "Unknown")

                    if "graph_data" in result and "nodes" in result["graph_data"]:
                        nodes_by_uuid = {
                            n.get("uuid"): n
                            for n in result["graph_data"]["nodes"]
                            if isinstance(n, dict)
                        }
                        source_uuid = edge.get("source_uuid")
                        target_uuid = edge.get("target_uuid")

                        if source_uuid and source_uuid in nodes_by_uuid:
                            source_name = nodes_by_uuid[source_uuid].get("name", source_name)
                        if target_uuid and target_uuid in nodes_by_uuid:
                            target_name = nodes_by_uuid[target_uuid].get("name", target_name)

                    relationships.append({
                        "source": source_name,
                        "target": target_name,
                        "relationship": edge.get("relationship_type", "RELATED_TO"),
                    })
        # Fallback: Check for edges at top level (other tools)
        elif "edges" in result:
            # ... existing logic
```

#### Source Extraction (lines 498-520)
```python
def _extract_sources_from_result(self, result: Any) -> list[str]:
    """Extract source citations from tool result."""
    sources = []

    if isinstance(result, dict):
        # NEW: Check for sources in structured search output
        if "sources" in result:
            for source in result["sources"]:
                if isinstance(source, dict):
                    # Format: "title: url"
                    title = source.get("title", "Unknown")
                    url = source.get("url", "")
                    sources.append(f"{title}: {url}" if url else title)
                else:
                    sources.append(str(source))
        elif "episodes" in result:
            # ... existing logic
```

## Structured Output Format

The search tool now returns this structure by default:

```json
{
  "query": "Google regulatory exposure DMA DSA AI Act",
  "search_type": "comprehensive",
  "total_results": 18,
  "returned_results": 5,
  "results": [
    {
      "rank": 1,
      "content": "Meta's AI training practices likely breach GDPR...",
      "type": "relationship",
      "name": "VIOLATES",
      "relevance_score": 0.286,
      "source": {
        "url": "https://securityaffairs.com",
        "title": "securityaffairs.com: meta plans to train ai...",
        "date": "20250516"
      },
      "uuid": "abc-123-def"
    }
  ],
  "graph_data": {  // ← Key path: graph_data.nodes, not just nodes
    "nodes": [
      {
        "uuid": "8528013e-2ee5-4641-9204-fb2854c7bce2",
        "name": "Meta Platforms",  // ← Enriched name
        "type": "Entity, Company"  // ← Enriched type
      }
    ],
    "edges": [
      {
        "uuid": "...",
        "source_uuid": "8528013e-2ee5-4641-9204-fb2854c7bce2",
        "target_uuid": "2274cb13-a6c9-44f5-b018-607e2ef80968",
        "relationship_type": "VIOLATES",
        "fact": "Meta's AI training practices..."
      }
    ]
  },
  "sources": [  // ← Top-level sources array
    {
      "title": "securityaffairs.com: meta plans to train ai...",
      "url": "https://securityaffairs.com",
      "count": 2
    }
  ]
}
```

## Expected Result After Fix

Now when you search via the agent, you should see:

```json
{
  "tool_name": "search",
  "success": true,
  "execution_time": 2.8,
  "raw_output": {
    "query": "regulatory changes affecting Google",
    "total_results": 20,
    "results": [...],
    "graph_data": {...},
    "sources": [...]
  },
  "entities_found": [  // ← NOW POPULATED!
    {
      "name": "Meta Platforms",
      "type": "Entity, Company",
      "relevance": "high"
    },
    {
      "name": "General Data Protection Regulation",
      "type": "Entity, LegalFramework",
      "relevance": "high"
    }
  ],
  "relationships_discovered": [  // ← NOW POPULATED!
    {
      "source": "Meta Platforms",
      "target": "General Data Protection Regulation",
      "relationship": "VIOLATES"
    }
  ],
  "source_citations": [  // ← NOW POPULATED!
    "securityaffairs.com: meta plans to train ai...: https://securityaffairs.com",
    "breached.company: brussels tech crackdown...: https://breached.company"
  ]
}
```

## Testing

To test the fix:

1. **Via Open WebUI** (http://localhost:3000):
   - Ask: "What regulatory changes affect Google?"
   - The agent will now see populated entities, relationships, and sources

2. **Via Python**:
```python
import asyncio
from graphiti_core import Graphiti
from src.chat.tools.search import GraphitiSearchTool

async def test():
    client = Graphiti("bolt://localhost:7687", "neo4j", "password123")
    tool = GraphitiSearchTool(graphiti_client=client)

    # Structured output (default now)
    result = await tool._arun(
        query="Google regulatory exposure",
        limit=5
    )

    print(f"Entities: {len(result['graph_data']['nodes'])}")
    print(f"Relationships: {len(result['graph_data']['edges'])}")
    print(f"Sources: {len(result['sources'])}")

    await client.close()

asyncio.run(test())
```

## Deployment

✅ **Deployed**: 2025-11-19 13:03:43

All Ray Serve applications redeployed with the fix:
- chat-server: HEALTHY
- flow5b-bundestag-vorgang: HEALTHY
- flow5f-bundestag-aktivitaet: HEALTHY

## Benefits

1. ✅ **Entities**: Agent now sees extracted entities with names and types
2. ✅ **Relationships**: Agent now sees connections between entities
3. ✅ **Sources**: Agent now sees where information came from
4. ✅ **Backward Compatible**: Other tools that return top-level "nodes"/"edges" still work

## Files Changed

1. `src/chat/tools/search.py`:
   - Changed default output format from "text" to "structured"
   - Updated Field description (lines 32-35)
   - Updated method signature (line 71)

2. `src/chat/agent/tool_integration.py`:
   - Updated `_extract_entities_from_result()` (lines 423-451)
   - Updated `_extract_relationships_from_result()` (lines 453-496)
   - Updated `_extract_sources_from_result()` (lines 498-520)

---

**Status**: ✅ **Production Ready**

The search tool now properly exposes all the improvements (relevance scores, source extraction, node enrichment) to the multi-agent system! 🎉
