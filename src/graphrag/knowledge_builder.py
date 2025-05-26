"""Build and maintain political domain knowledge graph using Neo4j GraphRAG."""

import asyncio
import json
from typing import Any, Optional

import structlog
from neo4j import GraphDatabase
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from neo4j_graphrag.experimental.components.schema import SchemaBuilder
from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.retrievers import HybridCypherRetriever, HybridRetriever

from src.prompts.prompt_manager import prompt_manager

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
            Search results with metadata
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
            results = await loop.run_in_executor(None, _search)

            return results

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
                        import json

                        content_data = json.loads(item.content)
                        processed_results.append(
                            {
                                "text": content_data.get("text", ""),
                                "score": item.metadata.get("score", 0),
                                "political_context": content_data.get("metadata", {}),
                                "relationship_count": content_data.get("relationship_count", 0),
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

    async def analyze_entities_with_langfuse(
        self, query_results: list[dict[str, Any]], company_context: dict[str, Any], query_topic: str
    ) -> dict[str, Any]:
        """Analyze GraphRAG entities using Langfuse prompts for enhanced insights.

        Args:
            query_results: Results from GraphRAG search
            company_context: Business context for relevance analysis
            query_topic: The search topic for contextual analysis

        Returns:
            Enhanced analysis with political intelligence insights
        """
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

            # Prepare variables for the prompt
            prompt_variables = {
                "company_terms": company_context.get("terms", []),
                "core_industries": company_context.get("industries", []),
                "primary_markets": company_context.get("markets", []),
                "strategic_themes": company_context.get("themes", []),
                "entities": json.dumps(entities, indent=2),
                "relationships": json.dumps(relationships, indent=2),
                "graph_results": json.dumps(query_results, indent=2),
            }

            # Get enhanced analysis prompt from Langfuse
            analysis_prompt = await prompt_manager.get_prompt(
                "graphrag_entity_analysis", variables=prompt_variables
            )

            # Send to LLM for analysis
            def _analyze():
                response = self.llm.invoke(analysis_prompt)
                return response.content

            loop = asyncio.get_event_loop()
            llm_response = await loop.run_in_executor(None, _analyze)

            # Parse LLM response as JSON
            try:
                analysis_result = json.loads(llm_response)
                analysis_result["query_topic"] = query_topic
                analysis_result["analysis_type"] = "graphrag_entity_analysis"
                analysis_result["entities_analyzed"] = len(entities)
                analysis_result["relationships_analyzed"] = len(relationships)

                return analysis_result

            except json.JSONDecodeError as json_error:
                logger.warning(
                    "Failed to parse LLM analysis response as JSON", error=str(json_error)
                )
                return {
                    "query_topic": query_topic,
                    "analysis_type": "graphrag_entity_analysis",
                    "error": "Failed to parse LLM response",
                    "raw_response": llm_response,
                    "entities_analyzed": len(entities),
                    "relationships_analyzed": len(relationships),
                }

        except Exception as e:
            logger.error("Failed to analyze entities with Langfuse", error=str(e))
            return {
                "query_topic": query_topic,
                "analysis_type": "graphrag_entity_analysis",
                "error": str(e),
                "entities_analyzed": 0,
                "relationships_analyzed": 0,
            }

    async def generate_relationship_insights(
        self,
        graph_traversal_results: dict[str, Any],
        company_context: dict[str, Any],
        time_horizon: str = "6-12 months",
    ) -> dict[str, Any]:
        """Generate strategic insights from relationship patterns using Langfuse prompts.

        Args:
            graph_traversal_results: Results from graph traversal search
            company_context: Business context for strategic analysis
            time_horizon: Planning timeframe for recommendations

        Returns:
            Strategic insights and recommendations based on relationship analysis
        """
        try:
            # Extract network patterns from traversal results
            relationship_patterns = []
            entity_clusters = {}

            for result in graph_traversal_results.get("results", []):
                political_context = result.get("political_context", {})

                # Extract relationship patterns
                if "relationships" in political_context:
                    relationship_patterns.extend(political_context["relationships"])

                # Group entities by type for cluster analysis
                if "entities" in political_context:
                    for entity in political_context["entities"]:
                        entity_type = entity.get("type", "unknown")
                        if entity_type not in entity_clusters:
                            entity_clusters[entity_type] = []
                        entity_clusters[entity_type].append(entity)

            # Calculate basic network metrics
            network_metrics = {
                "total_relationships": len(relationship_patterns),
                "entity_types": len(entity_clusters),
                "entities_per_type": {k: len(v) for k, v in entity_clusters.items()},
                "relationship_types": list(
                    set([rel.get("type", "unknown") for rel in relationship_patterns])
                ),
                "political_entities_count": graph_traversal_results.get(
                    "political_entities_found", 0
                ),
                "regulations_count": graph_traversal_results.get("regulations_found", 0),
            }

            # Prepare variables for the relationship insights prompt
            prompt_variables = {
                "query_topic": graph_traversal_results.get("query", ""),
                "company_terms": company_context.get("terms", []),
                "strategic_themes": company_context.get("themes", []),
                "time_horizon": time_horizon,
                "relationship_patterns": json.dumps(relationship_patterns, indent=2),
                "entity_clusters": json.dumps(entity_clusters, indent=2),
                "network_metrics": json.dumps(network_metrics, indent=2),
                "traversal_results": json.dumps(graph_traversal_results, indent=2),
            }

            # Get strategic insights prompt from Langfuse
            insights_prompt = await prompt_manager.get_prompt(
                "graphrag_relationship_insights", variables=prompt_variables
            )

            # Send to LLM for strategic analysis
            def _analyze():
                response = self.llm.invoke(insights_prompt)
                return response.content

            loop = asyncio.get_event_loop()
            llm_response = await loop.run_in_executor(None, _analyze)

            # Parse LLM response
            try:
                insights_result = json.loads(llm_response)
                insights_result["query_topic"] = graph_traversal_results.get("query", "")
                insights_result["analysis_type"] = "graphrag_relationship_insights"
                insights_result["network_metrics"] = network_metrics
                insights_result["time_horizon"] = time_horizon

                return insights_result

            except json.JSONDecodeError as json_error:
                logger.warning(
                    "Failed to parse relationship insights response as JSON", error=str(json_error)
                )
                return {
                    "query_topic": graph_traversal_results.get("query", ""),
                    "analysis_type": "graphrag_relationship_insights",
                    "error": "Failed to parse LLM response",
                    "raw_response": llm_response,
                    "network_metrics": network_metrics,
                    "time_horizon": time_horizon,
                }

        except Exception as e:
            logger.error("Failed to generate relationship insights", error=str(e))
            return {
                "query_topic": graph_traversal_results.get("query", ""),
                "analysis_type": "graphrag_relationship_insights",
                "error": str(e),
                "network_metrics": {},
                "time_horizon": time_horizon,
            }

    async def compare_with_traditional_analysis(
        self,
        traditional_results: dict[str, Any],
        graphrag_entity_analysis: dict[str, Any],
        graphrag_relationship_insights: dict[str, Any],
        analysis_topic: str,
        company_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Compare GraphRAG insights with traditional analysis using Langfuse prompts.

        Args:
            traditional_results: Results from traditional document analysis
            graphrag_entity_analysis: Results from GraphRAG entity analysis
            graphrag_relationship_insights: Results from GraphRAG relationship analysis
            analysis_topic: The topic being analyzed
            company_context: Business context for the comparison

        Returns:
            Comparative analysis highlighting unique value of GraphRAG approach
        """
        try:
            # Prepare variables for comparative analysis prompt
            prompt_variables = {
                "analysis_topic": analysis_topic,
                "company_context": json.dumps(company_context, indent=2),
                "strategic_focus": company_context.get("strategic_focus", ""),
                "traditional_results": json.dumps(traditional_results, indent=2),
                "graphrag_entities": json.dumps(graphrag_entity_analysis, indent=2),
                "graphrag_relationships": json.dumps(graphrag_relationship_insights, indent=2),
                "network_metrics": json.dumps(
                    graphrag_relationship_insights.get("network_metrics", {}), indent=2
                ),
            }

            # Get comparative analysis prompt from Langfuse
            comparison_prompt = await prompt_manager.get_prompt(
                "graphrag_comparative_analysis", variables=prompt_variables
            )

            # Send to LLM for comparative analysis
            def _analyze():
                response = self.llm.invoke(comparison_prompt)
                return response.content

            loop = asyncio.get_event_loop()
            llm_response = await loop.run_in_executor(None, _analyze)

            # Parse LLM response
            try:
                comparison_result = json.loads(llm_response)
                comparison_result["analysis_topic"] = analysis_topic
                comparison_result["analysis_type"] = "graphrag_comparative_analysis"
                comparison_result["traditional_method"] = traditional_results.get(
                    "method", "document_analysis"
                )
                comparison_result["graphrag_methods"] = ["entity_analysis", "relationship_insights"]

                return comparison_result

            except json.JSONDecodeError as json_error:
                logger.warning(
                    "Failed to parse comparative analysis response as JSON", error=str(json_error)
                )
                return {
                    "analysis_topic": analysis_topic,
                    "analysis_type": "graphrag_comparative_analysis",
                    "error": "Failed to parse LLM response",
                    "raw_response": llm_response,
                    "traditional_method": traditional_results.get("method", "document_analysis"),
                    "graphrag_methods": ["entity_analysis", "relationship_insights"],
                }

        except Exception as e:
            logger.error("Failed to compare with traditional analysis", error=str(e))
            return {
                "analysis_topic": analysis_topic,
                "analysis_type": "graphrag_comparative_analysis",
                "error": str(e),
                "traditional_method": traditional_results.get("method", "document_analysis"),
                "graphrag_methods": ["entity_analysis", "relationship_insights"],
            }
