---
name: graphiti_episode_creation
version: 1
description: Structure political documents for Graphiti temporal knowledge graph ingestion
tags: ["graphiti", "episode", "temporal", "political"]
---

# Graphiti Episode Creation for Political Documents

This prompt guides the structuring of political and regulatory documents for optimal ingestion into Graphiti temporal knowledge graphs.

## EPISODE STRUCTURE GOALS

### Temporal Context
- Establish clear timeline information for policy evolution
- Link events to specific dates and time periods
- Enable temporal queries across regulatory changes

### Entity Density
- Optimize text chunks for maximum entity extraction
- Ensure sufficient context for relationship detection
- Balance chunk size with processing efficiency

### Business Focus
- Emphasize company impact information
- Highlight compliance requirements and deadlines
- Prioritize enforcement and precedent information

## DOCUMENT PREPROCESSING

### Content Extraction
```
1. Extract clean text from document
2. Identify document metadata (date, author, type, jurisdiction)
3. Segment into logical sections
4. Preserve chronological order
5. Maintain reference context
```

### Temporal Anchoring
```
- Identify document publication/effective date
- Extract mentioned dates and deadlines
- Note policy stage transitions
- Map implementation timelines
```

## EPISODE NAMING STRATEGY

### Format Pattern
```
{document_type}_{jurisdiction}_{topic}_{date}_{sequence}
```

### Examples
```
- policy_eu_ai_act_20240315_001
- enforcement_us_sec_privacy_20240220_001
- consultation_uk_online_safety_20240110_001
- amendment_california_ccpa_20240405_001
```

### Naming Rules
1. Use lowercase with underscores
2. Include ISO date format (YYYYMMDD)
3. Add sequence number for multi-part documents
4. Keep under 100 characters
5. Use standard jurisdiction codes (EU, US, UK, etc.)

## EPISODE CONTENT STRUCTURE

### Main Content
The episode body should contain the full, clean text of the document or section, optimized for entity extraction:

```
[DOCUMENT HEADER INFO]
Title: {document_title}
Date: {publication_date}
Jurisdiction: {primary_jurisdiction}
Type: {document_type}
Source: {source_organization}

[MAIN CONTENT]
{cleaned_document_text}

[METADATA SECTION]
Key Dates: {extracted_dates}
Affected Entities: {mentioned_companies_industries}
Policy Areas: {regulatory_domains}
Cross-References: {cited_documents}
```

### Content Optimization
- Remove formatting artifacts but preserve structure
- Keep section headers for context
- Include footnotes and references inline
- Preserve legal citation formats
- Maintain chronological narrative flow

## EPISODE METADATA

### Required Fields
```python
{
    "name": "episode_name_following_convention",
    "episode_body": "structured_content_as_above", 
    "source": "text",
    "source_description": "Political document: {type} from {organization}",
    "reference_time": datetime_object,  # Document date or effective date
    "group_id": "political_docs"  # Or client-specific group
}
```

### Enhanced Metadata Properties
```python
{
    "document_type": "policy|regulation|enforcement|consultation|amendment",
    "jurisdiction": "primary_jurisdiction_code",
    "policy_area": "ai|privacy|financial|cybersecurity|competition",
    "business_impact": "high|medium|low",
    "compliance_deadline": "ISO_date_if_applicable",
    "affected_industries": ["technology", "financial_services"],
    "mentioned_companies": ["Apple", "Google", "Meta"],
    "extraction_priority": "high|normal|low"
}
```

## DOCUMENT TYPE HANDLING

### Policy Documents
- Focus on implementation timelines
- Extract compliance requirements
- Identify affected business activities
- Note exemptions and safe harbors

### Enforcement Actions
- Highlight precedent value
- Extract penalty amounts and calculations
- Identify compliance failures
- Map to underlying regulations

### Consultation Documents
- Track stakeholder positions
- Identify industry concerns
- Note proposed changes
- Map influence networks

### Amendment Documents
- Clearly state what changes
- Preserve before/after context
- Identify transition periods
- Note grandfathering provisions

## TEMPORAL INFORMATION EXTRACTION

### Key Dates to Capture
```
- Publication/announcement date
- Effective date
- Compliance deadline
- Implementation phases
- Review periods
- Sunset clauses
- Appeal deadlines
```

### Temporal Relationship Mapping
```
- Before/after sequences
- Cause/effect chains
- Parallel processes
- Overlapping jurisdictions
- Phase-in schedules
```

## QUALITY ASSURANCE

### Content Validation
- Verify all entities are properly named
- Check temporal consistency
- Ensure business relevance
- Validate cross-references

### Optimization Checks
- Chunk size appropriate (1000-3000 tokens)
- Entity density sufficient for extraction
- Context preserved for relationships
- Temporal anchoring clear

### Error Prevention
- Remove personal information
- Sanitize confidential data
- Standardize entity naming
- Validate date formats

## EXAMPLE EPISODE STRUCTURE

### Input Document
"Commission Implementing Regulation (EU) 2024/1234 on AI System Classification"

### Structured Episode
```python
{
    "name": "regulation_eu_ai_classification_20240315_001",
    "episode_body": """
COMMISSION IMPLEMENTING REGULATION (EU) 2024/1234
Date: 15 March 2024
Jurisdiction: European Union
Type: Implementing Regulation
Source: European Commission

Article 1 - Classification Requirements
AI systems deployed in the European Union must be classified according to risk levels as defined in Article 6 of Regulation (EU) 2024/1689 (AI Act). Companies operating AI systems must complete classification within 6 months of this regulation's entry into force.

High-risk AI systems, including those used in recruitment, credit scoring, and content recommendation at scale, require conformity assessments by notified bodies. The European Commission designates notified bodies through member state nominations.

Article 2 - Implementation Timeline
This regulation enters into force on 1 August 2024. Companies have until 1 February 2025 to complete initial classifications. The European AI Office will publish guidance documents by 1 June 2024.

Key Dates:
- Entry into force: 1 August 2024
- Classification deadline: 1 February 2025
- Guidance publication: 1 June 2024

Affected Entities: Technology companies, AI system operators, recruitment platforms
Policy Areas: Artificial intelligence, risk management, conformity assessment
Cross-References: Regulation (EU) 2024/1689 (AI Act), Article 6
    """,
    "source": "text",
    "source_description": "Political document: EU implementing regulation on AI classification",
    "reference_time": datetime(2024, 3, 15),
    "group_id": "political_docs"
}
```

This structure optimizes the document for:
1. Entity extraction (European Commission, AI Act, companies)
2. Relationship detection (IMPLEMENTS, REQUIRES_COMPLIANCE, AFFECTS)
3. Temporal queries (timeline tracking, deadline management)
4. Business impact analysis (compliance obligations, affected industries)

Follow this structure for consistent, high-quality episode creation that maximizes Graphiti's temporal knowledge graph capabilities.