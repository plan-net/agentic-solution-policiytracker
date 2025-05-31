# LangGraph Implementation Patterns

## Overview
This document captures key learnings from implementing a multi-agent system using LangGraph for the Political Monitoring Agent. These patterns emerged from fixing critical issues with fixed routing, poor streaming, and state management.

## Core Architecture Patterns

### ✅ **Pattern 1: Agent Handoffs with Command Objects**

**Problem**: Fixed sequential routing that agents can't control.

```python
# ❌ WRONG: Fixed routing logic
def _determine_next_agent(state):
    if current == "query_understanding":
        return "tool_planning"  # RIGID!
    elif current == "tool_planning":
        return "tool_execution"  # NO FLEXIBILITY!
```

**Solution**: Agents return `Command` objects to control flow.

```python
# ✅ CORRECT: Agent-controlled handoffs
from langgraph.types import Command

async def _query_understanding_node(self, state):
    result = await self.query_agent.process(state)
    
    if result.success:
        # Agent decides next step
        return Command(
            goto="tool_planning",
            update=result.updated_state
        )
    else:
        # Agent can end workflow on failure
        return Command(
            goto=END,
            update=error_state
        )
```

**Key Benefits**:
- Agents make intelligent routing decisions
- Dynamic workflow paths based on results
- Proper error handling and early termination
- Cleaner state management

### ✅ **Pattern 2: Native LangGraph Streaming**

**Problem**: Custom streaming wrapper that dumps raw JSON.

```python
# ❌ WRONG: Custom streaming that dumps state
async for chunk in custom_orchestrator.process_query_with_streaming():
    content = f"<think>\nReceived workflow update: {raw_json_dump}\n</think>\n"
```

**Solution**: Use LangGraph's built-in streaming modes.

```python
# ✅ CORRECT: Native LangGraph streaming
async for chunk in graph.astream(initial_state, stream_mode=["updates", "custom"]):
    if isinstance(chunk, tuple) and len(chunk) == 2:
        mode, data = chunk
        
        if mode == "updates":
            # Convert to intelligent reasoning
            reasoning = await self._convert_update_to_reasoning(data)
            yield self._create_chunk(chat_id, created, model, reasoning)
        
        elif mode == "custom":
            # Direct reasoning from agents using get_stream_writer()
            yield self._create_chunk(chat_id, created, model, data.get("reasoning", ""))
```

#### LangGraph Streaming Modes Explained

```python
# Stream mode options:
stream_mode="values"     # Full state after each step
stream_mode="updates"    # State deltas after each step (RECOMMENDED)
stream_mode="custom"     # User-defined data from get_stream_writer()
stream_mode="messages"   # LLM tokens + metadata
stream_mode="debug"      # Detailed execution traces

# Multiple modes (recommended for agents):
stream_mode=["updates", "custom"]  # Both state updates AND custom reasoning
```

#### Using Custom Streaming in Agent Nodes

```python
from langgraph.config import get_stream_writer

async def _query_understanding_node(self, state):
    # Get the stream writer for custom output
    writer = get_stream_writer()
    
    # Send custom reasoning updates
    writer({"reasoning": "🔍 Starting query analysis...\n"})
    
    result = await self.query_agent.process(state)
    
    if result.success:
        writer({"reasoning": f"✅ Identified {result.intent} with {result.confidence:.0%} confidence\n"})
        return Command(goto="tool_planning", update=result.updated_state)
    else:
        writer({"reasoning": f"❌ Query analysis failed: {result.error}\n"})
        return Command(goto=END, update=error_state)
```

#### Complete Streaming Setup

```python
# 1. Initialize graph with streaming
graph = StateGraph(MultiAgentState)
graph.add_node("agent1", self._agent_node)
compiled_graph = graph.compile(checkpointer=checkpointer)

# 2. Stream with multiple modes
async for chunk in compiled_graph.astream(
    initial_state, 
    config={"configurable": {"thread_id": session_id}},
    stream_mode=["updates", "custom"]
):
    # Handle different streaming modes
    if isinstance(chunk, tuple):
        mode, data = chunk
        
        if mode == "updates":
            # Process state updates
            for node_name, node_state in data.items():
                reasoning = convert_node_update_to_reasoning(node_name, node_state)
                yield reasoning
        
        elif mode == "custom":
            # Direct custom output from agents
            yield data.get("reasoning", "")
    
    else:
        # Single mode output (fallback)
        reasoning = convert_update_to_reasoning(chunk)
        yield reasoning
```

**Key Benefits**:
- Single continuous thinking stream
- No multiple `<think>` blocks
- Intelligent reasoning instead of JSON dumps
- Better Open WebUI compatibility

### ✅ **Pattern 3: Intelligent State Updates to Reasoning**

**Problem**: Raw state dumps are unreadable.

```python
# ❌ WRONG: Dumping raw state
content = f"<think>\nState update: {raw_state_dict}\n</think>\n"
```

**Solution**: Convert state updates to narrative reasoning.

```python
# ✅ CORRECT: Intelligent reasoning conversion
async def _convert_update_to_reasoning(self, data: Dict[str, Any]) -> str:
    reasoning_parts = []
    
    for node_name, node_state in data.items():
        if node_name == "query_understanding" and "query_analysis" in node_state:
            analysis = node_state["query_analysis"]
            reasoning_parts.append(
                f"🔍 Understanding Query: Identified '{analysis.get('intent')}' intent "
                f"with {analysis.get('confidence', 0):.0%} confidence. "
                f"Primary focus: {analysis.get('primary_entity')}. "
                f"Strategy: {analysis.get('analysis_strategy')}.\n"
            )
        
        elif node_name == "tool_planning" and "tool_plan" in node_state:
            plan = node_state["tool_plan"]
            tools = plan.get("tool_sequence", [])
            reasoning_parts.append(
                f"📋 Planning Execution: Designed {plan.get('strategy_type')} strategy "
                f"with {len(tools)} tools. "
                f"Tools: {', '.join(t.get('tool_name') for t in tools)}.\n"
            )
    
    return "".join(reasoning_parts)
```

**Key Benefits**:
- Readable reasoning output
- User-friendly progress updates
- Professional thinking narrative
- Better user experience

### ✅ **Pattern 4: Single Thinking Block Architecture**

**Problem**: Multiple `<think>` blocks break Open WebUI.

```python
# ❌ WRONG: Multiple thinking blocks
yield "<think>\nStep 1\n</think>\n"
yield "<think>\nStep 2\n</think>\n"  # BREAKS UI!
```

**Solution**: One continuous thinking stream.

```python
# ✅ CORRECT: Single continuous thinking
# Start thinking block
yield self._create_chunk(chat_id, created, model, "<think>\nAnalyzing query...\n\n")

# Stream reasoning updates (NO new <think> tags)
async for chunk in graph.astream(...):
    reasoning = await self._convert_update_to_reasoning(chunk)
    yield self._create_chunk(chat_id, created, model, reasoning)

# Close thinking and provide response
yield self._create_chunk(chat_id, created, model, "\nAnalysis complete.\n</think>\n\n")
yield self._create_chunk(chat_id, created, model, final_response)
```

**Key Benefits**:
- Open WebUI compatibility
- Proper response timing tracking
- Clean user experience
- No UI duplication issues

### ✅ **Pattern 5: Simplified Graph Structure**

**Problem**: Complex routing nodes and conditional edges.

```python
# ❌ WRONG: Complex routing with many nodes
graph.add_node("route_next", self._route_next_agent)
graph.add_conditional_edges(
    "route_next",
    self._determine_next_agent,
    {"tool_planning": "tool_planning", "end": END}
)
```

**Solution**: Direct agent nodes with Command handoffs.

```python
# ✅ CORRECT: Simple graph with Command handoffs
graph = StateGraph(MultiAgentState)

# Add only agent nodes - they control flow
graph.add_node("query_understanding", self._query_understanding_node)
graph.add_node("tool_planning", self._tool_planning_node)
graph.add_node("tool_execution", self._tool_execution_node)
graph.add_node("response_synthesis", self._response_synthesis_node)

# Single entry point - agents handle routing
graph.add_edge(START, "query_understanding")

return graph.compile(checkpointer=self.checkpointer)
```

**Key Benefits**:
- Cleaner graph structure
- Less complex routing logic
- Agent autonomy in decisions
- Easier debugging and maintenance

## Anti-Patterns to Avoid

### ❌ **Anti-Pattern 1: Fixed Sequential Routing**
Don't hardcode agent sequences. Let agents decide next steps based on results.

### ❌ **Anti-Pattern 2: Custom Streaming Wrappers**
Don't build custom streaming on top of LangGraph. Use native streaming modes.

### ❌ **Anti-Pattern 3: Raw State Dumps**
Don't stream raw JSON/dict state. Convert to intelligent reasoning.

### ❌ **Anti-Pattern 4: Multiple Thinking Blocks**
Don't create multiple `<think>` blocks. Use one continuous stream.

### ❌ **Anti-Pattern 5: Over-Complex Routing**
Don't add many routing nodes. Let agents control flow with Commands.

## Debugging Patterns

### Debug with Native Streaming
```python
# Test with debug mode to see full execution
async for chunk in graph.astream(initial_state, stream_mode="debug"):
    print(f"Debug: {chunk}")
```

### Troubleshooting Streaming Issues

#### Issue 1: No Streaming Output
```python
# Problem: Stream seems empty
async for chunk in graph.astream(initial_state, stream_mode="updates"):
    print("Never prints")

# Solution: Check if nodes actually update state
async def _agent_node(self, state):
    # ❌ Wrong: No state update
    return state
    
    # ✅ Correct: Return Command with state update
    return Command(goto="next_agent", update={"new_field": "value"})
```

#### Issue 2: get_stream_writer() Not Working
```python
# Problem: writer = get_stream_writer() fails

# Solution 1: Use correct stream mode
async for chunk in graph.astream(initial_state, stream_mode=["custom"]):  # Need "custom"
    
# Solution 2: Check Python version (< 3.11 has issues)
# For Python < 3.11, pass writer manually:
async def _agent_node(self, state, config):
    writer = config.get("stream_writer")  # Manual injection
```

#### Issue 3: Wrong Chunk Format
```python
# Problem: Chunks don't match expected format
async for chunk in graph.astream(..., stream_mode=["updates", "custom"]):
    # Sometimes tuple, sometimes dict
    
# Solution: Handle both formats
if isinstance(chunk, tuple) and len(chunk) == 2:
    mode, data = chunk
    # Handle multi-mode output
else:
    # Handle single-mode output
    data = chunk
```

#### Issue 4: Empty Custom Streams
```python
# Problem: Custom stream mode returns empty
writer = get_stream_writer()
writer("some data")  # Nothing appears in stream

# Solution: Use dict format for custom data
writer({"reasoning": "some data", "type": "thinking"})
```

### Test State Progression
```python
# Verify each agent updates state correctly
final_state = await graph.aget_state(thread_config)
assert "query_analysis" in final_state.values
assert "tool_plan" in final_state.values
assert "final_response" in final_state.values
```

### Validate Agent Handoffs
```python
# Ensure Commands are returned properly
result = await agent_node(test_state)
assert isinstance(result, Command)
assert result.goto in ["next_agent", END]
```

## Performance Considerations

### Streaming Responsiveness
- Use `stream_mode=["updates", "custom"]` for real-time progress
- Convert state updates immediately to avoid blocking
- Send reasoning incrementally, not in large chunks

### Memory Management
- Use LangGraph's built-in checkpointing for state persistence
- Don't accumulate large state objects unnecessarily
- Clean up temporary data between agents

### Error Handling
- Agents should handle their own errors and decide on handoffs
- Use Commands to route to END on critical failures
- Provide meaningful error messages in reasoning stream

## Integration with External Systems

### OpenAI API Compatibility
```python
def _create_chunk(self, chat_id: str, created: int, model: str, content: str) -> str:
    """Create OpenAI-compatible streaming chunk."""
    chunk = StreamResponse(
        id=chat_id,
        created=created,
        model=model,
        choices=[StreamChoice(index=0, delta={"content": content})]
    )
    return f"data: {chunk.model_dump_json()}\n\n"
```

### Knowledge Graph Integration
- Use proper tool integration managers
- Stream tool execution progress through custom mode
- Handle tool failures gracefully in agent logic

## Testing Strategies

### Unit Testing Agents
```python
async def test_agent_handoff():
    result = await query_understanding_node(test_state)
    assert isinstance(result, Command)
    assert result.goto == "tool_planning"
    assert "query_analysis" in result.update
```

### Integration Testing Workflow
```python
async def test_complete_workflow():
    final_state = None
    async for chunk in graph.astream(initial_state):
        final_state = chunk
    
    assert final_state.get("final_response")
    assert not final_state.get("errors")
```

### Streaming Testing
```python
async def test_streaming_format():
    chunks = []
    async for chunk in graph.astream(initial_state, stream_mode="updates"):
        reasoning = await convert_update_to_reasoning(chunk)
        chunks.append(reasoning)
    
    # Verify no JSON dumps in reasoning
    for chunk in chunks:
        assert not chunk.startswith("{")
        assert "🔍" in chunk or "📋" in chunk  # Expected emojis
```

## Best Practices Summary

1. **Use Command handoffs** instead of fixed routing
2. **Leverage native LangGraph streaming** with proper modes
3. **Convert state to intelligent reasoning** for user experience
4. **Maintain single continuous thinking stream** for UI compatibility
5. **Keep graph structure simple** and let agents control flow
6. **Test agent handoffs and state progression** thoroughly
7. **Handle errors gracefully** with meaningful user feedback
8. **Optimize for streaming responsiveness** and memory usage

## Common Gotchas

- **Missing `Command` import**: Always import from `langgraph.types`
- **Wrong stream mode**: Use `["updates", "custom"]` for comprehensive streaming
- **State mutation**: Always return new state objects, don't mutate in place
- **Async context**: Ensure proper async/await usage throughout
- **Tool integration**: Set up tool managers properly in agent constructors

## Future Enhancements

- **Conditional agent routing**: Agents could skip steps based on confidence
- **Parallel agent execution**: Some agents could run concurrently
- **Dynamic tool selection**: Agents could choose tools based on context
- **Adaptive streaming**: Adjust reasoning detail based on user preferences
- **Error recovery**: Agents could retry with different strategies

---

**Status**: Production-ready patterns validated with Political Monitoring Agent
**Last Updated**: 2025-05-31
**Version**: 1.0