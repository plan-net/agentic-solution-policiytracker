# RAG Evaluation Framework - Implementation Plan

**Date**: 2026-01-20
**Status**: Planning Complete - Ready for Implementation
**Owner**: Political Monitoring Team

---

## Executive Summary

### Problem Statement

The GraphRAG system currently lacks scientific, structured methods for assessing precision and recall of retrieval quality. While we have:
- ✅ Quality assessment system (8 dimensions)
- ✅ LangWatch observability (v0.5.0)
- ✅ Test infrastructure

We are missing:
- ❌ RAG-specific precision/recall metrics
- ❌ Context relevance scoring
- ❌ Systematic evaluation framework
- ❌ Ground truth evaluation datasets

### Recommended Solution

**Three-Phase Approach**:
1. **Phase 1 (Week 1)**: Enhance LangWatch with RAG data capture
2. **Phase 2 (Week 2)**: Integrate RAGAS framework for scientific evaluation
3. **Phase 3 (Week 3)**: Implement production monitoring and alerting

**Why RAGAS?**
- Industry-standard RAG evaluation framework
- LLM-as-judge approach (no manual labeling required)
- Proven metrics: faithfulness, context precision/recall, answer relevance
- Integrates with existing LangChain infrastructure

### Cost-Benefit Analysis

**Investment**:
- Timeline: 3 weeks (12 working days)
- Cost: $10-30/month ongoing
- Effort: 1 senior developer

**Returns**:
- Scientific measurement of RAG quality
- Early detection of retrieval degradation
- Data-driven optimization decisions
- Improved user satisfaction through quality monitoring

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Research Findings](#research-findings)
3. [Implementation Plan](#implementation-plan)
4. [Technical Details](#technical-details)
5. [Success Metrics](#success-metrics)
6. [Risk Mitigation](#risk-mitigation)
7. [Timeline and Milestones](#timeline-and-milestones)

---

## Current State Analysis

### Existing Infrastructure

#### 1. Quality Assessment System ✅

**Location**: `src/chat/agent/quality_assessment.py`

**Current Capabilities**:
- 8 quality dimensions evaluated
- Scores from 0-1.0 for each dimension
- LLM-based assessment

**Quality Dimensions**:
```python
class QualityDimension(Enum):
    COMPLETENESS = "completeness"        # Answer covers all aspects
    ACCURACY = "accuracy"                # Factual correctness
    RELEVANCE = "relevance"              # Addresses the query
    CLARITY = "clarity"                  # Clear and understandable
    COHERENCE = "coherence"              # Logical flow
    TIMELINESS = "timeliness"            # Up-to-date information
    ACTIONABILITY = "actionability"      # Provides actionable insights
    SOURCE_QUALITY = "source_quality"    # Reliable sources
```

**Gap**: No retrieval-specific metrics (precision, recall, context relevance)

#### 2. LangWatch Integration ✅

**Location**: `src/chat/observability/langwatch_config.py`

**Current Capabilities**:
- Session-level tracing (conversations tracked end-to-end)
- Tool call capture (all MCP tool invocations logged)
- Smart payload truncation (preserves critical fields, removes embeddings)
- REST API integration (sends data to LangWatch platform)

**Key Methods**:
```python
capture_tool_call_with_response()  # Track tool executions
capture_agentic_turn()             # Track agent loop iterations
@trace() decorator                 # Function-level tracing
```

**Gap**: Not capturing RAG-specific data (retrieved contexts, similarity scores, query-context pairs)

#### 3. GraphRAG Architecture ✅

**Components**:
- **Knowledge Graph**: Neo4j (31,129 entities, 53,772 relationships, 7,795 episodic nodes)
- **Embeddings**: text-embedding-ada-002 (100% migration complete)
- **Entity Extraction**: Graphiti temporal framework
- **Retrieval**: Vector similarity search + MCP Graph Retrieval server

**Gap**: No labeled ground truth data for evaluation

#### 4. Test Infrastructure ✅

**Location**: `/tests/` directory

**Current Tests**:
- Integration tests for GraphRAG pipeline
- Unit tests for individual components
- End-to-end workflow tests

**Gap**: No precision/recall measurement tests

### Critical Gap Summary

| Component | Current State | Gap | Priority |
|-----------|---------------|-----|----------|
| Quality Metrics | 8 dimensions (0-1 scores) | No precision/recall | 🔴 High |
| Observability | LangWatch integrated | No RAG context capture | 🔴 High |
| Ground Truth | None | No evaluation dataset | 🟡 Medium |
| Monitoring | Basic quality scores | No retrieval trends | 🟢 Low |

---

## Research Findings

### Framework Comparison

#### Option 1: RAGAS ⭐ **RECOMMENDED**

**Overview**:
- Open-source RAG evaluation framework
- LLM-as-judge approach (no manual labeling)
- Industry standard with extensive documentation

**Key Metrics**:

1. **Faithfulness/Groundedness** (0-1):
   - Measures if answer is supported by retrieved context
   - Detects hallucinations
   - Formula: `faithful_statements / total_statements`

2. **Answer Relevance** (0-1):
   - How well answer addresses the query
   - Penalizes irrelevant information
   - Uses question-answer semantic similarity

3. **Context Precision** (0-1):
   - Percentage of retrieved chunks that are actually relevant
   - Formula: `relevant_retrieved / total_retrieved`
   - Measures retrieval precision

4. **Context Recall** (0-1):
   - Percentage of relevant information that was retrieved
   - Formula: `relevant_retrieved / total_relevant`
   - Measures retrieval completeness

5. **Context Relevancy** (0-1):
   - Overall relevance of retrieved context to query
   - Considers all retrieved chunks

**Integration Example**:
```python
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall
)

# Evaluation dataset
dataset = {
    "question": ["What are GDPR penalties?", ...],
    "contexts": [[chunk1, chunk2], ...],
    "answer": ["GDPR penalties are...", ...],
    "ground_truth": ["Penalties up to €20M...", ...]
}

# Run evaluation
results = evaluate(
    dataset=dataset,
    metrics=[faithfulness, answer_relevancy, context_precision, context_recall]
)

print(results)
# {
#   'faithfulness': 0.85,
#   'answer_relevancy': 0.92,
#   'context_precision': 0.78,
#   'context_recall': 0.71
# }
```

**Benefits**:
- ✅ Purpose-built for RAG systems
- ✅ No labeled data required (LLM judges quality)
- ✅ Well-documented and actively maintained
- ✅ Integrates with LangChain (already in project)
- ✅ Supports custom metrics
- ✅ Proven in production at scale

**Challenges**:
- Requires evaluation dataset format (question, contexts, answer, ground_truth)
- LLM-as-judge adds latency and cost (~$0.01-0.05 per sample)
- Need representative evaluation samples (20-50 to start)

**Cost**:
- Development: Included in Phase 2 timeline
- Evaluation runs: $0.50-$2.50 per 50 samples
- Production sampling (5%): $5-20/month

#### Option 2: LangWatch Custom Evaluators

**Overview**:
- Extend existing LangWatch with custom RAG metrics
- Build on already-integrated infrastructure

**Approach**:
```python
from langwatch import Evaluator

class ContextPrecisionEvaluator(Evaluator):
    """Custom evaluator for context precision."""

    def evaluate(self, retrieved_contexts, query, ground_truth):
        # Custom logic to calculate precision
        relevant_count = 0
        for ctx in retrieved_contexts:
            if self.is_relevant(ctx, query):
                relevant_count += 1
        return relevant_count / len(retrieved_contexts)
```

**Benefits**:
- ✅ Already integrated (no new service)
- ✅ Real-time production monitoring
- ✅ No additional deployment complexity

**Challenges**:
- ❌ Need to implement metrics ourselves
- ❌ Less comprehensive than RAGAS out-of-box
- ❌ More development effort required

**Recommendation**: Use for Phase 1 (basic metrics), complement with RAGAS in Phase 2

#### Option 3: Alternative Frameworks

**TruLens** (https://www.trulens.org/):
- Focus: Explainability + RAG evaluation
- Metrics: Groundedness, answer relevance, context relevance
- Dashboard: Built-in visualization
- **Use Case**: If explainability is critical

**DeepEval** (https://github.com/confident-ai/deepeval):
- Similar to RAGAS (LLM-based)
- Metrics: Hallucination, relevance, faithfulness
- Integration: Pytest native
- **Use Case**: Secondary framework for hallucination detection

**Phoenix (Arize AI)** (https://phoenix.arize.com/):
- Focus: Real-time LLM tracing + evaluation
- Metrics: RAG-specific metrics
- Deployment: Open-source, self-hosted
- **Use Case**: If real-time tracing is priority

**LangSmith** (https://www.langchain.com/langsmith):
- Platform: LangChain's LLMOps
- Features: Datasets, metrics, monitoring
- Integration: Deep LangChain integration
- **Use Case**: If already using LangChain heavily

### Recommended Stack

**Primary**: RAGAS
- Comprehensive RAG metrics
- Industry standard
- LLM-as-judge approach

**Secondary**: LangWatch
- Real-time production monitoring
- Existing integration
- Custom evaluators for simple metrics

**Optional**: DeepEval
- Hallucination detection
- Pytest integration
- Complementary to RAGAS

---

## Implementation Plan

### Phase 1: LangWatch Enhancement (Week 1)

**Goal**: Capture RAG-specific data in existing observability infrastructure

**Effort**: 1-2 days
**Priority**: 🔴 IMMEDIATE
**Dependencies**: None

#### Actions

**1. Modify LangWatch Configuration**

**File**: `src/chat/observability/langwatch_config.py`

Changes:
- Add RAG context capture to `capture_agentic_turn()`
- Extend `capture_tool_call_with_response()` to log retrieval metadata
- Add custom spans for retrieval operations

```python
# Example: Enhanced context capture
def capture_retrieval_context(
    query: str,
    retrieved_entities: List[Dict],
    retrieved_relationships: List[Dict],
    similarity_scores: List[float]
):
    """Capture RAG retrieval data in LangWatch."""
    langwatch.capture_custom_event(
        event_type="rag_retrieval",
        data={
            "query": query,
            "num_entities": len(retrieved_entities),
            "num_relationships": len(retrieved_relationships),
            "avg_similarity": np.mean(similarity_scores),
            "min_similarity": min(similarity_scores),
            "max_similarity": max(similarity_scores)
        }
    )
```

**2. Create RAG Metrics Module**

**File**: `src/chat/observability/rag_metrics.py` (NEW)

Purpose: Simple precision/recall calculators for basic metrics

```python
"""RAG-specific quality metrics."""

from typing import List, Dict, Any
from dataclasses import dataclass
import numpy as np

@dataclass
class RAGMetrics:
    """RAG evaluation metrics."""
    context_precision: float
    context_recall: float
    context_relevancy: float
    retrieval_coverage: float
    avg_similarity: float

class RAGMetricsCalculator:
    """Calculate basic RAG quality metrics."""

    def calculate_context_precision(
        self,
        retrieved_contexts: List[str],
        relevant_contexts: List[str]
    ) -> float:
        """
        Calculate % of retrieved contexts that are relevant.

        Precision = relevant_retrieved / total_retrieved
        """
        if not retrieved_contexts:
            return 0.0

        relevant_count = sum(
            1 for ctx in retrieved_contexts
            if ctx in relevant_contexts
        )
        return relevant_count / len(retrieved_contexts)

    def calculate_context_recall(
        self,
        retrieved_contexts: List[str],
        relevant_contexts: List[str]
    ) -> float:
        """
        Calculate % of relevant contexts that were retrieved.

        Recall = relevant_retrieved / total_relevant
        """
        if not relevant_contexts:
            return 1.0  # No relevant contexts to retrieve

        retrieved_count = sum(
            1 for ctx in relevant_contexts
            if ctx in retrieved_contexts
        )
        return retrieved_count / len(relevant_contexts)

    def calculate_retrieval_coverage(
        self,
        query: str,
        retrieved_entities: List[Dict],
        retrieved_relationships: List[Dict]
    ) -> float:
        """
        Calculate coverage of knowledge graph retrieval.

        Coverage = entities_found + relationships_found
        """
        return len(retrieved_entities) + len(retrieved_relationships)

    def calculate_avg_similarity(
        self,
        similarity_scores: List[float]
    ) -> float:
        """Calculate average similarity score of retrieved items."""
        if not similarity_scores:
            return 0.0
        return np.mean(similarity_scores)
```

**3. Update Chat Agent**

**File**: `src/chat/agent/chat_agent.py`

Changes:
- Capture retrieved contexts before answering
- Log context-answer pairs to LangWatch
- Track retrieval similarity scores

```python
# Example integration
async def answer_question(self, query: str):
    # Retrieve contexts
    entities = await self.retrieve_entities(query)
    relationships = await self.retrieve_relationships(query)

    # Log retrieval data
    langwatch.capture_retrieval_context(
        query=query,
        retrieved_entities=entities,
        retrieved_relationships=relationships,
        similarity_scores=[e['similarity'] for e in entities]
    )

    # Generate answer
    answer = await self.generate_answer(query, entities, relationships)

    # Calculate basic metrics
    metrics = self.rag_calculator.calculate_metrics(
        retrieved=[e['name'] for e in entities],
        relevant=[]  # Will be populated in Phase 2
    )

    return answer, metrics
```

#### Deliverables

- ✅ Enhanced LangWatch traces with RAG data
- ✅ Basic precision/recall calculators
- ✅ Production monitoring for retrieval quality
- ✅ No performance degradation (<10ms overhead)

#### Verification

```bash
# Test enhanced logging
.venv/bin/python -m pytest tests/observability/test_rag_metrics.py

# Check LangWatch dashboard for new RAG events
# Visit: https://app.langwatch.ai/
```

---

### Phase 2: RAGAS Integration (Week 2)

**Goal**: Add scientific RAG evaluation with industry-standard framework

**Effort**: 2-3 days
**Priority**: 🔴 HIGH VALUE
**Dependencies**: Evaluation dataset creation

#### Actions

**1. Add Dependencies**

**File**: `pyproject.toml`

```toml
[project.optional-dependencies]
test = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "ragas>=0.1.0",           # RAG evaluation framework
    "deepeval>=0.21.0",       # Optional: hallucination detection
]
```

Install:
```bash
pip install ragas deepeval
# or
poetry add --group test ragas deepeval
```

**2. Create Evaluation Dataset**

**File**: `tests/evaluation/rag_evaluation_dataset.json` (NEW)

Format:
```json
{
  "samples": [
    {
      "question": "What are the main requirements of the Consumer Credit Directive?",
      "contexts": [
        "The Consumer Credit Directive requires financial services to provide consumers with better protection starting November 2026.",
        "Standard European Consumer Credit Information sheets must be provided to consumers under the new directive.",
        "Most third-party BNPL services will need to follow all CCD II rules, with limited exemptions for loans under €200."
      ],
      "answer": "The Consumer Credit Directive (CCD II) has several main requirements: (1) Financial services must provide better consumer protection starting November 2026, (2) Standard European Consumer Credit Information sheets must be provided to consumers, and (3) Most Buy-Now-Pay-Later services must comply with all rules, with limited exemptions for small loans under €200 or those paid within three months.",
      "ground_truth": "Main requirements include consumer protection measures effective November 2026, mandatory standardized credit information sheets, and regulation of BNPL services with limited exemptions for small loans."
    },
    {
      "question": "What are GDPR penalties for data breaches?",
      "contexts": [
        "GDPR Article 83 specifies administrative fines up to €20 million or 4% of annual global turnover, whichever is higher.",
        "Data breach notifications must be made to supervisory authorities within 72 hours under GDPR Article 33.",
        "Individuals affected by data breaches must be notified without undue delay when the breach is likely to result in high risk to their rights."
      ],
      "answer": "Under GDPR Article 83, penalties for data breaches can reach up to €20 million or 4% of annual global turnover, whichever is higher. Additionally, organizations must notify supervisory authorities within 72 hours of becoming aware of a breach (Article 33), and must inform affected individuals without undue delay if the breach poses high risk to their rights.",
      "ground_truth": "GDPR penalties for data breaches can be up to €20 million or 4% of global annual revenue, with mandatory notification to authorities within 72 hours and to affected individuals when high risk exists."
    }
  ]
}
```

**Dataset Creation Approaches**:

**Approach 1: Sample from Production** (Recommended)
1. Extract 50-100 real user queries from LangWatch
2. Manually annotate ground truth answers
3. Identify relevant contexts from actual retrievals

**Approach 2: Synthetic Dataset**
1. Create representative queries for key topics:
   - EU regulations (GDPR, DSA, AI Act, Consumer Credit Directive)
   - German political processes (Bundestag, Bundesrat)
   - Cross-lingual queries (English ↔ German)
2. Write ground truth answers based on documentation
3. Identify expected relevant entities/relationships

**Recommended Mix**: Start with 20-30 queries (60% production, 40% synthetic), expand to 100+ over time

**3. Create RAGAS Test Suite**

**File**: `tests/evaluation/test_rag_evaluation.py` (NEW)

```python
"""RAGAS-based RAG evaluation tests."""

import pytest
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
    context_relevancy
)
from tests.evaluation.dataset_loader import load_evaluation_dataset

@pytest.mark.evaluation
@pytest.mark.slow
def test_graphrag_precision_recall():
    """
    Test GraphRAG system precision and recall with RAGAS.

    This test evaluates the entire RAG pipeline:
    - Retrieval quality (context precision/recall)
    - Answer quality (faithfulness/relevancy)
    """
    # Load evaluation dataset
    dataset = load_evaluation_dataset("tests/evaluation/rag_evaluation_dataset.json")

    # Run RAGAS evaluation
    results = evaluate(
        dataset=dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
            context_relevancy
        ]
    )

    # Assert quality thresholds
    assert results['faithfulness'] >= 0.80, \
        "Answers must be grounded in retrieved context (no hallucinations)"

    assert results['context_precision'] >= 0.70, \
        "Retrieved contexts must be relevant to the query"

    assert results['context_recall'] >= 0.65, \
        "Must retrieve sufficient relevant context from knowledge graph"

    assert results['answer_relevancy'] >= 0.75, \
        "Answers must directly address the user's query"

    assert results['context_relevancy'] >= 0.70, \
        "Overall context relevance must be high"

    # Generate detailed report
    print(f"\n{'='*60}")
    print("RAG EVALUATION RESULTS")
    print(f"{'='*60}")
    for metric, score in results.items():
        status = "✅" if score >= 0.70 else "⚠️"
        print(f"{metric:<25}: {score:.3f} {status}")
    print(f"{'='*60}\n")

    return results


@pytest.mark.evaluation
def test_cross_lingual_rag_quality():
    """Test RAG quality for cross-lingual queries (English ↔ German)."""
    dataset = load_evaluation_dataset("tests/evaluation/cross_lingual_dataset.json")

    results = evaluate(
        dataset=dataset,
        metrics=[context_precision, context_recall]
    )

    # Cross-lingual retrieval should maintain quality
    assert results['context_precision'] >= 0.65, \
        "Cross-lingual retrieval precision must be maintained"

    assert results['context_recall'] >= 0.60, \
        "Cross-lingual retrieval recall must be maintained"

    return results
```

**File**: `tests/evaluation/dataset_loader.py` (NEW)

```python
"""Dataset loader for RAG evaluation."""

import json
from pathlib import Path
from typing import Dict, List
from datasets import Dataset

def load_evaluation_dataset(path: str) -> Dataset:
    """
    Load evaluation dataset from JSON file.

    Args:
        path: Path to JSON file with evaluation samples

    Returns:
        Dataset object compatible with RAGAS
    """
    with open(path, 'r') as f:
        data = json.load(f)

    samples = data['samples']

    # Convert to RAGAS format
    dataset = Dataset.from_dict({
        'question': [s['question'] for s in samples],
        'contexts': [s['contexts'] for s in samples],
        'answer': [s['answer'] for s in samples],
        'ground_truth': [s['ground_truth'] for s in samples]
    })

    return dataset
```

**4. Create Standalone Evaluation Script**

**File**: `scripts/evaluate_rag.py` (NEW)

```python
"""Standalone RAG evaluation script with RAGAS."""

import asyncio
import argparse
import json
from pathlib import Path
from datetime import datetime

from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
    context_relevancy
)
from tests.evaluation.dataset_loader import load_evaluation_dataset


async def evaluate_graphrag(
    dataset_path: str,
    output_path: str = None,
    metrics: List[str] = None
):
    """
    Run RAGAS evaluation on GraphRAG system.

    Args:
        dataset_path: Path to evaluation dataset JSON
        output_path: Optional path to save results
        metrics: Optional list of metrics to evaluate
    """
    print("="*80)
    print("RAG EVALUATION - GRAPHRAG SYSTEM")
    print("="*80)
    print(f"\nDataset: {dataset_path}")
    print(f"Timestamp: {datetime.now().isoformat()}\n")

    # Load dataset
    print("Loading evaluation dataset...")
    dataset = load_evaluation_dataset(dataset_path)
    print(f"  Loaded {len(dataset)} samples\n")

    # Define metrics
    if metrics is None:
        metrics_to_use = [
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
            context_relevancy
        ]
    else:
        # Map metric names to objects
        metric_map = {
            'faithfulness': faithfulness,
            'answer_relevancy': answer_relevancy,
            'context_precision': context_precision,
            'context_recall': context_recall,
            'context_relevancy': context_relevancy
        }
        metrics_to_use = [metric_map[m] for m in metrics]

    # Run evaluation
    print("Running RAGAS evaluation...")
    print(f"  Metrics: {[str(m) for m in metrics_to_use]}\n")

    results = evaluate(
        dataset=dataset,
        metrics=metrics_to_use
    )

    # Display results
    print("\n" + "="*80)
    print("EVALUATION RESULTS")
    print("="*80)

    for metric_name, score in results.items():
        threshold = 0.70  # Default threshold
        status = "✅ PASS" if score >= threshold else "❌ FAIL"
        print(f"{metric_name:<25}: {score:.3f} {status} (threshold: {threshold})")

    # Overall assessment
    avg_score = sum(results.values()) / len(results)
    overall_status = "✅ EXCELLENT" if avg_score >= 0.80 else \
                     "✓ GOOD" if avg_score >= 0.70 else \
                     "⚠️ NEEDS IMPROVEMENT"

    print(f"\nAverage Score: {avg_score:.3f} {overall_status}")
    print("="*80 + "\n")

    # Save results
    if output_path:
        output_data = {
            'timestamp': datetime.now().isoformat(),
            'dataset': dataset_path,
            'num_samples': len(dataset),
            'results': results,
            'average_score': avg_score
        }

        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)

        print(f"Results saved to: {output_path}\n")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Evaluate GraphRAG system with RAGAS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evaluate with default dataset
  python scripts/evaluate_rag.py

  # Evaluate specific dataset
  python scripts/evaluate_rag.py --dataset tests/evaluation/cross_lingual_dataset.json

  # Save results to file
  python scripts/evaluate_rag.py --output evaluation_results_20260120.json

  # Evaluate specific metrics only
  python scripts/evaluate_rag.py --metrics faithfulness context_precision
        """
    )

    parser.add_argument(
        "--dataset",
        default="tests/evaluation/rag_evaluation_dataset.json",
        help="Path to evaluation dataset JSON"
    )

    parser.add_argument(
        "--output",
        help="Path to save evaluation results"
    )

    parser.add_argument(
        "--metrics",
        nargs="+",
        choices=['faithfulness', 'answer_relevancy', 'context_precision',
                 'context_recall', 'context_relevancy'],
        help="Specific metrics to evaluate (default: all)"
    )

    args = parser.parse_args()

    asyncio.run(evaluate_graphrag(args.dataset, args.output, args.metrics))
```

#### Deliverables

- ✅ RAGAS integration in test suite
- ✅ Evaluation dataset (20+ queries)
- ✅ Automated tests with quality thresholds
- ✅ Standalone evaluation script
- ✅ Documentation and usage examples

#### Verification

```bash
# Run RAGAS evaluation tests
.venv/bin/python -m pytest tests/evaluation/test_rag_evaluation.py -v

# Run standalone evaluation
.venv/bin/python scripts/evaluate_rag.py --output results.json

# Check results
cat results.json | jq '.results'
```

---

### Phase 3: Production Monitoring (Week 3)

**Goal**: Continuous RAG quality monitoring in production

**Effort**: 2-3 days
**Priority**: 🟡 ONGOING
**Dependencies**: Phase 1 & 2 complete

#### Actions

**1. Create RAG Quality Monitor**

**File**: `src/chat/agent/rag_quality_monitor.py` (NEW)

```python
"""Real-time RAG quality monitoring."""

import asyncio
from typing import Dict, List
from datetime import datetime, timedelta

from ragas import evaluate
from ragas.metrics import faithfulness, context_precision, context_recall
from src.chat.observability.langwatch_config import langwatch


class RAGQualityMonitor:
    """Monitor RAG quality in production."""

    def __init__(
        self,
        sampling_rate: float = 0.05,  # Sample 5% of queries
        evaluation_interval: int = 3600  # Evaluate every hour
    ):
        self.sampling_rate = sampling_rate
        self.evaluation_interval = evaluation_interval
        self.query_buffer = []

    async def capture_query(
        self,
        query: str,
        contexts: List[str],
        answer: str,
        ground_truth: str = None
    ):
        """
        Capture query for evaluation.

        Args:
            query: User query
            contexts: Retrieved contexts
            answer: Generated answer
            ground_truth: Optional ground truth (if available)
        """
        # Sample queries based on sampling rate
        if random.random() < self.sampling_rate:
            self.query_buffer.append({
                'timestamp': datetime.now().isoformat(),
                'question': query,
                'contexts': contexts,
                'answer': answer,
                'ground_truth': ground_truth or "N/A"
            })

            # Log to LangWatch
            langwatch.capture_custom_event(
                event_type="rag_query_sampled",
                data={
                    'query': query,
                    'num_contexts': len(contexts),
                    'has_ground_truth': ground_truth is not None
                }
            )

    async def evaluate_buffer(self):
        """Evaluate buffered queries with RAGAS."""
        if len(self.query_buffer) < 10:
            return None  # Need at least 10 samples

        # Convert to RAGAS format
        dataset = Dataset.from_dict({
            'question': [q['question'] for q in self.query_buffer],
            'contexts': [q['contexts'] for q in self.query_buffer],
            'answer': [q['answer'] for q in self.query_buffer],
            'ground_truth': [q['ground_truth'] for q in self.query_buffer]
        })

        # Run evaluation
        results = evaluate(
            dataset=dataset,
            metrics=[faithfulness, context_precision, context_recall]
        )

        # Log results to LangWatch
        langwatch.capture_custom_event(
            event_type="rag_evaluation_batch",
            data={
                'num_samples': len(self.query_buffer),
                'results': results,
                'timestamp': datetime.now().isoformat()
            }
        )

        # Check for degradation
        if results['faithfulness'] < 0.75:
            self._alert_quality_degradation('faithfulness', results['faithfulness'])

        if results['context_precision'] < 0.65:
            self._alert_quality_degradation('context_precision', results['context_precision'])

        # Clear buffer
        self.query_buffer.clear()

        return results

    def _alert_quality_degradation(self, metric: str, score: float):
        """Alert when quality drops below threshold."""
        print(f"⚠️ ALERT: {metric} dropped to {score:.3f}")

        # Send alert via LangWatch
        langwatch.capture_custom_event(
            event_type="rag_quality_alert",
            data={
                'metric': metric,
                'score': score,
                'threshold_breached': True,
                'timestamp': datetime.now().isoformat()
            },
            level="warning"
        )

    async def start_monitoring(self):
        """Start continuous monitoring loop."""
        while True:
            await asyncio.sleep(self.evaluation_interval)
            await self.evaluate_buffer()
```

**2. Integrate with Chat Agent**

**File**: `src/chat/agent/chat_agent.py`

```python
# Add to chat agent
from src.chat.agent.rag_quality_monitor import RAGQualityMonitor

class ChatAgent:
    def __init__(self):
        # ... existing init ...
        self.quality_monitor = RAGQualityMonitor(
            sampling_rate=0.05,  # 5% sampling
            evaluation_interval=3600  # Hourly evaluation
        )

        # Start monitoring in background
        asyncio.create_task(self.quality_monitor.start_monitoring())

    async def answer_question(self, query: str):
        # ... retrieve contexts ...
        # ... generate answer ...

        # Capture for quality monitoring
        await self.quality_monitor.capture_query(
            query=query,
            contexts=retrieved_contexts,
            answer=answer,
            ground_truth=None  # Optional
        )

        return answer
```

**3. Create Dashboards**

**Dashboard Requirements**:
- Precision/recall trends over time
- Quality by query type (simple, complex, cross-lingual)
- Alert on degradation
- Comparison before/after changes

**Implementation**: Use LangWatch dashboard + custom views

#### Deliverables

- ✅ Production RAG quality monitoring
- ✅ Real-time dashboards in LangWatch
- ✅ Automated quality alerts
- ✅ Weekly evaluation reports

#### Verification

```bash
# Check monitoring is running
curl http://localhost:8000/health/rag-monitor

# Trigger manual evaluation
curl -X POST http://localhost:8000/admin/evaluate-rag

# View dashboard
open https://app.langwatch.ai/dashboard/rag-quality
```

---

## Technical Details

### Evaluation Dataset Format

**Required Fields**:
```json
{
  "samples": [
    {
      "question": "string",      // User query
      "contexts": ["string"],    // Retrieved chunks/contexts
      "answer": "string",        // Generated answer
      "ground_truth": "string"   // Expected answer (optional for some metrics)
    }
  ]
}
```

**Best Practices**:
1. **Diverse Query Types**: Include simple, complex, and edge cases
2. **Cross-lingual Coverage**: Test English ↔ German queries
3. **Domain Coverage**: Cover all major topics (regulations, politics, economics)
4. **Quality Over Quantity**: Start with 20-30 high-quality samples
5. **Regular Updates**: Add new samples based on production queries

### Files to Create

```
/Users/mangeshkarangutkar/Documents/Agentic_AI/policiytracker-agentic-solution/agentic-solution-policiytracker/
├── src/
│   └── chat/
│       ├── agent/
│       │   └── rag_quality_monitor.py          (NEW - Phase 3)
│       └── observability/
│           └── rag_metrics.py                   (NEW - Phase 1)
├── tests/
│   └── evaluation/
│       ├── rag_evaluation_dataset.json         (NEW - Phase 2)
│       ├── cross_lingual_dataset.json          (NEW - Phase 2)
│       ├── dataset_loader.py                   (NEW - Phase 2)
│       └── test_rag_evaluation.py              (NEW - Phase 2)
└── scripts/
    └── evaluate_rag.py                          (NEW - Phase 2)
```

### Files to Modify

```
/Users/mangeshkarangutkar/Documents/Agentic_AI/policiytracker-agentic-solution/agentic-solution-policiytracker/
├── pyproject.toml                               (ADD ragas, deepeval)
├── src/
│   └── chat/
│       ├── agent/
│       │   └── chat_agent.py                    (ADD monitoring integration)
│       └── observability/
│           └── langwatch_config.py              (ADD RAG context capture)
└── README.md                                    (ADD evaluation documentation)
```

---

## Success Metrics

### Phase 1 Success Criteria

- ✅ RAG data captured in all production queries
- ✅ Basic precision/recall visible in LangWatch dashboard
- ✅ No performance degradation (<10ms overhead)
- ✅ 100% test coverage for new metrics module

**Verification**:
```bash
# Check LangWatch captures RAG data
grep "rag_retrieval" logs/langwatch.log | wc -l

# Verify performance
pytest tests/performance/test_rag_metrics_overhead.py
```

### Phase 2 Success Criteria

- ✅ Evaluation dataset with ≥20 queries
- ✅ RAGAS tests passing with thresholds:
  - Faithfulness ≥ 0.80
  - Context Precision ≥ 0.70
  - Context Recall ≥ 0.65
  - Answer Relevance ≥ 0.75
- ✅ Automated test runs in CI/CD
- ✅ Evaluation script generates reports

**Verification**:
```bash
# Run RAGAS tests
pytest tests/evaluation/test_rag_evaluation.py -v

# Check CI/CD integration
cat .github/workflows/test.yml | grep ragas

# Generate report
python scripts/evaluate_rag.py --output report.json
```

### Phase 3 Success Criteria

- ✅ Real-time quality metrics in dashboard
- ✅ Alerts on quality degradation
- ✅ Weekly evaluation reports
- ✅ Monitoring overhead <1% of requests

**Verification**:
```bash
# Check monitoring is active
curl http://localhost:8000/health/rag-monitor

# Verify alerts working
python scripts/simulate_quality_drop.py

# Check dashboard
open https://app.langwatch.ai/dashboard/rag-quality
```

### Quality Thresholds

| Metric | Threshold | Current | Target |
|--------|-----------|---------|--------|
| Faithfulness | ≥0.80 | TBD | 0.85+ |
| Context Precision | ≥0.70 | TBD | 0.75+ |
| Context Recall | ≥0.65 | TBD | 0.70+ |
| Answer Relevance | ≥0.75 | TBD | 0.80+ |
| Context Relevancy | ≥0.70 | TBD | 0.75+ |

---

## Risk Mitigation

### Risk 1: Lack of Ground Truth Data

**Impact**: Cannot measure absolute accuracy without labeled data

**Likelihood**: 🔴 High (no ground truth currently exists)

**Mitigations**:
1. Use LLM-as-judge (RAGAS) for relative quality assessment
2. Start with small dataset (20 queries) and expand iteratively
3. Sample from production logs for realistic queries
4. Crowdsource ground truth from domain experts

**Contingency**: If ground truth creation is blocked, focus on comparative evaluation (before/after changes)

### Risk 2: LLM-as-Judge Reliability

**Impact**: Evaluation quality depends on judge LLM accuracy

**Likelihood**: 🟡 Medium (judge LLMs can make mistakes)

**Mitigations**:
1. Use high-quality judge LLM (GPT-4 or Claude Opus)
2. Spot-check judge decisions manually (10% sample)
3. Refine prompts based on edge cases
4. Compare multiple judges for critical evaluations

**Contingency**: Supplement LLM-as-judge with simple heuristic metrics (exact match, keyword overlap)

### Risk 3: Evaluation Dataset Representativeness

**Impact**: Metrics may not reflect real user experience

**Likelihood**: 🟡 Medium (synthetic data differs from production)

**Mitigations**:
1. Sample queries from production logs (60% production, 40% synthetic)
2. Include diverse query types (simple, complex, cross-lingual)
3. Regular dataset updates based on user feedback
4. A/B test changes in production before rolling out

**Contingency**: Run parallel evaluation on both synthetic and production-sampled datasets

### Risk 4: Performance Impact

**Impact**: RAG evaluation adds latency to production

**Likelihood**: 🟢 Low (async evaluation, sampling)

**Mitigations**:
1. Run evaluations asynchronously (non-blocking)
2. Sample only 5-10% of production queries
3. Batch evaluation (hourly, not per-query)
4. Use faster evaluation models when possible

**Contingency**: Reduce sampling rate or evaluation frequency if performance issues arise

### Risk 5: Cost Overruns

**Impact**: LLM-as-judge evaluation costs exceed budget

**Likelihood**: 🟢 Low (estimated $10-30/month)

**Mitigations**:
1. Set monthly cost caps in evaluation service
2. Use cheaper models for non-critical evaluations
3. Reduce sampling rate if costs increase
4. Cache evaluation results for identical queries

**Contingency**: Fall back to Phase 1 basic metrics if RAGAS costs are prohibitive

---

## Timeline and Milestones

### Week 1: LangWatch Enhancement

| Day | Task | Deliverable | Owner |
|-----|------|-------------|-------|
| 1 | Implement RAG context capture | `rag_metrics.py` | Developer |
| 1-2 | Modify LangWatch config | Enhanced logging | Developer |
| 2 | Update chat agent integration | Context capture in agent | Developer |
| 3 | Write tests for metrics module | Test suite | Developer |
| 3 | Deploy to staging | Staging deployment | DevOps |
| 4 | Verify in production | LangWatch dashboard | Developer |
| 4 | Document Phase 1 changes | Documentation | Developer |

**Milestone**: ✅ RAG data visible in LangWatch dashboard

---

### Week 2: RAGAS Integration

| Day | Task | Deliverable | Owner |
|-----|------|-------------|-------|
| 5 | Add RAGAS dependencies | `pyproject.toml` | Developer |
| 5-6 | Create evaluation dataset | 20+ query dataset | Team |
| 6 | Implement dataset loader | `dataset_loader.py` | Developer |
| 6-7 | Write RAGAS test suite | `test_rag_evaluation.py` | Developer |
| 7 | Create standalone script | `evaluate_rag.py` | Developer |
| 8 | Run baseline evaluation | Baseline metrics | Developer |
| 8 | Define quality thresholds | Threshold documentation | Team |
| 8 | Integrate into CI/CD | GitHub Actions | DevOps |

**Milestone**: ✅ RAGAS evaluation running in CI/CD

---

### Week 3: Production Monitoring

| Day | Task | Deliverable | Owner |
|-----|------|-------------|-------|
| 9 | Implement quality monitor | `rag_quality_monitor.py` | Developer |
| 9-10 | Integrate with chat agent | Production integration | Developer |
| 10 | Set up alerting | Alert rules | Developer |
| 10-11 | Create LangWatch dashboards | Custom dashboards | Developer |
| 11 | Deploy monitoring to production | Production deployment | DevOps |
| 12 | Test alert system | Simulated quality drop | Developer |
| 12 | Documentation and handoff | Final documentation | Developer |

**Milestone**: ✅ Production monitoring active with alerting

---

### Overall Timeline

```
Week 1: LangWatch Enhancement          [████████████████████] 100%
Week 2: RAGAS Integration              [████████████████████] 100%
Week 3: Production Monitoring          [████████████████████] 100%
                                        └─────── 3 weeks ──────┘
```

**Total Duration**: 3 weeks (15 working days)
**Team Size**: 1 senior developer (with DevOps support for deployments)

---

## Cost Analysis

### Development Costs

| Phase | Effort | Rate | Cost |
|-------|--------|------|------|
| Phase 1 | 2 days | - | Included in sprint |
| Phase 2 | 3 days | - | Included in sprint |
| Phase 3 | 3 days | - | Included in sprint |
| **Total** | **8 days** | - | **1 sprint** |

### Operational Costs (Monthly)

| Component | Usage | Unit Cost | Monthly Cost |
|-----------|-------|-----------|--------------|
| RAGAS Evaluations | 50 samples/run | $0.01-0.05/sample | $0.50-$2.50/run |
| Production Sampling | 5% of queries | $0.01/sample | $5-20/month |
| LangWatch Storage | +10-20% data | Included | $0 |
| Additional Infrastructure | - | - | $0 |
| **Total** | - | - | **$10-30/month** |

### Cost Breakdown

**Scenario 1: Low Usage** (100 queries/day)
- Sampled queries: 5/day × 30 days = 150/month
- Cost: ~$10/month

**Scenario 2: Medium Usage** (500 queries/day)
- Sampled queries: 25/day × 30 days = 750/month
- Cost: ~$20/month

**Scenario 3: High Usage** (1000 queries/day)
- Sampled queries: 50/day × 30 days = 1,500/month
- Cost: ~$30/month

**Cost Controls**:
1. Adjustable sampling rate (default: 5%)
2. Batch evaluation (reduces API calls)
3. Caching for identical queries
4. Monthly spending caps

---

## Next Steps

### Immediate Actions (This Week)

1. **Get Approval**: Review this plan with stakeholders
2. **Assign Resources**: Allocate 1 senior developer for 3 weeks
3. **Set Up Environment**: Install RAGAS dependencies
4. **Create Dataset Template**: Start collecting evaluation queries

### Week 1 Kickoff

1. **Day 1 Morning**: Kickoff meeting with developer
2. **Day 1 Afternoon**: Begin Phase 1 implementation
3. **Day 2-3**: Complete Phase 1
4. **Day 4**: Deploy Phase 1 to production
5. **Day 5**: Begin Phase 2

### Questions to Resolve

1. **Dataset Creation**: Who will create/annotate the evaluation dataset?
2. **Quality Thresholds**: What are acceptable threshold ranges for our use case?
3. **Alerting**: Who should receive quality degradation alerts?
4. **Budget**: Is $10-30/month operational cost acceptable?

---

## Appendix

### A. Related Documentation

- [Multilingual Search Verification Report](MULTILINGUAL_SEARCH_VERIFICATION_REPORT.md)
- [Consumer Credit Directive Findings](CONSUMER_CREDIT_DIRECTIVE_FINDINGS.md)
- [Quality Assessment System](src/chat/agent/quality_assessment.py)
- [LangWatch Configuration](src/chat/observability/langwatch_config.py)

### B. References

- **RAGAS Documentation**: https://docs.ragas.io/
- **LangWatch Documentation**: https://docs.langwatch.ai/
- **DeepEval Documentation**: https://docs.confident-ai.com/
- **TruLens Documentation**: https://www.trulens.org/docs/

### C. Glossary

- **RAG**: Retrieval-Augmented Generation
- **LLM-as-judge**: Using a language model to evaluate outputs
- **Faithfulness**: Answer grounded in retrieved context
- **Context Precision**: % of retrieved contexts that are relevant
- **Context Recall**: % of relevant contexts that were retrieved
- **Hallucination**: Generated information not supported by context

---

**Document Version**: 1.0
**Last Updated**: 2026-01-20
**Author**: Claude (Anthropic)
**Reviewers**: [To be assigned]
**Approval Status**: ⏳ Pending
