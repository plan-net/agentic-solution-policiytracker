# Political Monitoring Chat Interface

A sophisticated AI chat interface for political and regulatory analysis, powered by LangGraph workflows and 15 specialized knowledge graph tools.

## Overview

This chat interface provides intelligent analysis of political documents, regulatory relationships, and policy networks through a temporal knowledge graph. It combines LangGraph's workflow orchestration with LangChain's tool ecosystem to deliver comprehensive, streaming responses with transparent reasoning.

### Key Features

- 🧠 **Intelligent Workflow**: 4-node LangGraph pipeline (understand → plan → execute → synthesize)
- 🔧 **15 Specialized Tools**: Entity analysis, relationship traversal, temporal queries, community detection
- 🧩 **Knowledge Graph Integration**: Graphiti temporal knowledge graphs with entity extraction
- 💭 **Transparent Reasoning**: Real-time thinking output with `<think>` tags for Open WebUI
- 🔄 **Streaming Responses**: OpenAI-compatible streaming API with natural pacing
- 💾 **Session Memory**: LangChain ConversationBufferWindowMemory for context awareness
- 📝 **External Prompts**: Modular prompt system with YAML frontmatter

## Architecture

### LangGraph Workflow

```python
# 4-Node Pipeline
START → understand_query_node → plan_tools_node → execute_tools_node → synthesize_response_node → END
```

#### Node Responsibilities

1. **`understand_query_node`**: LLM-driven query analysis and intent classification
2. **`plan_tools_node`**: Strategic tool selection based on query complexity
3. **`execute_tools_node`**: Parallel execution of selected tools with progress tracking
4. **`synthesize_response_node`**: Comprehensive response generation with graph insights

### State Management

```python
@dataclass
class AgentState(MessagesState):
    # Query Processing
    original_query: str
    query_analysis: Optional[QueryAnalysis]
    
    # Tool Execution
    tool_plan: Optional[ToolPlan]
    tool_results: List[ToolResult]
    
    # Reasoning State
    thinking_state: ThinkingState
    
    # Memory & Context
    conversation_memory: Dict[str, Any]
    session_context: Dict[str, Any]
```

### LangChain Integration

- **Memory**: `ConversationBufferWindowMemory` for 10-exchange context
- **Tools**: 15 custom tools wrapping Graphiti knowledge graph operations
- **Prompts**: External markdown files with template variables
- **Chains**: LLM chains for query analysis, tool planning, and synthesis

## Tools Ecosystem

### 🔍 Search & Discovery
```python
GraphitiSearchTool(graphiti_client)           # Hybrid semantic + keyword search
```

### 👤 Entity Analysis
```python
EntityDetailsTool(graphiti_client)            # Comprehensive entity information
EntityRelationshipsTool(graphiti_client)      # Entity connections and relationships
EntityTimelineTool(graphiti_client)           # Entity evolution over time
SimilarEntitesTool(graphiti_client)           # Similar entities by graph structure
```

### 🕸️ Network Traversal
```python
TraverseFromEntityTool(graphiti_client)       # Multi-hop relationship exploration
FindPathsTool(graphiti_client)                # Connection paths between entities
GetNeighborsTool(graphiti_client)             # Immediate neighbors and relationships
ImpactAnalysisTool(graphiti_client)           # Impact networks and influence analysis
```

### ⏰ Temporal Analysis
```python
DateRangeSearchTool(graphiti_client)          # Events within specific date ranges
EntityHistoryTool(graphiti_client)            # Historical entity changes
ConcurrentEventsTool(graphiti_client)         # Events in same time period
PolicyEvolutionTool(graphiti_client)          # Policy amendment tracking
```

### 🏘️ Community Detection
```python
GetCommunitiesTool(graphiti_client)           # Community and cluster discovery
CommunityMembersTool(graphiti_client)         # Members of specific communities
PolicyClustersTool(graphiti_client)           # Policy groupings by theme/jurisdiction
```

## Streaming with Think Tags

### Overview

The chat interface provides real-time thinking output compatible with Open WebUI's thinking tag rendering:

```html
<think>
Looking at this question, I need to understand what type of analysis you're requesting.
The key entities here appear to be EU AI Act, Meta, compliance requirements.
Since this involves complex regulatory relationships, a graph-based approach will be essential.
</think>

Based on my analysis of the knowledge graph...
```

### Implementation

```python
async def stream_query(self, query: str) -> AsyncGenerator[str, None]:
    """Stream with real-time thinking output."""
    
    # Phase 1: Start thinking
    yield "<think>\n"
    
    # Phase 2: Natural reasoning
    yield "Looking at this question, I need to understand what type of analysis you're requesting. "
    
    # Phase 3: Tool execution with progress updates
    graph_task = asyncio.create_task(self.graph.ainvoke(initial_state))
    
    thinking_updates = [
        "The key entities and relationships involved need to be identified first.",
        "I'll need to map the regulatory landscape to understand the connections.",
        "Graph-based analysis will reveal patterns that simple searches would miss."
    ]
    
    for update in thinking_updates:
        yield update + "\n\n"
        await asyncio.sleep(1.2)
        if graph_task.done():
            break
    
    # Phase 4: Complete thinking
    yield "</think>\n\n"
    
    # Phase 5: Stream final response
    response = final_state.final_response
    sentences = response.split('. ')
    for sentence in sentences:
        yield sentence + ". "
        await asyncio.sleep(0.8)  # Natural reading pace
```

### Thinking Style Guidelines

- **First person narrative**: "I need to examine...", "This shows..."
- **Natural conversational tone**: No emojis, section headers, or structured formatting
- **Logical progression**: Understanding → planning → execution → synthesis
- **Real-time updates**: Progress indicators during tool execution

## API Compatibility

### OpenAI Chat Completions Format

```bash
# Non-streaming
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "political-monitoring-agent",
    "messages": [{"role": "user", "content": "What is the EU AI Act?"}],
    "stream": false
  }'

# Streaming with thinking
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "political-monitoring-agent", 
    "messages": [{"role": "user", "content": "How does GDPR affect Meta?"}],
    "stream": true
  }'
```

### Response Format

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "political-monitoring-agent",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "The EU AI Act is a comprehensive regulation..."
    },
    "finish_reason": "stop"
  }]
}
```

## Prompt System

### External Prompt Management

All prompts are stored as markdown files with YAML frontmatter:

```markdown
---
name: query_analysis
version: 1
description: Analyze user queries for intent, entities, and strategy
tags: ["analysis", "planning", "core"]
---

# Query Analysis

Analyze this user query to understand their intent and extract key information.

## Query to Analyze
{query}

## Analysis Framework
...
```

### Prompt Files

- **`system_prompt.md`**: Main system prompt with tool strategies
- **`query_analysis.md`**: Structured query understanding framework
- **`tool_planning.md`**: Strategic tool execution planning
- **`thinking_template.md`**: Natural conversational thinking patterns
- **`synthesis.md`**: Comprehensive response synthesis

### Loading Prompts

```python
prompt_manager = PromptManager()
analysis_prompt = await prompt_manager.get_prompt("query_analysis")

prompt = ChatPromptTemplate.from_template(analysis_prompt)
chain = prompt | llm | StrOutputParser()
result = await chain.ainvoke({"query": user_query})
```

## Development Workflow

### Setting Up the Agent

```python
from src.chat.agent.graph import EnhancedPoliticalMonitoringAgent
from graphiti_core import Graphiti

# Initialize Graphiti client
graphiti_client = Graphiti(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
await graphiti_client.build_indices_and_constraints()

# Create enhanced agent
agent = EnhancedPoliticalMonitoringAgent(graphiti_client, openai_api_key)

# Process query
response = await agent.process_query("What is the EU Digital Services Act?")

# Stream query with thinking
async for chunk in agent.stream_query("How does GDPR affect Google?"):
    print(chunk, end="", flush=True)
```

### Adding New Tools

1. **Create tool class** inheriting from LangChain `BaseTool`:

```python
class CustomAnalysisTool(BaseTool):
    name = "custom_analysis"
    description = "Performs custom analysis on political entities"
    
    def __init__(self, graphiti_client):
        super().__init__()
        self.graphiti_client = graphiti_client
    
    async def _arun(self, query: str) -> str:
        # Implement tool logic
        results = await self.graphiti_client.search(query)
        return self._format_results(results)
```

2. **Register in nodes.py**:

```python
def _create_tools_map() -> Dict[str, Any]:
    return {
        # ... existing tools
        "custom_analysis": CustomAnalysisTool(graphiti_client),
    }
```

3. **Update tool planning prompt** to include the new tool.

### Modifying Workflow

The LangGraph workflow can be extended with additional nodes:

```python
def _build_graph(self) -> StateGraph:
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("understand", understand_query_node)
    workflow.add_node("plan", plan_tools_node)
    workflow.add_node("execute", execute_tools_node)
    workflow.add_node("custom_analysis", custom_analysis_node)  # New node
    workflow.add_node("synthesize", synthesize_response_node)
    
    # Define flow with conditional routing
    workflow.add_edge(START, "understand")
    workflow.add_edge("understand", "plan")
    workflow.add_conditional_edges(
        "plan",
        should_use_custom_analysis,
        {"custom": "custom_analysis", "standard": "execute"}
    )
    workflow.add_edge("custom_analysis", "synthesize")
    workflow.add_edge("execute", "synthesize")
    workflow.add_edge("synthesize", END)
    
    return workflow.compile()
```

## Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password123

# Optional
NEO4J_DATABASE=neo4j
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.3
MAX_ITERATIONS=8
MEMORY_WINDOW_SIZE=10
```

### Ray Serve Configuration

```python
# Deploy chat server
@serve.deployment(num_replicas=1)
@serve.ingress(app)
class ChatServer:
    def __init__(self):
        self.agent = None  # Lazy initialization
    
    async def _get_agent(self):
        if self.agent is None:
            graphiti_client = await self._get_graphiti_client()
            self.agent = EnhancedPoliticalMonitoringAgent(
                graphiti_client, 
                os.getenv("OPENAI_API_KEY")
            )
        return self.agent
```

## Examples

### Basic Information Lookup

**Query**: "What is GDPR?"

**Workflow**:
1. **Understanding**: Classifies as "information_lookup" with entity "GDPR"
2. **Planning**: Selects tools: `search`, `get_entity_details`, `get_entity_relationships`
3. **Execution**: Gathers comprehensive information about GDPR
4. **Synthesis**: Provides detailed overview with relationships and implications

### Complex Relationship Analysis

**Query**: "How does the EU AI Act affect US tech companies operating in Europe?"

**Workflow**:
1. **Understanding**: Multi-entity relationship analysis with temporal scope
2. **Planning**: Complex tool sequence: `search`, `get_entity_relationships`, `analyze_entity_impact`, `find_paths_between_entities`
3. **Execution**: Maps regulatory relationships and impact pathways
4. **Synthesis**: Reveals compliance requirements, enforcement mechanisms, and business implications

### Temporal Policy Evolution

**Query**: "How has EU data protection regulation evolved since GDPR?"

**Workflow**:
1. **Understanding**: Temporal analysis with policy evolution focus
2. **Planning**: Temporal tools: `get_entity_timeline`, `track_policy_evolution`, `find_concurrent_events`
3. **Execution**: Tracks regulatory changes and policy amendments
4. **Synthesis**: Provides chronological overview with impact assessment

## Monitoring and Debugging

### Logging

```python
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Node execution logs
logger.info(f"Understanding query: {state.original_query}")
logger.info(f"Tool plan created: {len(tool_plan.tool_sequence)} tools planned")
logger.info(f"Tool execution complete: {successful_tools}/{total_tools} successful")
```

### State Inspection

```python
# Debug state at any node
async def debug_node(state: AgentState) -> Dict[str, Any]:
    print(f"Current step: {state.current_step}")
    print(f"Query analysis: {state.query_analysis}")
    print(f"Tools executed: {state.executed_tools}")
    print(f"Thinking state: {state.thinking_state.current_phase}")
    return {}
```

### Performance Metrics

- **Response Time**: Typically 10-30 seconds for complex queries
- **Tool Execution**: Average 2-8 tools per query depending on complexity
- **Memory Usage**: Bounded by ConversationBufferWindowMemory (10 exchanges)
- **Streaming Latency**: ~0.8s between response chunks for natural pacing

## Testing

### Unit Testing

```python
@pytest.fixture
async def mock_agent():
    mock_client = MagicMock()
    agent = EnhancedPoliticalMonitoringAgent(mock_client, "test-key")
    return agent

async def test_query_understanding(mock_agent):
    state = AgentState(original_query="What is GDPR?")
    result = await understand_query_node(state)
    
    assert result["query_analysis"].intent == "information_lookup"
    assert "GDPR" in result["query_analysis"].primary_entity
```

### Integration Testing

```python
async def test_full_workflow():
    # Test complete agent workflow
    agent = EnhancedPoliticalMonitoringAgent(real_client, test_api_key)
    response = await agent.process_query("Test query")
    
    assert len(response) > 100  # Meaningful response
    assert "graph" in response.lower()  # Uses graph capabilities
```

### API Testing

```python
def test_streaming_endpoint():
    response = requests.post(
        "http://localhost:8001/v1/chat/completions",
        json={"model": "political-monitoring-agent", "messages": [...], "stream": True},
        stream=True
    )
    
    chunks = []
    thinking_found = False
    
    for line in response.iter_lines():
        if b'<think>' in line:
            thinking_found = True
        chunks.append(line)
    
    assert thinking_found
    assert len(chunks) > 10
```

## Troubleshooting

### Common Issues

**1. "Agent not responding"**
- Check Graphiti client connection: `await client.build_indices_and_constraints()`
- Verify OpenAI API key is valid
- Check Ray Serve deployment: `ray status`

**2. "Tools not executing"**
- Verify tool imports in `_create_tools_map()`
- Check tool-specific authentication (Neo4j, OpenAI)
- Review tool execution logs for errors

**3. "Memory not persisting"**
- Ensure LangChain memory is properly initialized
- Check session context passing between requests
- Verify memory cleanup thresholds

**4. "Streaming interrupted"**
- Check network connectivity and timeouts
- Verify Open WebUI streaming configuration
- Review async/await patterns in streaming functions

### Debug Commands

```bash
# Check Ray status
ray status

# View server logs
tail -f /tmp/ray/session_*/logs/serve/replica_chat-server_*.log

# Test health endpoint
curl http://localhost:8001/health

# Test basic query
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "political-monitoring-agent", "messages": [{"role": "user", "content": "test"}], "stream": false}'
```

## Future Enhancements

### Planned Features

- **Conditional Workflows**: Dynamic routing based on query complexity
- **Multi-Document Synthesis**: Cross-reference multiple knowledge sources
- **Real-time Knowledge Updates**: Live integration with document processing pipeline
- **Advanced Memory**: Long-term memory persistence beyond session scope
- **Custom Entity Types**: Domain-specific entity classification and handling

### Extension Points

- **Custom Tools**: Domain-specific analysis capabilities
- **Workflow Nodes**: Specialized processing steps
- **Memory Adapters**: Alternative memory backends (Redis, PostgreSQL)
- **Prompt Templates**: Specialized prompts for different analysis types
- **Response Formatters**: Custom output formats (JSON, structured data)

---

## Quick Start

1. **Install dependencies**: LangChain, LangGraph, Graphiti, Ray Serve
2. **Configure environment**: Set OpenAI API key and Neo4j credentials
3. **Deploy server**: `ray serve run src.chat.server.app:ChatServer`
4. **Test endpoint**: Send request to `http://localhost:8001/v1/chat/completions`
5. **Integrate with Open WebUI**: Add as custom model endpoint

For detailed setup instructions, see the main project README.