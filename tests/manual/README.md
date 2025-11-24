# Manual Testing Scripts

This directory contains scripts for manual testing and validation of specific features.

## Scripts

### Entity & Search Tools
- **test_entity_resolution.py** - Test entity resolution improvements
  - Smart entity resolution (no false positives)
  - Structured output format
  - UUID-based fact retrieval
  - Relationship extraction
  - Source attribution
  - Serialization safety checks

- **test_search_tool.py** - Test the search tool with specific queries
  - Manual query testing
  - Search result validation
  - Performance testing

- **test_search_features.py** - Comprehensive search feature testing
  - Multiple search scenarios
  - Feature validation

- **test_tool3_quick.py** - Quick tool testing script
  - Rapid feature verification
  - Quick smoke tests

## Usage

Run any script directly:

```bash
# From project root
python tests/manual/test_entity_resolution.py

# Or with environment variables
NEO4J_URI=bolt://localhost:7687 python tests/manual/test_search_tool.py
```

## Environment Variables

Most scripts use these environment variables:
- `NEO4J_URI` - Neo4j connection URI (default: bolt://localhost:7687)
- `NEO4J_USER` - Neo4j username (default: neo4j)
- `NEO4J_PASSWORD` - Neo4j password (default: password123)
- `OPENAI_API_KEY` - OpenAI API key for LLM features

## Purpose

These scripts are for:
- ✅ Manual feature verification
- ✅ Interactive testing during development
- ✅ Debugging specific functionality
- ✅ Performance analysis
- ✅ Quick smoke tests

**Note**: For automated tests, see `tests/unit/` and `tests/integration/`
