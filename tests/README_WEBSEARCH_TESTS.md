# WebSearch Tool Testing Guide

This guide helps you verify that the native WebSearch tool is properly configured and being triggered in the PolicyTracker agent.

## Quick Start

### 1. Quick Diagnostic (Recommended First Step)

Run the quick diagnostic script to verify configuration and test execution:

```bash
# From the project root
cd agentic-solution-policiytracker
python scripts/test_websearch_quick.py
```

**What it checks:**
- ✅ WebSearch is in `allowed_tools`
- ✅ Old Exa.ai tools are removed
- ✅ DPA tools remain available
- ✅ WebSearch is triggered for a test query
- ✅ WebSearch is disabled when `enable_web_search=False`

**Expected output:**
```
======================================================================
  STEP 1: Configuration Check
======================================================================

Total allowed tools: 21

✅ WebSearch in allowed_tools: True
✅ DPA/Web search MCP tools: 2
   - mcp__web_search__search_dpa_news
   - mcp__web_search__get_article_content

✅ Old Exa.ai tools correctly removed
...
```

---

### 2. Real-Time Tool Monitoring

Monitor tool calls in real-time during query execution:

```bash
# With a specific query
python scripts/monitor_tools.py "What are the latest EU AI regulations?"

# Interactive mode (choose from predefined queries)
python scripts/monitor_tools.py
```

**What it shows:**
- 🔧 Each tool call as it happens
- 📊 Summary of all tools used
- ✅ Whether WebSearch was triggered
- 📄 Full response

**Example output:**
```
======================================================================
🔧 TOOL CALL #1: WebSearch
======================================================================
Input: {"query": "latest EU AI regulations 2026"}

======================================================================
🔧 TOOL CALL #2: search_knowledge_graph
======================================================================
Input: {"query": "EU AI Act"}
...
```

---

### 3. Comprehensive Test Suite

Run the full test suite with pytest:

```bash
# Run all WebSearch tests
pytest tests/test_web_search.py -v

# Run specific test categories
pytest tests/test_web_search.py::TestWebSearchConfiguration -v
pytest tests/test_web_search.py::TestWebSearchExecution -v
pytest tests/test_web_search.py::TestWebSearchStreaming -v

# Run with detailed output
pytest tests/test_web_search.py -v -s
```

**Test categories:**
1. **Configuration Tests**: Verify WebSearch is properly configured
2. **Execution Tests**: Test WebSearch with various query types
3. **Streaming Tests**: Test WebSearch with streaming responses

---

## Test Scripts Overview

### 📄 `scripts/test_websearch_quick.py`

**Purpose**: Quick verification of WebSearch configuration and basic functionality

**Use when**:
- First time testing WebSearch integration
- After making configuration changes
- Quick sanity check before deployment

**Runtime**: ~30-60 seconds (runs 1 query)

**Pros**:
- Fast and simple
- Clear pass/fail output
- No dependencies beyond the agent

---

### 📄 `scripts/monitor_tools.py`

**Purpose**: Real-time monitoring of tool calls during execution

**Use when**:
- Debugging why WebSearch isn't triggered
- Understanding tool selection behavior
- Seeing the full sequence of tool calls

**Runtime**: ~30-60 seconds per query

**Pros**:
- Shows tool calls as they happen
- Accepts custom queries
- Detailed logging

---

### 📄 `tests/test_web_search.py`

**Purpose**: Comprehensive test suite for WebSearch integration

**Use when**:
- Running automated tests in CI/CD
- Verifying all WebSearch scenarios
- Regression testing after changes

**Runtime**: ~3-5 minutes (runs multiple queries)

**Pros**:
- Complete coverage
- Works with pytest
- Automated assertions

---

## Understanding Test Results

### ✅ WebSearch is Working

You should see:
```
✅ WebSearch in allowed_tools: True
✅ WebSearch triggered: True
Tools used: ['WebSearch', 'search_knowledge_graph', ...]
```

**What this means:**
- WebSearch is properly configured
- Agent can access the tool
- Tool is being used for appropriate queries

---

### ⚠️ WebSearch Not Triggered

You might see:
```
✅ WebSearch in allowed_tools: True
⚠️  WebSearch triggered: False
Tools used: ['search_knowledge_graph', 'get_entity_info']
```

**What this means:**
- WebSearch is configured correctly
- Agent chose other tools instead
- **This may be expected behavior**

**Reasons why WebSearch might not trigger:**
1. **Query answerable from knowledge graph** - Agent prefers existing knowledge
2. **Bundestag API has the data** - Agent uses specialized tools first
3. **Query too vague** - Agent needs more specific search intent
4. **System prompt guidance** - Agent follows "start with knowledge graph" instruction

**How to force WebSearch:**
- Use explicit search terms: "search the web for..."
- Ask for very recent information: "latest news from January 2026..."
- Request breaking news: "breaking news about..."
- Disable other tools temporarily: `agent = PolicyTrackerSDKAgent(enable_bundestag=False)`

---

### ❌ WebSearch Not Configured

You might see:
```
❌ WebSearch in allowed_tools: False
❌ WebSearch triggered: False
```

**What this means:**
- WebSearch is not properly configured
- Check `agent_sdk.py` modifications
- Verify `enable_web_search=True`

**How to fix:**
1. Verify changes in [`agent_sdk.py:360`](../src/claude_agent/agent_sdk.py#L360):
   ```python
   if self.enable_web_search:
       allowed_tools.extend([f"mcp__web_search__{tool}" for tool in WEB_SEARCH_TOOLS])
       allowed_tools.append("WebSearch")  # This line must be present
   ```

2. Check `WEB_SEARCH_TOOLS` constant (line 119):
   ```python
   WEB_SEARCH_TOOLS = [
       "search_dpa_news",
       "get_article_content",
   ]
   ```

3. Verify system prompt mentions WebSearch (line 81):
   ```python
   - WebSearch - Native web search with automatic citations (use for general web searches)
   ```

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'src'"

**Solution**: Run scripts from the project root:
```bash
cd /path/to/agentic-solution-policiytracker
python scripts/test_websearch_quick.py
```

---

### Issue: "Connection refused" or MCP server errors

**Solution**: Ensure MCP servers are running:
```bash
# Check if servers are running
curl http://localhost:8003/sse  # Knowledge graph
curl http://localhost:8004/sse  # Bundestag
curl http://localhost:8005/sse  # Web search

# Start servers if needed
docker-compose up
```

---

### Issue: WebSearch in allowed_tools but never used

**Possible causes:**

1. **System prompt doesn't mention WebSearch**
   - Check [`agent_sdk.py:79-83`](../src/claude_agent/agent_sdk.py#L79-L83)
   - Should include: `"WebSearch - Native web search with automatic citations"`

2. **Agent prefers other tools**
   - Expected behavior per system prompt
   - Agent uses knowledge graph first, then Bundestag, then web search
   - Try queries that require very recent information

3. **ANTHROPIC_API_KEY not set**
   - WebSearch requires valid API key
   - Check: `echo $ANTHROPIC_API_KEY`
   - Set in `.env` or environment

4. **Tool not passed to ClaudeAgentOptions**
   - Verify in [`agent_sdk.py:487`](../src/claude_agent/agent_sdk.py#L487)
   - Should have: `allowed_tools=self._get_allowed_tools()`

---

### Issue: Tests timeout or hang

**Solution**: Increase timeout or check for deadlocks:
```python
# In test file, increase timeout
@pytest.mark.timeout(300)  # 5 minutes
async def test_websearch_with_current_events_query():
    ...
```

Or check Neo4j connection:
```bash
# Test Neo4j connectivity
docker exec -it neo4j cypher-shell -u neo4j -p your_password "MATCH (n) RETURN count(n);"
```

---

## Expected Tool Usage Patterns

### Query: "What is GDPR?"
**Expected tools**: `search_knowledge_graph`, `get_entity_info`
**Why**: Established regulation, available in knowledge graph

### Query: "What are the latest EU AI regulations in 2026?"
**Expected tools**: `WebSearch`, `search_knowledge_graph`
**Why**: Recent information requires web search, then knowledge graph for context

### Query: "Find German Bundestag activities on climate policy"
**Expected tools**: `search_bundestag_activities`, `search_knowledge_graph`
**Why**: Bundestag-specific query uses specialized API

### Query: "Search the web for breaking news about data protection"
**Expected tools**: `WebSearch`
**Why**: Explicit web search request with recent information need

---

## Testing Tips

### 1. Test with Different Query Types

```python
# Current events (should trigger WebSearch)
"What are the latest news about EU regulations?"

# Established topics (should use knowledge graph)
"What is GDPR?"

# Recent breaking news (should trigger WebSearch)
"Breaking news about climate policy in Europe"

# Specific tool request (forces tool usage)
"Search the web for latest AI regulations"
```

### 2. Monitor Logs

Enable debug logging to see tool calls:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Look for log entries like:
```
DEBUG:claude_agent.agent_sdk:Tool called: WebSearch
DEBUG:claude_agent.agent_sdk:Tool input: {"query": "latest EU regulations"}
```

### 3. Check Metadata

Always inspect the returned metadata:
```python
response, session_id, metadata = await agent.query(query)
print(f"Tools used: {metadata['tools_used']}")
print(f"Turns: {metadata['turns']}")
print(f"Entities: {metadata['entities_tracked']}")
```

### 4. Test Edge Cases

```python
# WebSearch disabled
agent = PolicyTrackerSDKAgent(enable_web_search=False)
# Should NOT use WebSearch

# Only web search enabled
agent = PolicyTrackerSDKAgent(
    enable_bundestag=False,
    enable_web_search=True
)
# Should prefer WebSearch

# Empty query
response = await agent.query("")
# Should handle gracefully
```

---

## CI/CD Integration

Add to your CI pipeline:

```yaml
# .github/workflows/test.yml
- name: Run WebSearch tests
  run: |
    pytest tests/test_web_search.py -v --tb=short
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    NEO4J_URI: bolt://localhost:7687
    MCP_SERVER_URL: http://localhost:8003/sse
```

---

## Next Steps

After verifying WebSearch is working:

1. **Monitor Usage**: Track how often WebSearch is used vs other tools
2. **Optimize Prompts**: Adjust system prompt to guide tool selection
3. **Cost Analysis**: Monitor WebSearch costs ($10 per 1,000 searches)
4. **Performance**: Measure response times with WebSearch
5. **Quality**: Compare answer quality with vs without WebSearch

---

## Support

If tests fail or WebSearch doesn't work:

1. **Check Configuration**: Run `python scripts/test_websearch_quick.py`
2. **Review Logs**: Look for errors in agent logs
3. **Verify Environment**: Ensure all MCP servers are running
4. **Check API Key**: Verify ANTHROPIC_API_KEY is valid
5. **Read Documentation**: See [`docs/session-management.md`](../docs/session-management.md)

For issues, check:
- Implementation plan: [`~/.claude/plans/bubbly-munching-cherny.md`]
- Agent SDK code: [`src/claude_agent/agent_sdk.py`](../src/claude_agent/agent_sdk.py)
- System prompt: Lines 54-89 in agent_sdk.py
