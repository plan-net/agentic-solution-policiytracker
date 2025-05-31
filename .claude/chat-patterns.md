# Chat Interface v0.2.0 Patterns

## Multi-Agent Chat Architecture

### Core Components
- **FastAPI Server**: OpenAI-compatible streaming API at `/v1/chat/completions`
- **LangGraph Orchestrator**: 4-agent workflow with Command handoffs
- **Knowledge Graph Tools**: 15 specialized tools for graph exploration
- **Session Memory**: Conversation context with 10-exchange history

### Agent Workflow Pattern
```python
# 4-agent sequential workflow
query_understanding → tool_planning → tool_execution → response_synthesis

# Using Command handoffs for dynamic routing
async def _query_understanding_node(self, state):
    result = await self.query_agent.process(state)
    if result.success:
        return Command(goto="tool_planning", update=result.state)
    else:
        return Command(goto=END, update=error_state)
```

## Streaming Chat Implementation

### OpenAI-Compatible Streaming
```python
# FastAPI endpoint with streaming response
@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    if request.stream:
        return StreamingResponse(
            orchestrator.process_query_streaming(request),
            media_type="text/plain"
        )
```

### LangGraph Native Streaming
```python
# Use native LangGraph streaming modes
async for chunk in graph.astream(
    initial_state,
    stream_mode=["updates", "custom"]
):
    if isinstance(chunk, tuple):
        mode, data = chunk
        if mode == "updates":
            reasoning = convert_update_to_reasoning(data)
        elif mode == "custom":
            reasoning = data.get("reasoning", "")
    
    yield create_streaming_chunk(reasoning)
```

### Single Thinking Block Pattern
```python
# Start thinking block
yield "<think>\nAnalyzing query...\n\n"

# Stream continuous reasoning (NO new <think> tags)
async for reasoning in process_workflow():
    yield reasoning

# Close thinking and provide response  
yield "\nAnalysis complete.\n</think>\n\n"
yield final_response
```

## Knowledge Graph Tool Integration

### Tool Categories (15 total)
```python
ENTITY_TOOLS = [
    "entity_details", "entity_relationships", 
    "entity_timeline", "entity_search"
]

NETWORK_TOOLS = [
    "traverse_network", "find_central_entities",
    "find_shortest_path", "detect_communities"  
]

TEMPORAL_TOOLS = [
    "track_changes", "compare_timeframes", "timeline_analysis"
]

SEARCH_TOOLS = [
    "semantic_search", "search_rerank", "explore_graph"
]
```

### Tool Execution Pattern
```python
async def execute_tools(self, state: MultiAgentState):
    results = []
    
    for tool_spec in state.tool_plan.tool_sequence:
        # Get tool by name
        tool = self.knowledge_graph_tools.get_tool(tool_spec.tool_name)
        
        # Execute with parameters
        result = await tool.execute(**tool_spec.parameters)
        results.append(result)
        
        # Stream progress
        writer = get_stream_writer()
        writer({"reasoning": f"✅ {tool_spec.tool_name} completed\n"})
    
    return Command(goto="response_synthesis", update={"tool_results": results})
```

## Session Memory Management

### LangChain Memory Integration
```python
# Configure conversation memory
memory = ConversationSummaryBufferMemory(
    llm=llm,
    max_token_limit=2000,  # Adjust based on model context
    return_messages=True
)

# Memory in chat state
class MultiAgentState(TypedDict):
    messages: List[BaseMessage]
    conversation_history: str
    session_id: str
    memory_summary: Optional[str]
```

### Context Window Management
```python
def manage_context_window(messages: List[BaseMessage], max_exchanges: int = 10):
    """Keep last N exchanges plus system message."""
    if len(messages) <= (max_exchanges * 2 + 1):  # +1 for system message
        return messages
    
    # Keep system message + last N exchanges
    system_msg = messages[0]
    recent_exchanges = messages[-(max_exchanges * 2):]
    return [system_msg] + recent_exchanges
```

## Agent Specialization Patterns

### Query Understanding Agent
```python
class QueryUnderstandingAgent:
    async def process(self, state):
        # Analyze query intent and complexity
        analysis = await self.llm.ainvoke([
            SystemMessage(content=QUERY_ANALYSIS_PROMPT),
            HumanMessage(content=state.current_query)
        ])
        
        return AgentResult(
            success=True,
            updated_state={
                "query_analysis": {
                    "intent": analysis.intent,
                    "complexity": analysis.complexity,
                    "entities_mentioned": analysis.entities,
                    "strategy": analysis.recommended_strategy
                }
            }
        )
```

### Tool Planning Agent  
```python
class ToolPlanningAgent:
    async def process(self, state):
        # Create tool execution plan based on query analysis
        query_analysis = state.query_analysis
        
        tool_plan = await self.create_tool_sequence(
            intent=query_analysis.intent,
            complexity=query_analysis.complexity,
            available_tools=self.knowledge_graph_tools.list_tools()
        )
        
        return AgentResult(
            success=True,
            updated_state={"tool_plan": tool_plan}
        )
```

## Error Handling Patterns

### Agent Error Recovery
```python
async def _tool_execution_node(self, state):
    try:
        results = await self.tool_agent.execute_tools(state)
        return Command(goto="response_synthesis", update=results.state)
    
    except ToolExecutionError as e:
        # Graceful degradation
        fallback_results = await self.create_fallback_response(e, state)
        return Command(goto="response_synthesis", update=fallback_results)
    
    except Exception as e:
        # Critical error - end workflow
        return Command(
            goto=END,
            update={"error": f"Tool execution failed: {str(e)}"}
        )
```

### Streaming Error Handling
```python
async def process_query_streaming(self, request):
    try:
        # Start thinking block
        yield self._create_chunk(chat_id, created, model, "<think>\n")
        
        # Process workflow
        async for chunk in self.workflow_processor.stream(request):
            yield self._create_chunk(chat_id, created, model, chunk)
            
    except Exception as e:
        # Error in thinking block
        error_msg = f"\n❌ Error: {str(e)}\n</think>\n\nI encountered an error processing your request."
        yield self._create_chunk(chat_id, created, model, error_msg)
```

## Performance Optimization

### Tool Execution Optimization
```python
# Parallel tool execution when possible
async def execute_parallel_tools(self, tool_specs):
    # Group independent tools
    parallel_groups = self.group_independent_tools(tool_specs)
    
    results = []
    for group in parallel_groups:
        # Execute group in parallel
        group_results = await asyncio.gather(*[
            self.execute_single_tool(tool_spec) 
            for tool_spec in group
        ])
        results.extend(group_results)
    
    return results
```

### Memory Optimization
```python
# Efficient state updates
def update_state_efficiently(state: MultiAgentState, updates: Dict):
    """Update only changed fields to minimize memory usage."""
    new_state = state.copy()
    for key, value in updates.items():
        if key in new_state and new_state[key] != value:
            new_state[key] = value
    return new_state
```

## Integration with Open WebUI

### Open WebUI Compatibility
```python
# Ensure compatibility with Open WebUI expectations
def _create_chunk(self, chat_id: str, created: int, model: str, content: str):
    """Create OpenAI-compatible streaming chunk."""
    chunk = {
        "id": chat_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {"content": content},
            "finish_reason": None
        }]
    }
    return f"data: {json.dumps(chunk)}\n\n"
```

### Metadata Handling
```python
# Include tool usage metadata for Open WebUI
def create_final_chunk_with_metadata(self, response: str, tool_results: List):
    """Create final chunk with tool execution metadata."""
    metadata = {
        "tools_used": [result.tool_name for result in tool_results],
        "execution_time": sum(r.execution_time for r in tool_results),
        "knowledge_graph_queries": len(tool_results)
    }
    
    # Open WebUI can display this metadata
    return {
        "content": response,
        "metadata": metadata
    }
```

## Testing Patterns

### End-to-End Chat Testing
```python
async def test_chat_workflow():
    # Test complete chat flow
    request = ChatCompletionRequest(
        model="political-monitoring-agent",
        messages=[{"role": "user", "content": "What is the EU AI Act?"}],
        stream=True
    )
    
    response_chunks = []
    async for chunk in orchestrator.process_query_streaming(request):
        response_chunks.append(chunk)
    
    # Verify thinking block structure
    full_response = "".join(response_chunks)
    assert "<think>" in full_response
    assert "</think>" in full_response
    assert "EU AI Act" in full_response
```

### Tool Integration Testing
```python
async def test_knowledge_graph_tools():
    # Test tool discovery and execution
    available_tools = knowledge_graph_tools.list_tools()
    assert len(available_tools) == 15
    
    # Test entity search tool
    result = await knowledge_graph_tools.execute_tool(
        "entity_search",
        {"query": "EU AI Act", "limit": 5}
    )
    
    assert result.success
    assert len(result.entities) <= 5
```

## Common Anti-Patterns

❌ **Multiple thinking blocks**:
```python
# DON'T: Create multiple <think> blocks
yield "<think>Step 1</think>"
yield "<think>Step 2</think>"  # Breaks Open WebUI
```

❌ **Fixed routing**:
```python
# DON'T: Hardcode agent sequences
def route_next_agent(state):
    return "tool_planning"  # No flexibility
```

❌ **Raw JSON in reasoning**:
```python
# DON'T: Stream raw state dumps
yield f"<think>{json.dumps(state)}</think>"
```

✅ **Correct patterns**:
```python
# DO: Single continuous thinking stream
yield "<think>\nStep 1: Understanding query...\nStep 2: Planning tools...\n</think>"

# DO: Dynamic routing with Commands
return Command(goto="tool_planning", update=new_state)

# DO: Intelligent reasoning conversion
yield "🔍 Analyzing query intent and identifying relevant entities..."
```