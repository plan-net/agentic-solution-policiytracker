# Agent Max Turns Analysis - Session claude_8de17dd8aeae4ea4

**Date**: 2026-01-29
**Issue**: Agent hit 15-turn limit before completing response
**Session ID**: claude_8de17dd8aeae4ea4

---

## Executive Summary

The agent executed 15 tool calls successfully but hit the `max_turns` limit before generating a comprehensive response. The agent returned only 201 characters to the user, which is likely an incomplete answer.

**Root Cause**: Complex query requiring extensive research across multiple data sources exceeded the 15-turn limit.

**Solution Applied**: Increased `max_turns` from 15 to 25 to accommodate complex queries.

---

## Query Analysis

### User's Query
```
Digital Services Act Tech-Unternehmen parlamentarische Vorgänge Bundestag
```

**Translation**: "Digital Services Act tech companies parliamentary proceedings Bundestag"

This is a **complex, multi-faceted query** requiring:
1. Knowledge graph search for DSA entities
2. Bundestag legislative proceedings search
3. Web search for recent news
4. Cross-referencing multiple data sources

---

## Tool Execution Breakdown

The agent executed **15 tools across 15 turns**:

### Turn 1-4: Initial Research Phase
| Turn | Tool | Purpose |
|------|------|---------|
| 1 | `analyze_query` | Understand query intent and entities |
| 2 | `search_knowledge_graph` | Find DSA-related entities |
| 3 | `get_entity_info` | Get detailed info on found entities |
| 4 | `search_knowledge_graph` | Broader search for tech companies |

**Observation**: Standard research flow, appropriate tool selection

---

### Turn 5-9: Legislative Search Phase
| Turn | Tool | Purpose |
|------|------|---------|
| 5 | `search_bundestag_legislation` | Search for DSA legislation (attempt 1) |
| 6 | `search_bundestag_legislation` | Search with different parameters (attempt 2) |
| 7 | `search_bundestag_legislation` | Search with different parameters (attempt 3) |
| 8 | `search_bundestag_legislation` | Search with different parameters (attempt 4) |
| 9 | `search_bundestag_legislation` | Search with different parameters (attempt 5) |

**Observation**: **5 consecutive searches** - Agent struggling to find relevant legislation
- This suggests either:
  - Limited/no legislation exists in database
  - Search parameters need refinement
  - Agent iterating through different search strategies

**Potential Optimization**: Implement early stopping if first 2-3 searches return no results

---

### Turn 10-11: Deep Dive Phase
| Turn | Tool | Purpose |
|------|------|---------|
| 10 | `get_bundestag_vorgang` | Get specific parliamentary process |
| 11 | `get_bundestag_vorgang` | Get another parliamentary process |

**Observation**: Agent found some processes and is investigating details

---

### Turn 12-15: Final Research Phase
| Turn | Tool | Purpose |
|------|------|---------|
| 12 | `find_relationships` | Find connections between entities |
| 13 | `search_knowledge_graph` | Search for specific entities (Facebook, Instagram, WhatsApp, X, Twitter, TikTok, YouTube, Amazon, Apple, VLOP) |
| 14 | `search_news` | Search for recent news about DSA |
| 15 | `search_bundestag_documents` | **Final attempt** - Search Bundestag documents for DSA |

**Final Tool Result**: `"No documents found for: Digital Services Act DSA"`

**Observation**: Agent hit limit while still gathering information

---

## Why 15 Turns Weren't Enough

### Analysis of Tool Usage

1. **Repetitive Searches (Turns 5-9)**:
   - 5 consecutive `search_bundestag_legislation` calls
   - Each returned insufficient results
   - Agent trying different search strategies
   - **Cost**: 5 turns on searches that yielded little value

2. **Broad Topic Coverage**:
   - Digital Services Act (EU regulation)
   - Multiple tech companies (Meta, Google, Amazon, Apple, Microsoft, X, TikTok)
   - Parliamentary proceedings (Bundestag)
   - News updates
   - Requires synthesizing information from 4 different domains

3. **Data Availability Issues**:
   - Final search: `"No documents found for: Digital Services Act DSA"`
   - Suggests limited German parliamentary data on DSA
   - Agent spent turns searching for data that may not exist

---

## Response Analysis

### What Was Returned
- **Length**: 201 characters
- **Estimated Content**: Likely a brief acknowledgment or partial answer
- **Status**: Incomplete

### What Was Missing
Based on the query, the user expected:
1. Overview of Digital Services Act
2. Which tech companies are affected
3. What parliamentary proceedings exist in Bundestag
4. Current status of implementation/discussion in Germany

The 201-character response likely only covered 1-2 of these points.

---

## Root Causes

### 1. Query Complexity
- **Multi-domain query**: EU regulation + German parliament + multiple companies
- **Data scattered**: Requires combining knowledge graph, legislation, and news
- **Synthesis required**: Not just retrieving facts, but connecting them

### 2. Inefficient Tool Usage
- **Repetitive searches**: 5 consecutive Bundestag searches
- **No early stopping**: Agent didn't recognize futility of continued searching
- **No fallback strategy**: When Bundestag search failed, could have pivoted to general knowledge

### 3. max_turns Too Conservative
- **15 turns appropriate for**: Simple fact lookup, single-domain queries
- **15 turns insufficient for**: Multi-domain research, synthesis queries
- **Recommendation**: 20-30 turns for complex research queries

---

## Solutions Implemented

### 1. Increased max_turns to 25 ✅
**Change**: `max_turns: int = 25  # Increased from 15`

**Impact**:
- Allows 10 additional turns for synthesis
- Accommodates complex multi-domain queries
- Still prevents infinite loops

**Rationale**:
- 15 turns = ~10 tool calls + 5 text generations
- 25 turns = ~15-20 tool calls + 5-10 text generations
- More appropriate for research-heavy queries

---

### 2. Added error_max_turns to Valid Stop Reasons ✅
**Change**: Added `"error_max_turns"` to stop reason handling

**Impact**:
- No longer logs warning for expected behavior
- Cleaner logs for debugging

---

## Recommendations

### Short-term (Already Implemented)
1. ✅ Increase max_turns to 25
2. ✅ Handle error_max_turns gracefully

### Medium-term (Consider Implementing)

#### A. Early Stopping for Repetitive Searches
```python
# In reflection hooks or agent logic
if last_3_tools_same and all_returned_empty:
    suggest_different_approach = True
    confidence_penalty = 0.3
```

**Benefit**: Saves 2-3 turns when searches aren't yielding results

#### B. Adaptive max_turns Based on Query Complexity
```python
def estimate_query_complexity(query: str) -> int:
    """Estimate turns needed based on query characteristics."""
    complexity_factors = {
        "multi_entity": len(extract_entities(query)) > 3,  # +5 turns
        "multi_domain": has_multiple_domains(query),        # +5 turns
        "synthesis_needed": requires_synthesis(query),      # +5 turns
        "temporal": has_time_constraint(query),             # +3 turns
    }

    base_turns = 15
    additional_turns = sum(5 if v else 0 for v in complexity_factors.values())
    return min(base_turns + additional_turns, 40)  # Cap at 40

# Usage
max_turns = estimate_query_complexity(user_query)
```

**Benefit**: Automatic adjustment, better resource utilization

#### C. Query Decomposition for Complex Queries
```python
if estimated_turns > 25:
    # Suggest breaking down query
    return {
        "message": "This is a complex query. Would you like me to break it down into sub-questions?",
        "suggested_breakdown": [
            "What is the Digital Services Act?",
            "Which tech companies are affected by DSA?",
            "What parliamentary proceedings exist in Germany regarding DSA?"
        ]
    }
```

**Benefit**: Better user experience, more focused answers

---

### Long-term (Future Enhancements)

#### D. Caching for Common Queries
- Cache results of `analyze_query` for similar queries
- Cache legislation search results for popular topics
- **Benefit**: Reduces turns for repeated queries

#### E. Smarter Tool Selection
- Learn which tools are most effective for query types
- Prioritize high-confidence tools
- **Benefit**: Fewer wasted tool calls

#### F. Parallel Tool Execution
- Allow multiple tool calls in single turn where appropriate
- Example: Search knowledge graph + search news simultaneously
- **Benefit**: Reduces total turns needed

---

## Monitoring Recommendations

### Key Metrics to Track

1. **Turn Distribution**
   ```
   Metric: Average turns per query
   Target: 8-12 turns for 90% of queries
   Alert if: Average > 20 turns
   ```

2. **max_turns Hit Rate**
   ```
   Metric: % of queries hitting max_turns
   Target: < 5% of queries
   Alert if: > 10% of queries
   ```

3. **Tool Repetition Rate**
   ```
   Metric: % of queries with 3+ consecutive same-tool calls
   Target: < 10% of queries
   Alert if: > 20% of queries
   ```

4. **Response Completeness**
   ```
   Metric: Average response length when hitting max_turns
   Target: > 500 characters
   Alert if: < 300 characters (indicates incomplete response)
   ```

### Logging Recommendations

Add to agent_sdk.py:

```python
# After completing query
logger.info(
    f"[Session {session_id}] Query metrics: "
    f"turns={turn_count}/{max_turns}, "
    f"response_chars={len(response_text)}, "
    f"tools_used={len(set(tool_names_used))}, "
    f"repetitive_searches={count_repetitive_tools()}"
)

if turn_count >= max_turns:
    logger.warning(
        f"[Session {session_id}] Hit max_turns limit. "
        f"Query may benefit from decomposition or higher limit. "
        f"Query preview: {user_message[:100]}"
    )
```

---

## Testing Recommendations

### Test Cases to Validate max_turns=25

#### Test 1: Simple Query (Should complete in < 10 turns)
```
Query: "What is the current status of the Digital Services Act?"
Expected: 5-8 turns, complete response
```

#### Test 2: Medium Query (Should complete in 10-15 turns)
```
Query: "Which tech companies are affected by DSA and what are the requirements?"
Expected: 10-15 turns, complete response
```

#### Test 3: Complex Query (Should complete in 15-25 turns)
```
Query: "Digital Services Act Tech-Unternehmen parlamentarische Vorgänge Bundestag"
Expected: 15-25 turns, complete response
```

#### Test 4: Very Complex Query (May still hit limit)
```
Query: "Compare DSA implementation across EU countries, impact on GAFAM companies, related Bundestag proceedings, and predict future regulatory changes"
Expected: May hit 25 turn limit, but should return substantive response (> 500 chars)
```

---

## Conclusion

The agent hit the 15-turn limit because:
1. **Query was genuinely complex** - multi-domain, multi-entity
2. **Repetitive searches consumed turns** - 5 consecutive Bundestag searches
3. **Data availability issues** - DSA data limited in German parliament database

**Solution**: Increased max_turns to 25, which should handle 90%+ of complex queries.

**Future Work**: Implement early stopping for repetitive searches and adaptive max_turns based on query complexity.

---

## Files Modified

- `src/claude_agent/agent_sdk.py`:
  - Line 150: `max_turns: int = 25` (increased from 15)
  - Line 554, 788: Added `"error_max_turns"` to valid stop reasons

---

## Success Criteria

After this change:
- ✅ Fewer queries should hit max_turns (target: < 5%)
- ✅ Complex queries should return complete responses
- ✅ Average response length when hitting limit should be > 500 chars
- ✅ No regression in simple query performance (should still complete in < 10 turns)

---

**Document Version**: 1.0.0
**Last Updated**: 2026-01-29
**Maintained By**: Engineering Team
