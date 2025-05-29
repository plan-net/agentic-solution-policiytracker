---
name: chat_format_response
version: 1
description: Prompt for formatting final responses to users
tags: ["chat", "response", "formatting"]
---

# Response Formatting Task

Create a comprehensive, well-structured response based on your knowledge graph exploration.

## Original Query
{{original_query}}

## Search Results
{{all_search_results}}

## Confidence Level
{{confidence_level}}

## Your Task

Format a professional response that directly addresses the user's query:

### 1. Direct Answer
Start with a clear, direct answer to the user's question:
- Address the main query upfront
- Be specific and factual
- Include key findings prominently

### 2. Supporting Evidence
Provide detailed evidence from the knowledge graph:
- Cite specific facts and their sources
- Include relevant relationships and connections
- Mention dates, jurisdictions, and key entities
- Use bullet points for clarity when appropriate

### 3. Context and Analysis
Add valuable context:
- Explain the significance of findings
- Highlight important relationships or patterns
- Provide regulatory or policy context where relevant
- Note any temporal aspects or changes over time

### 4. Confidence and Limitations
Be transparent about the information:
- Indicate your confidence level in the findings
- Mention any significant gaps or limitations
- Distinguish between certain facts and inferences
- Note if information is time-sensitive

### 5. Follow-up Suggestions
Help the user explore further:
- Suggest related queries they might find interesting
- Point out areas where more detailed information might be available
- Recommend specific aspects worth investigating

## Response Format

Use this structure:

**[Direct answer addressing the main query]**

**Key Findings:**
- [Fact 1 with source/context]
- [Fact 2 with source/context]
- [Fact 3 with source/context]

**Additional Context:**
[Relevant background, relationships, temporal aspects]

**Confidence:** [Level] based on [reasoning]

**Related Topics You Might Explore:**
- [Suggestion 1]
- [Suggestion 2]

**Sources:** [Summary of knowledge graph sources used]

---

Remember to:
- Use clear, professional language
- Be precise about jurisdictions and dates
- Cite sources appropriately
- Maintain objectivity and factual accuracy