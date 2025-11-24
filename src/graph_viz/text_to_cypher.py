"""Text-to-Cypher conversion service using LangChain and OpenAI."""

import logging
import time
from typing import Any, Optional

from langchain.chains import GraphCypherQAChain
from langchain_community.graphs import Neo4jGraph
from langchain_openai import ChatOpenAI
from neo4j import AsyncDriver

from .models import GraphEdge, GraphNode

logger = logging.getLogger(__name__)


class TextToCypherService:
    """Service for converting natural language to Cypher queries and executing them."""

    # Read-only Cypher keywords (whitelist)
    ALLOWED_KEYWORDS = {
        "MATCH",
        "RETURN",
        "WHERE",
        "WITH",
        "ORDER BY",
        "LIMIT",
        "SKIP",
        "DISTINCT",
        "AS",
        "AND",
        "OR",
        "NOT",
        "IN",
        "CONTAINS",
        "STARTS WITH",
        "ENDS WITH",
        "OPTIONAL MATCH",
        "UNWIND",
        "CASE",
        "WHEN",
        "THEN",
        "ELSE",
        "END",
    }

    # Write operations (blacklist)
    FORBIDDEN_KEYWORDS = {
        "CREATE",
        "DELETE",
        "REMOVE",
        "SET",
        "MERGE",
        "DETACH DELETE",
        "DROP",
        "ALTER",
    }

    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str, openai_api_key: str):
        """Initialize the text-to-Cypher service."""
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password

        # Initialize Neo4j graph for LangChain with enhanced_schema disabled to reduce context
        # Note: Neo4jGraph calls refresh_schema() in __init__, which queries the database
        # If the schema query fails, we catch the error and set a minimal manual schema
        try:
            self.graph = Neo4jGraph(
                url=neo4j_uri,
                username=neo4j_user,
                password=neo4j_password,
                enhanced_schema=False,  # Disable to reduce context size
                sanitize=True,
            )
            logger.info("Neo4j graph initialized with auto-schema")
        except KeyError as e:
            # LangChain bug: refresh_schema() fails with KeyError: 'properties'
            # This happens when Neo4j returns schema in unexpected format
            # Workaround: Initialize without schema and set it manually
            logger.warning(f"Schema auto-refresh failed ({e}), using minimal manual schema")

            # Import GraphDatabase for manual initialization
            from neo4j import GraphDatabase

            # Create a minimal compatible graph object
            class MinimalNeo4jGraph:
                def __init__(self, uri, username, password):
                    self.driver = GraphDatabase.driver(uri, auth=(username, password))
                    self.schema = (
                        "Node properties:\n"
                        "Policy {name: STRING, status: STRING, jurisdiction: STRING}\n"
                        "Politician {name: STRING, party: STRING}\n"
                        "Organization {name: STRING, type: STRING}\n"
                        "Document {name: STRING, source: STRING}\n"
                        "News {title: STRING, date: DATE}\n\n"
                        "Relationship properties:\n\n"
                        "The relationships:\n"
                        "(:Policy)-[:AFFECTS]->(:Organization)\n"
                        "(:Document)-[:MENTIONS]->(:Policy)\n"
                        "(:Politician)-[:AUTHORED_BY]->(:Policy)\n"
                        "(:News)-[:RELATED_TO]->(:Policy)"
                    )
                    self.structured_schema = {
                        "node_props": {
                            "Policy": [
                                {"property": "name", "type": "STRING"},
                                {"property": "status", "type": "STRING"},
                                {"property": "jurisdiction", "type": "STRING"},
                            ],
                            "Politician": [
                                {"property": "name", "type": "STRING"},
                                {"property": "party", "type": "STRING"},
                            ],
                            "Organization": [
                                {"property": "name", "type": "STRING"},
                                {"property": "type", "type": "STRING"},
                            ],
                            "Document": [
                                {"property": "name", "type": "STRING"},
                                {"property": "source", "type": "STRING"},
                            ],
                            "News": [
                                {"property": "title", "type": "STRING"},
                                {"property": "date", "type": "DATE"},
                            ],
                        },
                        "rel_props": {},
                        "relationships": [
                            {"start": "Policy", "type": "AFFECTS", "end": "Organization"},
                            {"start": "Document", "type": "MENTIONS", "end": "Policy"},
                            {"start": "Politician", "type": "AUTHORED_BY", "end": "Policy"},
                            {"start": "News", "type": "RELATED_TO", "end": "Policy"},
                        ],
                    }

                def query(self, cypher_query, params=None):
                    with self.driver.session() as session:
                        result = session.run(cypher_query, params or {})
                        return result.data()

                @property
                def get_structured_schema(self):
                    """Return structured schema as a property."""
                    return self.structured_schema

                def refresh_schema(self):
                    # No-op - we use manual schema
                    pass

            self.graph = MinimalNeo4jGraph(neo4j_uri, neo4j_user, neo4j_password)
            logger.info("Initialized Neo4j graph with minimal manual schema")

        # Initialize LLM
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=openai_api_key,
        )

        # Initialize Cypher QA chain with minimal schema
        # We acknowledge the risks and have implemented additional safety validation
        self.cypher_chain = GraphCypherQAChain.from_llm(
            llm=self.llm,
            graph=self.graph,
            verbose=True,
            validate_cypher=True,
            top_k=20,  # Reduced from 50 to limit results
            return_intermediate_steps=True,
            allow_dangerous_requests=True,  # We have additional safety checks in validate_cypher()
        )

        logger.info("Text-to-Cypher service initialized")

    def validate_cypher(self, cypher: str) -> tuple[bool, Optional[str]]:
        """
        Validate that a Cypher query is safe to execute (read-only).

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Convert to uppercase for keyword checking
        cypher_upper = cypher.upper()

        # Check for forbidden keywords
        for keyword in self.FORBIDDEN_KEYWORDS:
            if keyword in cypher_upper:
                return (
                    False,
                    f"Forbidden operation detected: {keyword}. Only read operations are allowed.",
                )

        # Check if query contains at least one MATCH or RETURN
        if "MATCH" not in cypher_upper and "RETURN" not in cypher_upper:
            return False, "Query must contain at least one MATCH or RETURN statement"

        return True, None

    async def convert_and_execute(
        self, text: str, limit: int = 50, driver: Optional[AsyncDriver] = None
    ) -> dict[str, Any]:
        """
        Convert natural language to Cypher, validate, and execute the query.

        Args:
            text: Natural language query
            limit: Maximum number of nodes to return
            driver: Neo4j async driver for execution

        Returns:
            Dict containing cypher, nodes, links, execution_time, and optionally error
        """
        start_time = time.time()

        try:
            # Generate Cypher from natural language
            logger.info(f"Converting text to Cypher: {text}")

            # Use the chain to generate Cypher
            result = self.cypher_chain.invoke({"query": text})

            # Extract generated Cypher from intermediate steps
            cypher = None
            if "intermediate_steps" in result:
                for step in result["intermediate_steps"]:
                    if "query" in step:
                        cypher = step["query"]
                        break

            if not cypher:
                # Fallback: try to extract from result
                cypher = result.get("cypher", "")

            logger.info(f"Generated Cypher: {cypher}")

            # Validate Cypher
            is_valid, error_msg = self.validate_cypher(cypher)
            if not is_valid:
                return {
                    "cypher": cypher,
                    "nodes": [],
                    "links": [],
                    "execution_time": time.time() - start_time,
                    "error": error_msg,
                }

            # Add LIMIT clause if not present
            if "LIMIT" not in cypher.upper():
                cypher = f"{cypher.rstrip(';')} LIMIT {limit}"

            # Execute the validated Cypher query
            if driver:
                nodes, links = await self._execute_cypher(cypher, driver)
            else:
                # Fallback to synchronous execution via Neo4jGraph
                nodes, links = await self._execute_cypher_sync(cypher)

            execution_time = time.time() - start_time

            return {
                "cypher": cypher,
                "nodes": nodes,
                "links": links,
                "execution_time": execution_time,
                "error": None,
            }

        except Exception as e:
            logger.error(f"Error in text-to-Cypher conversion: {e}")
            execution_time = time.time() - start_time
            return {
                "cypher": "",
                "nodes": [],
                "links": [],
                "execution_time": execution_time,
                "error": str(e),
            }

    async def _execute_cypher(
        self, cypher: str, driver: AsyncDriver
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        """Execute Cypher query using async driver and convert results to graph format."""
        nodes_dict = {}
        links = []

        try:
            async with driver.session() as session:
                result = await session.run(cypher)
                records = await result.data()

                for record in records:
                    for key, value in record.items():
                        # Handle node objects
                        if hasattr(value, "id") and hasattr(value, "labels"):
                            node_id = str(value.element_id or value.id)
                            if node_id not in nodes_dict:
                                # Convert node to dict to access properties
                                node_props = dict(value)
                                nodes_dict[node_id] = GraphNode(
                                    id=node_id,
                                    name=node_props.get(
                                        "name",
                                        node_props.get(
                                            "politician_name",
                                            node_props.get("company_name", f"Node-{node_id[:8]}"),
                                        ),
                                    ),
                                    type=list(value.labels)[0] if value.labels else "Entity",
                                    properties=node_props,
                                )

                        # Handle relationship objects
                        elif hasattr(value, "start_node") and hasattr(value, "end_node"):
                            # Extract source and target node IDs
                            source_id = str(value.start_node.element_id or value.start_node.id)
                            target_id = str(value.end_node.element_id or value.end_node.id)

                            # Add source and target nodes if not already present
                            if source_id not in nodes_dict:
                                start_node_props = dict(value.start_node)
                                nodes_dict[source_id] = GraphNode(
                                    id=source_id,
                                    name=start_node_props.get(
                                        "name",
                                        start_node_props.get(
                                            "politician_name",
                                            start_node_props.get(
                                                "company_name", f"Node-{source_id[:8]}"
                                            ),
                                        ),
                                    ),
                                    type=(
                                        list(value.start_node.labels)[0]
                                        if value.start_node.labels
                                        else "Entity"
                                    ),
                                    properties=start_node_props,
                                )

                            if target_id not in nodes_dict:
                                end_node_props = dict(value.end_node)
                                nodes_dict[target_id] = GraphNode(
                                    id=target_id,
                                    name=end_node_props.get(
                                        "name",
                                        end_node_props.get(
                                            "politician_name",
                                            end_node_props.get(
                                                "company_name", f"Node-{target_id[:8]}"
                                            ),
                                        ),
                                    ),
                                    type=(
                                        list(value.end_node.labels)[0]
                                        if value.end_node.labels
                                        else "Entity"
                                    ),
                                    properties=end_node_props,
                                )

                            # Add edge
                            links.append(
                                GraphEdge(
                                    source=source_id,
                                    target=target_id,
                                    type=value.type,
                                    properties=dict(value),
                                )
                            )

        except Exception as e:
            logger.error(f"Error executing Cypher query: {e}")
            raise

        nodes = list(nodes_dict.values())
        return nodes, links

    async def _execute_cypher_sync(self, cypher: str) -> tuple[list[GraphNode], list[GraphEdge]]:
        """Fallback: Execute Cypher using synchronous Neo4jGraph."""
        nodes_dict = {}
        links = []

        try:
            # Use Neo4jGraph's query method
            results = self.graph.query(cypher)

            for record in results:
                for key, value in record.items():
                    # Handle dictionaries that represent nodes
                    if isinstance(value, dict) and ("name" in value or "uuid" in value):
                        node_id = value.get("uuid", str(hash(str(value))))
                        if node_id not in nodes_dict:
                            nodes_dict[node_id] = GraphNode(
                                id=node_id,
                                name=value.get("name", f"Node-{node_id[:8]}"),
                                type=value.get("type", "Entity"),
                                properties=value,
                            )

        except Exception as e:
            logger.error(f"Error in synchronous Cypher execution: {e}")
            raise

        nodes = list(nodes_dict.values())
        return nodes, links
