"""
Political Domain Schema for Policy Monitoring - v4.0 (German Bundestag Extension)

This schema extends v3.0 with German Bundestag parliamentary system entities while
maintaining full EU and multi-jurisdiction support.

Version: 4.0
Last Updated: 2025-11-12
Base Schema: v3.0
Extensions: German Bundestag Parliamentary System
Graphiti Compatible: Yes
"""

from typing import Optional
from pydantic import BaseModel, Field

# Import all v3 entities and edges
from src.graphrag.political_schema_v3 import (
    # Tier 1: Legislative Process
    LegislativeProposal,
    LegislativeBody,
    Committee,
    Document,
    Vote,
    # Tier 2: Final Outcomes
    Policy,
    Regulation,
    # Tier 3: Actors
    Politician,
    Person,
    PoliticalParty,
    GovernmentAgency,
    LobbyGroup,
    # Tier 4: Business
    Company,
    Industry,
    ComplianceObligation,
    # Tier 5: Process Tracking
    ConsultationProcess,
    EnforcementAction,
    # Tier 6: Geographic
    Jurisdiction,
    # Tier 7: Technical/Legal
    LegalFramework,
    TechnicalStandard,
    # All v3 edges
    InJurisdiction,
    MemberOf,
    Represents,
    Proposes,
    SubmitsTo,
    Examines,
    AmendsProposal,
    VotesOn,
    Becomes,
    Transposes,
    GoldPlates,
    InfringementAgainst,
    PreliminaryReference,
    Influences,
    LobbiesFor,
    LobbiesAgainst,
    HasPosition,
    Contributes,
    AffiliatedWith,
    Affects,
    SubjectTo,
    RequiresCompliance,
    OperatesIn,
    CompetesIn,
    Implements,
    Enforces,
    DelegatesTo,
    Supersedes,
    Amends,
    Triggers,
    Precedes,
    References,
    HarmonizesWith,
    ConflictsWith,
    Advises,
    Monitors,
)


# ===================================================================
# SECTION 1: NEW GERMAN BUNDESTAG ENTITY DEFINITIONS (8 Entity Types)
# ===================================================================

class Drucksache(BaseModel):
    """German parliamentary printed document - bills, motions, reports

    Drucksachen are official parliamentary documents in the Bundestag,
    including legislative proposals (Gesetzentwürfe), motions (Anträge),
    committee recommendations (Beschlussempfehlungen), and reports (Berichte).
    """
    drucksache_name: str = Field(..., description="Document title in German")
    drucksache_nummer: str = Field(..., description="Document number format: wahlperiode/nummer (e.g., 20/1234)")
    wahlperiode: int = Field(..., description="Electoral period number: 19, 20, 21, etc.")
    dokumentart: str = Field(..., description="Document type: Gesetzentwurf, Antrag, Beschlussempfehlung, Bericht, Unterrichtung, Kleine Anfrage, Große Anfrage")
    drucksachetyp: Optional[str] = Field(None, description="Type classification from API")

    datum: Optional[str] = Field(None, description="Document publication date (ISO format)")
    herausgeber: Optional[str] = Field(None, description="Publisher: BT (Bundestag), BR (Bundesrat), Ausschuss")

    pdf_url: Optional[str] = Field(None, description="Direct link to PDF document")
    full_text: Optional[str] = Field(None, description="Extracted full text content from drucksache-text endpoint")

    autoren_anzahl: Optional[int] = Field(None, description="Number of document authors")
    autoren_anzeige: Optional[str] = Field(None, description="Display string of author names")

    fundstelle: Optional[str] = Field(None, description="Official reference/citation")
    aktualisiert: Optional[str] = Field(None, description="Last updated timestamp from API")

    vorgangsbezug_anzahl: Optional[int] = Field(None, description="Number of related Vorgang procedures")
    related_vorgang_ids: Optional[str] = Field(None, description="JSON array of related Vorgang IDs")

    url: Optional[str] = Field(None, description="Link to document details on dip.bundestag.de")


class Plenarprotokoll(BaseModel):
    """Record of Bundestag plenary session debates and proceedings

    Plenarprotokolle document complete plenary sessions including all speeches,
    votes, and procedural actions. They are the official record of parliamentary debates.
    """
    plenarprotokoll_name: str = Field(..., description="Protocol title (usually session number)")
    sitzungsnummer: str = Field(..., description="Session number within the Wahlperiode")
    wahlperiode: int = Field(..., description="Electoral period number")
    datum: str = Field(..., description="Date of plenary session (ISO format)")

    herausgeber: str = Field(..., description="Publisher (typically BT - Bundestag)")
    pdf_url: Optional[str] = Field(None, description="Link to PDF protocol")
    full_text: Optional[str] = Field(None, description="Complete session transcript from plenarprotokoll-text endpoint")

    tagesordnungspunkte: Optional[str] = Field(
        None,
        description="JSON array of agenda items (TOPs): [{top_nummer: '1', titel: '...', vorgaenge: [...]}]"
    )
    reden_anzahl: Optional[int] = Field(None, description="Number of speeches delivered in session")

    fundstelle: Optional[str] = Field(None, description="Official citation reference")
    aktualisiert: Optional[str] = Field(None, description="Last updated timestamp from API")

    vorgangsbezug_anzahl: Optional[int] = Field(None, description="Number of procedures discussed")
    related_vorgang_ids: Optional[str] = Field(None, description="JSON array of Vorgang IDs discussed in session")

    url: Optional[str] = Field(None, description="Link to protocol on dip.bundestag.de")


class Vorgang(BaseModel):
    """Complete legislative procedure/process in the German Bundestag

    A Vorgang represents the entire lifecycle of a legislative initiative,
    from proposal through committee work, plenary debates, votes, and final outcome.
    """
    vorgang_name: str = Field(..., description="Official procedure title in German")
    vorgangstyp: str = Field(..., description="Procedure type: Gesetzgebung, Antrag, Große Anfrage, Kleine Anfrage, EU-Vorlage, etc.")

    wahlperiode: int = Field(..., description="Electoral period number")
    vorgangsnummer: Optional[str] = Field(None, description="Unique procedure number within Wahlperiode")

    initiative: Optional[str] = Field(None, description="Initiator: Bundesregierung (Government), Fraktion (Parliamentary Group), Bundesrat, Länder")
    beratungsstand: str = Field(..., description="Current status: Noch nicht beraten, In Beratung, Abgeschlossen, Erledigt, Zurückgezogen")
    sachgebiet: Optional[str] = Field(None, description="Policy area: Digitalisierung, Innere Sicherheit, Wirtschaft, etc.")

    datum: Optional[str] = Field(None, description="Procedure start date (ISO format)")
    abgeschlossen_datum: Optional[str] = Field(None, description="Completion/conclusion date if finished")

    abstract: Optional[str] = Field(None, description="Executive summary of the procedure")
    ziel: Optional[str] = Field(None, description="Stated objective or goal of the initiative")

    wichtige_drucksachen: Optional[str] = Field(
        None,
        description="JSON array of key document numbers: ['20/1234', '20/5678']"
    )
    plenum_anzahl: Optional[int] = Field(None, description="Number of plenary debates held")
    ausschuss_federf: Optional[str] = Field(None, description="Lead committee (federführender Ausschuss)")

    inkrafttreten: Optional[str] = Field(None, description="Date law entered into force")
    verkuendung_bundesgesetzblatt: Optional[str] = Field(None, description="Federal Law Gazette citation if enacted: BGBl. I S. 2097")
    ratifikation: Optional[str] = Field(None, description="Ratification information for international treaties")

    gesta_id: Optional[str] = Field(None, description="GESTA database ID if applicable")
    aktualisiert: Optional[str] = Field(None, description="Last updated timestamp from API")
    url: Optional[str] = Field(None, description="Link to procedure on dip.bundestag.de")


class Vorgangsposition(BaseModel):
    """Specific position or step within a legislative procedure

    Vorgangspositionen track individual stages and actions within a Vorgang,
    such as committee referrals, readings, amendments, and votes.
    """
    vorgangsposition_name: str = Field(..., description="Position title/description")
    zuordnung: str = Field(..., description="Classification: BT (Bundestag), BR (Bundesrat), Ausschuss, etc.")

    vorgangstyp: Optional[str] = Field(None, description="Related procedure type")
    gang: Optional[str] = Field(None, description="Process stage or phase")
    fortsetzung: Optional[bool] = Field(None, description="Whether this is a continuation")
    nachtrag: Optional[bool] = Field(None, description="Whether this is an addendum/supplement")

    related_vorgang_id: Optional[str] = Field(None, description="Parent Vorgang ID this position belongs to")
    dokumentnummer: Optional[str] = Field(None, description="Associated Drucksache number if applicable")

    urheber: Optional[str] = Field(None, description="Originator of this procedural step")
    fundstelle: Optional[str] = Field(None, description="Where this step is documented")

    aktualisiert: Optional[str] = Field(None, description="Last updated timestamp from API")


class Aktivitaet(BaseModel):
    """Specific parliamentary activity or action

    Aktivitäten represent discrete actions taken in the parliamentary process,
    such as committee meetings, hearings, expert testimonies, or procedural motions.
    """
    aktivitaet_name: str = Field(..., description="Activity title/description")
    aktivitaetsart: str = Field(..., description="Activity type from API classification")

    wahlperiode: Optional[int] = Field(None, description="Electoral period if applicable")
    datum: Optional[str] = Field(None, description="Activity date (ISO format)")

    related_vorgang_id: Optional[str] = Field(None, description="Related Vorgang procedure ID")
    related_drucksache_nummer: Optional[str] = Field(None, description="Related Drucksache document number")

    urheber: Optional[str] = Field(None, description="Who initiated or performed the activity")
    fundstelle: Optional[str] = Field(None, description="Where activity details can be found")

    dokumentart: Optional[str] = Field(None, description="Type of related document if applicable")
    aktualisiert: Optional[str] = Field(None, description="Last updated timestamp from API")


class Wahlperiode(BaseModel):
    """German Bundestag electoral period/legislative term

    A Wahlperiode spans from one federal election to the next (typically 4 years),
    serving as the primary temporal organizing unit for German parliamentary data.
    """
    wahlperiode_nummer: int = Field(..., description="Period number: 1 (1949), 19 (2017-2021), 20 (2021-2025), etc.")
    von: str = Field(..., description="Start date of electoral period (ISO format)")
    bis: Optional[str] = Field(None, description="End date of period (null if current/ongoing)")

    bundeskanzler: Optional[str] = Field(None, description="Federal Chancellor during this period")
    koalition: Optional[str] = Field(None, description="Governing coalition: e.g., 'SPD, GRÜNE, FDP'")

    sitze_gesamt: Optional[int] = Field(None, description="Total number of Bundestag seats (varies by period)")
    fraktionen: Optional[str] = Field(
        None,
        description="JSON array of parliamentary groups with seat counts: [{name: 'SPD', sitze: 206}, {name: 'CDU/CSU', sitze: 197}, ...]"
    )

    wahltag: Optional[str] = Field(None, description="Federal election date that initiated this period")
    besonderheiten: Optional[str] = Field(None, description="Notable characteristics: e.g., 'First East-West unified Bundestag', 'Smallest majority since...', etc.")


class BundestagPerson(BaseModel):
    """Member of the German Bundestag (MdB) - extends Politician with German-specific fields

    Represents current and former members of the Bundestag with German parliamentary
    context including Fraktion membership, committee assignments, and electoral information.
    """
    person_name: str = Field(..., description="Full name (Vorname Nachname)")
    person_id: str = Field(..., description="Unique person ID from Bundestag API")

    fraktion: Optional[str] = Field(None, description="Current parliamentary group: CDU/CSU, SPD, GRÜNE, FDP, AfD, DIE LINKE, or fraktionslos")
    partei: Optional[str] = Field(None, description="Political party affiliation (may differ from Fraktion)")

    wahlperioden: Optional[str] = Field(
        None,
        description="JSON array of Wahlperiode numbers served: [19, 20, 21]"
    )
    ausschuss_mitgliedschaften: Optional[str] = Field(
        None,
        description="JSON array of committee memberships: [{ausschuss: 'Ausschuss Digitales', rolle: 'Mitglied/Vorsitzende/Obmann', von: '2021-11-01'}]"
    )

    titel: Optional[str] = Field(None, description="Academic or professional title: Dr., Prof. Dr., etc.")
    beruf: Optional[str] = Field(None, description="Professional occupation/background")
    geburtsdatum: Optional[str] = Field(None, description="Date of birth (may be partially redacted for privacy)")
    geburtsort: Optional[str] = Field(None, description="Place of birth")

    wahlkreis: Optional[str] = Field(None, description="Directly elected constituency (Wahlkreis) if applicable")
    landesliste: Optional[str] = Field(None, description="State list position if elected via proportional representation")

    website: Optional[str] = Field(None, description="Personal or official website")
    foto_url: Optional[str] = Field(None, description="Link to official photo")

    aktualisiert: Optional[str] = Field(None, description="Last updated timestamp from API")


class BundestagFraktion(BaseModel):
    """Parliamentary group/faction in the German Bundestag

    Fraktionen are officially recognized parliamentary groups that must have
    at least 5% of seats. They organize legislative work and represent ideological blocs.
    """
    fraktion_name: str = Field(..., description="Full faction name: 'SPD', 'CDU/CSU', 'BÜNDNIS 90/DIE GRÜNEN', etc.")
    kurz: str = Field(..., description="Short name/abbreviation: 'SPD', 'CDU/CSU', 'GRÜNE', 'FDP', 'AfD', 'LINKE'")

    wahlperiode: int = Field(..., description="Electoral period this faction exists in")
    sitze: int = Field(..., description="Number of Bundestag seats held")
    prozent: Optional[float] = Field(None, description="Percentage of total Bundestag seats (0-100)")

    vorsitzende: Optional[str] = Field(
        None,
        description="JSON array of faction leaders/chairs: [{name: 'Person Name', von: '2021-11-01', bis: null}]"
    )
    parlamentarische_geschaeftsfuehrer: Optional[str] = Field(
        None,
        description="JSON array of parliamentary managers/whips"
    )

    koalition_opposition: str = Field(..., description="Status: 'Koalition' or 'Opposition'")
    koalitionspartner: Optional[str] = Field(None, description="Coalition partners if in government: ['SPD', 'GRÜNE', 'FDP']")

    gruendungsdatum: Optional[str] = Field(None, description="Formation date in this Wahlperiode")
    mitglieder_anzahl: Optional[int] = Field(None, description="Total number of MdB members")

    farbe: Optional[str] = Field(None, description="Traditional party color for visualization: '#E3000F' (SPD red), '#000000' (CDU black), etc.")


# ===================================================================
# SECTION 2: NEW GERMAN BUNDESTAG EDGE TYPE DEFINITIONS (15 Edge Types)
# ===================================================================

class PartOfVorgang(BaseModel):
    """Vorgangsposition or Aktivität is part of a Vorgang procedure"""
    relationship_type: str = Field(default="PART_OF_VORGANG", description="Type of containment relationship")
    sequence_number: Optional[int] = Field(None, description="Order in procedure if applicable")
    stage: Optional[str] = Field(None, description="Procedural stage: Einleitung, Beratung, Beschlussfassung, etc.")


class InitiatesVorgang(BaseModel):
    """Person or Fraktion initiates a legislative procedure"""
    date_initiated: Optional[str] = Field(None, description="When procedure was initiated")
    role: str = Field(..., description="Initiator role: Antragsteller, Einbringer, Urheber")
    co_initiators: Optional[str] = Field(None, description="JSON array of additional initiators")


class RelatesToDrucksache(BaseModel):
    """Vorgang or Vorgangsposition relates to a specific Drucksache"""
    relationship_type: str = Field(..., description="Type of relationship: hauptdrucksache, beratungsgrundlage, beschlussempfehlung")
    relevance: Optional[str] = Field(None, description="Importance: primary, supporting, reference")


class DebatedInPlenum(BaseModel):
    """Vorgang was debated in a plenary session"""
    debate_date: str = Field(..., description="Date of debate")
    reading: Optional[str] = Field(None, description="Which reading: Erste Beratung, Zweite Beratung, Dritte Beratung")
    tagesordnungspunkt: Optional[str] = Field(None, description="Agenda item number (TOP)")
    outcome: Optional[str] = Field(None, description="Result of debate: angenommen, abgelehnt, überwiesen, vertagt")


class SpeaksInPlenum(BaseModel):
    """Person delivers a speech in plenary session"""
    speech_date: str = Field(..., description="Date of speech")
    rede_nummer: Optional[str] = Field(None, description="Speech number in protocol")
    tagesordnungspunkt: Optional[str] = Field(None, description="Agenda item being addressed")
    rede_art: Optional[str] = Field(None, description="Speech type: Hauptrede, Zwischenruf, Persönliche Erklärung, Kurzintervention")
    dauer_minuten: Optional[int] = Field(None, description="Speech duration in minutes if available")


class InWahlperiode(BaseModel):
    """Entity exists within or is associated with an electoral period"""
    entity_type: str = Field(..., description="Type of entity linked to Wahlperiode")
    active_from: Optional[str] = Field(None, description="Start of activity in this period")
    active_until: Optional[str] = Field(None, description="End of activity in this period (null if ongoing)")


class MemberOfFraktion(BaseModel):
    """Person is a member of a parliamentary group"""
    joined_date: Optional[str] = Field(None, description="When person joined faction")
    left_date: Optional[str] = Field(None, description="When person left faction (null if current member)")
    role: Optional[str] = Field(None, description="Role in faction: Mitglied, Vorsitzende, Stellvertretende Vorsitzende, Parlamentarische Geschäftsführerin")


class LeadsFraktion(BaseModel):
    """Person leads a parliamentary group as chair/co-chair"""
    leadership_role: str = Field(..., description="Vorsitzende, Stellvertretende Vorsitzende, Fraktionsvorsitzende")
    from_date: str = Field(..., description="Start of leadership")
    to_date: Optional[str] = Field(None, description="End of leadership (null if current)")


class RepresentsWahlkreis(BaseModel):
    """Person represents an electoral constituency"""
    wahlkreis_nummer: str = Field(..., description="Constituency number")
    wahlkreis_name: str = Field(..., description="Constituency name")
    wahlperiode: int = Field(..., description="Electoral period of representation")
    elected_directly: bool = Field(..., description="True if directly elected in constituency, False if via Landesliste")
    vote_percentage: Optional[float] = Field(None, description="Percentage of votes received in constituency")


class BundesratInvolvement(BaseModel):
    """Vorgang involves Bundesrat (Federal Council) consultation or approval"""
    involvement_type: str = Field(..., description="Type: Zustimmungsbedürftig (consent required), Einspruchsgesetz (objection possible), Stellungnahme (opinion)")
    bundesrat_decision: Optional[str] = Field(None, description="Bundesrat decision: Zugestimmt, Einspruch eingelegt, Stellungnahme abgegeben")
    date: Optional[str] = Field(None, description="Date of Bundesrat action")


class BecomesBundesgesetz(BaseModel):
    """Vorgang becomes enacted federal law"""
    date_enacted: str = Field(..., description="Date of enactment")
    bundesgesetzblatt_reference: str = Field(..., description="Federal Law Gazette citation: BGBl. I S. 2097")
    date_effective: str = Field(..., description="Date law takes effect")
    verkuendung_date: Optional[str] = Field(None, description="Date of promulgation")


class AuthorsDrucksache(BaseModel):
    """Person is an author of a Drucksache document"""
    author_role: str = Field(..., description="Role: Hauptautor, Mitautor, Berichterstatter")
    author_position: Optional[int] = Field(None, description="Position in author list (1 = first author)")


class AmendsDrucksache(BaseModel):
    """One Drucksache amends another"""
    amendment_type: str = Field(..., description="Type: Änderungsantrag, Ergänzungsantrag, Alternativantrag")
    date_proposed: Optional[str] = Field(None, description="When amendment was proposed")


class ReferencesVorgang(BaseModel):
    """Drucksache or Plenarprotokoll references a Vorgang"""
    reference_type: str = Field(..., description="Type of reference: direkter_bezug, thematischer_bezug, verfahrensbezug")
    context: Optional[str] = Field(None, description="Context of the reference")


class ActivityInVorgang(BaseModel):
    """Aktivität occurs as part of a Vorgang procedure"""
    activity_sequence: Optional[int] = Field(None, description="Order of activity in procedure")
    activity_impact: Optional[str] = Field(None, description="Impact on procedure: procedural, substantive, informational")


# ===================================================================
# SECTION 3: UPDATED REGISTRY DICTIONARIES (v4.0)
# ===================================================================

# Combine v3 entities with v4 German entities
ENTITY_TYPE_REGISTRY_V4: dict[str, type[BaseModel]] = {
    # ===== V3 ENTITIES (20) =====
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

    # ===== V4 GERMAN BUNDESTAG ENTITIES (8) =====
    "Drucksache": Drucksache,
    "Plenarprotokoll": Plenarprotokoll,
    "Vorgang": Vorgang,
    "Vorgangsposition": Vorgangsposition,
    "Aktivitaet": Aktivitaet,
    "Wahlperiode": Wahlperiode,
    "BundestagPerson": BundestagPerson,
    "BundestagFraktion": BundestagFraktion,
}

# Combine v3 edges with v4 German edges
EDGE_TYPE_REGISTRY_V4: dict[str, type[BaseModel]] = {
    # ===== V3 EDGES (37) =====
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

    # ===== V4 GERMAN BUNDESTAG EDGES (15) =====
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


# ===================================================================
# SECTION 4: EXTENDED EDGE TYPE MAP (v4.0)
# ===================================================================

# Import v3 edge type map and extend with German relationships
from src.graphrag.political_schema_v3 import EDGE_TYPE_MAP as EDGE_TYPE_MAP_V3

# Create v4 edge type map by extending v3
EDGE_TYPE_MAP_V4: dict[tuple[str, str], list[str]] = {
    **EDGE_TYPE_MAP_V3,  # Include all v3 mappings

    # ===== GERMAN BUNDESTAG EDGE MAPPINGS =====

    # Vorgangsposition relationships
    ("Vorgangsposition", "Vorgang"): ["PART_OF_VORGANG"],

    # Aktivität relationships
    ("Aktivitaet", "Vorgang"): ["PART_OF_VORGANG", "ACTIVITY_IN_VORGANG"],
    ("Aktivitaet", "Drucksache"): ["REFERENCES"],

    # BundestagPerson relationships
    ("BundestagPerson", "Vorgang"): ["INITIATES_VORGANG"],
    ("BundestagPerson", "Drucksache"): ["AUTHORS_DRUCKSACHE"],
    ("BundestagPerson", "Plenarprotokoll"): ["SPEAKS_IN_PLENUM"],
    ("BundestagPerson", "BundestagFraktion"): ["MEMBER_OF_FRAKTION", "LEADS_FRAKTION"],
    ("BundestagPerson", "Wahlperiode"): ["IN_WAHLPERIODE"],
    ("BundestagPerson", "Jurisdiction"): ["REPRESENTS_WAHLKREIS"],

    # BundestagFraktion relationships
    ("BundestagFraktion", "Vorgang"): ["INITIATES_VORGANG"],
    ("BundestagFraktion", "Wahlperiode"): ["IN_WAHLPERIODE"],

    # Vorgang relationships
    ("Vorgang", "Drucksache"): ["RELATES_TO_DRUCKSACHE"],
    ("Vorgang", "Plenarprotokoll"): ["DEBATED_IN_PLENUM"],
    ("Vorgang", "Wahlperiode"): ["IN_WAHLPERIODE"],
    ("Vorgang", "LegislativeBody"): ["BUNDESRAT_INVOLVEMENT"],  # Link to Bundesrat
    ("Vorgang", "Policy"): ["BECOMES_BUNDESGESETZ", "BECOMES"],
    ("Vorgang", "LegislativeProposal"): ["BECOMES"],  # Can also become a proposal entity

    # Drucksache relationships
    ("Drucksache", "Drucksache"): ["AMENDS_DRUCKSACHE", "REFERENCES"],
    ("Drucksache", "Vorgang"): ["REFERENCES_VORGANG"],
    ("Drucksache", "Wahlperiode"): ["IN_WAHLPERIODE"],

    # Plenarprotokoll relationships
    ("Plenarprotokoll", "Vorgang"): ["REFERENCES_VORGANG"],
    ("Plenarprotokoll", "Wahlperiode"): ["IN_WAHLPERIODE"],

    # Cross-references with v3 entities
    ("BundestagPerson", "Committee"): ["AFFILIATED_WITH"],  # Committee membership
    ("BundestagPerson", "Policy"): ["HAS_POSITION", "LOBBIES_FOR", "LOBBIES_AGAINST"],
    ("BundestagFraktion", "Policy"): ["HAS_POSITION", "LOBBIES_FOR", "LOBBIES_AGAINST"],
    ("BundestagFraktion", "LegislativeProposal"): ["PROPOSES", "INFLUENCES"],
}


# ===================================================================
# SECTION 5: SCHEMA METADATA (v4.0)
# ===================================================================

SCHEMA_INFO_V4 = {
    "version": "4.0",
    "last_updated": "2025-11-12",
    "base_schema": "v3.0",
    "extensions": ["German Bundestag Parliamentary System"],
    "graphiti_compatible": True,
    "entity_count": len(ENTITY_TYPE_REGISTRY_V4),  # 28 total (20 v3 + 8 v4)
    "edge_count": len(EDGE_TYPE_REGISTRY_V4),  # 52 total (37 v3 + 15 v4)
    "pattern_count": len(EDGE_TYPE_MAP_V4),
    "description": "Extended schema with German Bundestag parliamentary entities while maintaining full EU and multi-jurisdiction support",
    "jurisdictions_supported": ["EU", "Germany", "France", "Bundesländer", "Bundestag", "Bundesrat"],
    "data_sources": [
        "EU Official Journal",
        "EU Commission DGs",
        "German Bundestag DIP API",
        "German Bundesrat",
        "National legislative bodies"
    ]
}


# ===================================================================
# SECTION 6: HELPER FUNCTIONS (v4.0)
# ===================================================================

def get_entity_types_v4() -> list[str]:
    """Get list of all entity type names in v4 schema."""
    return list(ENTITY_TYPE_REGISTRY_V4.keys())


def get_edge_types_v4() -> list[str]:
    """Get list of all edge type names in v4 schema."""
    return list(EDGE_TYPE_REGISTRY_V4.keys())


def get_valid_edges_for_entity_pair_v4(source: str, target: str) -> list[str]:
    """Get valid edge types for a source-target entity pair in v4 schema."""
    return EDGE_TYPE_MAP_V4.get((source, target), [])


def validate_edge_pattern_v4(source: str, edge: str, target: str) -> bool:
    """Check if an edge pattern is valid in the v4 schema."""
    valid_edges = EDGE_TYPE_MAP_V4.get((source, target), [])
    return edge in valid_edges


def get_schema_statistics_v4() -> dict:
    """Get v4 schema statistics and metadata."""
    return SCHEMA_INFO_V4


def get_entities_by_tier_v4() -> dict[str, list[str]]:
    """Get entities organized by tier (v3 + v4 German entities)."""
    return {
        # V3 Tiers
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
        ],
        # V4 German Bundestag Tier
        "German Bundestag": [
            "Vorgang", "Drucksache", "Plenarprotokoll", "Vorgangsposition",
            "Aktivitaet", "Wahlperiode", "BundestagPerson", "BundestagFraktion"
        ]
    }


def get_german_bundestag_entities() -> list[str]:
    """Get list of German Bundestag-specific entity types."""
    return [
        "Drucksache", "Plenarprotokoll", "Vorgang", "Vorgangsposition",
        "Aktivitaet", "Wahlperiode", "BundestagPerson", "BundestagFraktion"
    ]


def get_german_bundestag_edges() -> list[str]:
    """Get list of German Bundestag-specific edge types."""
    return [
        "PART_OF_VORGANG", "INITIATES_VORGANG", "RELATES_TO_DRUCKSACHE",
        "DEBATED_IN_PLENUM", "SPEAKS_IN_PLENUM", "IN_WAHLPERIODE",
        "MEMBER_OF_FRAKTION", "LEADS_FRAKTION", "REPRESENTS_WAHLKREIS",
        "BUNDESRAT_INVOLVEMENT", "BECOMES_BUNDESGESETZ", "AUTHORS_DRUCKSACHE",
        "AMENDS_DRUCKSACHE", "REFERENCES_VORGANG", "ACTIVITY_IN_VORGANG"
    ]


# ===================================================================
# USAGE EXAMPLES
# ===================================================================

if __name__ == "__main__":
    # Print v4 schema statistics
    print("=" * 80)
    print("POLITICAL SCHEMA V4.0 - German Bundestag Extension")
    print("=" * 80)

    stats = get_schema_statistics_v4()
    print(f"\nSchema Version: {stats['version']}")
    print(f"Base Schema: {stats['base_schema']}")
    print(f"Extensions: {', '.join(stats['extensions'])}")
    print(f"\nTotal Entities: {stats['entity_count']} (20 v3 + 8 v4 German)")
    print(f"Total Edge Types: {stats['edge_count']} (37 v3 + 15 v4 German)")
    print(f"Total Edge Patterns: {stats['pattern_count']}")

    print("\n" + "=" * 80)
    print("ENTITIES BY TIER")
    print("=" * 80)
    for tier, entities in get_entities_by_tier_v4().items():
        print(f"\n{tier} ({len(entities)} entities):")
        for entity in entities:
            print(f"  - {entity}")

    print("\n" + "=" * 80)
    print("GERMAN BUNDESTAG ENTITIES (New in v4)")
    print("=" * 80)
    for entity in get_german_bundestag_entities():
        print(f"  - {entity}")

    print("\n" + "=" * 80)
    print("GERMAN BUNDESTAG EDGES (New in v4)")
    print("=" * 80)
    for edge in get_german_bundestag_edges():
        print(f"  - {edge}")

    print("\n" + "=" * 80)
    print("EXAMPLE EDGE VALIDATIONS")
    print("=" * 80)

    # Test some German Bundestag edge patterns
    test_patterns = [
        ("BundestagPerson", "MEMBER_OF_FRAKTION", "BundestagFraktion"),
        ("Vorgang", "DEBATED_IN_PLENUM", "Plenarprotokoll"),
        ("Drucksache", "IN_WAHLPERIODE", "Wahlperiode"),
        ("BundestagPerson", "AUTHORS_DRUCKSACHE", "Drucksache"),
    ]

    for source, edge, target in test_patterns:
        is_valid = validate_edge_pattern_v4(source, edge, target)
        status = "✅ Valid" if is_valid else "❌ Invalid"
        print(f"{status}: {source} --[{edge}]--> {target}")

    print("\n" + "=" * 80)
