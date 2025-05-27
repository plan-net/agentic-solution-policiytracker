"""Build and maintain political domain knowledge graph using Neo4j GraphRAG."""

import asyncio
import json
from typing import Any, Optional

import structlog
from langfuse.decorators import langfuse_context, observe
from neo4j import GraphDatabase
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from neo4j_graphrag.experimental.components.schema import SchemaBuilder
from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.retrievers import HybridCypherRetriever, HybridRetriever

from src.llm.langchain_service import LangChainLLMService

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

        # Initialize LangChain service for proper Langfuse integration
        self.langchain_service = LangChainLLMService()

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
                "Jurisdiction",
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
                "APPLIES_TO",
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
                ("Event", "RELATES_TO", "Regulation"),
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
                    vector_index_query = """
                    CREATE VECTOR INDEX chunk_embeddings IF NOT EXISTS
                    FOR (c:Chunk) ON (c.embedding)
                    OPTIONS {indexConfig: {
                        `vector.dimensions`: 1536,
                        `vector.similarity_function`: 'cosine'
                    }}
                    """
                    session.run(vector_index_query)
                    logger.info("Vector index created for chunk embeddings")

                    # Create fulltext index for chunk text (required for HybridRetriever)
                    fulltext_index_query = """
                    CREATE FULLTEXT INDEX chunk_fulltext IF NOT EXISTS
                    FOR (c:Chunk) ON EACH [c.text]
                    """
                    session.run(fulltext_index_query)
                    logger.info("Fulltext index created for chunk text")

            # Execute in thread pool to avoid blocking async context
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _create_vector_index)

        except Exception as e:
            logger.error("Failed to create vector index", error=str(e))
            # Don't raise - index might already exist

    async def process_documents(self, document_paths: list[str]) -> dict[str, Any]:
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
                        with open(doc_path, encoding="utf-8") as f:
                            text_content = f.read()

                        # Run the knowledge graph pipeline with text content
                        result = asyncio.run(self.kg_pipeline.run_async(text=text_content))
                        results.append(
                            {
                                "document_path": doc_path,
                                "status": "success",
                                "result": result,
                            }
                        )
                        print(f"Document processed successfully: {doc_path}")
                    except Exception as e:
                        print(f"Failed to process document {doc_path}: {e}")
                        results.append(
                            {
                                "document_path": doc_path,
                                "status": "error",
                                "error": str(e),
                            }
                        )
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

    async def create_retriever(self) -> HybridRetriever:
        """Create a HybridRetriever for querying the knowledge graph.

        Returns:
            Configured HybridRetriever with vector and fulltext search
        """
        return HybridRetriever(
            driver=self.driver,
            vector_index_name="chunk_embeddings",
            fulltext_index_name="chunk_fulltext",
            embedder=self.embedder,
        )

    async def create_graph_traversal_retriever(self) -> HybridCypherRetriever:
        """Create a HybridCypherRetriever for graph traversal with political relationships.

        Returns:
            Configured HybridCypherRetriever with custom political traversal query
        """
        # Political graph traversal query - finds related entities and regulations
        political_traversal_query = """
        // After vector/fulltext search finds initial chunks
        MATCH (chunk:Chunk)<-[:HAS_CHUNK]-(doc:Document)

        // Find political entities mentioned in the document
        OPTIONAL MATCH (doc)-[:MENTIONS]->(entity)
        WHERE entity:Policy OR entity:Politician OR entity:Organization OR entity:Regulation

        // Find regulations that implement or relate to policies
        OPTIONAL MATCH (doc)-[:REFERENCES]->(regulation:Regulation)
        OPTIONAL MATCH (regulation)-[:IMPLEMENTS]->(policy:Policy)

        // Find organizations affected by policies
        OPTIONAL MATCH (entity)-[:AFFECTS]->(affected_org:Organization)

        // Find politicians who authored policies
        OPTIONAL MATCH (policy)-[:AUTHORED_BY]->(politician:Politician)

        // Find topics covered by the document
        OPTIONAL MATCH (doc)-[:COVERS]->(topic:Topic)

        // Return rich political context
        RETURN
            chunk.text AS text,
            score,
            {
                document_id: doc.id,
                document_title: doc.title,
                entities: collect(DISTINCT {
                    name: entity.name,
                    type: labels(entity)[0],
                    properties: properties(entity)
                }),
                regulations: collect(DISTINCT {
                    name: regulation.name,
                    code: regulation.code,
                    jurisdiction: regulation.jurisdiction
                }),
                policies: collect(DISTINCT {
                    name: policy.name,
                    status: policy.status
                }),
                politicians: collect(DISTINCT {
                    name: politician.name,
                    party: politician.party,
                    role: politician.role
                }),
                affected_organizations: collect(DISTINCT {
                    name: affected_org.name,
                    type: affected_org.type,
                    sector: affected_org.sector
                }),
                topics: collect(DISTINCT {
                    name: topic.name,
                    description: topic.description
                }),
                chunk_position: chunk.position
            } AS metadata
        ORDER BY score DESC
        """

        return HybridCypherRetriever(
            driver=self.driver,
            vector_index_name="chunk_embeddings",
            fulltext_index_name="chunk_fulltext",
            retrieval_query=political_traversal_query,
            embedder=self.embedder,
        )

    async def search_documents(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Search documents using HybridRetriever (vector + fulltext).

        Args:
            query: Search query text
            top_k: Number of results to return

        Returns:
            Search results with metadata as list of dictionaries
        """
        try:

            def _search():
                # Create HybridRetriever using the official package
                retriever = HybridRetriever(
                    driver=self.driver,
                    vector_index_name="chunk_embeddings",
                    fulltext_index_name="chunk_fulltext",
                    embedder=self.embedder,
                )

                # Use the official search method
                return retriever.search(query_text=query, top_k=top_k)

            # Run search in thread pool
            loop = asyncio.get_event_loop()
            retriever_result = await loop.run_in_executor(None, _search)

            # Convert RetrieverResult to list of dictionaries
            if hasattr(retriever_result, "items") and retriever_result.items:
                results = []
                for item in retriever_result.items:
                    try:
                        # Extract text and metadata from each result item
                        result_dict = {
                            "text": item.content if hasattr(item, "content") else str(item),
                            "score": item.metadata.get("score", 0)
                            if hasattr(item, "metadata") and item.metadata
                            else 0,
                            "metadata": item.metadata if hasattr(item, "metadata") else {},
                            "political_context": {},  # Will be populated by analysis
                        }
                        results.append(result_dict)
                    except Exception as parse_error:
                        logger.warning("Failed to parse search result item", error=str(parse_error))
                        continue

                return results
            else:
                logger.info("No search results found", query=query)
                return []

        except Exception as e:
            logger.error("Failed to search documents", query=query, error=str(e))
            return []

    async def search_with_graph_traversal(self, query: str, top_k: int = 5) -> dict[str, Any]:
        """Search using HybridCypherRetriever with political graph traversal.

        Args:
            query: Search query text
            top_k: Number of results to return

        Returns:
            Rich results with political entity relationships and context
        """
        try:

            def _graph_search():
                # Create HybridCypherRetriever with political traversal
                retriever = HybridCypherRetriever(
                    driver=self.driver,
                    vector_index_name="chunk_embeddings",
                    fulltext_index_name="chunk_fulltext",
                    retrieval_query="""
                    // Basic graph traversal after vector search
                    MATCH (chunk:Chunk)<-[:HAS_CHUNK]-(doc:Document)

                    // Find one political entity as example of graph traversal
                    OPTIONAL MATCH (doc)-[:MENTIONS]->(entity)
                    WHERE entity:Policy OR entity:Politician OR entity:Organization OR entity:Regulation

                    // Return with basic political context
                    RETURN
                        chunk.text AS text,
                        score,
                        doc.id + '_traversed' AS document_id,
                        doc.title AS document_title,
                        entity.name AS found_entity
                    ORDER BY score DESC
                    """,
                    embedder=self.embedder,
                )

                return retriever.search(query_text=query, top_k=top_k)

            # Run search in thread pool
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(None, _graph_search)

            # Process results to extract political insights
            if hasattr(results, "items") and results.items:
                processed_results = []
                for item in results.items:
                    try:
                        # Handle both JSON and direct content
                        if hasattr(item, "content"):
                            try:
                                # Try to parse as JSON first
                                content_data = json.loads(item.content)
                                text = content_data.get("text", "")
                                political_context = content_data.get("metadata", {})
                                relationship_count = content_data.get("relationship_count", 0)
                            except (json.JSONDecodeError, TypeError):
                                # If not JSON, treat as plain text
                                text = str(item.content)
                                political_context = {}
                                relationship_count = 0
                        else:
                            text = str(item)
                            political_context = {}
                            relationship_count = 0

                        processed_results.append(
                            {
                                "text": text,
                                "score": item.metadata.get("score", 0)
                                if hasattr(item, "metadata") and item.metadata
                                else 0,
                                "political_context": political_context,
                                "relationship_count": relationship_count,
                            }
                        )
                    except Exception as parse_error:
                        logger.warning(
                            "Failed to parse graph search result", error=str(parse_error)
                        )
                        continue

                return {
                    "query": query,
                    "results": processed_results,
                    "total_results": len(processed_results),
                    "retrieval_method": "graph_traversal",
                    "political_entities_found": len(
                        set(
                            [
                                entity["name"]
                                for result in processed_results
                                for entity in result.get("political_context", {}).get(
                                    "entities", []
                                )
                            ]
                        )
                    ),
                    "regulations_found": len(
                        set(
                            [
                                reg["name"]
                                for result in processed_results
                                for reg in result.get("political_context", {}).get(
                                    "regulations", []
                                )
                            ]
                        )
                    ),
                }
            else:
                return {
                    "query": query,
                    "results": [],
                    "total_results": 0,
                    "retrieval_method": "graph_traversal",
                    "message": "No results found",
                }

        except Exception as e:
            logger.error("Failed to search with graph traversal", query=query, error=str(e))
            return {
                "query": query,
                "results": [],
                "total_results": 0,
                "retrieval_method": "graph_traversal",
                "error": str(e),
            }

    async def get_document_context(self, document_id: str) -> dict[str, Any]:
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

    async def get_graph_stats(self) -> dict[str, Any]:
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

    @observe()
    async def analyze_entities_with_langfuse(
        self,
        query_results: list[dict[str, Any]],
        company_context: dict[str, Any],
        query_topic: str,
        session_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Analyze GraphRAG entities using Langfuse prompts for enhanced insights.

        Args:
            query_results: Results from GraphRAG search
            company_context: Business context for relevance analysis
            query_topic: The search topic for contextual analysis

        Returns:
            Enhanced analysis with political intelligence insights
        """
        # Update trace with meaningful metadata
        langfuse_context.update_current_trace(
            name="GraphRAG Entity Analysis",
            tags=["graphrag", "entity-analysis"],
            metadata={
                "query_topic": query_topic,
                "results_count": len(query_results),
                "company_terms": company_context.get("terms", []),
            },
        )

        try:
            # Extract entities and relationships from search results
            entities = []
            relationships = []

            for result in query_results:
                political_context = result.get("political_context", {})
                if "entities" in political_context:
                    entities.extend(political_context["entities"])
                if "relationships" in political_context:
                    relationships.extend(political_context["relationships"])

            # Prepare variables for the prompt - clean data to avoid Unicode issues
            def clean_for_prompt(data):
                """Clean data to avoid Unicode escape issues in prompts"""
                if isinstance(data, str):
                    # Replace problematic Unicode characters
                    return data.encode("ascii", "ignore").decode("ascii")
                elif isinstance(data, list):
                    return [clean_for_prompt(item) for item in data]
                elif isinstance(data, dict):
                    return {k: clean_for_prompt(v) for k, v in data.items()}
                else:
                    return data

            cleaned_entities = clean_for_prompt(entities)
            cleaned_relationships = clean_for_prompt(relationships)
            cleaned_results = clean_for_prompt(query_results)

            prompt_variables = {
                "company_terms": company_context.get("terms", []),
                "core_industries": company_context.get("industries", []),
                "primary_markets": company_context.get("markets", []),
                "strategic_themes": company_context.get("themes", []),
                "entities": json.dumps(cleaned_entities, indent=2, ensure_ascii=True),
                "relationships": json.dumps(cleaned_relationships, indent=2, ensure_ascii=True),
                "graph_results": json.dumps(cleaned_results, indent=2, ensure_ascii=True),
            }

            # Call LangChain service method directly (following v0.1.0 pattern)
            analysis_result = await self.langchain_service.analyze_graphrag_entities(
                query_results=query_results,
                company_context=company_context,
                query_topic=query_topic,
                session_id=session_id,
            )

            return analysis_result

        except Exception as e:
            logger.error("Failed to analyze entities with Langfuse", error=str(e))
            return {
                "query_topic": query_topic,
                "analysis_type": "graphrag_entity_analysis",
                "error": str(e),
                "entities_analyzed": 0,
                "relationships_analyzed": 0,
            }

    @observe()
    async def generate_relationship_insights(
        self,
        query_results: list[dict[str, Any]],
        company_context: dict[str, Any],
        query_topic: str,
        session_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Generate insights about relationships between entities."""
        try:
            # Call LangChain service method directly (following v0.1.0 pattern)
            analysis_result = await self.langchain_service.analyze_graphrag_relationships(
                query_results=query_results,
                company_context=company_context,
                query_topic=query_topic,
                session_id=session_id,
            )

            return analysis_result

        except Exception as e:
            logger.error(f"Failed to generate relationship insights: {e}")
            return {
                "relationships": [],
                "insights": [f"Error generating insights: {str(e)}"],
                "recommendations": [],
                "error": str(e),
            }

    @observe()
    async def compare_with_traditional_analysis(
        self,
        graphrag_results: dict[str, Any],
        traditional_results: dict[str, Any],
        company_context: dict[str, Any],
        session_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Compare GraphRAG results with traditional document analysis."""
        try:
            # Call LangChain service method directly (following v0.1.0 pattern)
            analysis_result = await self.langchain_service.analyze_graphrag_comparison(
                graphrag_results=graphrag_results,
                traditional_results=traditional_results,
                company_context=company_context,
                session_id=session_id,
            )

            return analysis_result

        except Exception as e:
            logger.error(f"Failed to compare with traditional analysis: {e}")
            return {
                "unique_to_graphrag": [],
                "unique_to_traditional": [],
                "common_insights": [f"Error in comparison: {str(e)}"],
                "recommendation": "Comparison failed",
                "confidence": 0.0,
                "error": str(e),
            }
