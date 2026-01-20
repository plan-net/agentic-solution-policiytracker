---
name: weekly_report_planning
version: 1
description: Planning strategy for weekly report generation
tags: ["sdk", "strategy", "report", "planning"]
---
## Report Generation Strategy

Execute your research in this order for comprehensive coverage:

### Step 1: Category Research

Research each category systematically. For each category:

1. **Initial Search**: Use `search_knowledge_graph` with category-specific query
   - Legislative: "regulations directives laws digital policy"
   - Personnel: "appointments leadership changes officials"
   - Compliance: "enforcement fines compliance actions"
   - Policy: "government strategy policy announcements"
   - Events: "deadlines hearings events calendar"

2. **Handle Sparse Results**: If initial search returns few results:
   - Broaden search terms
   - Try related concepts
   - Use `find_relationships` to discover connected entities

3. **Verify Key Entities**: For important entities mentioned:
   - Use `get_entity_info` to get full details
   - Confirm dates, names, and specifics

### Step 2: Cross-Category Analysis

After researching individual categories:

1. **Find Cross-References**: Use `find_relationships` to discover:
   - How regulatory changes affect companies
   - Which personnel are involved in multiple developments
   - Connections between policies and enforcement

2. **Identify Themes**: Look for patterns that span categories:
   - Multiple developments related to same regulation
   - Coordinated policy initiatives
   - Emerging focus areas

### Step 3: Validation Pass

Before synthesizing the report:

1. **Verify Critical Facts**: Double-check important information
   - Dates and deadlines
   - Names and titles
   - Specific regulatory references

2. **Check for Gaps**: Ensure each category has coverage
   - If a category is thin, note data limitations
   - Don't fabricate information to fill gaps

3. **Assess Confidence**: Rate your confidence for each section
   - High: Multiple sources, specific details
   - Medium: Some information but incomplete
   - Low: Limited data, note uncertainty

### Step 4: Synthesis

Combine findings into the report structure:

1. **Executive Summary First**: Write after researching all sections
   - Pull the most impactful items from each category
   - Prioritize by urgency and stakeholder relevance

2. **Category Sections**: Write in order of research
   - Lead with most significant developments
   - Include specific details (names, dates, references)
   - Cite knowledge graph sources

3. **Cross-Cutting Themes**: Synthesize patterns identified
   - Connect developments across categories
   - Highlight implications

4. **Action Items**: Compile from all sections
   - Assign priority levels (🔴🟡🟢)
   - Include deadlines where known
   - Be specific about what action is needed

## Research Efficiency Tips

- **Batch Related Queries**: Group searches by topic area
- **Use Entity Info Sparingly**: Only for key entities that need verification
- **Track What You've Searched**: Avoid redundant queries
- **Note Gaps Early**: Don't spend excessive time on sparse areas

## Quality Checkpoints

Before finalizing each section, verify:

- [ ] Specific entities and dates cited
- [ ] Sources from knowledge graph referenced
- [ ] Priority levels assigned to actionable items
- [ ] Limitations acknowledged where data is sparse
- [ ] Cross-references to other sections noted
