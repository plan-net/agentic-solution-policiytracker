# Query Analysis Phase

You are analyzing a user query to understand their intent and plan the best approach to provide a comprehensive response.

## Current Query
**User Question**: {query}

## Conversation Context
{context}

## Analysis Tasks

1. **Intent Classification**: What is the user trying to learn?
   - Entity exploration (learning about specific entities)
   - Relationship analysis (understanding connections)
   - Impact assessment (understanding effects and consequences)
   - Temporal analysis (tracking changes over time)
   - Network exploration (discovering clusters and communities)
   - Path discovery (finding connections between entities)

2. **Entity Extraction**: Identify key entities mentioned:
   - Primary entity (main focus)
   - Secondary entities (related/connected entities)
   - Entity types (Policy, Organization, Politician, etc.)

3. **Tool Selection Strategy**: Choose 2-4 tools maximum that will provide the most value:
   - Avoid redundant tool calls
   - Prioritize tools that leverage graph structure
   - Consider user's expertise level

4. **Expected Insights**: What unique value can the knowledge graph provide?
   - Multi-hop relationships not obvious from simple search
   - Temporal patterns and evolution
   - Impact cascades and network effects
   - Community structures and clustering
   - Regulatory pathways and compliance chains

## Response Strategy
- Start with most informative tool
- Build narrative connecting different aspects
- Highlight unique graph-based insights
- Provide actionable next steps

## Output Format
Provide your analysis in this structure:

**Intent**: [Primary intent category]
**Key Entities**: [List of entities to focus on]
**Tool Strategy**: [2-4 tools to use and why]
**Unique Value**: [What graph analysis will reveal that basic search cannot]