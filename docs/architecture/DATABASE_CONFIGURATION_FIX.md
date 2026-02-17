# Database Configuration Fix

## Issue Identified
The chat server was configured to use `politicamonitoring.v2` database, but Graphiti was not actually connecting to it.

## Root Cause
Graphiti uses the `DEFAULT_DATABASE` environment variable (loaded from `graphiti_core/helpers.py`), not the standard `NEO4J_DATABASE` variable. Without this setting, Graphiti defaults to `None`, which causes it to use Neo4j's default database (usually `neo4j`).

### Technical Details
```python
# graphiti_core/helpers.py
DEFAULT_DATABASE = os.getenv('DEFAULT_DATABASE', None)

# graphiti_core/graphiti.py (line ~200)
self.database = DEFAULT_DATABASE
```

## Solution Applied

### 1. Updated config.yaml
Added `DEFAULT_DATABASE` environment variable to chat-server configuration:

```yaml
- name: chat-server
  runtime_env:
    env_vars:
      NEO4J_DATABASE: politicamonitoring.v2
      DEFAULT_DATABASE: politicamonitoring.v2  # ADDED THIS
```

### 2. Updated config.yaml.template
Added the same for template file to maintain consistency:

```yaml
NEO4J_DATABASE: ${NEO4J_DATABASE}
DEFAULT_DATABASE: ${NEO4J_DATABASE}  # ADDED THIS
```

### 3. Redeployed Ray Serve
```bash
serve deploy config.yaml
```

## Verification

### Test Results
```bash
# Database connection test
Graphiti database: politicamonitoring.v2
Node count in 'politicamonitoring.v2': 241,721 nodes

# Chat server response test
✅ Successfully responds to queries about Matthias Gastel (Bundestag person)
✅ Uses correct database with Bundestag data (Aktivitäten, Vorgänge, etc.)
```

### Ray Serve Status
```
applications:
  chat-server:
    status: RUNNING
    deployments:
      ChatServer:
        status: HEALTHY
        replica_states:
          RUNNING: 1
```

## Database Contents (politicamonitoring.v2)

The database contains German Bundestag legislative data:

| Entity Type | Count |
|---|---|
| Aktivitaet | 160,141 |
| Vorgang | 44,620 |
| Drucksache | 24,764 |
| Deskriptor | 9,960 |
| BundestagPerson | 1,468 |
| Plenarprotokoll | 304 |
| **Total Nodes** | **241,721** |

### Key Relationships
- TAGGED_WITH: 264,985
- RELATED_TO_VORGANG: 174,672
- PERFORMED_BY: 160,137
- REFERENCES_DOCUMENT: 158,504

## Impact

✅ **Chat server now correctly uses `politicamonitoring.v2` database**
✅ **All 15 knowledge graph tools have access to Bundestag data**
✅ **Test questions from `test_questions_graphrag.md` will work properly**

## Future Considerations

1. **Environment Variable Precedence**: Be aware that Graphiti loads `DEFAULT_DATABASE` at module import time
2. **Database Switching**: To switch databases, you must:
   - Update `DEFAULT_DATABASE` in config.yaml
   - Redeploy with `serve deploy config.yaml`
3. **Testing**: Always verify database connection after deployment changes

## Related Files
- `/config.yaml` - Main Ray Serve configuration (line 25)
- `/config.yaml.template` - Template configuration (line 195)
- `/src/chat/server/app.py` - Chat server initialization (line 122-128)
- `/test_questions_graphrag.md` - Test questions for GraphRAG system

## Date
2025-01-18

## Status
✅ **RESOLVED** - Chat server now correctly connects to `politicamonitoring.v2` database
