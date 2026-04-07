# Dual Language Search - Quick Reference

**For**: Developers integrating multilingual search
**See Also**: [Full Documentation](./dual-language-search.md)

## TL;DR

Queries are automatically searched in both German and English, with results merged and deduplicated by UUID.

## Quick Start

### Basic Usage

```python
from src.mcp.graph_retrieval.retriever import GraphContextRetriever

# Initialize (multilingual enabled by default)
retriever = GraphContextRetriever()

# Query in any language
context = await retriever.retrieve("What is the Digital Services Act?")
# OR
context = await retriever.retrieve("Was ist das Digitale-Dienste-Gesetz?")

# Both return merged results from EN + DE searches
print(f"Found {len(context.entities)} entities")
```

### Disable Multilingual Search

```python
from src.mcp.graph_retrieval.retriever import MCPExecutor, Neo4jConfig

executor = MCPExecutor(Neo4jConfig())
await executor.initialize()

# Single-language search only
results = await executor._search({
    "query": "GDPR compliance",
    "limit": 10,
    "multilingual": False  # Disable dual-language
})
```

## How It Works (30 Second Version)

1. **Detect**: Is query German or English? (stopword matching)
2. **Translate**: Claude Haiku translates to opposite language
3. **Search**: Run both searches in parallel (original + translated)
4. **Merge**: Deduplicate by UUID, keep highest scores
5. **Return**: Combined results sorted by relevance

## Common Use Cases

### Use Case 1: EU Regulation Search

```python
# User queries in German
results = await retriever.retrieve("DSGVO Compliance Anforderungen")

# Internally searches:
# • German: "DSGVO Compliance Anforderungen"
# • English: "GDPR compliance requirements"
# Returns merged results from both
```

### Use Case 2: Bundestag Document Search

```python
# User queries in English
results = await retriever.retrieve("Bundestag AI Act debate")

# Internally searches:
# • English: "Bundestag AI Act debate"
# • German: "Bundestag KI-Gesetz Debatte"
# Returns merged results from both
```

### Use Case 3: Mixed-Language Entity

```python
# Query mentions both EN and DE terms
results = await retriever.retrieve("How does DSGVO relate to data protection?")

# Language detection: English (more EN stopwords)
# Translates to German, searches both
# Finds entities with either GDPR or DSGVO names
```

## Configuration Cheat Sheet

### Global On/Off

```python
# In src/config.py or environment
ENABLE_MULTILINGUAL_SEARCH = True   # Default: on
ENABLE_MULTILINGUAL_SEARCH = False  # Turn off globally
```

### Per-Query Override

```python
# Override global setting for specific query
params = {
    "query": "Your query here",
    "limit": 10,
    "multilingual": True   # or False
}
results = await executor._search(params)
```

## Performance Quick Facts

| Metric | Value |
|--------|-------|
| Translation Time | 200-500ms |
| Total Overhead | ~500ms average |
| Cost per Query | ~$0.0003 |
| Queries per $1 | ~3,000 |

## Troubleshooting Quick Fixes

### Query Not Translated

**Problem**: Only searching in one language

**Quick Check**:
```bash
grep "Translated query" logs/retriever.log | tail -5
```

**Quick Fix**: Check if Claude API is accessible via APISIX

---

### High Latency

**Problem**: Queries taking >2 seconds

**Quick Check**:
```bash
grep "Translation.*ms" logs/retriever.log | tail -10
```

**Quick Fix**: Disable multilingual for time-sensitive queries:
```python
results = await search(query="...", multilingual=False)
```

---

### Wrong Language Detected

**Problem**: English query detected as German (or vice versa)

**Cause**: Query has few stopwords, heuristic guesses wrong

**Quick Fix**: Detection is not critical - both languages searched anyway. If it's consistently wrong, add domain stopwords.

---

### Duplicate Results

**Problem**: Same entity appears twice

**Cause**: Different UUIDs for same entity (not a bug)

**Check**:
```cypher
MATCH (e:Entity)
WHERE e.name IN ['GDPR', 'DSGVO']
RETURN e.uuid, e.name
```

**Fix**: If UUIDs differ, entities are distinct. If same UUID, merging should work.

## Code Snippets

### Check if Multilingual is Enabled

```python
from src.config import graphrag_settings

if graphrag_settings.ENABLE_MULTILINGUAL_SEARCH:
    print("Multilingual search is enabled")
else:
    print("Single-language search only")
```

### Monitor Translation Success

```python
import logging
logger = logging.getLogger("src.mcp.graph_retrieval.retriever")

# Translation logs at INFO level
# Look for: "Translated query [de→en]: '...' → '...'"
```

### Test Translation Directly

```python
from src.mcp.graph_retrieval.retriever import MCPExecutor, Neo4jConfig

executor = MCPExecutor(Neo4jConfig())

# Test translation
translated = await executor._translate_query(
    query="Was ist die DSGVO?",
    source_lang="de"
)
print(f"Translated: {translated}")
# Expected: "What is the GDPR?"
```

### Test Language Detection

```python
executor = MCPExecutor(Neo4jConfig())

# Detect language
lang = executor._detect_language("Was ist die DSGVO?")
print(f"Detected: {lang}")  # Expected: 'de'

lang = executor._detect_language("What is the GDPR?")
print(f"Detected: {lang}")  # Expected: 'en'
```

## Logging Patterns

### Search for Multilingual Activity

```bash
# See all multilingual searches
grep "Multilingual search enabled" logs/retriever.log

# See all translations
grep "Translated query" logs/retriever.log

# See merge results
grep "Merged multilingual results" logs/retriever.log

# Count by language
grep "Detected language: de" logs/retriever.log | wc -l
grep "Detected language: en" logs/retriever.log | wc -l
```

### Filter by Date

```bash
# Today's multilingual searches
grep "$(date +%Y-%m-%d)" logs/retriever.log | grep "Multilingual"

# Last hour's translations
grep "$(date +%Y-%m-%d\ %H):" logs/retriever.log | grep "Translated"
```

## Entity Preservation Examples

These entities are preserved during translation:

| Original (EN) | Preserved (DE) | Original (DE) | Preserved (EN) |
|--------------|----------------|--------------|----------------|
| GDPR | GDPR ✅ | DSGVO | DSGVO ✅ |
| DSA | DSA ✅ | KI-Gesetz | KI-Gesetz ✅ |
| AI Act | AI Act ✅ | Bundestag | Bundestag ✅ |
| European Commission | European Commission ✅ | Europäische Kommission | Europäische Kommission ✅ |

**Translation Prompt** ensures acronyms and entity names are preserved across languages.

## Integration Points

### With Claude Agent

```python
# Claude agent automatically uses multilingual search via MCP
from src.claude_agent.agent import PolicyTrackerAgent

agent = PolicyTrackerAgent()

# User query in any language
response = await agent.query("Was sind DSGVO Anforderungen?")

# Agent receives merged EN + DE results
# Synthesizes answer using both sources
```

### With MCP Server

```python
# MCP server exposes search_knowledge_graph tool
# Multilingual search enabled by default

await mcp_client.call_tool("search_knowledge_graph", {
    "query": "Digital Services Act enforcement",
    # multilingual=True (default, not needed)
})
```

## Best Practices

### ✅ DO

- Let multilingual search run by default (best user experience)
- Monitor translation logs for quality issues
- Use meaningful entity names that translate well
- Preserve acronyms in your knowledge graph

### ❌ DON'T

- Disable multilingual search unless you have a specific reason
- Rely on language detection being 100% accurate (it's a heuristic)
- Expect identical results across languages (ranking may differ slightly)
- Forget to check merge statistics for deduplication effectiveness

## Key Files

| File | Purpose |
|------|---------|
| `src/mcp/graph_retrieval/retriever.py` | Main implementation (lines 452-665) |
| `src/config.py` | Global configuration |
| `tests/unit/mcp/test_multilingual_search.py` | Unit tests (if exists) |
| `docs/features/multilingual/dual-language-search.md` | Full documentation |

## When to Disable

Consider disabling multilingual search when:

1. **Latency Critical**: Real-time applications where 500ms matters
2. **Cost Sensitive**: Very high query volume on tight budget
3. **Single Language Content**: Graph only has one language
4. **Testing**: Isolating search behavior for debugging

## Resources

- **Full Docs**: [dual-language-search.md](./dual-language-search.md)
- **Architecture**: See "Architecture" section in full docs
- **Troubleshooting**: See "Troubleshooting" section in full docs
- **Performance**: See "Performance Characteristics" section in full docs

---

**Version**: 1.0
**Last Updated**: 2025-01-13
**Quick Reference For**: Developers, DevOps, QA
