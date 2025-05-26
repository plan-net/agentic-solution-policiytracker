"""Build and maintain political domain knowledge graph in Neo4j."""

import asyncio
from typing import Any, Dict, List, Optional

import structlog
from neo4j import AsyncGraphDatabase, AsyncSession

logger = structlog.get_logger()


class PoliticalKnowledgeBuilder:
    """Build and maintain political domain knowledge graph."""

    def __init__(self, uri: str, username: str, password: str, database: str = "neo4j"):
        self.uri = uri
        self.database = database
        self.driver = AsyncGraphDatabase.driver(uri, auth=(username, password))
        logger.info("Neo4j knowledge builder initialized", uri=uri, database=database)

    async def __aenter__(self):
        """Async context manager entry."""
        await self.init_schema()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close Neo4j driver connection."""
        await self.driver.close()

    async def init_schema(self):
        """Initialize graph schema with constraints and indexes."""
        try:
            async with self.driver.session(database=self.database) as session:
                # Create uniqueness constraints
                constraints = [
                    # Document constraints
                    "CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
                    # Chunk constraints  
                    "CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE",
                    # Entity constraints
                    "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
                    # Regulation constraints
                    "CREATE CONSTRAINT regulation_id_unique IF NOT EXISTS FOR (r:Regulation) REQUIRE r.id IS UNIQUE",
                    # Topic constraints
                    "CREATE CONSTRAINT topic_id_unique IF NOT EXISTS FOR (t:Topic) REQUIRE t.id IS UNIQUE",
                ]

                for constraint in constraints:
                    try:
                        await session.run(constraint)
                        logger.debug(f"Created constraint: {constraint.split(' ')[2]}")
                    except Exception as e:
                        if "already exists" not in str(e):
                            logger.error(f"Failed to create constraint", constraint=constraint, error=str(e))

                # Create indexes for performance
                indexes = [
                    # Document indexes
                    "CREATE INDEX document_date IF NOT EXISTS FOR (d:Document) ON (d.date)",
                    "CREATE INDEX document_type IF NOT EXISTS FOR (d:Document) ON (d.type)",
                    # Entity indexes
                    "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)",
                    "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)",
                    # Regulation indexes
                    "CREATE INDEX regulation_jurisdiction IF NOT EXISTS FOR (r:Regulation) ON (r.jurisdiction)",
                    "CREATE INDEX regulation_status IF NOT EXISTS FOR (r:Regulation) ON (r.status)",
                ]

                for index in indexes:
                    try:
                        await session.run(index)
                        logger.debug(f"Created index: {index.split(' ')[2]}")
                    except Exception as e:
                        if "already exists" not in str(e):
                            logger.error(f"Failed to create index", index=index, error=str(e))

                # Note: Vector index creation would happen here once embeddings are ready
                # For now, we'll add it as a placeholder comment
                """
                CREATE VECTOR INDEX chunk_embeddings IF NOT EXISTS
                FOR (c:Chunk) ON (c.embedding)
                OPTIONS {indexConfig: {
                    `vector.dimensions`: 1536,
                    `vector.similarity_function`: 'cosine'
                }}
                """

                logger.info("Neo4j schema initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize Neo4j schema", error=str(e))
            raise

    async def create_document_node(self, session: AsyncSession, document_data: Dict[str, Any]) -> str:
        """Create or update a document node."""
        query = """
        MERGE (d:Document {id: $document_id})
        SET d.path = $path,
            d.title = $title,
            d.type = $type,
            d.source = $source,
            d.extracted_at = datetime($extracted_at),
            d.size_bytes = $size_bytes,
            d.word_count = $word_count
        RETURN d.id as document_id
        """
        
        result = await session.run(
            query,
            document_id=document_data["document_id"],
            path=document_data.get("path", ""),
            title=document_data.get("title", document_data.get("path", "").split("/")[-1]),
            type=document_data.get("type", "unknown"),
            source=document_data.get("container", "unknown"),
            extracted_at=document_data.get("extracted_at"),
            size_bytes=document_data.get("size_bytes", 0),
            word_count=document_data.get("word_count", 0),
        )
        
        record = await result.single()
        return record["document_id"]

    async def create_chunk_nodes(self, session: AsyncSession, chunks: List[Dict[str, Any]]):
        """Create chunk nodes and link to document."""
        query = """
        UNWIND $chunks as chunk
        MATCH (d:Document {id: chunk.document_id})
        MERGE (c:Chunk {id: chunk.chunk_id})
        SET c.text = chunk.text,
            c.position = chunk.position,
            c.chunk_index = chunk.chunk_index,
            c.tokens = size(split(chunk.text, ' '))
        MERGE (d)-[:HAS_CHUNK {position: chunk.position}]->(c)
        RETURN count(c) as chunks_created
        """
        
        result = await session.run(query, chunks=chunks)
        record = await result.single()
        return record["chunks_created"]

    async def process_document_batch(self, documents: List[Dict[str, Any]], chunks: List[Dict[str, Any]]):
        """Process a batch of documents and their chunks."""
        try:
            async with self.driver.session(database=self.database) as session:
                # Group chunks by document
                chunks_by_doc = {}
                for chunk in chunks:
                    doc_id = chunk["document_id"]
                    if doc_id not in chunks_by_doc:
                        chunks_by_doc[doc_id] = []
                    chunks_by_doc[doc_id].append(chunk)

                # Process each document
                for doc in documents:
                    doc_id = doc["document_id"]
                    
                    # Create document node
                    await self.create_document_node(session, doc)
                    
                    # Create associated chunks
                    if doc_id in chunks_by_doc:
                        await self.create_chunk_nodes(session, chunks_by_doc[doc_id])
                        logger.info(
                            "Document processed",
                            document_id=doc_id,
                            chunks_count=len(chunks_by_doc[doc_id]),
                        )

        except Exception as e:
            logger.error("Failed to process document batch", error=str(e))
            raise

    async def find_similar_documents(self, document_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar documents based on shared entities and topics."""
        query = """
        MATCH (d1:Document {id: $document_id})
        MATCH (d1)-[:MENTIONS|:COVERS]->(shared)<-[:MENTIONS|:COVERS]-(d2:Document)
        WHERE d1 <> d2
        WITH d2, count(DISTINCT shared) as similarity_score
        ORDER BY similarity_score DESC
        LIMIT $limit
        RETURN d2.id as document_id,
               d2.title as title,
               d2.type as type,
               similarity_score
        """
        
        async with self.driver.session(database=self.database) as session:
            result = await session.run(query, document_id=document_id, limit=limit)
            return await result.data()

    async def get_document_context(self, document_id: str) -> Dict[str, Any]:
        """Get comprehensive context for a document from the graph."""
        context = {
            "document_id": document_id,
            "entities": [],
            "regulations": [],
            "topics": [],
            "related_documents": [],
        }
        
        async with self.driver.session(database=self.database) as session:
            # Get entities mentioned in the document
            entities_query = """
            MATCH (d:Document {id: $document_id})-[:MENTIONS]->(e:Entity)
            RETURN e.id as id, e.name as name, e.type as type
            ORDER BY e.name
            """
            entities_result = await session.run(entities_query, document_id=document_id)
            context["entities"] = await entities_result.data()
            
            # Get regulations referenced
            regulations_query = """
            MATCH (d:Document {id: $document_id})-[:REFERENCES]->(r:Regulation)
            RETURN r.id as id, r.name as name, r.jurisdiction as jurisdiction
            ORDER BY r.name
            """
            regulations_result = await session.run(regulations_query, document_id=document_id)
            context["regulations"] = await regulations_result.data()
            
            # Get topics covered
            topics_query = """
            MATCH (d:Document {id: $document_id})-[:COVERS]->(t:Topic)
            RETURN t.id as id, t.name as name, t.description as description
            ORDER BY t.name
            """
            topics_result = await session.run(topics_query, document_id=document_id)
            context["topics"] = await topics_result.data()
            
            # Get related documents
            context["related_documents"] = await self.find_similar_documents(document_id)
            
        return context

    async def get_graph_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge graph."""
        query = """
        CALL {
            MATCH (d:Document)
            RETURN count(d) as document_count
        }
        CALL {
            MATCH (c:Chunk)
            RETURN count(c) as chunk_count
        }
        CALL {
            MATCH (e:Entity)
            RETURN count(e) as entity_count
        }
        CALL {
            MATCH (r:Regulation)
            RETURN count(r) as regulation_count
        }
        CALL {
            MATCH (t:Topic)
            RETURN count(t) as topic_count
        }
        RETURN document_count, chunk_count, entity_count, regulation_count, topic_count
        """
        
        async with self.driver.session(database=self.database) as session:
            result = await session.run(query)
            record = await result.single()
            
            if record:
                return {
                    "documents": record["document_count"],
                    "chunks": record["chunk_count"],
                    "entities": record["entity_count"],
                    "regulations": record["regulation_count"],
                    "topics": record["topic_count"],
                }
            else:
                return {
                    "documents": 0,
                    "chunks": 0,
                    "entities": 0,
                    "regulations": 0,
                    "topics": 0,
                }