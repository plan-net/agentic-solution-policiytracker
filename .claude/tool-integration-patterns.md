# Knowledge Graph Tool Integration v0.2.0 Patterns

## Tool Architecture Overview

### 15 Specialized Tools Structure
```python
# Tool categories for multi-agent system
TOOL_CATEGORIES = {
    "entity": ["entity_details", "entity_relationships", "entity_timeline", "entity_search"],
    "network": ["traverse_network", "find_central_entities", "find_shortest_path", "detect_communities"],
    "temporal": ["track_changes", "compare_timeframes", "timeline_analysis"],
    "search": ["semantic_search", "search_rerank", "explore_graph"]
}
```

### Tool Manager Integration
```python
# src/chat/tools/__init__.py
from src.chat.tools.entity import EntityTools
from src.chat.tools.network import NetworkTools
from src.chat.tools.temporal import TemporalTools
from src.chat.tools.search import SearchTools

class KnowledgeGraphToolManager:
    def __init__(self, graphiti_client):
        self.graphiti_client = graphiti_client
        self.tools = {}
        self._initialize_tools()
    
    def _initialize_tools(self):
        # Initialize tool categories
        self.entity_tools = EntityTools(self.graphiti_client)
        self.network_tools = NetworkTools(self.graphiti_client)
        self.temporal_tools = TemporalTools(self.graphiti_client)
        self.search_tools = SearchTools(self.graphiti_client)
        
        # Register all tools
        self._register_category_tools("entity", self.entity_tools)
        self._register_category_tools("network", self.network_tools)
        self._register_category_tools("temporal", self.temporal_tools)
        self._register_category_tools("search", self.search_tools)
    
    def list_tools(self) -> List[Dict]:
        """Return available tools with descriptions."""
        return [
            {
                "name": name,
                "description": tool.description,
                "parameters": tool.parameters,
                "category": tool.category
            }
            for name, tool in self.tools.items()
        ]
    
    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a specific tool with parameters."""
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        tool = self.tools[tool_name]
        return await tool.execute(**kwargs)
```

## Entity Tools Implementation

### Entity Details Tool
```python
# src/chat/tools/entity.py
class EntityDetailsDriver(BaseTool):
    name = "entity_details"
    description = "Get comprehensive information about a specific entity"
    category = "entity"
    
    parameters = {
        "entity_name": {"type": "string", "description": "Name of the entity to analyze"},
        "include_relationships": {"type": "boolean", "default": True},
        "max_relationships": {"type": "integer", "default": 10}
    }
    
    async def execute(self, entity_name: str, include_relationships: bool = True, max_relationships: int = 10) -> ToolResult:
        try:
            # Search for entity
            search_results = await self.graphiti_client.search(entity_name)
            
            if not search_results.nodes:
                return ToolResult(
                    success=False,
                    message=f"Entity '{entity_name}' not found in knowledge graph"
                )
            
            # Get best matching entity
            entity = self._find_best_match(search_results.nodes, entity_name)
            
            result = {
                "entity": {
                    "name": entity.name,
                    "type": entity.labels[0] if entity.labels else "Unknown",
                    "properties": entity.properties,
                    "uuid": entity.uuid
                }
            }
            
            if include_relationships:
                relationships = await self._get_entity_relationships(entity.uuid, max_relationships)
                result["relationships"] = relationships
            
            return ToolResult(
                success=True,
                data=result,
                message=f"Found detailed information for entity: {entity.name}"
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                message=f"Error retrieving entity details: {str(e)}"
            )
```

### Entity Search Tool
```python
class EntitySearchDriver(BaseTool):
    name = "entity_search"
    description = "Search for entities matching a query"
    
    parameters = {
        "query": {"type": "string", "description": "Search query for entities"},
        "entity_types": {"type": "array", "items": {"type": "string"}, "description": "Filter by entity types"},
        "limit": {"type": "integer", "default": 10, "description": "Maximum number of results"}
    }
    
    async def execute(self, query: str, entity_types: List[str] = None, limit: int = 10) -> ToolResult:
        try:
            # Execute search
            results = await self.graphiti_client.search(query)
            
            # Filter by entity types if specified
            filtered_nodes = results.nodes
            if entity_types:
                filtered_nodes = [
                    node for node in results.nodes
                    if any(label in entity_types for label in node.labels)
                ]
            
            # Limit results
            limited_nodes = filtered_nodes[:limit]
            
            entities = [
                {
                    "name": node.name,
                    "type": node.labels[0] if node.labels else "Unknown",
                    "relevance_score": getattr(node, 'score', 0.0),
                    "uuid": node.uuid
                }
                for node in limited_nodes
            ]
            
            return ToolResult(
                success=True,
                data={"entities": entities, "total_found": len(filtered_nodes)},
                message=f"Found {len(entities)} entities matching '{query}'"
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                message=f"Error searching entities: {str(e)}"
            )
```

## Network Analysis Tools

### Network Traversal Tool
```python
# src/chat/tools/network.py
class TraverseNetworkDriver(BaseTool):
    name = "traverse_network"
    description = "Traverse the network from a starting entity to find connected entities"
    
    parameters = {
        "start_entity": {"type": "string", "description": "Starting entity name"},
        "max_hops": {"type": "integer", "default": 2, "description": "Maximum number of hops"},
        "relationship_types": {"type": "array", "items": {"type": "string"}, "description": "Filter by relationship types"},
        "max_results": {"type": "integer", "default": 20}
    }
    
    async def execute(self, start_entity: str, max_hops: int = 2, relationship_types: List[str] = None, max_results: int = 20) -> ToolResult:
        try:
            # Find starting entity
            start_results = await self.graphiti_client.search(start_entity)
            if not start_results.nodes:
                return ToolResult(
                    success=False,
                    message=f"Starting entity '{start_entity}' not found"
                )
            
            start_node = start_results.nodes[0]
            
            # Traverse network using graph algorithms
            traversal_paths = await self._traverse_from_entity(
                start_node.uuid,
                max_hops=max_hops,
                relationship_types=relationship_types,
                max_results=max_results
            )
            
            return ToolResult(
                success=True,
                data={
                    "start_entity": start_node.name,
                    "traversal_paths": traversal_paths,
                    "total_entities_found": len(set(entity["uuid"] for path in traversal_paths for entity in path["entities"]))
                },
                message=f"Traversed {max_hops} hops from {start_node.name}, found {len(traversal_paths)} paths"
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                message=f"Error traversing network: {str(e)}"
            )
```

### Community Detection Tool
```python
class DetectCommunitiesDriver(BaseTool):
    name = "detect_communities"
    description = "Detect communities or clusters in the knowledge graph"
    
    parameters = {
        "focus_area": {"type": "string", "description": "Focus area for community detection"},
        "min_community_size": {"type": "integer", "default": 3},
        "algorithm": {"type": "string", "enum": ["modularity", "infomap"], "default": "modularity"}
    }
    
    async def execute(self, focus_area: str = None, min_community_size: int = 3, algorithm: str = "modularity") -> ToolResult:
        try:
            # Get relevant subgraph
            if focus_area:
                subgraph_results = await self.graphiti_client.search(focus_area)
                entity_uuids = [node.uuid for node in subgraph_results.nodes[:50]]  # Limit for performance
            else:
                # Get all entities (limited for performance)
                all_results = await self.graphiti_client.search("")
                entity_uuids = [node.uuid for node in all_results.nodes[:100]]
            
            # Apply community detection algorithm
            communities = await self._detect_communities_in_subgraph(
                entity_uuids,
                min_size=min_community_size,
                algorithm=algorithm
            )
            
            # Format results
            formatted_communities = []
            for i, community in enumerate(communities):
                formatted_communities.append({
                    "community_id": i + 1,
                    "size": len(community["entities"]),
                    "entities": community["entities"][:10],  # Limit displayed entities
                    "common_themes": community.get("themes", []),
                    "centrality_scores": community.get("centrality", {})
                })
            
            return ToolResult(
                success=True,
                data={
                    "communities": formatted_communities,
                    "total_communities": len(communities),
                    "algorithm_used": algorithm
                },
                message=f"Detected {len(communities)} communities using {algorithm} algorithm"
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                message=f"Error detecting communities: {str(e)}"
            )
```

## Temporal Analysis Tools

### Timeline Analysis Tool
```python
# src/chat/tools/temporal.py
class TimelineAnalysisDriver(BaseTool):
    name = "timeline_analysis"
    description = "Analyze temporal evolution of entities and relationships"
    
    parameters = {
        "entity_or_topic": {"type": "string", "description": "Entity or topic to analyze over time"},
        "time_range": {"type": "object", "properties": {
            "start_date": {"type": "string", "format": "date"},
            "end_date": {"type": "string", "format": "date"}
        }},
        "granularity": {"type": "string", "enum": ["day", "week", "month"], "default": "month"}
    }
    
    async def execute(self, entity_or_topic: str, time_range: Dict = None, granularity: str = "month") -> ToolResult:
        try:
            # Parse time range
            if time_range:
                start_date = datetime.fromisoformat(time_range["start_date"])
                end_date = datetime.fromisoformat(time_range["end_date"])
            else:
                # Default to last 6 months
                end_date = datetime.now()
                start_date = end_date - timedelta(days=180)
            
            # Get temporal data
            timeline_data = await self._get_temporal_data(
                entity_or_topic,
                start_date,
                end_date,
                granularity
            )
            
            # Analyze trends
            trends = self._analyze_temporal_trends(timeline_data)
            
            return ToolResult(
                success=True,
                data={
                    "entity_topic": entity_or_topic,
                    "time_range": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat()
                    },
                    "timeline": timeline_data,
                    "trends": trends,
                    "key_events": self._identify_key_events(timeline_data)
                },
                message=f"Analyzed timeline for {entity_or_topic} from {start_date.date()} to {end_date.date()}"
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                message=f"Error analyzing timeline: {str(e)}"
            )
```

## Search and Discovery Tools

### Semantic Search Tool
```python
# src/chat/tools/search.py
class SemanticSearchDriver(BaseTool):
    name = "semantic_search"
    description = "Perform semantic search across the knowledge graph"
    
    parameters = {
        "query": {"type": "string", "description": "Natural language search query"},
        "search_type": {"type": "string", "enum": ["entities", "relationships", "both"], "default": "both"},
        "limit": {"type": "integer", "default": 15},
        "include_context": {"type": "boolean", "default": True}
    }
    
    async def execute(self, query: str, search_type: str = "both", limit: int = 15, include_context: bool = True) -> ToolResult:
        try:
            # Execute semantic search via Graphiti
            search_results = await self.graphiti_client.search(query)
            
            # Process and rank results
            processed_results = await self._process_search_results(
                search_results,
                search_type,
                limit,
                include_context
            )
            
            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "results": processed_results,
                    "total_found": len(search_results.nodes),
                    "search_type": search_type
                },
                message=f"Found {len(processed_results)} relevant results for '{query}'"
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                message=f"Error performing semantic search: {str(e)}"
            )
```

## Tool Integration in Multi-Agent System

### Tool Planning Agent Integration
```python
# src/chat/agent/agents.py
class ToolPlanningAgent:
    def __init__(self, knowledge_graph_tools: KnowledgeGraphToolManager):
        self.tools = knowledge_graph_tools
    
    async def create_tool_plan(self, query_analysis: Dict) -> ToolPlan:
        # Get available tools
        available_tools = self.tools.list_tools()
        
        # Select tools based on query analysis
        selected_tools = await self._select_tools_for_query(
            query_analysis,
            available_tools
        )
        
        # Create execution sequence
        tool_sequence = await self._optimize_tool_sequence(selected_tools)
        
        return ToolPlan(
            strategy_type=self._determine_strategy_type(tool_sequence),
            tool_sequence=tool_sequence,
            estimated_execution_time=self._estimate_execution_time(tool_sequence)
        )
    
    async def _select_tools_for_query(self, query_analysis: Dict, available_tools: List) -> List:
        """Select appropriate tools based on query intent and complexity."""
        
        intent = query_analysis.get("intent", "unknown")
        entities = query_analysis.get("entities_mentioned", [])
        complexity = query_analysis.get("complexity", "medium")
        
        selected_tools = []
        
        # Entity-focused queries
        if entities and intent in ["entity_info", "entity_relationships"]:
            selected_tools.extend([
                {"tool_name": "entity_details", "parameters": {"entity_name": entities[0]}},
                {"tool_name": "entity_relationships", "parameters": {"entity_name": entities[0]}}
            ])
        
        # Network analysis queries
        if intent in ["network_analysis", "influence_mapping"]:
            selected_tools.extend([
                {"tool_name": "traverse_network", "parameters": {"start_entity": entities[0] if entities else ""}},
                {"tool_name": "find_central_entities", "parameters": {}}
            ])
        
        # Temporal queries
        if intent in ["timeline", "temporal_analysis", "trend_analysis"]:
            selected_tools.extend([
                {"tool_name": "timeline_analysis", "parameters": {"entity_or_topic": entities[0] if entities else query_analysis.get("primary_topic", "")}},
                {"tool_name": "track_changes", "parameters": {}}
            ])
        
        # Search and discovery
        if intent in ["search", "exploration", "discovery"]:
            selected_tools.extend([
                {"tool_name": "semantic_search", "parameters": {"query": query_analysis.get("original_query", "")}},
                {"tool_name": "search_rerank", "parameters": {}}
            ])
        
        return selected_tools
```

### Tool Execution Agent Integration
```python
class ToolExecutionAgent:
    async def execute_tools(self, state: MultiAgentState) -> AgentResult:
        tool_results = []
        execution_errors = []
        
        for tool_spec in state.tool_plan.tool_sequence:
            try:
                # Execute tool
                result = await self.knowledge_graph_tools.execute_tool(
                    tool_spec.tool_name,
                    **tool_spec.parameters
                )
                
                tool_results.append(result)
                
                # Stream progress update
                writer = get_stream_writer()
                if result.success:
                    writer({"reasoning": f"✅ {tool_spec.tool_name}: {result.message}\n"})
                else:
                    writer({"reasoning": f"⚠️ {tool_spec.tool_name}: {result.message}\n"})
                    execution_errors.append(result.message)
                
            except Exception as e:
                error_msg = f"Error executing {tool_spec.tool_name}: {str(e)}"
                execution_errors.append(error_msg)
                
                writer = get_stream_writer()
                writer({"reasoning": f"❌ {tool_spec.tool_name}: {error_msg}\n"})
        
        return AgentResult(
            success=len(execution_errors) < len(tool_results) / 2,  # Success if < 50% errors
            updated_state={
                "tool_results": tool_results,
                "tool_execution_errors": execution_errors,
                "tools_executed": len(tool_results),
                "successful_tools": len([r for r in tool_results if r.success])
            }
        )
```

## Error Handling and Resilience

### Tool Execution Error Handling
```python
class RobustToolExecutor:
    async def execute_tool_with_retry(self, tool_name: str, max_retries: int = 3, **kwargs) -> ToolResult:
        """Execute tool with retry logic and fallback strategies."""
        
        for attempt in range(max_retries):
            try:
                result = await self.knowledge_graph_tools.execute_tool(tool_name, **kwargs)
                
                if result.success:
                    return result
                
                # Tool returned error - try fallback
                if attempt < max_retries - 1:
                    fallback_result = await self._try_fallback_tool(tool_name, **kwargs)
                    if fallback_result and fallback_result.success:
                        return fallback_result
                
            except Exception as e:
                if attempt == max_retries - 1:
                    return ToolResult(
                        success=False,
                        message=f"Tool {tool_name} failed after {max_retries} attempts: {str(e)}"
                    )
                
                # Wait before retry
                await asyncio.sleep(2 ** attempt)
        
        return ToolResult(success=False, message=f"Tool {tool_name} failed after all retry attempts")
    
    async def _try_fallback_tool(self, primary_tool: str, **kwargs) -> Optional[ToolResult]:
        """Try fallback tools when primary tool fails."""
        
        fallback_mappings = {
            "entity_details": ["entity_search", "semantic_search"],
            "traverse_network": ["entity_relationships", "find_shortest_path"],
            "timeline_analysis": ["track_changes", "entity_timeline"],
            "semantic_search": ["entity_search", "explore_graph"]
        }
        
        fallback_tools = fallback_mappings.get(primary_tool, [])
        
        for fallback_tool in fallback_tools:
            try:
                # Adapt parameters for fallback tool
                adapted_kwargs = self._adapt_parameters_for_tool(fallback_tool, kwargs)
                result = await self.knowledge_graph_tools.execute_tool(fallback_tool, **adapted_kwargs)
                
                if result.success:
                    result.message = f"Fallback: {result.message} (via {fallback_tool})"
                    return result
                    
            except Exception:
                continue  # Try next fallback
        
        return None
```

## Performance Optimization

### Tool Execution Optimization
```python
# Parallel tool execution for independent tools
async def execute_tools_optimized(self, tool_specs: List[ToolSpec]) -> List[ToolResult]:
    # Group tools by dependencies
    independent_groups = self._group_independent_tools(tool_specs)
    
    all_results = []
    
    for group in independent_groups:
        if len(group) == 1:
            # Single tool - execute normally
            result = await self.execute_single_tool(group[0])
            all_results.append(result)
        else:
            # Multiple independent tools - execute in parallel
            tasks = [self.execute_single_tool(tool_spec) for tool_spec in group]
            group_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle any exceptions
            for i, result in enumerate(group_results):
                if isinstance(result, Exception):
                    error_result = ToolResult(
                        success=False,
                        message=f"Tool execution failed: {str(result)}"
                    )
                    all_results.append(error_result)
                else:
                    all_results.append(result)
    
    return all_results

def _group_independent_tools(self, tool_specs: List[ToolSpec]) -> List[List[ToolSpec]]:
    """Group tools that can be executed independently."""
    
    # Define tool dependencies
    dependencies = {
        "entity_relationships": ["entity_details"],
        "traverse_network": ["entity_search"],
        "timeline_analysis": ["entity_details"],
        "search_rerank": ["semantic_search"]
    }
    
    # Group tools by dependency chains
    groups = []
    remaining_tools = tool_specs.copy()
    
    while remaining_tools:
        independent_tools = []
        
        for tool_spec in remaining_tools:
            # Check if dependencies are satisfied
            deps = dependencies.get(tool_spec.tool_name, [])
            deps_satisfied = all(
                any(executed_tool.tool_name == dep for executed_tool in tool_specs[:tool_specs.index(tool_spec)])
                for dep in deps
            )
            
            if not deps or deps_satisfied:
                independent_tools.append(tool_spec)
        
        if independent_tools:
            groups.append(independent_tools)
            for tool in independent_tools:
                remaining_tools.remove(tool)
        else:
            # No more independent tools - add remaining sequentially
            groups.extend([[tool] for tool in remaining_tools])
            break
    
    return groups
```

## Testing Tool Integration

### Tool Execution Testing
```python
# tests/integration/test_tool_integration.py
async def test_knowledge_graph_tools_end_to_end():
    """Test complete tool integration workflow."""
    
    # Initialize tool manager
    graphiti_client = MockGraphitiClient()
    tool_manager = KnowledgeGraphToolManager(graphiti_client)
    
    # Test tool discovery
    available_tools = tool_manager.list_tools()
    assert len(available_tools) == 15
    assert all("name" in tool and "description" in tool for tool in available_tools)
    
    # Test entity tools
    entity_result = await tool_manager.execute_tool(
        "entity_details",
        entity_name="EU AI Act"
    )
    assert entity_result.success
    assert "entity" in entity_result.data
    
    # Test network tools
    network_result = await tool_manager.execute_tool(
        "traverse_network",
        start_entity="EU AI Act",
        max_hops=2
    )
    assert network_result.success
    assert "traversal_paths" in network_result.data
    
    # Test temporal tools
    temporal_result = await tool_manager.execute_tool(
        "timeline_analysis",
        entity_or_topic="EU AI Act"
    )
    assert temporal_result.success
    assert "timeline" in temporal_result.data
```

## Common Anti-Patterns

❌ **Blocking tool execution**:
```python
# DON'T: Execute tools synchronously
for tool in tools:
    result = tool.execute()  # Blocks entire workflow
```

❌ **No error handling**:
```python
# DON'T: Ignore tool failures
result = await tool.execute()
return result.data  # May fail if tool unsuccessful
```

❌ **Excessive tool calls**:
```python
# DON'T: Call too many tools without purpose
tools_to_execute = all_available_tools  # May overwhelm system
```

✅ **Correct patterns**:
```python
# DO: Execute tools asynchronously with error handling
async def execute_tools_safely(tools):
    results = []
    for tool in tools:
        try:
            result = await tool.execute()
            if result.success:
                results.append(result)
            else:
                logger.warning(f"Tool {tool.name} failed: {result.message}")
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
    return results
```