# GraphRAG Test Questions - politicalmonitoring Database

## Overview
These questions test the multi-agent chat server with 15 knowledge graph tools against the `politicalmonitoring` database containing Graphiti-formatted political monitoring data. The questions showcase different GraphRAG capabilities: entity lookup, relationship traversal, temporal analysis, and complex reasoning.

## Database Context
- **Entities**: 3,026 Entities (1,051 Companies, 349 Persons, 141 Documents, 134 Industries, 97 Jurisdictions, 70 Gov Agencies, 66 Legislative Proposals, 66 Lobby Groups, 49 Regulations, 47 Politicians, 24 Technical Standards, 21 Policies, 21 Legal Frameworks, 16 Legislative Bodies)
- **Episodic Data**: 1,747 Episodic nodes (documents with timestamps)
- **Relationships**: AFFECTS, INFLUENCES, COMMENTS_ON, TRIGGERS, HAS_POSITION, ANNOUNCED_SUPPORT_FOR
- **Schema**: Graphiti-compatible (Entity, Episodic, Community labels) + Political schema overlays
- **Coverage**: EU regulations (DSA, DMA, AI Act, GDPR), major tech companies, politicians, policies

---

## Level 1: Simple Entity Lookups
*Tests: entity_details, entity_search, search tools*

### Q1.1: Company Information
**Question**: "What do we know about Meta Platforms and their regulatory challenges?"

**Expected Capabilities**:
- Entity search by name (Meta Platforms)
- Extract entity properties and summary
- Find related regulations and policies
- Display structured company information

**Success Criteria**: Returns Meta, shows DSA/privacy-related issues, regulatory relationships

---

### Q1.2: Regulation Lookup
**Question**: "What is the AI Act and what are its key provisions?"

**Expected Capabilities**:
- Direct entity search for "AI Act"
- Extract regulation details from Entity properties
- Parse and display key requirements
- Show related legislative proposals

**Success Criteria**: Returns AI Act regulation, shows risk-based approach, compliance requirements

---

### Q1.3: Policy Discovery
**Question**: "Find all policies related to Digital Services Act (DSA)"

**Expected Capabilities**:
- Semantic search across Policy entities
- Filter by DSA keyword/relationship
- Rank by relevance
- Show policy details and connections

**Success Criteria**: Returns DSA and related policies, shows EU digital regulation context

---

## Level 2: Relationship Traversal
*Tests: entity_relationships, traverse_network tools*

### Q2.1: Company-Regulation Relationships
**Question**: "Which regulations AFFECT Google and what are the compliance implications?"

**Expected Capabilities**:
- Start from Google Entity
- Traverse AFFECTS relationships to Regulation entities
- Show relationship properties (fact, valid_at)
- Summarize regulatory landscape

**Success Criteria**: Returns DMA, DSA, AI Act connections, shows Google's regulatory exposure

---

### Q2.2: Politician-Policy Connections
**Question**: "What policies or regulations has Donald J. Trump COMMENTED_ON or INFLUENCED?"

**Expected Capabilities**:
- Search for Politician entity
- Follow COMMENTS_ON and INFLUENCES relationships
- Show temporal aspect (when comments made)
- Display policy/regulation targets

**Success Criteria**: Returns Trump's regulatory positions, shows influence relationships

---

### Q2.3: Industry Impact Analysis
**Question**: "How does the Digital Markets Act affect the crypto industry?"

**Expected Capabilities**:
- Find Digital Markets Act Entity
- Traverse to Industry entities via AFFECTS relationships
- Find crypto industry connections
- Show impact pathways

**Success Criteria**: Links DMA to crypto regulations, shows industry impact chain

---

## Level 3: Temporal Queries
*Tests: timeline_analysis, search_by_date_range, find_concurrent_events tools*

### Q3.1: Regulation Timeline
**Question**: "Track the timeline of the Cyber Resilience Act from proposal to current status"

**Expected Capabilities**:
- Find Cyber Resilience Act entity
- Extract temporal data (created_at, valid_at)
- Find related Episodic nodes with timestamps
- Show progression over time

**Success Criteria**: Returns CRA timeline, shows legislative journey with dates

---

### Q3.2: Recent Policy Developments
**Question**: "What policy developments related to Microsoft occurred in 2025?"

**Expected Capabilities**:
- Filter by date range (2025)
- Search Episodic nodes mentioning Microsoft
- Extract policy-related events
- Show chronological list

**Success Criteria**: Returns 2025 Microsoft policy events, shows recent regulatory activity

---

### Q3.3: Concurrent Regulatory Events
**Question**: "What major EU regulations were being discussed or enacted around October 2024?"

**Expected Capabilities**:
- Time-based search (October 2024)
- Find concurrent Episodic nodes
- Identify regulation-related events
- Group by policy area

**Success Criteria**: Shows multiple EU regulations active in Oct 2024 timeframe

---

## Level 4: Semantic Search & Discovery
*Tests: semantic_search, search_rerank, explore_graph tools*

### Q4.1: Thematic Policy Search
**Question**: "What policies and regulations address data privacy and digital rights in the EU?"

**Expected Capabilities**:
- Semantic search across Policy and Regulation entities
- Find conceptually related items (GDPR, DSA, Data Act)
- Rank by relevance to data privacy theme
- Show connections between regulations

**Success Criteria**: Returns GDPR, DSA, Data Act, ePrivacy; shows how they interrelate

---

### Q4.2: Company Compliance Landscape
**Question**: "Which tech companies are most impacted by EU digital regulations?"

**Expected Capabilities**:
- Aggregate AFFECTS relationships from regulations to companies
- Count regulation connections per company
- Rank companies by regulatory exposure
- Show key compliance areas

**Success Criteria**: Returns Google, Meta, Microsoft, TikTok; shows they face multiple regulations

---

### Q4.3: Stakeholder Identification
**Question**: "Who are the key Government Agencies and Lobby Groups involved in AI regulation?"

**Expected Capabilities**:
- Search for entities connected to AI Act
- Filter by entity types (GovernmentAgency, LobbyGroup)
- Find COMMENTS_ON or INFLUENCES relationships
- Show stakeholder landscape

**Success Criteria**: Returns agencies/groups involved in AI Act, shows advocacy positions

---

## Level 5: Complex Multi-Hop Reasoning
*Tests: find_paths_between_entities, traverse_from_entity, analyze_entity_impact tools*

### Q5.1: Company-to-Politician Influence Path
**Question**: "Trace the connection between Meta Platforms and politicians who have commented on social media regulation"

**Expected Capabilities**:
- Start from Meta entity
- Find paths to Politician entities
- Traverse through Policy/Regulation intermediates
- Show influence chains (e.g., Meta → DSA → Politician comments)

**Success Criteria**: Returns multi-hop paths showing Meta → regulation → politician connections

---

### Q5.2: Cross-Regulation Impact Analysis
**Question**: "How do the Digital Services Act and Digital Markets Act work together to regulate large tech platforms?"

**Expected Capabilities**:
- Find both DSA and DMA entities
- Analyze overlapping AFFECTS relationships (common companies)
- Compare compliance requirements
- Show complementary regulatory approach

**Success Criteria**: Shows both acts target same platforms (Google, Meta) but with different angles

---

### Q5.3: Policy Evolution Tracking
**Question**: "How has EU data protection policy evolved from GDPR through DSA to the Data Act?"

**Expected Capabilities**:
- Find all three regulations (GDPR, DSA, Data Act)
- Order by temporal sequence (created_at, valid_at)
- Analyze how later policies build on earlier ones
- Show evolution of data rights

**Success Criteria**: Returns chronological evolution, shows GDPR → DSA → Data Act progression

---

### Q5.4: Industry-Wide Regulatory Impact
**Question**: "For the financial services industry, what is the combined impact of MiFID II and Payment Service Regulation?"

**Expected Capabilities**:
- Find both regulations
- Identify affected financial entities (banks, fintechs)
- Analyze cumulative compliance burden
- Show how regulations intersect

**Success Criteria**: Returns both regulations, shows overlapping requirements for financial firms

---

### Q5.5: Regulatory Precedent Analysis
**Question**: "Which earlier regulations influenced the design of the AI Act, and how?"

**Expected Capabilities**:
- Find AI Act entity
- Search for related/predecessor regulations
- Analyze common patterns (risk-based approach)
- Show regulatory lineage

**Success Criteria**: Links AI Act to prior regulations (DSA, product safety), shows borrowed concepts

---

## Level 6: Advanced Knowledge Graph Analysis
*Tests: get_communities, get_policy_clusters, find_central_entities tools*

### Q6.1: Regulatory Ecosystem Mapping
**Question**: "Identify the clusters of interconnected regulations in the EU digital policy space and show how they relate"

**Expected Capabilities**:
- Apply community detection to Regulation entities
- Find densely connected regulatory clusters
- Name clusters by policy theme (e.g., "Digital Services," "Data Protection," "AI Governance")
- Show cross-cluster bridges

**Success Criteria**: Returns 3-5 regulatory clusters (digital services, data protection, competition, AI), shows overlaps

---

### Q6.2: Most Central Tech Company
**Question**: "Which tech company is most central to EU regulatory discussions based on the number of regulations affecting them?"

**Expected Capabilities**:
- Calculate degree centrality for Company entities
- Count incoming AFFECTS relationships from regulations
- Rank companies by regulatory exposure
- Explain why they're central (market power, data practices)

**Success Criteria**: Returns Google or Meta as most central, shows they're targeted by 5+ regulations

---

### Q6.3: Lobbying Influence Network
**Question**: "Map the lobbying network around the Digital Markets Act - which companies and lobby groups are trying to influence it?"

**Expected Capabilities**:
- Start from DMA entity
- Find all INFLUENCES relationships
- Identify Company and LobbyGroup entities
- Show advocacy positions (for/against provisions)

**Success Criteria**: Returns tech companies + lobby groups, shows competing interests

---

### Q6.4: Legislative Body Activity
**Question**: "Which legislative bodies (European Parliament, Council, Commission) are most active in proposing digital regulations?"

**Expected Capabilities**:
- Find LegislativeBody entities
- Count associated LegislativeProposal entities
- Analyze proposal success rate (became Policy/Regulation)
- Compare legislative productivity

**Success Criteria**: Returns EU bodies, shows European Commission is most active proposer

---

### Q6.5: Temporal Regulatory Waves
**Question**: "Identify waves or clusters of regulatory activity - when did EU significantly ramp up digital regulation?"

**Expected Capabilities**:
- Group regulations by created_at dates
- Identify temporal clusters (e.g., 2020-2023 surge)
- Analyze triggers for regulatory waves
- Show correlation with events (scandals, market changes)

**Success Criteria**: Shows 2020-2023 wave (DSA, DMA, AI Act, Data Act), links to post-Cambridge Analytica era

---

## Level 7: Document-Grounded Analysis
*Tests: Episodic search, episode-focused queries*

### Q7.1: Source Document Retrieval
**Question**: "Find the original documents or news articles that discuss Meta's response to the Digital Services Act"

**Expected Capabilities**:
- Search Episodic nodes for "Meta" + "DSA"
- Extract episode content and source information
- Show document titles, dates, sources
- Provide citations

**Success Criteria**: Returns actual documents (e.g., from noyb.eu, pymnts.com), shows Meta's DSA compliance actions

---

### Q7.2: Regulatory Commentary Analysis
**Question**: "What have politicians and policy experts said about the AI Act according to the documents?"

**Expected Capabilities**:
- Search Episodic content for AI Act mentions
- Filter for politician names or quotes
- Extract key statements and positions
- Show who said what, when

**Success Criteria**: Returns specific statements from politicians about AI Act, with sources

---

### Q7.3: Document Timeline Correlation
**Question**: "Show how media coverage of TikTok evolved alongside regulatory proposals against it"

**Expected Capabilities**:
- Find Episodic nodes mentioning TikTok
- Order by timestamp (created_at, valid_at)
- Correlate with LegislativeProposal entities
- Show media narrative arc

**Success Criteria**: Returns chronological TikTok coverage, shows timing relative to ban proposals

---

## Testing Strategy

### Progression Path
1. **Start with Level 1-2**: Validate basic search and relationship traversal
2. **Test Level 3-4**: Verify temporal and semantic search capabilities
3. **Challenge with Level 5-6**: Advanced graph algorithms and multi-hop reasoning
4. **Verify Level 7**: Document grounding and source citations

### Expected Tool Usage

| Question Level | Primary Tools | Secondary Tools |
|---|---|---|
| Level 1 | search, entity_details, entity_search | get_entity_relationships |
| Level 2 | get_entity_relationships, traverse_from_entity | search |
| Level 3 | search_by_date_range, get_entity_timeline, find_concurrent_events | search |
| Level 4 | search (semantic), explore_graph | find_similar_entities |
| Level 5 | find_paths_between_entities, analyze_entity_impact | traverse_from_entity |
| Level 6 | get_communities, get_policy_clusters | find_central_entities |
| Level 7 | search (episode_focused) | get_entity_details |

### Success Metrics
- **Response Quality**: Accurate, relevant answers with proper context
- **Tool Selection**: Appropriate tools chosen by planning agent
- **Reasoning Transparency**: Clear thinking stream showing query → plan → execution → synthesis
- **Data Accuracy**: Correct entity/relationship data from politicalmonitoring database
- **Performance**: Responses within 10-30 seconds depending on complexity
- **Source Citations**: Episodic sources properly cited when available

### Sample Entities for Quick Testing

**Companies**: Meta Platforms, Google, Microsoft, TikTok, Twitter, Salesforce
**Regulations**: AI Act, DSA, Digital Markets Act, Cyber Resilience Act, Data Act, GDPR
**Policies**: Digital Services Act, MiFID II, NIS2 Implementation Act
**Politicians**: Donald J. Trump, Friedrich Merz, Keir Starmer
**Legislative Proposals**: Digital Services Act, Markets in Crypto-Assets Regulation
**Industries**: crypto industry, American tech companies, financial services

---

## Implementation Notes

### Data Quality Considerations
- Entity names may vary (e.g., "DSA" vs "Digital Services Act") - use semantic search
- Some entities have dual labels (e.g., `:Entity:Policy` or `:Entity:Company`)
- Episodic nodes contain timestamped document chunks (name format: `political_doc_YYYYMMDD_source_title_timestamp_chunk_N`)
- Relationships are all type `:RELATES_TO` with `name` property for semantic type (AFFECTS, INFLUENCES, etc.)

### Query Optimization Tips
- Use entity labels for filtering: `(n:Entity:Company)` vs `(n:Entity:Regulation)`
- Leverage fulltext indices: `node_name_and_summary`, `edge_name_and_fact`, `episode_content`
- For temporal queries, use Episodic nodes (have timestamps) rather than Entity nodes
- Semantic search benefits from Graphiti's cross-encoder reranking

### Expected Challenges
1. **Entity name variations**: Same entity might have multiple names (semantic search helps)
2. **Relationship inference**: Some connections may require 2-3 hop traversal
3. **Temporal precision**: Episodic timestamps are creation time, not event time
4. **Missing data**: Not all regulations have complete stakeholder mapping
5. **German language**: Some entities have German names (Gesetz zur Verbesserung...)

---

## Comparison with politicamonitoring.v2 Questions

| Aspect | politicamonitoring.v2 (Bundestag) | politicalmonitoring (EU/Global) |
|--------|----------------------------------|-------------------------------|
| **Geography** | Germany only | EU + global |
| **Entities** | Bundestag-specific (Vorgang, Drucksache) | Generic political (Company, Policy, Regulation) |
| **Data Volume** | 241K nodes | 4.8K nodes |
| **Search** | ❌ No indices | ✅ Graphiti fulltext |
| **Schema** | Custom Bundestag | Graphiti + Political overlay |
| **Use Case** | German legislative tracking | EU regulatory monitoring |
| **Questions Focus** | Parliamentary procedures | Corporate compliance & policy impact |

---

**Document Version**: 1.0
**Created**: 2025-01-18
**Database**: politicalmonitoring
**Schema**: Graphiti (Entity/Episodic/Community) + Political overlays
**Total Entities**: 3,026 Entities + 1,747 Episodic nodes
