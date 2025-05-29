---
name: chat_evaluate_results
version: 1
description: Prompt for evaluating search results and deciding next steps
tags: ["chat", "evaluation", "decision"]
---

# Results Evaluation Task

Evaluate the search results and determine if you have sufficient information to provide a comprehensive answer.

## Original Query
{{original_query}}

## Search Results So Far
{{search_results}}

## Current Iteration
{{current_iteration}} of {{max_iterations}}

## Your Task

Analyze the current state and make a decision:

### 1. Information Assessment
Evaluate what you've found:
- **Completeness**: Do you have enough information to answer the query?
- **Quality**: Are the facts relevant and reliable?
- **Coverage**: Are all aspects of the query addressed?
- **Depth**: Is the information detailed enough?

### 2. Gap Analysis
Identify what's missing:
- Key information gaps that need filling
- Areas where more detail would be valuable
- Potential follow-up searches that could help

### 3. Confidence Level
Rate your confidence in providing a good answer:
- **High (80-100%)**: Comprehensive information available
- **Medium (50-79%)**: Good information but some gaps
- **Low (20-49%)**: Limited information, significant gaps
- **Very Low (0-19%)**: Insufficient information to answer

### 4. Decision
Choose one:
- **CONTINUE**: More searches needed - specify what to search for next
- **RESPOND**: Sufficient information to provide a good answer
- **CLARIFY**: Need user clarification to proceed effectively

Provide your evaluation in this format:

**Information Quality**: [Assessment of current results]

**Coverage Analysis**: [What aspects are well covered vs. missing]

**Confidence Level**: [High/Medium/Low/Very Low] - [Percentage]

**Decision**: [CONTINUE/RESPOND/CLARIFY]

**Reasoning**: [Detailed explanation of your decision]

**Next Action**: [If CONTINUE: what to search for next; If RESPOND: key points to include; If CLARIFY: what to ask user]