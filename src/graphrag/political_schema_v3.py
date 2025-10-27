"""
Simplified Political Domain Schema for Policy Monitoring - v3.0 (Cleaned)

This schema provides Graphiti-compatible entity and edge definitions for tracking
legislative processes and regulatory changes across EU and national levels.

Version: 3.0 (Cleaned)
Last Updated: 2025-01-13
Graphiti Compatible: Yes
"""

from typing import Optional
from pydantic import BaseModel, Field


# ===================================================================
# SECTION 1: ENTITY TYPE DEFINITIONS (20 Entity Types)
# ===================================================================

# --- TIER 1: LEGISLATIVE PROCESS ENTITIES ---

class LegislativeProposal(BaseModel):
    """Draft legislation moving through the legislative process"""
    legislative_proposal_name: str = Field(..., description="Working title of the proposal")
    proposal_id: Optional[str] = Field(None, description="Official identifier: COM(2024)123, BT-Drs 20/1234, etc.")
    jurisdiction: str = Field(..., description="EU, Germany, France, Bayern, etc.")
    legislative_body: str = Field(..., description="European Parliament, Bundestag, Bundesrat, National Assembly, etc.")
    
    stage: str = Field(..., description="Current stage: drafting, consultation, first_reading, committee, second_reading, third_reading, conciliation, mediation, adopted, rejected, withdrawn")
    
    procedure_type: Optional[str] = Field(None, description="EU: ordinary_legislative, special_legislative, consent, consultation; Germany: consent_law, objection_law; France: normal, accelerated")
    
    date_proposed: str = Field(..., description="When submitted to legislative body")
    expected_adoption: Optional[str] = Field(None, description="Expected/target adoption date")
    date_withdrawn: Optional[str] = Field(None, description="If withdrawn before vote")
    date_rejected: Optional[str] = Field(None, description="If rejected by vote")
    last_stage_change: Optional[str] = Field(None, description="When stage last changed")
    
    primary_sponsor: Optional[str] = Field(None, description="Main sponsor: politician, party, or institution")
    co_sponsors: Optional[str] = Field(None, description="Additional sponsors")
    
    becomes_policy_id: Optional[str] = Field(None, description="Reference to final Policy entity if adopted")
    
    legal_basis: Optional[str] = Field(None, description="Treaty basis: TFEU Art. 114, TFEU Art. 153, etc.")
    comitology_procedure: Optional[str] = Field(None, description="For implementing acts: examination, advisory")
    
    requires_bundesrat_consent: Optional[bool] = Field(None, description="Zustimmungsgesetz (true) vs Einspruchsgesetz (false)")
    mediation_committee_involved: Optional[bool] = Field(None, description="Whether Vermittlungsausschuss was invoked")
    
    transposes_eu_directive: Optional[str] = Field(None, description="EU Directive ID being transposed")
    transposition_deadline: Optional[str] = Field(None, description="Deadline for transposition")
    
    legislative_proposal_summary: Optional[str] = Field(None, description="Brief summary of proposal content")
    policy_areas: Optional[str] = Field(None, description="Policy domains affected")
    
    voting_history: Optional[str] = Field(
        None,
        description="JSON array of votes on this proposal: [{body: 'European Parliament', stage: 'second_reading', date: '2024-01-15', outcome: 'passed', votes_for: 450, votes_against: 120, abstentions: 80, required_majority: 'simple', threshold_met: true, amendments_voted: 'Amendment 123, 124', notes: '...'}]"
    )
    
    last_updated: Optional[str] = Field(None, description="Last status update date")
    url: Optional[str] = Field(None, description="Link to official proposal page")


class LegislativeBody(BaseModel):
    """Unified entity for all legislative institutions"""
    legislative_body_name: str = Field(..., description="European Parliament, Bundestag, Council of EU, Bundesrat, National Assembly, etc.")
    jurisdiction: str = Field(..., description="EU, Germany, France, or Bundesland name")
    type: str = Field(..., description="parliament, upper_chamber, lower_chamber, council, commission")
    
    legislative_powers: str = Field(..., description="co_decision, co_legislator, consent_only, objection, initiation_monopoly, advisory")
    composition: Optional[str] = Field(None, description="Number of seats, composition rules, voting procedures")
    term_length: Optional[str] = Field(None, description="Electoral term length")
    
    council_configuration: Optional[str] = Field(None, description="For Council of EU: ECOFIN, EPSCO, AGRIFISH, etc.")
    voting_rule: Optional[str] = Field(None, description="Qualified majority, unanimity, simple majority")
    
    current_president: Optional[str] = Field(None, description="Current president/speaker")
    majority_party: Optional[str] = Field(None, description="Party holding majority")
    
    website: Optional[str] = Field(None, description="Official website")


class Committee(BaseModel):
    """Parliamentary/Council committees that examine legislation in detail"""
    committee_name: str = Field(..., description="Committee on Industry, Research and Energy; Ausschuss für Digitales, etc.")
    parent_body: str = Field(..., description="Which LegislativeBody this belongs to")
    jurisdiction: str = Field(..., description="EU, Germany, etc.")
    
    policy_areas: Optional[str] = Field(None, description="Policy domains: digital, environment, finance, etc.")
    mandate: Optional[str] = Field(None, description="Official mandate and responsibilities")
    
    chair: Optional[str] = Field(None, description="Committee chair")
    members_count: Optional[int] = Field(None, description="Number of committee members")
    
    current_proposals: Optional[str] = Field(None, description="Proposals currently under examination")
    
    committee_type: Optional[str] = Field(None, description="For EU: standing, temporary, inquiry, budgetary_control")


class Document(BaseModel):
    """Official documents produced during the legislative process"""
    title: str = Field(..., description="Document title")
    document_id: Optional[str] = Field(None, description="Official identifier if available")
    document_type: str = Field(..., description="impact_assessment, consultation_response, committee_report, amendment, position_paper, commission_proposal, referentenentwurf, regierungsentwurf, official_journal, reasoned_opinion, evaluation_report")
    jurisdiction: str = Field(..., description="EU, Germany, etc.")
    
    author: str = Field(..., description="Who produced it: Commission, Ministry, Committee, Politician, etc.")
    author_type: Optional[str] = Field(None, description="institution, politician, stakeholder, expert")
    
    related_proposal: Optional[str] = Field(None, description="LegislativeProposal ID this relates to")
    related_policy: Optional[str] = Field(None, description="Final Policy ID this relates to")
    
    document_summary: Optional[str] = Field(None, description="Brief summary of document content")
    language: Optional[str] = Field(None, description="Document language")
    
    date_published: Optional[str] = Field(None, description="Publication date")
    url: Optional[str] = Field(None, description="Link to document")


class Vote(BaseModel):
    """Voting records on legislative proposals"""
    proposal: str = Field(..., description="LegislativeProposal ID being voted on")
    voting_body: str = Field(..., description="LegislativeBody name that voted")
    jurisdiction: str = Field(..., description="EU, Germany, etc.")
    
    date: str = Field(..., description="Date of vote")
    stage: str = Field(..., description="Which reading/stage: first_reading, second_reading, third_reading, final, conciliation")
    outcome: str = Field(..., description="passed, rejected, postponed, withdrawn")
    
    votes_for: Optional[int] = Field(None, description="Number of votes in favor")
    votes_against: Optional[int] = Field(None, description="Number of votes against")
    abstentions: Optional[int] = Field(None, description="Number of abstentions")
    
    required_majority: Optional[str] = Field(None, description="simple, absolute, qualified, two_thirds, unanimity")
    threshold_met: Optional[bool] = Field(None, description="Whether required threshold was met")
    
    amendments_voted: Optional[str] = Field(None, description="Specific amendments voted on")
    notes: Optional[str] = Field(None, description="Additional context about the vote")


# --- TIER 2: FINAL POLICY OUTCOMES ---

class Policy(BaseModel):
    """Final enacted laws and regulations"""
    policy_name: str = Field(..., description="Official name of the enacted policy")
    policy_id: str = Field(..., description="Official identifier: Regulation (EU) 2016/679, BGBl. I S. 2097, etc.")
    jurisdiction: str = Field(..., description="EU, Germany, Bayern, etc.")
    
    policy_type: str = Field(..., description="EU: regulation, directive, decision; Germany: bundesgesetz, landesgesetz, rechtsverordnung; France: loi, décret")
    
    legal_basis: Optional[str] = Field(None, description="Treaty article or constitutional article: TFEU Art. 114, GG Art. 74, etc.")
    
    date_enacted: str = Field(..., description="Date of enactment/adoption")
    date_effective: str = Field(..., description="Date when policy takes effect")
    date_entry_into_force: Optional[str] = Field(None, description="Official entry into force date")
    
    is_directive: Optional[bool] = Field(None, description="True if this is an EU Directive requiring transposition")
    transposition_deadline: Optional[str] = Field(None, description="Deadline for member states to transpose")
    
    status: str = Field(..., description="in_force, repealed, amended, under_review, suspended")
    supersedes: Optional[str] = Field(None, description="Previous policy ID that this replaces")
    
    policy_summary: Optional[str] = Field(None, description="Summary of policy content and objectives")
    policy_areas: Optional[str] = Field(None, description="Policy domains affected")
    scope: Optional[str] = Field(None, description="Who/what is covered by this policy")
    
    implementing_authority: Optional[str] = Field(None, description="Agency responsible for implementation")
    evaluation_clause: Optional[str] = Field(None, description="Evaluation requirements and timeline")
    
    exemptions: Optional[str] = Field(
        None,
        description="JSON array of exemptions: [{type: 'small_business', beneficiaries: '<250 employees', conditions: 'non-high-risk processing', scope: 'GDPR Article 30.5', expiry_date: null}]"
    )
    derogations: Optional[str] = Field(
        None,
        description="JSON array of member state derogations: [{member_state: 'France', provision: 'Article 23', justification: 'national security', duration: 'permanent'}]"
    )
    transitional_provisions: Optional[str] = Field(
        None,
        description="JSON array of grandfathering and phase-in rules: [{type: 'grandfathering', beneficiaries: 'existing systems', conditions: 'deployed before 2024', sunset_date: '2030-01-01'}]"
    )
    
    official_journal_reference: Optional[str] = Field(None, description="For EU: OJ reference")
    url: Optional[str] = Field(None, description="Link to official text")


class Regulation(BaseModel):
    """Implementing rules and technical regulations"""
    regulation_name: str = Field(..., description="Name of the implementing regulation")
    regulation_id: str = Field(..., description="Official identifier")
    jurisdiction: str = Field(..., description="EU, Germany, etc.")
    
    parent_policy: str = Field(..., description="Policy ID that this regulation implements")
    
    regulation_type: Optional[str] = Field(None, description="EU: implementing_act, delegated_act; Germany: rechtsverordnung, verwaltungsvorschrift")
    
    issuing_authority: str = Field(..., description="Commission, Federal Ministry, State Ministry, etc.")
    legal_basis: Optional[str] = Field(None, description="Article empowering this regulation")
    
    date_issued: Optional[str] = Field(None, description="Date regulation was issued")
    effective_date: str = Field(..., description="Date regulation takes effect")
    
    compliance_deadline: Optional[str] = Field(None, description="Deadline for entities to comply")
    grace_period: Optional[str] = Field(None, description="Any grace period provisions")
    
    technical_requirements: Optional[str] = Field(None, description="Specific technical requirements")
    standards_referenced: Optional[str] = Field(None, description="Technical standards referenced")
    
    enforcement_mechanism: Optional[str] = Field(None, description="How compliance is enforced")
    penalty_structure: Optional[str] = Field(None, description="Penalties for non-compliance")
    
    review_cycle: Optional[str] = Field(None, description="How often regulation is reviewed")
    status: Optional[str] = Field(None, description="active, suspended, repealed")
    
    exemptions: Optional[str] = Field(
        None,
        description="JSON array of exemptions applicable to this regulation"
    )


# --- TIER 3: ACTORS ---

class Politician(BaseModel):
    """Individual politicians, elected officials, and appointees"""
    politician_name: str = Field(..., description="Full name")
    jurisdiction: str = Field(..., description="EU, Germany, France, etc.")
    
    role: str = Field(..., description="MEP, MdB (Member of Bundestag), Minister, Commissioner, Senator, etc.")
    title: Optional[str] = Field(None, description="Official title if applicable")
    
    party: Optional[str] = Field(None, description="Political party")
    party_group: Optional[str] = Field(None, description="For EU: EPP, S&D, Renew, Greens, etc.")
    
    legislative_body: Optional[str] = Field(None, description="Which LegislativeBody they belong to")
    committee_memberships: Optional[str] = Field(None, description="Committee memberships")
    leadership_positions: Optional[str] = Field(None, description="Committee chair, faction leader, etc.")
    
    policy_focus: Optional[str] = Field(None, description="Policy areas of focus")
    proposals_sponsored: Optional[str] = Field(None, description="Key proposals sponsored")
    
    term_start: Optional[str] = Field(None, description="Start of current term")
    term_end: Optional[str] = Field(None, description="End of current term")
    
    website: Optional[str] = Field(None, description="Official website")
    voting_record_url: Optional[str] = Field(None, description="Link to voting record")


class Person(BaseModel):
    """Non-politician individuals who influence or comment on policy"""
    person_name: str = Field(..., description="Full name")
    
    role: str = Field(..., description="CEO, expert, academic, activist, journalist, influencer, consultant, etc.")
    title: Optional[str] = Field(None, description="Professional title: Dr., Prof., etc.")
    
    organization: Optional[str] = Field(None, description="Company, university, think tank, media outlet they represent")
    organization_type: Optional[str] = Field(None, description="company, university, ngo, think_tank, media, consultancy")
    
    expertise_areas: Optional[str] = Field(None, description="Areas of expertise: AI, climate, finance, etc.")
    credentials: Optional[str] = Field(None, description="Academic degrees, certifications, achievements")
    
    influence_level: Optional[str] = Field(None, description="high, medium, low - level of public influence")
    public_profile: Optional[str] = Field(None, description="Level of public recognition")
    
    jurisdiction: Optional[str] = Field(None, description="Primary country/region")
    
    linkedin_url: Optional[str] = Field(None, description="LinkedIn profile")
    twitter_handle: Optional[str] = Field(None, description="Twitter/X handle")
    website: Optional[str] = Field(None, description="Personal or professional website")


class PoliticalParty(BaseModel):
    """Political parties and their positions"""
    political_party_name: str = Field(..., description="Party name")
    jurisdiction: str = Field(..., description="Country or level where party operates")
    
    party_family: Optional[str] = Field(None, description="European party family: PES, EPP, ALDE, EGP, etc.")
    
    seats_held: Optional[int] = Field(None, description="Number of seats in main legislative body")
    vote_share: Optional[str] = Field(None, description="Vote share in last election")
    
    party_leader: Optional[str] = Field(None, description="Current party leader")
    
    policy_platform: Optional[str] = Field(None, description="Key policy positions")
    regulatory_stance: Optional[str] = Field(None, description="General approach to regulation: pro-regulation, deregulation, balanced")
    business_stance: Optional[str] = Field(None, description="Stance on business regulation")
    
    coalition_partners: Optional[str] = Field(None, description="Current coalition or alliance partners")
    in_government: Optional[bool] = Field(None, description="Whether party is in government")


class GovernmentAgency(BaseModel):
    """Executive agencies, regulatory bodies, ministries"""
    government_agency_name: str = Field(..., description="Official agency name")
    jurisdiction: str = Field(..., description="EU, Germany, etc.")
    
    agency_type: str = Field(..., description="commission_dg, federal_ministry, state_ministry, regulatory_authority, executive_agency")
    
    mandate: Optional[str] = Field(None, description="Official mandate and responsibilities")
    policy_areas: Optional[str] = Field(None, description="Policy areas covered")
    
    regulatory_powers: Optional[str] = Field(None, description="Regulatory powers granted")
    enforcement_authority: Optional[str] = Field(None, description="Enforcement powers")
    can_issue_regulations: Optional[bool] = Field(None, description="Whether agency can issue implementing regulations")
    
    budget: Optional[str] = Field(None, description="Annual budget")
    staff_size: Optional[int] = Field(None, description="Number of staff")
    
    director: Optional[str] = Field(None, description="Agency head")
    reporting_to: Optional[str] = Field(None, description="Who agency reports to")
    
    parent_organization: Optional[str] = Field(None, description="Parent ministry or commission")
    website: Optional[str] = Field(None, description="Official website")


class LobbyGroup(BaseModel):
    """Interest groups, industry associations, NGOs, advocacy organizations"""
    lobby_group_name: str = Field(..., description="Organization name")
    type: str = Field(..., description="industry_association, trade_union, ngo, think_tank, advocacy_group, professional_association")
    
    primary_jurisdiction: str = Field(..., description="Main jurisdiction where organization is based: EU, Germany, France, etc.")
    additional_jurisdictions: Optional[str] = Field(None, description="JSON array of additional jurisdictions where active: ['France', 'Spain', 'Italy']")
    policy_focus: Optional[str] = Field(None, description="Policy areas of focus")
    
    members: Optional[str] = Field(None, description="Key member organizations or number of members")
    sectors_represented: Optional[str] = Field(None, description="Industry sectors represented")
    
    lobbying_budget: Optional[str] = Field(None, description="Annual lobbying expenditure")
    registered_lobbyists: Optional[int] = Field(None, description="Number of registered lobbyists")
    
    key_positions: Optional[str] = Field(None, description="Key policy positions")
    active_campaigns: Optional[str] = Field(None, description="Current advocacy campaigns")
    
    transparency_register_id: Optional[str] = Field(None, description="EU Transparency Register ID if applicable")
    website: Optional[str] = Field(None, description="Organization website")


# --- TIER 4: BUSINESS ENTITIES ---

class Company(BaseModel):
    """Individual corporations and business entities"""
    company_name: str = Field(..., description="Company name")
    
    sector: str = Field(..., description="Primary industry sector")
    size: Optional[str] = Field(None, description="small, medium, large, multinational")
    
    revenue: Optional[str] = Field(None, description="Annual revenue")
    employee_count: Optional[int] = Field(None, description="Number of employees")
    
    headquarters: Optional[str] = Field(None, description="HQ location")
    jurisdictions_active: Optional[str] = Field(None, description="Countries/regions where company operates")
    
    business_model: Optional[str] = Field(None, description="Primary business model")
    key_products: Optional[str] = Field(None, description="Main products/services")
    
    business_activities: Optional[str] = Field(
        None,
        description="JSON array of business activities: [{activity: 'algorithmic decision-making', risk_level: 'high', technology: 'AI', regulatory_coverage: 'AI Act, GDPR Art 22', data_implications: 'automated profiling'}]"
    )
    
    regulatory_risk_score: Optional[float] = Field(None, description="Computed overall regulatory risk score 0-100")
    identified_risks: Optional[str] = Field(
        None,
        description="JSON array of identified regulatory risks: [{risk_type: 'compliance_failure', probability: 'high', impact_severity: 'critical', mitigation_strategies: '...', timeline: 'short_term'}]"
    )
    regulatory_risk_level: Optional[str] = Field(None, description="Overall risk category: low, medium, high, critical")
    
    compliance_status: Optional[str] = Field(None, description="Overall compliance standing")
    data_practices: Optional[str] = Field(None, description="Data handling practices")
    
    public_private: Optional[str] = Field(None, description="public, private, state_owned")
    stock_ticker: Optional[str] = Field(None, description="Stock ticker if publicly traded")
    parent_company: Optional[str] = Field(None, description="Parent company if subsidiary")


class Industry(BaseModel):
    """Business sectors and industry classifications"""
    industry_name: str = Field(..., description="Industry name")
    classification_code: Optional[str] = Field(None, description="NACE, NAICS, or SIC code")
    
    description: Optional[str] = Field(None, description="Industry description")
    sub_sectors: Optional[str] = Field(None, description="Key sub-sectors")
    
    market_size: Optional[str] = Field(None, description="Total market value")
    employment: Optional[int] = Field(None, description="Total industry employment")
    gdp_contribution: Optional[str] = Field(None, description="Contribution to GDP")
    
    key_players: Optional[str] = Field(None, description="Major companies in industry")
    market_concentration: Optional[str] = Field(None, description="HHI or concentration ratio")
    
    regulatory_intensity: Optional[str] = Field(None, description="Level of regulatory oversight: low, medium, high")
    key_regulations: Optional[str] = Field(None, description="Main regulations affecting industry")
    
    innovation_rate: Optional[str] = Field(None, description="Pace of technological change")
    emerging_technologies: Optional[str] = Field(None, description="New technologies impacting industry")
    
    common_activities: Optional[str] = Field(
        None,
        description="JSON array of typical business activities: [{activity: 'data processing', prevalence: 'widespread', technology: 'cloud computing'}]"
    )
    
    markets: Optional[str] = Field(
        None,
        description="JSON array of markets: [{name: 'EU digital advertising', geographic_scope: 'EU', market_size: '€50B', growth_rate: '8%', concentration: 'high', barriers_to_entry: 'high'}]"
    )


class ComplianceObligation(BaseModel):
    """Specific requirements that companies must meet"""
    requirement: str = Field(..., description="Specific compliance requirement description")
    source_policy: str = Field(..., description="Policy or Regulation creating this obligation")
    jurisdiction: str = Field(..., description="Where this applies")
    
    applies_to: Optional[str] = Field(None, description="Which entities must comply: all companies, specific sectors, size thresholds")
    
    effective_date: Optional[str] = Field(None, description="When obligation takes effect")
    deadline: Optional[str] = Field(None, description="Compliance deadline")
    grace_period: Optional[str] = Field(None, description="Any grace period")
    
    frequency: Optional[str] = Field(None, description="How often requirement must be met: one-time, annual, continuous")
    documentation_required: Optional[str] = Field(None, description="Documentation companies must maintain")
    
    enforcing_authority: str = Field(..., description="Agency that enforces this obligation")
    penalty_for_non_compliance: Optional[str] = Field(None, description="Penalties for violation")
    
    complexity_level: Optional[str] = Field(None, description="Implementation complexity: low, medium, high")
    estimated_cost: Optional[str] = Field(None, description="Estimated implementation cost")
    
    status: Optional[str] = Field(None, description="pending, active, suspended, repealed")


# --- TIER 5: PROCESS TRACKING ---

class ConsultationProcess(BaseModel):
    """Public consultations and stakeholder engagement processes"""
    consultation_process_name: str = Field(..., description="Consultation name/title")
    jurisdiction: str = Field(..., description="EU, Germany, etc.")
    
    organizing_authority: str = Field(..., description="Institution conducting consultation: Commission, Ministry, etc.")
    
    related_proposal: Optional[str] = Field(None, description="LegislativeProposal ID if applicable")
    policy_area: Optional[str] = Field(None, description="Policy domain")
    consultation_type: Optional[str] = Field(None, description="public_consultation, stakeholder_dialogue, impact_assessment_consultation")
    
    start_date: str = Field(..., description="Consultation opening date")
    end_date: str = Field(..., description="Consultation closing date")
    duration_weeks: Optional[int] = Field(None, description="Duration in weeks")
    
    target_audience: Optional[str] = Field(None, description="Who can participate")
    submission_count: Optional[int] = Field(None, description="Number of responses received")
    participant_breakdown: Optional[str] = Field(None, description="Types of participants: companies, NGOs, citizens, etc.")
    
    key_themes: Optional[str] = Field(None, description="Main themes from responses")
    summary_report: Optional[str] = Field(None, description="Link to feedback summary")
    influence_on_outcome: Optional[str] = Field(None, description="How consultation shaped final proposal")
    
    responses_published: Optional[bool] = Field(None, description="Whether responses are published")
    url: Optional[str] = Field(None, description="Link to consultation")


class EnforcementAction(BaseModel):
    """Fines, investigations, infringement procedures, sanctions"""
    action_type: str = Field(..., description="infringement_notice, reasoned_opinion, cjeu_referral, fine, investigation, warning, sanction, criminal_prosecution")
    jurisdiction: str = Field(..., description="EU, Germany, etc.")
    
    target: str = Field(..., description="Entity targeted: Company name, Member State, etc.")
    target_type: Optional[str] = Field(None, description="company, member_state, individual")
    
    enforcing_authority: str = Field(..., description="Commission, regulatory agency, court, etc.")
    
    date: str = Field(..., description="Date of action")
    violation: Optional[str] = Field(None, description="What law/regulation was violated")
    legal_basis: Optional[str] = Field(None, description="Legal basis for enforcement")
    
    fine_amount: Optional[str] = Field(None, description="Monetary penalty if applicable")
    daily_penalty: Optional[str] = Field(None, description="Daily penalty for continued non-compliance")
    
    status: str = Field(..., description="initiated, ongoing, concluded, appealed, settled")
    appeal_status: Optional[str] = Field(None, description="Status of any appeal")
    outcome: Optional[str] = Field(None, description="Final outcome if concluded")
    
    precedent_value: Optional[str] = Field(None, description="Significance as legal precedent")
    corrective_measures_required: Optional[str] = Field(None, description="What target must do to comply")
    
    case_number: Optional[str] = Field(None, description="Official case number")
    url: Optional[str] = Field(None, description="Link to case details")


# --- TIER 6: GEOGRAPHIC ---

class Jurisdiction(BaseModel):
    """Geographic and legal jurisdictions"""
    jurisdiction_name: str = Field(..., description="EU, Germany, France, Bayern, Paris, etc.")
    type: str = Field(..., description="supranational, member_state, bundesland, region, municipality")
    
    parent_jurisdiction: Optional[str] = Field(None, description="Bayern -> Germany -> EU")
    member_of: Optional[str] = Field(None, description="Which higher-level jurisdiction: EU, etc.")
    
    legal_system_type: Optional[str] = Field(None, description="civil_law, common_law, mixed")
    constitutional_basis: Optional[str] = Field(None, description="Constitution or treaty basis")
    
    population: Optional[int] = Field(None, description="Population size")
    gdp: Optional[str] = Field(None, description="GDP or economic size")
    
    regulatory_approach: Optional[str] = Field(None, description="Overall regulatory philosophy")
    enforcement_capability: Optional[str] = Field(None, description="Strength of enforcement: weak, moderate, strong")
    
    treaties: Optional[str] = Field(None, description="International agreements and treaties")
    
    eu_accession_date: Optional[str] = Field(None, description="For member states: when joined EU")
    eurozone_member: Optional[bool] = Field(None, description="Whether in eurozone")
    schengen_member: Optional[bool] = Field(None, description="Whether in Schengen area")


# --- TIER 7: TECHNICAL/LEGAL SUPPORT ---

class LegalFramework(BaseModel):
    """Broader legal context: constitutions, treaties, framework legislation"""
    legal_framework_name: str = Field(..., description="Treaty on European Union, Grundgesetz, Charter of Fundamental Rights, etc.")
    jurisdiction: str = Field(..., description="EU, Germany, etc.")
    
    framework_type: str = Field(..., description="constitution, treaty, charter, framework_directive, enabling_act")
    
    hierarchy_level: str = Field(..., description="Position in legal hierarchy: primary_law, secondary_law, tertiary_law")
    
    scope: Optional[str] = Field(None, description="What this framework covers")
    fundamental_principles: Optional[str] = Field(None, description="Core principles established")
    rights_protected: Optional[str] = Field(None, description="Fundamental rights enshrined")
    
    legal_basis: Optional[str] = Field(None, description="What gives this framework authority")
    enforcement_mechanisms: Optional[str] = Field(None, description="How framework is enforced")
    
    amendment_process: Optional[str] = Field(None, description="Process for changing framework")
    last_amended: Optional[str] = Field(None, description="Date of last amendment")
    
    url: Optional[str] = Field(None, description="Link to official text")


class TechnicalStandard(BaseModel):
    """Technical standards and specifications"""
    technical_standard_name: str = Field(..., description="ISO 27001, EN standards, etc.")
    standard_id: Optional[str] = Field(None, description="Official standard identifier")
    
    issuing_body: str = Field(..., description="ISO, CEN, CENELEC, DIN, ETSI, etc.")
    jurisdiction: Optional[str] = Field(None, description="Where standard applies")
    
    standard_type: Optional[str] = Field(None, description="product_standard, process_standard, management_standard, testing_standard")
    
    mandatory_voluntary: str = Field(..., description="mandatory, voluntary, voluntary_but_presumed_compliance")
    harmonized_standard: Optional[bool] = Field(None, description="For EU: whether it's a harmonized standard")
    
    version: Optional[str] = Field(None, description="Current version")
    technical_specifications: Optional[str] = Field(None, description="Key technical requirements")
    
    certification_required: Optional[bool] = Field(None, description="Whether certification is needed")
    testing_procedures: Optional[str] = Field(None, description="How compliance is tested")
    certification_bodies: Optional[str] = Field(None, description="Accredited certification bodies")
    
    date_published: Optional[str] = Field(None, description="Publication date")
    review_cycle: Optional[str] = Field(None, description="How often standard is reviewed")
    supersedes: Optional[str] = Field(None, description="Previous standard version")
    
    international_recognition: Optional[str] = Field(None, description="Where standard is recognized")


# ===================================================================
# SECTION 2: EDGE TYPE DEFINITIONS
# ===================================================================

# --- JURISDICTION RELATIONSHIP EDGES ---

class InJurisdiction(BaseModel):
    """Entity is located in or associated with jurisdiction"""
    relationship_type: str = Field(
        ..., 
        description="based_in, proposed_in, enacted_in, conducted_in - specifies nature of relationship"
    )
    since: Optional[str] = Field(None, description="Start date of relationship")
    scope: Optional[str] = Field(None, description="full, partial, conditional")


class MemberOf(BaseModel):
    """Jurisdiction is member of parent jurisdiction"""
    membership_type: str = Field(..., description="member_state, bundesland, region, municipality, etc.")
    joined_date: Optional[str] = Field(None, description="When joined")


class Represents(BaseModel):
    """Politician/Party represents jurisdiction"""
    representation_type: str = Field(..., description="elected, appointed")
    constituency: Optional[str]
    electoral_district: Optional[str] = Field(None, description="Specific district if applicable")
    term_start: Optional[str]
    term_end: Optional[str]


# --- LEGISLATIVE PROCESS EDGES ---

class Proposes(BaseModel):
    """Who proposes legislation"""
    date_proposed: Optional[str]
    co_proposers: Optional[str] = Field(None, description="Additional proposers")


class SubmitsTo(BaseModel):
    """Proposal submitted to legislative body"""
    date_submitted: str
    submission_method: Optional[str] = Field(None, description="How submitted")


class Examines(BaseModel):
    """Committee examines proposal"""
    date_assigned: Optional[str]
    rapporteur: Optional[str] = Field(None, description="Committee rapporteur")
    opinion_type: Optional[str] = Field(None, description="leading, opinion, consultation")


class AmendsProposal(BaseModel):
    """Document proposes changes to proposal"""
    amendment_number: Optional[str]
    date_proposed: Optional[str]
    status: Optional[str] = Field(None, description="adopted, rejected, withdrawn, pending")


class VotesOn(BaseModel):
    """Vote on a proposal"""
    pass


class Becomes(BaseModel):
    """Proposal becomes final policy"""
    date_enacted: str
    changes_made: Optional[str] = Field(None, description="Summary of changes from proposal to final")


# --- EU-GERMANY COORDINATION EDGES ---

class Transposes(BaseModel):
    """National law transposes EU Directive"""
    transposition_deadline: str
    transposition_date: Optional[str]
    transposition_status: str = Field(..., description="not_started, in_progress, completed, overdue")
    compliance_level: Optional[str] = Field(None, description="full, partial, incomplete")
    deviations: Optional[str] = Field(None, description="How national law differs from directive")


class GoldPlates(BaseModel):
    """National measure exceeds EU minimum requirements"""
    areas_exceeded: str = Field(..., description="Where national law goes beyond minimum")
    justification: Optional[str] = Field(None, description="Stated reason for gold-plating")


class InfringementAgainst(BaseModel):
    """Commission brings infringement against member state"""
    infringement_stage: str = Field(..., description="letter_of_formal_notice, reasoned_opinion, cjeu_referral")
    grounds: str = Field(..., description="Basis for infringement")
    date_initiated: str


class PreliminaryReference(BaseModel):
    """National court asks CJEU for interpretation"""
    case_number: str
    date_referred: str
    question: Optional[str] = Field(None, description="Legal question referred")
    date_decided: Optional[str]
    ruling_impact: Optional[str]


# --- INFLUENCE AND POWER EDGES ---

class Influences(BaseModel):
    """General influence relationship"""
    influence_type: str = Field(..., description="lobbying, advisory, financial, technical")
    strength: Optional[str] = Field(None, description="weak, moderate, strong")
    mechanism: Optional[str] = Field(None, description="How influence is exerted")


class LobbiesFor(BaseModel):
    """Active support for policy"""
    position: str = Field(..., description="Specific position advocated")
    resources_spent: Optional[str]
    tactics: Optional[str] = Field(None, description="Lobbying methods used")


class LobbiesAgainst(BaseModel):
    """Active opposition to policy"""
    objections: str = Field(..., description="Specific objections")
    alternative_proposed: Optional[str]
    resources_spent: Optional[str]


class HasPosition(BaseModel):
    """Person/entity has a position on proposal or policy"""
    position_type: str = Field(..., description="supports, opposes, neutral")
    reasoning: Optional[str] = Field(None, description="Why they hold this position")
    public_statement_date: Optional[str]
    statement_url: Optional[str]
    intensity: Optional[str] = Field(None, description="strong, moderate, weak")


class Contributes(BaseModel):
    """Person contributes expertise, testimony, or content"""
    contribution_type: str = Field(..., description="testimony, authorship, consultation_response, expert_opinion, speaking_engagement")
    date: Optional[str]
    topic: Optional[str]
    url: Optional[str]
    role: Optional[str] = Field(None, description="lead_author, co_author, expert_witness, panelist")


class AffiliatedWith(BaseModel):
    """Person affiliated with organization"""
    affiliation_type: str = Field(..., description="employee, executive, board_member, consultant, advisor")
    position: Optional[str] = Field(None, description="Specific position/title")
    start_date: Optional[str]
    end_date: Optional[str]
    is_current: Optional[bool] = Field(None, description="Whether affiliation is current")


# --- BUSINESS IMPACT EDGES ---

class Affects(BaseModel):
    """Policy affects business entity"""
    impact_type: str = Field(..., description="operational, financial, strategic, competitive, reputational")
    severity: str = Field(..., description="minimal, low, moderate, high, critical")
    timeline: Optional[str] = Field(None, description="When impact occurs")
    cost_estimate: Optional[str]


class SubjectTo(BaseModel):
    """Entity subject to regulation"""
    applicability_scope: str
    conditions: Optional[str]
    exceptions_applicable: Optional[str]


class RequiresCompliance(BaseModel):
    """Specific compliance requirement"""
    deadline: Optional[str]
    penalty_for_non_compliance: Optional[str]
    monitoring_frequency: Optional[str]


class OperatesIn(BaseModel):
    """Company operates in jurisdiction"""
    market_share: Optional[str]
    years_active: Optional[str]
    regulatory_status: Optional[str] = Field(None, description="authorized, under_review, restricted")


class CompetesIn(BaseModel):
    """Competition relationship"""
    market_position: Optional[str] = Field(None, description="leader, challenger, follower")
    competitive_advantage: Optional[str]


# --- REGULATORY HIERARCHY EDGES ---

class Implements(BaseModel):
    """How policy is implemented"""
    implementation_date: Optional[str]
    implementing_authority: Optional[str]
    completeness: Optional[str] = Field(None, description="full, partial")


class Enforces(BaseModel):
    """Who enforces what"""
    enforcement_scope: Optional[str]
    enforcement_tools: Optional[str]
    success_rate: Optional[str]


class DelegatesTo(BaseModel):
    """Authority delegation"""
    scope_of_delegation: str
    conditions: Optional[str]
    can_be_revoked: Optional[bool]


# --- TEMPORAL EDGES ---

class Supersedes(BaseModel):
    """Policy replaces another"""
    transition_date: str
    reason: Optional[str]
    transitional_provisions: Optional[str]


class Amends(BaseModel):
    """Policy amends another"""
    amendment_date: str
    sections_modified: Optional[str]
    nature_of_change: Optional[str] = Field(None, description="expansion, restriction, clarification, correction")


class Triggers(BaseModel):
    """Event triggers response"""
    trigger_event: str
    response_timeline: Optional[str]


class Precedes(BaseModel):
    """Sequential relationship"""
    time_gap: Optional[str]
    dependency_type: Optional[str] = Field(None, description="required, optional, recommended")


# --- REFERENCE EDGES ---

class References(BaseModel):
    """Cross-reference between documents"""
    citation_type: Optional[str] = Field(None, description="direct, indirect, general")
    section: Optional[str]
    purpose: Optional[str] = Field(None, description="legal_basis, interpretation, context")


class HarmonizesWith(BaseModel):
    """Coordination between jurisdictions"""
    harmonization_level: str = Field(..., description="full, substantial, partial, minimal")
    coordination_mechanism: Optional[str]


class ConflictsWith(BaseModel):
    """Regulatory conflict"""
    conflict_type: str = Field(..., description="direct_contradiction, overlapping_scope, inconsistent_requirements")
    resolution_mechanism: Optional[str]
    priority_rule: Optional[str] = Field(None, description="Which takes precedence")


# --- STAKEHOLDER EDGES ---

class Advises(BaseModel):
    """Advisory relationship"""
    advice_type: str = Field(..., description="technical, policy, legal, scientific")
    frequency: Optional[str]


class Monitors(BaseModel):
    """Oversight relationship"""
    monitoring_scope: str
    reporting_frequency: Optional[str]
    enforcement_powers: Optional[bool]


# ===================================================================
# SECTION 3: REGISTRY DICTIONARIES
# ===================================================================

ENTITY_TYPE_REGISTRY: dict[str, type[BaseModel]] = {
    # Tier 1: Legislative Process
    "LegislativeProposal": LegislativeProposal,
    "LegislativeBody": LegislativeBody,
    "Committee": Committee,
    "Document": Document,
    "Vote": Vote,
    
    # Tier 2: Final Outcomes
    "Policy": Policy,
    "Regulation": Regulation,
    
    # Tier 3: Actors
    "Politician": Politician,
    "Person": Person,
    "PoliticalParty": PoliticalParty,
    "GovernmentAgency": GovernmentAgency,
    "LobbyGroup": LobbyGroup,
    
    # Tier 4: Business
    "Company": Company,
    "Industry": Industry,
    "ComplianceObligation": ComplianceObligation,
    
    # Tier 5: Process Tracking
    "ConsultationProcess": ConsultationProcess,
    "EnforcementAction": EnforcementAction,
    
    # Tier 6: Geographic
    "Jurisdiction": Jurisdiction,
    
    # Tier 7: Technical/Legal
    "LegalFramework": LegalFramework,
    "TechnicalStandard": TechnicalStandard,
}

EDGE_TYPE_REGISTRY: dict[str, type[BaseModel]] = {
    # Jurisdiction Relationships
    "IN_JURISDICTION": InJurisdiction,
    "MEMBER_OF": MemberOf,
    "REPRESENTS": Represents,
    
    # Legislative Process
    "PROPOSES": Proposes,
    "SUBMITS_TO": SubmitsTo,
    "EXAMINES": Examines,
    "AMENDS_PROPOSAL": AmendsProposal,
    "VOTES_ON": VotesOn,
    "BECOMES": Becomes,
    
    # EU-Germany Coordination
    "TRANSPOSES": Transposes,
    "GOLD_PLATES": GoldPlates,
    "INFRINGEMENT_AGAINST": InfringementAgainst,
    "PRELIMINARY_REFERENCE": PreliminaryReference,
    
    # Influence and Power
    "INFLUENCES": Influences,
    "LOBBIES_FOR": LobbiesFor,
    "LOBBIES_AGAINST": LobbiesAgainst,
    "HAS_POSITION": HasPosition,
    "CONTRIBUTES": Contributes,
    "AFFILIATED_WITH": AffiliatedWith,
    
    # Business Impact
    "AFFECTS": Affects,
    "SUBJECT_TO": SubjectTo,
    "REQUIRES_COMPLIANCE": RequiresCompliance,
    "OPERATES_IN": OperatesIn,
    "COMPETES_IN": CompetesIn,
    
    # Regulatory Hierarchy
    "IMPLEMENTS": Implements,
    "ENFORCES": Enforces,
    "DELEGATES_TO": DelegatesTo,
    
    # Temporal
    "SUPERSEDES": Supersedes,
    "AMENDS": Amends,
    "TRIGGERS": Triggers,
    "PRECEDES": Precedes,
    
    # Reference
    "REFERENCES": References,
    "HARMONIZES_WITH": HarmonizesWith,
    "CONFLICTS_WITH": ConflictsWith,
    
    # Stakeholder
    "ADVISES": Advises,
    "MONITORS": Monitors,
}


# ===================================================================
# SECTION 4: EDGE TYPE MAP
# ===================================================================

EDGE_TYPE_MAP: dict[tuple[str, str], list[str]] = {
    # ===== JURISDICTION RELATIONSHIPS =====
    
    # IN_JURISDICTION - general relationship to jurisdiction
    ("Policy", "Jurisdiction"): ["IN_JURISDICTION"],
    ("Regulation", "Jurisdiction"): ["IN_JURISDICTION"],
    ("ComplianceObligation", "Jurisdiction"): ["IN_JURISDICTION"],
    ("LegislativeProposal", "Jurisdiction"): ["IN_JURISDICTION"],
    ("LegislativeBody", "Jurisdiction"): ["IN_JURISDICTION"],
    ("Committee", "Jurisdiction"): ["IN_JURISDICTION"],
    ("GovernmentAgency", "Jurisdiction"): ["IN_JURISDICTION"],
    ("ConsultationProcess", "Jurisdiction"): ["IN_JURISDICTION"],
    ("EnforcementAction", "Jurisdiction"): ["IN_JURISDICTION", "INFRINGEMENT_AGAINST"],
    ("Company", "Jurisdiction"): ["IN_JURISDICTION", "OPERATES_IN"],
    ("Industry", "Jurisdiction"): ["IN_JURISDICTION", "OPERATES_IN"],
    ("LobbyGroup", "Jurisdiction"): ["IN_JURISDICTION"],
    ("PoliticalParty", "Jurisdiction"): ["IN_JURISDICTION", "REPRESENTS"],
    
    # MEMBER_OF - jurisdiction hierarchy
    ("Jurisdiction", "Jurisdiction"): ["MEMBER_OF", "HARMONIZES_WITH", "CONFLICTS_WITH"],
    
    # REPRESENTS - politicians/parties representing jurisdictions
    ("Politician", "Jurisdiction"): ["REPRESENTS"],
    ("PoliticalParty", "Jurisdiction"): ["REPRESENTS"],
    
    # ===== LEGISLATIVE PROCESS =====
    ("Politician", "LegislativeProposal"): ["PROPOSES", "AMENDS_PROPOSAL"],
    ("PoliticalParty", "LegislativeProposal"): ["PROPOSES"],
    ("GovernmentAgency", "LegislativeProposal"): ["PROPOSES"],
    ("LegislativeBody", "LegislativeProposal"): ["PROPOSES"],
    
    ("LegislativeProposal", "LegislativeBody"): ["SUBMITS_TO"],
    
    ("Committee", "LegislativeProposal"): ["EXAMINES"],
    
    ("Document", "LegislativeProposal"): ["AMENDS_PROPOSAL"],
    
    ("Vote", "LegislativeProposal"): ["VOTES_ON"],
    
    ("LegislativeProposal", "Policy"): ["BECOMES", "TRANSPOSES"],
    ("LegislativeProposal", "Regulation"): ["BECOMES"],
    
    # ===== EU-GERMANY COORDINATION =====
    ("Policy", "Policy"): ["TRANSPOSES", "GOLD_PLATES", "SUPERSEDES", "AMENDS", "REFERENCES", "CONFLICTS_WITH"],
    
    ("Document", "Policy"): ["PRELIMINARY_REFERENCE", "PRECEDES"],
    
    # ===== INFLUENCE AND POWER =====
    ("LobbyGroup", "Politician"): ["INFLUENCES", "ADVISES"],
    ("LobbyGroup", "LegislativeProposal"): ["INFLUENCES", "LOBBIES_FOR", "LOBBIES_AGAINST"],
    ("LobbyGroup", "Policy"): ["LOBBIES_FOR", "LOBBIES_AGAINST"],
    ("LobbyGroup", "Industry"): ["REPRESENTS"],
    ("LobbyGroup", "ConsultationProcess"): ["ADVISES"],
    
    ("Industry", "GovernmentAgency"): ["INFLUENCES", "ADVISES"],
    ("Industry", "LegislativeProposal"): ["LOBBIES_FOR", "LOBBIES_AGAINST"],
    ("Industry", "Policy"): ["SUBJECT_TO"],
    ("Industry", "TechnicalStandard"): ["SUBJECT_TO"],
    
    ("Company", "LegislativeProposal"): ["LOBBIES_FOR", "LOBBIES_AGAINST"],
    ("Company", "Policy"): ["LOBBIES_FOR", "LOBBIES_AGAINST", "SUBJECT_TO"],
    ("Company", "Regulation"): ["SUBJECT_TO"],
    ("Company", "ComplianceObligation"): ["SUBJECT_TO"],
    ("Company", "Industry"): ["COMPETES_IN"],
    ("Company", "ConsultationProcess"): ["ADVISES"],
    
    ("Person", "LegislativeProposal"): ["INFLUENCES", "HAS_POSITION"],
    ("Person", "Policy"): ["INFLUENCES", "HAS_POSITION"],
    ("Person", "ConsultationProcess"): ["CONTRIBUTES"],
    ("Person", "Committee"): ["CONTRIBUTES"],
    ("Person", "Document"): ["CONTRIBUTES"],
    ("Person", "Company"): ["AFFILIATED_WITH"],
    ("Person", "GovernmentAgency"): ["AFFILIATED_WITH"],
    ("Person", "LobbyGroup"): ["AFFILIATED_WITH"],
    
    ("PoliticalParty", "LegislativeProposal"): ["INFLUENCES"],
    ("PoliticalParty", "Policy"): ["INFLUENCES"],
    
    # ===== BUSINESS IMPACT =====
    ("Policy", "Company"): ["AFFECTS", "REQUIRES_COMPLIANCE"],
    ("Policy", "Industry"): ["AFFECTS", "REQUIRES_COMPLIANCE"],
    
    ("Regulation", "Company"): ["AFFECTS", "REQUIRES_COMPLIANCE"],
    ("Regulation", "Industry"): ["AFFECTS"],
    ("Regulation", "Policy"): ["IMPLEMENTS", "REFERENCES"],
    ("Regulation", "TechnicalStandard"): ["REFERENCES"],
    ("Regulation", "Regulation"): ["SUPERSEDES", "AMENDS", "CONFLICTS_WITH"],
    
    ("ComplianceObligation", "Company"): ["AFFECTS"],
    ("ComplianceObligation", "Policy"): ["IMPLEMENTS"],
    ("ComplianceObligation", "Regulation"): ["IMPLEMENTS"],
    
    ("EnforcementAction", "Company"): ["AFFECTS"],
    ("EnforcementAction", "Industry"): ["AFFECTS"],
    ("EnforcementAction", "Policy"): ["TRIGGERS"],
    
    # ===== REGULATORY HIERARCHY =====
    ("TechnicalStandard", "Policy"): ["IMPLEMENTS"],
    ("TechnicalStandard", "LegalFramework"): ["IMPLEMENTS"],
    
    ("GovernmentAgency", "Policy"): ["ENFORCES"],
    ("GovernmentAgency", "Regulation"): ["ENFORCES"],
    ("GovernmentAgency", "Company"): ["MONITORS"],
    ("GovernmentAgency", "Industry"): ["MONITORS"],
    ("GovernmentAgency", "GovernmentAgency"): ["DELEGATES_TO"],
    
    ("Jurisdiction", "Policy"): ["ENFORCES"],
    ("Jurisdiction", "GovernmentAgency"): ["DELEGATES_TO"],
    
    ("LegislativeBody", "GovernmentAgency"): ["DELEGATES_TO"],
    
    # ===== TEMPORAL =====
    ("ConsultationProcess", "LegislativeProposal"): ["TRIGGERS", "PRECEDES"],
    
    # ===== REFERENCE =====
    ("Policy", "LegalFramework"): ["REFERENCES"],
    ("LegislativeProposal", "LegalFramework"): ["REFERENCES"],
}


# ===================================================================
# SECTION 5: SCHEMA METADATA
# ===================================================================

SCHEMA_INFO = {
    "version": "3.0-cleaned",
    "last_updated": "2025-01-13",
    "graphiti_compatible": True,
    "entity_count": len(ENTITY_TYPE_REGISTRY),
    "edge_count": len(EDGE_TYPE_REGISTRY),
    "pattern_count": sum(len(edges) for edges in EDGE_TYPE_MAP.values()),
    "description": "Cleaned and optimized schema with 20 entities - removed BusinessActivity, Market, RegulatoryRisk, and Exception as standalone entities (now properties)"
}


# ===================================================================
# HELPER FUNCTIONS
# ===================================================================

def get_entity_types() -> list[str]:
    """Get list of all entity type names."""
    return list(ENTITY_TYPE_REGISTRY.keys())


def get_edge_types() -> list[str]:
    """Get list of all edge type names."""
    return list(EDGE_TYPE_REGISTRY.keys())


def get_valid_edges_for_entity_pair(source: str, target: str) -> list[str]:
    """Get valid edge types for a source-target entity pair."""
    return EDGE_TYPE_MAP.get((source, target), [])


def validate_edge_pattern(source: str, edge: str, target: str) -> bool:
    """Check if an edge pattern is valid in the schema."""
    valid_edges = EDGE_TYPE_MAP.get((source, target), [])
    return edge in valid_edges


def get_schema_statistics() -> dict:
    """Get schema statistics and metadata."""
    return SCHEMA_INFO


def get_entities_by_tier() -> dict[str, list[str]]:
    """Get entities organized by tier."""
    return {
        "Legislative Process": [
            "LegislativeProposal", "LegislativeBody", "Committee", "Document", "Vote"
        ],
        "Final Outcomes": [
            "Policy", "Regulation"
        ],
        "Actors": [
            "Politician", "Person", "PoliticalParty", "GovernmentAgency", "LobbyGroup"
        ],
        "Business": [
            "Company", "Industry", "ComplianceObligation"
        ],
        "Process Tracking": [
            "ConsultationProcess", "EnforcementAction"
        ],
        "Geographic": [
            "Jurisdiction"
        ],
        "Technical/Legal": [
            "LegalFramework", "TechnicalStandard"
        ]
    }


# ===================================================================
# USAGE EXAMPLES
# ===================================================================

if __name__ == "__main__":
    # Print schema statistics
    stats = get_schema_statistics()
    print(f"Schema Version: {stats['version']}")
    print(f"Total Entities: {stats['entity_count']}")
    print(f"Total Edge Types: {stats['edge_count']}")
    print(f"Total Edge Patterns: {stats['pattern_count']}")
    
    print("\nEntities by Tier:")
    for tier, entities in get_entities_by_tier().items():
        print(f"\n{tier} ({len(entities)} entities):")
        for entity in entities:
            print(f"  - {entity}")
