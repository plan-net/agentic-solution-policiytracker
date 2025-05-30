# Multi-Agent LangGraph Implementation Plan

## Overview

Replace the current LangGraph implementation with a proper multi-agent system using `create_react_agent()` for each specialized agent. Each agent will have its own optimized prompts and clear responsibilities, following LangGraph best practices for multi-agent systems, advanced streaming capabilities, and memory management.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Query           │───▶│ Tool Planning   │───▶│ Tool Execution  │───▶│ Response        │
│ Understanding   │    │ Agent           │    │ Agent           │    │ Synthesis Agent │
│ Agent           │    │                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Agent Specifications

### Agent 1: Query Understanding Agent
- **Purpose**: Analyze user queries for intent, entities, complexity, and temporal scope
- **Tools**: None (pure LLM analysis)
- **Input**: Raw user query + session context
- **Output**: Structured query analysis (intent, entities, complexity, temporal_scope)
- **Prompt Focus**: Intent classification, entity extraction, regulatory domain understanding
- **Streaming**: Custom thinking about query analysis process
- **Memory**: Access to user preferences and conversation history

### Agent 2: Tool Planning Agent
- **Purpose**: Create optimal tool execution strategy based on query analysis
- **Tools**: None (pure planning logic) 
- **Input**: Query analysis results + conversation context
- **Output**: Structured tool execution plan (tool_sequence, strategy, expected_results)
- **Prompt Focus**: Strategic tool selection, optimization for political/regulatory analysis
- **Streaming**: Custom thinking about strategy selection and reasoning
- **Memory**: Learn from previous successful tool combinations

### Agent 3: Tool Execution Agent
- **Purpose**: Execute planned tools and gather comprehensive data
- **Tools**: All 16 political analysis tools (search, entity, traverse, temporal, community)
- **Input**: Tool execution plan + query context
- **Output**: Raw tool results and findings
- **Prompt Focus**: Efficient tool usage, data quality assessment, iterative refinement
- **Streaming**: Real-time LLM tokens + custom progress updates during tool execution
- **Memory**: Track tool performance and user preferences

### Agent 4: Response Synthesis Agent
- **Purpose**: Combine all results into comprehensive, well-formatted responses
- **Tools**: None (pure synthesis)
- **Input**: All tool results + original query + user preferences
- **Output**: Final formatted response with sources
- **Prompt Focus**: Result integration, source attribution, insight highlighting
- **Streaming**: Custom thinking about synthesis process + real-time response generation
- **Memory**: User response format preferences, citation styles

## Implementation Plan - Test-Driven Approach

### Phase 1: Foundation & Testing Infrastructure

#### Task 1.1: Create Agent Base Classes and Interfaces
- [ ] Create `BaseAgent` interface with standard methods
- [ ] Define `AgentResult` data structures for inter-agent communication
- [ ] Create `MultiAgentState` schema extending `MessagesState` with memory support
- [ ] Setup memory management interfaces (short-term + long-term)
- [ ] Create streaming interfaces with `get_stream_writer()` support
- [ ] Write unit tests for base classes

**Files to create/modify:**
- `src/chat/agent/base.py` - Base agent interface
- `src/chat/agent/state.py` - Update state schema for multi-agent with memory
- `src/chat/agent/memory.py` - Memory management interfaces
- `src/chat/agent/streaming.py` - Streaming utilities and interfaces
- `tests/unit/test_agent_base.py` - Base class tests
- `tests/unit/test_memory_management.py` - Memory system tests

#### Task 1.2: Adapt Existing Prompt Templates for Multi-Agent System
- [ ] **Review existing prompts**: Analyze current chat prompts for reusability
  - `understand_query.md` → Query Understanding Agent
  - `plan_exploration.md` → Tool Planning Agent  
  - `agent_system.md` → Tool Execution Agent (needs enhancement)
  - `format_response.md` → Response Synthesis Agent
  - `evaluate_results.md` → Can be integrated into Tool Execution Agent
- [ ] **Enhance existing prompts** for multi-agent context:
  - Add streaming directives using `get_stream_writer()`
  - Add memory context integration
  - Update for `create_react_agent()` usage
  - Add handoff logic and inter-agent communication
- [ ] **Create missing prompts** for new capabilities:
  - Tool execution prompt with 16 political analysis tools
  - Memory-aware prompt templates
  - Streaming-specific prompt enhancements
- [ ] Write tests for prompt loading, validation, and adaptation

**Files to enhance/create:**
- `src/prompts/chat/understand_query.md` - Enhance for streaming + memory
- `src/prompts/chat/plan_exploration.md` - Enhance for 16 political tools
- `src/prompts/chat/tool_execution.md` - NEW: Based on agent_system.md
- `src/prompts/chat/format_response.md` - Enhance for memory context
- `src/prompts/chat/agent_handoffs.md` - NEW: Inter-agent communication
- `tests/unit/test_adapted_prompts.py` - Test enhanced prompts

#### Task 1.3: Create Mock Testing Framework
- [ ] Create mock agents for testing inter-agent communication
- [ ] Create test fixtures for agent inputs/outputs
- [ ] Create integration test framework for multi-agent flows
- [ ] Write handoff testing utilities

**Files to create:**
- `tests/fixtures/agent_fixtures.py`
- `tests/unit/test_agent_communication.py`
- `tests/integration/test_multi_agent_flow.py`

### Phase 2: Individual Agent Implementation

#### Task 2.1: Query Understanding Agent
- [ ] **Test First**: Write tests for query analysis functionality
  - Test intent classification (Information lookup, Relationship analysis, Impact analysis, Temporal analysis)
  - Test entity extraction from political/regulatory text
  - Test complexity assessment (simple, medium, complex)
  - Test temporal scope detection
- [ ] Implement `QueryUnderstandingAgent` using `create_react_agent()`
- [ ] Create structured output schema for query analysis
- [ ] Optimize prompt for political domain understanding
- [ ] Test with real political queries

**Files to create:**
- `src/chat/agent/query_understanding.py`
- `tests/unit/test_query_understanding_agent.py`
- Integration with existing prompt manager

#### Task 2.2: Tool Planning Agent  
- [ ] **Test First**: Write tests for tool planning logic
  - Test strategy selection based on query analysis
  - Test tool sequence optimization
  - Test planning for different complexity levels
  - Test tool combination strategies
- [ ] Implement `ToolPlanningAgent` using `create_react_agent()`
- [ ] Create tool planning strategies (simple, comprehensive, analytical)
- [ ] Implement dynamic tool selection logic
- [ ] Test planning optimization

**Files to create:**
- `src/chat/agent/tool_planning.py`
- `tests/unit/test_tool_planning_agent.py`

#### Task 2.3: Tool Execution Agent
- [ ] **Test First**: Write tests for tool execution
  - Test individual tool execution
  - Test tool sequence execution
  - Test error handling and fallbacks
  - Test result aggregation
- [ ] Implement `ToolExecutionAgent` using `create_react_agent()`
- [ ] Integrate all 16 existing political analysis tools
- [ ] Implement execution monitoring and error recovery
- [ ] Add result quality assessment
- [ ] Test with real knowledge graph data

**Files to create:**
- `src/chat/agent/tool_execution.py`
- `tests/unit/test_tool_execution_agent.py`
- `tests/integration/test_tool_execution_real_data.py`

#### Task 2.4: Response Synthesis Agent
- [ ] **Test First**: Write tests for response synthesis
  - Test result integration from multiple tools
  - Test source attribution and citation formatting
  - Test insight highlighting and relationship explanation
  - Test response quality and completeness
- [ ] Implement `ResponseSynthesisAgent` using `create_react_agent()`
- [ ] Create response templates and formatting logic
- [ ] Implement source tracking and citation generation
- [ ] Add insight extraction and highlighting
- [ ] Test response quality

**Files to create:**
- `src/chat/agent/response_synthesis.py`
- `tests/unit/test_response_synthesis_agent.py`

### Phase 3: Multi-Agent Orchestration

#### Task 3.1: Agent Communication & Handoffs
- [ ] **Test First**: Write tests for agent handoffs
  - Test `Command` object creation and routing
  - Test state passing between agents
  - Test error propagation and handling
  - Test handoff decision logic
- [ ] Implement handoff tools using `Command` objects
- [ ] Create agent routing logic
- [ ] Implement state management between agents
- [ ] Test complete handoff chains

**Files to create:**
- `src/chat/agent/handoffs.py`
- `tests/unit/test_agent_handoffs.py`

#### Task 3.2: Multi-Agent Graph Construction
- [ ] **Test First**: Write tests for graph construction
  - Test graph node creation with agents
  - Test edge configuration and routing
  - Test state flow through the graph
  - Test error handling in graph execution
- [ ] Build the multi-agent `StateGraph`
- [ ] Configure agent nodes and handoff edges
- [ ] Implement conditional routing if needed
- [ ] Test graph compilation and execution

**Files to create:**
- `src/chat/agent/multi_agent_graph.py`
- `tests/unit/test_multi_agent_graph.py`

#### Task 3.3: Main Multi-Agent Orchestrator
- [ ] **Test First**: Write tests for the main orchestrator
  - Test end-to-end query processing
  - Test streaming capability integration
  - Test session context handling
  - Test error recovery and fallbacks
- [ ] Implement `MultiAgentPoliticalMonitoringSystem`
- [ ] Integrate streaming capabilities with thinking output
- [ ] Add session management and context handling
- [ ] Implement monitoring and logging

**Files to create:**
- `src/chat/agent/multi_agent_system.py`
- `tests/unit/test_multi_agent_system.py`

### Phase 4: Advanced Streaming & Memory Management

#### Task 4.1: Advanced Streaming Integration
- [ ] **Test First**: Write comprehensive streaming tests
  - Test multi-mode streaming (`["updates", "custom", "messages"]`)
  - Test `get_stream_writer()` integration in each agent
  - Test real-time LLM token streaming from tool execution
  - Test custom thinking output during agent transitions
  - Test node-specific streaming filtering
  - Test streaming performance under load
- [ ] Implement advanced streaming system for multi-agent workflow
- [ ] Add real-time LLM token streaming from tool execution agent
- [ ] Create sophisticated thinking output using `get_stream_writer()`
- [ ] Implement progress indicators and agent transition notifications
- [ ] Add streaming error handling and fallbacks
- [ ] Test comprehensive streaming user experience

**Files to create/modify:**
- `src/chat/agent/streaming.py` - Advanced streaming system
- `src/chat/agent/stream_handlers.py` - Streaming event handlers
- `tests/unit/test_advanced_streaming.py` - Streaming system tests
- `tests/integration/test_streaming_performance.py` - Performance tests

#### Task 4.2: Memory Management System
- [ ] **Test First**: Write memory management tests
  - Test short-term memory (conversation history)
  - Test long-term memory (user preferences, learned patterns)
  - Test message trimming and summarization
  - Test memory persistence across sessions
  - Test memory-aware agent behavior
- [ ] Implement short-term memory with `InMemorySaver` checkpointer
- [ ] Implement long-term memory with `InMemoryStore` 
- [ ] Add conversation history trimming using `trim_messages()`
- [ ] Implement message summarization for long conversations
- [ ] Create user preference storage and retrieval
- [ ] Add memory-aware prompt templates for each agent
- [ ] Test memory integration with multi-agent workflow

**Files to create:**
- `src/chat/agent/memory.py` - Memory management system
- `src/chat/agent/memory_stores.py` - Custom memory store implementations
- `src/chat/agent/summarization.py` - Conversation summarization
- `tests/unit/test_memory_system.py` - Memory tests
- `tests/integration/test_memory_persistence.py` - Persistence tests

#### Task 4.3: Update Server Integration
- [ ] **Test First**: Write tests for server integration
  - Test OpenAI-compatible API endpoint updates
  - Test advanced streaming response formatting (multi-mode)
  - Test memory persistence across requests
  - Test session management with thread_id
  - Test error handling in server context
- [ ] Update `src/chat/server/app.py` to use new multi-agent system
- [ ] Integrate memory management (checkpointer + store)
- [ ] Add advanced streaming endpoint with multi-mode support
- [ ] Maintain backward compatibility with existing API
- [ ] Add session management for memory persistence
- [ ] Test server integration with real requests

**Files to modify:**
- `src/chat/server/app.py` - Enhanced with memory and streaming
- `tests/integration/test_chat_server.py` - Updated server tests
- `tests/integration/test_server_memory.py` - Memory persistence tests

### Phase 5: Integration & Optimization

#### Task 5.1: End-to-End Integration Testing
- [ ] **Test First**: Create comprehensive integration tests
  - Test complete user journey from query to response
  - Test with various query types and complexities
  - Test performance under load
  - Test memory usage and optimization
- [ ] Run integration tests with real knowledge graph data
- [ ] Performance testing and optimization
- [ ] Memory usage analysis and optimization

**Files to create:**
- `tests/integration/test_end_to_end_multi_agent.py`
- `tests/performance/test_multi_agent_performance.py`

#### Task 5.2: Documentation & Examples
- [ ] Create multi-agent system documentation
- [ ] Add usage examples for different query types
- [ ] Create troubleshooting guide
- [ ] Update API documentation

**Files to create:**
- `docs/multi-agent-system.md`
- `docs/examples/multi-agent-queries.md`

#### Task 5.3: Migration & Deployment
- [ ] Create migration guide from current system
- [ ] Update deployment configuration
- [ ] Create rollback plan
- [ ] Test deployment in staging environment

## Testing Strategy

### Unit Tests (Per Agent)
- **Input validation**: Test each agent with valid/invalid inputs
- **Output validation**: Test structured outputs match expected schemas
- **Error handling**: Test graceful failure and error propagation
- **Prompt effectiveness**: Test agent responses to various inputs

### Integration Tests (Agent Communication)
- **Handoff testing**: Test state passing between agents
- **End-to-end flows**: Test complete query processing
- **Error recovery**: Test system behavior when agents fail
- **Performance**: Test response times and resource usage

### Acceptance Tests (User Journey)
- **Query variety**: Test with different political/regulatory query types
- **Response quality**: Test accuracy and comprehensiveness
- **User experience**: Test streaming and interaction quality
- **Real data**: Test with actual knowledge graph content

## Success Criteria

### Functional Requirements
- [ ] Each agent successfully handles its specialized role with optimized prompts
- [ ] Agent handoffs work seamlessly with proper state management
- [ ] System maintains or improves response quality vs current implementation
- [ ] Advanced streaming provides excellent user experience (thinking + tokens + progress)
- [ ] Memory system enhances conversations and learns user preferences
- [ ] System handles errors gracefully with appropriate fallbacks
- [ ] Multi-mode streaming works reliably (`updates`, `custom`, `messages`)

### Performance Requirements
- [ ] Response time ≤ 30 seconds for complex queries
- [ ] Memory usage ≤ 2GB during operation including memory stores
- [ ] System supports concurrent users (≥5 simultaneous queries) with session isolation
- [ ] 95% of queries complete successfully
- [ ] Streaming latency ≤ 100ms for real-time updates
- [ ] Memory operations (save/retrieve) ≤ 50ms

### Quality Requirements
- [ ] Responses include proper source citations with memory-enhanced context
- [ ] Political/regulatory insights are accurate and relevant
- [ ] System handles edge cases gracefully
- [ ] Logging and monitoring provide good observability
- [ ] Memory system preserves user preferences accurately
- [ ] Conversation summarization maintains context quality

### Memory Requirements
- [ ] Short-term memory preserves conversation context within sessions
- [ ] Long-term memory stores and retrieves user preferences across sessions
- [ ] Message trimming prevents context window overflow
- [ ] Conversation summarization maintains quality for long conversations
- [ ] Memory persistence survives system restarts
- [ ] Session isolation prevents data leakage between users

### Streaming Requirements
- [ ] Real-time thinking output engages users during processing
- [ ] LLM token streaming provides immediate feedback during synthesis
- [ ] Progress indicators show clear agent transition states
- [ ] Custom streaming data provides meaningful insights
- [ ] Multi-mode streaming coordination works seamlessly
- [ ] Streaming error handling maintains user experience

## Migration Plan

### Phase A: Parallel Implementation
- Implement new multi-agent system alongside current system
- A/B testing framework for comparison
- Gradual user migration

### Phase B: Feature Parity
- Ensure new system matches all current functionality
- Performance optimization
- Bug fixes and improvements

### Phase C: Full Migration
- Switch default implementation to multi-agent system
- Remove old implementation
- Update documentation and deployment

## Future Extensibility

This architecture enables future enhancements:
- **Additional agents**: Domain-specific analysis agents
- **Dynamic routing**: AI-powered agent selection
- **Human-in-the-loop**: Approval workflows between agents
- **Multi-turn conversations**: Session-aware agent interactions
- **Custom workflows**: User-configurable agent chains

## Risk Mitigation

### Technical Risks
- **Complexity**: Start with simple handoffs, add sophistication gradually
- **Performance**: Implement caching and optimization from the start
- **Debugging**: Comprehensive logging and state tracking

### Quality Risks  
- **Response degradation**: Extensive testing and comparison with current system
- **Agent specialization**: Clear role definitions and prompt optimization
- **Error propagation**: Robust error handling at each agent level

## Timeline Estimate

- **Phase 1 (Foundation + Memory/Streaming Setup)**: 4-5 days
- **Phase 2 (Individual Agents with Streaming)**: 6-8 days  
- **Phase 3 (Multi-Agent Orchestration)**: 4-5 days
- **Phase 4 (Advanced Streaming + Memory Integration)**: 4-5 days
- **Phase 5 (Integration + Optimization)**: 3-4 days

**Total Estimate**: 21-27 days

### Detailed Breakdown
- **Memory system implementation**: +3 days
- **Advanced streaming with multi-mode**: +4 days  
- **Enhanced agent prompts and testing**: +2 days
- **Integration complexity**: +1 day

## Dependencies

- LangGraph prebuilt agents (`create_react_agent`)
- Existing tool implementations (16 political analysis tools)
- Existing prompt management system
- Existing knowledge graph infrastructure
- Current testing framework