# Claude Agent SDK - Policy Tracker Agent

An OpenAI-compatible conversational agent for querying the political monitoring knowledge graph using Claude's native tool-use capabilities via MCP.

## Overview

The Claude Agent provides a production-ready API for conversational access to the knowledge graph. It uses Claude's native agentic loop to autonomously select and execute tools, track conversation context, and enable graph visualization of discussed entities.

**Key Features:**
- 🤖 **OpenAI-Compatible API** - Drop-in replacement for OpenAI chat completions
- 🔧 **Native Tool Use** - Claude's built-in agentic capabilities (no LangChain)
- 📊 **Graph Visualization** - Session tracking for visual context exploration
- ⚡ **Streaming Support** - Real-time response streaming
- 🎯 **Context Aware** - Automatic entity and relationship tracking
- 🚀 **Production Ready** - Ray Serve deployment with health monitoring

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    Client Applications                      │
│   (React UI, API consumers, OpenAI-compatible clients)     │
└───────────────────────┬────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────────┐
│              FastAPI Server (server.py)                     │
│  Endpoints: /v1/chat/completions, /health, /v1/models     │
│  Features: OpenAI compatibility, streaming, CORS           │
└───────────────────────┬────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────────┐
│           PolicyTrackerAgent (agent.py)                     │
│  - Agentic conversation loop                               │
│  - Tool orchestration and execution                        │
│  - Session management and context tracking                 │
│  - Entity extraction and UUID resolution                   │
└───────────────────────┬────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────────┐
│              MCP Client (mcp_client.py)                     │
│  - HTTP/SSE transport to MCP server                        │
│  - Tool call execution via MCP protocol                    │
│  - Connection pooling and retry logic                      │
└───────────────────────┬────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────────┐
│        MCP Server + Knowledge Graph (Neo4j)                │
│  Tools: search_knowledge_graph, analyze_query,            │
│         get_entity_info, find_relationships                │
└────────────────────────────────────────────────────────────┘
```

## Quick Start

### Installation

```bash
# Already installed as part of main project
# Ensure dependencies are available
pip install anthropic fastapi ray[serve] neo4j
```

### Basic Usage

#### 1. Direct Python Usage

```python
from src.claude_agent.agent import PolicyTrackerAgent

# Initialize
agent = PolicyTrackerAgent(
    anthropic_api_key="sk-ant-...",
    mcp_server_url="https://gp-retr-mcp-polmo.kodosumi.io/sse",
    claude_model="claude-sonnet-4-20250514"
)

# Non-streaming query
response, session_id = await agent.query(
    "What are the latest GDPR enforcement actions?"
)

print(f"Response: {response}")
print(f"Session ID: {session_id}")

# Streaming query
async for chunk, session_id in agent.stream_query(
    "Tell me about the Digital Services Act"
):
    print(chunk, end="", flush=True)

# Cleanup
await agent.close()
```

#### 2. OpenAI-Compatible API

```python
import openai

# Configure to use Claude Agent
openai.api_base = "http://localhost:8000/v1"
openai.api_key = "not-needed"  # Agent uses ANTHROPIC_API_KEY

response = openai.ChatCompletion.create(
    model="claude-policytracker",
    messages=[
        {"role": "user", "content": "What regulations were updated this week?"}
    ]
)

print(response.choices[0].message.content)
print(f"Session ID: {response.session_id}")
```

#### 3. Using requests/httpx

```python
import httpx

response = httpx.post(
    "http://localhost:8000/v1/chat/completions",
    json={
        "model": "claude-policytracker",
        "messages": [
            {"role": "user", "content": "Find politicians involved in GDPR"}
        ],
        "stream": False
    }
)

data = response.json()
print(data["choices"][0]["message"]["content"])
print(f"Session: {data['session_id']}")
```

## Deployment

### Ray Serve Deployment

```bash
# Deploy the agent
serve deploy src/claude_agent/server.py:app

# Check status
serve status

# View logs
serve logs claude-agent-server

# Shutdown
serve shutdown
```

### Configuration

Set environment variables:

```bash
# Required
export ANTHROPIC_API_KEY="sk-ant-..."

# Optional (defaults shown)
export MCP_SERVER_URL="https://gp-retr-mcp-polmo.kodosumi.io/sse"
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="your-password"
export NEO4J_DATABASE="neo4j"
export LOG_LEVEL="INFO"
```

### Docker Deployment

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["serve", "run", "src/claude_agent/server.py:app", "--host", "0.0.0.0", "--port", "8000"]
```

## API Reference

### Endpoints

#### `POST /v1/chat/completions`

OpenAI-compatible chat completions with session tracking.

**Request:**
```json
{
  "model": "claude-policytracker",
  "messages": [
    {"role": "user", "content": "Your query here"}
  ],
  "temperature": 0.7,
  "max_tokens": 4096,
  "stream": false,
  "session_id": "optional-existing-session"
}
```

**Response:**
```json
{
  "id": "chatcmpl-abc123...",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "claude-policytracker",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Response text here..."
    },
    "finish_reason": "stop"
  }],
  "session_id": "claude_xyz789..."
}
```

**Streaming:**

Set `"stream": true` to receive Server-Sent Events:

```
data: {"id":"chatcmpl-...","choices":[{"delta":{"content":"Hello"}}]}

data: {"id":"chatcmpl-...","choices":[{"delta":{"content":" there"}}]}

data: {"id":"chatcmpl-...","choices":[{"delta":{},"finish_reason":"stop"}],"session_id":"claude_xyz"}

data: [DONE]
```

#### `GET /health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "claude-policytracker-agent",
  "model": "claude-sonnet-4-20250514",
  "features": ["session_tracking", "graph_visualization"]
}
```

#### `GET /v1/models`

List available models (OpenAI-compatible).

**Response:**
```json
{
  "object": "list",
  "data": [{
    "id": "claude-policytracker",
    "object": "model",
    "created": 1234567890,
    "owned_by": "policytracker"
  }]
}
```

## Available Tools

The agent has access to these knowledge graph tools via MCP:

### 1. `search_knowledge_graph`

Search for entities and information using natural language.

**Usage:**
```
User: "What regulations deal with data privacy?"
Agent: → search_knowledge_graph(query="regulations about data privacy")
```

### 2. `analyze_query`

Analyze query intent and extract entities without executing search.

**Usage:**
```
User: "Tell me about GDPR and the Irish DPC"
Agent: → analyze_query(query="GDPR and Irish DPC")
Result: Identifies entities [GDPR, Irish DPC] and intent [informational]
```

### 3. `get_entity_info`

Get detailed information about a specific entity.

**Usage:**
```
User: "More details about the Digital Services Act"
Agent: → get_entity_info(entity_name="Digital Services Act")
```

### 4. `find_relationships`

Explore connections and relationships for an entity.

**Usage:**
```
User: "Who is involved with GDPR enforcement?"
Agent: → find_relationships(entity_name="GDPR", max_results=10)
```

### 5. `graph_statistics`

Get metadata about the knowledge graph (node counts, types, etc.).

**Usage:**
```
User: "What kind of data do you have?"
Agent: → graph_statistics()
```

## Session Management

Every conversation is assigned a `session_id` that enables:

1. **Context Tracking** - Entities and relationships mentioned are stored
2. **Graph Visualization** - UI can render conversation context as a graph
3. **Message History** - Conversations are persisted to Neo4j
4. **Follow-up Queries** - Context-aware responses in multi-turn conversations

### Using Sessions

```python
# Start a new session
response1, session_id = await agent.query("What is GDPR?")

# Continue the same session
response2, _ = await agent.query(
    "Who enforces it?",
    session_id=session_id
)

# The agent remembers we're talking about GDPR
```

### Visualizing Session Context

Use the session ID with the graph visualization API:

```bash
# Get entities discussed in a conversation
curl "http://localhost:5174/api/graph/chat-context?session_id=claude_abc123"
```

Or view in the UI:
```
http://localhost:5173/chat-context?session=claude_abc123&mode=3d
```

## Advanced Usage

### Custom System Prompt

```python
from src.claude_agent.agent import PolicyTrackerAgent

# Modify the system prompt
custom_prompt = """You are a specialized GDPR compliance assistant...
[Your custom instructions]
"""

agent = PolicyTrackerAgent()
agent.SYSTEM_PROMPT = custom_prompt  # Modify before first query
```

### Custom MCP Server

```python
agent = PolicyTrackerAgent(
    mcp_server_url="http://your-custom-mcp-server:8080/sse"
)
```

### Tool Call Inspection

```python
# Access the MCP client directly for debugging
result = await agent.mcp_client.call_tool(
    "search_knowledge_graph",
    {"query": "test query"}
)
print(result)
```

### Context Tracker Access

```python
# Get the context tracker
tracker = await agent._get_context_tracker()

# Query stored context
context = tracker.context_cache.get(session_id)
print(f"Entities: {context['entity_uuids']}")
print(f"Tools used: {context['tools_used']}")
```

## Monitoring and Debugging

### Logging

Configure logging level:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Agent logs include:
# - Tool executions
# - Entity extraction
# - Session tracking
# - API calls
```

### Health Monitoring

```bash
# Check if agent is running
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","service":"claude-policytracker-agent",...}
```

### Common Issues

#### Tool calls failing
```python
# Test MCP connection directly
from src.claude_agent.mcp_client import MCPClient

client = MCPClient("https://gp-retr-mcp-polmo.kodosumi.io/sse")
result = await client.call_tool("graph_statistics", {})
print(result)  # Should return graph stats
await client.close()
```

#### Session tracking not working
```python
# Verify Neo4j connection
from neo4j import AsyncGraphDatabase

driver = AsyncGraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "password")
)

async with driver.session() as session:
    result = await session.run("RETURN 1 as num")
    print(await result.single())  # Should print: <Record num=1>

await driver.close()
```

#### Poor response quality

- Ensure MCP server is returning relevant results
- Check that knowledge graph has recent data
- Try adjusting max_tokens or temperature
- Review system prompt for clarity

## Performance

### Response Times

| Query Type | Avg. Time | Example |
|------------|-----------|---------|
| Simple factual | 2-3s | "What is GDPR?" |
| Entity lookup | 3-5s | "Find info on Irish DPC" |
| Multi-tool research | 10-15s | "Compare DSA and DMA enforcement" |
| Complex analysis | 20-30s | "Trends in AI regulation over time" |

### Optimization Tips

1. **Use streaming** for better UX on slow queries
2. **Reuse sessions** to maintain context
3. **Limit tool calls** via system prompt guidance
4. **Cache common queries** at application level
5. **Monitor API usage** to stay within rate limits

### Resource Usage

- **Memory**: ~50MB per active session
- **CPU**: Low (mostly waiting on API calls)
- **Network**: ~100-500KB per query (varies with tool results)
- **Rate Limits**: Subject to Anthropic API tier limits

## Testing

### Unit Tests

```python
import pytest
from src.claude_agent.agent import PolicyTrackerAgent

@pytest.mark.asyncio
async def test_agent_query():
    agent = PolicyTrackerAgent()
    response, session_id = await agent.query("test")
    assert len(response) > 0
    assert session_id.startswith("claude_")
    await agent.close()

@pytest.mark.asyncio
async def test_streaming():
    agent = PolicyTrackerAgent()
    chunks = []
    async for chunk, sid in agent.stream_query("test"):
        chunks.append(chunk)
    assert len(chunks) > 0
    await agent.close()
```

### Integration Tests

```bash
# Test via HTTP API
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-policytracker",
    "messages": [{"role": "user", "content": "test"}]
  }'
```

## Examples

### Example 1: Simple Query

```python
agent = PolicyTrackerAgent()
response, session = await agent.query(
    "What is the Digital Services Act?"
)
print(response)
# Output: "The Digital Services Act (DSA) is a European Union regulation..."
```

### Example 2: Multi-Turn Conversation

```python
agent = PolicyTrackerAgent()

# First query
resp1, sid = await agent.query("What is GDPR?")

# Follow-up query (remembers context)
resp2, _ = await agent.query("Who enforces it in Ireland?", session_id=sid)

# Another follow-up
resp3, _ = await agent.query("What penalties can they impose?", session_id=sid)
```

### Example 3: Research Query

```python
agent = PolicyTrackerAgent()
response, session = await agent.query("""
Analyze the relationship between the Digital Services Act and
content moderation policies across EU member states. Include
key politicians and regulatory bodies involved.
""")
print(response)
# Agent will use multiple tools: search, get_entity_info, find_relationships
```

### Example 4: Streaming Response

```python
import asyncio

agent = PolicyTrackerAgent()

async def stream_example():
    print("Assistant: ", end="", flush=True)
    async for chunk, session_id in agent.stream_query(
        "Explain the AI Act enforcement timeline"
    ):
        if chunk:
            print(chunk, end="", flush=True)
    print(f"\n\nSession: {session_id}")

asyncio.run(stream_example())
```

## Comparison with Other Approaches

| Feature | Claude Agent SDK | LangChain | LangGraph |
|---------|------------------|-----------|-----------|
| **Complexity** | Low | Medium | High |
| **Tool Use** | Native Claude | Wrapped tools | State machine |
| **Streaming** | Built-in | Limited | Complex |
| **Flexibility** | High | Medium | Very High |
| **Maintenance** | Easy | Medium | Complex |
| **Performance** | Fast | Medium | Variable |

## Roadmap

### Planned Features

- [ ] Multi-session conversation memory
- [ ] Custom tool registration API
- [ ] Webhook notifications for long queries
- [ ] Integration with document upload
- [ ] Fine-tuned system prompts per domain
- [ ] Advanced caching strategies
- [ ] Batch query support
- [ ] WebSocket alternative to SSE

## Support

- **Documentation**: See [main docs](../../docs/)
- **Issues**: Check logs with `just logs` or `just kodosumi-logs`
- **Questions**: Review [User Guide](../../docs/USER_GUIDE.md)

## License

Part of the Political Monitoring Agent project. See [LICENSE](../../LICENSE) for details.

---

*Claude Agent SDK v1.0.0 - Built with Anthropic Claude and MCP*
