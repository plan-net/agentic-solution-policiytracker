# Development Testing Scripts

This directory contains ad-hoc scripts created during development for testing specific features and functionality. These scripts are **not part of the main workflow** but are preserved for reference and debugging.

## 📁 **Script Categories**

### **ETL & Data Collection Testing**
- `etl_test_summary.py` - ETL test result summaries
- `test_etl_initialization.py` - ETL initialization testing
- `test_etl_with_exa.py` - ETL pipeline with Exa.ai testing
- `test_policy_simple.py` - Basic policy component testing (no API needed)
- `compare_news_collectors.py` - News collector comparison testing

### **Exa.ai Integration Testing**
- `test_exa_direct.py` - Direct Exa.ai API testing
- `test_exa_direct_collector.py` - Exa direct collector testing
- `test_exa_simple.py` - Simple Exa.ai integration testing

### **Document Processing Testing**
- `full_document_processing.py` - Complete document processing pipeline testing
- `process_all_documents_simple.py` - Simple document processing testing
- `process_documents_no_clear.py` - Document processing without clearing data

### **GraphRAG & Knowledge Graph Testing**
- `test_graphrag_langfuse.py` - GraphRAG with Langfuse integration testing
- `explore_graphiti_mcp_search.py` - Graphiti MCP search exploration
- `inspect_graph_schema.py` - Graph schema inspection

### **Validation & Verification**
- `validate_document_content_retrieval.py` - Document content retrieval validation
- `validate_document_retrieval.py` - Document retrieval validation
- `verify_entity_types.py` - Entity type verification

## ⚠️ **Important Notes**

- These scripts may have **hardcoded paths** or **temporary configurations**
- They were created for **one-time testing** during development
- **Dependencies may be outdated** or inconsistent with current codebase
- **Not maintained** - use at your own risk for debugging/reference

## 🔧 **Usage**

If you need to run any of these scripts for debugging:

```bash
# From project root
uv run python scripts/_dev_testing/script_name.py
```

**Recommendation**: Review the script contents before running to understand dependencies and expected environment.

## 🚀 **For Production Use**

Use the main utility scripts in `scripts/` directory instead, which are:
- Integrated with `justfile` commands
- Actively maintained
- Part of the production workflow
- Properly documented and tested