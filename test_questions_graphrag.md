# GraphRAG System Test Questions

## Overview
These questions test the multi-agent chat server with 15 knowledge graph tools against German Bundestag legislative data. The questions showcase different GraphRAG capabilities: entity lookup, relationship traversal, temporal analysis, aggregation, and complex multi-hop reasoning.

## Database Context
- **Entities**: 160K Aktivitäten, 44K Vorgänge, 24K Drucksachen, 1.4K BundestagPersonen
- **Relationships**: 264K TAGGED_WITH, 174K RELATED_TO_VORGANG, 160K PERFORMED_BY, 158K REFERENCES_DOCUMENT
- **Schema**: 20 entity types, 38 edge types (political_schema_v3.py)
- **Coverage**: Wahlperioden 18-21 (2013-2025), all major Fraktionen

---

## Level 1: Simple Entity Lookups
*Tests: entity_details, entity_search tools*

### Q1.1: Person Information
**Question**: "Who is Matthias Gastel and what is his political affiliation?"

**Expected Capabilities**:
- Entity search by name
- Extract person properties (current_fraktion, wahlperioden, funktion)
- Display structured information

**Success Criteria**: Returns Matthias Gastel, BÜNDNIS 90/DIE GRÜNEN, MdB status, Wahlperioden 18-21

---

### Q1.2: Legislative Procedure Lookup
**Question**: "What is Vorgang 311889 about?"

**Expected Capabilities**:
- Direct entity lookup by ID
- Parse and display complex properties (titel, abstract, deskriptoren)
- Show legislative status (beratungsstand: Verkündet)

**Success Criteria**: Returns the Cannabis/THC road traffic law, shows it was enacted (Verkündet) as BGBl I 2024, 266

---

### Q1.3: Topic Discovery
**Question**: "Find all Vorgänge related to Pflegeversicherung (nursing care insurance)"

**Expected Capabilities**:
- Semantic search across Vorgang entities
- Filter by deskriptor/topic keywords
- Rank by relevance

**Success Criteria**: Returns multiple Vorgänge including 315362, shows sachgebiet: Gesundheit

---

## Level 2: Relationship Traversal
*Tests: entity_relationships, traverse_network tools*

### Q2.1: Person Activities
**Question**: "What activities (Aktivitäten) has Franziska Brantner participated in during Wahlperiode 20?"

**Expected Capabilities**:
- Start from BundestagPerson entity
- Traverse PERFORMED_BY relationships (inverted)
- Filter by IN_WAHLPERIODE relationship
- Count and summarize activities

**Success Criteria**: Returns list of Aktivitäten, shows count, demonstrates relationship traversal

---

### Q2.2: Document-Vorgang Connections
**Question**: "Which Vorgänge are associated with Drucksache about Cannabis legislation?"

**Expected Capabilities**:
- Search for Drucksachen by keyword (Cannabis)
- Follow DOCUMENT_FOR relationships to Vorgänge
- Show both document and procedure information

**Success Criteria**: Links Drucksachen to their parent Vorgänge, shows the connection chain

---

### Q2.3: Faction Member Analysis
**Question**: "Who are the current members of the BÜNDNIS 90/DIE GRÜNEN Fraktion in the Bundestag?"

**Expected Capabilities**:
- Find Fraktion entity
- Traverse MEMBER_OF relationships (inverted)
- Filter by current status (wahlperioden includes 21)
- List persons with details

**Success Criteria**: Returns list of Green party members, shows their roles (MdB status)

---

## Level 3: Temporal Queries
*Tests: timeline_analysis, track_changes tools*

### Q3.1: Legislative Journey Tracking
**Question**: "Track the legislative journey of Vorgang 311889 from proposal to enactment (Verkündung)"

**Expected Capabilities**:
- Find Vorgang by ID
- Extract temporal data (datum, aktualisiert, verkuendung dates)
- Show progression: initiative → Beratungsstand → Verkündung
- Display timeline with dates

**Success Criteria**: Shows timeline from 2024 proposal to August 2024 enactment (BGBl I 2024, 266)

---

### Q3.2: Activity Timeline for Person
**Question**: "Show the timeline of parliamentary activities for Matthias Gastel from 2023 to 2025"

**Expected Capabilities**:
- Filter activities by person and date range
- Group activities by time period (monthly/quarterly)
- Show activity types and frequency

**Success Criteria**: Returns chronological list of activities, demonstrates temporal filtering

---

### Q3.3: Wahlperiode Comparison
**Question**: "Compare the number of Vorgänge initiated in Wahlperiode 20 versus Wahlperiode 19"

**Expected Capabilities**:
- Aggregate Vorgänge by wahlperiode property
- Count and compare across time periods
- Show breakdown by vorgangstyp if possible

**Success Criteria**: Returns counts for both Wahlperioden, shows comparison

---

## Level 4: Aggregation and Statistics
*Tests: semantic_search, find_central_entities tools*

### Q4.1: Topic Frequency Analysis
**Question**: "What are the top 10 most frequently used Deskriptoren (descriptors) in Vorgänge from Wahlperiode 20?"

**Expected Capabilities**:
- Aggregate across TAGGED_WITH relationships
- Count descriptor frequency
- Rank and return top N
- Show which topics dominate legislation

**Success Criteria**: Returns ranked list of Deskriptoren with counts, likely shows health/social topics prominent

---

### Q4.2: Initiative Source Analysis
**Question**: "Which Fraktionen or Länder have initiated the most Vorgänge in the current Wahlperiode?"

**Expected Capabilities**:
- Parse initiative property from Vorgänge
- Group by initiator (Fraktion or Land)
- Count and rank
- Handle both Fraktion and Land initiatives

**Success Criteria**: Returns ranked list showing government coalition (SPD/GRÜNE/FDP) most active

---

### Q4.3: Subject Area Distribution
**Question**: "What is the distribution of Vorgänge across different Sachgebiete (subject areas) in 2024?"

**Expected Capabilities**:
- Filter Vorgänge by year (datum property)
- Group by sachgebiet property
- Calculate percentages or counts
- Show legislative focus areas

**Success Criteria**: Returns breakdown by Sachgebiet (Gesundheit, Verkehr, etc.), shows which areas received most attention

---

## Level 5: Complex Multi-Hop Reasoning
*Tests: traverse_network, find_shortest_path, detect_communities tools*

### Q5.1: Co-Sponsorship Network
**Question**: "Which politicians frequently co-sponsor Vorgänge with members of BÜNDNIS 90/DIE GRÜNEN?"

**Expected Capabilities**:
- Find Green party members
- Traverse to their Aktivitäten/Vorgänge
- Find other persons linked to same Vorgänge
- Count co-occurrences across party lines
- Detect cross-party collaboration patterns

**Success Criteria**: Returns list of politicians from other Fraktionen who collaborate with Greens, shows coalition patterns (likely SPD, FDP)

---

### Q5.2: Policy Impact Path Analysis
**Question**: "For Vorgänge about Cannabis regulation, trace the path from proposal through documents to final enactment"

**Expected Capabilities**:
- Semantic search for Cannabis-related Vorgänge
- Follow multi-hop relationships: Vorgang → DOCUMENT_FOR → Drucksache → REFERENCES_DOCUMENT
- Show initiative → Beratungsstand changes → Verkündung
- Display full legislative pathway

**Success Criteria**: Shows complete path: Initiative (Fraktionen) → Vorgang creation → Drucksachen produced → Parliamentary debate → Final enactment (BGBl)

---

### Q5.3: Influential Person Detection
**Question**: "Who are the most central/influential politicians in Vorgänge related to Gesundheit (health) topics based on their activity connections?"

**Expected Capabilities**:
- Filter Vorgänge by sachgebiet: Gesundheit
- Find all persons linked via PERFORMED_BY relationships
- Calculate centrality metrics (degree, betweenness)
- Rank persons by influence
- Show why they're central (number of activities, key Vorgänge)

**Success Criteria**: Returns ranked list of health policy influencers, likely includes health committee members and ministry officials

---

### Q5.4: Topic Clustering and Communities
**Question**: "Identify clusters of related Vorgänge based on shared Deskriptoren and show the major policy themes"

**Expected Capabilities**:
- Use TAGGED_WITH relationships to find Vorgänge sharing descriptors
- Apply community detection algorithm
- Group Vorgänge into thematic clusters
- Name/describe each cluster based on common deskriptoren
- Show size and key Vorgänge in each cluster

**Success Criteria**: Returns 5-10 policy clusters (e.g., "Social Policy," "Economic Regulation," "Environmental Law"), shows which Vorgänge belong to each, demonstrates graph analysis capabilities

---

### Q5.5: Historical Precedent Search
**Question**: "For the recent Cannabis road traffic law (Vorgang 311889), find similar Vorgänge from earlier Wahlperioden that dealt with substance use and traffic safety"

**Expected Capabilities**:
- Extract deskriptoren from source Vorgang (Cannabis, Fahruntüchtigkeit, Straßenverkehr, Grenzwert)
- Semantic search across older Wahlperioden (18, 19)
- Find Vorgänge with similar descriptor patterns
- Compare approaches/outcomes across time
- Show legislative precedents

**Success Criteria**: Returns earlier alcohol/drug-related traffic legislation, shows how policy evolved over time, demonstrates temporal semantic search

---

## Level 6: Advanced Cross-Entity Analysis
*Tests: explore_graph, search_rerank tools*

### Q6.1: Legislative Productivity by Faction Over Time
**Question**: "Compare the legislative productivity of CDU/CSU, SPD, and BÜNDNIS 90/DIE GRÜNEN across Wahlperioden 19 and 20 - how many Vorgänge did each initiate and how many were successfully enacted?"

**Expected Capabilities**:
- Filter Vorgänge by initiative (Fraktion name)
- Group by Wahlperiode and Fraktion
- Count total initiatives vs. enacted (beratungsstand: Verkündet)
- Calculate success rates
- Compare across time and parties

**Success Criteria**: Returns comparative statistics showing SPD/GRÜNE/FDP coalition dominance in WP20, CDU/CSU opposition role, quantifies legislative success

---

### Q6.2: Cross-Reference Document Analysis
**Question**: "Find Vorgänge that reference multiple other Vorgänge (via REFERENCES_VORGANG relationships) - which legislative procedures are most interconnected?"

**Expected Capabilities**:
- Analyze REFERENCES_VORGANG relationship patterns
- Count incoming/outgoing references per Vorgang
- Identify highly connected "hub" Vorgänge
- Show reference network
- Explain why certain Vorgänge are referenced frequently

**Success Criteria**: Returns Vorgänge with many cross-references (likely framework laws, constitutional matters), shows reference network visualization or description

---

### Q6.3: Subject Area Evolution Analysis
**Question**: "How has the focus on 'Gesundheit' (health) legislation changed from Wahlperiode 19 (2017-2021) through Wahlperiode 20 (2021-2025)? Did COVID-19 pandemic influence legislative activity?"

**Expected Capabilities**:
- Filter Vorgänge by sachgebiet: Gesundheit
- Compare counts and types across Wahlperioden
- Analyze temporal patterns within WP20 (2020-2021 pandemic period)
- Look at deskriptoren to identify pandemic-related topics
- Show trends over time

**Success Criteria**: Shows spike in health legislation during pandemic period, identifies COVID-related deskriptoren (Infektionsschutz, Impfung, etc.), demonstrates temporal trend analysis

---

## Testing Strategy

### Progression Path
1. **Start with Level 1-2**: Validate basic entity lookup and relationship traversal work
2. **Move to Level 3-4**: Test temporal and aggregation capabilities
3. **Challenge with Level 5-6**: Demonstrate advanced graph algorithms and multi-hop reasoning

### Expected Tool Usage

| Question Level | Primary Tools | Secondary Tools |
|---|---|---|
| Level 1 | entity_details, entity_search | semantic_search |
| Level 2 | entity_relationships, traverse_network | entity_search |
| Level 3 | timeline_analysis, track_changes | entity_details |
| Level 4 | semantic_search, find_central_entities | explore_graph |
| Level 5 | traverse_network, find_shortest_path, detect_communities | search_rerank |
| Level 6 | explore_graph, detect_communities, compare_timeframes | All tools combined |

### Success Metrics
- **Response Quality**: Accurate, relevant answers with proper context
- **Tool Selection**: Appropriate tools chosen by planning agent
- **Reasoning Transparency**: Clear thinking stream showing query understanding → tool planning → execution → synthesis
- **Data Accuracy**: Correct entity/relationship data from Neo4j
- **Performance**: Responses within 10-30 seconds depending on complexity
- **Error Handling**: Graceful handling of missing data or ambiguous queries

### Additional Test Questions (Bonus)

**Cross-Party Consensus**: "Find Vorgänge initiated jointly by multiple Fraktionen from different political camps (e.g., CDU/CSU + GRÜNE) - what topics achieve cross-party support?"

**Ministerial Activity**: "Which persons with 'Parl. Staatssekr.' or ministerial roles (check person_roles_history) are most active in Vorgänge related to their portfolio?"

**Document Page Analysis**: "For Drucksachen with multiple pages (HAS_PAGE relationships), analyze which types of documents are longest and most detailed"

**Successor Tracking**: "Use SUCCESSOR_OF relationships to find political succession chains - who replaced whom in the Bundestag?"

---

## Implementation Notes

### Data Quality Considerations
- Some BundestagPerson entities may have NULL names (1468 persons, some may be incomplete)
- Deskriptor parsing requires JSON handling (deskriptor_json property)
- Initiative property contains arrays (multiple initiators possible)
- Wahlperioden stored as array property (persons can serve multiple terms)

### Query Optimization Tips
- Use person_id, vorgang_id for direct lookups
- Leverage indexed properties: wahlperiode, sachgebiet, current_fraktion
- Limit result sets for large traversals (e.g., top 10, top 20)
- Cache frequently accessed entities (popular persons, current Wahlperiode)

### Expected Challenges
1. **Ambiguous person names**: Some names may match multiple entities
2. **Date parsing**: Multiple date fields (datum, aktualisiert, basisdatum) serve different purposes
3. **German text processing**: Queries may be in English but data is German
4. **Complex relationships**: Some relationships may require 3+ hops to find meaningful connections
5. **Missing data**: Not all Vorgänge have Verkündung (many still in process)

---

**Document Version**: 1.0
**Created**: 2025-01-18
**Database**: politicamonitoring.v2
**Schema**: political_schema_v3.py
