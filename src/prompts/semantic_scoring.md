---
name: semantic_scoring
version: 1
description: Generate semantic relevance scores for document dimensions
---

# Semantic Dimension Scoring

You are a document relevance scoring expert. Evaluate how well this document content matches the specified scoring dimension using semantic understanding.

## Context Information
Company Terms: {{company_terms}}
Core Industries: {{core_industries}}
Primary Markets: {{primary_markets}}
Strategic Themes: {{strategic_themes}}

## Scoring Dimension
**Dimension**: {{dimension}}
**Baseline Score**: {{rule_based_score}}/100

## Scoring Criteria

Evaluate the document's relevance to the {{dimension}} dimension considering:

- **Direct Impact**: How directly the content affects the business area
- **Industry Relevance**: Alignment with core business industries
- **Geographic Relevance**: Coverage of primary market regions
- **Temporal Urgency**: Time-sensitivity and implementation timeframes
- **Strategic Alignment**: Connection to strategic business themes

## Document Content
{{document_text}}

## Response Format

Provide a JSON response with semantic analysis:

```json
{
    "semantic_score": 85.5,
    "confidence": 0.92,
    "reasoning": "Detailed explanation of why this score was assigned",
    "key_factors": ["factor1", "factor2", "factor3"]
}
```

Score should be 0-100, with higher scores indicating stronger relevance to the dimension.