# Entity Deduplication Strategy

**Version**: 1.0
**Status**: Phase 1 Implemented
**Last Updated**: 2025-11-25

## Executive Summary

This document outlines the comprehensive deduplication strategy for the Political Monitoring Agent's Neo4j knowledge graph. The strategy addresses duplicate entity creation across two ingestion approaches:

1. **Bundestag DIP Flow**: Structured data from German parliament API (lower duplication risk)
2. **Markdown Processing Flow**: Unstructured documents via Graphiti LLM extraction (higher duplication risk)

The strategy employs a **two-pronged approach**:
- **Prevention**: Entity name normalization before LLM extraction (~40% reduction in obvious duplicates)
- **Cleanup**: Post-processing consolidation using fuzzy string matching (addresses remaining duplicates)

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Architecture Overview](#architecture-overview)
3. [Phase 1: Quick Wins (Implemented)](#phase-1-quick-wins-implemented)
4. [EntityNormalizer Usage Guide](#entitynormalizer-usage-guide)
5. [Consolidation Script Guide](#consolidation-script-guide)
6. [Metrics and Monitoring](#metrics-and-monitoring)
7. [Phase 2 Roadmap](#phase-2-roadmap)
8. [Troubleshooting](#troubleshooting)

## Problem Statement

### Duplication Sources

**Markdown Processing Flow (High Risk)**:
- Same entity with name variations: "EU Commission" vs "European Commission"
- Abbreviations vs full forms: "GDPR" vs "General Data Protection Regulation"
- Cross-document duplication: Same entity mentioned in multiple documents
- Within-document chunk duplication: Same entity in multiple chunks of one document

**Bundestag DIP Flow (Low Risk)**:
- Already uses Neo4j MERGE operations with unique constraints
- Structured data with consistent naming
- Minimal deduplication needed (handled by existing upsert logic)

### Impact of Duplicates

- **Fragmented Knowledge**: Same entity appears as multiple disconnected nodes
- **Incomplete Relationships**: Relationships scattered across duplicate nodes
- **Degraded Search**: Search results show multiple copies of same entity
- **Increased Storage**: Unnecessary data redundancy
- **Analysis Errors**: Entity counts and metrics inflated

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   DEDUPLICATION STRATEGY                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────────────────────────────────────────┐    │
│  │         PREVENTION (Phase 1)                      │    │
│  ├───────────────────────────────────────────────────┤    │
│  │  1. EntityNormalizer (Pre-Processing)             │    │
│  │     - Abbreviation expansion (35 mappings)        │    │
│  │     - Whitespace normalization                    │    │
│  │     - Possessive normalization                    │    │
│  │     └─> Applied before Graphiti LLM extraction    │    │
│  │                                                    │    │
│  │  2. Enhanced DocumentTracker                      │    │
│  │     - Entity name hashing                         │    │
│  │     - Duplicate detection statistics              │    │
│  │     - Cross-document similarity analysis          │    │
│  └───────────────────────────────────────────────────┘    │
│                          ↓                                 │
│  ┌───────────────────────────────────────────────────┐    │
│  │         CLEANUP (Phase 1)                         │    │
│  ├───────────────────────────────────────────────────┤    │
│  │  3. Consolidation Script (Post-Processing)        │    │
│  │     - Levenshtein similarity matching (≥0.85)     │    │
│  │     - Relationship transfer                       │    │
│  │     - Safe duplicate removal                      │    │
│  │     - Weekly automated runs via Airflow           │    │
│  └───────────────────────────────────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Phase 1: Quick Wins (Implemented)

### 1. Entity Name Normalization

**File**: `src/flows/data_ingestion/entity_normalizer.py`

**Purpose**: Standardize entity mentions in documents before Graphiti LLM extraction to prevent duplicate creation.

**Key Features**:
- 35 pre-configured abbreviation mappings for political/regulatory domain
- Regex-based pattern matching with word boundaries
- Configurable normalization options
- Real-time statistics tracking

**Integration Point**: Applied in `document_processor.py` after preprocessing and before Graphiti extraction.

### 2. Document Tracking Enhancements

**File**: `src/flows/data_ingestion/document_tracker.py`

**Enhancements**:
- Entity name hashing (SHA-256) for duplicate detection
- Unique entity count tracking per document
- Cross-document similarity analysis methods
- Deduplication statistics API

**Use Cases**:
- Identify documents with similar entity sets
- Track duplicate reduction over time
- Analyze within-document vs cross-document duplicates

### 3. Post-Processing Consolidation

**File**: `scripts/consolidate_duplicate_entities.py`

**Purpose**: Find and merge duplicate entities that were created despite normalization.

**Key Features**:
- Levenshtein distance-based matching (default threshold: 0.85)
- Safe relationship transfer before deletion
- Dry-run mode for preview
- Rich CLI with progress bars and formatted tables
- Automated weekly runs via Airflow DAG

## EntityNormalizer Usage Guide

### Basic Usage

```python
from src.flows.data_ingestion.entity_normalizer import EntityNormalizer

# Initialize with default settings
normalizer = EntityNormalizer()

# Normalize document text
original_text = "The EU Commission announced new GDPR enforcement actions."
normalized_text = normalizer.normalize_text(original_text)
# Result: "The European Commission announced new General Data Protection Regulation enforcement actions."
```

### Configuration Options

```python
# Custom initialization
normalizer = EntityNormalizer(
    custom_mappings={"BfDI": "Federal Commissioner for Data Protection"},  # Add custom mappings
    enable_abbreviation_expansion=True,      # Expand abbreviations (default: True)
    enable_whitespace_normalization=True,    # Clean whitespace (default: True)
    enable_possessive_normalization=True,    # Normalize possessives (default: True)
    case_sensitive=False,                    # Case-sensitive matching (default: False)
)
```

### Adding Custom Mappings at Runtime

```python
normalizer = EntityNormalizer()

# Add domain-specific mapping
normalizer.add_custom_mapping(
    abbreviation="BfDI",
    full_form="Federal Commissioner for Data Protection and Freedom of Information"
)

# Use updated normalizer
text = "BfDI announced new guidelines."
normalized = normalizer.normalize_text(text)
# Result: "Federal Commissioner for Data Protection and Freedom of Information announced new guidelines."
```

### Getting Normalization Statistics

```python
text = "The EU and U.S. agreed on GDPR adequacy. The DSA affects Meta and Google."

stats = normalizer.get_statistics(text)
print(stats)
# Output:
# {
#     "total_abbreviations": 5,
#     "excessive_whitespace_count": 0,
#     "abbreviation_counts": {
#         "EU": 1,
#         "U.S.": 1,
#         "GDPR": 1,
#         "DSA": 1,
#         "Meta": 1  # Note: "Meta" might map to "Facebook" depending on configuration
#     }
# }
```

### Pre-Configured Abbreviation Mappings

**European Union**:
- EU → European Union
- E.U. → European Union
- EU Commission → European Commission
- EC → European Commission

**United States**:
- US → United States
- U.S. → United States
- USA → United States

**United Kingdom**:
- UK → United Kingdom
- U.K. → United Kingdom

**EU Institutions**:
- EP → European Parliament
- ECJ → European Court of Justice
- EDPB → European Data Protection Board
- EDPS → European Data Protection Supervisor

**German Entities**:
- BT → Bundestag
- BR → Bundesrat
- BVerfG → Bundesverfassungsgericht
- SPD → Social Democratic Party
- CDU → Christian Democratic Union
- CSU → Christian Social Union
- FDP → Free Democratic Party

**Regulations**:
- GDPR → General Data Protection Regulation
- DSA → Digital Services Act
- DMA → Digital Markets Act
- AI Act → Artificial Intelligence Act

**Companies**:
- Meta Platforms → Meta
- Facebook → Meta
- Google LLC → Google
- Alphabet Inc. → Google
- Amazon.com → Amazon
- Microsoft Corp. → Microsoft
- Apple Inc. → Apple

### Testing Normalization

```python
# Test with sample political text
test_text = """
The EU Commission announced that the DSA and DMA will be enforced starting 2024.
Meta and Google must comply with GDPR requirements.
The BT and BR approved the transposition law.
"""

normalizer = EntityNormalizer()
normalized = normalizer.normalize_text(test_text)

print("Original:", test_text)
print("\nNormalized:", normalized)
print("\nStats:", normalizer.get_statistics(test_text))
```

### Best Practices

1. **Always normalize before LLM extraction**: Apply normalization as the last step of preprocessing
2. **Monitor statistics**: Track normalization stats to identify new abbreviation patterns
3. **Custom mappings for domain-specific terms**: Add client-specific abbreviations
4. **Case-insensitive by default**: Most abbreviations should be case-insensitive
5. **Preserve context**: Normalization should not change meaning (e.g., "AI" in "AI Act" vs "AI" as standalone term)

### Integration with Document Processor

The EntityNormalizer is automatically integrated into the document processing pipeline:

```python
# In src/flows/data_ingestion/document_processor.py
def _read_document(self, doc_path: Path) -> str:
    # 1. Read with encoding detection
    # 2. Apply preprocessing (link removal, deduplication)
    preprocessed = preprocess_document(content, enable_link_removal=True)

    # 3. Apply entity normalization (AUTOMATIC)
    normalized = self.entity_normalizer.normalize_text(preprocessed)

    # 4. Log statistics
    norm_stats = self.entity_normalizer.get_statistics(preprocessed)
    if norm_stats["total_abbreviations"] > 0:
        logger.info(f"Normalized {norm_stats['total_abbreviations']} abbreviations")

    return normalized
```

## Consolidation Script Guide

### Overview

The consolidation script (`scripts/consolidate_duplicate_entities.py`) finds and merges duplicate entities using fuzzy string matching.

### Prerequisites

**APOC Plugin Required**: The script uses `apoc.text.levenshteinSimilarity()` for fuzzy matching.

Verify APOC is installed:
```bash
docker exec -it neo4j cypher-shell -u neo4j -p password123 \
  "RETURN apoc.version() AS version;"
```

If APOC is missing, add to docker-compose.yml:
```yaml
neo4j:
  environment:
    - NEO4J_PLUGINS=["apoc"]
```

### Command-Line Usage

**Dry Run (Preview Only)**:
```bash
python scripts/consolidate_duplicate_entities.py --dry-run
```

**Live Consolidation (Default)**:
```bash
python scripts/consolidate_duplicate_entities.py
# Will prompt for confirmation before merging
```

**Automated Mode (No Confirmation)**:
```bash
AUTO_CONFIRM=true python scripts/consolidate_duplicate_entities.py
```

**Custom Similarity Threshold**:
```bash
# Default is 0.85, increase for stricter matching
python scripts/consolidate_duplicate_entities.py --similarity 0.90

# Decrease for looser matching (use with caution)
python scripts/consolidate_duplicate_entities.py --similarity 0.80
```

**Filter by Entity Types**:
```bash
python scripts/consolidate_duplicate_entities.py --entity-types Policy,Regulation,Politician
```

### Understanding Similarity Scores

**Levenshtein Similarity Scale**:
- **1.0**: Identical strings
- **0.90-0.99**: Very similar (minor typos, capitalization differences)
- **0.85-0.89**: Similar (abbreviation variations, minor word differences)
- **0.70-0.84**: Moderately similar (could be duplicates or different entities)
- **<0.70**: Likely different entities

**Examples**:
```
"European Commission" vs "European Commision"  → 0.98 (typo)
"EU Commission" vs "European Commission"       → 0.76 (abbreviation)
"Digital Services Act" vs "Digital Service Act" → 0.98 (plural)
"Meta" vs "Facebook"                           → 0.33 (different)
```

**Recommended Thresholds**:
- **0.85**: Good balance (default)
- **0.90**: Very safe, catches only obvious duplicates
- **0.80**: More aggressive, requires manual review

### Output Interpretation

**Dry Run Output Example**:
```
╭───────────────────────────────────────────────────────────────╮
│            🔍 Duplicate Entity Consolidation Report           │
├───────────────────────────────────────────────────────────────┤
│  Mode: DRY RUN (no changes will be made)                     │
│  Similarity Threshold: 0.85                                   │
│  Neo4j Database: politicalmonitoring.v3                       │
╰───────────────────────────────────────────────────────────────╯

Finding duplicate pairs...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%

Found 15 potential duplicate pairs:

┏━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Entity 1                 ┃ Entity 2                 ┃ Similarity ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ European Commission      │ European Commision       │ 0.98       │
│ Digital Services Act     │ Digital Service Act      │ 0.98       │
│ General Data Protection… │ GDPR                     │ 0.87       │
│ Meta Platforms           │ Meta                     │ 0.92       │
└──────────────────────────┴──────────────────────────┴────────────┘

Would merge 15 duplicate entities
```

**Live Run Output Example**:
```
Proceed with consolidation? [y/N]: y

Consolidating duplicates...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%

✅ Consolidation Complete!

┏━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Metric                    ┃ Value   ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━┩
│ Duplicates Found          │ 15      │
│ Successfully Merged       │ 15      │
│ Failed Merges             │ 0       │
│ Relationships Transferred │ 127     │
│ Entities Removed          │ 15      │
└───────────────────────────┴─────────┘
```

### Manual Review Workflow

**Step 1: Dry Run to Generate Report**
```bash
python scripts/consolidate_duplicate_entities.py --dry-run > /tmp/dedup_report.txt
```

**Step 2: Review Duplicate Pairs**
- Check each pair manually
- Verify they are truly duplicates
- Note any false positives

**Step 3: Adjust Threshold if Needed**
```bash
# If too many false positives, increase threshold
python scripts/consolidate_duplicate_entities.py --similarity 0.90 --dry-run
```

**Step 4: Run Live Consolidation**
```bash
python scripts/consolidate_duplicate_entities.py
# Review and confirm
```

### What Happens During Consolidation

**For each duplicate pair**:
1. **Identify Canonical Entity**: The entity with the most relationships is kept
2. **Transfer Relationships**: All relationships from duplicate are transferred to canonical
3. **Transfer Properties**: Properties from duplicate are merged (if not conflicting)
4. **Delete Duplicate**: Duplicate entity is removed
5. **Log Transaction**: Action is logged for audit trail

**Example Transaction**:
```cypher
// Before:
(e1:Entity {name: "European Commission", uuid: "abc123"})
(e2:Entity {name: "European Commision", uuid: "def456"})  // Typo
(e2)-[:ENFORCES]->(p:Policy)

// After consolidation:
(e1:Entity {name: "European Commission", uuid: "abc123"})
(e1)-[:ENFORCES]->(p:Policy)  // Relationship transferred
// e2 deleted
```

### Error Handling

**APOC Not Installed**:
```
❌ Error: APOC plugin is not installed
Install APOC and restart Neo4j before running consolidation.
```

**Neo4j Connection Failed**:
```
❌ Error: Failed to connect to Neo4j at bolt://localhost:7687
Check that Neo4j is running and credentials are correct.
```

**Merge Failed**:
- Script will log the error and continue with remaining pairs
- Failed merges are tracked in statistics
- Review logs in `/tmp/consolidation_errors.log`

### Automated Scheduling

The consolidation script is scheduled to run weekly via Airflow DAG (see next section).

**Manual Trigger**:
```bash
# Trigger Airflow DAG manually
airflow dags trigger entity_deduplication_weekly
```

## Metrics and Monitoring

### DocumentTracker Metrics

**Get Overall Deduplication Stats**:
```python
from src.flows.data_ingestion.document_tracker import DocumentTracker

tracker = DocumentTracker()
stats = tracker.get_duplicate_detection_stats()

print(stats)
# Output:
# {
#     "documents_with_entity_tracking": 150,
#     "total_entities_extracted": 3500,
#     "total_unique_entities_in_docs": 2800,
#     "within_document_duplicate_rate": 20.0,  # 20% duplicates within documents
#     "estimated_cross_document_duplicates": "Manual analysis required"
# }
```

**Find Similar Documents**:
```python
# Find documents with similar entity sets
entity_names = ["European Commission", "GDPR", "Meta", "Digital Services Act"]

similar_docs = tracker.find_similar_documents(
    entity_names=entity_names,
    similarity_threshold=0.5  # 50% Jaccard similarity
)

for doc in similar_docs:
    print(f"Document: {doc['path']}")
    print(f"  Entity Count: {doc['entity_count']}")
    print(f"  Similarity: {doc['similarity_score']:.2%}")
    print(f"  Hash: {doc['entity_names_hash']}")
```

**Track Processing Stats**:
```python
stats = tracker.get_stats()
print(stats)
# Output:
# {
#     "total_processed": 150,
#     "completed": 148,
#     "failed": 2,
#     "success_rate": 98.67,
#     "total_entities": 3500,
#     "total_relationships": 8200
# }
```

### Consolidation Metrics

**Track Duplicate Reduction Over Time**:
```python
import json
from datetime import datetime

# Log consolidation results
consolidation_results = {
    "timestamp": datetime.now().isoformat(),
    "duplicates_found": 15,
    "duplicates_merged": 15,
    "relationships_transferred": 127,
    "entities_removed": 15
}

# Save to metrics file
with open("data/metrics/deduplication_history.jsonl", "a") as f:
    f.write(json.dumps(consolidation_results) + "\n")
```

**Calculate Duplicate Reduction Rate**:
```python
# Before consolidation
query_before = "MATCH (e:Entity) RETURN count(e) AS total"
entities_before = 1200

# After consolidation
query_after = "MATCH (e:Entity) RETURN count(e) AS total"
entities_after = 1150

reduction_rate = (entities_before - entities_after) / entities_before * 100
print(f"Duplicate Reduction: {reduction_rate:.2f}%")  # 4.17%
```

### Neo4j Query Metrics

**Count Entities by Type**:
```cypher
MATCH (e:Entity)
RETURN labels(e)[0] AS entity_type, count(e) AS count
ORDER BY count DESC
```

**Find Entities with Most Relationships**:
```cypher
MATCH (e:Entity)
RETURN e.name, count{(e)-[]->()} AS out_degree,
       count{(e)<-[]-()} AS in_degree,
       count{(e)-[]-()} AS total_degree
ORDER BY total_degree DESC
LIMIT 20
```

**Identify Potential Duplicates**:
```cypher
// Find entities with very similar names (requires APOC)
MATCH (e1:Entity), (e2:Entity)
WHERE e1.uuid < e2.uuid
  AND apoc.text.levenshteinSimilarity(toLower(e1.name), toLower(e2.name)) >= 0.85
RETURN e1.name, e2.name,
       apoc.text.levenshteinSimilarity(toLower(e1.name), toLower(e2.name)) AS similarity
ORDER BY similarity DESC
LIMIT 50
```

### Dashboard Metrics

**Key Metrics to Track**:
1. **Total Entities**: Overall entity count in knowledge graph
2. **Duplicate Rate**: Percentage of entities that are duplicates
3. **Weekly Consolidations**: Number of duplicates merged per week
4. **Normalization Effectiveness**: Abbreviations normalized per document
5. **Within-Document Duplicates**: Duplicate rate within single documents
6. **Cross-Document Duplicates**: Duplicate rate across documents
7. **Entity Growth Rate**: New entities per week
8. **Relationship Growth Rate**: New relationships per week

## Phase 2 Roadmap

### Entity Registry Service (Month 1)

**Purpose**: Centralized canonical name management for entities.

**Components**:
- Entity registry database table
- Canonical name resolution API
- Alias management interface
- Confidence scoring for matches

**Implementation**:
```python
class EntityRegistry:
    """Manage canonical entity names and aliases."""

    def get_canonical_name(self, entity_name: str) -> str:
        """Resolve entity name to canonical form."""
        pass

    def add_alias(self, canonical: str, alias: str, confidence: float):
        """Register alias for canonical entity."""
        pass

    def find_matches(self, entity_name: str, threshold: float = 0.85) -> List[Dict]:
        """Find potential canonical matches."""
        pass
```

### DeduplicatingGraphitiClient Wrapper (Month 2)

**Purpose**: Wrap Graphiti client to check for existing entities before creation.

**Features**:
- Pre-creation entity lookup
- Automatic alias resolution
- Deduplication at ingestion time
- Relationship consolidation

**Implementation**:
```python
class DeduplicatingGraphitiClient:
    """Graphiti client wrapper with built-in deduplication."""

    def __init__(self, base_client: Graphiti, entity_registry: EntityRegistry):
        self.base_client = base_client
        self.entity_registry = entity_registry

    async def add_episode(self, **kwargs):
        # Pre-process entity names via registry
        # Check for existing entities
        # Merge relationships if entity exists
        # Create only if truly new
        pass
```

### Chunk-Aware Entity Tracking (Month 3)

**Purpose**: Track entities across chunks of the same document to prevent within-document duplicates.

**Features**:
- Chunk context linking
- Cross-chunk entity resolution
- Episode UUID chain tracking
- Enhanced duplicate detection

### Entity Similarity Cache (Month 4)

**Purpose**: Cache similarity computations to speed up consolidation.

**Features**:
- Redis-based similarity cache
- TTL-based invalidation
- Batch similarity computation
- API for similarity queries

### Machine Learning Duplicate Detection (Month 5-6)

**Purpose**: Use ML models to improve duplicate detection accuracy.

**Features**:
- Entity embedding generation (Sentence-BERT)
- Semantic similarity scoring
- Active learning for edge cases
- Continuous model improvement

## Troubleshooting

### EntityNormalizer Issues

**Problem**: Abbreviations not being expanded

**Diagnosis**:
```python
from src.flows.data_ingestion.entity_normalizer import EntityNormalizer

normalizer = EntityNormalizer()
text = "The EU announced new rules."

# Check if abbreviation is in mapping
print("EU" in normalizer.abbreviation_map)  # Should be True

# Check statistics
stats = normalizer.get_statistics(text)
print(stats["abbreviation_counts"])  # Should show {"EU": 1}

# Test normalization
normalized = normalizer.normalize_text(text)
print(normalized)  # Should contain "European Union"
```

**Solutions**:
- Verify abbreviation is in `DEFAULT_ABBREVIATION_MAP`
- Check case sensitivity settings
- Add custom mapping if abbreviation is domain-specific

**Problem**: Normalization breaking document structure

**Diagnosis**:
```python
# Test whitespace normalization
text = "Paragraph 1.\n\nParagraph 2."
normalized = normalizer.normalize_text(text)
print(repr(normalized))  # Should preserve double newlines
```

**Solutions**:
- Disable whitespace normalization: `enable_whitespace_normalization=False`
- Adjust preprocessing order (normalize before chunking)

### Consolidation Script Issues

**Problem**: APOC plugin errors

**Diagnosis**:
```bash
# Check if APOC is installed
docker exec -it neo4j cypher-shell -u neo4j -p password123 \
  "RETURN apoc.version() AS version;"
```

**Solutions**:
```bash
# Add APOC to docker-compose.yml
# neo4j:
#   environment:
#     - NEO4J_PLUGINS=["apoc"]

# Restart Neo4j
docker compose restart neo4j

# Wait for startup
sleep 10

# Verify installation
docker exec -it neo4j cypher-shell -u neo4j -p password123 \
  "RETURN apoc.version();"
```

**Problem**: Too many false positives

**Solutions**:
- Increase similarity threshold: `--similarity 0.90`
- Filter by entity types: `--entity-types Policy,Regulation`
- Manual review with dry-run mode

**Problem**: Script running very slowly

**Diagnosis**:
```bash
# Check entity count
docker exec -it neo4j cypher-shell -u neo4j -p password123 \
  "MATCH (e:Entity) RETURN count(e);"
```

**Solutions**:
- Run consolidation more frequently (weekly instead of monthly)
- Filter by entity types to process in batches
- Add indexes on entity names:
  ```cypher
  CREATE INDEX entity_name_index FOR (e:Entity) ON (e.name)
  ```

### DocumentTracker Issues

**Problem**: Entity metrics not being tracked

**Diagnosis**:
```python
from src.flows.data_ingestion.document_tracker import DocumentTracker

tracker = DocumentTracker()
docs = tracker.get_processed_documents()

# Check if entity_names_hash exists
for doc in docs[:5]:
    print(f"Doc: {doc['path']}")
    print(f"  Entity Hash: {doc.get('entity_names_hash', 'MISSING')}")
    print(f"  Unique Count: {doc.get('unique_entity_count', 'MISSING')}")
```

**Solutions**:
- Ensure using updated DocumentTracker with entity tracking methods
- Re-process documents to populate entity metrics
- Clear and re-ingest: `tracker.clear_all()`

**Problem**: Similarity search returning no results

**Diagnosis**:
```python
tracker = DocumentTracker()
stats = tracker.get_duplicate_detection_stats()
print(f"Documents with tracking: {stats['documents_with_entity_tracking']}")
```

**Solutions**:
- Entity tracking only works for newly processed documents
- Lower similarity threshold in `find_similar_documents()`
- Check if entity names are being passed to `mark_processed()`

### Integration Issues

**Problem**: Normalization not being applied

**Diagnosis**:
```bash
# Check document processor logs
grep -i "normalized.*abbreviations" /tmp/ray/session_latest/logs/serve/replica_*data-ingestion*.log | tail -20
```

**Solutions**:
- Verify EntityNormalizer is initialized in DocumentProcessorActor
- Check import statement in document_processor.py
- Redeploy Ray services: `just deploy-all`

**Problem**: Documents still creating duplicates

**Diagnosis**:
```bash
# Run consolidation in dry-run mode
python scripts/consolidate_duplicate_entities.py --dry-run

# Check normalization statistics in logs
grep -i "abbreviation" /tmp/ray/session_latest/logs/serve/replica_*data-ingestion*.log
```

**Solutions**:
- Add missing abbreviations to EntityNormalizer
- Adjust similarity threshold in consolidation script
- Investigate if duplicates are from different sources (internet vs Bundestag)

## Appendix

### Quick Reference Commands

```bash
# Test normalization
uv run python src/flows/data_ingestion/entity_normalizer.py

# Dry run consolidation
python scripts/consolidate_duplicate_entities.py --dry-run

# Live consolidation
python scripts/consolidate_duplicate_entities.py

# Get tracker statistics
uv run python -c "
from src.flows.data_ingestion.document_tracker import DocumentTracker
tracker = DocumentTracker()
stats = tracker.get_duplicate_detection_stats()
print(stats)
"

# Check Neo4j entity count
docker exec -it neo4j cypher-shell -u neo4j -p password123 \
  "MATCH (e:Entity) RETURN count(e);"

# Find potential duplicates
docker exec -it neo4j cypher-shell -u neo4j -p password123 \
  "MATCH (e1:Entity), (e2:Entity)
   WHERE e1.uuid < e2.uuid
     AND apoc.text.levenshteinSimilarity(toLower(e1.name), toLower(e2.name)) >= 0.85
   RETURN e1.name, e2.name LIMIT 10;"
```

### Configuration Files

**EntityNormalizer Custom Mappings** (`config/entity_mappings.yaml`):
```yaml
abbreviations:
  # Client-specific abbreviations
  BfDI: Federal Commissioner for Data Protection
  BKartA: German Federal Cartel Office
  BNetzA: German Federal Network Agency

  # Industry-specific terms
  AdTech: Advertising Technology
  MarTech: Marketing Technology
```

**Consolidation Thresholds** (`config/deduplication.yaml`):
```yaml
consolidation:
  similarity_threshold: 0.85
  entity_types:
    - Policy
    - Regulation
    - Politician
    - Organization
    - Company

  schedule:
    frequency: weekly
    day: sunday
    time: "02:00"
```

### Related Documentation

- [Graphiti Patterns](../.claude/graphiti-patterns.md)
- [Document Processing Flow](../src/flows/data_ingestion/README.md)
- [Neo4j Upsert Logic](../src/flows/bundestag_common/README.md)
- [Entity Normalizer API](../src/flows/data_ingestion/entity_normalizer.py)
- [Consolidation Script](../scripts/consolidate_duplicate_entities.py)

---

**Feedback and Improvements**: Please report issues or suggest improvements by creating a GitHub issue or contacting the development team.
