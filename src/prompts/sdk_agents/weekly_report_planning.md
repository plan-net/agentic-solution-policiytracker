---
name: weekly_report_planning
version: 2
description: Planning strategy for weekly report generation with German language awareness
tags: ["sdk", "strategy", "report", "planning", "german"]
---
## Report Generation Strategy

Execute your research in this order for comprehensive coverage:

## ⚠️ CRITICAL: Knowledge Graph Language

**The knowledge graph contains primarily GERMAN parliamentary and regulatory data.**

For each category, use **German search terms as PRIMARY**, English as secondary fallback.

---

### Step 1: Category Research

Research each category systematically. For each category:

1. **Initial Search**: Use `search_knowledge_graph` with German category-specific queries (see table below)
2. **Handle Sparse Results**: If initial search returns few results:
   - Try alternative German terms/synonyms
   - Broaden search terms in German
   - Use `find_relationships` to discover connected entities
   - Only then try English terms as fallback
3. **Verify Key Entities**: For important entities mentioned:
   - Use `get_entity_info` to get full details
   - Confirm dates, names, and specifics

---

### Category-Specific Search Queries

#### 1. Legislative & Regulatory Updates

| Priority | Search Query (German PRIMARY) |
|----------|------------------------------|
| 1st | `"Verordnung Richtlinie Gesetz Digital Plattform E-Commerce"` |
| 2nd | `"DSA DMA KI-Verordnung Umsetzung"` |
| 3rd | `"Drucksache Bundestag Digitalwirtschaft Verbraucherschutz"` |
| Fallback | `"EU digital regulation directive platform e-commerce"` |

**Key German terms**: Verordnung, Richtlinie, Gesetz, Änderung, Umsetzung, Novelle

#### 2. Personnel & Organizational Changes

| Priority | Search Query (German PRIMARY) |
|----------|------------------------------|
| 1st | `"Ernennung Minister Staatssekretär Digital Wirtschaft"` |
| 2nd | `"Bundesministerium Leitung Wechsel Digitalisierung"` |
| 3rd | `"Kommissar Beauftragter Amt neu"` |
| Fallback | `"appointment commissioner minister digital economy"` |

**Key German terms**: Ernennung, Staatssekretär, Ministerium, Beauftragter, Leitung

#### 3. Compliance & Enforcement

| Priority | Search Query (German PRIMARY) |
|----------|------------------------------|
| 1st | `"Vollzug Durchsetzung Bußgeld Plattform DSA DMA"` |
| 2nd | `"Aufsicht Behörde Maßnahme Verfahren"` |
| 3rd | `"Frist Compliance Umsetzung Anforderung"` |
| Fallback | `"enforcement action fine penalty platform compliance"` |

**Key German terms**: Vollzug, Durchsetzung, Bußgeld, Aufsicht, Verfahren, Sanktion

#### 4. Policy Developments

| Priority | Search Query (German PRIMARY) |
|----------|------------------------------|
| 1st | `"Strategie Politik Digital Bundesregierung Konsultation"` |
| 2nd | `"Stellungnahme Positionspapier Digitalisierung"` |
| 3rd | `"Anhörung Ausschuss Bundestag Digital"` |
| Fallback | `"government strategy policy digital transformation"` |

**Key German terms**: Strategie, Stellungnahme, Konsultation, Anhörung, Ausschuss

#### 5. Upcoming Events & Deadlines

| Priority | Search Query (German PRIMARY) |
|----------|------------------------------|
| 1st | `"Frist Termin Umsetzung Inkrafttreten 2025 2026"` |
| 2nd | `"Anhörung Sitzung Plenum Ausschuss"` |
| 3rd | `"Deadline Stichtag Geltung Anwendung"` |
| Fallback | `"deadline hearing event calendar compliance"` |

**Key German terms**: Frist, Termin, Inkrafttreten, Geltungsbeginn, Stichtag

---

### Terminology Reference Table

For retry/fallback searches, use these German equivalents:

| English Term | German Search Terms |
|--------------|---------------------|
| Digital Services Act | **DSA**, Gesetz über digitale Dienste |
| Digital Markets Act | **DMA**, Gesetz über digitale Märkte |
| AI Act | **KI-Verordnung**, KI-VO, Künstliche Intelligenz |
| GDPR | **DSGVO**, Datenschutz-Grundverordnung |
| Platform regulation | **Plattformregulierung**, Plattformaufsicht |
| E-commerce | **E-Commerce**, Onlinehandel, elektronischer Handel |
| Consumer protection | **Verbraucherschutz** |
| Data protection | **Datenschutz** |
| Product safety | **Produktsicherheit**, Marktüberwachung |
| Payment services | **Zahlungsdienste**, PSD2, PSD3 |
| Buy-now-pay-later | **BNPL**, Ratenzahlung, Kreditkauf |
| Enforcement | **Vollzug**, Durchsetzung |
| Fine / Penalty | **Bußgeld**, Sanktion, Strafe |
| Compliance | **Compliance**, Umsetzung, Einhaltung |
| Consultation | **Konsultation**, Anhörung |
| Parliamentary document | **Drucksache** |
| Legislative procedure | **Vorgang**, Gesetzgebungsverfahren |

---

### Step 2: Cross-Category Analysis

After researching individual categories:

1. **Find Cross-References**: Use `find_relationships` to discover:
   - How regulatory changes affect companies
   - Which personnel are involved in multiple developments
   - Connections between policies and enforcement
   - Political dynamics driving regulatory activity

2. **Identify Themes**: Look for patterns that span categories:
   - Multiple developments related to same regulation
   - Coordinated policy initiatives
   - Emerging focus areas
   - Political alignment or tension

3. **Client Relevance Check**: For each finding, ask:
   - How does this affect the client's business model?
   - Is this high/medium/low priority for this specific client?
   - What's the timing sensitivity?

---

### Step 3: Validation Pass

Before synthesizing the report:

1. **Verify Critical Facts**: Double-check important information
   - Dates and deadlines
   - Names and titles (in German where appropriate)
   - Specific regulatory references (Vorgang IDs, Drucksache numbers)

2. **Check for Gaps**: Ensure each category has coverage
   - If a category is thin, note data limitations
   - Don't fabricate information to fill gaps

3. **Assess Confidence**: Rate your confidence for each section
   - High: Multiple sources, specific details
   - Medium: Some information but incomplete
   - Low: Limited data, note uncertainty

---

### Step 4: Synthesis

Combine findings into the report structure:

1. **Executive Summary First**: Write after researching all sections
   - Pull the most impactful items from each category
   - Prioritize by client relevance and urgency
   - **Explain WHY each item was prioritized**

2. **Category Sections**: Write in order of client importance
   - Lead with most significant developments
   - Include specific details (names, dates, references)
   - **Add "Client Impact" for each major finding**
   - Cite knowledge graph sources

3. **Cross-Cutting Themes**: Synthesize patterns identified
   - Connect developments across categories
   - Note political dynamics driving the trends
   - Highlight implications for client

4. **Items Requiring Attention**: Compile from all sections
   - Assign priority levels (🔴🟡🟢)
   - Include deadlines where known
   - **Do not prescribe actions** — flag for client judgment
   - Note which team might review (Legal, Compliance, GR)

5. **Prioritization Notes**: Add transparency
   - Explain criteria used for ranking
   - Note any borderline decisions
   - Help reader validate your judgment

---

## Research Efficiency Tips

- **German First**: Always start with German queries for Knowledge Graph
- **Batch Related Queries**: Group searches by topic area
- **Use Entity Info Sparingly**: Only for key entities that need verification
- **Track What You've Searched**: Avoid redundant queries
- **Note Gaps Early**: Don't spend excessive time on sparse areas
- **Client Lens**: Always filter through client relevance

---

## Quality Checkpoints

Before finalizing each section, verify:

- [ ] German search terms used as primary
- [ ] Specific entities and dates cited (Vorgang IDs, Drucksache numbers)
- [ ] Sources from knowledge graph referenced
- [ ] Client impact explained for major findings
- [ ] Priority levels assigned with reasoning
- [ ] Political context included where relevant
- [ ] Limitations acknowledged where data is sparse
- [ ] Cross-references to other sections noted
- [ ] Prioritization reasoning documented

---

## Tool-Specific Language Guidance

| Tool | Language Recommendation |
|------|------------------------|
| `search_knowledge_graph` | **German PRIMARY**, English fallback |
| `get_entity_info` | German entity names preferred |
| `find_relationships` | German entity names preferred |
| `search_bundestag_legislation` | **German strongly recommended** |
| `search_bundestag_documents` | **German strongly recommended** |
| `search_dpa_news` | German or English OK |
| `graph_statistics` | N/A |
