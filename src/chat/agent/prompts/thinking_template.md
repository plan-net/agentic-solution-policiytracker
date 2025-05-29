---
name: thinking_template
version: 1
description: Template for generating conversational thinking output
tags: ["thinking", "reasoning", "template"]
---

# Thinking Output Template

Generate natural, conversational thinking output that shows the agent's reasoning process.

## Current Context
**Query**: {query}
**Current Tool**: {current_tool}
**Tool Input**: {tool_input}
**Stage**: {stage}
**Previous Results**: {previous_results}

## Thinking Style Guidelines

### Voice and Tone
- Write in first person ("I need to...", "This shows...")
- Use natural, conversational language
- Show genuine reasoning, not just steps
- Vary sentence starters beyond "I"
- Build logical conclusions that lead to next steps

### Structure Patterns
- **Understanding**: What I'm learning from the current information
- **Reasoning**: Why this leads me to a particular conclusion  
- **Next Step**: Therefore, I should do this next action
- **Connection**: How this relates to previous findings

### Example Patterns

**Query Understanding**:
"Looking at this question, I can see it involves {entities}. This appears to be asking about {intent_explanation}. Since this involves complex regulatory relationships, I'll need to use graph-based analysis to uncover the full picture."

**Tool Execution**:
"I'm starting with a broad search to map the current landscape. This will help me understand what entities are involved and their current status."

**Finding Insights**:
"The search results show {key_finding}. This is interesting because it suggests {implication}. I should now examine the relationships between these entities to understand how they're connected."

**Building Understanding**:
"Now I can see a pattern emerging. The data shows that {pattern}. This means I need to look deeper into {specific_aspect} to get the complete picture."

**Synthesis**:
"Putting all the pieces together, I've discovered {key_insights}. The graph analysis has revealed connections that wouldn't be visible through traditional search methods."

## Output Requirements

Generate thinking output appropriate for the current stage:
- Use paragraph breaks (\n\n) for readability
- Keep individual thoughts to 1-3 sentences
- Show logical progression from observation to conclusion to next action
- Maintain conversational, natural tone throughout
- Avoid repetitive sentence structures