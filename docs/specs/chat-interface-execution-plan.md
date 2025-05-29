# Chat Interface Execution Plan

## Overview
Implementation plan for adding a conversational AI interface to the Political Monitoring Agent, enabling users to explore the Neo4j/Graphiti knowledge graph through natural language queries.

## Architecture Summary
- **Frontend**: Open WebUI (external)
- **Backend**: Ray Serve API endpoint
- **Agent**: LangChain + LangGraph ReAct agent
- **Data Layer**: Direct Graphiti client (no wrapper)
- **Memory**: LangChain session memory
- **Tools**: Graphiti search capabilities as LangGraph tools

## Folder Structure

```
src/
├── chat/                           # New chat interface module
│   ├── __init__.py
│   ├── agent/                      # LangGraph agent implementation
│   │   ├── __init__.py
│   │   ├── graph.py               # Main agent graph definition
│   │   ├── nodes.py               # Agent nodes (understand, plan, search, evaluate)
│   │   ├── state.py               # Agent state management
│   │   └── memory.py              # Session memory configuration
│   ├── tools/                      # Graphiti tools for the agent
│   │   ├── __init__.py
│   │   ├── search.py              # Basic search tool
│   │   ├── traverse.py            # Graph traversal tools
│   │   ├── community.py           # Community detection tools
│   │   ├── entity.py              # Entity-specific tools
│   │   └── temporal.py            # Time-based query tools
│   ├── server/                     # Ray Serve API
│   │   ├── __init__.py
│   │   ├── app.py                 # Ray Serve deployment
│   │   └── endpoints.py           # API endpoints
│   └── utils/                      # Shared utilities
│       ├── __init__.py
│       ├── response_formatter.py   # Format agent responses
│       └── query_parser.py        # Parse user queries
├── prompts/
│   └── chat/                       # Chat-specific prompts
│       ├── agent_system.md         # Main agent system prompt
│       ├── understand_query.md     # Query understanding prompt
│       ├── plan_exploration.md     # Planning prompt
│       ├── evaluate_results.md     # Result evaluation prompt
│       └── format_response.md      # Response formatting prompt
```

## Implementation Phases

### Phase 1: Foundation (Week 1)
1. Set up folder structure and base files
2. Create Ray Serve deployment configuration
3. Implement basic chat endpoint
4. Set up Graphiti client initialization
5. Create prompt templates

### Phase 2: Core Agent (Week 2)
1. Implement LangGraph agent structure
2. Create agent nodes (understand, plan, search, evaluate)
3. Implement state management
4. Add session memory
5. Create agent execution loop

### Phase 3: Graphiti Tools (Week 3)
1. Implement search tools based on Graphiti capabilities
2. Create entity-specific tools
3. Add temporal query tools
4. Implement graph traversal tools
5. Add community detection tools

### Phase 4: Integration & Testing (Week 4)
1. Integrate with Open WebUI
2. Add comprehensive error handling
3. Implement response formatting
4. Create test suite
5. Performance optimization

## Detailed TODO List

### 1. Project Setup
- [ ] Create folder structure under `src/chat/`
- [ ] Add Ray Serve to dependencies in `pyproject.toml`
- [ ] Create Docker configuration for Open WebUI
- [ ] Update `docker-compose.yml` with Open WebUI service
- [ ] Create environment variables for chat configuration

### 2. Ray Serve Configuration
- [ ] Create `src/chat/server/app.py` with Ray Serve deployment
- [ ] Implement chat endpoint compatible with OpenWebUI API
- [ ] Add health check endpoint
- [ ] Configure CORS for Open WebUI
- [ ] Set up proper error handling and logging

### 3. Agent Foundation
- [ ] Create `src/chat/agent/state.py` with agent state schema
- [ ] Implement `src/chat/agent/memory.py` with LangChain memory
- [ ] Create base agent graph in `src/chat/agent/graph.py`
- [ ] Define agent workflow with conditional edges
- [ ] Implement retry and fallback mechanisms

### 4. Agent Nodes
- [ ] **Understand Node**: Parse and understand user query
  - [ ] Extract entities mentioned
  - [ ] Identify query intent
  - [ ] Determine required search depth
- [ ] **Plan Node**: Plan exploration strategy
  - [ ] Select appropriate tools
  - [ ] Define search sequence
  - [ ] Set evaluation criteria
- [ ] **Search Node**: Execute searches
  - [ ] Call selected tools
  - [ ] Collect results
  - [ ] Handle errors gracefully
- [ ] **Evaluate Node**: Assess results
  - [ ] Check if answer is complete
  - [ ] Decide if more searches needed
  - [ ] Summarize findings

### 5. Graphiti Tools Implementation
- [ ] **Basic Search Tool** (`src/chat/tools/search.py`)
  - [ ] Implement `search_entities(query: str)`
  - [ ] Implement `search_episodes(query: str)`
  - [ ] Add result parsing and formatting
- [ ] **Entity Tools** (`src/chat/tools/entity.py`)
  - [ ] `get_entity_details(entity_id: str)`
  - [ ] `get_entity_relationships(entity_id: str)`
  - [ ] `get_entity_timeline(entity_id: str)`
- [ ] **Traversal Tools** (`src/chat/tools/traverse.py`)
  - [ ] `traverse_from_entity(entity_id: str, relationship_types: List[str])`
  - [ ] `find_paths_between(source_id: str, target_id: str)`
  - [ ] `get_neighbors(entity_id: str, max_depth: int)`
- [ ] **Temporal Tools** (`src/chat/tools/temporal.py`)
  - [ ] `search_by_date_range(start: datetime, end: datetime)`
  - [ ] `get_entity_history(entity_id: str)`
  - [ ] `find_concurrent_events(date: datetime)`
- [ ] **Community Tools** (`src/chat/tools/community.py`)
  - [ ] `get_communities()`
  - [ ] `get_community_members(community_id: str)`
  - [ ] `find_related_communities(entity_id: str)`

### 6. Prompt Management
- [ ] Create prompt templates following existing patterns
- [ ] **System Prompt** (`src/prompts/chat/agent_system.md`)
  - [ ] Define agent persona and capabilities
  - [ ] Set exploration guidelines
  - [ ] Define response formatting rules
- [ ] **Understanding Prompt** (`src/prompts/chat/understand_query.md`)
  - [ ] Query parsing instructions
  - [ ] Entity extraction guidelines
  - [ ] Intent classification
- [ ] **Planning Prompt** (`src/prompts/chat/plan_exploration.md`)
  - [ ] Tool selection criteria
  - [ ] Search strategy templates
  - [ ] Depth determination rules
- [ ] **Evaluation Prompt** (`src/prompts/chat/evaluate_results.md`)
  - [ ] Completeness criteria
  - [ ] Quality assessment
  - [ ] Decision logic for further exploration
- [ ] **Response Prompt** (`src/prompts/chat/format_response.md`)
  - [ ] User-friendly formatting
  - [ ] Citation guidelines
  - [ ] Confidence expression

### 7. Integration & Configuration
- [ ] Create Open WebUI configuration
- [ ] Set up authentication (if needed)
- [ ] Configure rate limiting
- [ ] Add monitoring and metrics
- [ ] Create deployment scripts

### 8. Testing
- [ ] Unit tests for each tool
- [ ] Integration tests for agent workflow
- [ ] End-to-end tests with sample queries
- [ ] Performance benchmarks
- [ ] Load testing for concurrent users

### 9. Documentation
- [ ] API documentation for chat endpoint
- [ ] Tool usage guide
- [ ] Deployment instructions
- [ ] User guide for Open WebUI
- [ ] Troubleshooting guide

### 10. Future Enhancements (Post-MVP)
- [ ] Add Langfuse integration for tracing
- [ ] Implement advanced caching
- [ ] Add user feedback mechanism
- [ ] Create custom UI components
- [ ] Add export functionality

## Key Design Decisions

### 1. Direct Graphiti Usage
- No wrapper around Graphiti client
- Direct API calls in tools
- Handle connection pooling at tool level

### 2. Multi-Loop Agent Design
```python
# Pseudo-code for agent loop
while not satisfied and iterations < max_iterations:
    understanding = understand_query(query, context)
    plan = create_exploration_plan(understanding)
    results = execute_searches(plan)
    evaluation = evaluate_results(results, query)
    if evaluation.is_complete:
        break
    context.update(results)
```

### 3. Tool Selection Strategy
- Tools are selected based on query understanding
- Each tool has clear input/output contracts
- Tools can be chained for complex queries

### 4. Memory Management
- Session-based memory only (no persistence initially)
- Clear memory after session timeout
- Configurable memory size limits

## Success Criteria
1. Agent can answer complex graph queries accurately
2. Response time < 5 seconds for simple queries
3. Can handle multi-hop relationship queries
4. Provides source citations for answers
5. Gracefully handles ambiguous queries

## Risk Mitigation
1. **Performance**: Implement query caching and result pagination
2. **Accuracy**: Add confidence scores and source attribution
3. **Security**: Implement query sanitization and access controls
4. **Scalability**: Use Ray Serve auto-scaling features
5. **Reliability**: Add circuit breakers and fallback responses

## Dependencies
- Ray Serve
- LangChain
- LangGraph
- Open WebUI (Docker)
- Existing Graphiti client
- Neo4j connection

## Timeline
- **Week 1**: Foundation and setup
- **Week 2**: Core agent implementation
- **Week 3**: Tool development
- **Week 4**: Integration and testing
- **Week 5**: Deployment and documentation

This plan provides a structured approach to building a sophisticated chat interface that leverages the full power of the Graphiti knowledge graph while maintaining clean architecture and following project conventions.