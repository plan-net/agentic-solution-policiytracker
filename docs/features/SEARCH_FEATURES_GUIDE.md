# How to See Search Tool Features

The updated search tool has 3 new features that you can access in different ways:

## 1. 🎯 Relevance Scoring

**Where to see it**: Default text output format

**How to access**:
```python
# Via Chat Interface (Open WebUI at http://localhost:3000)
# Just ask a natural language question:
"What regulatory changes affect Google?"

# The search tool will automatically show relevance scores:
# Found 5 facts for 'Google regulatory changes':
# 1. [Score: 0.429] Google faces DMA compliance requirements...
# 2. [Score: 0.286] EU opens investigation into Google's practices...
# 3. [Score: 0.143] Tech companies including Google must comply...
```

**What you'll see**:
- Each result has a `[Score: X.XXX]` prefix
- Scores range from 0.0 to 1.0
- Higher scores = more query terms matched
- Example: `[Score: 0.429]` means 42.9% of query terms found

---

## 2. 📰 Source Extraction

**Where to see it**: Default text output format (at the bottom)

**How to access**:
```python
# Same as above - ask any question via Open WebUI
"Tell me about EU AI Act enforcement"

# At the bottom of results, you'll see:
# **Sources:**
# - europa.eu: commission adopts ai act implementation guidelines: https://europa.eu
# - politico.eu: brussels prepares ai act enforcement: https://politico.eu
# - techcrunch.com: eu ai act takes effect what companies need: https://techcrunch.com
```

**What you'll see**:
- List of unique sources at the bottom
- Format: `domain: title: URL`
- Extracted from Episodic node filenames
- Only shows sources for results with episode links

---

## 3. 📊 Structured Output (Graph Visualization Data)

**Where to see it**: JSON format with complete graph data

**How to access via Python**:
```python
import asyncio
from graphiti_core import Graphiti
from src.chat.tools.search import GraphitiSearchTool

async def test_structured_output():
    # Initialize
    client = Graphiti("bolt://localhost:7687", "neo4j", "password123")
    tool = GraphitiSearchTool(graphiti_client=client)

    # Search with structured output
    result = await tool._arun(
        query="Google regulatory exposure DMA DSA AI Act",
        limit=5,
        search_type="comprehensive",
        output_format="structured"  # ← KEY PARAMETER!
    )

    print(result)

asyncio.run(test_structured_output())
```

**How to access via Chat Agent**:
The search tool is called automatically by the multi-agent system. To get structured output, you would need to modify the tool call in the agent to use `output_format="structured"`.

**What you'll see**:
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
      "relevance_score": 0.286,  // ← RELEVANCE SCORE
      "source": {  // ← SOURCE INFO
        "url": "https://securityaffairs.com",
        "title": "securityaffairs.com: meta plans to train ai on eu user data from may 27",
        "date": "20250516"
      },
      "uuid": "abc-123-def"
    }
  ],
  "graph_data": {  // ← GRAPH VISUALIZATION DATA
    "nodes": [
      {
        "uuid": "8528013e-2ee5-4641-9204-fb2854c7bce2",
        "name": "Meta Platforms",  // ← ENRICHED NAME (not "Unknown")
        "type": "Entity, Company"  // ← ENRICHED TYPE
      },
      {
        "uuid": "2274cb13-a6c9-44f5-b018-607e2ef80968",
        "name": "General Data Protection Regulation",
        "type": "Entity, LegalFramework"
      }
    ],
    "edges": [
      {
        "source_uuid": "8528013e-2ee5-4641-9204-fb2854c7bce2",
        "target_uuid": "2274cb13-a6c9-44f5-b018-607e2ef80968",
        "relationship_type": "VIOLATES",
        "fact": "Meta's AI training practices likely breach GDPR..."
      }
    ]
  },
  "sources": [  // ← AGGREGATED SOURCES
    {
      "title": "securityaffairs.com: meta plans to train ai on eu user data from may 27",
      "url": "https://securityaffairs.com",
      "count": 2
    },
    {
      "title": "breached.company: brussels tech crackdown inside the eus expanding w",
      "url": "https://breached.company",
      "count": 1
    }
  ]
}
```

---

## 📍 Where to Test Each Feature

### Option 1: Open WebUI (Easiest) 🌐
**URL**: http://localhost:3000

1. Open the chat interface
2. Ask any question about policies, regulations, companies
3. The search tool is called automatically by the agent
4. You'll see:
   - ✅ Relevance scores in the thinking process
   - ✅ Sources at the bottom of results
   - ❌ Structured output (not exposed in UI)

**Example Questions**:
- "What regulatory changes affect Google?"
- "Tell me about EU AI Act enforcement"
- "What are the DMA compliance requirements?"
- "Show me Meta's regulatory issues"

---

### Option 2: Direct Python Testing 🐍
**File**: Create `test_search_features.py`

```python
import asyncio
from graphiti_core import Graphiti
from src.chat.tools.search import GraphitiSearchTool

async def test_all_features():
    # Initialize
    client = Graphiti("bolt://localhost:7687", "neo4j", "password123")
    tool = GraphitiSearchTool(graphiti_client=client)

    print("=" * 80)
    print("TEST 1: Text Output (Relevance + Sources)")
    print("=" * 80)

    text_result = await tool._arun(
        query="Google regulatory exposure DMA DSA AI Act",
        limit=5,
        search_type="comprehensive",
        output_format="text"  # Default
    )
    print(text_result)

    print("\n" + "=" * 80)
    print("TEST 2: Structured Output (Graph Data)")
    print("=" * 80)

    structured_result = await tool._arun(
        query="Google regulatory exposure DMA DSA AI Act",
        limit=5,
        search_type="comprehensive",
        output_format="structured"  # JSON format
    )

    import json
    print(json.dumps(structured_result, indent=2))

    # Close client
    await client.close()

if __name__ == "__main__":
    asyncio.run(test_all_features())
```

**Run it**:
```bash
source .venv/bin/activate
python test_search_features.py
```

---

### Option 3: Ray Serve Direct Call 🚀
**URL**: http://localhost:8001/v1/chat/completions

```bash
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "political-monitoring-agent",
    "messages": [
      {"role": "user", "content": "What regulatory changes affect Google?"}
    ],
    "stream": false
  }'
```

This will show the agent's response with the search tool results embedded.

---

## 🔍 Feature Comparison

| Feature | Text Output | Structured Output |
|---------|-------------|-------------------|
| **Relevance Scores** | ✅ `[Score: 0.429]` | ✅ `"relevance_score": 0.429` |
| **Source Extraction** | ✅ Listed at bottom | ✅ Per-result + aggregated |
| **Node Enrichment** | ❌ Not shown | ✅ Full node names/types |
| **Graph Data** | ❌ Not shown | ✅ Nodes + edges for viz |
| **Use Case** | Human-readable chat | Graph visualization, analytics |

---

## 📝 Summary

1. **For quick testing**: Use Open WebUI at http://localhost:3000
   - Ask any question
   - See relevance scores and sources automatically

2. **For detailed inspection**: Create Python test script
   - Use `output_format="text"` for scores + sources
   - Use `output_format="structured"` for complete graph data

3. **For integration**: Call via Ray Serve API
   - Chat endpoint calls search tool automatically
   - Results include all features in agent response

The easiest way to see everything is to use Open WebUI and ask questions! The agent will automatically call the search tool and display the results with relevance scores and sources. 🎉
