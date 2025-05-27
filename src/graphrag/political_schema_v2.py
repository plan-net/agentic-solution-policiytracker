"""
Enhanced Political Domain Schema for Company Impact Analysis.

This schema is designed to comprehensively track how political and regulatory 
changes affect companies through multi-layered regulatory hierarchy, business 
impact mapping, stakeholder influence networks, and temporal policy lifecycles.

Version: 2.0
Last Updated: 2025-05-27
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field


class PolicyStage(str, Enum):
    """Stages in the policy lifecycle."""
    DRAFT = "draft"
    CONSULTATION = "consultation"
    PROPOSED = "proposed"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    ENACTED = "enacted"
    IMPLEMENTED = "implemented"
    ENFORCED = "enforced"
    AMENDED = "amended"
    REPEALED = "repealed"


class ImpactSeverity(str, Enum):
    """Severity levels for business impact assessment."""
    MINIMAL = "minimal"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class JurisdictionLevel(str, Enum):
    """Hierarchical levels of jurisdiction."""
    GLOBAL = "global"
    SUPRANATIONAL = "supranational"  # EU, ASEAN, etc.
    NATIONAL = "national"
    SUBNATIONAL = "subnational"  # States, provinces
    LOCAL = "local"


class ComplianceStatus(str, Enum):
    """Status of compliance obligations."""
    NOT_APPLICABLE = "not_applicable"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    UNDER_REVIEW = "under_review"
    EXEMPTED = "exempted"


# === ENTITY DEFINITIONS ===

ENHANCED_POLITICAL_ENTITIES = {
    # === CORE POLITICAL ENTITIES ===
    "Policy": {
        "description": "High-level laws, acts, directives, and policy frameworks",
        "properties": [
            "name", "description", "policy_type", "stage", "jurisdiction",
            "date_introduced", "date_enacted", "date_effective", "sponsor",
            "legal_basis", "scope", "objectives", "budget_impact"
        ],
        "examples": ["EU AI Act", "California Privacy Rights Act", "UK Online Safety Bill"]
    },
    
    "Regulation": {
        "description": "Implementing rules, technical standards, and detailed requirements",
        "properties": [
            "name", "regulation_number", "parent_policy", "authority",
            "effective_date", "compliance_deadline", "technical_requirements",
            "enforcement_mechanism", "penalty_structure", "review_cycle"
        ],
        "examples": ["GDPR Article 25 (Privacy by Design)", "SOX Section 404", "Basel III Capital Requirements"]
    },
    
    "Politician": {
        "description": "Individual decision makers, elected officials, and appointees",
        "properties": [
            "name", "title", "party", "jurisdiction", "role", "committee_memberships",
            "policy_positions", "voting_record", "influence_score", "term_dates",
            "contact_info", "constituencies"
        ],
        "examples": ["Margrethe Vestager", "Elizabeth Warren", "Thierry Breton"]
    },
    
    "PoliticalParty": {
        "description": "Political parties and their collective positions",
        "properties": [
            "name", "ideology", "jurisdiction", "seats_held", "leadership",
            "policy_platform", "business_stance", "regulatory_approach",
            "coalition_partnerships", "electoral_strength"
        ],
        "examples": ["European People's Party", "Democratic Party", "Conservative Party"]
    },
    
    "GovernmentAgency": {
        "description": "Regulatory bodies, enforcement agencies, and government departments",
        "properties": [
            "name", "jurisdiction", "mandate", "regulatory_powers", "enforcement_authority",
            "budget", "staff_size", "leadership", "reporting_structure",
            "sector_focus", "international_cooperation"
        ],
        "examples": ["European Commission DG COMP", "US SEC", "UK ICO", "German BaFin"]
    },
    
    "LobbyGroup": {
        "description": "Industry associations, advocacy groups, and influence organizations",
        "properties": [
            "name", "type", "members", "budget", "policy_focus", "lobbying_spend",
            "registered_lobbyists", "political_connections", "influence_tactics",
            "position_papers", "coalition_memberships"
        ],
        "examples": ["DigitalEurope", "CCIA", "Financial Services Roundtable", "EDPB"]
    },
    
    # === BUSINESS/ECONOMIC ENTITIES ===
    "Company": {
        "description": "Individual corporations and business entities",
        "properties": [
            "name", "sector", "size", "revenue", "headquarters", "jurisdictions_active",
            "business_model", "data_practices", "regulatory_history", "compliance_status",
            "subsidiaries", "public_private", "stock_ticker", "key_executives"
        ],
        "examples": ["Apple Inc.", "Volkswagen AG", "JPMorgan Chase", "Spotify"]
    },
    
    "Industry": {
        "description": "Business sectors and industry classifications",
        "properties": [
            "name", "classification_code", "description", "size", "key_players",
            "regulatory_intensity", "innovation_rate", "market_concentration",
            "employment", "contribution_to_gdp", "trade_associations"
        ],
        "examples": ["Financial Technology", "Automotive", "Social Media Platforms", "Biotechnology"]
    },
    
    "BusinessActivity": {
        "description": "Specific business practices that get regulated",
        "properties": [
            "name", "description", "risk_level", "regulatory_coverage", "technology_involved",
            "data_implications", "cross_border_nature", "innovation_impact",
            "standardization_level", "enforcement_frequency"
        ],
        "examples": ["Algorithmic Decision Making", "Cross-Border Data Transfer", "High-Frequency Trading"]
    },
    
    "Market": {
        "description": "Geographic or product markets where companies compete",
        "properties": [
            "name", "geographic_scope", "product_category", "market_size", "growth_rate",
            "concentration_ratio", "barriers_to_entry", "regulatory_framework",
            "competitive_dynamics", "consumer_protection_level"
        ],
        "examples": ["EU Digital Single Market", "US Healthcare Market", "Global Cloud Services"]
    },
    
    "ComplianceObligation": {
        "description": "Specific requirements companies must meet",
        "properties": [
            "requirement", "deadline", "penalty", "scope", "authority", "status",
            "implementation_cost", "complexity_level", "frequency", "documentation_required",
            "third_party_involvement", "cross_reference"
        ],
        "examples": ["Annual Privacy Impact Assessment", "Quarterly Capital Reporting", "AI System Registration"]
    },
    
    # === LEGAL/PROCESS ENTITIES ===
    "LegalFramework": {
        "description": "Broader legal context and constitutional foundations",
        "properties": [
            "name", "jurisdiction", "legal_basis", "hierarchy_level", "scope",
            "fundamental_rights", "enforcement_mechanisms", "amendment_process",
            "international_treaties", "precedent_system"
        ],
        "examples": ["GDPR Framework", "US Constitutional Commerce Clause", "WTO Trade Rules"]
    },
    
    "PolicyStage": {
        "description": "Specific phases in policy development and implementation",
        "properties": [
            "stage_name", "description", "typical_duration", "key_stakeholders",
            "decision_points", "public_participation", "appeal_mechanisms",
            "documentation_requirements", "transparency_level"
        ],
        "examples": ["Public Consultation Phase", "Committee Review", "Parliamentary Vote"]
    },
    
    "EnforcementAction": {
        "description": "Fines, investigations, sanctions, and enforcement measures",
        "properties": [
            "action_type", "target", "authority", "date", "amount", "reason",
            "legal_basis", "appeal_status", "precedent_value", "settlement_terms",
            "compliance_measures", "monitoring_requirements"
        ],
        "examples": ["€4.3B Google Android Fine", "Wells Fargo Consent Order", "Facebook FTC Settlement"]
    },
    
    "Exception": {
        "description": "Exemptions, safe harbors, and grandfathering provisions",
        "properties": [
            "exception_type", "scope", "conditions", "duration", "beneficiaries",
            "justification", "review_mechanism", "expiry_date", "renewal_process",
            "reporting_requirements", "limitations"
        ],
        "examples": ["Small Business Exemption", "Research Exception", "Existing Contract Grandfathering"]
    },
    
    "ConsultationProcess": {
        "description": "Public comment periods and stakeholder engagement",
        "properties": [
            "name", "authority", "start_date", "end_date", "scope", "participants",
            "submission_count", "key_themes", "influence_on_outcome", "transparency_level",
            "methodology", "follow_up_actions"
        ],
        "examples": ["EU AI Act Public Consultation", "FCC Net Neutrality Comments", "Basel III Industry Feedback"]
    },
    
    # === GEOGRAPHIC/TEMPORAL ENTITIES ===
    "Jurisdiction": {
        "description": "Countries, states, regions, and economic blocs",
        "properties": [
            "name", "type", "level", "parent_jurisdiction", "legal_system",
            "regulatory_approach", "enforcement_capability", "international_agreements",
            "economic_size", "political_stability", "business_environment_rank"
        ],
        "examples": ["European Union", "California", "United Kingdom", "Singapore"]
    },
    
    "RegulatoryTerritory": {
        "description": "Specific geographic areas where regulations apply",
        "properties": [
            "name", "boundaries", "population", "economic_activity", "regulatory_density",
            "enforcement_resources", "compliance_costs", "business_impact",
            "cross_border_coordination", "harmonization_level"
        ],
        "examples": ["EU Single Market", "US Interstate Commerce", "ASEAN Economic Community"]
    },
    
    "ComplianceDeadline": {
        "description": "Time-bound compliance obligations and milestones",
        "properties": [
            "deadline_date", "requirement", "penalty_for_delay", "extension_possibility",
            "notification_requirements", "grace_period", "enforcement_likelihood",
            "preparation_time_needed", "industry_readiness", "implementation_support"
        ],
        "examples": ["GDPR Compliance (May 25, 2018)", "PSD2 Strong Authentication (Dec 31, 2020)"]
    },
    
    "ImplementationPhase": {
        "description": "Rollout stages with different timelines and requirements",
        "properties": [
            "phase_name", "start_date", "end_date", "requirements", "affected_entities",
            "milestone_criteria", "success_metrics", "support_mechanisms",
            "escalation_procedures", "feedback_loops", "adjustment_mechanisms"
        ],
        "examples": ["GDPR Phase 1: Data Mapping", "Basel III Phase-in Period", "AI Act Grace Period"]
    },
    
    # === TOPIC/DOMAIN ENTITIES ===
    "PolicyArea": {
        "description": "Domains of policy focus and regulatory attention",
        "properties": [
            "name", "description", "complexity_level", "stakeholder_diversity",
            "innovation_pace", "regulatory_maturity", "international_coordination",
            "business_impact_scope", "consumer_interest", "technical_expertise_required"
        ],
        "examples": ["Artificial Intelligence Governance", "Data Protection", "Financial Technology", "Climate Policy"]
    },
    
    "TechnicalStandard": {
        "description": "Specific technical requirements and standards",
        "properties": [
            "standard_name", "version", "issuing_body", "mandatory_voluntary",
            "technical_specifications", "compliance_testing", "certification_required",
            "international_recognition", "update_frequency", "industry_adoption"
        ],
        "examples": ["ISO 27001", "PCI DSS", "NIST Cybersecurity Framework", "IEEE AI Ethics Standards"]
    },
    
    "RegulatoryRisk": {
        "description": "Identified compliance risks for companies",
        "properties": [
            "risk_type", "probability", "impact_severity", "affected_companies",
            "mitigation_strategies", "monitoring_indicators", "early_warning_signs",
            "cost_of_non_compliance", "competitive_implications", "timeline"
        ],
        "examples": ["Data Localization Requirements", "AI Bias Liability", "ESG Reporting Gaps"]
    }
}

# === RELATIONSHIP DEFINITIONS ===

ENHANCED_POLITICAL_RELATIONSHIPS = {
    # === INFLUENCE AND POWER ===
    "INFLUENCES": {
        "description": "Who shapes policy decisions and regulatory outcomes",
        "properties": ["influence_type", "strength", "mechanism", "duration", "reciprocal"],
        "patterns": [
            ("LobbyGroup", "INFLUENCES", "Politician"),
            ("Industry", "INFLUENCES", "GovernmentAgency"),
            ("Company", "INFLUENCES", "PolicyArea"),
            ("PoliticalParty", "INFLUENCES", "Policy")
        ]
    },
    
    "LOBBIES_FOR": {
        "description": "Active support and advocacy for policies",
        "properties": ["position", "resources_spent", "tactics", "success_probability"],
        "patterns": [
            ("Company", "LOBBIES_FOR", "Policy"),
            ("LobbyGroup", "LOBBIES_FOR", "Regulation"),
            ("Industry", "LOBBIES_FOR", "Exception")
        ]
    },
    
    "LOBBIES_AGAINST": {
        "description": "Active opposition and resistance to policies",
        "properties": ["objections", "resources_spent", "alternative_proposals", "coalition_building"],
        "patterns": [
            ("Company", "LOBBIES_AGAINST", "Regulation"),
            ("Industry", "LOBBIES_AGAINST", "ComplianceObligation"),
            ("LobbyGroup", "LOBBIES_AGAINST", "Policy")
        ]
    },
    
    # === BUSINESS IMPACT ===
    "AFFECTS": {
        "description": "Direct business impact relationships",
        "properties": ["impact_type", "severity", "timeline", "cost_estimate", "mitigation_possible"],
        "patterns": [
            ("Policy", "AFFECTS", "Company"),
            ("Regulation", "AFFECTS", "Industry"),
            ("ComplianceObligation", "AFFECTS", "BusinessActivity"),
            ("EnforcementAction", "AFFECTS", "Market")
        ]
    },
    
    "SUBJECT_TO": {
        "description": "What regulations apply to whom",
        "properties": ["applicability_scope", "conditions", "exceptions", "enforcement_probability"],
        "patterns": [
            ("Company", "SUBJECT_TO", "Regulation"),
            ("BusinessActivity", "SUBJECT_TO", "ComplianceObligation"),
            ("Industry", "SUBJECT_TO", "TechnicalStandard"),
            ("Market", "SUBJECT_TO", "LegalFramework")
        ]
    },
    
    "REQUIRES_COMPLIANCE": {
        "description": "Specific compliance obligations",
        "properties": ["deadline", "penalty", "monitoring_authority", "reporting_frequency"],
        "patterns": [
            ("Regulation", "REQUIRES_COMPLIANCE", "Company"),
            ("Policy", "REQUIRES_COMPLIANCE", "Industry"),
            ("TechnicalStandard", "REQUIRES_COMPLIANCE", "BusinessActivity")
        ]
    },
    
    "OPERATES_IN": {
        "description": "Where companies do business",
        "properties": ["business_scope", "market_share", "regulatory_status", "compliance_history"],
        "patterns": [
            ("Company", "OPERATES_IN", "Jurisdiction"),
            ("Industry", "OPERATES_IN", "Market"),
            ("BusinessActivity", "OPERATES_IN", "RegulatoryTerritory")
        ]
    },
    
    "COMPETES_IN": {
        "description": "Market competition relationships",
        "properties": ["market_position", "competitive_advantage", "regulatory_arbitrage"],
        "patterns": [
            ("Company", "COMPETES_IN", "Market"),
            ("BusinessActivity", "COMPETES_IN", "PolicyArea")
        ]
    },
    
    # === REGULATORY HIERARCHY ===
    "IMPLEMENTS": {
        "description": "How policies become enforceable rules",
        "properties": ["implementation_date", "completeness", "authority", "adaptation_required"],
        "patterns": [
            ("Regulation", "IMPLEMENTS", "Policy"),
            ("ComplianceObligation", "IMPLEMENTS", "Regulation"),
            ("TechnicalStandard", "IMPLEMENTS", "LegalFramework"),
            ("EnforcementAction", "IMPLEMENTS", "ComplianceObligation")
        ]
    },
    
    "ENFORCES": {
        "description": "Who ensures compliance",
        "properties": ["authority_scope", "enforcement_tools", "success_rate", "resource_allocation"],
        "patterns": [
            ("GovernmentAgency", "ENFORCES", "Regulation"),
            ("Jurisdiction", "ENFORCES", "Policy"),
            ("RegulatoryTerritory", "ENFORCES", "ComplianceObligation")
        ]
    },
    
    "DELEGATES_TO": {
        "description": "Regulatory authority delegation",
        "properties": ["scope", "conditions", "oversight_mechanism", "revocation_conditions"],
        "patterns": [
            ("GovernmentAgency", "DELEGATES_TO", "Industry"),
            ("Jurisdiction", "DELEGATES_TO", "GovernmentAgency"),
            ("Policy", "DELEGATES_TO", "TechnicalStandard")
        ]
    },
    
    # === TEMPORAL RELATIONSHIPS ===
    "SUPERSEDES": {
        "description": "Policy evolution and replacement",
        "properties": ["transition_date", "reason", "grandfathering", "sunset_provisions"],
        "patterns": [
            ("Policy", "SUPERSEDES", "Policy"),
            ("Regulation", "SUPERSEDES", "Regulation"),
            ("TechnicalStandard", "SUPERSEDES", "TechnicalStandard")
        ]
    },
    
    "AMENDS": {
        "description": "Modifications to existing rules",
        "properties": ["amendment_date", "change_type", "sections_modified", "impact_assessment"],
        "patterns": [
            ("Policy", "AMENDS", "Policy"),
            ("Regulation", "AMENDS", "Regulation"),
            ("Exception", "AMENDS", "ComplianceObligation")
        ]
    },
    
    "TRIGGERS": {
        "description": "Events that cause regulatory responses",
        "properties": ["trigger_event", "response_timeline", "scope", "precedent_value"],
        "patterns": [
            ("EnforcementAction", "TRIGGERS", "Policy"),
            ("BusinessActivity", "TRIGGERS", "Regulation"),
            ("Market", "TRIGGERS", "ConsultationProcess")
        ]
    },
    
    "PRECEDES": {
        "description": "Sequential relationships in policy development",
        "properties": ["sequence_order", "dependency_type", "timeline", "conditional_relationship"],
        "patterns": [
            ("ConsultationProcess", "PRECEDES", "Policy"),
            ("PolicyStage", "PRECEDES", "PolicyStage"),
            ("ComplianceDeadline", "PRECEDES", "EnforcementAction")
        ]
    },
    
    # === REFERENCE AND COORDINATION ===
    "REFERENCES": {
        "description": "Citations and cross-references between documents",
        "properties": ["citation_type", "section", "relevance", "interpretation"],
        "patterns": [
            ("Policy", "REFERENCES", "LegalFramework"),
            ("Regulation", "REFERENCES", "TechnicalStandard"),
            ("ComplianceObligation", "REFERENCES", "PolicyArea")
        ]
    },
    
    "HARMONIZES_WITH": {
        "description": "International coordination and alignment",
        "properties": ["harmonization_level", "coordination_mechanism", "differences", "convergence_timeline"],
        "patterns": [
            ("Policy", "HARMONIZES_WITH", "Policy"),
            ("Jurisdiction", "HARMONIZES_WITH", "Jurisdiction"),
            ("TechnicalStandard", "HARMONIZES_WITH", "TechnicalStandard")
        ]
    },
    
    "CONFLICTS_WITH": {
        "description": "Regulatory conflicts and inconsistencies",
        "properties": ["conflict_type", "resolution_mechanism", "affected_parties", "priority_rules"],
        "patterns": [
            ("Regulation", "CONFLICTS_WITH", "Regulation"),
            ("Jurisdiction", "CONFLICTS_WITH", "Jurisdiction"),
            ("ComplianceObligation", "CONFLICTS_WITH", "ComplianceObligation")
        ]
    },
    
    # === STAKEHOLDER RELATIONSHIPS ===
    "REPRESENTS": {
        "description": "Representation and advocacy relationships",
        "properties": ["representation_type", "constituency", "mandate", "accountability"],
        "patterns": [
            ("Politician", "REPRESENTS", "Jurisdiction"),
            ("LobbyGroup", "REPRESENTS", "Industry"),
            ("PoliticalParty", "REPRESENTS", "PolicyArea")
        ]
    },
    
    "ADVISES": {
        "description": "Advisory and consultative relationships",
        "properties": ["advice_type", "frequency", "influence_level", "expertise_area"],
        "patterns": [
            ("Industry", "ADVISES", "GovernmentAgency"),
            ("LobbyGroup", "ADVISES", "Politician"),
            ("Company", "ADVISES", "ConsultationProcess")
        ]
    },
    
    "MONITORS": {
        "description": "Oversight and monitoring relationships",
        "properties": ["monitoring_scope", "frequency", "reporting_requirements", "corrective_powers"],
        "patterns": [
            ("GovernmentAgency", "MONITORS", "Company"),
            ("Jurisdiction", "MONITORS", "Industry"),
            ("PolicyArea", "MONITORS", "BusinessActivity")
        ]
    }
}

# === SCHEMA VALIDATION PATTERNS ===

POLITICAL_SCHEMA_PATTERNS = [
    # Core policy creation and implementation
    ("Politician", "INFLUENCES", "Policy"),
    ("Policy", "IMPLEMENTS", "Regulation"),
    ("GovernmentAgency", "ENFORCES", "Regulation"),
    ("Company", "SUBJECT_TO", "Regulation"),
    
    # Business impact chains
    ("Policy", "AFFECTS", "Industry"),
    ("Industry", "OPERATES_IN", "Market"),
    ("Market", "SUBJECT_TO", "RegulatoryTerritory"),
    ("Company", "REQUIRES_COMPLIANCE", "ComplianceObligation"),
    
    # Influence networks
    ("LobbyGroup", "REPRESENTS", "Industry"),
    ("Industry", "LOBBIES_FOR", "Exception"),
    ("Company", "LOBBIES_AGAINST", "Regulation"),
    ("PoliticalParty", "INFLUENCES", "GovernmentAgency"),
    
    # Temporal evolution
    ("ConsultationProcess", "PRECEDES", "Policy"),
    ("Policy", "SUPERSEDES", "Policy"),
    ("EnforcementAction", "TRIGGERS", "PolicyArea"),
    ("ComplianceDeadline", "PRECEDES", "EnforcementAction"),
    
    # Cross-jurisdictional
    ("Jurisdiction", "HARMONIZES_WITH", "Jurisdiction"),
    ("Policy", "REFERENCES", "LegalFramework"),
    ("RegulatoryTerritory", "CONFLICTS_WITH", "RegulatoryTerritory"),
    
    # Risk and compliance
    ("RegulatoryRisk", "AFFECTS", "BusinessActivity"),
    ("TechnicalStandard", "IMPLEMENTS", "PolicyArea"),
    ("Exception", "AMENDS", "ComplianceObligation")
]


def get_enhanced_extraction_prompt() -> str:
    """Get the comprehensive LLM prompt for political entity and relationship extraction."""
    return """
You are an expert in political, regulatory, and business analysis. Extract entities and relationships from the given text that are relevant for tracking how political and regulatory changes affect companies.

FOCUS ON BUSINESS IMPACT: Prioritize information that helps understand:
1. How regulations affect specific companies and industries
2. Who has influence over policy decisions
3. Compliance requirements and deadlines
4. Enforcement actions and their precedent value
5. Cross-jurisdictional regulatory complexity

=== POLITICAL ENTITIES ===
- Policy: High-level laws, acts, directives (EU AI Act, CCPA, SOX)
- Regulation: Implementing rules, technical standards (GDPR Art. 25, Basel III)
- Politician: Decision makers, officials (commissioners, ministers, regulators)
- PoliticalParty: Party positions on business regulation
- GovernmentAgency: Regulatory bodies (SEC, ICO, BaFin, European Commission)
- LobbyGroup: Industry associations, advocacy groups (DigitalEurope, CCIA)

=== BUSINESS ENTITIES ===
- Company: Specific corporations (Apple, Volkswagen, JPMorgan)
- Industry: Business sectors (fintech, automotive, social media)
- BusinessActivity: Regulated practices (AI deployment, data transfer, trading)
- Market: Geographic/product markets (EU Digital Market, US Healthcare)
- ComplianceObligation: Specific requirements (annual reporting, impact assessments)

=== LEGAL/PROCESS ENTITIES ===
- LegalFramework: Constitutional/treaty basis (GDPR framework, Commerce Clause)
- PolicyStage: Development phases (consultation, enacted, implemented)
- EnforcementAction: Fines, sanctions, investigations (Google Android fine)
- Exception: Exemptions, safe harbors, grandfathering
- ConsultationProcess: Public comment periods, stakeholder input

=== GEOGRAPHIC/TEMPORAL ===
- Jurisdiction: Countries, regions, economic blocs (EU, California, UK)
- RegulatoryTerritory: Where rules apply (Single Market, Interstate Commerce)
- ComplianceDeadline: Time-bound obligations with specific dates
- ImplementationPhase: Rollout stages with different timelines

=== DOMAIN/TOPIC ===
- PolicyArea: Regulatory domains (AI governance, data protection, fintech)
- TechnicalStandard: Specific standards (ISO 27001, PCI DSS, NIST)
- RegulatoryRisk: Compliance risks for companies

=== KEY RELATIONSHIPS ===
- AFFECTS: Direct business impact (Policy AFFECTS Company)
- INFLUENCES: Who shapes decisions (LobbyGroup INFLUENCES Politician)
- REQUIRES_COMPLIANCE: Specific obligations (Regulation REQUIRES_COMPLIANCE Company)
- SUBJECT_TO: What rules apply (Company SUBJECT_TO Regulation)
- IMPLEMENTS: How policies become rules (Regulation IMPLEMENTS Policy)
- ENFORCES: Who ensures compliance (GovernmentAgency ENFORCES Regulation)
- OPERATES_IN: Where companies do business (Company OPERATES_IN Jurisdiction)
- LOBBIES_FOR/AGAINST: Influence direction (Industry LOBBIES_AGAINST Regulation)
- SUPERSEDES: Policy evolution (New_Policy SUPERSEDES Old_Policy)
- TRIGGERS: Events causing responses (EnforcementAction TRIGGERS Policy)

EXTRACTION GUIDELINES:
1. Extract NAMED entities (specific companies, laws, people, not generic terms)
2. Focus on BUSINESS RELEVANCE (how does this affect companies?)
3. Capture TEMPORAL aspects (when do requirements take effect?)
4. Identify INFLUENCE NETWORKS (who has power to shape outcomes?)
5. Map COMPLIANCE CHAINS (policy → regulation → obligation → enforcement)
6. Note CROSS-BORDER implications (EU rules affecting US companies)

Be precise and only extract entities/relationships that are explicitly mentioned or clearly implied in the text.
"""


# === PYDANTIC MODELS FOR VALIDATION ===

class PoliticalEntity(BaseModel):
    """Base model for all political entities."""
    name: str = Field(..., description="Entity name")
    entity_type: str = Field(..., description="Type of entity")
    description: Optional[str] = Field(None, description="Entity description")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Entity-specific properties")
    jurisdiction: Optional[str] = Field(None, description="Primary jurisdiction")
    created_date: Optional[datetime] = Field(None, description="When entity was created/identified")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Extraction confidence")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PoliticalRelationship(BaseModel):
    """Base model for all political relationships."""
    source_entity: str = Field(..., description="Source entity name")
    target_entity: str = Field(..., description="Target entity name")
    relationship_type: str = Field(..., description="Type of relationship")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Relationship-specific properties")
    start_date: Optional[datetime] = Field(None, description="When relationship started")
    end_date: Optional[datetime] = Field(None, description="When relationship ended")
    strength: Optional[float] = Field(None, ge=0.0, le=1.0, description="Relationship strength")
    bidirectional: bool = Field(False, description="Whether relationship is bidirectional")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Extraction confidence")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PolicyEntity(PoliticalEntity):
    """Specific model for Policy entities."""
    entity_type: str = Field(default="Policy")
    stage: Optional[PolicyStage] = Field(None, description="Current stage in policy lifecycle")
    date_introduced: Optional[datetime] = Field(None, description="When policy was first introduced")
    date_enacted: Optional[datetime] = Field(None, description="When policy was enacted")
    date_effective: Optional[datetime] = Field(None, description="When policy takes effect")
    sponsor: Optional[str] = Field(None, description="Primary sponsor or author")
    legal_basis: Optional[str] = Field(None, description="Legal foundation for the policy")
    scope: Optional[str] = Field(None, description="Scope of policy application")


class CompanyEntity(PoliticalEntity):
    """Specific model for Company entities."""
    entity_type: str = Field(default="Company")
    sector: Optional[str] = Field(None, description="Industry sector")
    size: Optional[str] = Field(None, description="Company size (small, medium, large, multinational)")
    revenue: Optional[float] = Field(None, description="Annual revenue")
    headquarters: Optional[str] = Field(None, description="Headquarters location")
    jurisdictions_active: List[str] = Field(default_factory=list, description="Jurisdictions where company operates")
    business_model: Optional[str] = Field(None, description="Primary business model")
    public_private: Optional[str] = Field(None, description="Public or private company")
    stock_ticker: Optional[str] = Field(None, description="Stock ticker symbol if public")


class ComplianceObligationEntity(PoliticalEntity):
    """Specific model for Compliance Obligation entities."""
    entity_type: str = Field(default="ComplianceObligation")
    requirement: str = Field(..., description="Specific compliance requirement")
    deadline: Optional[datetime] = Field(None, description="Compliance deadline")
    penalty: Optional[str] = Field(None, description="Penalty for non-compliance")
    authority: Optional[str] = Field(None, description="Enforcing authority")
    status: Optional[ComplianceStatus] = Field(None, description="Current compliance status")
    implementation_cost: Optional[float] = Field(None, description="Estimated cost of compliance")
    complexity_level: Optional[str] = Field(None, description="Implementation complexity")


class BusinessImpactRelationship(PoliticalRelationship):
    """Specific model for business impact relationships."""
    impact_severity: Optional[ImpactSeverity] = Field(None, description="Severity of business impact")
    cost_estimate: Optional[float] = Field(None, description="Estimated financial impact")
    timeline: Optional[str] = Field(None, description="Timeline for impact realization")
    mitigation_possible: bool = Field(True, description="Whether impact can be mitigated")
    competitive_advantage: Optional[str] = Field(None, description="Competitive implications")


class InfluenceRelationship(PoliticalRelationship):
    """Specific model for influence relationships."""
    influence_type: Optional[str] = Field(None, description="Type of influence mechanism")
    resources_involved: Optional[float] = Field(None, description="Resources spent on influence")
    success_probability: Optional[float] = Field(None, ge=0.0, le=1.0, description="Likelihood of success")
    tactics: List[str] = Field(default_factory=list, description="Influence tactics used")
    transparency_level: Optional[str] = Field(None, description="Public visibility of influence")


class ExtractionResult(BaseModel):
    """Container for extraction results."""
    entities: List[PoliticalEntity] = Field(default_factory=list, description="Extracted entities")
    relationships: List[PoliticalRelationship] = Field(default_factory=list, description="Extracted relationships")
    document_id: Optional[str] = Field(None, description="Source document identifier")
    extraction_timestamp: datetime = Field(default_factory=datetime.now, description="When extraction was performed")
    extraction_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Overall extraction confidence")
    processing_metadata: Dict[str, Any] = Field(default_factory=dict, description="Processing metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# === SCHEMA UTILITIES ===

def validate_entity_type(entity_type: str) -> bool:
    """Validate that an entity type is defined in the schema."""
    return entity_type in ENHANCED_POLITICAL_ENTITIES


def validate_relationship_type(relationship_type: str) -> bool:
    """Validate that a relationship type is defined in the schema."""
    return relationship_type in ENHANCED_POLITICAL_RELATIONSHIPS


def get_entity_properties(entity_type: str) -> List[str]:
    """Get the defined properties for an entity type."""
    return ENHANCED_POLITICAL_ENTITIES.get(entity_type, {}).get("properties", [])


def get_relationship_properties(relationship_type: str) -> List[str]:
    """Get the defined properties for a relationship type."""
    return ENHANCED_POLITICAL_RELATIONSHIPS.get(relationship_type, {}).get("properties", [])


def validate_relationship_pattern(source_type: str, relationship_type: str, target_type: str) -> bool:
    """Validate that a relationship pattern is allowed in the schema."""
    relationship_def = ENHANCED_POLITICAL_RELATIONSHIPS.get(relationship_type, {})
    patterns = relationship_def.get("patterns", [])
    return (source_type, relationship_type, target_type) in patterns


def get_entity_examples(entity_type: str) -> List[str]:
    """Get example entities for a given type."""
    return ENHANCED_POLITICAL_ENTITIES.get(entity_type, {}).get("examples", [])


def create_entity_from_dict(data: Dict) -> PoliticalEntity:
    """Create appropriate entity model from dictionary data."""
    entity_type = data.get("entity_type", "")
    
    # Map to specific entity models
    entity_models = {
        "Policy": PolicyEntity,
        "Company": CompanyEntity,
        "ComplianceObligation": ComplianceObligationEntity,
    }
    
    model_class = entity_models.get(entity_type, PoliticalEntity)
    return model_class(**data)


def create_relationship_from_dict(data: Dict) -> PoliticalRelationship:
    """Create appropriate relationship model from dictionary data."""
    relationship_type = data.get("relationship_type", "")
    
    # Map to specific relationship models
    if relationship_type in ["AFFECTS", "SUBJECT_TO", "REQUIRES_COMPLIANCE"]:
        return BusinessImpactRelationship(**data)
    elif relationship_type in ["INFLUENCES", "LOBBIES_FOR", "LOBBIES_AGAINST"]:
        return InfluenceRelationship(**data)
    else:
        return PoliticalRelationship(**data)


# === SCHEMA METADATA ===

SCHEMA_VERSION = "2.0"
SCHEMA_LAST_UPDATED = "2025-05-27"
SCHEMA_DESCRIPTION = """
Enhanced Political Domain Schema for Company Impact Analysis

This schema provides comprehensive modeling of political and regulatory ecosystems
with a focus on understanding how policy changes affect business operations.

Key Features:
- Multi-layered regulatory hierarchy (Policy → Regulation → Implementation → Enforcement)
- Business impact mapping with severity and cost estimation
- Stakeholder influence networks and lobbying relationships
- Temporal policy lifecycles with implementation phases
- Cross-jurisdictional regulatory complexity
- Granular compliance obligations and deadlines

Use Cases:
- Political risk assessment for companies
- Regulatory change impact analysis
- Compliance planning and timeline management
- Stakeholder influence mapping
- Cross-border regulatory coordination
- Policy development monitoring
"""

SCHEMA_STATISTICS = {
    "total_entity_types": len(ENHANCED_POLITICAL_ENTITIES),
    "total_relationship_types": len(ENHANCED_POLITICAL_RELATIONSHIPS),
    "total_patterns": len(POLITICAL_SCHEMA_PATTERNS),
    "categories": {
        "political_entities": 6,
        "business_entities": 5,
        "legal_process_entities": 5,
        "geographic_temporal_entities": 4,
        "domain_topic_entities": 3
    }
}