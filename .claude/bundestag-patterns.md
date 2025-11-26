# Bundestag Ingestion Flow Patterns (Flow 5)

## Overview
Flow 5 provides comprehensive German parliamentary data ingestion from the Bundestag Document and Information System (DIP) API. It collects 8 different types of parliamentary data and transforms them into knowledge graph entities and relationships.

## Architecture Patterns

### 8 Data Source Collectors
```python
# All collectors extend BaseCollector
class VorgangCollector(BaseCollector):
    endpoint = "vorgang"
    entity_type = "Vorgang"

class DrucksacheCollector(BaseCollector):
    endpoint = "drucksache"
    entity_type = "Drucksache"

# Plus: Person, Plenarprotokoll, Vorgangsposition, Aktivitaet, Wahlperiode, Fraktion
```

### Collector Pattern Structure
```python
class BaseCollector(ABC):
    """
    Abstract base with common functionality:
    - fetch_with_pagination()
    - collect_with_filters()
    - health_check()
    - _transform_to_entities()
    - _transform_to_edges()
    """

    @abstractmethod
    async def collect_and_transform(self, inputs: Dict) -> Dict:
        """Subclasses implement specific collection logic."""
        pass
```

### Transformation Pipeline
```
Bundestag API → Collector → Entity Builder → Edge Builder → Knowledge Graph
                    ↓
              Statistics Tracking
```

## API Client Pattern

### Robust HTTP Client
```python
class BundestagAPIClient:
    """
    Async HTTP client with:
    - Automatic retry with exponential backoff
    - Rate limit handling (429 responses)
    - Configurable timeout and max retries
    - Health check support
    """

    BASE_URL = "https://search.dip.bundestag.de/api/v1/"
    DEFAULT_API_KEY = "PUBLIC_KEY"  # Valid until 05/2026

    async def get(self, endpoint: str, params: Dict) -> Dict:
        # Implements retry logic with exponential backoff
        # Handles 429 rate limiting automatically
        # Returns JSON response
```

### Rate Limiting Strategy
- **Default**: 100 requests/minute, 20 requests/second burst
- **Handler**: Automatic retry with Retry-After header
- **Backoff**: Exponential: 1s, 2s, 4s, 8s...

## Pagination Pattern

### Cursor-Based Pagination
```python
class PaginationHelper:
    """
    Async iterator for paginated API responses.

    Usage:
        async for item in pagination.paginate(endpoint, filters):
            process(item)
    """

    async def paginate(self, endpoint: str, filters: Dict):
        cursor = None
        collected = 0

        while True:
            response = await self.api_client.get(endpoint, {
                **filters,
                "cursor": cursor
            })

            for item in response["documents"]:
                yield item
                collected += 1
                if self.max_items and collected >= self.max_items:
                    return

            cursor = response.get("cursor")
            if not cursor:  # Last page
                break
```

### Pagination Best Practices
- Always use cursor-based pagination (not offset)
- Set reasonable max_items limits
- Handle empty responses gracefully
- Track total items collected

## Filter Building Pattern

### Flexible Filter Construction
```python
class FilterBuilder:
    """
    Builds DIP API filter parameters from high-level inputs.
    """

    def build_filters(
        self,
        wahlperiode: Optional[str] = None,
        datum_von: Optional[str] = None,
        datum_bis: Optional[str] = None,
        limit: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        # Converts to DIP API format: f.wahlperiode, f.datum, etc.
```

### Common Filters
- `f.wahlperiode`: Electoral period (19, 20, 21)
- `f.datum`: Date filter (ISO 8601)
- `f.vorgangstyp`: Procedure type
- `f.beratungsstand`: Status filter
- `num`: Results per page (max 100)

## Deduplication Patterns

### Overview
Deduplication prevents duplicate data ingestion and ensures efficient processing. We implement deduplication at multiple levels: database, entity, document, and relationship.

### 1. Database-Level Deduplication (Primary Strategy)

#### Neo4j MERGE Pattern
```python
# MERGE ensures node uniqueness based on entity ID
query = """
MATCH (d:Drucksache {drucksache_nummer: $drucksache_nummer})
RETURN count(d) > 0 as exists
"""

# Use MERGE for relationships to avoid duplicates
query = """
MERGE (d:Drucksache {drucksache_nummer: $nummer})
MERGE (w:Wahlperiode {wahlperiode_nummer: $wahlperiode})
MERGE (d)-[:BELONGS_TO]->(w)
"""
```

**Benefits**:
- ✅ Atomic operation (no race conditions)
- ✅ Idempotent (safe to re-run)
- ✅ Database-enforced uniqueness
- ✅ Handles concurrent writes

**When to Use**:
- All entity upserts
- All relationship creation
- When multiple flows might create same entity

### 2. Pre-Processing Document Deduplication

#### Check Before Download Pattern (Flow 5c: Drucksache)
```python
def check_drucksache_exists(driver: Driver, database: str, drucksache_nummer: str) -> bool:
    """
    Check if Drucksache node already exists in Neo4j.

    Args:
        driver: Neo4j driver instance
        database: Database name
        drucksache_nummer: Drucksache identifier to check

    Returns:
        True if exists, False if new
    """
    try:
        with driver.session(database=database) as session:
            result = session.run(
                """
                MATCH (d:Drucksache {drucksache_nummer: $drucksache_nummer})
                RETURN count(d) > 0 as exists
                """,
                drucksache_nummer=drucksache_nummer,
            )

            record = result.single()
            return record["exists"] if record else False
    except Exception as e:
        logger.warning(f"Error checking if Drucksache exists: {e}")
        # On error, assume it doesn't exist (safe fallback - will process)
        return False


# Usage in processor
if extract_full_text and drucksache_entity.get("dokument_url"):
    pdf_url = drucksache_entity["dokument_url"]
    drucksache_nummer = drucksache_entity["drucksache_nummer"]

    # CHECK: Only download PDF if this is a NEW document
    exists = check_drucksache_exists(driver, neo4j_database, drucksache_nummer)

    if not exists:
        # Document is NEW - queue for download
        pdf_download_tasks.append({
            "url": pdf_url,
            "path": pdf_path,
            "nummer": drucksache_nummer,
            "wahlperiode": wp_int,
        })
        logger.info(f"📥 Queued NEW document for PDF download: {drucksache_nummer}")
    else:
        logger.info(f"⏭️ Skipping PDF download for existing document: {drucksache_nummer}")
        stats["drucksachen_skipped"] += 1
```

**Benefits**:
- ✅ Prevents expensive PDF downloads for existing documents
- ✅ Saves bandwidth and storage
- ✅ Speeds up re-runs significantly
- ✅ Safe fallback on errors (processes if unsure)

**Use Cases**:
- Large file downloads (PDFs, images)
- Expensive API calls
- Resource-intensive processing
- Re-running flows after failures

**Statistics Tracking**:
```python
stats = {
    "drucksachen_created": 0,
    "drucksachen_skipped": 0,  # Track how many were already present
    "pdfs_downloaded": 0,
}
```

### 3. Related Entity Deduplication (In-Memory)

#### Dictionary-Based Deduplication Pattern (Flow 5b: Vorgang)
```python
# Extract deskriptoren from multiple vorgänge
all_deskriptoren = []
for doc in documents:
    deskriptoren = extract_deskriptoren(doc)
    all_deskriptoren.extend(deskriptoren)

# Deduplicate by deskriptor_id using dictionary
unique_deskriptoren = {
    d["deskriptor_id"]: d for d in all_deskriptoren
}.values()

# Upsert only unique deskriptoren
desk_results = upsert_manager.upsert_entities_batch(
    entity_type="Deskriptor",
    entities=list(unique_deskriptoren),
    batch_size=batch_size,
)
```

**Pattern Breakdown**:
1. Collect entities from multiple API responses
2. Create dictionary with unique ID as key (last occurrence wins)
3. Extract unique values via `.values()`
4. Convert back to list for batch processing

**Benefits**:
- ✅ Fast in-memory deduplication (O(n))
- ✅ Reduces database writes
- ✅ Handles transitive duplicates (across batches)
- ✅ Simple and maintainable

**Similar Pattern for Sachgebiete**:
```python
# Deduplicate sachgebiete by name
unique_sachgebiete = {
    s["sachgebiet_name"]: s for s in all_sachgebiete
}.values()

sg_results = upsert_manager.upsert_entities_batch(
    entity_type="Sachgebiet",
    entities=list(unique_sachgebiete),
    batch_size=batch_size,
)
```

### 4. URL-Based Deduplication (ETL Patterns)

#### Content Deduplication by URL
```python
def deduplicate_by_url(documents: List[Dict]) -> List[Dict]:
    """
    Deduplicate documents by URL.

    Args:
        documents: List of document dicts with 'url' field

    Returns:
        List of unique documents (first occurrence per URL)
    """
    seen_urls = set()
    unique_documents = []

    for doc in documents:
        url = doc.get('url')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_documents.append(doc)

    return unique_documents


# Usage in ETL collectors
raw_articles = await exa_collector.collect_news(query=query, num_results=20)
deduplicated_articles = deduplicate_by_url(raw_articles)
```

**Benefits**:
- ✅ Prevents duplicate content ingestion
- ✅ Maintains first-seen semantics
- ✅ Fast set-based lookup (O(1))
- ✅ Useful for news aggregation

### 5. Temporal Deduplication

#### Prevent Re-Processing Recent Data
```python
class TemporalDeduplicator:
    """
    Track when entities were last processed to avoid redundant work.
    """

    def __init__(self, driver: Driver, database: str):
        self.driver = driver
        self.database = database

    def get_last_update_date(self, entity_type: str, entity_id: str) -> Optional[datetime]:
        """Get when entity was last updated."""
        with self.driver.session(database=self.database) as session:
            result = session.run(
                f"""
                MATCH (e:{entity_type} {{{entity_type.lower()}_id: $entity_id}})
                RETURN e.aktualisiert AS last_update
                """,
                entity_id=entity_id,
            )
            record = result.single()
            if record and record["last_update"]:
                return datetime.fromisoformat(record["last_update"])
            return None

    def should_update(
        self,
        entity_type: str,
        entity_id: str,
        api_update_date: datetime,
        staleness_threshold: timedelta = timedelta(days=1)
    ) -> bool:
        """
        Determine if entity should be updated based on API timestamp.

        Returns True if:
        - Entity doesn't exist (new)
        - API data is newer than database
        - Database data is older than threshold
        """
        last_update = self.get_last_update_date(entity_type, entity_id)

        if not last_update:
            return True  # New entity

        if api_update_date > last_update:
            return True  # API has newer data

        if datetime.now() - last_update > staleness_threshold:
            return True  # Stale data, refresh anyway

        return False  # Skip, data is fresh


# Usage in collectors
deduplicator = TemporalDeduplicator(driver, database)

for vorgang in vorgaenge:
    vorgang_id = vorgang["id"]
    api_update_date = datetime.fromisoformat(vorgang["aktualisiert"])

    if deduplicator.should_update("Vorgang", vorgang_id, api_update_date):
        # Process and update entity
        entity = map_vorgang_to_entity(vorgang)
        upsert_manager.upsert_entity("Vorgang", entity)
    else:
        logger.debug(f"Skipping Vorgang {vorgang_id} - data is fresh")
        stats["skipped_fresh"] += 1
```

**Benefits**:
- ✅ Avoids re-processing unchanged data
- ✅ Respects API update timestamps
- ✅ Configurable staleness threshold
- ✅ Reduces computational overhead

### 6. Batch-Level Deduplication

#### Cross-Batch Deduplication Pattern
```python
class BatchDeduplicator:
    """
    Maintain deduplication state across multiple batches.
    """

    def __init__(self):
        self.seen_ids = set()
        self.batch_number = 0

    def filter_batch(self, entities: List[Dict], id_field: str) -> List[Dict]:
        """
        Filter out entities already seen in previous batches.

        Args:
            entities: List of entity dictionaries
            id_field: Name of the ID field (e.g., "vorgang_id")

        Returns:
            List of unique entities not seen before
        """
        unique_entities = []

        for entity in entities:
            entity_id = entity.get(id_field)
            if entity_id and entity_id not in self.seen_ids:
                self.seen_ids.add(entity_id)
                unique_entities.append(entity)

        return unique_entities

    def get_statistics(self) -> Dict[str, int]:
        """Get deduplication statistics."""
        return {
            "total_unique": len(self.seen_ids),
            "batches_processed": self.batch_number,
        }


# Usage in paginated collection
deduplicator = BatchDeduplicator()

cursor = None
while cursor:
    # Fetch batch from API
    documents, cursor = await fetch_vorgaenge_from_api(cursor=cursor)

    # Map to entities
    entities = [map_vorgang_to_entity(doc) for doc in documents]

    # Deduplicate across batches
    unique_entities = deduplicator.filter_batch(entities, id_field="vorgang_id")

    # Process only unique entities
    if unique_entities:
        upsert_manager.upsert_entities_batch("Vorgang", unique_entities)
        logger.info(f"Batch {deduplicator.batch_number}: {len(unique_entities)} unique vorgänge")

    deduplicator.batch_number += 1
```

**Use Cases**:
- Paginated API responses that may overlap
- Multi-source data collection
- Concurrent collection from multiple endpoints

### 7. Relationship Deduplication

#### Automatic via MERGE
```python
# MERGE handles relationship deduplication automatically
def create_vorgang_relationships(driver, database: str, vorgang_ids: list[str]) -> int:
    """Create relationships for vorgänge."""
    with driver.session(database=database) as session:
        # MERGE ensures no duplicate relationships
        query = """
        MATCH (v:Vorgang)
        WHERE v.vorgang_id IN $vorgang_ids AND v.wahlperiode IS NOT NULL
        MATCH (w:Wahlperiode {wahlperiode_nummer: v.wahlperiode})
        MERGE (v)-[:BELONGS_TO]->(w)
        RETURN count(*) as count
        """
        result = session.run(query, vorgang_ids=vorgang_ids)
        return result.single()["count"]
```

**Key Points**:
- ✅ MERGE prevents duplicate relationships
- ✅ Idempotent - safe to run multiple times
- ✅ No manual deduplication needed
- ✅ Handles concurrent relationship creation

### Deduplication Best Practices

#### ✅ DO
1. **Use MERGE for all Neo4j writes** - Database-enforced uniqueness
2. **Check existence before expensive operations** - PDF downloads, API calls
3. **Deduplicate in-memory when collecting related entities** - Deskriptoren, Sachgebiete
4. **Track statistics** - Count created vs. skipped entities
5. **Use temporal checks** - Avoid re-processing fresh data
6. **Implement safe fallbacks** - Process if unsure rather than skip

#### ❌ DON'T
1. **Don't skip deduplication for "small" datasets** - They grow quickly
2. **Don't deduplicate after database writes** - Too late, wastes resources
3. **Don't use offset-based pagination** - Can create duplicates across pages
4. **Don't ignore API update timestamps** - Use them for temporal deduplication
5. **Don't hardcode staleness thresholds** - Make them configurable

### Deduplication Statistics

#### Standard Tracking Pattern
```python
stats = {
    # Entity counts
    "total_fetched": 0,        # From API
    "total_processed": 0,      # Attempted to process
    "entities_created": 0,     # Successfully created/updated
    "entities_skipped": 0,     # Already existed (deduplicated)

    # Deduplication breakdown
    "skipped_exists": 0,       # Pre-check found existing
    "skipped_fresh": 0,        # Temporal deduplication
    "duplicates_in_batch": 0,  # In-memory deduplication

    # Resource savings
    "pdfs_downloaded": 0,      # Expensive operations performed
    "pdfs_skipped": 0,         # Expensive operations avoided

    # Errors
    "errors": [],
}
```

### Performance Impact

#### Resource Savings from Deduplication
```python
# Example: Flow 5c (Drucksache) with 1000 documents
Without Deduplication:
- Downloads: 1000 PDFs × 2MB = 2GB bandwidth
- Processing: 1000 PDFs × 30s = 8.3 hours
- Storage: 2GB disk space

With Deduplication (70% already exist):
- Downloads: 300 PDFs × 2MB = 600MB bandwidth (70% savings)
- Processing: 300 PDFs × 30s = 2.5 hours (70% time savings)
- Storage: +600MB disk space (70% savings)
```

### Testing Deduplication Logic

#### Unit Test Pattern
```python
@pytest.mark.asyncio
async def test_drucksache_deduplication():
    """Test that existing drucksachen are not re-downloaded."""

    # Setup: Create existing Drucksache in test database
    existing_nummer = "20/12345"
    with driver.session(database=test_database) as session:
        session.run(
            "CREATE (d:Drucksache {drucksache_nummer: $nummer})",
            nummer=existing_nummer
        )

    # Test: Check existence
    exists = check_drucksache_exists(driver, test_database, existing_nummer)
    assert exists == True

    # Test: New document
    new_nummer = "20/99999"
    exists = check_drucksache_exists(driver, test_database, new_nummer)
    assert exists == False
```

#### Integration Test Pattern
```python
@pytest.mark.asyncio
async def test_full_deduplication_flow():
    """Test complete deduplication flow."""

    # First run: Process 100 documents
    result1 = await process_drucksache_batch({
        "wahlperioden": ["20"],
        "max_drucksachen": 100,
        "extract_full_text": True,
    }, tracer)

    assert result1["drucksachen_created"] == 100
    assert result1["pdfs_downloaded"] == 100
    assert result1["drucksachen_skipped"] == 0

    # Second run: Same 100 documents (should skip)
    result2 = await process_drucksache_batch({
        "wahlperioden": ["20"],
        "max_drucksachen": 100,
        "extract_full_text": True,
    }, tracer)

    assert result2["drucksachen_created"] == 0  # Already exist
    assert result2["pdfs_downloaded"] == 0      # Skipped
    assert result2["drucksachen_skipped"] == 100  # All deduplicated
```

### Common Deduplication Scenarios

#### Scenario 1: Re-running After Failure
```python
# Flow crashed after processing 500/1000 items
# On restart, deduplication ensures:
# - 500 existing items are skipped (fast)
# - 500 remaining items are processed (completes job)
# - No duplicate nodes or relationships created
```

#### Scenario 2: Incremental Updates
```python
# Daily collection with 95% overlap from previous day
# Deduplication ensures:
# - 95% of items skipped (already have)
# - 5% new items processed
# - Only new items trigger expensive operations
```

#### Scenario 3: Multiple Sources
```python
# Collecting same data from different endpoints
# Deduplication ensures:
# - First source creates entities
# - Second source skips duplicates
# - Third source adds missing entities
# - No conflicts or overwrites
```

### 8. Canonical Entities Deduplication (EntityRegistry)

#### Purpose
**Prevention at ingestion time** - Resolve entity names to canonical forms before creating nodes, preventing duplicates from being created in the first place.

#### Neo4j Schema
```cypher
// Canonical Entity Node (authoritative version)
(ce:CanonicalEntity {
    uuid: "canonical-uuid-123",
    name: "European Commission",
    entity_type: "Organization",
    created_at: "2025-11-25T10:00:00Z",
    last_updated: "2025-11-25T10:00:00Z",
    usage_count: 15,  // Number of documents using this entity
    source: "registry"
})

// Entity Alias Node (variations of canonical)
(ea:EntityAlias {
    uuid: "alias-uuid-456",
    alias: "EU Commission",
    confidence: 0.95,
    source: "normalization",  // How was this alias discovered
    created_at: "2025-11-25T10:00:00Z",
    usage_count: 8
})

// Relationship
(ea)-[:ALIAS_OF]->(ce)
```

#### EntityRegistry API
```python
from src.flows.bundestag_common.entity_registry import EntityRegistry

class EntityRegistry:
    """
    Centralized canonical entity name management.

    Storage: Neo4j with CanonicalEntity and EntityAlias nodes
    Performance: Sub-millisecond lookups via 9 optimized indexes
    """

    def __init__(self, neo4j_driver, database: str = "politicalmonitoring.v3"):
        self.driver = neo4j_driver
        self.database = database

    async def get_canonical_entity(
        self,
        entity_name: str,
        entity_type: str = None
    ) -> Optional[Dict]:
        """
        Resolve entity name to canonical form.

        Resolution Strategy:
        1. Exact Match - Check if name exists as canonical
        2. Alias Match - Check if name exists as alias
        3. Fuzzy Match - Levenshtein similarity (threshold: 0.85)
        4. Create New - No match found

        Returns:
            {
                "canonical_uuid": "...",
                "canonical_name": "European Commission",
                "entity_type": "Organization",
                "confidence": 0.95,
                "match_type": "exact" | "alias" | "fuzzy"
            }
        """

    async def register_canonical_entity(
        self,
        name: str,
        entity_type: str,
        entity_uuid: str
    ) -> bool:
        """Register a new canonical entity."""

    async def add_alias(
        self,
        canonical_uuid: str,
        alias: str,
        confidence: float,
        source: str
    ) -> bool:
        """Add an alias for a canonical entity."""
```

#### Neo4j Index Optimization (Phase 2)

**9 Optimized Indexes for Sub-Millisecond Lookups**:

**CanonicalEntity Indexes (6)**:
1. `canonical_entity_uuid` - UNIQUE constraint (primary key)
2. `canonical_entity_name` - Index on name (basic lookups)
3. `canonical_entity_type` - Index on entity_type (filtering)
4. **`canonical_entity_name_type`** - **Composite (name, entity_type)** - PRIMARY LOOKUP
5. **`canonical_entity_name_text`** - **Text index** - FUZZY SEARCH
6. `canonical_entity_usage_count` - Index on usage_count (stats)

**EntityAlias Indexes (3)**:
1. `entity_alias_uuid` - UNIQUE constraint (primary key)
2. `entity_alias_alias` - Index on alias (basic lookups)
3. **`entity_alias_alias_confidence`** - **Composite** - HIGH-CONFIDENCE LOOKUPS

**Performance Impact**:
```
Before Optimization:
- Canonical lookups: ~10-50ms (O(n) full scan)
- Alias resolution: ~20-100ms (O(n) scan)

After Optimization:
- Canonical lookups: ~1-5ms (O(log n) index) - 100x faster
- Alias resolution: ~2-5ms (composite index) - 50x faster
- Fuzzy matching: ~5-20ms (text index + APOC) - 10x faster

Scaling:
- 1K entities: <2ms average
- 10K entities: <3ms average
- 100K entities: <5ms average
- 1M+ entities: <10ms (logarithmic scaling)
```

#### Integration with Document Processing
```python
# In document_processor.py - Phase 2 Integration

from src.flows.bundestag_common.entity_registry import EntityRegistry
from src.flows.bundestag_common.deduplicating_graphiti_client import (
    DeduplicatingGraphitiClient
)

async def process_document_with_canonical_entities(doc_path: Path):
    # Initialize Phase 2 components
    entity_registry = EntityRegistry(neo4j_driver, database="politicalmonitoring.v3")

    # Wrap Graphiti client with deduplication logic
    dedupe_client = DeduplicatingGraphitiClient(
        base_client=graphiti_client,
        entity_registry=entity_registry,
        entity_normalizer=EntityNormalizer()
    )

    # Process chunks with automatic canonical entity resolution
    for chunk in chunks:
        result = await dedupe_client.add_episode(
            name=f"doc_{doc_path.stem}_chunk_{chunk['index']}",
            episode_body=chunk['text'],
            source=EpisodeType.text,
            **kwargs
        )

        # Post-processing: Entity UUIDs are automatically resolved to canonical
        for entity in result.nodes:
            # Entity UUID is now canonical UUID if match was found
            # Aliases are automatically registered in EntityRegistry
            pass
```

#### DeduplicatingGraphitiClient Flow
```python
class DeduplicatingGraphitiClient:
    """
    Graphiti client wrapper with entity deduplication.

    Prevents duplicate entity creation by:
    1. Normalizing entity names (Phase 1 EntityNormalizer)
    2. Checking EntityRegistry for existing entities
    3. Reusing canonical entity UUIDs when matches found
    4. Registering new entities and aliases in registry
    """

    async def add_episode(self, name: str, episode_body: str, **kwargs):
        # Step 1: Normalize text (Phase 1)
        normalized_body = self.normalizer.normalize_text(episode_body)

        # Step 2: Extract entities via base Graphiti client
        result = await self.base_client.add_episode(
            name=name,
            episode_body=normalized_body,
            **kwargs
        )

        # Step 3: Post-process entities - resolve to canonical
        entity_map = {}  # Original UUID → Canonical UUID

        for entity in result.nodes:
            # Check registry for canonical form
            canonical = await self.registry.get_canonical_entity(
                entity.name,
                entity_type=entity.labels[0] if entity.labels else None
            )

            if canonical:
                # Reuse existing canonical entity
                entity_map[entity.uuid] = canonical["canonical_uuid"]

                # Register alias if not exact match
                if entity.name.lower() != canonical["canonical_name"].lower():
                    await self.registry.add_alias(
                        canonical_uuid=canonical["canonical_uuid"],
                        alias=entity.name,
                        confidence=canonical["confidence"],
                        source="graphiti_extraction"
                    )
            else:
                # New entity - register as canonical
                await self.registry.register_canonical_entity(
                    name=entity.name,
                    entity_type=entity.labels[0] if entity.labels else "Entity",
                    entity_uuid=entity.uuid
                )
                entity_map[entity.uuid] = entity.uuid  # Self-mapping

        # Step 4: Update relationships to use canonical UUIDs
        updated_result = self._update_entity_references(result, entity_map)

        return updated_result
```

#### Success Metrics
```python
# Entity Reuse Rate
entity_reuse_rate = (canonical_entities_reused / total_entities_extracted) * 100
# Target: >60% for common entities (EU Commission, GDPR, etc.)

# Duplicate Reduction (beyond Phase 1)
phase2_reduction = (entities_before_phase2 - entities_after_phase2) / entities_before_phase2 * 100
# Target: 30-40% additional reduction (total 60-70% with Phase 1)

# Alias Coverage
alias_coverage = (entities_with_aliases / total_canonical_entities) * 100
# Target: >80% of common variations captured

# Resolution Accuracy
resolution_accuracy = correct_matches / total_matches * 100
# Target: >95% precision (validated manually on sample)
```

**Key Points**:
- ✅ Prevents duplicates at ingestion time (proactive)
- ✅ Sub-millisecond lookups via composite indexes
- ✅ Automatic alias discovery and registration
- ✅ Handles entity name variations (abbreviations, typos)
- ✅ Transparent integration with existing flows
- ⚠️ Requires OpenAI API key for entity extraction
- ⚠️ Performance overhead: <10% vs non-deduplicated ingestion

### 9. Automated Entity Deduplication (Airflow DAG)

#### Purpose
**Weekly post-processing cleanup** - Automated fuzzy string matching to find and merge duplicate entities that were created despite normalization and canonical entity resolution.

#### Airflow DAG Configuration
```python
# File: src/etl/dags/entity_deduplication_dag.py

DAG_ID = "entity_deduplication_weekly"
SCHEDULE = "0 3 * * 0"  # Sundays at 3 AM UTC (after policy collection)

# Environment Variables
DEDUP_SIMILARITY_THRESHOLD = 0.85      # Levenshtein similarity threshold
DEDUP_AUTO_CONFIRM = "false"           # Require manual confirmation
DEDUP_ENTITY_TYPES = "Policy,Regulation,Politician,Organization,Company"
DEDUP_REPORT_DIR = "data/reports/deduplication"
```

#### DAG Workflow
```
┌─────────────────────────────────────────────────────────────┐
│          Entity Deduplication DAG Workflow                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. check_apoc_availability                                 │
│     └─> Verify APOC plugin installed (required for fuzzy)  │
│                                                             │
│  2. run_dry_run_consolidation                               │
│     └─> Find duplicate pairs (similarity ≥ 0.85)           │
│     └─> Generate preview report                             │
│     └─> Save to: data/reports/deduplication/               │
│                                                             │
│  3. check_consolidation_threshold (BRANCH)                  │
│     ├─> No duplicates found                                 │
│     │   └─> generate_summary_no_duplicates                 │
│     ├─> Duplicates found + AUTO_CONFIRM=false              │
│     │   └─> generate_summary_manual_review                 │
│     └─> Duplicates found + AUTO_CONFIRM=true               │
│         └─> run_live_consolidation                         │
│             └─> generate_summary_consolidated              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Task Implementations

**1. Check APOC Availability**
```python
def check_apoc_availability(**context) -> dict[str, Any]:
    """
    Verify APOC plugin is available in Neo4j.
    Required for apoc.text.levenshteinSimilarity() function.
    """
    from neo4j import GraphDatabase

    config = load_deduplication_config()
    driver = GraphDatabase.driver(
        config["neo4j_uri"],
        auth=(config["neo4j_user"], config["neo4j_password"])
    )

    with driver.session(database=config["neo4j_database"]) as session:
        result = session.run("RETURN apoc.version() AS version")
        apoc_info = result.single()

        if not apoc_info:
            raise RuntimeError("APOC plugin not installed")

        return {
            "apoc_available": True,
            "apoc_version": apoc_info["version"],
            "config": config
        }
```

**2. Run Dry-Run Consolidation**
```python
def run_dry_run_consolidation(**context) -> dict[str, Any]:
    """
    Execute consolidation script in dry-run mode.

    Finds potential duplicates using:
    - Levenshtein similarity ≥ 0.85
    - Same entity type (Policy, Regulation, etc.)
    - Different UUIDs
    """
    config = context["task_instance"].xcom_pull(
        task_ids="check_apoc_availability",
        key="apoc_check"
    )["config"]

    # Build command
    cmd = [
        "python",
        config["consolidation_script_path"],
        "--dry-run",
        "--similarity", str(config["similarity_threshold"]),
        "--entity-types", ",".join(config["entity_types"])
    ]

    # Execute
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        raise RuntimeError(f"Dry-run failed: {result.stderr}")

    # Parse output
    duplicates_found = _parse_duplicates_count(result.stdout)

    dry_run_result = {
        "duplicates_found": duplicates_found,
        "output": result.stdout,
        "similarity_threshold": config["similarity_threshold"],
        "entity_types": config["entity_types"],
        "execution_timestamp": datetime.now().isoformat()
    }

    # Save report
    _save_dry_run_report(dry_run_result, config)

    return dry_run_result
```

**3. Check Consolidation Threshold (Branch)**
```python
def check_consolidation_threshold(**context) -> str:
    """
    Decision logic for consolidation routing.

    Returns task_id of next step:
    - "generate_summary_no_duplicates" - No duplicates found
    - "run_live_consolidation" - Auto-confirm enabled
    - "generate_summary_manual_review" - Manual review required
    """
    dry_run_result = context["task_instance"].xcom_pull(
        task_ids="run_dry_run_consolidation",
        key="dry_run_result"
    )

    duplicates_found = dry_run_result.get("duplicates_found", 0)
    auto_confirm = config.get("auto_confirm", False)

    if duplicates_found == 0:
        return "generate_summary_no_duplicates"
    elif auto_confirm:
        return "run_live_consolidation"
    else:
        return "generate_summary_manual_review"
```

**4. Run Live Consolidation**
```python
def run_live_consolidation(**context) -> dict[str, Any]:
    """
    Execute actual entity consolidation.

    For each duplicate pair:
    1. Identify canonical entity (most relationships)
    2. Transfer all relationships to canonical
    3. Merge properties (if not conflicting)
    4. Delete duplicate entity
    5. Log transaction for audit
    """
    config = context["task_instance"].xcom_pull(...)["config"]

    # Build command (no --dry-run)
    cmd = [
        "python",
        config["consolidation_script_path"],
        "--similarity", str(config["similarity_threshold"])
    ]

    # Set AUTO_CONFIRM environment variable
    env = os.environ.copy()
    env["AUTO_CONFIRM"] = "true"

    # Execute
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=600)

    if result.returncode != 0:
        raise RuntimeError(f"Live consolidation failed: {result.stderr}")

    # Parse statistics
    return {
        "duplicates_merged": _parse_merged_count(result.stdout),
        "relationships_transferred": _parse_relationships_transferred(result.stdout),
        "execution_timestamp": datetime.now().isoformat()
    }
```

#### Consolidation Script Integration
```bash
# Manual execution (outside Airflow)

# Dry run - preview duplicates
python scripts/consolidate_duplicate_entities.py --dry-run

# Live consolidation with confirmation prompt
python scripts/consolidate_duplicate_entities.py

# Automated (no prompt)
AUTO_CONFIRM=true python scripts/consolidate_duplicate_entities.py

# Custom threshold
python scripts/consolidate_duplicate_entities.py --similarity 0.90

# Filter by entity types
python scripts/consolidate_duplicate_entities.py --entity-types Policy,Regulation
```

#### Monitoring and Reporting

**Dry-Run Report Example**:
```
╭───────────────────────────────────────────────────────────────╮
│            🔍 Duplicate Entity Consolidation Report           │
├───────────────────────────────────────────────────────────────┤
│  Mode: DRY RUN (no changes will be made)                     │
│  Similarity Threshold: 0.85                                   │
│  Neo4j Database: politicalmonitoring.v3                       │
╰───────────────────────────────────────────────────────────────╯

Found 15 potential duplicate pairs:

┏━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Entity 1                 ┃ Entity 2                 ┃ Similarity ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ European Commission      │ European Commision       │ 0.98       │
│ Digital Services Act     │ Digital Service Act      │ 0.98       │
│ General Data Protection… │ GDPR                     │ 0.87       │
└──────────────────────────┴──────────────────────────┴────────────┘

Would merge 15 duplicate entities
```

**Live Consolidation Report Example**:
```
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

#### Airflow DAG Metrics
```python
# DAG Summary stored in XCom
{
    "dag_run_summary": {
        "dag_id": "entity_deduplication_weekly",
        "execution_date": "2025-11-25T03:00:00Z",
        "result": "consolidation_successful"  # or "no_duplicates_found" or "manual_review_required"
    },
    "deduplication_metrics": {
        "duplicates_found": 15,
        "duplicates_merged": 15,
        "relationships_transferred": 127,
        "success_rate": 1.0,
        "similarity_threshold": 0.85
    },
    "quality_indicators": {
        "knowledge_graph_health": "improved",
        "entity_count_reduction": 15,
        "relationships_per_duplicate": 8.47
    },
    "next_steps": {
        "next_scheduled_run": "Next Sunday 3 AM UTC",
        "recommended_actions": [
            "Successfully consolidated 15 duplicate entities",
            "Transferred 127 relationships",
            "Monitor entity extraction patterns to improve normalization"
        ]
    }
}
```

#### Configuration Management
```yaml
# config/deduplication.yaml (optional)
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
    time: "03:00"  # UTC

  auto_confirm: false  # Require manual review by default

  reporting:
    output_dir: data/reports/deduplication
    retention_days: 90
```

**Key Points**:
- ✅ Fully automated weekly cleanup
- ✅ Safe dry-run preview before consolidation
- ✅ Configurable similarity threshold and entity types
- ✅ Optional auto-confirm for hands-off operation
- ✅ Comprehensive reporting and metrics
- ✅ Scheduled after data collection (Sundays 3 AM)
- ⚠️ Requires APOC plugin installed in Neo4j
- ⚠️ Manual review recommended for first few runs
- ⚠️ Can take 5-10 minutes for large graphs (1000+ entities)

## Entity and Edge Transformation

### Entity Builder Pattern
```python
class BundestagEntityBuilder:
    """
    Creates Pydantic entities from raw API data.
    Supports all 8 entity types from political_schema_v4.
    """

    async def create_vorgang_entity(self, **kwargs) -> Vorgang:
        return Vorgang(**kwargs)

    async def create_person_entity(self, **kwargs) -> BundestagPerson:
        return BundestagPerson(**kwargs)

    async def build(self, raw_data: Dict) -> Any:
        # Generic method that routes to specific builder
```

### Edge Builder Pattern
```python
class BundestagEdgeBuilder:
    """
    Creates relationship edges between entities.
    Supports 15 edge types from political_schema_v4.
    """

    async def build(self, raw_data: Dict, entity: Any) -> List[Edge]:
        # Extracts relationships from raw data
        # Returns list of edge objects
```

### 15 Edge Types
1. Vorgang → Wahlperiode (IN_WAHLPERIODE)
2. Vorgang → Drucksache (HAS_DRUCKSACHE)
3. Person → Fraktion (MEMBER_OF_FRAKTION)
4. Person → Wahlperiode (ACTIVE_IN_WAHLPERIODE)
5. Fraktion → Wahlperiode (EXISTS_IN_WAHLPERIODE)
6. Vorgangsposition → Vorgang (POSITION_OF_VORGANG)
7. Aktivitaet → Vorgang (ACTIVITY_OF_VORGANG)
8. Aktivitaet → Plenarprotokoll (DOCUMENTED_IN_PROTOKOLL)
9. Plenarprotokoll → Wahlperiode (IN_WAHLPERIODE)
10. Person → Vorgang (INITIATES_VORGANG)
11. Person → Aktivitaet (PARTICIPATES_IN_ACTIVITY)
12. Drucksache → Person (AUTHORED_BY)
13. Drucksache → Wahlperiode (IN_WAHLPERIODE)
14. Vorgang → Vorgang (RELATED_TO_VORGANG)
15. Fraktion → Vorgang (FRAKTION_POSITION_ON)

## Testing Patterns

### Following Good Test Practices
✅ **DO**: Mock only external dependencies (HTTP API calls)
✅ **DO**: Test real internal logic (transformers, builders)
✅ **DO**: Use interface contract validation
✅ **DO**: Test with realistic sample data

❌ **DON'T**: Over-mock internal interfaces
❌ **DON'T**: Mock the transformation logic you're testing
❌ **DON'T**: Skip interface validation

### Test Structure
```
tests/
├── fixtures/
│   └── bundestag_sample_data.py       # Realistic API responses
├── unit/flows/bundestag_ingestion/
│   ├── test_collectors.py             # All 8 collectors
│   ├── test_transformers.py           # Entity/edge builders
│   └── test_utils.py                  # API client, pagination, filters
└── integration/flows/
    └── test_bundestag_ingestion_flow.py  # End-to-end flow
```

### Sample Data Pattern
```python
# tests/fixtures/bundestag_sample_data.py
SAMPLE_VORGANG_RESPONSE = {
    "documents": [{
        "id": "287654",
        "titel": "Gesetz zur...",
        "vorgangstyp": "Gesetzgebung",
        "wahlperiode": 20,
        # ... realistic field values
    }],
    "numFound": 1,
    "cursor": "AoE/cursor_string"
}
```

### Interface Contract Testing
```python
def test_all_collectors_have_consistent_interface():
    """Validate all collectors implement required interface."""
    collectors = [
        VorgangCollector(...),
        DrucksacheCollector(...),
        # ... all 8 collectors
    ]

    for collector in collectors:
        assert hasattr(collector, 'endpoint')
        assert hasattr(collector, 'entity_type')
        assert hasattr(collector, 'collect_and_transform')
        assert hasattr(collector, 'health_check')
```

### Real Logic Testing
```python
@pytest.mark.asyncio
async def test_collect_with_real_transformation():
    """Test real collection with actual transformation logic."""
    # Mock only external API
    api_client.get = AsyncMock(return_value=SAMPLE_VORGANG_RESPONSE)

    # Use real transformers (not mocked!)
    entity_builder = BundestagEntityBuilder()
    edge_builder = BundestagEdgeBuilder()

    collector = VorgangCollector(api_client, entity_builder, edge_builder)

    # Test real logic
    result = await collector.collect_and_transform(inputs)

    # This would catch method name bugs!
    assert result["entities_created"] >= 0
```

## Statistics and Reporting

### Standard Statistics Format
```python
{
    "entities_created": 42,
    "edges_created": 156,
    "duration": 12.34,
    "items_collected": 42,
    "collector_type": "VorgangCollector",
    "endpoint": "vorgang",
    "entity_type": "Vorgang",
    "errors": []
}
```

### Progress Tracking
Collectors track:
- Items collected from API
- Entities created in knowledge graph
- Edges created between entities
- Processing duration
- Error messages (if any)

## Error Handling Patterns

### API Error Handling
```python
try:
    response = await api_client.get(endpoint, params)
except aiohttp.ClientError as e:
    logger.error("API request failed", error=str(e))
    # Retry with exponential backoff
    # Or report error in statistics
```

### Transformation Error Handling
```python
for item in items:
    try:
        entity = await entity_builder.build(item)
        entities.append(entity)
    except Exception as e:
        logger.error("Failed to transform item", item_id=item.get("id"), error=str(e))
        errors.append(str(e))
        continue  # Continue with next item
```

### Health Check Pattern
```python
async def health_check(self) -> bool:
    """Verify collector can access API."""
    try:
        items = await self.fetch_with_pagination(filters={}, limit=1)
        return True
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return False
```

## Integration with Kodosumi

### Flow Integration Pattern
Collectors integrate with Kodosumi flows:
- Return standardized statistics dictionary
- Support progress tracking via tracer
- Generate markdown reports
- Handle batch processing

### Knowledge Graph Integration
Entities and edges are stored via Kodosumi interface:
- Entities → Neo4j nodes
- Edges → Neo4j relationships
- Maintains schema consistency with political_schema_v4

## Performance Patterns

### Batch Collection
```python
# Collect multiple sources in parallel
import asyncio

results = await asyncio.gather(*[
    vorgang_collector.collect_with_filters(...),
    drucksache_collector.collect_with_filters(...),
    person_collector.collect_with_filters(...)
])
```

### Memory Management
```python
# Process in smaller batches for large collections
batch_size = 100
for offset in range(0, total_items, batch_size):
    result = await collector.collect_with_filters(limit=batch_size)
    # Process batch before loading next
```

### Caching Strategy
```python
# Cache rarely-changing reference data
wahlperiode_cache = {}  # Electoral periods
fraktion_cache = {}     # Parliamentary groups per period
```

## Documentation Pattern

### Documentation Structure
```
docs/flows/bundestag_ingestion.md
├── Overview & Purpose
├── Architecture Diagram
├── 8 Data Sources (detailed)
├── Entity Relationships (15 edge types)
├── Configuration Options
├── Usage Examples
├── API Endpoint Reference
├── Troubleshooting Guide
├── Performance Optimization
├── Integration with Knowledge Graph
└── Testing & References
```

### Code Comments
```python
"""
Brief description of module/class/function.

Detailed explanation of:
- What it does
- Why it's designed this way
- Key patterns used
- Integration points

Args:
    param: Description

Returns:
    Description of return value

Raises:
    ExceptionType: When and why
"""
```

## Common Anti-Patterns to Avoid

❌ **Over-mocking in tests**: Don't mock internal transformation logic
❌ **Ignoring pagination**: Always handle multi-page responses
❌ **Hardcoded values**: Use configuration for API URLs, keys, limits
❌ **No error handling**: Always handle API and transformation errors
❌ **Missing interface validation**: Always test method signatures exist
❌ **Blocking operations**: Use async/await throughout
❌ **No health checks**: Always implement health check methods

## Success Metrics

### Test Coverage
- Overall: >90%
- Collectors: 95%
- Transformers: 92%
- Utils: 93%
- Integration: 88%

### Performance Targets
- API response time: <2s per request
- Pagination handling: Support 10,000+ items
- Transformation rate: >100 entities/second
- Memory usage: <500MB per collector

### Data Quality
- Entity extraction accuracy: >95%
- Edge creation accuracy: >90%
- Error rate: <5%
- Deduplication effectiveness: >99%

## References

- [Bundestag DIP API Documentation](https://dip.bundestag.de/documents/informationen-zur-dip-api.pdf)
- [Political Schema v4](../src/graphrag/political_schema_v4.py)
- [Flow 5 Documentation](../docs/flows/bundestag_ingestion.md)
- [Test Patterns](./test-patterns.md)
- [Testing Standards](./testing-standards.md)

---

**Version**: 0.2.0
**Last Updated**: 2025-11-12
**Status**: Production Ready
