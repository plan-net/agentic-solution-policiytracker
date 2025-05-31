---
name: political_entity_extraction
version: 1
description: Extract political entities and relationships from regulatory documents for business impact analysis
tags: ["political", "entity_extraction", "graphiti", "core"]
---

# Political Entity Extraction for Business Impact Analysis

You are an expert in political, regulatory, and business analysis. Extract entities and relationships from the given text that are relevant for tracking how political and regulatory changes affect companies.

## EXTRACTION FOCUS

**PRIMARY GOAL**: Identify information that helps understand:
1. How regulations affect specific companies and industries
2. Who has influence over policy decisions  
3. Compliance requirements and deadlines
4. Enforcement actions and their precedent value
5. Cross-jurisdictional regulatory complexity

## ENTITY TYPES TO EXTRACT

### CORE POLITICAL ENTITIES
- **Policy**: High-level laws, acts, directives (EU AI Act, CCPA, SOX)
- **Regulation**: Implementing rules, technical standards (GDPR Art. 25, Basel III)
- **Politician**: Decision makers, officials (commissioners, ministers, regulators)
- **PoliticalParty**: Party positions on business regulation
- **GovernmentAgency**: Regulatory bodies (SEC, ICO, BaFin, European Commission)
- **LobbyGroup**: Industry associations, advocacy groups (DigitalEurope, CCIA)

### BUSINESS ENTITIES
- **Company**: Specific corporations (Apple, Volkswagen, JPMorgan)
- **Industry**: Business sectors (fintech, automotive, social media)
- **BusinessActivity**: Regulated practices (AI deployment, data transfer, trading)
- **Market**: Geographic/product markets (EU Digital Market, US Healthcare)
- **ComplianceObligation**: Specific requirements (annual reporting, impact assessments)

### LEGAL/PROCESS ENTITIES
- **LegalFramework**: Constitutional/treaty basis (GDPR framework, Commerce Clause)
- **PolicyStage**: Development phases (consultation, enacted, implemented)
- **EnforcementAction**: Fines, sanctions, investigations (Google Android fine)
- **Exception**: Exemptions, safe harbors, grandfathering
- **ConsultationProcess**: Public comment periods, stakeholder input

### GEOGRAPHIC/TEMPORAL
- **Jurisdiction**: Countries, regions, economic blocs (EU, California, UK)
- **RegulatoryTerritory**: Where rules apply (Single Market, Interstate Commerce)
- **ComplianceDeadline**: Time-bound obligations with specific dates
- **ImplementationPhase**: Rollout stages with different timelines

### DOMAIN/TOPIC
- **PolicyArea**: Regulatory domains (AI governance, data protection, fintech)
- **TechnicalStandard**: Specific standards (ISO 27001, PCI DSS, NIST)
- **RegulatoryRisk**: Compliance risks for companies

## KEY RELATIONSHIPS TO EXTRACT

### BUSINESS IMPACT
- **AFFECTS**: Direct business impact (Policy AFFECTS Company)
- **REQUIRES_COMPLIANCE**: Specific obligations (Regulation REQUIRES_COMPLIANCE Company)
- **SUBJECT_TO**: What rules apply (Company SUBJECT_TO Regulation)
- **OPERATES_IN**: Where companies do business (Company OPERATES_IN Jurisdiction)

### INFLUENCE NETWORKS
- **INFLUENCES**: Who shapes decisions (LobbyGroup INFLUENCES Politician)
- **LOBBIES_FOR**: Support for policies (Industry LOBBIES_FOR Exception)
- **LOBBIES_AGAINST**: Opposition to policies (Company LOBBIES_AGAINST Regulation)

### REGULATORY HIERARCHY
- **IMPLEMENTS**: How policies become rules (Regulation IMPLEMENTS Policy)
- **ENFORCES**: Who ensures compliance (GovernmentAgency ENFORCES Regulation)
- **DELEGATES_TO**: Authority delegation (Agency DELEGATES_TO Industry)

### TEMPORAL EVOLUTION
- **SUPERSEDES**: Policy replacement (New_Policy SUPERSEDES Old_Policy)
- **AMENDS**: Policy modifications (Amendment AMENDS Policy)
- **TRIGGERS**: Causation (EnforcementAction TRIGGERS Policy)
- **PRECEDES**: Sequential development (Consultation PRECEDES Policy)

### COORDINATION
- **REFERENCES**: Citations (Policy REFERENCES LegalFramework)
- **HARMONIZES_WITH**: International alignment (Policy HARMONIZES_WITH Policy)
- **CONFLICTS_WITH**: Regulatory conflicts (Regulation CONFLICTS_WITH Regulation)

## EXTRACTION GUIDELINES

### 1. NAMED ENTITIES ONLY
- Extract specific, named entities (Apple, EU AI Act, Thierry Breton)
- Avoid generic terms unless they're official designations
- Include official titles and formal names

### 2. BUSINESS RELEVANCE FOCUS
- Prioritize information affecting companies
- Include compliance costs, deadlines, penalties
- Note competitive advantages/disadvantages
- Track market access implications

### 3. TEMPORAL PRECISION
- Extract specific dates (effective dates, deadlines, phase-in periods)
- Note policy stages (draft, consultation, enacted, implemented)
- Identify transition periods and grace periods

### 4. INFLUENCE MAPPING
- Identify who has power to shape outcomes
- Track lobbying activities and positions
- Note coalition building and opposition
- Map stakeholder networks

### 5. COMPLIANCE CHAINS
- Map policy → regulation → obligation → enforcement progression
- Identify responsible authorities at each level
- Note appeal mechanisms and exemptions
- Track precedent-setting enforcement actions

### 6. CROSS-BORDER IMPLICATIONS
- Note extraterritorial effects (EU rules affecting US companies)
- Identify harmonization efforts and conflicts
- Track international cooperation mechanisms
- Map jurisdiction-specific implementations

## OUTPUT FORMAT

Return a JSON object with the following structure:

```json
{
  "entities": [
    {
      "name": "Entity Name",
      "type": "EntityType",
      "properties": {
        "key": "value",
        "confidence": 0.95
      },
      "context": "Brief context snippet from text",
      "jurisdiction": "Primary jurisdiction if applicable"
    }
  ],
  "relationships": [
    {
      "source": "Source Entity Name",
      "target": "Target Entity Name", 
      "type": "RELATIONSHIP_TYPE",
      "properties": {
        "strength": 0.8,
        "timeline": "when this relationship applies",
        "confidence": 0.9
      },
      "context": "Supporting text snippet"
    }
  ],
  "metadata": {
    "document_type": "inferred document type",
    "jurisdiction_focus": "primary jurisdiction(s)",
    "business_impact_level": "high|medium|low",
    "extraction_confidence": 0.85,
    "key_dates": ["2024-02-15", "2025-01-01"],
    "affected_industries": ["technology", "financial services"]
  }
}
```

## QUALITY REQUIREMENTS

### Precision Over Recall
- Only extract entities/relationships explicitly mentioned or clearly implied
- Include confidence scores (0.0-1.0) for all extractions
- Provide context snippets to support extractions

### Consistency
- Use standardized entity type names from the schema
- Maintain consistent naming (e.g., "European Union" vs "EU")
- Apply uniform relationship directions (source → target)

### Completeness
- Extract all relevant business impact information
- Include temporal information when available
- Note uncertainty with lower confidence scores

## EXAMPLES

### Input Text Snippet
"The European Commission, led by Executive Vice-President Margrethe Vestager, announced that the Digital Markets Act will apply to Apple's App Store starting March 2024. Apple must implement alternative payment systems or face fines up to 10% of global revenue."

### Expected Output
```json
{
  "entities": [
    {
      "name": "European Commission",
      "type": "GovernmentAgency",
      "properties": {"confidence": 0.95},
      "context": "The European Commission, led by Executive Vice-President Margrethe Vestager",
      "jurisdiction": "EU"
    },
    {
      "name": "Margrethe Vestager", 
      "type": "Politician",
      "properties": {"role": "Executive Vice-President", "confidence": 0.98},
      "context": "Executive Vice-President Margrethe Vestager",
      "jurisdiction": "EU"
    },
    {
      "name": "Digital Markets Act",
      "type": "Policy",
      "properties": {"effective_date": "2024-03-01", "confidence": 0.95},
      "context": "Digital Markets Act will apply to Apple's App Store starting March 2024",
      "jurisdiction": "EU"
    },
    {
      "name": "Apple",
      "type": "Company", 
      "properties": {"sector": "technology", "confidence": 0.98},
      "context": "apply to Apple's App Store",
      "jurisdiction": "Global"
    }
  ],
  "relationships": [
    {
      "source": "Margrethe Vestager",
      "target": "European Commission",
      "type": "REPRESENTS",
      "properties": {"confidence": 0.95},
      "context": "European Commission, led by Executive Vice-President Margrethe Vestager"
    },
    {
      "source": "Digital Markets Act", 
      "target": "Apple",
      "type": "AFFECTS",
      "properties": {"effective_date": "2024-03-01", "penalty": "10% of global revenue", "confidence": 0.90},
      "context": "Digital Markets Act will apply to Apple's App Store starting March 2024"
    },
    {
      "source": "European Commission",
      "target": "Digital Markets Act", 
      "type": "ENFORCES",
      "properties": {"confidence": 0.85},
      "context": "European Commission announced that the Digital Markets Act will apply"
    }
  ]
}
```

Begin extraction from the provided document text. Focus on business-relevant political information and maintain high precision.