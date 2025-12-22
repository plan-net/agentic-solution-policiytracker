// Entity type colors matching Figma design
export const ENTITY_COLORS = {
  // Primary types from Figma
  Risk: '#EC4899',
  Event: '#EF4444',
  Associations: '#10B981',
  Company: '#14B8A6',
  Law: '#3B82F6',
  Regulator: '#EC4899',
  Official: '#10B981',

  // Extended types from Neo4j schema
  Entity: '#c99286',
  Policy: '#aad3fa',
  Regulation: '#d0bfe1',
  Document: '#5bfff7',
  Person: '#abaa86',
  Organization: '#14B8A6',

  // Government & Political
  GovernmentAgency: '#00e3cf',
  LegislativeBody: '#8fd2ff',
  LegislativeProposal: '#ffa511',
  Politician: '#97ad86',
  PoliticalParty: '#bea978',
  Committee: '#9cc992',
  Vote: '#81b1ff',
  Jurisdiction: '#8da0d4',

  // Legal & Compliance
  LegalFramework: '#6aafb3',
  ComplianceObligation: '#03ffc4',
  EnforcementAction: '#f9ae6d',
  TechnicalStandard: '#98c598',
  ConsultationProcess: '#7bbfdc',

  // Business & Industry
  Industry: '#d294bc',
  Market: '#ff96b9',
  LobbyGroup: '#9cd28d',
  BusinessActivity: '#a8afd1',
  Exception: '#c487ce',

  // German Parliament (Bundestag)
  Drucksache: '#3cc5f2',
  Sachgebiet: '#21ebbd',
  Deskriptor: '#61dbff',
  Vorgang: '#fae353',
  BundestagPerson: '#ff8d64',
  Fraktion: '#5dd759',
  BundestagFraktion: '#87fd92',
  Wahlperiode: '#1946f6',
  Plenarprotokoll: '#f7a9cb',
  Vorgangsposition: '#b3a784',
  Aktivitaet: '#a7a884',
  DrucksachePage: '#ffc4f4',

  // Other types
  ChatSession: '#7fddbf',
  Community: '#7cc2ff',
  EntityAlias: '#ffd0d3',
  CanonicalEntity: '#ff657b',
  Episodic: '#3fa5f5',

  // Fallback
  Unknown: '#888888',
}

// Status badge configurations
export const STATUS_CONFIG = {
  complete: {
    label: 'Complete',
    color: 'bg-status-complete',
    textColor: 'text-white',
  },
  working: {
    label: 'Working',
    color: 'bg-status-working',
    textColor: 'text-white',
  },
  ready: {
    label: 'Ready',
    color: 'bg-status-ready',
    textColor: 'text-white',
  },
  draft: {
    label: 'Draft',
    color: 'bg-status-draft',
    textColor: 'text-white',
  },
  error: {
    label: 'Error',
    color: 'bg-status-error',
    textColor: 'text-white',
  },
}

// Category configurations for Knowledge Graph
export const ENTITY_CATEGORIES = [
  { key: 'risk', label: 'Risk', color: '#EC4899' },
  { key: 'event', label: 'Event', color: '#EF4444' },
  { key: 'associations', label: 'Associations', color: '#10B981' },
  { key: 'company', label: 'Company', color: '#14B8A6' },
  { key: 'law', label: 'Law', color: '#3B82F6' },
  { key: 'regulator', label: 'Regulator', color: '#EC4899' },
  { key: 'official', label: 'Official', color: '#10B981' },
]

// API configuration
export const API_CONFIG = {
  BASE_URL: '',
  CHAT_ENDPOINT: '/v1/chat/completions',
  GRAPH_ENDPOINT: '/api/graph',
  REPORTS_ENDPOINT: '/api/reports',
  ASSESSMENTS_ENDPOINT: '/api/assessments',
  CHAT_SESSIONS_ENDPOINT: '/api/chat/sessions',
}

// Date format options
export const DATE_FORMATS = {
  display: 'dd MMMM yyyy',
  short: 'dd.MM.yy',
  iso: 'yyyy-MM-dd',
  week: "'KW'ww/yyyy",
}
