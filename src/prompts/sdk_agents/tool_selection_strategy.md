---
name: tool_selection_strategy
version: 1
description: Tool selection and reflection strategy for SDK agents
tags: ["sdk", "strategy", "tools", "reflection"]
---
## Tool Selection Strategy

Choose the most appropriate tool based on query intent:

| Query Type | Primary Tool | Fallback Tool |
|------------|--------------|---------------|
| "What is X?" | `get_entity_info` | `search_knowledge_graph` |
| "How does X relate to Y?" | `find_relationships` | `search_knowledge_graph` |
| "Find all X" / "List X" | `search_knowledge_graph` | `find_relationships` |
| "Latest updates on X" | `search_knowledge_graph` | `get_entity_info` |
| "Statistics about X" | `graph_statistics` | `search_knowledge_graph` |
| Complex multi-part question | `analyze_query` first | Then appropriate tool |

## Multi-Step Strategy for Complex Queries

For complex questions that span multiple topics or require synthesis:

1. **Analyze First**: Use `analyze_query` to understand the question components
2. **Research Systematically**: Query each component using the primary tool
3. **Verify Key Facts**: Use `get_entity_info` to confirm important details
4. **Explore Connections**: Use `find_relationships` to find non-obvious links
5. **Synthesize**: Combine findings into a coherent response

## Self-Reflection Protocol

After each tool execution, evaluate your results before proceeding:

### 1. Completeness Check
Ask yourself:
- Did the tool return sufficient information to answer the question?
- Are there important aspects of the question still unanswered?
- Would additional searches help fill gaps?

**If results are sparse or empty**:
- Try broader search terms
- Use related concepts or synonyms
- Try the fallback tool from the strategy table
- Consider breaking the question into smaller parts

### 2. Confidence Assessment

Rate your confidence in the results:

| Confidence | Criteria | Action |
|------------|----------|--------|
| **High** | Multiple relevant results, specific details | Proceed with synthesis |
| **Medium** | Some results but incomplete | Proceed but note uncertainty |
| **Low** | Few or no results, or ambiguous | Retry with different strategy |

### 3. Cross-Validation

For important facts that will be central to your response:
- Verify entity details with `get_entity_info`
- Confirm relationships with `find_relationships`
- Check for contradictory information across sources

### 4. Error Recovery

If a tool fails or returns an error:

1. **First attempt**: Retry with modified parameters
   - Simplify the query
   - Use different keywords
   - Reduce scope

2. **Second attempt**: Try the fallback tool
   - See strategy table above
   - May require reformulating the question

3. **Final fallback**: Acknowledge limitation
   - Clearly state what information could not be found
   - Explain what was attempted
   - Suggest what additional information might help

## Quality Signals

**Good results typically have**:
- Specific entity names and identifiers
- Dates and timestamps
- Clear relationship types
- Multiple corroborating data points

**Warning signs to watch for**:
- Very generic or vague results
- Missing key details (dates, names)
- Results that don't directly relate to the query
- Contradictory information

## Iteration Guidelines

- **Maximum tool calls**: Aim for efficiency; typically 3-5 calls should suffice
- **Diminishing returns**: If 2-3 attempts with different strategies yield no results, the data may not exist
- **Time sensitivity**: Balance thoroughness with responsiveness
- **User context**: Consider what level of detail the user needs
