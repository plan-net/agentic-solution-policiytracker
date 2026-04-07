# Multilingual Features

This directory contains documentation for multilingual capabilities in the Political Monitoring Agent.

## Available Features

### 1. Dual Language Search

**Status**: ✅ Production
**File**: [dual-language-search.md](./dual-language-search.md)

Automatic cross-lingual retrieval for German and English queries. Users can query in either language and retrieve relevant results regardless of which language the content was indexed in.

**Key Capabilities**:
- Automatic language detection (German/English)
- Claude-powered query translation
- Parallel search in both languages
- Smart result deduplication by UUID
- Integration with hybrid keyword + vector search

**Use Cases**:
- German users searching for English-indexed EU regulations
- English users searching for German Bundestag documents
- Cross-lingual policy analysis
- Multilingual knowledge discovery

**Configuration**:
```python
# Global setting
ENABLE_MULTILINGUAL_SEARCH = True  # Default

# Per-query override
results = await search(query="...", multilingual=True/False)
```

## Supported Language Pairs

| Source Language | Target Language | Status |
|----------------|-----------------|--------|
| English | German | ✅ Production |
| German | English | ✅ Production |
| English | French | 🚧 Planned |
| German | French | 🚧 Planned |

## Architecture Overview

```
User Query (Any Language)
    ↓
Language Detection (Stopword-based)
    ↓
Query Translation (Claude Haiku)
    ↓
Parallel Search (Original + Translated)
    ↓
Result Merging (UUID-based deduplication)
    ↓
Unified Results (Scored & Ranked)
```

## Performance Metrics

- **Average Latency**: 400-1400ms (mostly translation)
- **Cost per Query**: ~$0.0003 (translation + embeddings)
- **Language Detection Accuracy**: >98%
- **Translation Quality**: High for political/legal domain

## Future Roadmap

### Q1 2025
- ✅ Dual Language Search (EN/DE) - **COMPLETED**
- 🚧 Translation caching for common queries

### Q2 2025
- 📋 French language support (EN↔FR, DE↔FR)
- 📋 Spanish language support (EN↔ES)
- 📋 Multi-language search (3+ languages)

### Q3 2025
- 📋 Italian language support
- 📋 Custom stopwords for domain-specific detection
- 📋 Translation quality monitoring dashboard

## Related Documentation

- [Hybrid Search](../search/hybrid-search.md) - Keyword + vector search
- [MCP Integration](../../../.claude/mcp-patterns.md) - MCP server patterns
- [Knowledge Graph](../graph/knowledge-graph.md) - Graph architecture

## Configuration

### Global Configuration

**File**: `src/config.py`

```python
class GraphRAGSettings:
    # Enable/disable multilingual search globally
    ENABLE_MULTILINGUAL_SEARCH: bool = True

    # Supported language pairs
    SUPPORTED_LANGUAGE_PAIRS: list = [
        ("en", "de"),  # English ↔ German
        ("de", "en"),  # German ↔ English
    ]

    # Translation model
    TRANSLATION_MODEL: str = "claude-3-5-haiku-20241022"
```

### Per-Query Configuration

```python
# Enable multilingual search for a specific query
results = await retriever.retrieve(
    query="What is the GDPR?",
    multilingual=True  # Override global setting
)

# Disable multilingual search for a specific query
results = await retriever.retrieve(
    query="What is the GDPR?",
    multilingual=False  # Single-language only
)
```

## Monitoring

### Key Metrics

Monitor these metrics to ensure multilingual search quality:

1. **Translation Success Rate**: `grep "Translated query" logs/retriever.log | wc -l`
2. **Language Distribution**: Count of queries per language
3. **Average Latency**: Translation + search time
4. **Merge Statistics**: Deduplication effectiveness

### Dashboards

- **LangWatch**: `http://localhost:3001` - Translation cost and latency
- **Ray Dashboard**: `http://localhost:8265` - Search performance
- **Neo4j Browser**: `http://localhost:7474` - Graph statistics

## Support

For issues or questions about multilingual features:

1. Check the feature documentation in this directory
2. Review troubleshooting sections in feature docs
3. Check logs: `grep "multilingual\|translation" logs/retriever.log`
4. Open issue: [GitHub Issues](https://github.com/your-repo/issues)

---

**Last Updated**: 2025-01-13
**Maintained By**: Political Monitoring Agent Team
