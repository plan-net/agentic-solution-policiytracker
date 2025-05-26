"""Build and maintain political domain knowledge graph using Neo4j GraphRAG."""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
from neo4j import GraphDatabase
from neo4j_graphrag.embeddings import OpenAIEmbeddings, SentenceTransformerEmbeddings
from neo4j_graphrag.experimental.components.schema import SchemaBuilder
from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.retrievers import VectorCypherRetriever

from .political_schema import (
    POLITICAL_SCHEMA,
    get_node_properties,
    get_political_extraction_prompt,
    get_relationship_properties,
)

logger = structlog.get_logger()


class PoliticalKnowledgeBuilder:
    """Build and maintain political domain knowledge graph using Neo4j GraphRAG."""

    def __init__(
        self,
        uri: str,
        username: str,
        password: str,
        database: str = "neo4j",
        openai_api_key: Optional[str] = None,
        embedding_model: str = "text-embedding-3-small",
        llm_model: str = "gpt-4o-mini",
    ):
        self.uri = uri
        self.database = database
        
        # Use synchronous driver for neo4j-graphrag compatibility
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
        
        # Initialize LLM and embeddings
        self.llm = OpenAILLM(
            model_name=llm_model,
            api_key=openai_api_key,
        )
        
        # Initialize OpenAI embeddings
        if not openai_api_key:
            raise ValueError("OpenAI API key required for embeddings")
        self.embedder = OpenAIEmbeddings(
            model=embedding_model,
            api_key=openai_api_key,
        )
        
        # Initialize schema builder with political domain
        self.schema_builder = SchemaBuilder()
        
        # Initialize SimpleKGPipeline
        self.kg_pipeline = None
        self._initialize_pipeline()
        
        logger.info(
            "Political knowledge builder initialized",
            uri=uri,
            database=database,
            llm_model=llm_model,
            embedding_model=embedding_model,
        )

    def _initialize_pipeline(self):
        """Initialize the SimpleKGPipeline with political domain configuration."""
        try:
            # Define political entities using simple string format first
            entities = [
                "Policy",
                "Politician", 
                "Organization",
                "Regulation",
                "Event",
                "Topic",
                "Jurisdiction"
            ]
            
            # Define political relationships
            relations = [
                "AUTHORED_BY",
                "AFFECTS", 
                "SUPPORTS",
                "OPPOSES",
                "RELATES_TO",
                "REFERENCES",
                "IMPLEMENTS",
                "APPLIES_TO"
            ]
            
            # Define potential schema (relationship constraints)
            potential_schema = [
                ("Policy", "AUTHORED_BY", "Politician"),
                ("Policy", "AUTHORED_BY", "Organization"),
                ("Policy", "AFFECTS", "Organization"),
                ("Policy", "RELATES_TO", "Topic"),
                ("Policy", "APPLIES_TO", "Jurisdiction"),
                ("Politician", "SUPPORTS", "Policy"),
                ("Politician", "OPPOSES", "Policy"),
                ("Organization", "SUPPORTS", "Policy"),
                ("Regulation", "IMPLEMENTS", "Policy"),
                ("Regulation", "APPLIES_TO", "Jurisdiction"),
                ("Event", "RELATES_TO", "Policy"),
                ("Event", "RELATES_TO", "Regulation")
            ]
            
            # Create the knowledge graph pipeline with political schema
            self.kg_pipeline = SimpleKGPipeline(
                llm=self.llm,
                driver=self.driver,
                embedder=self.embedder,
                entities=entities,
                relations=relations,
                potential_schema=potential_schema,
                from_pdf=False,  # We're processing text files
                neo4j_database=self.database,
                perform_entity_resolution=True,  # Merge similar entities
            )
            
            logger.info("SimpleKGPipeline initialized with political domain schema")
            
        except Exception as e:
            logger.error("Failed to initialize SimpleKGPipeline", error=str(e))
            raise

    async def __aenter__(self):
        """Async context manager entry."""
        await self.init_vector_index()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close Neo4j driver connection."""
        self.driver.close()

    async def init_vector_index(self):
        """Initialize vector index for embeddings."""
        try:
            # Run in thread pool since neo4j-graphrag uses sync driver
            def _create_vector_index():
                with self.driver.session(database=self.database) as session:
                    # Create vector index for chunk embeddings (1536 dimensions for OpenAI)
                    create_index_query = """
                    CREATE VECTOR INDEX chunk_embeddings IF NOT EXISTS
                    FOR (c:Chunk) ON (c.embedding)
                    OPTIONS {indexConfig: {
                        `vector.dimensions`: 1536,
                        `vector.similarity_function`: 'cosine'
                    }}
                    """
                    session.run(create_index_query)
                    logger.info("Vector index created for chunk embeddings")

            # Execute in thread pool to avoid blocking async context
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _create_vector_index)

        except Exception as e:
            logger.error("Failed to create vector index", error=str(e))
            # Don't raise - index might already exist

    async def process_documents(self, document_paths: List[str]) -> Dict[str, Any]:
        """Process documents using SimpleKGPipeline.
        
        Args:
            document_paths: List of file paths to process
            
        Returns:
            Processing results and statistics
        """
        try:
            def _run_pipeline():
                results = []
                for doc_path in document_paths:
                    try:
                        # Read text content for non-PDF processing
                        with open(doc_path, 'r', encoding='utf-8') as f:
                            text_content = f.read()
                        
                        # Run the knowledge graph pipeline with text content
                        result = asyncio.run(self.kg_pipeline.run_async(text=text_content))
                        results.append({
                            "document_path": doc_path,
                            "status": "success",
                            "result": result,
                        })
                        print(f"Document processed successfully: {doc_path}")
                    except Exception as e:
                        print(f"Failed to process document {doc_path}: {e}")
                        results.append({
                            "document_path": doc_path,
                            "status": "error",
                            "error": str(e),
                        })
                return results

            # Run pipeline in thread pool
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(None, _run_pipeline)
            
            # Get updated statistics
            stats = await self.get_graph_stats()
            
            return {
                "processed_documents": len(document_paths),
                "successful": len([r for r in results if r["status"] == "success"]),
                "failed": len([r for r in results if r["status"] == "error"]),
                "results": results,
                "graph_stats": stats,
            }

        except Exception as e:
            logger.error("Failed to process documents", error=str(e))
            raise

    async def create_retriever(self, retrieval_query: Optional[str] = None) -> VectorCypherRetriever:
        """Create a retriever for querying the knowledge graph.
        
        Args:
            retrieval_query: Optional custom Cypher query for retrieval
            
        Returns:
            Configured VectorCypherRetriever
        """
        # Default query for political document retrieval
        default_query = """
        MATCH (node)-[:HAS_CHUNK]->(chunk:Chunk)
        WHERE chunk.embedding IS NOT NULL
        WITH node, chunk, vector.similarity.cosine(chunk.embedding, $embedding) AS score
        WHERE score > 0.7
        
        // Get political context
        OPTIONAL MATCH (node)-[:MENTIONS]->(entity:Entity)
        OPTIONAL MATCH (node)-[:COVERS]->(topic:Topic)
        OPTIONAL MATCH (node)-[:REFERENCES]->(regulation:Regulation)
        
        RETURN 
            chunk.text AS text,
            score,
            {
                document_id: node.id,
                document_title: node.title,
                document_type: node.type,
                entities: collect(DISTINCT entity.name),
                topics: collect(DISTINCT topic.name),
                regulations: collect(DISTINCT regulation.name),
                chunk_position: chunk.position
            } AS metadata
        ORDER BY score DESC
        LIMIT 5
        """
        
        query = retrieval_query or default_query
        
        return VectorCypherRetriever(
            driver=self.driver,
            database=self.database,
            index_name="chunk_embeddings",
            embedder=self.embedder,
            retrieval_query=query,
        )

    async def search_documents(
        self, 
        query: str, 
        top_k: int = 5,
        include_entities: bool = True
    ) -> List[Dict[str, Any]]:
        """Search documents using vector similarity and graph context.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            include_entities: Whether to include entity context
            
        Returns:
            Search results with context
        """
        try:
            def _search():
                retriever = VectorCypherRetriever(
                    driver=self.driver,
                    database=self.database,
                    index_name="chunk_embeddings", 
                    embedder=self.embedder,
                    retrieval_query=f"""
                    MATCH (doc:Document)-[:HAS_CHUNK]->(chunk:Chunk)
                    WHERE chunk.embedding IS NOT NULL
                    WITH doc, chunk, vector.similarity.cosine(chunk.embedding, $embedding) AS score
                    WHERE score > 0.7
                    
                    {"OPTIONAL MATCH (doc)-[:MENTIONS]->(entity:Entity)" if include_entities else ""}
                    {"OPTIONAL MATCH (doc)-[:COVERS]->(topic:Topic)" if include_entities else ""}
                    
                    RETURN 
                        chunk.text AS text,
                        score,
                        {{
                            document_id: doc.id,
                            document_title: doc.title,
                            document_type: doc.type,
                            chunk_position: chunk.position
                            {", entities: collect(DISTINCT entity.name)" if include_entities else ""}
                            {", topics: collect(DISTINCT topic.name)" if include_entities else ""}
                        }} AS metadata
                    ORDER BY score DESC
                    LIMIT {top_k}
                    """,
                )
                
                return retriever.search(query_text=query, top_k=top_k)

            # Run search in thread pool
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(None, _search)
            
            return results

        except Exception as e:
            logger.error("Failed to search documents", query=query, error=str(e))
            return []

    async def get_document_context(self, document_id: str) -> Dict[str, Any]:
        """Get comprehensive context for a document from the graph."""
        def _get_context():
            with self.driver.session(database=self.database) as session:
                context = {
                    "document_id": document_id,
                    "entities": [],
                    "regulations": [],
                    "topics": [],
                    "related_documents": [],
                }
                
                # Get entities mentioned in the document
                entities_query = """
                MATCH (d:Document {id: $document_id})-[:MENTIONS]->(e:Entity)
                RETURN e.id as id, e.name as name, e.type as type
                ORDER BY e.name
                """
                entities_result = session.run(entities_query, document_id=document_id)
                context["entities"] = list(entities_result.data())
                
                # Get regulations referenced
                regulations_query = """
                MATCH (d:Document {id: $document_id})-[:REFERENCES]->(r:Regulation)
                RETURN r.id as id, r.name as name, r.jurisdiction as jurisdiction
                ORDER BY r.name
                """
                regulations_result = session.run(regulations_query, document_id=document_id)
                context["regulations"] = list(regulations_result.data())
                
                # Get topics covered
                topics_query = """
                MATCH (d:Document {id: $document_id})-[:COVERS]->(t:Topic)
                RETURN t.id as id, t.name as name, t.description as description
                ORDER BY t.name
                """
                topics_result = session.run(topics_query, document_id=document_id)
                context["topics"] = list(topics_result.data())
                
                # Get related documents
                related_query = """
                MATCH (d1:Document {id: $document_id})
                MATCH (d1)-[:MENTIONS|:COVERS]->(shared)<-[:MENTIONS|:COVERS]-(d2:Document)
                WHERE d1 <> d2
                WITH d2, count(DISTINCT shared) as similarity_score
                ORDER BY similarity_score DESC
                LIMIT 5
                RETURN d2.id as document_id,
                       d2.title as title,
                       d2.type as type,
                       similarity_score
                """
                related_result = session.run(related_query, document_id=document_id)
                context["related_documents"] = list(related_result.data())
                
                return context

        # Run query in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _get_context)

    async def get_graph_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge graph."""
        def _get_stats():
            with self.driver.session(database=self.database) as session:
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
                CALL {
                    MATCH ()-[rel]->()
                    RETURN count(rel) as relationship_count
                }
                RETURN document_count, chunk_count, entity_count, regulation_count, topic_count, relationship_count
                """
                
                result = session.run(query)
                record = result.single()
                
                if record:
                    return {
                        "documents": record["document_count"],
                        "chunks": record["chunk_count"],
                        "entities": record["entity_count"],
                        "regulations": record["regulation_count"],
                        "topics": record["topic_count"],
                        "relationships": record["relationship_count"],
                    }
                else:
                    return {
                        "documents": 0,
                        "chunks": 0,
                        "entities": 0,
                        "regulations": 0,
                        "topics": 0,
                        "relationships": 0,
                    }

        # Run query in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _get_stats)

    async def clear_graph(self) -> bool:
        """Clear all data from the knowledge graph."""
        try:
            def _clear():
                with self.driver.session(database=self.database) as session:
                    # Delete all nodes and relationships
                    session.run("MATCH (n) DETACH DELETE n")
                    logger.info("Knowledge graph cleared")
                    return True

            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, _clear)

        except Exception as e:
            logger.error("Failed to clear knowledge graph", error=str(e))
            return False