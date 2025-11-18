# Markdown Data Ingestion Patterns v0.2.0

## Overview

This document describes the complete pipeline for ingesting markdown documents into the Neo4j knowledge graph via Graphiti temporal knowledge graph system. The pipeline ensures deduplication, preprocessing, intelligent chunking, and structured entity extraction.

## Pipeline Architecture

```
Markdown Files (data/input/)
    ↓
1. File Selection & Discovery
    ↓
2. Deduplication Check (DocumentTracker)
    ↓
3. Preprocessing (link removal, cleaning)
    ↓
4. Chunking (120K tokens, 10% overlap)
    ↓
5. Graphiti Processing (entity extraction)
    ↓
6. Neo4j Storage (temporal knowledge graph)
    ↓
7. Tracking Update (mark processed)
```

## 1. File Selection & Discovery

### Source Directories

Documents are organized by date and type:

```
data/input/
├── news/
│   └── YYYY-MM/
│       └── YYYYMMDD_source_title_hash.md
├── policy/
│   └── YYYY-MM/
│       └── YYYYMMDD_source_title_hash.md
└── documents_md/
    └── *.md (unstructured documents)
```

**Directory Purposes**:
- `news/`: News articles collected via ETL pipelines (date-organized)
- `policy/`: Policy documents and regulations (date-organized)
- `documents_md/`: Manual uploads or unstructured documents (no date hierarchy)

### File Discovery Pattern

```python
from pathlib import Path

def discover_documents(base_path: str = "data/input") -> list[Path]:
    """
    Discover all markdown files in input directories.

    Returns list of Path objects for .md files.
    """
    base = Path(base_path)

    # Find all markdown files recursively
    news_files = list((base / "news").rglob("*.md"))
    policy_files = list((base / "policy").rglob("*.md"))
    documents_files = list((base / "documents_md").rglob("*.md"))

    all_files = news_files + policy_files + documents_files

    return sorted(all_files)  # Deterministic order
```

### File Naming Convention

**Format**: `YYYYMMDD_source_title-slug_hash.md`

- **YYYYMMDD**: Publication date (e.g., `20251117`)
- **source**: Source website slug (e.g., `reuters`, `europa`)
- **title-slug**: Shortened title (max 50 chars)
- **hash**: Short hash for uniqueness (8 chars)

**Example**: `20251117_europa_eu-ai-act-implementation_a3f2b8c9.md`

### Frontmatter Structure

All markdown files include YAML frontmatter:

```yaml
---
title: "Document Title"
url: "https://source.com/article"
published_date: "2025-11-17"
source: "europa.eu"
collection_date: "2025-11-17T19:30:00"
content_type: "policy" or "news"
language: "en"
---

# Document content starts here...
```

## 2. Deduplication with DocumentTracker

**Location**: `src/flows/data_ingestion/document_tracker.py`

### Purpose

Prevents reprocessing of documents that have already been ingested, maintaining a persistent JSON-based tracking file.

### Tracking File Structure

**Location**: `data/processed_documents.json`

```json
{
  "data/input/news/2025-11/20251117_reuters_article_abc123.md": {
    "episode_uuids": ["uuid1", "uuid2", "uuid3"],
    "primary_episode_id": "uuid1",
    "processed_at": "2025-11-17T19:30:00",
    "status": "completed",
    "entity_count": 42,
    "relationship_count": 156,
    "is_chunked": true,
    "total_chunks": 3,
    "successful_chunks": 3,
    "chunking_strategy": "hybrid",
    "chunk_summary": [
      {
        "chunk_index": 0,
        "episode_uuid": "uuid1",
        "entities": 15,
        "relationships": 52,
        "boundary_type": "header"
      },
      {
        "chunk_index": 1,
        "episode_uuid": "uuid2",
        "entities": 18,
        "relationships": 67,
        "boundary_type": "header"
      },
      {
        "chunk_index": 2,
        "episode_uuid": "uuid3",
        "entities": 9,
        "relationships": 37,
        "boundary_type": "paragraph"
      }
    ]
  },
  "data/input/policy/2025-11/20251115_commission_policy_def456.md": {
    "episode_id": "uuid4",
    "processed_at": "2025-11-15T10:15:00",
    "status": "failed",
    "error": "Neo4j connection timeout"
  }
}
```

### Usage Pattern

```python
from src.flows.data_ingestion.document_tracker import DocumentTracker

# Initialize tracker
tracker = DocumentTracker("data/processed_documents.json")

# Check if document already processed
if tracker.is_processed(doc_path):
    logger.info(f"Skipping already processed: {doc_path}")
    continue

# Process document...
# (preprocessing, chunking, Graphiti)

# Mark as processed with chunk details
tracker.mark_processed_chunked(
    doc_path=doc_path,
    episode_uuids=["uuid1", "uuid2", "uuid3"],
    total_chunks=3,
    entity_count=42,
    relationship_count=156,
    chunk_results=chunk_results
)

# Or mark as failed
try:
    process_document(doc_path)
except Exception as e:
    tracker.mark_failed(doc_path, str(e))
```

### Tracker Features

**1. Concurrent Access Safety**
- File locking with `fcntl.flock()` for multi-process access
- Atomic writes with temp file + rename
- Smart merge strategy (only overwrites this actor's documents)

**2. Status Tracking**
- `completed`: Successfully processed
- `failed`: Processing failed with error details

**3. Statistics**
```python
stats = tracker.get_stats()
# Returns:
{
    "total_processed": 150,
    "completed": 145,
    "failed": 5,
    "success_rate": 96.7,
    "total_entities": 6300,
    "total_relationships": 18900
}
```

**4. Failed Document Recovery**
```python
# Get list of failed documents for retry
failed = tracker.get_failed_documents()
for doc in failed:
    print(f"{doc['path']}: {doc['error']}")
```

### Clearing Tracking Data

```python
# Clear all tracking (used with clear_data option)
count = tracker.clear_all()
logger.info(f"Cleared tracking for {count} documents")
```

## 3. Document Preprocessing

**Location**: `src/flows/data_ingestion/document_preprocessor.py`

### Purpose

Cleans scraped web content to improve knowledge graph extraction quality by removing noise and preserving semantic content.

### Preprocessing Pipeline

```python
from src.flows.data_ingestion.document_preprocessor import preprocess_document

# Full preprocessing (default: link removal enabled)
clean_content = preprocess_document(content, enable_link_removal=True)

# Preprocessing without link removal
clean_content = preprocess_document(content, enable_link_removal=False)
```

### Step-by-Step Process

#### Step 1: Frontmatter Extraction

Preserves YAML frontmatter while cleaning body:

```python
def extract_frontmatter(content: str) -> Tuple[str, str]:
    """
    Extract YAML frontmatter from document.

    Returns: (frontmatter, body)
    """
    pattern = r'^---\n(.*?)\n---\n(.*)$'
    match = re.match(pattern, content, re.DOTALL)

    if match:
        return match.group(1), match.group(2)
    return "", content
```

#### Step 2: Link Removal (Optional)

Removes various types of links that add noise:

```python
def remove_links(text: str) -> str:
    """
    Remove links while preserving semantic content.

    Removes:
    - Image links: ![alt](url) → (removed entirely)
    - Markdown links: [text](url) → (removed entirely)
    - Bare URLs: https://... → (removed)
    - www URLs: www.example.com → (removed)
    """
    # Remove image links
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)

    # Remove markdown links entirely (both text and URL)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', '', text)

    # Remove standalone URLs
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'www\.\S+', '', text)

    return text
```

**Why remove links?**
- Reduces token count (links can be very long)
- Eliminates navigation noise from scraped content
- Focuses extraction on semantic content
- Source URL preserved in frontmatter

#### Step 3: Duplicate Line Removal

Removes consecutive duplicate lines common in scraped content:

```python
def remove_duplicate_lines(text: str) -> str:
    """
    Remove consecutive duplicate lines.

    Common in scraped content where navigation elements repeat.
    Preserves empty lines for spacing.
    """
    lines = text.split('\n')
    deduplicated = []
    prev_line = None

    for line in lines:
        stripped = line.strip()
        # Keep if different from previous or is empty
        if stripped != prev_line or not stripped:
            deduplicated.append(line)
            prev_line = stripped

    return '\n'.join(deduplicated)
```

#### Step 4: Whitespace Cleaning

Normalizes excessive whitespace:

```python
def clean_whitespace(text: str) -> str:
    """
    Clean excessive whitespace.

    - Multiple blank lines → single blank line
    - Trailing whitespace → removed
    - Leading/trailing document whitespace → preserved
    """
    # Replace multiple blank lines with double newline
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

    # Remove trailing whitespace from each line
    lines = [line.rstrip() for line in text.split('\n')]

    return '\n'.join(lines)
```

#### Step 5: Document Reassembly

Combines cleaned body with original frontmatter:

```python
# Reassemble document
if frontmatter:
    return f"---\n{frontmatter}\n---\n\n{body}"
return body
```

### Preprocessing Benefits

1. **Reduced Token Count**: Links and duplicates consume many tokens
2. **Improved Extraction**: Less noise → better entity recognition
3. **Preserved Metadata**: Frontmatter retained with source URLs
4. **Configurable**: Link removal can be disabled if needed

### Example Transformation

**Before Preprocessing**:
```markdown
---
title: "EU AI Act"
url: "https://example.com/article"
---

# EU AI Act Updates

Visit [our website](https://example.com) for more.
Read more at https://example.com/details

Navigation: Home | About | Contact
Navigation: Home | About | Contact

The EU has approved the AI Act.


The regulation introduces new requirements.
```

**After Preprocessing**:
```markdown
---
title: "EU AI Act"
url: "https://example.com/article"
---

# EU AI Act Updates

Navigation: Home | About | Contact

The EU has approved the AI Act.

The regulation introduces new requirements.
```

## 4. Document Chunking

**Location**: `src/flows/data_ingestion/document_chunker.py`

### Purpose

Splits large documents into manageable chunks that fit within Graphiti's token limits while preserving semantic coherence and document structure.

### Chunking Strategy: Three-Tier Hybrid Approach

```
Tier 1: Semantic Chunking (by markdown headers)
    ↓ (if chunk > 120K tokens)
Tier 2: Paragraph Chunking (by paragraph boundaries)
    ↓ (if chunk > 120K tokens)
Tier 3: Fixed-Size Chunking (with 10% overlap)
```

### Configuration

```python
from src.flows.data_ingestion.document_chunker import HybridDocumentChunker

# Initialize with configuration
chunker = HybridDocumentChunker(
    max_tokens=120000,      # Safety margin below 128K limit
    overlap_ratio=0.10      # 10% overlap between chunks
)

# Create chunks
chunks = chunker.create_chunks(content)
```

### Default Configuration

- **Max tokens**: 120,000 (safety margin below GPT-4 128K limit)
- **Overlap ratio**: 10% (12,000 tokens overlap)
- **Min chunk tokens**: 1,000 (minimum viable chunk)

### Tier 1: Semantic Chunking by Headers

**Priority**: Highest (preserves document structure)

Splits by markdown headers using LangChain's `MarkdownHeaderTextSplitter`:

```python
def _split_by_headers(self, body: str) -> List[Dict]:
    """
    Split document by markdown headers.

    Splits on: #, ##, ### (H1, H2, H3)
    Preserves headers in content for context
    """
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ],
        strip_headers=False  # Keep headers for context
    )

    docs = header_splitter.split_text(body)

    return [
        {
            "text": doc.page_content,
            "metadata": doc.metadata,
            "boundary_type": "header"
        }
        for doc in docs
    ]
```

**Example**:
```markdown
# Introduction
Content for introduction...

## Background
Content for background...

### Historical Context
Content for context...
```

Produces 3 semantic chunks with preserved structure.

### Tier 2: Paragraph Chunking

**Used when**: Semantic chunks exceed token limit

Uses LangChain's `RecursiveCharacterTextSplitter` with intelligent separators:

```python
def _split_by_paragraphs(self, text: str, metadata: dict) -> List[Dict]:
    """
    Split by paragraph boundaries.

    Separators in priority order:
    1. \n\n (paragraph break)
    2. \n (line break)
    3. . (sentence end)
    4. (space)
    5. "" (character-level fallback)
    """
    paragraph_splitter = RecursiveCharacterTextSplitter(
        chunk_size=120000 * 4,  # Character estimate
        chunk_overlap=12000 * 4,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=count_tokens  # Actual token counting
    )

    docs = paragraph_splitter.create_documents([text])

    return [
        {
            "text": doc.page_content,
            "metadata": metadata,
            "boundary_type": "paragraph"
        }
        for doc in docs
    ]
```

### Tier 3: Fixed-Size Chunking with Overlap

**Used when**: Paragraph chunks still exceed limit (last resort)

**Guarantees**: All chunks fit within token limit

```python
def _fixed_size_split(self, text: str, metadata: dict) -> List[Dict]:
    """
    Fixed-size splitting with overlap.

    Uses tiktoken for precise token-level splitting.
    Ensures 10% overlap between chunks for context.
    """
    encoding = tiktoken.encoding_for_model("gpt-4")
    tokens = encoding.encode(text)
    total_tokens = len(tokens)

    chunks = []
    start = 0

    while start < total_tokens:
        end = min(start + self.max_tokens, total_tokens)
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens)

        chunks.append({
            "text": chunk_text,
            "metadata": metadata,
            "boundary_type": "fixed_size",
            "token_range": (start, end)
        })

        # Move forward with overlap
        start = end - self.overlap_tokens

    return chunks
```

### Chunk Output Structure

Each chunk includes comprehensive metadata:

```python
{
    "text": "Chunk content...",
    "chunk_index": 0,
    "total_chunks": 3,
    "has_frontmatter": True,  # First chunk only
    "token_count": 45000,
    "boundary_type": "header",  # or "paragraph", "fixed_size"
    "metadata": {
        "Header 1": "Introduction",
        "Header 2": "Background"
    }
}
```

### Frontmatter Handling

**Frontmatter is prepended to first chunk only**:

```python
# Step 1: Extract frontmatter from full document
frontmatter, body = extract_frontmatter(content)

# Step 2: Chunk the body
chunks = chunker.create_chunks(body)

# Step 3: Add frontmatter to first chunk
if frontmatter and chunks:
    chunks[0]["text"] = f"---\n{frontmatter}\n---\n\n{chunks[0]['text']}"
    chunks[0]["token_count"] = count_tokens(chunks[0]["text"])
```

### Chunking Benefits

1. **Structure Preservation**: Semantic boundaries preserved when possible
2. **Token Guarantee**: All chunks guaranteed to fit within limits
3. **Context Maintenance**: 10% overlap maintains context across boundaries
4. **Intelligent Fallback**: Three-tier strategy ensures success
5. **Metadata Rich**: Extensive metadata for debugging and analysis

### Example Chunking Output

**Input**: 350K token document with 5 major sections

**Output**:
```python
[
    {
        "chunk_index": 0,
        "total_chunks": 4,
        "token_count": 118500,
        "boundary_type": "header",
        "has_frontmatter": True,
        "metadata": {"Header 1": "Introduction"}
    },
    {
        "chunk_index": 1,
        "total_chunks": 4,
        "token_count": 119200,
        "boundary_type": "header",
        "metadata": {"Header 1": "Background"}
    },
    {
        "chunk_index": 2,
        "total_chunks": 4,
        "token_count": 85000,
        "boundary_type": "paragraph",  # Section was too large
        "metadata": {"Header 1": "Analysis"}
    },
    {
        "chunk_index": 3,
        "total_chunks": 4,
        "token_count": 27300,
        "boundary_type": "header",
        "metadata": {"Header 1": "Conclusion"}
    }
]
```

## 5. Graphiti Processing & Neo4j Storage

**Location**: `src/flows/data_ingestion/document_processor.py`

### Purpose

Processes chunks through Graphiti temporal knowledge graph system to extract entities and relationships, storing them in Neo4j with custom political schema.

### Graphiti Integration Architecture

```python
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from src.graphrag.political_schema_v4 import (
    ENTITY_TYPE_REGISTRY_V4,  # 28 entity types
    EDGE_TYPE_REGISTRY_V4,    # 52 edge types
    EDGE_TYPE_MAP_V4,         # Valid source-target-edge patterns
)

# Initialize Graphiti client
graphiti_client = Graphiti(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="password123",
    llm_client=llm_client  # APISIX-routed LLM
)

await graphiti_client.build_indices_and_constraints()
```

### Ray-Based Parallel Processing

Uses Ray actors for concurrent document processing:

```python
@ray.remote
class DocumentProcessorActor:
    """
    Ray actor for parallel document processing.

    Each actor:
    - Maintains own Graphiti client
    - Processes documents independently
    - Reports progress via actor_id
    """

    def __init__(self, actor_id: int):
        self.actor_id = actor_id
        self.graphiti_client = None  # Initialized in async init

    async def initialize(self):
        """Initialize Graphiti client with APISIX routing."""
        from src.flows.shared.apisix_llm_client import create_graphiti_apisix_config

        context = AgentContext(
            agent_type="kodosumi_flow",
            agent_name="graphiti_document_processor",
            flow_name="data_ingestion"
        )
        llm_client, note = create_graphiti_apisix_config(context)

        self.graphiti_client = Graphiti(
            NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD,
            llm_client=llm_client
        )
        await self.graphiti_client.build_indices_and_constraints()
```

### Chunk Processing with Chain Linking

Chunks are processed sequentially with chain linking to maintain document coherence:

```python
async def process_single_document(self, doc_path: Path) -> Dict:
    """
    Process single document through Graphiti.

    Steps:
    1. Read and preprocess document
    2. Chunk document (120K tokens, 10% overlap)
    3. Process each chunk as Graphiti episode
    4. Link chunks via previous_episode_uuids
    5. Aggregate metrics across chunks
    """
    # Step 1: Read and preprocess
    content = read_document(doc_path)
    content = preprocess_document(content, enable_link_removal=True)

    # Step 2: Chunk document
    chunker = HybridDocumentChunker(max_tokens=120000, overlap_ratio=0.10)
    chunks = chunker.create_chunks(content)

    # Step 3: Process each chunk with chain linking
    episode_uuids = []
    previous_episode_uuid = None
    total_entities = 0
    total_relationships = 0
    chunk_results = []

    for chunk_index, chunk in enumerate(chunks):
        chunk_text = chunk["text"]
        chunk_token_count = chunk["token_count"]

        # Generate episode name
        episode_name = f"{generate_episode_name(doc_path, datetime.now())}_chunk_{chunk_index}"
        source_description = f"Political document chunk {chunk_index + 1}/{len(chunks)}: {doc_path.name}"
        reference_time = extract_document_date(chunk_text) or datetime.now()

        # Chain linking: link to previous chunk
        previous_episodes = [previous_episode_uuid] if previous_episode_uuid else None

        # Process through Graphiti
        result = await self.graphiti_client.add_episode(
            name=episode_name,
            episode_body=chunk_text,
            source_description=source_description,
            reference_time=reference_time,
            source=EpisodeType.text,
            group_id=GROUP_ID,  # "political_monitoring_v2"
            entity_types=ENTITY_TYPE_REGISTRY_V4,
            edge_types=EDGE_TYPE_REGISTRY_V4,
            edge_type_map=EDGE_TYPE_MAP_V4,
            previous_episode_uuids=previous_episodes,
        )

        # Track episode UUID for chain linking
        episode_uuid = result.episode.uuid if hasattr(result, "episode") else None
        episode_uuids.append(episode_uuid)
        previous_episode_uuid = episode_uuid

        # Aggregate metrics
        entity_count = len(result.nodes) if hasattr(result, "nodes") else 0
        relationship_count = len(result.edges) if hasattr(result, "edges") else 0
        total_entities += entity_count
        total_relationships += relationship_count

        chunk_results.append({
            "chunk_index": chunk_index,
            "episode_uuid": episode_uuid,
            "entities": entity_count,
            "relationships": relationship_count,
            "tokens": chunk_token_count,
            "boundary_type": chunk.get("boundary_type", "unknown"),
        })

    return {
        "doc_path": str(doc_path),
        "episode_uuids": episode_uuids,
        "total_chunks": len(chunks),
        "total_entities": total_entities,
        "total_relationships": total_relationships,
        "chunk_results": chunk_results,
    }
```

### Chain Linking Pattern

**Purpose**: Maintains document coherence across chunks

```python
# Chunk 0 (first chunk)
result1 = await graphiti_client.add_episode(
    name="doc_chunk_0",
    previous_episode_uuids=None  # First chunk has no predecessor
)

# Chunk 1 (links to chunk 0)
result2 = await graphiti_client.add_episode(
    name="doc_chunk_1",
    previous_episode_uuids=[result1.episode.uuid]  # Links to previous
)

# Chunk 2 (links to chunk 1)
result3 = await graphiti_client.add_episode(
    name="doc_chunk_2",
    previous_episode_uuids=[result2.episode.uuid]  # Links to previous
)
```

**Result**: Sequential chain of episodes in temporal graph:
```
Episode 0 → Episode 1 → Episode 2
```

### Custom Political Schema (v4.0)

**28 Entity Types** (20 v3 + 8 German Bundestag):

**Legislative Process**:
- LegislativeProposal, Policy, Regulation, Directive, Amendment

**Outcomes**:
- EnforcementAction, CourtRuling, ComplianceRequirement

**Actors**:
- Politician, PoliticalParty, Lobbyist, NGO, IndustryAssociation

**Business**:
- Company, Industry, Sector

**Process Tracking**:
- PolicyStage, Consultation, Hearing

**Geographic**:
- Jurisdiction, Region, Country

**Technical/Legal**:
- LegalFramework, PolicyArea

**German Bundestag (v4)**:
- Drucksache, DrucksachePage, Plenarprotokoll, Vorgang
- Vorgangsposition, Aktivitaet, Wahlperiode, BundestagPerson, BundestagFraktion

**52 Edge Types** (37 v3 + 15 German Bundestag):

Categories: Jurisdiction, Legislative, EU-Germany, Influence, Business, Regulatory, Temporal, Reference, Stakeholder, German-specific

See `.claude/graphiti-patterns.md` for complete schema details.

### APISIX LLM Routing

**Purpose**: Cost tracking and intelligent routing

```python
from src.flows.shared.apisix_llm_client import create_graphiti_apisix_config

context = AgentContext(
    agent_type="kodosumi_flow",
    agent_name="graphiti_document_processor",
    flow_name="data_ingestion"
)

llm_client, routing_note = create_graphiti_apisix_config(context)
# Routes to: OpenAI via APISIX gateway
# Tracks: Token usage, costs, request counts
```

### Episode Group Organization

All political documents belong to same group:

```python
GROUP_ID = "political_monitoring_v2"

result = await graphiti_client.add_episode(
    name=episode_name,
    group_id=GROUP_ID,  # Organizes episodes
    ...
)
```

### Processing Results

Returns comprehensive metrics for tracking:

```python
{
    "doc_path": "data/input/news/2025-11/20251117_reuters_article.md",
    "episode_uuids": ["uuid1", "uuid2", "uuid3"],
    "total_chunks": 3,
    "total_entities": 42,
    "total_relationships": 156,
    "chunk_results": [
        {
            "chunk_index": 0,
            "episode_uuid": "uuid1",
            "entities": 15,
            "relationships": 52,
            "tokens": 118500,
            "boundary_type": "header"
        },
        {
            "chunk_index": 1,
            "episode_uuid": "uuid2",
            "entities": 18,
            "relationships": 67,
            "tokens": 119200,
            "boundary_type": "header"
        },
        {
            "chunk_index": 2,
            "episode_uuid": "uuid3",
            "entities": 9,
            "relationships": 37,
            "tokens": 85000,
            "boundary_type": "paragraph"
        }
    ]
}
```

## Complete End-to-End Example

### Scenario: Processing 10 News Articles

```python
from pathlib import Path
from src.flows.data_ingestion.document_tracker import DocumentTracker
from src.flows.data_ingestion.document_preprocessor import preprocess_document
from src.flows.data_ingestion.document_chunker import HybridDocumentChunker
import ray

# Step 1: Discover documents
news_files = list(Path("data/input/news/2025-11").glob("*.md"))
logger.info(f"Discovered {len(news_files)} news files")

# Step 2: Initialize tracker
tracker = DocumentTracker("data/processed_documents.json")

# Step 3: Filter already processed
unprocessed = [f for f in news_files if not tracker.is_processed(f)]
logger.info(f"Found {len(unprocessed)} unprocessed documents")

# Step 4: Initialize Ray actors for parallel processing
num_actors = 3
actors = [
    DocumentProcessorActor.remote(actor_id=i)
    for i in range(num_actors)
]

# Initialize actors
await asyncio.gather(*[actor.initialize.remote() for actor in actors])

# Step 5: Distribute work to actors
tasks = []
for i, doc_path in enumerate(unprocessed):
    actor = actors[i % num_actors]  # Round-robin distribution
    task = actor.process_single_document.remote(doc_path)
    tasks.append((doc_path, task))

# Step 6: Process and track results
for doc_path, task in tasks:
    try:
        result = await task

        # Step 7: Mark as processed in tracker
        tracker.mark_processed_chunked(
            doc_path=doc_path,
            episode_uuids=result["episode_uuids"],
            total_chunks=result["total_chunks"],
            entity_count=result["total_entities"],
            relationship_count=result["total_relationships"],
            chunk_results=result["chunk_results"]
        )

        logger.info(
            f"Processed {doc_path.name}: "
            f"{result['total_entities']} entities, "
            f"{result['total_relationships']} relationships, "
            f"{result['total_chunks']} chunks"
        )

    except Exception as e:
        # Step 8: Mark as failed
        tracker.mark_failed(doc_path, str(e))
        logger.error(f"Failed to process {doc_path.name}: {e}")

# Step 9: Display statistics
stats = tracker.get_stats()
print(f"""
Processing Complete:
- Total processed: {stats['total_processed']}
- Completed: {stats['completed']}
- Failed: {stats['failed']}
- Success rate: {stats['success_rate']:.1f}%
- Total entities: {stats['total_entities']}
- Total relationships: {stats['total_relationships']}
""")
```

## Performance Considerations

### Processing Speed

**Typical rates** (depends on document size and LLM speed):
- Small documents (<10K tokens): 10-20 docs/minute
- Medium documents (10-50K tokens): 5-10 docs/minute
- Large documents (>50K tokens, chunked): 2-5 docs/minute

### Parallel Processing

**Ray actors** enable concurrent processing:
- 3 actors: ~3x throughput
- 5 actors: ~5x throughput
- Limited by: LLM API rate limits, Neo4j write capacity

### Token Optimization

**Preprocessing reduces tokens**:
- Link removal: -10% to -30% tokens
- Duplicate removal: -5% to -15% tokens
- Whitespace cleaning: -2% to -5% tokens
- **Total reduction**: ~15-50% tokens

**Cost impact**: Significant savings on LLM API costs

### Memory Usage

**Per Ray actor**:
- Base: ~500MB
- Graphiti client: ~200MB
- Document processing: ~100-500MB (depends on doc size)
- **Total**: ~1-1.5GB per actor

**Configuration** (in config.yaml):
```yaml
ray_actor_options:
  num_cpus: 2
  memory: 4000000000  # 4GB for document processing
```

## Troubleshooting

### Common Issues

**1. Neo4j Connection Errors**
```
Error: ServiceUnavailable: Connection refused
```
**Solution**: Check Neo4j status: `docker ps | grep neo4j`

**2. Chunk Size Errors**
```
Error: Token count exceeds limit (130000 > 128000)
```
**Solution**: Reduce `max_tokens` in chunker config to 115000

**3. Tracking File Corruption**
```
Error: JSONDecodeError in tracking file
```
**Solution**: Tracker auto-recovers, but verify with `cat data/processed_documents.json`

**4. Ray Actor Crashes**
```
Error: ActorDiedError
```
**Solution**: Check Ray logs: `tail -50 /tmp/ray/session_latest/logs/worker*.err`

### Debug Mode

Enable detailed logging:

```python
import structlog
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Structlog debug
logger = structlog.get_logger()
logger.debug("Processing document", doc_path=str(doc_path), chunk_count=len(chunks))
```

### Monitoring Progress

Use tracer for real-time progress in Kodosumi:

```python
await tracer.markdown(f"📄 Processing document {i+1}/{total}")
await tracer.markdown(f"🔍 Preprocessing: {len(content)} → {len(clean_content)} chars")
await tracer.markdown(f"✂️ Chunking: {len(chunks)} chunks")
await tracer.markdown(f"🧠 Graphiti: {entity_count} entities, {rel_count} relationships")
```

## Best Practices

### 1. Always Use Preprocessing
- Reduces tokens → lower costs
- Improves extraction quality
- Enable link removal by default

### 2. Monitor Tracker Statistics
```python
# Check stats regularly
stats = tracker.get_stats()
if stats["success_rate"] < 90:
    logger.warning("Low success rate, investigate failures")
    failed = tracker.get_failed_documents()
    # Review and retry
```

### 3. Use Appropriate Parallelism
- Small batch (<50 docs): 2-3 actors
- Medium batch (50-500 docs): 3-5 actors
- Large batch (>500 docs): 5-10 actors

### 4. Chunk Size Tuning
- **Default 120K tokens**: Safe for most documents
- **Reduce to 100K**: If seeing token limit errors
- **Increase overlap to 15%**: For highly interconnected documents

### 5. Clear Tracking Selectively
```python
# Clear only failed documents for retry
failed = tracker.get_failed_documents()
for doc in failed:
    del tracker.processed_docs[doc["path"]]
tracker._save_tracking()
```

### 6. Verify Chain Linking
```cypher
// Neo4j query to verify chunk chains
MATCH (e1:Episode)-[:NEXT_EPISODE]->(e2:Episode)
WHERE e1.name CONTAINS 'doc_name'
RETURN e1.name, e2.name
ORDER BY e1.name
```

## Integration with Flows

### Kodosumi Flow Integration

**Flow**: `data_ingestion` (Flow 1)

**Location**: `src/flows/data_ingestion/app.py` + `processor.py`

**Usage**:
```python
# processor.py entrypoint
async def process_documents(inputs: dict, tracer: Tracer):
    # Uses all components:
    # - DocumentTracker for deduplication
    # - preprocess_document for cleaning
    # - HybridDocumentChunker for chunking
    # - DocumentProcessorActor for Graphiti

    # Returns core.response.Markdown with statistics
```

### Airflow ETL Integration

**DAG**: Policy collection → Markdown files → Ingestion flow

```python
# ETL writes to: data/input/policy/YYYY-MM/
# Flow processes: Unprocessed files from input directories
# Tracking prevents: Duplicate processing
```

## References

- **Graphiti Documentation**: Temporal knowledge graph patterns in `.claude/graphiti-patterns.md`
- **Political Schema v4**: Entity and edge definitions in `src/graphrag/political_schema_v4.py`
- **Kodosumi Patterns**: Flow deployment in `.claude/kodosumi-patterns.md`
- **Ray Deployment**: Parallel processing in `.claude/ray-deployment-patterns.md`

---

**Version**: 1.0
**Created**: 2025-11-17
**Status**: Production Ready
