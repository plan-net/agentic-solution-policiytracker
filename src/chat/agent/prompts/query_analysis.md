---
name: query_analysis
version: 1
description: Analyze user queries for intent, entities, and strategy
tags: ["analysis", "planning", "core"]
---

# Query Analysis

Analyze this user query to understand their intent and extract key information for graph-based analysis.

## Query to Analyze
{query}

## Previous Context
{conversation_context}

## Analysis Framework

### 1. Intent Classification
Determine the primary intent:
- **Information lookup**: "What is X?" - seeking comprehensive information
- **Relationship analysis**: "How does X relate to Y?" - exploring connections  
- **Impact analysis**: "How does X affect Y?" - understanding consequences
- **Temporal analysis**: "How has X changed?" - tracking evolution over time
- **Community analysis**: "What groups/clusters exist?" - discovering networks
- **Path discovery**: "How is X connected to Y?" - finding connection routes
- **General inquiry**: Broad exploratory questions

### 2. Entity Extraction
Identify entities using these patterns:
- **Regulatory entities**: Policies, laws, regulations, directives
- **Corporate entities**: Companies, organizations, platforms
- **Political entities**: Politicians, agencies, government bodies
- **Jurisdictions**: EU, US, national, regional scopes
- **Topics**: AI, privacy, antitrust, cybersecurity domains

### 3. Complexity Assessment
- **Simple**: Single entity, basic information request
- **Medium**: Multiple entities, relationship exploration
- **Complex**: Network analysis, temporal patterns, impact cascades

## Output Requirements

Provide a structured analysis:

**Intent**: [Primary intent category from above]
**Complexity**: [Simple/Medium/Complex]
**Primary Entity**: [Main entity of focus]
**Secondary Entities**: [Additional relevant entities]
**Key Relationships**: [Types of relationships to explore]
**Temporal Scope**: [Time period if relevant, or "current"]
**Analysis Strategy**: [Approach for comprehensive coverage]