"""
Unified Political Domain Schema for Policy Monitoring - v5.0

This schema merges v3 (EU/multi-jurisdiction) and v4 (German Bundestag) into a single
source of truth with separate export registries for different ingestion patterns.

## Export Sets:

### GENERAL (for data_ingestion/):
- 20 entity types (NO Bundestag entities)
- 52 edge types (can create relationships TO Bundestag nodes)
- Use case: General documents should NOT create Bundestag entities

### FULL (for bundestag_ingestion/):
- 28 entity types (20 general + 8 German Bundestag)
- 52 edge types (all relationships)
- Use case: Bundestag DIP API creates all entity types

Version: 5.0
Last Updated: 2025-11-25
Graphiti Compatible: Yes
"""

from typing import Optional

from pydantic import BaseModel, Field

# ===================================================================
# SECTION 1: ENTITY TYPE DEFINITIONS (28 Entity Types)
# ===================================================================

# --- TIER 1: LEGISLATIVE PROCESS ENTITIES (V3 - 5 entities) ---


class LegislativeProposal(BaseModel):
    """Draft legislation moving through the legislative process"""

    # legislative_proposal_name: str = Field(..., description="Working title of the proposal")
    proposal_id: Optional[str] = Field(
        None, description="Official identifier: COM(2024)123, BT-Drs 20/1234, etc."
    )
    jurisdiction: str = Field(..., description="EU, Germany, France, Bayern, etc.")
    legislative_body: str = Field(
        ..., description="European Parliament, Bundestag, Bundesrat, National Assembly, etc."
    )

    stage: str = Field(
        ...,
        description="Current stage: drafting, consultation, first_reading, committee, second_reading, third_reading, conciliation, mediation, adopted, rejected, withdrawn",
    )

    procedure_type: Optional[str] = Field(
        None,
        description="EU: ordinary_legislative, special_legislative, consent, consultation; Germany: consent_law, objection_law; France: normal, accelerated",
    )

    date_proposed: str = Field(..., description="When submitted to legislative body")
    expected_adoption: Optional[str] = Field(None, description="Expected/target adoption date")
    date_withdrawn: Optional[str] = Field(None, description="If withdrawn before vote")
    date_rejected: Optional[str] = Field(None, description="If rejected by vote")
    last_stage_change: Optional[str] = Field(None, description="When stage last changed")

    primary_sponsor: Optional[str] = Field(
        None, description="Main sponsor: politician, party, or institution"
    )
    co_sponsors: Optional[str] = Field(None, description="Additional sponsors")

    becomes_policy_id: Optional[str] = Field(
        None, description="Reference to final Policy entity if adopted"
    )

    legal_basis: Optional[str] = Field(
        None, description="Treaty basis: TFEU Art. 114, TFEU Art. 153, etc."
    )
    comitology_procedure: Optional[str] = Field(
        None, description="For implementing acts: examination, advisory"
    )

    requires_bundesrat_consent: Optional[bool] = Field(
        None, description="Zustimmungsgesetz (true) vs Einspruchsgesetz (false)"
    )
    mediation_committee_involved: Optional[bool] = Field(
        None, description="Whether Vermittlungsausschuss was invoked"
    )

    transposes_eu_directive: Optional[str] = Field(
        None, description="EU Directive ID being transposed"
    )
    transposition_deadline: Optional[str] = Field(None, description="Deadline for transposition")

    legislative_proposal_summary: Optional[str] = Field(
        None, description="Brief summary of proposal content"
    )
    policy_areas: Optional[str] = Field(None, description="Policy domains affected")

    voting_history: Optional[str] = Field(
        None,
        description="JSON array of votes on this proposal: [{body: 'European Parliament', stage: 'second_reading', date: '2024-01-15', outcome: 'passed', votes_for: 450, votes_against: 120, abstentions: 80, required_majority: 'simple', threshold_met: true, amendments_voted: 'Amendment 123, 124', notes: '...'}]",
    )

    last_updated: Optional[str] = Field(None, description="Last status update date")
    url: Optional[str] = Field(None, description="Link to official proposal page")


class LegislativeBody(BaseModel):
    """Unified entity for all legislative institutions"""

    # legislative_body_name: str = Field(
    #     ...,
    #     description="European Parliament, Bundestag, Council of EU, Bundesrat, National Assembly, etc.",
    # )
    jurisdiction: str = Field(..., description="EU, Germany, France, or Bundesland name")
    type: str = Field(
        ..., description="parliament, upper_chamber, lower_chamber, council, commission"
    )

    legislative_powers: str = Field(
        ...,
        description="co_decision, co_legislator, consent_only, objection, initiation_monopoly, advisory",
    )
    composition: Optional[str] = Field(
        None, description="Number of seats, composition rules, voting procedures"
    )
    term_length: Optional[str] = Field(None, description="Electoral term length")

    council_configuration: Optional[str] = Field(
        None, description="For Council of EU: ECOFIN, EPSCO, AGRIFISH, etc."
    )
    voting_rule: Optional[str] = Field(
        None, description="Qualified majority, unanimity, simple majority"
    )

    current_president: Optional[str] = Field(None, description="Current president/speaker")
    majority_party: Optional[str] = Field(None, description="Party holding majority")

    website: Optional[str] = Field(None, description="Official website")


class Committee(BaseModel):
    """Parliamentary/Council committees that examine legislation in detail"""

    # committee_name: str = Field(
    #     ..., description="Committee on Industry, Research and Energy; Ausschuss für Digitales, etc."
    # )
    parent_body: str = Field(..., description="Which LegislativeBody this belongs to")
    jurisdiction: str = Field(..., description="EU, Germany, etc.")

    policy_areas: Optional[str] = Field(
        None, description="Policy domains: digital, environment, finance, etc."
    )
    mandate: Optional[str] = Field(None, description="Official mandate and responsibilities")

    chair: Optional[str] = Field(None, description="Committee chair")
    members_count: Optional[int] = Field(None, description="Number of committee members")

    current_proposals: Optional[str] = Field(
        None, description="Proposals currently under examination"
    )

    committee_type: Optional[str] = Field(
        None, description="For EU: standing, temporary, inquiry, budgetary_control"
    )


class Document(BaseModel):
    """Official documents produced during the legislative process"""

    title: str = Field(..., description="Document title")
    document_id: Optional[str] = Field(None, description="Official identifier if available")
    document_type: str = Field(
        ...,
        description="impact_assessment, consultation_response, committee_report, amendment, position_paper, commission_proposal, referentenentwurf, regierungsentwurf, official_journal, reasoned_opinion, evaluation_report",
    )
    jurisdiction: str = Field(..., description="EU, Germany, etc.")

    author: str = Field(
        ..., description="Who produced it: Commission, Ministry, Committee, Politician, etc."
    )
    author_type: Optional[str] = Field(
        None, description="institution, politician, stakeholder, expert"
    )

    related_proposal: Optional[str] = Field(
        None, description="LegislativeProposal ID this relates to"
    )
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
    stage: str = Field(
        ...,
        description="Which reading/stage: first_reading, second_reading, third_reading, final, conciliation",
    )
    outcome: str = Field(..., description="passed, rejected, postponed, withdrawn")

    votes_for: Optional[int] = Field(None, description="Number of votes in favor")
    votes_against: Optional[int] = Field(None, description="Number of votes against")
    abstentions: Optional[int] = Field(None, description="Number of abstentions")

    required_majority: Optional[str] = Field(
        None, description="simple, absolute, qualified, two_thirds, unanimity"
    )
    threshold_met: Optional[bool] = Field(None, description="Whether required threshold was met")

    amendments_voted: Optional[str] = Field(None, description="Specific amendments voted on")
    notes: Optional[str] = Field(None, description="Additional context about the vote")


# --- TIER 2: FINAL POLICY OUTCOMES (V3 - 2 entities) ---


class Policy(BaseModel):
    """Final enacted laws and regulations"""

    # policy_name: str = Field(..., description="Official name of the enacted policy")
    policy_id: str = Field(
        ..., description="Official identifier: Regulation (EU) 2016/679, BGBl. I S. 2097, etc."
    )
    jurisdiction: str = Field(..., description="EU, Germany, Bayern, etc.")

    policy_type: str = Field(
        ...,
        description="EU: regulation, directive, decision; Germany: bundesgesetz, landesgesetz, rechtsverordnung; France: loi, décret",
    )

    legal_basis: Optional[str] = Field(
        None,
        description="Treaty article or constitutional article: TFEU Art. 114, GG Art. 74, etc.",
    )

    date_enacted: str = Field(..., description="Date of enactment/adoption")
    date_effective: str = Field(..., description="Date when policy takes effect")
    date_entry_into_force: Optional[str] = Field(None, description="Official entry into force date")

    is_directive: Optional[bool] = Field(
        None, description="True if this is an EU Directive requiring transposition"
    )
    transposition_deadline: Optional[str] = Field(
        None, description="Deadline for member states to transpose"
    )

    status: str = Field(..., description="in_force, repealed, amended, under_review, suspended")
    supersedes: Optional[str] = Field(None, description="Previous policy ID that this replaces")

    policy_summary: Optional[str] = Field(
        None, description="Summary of policy content and objectives"
    )
    policy_areas: Optional[str] = Field(None, description="Policy domains affected")
    scope: Optional[str] = Field(None, description="Who/what is covered by this policy")

    implementing_authority: Optional[str] = Field(
        None, description="Agency responsible for implementation"
    )
    evaluation_clause: Optional[str] = Field(
        None, description="Evaluation requirements and timeline"
    )

    exemptions: Optional[str] = Field(
        None,
        description="JSON array of exemptions: [{type: 'small_business', beneficiaries: '<250 employees', conditions: 'non-high-risk processing', scope: 'GDPR Article 30.5', expiry_date: null}]",
    )
    derogations: Optional[str] = Field(
        None,
        description="JSON array of member state derogations: [{member_state: 'France', provision: 'Article 23', justification: 'national security', duration: 'permanent'}]",
    )
    transitional_provisions: Optional[str] = Field(
        None,
        description="JSON array of grandfathering and phase-in rules: [{type: 'grandfathering', beneficiaries: 'existing systems', conditions: 'deployed before 2024', sunset_date: '2030-01-01'}]",
    )

    official_journal_reference: Optional[str] = Field(None, description="For EU: OJ reference")
    url: Optional[str] = Field(None, description="Link to official text")


class Regulation(BaseModel):
    """Implementing rules and technical regulations"""

    # regulation_name: str = Field(..., description="Name of the implementing regulation")
    regulation_id: str = Field(..., description="Official identifier")
    jurisdiction: str = Field(..., description="EU, Germany, etc.")

    parent_policy: str = Field(..., description="Policy ID that this regulation implements")

    regulation_type: Optional[str] = Field(
        None,
        description="EU: implementing_act, delegated_act; Germany: rechtsverordnung, verwaltungsvorschrift",
    )

    issuing_authority: str = Field(
        ..., description="Commission, Federal Ministry, State Ministry, etc."
    )
    legal_basis: Optional[str] = Field(None, description="Article empowering this regulation")

    date_issued: Optional[str] = Field(None, description="Date regulation was issued")
    effective_date: str = Field(..., description="Date regulation takes effect")

    compliance_deadline: Optional[str] = Field(None, description="Deadline for entities to comply")
    grace_period: Optional[str] = Field(None, description="Any grace period provisions")

    technical_requirements: Optional[str] = Field(
        None, description="Specific technical requirements"
    )
    standards_referenced: Optional[str] = Field(None, description="Technical standards referenced")

    enforcement_mechanism: Optional[str] = Field(None, description="How compliance is enforced")
    penalty_structure: Optional[str] = Field(None, description="Penalties for non-compliance")

    review_cycle: Optional[str] = Field(None, description="How often regulation is reviewed")
    status: Optional[str] = Field(None, description="active, suspended, repealed")

    exemptions: Optional[str] = Field(
        None, description="JSON array of exemptions applicable to this regulation"
    )


# --- TIER 3: ACTORS (V3 - 5 entities) ---


class Politician(BaseModel):
    """Individual politicians, elected officials, and appointees"""

    # politician_name: str = Field(..., description="Full name")
    jurisdiction: str = Field(..., description="EU, Germany, France, etc.")

    role: str = Field(
        ..., description="MEP, MdB (Member of Bundestag), Minister, Commissioner, Senator, etc."
    )
    title: Optional[str] = Field(None, description="Official title if applicable")

    party: Optional[str] = Field(None, description="Political party")
    party_group: Optional[str] = Field(None, description="For EU: EPP, S&D, Renew, Greens, etc.")

    legislative_body: Optional[str] = Field(
        None, description="Which LegislativeBody they belong to"
    )
    committee_memberships: Optional[str] = Field(None, description="Committee memberships")
    leadership_positions: Optional[str] = Field(
        None, description="Committee chair, faction leader, etc."
    )

    policy_focus: Optional[str] = Field(None, description="Policy areas of focus")
    proposals_sponsored: Optional[str] = Field(None, description="Key proposals sponsored")

    term_start: Optional[str] = Field(None, description="Start of current term")
    term_end: Optional[str] = Field(None, description="End of current term")

    website: Optional[str] = Field(None, description="Official website")
    voting_record_url: Optional[str] = Field(None, description="Link to voting record")


class Person(BaseModel):
    """Non-politician individuals who influence or comment on policy"""

    # person_name: str = Field(..., description="Full name")

    role: str = Field(
        ..., description="CEO, expert, academic, activist, journalist, influencer, consultant, etc."
    )
    title: Optional[str] = Field(None, description="Professional title: Dr., Prof., etc.")

    organization: Optional[str] = Field(
        None, description="Company, university, think tank, media outlet they represent"
    )
    organization_type: Optional[str] = Field(
        None, description="company, university, ngo, think_tank, media, consultancy"
    )

    expertise_areas: Optional[str] = Field(
        None, description="Areas of expertise: AI, climate, finance, etc."
    )
    credentials: Optional[str] = Field(
        None, description="Academic degrees, certifications, achievements"
    )

    influence_level: Optional[str] = Field(
        None, description="high, medium, low - level of public influence"
    )
    public_profile: Optional[str] = Field(None, description="Level of public recognition")

    jurisdiction: Optional[str] = Field(None, description="Primary country/region")

    linkedin_url: Optional[str] = Field(None, description="LinkedIn profile")
    twitter_handle: Optional[str] = Field(None, description="Twitter/X handle")
    website: Optional[str] = Field(None, description="Personal or professional website")


class PoliticalParty(BaseModel):
    """Political parties and their positions"""

    # political_party_name: str = Field(..., description="Party name")
    jurisdiction: str = Field(..., description="Country or level where party operates")

    party_family: Optional[str] = Field(
        None, description="European party family: PES, EPP, ALDE, EGP, etc."
    )

    seats_held: Optional[int] = Field(None, description="Number of seats in main legislative body")
    vote_share: Optional[str] = Field(None, description="Vote share in last election")

    party_leader: Optional[str] = Field(None, description="Current party leader")

    policy_platform: Optional[str] = Field(None, description="Key policy positions")
    regulatory_stance: Optional[str] = Field(
        None, description="General approach to regulation: pro-regulation, deregulation, balanced"
    )
    business_stance: Optional[str] = Field(None, description="Stance on business regulation")

    coalition_partners: Optional[str] = Field(
        None, description="Current coalition or alliance partners"
    )
    in_government: Optional[bool] = Field(None, description="Whether party is in government")


class GovernmentAgency(BaseModel):
    """Executive agencies, regulatory bodies, ministries"""

    # government_agency_name: str = Field(..., description="Official agency name")
    jurisdiction: str = Field(..., description="EU, Germany, etc.")

    agency_type: str = Field(
        ...,
        description="commission_dg, federal_ministry, state_ministry, regulatory_authority, executive_agency",
    )

    mandate: Optional[str] = Field(None, description="Official mandate and responsibilities")
    policy_areas: Optional[str] = Field(None, description="Policy areas covered")

    regulatory_powers: Optional[str] = Field(None, description="Regulatory powers granted")
    enforcement_authority: Optional[str] = Field(None, description="Enforcement powers")
    can_issue_regulations: Optional[bool] = Field(
        None, description="Whether agency can issue implementing regulations"
    )

    budget: Optional[str] = Field(None, description="Annual budget")
    staff_size: Optional[int] = Field(None, description="Number of staff")

    director: Optional[str] = Field(None, description="Agency head")
    reporting_to: Optional[str] = Field(None, description="Who agency reports to")

    parent_organization: Optional[str] = Field(None, description="Parent ministry or commission")
    website: Optional[str] = Field(None, description="Official website")


class LobbyGroup(BaseModel):
    """Interest groups, industry associations, NGOs, advocacy organizations"""

    # lobby_group_name: str = Field(..., description="Organization name")
    type: str = Field(
        ...,
        description="industry_association, trade_union, ngo, think_tank, advocacy_group, professional_association",
    )

    primary_jurisdiction: str = Field(
        ..., description="Main jurisdiction where organization is based: EU, Germany, France, etc."
    )
    additional_jurisdictions: Optional[str] = Field(
        None,
        description="JSON array of additional jurisdictions where active: ['France', 'Spain', 'Italy']",
    )
    policy_focus: Optional[str] = Field(None, description="Policy areas of focus")

    members: Optional[str] = Field(
        None, description="Key member organizations or number of members"
    )
    sectors_represented: Optional[str] = Field(None, description="Industry sectors represented")

    lobbying_budget: Optional[str] = Field(None, description="Annual lobbying expenditure")
    registered_lobbyists: Optional[int] = Field(None, description="Number of registered lobbyists")

    key_positions: Optional[str] = Field(None, description="Key policy positions")
    active_campaigns: Optional[str] = Field(None, description="Current advocacy campaigns")

    transparency_register_id: Optional[str] = Field(
        None, description="EU Transparency Register ID if applicable"
    )
    website: Optional[str] = Field(None, description="Organization website")


# --- TIER 4: BUSINESS ENTITIES (V3 - 3 entities) ---


class Company(BaseModel):
    """Individual corporations and business entities"""

    # company_name: str = Field(..., description="Company name")

    sector: str = Field(..., description="Primary industry sector")
    size: Optional[str] = Field(None, description="small, medium, large, multinational")

    revenue: Optional[str] = Field(None, description="Annual revenue")
    employee_count: Optional[int] = Field(None, description="Number of employees")

    headquarters: Optional[str] = Field(None, description="HQ location")
    jurisdictions_active: Optional[str] = Field(
        None, description="Countries/regions where company operates"
    )

    business_model: Optional[str] = Field(None, description="Primary business model")
    key_products: Optional[str] = Field(None, description="Main products/services")

    business_activities: Optional[str] = Field(
        None,
        description="JSON array of business activities: [{activity: 'algorithmic decision-making', risk_level: 'high', technology: 'AI', regulatory_coverage: 'AI Act, GDPR Art 22', data_implications: 'automated profiling'}]",
    )

    regulatory_risk_score: Optional[float] = Field(
        None, description="Computed overall regulatory risk score 0-100"
    )
    identified_risks: Optional[str] = Field(
        None,
        description="JSON array of identified regulatory risks: [{risk_type: 'compliance_failure', probability: 'high', impact_severity: 'critical', mitigation_strategies: '...', timeline: 'short_term'}]",
    )
    regulatory_risk_level: Optional[str] = Field(
        None, description="Overall risk category: low, medium, high, critical"
    )

    compliance_status: Optional[str] = Field(None, description="Overall compliance standing")
    data_practices: Optional[str] = Field(None, description="Data handling practices")

    public_private: Optional[str] = Field(None, description="public, private, state_owned")
    stock_ticker: Optional[str] = Field(None, description="Stock ticker if publicly traded")
    parent_company: Optional[str] = Field(None, description="Parent company if subsidiary")


class Industry(BaseModel):
    """Business sectors and industry classifications"""

    # industry_name: str = Field(..., description="Industry name")
    classification_code: Optional[str] = Field(None, description="NACE, NAICS, or SIC code")

    description: Optional[str] = Field(None, description="Industry description")
    sub_sectors: Optional[str] = Field(None, description="Key sub-sectors")

    market_size: Optional[str] = Field(None, description="Total market value")
    employment: Optional[int] = Field(None, description="Total industry employment")
    gdp_contribution: Optional[str] = Field(None, description="Contribution to GDP")

    key_players: Optional[str] = Field(None, description="Major companies in industry")
    market_concentration: Optional[str] = Field(None, description="HHI or concentration ratio")

    regulatory_intensity: Optional[str] = Field(
        None, description="Level of regulatory oversight: low, medium, high"
    )
    key_regulations: Optional[str] = Field(None, description="Main regulations affecting industry")

    innovation_rate: Optional[str] = Field(None, description="Pace of technological change")
    emerging_technologies: Optional[str] = Field(
        None, description="New technologies impacting industry"
    )

    common_activities: Optional[str] = Field(
        None,
        description="JSON array of typical business activities: [{activity: 'data processing', prevalence: 'widespread', technology: 'cloud computing'}]",
    )

    markets: Optional[str] = Field(
        None,
        description="JSON array of markets: [{name: 'EU digital advertising', geographic_scope: 'EU', market_size: '€50B', growth_rate: '8%', concentration: 'high', barriers_to_entry: 'high'}]",
    )


class ComplianceObligation(BaseModel):
    """Specific requirements that companies must meet"""

    requirement: str = Field(..., description="Specific compliance requirement description")
    source_policy: str = Field(..., description="Policy or Regulation creating this obligation")
    jurisdiction: str = Field(..., description="Where this applies")

    applies_to: Optional[str] = Field(
        None,
        description="Which entities must comply: all companies, specific sectors, size thresholds",
    )

    effective_date: Optional[str] = Field(None, description="When obligation takes effect")
    deadline: Optional[str] = Field(None, description="Compliance deadline")
    grace_period: Optional[str] = Field(None, description="Any grace period")

    frequency: Optional[str] = Field(
        None, description="How often requirement must be met: one-time, annual, continuous"
    )
    documentation_required: Optional[str] = Field(
        None, description="Documentation companies must maintain"
    )

    enforcing_authority: str = Field(..., description="Agency that enforces this obligation")
    penalty_for_non_compliance: Optional[str] = Field(None, description="Penalties for violation")

    complexity_level: Optional[str] = Field(
        None, description="Implementation complexity: low, medium, high"
    )
    estimated_cost: Optional[str] = Field(None, description="Estimated implementation cost")

    status: Optional[str] = Field(None, description="pending, active, suspended, repealed")


# --- TIER 5: PROCESS TRACKING (V3 - 2 entities) ---


class ConsultationProcess(BaseModel):
    """Public consultations and stakeholder engagement processes"""

    # consultation_process_name: str = Field(..., description="Consultation name/title")
    jurisdiction: str = Field(..., description="EU, Germany, etc.")

    organizing_authority: str = Field(
        ..., description="Institution conducting consultation: Commission, Ministry, etc."
    )

    related_proposal: Optional[str] = Field(
        None, description="LegislativeProposal ID if applicable"
    )
    policy_area: Optional[str] = Field(None, description="Policy domain")
    consultation_type: Optional[str] = Field(
        None,
        description="public_consultation, stakeholder_dialogue, impact_assessment_consultation",
    )

    start_date: str = Field(..., description="Consultation opening date")
    end_date: str = Field(..., description="Consultation closing date")
    duration_weeks: Optional[int] = Field(None, description="Duration in weeks")

    target_audience: Optional[str] = Field(None, description="Who can participate")
    submission_count: Optional[int] = Field(None, description="Number of responses received")
    participant_breakdown: Optional[str] = Field(
        None, description="Types of participants: companies, NGOs, citizens, etc."
    )

    key_themes: Optional[str] = Field(None, description="Main themes from responses")
    summary_report: Optional[str] = Field(None, description="Link to feedback summary")
    influence_on_outcome: Optional[str] = Field(
        None, description="How consultation shaped final proposal"
    )

    responses_published: Optional[bool] = Field(None, description="Whether responses are published")
    url: Optional[str] = Field(None, description="Link to consultation")


class EnforcementAction(BaseModel):
    """Fines, investigations, infringement procedures, sanctions"""

    action_type: str = Field(
        ...,
        description="infringement_notice, reasoned_opinion, cjeu_referral, fine, investigation, warning, sanction, criminal_prosecution",
    )
    jurisdiction: str = Field(..., description="EU, Germany, etc.")

    target: str = Field(..., description="Entity targeted: Company name, Member State, etc.")
    target_type: Optional[str] = Field(None, description="company, member_state, individual")

    enforcing_authority: str = Field(..., description="Commission, regulatory agency, court, etc.")

    date: str = Field(..., description="Date of action")
    violation: Optional[str] = Field(None, description="What law/regulation was violated")
    legal_basis: Optional[str] = Field(None, description="Legal basis for enforcement")

    fine_amount: Optional[str] = Field(None, description="Monetary penalty if applicable")
    daily_penalty: Optional[str] = Field(
        None, description="Daily penalty for continued non-compliance"
    )

    status: str = Field(..., description="initiated, ongoing, concluded, appealed, settled")
    appeal_status: Optional[str] = Field(None, description="Status of any appeal")
    outcome: Optional[str] = Field(None, description="Final outcome if concluded")

    precedent_value: Optional[str] = Field(None, description="Significance as legal precedent")
    corrective_measures_required: Optional[str] = Field(
        None, description="What target must do to comply"
    )

    case_number: Optional[str] = Field(None, description="Official case number")
    url: Optional[str] = Field(None, description="Link to case details")


# --- TIER 6: GEOGRAPHIC (V3 - 1 entity) ---


class Jurisdiction(BaseModel):
    """Geographic and legal jurisdictions"""

    # jurisdiction_name: str = Field(..., description="EU, Germany, France, Bayern, Paris, etc.")
    type: str = Field(
        ..., description="supranational, member_state, bundesland, region, municipality"
    )

    parent_jurisdiction: Optional[str] = Field(None, description="Bayern -> Germany -> EU")
    member_of: Optional[str] = Field(None, description="Which higher-level jurisdiction: EU, etc.")

    legal_system_type: Optional[str] = Field(None, description="civil_law, common_law, mixed")
    constitutional_basis: Optional[str] = Field(None, description="Constitution or treaty basis")

    population: Optional[int] = Field(None, description="Population size")
    gdp: Optional[str] = Field(None, description="GDP or economic size")

    regulatory_approach: Optional[str] = Field(None, description="Overall regulatory philosophy")
    enforcement_capability: Optional[str] = Field(
        None, description="Strength of enforcement: weak, moderate, strong"
    )

    treaties: Optional[str] = Field(None, description="International agreements and treaties")

    eu_accession_date: Optional[str] = Field(None, description="For member states: when joined EU")
    eurozone_member: Optional[bool] = Field(None, description="Whether in eurozone")
    schengen_member: Optional[bool] = Field(None, description="Whether in Schengen area")


# --- TIER 7: TECHNICAL/LEGAL SUPPORT (V3 - 2 entities) ---


class LegalFramework(BaseModel):
    """Broader legal context: constitutions, treaties, framework legislation"""

    # legal_framework_name: str = Field(
    #     ...,
    #     description="Treaty on European Union, Grundgesetz, Charter of Fundamental Rights, etc.",
    # )
    jurisdiction: str = Field(..., description="EU, Germany, etc.")

    framework_type: str = Field(
        ..., description="constitution, treaty, charter, framework_directive, enabling_act"
    )

    hierarchy_level: str = Field(
        ..., description="Position in legal hierarchy: primary_law, secondary_law, tertiary_law"
    )

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

    # technical_standard_name: str = Field(..., description="ISO 27001, EN standards, etc.")
    standard_id: Optional[str] = Field(None, description="Official standard identifier")

    issuing_body: str = Field(..., description="ISO, CEN, CENELEC, DIN, ETSI, etc.")
    jurisdiction: Optional[str] = Field(None, description="Where standard applies")

    standard_type: Optional[str] = Field(
        None,
        description="product_standard, process_standard, management_standard, testing_standard",
    )

    mandatory_voluntary: str = Field(
        ..., description="mandatory, voluntary, voluntary_but_presumed_compliance"
    )
    harmonized_standard: Optional[bool] = Field(
        None, description="For EU: whether it's a harmonized standard"
    )

    version: Optional[str] = Field(None, description="Current version")
    technical_specifications: Optional[str] = Field(None, description="Key technical requirements")

    certification_required: Optional[bool] = Field(
        None, description="Whether certification is needed"
    )
    testing_procedures: Optional[str] = Field(None, description="How compliance is tested")
    certification_bodies: Optional[str] = Field(None, description="Accredited certification bodies")

    date_published: Optional[str] = Field(None, description="Publication date")
    review_cycle: Optional[str] = Field(None, description="How often standard is reviewed")
    supersedes: Optional[str] = Field(None, description="Previous standard version")

    international_recognition: Optional[str] = Field(
        None, description="Where standard is recognized"
    )


# --- TIER 8: GERMAN BUNDESTAG ENTITIES (V4 - 8 entities) ---


class Drucksache(BaseModel):
    """German parliamentary printed document - bills, motions, reports

    Drucksachen are official parliamentary documents in the Bundestag,
    including legislative proposals (Gesetzentwürfe), motions (Anträge),
    committee recommendations (Beschlussempfehlungen), and reports (Berichte).
    """

    # drucksache_name: str = Field(..., description="Document title in German")
    drucksache_nummer: str = Field(
        ..., description="Document number format: wahlperiode/nummer (e.g., 20/1234)"
    )
    wahlperiode: int = Field(..., description="Electoral period number: 19, 20, 21, etc.")
    dokumentart: str = Field(
        ...,
        description="Document type: Gesetzentwurf, Antrag, Beschlussempfehlung, Bericht, Unterrichtung, Kleine Anfrage, Große Anfrage",
    )
    drucksachetyp: Optional[str] = Field(None, description="Type classification from API")

    datum: Optional[str] = Field(None, description="Document publication date (ISO format)")
    herausgeber: Optional[str] = Field(
        None, description="Publisher: BT (Bundestag), BR (Bundesrat), Ausschuss"
    )

    pdf_url: Optional[str] = Field(None, description="Direct link to PDF document")
    full_text: Optional[str] = Field(
        None,
        description="Extracted full text content from drucksache-text endpoint (deprecated - use DrucksachePage entities)",
    )

    autoren_anzahl: Optional[int] = Field(None, description="Number of document authors")
    autoren_anzeige: Optional[str] = Field(None, description="Display string of author names")

    fundstelle: Optional[str] = Field(None, description="Official reference/citation")
    aktualisiert: Optional[str] = Field(None, description="Last updated timestamp from API")

    vorgangsbezug_anzahl: Optional[int] = Field(
        None, description="Number of related Vorgang procedures"
    )
    related_vorgang_ids: Optional[str] = Field(
        None, description="JSON array of related Vorgang IDs"
    )

    url: Optional[str] = Field(None, description="Link to document details on dip.bundestag.de")

    # Storage and extraction metadata (Flow 5c)
    local_pdf_path: Optional[str] = Field(
        None,
        description="Local filesystem path to stored PDF: data/input/bundestag/drucksache/pdf/wahlperiode_20/20_1234.pdf",
    )
    local_markdown_path: Optional[str] = Field(
        None,
        description="Local filesystem path to extracted markdown: data/input/bundestag/drucksache/markdown/wahlperiode_20/20_1234.md",
    )
    has_full_text: bool = Field(
        False,
        description="Whether full text has been extracted page-by-page (creates DrucksachePage entities)",
    )
    page_count: Optional[int] = Field(None, description="Total number of pages extracted from PDF")
    file_size_bytes: Optional[int] = Field(None, description="PDF file size in bytes")
    extraction_error: Optional[str] = Field(
        None, description="Error message if PDF extraction failed"
    )


class DrucksachePage(BaseModel):
    """Individual page from a Drucksache document - enables page-level search and navigation

    DrucksachePage entities are created by Flow 5c when full-text extraction is enabled.
    Each page contains the extracted text from one page of the PDF document, enabling
    granular search and sequential navigation through documents.
    """

    page_id: str = Field(
        ..., description="Composite unique ID: drucksache_nummer_page_N (e.g., '20_1234_page_1')"
    )
    drucksache_nummer: str = Field(
        ..., description="Parent document number format: wahlperiode/nummer (e.g., '20/1234')"
    )
    page_number: int = Field(..., description="Page number within the document (1-indexed)")

    page_text: str = Field(..., description="Extracted text content from this page")
    char_count: int = Field(..., description="Character count for this page's text")
    has_content: bool = Field(
        ...,
        description="Whether page contains extractable text content (some pages may be blank/images only)",
    )


class Plenarprotokoll(BaseModel):
    """Record of Bundestag plenary session debates and proceedings

    Plenarprotokolle document complete plenary sessions including all speeches,
    votes, and procedural actions. They are the official record of parliamentary debates.
    """

    # plenarprotokoll_name: str = Field(..., description="Protocol title (usually session number)")
    sitzungsnummer: str = Field(..., description="Session number within the Wahlperiode")
    wahlperiode: int = Field(..., description="Electoral period number")
    datum: str = Field(..., description="Date of plenary session (ISO format)")

    herausgeber: str = Field(..., description="Publisher (typically BT - Bundestag)")
    pdf_url: Optional[str] = Field(None, description="Link to PDF protocol")
    full_text: Optional[str] = Field(
        None, description="Complete session transcript from plenarprotokoll-text endpoint"
    )

    tagesordnungspunkte: Optional[str] = Field(
        None,
        description="JSON array of agenda items (TOPs): [{top_nummer: '1', titel: '...', vorgaenge: [...]}]",
    )
    reden_anzahl: Optional[int] = Field(None, description="Number of speeches delivered in session")

    fundstelle: Optional[str] = Field(None, description="Official citation reference")
    aktualisiert: Optional[str] = Field(None, description="Last updated timestamp from API")

    vorgangsbezug_anzahl: Optional[int] = Field(None, description="Number of procedures discussed")
    related_vorgang_ids: Optional[str] = Field(
        None, description="JSON array of Vorgang IDs discussed in session"
    )

    url: Optional[str] = Field(None, description="Link to protocol on dip.bundestag.de")


class Vorgang(BaseModel):
    """Complete legislative procedure/process in the German Bundestag

    A Vorgang represents the entire lifecycle of a legislative initiative,
    from proposal through committee work, plenary debates, votes, and final outcome.
    """

    # vorgang_name: str = Field(..., description="Official procedure title in German")
    vorgangstyp: str = Field(
        ...,
        description="Procedure type: Gesetzgebung, Antrag, Große Anfrage, Kleine Anfrage, EU-Vorlage, etc.",
    )

    wahlperiode: int = Field(..., description="Electoral period number")
    vorgangsnummer: Optional[str] = Field(
        None, description="Unique procedure number within Wahlperiode"
    )

    initiative: Optional[str] = Field(
        None,
        description="Initiator: Bundesregierung (Government), Fraktion (Parliamentary Group), Bundesrat, Länder",
    )
    beratungsstand: str = Field(
        ...,
        description="Current status: Noch nicht beraten, In Beratung, Abgeschlossen, Erledigt, Zurückgezogen",
    )
    sachgebiet: Optional[str] = Field(
        None, description="Policy area: Digitalisierung, Innere Sicherheit, Wirtschaft, etc."
    )

    datum: Optional[str] = Field(None, description="Procedure start date (ISO format)")
    abgeschlossen_datum: Optional[str] = Field(
        None, description="Completion/conclusion date if finished"
    )

    abstract: Optional[str] = Field(None, description="Executive summary of the procedure")
    ziel: Optional[str] = Field(None, description="Stated objective or goal of the initiative")

    wichtige_drucksachen: Optional[str] = Field(
        None, description="JSON array of key document numbers: ['20/1234', '20/5678']"
    )
    plenum_anzahl: Optional[int] = Field(None, description="Number of plenary debates held")
    ausschuss_federf: Optional[str] = Field(
        None, description="Lead committee (federführender Ausschuss)"
    )

    inkrafttreten: Optional[str] = Field(None, description="Date law entered into force")
    verkuendung_bundesgesetzblatt: Optional[str] = Field(
        None, description="Federal Law Gazette citation if enacted: BGBl. I S. 2097"
    )
    ratifikation: Optional[str] = Field(
        None, description="Ratification information for international treaties"
    )

    gesta_id: Optional[str] = Field(None, description="GESTA database ID if applicable")
    aktualisiert: Optional[str] = Field(None, description="Last updated timestamp from API")
    url: Optional[str] = Field(None, description="Link to procedure on dip.bundestag.de")


class Vorgangsposition(BaseModel):
    """Specific position or step within a legislative procedure

    Vorgangspositionen track individual stages and actions within a Vorgang,
    such as committee referrals, readings, amendments, and votes.
    """

    # vorgangsposition_name: str = Field(..., description="Position title/description")
    zuordnung: str = Field(
        ..., description="Classification: BT (Bundestag), BR (Bundesrat), Ausschuss, etc."
    )

    vorgangstyp: Optional[str] = Field(None, description="Related procedure type")
    gang: Optional[str] = Field(None, description="Process stage or phase")
    fortsetzung: Optional[bool] = Field(None, description="Whether this is a continuation")
    nachtrag: Optional[bool] = Field(None, description="Whether this is an addendum/supplement")

    related_vorgang_id: Optional[str] = Field(
        None, description="Parent Vorgang ID this position belongs to"
    )
    dokumentnummer: Optional[str] = Field(
        None, description="Associated Drucksache number if applicable"
    )

    urheber: Optional[str] = Field(None, description="Originator of this procedural step")
    fundstelle: Optional[str] = Field(None, description="Where this step is documented")

    aktualisiert: Optional[str] = Field(None, description="Last updated timestamp from API")


class Aktivitaet(BaseModel):
    """Specific parliamentary activity or action

    Aktivitäten represent discrete actions taken in the parliamentary process,
    such as committee meetings, hearings, expert testimonies, or procedural motions.
    """

    # aktivitaet_name: str = Field(..., description="Activity title/description")
    aktivitaetsart: str = Field(..., description="Activity type from API classification")

    wahlperiode: Optional[int] = Field(None, description="Electoral period if applicable")
    datum: Optional[str] = Field(None, description="Activity date (ISO format)")

    related_vorgang_id: Optional[str] = Field(None, description="Related Vorgang procedure ID")
    related_drucksache_nummer: Optional[str] = Field(
        None, description="Related Drucksache document number"
    )

    urheber: Optional[str] = Field(None, description="Who initiated or performed the activity")
    fundstelle: Optional[str] = Field(None, description="Where activity details can be found")

    dokumentart: Optional[str] = Field(None, description="Type of related document if applicable")
    aktualisiert: Optional[str] = Field(None, description="Last updated timestamp from API")


class Wahlperiode(BaseModel):
    """German Bundestag electoral period/legislative term

    A Wahlperiode spans from one federal election to the next (typically 4 years),
    serving as the primary temporal organizing unit for German parliamentary data.
    """

    wahlperiode_nummer: int = Field(
        ..., description="Period number: 1 (1949), 19 (2017-2021), 20 (2021-2025), etc."
    )
    von: str = Field(..., description="Start date of electoral period (ISO format)")
    bis: Optional[str] = Field(None, description="End date of period (null if current/ongoing)")

    bundeskanzler: Optional[str] = Field(None, description="Federal Chancellor during this period")
    koalition: Optional[str] = Field(
        None, description="Governing coalition: e.g., 'SPD, GRÜNE, FDP'"
    )

    sitze_gesamt: Optional[int] = Field(
        None, description="Total number of Bundestag seats (varies by period)"
    )
    fraktionen: Optional[str] = Field(
        None,
        description="JSON array of parliamentary groups with seat counts: [{name: 'SPD', sitze: 206}, {name: 'CDU/CSU', sitze: 197}, ...]",
    )

    wahltag: Optional[str] = Field(
        None, description="Federal election date that initiated this period"
    )
    besonderheiten: Optional[str] = Field(
        None,
        description="Notable characteristics: e.g., 'First East-West unified Bundestag', 'Smallest majority since...', etc.",
    )


class BundestagPerson(BaseModel):
    """Member of the German Bundestag (MdB) - extends Politician with German-specific fields

    Represents current and former members of the Bundestag with German parliamentary
    context including Fraktion membership, committee assignments, and electoral information.
    """

    # person_name: str = Field(..., description="Full name (Vorname Nachname)")
    person_id: str = Field(..., description="Unique person ID from Bundestag API")

    fraktion: Optional[str] = Field(
        None,
        description="Current parliamentary group: CDU/CSU, SPD, GRÜNE, FDP, AfD, DIE LINKE, or fraktionslos",
    )
    partei: Optional[str] = Field(
        None, description="Political party affiliation (may differ from Fraktion)"
    )

    wahlperioden: Optional[str] = Field(
        None, description="JSON array of Wahlperiode numbers served: [19, 20, 21]"
    )
    ausschuss_mitgliedschaften: Optional[str] = Field(
        None,
        description="JSON array of committee memberships: [{ausschuss: 'Ausschuss Digitales', rolle: 'Mitglied/Vorsitzende/Obmann', von: '2021-11-01'}]",
    )

    titel: Optional[str] = Field(
        None, description="Academic or professional title: Dr., Prof. Dr., etc."
    )
    beruf: Optional[str] = Field(None, description="Professional occupation/background")
    geburtsdatum: Optional[str] = Field(
        None, description="Date of birth (may be partially redacted for privacy)"
    )
    geburtsort: Optional[str] = Field(None, description="Place of birth")

    wahlkreis: Optional[str] = Field(
        None, description="Directly elected constituency (Wahlkreis) if applicable"
    )
    landesliste: Optional[str] = Field(
        None, description="State list position if elected via proportional representation"
    )

    website: Optional[str] = Field(None, description="Personal or official website")
    foto_url: Optional[str] = Field(None, description="Link to official photo")

    aktualisiert: Optional[str] = Field(None, description="Last updated timestamp from API")


class BundestagFraktion(BaseModel):
    """Parliamentary group/faction in the German Bundestag

    Fraktionen are officially recognized parliamentary groups that must have
    at least 5% of seats. They organize legislative work and represent ideological blocs.
    """

    # fraktion_name: str = Field(
    #     ..., description="Full faction name: 'SPD', 'CDU/CSU', 'BÜNDNIS 90/DIE GRÜNEN', etc."
    # )
    kurz: str = Field(
        ..., description="Short name/abbreviation: 'SPD', 'CDU/CSU', 'GRÜNE', 'FDP', 'AfD', 'LINKE'"
    )

    wahlperiode: int = Field(..., description="Electoral period this faction exists in")
    sitze: int = Field(..., description="Number of Bundestag seats held")
    prozent: Optional[float] = Field(
        None, description="Percentage of total Bundestag seats (0-100)"
    )

    vorsitzende: Optional[str] = Field(
        None,
        description="JSON array of faction leaders/chairs: [{name: 'Person Name', von: '2021-11-01', bis: null}]",
    )
    parlamentarische_geschaeftsfuehrer: Optional[str] = Field(
        None, description="JSON array of parliamentary managers/whips"
    )

    koalition_opposition: str = Field(..., description="Status: 'Koalition' or 'Opposition'")
    koalitionspartner: Optional[str] = Field(
        None, description="Coalition partners if in government: ['SPD', 'GRÜNE', 'FDP']"
    )

    gruendungsdatum: Optional[str] = Field(None, description="Formation date in this Wahlperiode")
    mitglieder_anzahl: Optional[int] = Field(None, description="Total number of MdB members")

    farbe: Optional[str] = Field(
        None,
        description="Traditional party color for visualization: '#E3000F' (SPD red), '#000000' (CDU black), etc.",
    )


# ===================================================================
# SECTION 2: EDGE TYPE DEFINITIONS (52 Edge Types)
# ===================================================================

# --- V3 JURISDICTION RELATIONSHIP EDGES (3 edges) ---


class InJurisdiction(BaseModel):
    """Entity is located in or associated with jurisdiction"""

    relationship_type: str = Field(
        ...,
        description="based_in, proposed_in, enacted_in, conducted_in - specifies nature of relationship",
    )
    since: Optional[str] = Field(None, description="Start date of relationship")
    scope: Optional[str] = Field(None, description="full, partial, conditional")


class MemberOf(BaseModel):
    """Jurisdiction is member of parent jurisdiction"""

    membership_type: str = Field(
        ..., description="member_state, bundesland, region, municipality, etc."
    )
    joined_date: Optional[str] = Field(None, description="When joined")


class Represents(BaseModel):
    """Politician/Party represents jurisdiction"""

    representation_type: str = Field(..., description="elected, appointed")
    constituency: Optional[str]
    electoral_district: Optional[str] = Field(None, description="Specific district if applicable")
    term_start: Optional[str]
    term_end: Optional[str]


# --- V3 LEGISLATIVE PROCESS EDGES (6 edges) ---


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
    changes_made: Optional[str] = Field(
        None, description="Summary of changes from proposal to final"
    )


# --- V3 EU-GERMANY COORDINATION EDGES (4 edges) ---


class Transposes(BaseModel):
    """National law transposes EU Directive"""

    transposition_deadline: str
    transposition_date: Optional[str]
    transposition_status: str = Field(
        ..., description="not_started, in_progress, completed, overdue"
    )
    compliance_level: Optional[str] = Field(None, description="full, partial, incomplete")
    deviations: Optional[str] = Field(None, description="How national law differs from directive")


class GoldPlates(BaseModel):
    """National measure exceeds EU minimum requirements"""

    areas_exceeded: str = Field(..., description="Where national law goes beyond minimum")
    justification: Optional[str] = Field(None, description="Stated reason for gold-plating")


class InfringementAgainst(BaseModel):
    """Commission brings infringement against member state"""

    infringement_stage: str = Field(
        ..., description="letter_of_formal_notice, reasoned_opinion, cjeu_referral"
    )
    grounds: str = Field(..., description="Basis for infringement")
    date_initiated: str


class PreliminaryReference(BaseModel):
    """National court asks CJEU for interpretation"""

    case_number: str
    date_referred: str
    question: Optional[str] = Field(None, description="Legal question referred")
    date_decided: Optional[str]
    ruling_impact: Optional[str]


# --- V3 INFLUENCE AND POWER EDGES (6 edges) ---


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

    contribution_type: str = Field(
        ...,
        description="testimony, authorship, consultation_response, expert_opinion, speaking_engagement",
    )
    date: Optional[str]
    topic: Optional[str]
    url: Optional[str]
    role: Optional[str] = Field(
        None, description="lead_author, co_author, expert_witness, panelist"
    )


class AffiliatedWith(BaseModel):
    """Person affiliated with organization"""

    affiliation_type: str = Field(
        ..., description="employee, executive, board_member, consultant, advisor"
    )
    position: Optional[str] = Field(None, description="Specific position/title")
    start_date: Optional[str]
    end_date: Optional[str]
    is_current: Optional[bool] = Field(None, description="Whether affiliation is current")


# --- V3 BUSINESS IMPACT EDGES (5 edges) ---


class Affects(BaseModel):
    """Policy affects business entity"""

    impact_type: str = Field(
        ..., description="operational, financial, strategic, competitive, reputational"
    )
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
    regulatory_status: Optional[str] = Field(
        None, description="authorized, under_review, restricted"
    )


class CompetesIn(BaseModel):
    """Competition relationship"""

    market_position: Optional[str] = Field(None, description="leader, challenger, follower")
    competitive_advantage: Optional[str]


# --- V3 REGULATORY HIERARCHY EDGES (3 edges) ---


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


# --- V3 TEMPORAL EDGES (4 edges) ---


class Supersedes(BaseModel):
    """Policy replaces another"""

    transition_date: str
    reason: Optional[str]
    transitional_provisions: Optional[str]


class Amends(BaseModel):
    """Policy amends another"""

    amendment_date: str
    sections_modified: Optional[str]
    nature_of_change: Optional[str] = Field(
        None, description="expansion, restriction, clarification, correction"
    )


class Triggers(BaseModel):
    """Event triggers response"""

    trigger_event: str
    response_timeline: Optional[str]


class Precedes(BaseModel):
    """Sequential relationship"""

    time_gap: Optional[str]
    dependency_type: Optional[str] = Field(None, description="required, optional, recommended")


# --- V3 REFERENCE EDGES (3 edges) ---


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

    conflict_type: str = Field(
        ..., description="direct_contradiction, overlapping_scope, inconsistent_requirements"
    )
    resolution_mechanism: Optional[str]
    priority_rule: Optional[str] = Field(None, description="Which takes precedence")


# --- V3 STAKEHOLDER EDGES (2 edges) ---


class Advises(BaseModel):
    """Advisory relationship"""

    advice_type: str = Field(..., description="technical, policy, legal, scientific")
    frequency: Optional[str]


class Monitors(BaseModel):
    """Oversight relationship"""

    monitoring_scope: str
    reporting_frequency: Optional[str]
    enforcement_powers: Optional[bool]


# --- V4 GERMAN BUNDESTAG EDGES (15 edges) ---


class PartOfVorgang(BaseModel):
    """Vorgangsposition or Aktivität is part of a Vorgang procedure"""

    relationship_type: str = Field(
        default="PART_OF_VORGANG", description="Type of containment relationship"
    )
    sequence_number: Optional[int] = Field(None, description="Order in procedure if applicable")
    stage: Optional[str] = Field(
        None, description="Procedural stage: Einleitung, Beratung, Beschlussfassung, etc."
    )


class InitiatesVorgang(BaseModel):
    """Person or Fraktion initiates a legislative procedure"""

    date_initiated: Optional[str] = Field(None, description="When procedure was initiated")
    role: str = Field(..., description="Initiator role: Antragsteller, Einbringer, Urheber")
    co_initiators: Optional[str] = Field(None, description="JSON array of additional initiators")


class RelatesToDrucksache(BaseModel):
    """Vorgang or Vorgangsposition relates to a specific Drucksache"""

    relationship_type: str = Field(
        ...,
        description="Type of relationship: hauptdrucksache, beratungsgrundlage, beschlussempfehlung",
    )
    relevance: Optional[str] = Field(None, description="Importance: primary, supporting, reference")


class DebatedInPlenum(BaseModel):
    """Vorgang was debated in a plenary session"""

    debate_date: str = Field(..., description="Date of debate")
    reading: Optional[str] = Field(
        None, description="Which reading: Erste Beratung, Zweite Beratung, Dritte Beratung"
    )
    tagesordnungspunkt: Optional[str] = Field(None, description="Agenda item number (TOP)")
    outcome: Optional[str] = Field(
        None, description="Result of debate: angenommen, abgelehnt, überwiesen, vertagt"
    )


class SpeaksInPlenum(BaseModel):
    """Person delivers a speech in plenary session"""

    speech_date: str = Field(..., description="Date of speech")
    rede_nummer: Optional[str] = Field(None, description="Speech number in protocol")
    tagesordnungspunkt: Optional[str] = Field(None, description="Agenda item being addressed")
    rede_art: Optional[str] = Field(
        None,
        description="Speech type: Hauptrede, Zwischenruf, Persönliche Erklärung, Kurzintervention",
    )
    dauer_minuten: Optional[int] = Field(
        None, description="Speech duration in minutes if available"
    )


class InWahlperiode(BaseModel):
    """Entity exists within or is associated with an electoral period"""

    entity_type: str = Field(..., description="Type of entity linked to Wahlperiode")
    active_from: Optional[str] = Field(None, description="Start of activity in this period")
    active_until: Optional[str] = Field(
        None, description="End of activity in this period (null if ongoing)"
    )


class MemberOfFraktion(BaseModel):
    """Person is a member of a parliamentary group"""

    joined_date: Optional[str] = Field(None, description="When person joined faction")
    left_date: Optional[str] = Field(
        None, description="When person left faction (null if current member)"
    )
    role: Optional[str] = Field(
        None,
        description="Role in faction: Mitglied, Vorsitzende, Stellvertretende Vorsitzende, Parlamentarische Geschäftsführerin",
    )


class LeadsFraktion(BaseModel):
    """Person leads a parliamentary group as chair/co-chair"""

    leadership_role: str = Field(
        ..., description="Vorsitzende, Stellvertretende Vorsitzende, Fraktionsvorsitzende"
    )
    from_date: str = Field(..., description="Start of leadership")
    to_date: Optional[str] = Field(None, description="End of leadership (null if current)")


class RepresentsWahlkreis(BaseModel):
    """Person represents an electoral constituency"""

    wahlkreis_nummer: str = Field(..., description="Constituency number")
    # wahlkreis_name: str = Field(..., description="Constituency name")
    wahlperiode: int = Field(..., description="Electoral period of representation")
    elected_directly: bool = Field(
        ..., description="True if directly elected in constituency, False if via Landesliste"
    )
    vote_percentage: Optional[float] = Field(
        None, description="Percentage of votes received in constituency"
    )


class BundesratInvolvement(BaseModel):
    """Vorgang involves Bundesrat (Federal Council) consultation or approval"""

    involvement_type: str = Field(
        ...,
        description="Type: Zustimmungsbedürftig (consent required), Einspruchsgesetz (objection possible), Stellungnahme (opinion)",
    )
    bundesrat_decision: Optional[str] = Field(
        None,
        description="Bundesrat decision: Zugestimmt, Einspruch eingelegt, Stellungnahme abgegeben",
    )
    date: Optional[str] = Field(None, description="Date of Bundesrat action")


class BecomesBundesgesetz(BaseModel):
    """Vorgang becomes enacted federal law"""

    date_enacted: str = Field(..., description="Date of enactment")
    bundesgesetzblatt_reference: str = Field(
        ..., description="Federal Law Gazette citation: BGBl. I S. 2097"
    )
    date_effective: str = Field(..., description="Date law takes effect")
    verkuendung_date: Optional[str] = Field(None, description="Date of promulgation")


class AuthorsDrucksache(BaseModel):
    """Person is an author of a Drucksache document"""

    author_role: str = Field(..., description="Role: Hauptautor, Mitautor, Berichterstatter")
    author_position: Optional[int] = Field(
        None, description="Position in author list (1 = first author)"
    )


class AmendsDrucksache(BaseModel):
    """One Drucksache amends another"""

    amendment_type: str = Field(
        ..., description="Type: Änderungsantrag, Ergänzungsantrag, Alternativantrag"
    )
    date_proposed: Optional[str] = Field(None, description="When amendment was proposed")


class ReferencesVorgang(BaseModel):
    """Drucksache or Plenarprotokoll references a Vorgang"""

    reference_type: str = Field(
        ..., description="Type of reference: direkter_bezug, thematischer_bezug, verfahrensbezug"
    )
    context: Optional[str] = Field(None, description="Context of the reference")


class ActivityInVorgang(BaseModel):
    """Aktivität occurs as part of a Vorgang procedure"""

    activity_sequence: Optional[int] = Field(None, description="Order of activity in procedure")
    activity_impact: Optional[str] = Field(
        None, description="Impact on procedure: procedural, substantive, informational"
    )


# ===================================================================
# SECTION 3: REGISTRY DICTIONARIES - GENERAL (20 Entities, 52 Edges)
# ===================================================================

ENTITY_TYPE_REGISTRY_GENERAL: dict[str, type[BaseModel]] = {
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

EDGE_TYPE_REGISTRY_GENERAL: dict[str, type[BaseModel]] = {
    # V3 Edges (37)
    "IN_JURISDICTION": InJurisdiction,
    "MEMBER_OF": MemberOf,
    "REPRESENTS": Represents,
    "PROPOSES": Proposes,
    "SUBMITS_TO": SubmitsTo,
    "EXAMINES": Examines,
    "AMENDS_PROPOSAL": AmendsProposal,
    "VOTES_ON": VotesOn,
    "BECOMES": Becomes,
    "TRANSPOSES": Transposes,
    "GOLD_PLATES": GoldPlates,
    "INFRINGEMENT_AGAINST": InfringementAgainst,
    "PRELIMINARY_REFERENCE": PreliminaryReference,
    "INFLUENCES": Influences,
    "LOBBIES_FOR": LobbiesFor,
    "LOBBIES_AGAINST": LobbiesAgainst,
    "HAS_POSITION": HasPosition,
    "CONTRIBUTES": Contributes,
    "AFFILIATED_WITH": AffiliatedWith,
    "AFFECTS": Affects,
    "SUBJECT_TO": SubjectTo,
    "REQUIRES_COMPLIANCE": RequiresCompliance,
    "OPERATES_IN": OperatesIn,
    "COMPETES_IN": CompetesIn,
    "IMPLEMENTS": Implements,
    "ENFORCES": Enforces,
    "DELEGATES_TO": DelegatesTo,
    "SUPERSEDES": Supersedes,
    "AMENDS": Amends,
    "TRIGGERS": Triggers,
    "PRECEDES": Precedes,
    "REFERENCES": References,
    "HARMONIZES_WITH": HarmonizesWith,
    "CONFLICTS_WITH": ConflictsWith,
    "ADVISES": Advises,
    "MONITORS": Monitors,
    # V4 German Bundestag Edges (15) - included for relationships TO Bundestag nodes
    "PART_OF_VORGANG": PartOfVorgang,
    "INITIATES_VORGANG": InitiatesVorgang,
    "RELATES_TO_DRUCKSACHE": RelatesToDrucksache,
    "DEBATED_IN_PLENUM": DebatedInPlenum,
    "SPEAKS_IN_PLENUM": SpeaksInPlenum,
    "IN_WAHLPERIODE": InWahlperiode,
    "MEMBER_OF_FRAKTION": MemberOfFraktion,
    "LEADS_FRAKTION": LeadsFraktion,
    "REPRESENTS_WAHLKREIS": RepresentsWahlkreis,
    "BUNDESRAT_INVOLVEMENT": BundesratInvolvement,
    "BECOMES_BUNDESGESETZ": BecomesBundesgesetz,
    "AUTHORS_DRUCKSACHE": AuthorsDrucksache,
    "AMENDS_DRUCKSACHE": AmendsDrucksache,
    "REFERENCES_VORGANG": ReferencesVorgang,
    "ACTIVITY_IN_VORGANG": ActivityInVorgang,
}

# Edge type map for GENERAL - V3 mappings only (no Bundestag entity sources)
EDGE_TYPE_MAP_GENERAL: dict[tuple[str, str], list[str]] = {
    # ===== JURISDICTION RELATIONSHIPS =====
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
    ("Jurisdiction", "Jurisdiction"): ["MEMBER_OF", "HARMONIZES_WITH", "CONFLICTS_WITH"],
    ("Politician", "Jurisdiction"): ["REPRESENTS"],
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
    ("Policy", "Policy"): [
        "TRANSPOSES",
        "GOLD_PLATES",
        "SUPERSEDES",
        "AMENDS",
        "REFERENCES",
        "CONFLICTS_WITH",
    ],
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
    # ===== RELATIONSHIPS TO BUNDESTAG ENTITIES (no sources from Bundestag entities) =====
    ("Person", "Vorgang"): ["INITIATES_VORGANG"],
    ("Person", "Drucksache"): ["AUTHORS_DRUCKSACHE"],
    ("Person", "Plenarprotokoll"): ["SPEAKS_IN_PLENUM"],
    ("Person", "BundestagFraktion"): ["MEMBER_OF_FRAKTION", "LEADS_FRAKTION"],
    ("Person", "Wahlperiode"): ["IN_WAHLPERIODE"],
    ("PoliticalParty", "Vorgang"): ["INITIATES_VORGANG"],
    ("LegislativeProposal", "Vorgang"): ["BECOMES"],
    ("LegislativeBody", "Vorgang"): ["BUNDESRAT_INVOLVEMENT"],
    ("Policy", "Vorgang"): ["BECOMES_BUNDESGESETZ"],
}


# ===================================================================
# SECTION 4: REGISTRY DICTIONARIES - FULL (28 Entities, 52 Edges)
# ===================================================================

ENTITY_TYPE_REGISTRY_FULL: dict[str, type[BaseModel]] = {
    **ENTITY_TYPE_REGISTRY_GENERAL,  # All 20 general entities
    # German Bundestag Entities (8)
    "Drucksache": Drucksache,
    "DrucksachePage": DrucksachePage,
    "Plenarprotokoll": Plenarprotokoll,
    "Vorgang": Vorgang,
    "Vorgangsposition": Vorgangsposition,
    "Aktivitaet": Aktivitaet,
    "Wahlperiode": Wahlperiode,
    "BundestagPerson": BundestagPerson,
    "BundestagFraktion": BundestagFraktion,
}

EDGE_TYPE_REGISTRY_FULL: dict[str, type[BaseModel]] = EDGE_TYPE_REGISTRY_GENERAL  # Same 52 edges

# Edge type map for FULL - includes all v3 + v4 mappings
EDGE_TYPE_MAP_FULL: dict[tuple[str, str], list[str]] = {
    **EDGE_TYPE_MAP_GENERAL,  # All general mappings
    # ===== GERMAN BUNDESTAG EDGE MAPPINGS (from v4) =====
    ("Vorgangsposition", "Vorgang"): ["PART_OF_VORGANG"],
    ("Aktivitaet", "Vorgang"): ["PART_OF_VORGANG", "ACTIVITY_IN_VORGANG"],
    ("Aktivitaet", "Drucksache"): ["REFERENCES"],
    ("BundestagPerson", "Vorgang"): ["INITIATES_VORGANG"],
    ("BundestagPerson", "Drucksache"): ["AUTHORS_DRUCKSACHE"],
    ("BundestagPerson", "Plenarprotokoll"): ["SPEAKS_IN_PLENUM"],
    ("BundestagPerson", "BundestagFraktion"): ["MEMBER_OF_FRAKTION", "LEADS_FRAKTION"],
    ("BundestagPerson", "Wahlperiode"): ["IN_WAHLPERIODE"],
    ("BundestagPerson", "Jurisdiction"): ["REPRESENTS_WAHLKREIS"],
    ("BundestagPerson", "Committee"): ["AFFILIATED_WITH"],
    ("BundestagPerson", "Policy"): ["HAS_POSITION", "LOBBIES_FOR", "LOBBIES_AGAINST"],
    ("BundestagFraktion", "Vorgang"): ["INITIATES_VORGANG"],
    ("BundestagFraktion", "Wahlperiode"): ["IN_WAHLPERIODE"],
    ("BundestagFraktion", "Policy"): ["HAS_POSITION", "LOBBIES_FOR", "LOBBIES_AGAINST"],
    ("BundestagFraktion", "LegislativeProposal"): ["PROPOSES", "INFLUENCES"],
    ("Vorgang", "Drucksache"): ["RELATES_TO_DRUCKSACHE"],
    ("Vorgang", "Plenarprotokoll"): ["DEBATED_IN_PLENUM"],
    ("Vorgang", "Wahlperiode"): ["IN_WAHLPERIODE"],
    ("Vorgang", "LegislativeBody"): ["BUNDESRAT_INVOLVEMENT"],
    ("Vorgang", "Policy"): ["BECOMES_BUNDESGESETZ", "BECOMES"],
    ("Vorgang", "LegislativeProposal"): ["BECOMES"],
    ("Drucksache", "Drucksache"): ["AMENDS_DRUCKSACHE", "REFERENCES"],
    ("Drucksache", "Vorgang"): ["REFERENCES_VORGANG"],
    ("Drucksache", "Wahlperiode"): ["IN_WAHLPERIODE"],
    ("Plenarprotokoll", "Vorgang"): ["REFERENCES_VORGANG"],
    ("Plenarprotokoll", "Wahlperiode"): ["IN_WAHLPERIODE"],
}


# ===================================================================
# SECTION 5: BACKWARDS COMPATIBILITY EXPORTS
# ===================================================================

# Default to FULL for backwards compatibility with existing code
ENTITY_TYPE_REGISTRY = ENTITY_TYPE_REGISTRY_FULL
EDGE_TYPE_REGISTRY = EDGE_TYPE_REGISTRY_FULL
EDGE_TYPE_MAP = EDGE_TYPE_MAP_FULL


# ===================================================================
# SECTION 6: SCHEMA METADATA
# ===================================================================

SCHEMA_INFO_V5 = {
    "version": "5.0",
    "last_updated": "2025-11-25",
    "base_schemas": ["v3.0", "v4.0"],
    "graphiti_compatible": True,
    "total_entity_count": len(ENTITY_TYPE_REGISTRY_FULL),  # 28 (20 general + 8 German)
    "general_entity_count": len(ENTITY_TYPE_REGISTRY_GENERAL),  # 20
    "bundestag_entity_count": 8,
    "total_edge_count": len(EDGE_TYPE_REGISTRY_FULL),  # 52 (37 v3 + 15 v4)
    "general_pattern_count": len(EDGE_TYPE_MAP_GENERAL),
    "full_pattern_count": len(EDGE_TYPE_MAP_FULL),
    "description": "Unified schema with separate export registries for general vs. Bundestag ingestion",
}


# ===================================================================
# SECTION 7: HELPER FUNCTIONS
# ===================================================================


def get_entity_types(registry: str = "full") -> list[str]:
    """Get list of all entity type names.

    Args:
        registry: "general" (20 entities) or "full" (28 entities)
    """
    if registry == "general":
        return list(ENTITY_TYPE_REGISTRY_GENERAL.keys())
    return list(ENTITY_TYPE_REGISTRY_FULL.keys())


def get_edge_types() -> list[str]:
    """Get list of all edge type names (same for both registries)."""
    return list(EDGE_TYPE_REGISTRY_FULL.keys())


def get_valid_edges_for_entity_pair(source: str, target: str, registry: str = "full") -> list[str]:
    """Get valid edge types for a source-target entity pair.

    Args:
        source: Source entity type
        target: Target entity type
        registry: "general" or "full" - determines which edge map to use
    """
    if registry == "general":
        return EDGE_TYPE_MAP_GENERAL.get((source, target), [])
    return EDGE_TYPE_MAP_FULL.get((source, target), [])


def validate_edge_pattern(source: str, edge: str, target: str, registry: str = "full") -> bool:
    """Check if an edge pattern is valid in the schema.

    Args:
        source: Source entity type
        edge: Edge type
        target: Target entity type
        registry: "general" or "full"
    """
    valid_edges = get_valid_edges_for_entity_pair(source, target, registry)
    return edge in valid_edges


def get_schema_statistics() -> dict:
    """Get schema statistics and metadata."""
    return SCHEMA_INFO_V5


def get_entities_by_tier(registry: str = "full") -> dict[str, list[str]]:
    """Get entities organized by tier.

    Args:
        registry: "general" (v3 only) or "full" (v3 + v4)
    """
    tiers = {
        "Legislative Process": [
            "LegislativeProposal",
            "LegislativeBody",
            "Committee",
            "Document",
            "Vote",
        ],
        "Final Outcomes": ["Policy", "Regulation"],
        "Actors": ["Politician", "Person", "PoliticalParty", "GovernmentAgency", "LobbyGroup"],
        "Business": ["Company", "Industry", "ComplianceObligation"],
        "Process Tracking": ["ConsultationProcess", "EnforcementAction"],
        "Geographic": ["Jurisdiction"],
        "Technical/Legal": ["LegalFramework", "TechnicalStandard"],
    }

    if registry == "full":
        tiers["German Bundestag"] = [
            "Drucksache",
            "DrucksachePage",
            "Plenarprotokoll",
            "Vorgang",
            "Vorgangsposition",
            "Aktivitaet",
            "Wahlperiode",
            "BundestagPerson",
            "BundestagFraktion",
        ]

    return tiers


def get_german_bundestag_entities() -> list[str]:
    """Get list of German Bundestag-specific entity types."""
    return [
        "Drucksache",
        "DrucksachePage",
        "Plenarprotokoll",
        "Vorgang",
        "Vorgangsposition",
        "Aktivitaet",
        "Wahlperiode",
        "BundestagPerson",
        "BundestagFraktion",
    ]


def get_german_bundestag_edges() -> list[str]:
    """Get list of German Bundestag-specific edge types."""
    return [
        "PART_OF_VORGANG",
        "INITIATES_VORGANG",
        "RELATES_TO_DRUCKSACHE",
        "DEBATED_IN_PLENUM",
        "SPEAKS_IN_PLENUM",
        "IN_WAHLPERIODE",
        "MEMBER_OF_FRAKTION",
        "LEADS_FRAKTION",
        "REPRESENTS_WAHLKREIS",
        "BUNDESRAT_INVOLVEMENT",
        "BECOMES_BUNDESGESETZ",
        "AUTHORS_DRUCKSACHE",
        "AMENDS_DRUCKSACHE",
        "REFERENCES_VORGANG",
        "ACTIVITY_IN_VORGANG",
    ]


# ===================================================================
# USAGE EXAMPLES
# ===================================================================

if __name__ == "__main__":
    # Print schema statistics
    stats = get_schema_statistics()
    print("=" * 80)
    print("POLITICAL SCHEMA V5.0 - UNIFIED WITH SEPARATE REGISTRIES")
    print("=" * 80)
    print(f"\nSchema Version: {stats['version']}")
    print(f"Base Schemas: {', '.join(stats['base_schemas'])}")
    print(f"\nTotal Entities: {stats['total_entity_count']} (28 = 20 general + 8 Bundestag)")
    print(f"Total Edge Types: {stats['total_edge_count']} (52 = 37 v3 + 15 v4)")
    print(
        f"\nGeneral Registry: {stats['general_entity_count']} entities, {stats['general_pattern_count']} patterns"
    )
    print(
        f"Full Registry: {stats['total_entity_count']} entities, {stats['full_pattern_count']} patterns"
    )

    print("\n" + "=" * 80)
    print("ENTITIES BY TIER (FULL REGISTRY)")
    print("=" * 80)
    for tier, entities in get_entities_by_tier("full").items():
        print(f"\n{tier} ({len(entities)} entities):")
        for entity in entities:
            print(f"  - {entity}")

    print("\n" + "=" * 80)
    print("GERMAN BUNDESTAG ENTITIES (v4 Extension)")
    print("=" * 80)
    for entity in get_german_bundestag_entities():
        print(f"  - {entity}")

    print("\n" + "=" * 80)
    print("EXAMPLE: GENERAL vs FULL REGISTRY DIFFERENCES")
    print("=" * 80)

    print("\nGENERAL Registry Entities (20):")
    print(f"  {', '.join(get_entity_types('general'))}")

    print("\nFULL Registry Entities (28):")
    print(f"  {', '.join(get_entity_types('full'))}")

    print("\n" + "=" * 80)
    print("EXAMPLE EDGE VALIDATIONS")
    print("=" * 80)

    # Test edge patterns in both registries
    test_patterns = [
        ("Person", "INITIATES_VORGANG", "Vorgang"),  # Valid in GENERAL (to Bundestag)
        ("BundestagPerson", "MEMBER_OF_FRAKTION", "BundestagFraktion"),  # Only valid in FULL
        ("Policy", "AFFECTS", "Company"),  # Valid in both
    ]

    for source, edge, target in test_patterns:
        general_valid = validate_edge_pattern(source, edge, target, "general")
        full_valid = validate_edge_pattern(source, edge, target, "full")
        print(f"\n{source} --[{edge}]--> {target}")
        print(f"  GENERAL: {'✅ Valid' if general_valid else '❌ Invalid'}")
        print(f"  FULL:    {'✅ Valid' if full_valid else '❌ Invalid'}")

    print("\n" + "=" * 80)
