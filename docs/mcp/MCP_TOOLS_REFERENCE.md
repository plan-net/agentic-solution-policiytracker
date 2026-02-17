# MCP Tools Reference Documentation

**Version:** 2.0
**Last Updated:** February 2026
**Total Tools:** 31 tools across 4 MCP servers

---

## Overview

The PolicyTracker system uses four MCP (Model Context Protocol) servers to provide comprehensive access to regulatory and parliamentary data:

| MCP Server | Port | Description | Tools |
|------------|------|-------------|-------|
| **Graph Retrieval** | 8003 | Knowledge graph search and analysis | 19 tools |
| **Bundestag DIP** | 8004 | German parliamentary data | 8 tools |
| **Web Search** | 8005 | Internet and news search | 4 tools |
| **Neo4j CRUD** | 8006 | Database CRUD operations | REST API |

---

## 1. Graph Retrieval MCP Server (Port 8003)

**URL:** `http://localhost:8003/sse`
**Purpose:** Access to the curated knowledge graph containing EU regulations, policies, politicians, and organizations.

### Base Tools (6 tools)

#### 1. `search_knowledge_graph`
Search for entities, facts, and relationships in the knowledge graph.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Search query (use German terms for best results) |
| `max_results` | integer | No | Maximum results (default: 10) |

**Use cases:**
- "What regulations affect digital services?"
- "Find information about KI-Verordnung"
- "Search for GDPR enforcement actions"

**Sample queries:**
```
"KI-Verordnung Compliance" (German - preferred)
"DSGVO Durchsetzung"
"NIS2-Richtlinie Umsetzung"
```

---

#### 2. `search_documents`
Search for specific documents and their content.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Document search query |
| `max_results` | integer | No | Maximum results (default: 10) |

**Use cases:**
- Looking for source documents, reports, or official texts
- Questions about specific document content

---

#### 3. `analyze_query`
Analyze and decompose complex queries before searching.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Complex query to analyze |

**Use cases:**
- Understanding multi-part questions before searching
- Planning research approach for complex topics

---

#### 4. `get_entity_info`
Get detailed information about a specific entity.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `entity_name` | string | Yes | Name of the entity |

**Use cases:**
- "Tell me about GDPR"
- "What is the European Commission?"
- Getting comprehensive entity properties and relationships

---

#### 5. `find_relationships`
Find connections between entities.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `source_entity` | string | Yes | First entity |
| `target_entity` | string | No | Second entity (optional) |
| `relationship_types` | array | No | Filter by relationship types |

**Use cases:**
- "How does X relate to Y?"
- Exploring entity connections

---

#### 6. `graph_statistics`
Get statistics about the knowledge graph.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| None | - | - | No parameters required |

**Use cases:**
- Understanding data coverage and scope
- Meta-questions about the knowledge base

---

### Temporal Tools (5 tools)

#### 7. `search_by_date_range`
Search within specific date ranges.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Search query |
| `start_date` | string | Yes | Start date (YYYY-MM-DD) |
| `end_date` | string | Yes | End date (YYYY-MM-DD) |
| `max_results` | integer | No | Maximum results (default: 20) |

**Use cases:**
- "What happened between January and March 2024?"
- Finding events in a specific time window

---

#### 8. `get_entity_history`
Track entity evolution over time.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `entity_name` | string | Yes | Name of the entity |
| `days_back` | integer | No | Period in days (default: 365) |
| `event_types` | array | No | Filter by event types |

**Use cases:**
- "How has GDPR changed over the past year?"
- Understanding policy evolution

---

#### 9. `find_concurrent_events`
Find events around a reference date.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `reference_date` | string | Yes | Reference date (YYYY-MM-DD) |
| `window_days` | integer | No | Days before/after (default: 30) |
| `event_context` | string | No | Optional context filter |

**Use cases:**
- "What else happened around January 15, 2024?"
- Contextualizing specific events

---

#### 10. `compare_timelines`
Compare multiple entity timelines.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `entities` | array | Yes | List of 2-5 entity names |
| `time_period` | integer | No | Period in days |
| `comparison_focus` | string | No | Focus area for comparison |

**Use cases:**
- "Compare GDPR and AI Act development"
- Finding parallel developments

---

#### 11. `track_policy_evolution`
Track policy lifecycle phases.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `policy_name` | string | Yes | Name of the policy |
| `evolution_period` | integer | No | Period in days (default: 730) |
| `evolution_aspects` | array | No | Aspects to track |

**Use cases:**
- "How has the AI Act evolved since 2023?"
- Tracking: proposal → amendment → implementation → enforcement

---

### Community Detection Tools (3 tools)

#### 12. `get_communities`
Discover entity communities/clusters in the knowledge graph.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `topic_focus` | string | No | Topic to focus search on |
| `max_communities` | integer | No | Maximum communities (default: 5) |
| `min_community_size` | integer | No | Minimum entities per community (default: 3) |

**Use cases:**
- "What are the main clusters of EU regulations?"
- "Find communities of related policy areas"
- Understanding the regulatory landscape

**Sample queries:**
```
"Find communities related to data protection"
"What clusters of AI regulations exist?"
"Discover groups of digital policy entities"
```

---

#### 13. `get_community_members`
Get members of a specific community.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `community_topic` | string | Yes | Topic that defines the community |
| `max_members` | integer | No | Maximum members (default: 10) |
| `member_types` | array | No | Entity types to focus on |

**Use cases:**
- "Who belongs to the AI regulation community?"
- "Show entities in the data privacy cluster"

**Sample queries:**
```
"Get members of the cybersecurity policy community"
"Who's in the digital services regulation group?"
```

---

#### 14. `get_policy_clusters`
Cluster policies by theme, jurisdiction, or time period.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `policy_area` | string | No | Policy area to focus on |
| `cluster_method` | string | No | Method: 'thematic', 'jurisdictional', 'temporal' |
| `max_clusters` | integer | No | Maximum clusters (default: 5) |

**Use cases:**
- "Group EU regulations by theme"
- "Find policy clusters by jurisdiction"
- "Organize financial regulations by time period"

**Sample queries:**
```
"Cluster digital policies by topic"
"Group regulations by EU/national jurisdiction"
```

---

### Graph Traversal Tools (4 tools)

#### 15. `traverse_from_entity`
Multi-hop traversal with relevance filtering.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `entity_name` | string | Yes | Starting entity |
| `max_depth` | integer | No | Maximum hops (default: 2, recommended: 1-3) |
| `max_results` | integer | No | Maximum results (default: 15) |

**Use cases:**
- "What entities are connected to GDPR within 2 hops?"
- "Explore the regulatory network around the AI Act"

**Sample queries:**
```
"Traverse from KI-Verordnung to depth 2"
"Explore connections from European Commission"
"What's connected to NIS2-Richtlinie within 3 hops?"
```

---

#### 16. `find_paths_between_entities`
Find connection paths between two entities using Neo4j shortest path algorithms.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `source_entity` | string | Yes | Starting entity |
| `target_entity` | string | Yes | Destination entity |
| `max_path_length` | integer | No | Maximum path length (default: 4) |
| `max_paths` | integer | No | Maximum paths to return (default: 5) |

**Use cases:**
- "How is the AI Act connected to GDPR?"
- "Find the path between European Commission and DSA"

**Sample queries:**
```
"Find paths between DSGVO and KI-Verordnung"
"How is the Bundestag connected to NIS2?"
"Show connection between European Parliament and Digital Services Act"
```

---

#### 17. `get_entity_neighbors`
Get directly connected entities (bidirectional).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `entity_name` | string | Yes | Entity to find neighbors for |
| `max_depth` | integer | No | Depth of neighbors (default: 1, recommended: 1-2) |

**Use cases:**
- "What entities are directly related to the European Parliament?"
- "Find immediate connections to NIS2 Directive"

**Sample queries:**
```
"Get neighbors of GDPR"
"What's directly connected to the European Commission?"
"Find immediate connections to KI-Verordnung"
```

---

#### 18. `analyze_entity_impact`
Analyze what entities are impacted by or impact the given entity.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `entity_name` | string | Yes | Entity to analyze |
| `impact_types` | array | No | Types of impact to focus on |
| `max_hops` | integer | No | Maximum hops to explore (default: 3) |

**Use cases:**
- "What is the impact network of GDPR?"
- "What entities are affected by the AI Act?"
- Mapping regulatory influence patterns

**Sample queries:**
```
"Analyze impact of DSGVO"
"What does the Digital Services Act affect?"
"Show impact network of NIS2-Richtlinie"
```

---

### Similarity Tool (1 tool)

#### 19. `find_similar_entities`
Find entities similar to a given entity based on graph structure and context.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `entity_name` | string | Yes | Entity to find similar entities for |
| `max_similar` | integer | No | Maximum similar entities (default: 5) |

**Use cases:**
- "Find regulations similar to GDPR"
- "What entities are structurally similar to the European Commission?"

**Sample queries:**
```
"Find regulations similar to KI-Verordnung"
"What's like GDPR in the knowledge graph?"
"Find entities similar to NIS2"
```

---

## 2. Bundestag DIP MCP Server (Port 8004)

**URL:** `http://localhost:8004/sse`
**Purpose:** Real-time access to German parliamentary data via the Bundestag DIP API.

### Tools (8 tools)

#### 1. `search_bundestag_legislation`
Search for legislative procedures (Vorgänge).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Search query |
| `wahlperiode` | integer | No | Electoral period (default: 20) |
| `vorgangstyp` | string | No | Procedure type |
| `limit` | integer | No | Maximum results (default: 10) |

**Procedure types:** `Gesetzgebung`, `Antrag`, `Kleine Anfrage`, `Große Anfrage`, `Entschließungsantrag`

**Sample queries:**
```
"Klimaschutz"
"Digitalisierung"
"Künstliche Intelligenz"
```

---

#### 2. `get_bundestag_vorgang`
Get details of a specific legislative procedure.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `vorgang_id` | string | Yes | Vorgang ID (e.g., '287654') |

---

#### 3. `search_bundestag_documents`
Search for parliamentary documents (Drucksachen).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Search query |
| `dokumentart` | string | No | Document type |
| `wahlperiode` | integer | No | Electoral period |
| `limit` | integer | No | Maximum results |

**Document types:** `Gesetzentwurf`, `Beschlussempfehlung`, `Bericht`

---

#### 4. `get_bundestag_drucksache`
Get details of a specific document.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `drucksache_nummer` | string | Yes | Document number (e.g., '20/1234') |

---

#### 5. `search_bundestag_persons`
Search for Bundestag members.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | No | Person name |
| `fraktion` | string | No | Parliamentary group |
| `wahlperiode` | integer | No | Electoral period |
| `limit` | integer | No | Maximum results |

**Parliamentary groups:** `SPD`, `CDU/CSU`, `BÜNDNIS 90/DIE GRÜNEN`, `FDP`, `AfD`, `DIE LINKE`

---

#### 6. `get_bundestag_person`
Get details of a specific MP.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `person_id` | string | Yes | Person ID from DIP |

---

#### 7. `search_bundestag_activities`
Search for parliamentary activities.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | No | Search query |
| `aktivitaetsart` | string | No | Activity type (e.g., 'Rede', 'Abstimmung') |
| `date_from` | string | No | Start date (YYYY-MM-DD) |
| `date_to` | string | No | End date (YYYY-MM-DD) |
| `limit` | integer | No | Maximum results |

---

#### 8. `get_bundestag_plenarprotokoll`
Get plenary protocol (transcript).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sitzungsnummer` | string | No | Session number (e.g., '20/123') |
| `date` | string | No | Session date (YYYY-MM-DD) |

---

## 3. Web Search MCP Server (Port 8005)

**URL:** `http://localhost:8005/sse`
**Purpose:** Internet search and news retrieval via Exa.ai and DPA news.

### Tools (4 tools)

#### 1. `web_search`
General web search via Exa.ai.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Search query |
| `num_results` | integer | No | Results to return (default: 10, max: 50) |
| `include_domains` | array | No | Only include these domains |
| `exclude_domains` | array | No | Exclude these domains |

---

#### 2. `search_news`
News-specific search with date filtering.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | News search query |
| `num_results` | integer | No | Results to return (default: 10) |
| `days_back` | integer | No | Days to search back (default: 7) |
| `include_domains` | array | No | Specific news sources |

---

#### 3. `search_dpa_news`
German Press Agency (DPA) news search.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Search query (German or English) |
| `max_items` | integer | No | Maximum articles (default: 10) |
| `days_back` | integer | No | Days to search back (default: 7) |

**Best for:** German-language news, official press releases

---

#### 4. `get_article_content`
Fetch full article content from URLs.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `urls` | array | Yes | List of URLs (max 10) |

---

## 4. Neo4j CRUD MCP Server (Port 8006)

**URL:** `http://localhost:8006`
**Purpose:** Database CRUD operations (REST API, not MCP tools).

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/create_node` | POST | Create a new node |
| `/update_node` | POST | Update node properties |
| `/delete_node` | POST | Delete a node |
| `/create_relationship` | POST | Create relationship |
| `/update_relationship` | POST | Update relationship |
| `/query_nodes` | POST | Query nodes |

---

## Quick Reference: Tool Selection by Query Type

| Query Type | Primary Tool | Fallback Tool |
|------------|--------------|---------------|
| "What is X?" | `get_entity_info` | `search_knowledge_graph` |
| "How does X relate to Y?" | `find_relationships` | `search_knowledge_graph` |
| "Find all X" / "List X" | `search_knowledge_graph` | `find_relationships` |
| "What happened between dates?" | `search_by_date_range` | `search_knowledge_graph` |
| "How has X evolved?" | `get_entity_history` | `track_policy_evolution` |
| "Find entity clusters/groups" | `get_communities` | `get_policy_clusters` |
| "Who's in this community?" | `get_community_members` | `get_entity_neighbors` |
| "Group policies by theme" | `get_policy_clusters` | `get_communities` |
| "What's connected within N hops?" | `traverse_from_entity` | `get_entity_neighbors` |
| "How is A connected to B?" | `find_paths_between_entities` | `find_relationships` |
| "What's directly connected?" | `get_entity_neighbors` | `find_relationships` |
| "What does X impact?" | `analyze_entity_impact` | `traverse_from_entity` |
| "Find similar entities" | `find_similar_entities` | `search_knowledge_graph` |
| "Current Bundestag status" | `search_bundestag_legislation` | `search_bundestag_documents` |
| "Recent news about X" | `search_news` | `search_dpa_news` |

---

## Language Guidelines

| Tool Category | Language Recommendation |
|---------------|------------------------|
| Knowledge Graph tools | **German PRIMARY**, English fallback |
| Bundestag DIP tools | **German strongly recommended** |
| Web Search tools | German or English OK |
| DPA News | German or English OK |

### German Translation Reference

| English Term | German Search Term |
|--------------|-------------------|
| AI Act / EU AI Act | **KI-Verordnung**, KI-VO |
| GDPR | **DSGVO**, Datenschutz-Grundverordnung |
| NIS2 Directive | **NIS2-Richtlinie** |
| Digital Services Act | **DSA**, Gesetz über digitale Dienste |
| Digital Markets Act | **DMA**, Gesetz über digitale Märkte |
| Data Protection | **Datenschutz** |
| Cybersecurity | **Cybersicherheit**, IT-Sicherheit |
| Consumer Protection | **Verbraucherschutz** |

---

## Sample Multi-Tool Workflows

### 1. Comprehensive Regulation Analysis
```
1. search_knowledge_graph("KI-Verordnung") - Get overview
2. get_communities(topic_focus="AI regulation") - Find related clusters
3. traverse_from_entity("KI-Verordnung", max_depth=2) - Explore connections
4. analyze_entity_impact("KI-Verordnung") - Understand impact
5. search_bundestag_legislation("Künstliche Intelligenz") - Check current status
6. search_news("EU AI Act") - Get latest news
```

### 2. Entity Connection Discovery
```
1. get_entity_neighbors("GDPR") - Find direct connections
2. find_paths_between_entities("GDPR", "AI Act") - Find paths
3. get_community_members("data protection") - Find related entities
4. find_similar_entities("GDPR") - Find similar regulations
```

### 3. Policy Evolution Tracking
```
1. get_entity_history("KI-Verordnung", days_back=730) - Track changes
2. track_policy_evolution("KI-Verordnung") - Track lifecycle phases
3. compare_timelines(["KI-Verordnung", "DSGVO"]) - Compare developments
4. find_concurrent_events("2024-03-13") - Context around key dates
```

---

*Generated: February 2026 | Total: 31 tools across 4 MCP servers*
