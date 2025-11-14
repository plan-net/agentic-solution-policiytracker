# Flow 5c: Page-Level Nodes Quick Reference

## Overview
Flow 5c (Bundestag Drucksache Ingestion) now creates individual page nodes in Neo4j with embeddings for fine-grained semantic search.

**🚀 Smart Resource Management**: Flow 5c now intelligently skips documents that already exist in Neo4j, preventing wasteful reprocessing of PDFs and regeneration of embeddings.

## Quick Start

### Running the Flow

**Kodosumi Configuration**:
```json
{
  "wahlperioden": "20",
  "dokumentart": "Alle",
  "max_drucksachen": 5,
  "extract_full_text": true,
  "max_concurrent_downloads": 3
}
```

### What Gets Created

For each PDF page:
```
DrucksachePage Node
├── page_id: "20/12345_page_1"
├── page_number: 1
├── drucksache_nummer: "20/12345"
├── wahlperiode: 20
├── content: "Full page text..."
└── embedding: [1536 floats]
```

Plus two relationship types:
- `HAS_PAGE`: Parent document → Page
- `NEXT_PAGE`: Page → Next page

## Common Queries

### Get All Pages of a Document
```cypher
MATCH (d:Drucksache {drucksache_nummer: "20/12345"})-[:HAS_PAGE]->(p:DrucksachePage)
RETURN p.page_number, substring(p.content, 0, 200) as preview
ORDER BY p.page_number
```

### Navigate Sequential Pages
```cypher
MATCH path = (p1:DrucksachePage {page_id: "20/12345_page_1"})-[:NEXT_PAGE*]->(pN)
RETURN path
LIMIT 5
```

### Get Page with Context
```cypher
MATCH (prev)-[:NEXT_PAGE]->(current:DrucksachePage {page_id: "20/12345_page_5"})-[:NEXT_PAGE]->(next)
RETURN prev.page_number, current.content, next.page_number
```

### Count Pages per Document
```cypher
MATCH (d:Drucksache)-[:HAS_PAGE]->(p:DrucksachePage)
RETURN d.drucksache_nummer, count(p) as total_pages
ORDER BY total_pages DESC
```

### Find Pages Mentioning Topic
```cypher
MATCH (p:DrucksachePage)
WHERE p.content CONTAINS "Klimaschutz"
RETURN p.drucksache_nummer, p.page_number,
       substring(p.content, 0, 200) as excerpt
LIMIT 10
```

### Check NEXT_PAGE Relationships
```cypher
MATCH (p1:DrucksachePage)-[:NEXT_PAGE]->(p2:DrucksachePage)
WHERE p1.drucksache_nummer = "20/12345"
RETURN p1.page_number, p2.page_number
ORDER BY p1.page_number
```

## Vector Search Setup

### Create Vector Index
```cypher
CREATE VECTOR INDEX drucksache_page_embedding IF NOT EXISTS
FOR (p:DrucksachePage)
ON p.embedding
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 1536,
    `vector.similarity_function`: 'cosine'
  }
}
```

### Vector Similarity Search
```cypher
// Find pages similar to a specific page
MATCH (source:DrucksachePage {page_id: "20/12345_page_1"})
CALL db.index.vector.queryNodes('drucksache_page_embedding', 5, source.embedding)
YIELD node, score
WHERE node.page_id <> source.page_id
RETURN node.drucksache_nummer, node.page_number, score
ORDER BY score DESC
```

## Graph Visualization

### Visualize Document Structure
```cypher
MATCH path = (d:Drucksache {drucksache_nummer: "20/12345"})-[:HAS_PAGE]->(p:DrucksachePage)
OPTIONAL MATCH (p)-[:NEXT_PAGE]->(next:DrucksachePage)
RETURN path
LIMIT 20
```

## Troubleshooting

### No Pages Created?
Check:
1. `extract_full_text: true` in configuration
2. PDFs downloaded successfully
3. OpenAI API key set correctly

### Missing NEXT_PAGE Relationships?
```cypher
// Check if relationships exist
MATCH (p1:DrucksachePage)-[:NEXT_PAGE]->(p2:DrucksachePage)
RETURN count(*) as next_page_count

// Should be: (total_pages - documents_processed)
```

### View Statistics
```cypher
// Count all page nodes
MATCH (p:DrucksachePage)
RETURN count(p) as total_pages

// Count relationships
MATCH (d:Drucksache)-[:HAS_PAGE]->(p:DrucksachePage)
RETURN count(p) as has_page_rels

MATCH ()-[:NEXT_PAGE]->()
RETURN count(*) as next_page_rels
```

## Performance Tips

1. **Start Small**: Use `max_drucksachen: 5` for testing
2. **Monitor API**: Watch OpenAI embedding API usage
3. **Batch Processing**: Process documents in batches during off-peak hours
4. **Index Creation**: Create vector index after bulk processing, not before
5. **⭐ Rerun Optimization**: Flow automatically skips existing documents - safe to rerun without wasting resources!

## Resource Optimization (NEW)

### Smart Duplicate Prevention

Flow 5c now checks if documents exist in Neo4j before downloading PDFs and creating page nodes:

**First Run** (documents don't exist):
```
✅ Downloads all PDFs
✅ Extracts text from each page
✅ Creates page nodes with embeddings
✅ Statistics: "Drucksachen Skipped: 0"
```

**Second Run** (documents already exist):
```
⏭️ Skips all PDF downloads
⏭️ Skips text extraction
⏭️ Skips embedding generation
✅ Statistics: "Drucksachen Skipped: 5"
```

### Resource Savings

When rerunning Flow 5c on existing documents:
- **⏱️ Time Saved**: ~8-14 minutes per 100 documents
- **💰 Cost Saved**: ~$0.50 per 100 documents (10 pages each)
- **🌐 Network**: No redundant PDF downloads
- **💾 Storage**: No duplicate files

### How It Works

1. Before queueing PDF download, Flow checks: `check_drucksache_exists(drucksache_nummer)`
2. If document exists in Neo4j → Skip PDF download and processing
3. If document is new → Download PDF and create page nodes
4. Final report shows: "Drucksachen Skipped (already exist): X"

### Best Practices

- Safe to rerun Flow 5c multiple times on same Wahlperiode
- Use for incremental updates (processes only new documents)
- Monitor "Drucksachen Skipped" in final report to verify optimization working

## Configuration

**Required Environment Variables**:
```bash
OPENAI_API_KEY=your_key_here
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123
```

**Embedding Settings** (src/config.py):
- Model: text-embedding-3-small
- Dimensions: 1536
- Provider: OpenAI

## Cost Estimation

**OpenAI Embeddings** (text-embedding-3-small):
- Cost: ~$0.02 per 1M tokens
- Average page: ~500 tokens
- 100 pages: ~$0.001 (very cheap!)
- 10,000 pages: ~$0.10

## Integration Examples

### Python: Get Page Content
```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password123"))

def get_page_content(drucksache_nummer, page_number):
    with driver.session() as session:
        result = session.run("""
            MATCH (p:DrucksachePage {
                drucksache_nummer: $drucksache_nummer,
                page_number: $page_number
            })
            RETURN p.content as content
        """, drucksache_nummer=drucksache_nummer, page_number=page_number)

        record = result.single()
        return record["content"] if record else None

# Usage
content = get_page_content("20/12345", 1)
print(content)
```

### Python: Semantic Search
```python
from langchain_openai import OpenAIEmbeddings

def search_similar_pages(query_text, limit=5):
    # Create query embedding
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    query_vector = embeddings.embed_query(query_text)

    # Search Neo4j
    with driver.session() as session:
        result = session.run("""
            CALL db.index.vector.queryNodes(
                'drucksache_page_embedding',
                $limit,
                $query_vector
            )
            YIELD node, score
            RETURN node.drucksache_nummer as document,
                   node.page_number as page,
                   node.content as content,
                   score
            ORDER BY score DESC
        """, limit=limit, query_vector=query_vector)

        return [dict(record) for record in result]

# Usage
results = search_similar_pages("Klimaschutzmaßnahmen")
for r in results:
    print(f"{r['document']} Page {r['page']}: Score {r['score']:.3f}")
```

## Next Steps

1. ✅ **Test with small dataset**: Run with `max_drucksachen: 5`
2. ✅ **Verify in Neo4j**: Check nodes and relationships
3. ✅ **Create vector index**: Enable semantic search
4. ✅ **Try queries**: Test the example queries above
5. ✅ **Scale up**: Process larger datasets

## Support

For issues or questions:
1. Check `CHANGELOG_2025-11-14.md` for detailed documentation
2. Review Ray logs: `just ray-logs`
3. Check Neo4j browser: http://localhost:7474
4. Monitor Kodosumi: http://localhost:3370

## Resources

- **Full Changelog**: `CHANGELOG_2025-11-14.md`
- **Neo4j Browser**: http://localhost:7474
- **Kodosumi Admin**: http://localhost:3370 (admin/admin)
- **OpenAI Embeddings**: https://platform.openai.com/docs/guides/embeddings
