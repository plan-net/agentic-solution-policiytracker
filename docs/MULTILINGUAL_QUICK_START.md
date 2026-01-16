# Multilingual Retrieval - Quick Start Guide

**Last Updated**: 2026-01-16
**Time to Complete**: 15 minutes

---

## 🎯 What This Is About

Your PolicyTracker knowledge graph contains both **English** and **German** content, but searches in one language don't find entities in the other language well. This causes incomplete results for users.

**Example Problem**:
- User searches: "GDPR penalties" → Finds English entities, **misses** German "DSGVO" entities ❌
- User searches: "DSGVO-Strafen" → Finds German entities, **misses** English "GDPR" entities ❌

**Goal**: Make searches work across both languages automatically ✅

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Run Embedding Test

```bash
cd /path/to/policiytracker-agentic-solution/agentic-solution-policiytracker

# Set environment variables (if not in .env)
export OPENAI_API_KEY="your-key-here"
export APISIX_GATEWAY_URL="http://localhost:9080/v1"

# Run test
python test_multilingual_embeddings.py
```

**What it does**: Tests if your current embeddings (text-embedding-3-small) already support cross-lingual similarity.

**Takes**: ~5-7 minutes

**Look for this line**:
```
✅ EXCELLENT: Current embeddings are MULTILINGUAL
   → No need to re-embed the knowledge graph
```

---

### Step 2: Run Graph Analysis

```bash
# Make sure Neo4j environment variables are set
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="your-password"
export NEO4J_DATABASE="politicalmonitoring.v3"

# Run test
python test_graph_embeddings.py
```

**What it does**: Analyzes your actual Neo4j graph to see language distribution and embedding quality.

**Takes**: ~2-3 minutes

**Look for**:
- Embedding coverage: Should be >90%
- German vs English entity counts
- Whether vector search returns mixed languages

---

## 📊 Interpreting Results

### Scenario A: Embeddings ARE Multilingual ✅

**Test output says:**
```
✅ EXCELLENT: Current embeddings are MULTILINGUAL
   Pass rate: 85%
```

**What this means:**
- Your embeddings already work across languages!
- Vector similarity finds both German and English entities
- **Only keyword search needs fixing** (CONTAINS matching)

**Next step:** Implement **Option 1** (Query Translation)
- Add translation for keyword search
- Keep existing embeddings
- **Time**: 2-3 days
- **Cost**: +$0.0002 per query

---

### Scenario B: Embeddings NOT Multilingual ❌

**Test output says:**
```
❌ POOR: Embeddings are NOT multilingual
   Pass rate: 45%
```

**What this means:**
- Vector search doesn't find cross-lingual matches
- Both keyword AND vector search need fixing

**Next step:** Implement **Option 1 + Option 2**
- Short-term: Add query translation (2-3 days)
- Long-term: Re-embed with multilingual model (2-3 weeks)
- **Cost**: +$0.30 one-time re-embedding

---

### Scenario C: Partial Multilingual ⚠️

**Test output says:**
```
⚠️  PARTIAL: Embeddings have some multilingual capability
   Pass rate: 65%
```

**What this means:**
- Works for common terms, struggles with specialized vocabulary

**Next step:** Implement **Option 1 first**, evaluate if Option 2 needed
- Monitor performance after Option 1
- Decide on re-embedding based on results

---

## 🛠️ What Happens Next?

### Option 1: Query Translation (Recommended First Step)

**How it works:**
```
User Query: "GDPR penalties"
    ↓
1. Detect language → English
2. Translate → "DSGVO-Strafen"
3. Search BOTH versions in parallel
4. Merge results (deduplicate by UUID)
    ↓
Result: Entities from both English and German
```

**Files to modify:**
- `src/mcp/graph_retrieval/retriever.py` - Add translation logic
- `src/config.py` - Add configuration flags

**Timeline**: 2-3 days development + 1 day testing

**Benefits:**
- ✅ Immediate improvement (+35% recall)
- ✅ No graph changes needed
- ✅ Works with existing embeddings

**Drawbacks:**
- ❌ Adds translation latency (~200ms)
- ❌ 2x search cost (can optimize later)

---

### Option 2: Multilingual Embeddings (Long-term)

**How it works:**
```
Current: text-embedding-3-small (may or may not be multilingual)
    ↓
Migrate to: text-embedding-3-large OR Cohere embed-multilingual-v3.0
    ↓
Re-embed all 45K entities in graph
    ↓
Vector search automatically finds cross-lingual matches
```

**Timeline**: 2-3 weeks

**Benefits:**
- ✅ Best long-term solution
- ✅ Single search (no translation needed)
- ✅ Natural cross-lingual discovery

**Drawbacks:**
- ❌ Requires re-embedding entire graph
- ❌ Migration complexity
- ❌ One-time cost (~$0.30)

---

## 📋 Implementation Checklist

### Pre-Implementation
- [ ] Run `test_multilingual_embeddings.py`
- [ ] Run `test_graph_embeddings.py`
- [ ] Document results in `MULTILINGUAL_TEST_RESULTS.md`
- [ ] Make go/no-go decision on approach
- [ ] Get stakeholder approval

### Option 1 Implementation
- [ ] Implement language detection
- [ ] Implement query translation (Claude Haiku)
- [ ] Modify search to execute dual search
- [ ] Implement result merging/deduplication
- [ ] Add configuration flags
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Performance testing
- [ ] Deploy to staging
- [ ] Validate with real queries
- [ ] Deploy to production
- [ ] Monitor metrics

### Option 2 Implementation (if needed)
- [ ] Select multilingual embedding model
- [ ] Create re-embedding pipeline
- [ ] Test with sample entities
- [ ] Batch re-embed all entities
- [ ] Update Neo4j properties
- [ ] Validate retrieval quality
- [ ] Performance tuning
- [ ] Deploy changes

---

## 🎓 Key Concepts

### What is Hybrid Search?

```
Hybrid Search = Keyword Search + Vector Search

Keyword Search (40%):
  - Exact matching: "Digital" CONTAINS "Digital Services Act" ✓
  - Language-dependent: "Digital" does NOT match "Digitale" ✗

Vector Search (60%):
  - Semantic similarity: embeddings capture meaning
  - May work across languages (if model is multilingual)
```

### Why Language Matters

**English Query Example:**
```cypher
MATCH (n:Entity)
WHERE toLower(n.name) CONTAINS "digital"  // Only finds "Digital Services Act"
   OR vector_similarity(n.embedding, query_emb) > 0.3  // May find "Digitale-Dienste-Gesetz" IF embeddings are multilingual
```

**Problem:** Keyword part always language-specific, vector part depends on embedding model.

---

## 🔍 Troubleshooting

### Test Script Fails

**Error**: `OPENAI_API_KEY not set`
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

**Error**: `Neo4j connection failed`
```bash
# Check Neo4j is running
docker ps | grep neo4j

# Verify credentials
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="your-password"
```

**Error**: `Module not found`
```bash
pip install -r requirements.txt
```

---

### Unexpected Test Results

**All tests fail (similarity = 0.0)**
- Check if entities have embeddings in Neo4j
- Run `test_graph_embeddings.py` to verify coverage

**Some tests pass, some fail**
- This is expected! Different terms have different cross-lingual similarity
- Look at pass rate: >80% = Good, 60-80% = OK, <60% = Poor

---

## 📞 Getting Help

**Questions?**
- Read full documentation: `docs/MULTILINGUAL_RETRIEVAL.md`
- Check test results: `docs/MULTILINGUAL_TEST_RESULTS.md`
- Contact: [Team lead / Slack channel]

**Found a bug?**
- File issue with test output attached
- Include environment details (Python version, Neo4j version, etc.)

---

## 📚 Additional Resources

### Documentation Files
- `MULTILINGUAL_RETRIEVAL.md` - Full technical documentation (40 pages)
- `MULTILINGUAL_TEST_RESULTS.md` - Test results tracking template
- `MULTILINGUAL_QUICK_START.md` - This file

### Test Scripts
- `test_multilingual_embeddings.py` - OpenAI embedding tests
- `test_graph_embeddings.py` - Neo4j graph analysis

### Code References
- `src/mcp/graph_retrieval/retriever.py:452-719` - Hybrid search implementation
- `src/claude_agent/agent.py:30-58` - System prompt with language instructions
- `src/flows/shared/apisix_llm_client.py:400-441` - Embedding client

### External Links
- [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)
- [Cohere Multilingual Models](https://docs.cohere.com/docs/multilingual-language-models)
- [Neo4j Vector Search](https://neo4j.com/docs/cypher-manual/current/indexes-for-vector-search/)

---

## ✅ Success Criteria

After implementation, you should see:

| Metric | Before | Target | How to Measure |
|--------|--------|--------|----------------|
| English query recall | ~70% | 85% | Manual evaluation of sample queries |
| German query recall | ~70% | 85% | Manual evaluation of sample queries |
| Cross-lingual recall | ~40% | 80% | Test queries that should find both languages |
| Query latency (P50) | 800ms | <1200ms | APM monitoring |
| User satisfaction | ? | 4.5/5 | User surveys |

**"Done" means:**
- ✅ Tests show ≥80% cross-lingual recall
- ✅ Production metrics match targets
- ✅ User feedback is positive
- ✅ No performance degradation

---

**Ready to start? Run the tests! 🚀**

```bash
python test_multilingual_embeddings.py
python test_graph_embeddings.py
```

Then document your findings and make a plan!
