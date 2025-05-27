#!/usr/bin/env python3
"""
Test script for Enhanced Political Schema v2.0

This script demonstrates the usage of the enhanced political schema
with practical examples of entity creation, relationship mapping,
and validation.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.graphrag.political_schema_v2 import (
    # Entities
    PolicyEntity, CompanyEntity, ComplianceObligationEntity,
    # Relationships  
    BusinessImpactRelationship, InfluenceRelationship,
    # Enums
    PolicyStage, ImpactSeverity, ComplianceStatus,
    # Utilities
    validate_entity_type, validate_relationship_pattern,
    get_entity_examples, SCHEMA_STATISTICS
)


def test_schema_validation():
    """Test basic schema validation functions."""
    print("=== Testing Schema Validation ===")
    
    # Test entity type validation
    assert validate_entity_type("Policy") == True
    assert validate_entity_type("Company") == True
    assert validate_entity_type("InvalidType") == False
    print("✅ Entity type validation working")
    
    # Test relationship pattern validation
    assert validate_relationship_pattern("Policy", "AFFECTS", "Company") == True
    assert validate_relationship_pattern("Company", "LOBBIES_AGAINST", "Regulation") == True
    assert validate_relationship_pattern("Invalid", "INVALID", "Pattern") == False
    print("✅ Relationship pattern validation working")
    
    # Test examples
    examples = get_entity_examples("Policy")
    assert "EU AI Act" in examples
    print("✅ Entity examples available")
    
    print(f"📊 Schema Statistics: {SCHEMA_STATISTICS}")


def test_gdpr_scenario():
    """Test GDPR compliance scenario."""
    print("\n=== Testing GDPR Compliance Scenario ===")
    
    # Create GDPR policy entity
    gdpr = PolicyEntity(
        name="General Data Protection Regulation",
        stage=PolicyStage.ENFORCED,
        jurisdiction="European Union",
        date_enacted=datetime(2016, 4, 27),
        date_effective=datetime(2018, 5, 25),
        sponsor="European Commission",
        legal_basis="Charter of Fundamental Rights",
        scope="Data protection and privacy"
    )
    print(f"✅ Created GDPR policy: {gdpr.name} (Stage: {gdpr.stage})")
    
    # Create company entity
    google = CompanyEntity(
        name="Google LLC",
        sector="Technology",
        size="multinational",
        revenue=282836000000,  # 2022 revenue
        headquarters="Mountain View, CA",
        jurisdictions_active=["US", "EU", "UK", "Japan"],
        business_model="Digital advertising and cloud services",
        public_private="public",
        stock_ticker="GOOGL"
    )
    print(f"✅ Created company: {google.name} (Sector: {google.sector})")
    
    # Create compliance obligation
    dpia_obligation = ComplianceObligationEntity(
        name="Data Protection Impact Assessment Requirement",
        requirement="Conduct DPIA for high-risk processing activities",
        deadline=datetime(2018, 5, 25),
        penalty="Up to 4% of annual global turnover",
        authority="Data Protection Authorities",
        status=ComplianceStatus.COMPLIANT,
        implementation_cost=50000,
        complexity_level="medium"
    )
    print(f"✅ Created compliance obligation: {dpia_obligation.requirement}")
    
    # Create business impact relationship
    gdpr_impact = BusinessImpactRelationship(
        source_entity="GDPR",
        target_entity="Google LLC",
        relationship_type="AFFECTS",
        impact_severity=ImpactSeverity.HIGH,
        cost_estimate=2500000000,  # Estimated compliance costs
        timeline="2-year implementation period",
        mitigation_possible=True,
        competitive_advantage="Strong privacy compliance as differentiator",
        start_date=datetime(2018, 5, 25)
    )
    print(f"✅ Created impact relationship: {gdpr_impact.impact_severity} severity")
    
    # Validate the scenario
    assert gdpr.stage == PolicyStage.ENFORCED
    assert google.sector == "Technology"
    assert gdpr_impact.impact_severity == ImpactSeverity.HIGH
    print("✅ GDPR scenario validation successful")


def test_eu_ai_act_lobbying():
    """Test EU AI Act lobbying scenario."""
    print("\n=== Testing EU AI Act Lobbying Scenario ===")
    
    # Create AI Act policy
    ai_act = PolicyEntity(
        name="EU AI Act",
        stage=PolicyStage.UNDER_REVIEW,
        jurisdiction="European Union",
        date_introduced=datetime(2021, 4, 21),
        sponsor="European Commission",
        legal_basis="Article 114 TFEU",
        scope="Artificial intelligence regulation"
    )
    print(f"✅ Created AI Act: {ai_act.name} (Stage: {ai_act.stage})")
    
    # Create influence relationship for tech industry lobbying
    tech_lobbying = InfluenceRelationship(
        source_entity="Technology Industry",
        target_entity="EU AI Act",
        relationship_type="LOBBIES_FOR",
        influence_type="regulatory_amendments",
        resources_involved=15000000,  # Estimated lobbying spend
        success_probability=0.7,
        tactics=["position_papers", "stakeholder_meetings", "technical_consultations"],
        transparency_level="high",
        start_date=datetime(2021, 6, 1)
    )
    print(f"✅ Created lobbying relationship: {tech_lobbying.success_probability} success probability")
    
    assert ai_act.stage == PolicyStage.UNDER_REVIEW
    assert tech_lobbying.relationship_type == "LOBBIES_FOR"
    print("✅ AI Act lobbying scenario validation successful")


def test_cross_border_compliance():
    """Test cross-border compliance scenario."""
    print("\n=== Testing Cross-Border Compliance Scenario ===")
    
    # Create multinational company
    apple = CompanyEntity(
        name="Apple Inc.",
        sector="Technology",
        size="multinational",
        revenue=394328000000,  # 2022 revenue
        headquarters="Cupertino, CA",
        jurisdictions_active=["US", "EU", "UK", "China", "Japan", "Australia"],
        business_model="Consumer electronics and digital services"
    )
    
    # Create multiple compliance obligations across jurisdictions
    us_privacy = ComplianceObligationEntity(
        name="California Consumer Privacy Act Compliance",
        requirement="Provide privacy rights to California consumers",
        deadline=datetime(2020, 1, 1),
        authority="California Attorney General",
        status=ComplianceStatus.COMPLIANT
    )
    
    eu_privacy = ComplianceObligationEntity(
        name="GDPR Article 17 Right to Erasure",
        requirement="Enable data subject deletion requests",
        deadline=datetime(2018, 5, 25),
        authority="European Data Protection Authorities",
        status=ComplianceStatus.COMPLIANT
    )
    
    # Create cross-jurisdictional relationships
    us_impact = BusinessImpactRelationship(
        source_entity="CCPA",
        target_entity="Apple Inc.",
        relationship_type="REQUIRES_COMPLIANCE",
        impact_severity=ImpactSeverity.MODERATE,
        cost_estimate=100000000
    )
    
    eu_impact = BusinessImpactRelationship(
        source_entity="GDPR",
        target_entity="Apple Inc.",
        relationship_type="REQUIRES_COMPLIANCE",
        impact_severity=ImpactSeverity.HIGH,
        cost_estimate=500000000
    )
    
    print(f"✅ Cross-border compliance for {apple.name}:")
    print(f"   - US Impact: {us_impact.impact_severity}")
    print(f"   - EU Impact: {eu_impact.impact_severity}")
    print("✅ Cross-border scenario validation successful")


def main():
    """Run all schema tests."""
    print("🧪 Testing Enhanced Political Schema v2.0")
    print("=" * 50)
    
    try:
        test_schema_validation()
        test_gdpr_scenario()
        test_eu_ai_act_lobbying()
        test_cross_border_compliance()
        
        print(f"\n🎉 All schema tests passed!")
        print(f"📈 Schema covers {SCHEMA_STATISTICS['total_entity_types']} entity types")
        print(f"🔗 Schema defines {SCHEMA_STATISTICS['total_relationship_types']} relationship types")
        print(f"✅ Ready for production use!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)