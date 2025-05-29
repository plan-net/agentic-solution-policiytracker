---
name: tool_planning
version: 1
description: Plan tool execution sequence based on query analysis
tags: ["planning", "strategy", "tools"]
---

# Tool Execution Planning

Based on the query analysis, plan the optimal sequence of tools to use for comprehensive coverage.

## Query Analysis Results
**Intent**: {intent}
**Complexity**: {complexity}
**Primary Entity**: {primary_entity}
**Secondary Entities**: {secondary_entities}
**Analysis Strategy**: {strategy}

## Available Tools
- search: Hybrid semantic + keyword search
- get_entity_details: Comprehensive entity information
- get_entity_relationships: Entity connections and relationships  
- get_entity_timeline: Entity evolution over time
- find_similar_entities: Similar entities based on graph structure
- traverse_from_entity: Multi-hop relationship exploration
- find_paths_between_entities: Connection paths between entities
- get_entity_neighbors: Immediate neighbors and relationships
- analyze_entity_impact: Impact networks and influence analysis
- search_by_date_range: Temporal event search
- get_entity_history: Historical entity changes
- find_concurrent_events: Events in same time period
- track_policy_evolution: Policy amendment and change tracking
- get_communities: Community and cluster discovery
- get_community_members: Members of specific communities
- get_policy_clusters: Policy groupings by theme/jurisdiction

## Planning Principles

### Tool Selection by Intent
- **Information lookup**: search → get_entity_details → get_entity_relationships
- **Relationship analysis**: search → get_entity_relationships → traverse_from_entity
- **Impact analysis**: search → analyze_entity_impact → find_paths_between_entities
- **Temporal analysis**: search → get_entity_timeline → search_by_date_range → track_policy_evolution
- **Community analysis**: search → get_communities → get_community_members → get_policy_clusters
- **Path discovery**: search → find_paths_between_entities → get_entity_neighbors

### Complexity Considerations  
- **Simple queries**: 2-3 tools maximum
- **Medium queries**: 4-6 tools with logical progression
- **Complex queries**: 6-10 tools with comprehensive coverage

## Required Output

Provide a detailed execution plan:

**Tool Sequence**: [Ordered list of 2-8 tools to execute]
**Rationale**: [Why this sequence provides optimal coverage]
**Expected Insights**: [What unique graph-based insights will emerge]
**Thinking Narrative**: [How to structure the thinking process for user]