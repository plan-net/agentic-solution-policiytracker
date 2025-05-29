---
name: chat_plan_exploration
version: 1
description: Prompt for planning knowledge graph exploration strategy
tags: ["chat", "planning", "strategy"]
---

# Exploration Planning Task

Based on your understanding of the user's query, create a detailed plan for exploring the knowledge graph.

## Query Understanding
**Intent**: {{query_intent}}
**Key Entities**: {{key_entities}}
**Temporal Scope**: {{temporal_scope}}

## Available Tools
- **search(query)**: Semantic search for facts and relationships
- **entity_lookup(entity_name)**: Detailed entity information
- **relationship_analysis(entity1, entity2)**: Explore connections
- **temporal_query(entity, time_range)**: Track changes over time

## Your Task

Create a step-by-step exploration plan:

### 1. Search Sequence
Plan the order of searches to maximize information gathering:
- Which tool to use first and why
- What search terms or entities to start with
- How to build on initial results

### 2. Information Priorities
Rank what information is most important:
- Critical facts needed to answer the query
- Supporting context that would be valuable
- Nice-to-have information if available

### 3. Search Depth
Determine how deep to explore:
- Number of search iterations needed
- When to stop and provide an answer
- Criteria for satisfaction

### 4. Contingency Planning
Plan for different scenarios:
- What to do if initial searches return limited results
- Alternative search strategies
- How to broaden or narrow the search scope

Provide your plan in this format:

**Step 1**: [Tool name](parameters) - [Reasoning]
**Step 2**: [Tool name](parameters) - [Reasoning]
**Step 3**: [Tool name](parameters) - [Reasoning]

**Success Criteria**: [What would constitute a good answer]

**Backup Strategies**: [Alternative approaches if primary plan doesn't work]

**Stopping Conditions**: [When to conclude the search and respond]