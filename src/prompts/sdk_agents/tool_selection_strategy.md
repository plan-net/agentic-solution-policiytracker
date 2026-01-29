---
name: tool_selection_strategy
version: 2
description: Tool selection and reflection strategy for SDK agents with German language awareness
tags: ["sdk", "strategy", "tools", "reflection", "german"]
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
- **For Knowledge Graph: Try German equivalents** (see table below)
- Try the fallback tool from the strategy table
- Consider breaking the question into smaller parts

### Language-Aware Retry Strategy for Knowledge Graph

**The Knowledge Graph contains German data. If English searches return empty, try German equivalents:**

| If you searched for... | Try German equivalent... |
|------------------------|--------------------------|
| AI Act | **KI-Verordnung**, KI-VO |
| artificial intelligence | **Künstliche Intelligenz**, KI |
| GDPR | **DSGVO** |
| NIS2 | **NIS2-Richtlinie** |
| Digital Services Act | **DSA**, Gesetz über digitale Dienste |
| Digital Markets Act | **DMA**, Gesetz über digitale Märkte |
| compliance | **Umsetzung**, Einhaltung, Compliance |
| regulation | **Verordnung**, Regulierung |
| directive | **Richtlinie** |
| legislation | **Gesetzgebung**, Gesetz |
| consumer protection | **Verbraucherschutz** |
| data protection | **Datenschutz** |
| cybersecurity | **Cybersicherheit**, IT-Sicherheit |
| platform | **Plattform** |
| e-commerce | **E-Commerce**, Onlinehandel |
| SME / small business | **KMU**, kleine und mittlere Unternehmen |
| startup | **Startup**, Startups |

**Retry Example:**
```
First search:  "AI Act compliance SME" → ❌ No results
Retry search:  "KI-Verordnung Umsetzung KMU" → ✅ Found results!
```

### 2. Confidence Assessment

Rate your confidence in the results:

| Confidence | Criteria | Action |
|------------|----------|--------|
| **High** | Multiple relevant results, specific details | Proceed with synthesis |
| **Medium** | Some results but incomplete | Proceed but note uncertainty |
| **Low** | Few or no results, or ambiguous | Retry with different strategy |

**Low confidence triggers:**
- Empty results → Try German terms, then try fallback tool
- Only 1-2 vague results → Try more specific German terms
- Results don't match query intent → Reformulate query

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
   - **Switch to German terms if using English**
   - Reduce scope

2. **Second attempt**: Try the fallback tool
   - See strategy table above
   - May require reformulating the question
   - **Try German equivalents with fallback tool too**

3. **Third attempt**: Try alternative data sources
   - If Knowledge Graph empty → Try Bundestag DIP
   - If Bundestag empty → Try DPA News or Web Search
   - Web search can use English terms more effectively

4. **Final fallback**: Acknowledge limitation
   - Clearly state what information could not be found
   - Explain what was attempted
   - Suggest what additional information might help

## Quality Signals

**Good results typically have**:
- Specific entity names and identifiers
- Dates and timestamps
- Clear relationship types
- Multiple corroborating data points
- German regulatory terminology (Verordnung, Richtlinie, Drucksache, etc.)

**Warning signs to watch for**:
- Very generic or vague results
- Missing key details (dates, names)
- Results that don't directly relate to the query
- Contradictory information
- **Empty results when using English terms for German data sources**

## Iteration Guidelines

- **Maximum tool calls**: Aim for efficiency; typically 3-5 calls should suffice
- **Diminishing returns**: If 2-3 attempts with different strategies yield no results, the data may not exist
- **Language check**: Before concluding "no data", ensure you tried German terms
- **Time sensitivity**: Balance thoroughness with responsiveness
- **User context**: Consider what level of detail the user needs

## Tool-Specific Language Guidance

| Tool | Language Recommendation |
|------|------------------------|
| `search_knowledge_graph` | **German PRIMARY**, English fallback |
| `get_entity_info` | German entity names preferred |
| `find_relationships` | German entity names preferred |
| `search_bundestag_legislation` | **German strongly recommended** |
| `search_bundestag_documents` | **German strongly recommended** |
| `search_dpa_news` | German or English OK |
| `web_search` | English or German OK |
| `search_news` | English or German OK |
