# Multilingual Retrieval Issue - Documentation Index

**Project**: PolicyTracker Knowledge Graph
**Issue**: Cross-lingual Search & Retrieval
**Status**: 📋 Documented, 🧪 Testing Phase
**Created**: 2026-01-16

---

## 📚 Documentation Overview

This directory contains comprehensive documentation for addressing the multilingual retrieval challenge in PolicyTracker. The issue affects users querying the knowledge graph in English or German, resulting in incomplete results.

---

## 🗂️ Document Guide

### 1. Executive Summary (Start Here for Leadership)
**File**: [`MULTILINGUAL_EXECUTIVE_SUMMARY.md`](./MULTILINGUAL_EXECUTIVE_SUMMARY.md)
**Audience**: Product Managers, CTOs, Decision Makers
**Read Time**: 5 minutes

**What's Inside**:
- Business impact and user pain points
- Proposed solution with cost-benefit analysis
- Timeline and resource requirements
- ROI analysis and approval section

**When to Read**: Before making go/no-go decision

---

### 2. Quick Start Guide (Start Here for Engineers)
**File**: [`MULTILINGUAL_QUICK_START.md`](./MULTILINGUAL_QUICK_START.md)
**Audience**: Developers, QA Engineers
**Read Time**: 15 minutes

**What's Inside**:
- How to run the tests (step-by-step)
- Interpreting test results
- What happens next based on results
- Troubleshooting common issues

**When to Read**: Before running tests or implementing

---

### 3. Full Technical Documentation
**File**: [`MULTILINGUAL_RETRIEVAL.md`](./MULTILINGUAL_RETRIEVAL.md)
**Audience**: Senior Engineers, Architects, Technical Leads
**Read Time**: 30-45 minutes

**What's Inside**:
- Detailed problem analysis and root causes
- Current architecture breakdown
- 5 solution options with pros/cons/costs
- Implementation pseudocode
- Testing strategy
- Complete timeline and phases

**When to Read**: For deep technical understanding and implementation planning

---

### 4. Test Results & Progress Tracking
**File**: [`MULTILINGUAL_TEST_RESULTS.md`](./MULTILINGUAL_TEST_RESULTS.md)
**Audience**: Everyone (Living Document)
**Read Time**: 5-10 minutes

**What's Inside**:
- Progress tracker with task status
- Test results log (to be filled)
- Performance benchmarks
- Decision log
- User feedback tracking

**When to Read**:
- After running tests (to document results)
- To track implementation progress
- To review historical decisions

---

## 🧪 Test Scripts

### Test 1: API Embedding Evaluation
**File**: `../test_multilingual_embeddings.py`
**Purpose**: Test if OpenAI embeddings support cross-lingual similarity
**Duration**: 5-7 minutes
**Prerequisites**: `OPENAI_API_KEY`, `APISIX_GATEWAY_URL`

**Run**:
```bash
python test_multilingual_embeddings.py
```

**Output**: Pass/fail results for 26 English-German translation pairs

---

### Test 2: Neo4j Graph Analysis
**File**: `../test_graph_embeddings.py`
**Purpose**: Analyze existing embeddings in your knowledge graph
**Duration**: 2-3 minutes
**Prerequisites**: `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`

**Run**:
```bash
python test_graph_embeddings.py
```

**Output**: Graph composition, embedding coverage, cross-lingual behavior

---

## 🚀 Getting Started

### For First-Time Readers

**If you're a decision maker**:
1. Read: [`MULTILINGUAL_EXECUTIVE_SUMMARY.md`](./MULTILINGUAL_EXECUTIVE_SUMMARY.md) (5 min)
2. Ask: "Do we approve Phase 1?"
3. Next: Delegate to engineering team

**If you're an engineer**:
1. Read: [`MULTILINGUAL_QUICK_START.md`](./MULTILINGUAL_QUICK_START.md) (15 min)
2. Run: Both test scripts (10 min)
3. Document: Results in [`MULTILINGUAL_TEST_RESULTS.md`](./MULTILINGUAL_TEST_RESULTS.md)
4. Read: [`MULTILINGUAL_RETRIEVAL.md`](./MULTILINGUAL_RETRIEVAL.md) for implementation details
5. Start: Coding!

**If you're a product manager**:
1. Read: [`MULTILINGUAL_EXECUTIVE_SUMMARY.md`](./MULTILINGUAL_EXECUTIVE_SUMMARY.md) (5 min)
2. Read: [`MULTILINGUAL_RETRIEVAL.md`](./MULTILINGUAL_RETRIEVAL.md) sections 1-4 (15 min)
3. Review: Test results when available
4. Decide: Approve/defer/modify

---

## 📋 Typical Workflow

### Week 1: Investigation

```
Day 1-2: Run Tests
├─ Run test_multilingual_embeddings.py
├─ Run test_graph_embeddings.py
└─ Document results in MULTILINGUAL_TEST_RESULTS.md

Day 3: Analysis
├─ Review test results
├─ Determine which option to pursue
└─ Update decision log in MULTILINGUAL_TEST_RESULTS.md

Day 4-5: Planning
├─ Present findings to stakeholders
├─ Get approval via MULTILINGUAL_EXECUTIVE_SUMMARY.md
└─ Plan implementation sprint
```

### Week 2: Implementation (Phase 1)

```
Day 1-2: Coding
├─ Implement language detection
├─ Implement query translation
├─ Implement dual search
└─ Implement result merging

Day 3: Testing
├─ Unit tests
├─ Integration tests
└─ Performance testing

Day 4-5: Deployment
├─ Deploy to staging
├─ Validate with real queries
└─ Monitor metrics
```

### Week 3+: Rollout & Optimization

```
Week 3: Gradual Rollout
├─ 10% traffic (monitor closely)
├─ 50% traffic (collect feedback)
└─ 100% traffic (full deployment)

Week 4-5: Phase 2 Decision
├─ Review Phase 1 results
├─ Decide if Phase 2 needed
└─ Plan Phase 2 if approved
```

---

## 🎯 Key Decisions to Make

### Decision #1: Run Tests?
**Question**: Should we invest time to test our embeddings?
**Cost**: 10 minutes + 0.5 developer-day
**Benefit**: Know exactly what needs fixing
**Recommendation**: ✅ Yes - low cost, high value

**Documented in**: All files mention this as first step

---

### Decision #2: Which Option?
**Question**: Option 1 (Translation) or Option 2 (Re-embedding) or both?
**Depends on**: Test results
**Timeline**: Decide after tests complete

**Decision Tree**:
```
Test Results → Embeddings multilingual?
                    ↓
        ┌───────────┴───────────┐
        ↓                       ↓
    YES (≥80%)              NO (<60%)
        ↓                       ↓
  Option 1 only         Option 1 + 2
  (2-3 days)           (Short+Long term)
```

**Documented in**: `MULTILINGUAL_RETRIEVAL.md` - Decision Tree section

---

### Decision #3: Phase 2 Needed?
**Question**: After Phase 1, do we need Phase 2?
**Timing**: Week 3 (after Phase 1 deployment)
**Criteria**:
- ✅ If cross-lingual recall ≥80% → Skip Phase 2
- ❌ If cross-lingual recall <70% → Proceed with Phase 2

**Documented in**: `MULTILINGUAL_TEST_RESULTS.md` - Decision Log

---

## 📊 Success Metrics

Track these metrics to measure success:

| Metric | Current | Target | How to Measure |
|--------|---------|--------|----------------|
| English query recall | ~70% | 85% | Manual evaluation |
| German query recall | ~70% | 85% | Manual evaluation |
| Cross-lingual recall | ~40% | 80% | Test queries |
| Query latency (P50) | 800ms | <1200ms | APM monitoring |
| User satisfaction | 3.5/5 | 4.5/5 | Surveys |
| Support tickets | Baseline | -30% | Ticket system |

**How to Track**: Document in `MULTILINGUAL_TEST_RESULTS.md` - Performance Benchmarks section

---

## 🔗 Related Resources

### Code Files to Modify (Phase 1)
- `src/mcp/graph_retrieval/retriever.py` - Add multilingual search logic
- `src/config.py` - Add configuration flags
- `src/claude_agent/agent.py` - May need prompt updates

### Code Files to Understand
- `src/mcp/graph_retrieval/retriever.py:452-719` - Current search implementation
- `src/flows/shared/apisix_llm_client.py:400-441` - Embedding client
- `src/graph_viz/context_tracker.py` - Entity tracking

### External References
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)
- [Cohere Multilingual](https://docs.cohere.com/docs/multilingual-language-models)
- [Neo4j Vector Search](https://neo4j.com/docs/cypher-manual/current/indexes-for-vector-search/)

---

## ❓ FAQ

### Q: Why is this happening?
**A**: Your hybrid search uses keyword matching (CONTAINS) + vector similarity. Keyword matching is always language-specific. Vector matching MAY work across languages, but only if the embedding model was trained on multilingual data.

### Q: Can't we just translate entity names in the graph?
**A**: That's Option 4 (Entity Aliases). It works but:
- Doesn't scale to all entities (45K+)
- Requires manual curation
- Maintenance overhead
Better to fix at query time (Option 1) or embedding level (Option 2)

### Q: What if tests show embeddings ARE multilingual?
**A**: Great! You only need Option 1 (Query Translation) to fix keyword search. Simpler and faster.

### Q: What if embeddings are NOT multilingual?
**A**: Do Option 1 immediately (quick fix), then plan Option 2 (long-term solution).

### Q: How much will this cost?
**A**:
- Phase 1: ~$2/month for 10K queries
- Phase 2: ~$0.30 one-time re-embedding
- Total: Negligible (< $30/year)

### Q: Will this slow down searches?
**A**:
- Phase 1: +300ms (translation + dual search)
- Phase 2: -50ms (single search, no translation)
- Net: Acceptable for quality improvement

### Q: Can we add more languages later?
**A**: Yes! Architecture supports any language:
- Phase 1: Add translation pairs (EN↔FR, DE↔FR, etc.)
- Phase 2: Multilingual embeddings support 100+ languages

### Q: What if something goes wrong?
**A**: All changes are reversible:
- Phase 1: Toggle feature flag off
- Phase 2: Keep old embeddings as backup
- Risk is minimal

---

## 📞 Support & Contact

**Questions about**:
- **Testing**: See `MULTILINGUAL_QUICK_START.md` - Troubleshooting section
- **Implementation**: See `MULTILINGUAL_RETRIEVAL.md` - Implementation Plan
- **Business case**: See `MULTILINGUAL_EXECUTIVE_SUMMARY.md`
- **Progress**: See `MULTILINGUAL_TEST_RESULTS.md` - Progress Tracker

**Contact**:
- Technical Lead: [Name / Slack]
- Product Manager: [Name / Slack]
- Team Channel: [#channel-name]

**Report Issues**:
- GitHub/Jira: [Link to issue tracker]
- Include: Test output, environment details, error messages

---

## 📝 Contributing

### Updating Documentation

**After running tests**:
1. Update `MULTILINGUAL_TEST_RESULTS.md` with results
2. Update decision log with chosen approach
3. Update progress tracker as you implement

**After implementation**:
1. Document performance benchmarks
2. Add lessons learned
3. Update success metrics

**After rollout**:
1. Document user feedback
2. Update FAQ with common questions
3. Add tips for future maintainers

---

## 📜 Document History

| Date | Document | Change | Author |
|------|----------|--------|--------|
| 2026-01-16 | All | Initial creation | Claude Agent |
| | MULTILINGUAL_RETRIEVAL.md | Full technical spec | Claude Agent |
| | MULTILINGUAL_EXECUTIVE_SUMMARY.md | Business case | Claude Agent |
| | MULTILINGUAL_QUICK_START.md | Developer guide | Claude Agent |
| | MULTILINGUAL_TEST_RESULTS.md | Results template | Claude Agent |
| | test_multilingual_embeddings.py | API test script | Claude Agent |
| | test_graph_embeddings.py | Graph test script | Claude Agent |

---

## ✅ Quick Checklist

**Before starting**:
- [ ] Read MULTILINGUAL_QUICK_START.md (15 min)
- [ ] Verify environment variables set
- [ ] Ensure Neo4j is running
- [ ] Ensure OpenAI API key is valid

**Testing phase**:
- [ ] Run test_multilingual_embeddings.py
- [ ] Run test_graph_embeddings.py
- [ ] Document results in MULTILINGUAL_TEST_RESULTS.md
- [ ] Make decision on approach

**Implementation phase** (if approved):
- [ ] Create feature branch
- [ ] Implement chosen solution
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Code review
- [ ] Deploy to staging
- [ ] Validate with real queries
- [ ] Deploy to production (gradual rollout)
- [ ] Monitor metrics

**Post-launch**:
- [ ] Measure success metrics (4 weeks)
- [ ] Collect user feedback
- [ ] Document lessons learned
- [ ] Decide on Phase 2 (if applicable)

---

**Start here**: [`MULTILINGUAL_QUICK_START.md`](./MULTILINGUAL_QUICK_START.md)

**Questions?** Contact your team lead or check the FAQ above.

**Ready to test?** Run the scripts!

```bash
python test_multilingual_embeddings.py
python test_graph_embeddings.py
```

Good luck! 🚀
