---
name: political_relationship_analysis
version: 1
description: Analyze and validate political relationships for business impact assessment
tags: ["political", "relationships", "validation", "analysis"]
---

# Political Relationship Analysis and Validation

This prompt guides the analysis and validation of political relationships extracted from regulatory documents, focusing on business impact and influence networks.

## RELATIONSHIP VALIDATION FRAMEWORK

### Accuracy Verification
- Confirm relationships are explicitly stated or clearly implied
- Validate relationship direction (source → target)
- Check temporal consistency of relationships
- Verify jurisdiction applicability

### Business Relevance Assessment
- Prioritize relationships affecting company operations
- Focus on compliance and enforcement chains
- Highlight competitive impact relationships
- Track influence network connections

## RELATIONSHIP CATEGORIES

### DIRECT BUSINESS IMPACT
**High Priority - Immediate Business Consequences**

#### AFFECTS Relationships
```
Policy AFFECTS Company
Regulation AFFECTS Industry
EnforcementAction AFFECTS Market
ComplianceObligation AFFECTS BusinessActivity
```
**Analysis Focus:**
- Quantify financial impact where possible
- Identify timeline for impact realization
- Assess severity (minimal, low, moderate, high, critical)
- Note mitigation possibilities

#### REQUIRES_COMPLIANCE Relationships
```
Regulation REQUIRES_COMPLIANCE Company
Policy REQUIRES_COMPLIANCE Industry
TechnicalStandard REQUIRES_COMPLIANCE BusinessActivity
```
**Analysis Focus:**
- Extract specific compliance deadlines
- Identify required actions and documentation
- Note penalty structures for non-compliance
- Track implementation costs and complexity

#### SUBJECT_TO Relationships
```
Company SUBJECT_TO Regulation
BusinessActivity SUBJECT_TO ComplianceObligation
Industry SUBJECT_TO TechnicalStandard
Market SUBJECT_TO LegalFramework
```
**Analysis Focus:**
- Define scope of applicability
- Identify conditions and exceptions
- Track enforcement probability
- Note jurisdictional variations

### INFLUENCE NETWORKS
**Medium Priority - Indirect Business Impact Through Political Process**

#### INFLUENCES Relationships
```
LobbyGroup INFLUENCES Politician
Industry INFLUENCES GovernmentAgency
Company INFLUENCES PolicyArea
PoliticalParty INFLUENCES Policy
```
**Analysis Focus:**
- Assess strength and mechanism of influence
- Track resources involved (lobbying spend, personnel)
- Identify reciprocal relationships
- Note duration and stability

#### LOBBIES_FOR / LOBBIES_AGAINST Relationships
```
Company LOBBIES_FOR Exception
LobbyGroup LOBBIES_FOR Regulation
Industry LOBBIES_AGAINST ComplianceObligation
```
**Analysis Focus:**
- Document specific positions and proposals
- Track success probability and tactics
- Identify coalition building efforts
- Note resource allocation and timing

### REGULATORY HIERARCHY
**Medium Priority - Understanding Regulatory Structure**

#### IMPLEMENTS Relationships
```
Regulation IMPLEMENTS Policy
ComplianceObligation IMPLEMENTS Regulation
TechnicalStandard IMPLEMENTS LegalFramework
EnforcementAction IMPLEMENTS ComplianceObligation
```
**Analysis Focus:**
- Track implementation completeness and fidelity
- Identify gaps between policy intent and rules
- Note adaptation requirements for different jurisdictions
- Assess implementation timeline and phases

#### ENFORCES Relationships
```
GovernmentAgency ENFORCES Regulation
Jurisdiction ENFORCES Policy
RegulatoryTerritory ENFORCES ComplianceObligation
```
**Analysis Focus:**
- Evaluate enforcement capability and resources
- Track enforcement tools and success rates
- Identify enforcement priorities and patterns
- Note resource allocation and coverage gaps

### TEMPORAL EVOLUTION
**Medium Priority - Tracking Regulatory Change**

#### SUPERSEDES / AMENDS Relationships
```
Policy SUPERSEDES Policy
Regulation AMENDS Regulation
Exception AMENDS ComplianceObligation
```
**Analysis Focus:**
- Identify transition dates and grandfathering
- Track reasons for changes and modifications
- Note sunset provisions and review cycles
- Assess impact on existing compliance efforts

#### TRIGGERS / PRECEDES Relationships
```
EnforcementAction TRIGGERS Policy
ConsultationProcess PRECEDES Policy
ComplianceDeadline PRECEDES EnforcementAction
```
**Analysis Focus:**
- Map causal chains and event sequences
- Identify trigger conditions and thresholds
- Track dependency relationships
- Note conditional and probabilistic relationships

## RELATIONSHIP STRENGTH ASSESSMENT

### Quantitative Indicators
```
0.9-1.0: Explicit, legally binding relationship
0.7-0.8: Clearly stated, high certainty
0.5-0.6: Implied, moderate confidence
0.3-0.4: Inferred, uncertain
0.1-0.2: Speculative, low confidence
```

### Qualitative Factors
- **Legal certainty**: Statutory vs. regulatory vs. guidance
- **Enforcement history**: Track record of similar relationships
- **Political stability**: Likelihood of relationship continuing
- **Economic significance**: Financial stakes involved
- **Public attention**: Visibility and controversy level

## BUSINESS IMPACT PRIORITIZATION

### Critical Relationships (Immediate Action Required)
1. New compliance obligations with deadlines <6 months
2. Enforcement actions setting new precedents
3. Policy changes affecting core business operations
4. Regulatory conflicts creating legal uncertainty

### Important Relationships (Monitor Closely)
1. Ongoing policy development affecting the business
2. Enforcement trends indicating regulatory priorities
3. Industry coalition positions on key issues
4. Cross-jurisdictional harmonization efforts

### Informational Relationships (Background Monitoring)
1. General political positioning and party platforms
2. Academic and think tank policy recommendations
3. International coordination and standard-setting
4. Long-term regulatory framework evolution

## VALIDATION CHECKLIST

### Factual Accuracy
- [ ] Relationship explicitly stated in source text
- [ ] Entity names match official designations
- [ ] Dates and timelines verified
- [ ] Jurisdiction scope correctly identified
- [ ] Legal status accurately represented

### Business Relevance
- [ ] Direct or indirect impact on company operations
- [ ] Compliance or enforcement implications
- [ ] Competitive advantage/disadvantage effects
- [ ] Market access or regulatory barriers
- [ ] Cost or revenue impact potential

### Temporal Consistency
- [ ] Relationship timeline makes logical sense
- [ ] No conflicts with known regulatory history
- [ ] Future dates are realistic and achievable
- [ ] Past relationships accurately represented
- [ ] Transition periods properly noted

### Strength Assessment
- [ ] Confidence level appropriate for evidence quality
- [ ] Uncertainty explicitly acknowledged
- [ ] Alternative interpretations considered
- [ ] Potential changes or updates noted
- [ ] Source credibility factored in

## OUTPUT FORMAT

### Validated Relationship Structure
```json
{
  "source": "Source Entity Name",
  "target": "Target Entity Name",
  "type": "RELATIONSHIP_TYPE", 
  "strength": 0.85,
  "business_impact": "high|medium|low",
  "priority": "critical|important|informational",
  "properties": {
    "timeline": "specific dates or periods",
    "mechanism": "how relationship operates",
    "conditions": "requirements or exceptions",
    "financial_impact": "cost/revenue estimates",
    "enforcement_probability": 0.7,
    "precedent_value": "low|medium|high"
  },
  "evidence": {
    "source_text": "supporting quote from document",
    "document_section": "section or article reference",
    "confidence_basis": "explanation of confidence level",
    "alternative_interpretations": ["list of other possible readings"]
  },
  "validation": {
    "factual_accuracy": true,
    "business_relevance": true,
    "temporal_consistency": true,
    "strength_appropriate": true,
    "validation_date": "2024-05-27",
    "validator_notes": "additional context or concerns"
  }
}
```

### Analysis Summary
```json
{
  "total_relationships": 15,
  "critical_relationships": 3,
  "important_relationships": 8, 
  "informational_relationships": 4,
  "business_impact_distribution": {
    "high": 5,
    "medium": 7,
    "low": 3
  },
  "key_findings": [
    "Three new compliance deadlines within 6 months",
    "Significant enforcement precedent set for AI liability",
    "Industry coalition forming against proposed amendments"
  ],
  "recommended_actions": [
    "Immediate compliance gap analysis for Q2 2024 deadlines",
    "Monitor enforcement trend for similar companies",
    "Engage with industry coalition on amendment response"
  ]
}
```

Use this framework to ensure political relationships are accurately extracted, properly validated, and effectively prioritized for business decision-making.