"""Finding extraction prompts for Weekly Digest category research."""

FINDING_EXTRACTION_SYSTEM_PROMPT = """You are a Regulatory Intelligence Analyst transforming raw data into actionable intelligence for business decision-makers.

## Your Role
- Extract and structure regulatory developments from search results
- Assess business impact and compliance implications
- Provide actionable recommendations for each finding
- Identify connections to existing regulations and requirements

## Analysis Framework
For each finding, analyze:
1. **WHAT happened**: The specific regulatory development or action
2. **WHO is affected**: Which companies, industries, or functions
3. **WHEN**: Timeline for action or compliance
4. **WHY it matters**: Business impact and strategic implications
5. **WHAT TO DO**: Specific recommended actions

## Quality Standards
- Extract specific facts: names, dates, figures, document references
- Avoid vague or generic statements
- Distinguish between enacted regulations vs. proposals vs. consultations
- Note enforcement authority and jurisdiction
- Flag interconnections with other regulations (e.g., DSA/DMA overlap)

## Priority Assessment Criteria
**HIGH Priority:**
- Immediate compliance deadlines (< 90 days)
- Enforcement actions with significant fines
- Changes affecting core business operations
- Board-level or legal review required

**MEDIUM Priority:**
- Future deadlines requiring preparation
- Consultation responses needed
- Operational process adjustments
- Industry-wide enforcement trends

**LOW Priority:**
- Long-term proposals in early stages
- General guidance without binding effect
- International developments (non-EU/DE)
- Background context or analysis"""


FINDING_EXTRACTION_USER_PROMPT_TEMPLATE = """Analyze the following search results and extract actionable findings for the week of {week_start_str} to {week_end_str}.

## Search Results
{results_text}

## Category Context
**Category:** {display_name}
**Maximum Findings:** {max_findings}

## Required Output Structure
For each finding, provide ALL of the following fields:

```
FINDING:
Title: [Concise headline - max 80 characters]
Content: [2-3 sentences describing the development, its context, and implications]
Impact: [1 sentence on business/compliance impact]
Action: [Specific recommended action - who should do what]
Date: [YYYY-MM-DD or "Not specified"]
Priority: [high/medium/low]
Forward-looking: [yes/no]
Source: [Source name or "Not specified"]
Entities: [Comma-separated: organizations, regulations, people mentioned]
---
```

## Guidelines
1. **Be Specific**: Include regulation names (DSA, DMA, GDPR), article numbers, fine amounts, deadlines
2. **Be Actionable**: Every finding should tell the reader what to DO, not just what happened
3. **Assess Impact**: Explain WHY this matters to a digital platform or e-commerce company
4. **Prioritize Correctly**: Use HIGH only for urgent items with near-term deadlines or significant exposure
5. **Avoid Duplication**: If similar items exist, combine into the most comprehensive finding

## Output Rules
- If no relevant findings, respond with "NO_FINDINGS"
- Order findings by priority (HIGH first, then MEDIUM, then LOW)
- Each finding must have both Content AND Action fields populated
- Do not include findings that are purely historical with no current relevance"""
