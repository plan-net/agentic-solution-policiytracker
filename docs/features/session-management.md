# Session Management in PolicyTracker Agent

## Overview

The PolicyTracker agent implements a **multi-layered session management system** that combines in-memory caching with Neo4j persistence to provide robust, stateful conversations. Sessions track conversation history, entity mentions, tool usage, and enable multi-turn context awareness.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Query                              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Session ID Generation                        │
│  (auto-generated or user-provided for continuation)             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ClaudeSDKClient                              │
│  (processes query with multi-turn context)                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
          ┌──────────────┴──────────────┐
          │                             │
          ▼                             ▼
┌──────────────────────┐    ┌──────────────────────┐
│  ChatContextTracker  │    │  SDKContextManager   │
│  (tool execution &   │    │  (conversation       │
│   entity tracking)   │    │   history loading)   │
└──────────┬───────────┘    └──────────┬───────────┘
           │                           │
           └───────────┬───────────────┘
                       │
                       ▼
           ┌───────────────────────┐
           │   Neo4j ChatSession   │
           │   (persistent storage) │
           └───────────────────────┘
```

## Core Components

### 1. Session ID Management

**Location**: [`src/claude_agent/agent_sdk.py:310-312`](../src/claude_agent/agent_sdk.py#L310-L312)

```python
def _generate_session_id(self) -> str:
    """Generate a unique session ID."""
    return f"claude_{uuid.uuid4().hex[:16]}"
```

**Session ID Format**: `claude_<16-char-hex>`

**Usage**:
- **New conversation**: Don't provide a session_id, one will be auto-generated
- **Continue conversation**: Provide the same session_id from a previous interaction

**Example**:
```python
# New session
response, session_id, metadata = await agent.query("Tell me about GDPR")
# Returns: session_id = "claude_a1b2c3d4e5f6g7h8"

# Continue session
response, session_id, metadata = await agent.query(
    "What are the penalties?",
    session_id="claude_a1b2c3d4e5f6g7h8"  # Same session
)
```

---

### 2. ChatContextTracker

**Location**: [`src/graph_viz/context_tracker.py`](../src/graph_viz/context_tracker.py)

**Purpose**: Tracks tool executions and chat messages in real-time during conversation

**Initialization**:
```python
context_tracker = ChatContextTracker(driver=neo4j_driver, ttl_minutes=60)
```

**In-Memory Cache Structure**:
```python
context_cache[session_id] = {
    "created_at": datetime,           # Session start time
    "entity_uuids": set(),           # UUIDs of entities mentioned
    "relationship_data": [],         # Graph relationships discovered
    "tools_used": [],                # History of tool calls
    "query_text": str,               # Original query text
    "messages": [                    # Chat message history
        {
            "role": "user" | "assistant",
            "content": str,
            "timestamp": str
        }
    ]
}
```

**Key Features**:

1. **Automatic Entity Extraction**: Extracts entity UUIDs from tool results
   - Searches for keys: `uuid`, `entity_uuid`, `source_uuid`, `target_uuid`, `node_uuid`
   - Tracks entities mentioned across multiple tool calls

2. **Tool Usage Tracking**: Records every tool call with timestamp
   ```python
   await context_tracker.track_tool_execution(
       session_id=session_id,
       tool_name="search_knowledge_graph",
       tool_result={"entities": [...], "relationships": [...]}
   )
   ```

3. **Message Storage**: Stores user and assistant messages
   ```python
   await context_tracker.store_message(session_id, "user", "What is GDPR?")
   await context_tracker.store_message(session_id, "assistant", "GDPR is...")
   ```

4. **Neo4j Persistence**: Automatically persists context to Neo4j after each update
   - Creates/updates `ChatSession` nodes
   - Survives server restarts
   - Enables cross-service access

**TTL (Time-to-Live)**:
- **In-memory cache**: 60 minutes (configurable)
- **Neo4j storage**: No expiration (persistent until manually deleted)

---

### 3. SDKContextManager

**Location**: [`src/shared/context_manager.py`](../src/shared/context_manager.py)

**Purpose**: Manages multi-turn conversation context for Claude Agent SDK

**Initialization**:
```python
sdk_context_manager = SDKContextManager(
    neo4j_driver=driver,
    max_context_messages=10,      # Max messages to include
    max_context_tokens=4000,      # Token limit for context
    context_ttl_hours=24          # Cache expiration
)
```

**Key Responsibilities**:

1. **Load Conversation History**: Retrieves past messages from Neo4j
   ```python
   context = await sdk_context_manager.get_session_context(session_id)
   # Returns: {messages: [...], entities: [...], tools_used: [...], is_continuation: bool}
   ```

2. **Build Context Prompts**: Creates conversation context for Claude
   ```python
   context_prompt = sdk_context_manager.build_context_prompt(context)
   # Example output:
   # """
   # ## Previous Conversation Context
   #
   # You are continuing a conversation from session claude_abc123.
   #
   # Recent messages:
   # - User: "Tell me about GDPR"
   # - Assistant: "GDPR is the General Data Protection Regulation..."
   # - User: "What are the penalties?"
   #
   # Entities discussed: [uuid-1, uuid-2, uuid-3]
   # Tools used: [search_knowledge_graph, get_entity_info]
   # """
   ```

3. **Token-Aware Trimming**: Ensures context fits within token limits
   - Keeps most recent messages
   - Estimates ~4 characters per token
   - Prevents context overflow

4. **Update Context**: Stores new interactions
   ```python
   await sdk_context_manager.update_context(
       session_id,
       {"role": "assistant", "content": "The penalties include..."},
       entities=["uuid-123", "uuid-456"]
   )
   ```

---

### 4. Multi-Turn Context Integration

**Location**: [`src/claude_agent/agent_sdk.py:271-308`](../src/claude_agent/agent_sdk.py#L271-L308)

**Process**:

1. **Load base system prompt** from PromptManager or fallback
2. **Add client context** (business understanding)
3. **Add response synthesis guidelines** (Public Affairs perspective)
4. **Add reflection/tool selection strategy** (if enabled)
5. **Add conversation context** (if multi-turn enabled and continuing session)

```python
async def _build_system_prompt_with_context(self, session_id: str) -> str:
    # Get base prompt
    base_prompt = await self._get_system_prompt()

    # Add client context
    client_context_prompt = await self._get_client_context_prompt()
    if client_context_prompt:
        base_prompt = f"{base_prompt}\n\n{client_context_prompt}"

    # Add conversation context if multi-turn enabled
    if self.enable_multi_turn:
        context_manager = await self._get_sdk_context_manager()
        context = await context_manager.get_session_context(session_id)
        context_prompt = context_manager.build_context_prompt(context)
        if context_prompt:
            base_prompt = f"{base_prompt}\n\n{context_prompt}"

    return base_prompt
```

**Configuration**:
```python
agent = PolicyTrackerSDKAgent(
    enable_multi_turn=True,  # Enable conversation history (default: True)
    max_turns=15            # Max tool-use turns per query (default: 15)
)
```

---

## Neo4j Storage Schema

### ChatSession Node

```cypher
(:ChatSession {
  session_id: string,              // Unique session identifier
  created_at: datetime,            // Session creation timestamp
  last_updated: datetime,          // Last update timestamp
  entity_uuids: [string],          // Array of entity UUIDs mentioned
  tools_used_json: string,         // JSON array of tool executions
  messages_json: string,           // JSON array of messages
  query_text: string               // Original query text
})
```

**Example**:
```cypher
CREATE (s:ChatSession {
  session_id: "claude_a1b2c3d4e5f6g7h8",
  created_at: datetime("2024-01-15T10:30:00Z"),
  last_updated: datetime("2024-01-15T10:35:00Z"),
  entity_uuids: ["uuid-123", "uuid-456", "uuid-789"],
  tools_used_json: '[{"tool_name": "search_knowledge_graph", "timestamp": "..."}]',
  messages_json: '[{"role": "user", "content": "What is GDPR?", "timestamp": "..."}]',
  query_text: "What is GDPR?"
})
```

**Querying Sessions**:
```cypher
// Get session by ID
MATCH (s:ChatSession {session_id: $session_id})
RETURN s

// Get recent sessions
MATCH (s:ChatSession)
WHERE s.last_updated > datetime() - duration({hours: 24})
RETURN s
ORDER BY s.last_updated DESC

// Get sessions mentioning specific entity
MATCH (s:ChatSession)
WHERE $entity_uuid IN s.entity_uuids
RETURN s
```

---

## Session Lifecycle

### 1. New Session Flow

```python
# User query without session_id
agent = PolicyTrackerSDKAgent()
response, session_id, metadata = await agent.query("Tell me about EU AI Act")

# What happens internally:
# 1. Generate new session_id: "claude_abc123"
# 2. Initialize empty context in ChatContextTracker
# 3. Execute query with Claude SDK
# 4. Track tool executions and extract entities
# 5. Store messages (user + assistant) in context
# 6. Persist context to Neo4j ChatSession node
# 7. Return response + session_id + metadata
```

**Response Metadata**:
```python
metadata = {
    "session_id": "claude_abc123",
    "turns": 2,                              # Number of tool-use turns
    "model": "claude-sonnet-4-20250514",
    "reflection": {
        "total_tools": 2,
        "avg_confidence": 0.85,
        "low_confidence_tools": []
    },
    "entities_tracked": 3,                   # Entities found
    "tools_used": ["search_knowledge_graph", "get_entity_info"]
}
```

### 2. Continuing Session Flow

```python
# User provides same session_id
response, session_id, metadata = await agent.query(
    "What about data protection?",
    session_id="claude_abc123"  # Same session
)

# What happens internally:
# 1. Receive existing session_id
# 2. SDKContextManager checks cache for session context
# 3. If not in cache, load from Neo4j ChatSession node
# 4. Build context prompt with previous messages + entities + tools
# 5. Add context prompt to system prompt
# 6. Execute query with full conversation context
# 7. Claude sees previous conversation and maintains continuity
# 8. Update context with new message + entities
# 9. Persist updated context to Neo4j
# 10. Return response with continuity
```

**Context Prompt Added to System**:
```
## Previous Conversation Context

You are continuing a conversation from session claude_abc123.

Recent messages:
- User: "Tell me about EU AI Act"
- Assistant: "The EU AI Act is a comprehensive regulatory framework..."
- User: "What about data protection?"

Entities discussed: [uuid-gdpr, uuid-ai-act, uuid-eu-commission]
Tools used: [search_knowledge_graph, get_entity_info, find_relationships]

Please maintain context from the above conversation when responding.
```

### 3. Session Expiration

**In-Memory Cache**:
- TTL: 60 minutes (default for ChatContextTracker)
- TTL: 24 hours (default for SDKContextManager)
- After expiration: Reloaded from Neo4j on next access

**Neo4j Storage**:
- No automatic expiration
- Persistent until manually deleted
- Can query historical sessions anytime

---

## Observability Integration

### LangWatch Integration

**Location**: [`src/claude_agent/agent_sdk.py:432-433`](../src/claude_agent/agent_sdk.py#L432-L433)

```python
# Set thread_id for LangWatch trace grouping
langwatch_config.set_thread_id(session_id)
langwatch_config.set_session_query(session_id, user_message)
```

**Features**:
- Groups all traces from same session under one thread
- Tracks tool usage per session
- Monitors token consumption across conversation
- Records turn count and stop reasons

### LangFuse Integration

**Location**: [`src/claude_agent/agent_sdk.py:436-446`](../src/claude_agent/agent_sdk.py#L436-L446)

```python
langfuse_trace = langfuse.start_as_current_span(
    name="policy_tracker_query",
    input={"user_message": user_message, "session_id": session_id},
    metadata={"agent": "PolicyTrackerSDKAgent", "model": self.model}
)
```

**Features**:
- Creates traces with session_id in metadata
- Links multiple queries in same session
- Tracks conversation flow and context usage

---

## API Reference

### PolicyTrackerSDKAgent.query()

**Signature**:
```python
async def query(
    self,
    user_message: str,
    session_id: Optional[str] = None,
) -> tuple[str, str, dict[str, Any]]
```

**Parameters**:
- `user_message` (str): The user's query
- `session_id` (Optional[str]): Session ID for continuation (auto-generated if not provided)

**Returns**:
- `response_text` (str): The agent's response
- `session_id` (str): The session identifier (generated or provided)
- `metadata` (dict): Session metadata including:
  - `session_id`: Session identifier
  - `turns`: Number of tool-use turns
  - `model`: Claude model used
  - `reflection`: Reflection summary with confidence scores
  - `entities_tracked`: Count of entities mentioned
  - `tools_used`: List of tools called

**Example**:
```python
agent = PolicyTrackerSDKAgent()

# New conversation
response1, sid, meta1 = await agent.query("What is GDPR?")
print(f"Session: {sid}")  # claude_abc123
print(f"Entities: {meta1['entities_tracked']}")  # 3
print(f"Tools: {meta1['tools_used']}")  # ['search_knowledge_graph', ...]

# Continue conversation
response2, sid, meta2 = await agent.query(
    "What are the penalties?",
    session_id=sid  # Use same session
)
print(f"Session: {sid}")  # claude_abc123 (same)
print(f"Total turns: {meta2['turns']}")
```

### PolicyTrackerSDKAgent.stream_query()

**Signature**:
```python
async def stream_query(
    self,
    user_message: str,
    session_id: Optional[str] = None,
) -> AsyncGenerator[tuple[str, str, dict[str, Any]], None]
```

**Yields**:
- `(chunk, session_id, metadata)` tuples
- `chunk` (str): Partial response text
- `session_id` (str): Session identifier
- `metadata` (dict): Session metadata (only in final yield)

**Example**:
```python
async for chunk, sid, meta in agent.stream_query("What is GDPR?"):
    if chunk:
        print(chunk, end="", flush=True)
    else:
        # Final yield with metadata
        print(f"\nSession: {sid}")
        print(f"Tools used: {meta['tools_used']}")
```

---

## Configuration Options

```python
agent = PolicyTrackerSDKAgent(
    # Multi-turn settings
    enable_multi_turn=True,          # Enable conversation history (default: True)
    max_turns=15,                    # Max tool-use turns per query (default: 15)

    # Tool settings
    enable_web_search=True,          # Enable web search tools (default: True)
    enable_bundestag=True,           # Enable Bundestag API tools (default: True)
    enable_todo=True,                # Enable TodoWrite tool (default: True)

    # Model settings
    claude_model="claude-sonnet-4-20250514",  # Claude model
    max_thinking_tokens=10000,       # Extended thinking budget (default: 10000)

    # Optional: Custom MCP server URLs
    mcp_server_url="http://localhost:8003/sse",
    bundestag_mcp_url="http://localhost:8004/sse",
    web_search_mcp_url="http://localhost:8005/sse"
)
```

---

## Best Practices

### 1. Session ID Management

✅ **DO**:
- Reuse session IDs for multi-turn conversations about the same topic
- Generate new session IDs for unrelated topics
- Store session IDs on client side for conversation continuation
- Use session IDs to track user conversation history

❌ **DON'T**:
- Reuse session IDs across different users (security risk)
- Keep sessions open indefinitely (eventual context overflow)
- Mix unrelated topics in the same session

### 2. Context Monitoring

Monitor these metadata fields to understand conversation state:

```python
response, session_id, metadata = await agent.query(query, session_id=sid)

# Check context usage
entities_count = metadata['entities_tracked']
if entities_count > 10:
    print("⚠️  Many entities tracked, consider starting new session")

# Check turn count
turns = metadata['turns']
if turns > 8:
    print("⚠️  Many tool calls, query might be too complex")

# Check confidence
avg_confidence = metadata['reflection']['avg_confidence']
if avg_confidence < 0.7:
    print("⚠️  Low confidence, verify answer quality")
```

### 3. Session Cleanup

Sessions persist in Neo4j indefinitely. Implement cleanup for old sessions:

```cypher
// Delete sessions older than 30 days
MATCH (s:ChatSession)
WHERE s.last_updated < datetime() - duration({days: 30})
DELETE s
```

### 4. Entity Tracking

Use entity UUIDs to understand what the conversation is about:

```python
# After query
response, session_id, metadata = await agent.query(query)

# Get tracked entities from Neo4j
async with neo4j_driver.session() as session:
    result = await session.run(
        """
        MATCH (s:ChatSession {session_id: $session_id})
        UNWIND s.entity_uuids AS entity_uuid
        MATCH (e:Entity {uuid: entity_uuid})
        RETURN e.name AS entity_name, e.type AS entity_type
        """,
        session_id=session_id
    )
    entities = [record async for record in result]
    print(f"Conversation is about: {entities}")
```

---

## Troubleshooting

### Session Not Continuing

**Symptom**: Agent doesn't remember previous conversation

**Possible Causes**:
1. `enable_multi_turn=False` in agent configuration
   - **Fix**: Set `enable_multi_turn=True`

2. Wrong session_id provided
   - **Fix**: Verify session_id matches previous query

3. Session expired from cache and Neo4j unreachable
   - **Fix**: Check Neo4j connection in logs

4. Session not in Neo4j yet (first message in session)
   - **Expected**: Context builds after first interaction

### High Memory Usage

**Symptom**: Agent using too much memory

**Possible Causes**:
1. Many active sessions in cache
   - **Fix**: Lower `ttl_minutes` in ChatContextTracker
   - **Fix**: Implement session cleanup

2. Long conversation history
   - **Fix**: Lower `max_context_messages` in SDKContextManager
   - **Fix**: Start new sessions periodically

### Context Too Long

**Symptom**: Queries timing out or hitting token limits

**Possible Causes**:
1. Too many messages in context
   - **Fix**: Lower `max_context_messages` (default: 10)
   - **Fix**: Start new session for topic changes

2. Long messages in context
   - **Fix**: Lower `max_context_tokens` (default: 4000)

---

## Performance Considerations

### In-Memory Cache

**Advantages**:
- Fast access (no database query)
- Reduces Neo4j load
- Suitable for active conversations

**Limitations**:
- Lost on server restart
- Memory overhead for many sessions
- Not shared across server instances

**Recommendation**: Use in-memory cache for active sessions, rely on Neo4j for resumption

### Neo4j Persistence

**Advantages**:
- Survives server restarts
- Enables historical analysis
- Shared across server instances
- Supports complex queries

**Limitations**:
- Slower than in-memory access
- Requires database connection
- Storage overhead

**Recommendation**: Use Neo4j for long-term storage and session resumption

### Token Usage

**Context adds tokens to each query**:
- Base system prompt: ~500 tokens
- Client context: ~200 tokens
- Conversation context: ~100-500 tokens (depends on history)
- **Total overhead**: ~800-1200 tokens per query

**Optimization**:
- Keep `max_context_messages` low for cost efficiency
- Start new sessions when topic changes significantly
- Monitor `metadata['turns']` to detect long conversations

---

## Example Use Cases

### 1. Customer Support Chatbot

```python
# Store session_id in user's session
user_sessions = {}  # {user_id: session_id}

async def handle_message(user_id: str, message: str):
    # Get or create session for user
    session_id = user_sessions.get(user_id)

    response, session_id, metadata = await agent.query(
        message,
        session_id=session_id
    )

    # Store session for next message
    user_sessions[user_id] = session_id

    return response
```

### 2. Research Assistant

```python
# Start new session per research topic
research_sessions = {}  # {topic: session_id}

async def research_query(topic: str, query: str):
    # Get or create session for topic
    session_id = research_sessions.get(topic)

    response, session_id, metadata = await agent.query(
        query,
        session_id=session_id
    )

    research_sessions[topic] = session_id

    # Track entities researched
    entities_count = metadata['entities_tracked']
    print(f"📊 {entities_count} entities researched on {topic}")

    return response
```

### 3. Multi-Session Analytics

```python
async def analyze_session_history(session_id: str):
    """Analyze a completed session."""
    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (s:ChatSession {session_id: $session_id})
            RETURN s.entity_uuids AS entities,
                   s.tools_used_json AS tools,
                   s.messages_json AS messages,
                   s.created_at AS started,
                   s.last_updated AS ended
            """,
            session_id=session_id
        )

        record = await result.single()
        if record:
            import json
            tools = json.loads(record['tools'])
            messages = json.loads(record['messages'])

            print(f"📈 Session Analytics:")
            print(f"  Duration: {record['ended'] - record['started']}")
            print(f"  Messages: {len(messages)}")
            print(f"  Entities: {len(record['entities'])}")
            print(f"  Tools used: {len(tools)}")

            # Most used tools
            tool_counts = {}
            for tool in tools:
                name = tool['tool_name']
                tool_counts[name] = tool_counts.get(name, 0) + 1

            print(f"  Top tools: {tool_counts}")
```

---

## Summary

The PolicyTracker agent's session management system provides:

✅ **Stateful Conversations**: Multi-turn context awareness with conversation history
✅ **Entity Tracking**: Automatic extraction and tracking of mentioned entities
✅ **Tool Usage Monitoring**: Complete audit trail of all tool executions
✅ **Persistent Storage**: Neo4j-backed persistence across server restarts
✅ **Performance Optimization**: In-memory caching with configurable TTL
✅ **Observability**: Integration with LangWatch and LangFuse
✅ **Flexible Configuration**: Customizable context limits and behavior

This architecture ensures conversations are contextual, traceable, and can be seamlessly resumed, making the agent suitable for complex, multi-turn policy research and analysis tasks.
