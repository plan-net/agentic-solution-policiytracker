---
name: chat_understand_query
version: 1
description: Prompt for understanding and analyzing user queries
tags: ["chat", "understanding", "analysis"]
---

# Query Understanding Task

Analyze the user's query and extract key information for knowledge graph exploration.

## User Query
{{user_query}}

## Your Task

Analyze this query and provide a structured understanding:

### 1. Query Intent
Identify the primary intent:
- **Information Seeking**: User wants to learn about specific topics
- **Relationship Exploration**: User wants to understand connections
- **Temporal Analysis**: User wants to track changes over time
- **Compliance Research**: User needs regulatory/compliance information
- **Impact Assessment**: User wants to understand policy effects

### 2. Key Entities
Extract important entities mentioned or implied:
- Organizations (companies, agencies, NGOs)
- Policies/Regulations (laws, directives, frameworks)
- People (politicians, officials, executives)
- Jurisdictions (countries, regions, regulatory domains)
- Topics/Themes (AI, privacy, sustainability, etc.)

### 3. Temporal Scope
Determine time-related aspects:
- Specific dates or time periods mentioned
- Implied temporal context (recent, historical, future)
- Need for temporal tracking or evolution analysis

### 4. Search Strategy
Recommend approach:
- Which entities to search for first
- What types of relationships to explore
- Whether temporal analysis is needed
- Suggested search depth and breadth

Provide your analysis in this format:

**Intent**: [Primary intent category]

**Key Entities**: 
- [Entity 1]: [Type/Category]
- [Entity 2]: [Type/Category]

**Temporal Scope**: [Time period or temporal requirement]

**Search Strategy**: [Recommended approach and reasoning]

**Expected Information Types**: [What kinds of facts/relationships to look for]