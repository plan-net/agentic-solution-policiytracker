# Enhanced Political Schema v2.0 - Company Impact Analysis

## Overview

The Enhanced Political Schema v2.0 is a comprehensive knowledge graph schema designed specifically for tracking how political and regulatory changes affect companies. This schema goes far beyond basic policy monitoring to provide detailed business impact analysis, stakeholder influence mapping, and temporal compliance tracking.

## Key Design Principles

### 1. Business-Centric Approach
- **Primary Focus**: How regulations affect specific companies and industries
- **Impact Mapping**: Clear connections between policies and business consequences
- **Compliance Tracking**: Granular obligations, deadlines, and enforcement actions
- **Risk Assessment**: Identified compliance risks with severity and cost estimates

### 2. Multi-Layered Regulatory Hierarchy
```
Policy → Regulation → Implementation → Enforcement
   ↓         ↓             ↓              ↓
Strategic  Technical    Operational   Compliance
 Level      Rules        Requirements   Actions
```

### 3. Temporal Sophistication
- **Policy Lifecycles**: Draft → Consultation → Enactment → Implementation
- **Implementation Phases**: Rollout stages with different timelines
- **Compliance Deadlines**: Time-bound obligations with enforcement dates
- **Historical Evolution**: Track how policies change over time

### 4. Influence Networks
- **Stakeholder Mapping**: Who has power to shape policy outcomes
- **Lobbying Activities**: Industry influence on regulatory decisions
- **Political Relationships**: How parties and politicians affect business regulation

### 5. Cross-Jurisdictional Complexity
- **Multi-Level Governance**: Global → Supranational → National → Subnational
- **Regulatory Territories**: Where specific rules apply
- **Harmonization**: International coordination and conflicts

## Entity Types

### Core Political Entities

#### Policy
High-level laws, acts, directives, and policy frameworks.
- **Examples**: EU AI Act, California Privacy Rights Act, UK Online Safety Bill
- **Key Properties**: stage, jurisdiction, sponsor, legal_basis, objectives
- **Use Case**: Track major legislative initiatives affecting business

#### Regulation
Implementing rules, technical standards, and detailed requirements.
- **Examples**: GDPR Article 25, SOX Section 404, Basel III Capital Requirements
- **Key Properties**: regulation_number, parent_policy, authority, compliance_deadline
- **Use Case**: Understand specific technical requirements companies must meet

#### Politician
Individual decision makers, elected officials, and appointees.
- **Examples**: Margrethe Vestager, Elizabeth Warren, Thierry Breton
- **Key Properties**: title, party, committee_memberships, policy_positions, influence_score
- **Use Case**: Track who makes decisions affecting your industry

#### PoliticalParty
Political parties and their collective positions on business regulation.
- **Examples**: European People's Party, Democratic Party, Conservative Party
- **Key Properties**: ideology, policy_platform, business_stance, regulatory_approach
- **Use Case**: Understand partisan approaches to business regulation

#### GovernmentAgency
Regulatory bodies, enforcement agencies, and government departments.
- **Examples**: European Commission DG COMP, US SEC, UK ICO, German BaFin
- **Key Properties**: mandate, regulatory_powers, enforcement_authority, sector_focus
- **Use Case**: Know which agencies regulate your business activities

#### LobbyGroup
Industry associations, advocacy groups, and influence organizations.
- **Examples**: DigitalEurope, CCIA, Financial Services Roundtable
- **Key Properties**: members, lobbying_spend, policy_focus, political_connections
- **Use Case**: Track industry influence on policy development

### Business/Economic Entities

#### Company
Individual corporations and business entities.
- **Examples**: Apple Inc., Volkswagen AG, JPMorgan Chase, Spotify
- **Key Properties**: sector, size, jurisdictions_active, business_model, compliance_status
- **Use Case**: Map regulatory exposure for specific companies

#### Industry
Business sectors and industry classifications.
- **Examples**: Financial Technology, Automotive, Social Media Platforms
- **Key Properties**: regulatory_intensity, market_concentration, key_players
- **Use Case**: Understand sector-wide regulatory trends

#### BusinessActivity
Specific business practices that get regulated.
- **Examples**: Algorithmic Decision Making, Cross-Border Data Transfer
- **Key Properties**: risk_level, regulatory_coverage, technology_involved
- **Use Case**: Identify which activities trigger compliance requirements

#### Market
Geographic or product markets where companies compete.
- **Examples**: EU Digital Single Market, US Healthcare Market
- **Key Properties**: geographic_scope, market_size, regulatory_framework
- **Use Case**: Understand market-specific regulatory environments

#### ComplianceObligation
Specific requirements companies must meet.
- **Examples**: Annual Privacy Impact Assessment, Quarterly Capital Reporting
- **Key Properties**: requirement, deadline, penalty, implementation_cost
- **Use Case**: Track specific compliance tasks and deadlines

### Legal/Process Entities

#### LegalFramework
Broader legal context and constitutional foundations.
- **Examples**: GDPR Framework, US Constitutional Commerce Clause
- **Key Properties**: jurisdiction, legal_basis, hierarchy_level, fundamental_rights
- **Use Case**: Understand the legal foundation for regulations

#### PolicyStage
Specific phases in policy development and implementation.
- **Examples**: Public Consultation Phase, Committee Review, Parliamentary Vote
- **Key Properties**: typical_duration, key_stakeholders, decision_points
- **Use Case**: Track policy development progress

#### EnforcementAction
Fines, investigations, sanctions, and enforcement measures.
- **Examples**: €4.3B Google Android Fine, Wells Fargo Consent Order
- **Key Properties**: action_type, target, amount, precedent_value
- **Use Case**: Understand enforcement patterns and precedents

#### Exception
Exemptions, safe harbors, and grandfathering provisions.
- **Examples**: Small Business Exemption, Research Exception
- **Key Properties**: scope, conditions, duration, beneficiaries
- **Use Case**: Identify compliance relief opportunities

#### ConsultationProcess
Public comment periods and stakeholder engagement.
- **Examples**: EU AI Act Public Consultation, FCC Net Neutrality Comments
- **Key Properties**: participants, submission_count, influence_on_outcome
- **Use Case**: Track opportunities for industry input

### Geographic/Temporal Entities

#### Jurisdiction
Countries, states, regions, and economic blocs.
- **Examples**: European Union, California, United Kingdom, Singapore
- **Key Properties**: legal_system, regulatory_approach, enforcement_capability
- **Use Case**: Map regulatory jurisdictions where companies operate

#### RegulatoryTerritory
Specific geographic areas where regulations apply.
- **Examples**: EU Single Market, US Interstate Commerce
- **Key Properties**: boundaries, regulatory_density, cross_border_coordination
- **Use Case**: Understand territorial scope of regulations

#### ComplianceDeadline
Time-bound compliance obligations and milestones.
- **Examples**: GDPR Compliance (May 25, 2018), PSD2 Strong Authentication
- **Key Properties**: deadline_date, penalty_for_delay, industry_readiness
- **Use Case**: Track critical compliance dates

#### ImplementationPhase
Rollout stages with different timelines and requirements.
- **Examples**: GDPR Phase 1: Data Mapping, Basel III Phase-in Period
- **Key Properties**: start_date, end_date, milestone_criteria
- **Use Case**: Plan phased compliance implementation

### Topic/Domain Entities

#### PolicyArea
Domains of policy focus and regulatory attention.
- **Examples**: Artificial Intelligence Governance, Data Protection, Financial Technology
- **Key Properties**: complexity_level, regulatory_maturity, business_impact_scope
- **Use Case**: Monitor regulatory developments by topic

#### TechnicalStandard
Specific technical requirements and standards.
- **Examples**: ISO 27001, PCI DSS, NIST Cybersecurity Framework
- **Key Properties**: issuing_body, mandatory_voluntary, compliance_testing
- **Use Case**: Track technical compliance requirements

#### RegulatoryRisk
Identified compliance risks for companies.
- **Examples**: Data Localization Requirements, AI Bias Liability
- **Key Properties**: probability, impact_severity, mitigation_strategies
- **Use Case**: Assess and manage regulatory risks

## Relationship Types

### Influence and Power

#### INFLUENCES
Who shapes policy decisions and regulatory outcomes.
- **Pattern**: LobbyGroup INFLUENCES Politician
- **Properties**: influence_type, strength, mechanism, duration
- **Use Case**: Map influence networks affecting your industry

#### LOBBIES_FOR / LOBBIES_AGAINST
Active support or opposition to policies.
- **Pattern**: Company LOBBIES_AGAINST Regulation
- **Properties**: position, resources_spent, tactics, success_probability
- **Use Case**: Track industry advocacy positions

### Business Impact

#### AFFECTS
Direct business impact relationships.
- **Pattern**: Policy AFFECTS Company
- **Properties**: impact_type, severity, timeline, cost_estimate
- **Use Case**: Assess how policies impact specific companies

#### SUBJECT_TO
What regulations apply to whom.
- **Pattern**: Company SUBJECT_TO Regulation
- **Properties**: applicability_scope, conditions, enforcement_probability
- **Use Case**: Map regulatory obligations for companies

#### REQUIRES_COMPLIANCE
Specific compliance obligations.
- **Pattern**: Regulation REQUIRES_COMPLIANCE Company
- **Properties**: deadline, penalty, monitoring_authority
- **Use Case**: Track specific compliance requirements

#### OPERATES_IN
Where companies do business.
- **Pattern**: Company OPERATES_IN Jurisdiction
- **Properties**: business_scope, market_share, regulatory_status
- **Use Case**: Map geographic regulatory exposure

### Regulatory Hierarchy

#### IMPLEMENTS
How policies become enforceable rules.
- **Pattern**: Regulation IMPLEMENTS Policy
- **Properties**: implementation_date, completeness, authority
- **Use Case**: Track policy implementation chain

#### ENFORCES
Who ensures compliance.
- **Pattern**: GovernmentAgency ENFORCES Regulation
- **Properties**: authority_scope, enforcement_tools, success_rate
- **Use Case**: Identify enforcement authorities

### Temporal Relationships

#### SUPERSEDES
Policy evolution and replacement.
- **Pattern**: New_Policy SUPERSEDES Old_Policy
- **Properties**: transition_date, grandfathering, sunset_provisions
- **Use Case**: Track regulatory evolution

#### TRIGGERS
Events that cause regulatory responses.
- **Pattern**: EnforcementAction TRIGGERS Policy
- **Properties**: trigger_event, response_timeline, precedent_value
- **Use Case**: Understand regulatory catalysts

## Usage Examples

### Example 1: GDPR Impact Analysis
```python
# Entities
gdpr = PolicyEntity(name="GDPR", stage=PolicyStage.ENFORCED, jurisdiction="EU")
google = CompanyEntity(name="Google", sector="Technology", jurisdictions_active=["EU", "US"])
data_transfer = BusinessActivity(name="Cross-Border Data Transfer", risk_level="high")

# Relationships
gdpr_affects_google = BusinessImpactRelationship(
    source_entity="GDPR",
    target_entity="Google", 
    relationship_type="AFFECTS",
    impact_severity=ImpactSeverity.HIGH,
    cost_estimate=50000000
)
```

### Example 2: EU AI Act Lobbying
```python
# Entities
ai_act = PolicyEntity(name="EU AI Act", stage=PolicyStage.CONSULTATION)
digitaleurope = LobbyGroup(name="DigitalEurope", type="Industry Association")
ai_exception = Exception(name="AI Research Exception", scope="Academic Research")

# Relationships
digitaleurope_lobbies = InfluenceRelationship(
    source_entity="DigitalEurope",
    target_entity="EU AI Act",
    relationship_type="LOBBIES_FOR",
    resources_involved=2000000,
    tactics=["position_papers", "stakeholder_meetings"]
)
```

## Integration with MCP

The schema is designed to work seamlessly with the Graphiti MCP server:

```python
# Add policy episode via MCP
episode_result = await graphiti_client.add_episode(
    name="EU AI Act Amendment",
    content="The European Parliament approved amendments to the AI Act...",
    metadata={
        "type": "policy_update",
        "entities": ["EU AI Act", "European Parliament", "AI regulation"],
        "impact_severity": "high"
    }
)

# Search for related entities
search_results = await graphiti_client.search(
    "AI regulation amendments affecting tech companies",
    max_nodes=20
)
```

## Schema Evolution

### Version History
- **v1.0**: Basic political entities (Policy, Politician, Organization)
- **v2.0**: Enhanced business-centric schema with compliance tracking

### Future Enhancements
- **v2.1**: ESG and sustainability regulations
- **v2.2**: International trade and sanctions
- **v2.3**: Sector-specific regulatory modules (healthcare, finance, tech)

## Best Practices

### 1. Entity Naming
- Use official names for policies and regulations
- Include jurisdiction in ambiguous cases ("CCPA (California)" vs "CCPA (Canada)")
- Use consistent company legal names

### 2. Relationship Properties
- Always include temporal information (start_date, end_date)
- Estimate impact severity and costs where possible
- Track confidence scores for extracted relationships

### 3. Compliance Tracking
- Set up monitoring for compliance deadlines
- Track implementation phases separately
- Document exceptions and exemptions

### 4. Cross-Reference Validation
- Validate entity types against schema definitions
- Check relationship patterns for consistency
- Maintain referential integrity between related entities

## Implementation Notes

### Required Dependencies
```python
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
```

### Schema Validation
```python
# Validate entity type
assert validate_entity_type("Company") == True

# Validate relationship pattern
assert validate_relationship_pattern("Policy", "AFFECTS", "Company") == True

# Get entity properties
props = get_entity_properties("ComplianceObligation")
```

### Model Creation
```python
# Create entities from dictionaries
entity_data = {"name": "GDPR", "entity_type": "Policy", "jurisdiction": "EU"}
entity = create_entity_from_dict(entity_data)

# Create relationships
rel_data = {"source_entity": "GDPR", "target_entity": "Google", "relationship_type": "AFFECTS"}
relationship = create_relationship_from_dict(rel_data)
```

This schema provides the foundation for comprehensive political monitoring and business impact analysis, enabling organizations to proactively manage regulatory risks and opportunities.