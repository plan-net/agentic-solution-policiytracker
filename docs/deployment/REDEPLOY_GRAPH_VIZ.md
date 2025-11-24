# Redeploy Graph Visualization Service

## 🔧 Fix Applied

Fixed the LangChain safety flag issue in `src/graph_viz/text_to_cypher.py`:

```python
# Added the required safety acknowledgment flag
self.cypher_chain = GraphCypherQAChain.from_llm(
    llm=self.llm,
    graph=self.graph,
    verbose=True,
    validate_cypher=True,
    top_k=50,
    return_intermediate_steps=True,
    allow_dangerous_requests=True,  # ✅ Added this
)
```

**Note**: This is safe because we have additional safety validation in the `validate_cypher()` method that blocks all write operations (CREATE, DELETE, SET, MERGE, etc.).

---

## 🚀 Redeploy Now

### Option 1: Using serve command directly

```bash
# Stop the current deployment (if running)
serve shutdown

# Redeploy all services
serve deploy config.yaml

# Check status
serve status
```

### Option 2: Using Ray CLI

```bash
# If Ray needs restart
ray stop
ray start --head

# Deploy
serve deploy config.yaml
```

### Option 3: Using project's deployment script

```bash
# If you have a deployment script
./scripts/deploy.sh

# Or using make/just
make deploy
# or
just deploy-all
```

---

## ✅ Verify Fix

### Test 1: Check Service Health

```bash
curl http://localhost:8001/graph-viz/api/graph/health
```

Expected response:
```json
{
  "status": "healthy",
  "neo4j_connected": true,
  "llm_available": true,  # ✅ Should be true now!
  "version": "0.2.0"
}
```

### Test 2: Test Text-to-Cypher

```bash
curl -X POST http://localhost:8001/graph-viz/api/graph/text-to-cypher \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Show me all policies",
    "limit": 10
  }'
```

Expected response:
```json
{
  "cypher": "MATCH (p:Entity) WHERE p.name CONTAINS 'policy' RETURN p LIMIT 10",
  "nodes": [...],
  "links": [...],
  "execution_time": 2.5,
  "error": null  # ✅ No error!
}
```

---

## 🐛 If Issues Persist

### Check Logs

```bash
# Ray logs
ray logs

# Serve logs
serve status -v

# Application logs (if using systemd)
journalctl -u graph-viz-server -f
```

### Check Environment Variables

```bash
# Verify OPENAI_API_KEY is set
echo $OPENAI_API_KEY

# Check config.yaml
grep OPENAI_API_KEY config.yaml
```

### Restart Services

```bash
# Full restart
ray stop
docker compose restart neo4j
ray start --head
serve deploy config.yaml
```

---

## 📝 What Changed

**File Modified**: `src/graph_viz/text_to_cypher.py`

**Change**: Added `allow_dangerous_requests=True` parameter to `GraphCypherQAChain.from_llm()`

**Why**: LangChain now requires explicit acknowledgment that the chain can execute database queries. This is a safety measure they added in recent versions.

**Is it Safe?**: Yes! We have additional safety checks:
1. `validate_cypher()` method blocks all write operations
2. Forbidden keywords list: CREATE, DELETE, SET, MERGE, DROP, etc.
3. Query timeout of 5 seconds
4. Result limit of 200 nodes max

---

## 🎯 Expected Behavior After Fix

1. ✅ Health check shows `llm_available: true`
2. ✅ Text-to-Cypher endpoint works without errors
3. ✅ Natural language queries get converted to Cypher
4. ✅ Frontend "Text to Cypher" tab works
5. ✅ GPT-4o-mini successfully generates queries

---

**Status**: Fix applied, ready to redeploy
**Next Step**: Run `serve deploy config.yaml`
