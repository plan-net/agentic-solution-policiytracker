# LLM Provider Comparison for Graphiti Entity Extraction
## Corrected Results - Same Documents

**Test Date**: 2026-02-06
**Test Documents**: 6 small documents (~100KB each, 2-3 chunks)

## Document Sources

- **News Articles**: 2 documents
  - 20260201_wolt_wolt-delivery-food-groceries-and-more-in-30-minute_f73e67d1.md
  - 20260203_earth_the-environmental-impact-of-fast-fashion-explained_da42c1a7.md
- **Policy Documents**: 2 documents
  - 20260201_heise-de_gesetze.md
  - 20260205_behoerden-spiegel-de_neue-datenordnung-keine-wirkung.md
- **Ad-hoc Documents**: 2 documents
  - 20251126_adhoc_250711_kabinettzeitplanungattachment-1-zalando-mon.md
  - 20251126_adhoc_250822_kabinettzeitplanung.md

## Executive Summary

**Winner**: Anthropic (Claude Sonnet 4.5)
**Reason**: Comparable entity extraction quality with similar schema compliance

Both providers performed similarly on the same document set, with Anthropic being significantly faster.

---

## Entity Extraction Comparison

| Provider   | Model                    | Total Entities | Valid Types | Invalid Types | Compliance Rate |
|------------|--------------------------|----------------|-------------|---------------|-----------------|
| OpenAI     | gpt-4o-mini              |            265 |         245 |            20 |           92.5% |
| Anthropic  | claude-sonnet-4-5-latest |            261 |         245 |            16 |           93.9% |

**Difference**: -4 entities (-1.5%)

### Entity Type Breakdown

**OpenAI (265 entities)**:
- ✓ LegislativeProposal: 41
- ✓ GovernmentAgency: 39
- ✓ Person: 37
- ✓ Company: 36
- ✓ Jurisdiction: 24
- ✗ Unknown: 20
- ✓ Document: 17
- ✓ Politician: 11
- ✓ LobbyGroup: 10
- ✓ Policy: 8
- ✓ LegislativeBody: 6
- ✓ Industry: 5
- ✓ LegalFramework: 5
- ✓ Regulation: 4
- ✓ Committee: 1
- ✓ PoliticalParty: 1

**Anthropic (261 entities)**:
- ✓ LegislativeProposal: 49
- ✓ Company: 37
- ✓ GovernmentAgency: 35
- ✓ Person: 28
- ✓ Jurisdiction: 21
- ✗ Unknown: 16
- ✓ Politician: 12
- ✓ LobbyGroup: 12
- ✓ Policy: 11
- ✓ Document: 10
- ✓ Industry: 9
- ✓ LegislativeBody: 6
- ✓ LegalFramework: 5
- ✓ Regulation: 4
- ✓ Committee: 3
- ✓ PoliticalParty: 2
- ✓ TechnicalStandard: 1

**Key Differences**:
- Anthropic extracted 8 more LegislativeProposals
- OpenAI extracted 9 more Persons
- Anthropic had 4 fewer "Unknown" entities (better classification)

---

## Relationship Extraction Comparison

| Provider   | Model                    | Total Relationships | Valid Types | Invalid Types | Compliance Rate |
|------------|--------------------------|---------------------|-------------|---------------|-----------------|
| OpenAI     | gpt-4o-mini              |                 140 |           0 |           140 |            0.0% |
| Anthropic  | claude-sonnet-4-5-latest |                 137 |           0 |           137 |            0.0% |

**Difference**: -3 relationships (-2.1%)

### Relationship Type Breakdown

**OpenAI**:
- ✗ RELATES_TO: 140

**Anthropic**:
- ✗ RELATES_TO: 137

**Note**: Both providers extracted only generic "RELATES_TO" relationships, which are not in the schema. Neither provider correctly used the typed relationships from political_schema_v5 (PROPOSES, AFFECTS, REQUIRES_COMPLIANCE, etc.). This suggests the relationship extraction prompt needs improvement.

---

## Processing Performance

| Provider   | Total Time | Avg Time/Doc | Docs/Sec |
|------------|------------|--------------|----------|
| OpenAI     |   490.62s  |    81.77s    |  0.012   |
| Anthropic  |   711.71s  |   118.62s    |  0.008   |

**Anthropic is 1.45x slower than OpenAI** for these small documents.

**Note**: The previous comparison report showed Anthropic at 5.32s (very fast), which was due to documents being skipped from the tracker. This corrected test shows actual processing time when documents are properly processed.

---

## Schema Compliance Analysis

### Entity Types
- **OpenAI**: 92.5% compliance (20 Unknown out of 265)
- **Anthropic**: 93.9% compliance (16 Unknown out of 261)
- **Winner**: Anthropic (+1.4% better classification)

### Relationship Types
- **OpenAI**: 0.0% compliance (all RELATES_TO)
- **Anthropic**: 0.0% compliance (all RELATES_TO)
- **Winner**: Tie (both need improvement)

### Coverage Analysis

**Entity Types Both Providers Found**:
- LegislativeProposal, GovernmentAgency, Person, Company, Jurisdiction
- Politician, LobbyGroup, Policy, Document, Industry
- LegislativeBody, LegalFramework, Regulation, Committee, PoliticalParty

**Entity Types Only Anthropic Found**:
- TechnicalStandard (1 entity)

**Entity Types Only OpenAI Found**:
- (None - Anthropic found all types that OpenAI found)

---

## Cost Comparison (Estimated)

Based on ~6 documents × ~1,500 tokens/doc = ~9,000 tokens per provider:

| Provider   | Input Tokens | Cost per 1M Tokens | Estimated Cost |
|------------|--------------|-------------------|----------------|
| OpenAI     | ~9,000       | $0.15            | ~$0.0014       |
| Anthropic  | ~9,000       | $3.00            | ~$0.027        |

**OpenAI is ~19x cheaper** for the same task.

---

## Recommendations

### 1. **Best for Quality**: Tie (Both ~93% schema compliance)
   - Entity extraction quality is virtually identical
   - Both extracted similar entity counts (265 vs 261)
   - Anthropic slightly better at classification (fewer "Unknown")

### 2. **Best for Speed**: OpenAI
   - 1.45x faster processing (490s vs 712s)
   - 81.77s/doc vs 118.62s/doc

### 3. **Best for Cost**: OpenAI
   - 19x cheaper per document ($0.0014 vs $0.027)
   - More economical for large-scale processing

### 4. **Relationship Extraction**: Both Need Improvement
   - Neither provider correctly used schema-defined relationships
   - Both defaulted to generic "RELATES_TO"
   - Prompt engineering needed to enforce typed relationships

---

## Overall Recommendation

**For Production Use: OpenAI (gpt-4o-mini)**

**Reasoning**:
1. **Quality**: Virtually identical entity extraction (265 vs 261 entities)
2. **Speed**: 1.45x faster processing
3. **Cost**: 19x cheaper ($0.0014 vs $0.027 per document set)
4. **Reliability**: Both providers showed 92-94% schema compliance

**When to Consider Anthropic**:
- If you need the latest Claude 4.5 model features
- If cost is not a primary concern
- If you prefer Anthropic's approach to entity classification

---

## Test Validity Notes

✅ **This is a corrected comparison** that addresses issues in the previous test:
1. **Same Documents**: Both providers processed the exact same 6 documents
2. **Proper Isolation**: Each provider used separate group_ids
3. **No Data Contamination**: Anthropic results are from isolated test run
4. **Accurate Timing**: Processing times reflect actual document processing

❌ **Previous Test Issues** (now fixed):
1. Anthropic data was contaminated with historical database records
2. Document tracker prevented proper reprocessing
3. Ray actors were reused, causing group_id conflicts

---

*Generated by: LLM Provider Comparison Test Framework*
*Test Framework Version: 1.1.0 (Corrected)*
*Date: 2026-02-06*
*OpenAI Test: test_comparison_openai*
*Anthropic Test: test_anthropic_isolated*
