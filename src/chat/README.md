# Political Monitoring Chat Interface

A sophisticated AI chat interface for political and regulatory analysis, powered by LangGraph multi-agent orchestration and 15 specialized knowledge graph tools.

## Overview

This chat interface provides intelligent analysis of political documents, regulatory relationships, and policy networks through a temporal knowledge graph. It combines LangGraph's multi-agent workflow orchestration with LangChain's tool ecosystem to deliver comprehensive, streaming responses with transparent reasoning.

### Key Features

- 🤖 **Multi-Agent Architecture**: 4 specialized agents (Query Understanding, Tool Planning, Tool Execution, Response Synthesis)
- 🧠 **Intelligent Workflow**: LangGraph StateGraph orchestration with conditional routing
- 🔧 **15 Specialized Tools**: Entity analysis, relationship traversal, temporal queries, community detection
- 🧩 **Knowledge Graph Integration**: Graphiti temporal knowledge graphs with entity extraction
- 💭 **Transparent Reasoning**: Real-time thinking output with `<think>` tags for Open WebUI
- 🔄 **Streaming Responses**: OpenAI-compatible streaming API with multi-agent progress updates
- 💾 **Session Memory**: InMemoryStore for conversation context and user personalization
- 📝 **External Prompts**: Modular prompt system optimized for each agent type
- 🎯 **Quality Assessment**: 8-dimensional response quality evaluation and optimization
- 🔄 **Production Ready**: Multiple deployment modes with performance optimization

## Architecture

### Multi-Agent System

The system uses 4 specialized agents orchestrated by LangGraph:

```python
# Multi-Agent Pipeline
START → QueryUnderstandingAgent → ToolPlanningAgent → ToolExecutionAgent → ResponseSynthesisAgent → END
```

#### Agent Responsibilities

1. **QueryUnderstandingAgent**: Analyzes user intent, extracts entities, determines complexity and strategy
2. **ToolPlanningAgent**: Intelligently selects and sequences knowledge graph tools based on query analysis
3. **ToolExecutionAgent**: Executes tools with progress tracking and error handling
4. **ResponseSynthesisAgent**: Synthesizes tool results into comprehensive, well-formatted responses

### State Management

```python
@dataclass
class MultiAgentState(TypedDict):
    # Core Query Processing
    original_query: str
    processed_query: str
    query_analysis: Optional[Dict[str, Any]]
    
    # Tool Execution
    tool_plan: Optional[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    
    # Agent Orchestration
    current_agent: str
    agent_sequence: List[str]
    execution_metadata: Dict[str, Any]
    
    # Response Generation
    final_response: str
    response_metadata: Dict[str, Any]
    
    # Session Management
    session_id: str
    conversation_history: List[Dict[str, Any]]
    user_preferences: Dict[str, Any]
    learned_patterns: Dict[str, Any]
    
    # Streaming & Progress
    is_streaming: bool
    thinking_updates: List[str]
    progress_indicators: List[str]
    
    # Error Handling
    errors: List[str]
    warnings: List[str]
    
    # LangChain Integration
    messages: List[BaseMessage]
```

### Agent Integration

Each agent inherits from specialized mixins for enhanced capabilities:

```python
class QueryUnderstandingAgent(BaseAgent, MemoryMixin, StreamingMixin):
    """Analyzes user queries for intent, entities, and strategy."""
    
class ToolPlanningAgent(BaseAgent, MemoryMixin, StreamingMixin):
    """Plans optimal tool execution strategies."""
    
class ToolExecutionAgent(BaseAgent, MemoryMixin, StreamingMixin):
    """Executes knowledge graph tools with intelligent selection."""
    
class ResponseSynthesisAgent(BaseAgent, MemoryMixin, StreamingMixin):
    """Synthesizes comprehensive responses from tool results."""
```

## Tools Ecosystem

### 🔍 Search & Discovery
```python
GraphitiSearchTool(graphiti_client)           # Hybrid semantic + keyword search with multiple strategies
```

### 👤 Entity Analysis
```python
EntityDetailsTool(graphiti_client)            # Comprehensive entity information and properties
EntityRelationshipsTool(graphiti_client)      # Entity connections and relationship networks
EntityTimelineTool(graphiti_client)           # Entity evolution and temporal changes
SimilarEntitesTool(graphiti_client)           # Similar entities by graph structure and context
```

### 🕸️ Network Traversal
```python
TraverseFromEntityTool(graphiti_client)       # Multi-hop relationship exploration
FindPathsTool(graphiti_client)                # Connection paths between entities
ImpactAnalysisTool(graphiti_client)           # Impact networks and influence analysis
```

### ⏰ Temporal Analysis
```python
DateRangeSearchTool(graphiti_client)          # Events within specific date ranges
ConcurrentEventsTool(graphiti_client)         # Events in same time period
PolicyEvolutionTool(graphiti_client)          # Policy amendment and evolution tracking
```

### 🏘️ Community Detection
```python
GetCommunitiesTool(graphiti_client)           # Community and cluster discovery
CommunityMembersTool(graphiti_client)         # Members of specific communities
PolicyClustersTool(graphiti_client)           # Policy groupings by theme/jurisdiction
```

## Multi-Agent Streaming

### Overview

The chat interface provides real-time progress updates from each agent with thinking output compatible with Open WebUI:

```html
<think>
Looking at this question about EU AI Act compliance requirements...
The QueryUnderstandingAgent has identified this as a complex regulatory analysis.
The ToolPlanningAgent is selecting entity relationship and impact analysis tools.
The ToolExecutionAgent is now querying the knowledge graph for relevant connections.
</think>

Based on my analysis of the knowledge graph and regulatory relationships...
```

### Implementation

```python
class MultiAgentStreamingOrchestrator(MultiAgentOrchestrator):
    """Enhanced orchestrator with real-time streaming capabilities."""
    
    async def process_query_with_streaming(
        self,
        query: str,
        session_id: str = None,
        user_id: str = None
    ):
        """Process query with real-time streaming using async generator."""
        
        # Set up streaming queue for agent updates
        stream_queue = asyncio.Queue()
        
        async def stream_callback(data):
            await stream_queue.put(data)
        
        # Start multi-agent processing in background
        process_task = asyncio.create_task(
            self.process_query(query, session_id, user_id, stream_callback)
        )
        
        # Yield streaming updates from each agent
        while not process_task.done():
            try:
                data = await asyncio.wait_for(stream_queue.get(), timeout=0.1)
                yield data
            except asyncio.TimeoutError:
                continue
        
        # Get final result
        final_result = await process_task
        yield {
            "type": "final_result",
            "data": final_result,
            "timestamp": datetime.now().isoformat()
        }
```

### Agent Progress Updates

- **Agent Transitions**: Real-time updates when workflow moves between agents
- **Tool Execution**: Progress indicators during knowledge graph queries
- **Quality Assessment**: Response quality evaluation in real-time
- **Error Handling**: Graceful error reporting with recovery suggestions

## Quality Assessment System

### Multi-Dimensional Evaluation

The system evaluates responses across 8 quality dimensions:

```python
class QualityDimension(Enum):
    COMPLETENESS = "completeness"      # How thoroughly the query is answered
    ACCURACY = "accuracy"              # Factual correctness of information
    RELEVANCE = "relevance"            # How well the response matches the query
    CLARITY = "clarity"                # How clear and understandable the response is
    DEPTH = "depth"                    # Level of detail and analysis provided
    COHERENCE = "coherence"            # Logical flow and structure
    USEFULNESS = "usefulness"          # Practical value to the user
    TRUSTWORTHINESS = "trustworthiness" # Reliability and source credibility
```

### Quality Optimization

```python
class QualityOptimizer:
    """Provides optimization suggestions based on quality assessment."""
    
    async def suggest_optimizations(
        self,
        quality_metrics: QualityMetrics,
        query_analysis: Dict[str, Any],
        tool_results: List[Dict[str, Any]]
    ) -> List[OptimizationSuggestion]:
        """Generate specific optimization suggestions."""
        
        suggestions = []
        
        if quality_metrics.completeness < 0.7:
            suggestions.append(OptimizationSuggestion(
                dimension="completeness",
                suggestion="Consider adding more comprehensive search tools",
                priority="high"
            ))
        
        return suggestions
```

## Tool Integration System

### Intelligent Tool Selection

The `ToolIntegrationManager` provides sophisticated tool selection based on query analysis:

```python
class ToolIntegrationManager:
    """Manages knowledge graph tool integration with intelligent selection."""
    
    def get_tool_recommendations(
        self, 
        intent: str, 
        entities: List[str], 
        complexity: str,
        strategy_type: str
    ) -> List[Dict[str, Any]]:
        """Get intelligent tool recommendations based on query analysis."""
        
        # Intent-based tool selection
        if intent == "information_seeking":
            if strategy_type == "focused":
                return [
                    {
                        "tool_name": "search",
                        "parameters": {"query": " ".join(entities[:2]), "limit": 5},
                        "purpose": "Find general information about key entities",
                        "priority": "high",
                        "estimated_time": 3.0
                    }
                ]
        
        elif intent == "relationship_analysis":
            return [
                {
                    "tool_name": "find_paths_between_entities",
                    "parameters": {"start_entity": entities[0], "end_entity": entities[1]},
                    "purpose": "Find connection paths between entities",
                    "priority": "high",
                    "estimated_time": 4.0
                }
            ]
```

## API Compatibility

### OpenAI Chat Completions Format

```bash
# Non-streaming with multi-agent processing
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "political-monitoring-agent",
    "messages": [{"role": "user", "content": "What is the EU AI Act?"}],
    "stream": false
  }'

# Streaming with real-time agent progress
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "political-monitoring-agent", 
    "messages": [{"role": "user", "content": "How does GDPR affect Meta?"}],
    "stream": true
  }'
```

### Server Implementation

```python
@serve.deployment(num_replicas=1)
@serve.ingress(app)
class ChatServer:
    """OpenAI-compatible chat server with multi-agent orchestration."""
    
    async def _get_orchestrator(self):
        """Lazy initialization of multi-agent orchestrator."""
        if self.orchestrator is None:
            llm = await self._get_llm()
            tool_manager = await self._get_tool_integration_manager()
            
            # Create tools dictionary from tool integration manager
            tools = tool_manager.tools
            
            # Initialize orchestrator with knowledge graph tools
            self.orchestrator = MultiAgentOrchestrator(llm=llm, tools=tools)
            
            # Set up tool integration manager
            self.orchestrator.tool_integration_manager = tool_manager
            self.orchestrator.planning_agent.set_tool_integration_manager(tool_manager)
            self.orchestrator.execution_agent.set_tool_integration_manager(tool_manager)
        
        return self.orchestrator
```

## Memory and Personalization

### Advanced Memory Management

```python
class MemoryManager:
    """Enhanced memory management with conversation pattern analysis."""
    
    async def update_user_conversation_patterns(
        self,
        user_id: str,
        query: str,
        intent: str,
        complexity: str,
        satisfaction_rating: float,
        response_time: float
    ):
        """Update user conversation patterns for personalization."""
        
        # Analyze query patterns
        patterns = await self.analyze_query_patterns(user_id, query, intent)
        
        # Update user preferences
        preferences = await self.get_user_preferences(user_id)
        preferences["preferred_complexity"] = complexity
        preferences["avg_satisfaction"] = (
            preferences.get("avg_satisfaction", 3.0) + satisfaction_rating
        ) / 2
        
        await self.store.aput(("user_prefs",), user_id, preferences)
```

### Personalization Features

- **Query Pattern Learning**: Adapts to user's preferred analysis depth
- **Tool Performance Tracking**: Optimizes tool selection based on success rates
- **Response Style Adaptation**: Adjusts output format based on user preferences
- **Session Context Preservation**: Maintains context across conversation turns

## Development Workflow

### Setting Up the Multi-Agent System

```python
from src.chat.agent.orchestrator import MultiAgentOrchestrator, MultiAgentStreamingOrchestrator
from src.chat.agent.tool_integration import ToolIntegrationManager
from graphiti_core import Graphiti
from langchain_openai import ChatOpenAI

# Initialize components
graphiti_client = Graphiti(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
await graphiti_client.build_indices_and_constraints()

llm = ChatOpenAI(api_key=OPENAI_API_KEY, model="gpt-4o-mini")
tool_manager = ToolIntegrationManager(graphiti_client)

# Create orchestrator
orchestrator = MultiAgentOrchestrator(llm=llm, tools=tool_manager.tools)

# Process query through multi-agent workflow
response = await orchestrator.process_query("What is the EU Digital Services Act?")

# Stream query with real-time agent updates
streaming_orchestrator = MultiAgentStreamingOrchestrator(llm=llm, tools=tool_manager.tools)
async for chunk in streaming_orchestrator.process_query_with_streaming("How does GDPR affect Google?"):
    print(chunk)
```

### Adding New Agents

1. **Create agent class** inheriting from `BaseAgent`:

```python
class CustomAnalysisAgent(BaseAgent, MemoryMixin, StreamingMixin):
    """Custom analysis agent for specialized tasks."""
    
    def __init__(self, llm: BaseLLM):
        super().__init__(llm)
        self.agent_role = AgentRole.CUSTOM_ANALYSIS
    
    async def process(self, state: MultiAgentState) -> AgentResult:
        # Implement agent logic
        analysis_result = await self._perform_custom_analysis(state)
        
        updated_state = dict(state)
        updated_state["custom_analysis"] = analysis_result
        
        return AgentResult(
            success=True,
            updated_state=updated_state,
            message="Custom analysis completed"
        )
```

2. **Register in orchestrator**:

```python
class ExtendedMultiAgentOrchestrator(MultiAgentOrchestrator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_agent = CustomAnalysisAgent(self.llm)
    
    def _build_graph(self) -> StateGraph:
        graph = super()._build_graph()
        
        # Add custom node
        graph.add_node("custom_analysis", self._custom_analysis_node)
        
        # Update routing logic
        graph.add_conditional_edges(
            "route_next",
            self._determine_next_agent_extended,
            {
                "custom_analysis": "custom_analysis",
                # ... existing routes
            }
        )
        
        return graph.compile(checkpointer=self.checkpointer)
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
LLM_TEMPERATURE=0.1
DEPLOYMENT_MODE=production  # development, staging, production
MAX_AGENT_ITERATIONS=8
MEMORY_WINDOW_SIZE=10
STREAMING_CHUNK_DELAY=0.8
QUALITY_THRESHOLD=0.7
```

### Production Configuration

```python
class ProductionConfig:
    """Production-ready configuration with performance optimization."""
    
    def __init__(self, deployment_mode: DeploymentMode = None):
        self.deployment_mode = deployment_mode or self._detect_deployment_mode()
        self.performance_level = self._determine_performance_level()
        self.resource_limits = self._load_resource_limits()
        self.quality_thresholds = self._load_quality_thresholds()
    
    def optimize_for_production(self):
        """Apply production optimizations."""
        if self.deployment_mode == DeploymentMode.PRODUCTION:
            # Enable parallel tool execution
            self.enable_parallel_tools = True
            
            # Optimize memory usage
            self.memory_cleanup_threshold = 100
            
            # Enhanced error handling
            self.enable_circuit_breakers = True
```

## Examples

### Basic Information Lookup

**Query**: "What is GDPR?"

**Multi-Agent Workflow**:
1. **QueryUnderstandingAgent**: Classifies as "information_seeking" with entity "GDPR", medium complexity
2. **ToolPlanningAgent**: Selects focused strategy with tools: `search`, `get_entity_details`
3. **ToolExecutionAgent**: Executes tools and gathers comprehensive GDPR information
4. **ResponseSynthesisAgent**: Synthesizes detailed overview with key provisions and implications

### Complex Relationship Analysis

**Query**: "How does the EU AI Act affect US tech companies operating in Europe?"

**Multi-Agent Workflow**:
1. **QueryUnderstandingAgent**: Multi-entity relationship analysis with jurisdictional scope
2. **ToolPlanningAgent**: Complex strategy with tools: `search`, `find_paths_between_entities`, `analyze_entity_impact`
3. **ToolExecutionAgent**: Maps regulatory relationships and cross-jurisdictional impacts
4. **ResponseSynthesisAgent**: Reveals compliance requirements, enforcement mechanisms, and business implications

### Temporal Policy Evolution

**Query**: "How has EU data protection regulation evolved since GDPR?"

**Multi-Agent Workflow**:
1. **QueryUnderstandingAgent**: Temporal analysis with policy evolution focus
2. **ToolPlanningAgent**: Temporal strategy with tools: `get_entity_timeline`, `track_policy_evolution`, `find_concurrent_events`
3. **ToolExecutionAgent**: Tracks regulatory changes and policy amendments over time
4. **ResponseSynthesisAgent**: Provides chronological overview with impact assessment and future implications

## Testing

### Unit Testing Multi-Agent Components

```python
@pytest.fixture
async def mock_orchestrator():
    mock_llm = MagicMock()
    mock_tools = {"search": MagicMock(), "get_entity_details": MagicMock()}
    orchestrator = MultiAgentOrchestrator(llm=mock_llm, tools=mock_tools)
    return orchestrator

async def test_query_understanding_agent(mock_orchestrator):
    agent = mock_orchestrator.query_agent
    state = MultiAgentState(original_query="What is GDPR?")
    
    result = await agent.process(state)
    
    assert result.success
    assert result.updated_state["query_analysis"]["intent"] == "information_seeking"
    assert "GDPR" in result.updated_state["query_analysis"]["primary_entity"]

async def test_multi_agent_workflow(mock_orchestrator):
    response = await mock_orchestrator.process_query("Test query")
    
    assert response["success"]
    assert len(response["agent_sequence"]) == 4  # All 4 agents executed
    assert response["response"]  # Non-empty response generated
```

### Integration Testing

```python
async def test_full_multi_agent_workflow():
    # Test complete multi-agent system with real components
    graphiti_client = await create_test_graphiti_client()
    tool_manager = ToolIntegrationManager(graphiti_client)
    orchestrator = MultiAgentOrchestrator(llm=test_llm, tools=tool_manager.tools)
    
    response = await orchestrator.process_query("What is the EU AI Act?")
    
    assert response["success"]
    assert len(response["response"]) > 100  # Meaningful response
    assert response["confidence"] > 0.5  # Reasonable confidence
    assert len(response["sources"]) > 0  # Sources included
```

## Performance Metrics

### Multi-Agent System Performance

- **Query Processing**: 15-45 seconds for complex multi-agent workflows
- **Agent Execution**: Average 4 agents per query with conditional routing
- **Tool Selection**: 2-8 tools per query based on intelligent planning
- **Memory Usage**: Bounded by InMemoryStore with configurable limits
- **Streaming Latency**: Real-time agent updates with ~0.8s natural pacing
- **Quality Scores**: Average 0.85+ on 8-dimensional quality assessment

### Scalability Features

- **Parallel Tool Execution**: Multiple knowledge graph tools execute concurrently
- **Lazy Initialization**: Components initialized on-demand for memory efficiency
- **Circuit Breakers**: Automatic error recovery and graceful degradation
- **Resource Limits**: Configurable memory and execution time limits
- **Session Management**: Efficient conversation context handling

## Troubleshooting

### Common Multi-Agent Issues

**1. "Agent workflow stuck"**
- Check LangGraph state transitions and conditional routing
- Verify all agents have proper error handling
- Review agent sequence logs for infinite loops

**2. "Tool selection suboptimal"**
- Verify ToolIntegrationManager configuration
- Check query analysis quality and entity extraction
- Review tool recommendation algorithms

**3. "Quality assessment failing"**
- Check quality dimension configurations
- Verify quality assessor initialization
- Review quality threshold settings

**4. "Streaming performance degraded"**
- Check async/await patterns in streaming orchestrator
- Verify queue management and timeout settings
- Review network connectivity for streaming endpoints

### Debug Commands

```bash
# Check multi-agent system health
curl http://localhost:8001/health

# Test agent workflow with debug info
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "political-monitoring-agent",
    "messages": [{"role": "user", "content": "debug: test multi-agent workflow"}],
    "stream": false
  }'

# Monitor agent execution logs
tail -f /tmp/ray/session_*/logs/serve/replica_chat-server_*.log | grep -E "(Agent|Tool|Quality)"
```

## Future Enhancements

### Planned Multi-Agent Features

- **Dynamic Agent Composition**: Runtime agent selection based on query complexity
- **Agent Learning**: Continuous improvement of agent performance through feedback
- **Cross-Agent Memory**: Shared learning across agent interactions
- **Advanced Routing**: Machine learning-based workflow optimization
- **Agent Specialization**: Domain-specific agent variants for different policy areas

### Extension Points

- **Custom Agents**: Specialized agents for specific analysis types
- **Advanced Tools**: Domain-specific knowledge graph operations
- **Quality Dimensions**: Additional evaluation criteria for response assessment
- **Memory Backends**: Alternative storage systems for conversation persistence
- **Streaming Protocols**: Enhanced real-time communication protocols

---

## Quick Start

1. **Install dependencies**: `pip install langchain langgraph graphiti-core ray[serve]`
2. **Configure environment**: Set OpenAI API key and Neo4j credentials
3. **Initialize services**: Start Neo4j and ensure Graphiti client connectivity
4. **Deploy server**: `ray serve run src.chat.server.app:chat_app`
5. **Test multi-agent system**: Send requests to `http://localhost:8001/v1/chat/completions`
6. **Integrate with Open WebUI**: Add as custom model endpoint with streaming support

For detailed setup instructions and advanced configuration, see the main project README.