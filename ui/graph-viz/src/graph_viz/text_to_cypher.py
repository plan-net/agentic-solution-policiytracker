"""Text-to-Cypher conversion service using LangChain."""

import logging
import re
from typing import Optional

from langchain.chains import GraphCypherQAChain
from langchain_community.graphs import Neo4jGraph
from langchain_openai import ChatOpenAI
from neo4j import AsyncDriver

from src.graph_viz.models import GraphEdge, GraphNode

logger = logging.getLogger(__name__)


class TextToCypherService:
    """Service for converting natural language to Cypher queries."""

    # Safety: Allowed Cypher keywords (read-only operations)
    ALLOWED_KEYWORDS = {
        "MATCH",
        "RETURN",
        "WHERE",
        "WITH",
        "ORDER BY",
        "LIMIT",
        "SKIP",
        "UNION",
        "UNWIND",
        "DISTINCT",
        "AS",
        "AND",
        "OR",
        "NOT",
        "IN",
        "CONTAINS",
        "STARTS WITH",
        "ENDS WITH",
        "COUNT",
        "SUM",
        "AVG",
        "MIN",
        "MAX",
        "COLLECT",
    }

    # Safety: Forbidden Cypher keywords (write operations)
    FORBIDDEN_KEYWORDS = {
        "CREATE",
        "DELETE",
        "REMOVE",
        "SET",
        "MERGE",
        "DROP",
        "DETACH",
        "CALL",
    }

    def __init__(
        self,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
        openai_api_key: str,
        neo4j_database: str = "politicalmonitoring",
    ):
        """Initialize Text-to-Cypher service with LangChain."""
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.neo4j_database = neo4j_database

        # Initialize Neo4j Graph for LangChain
        self.graph = Neo4jGraph(
            url=neo4j_uri,
            username=neo4j_user,
            password=neo4j_password,
            database=neo4j_database,
        )

        # Initialize GPT-4o-mini for fast conversion
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=openai_api_key,
        )

        # Create GraphCypherQAChain
        self.cypher_chain = GraphCypherQAChain.from_llm(
            llm=self.llm,
            graph=self.graph,
            verbose=True,
            validate_cypher=True,
            top_k=50,
            return_intermediate_steps=True,
        )

        logger.info("TextToCypherService initialized with GPT-4o-mini")

    def validate_cypher(self, cypher: str) -> tuple[bool, Optional[str]]:
        """
        Validate that a Cypher query is safe to execute (read-only).

        Returns:
            (is_valid, error_message)
        """
        cypher_upper = cypher.upper()

        # Check for forbidden keywords
        for keyword in self.FORBIDDEN_KEYWORDS:
            if keyword in cypher_upper:
                return False, f"Forbidden operation detected: {keyword}. Only read-only queries are allowed."

        # Ensure query contains MATCH and RETURN
        if "MATCH" not in cypher_upper:
            return False, "Query must contain MATCH clause"

        if "RETURN" not in cypher_upper:
            return False, "Query must contain RETURN clause"

        return True, None

    async def convert_and_execute(
        self, text: str, limit: int = 50, driver: Optional[AsyncDriver] = None
    ) -> tuple[str, list[GraphNode], list[GraphEdge], Optional[str]]:
        """
        Convert natural language to Cypher and execute it.

        Args:
            text: Natural language query
            limit: Maximum number of results
            driver: Optional Neo4j async driver for execution

        Returns:
            (cypher_query, nodes, edges, error_message)
        """
        try:
            # Generate Cypher using LangChain
            logger.info(f"Converting text to Cypher: {text}")

            # Invoke the chain
            result = self.cypher_chain.invoke({"query": text})

            # Extract generated Cypher from intermediate steps
            cypher_query = None
            if "intermediate_steps" in result:
                for step in result["intermediate_steps"]:
                    if "query" in step:
                        cypher_query = step["query"]
                        break

            if not cypher_query:
                return "", [], [], "Failed to generate Cypher query"

            logger.info(f"Generated Cypher: {cypher_query}")

            # Validate Cypher safety
            is_valid, error = self.validate_cypher(cypher_query)
            if not is_valid:
                return cypher_query, [], [], error

            # Add LIMIT if not present
            if "LIMIT" not in cypher_query.upper():
                cypher_query = f"{cypher_query.rstrip(';')} LIMIT {limit}"

            # Execute query if driver provided
            if driver:
                nodes, edges = await self._execute_cypher(cypher_query, driver)
                return cypher_query, nodes, edges, None
            else:
                return cypher_query, [], [], None

        except Exception as e:
            logger.error(f"Text-to-Cypher conversion failed: {e}")
            return "", [], [], f"Conversion error: {str(e)}"

    async def _execute_cypher(
        self, cypher: str, driver: AsyncDriver
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        """Execute Cypher query and convert results to graph format."""
        nodes = []
        edges = []
        node_map = {}

        try:
            async with driver.session(database=self.neo4j_database) as session:
                result = await session.run(cypher)
                records = await result.data()

                for record in records:
                    # Process nodes
                    for key, value in record.items():
                        if hasattr(value, "element_id"):  # Neo4j node
                            node_id = value.element_id
                            if node_id not in node_map:
                                node_data = dict(value.items())
                                node = GraphNode(
                                    id=node_id,
                                    name=node_data.get("name", node_id[:8]),
                                    type=list(value.labels)[0] if value.labels else "Entity",
                                    properties=node_data,
                                    val=1,
                                )
                                nodes.append(node)
                                node_map[node_id] = node

                    # Process relationships
                    for value in record.values():
                        if hasattr(value, "start_node"):  # Neo4j relationship
                            source_id = value.start_node.element_id
                            target_id = value.end_node.element_id

                            # Ensure nodes exist
                            if source_id not in node_map:
                                source_node = GraphNode(
                                    id=source_id,
                                    name=source_id[:8],
                                    type="Entity",
                                    properties={},
                                    val=1,
                                )
                                nodes.append(source_node)
                                node_map[source_id] = source_node

                            if target_id not in node_map:
                                target_node = GraphNode(
                                    id=target_id,
                                    name=target_id[:8],
                                    type="Entity",
                                    properties={},
                                    val=1,
                                )
                                nodes.append(target_node)
                                node_map[target_id] = target_node

                            edge = GraphEdge(
                                source=source_id,
                                target=target_id,
                                type=value.type,
                                value=1.0,
                                properties=dict(value.items()),
                            )
                            edges.append(edge)

        except Exception as e:
            logger.error(f"Cypher execution failed: {e}")
            raise

        return nodes, edges
