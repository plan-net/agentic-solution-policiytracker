# GPT-4o-mini vs GPT-4.1-nano Comparison
## Graphiti Entity Extraction Quality Test

**Test Date**: 2026-02-18
**Test Documents**: 6 documents (same for both models)

## Test Documents

| Type | Document |
|------|----------|
| News | 20260206_zoey-denmark__66123852.md |
| News | 20260203_earth_the-environmental-impact-of-fast-fashion-explained_da42c1a7.md |
| Policy | 20260206_dw-com_european-nations-gear-up-to-ban-social-media-for-c.md |
| Policy | 20260210_pharmtech-com_european-parliament-revamps-pharmaceutical-policy.md |
| Ad-hoc | 20251126_adhoc_250711_kabinettzeitplanungattachment-1-zalando-mon.md |
| Ad-hoc | 20251126_adhoc_250822_kabinettzeitplanung.md |

---

## Executive Summary

| Metric | GPT-4o-mini | GPT-4.1-nano | Winner |
|--------|-------------|--------------|--------|
| **Total Entities** | 196 | 122 | GPT-4o-mini (+61%) |
| **Total Relationships** | 204 | 71 | GPT-4o-mini (+187%) |
| **Processing Time** | 918s | 413s | GPT-4.1-nano (2.2x faster) |
| **Schema Compliance** | 90.8% | 78.7% | GPT-4o-mini (+12.1%) |
| **Unknown Entities** | 18 (9.2%) | 26 (21.3%) | GPT-4o-mini (less unknowns) |

**Overall Winner: GPT-4o-mini** for extraction quality
**Best Value: GPT-4.1-nano** for speed/cost efficiency

---

## Entity Extraction Comparison

### Summary

| Metric | GPT-4o-mini | GPT-4.1-nano | Difference |
|--------|-------------|--------------|------------|
| Total Entities | 196 | 122 | -74 (-37.8%) |
| Valid Entity Types | 178 | 96 | -82 (-46.1%) |
| Unknown Entities | 18 | 26 | +8 (+44.4%) |
| Schema Compliance | 90.8% | 78.7% | -12.1% |

### Entity Types Breakdown

**GPT-4o-mini (196 entities)**:
| Entity Type | Count | Valid? |
|-------------|-------|--------|
| LegislativeProposal | 57 | ✓ |
| Document | 28 | ✓ |
| Unknown | 18 | ✗ |
| LegislativeBody | 17 | ✓ |
| Company | 16 | ✓ |
| Jurisdiction | 13 | ✓ |
| Policy | 11 | ✓ |
| GovernmentAgency | 10 | ✓ |
| Person | 10 | ✓ |
| LobbyGroup | 7 | ✓ |
| Others | 9 | Mixed |

**GPT-4.1-nano (122 entities)**:
| Entity Type | Count | Valid? |
|-------------|-------|--------|
| Unknown | 26 | ✗ |
| GovernmentAgency | 20 | ✓ |
| Document | 15 | ✓ |
| Jurisdiction | 15 | ✓ |
| Person | 10 | ✓ |
| Politician | 9 | ✓ |
| Industry | 8 | ✓ |
| LegislativeBody | 5 | ✓ |
| PoliticalParty | 4 | ✓ |
| TechnicalStandard | 3 | ✓ |
| Others | 7 | Mixed |

### Key Observations

1. **LegislativeProposal Extraction**:
   - GPT-4o-mini: 57 entities (excellent for German political documents)
   - GPT-4.1-nano: 0 entities (missed entirely!)

2. **Unknown Entity Rate**:
   - GPT-4o-mini: 9.2% unknown
   - GPT-4.1-nano: 21.3% unknown
   - GPT-4o-mini is **2.3x better** at classifying entities correctly

3. **GovernmentAgency Detection**:
   - GPT-4o-mini: 10 entities
   - GPT-4.1-nano: 20 entities
   - GPT-4.1-nano detected more government agencies

---

## Relationship Extraction Comparison

| Metric | GPT-4o-mini | GPT-4.1-nano | Difference |
|--------|-------------|--------------|------------|
| Total Relationships | 204 | 71 | -133 (-65.2%) |
| Avg Relationships/Entity | 1.04 | 0.58 | -0.46 (-44.2%) |

**GPT-4o-mini extracted 2.9x more relationships** than GPT-4.1-nano, creating a much richer knowledge graph.

---

## Processing Performance

| Metric | GPT-4o-mini | GPT-4.1-nano | Difference |
|--------|-------------|--------------|------------|
| Total Time | 918.06s | 413.01s | -505s (-55%) |
| Avg Time/Document | 153.0s | 68.8s | -84.2s (-55%) |
| Entities/Second | 0.21 | 0.30 | +0.09 (+43%) |

**GPT-4.1-nano is 2.2x faster** than GPT-4o-mini.

---

## Cost Comparison (Estimated)

Based on OpenAI pricing (as of early 2026):

| Model | Input ($/1M tokens) | Output ($/1M tokens) | Estimated Cost* |
|-------|---------------------|----------------------|-----------------|
| GPT-4o-mini | $0.15 | $0.60 | ~$0.02 |
| GPT-4.1-nano | $0.10 | $0.40 | ~$0.013 |

*Rough estimate for 6 documents with ~10K tokens each

**GPT-4.1-nano is ~35% cheaper** than GPT-4o-mini.

---

## Quality vs Cost Analysis

| Aspect | GPT-4o-mini | GPT-4.1-nano |
|--------|-------------|--------------|
| Entities per Dollar | ~9,800 | ~9,385 |
| Relationships per Dollar | ~10,200 | ~5,462 |
| Schema Compliance | 90.8% | 78.7% |
| Speed (docs/min) | 0.39 | 0.87 |

**Value Assessment**:
- **GPT-4o-mini**: Better for quality-critical applications
- **GPT-4.1-nano**: Better for high-volume, cost-sensitive processing

---

## Recommendations

### Use GPT-4o-mini When:
1. ✅ Extracting **LegislativeProposal** entities (critical for political monitoring)
2. ✅ Building **comprehensive knowledge graphs** (more relationships)
3. ✅ **Schema compliance** is important (90.8% vs 78.7%)
4. ✅ You need to minimize **unknown entity classification**
5. ✅ Quality matters more than speed

### Use GPT-4.1-nano When:
1. ✅ Processing **high volumes** of documents (2.2x faster)
2. ✅ **Cost is a primary concern** (~35% cheaper)
3. ✅ Extracting **GovernmentAgency** entities (performs well)
4. ✅ Initial/exploratory data processing before refinement
5. ✅ Speed matters more than completeness

---

## Critical Finding: LegislativeProposal Gap

**GPT-4.1-nano completely missed LegislativeProposal entities** while GPT-4o-mini extracted 57 of them. This is critical for political monitoring use cases.

For the Policy Tracker application, which focuses on legislative proposals and policy monitoring, **GPT-4o-mini is strongly recommended** despite the higher cost and slower processing time.

---

## Test Configuration

```
Provider: OpenAI (direct API)
APISIX_GATEWAY_URL: https://api.openai.com/v1
Neo4j Database: politicalmonitoring.v3
Processing Framework: Ray with DocumentProcessorActor
Chunking: Hybrid (1500 tokens, 10% overlap)
```

---

*Generated: 2026-02-18*
*Test Framework: LLM Provider Comparison Test v1.1.0*
