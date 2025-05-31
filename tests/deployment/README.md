# Deployment Integration Test Strategy

## Overview

This test suite validates the complete multi-agent system in a deployed state with real LLM and knowledge graph components. Unlike unit/integration tests that use mocks, these tests exercise the full system end-to-end.

## Test Philosophy

### Real Components Only
- **Real LLM**: OpenAI API calls with actual token usage
- **Real Knowledge Graph**: Live Graphiti + Neo4j with actual data
- **Real Ray Serve**: Deployed chat server with proper networking
- **Real Streaming**: WebSocket/SSE connections with timing validation

### Systematic Coverage
1. **Agent Orchestration**: Validate 4-agent workflow with state transitions
2. **Tool Integration**: Test all 15 knowledge graph tools with real queries
3. **Quality Assessment**: Validate response quality evaluation system
4. **Error Scenarios**: Test graceful degradation and recovery
5. **Performance**: Validate response times and resource usage

### Test Structure
```
tests/deployment/
├── README.md                    # This file
├── conftest.py                  # Deployment-specific fixtures
├── test_ray_deployment.py       # Ray Serve deployment validation
├── test_multi_agent_workflow.py # End-to-end agent orchestration
├── test_knowledge_graph_tools.py # Tool integration validation
├── test_streaming_responses.py  # Streaming and progress updates
├── test_error_scenarios.py      # Error handling and recovery
├── test_performance_metrics.py  # Performance and scaling validation
└── scenarios/                   # Test scenario definitions
    ├── basic_queries.yaml
    ├── complex_analysis.yaml
    ├── temporal_queries.yaml
    └── error_conditions.yaml
```

## Positioning in Test Suite

### Integration with Existing Tests
- **Unit Tests** (`tests/unit/`): Mock external dependencies, fast execution
- **Integration Tests** (`tests/integration/`): Mixed real/mock components, medium speed  
- **Deployment Tests** (`tests/deployment/`): Real components only, slow execution

### Test Execution Strategy
```bash
# Development cycle (fast feedback)
just test-unit

# Feature validation (moderate feedback)  
just test-integration

# Pre-production validation (comprehensive)
just test-deployment

# Full validation (complete confidence)
just test-all
```

### CI/CD Integration
- **PR Checks**: Unit + Integration tests only
- **Merge to Main**: Add deployment test subset (critical paths)
- **Release Validation**: Full deployment test suite
- **Nightly**: Complete test suite with performance benchmarking

## Test Categories

### 1. Ray Serve Deployment Validation
**Purpose**: Ensure the chat server deploys correctly and responds to health checks

**Tests**:
- Ray Serve startup and deployment
- Health endpoint availability
- OpenAI API compatibility  
- Model endpoint registration
- Resource allocation validation

### 2. Multi-Agent Workflow Validation
**Purpose**: Validate the 4-agent orchestration works end-to-end

**Tests**:
- Query Understanding Agent: Intent classification and entity extraction
- Tool Planning Agent: Intelligent tool selection based on query analysis
- Tool Execution Agent: Knowledge graph tool execution with real data
- Response Synthesis Agent: Comprehensive response generation
- State transitions and conditional routing
- Session management and conversation context

### 3. Knowledge Graph Tool Integration
**Purpose**: Test all 15 tools with real Graphiti data

**Test Matrix**:
```
Query Intent | Tools Tested | Expected Behavior
-------------|-------------|------------------
Information Seeking | search, get_entity_details | Rich entity information
Relationship Analysis | find_paths_between_entities, get_entity_relationships | Connection mapping
Temporal Analysis | get_entity_timeline, track_policy_evolution | Historical progression
Impact Analysis | analyze_entity_impact, get_communities | Influence networks
```

### 4. Streaming Response Validation
**Purpose**: Ensure real-time agent progress updates work correctly

**Tests**:
- OpenAI-compatible streaming format
- Agent transition notifications
- Tool execution progress updates
- Thinking output with `<think>` tags
- Final response delivery
- Stream error handling

### 5. Error Scenario Testing
**Purpose**: Validate graceful degradation and recovery

**Error Conditions**:
- Neo4j connection failures
- OpenAI API rate limits/errors
- Malformed queries
- Tool execution timeouts
- Memory/resource constraints
- Partial tool failures

### 6. Performance and Quality Metrics
**Purpose**: Ensure system meets performance requirements

**Metrics**:
- End-to-end response time (target: <45 seconds)
- Agent execution times (individual and total)
- Tool selection accuracy
- Response quality scores (target: >0.8)
- Memory usage patterns
- Concurrent request handling

## Test Data Strategy

### Knowledge Graph Content
- **Static Test Data**: Curated policy documents with known entities/relationships
- **Live Data**: Current knowledge graph state (evolves over time)
- **Validation Approach**: Flexible assertions that adapt to data evolution

### Query Test Cases
- **Basic Queries**: Simple information lookup ("What is GDPR?")
- **Complex Analysis**: Multi-entity relationships ("How does EU AI Act affect US companies?")
- **Temporal Queries**: Evolution tracking ("How has data protection evolved since GDPR?")
- **Edge Cases**: Ambiguous queries, missing entities, complex relationships

## Success Criteria

### Functional Requirements
- ✅ All 4 agents execute in correct sequence
- ✅ Tool selection matches query intent and complexity
- ✅ Knowledge graph tools return relevant, structured data
- ✅ Responses include proper source citations
- ✅ Streaming works with proper agent progress updates
- ✅ Error scenarios gracefully degrade without system failure

### Quality Requirements  
- ✅ Response quality scores average >0.8
- ✅ Entity extraction accuracy >90% for political entities
- ✅ Tool selection precision >85% (tools contribute to final response)
- ✅ Source attribution >95% (facts linked to original documents)

### Performance Requirements
- ✅ Simple queries: <15 seconds end-to-end
- ✅ Complex queries: <45 seconds end-to-end  
- ✅ Streaming latency: <2 seconds for first agent update
- ✅ Memory usage: <4GB per concurrent request
- ✅ Concurrent requests: Support 5+ simultaneous users

## Test Execution Plan

### Phase 1: Basic Deployment Validation
1. Deploy Ray Serve with chat server
2. Validate health endpoints and basic connectivity
3. Test simple non-streaming requests
4. Verify component initialization (LLM, Graphiti, tools)

### Phase 2: Agent Workflow Validation
1. Test each agent individually with known inputs
2. Validate agent-to-agent state transitions
3. Test conditional routing logic
4. Verify memory and session handling

### Phase 3: Tool Integration Testing
1. Test each tool category with representative queries
2. Validate tool selection algorithms
3. Test parallel tool execution
4. Verify result aggregation and formatting

### Phase 4: Streaming and Real-time Features
1. Test streaming response format
2. Validate agent progress updates
3. Test thinking output generation
4. Verify real-time error reporting

### Phase 5: Error Handling and Edge Cases
1. Test component failure scenarios
2. Validate recovery mechanisms
3. Test malformed input handling
4. Verify resource constraint handling

### Phase 6: Performance and Scale Testing
1. Measure response times under load
2. Test concurrent request handling
3. Validate memory usage patterns
4. Benchmark quality metrics

## Execution Environment

### Prerequisites
- Neo4j running with test data
- OpenAI API key with sufficient quota
- Ray cluster or local Ray installation
- Network connectivity for all components

### Environment Setup
```bash
# Start required services
just services-up

# Deploy chat server to Ray
ray serve run src.chat.server.app:chat_app

# Verify deployment
curl http://localhost:8001/health

# Run deployment test suite
pytest tests/deployment/ -v --tb=short
```

### Test Configuration
```yaml
# tests/deployment/config.yaml
deployment:
  ray_address: "localhost:8001"
  health_timeout: 30
  response_timeout: 60
  concurrent_users: 3

testing:
  openai_model: "gpt-4o-mini"
  max_retries: 3
  quality_threshold: 0.8
  performance_threshold: 45  # seconds
```

## Maintenance and Evolution

### Data Evolution Handling
- **Flexible Assertions**: Check for entity types rather than specific entities
- **Content Validation**: Verify response structure and quality, not exact content
- **Baseline Updates**: Periodically update expected behaviors as data evolves

### Performance Monitoring
- **Trend Analysis**: Track performance metrics over time
- **Regression Detection**: Alert on significant performance degradations
- **Capacity Planning**: Use metrics to predict scaling needs

### Test Suite Evolution
- **New Feature Integration**: Add tests for new agents/tools
- **Query Pattern Updates**: Reflect real user query patterns
- **Quality Improvements**: Enhance assertions based on production learnings

---

This deployment test strategy ensures comprehensive validation of the multi-agent system while accounting for the dynamic nature of the knowledge graph and the need for real-world performance validation.