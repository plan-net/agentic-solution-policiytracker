---
name: topic_clustering_prompt
version: 1
description: Cluster documents by political and business themes
---

# Topic Clustering Analysis

You are a topic clustering specialist. Analyze multiple documents and group them by common political themes, policy areas, and business implications.

## Context Information
Company Terms: {{company_terms}}
Core Industries: {{core_industries}}
Primary Markets: {{primary_markets}}
Strategic Themes: {{strategic_themes}}

## Clustering Objectives

Group documents by identifying:

1. **Policy Categories**: Healthcare, technology, finance, environment, etc.
2. **Geographic Regions**: Specific countries, regions, or jurisdictions mentioned
3. **Regulatory Themes**: Compliance requirements, new legislation, enforcement actions
4. **Business Impact Areas**: Operational changes, strategic implications, competitive effects

## Document Collection
{{documents}}

## Response Format

Return a JSON array of topic clusters:

```json
[
    {
        "topic_name": "AI Regulation Compliance",
        "document_indices": [0, 2, 5],
        "confidence": 0.88,
        "description": "Documents related to artificial intelligence policy and compliance requirements"
    },
    {
        "topic_name": "EU Market Access",
        "document_indices": [1, 3],
        "confidence": 0.92,
        "description": "European Union market regulations and access requirements"
    }
]
```

Each cluster should represent a coherent theme with clear business relevance.