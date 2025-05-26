"""Political domain schema for Neo4j GraphRAG."""

from typing import Dict, List

# Political monitoring domain schema for SimpleKGPipeline
POLITICAL_SCHEMA = {
    "node_types": [
        "Policy",
        "Politician", 
        "Organization",
        "Regulation",
        "Event",
        "Topic",
        "Jurisdiction",
        "Amendment",
        "Compliance"
    ],
    "relationship_types": [
        "AUTHORED_BY",
        "AFFECTS", 
        "OPPOSES",
        "SUPPORTS",
        "RELATES_TO",
        "REFERENCES",
        "IMPLEMENTS",
        "SUPERSEDES",
        "AMENDS",
        "REQUIRES_COMPLIANCE",
        "GOVERNS",
        "APPLIES_TO"
    ],
    "patterns": [
        # Policy relationships
        ("Policy", "AUTHORED_BY", "Politician"),
        ("Policy", "AUTHORED_BY", "Organization"),
        ("Policy", "AFFECTS", "Organization"),
        ("Policy", "RELATES_TO", "Topic"),
        ("Policy", "APPLIES_TO", "Jurisdiction"),
        
        # Political relationships
        ("Politician", "SUPPORTS", "Policy"),
        ("Politician", "OPPOSES", "Policy"),
        ("Organization", "SUPPORTS", "Policy"),
        ("Organization", "OPPOSES", "Policy"),
        
        # Regulatory relationships
        ("Regulation", "IMPLEMENTS", "Policy"),
        ("Regulation", "GOVERNS", "Organization"),
        ("Regulation", "APPLIES_TO", "Jurisdiction"),
        ("Regulation", "REFERENCES", "Regulation"),
        
        # Amendment and compliance
        ("Amendment", "AMENDS", "Regulation"),
        ("Amendment", "AMENDS", "Policy"),
        ("Organization", "REQUIRES_COMPLIANCE", "Regulation"),
        ("Policy", "SUPERSEDES", "Policy"),
        
        # Event connections
        ("Event", "RELATES_TO", "Policy"),
        ("Event", "RELATES_TO", "Regulation"),
        ("Event", "AFFECTS", "Organization")
    ]
}

def get_political_extraction_prompt() -> str:
    """Get the LLM prompt for political entity and relationship extraction."""
    return """
You are an expert in political and regulatory analysis. Extract entities and relationships from the given text.

ENTITIES TO EXTRACT:
- Policy: Laws, bills, acts, policies, directives, regulations
- Politician: Individual politicians, ministers, commissioners, officials
- Organization: Government agencies, NGOs, companies, political parties, regulatory bodies
- Regulation: Specific regulatory frameworks, compliance requirements, standards
- Event: Political events, elections, hearings, consultations, announcements
- Topic: Policy areas like privacy, cybersecurity, AI, data protection, trade
- Jurisdiction: Geographic or legal jurisdictions (EU, US, UK, California, etc.)
- Amendment: Changes, updates, or modifications to existing policies/regulations
- Compliance: Compliance requirements, obligations, enforcement actions

RELATIONSHIPS TO EXTRACT:
- AUTHORED_BY: Who created or proposed a policy/regulation
- AFFECTS: What organizations or jurisdictions are impacted
- SUPPORTS/OPPOSES: Political positions on policies
- RELATES_TO: Topical connections
- REFERENCES: Citations between documents/regulations
- IMPLEMENTS: How regulations implement broader policies
- SUPERSEDES: When new policies replace old ones
- AMENDS: When policies are modified
- REQUIRES_COMPLIANCE: Compliance obligations
- GOVERNS: Regulatory authority over organizations
- APPLIES_TO: Geographic or sector application

Focus on:
1. Extracting named entities (specific names, not generic terms)
2. Identifying clear relationships between entities
3. Capturing temporal aspects (when relationships started/ended)
4. Political nuances (support vs opposition, regulatory vs policy)

Be precise and only extract entities/relationships that are explicitly mentioned or clearly implied in the text.
"""

def get_node_properties() -> Dict[str, List[str]]:
    """Define properties for each node type."""
    return {
        "Policy": ["name", "description", "status", "date_introduced", "jurisdiction"],
        "Politician": ["name", "title", "party", "jurisdiction", "role"],
        "Organization": ["name", "type", "sector", "jurisdiction", "size"],
        "Regulation": ["name", "code", "status", "effective_date", "jurisdiction"],
        "Event": ["name", "date", "type", "location", "outcome"],
        "Topic": ["name", "description", "domain", "keywords"],
        "Jurisdiction": ["name", "type", "level", "parent_jurisdiction"],
        "Amendment": ["name", "date", "type", "status", "summary"],
        "Compliance": ["requirement", "deadline", "penalty", "status", "authority"]
    }

def get_relationship_properties() -> Dict[str, List[str]]:
    """Define properties for each relationship type."""
    return {
        "AUTHORED_BY": ["date", "role", "primary_author"],
        "AFFECTS": ["impact_type", "severity", "start_date", "end_date"],
        "OPPOSES": ["reason", "date", "public_statement", "intensity"],
        "SUPPORTS": ["reason", "date", "public_statement", "intensity"],
        "RELATES_TO": ["relationship_type", "strength", "context"],
        "REFERENCES": ["citation_type", "section", "relevance"],
        "IMPLEMENTS": ["implementation_date", "completeness", "authority"],
        "SUPERSEDES": ["transition_date", "reason", "grandfathering"],
        "AMENDS": ["amendment_date", "change_type", "section_modified"],
        "REQUIRES_COMPLIANCE": ["deadline", "penalty", "monitoring_authority"],
        "GOVERNS": ["authority_type", "start_date", "scope"],
        "APPLIES_TO": ["application_date", "scope", "exceptions"]
    }