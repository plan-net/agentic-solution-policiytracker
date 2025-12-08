"""LangChain tools for Graphiti knowledge graph search."""

import logging
from datetime import datetime
from enum import Enum
from typing import Optional, Union

from graphiti_core import Graphiti
from graphiti_core.search.search_config_recipes import (
    COMBINED_HYBRID_SEARCH_CROSS_ENCODER,
    COMBINED_HYBRID_SEARCH_MMR,
    COMBINED_HYBRID_SEARCH_RRF,
    COMMUNITY_HYBRID_SEARCH_RRF,
    EDGE_HYBRID_SEARCH_EPISODE_MENTIONS,
    EDGE_HYBRID_SEARCH_NODE_DISTANCE,
    NODE_HYBRID_SEARCH_RRF,
)
from graphiti_core.search.search_filters import (
    ComparisonOperator,
    DateFilter,
    SearchFilters,
)
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TemporalFilterStrategy(str, Enum):
    """
    Configurable strategies for temporal filtering in Graphiti searches.

    Different report types may need different temporal filtering approaches:
    - COMPREHENSIVE: Maximize results for sparse data (weekly digest default)
    - VALID_ONLY: Point-in-time truth queries ("what was true then")
    - CREATED_ONLY: New information reports ("what's new in the graph")
    - CHANGES: Track what changed during the period
    """

    COMPREHENSIVE = "comprehensive"  # All 4 fields (OR) - maximize results
    VALID_ONLY = "valid_only"  # Only valid_at - point-in-time truth
    CREATED_ONLY = "created_only"  # Only created_at - new information
    CHANGES = "changes"  # valid_at + invalid_at - what changed


# Strategy -> Fields mapping for temporal searches
STRATEGY_FIELDS: dict[TemporalFilterStrategy, list[str]] = {
    TemporalFilterStrategy.COMPREHENSIVE: [
        "valid_at",
        "invalid_at",
        "created_at",
        "expired_at",
    ],
    TemporalFilterStrategy.VALID_ONLY: ["valid_at"],
    TemporalFilterStrategy.CREATED_ONLY: ["created_at"],
    TemporalFilterStrategy.CHANGES: ["valid_at", "invalid_at"],
}


class SearchInput(BaseModel):
    """Input schema for search tool."""

    query: str = Field(description="Search query for the knowledge graph")
    limit: int = Field(default=5, description="Maximum number of results to return")
    search_type: str = Field(
        default="comprehensive",
        description="Type of search: 'comprehensive', 'relationship_focused', 'entity_focused', or 'episode_focused'",
    )
    output_format: str = Field(
        default="structured",
        description="Output format: 'structured' (JSON with graph data) or 'text' (markdown)",
    )
    # Temporal filtering parameters
    date_filter_start: Optional[datetime] = Field(
        default=None,
        description="Start date for temporal filtering (inclusive)",
    )
    date_filter_end: Optional[datetime] = Field(
        default=None,
        description="End date for temporal filtering (inclusive)",
    )
    temporal_filter_strategy: str = Field(
        default="comprehensive",
        description="Temporal filter strategy: 'comprehensive' (all temporal fields), 'valid_only', 'created_only', or 'changes'",
    )


class GraphitiSearchTool(BaseTool):
    """LangChain tool for searching the Graphiti knowledge graph."""

    name: str = "search"
    description: str = "Advanced search using Graphiti's hybrid semantic + keyword search with reranking. Search types: 'comprehensive' (default, cross-encoder), 'relationship_focused' (edges with node distance), 'entity_focused' (nodes with RRF), 'episode_focused' (episode mentions)."
    args_schema: type[BaseModel] = SearchInput

    # Declare client as a class attribute for Pydantic
    client: Graphiti = None

    def __init__(self, graphiti_client: Graphiti, **kwargs):
        super().__init__(**kwargs)
        self.client = graphiti_client

    class Config:
        arbitrary_types_allowed = True

    def _run(
        self,
        query: str,
        limit: int = 5,
        search_type: str = "comprehensive",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute the search synchronously."""
        # For now, we'll need async support - this is a placeholder
        return "Sync search not implemented - use async version"

    async def _arun(
        self,
        query: str,
        limit: int = 5,
        search_type: str = "comprehensive",
        output_format: str = "structured",
        date_filter_start: Optional[datetime] = None,
        date_filter_end: Optional[datetime] = None,
        temporal_filter_strategy: str = "comprehensive",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Union[str, dict]:
        """Execute the search asynchronously using advanced Graphiti search configs.

        Args:
            query: Search query for the knowledge graph
            limit: Maximum number of results to return
            search_type: Type of search configuration to use
            output_format: Output format ('structured' or 'text')
            date_filter_start: Start date for temporal filtering (inclusive)
            date_filter_end: End date for temporal filtering (inclusive)
            temporal_filter_strategy: Strategy for temporal filtering
                ('comprehensive', 'valid_only', 'created_only', 'changes')
            run_manager: LangChain callback manager
        """
        try:
            logger.info(
                f"Searching knowledge graph for: {query} (type: {search_type}, format: {output_format})"
            )

            # Select search configuration based on search type
            search_config = self._get_search_config(search_type)

            # Check if temporal filtering is requested
            results = []
            if date_filter_start and date_filter_end:
                # Parse strategy string to enum
                try:
                    strategy = TemporalFilterStrategy(temporal_filter_strategy)
                except ValueError:
                    logger.warning(
                        f"Invalid temporal_filter_strategy '{temporal_filter_strategy}', "
                        "defaulting to 'comprehensive'"
                    )
                    strategy = TemporalFilterStrategy.COMPREHENSIVE

                logger.info(
                    f"Applying temporal filter: {date_filter_start.date()} to "
                    f"{date_filter_end.date()} (strategy: {strategy.value})"
                )

                # Use temporal-filtered search with OR across fields
                edges, nodes = await self._search_with_temporal_filter(
                    query=query,
                    start_date=date_filter_start,
                    end_date=date_filter_end,
                    config=search_config,
                    strategy=strategy,
                )

                results.extend(edges)
                results.extend(nodes)
            else:
                # Standard search without temporal filtering
                search_results = await self.client._search(query=query, config=search_config)

                # Extract facts from the search results
                if hasattr(search_results, "edges") and search_results.edges:
                    results.extend(search_results.edges)
                if hasattr(search_results, "nodes") and search_results.nodes:
                    results.extend(search_results.nodes)

            if not results:
                if output_format == "structured":
                    return {
                        "query": query,
                        "total_results": 0,
                        "returned_results": 0,
                        "results": [],
                        "graph_data": {"nodes": [], "edges": []},
                    }
                return f"No results found for query: {query}"

            # Choose output format
            if output_format == "structured":
                return await self._format_structured_output(results, query, search_type, limit)
            else:
                return await self._format_text_output(results, query, limit)

        except Exception as e:
            logger.error(f"Search error: {e}")
            if output_format == "structured":
                return {"error": str(e), "query": query}
            return f"Search error: {str(e)}"

    async def _format_text_output(self, results: list, query: str, limit: int) -> str:
        """Format search results as markdown text."""
        formatted_results = []
        sources = set()  # Track unique sources

        for i, result in enumerate(results[:limit], 1):
            # Handle both edges (with .fact) and nodes (with .summary)
            if hasattr(result, "fact") and result.fact:
                content = result.fact
                content_type = "Relationship"
            elif hasattr(result, "summary") and result.summary:
                content = result.summary
                content_type = "Entity"
            else:
                continue  # Skip if no content

            # Calculate relevance score
            relevance_score = self._calculate_relevance_score(result, query)
            score_text = f"[Score: {relevance_score:.3f}] " if relevance_score is not None else ""

            fact_text = f"{i}. {score_text}{content}"
            if hasattr(result, "name") and result.name:
                fact_text += f" ({content_type}: {result.name})"

            # Extract source information from episodes
            source_info = await self._extract_source_from_episodes(result)
            if source_info:
                fact_text += f" [Source: {source_info['title']}]"
                sources.add(f"- {source_info['title']}: {source_info['url']}")

            formatted_results.append(fact_text)

        response = f"Found {len(results)} facts for '{query}' (showing top {min(limit, len(results))}):\n\n"
        response += "\n".join(formatted_results)

        # Add sources section
        if sources:
            response += "\n\n**Sources:**\n" + "\n".join(sorted(sources))

        if len(results) > limit:
            response += f"\n\n... and {len(results) - limit} more results available."

        logger.info(
            f"Returning {len(formatted_results)} formatted results with {len(sources)} sources"
        )
        return response

    async def _format_structured_output(
        self, results: list, query: str, search_type: str, limit: int
    ) -> dict:
        """Format search results as structured JSON with graph data."""
        structured_results = []
        all_nodes = {}  # uuid -> node data
        all_edges = []
        node_uuids_to_enrich = set()  # Track node UUIDs that need enrichment

        for i, result in enumerate(results[:limit], 1):
            # Extract content
            if hasattr(result, "fact") and result.fact:
                content = result.fact
                result_type = "relationship"
            elif hasattr(result, "summary") and result.summary:
                content = result.summary
                result_type = "entity"
            else:
                continue

            # Extract relevance score (calculate based on query match)
            relevance_score = self._calculate_relevance_score(result, query)

            # Extract source from episodes
            source_info = await self._extract_source_from_episodes(result)

            # Get result UUID
            result_uuid = getattr(result, "uuid", None)
            if result_uuid:
                result_uuid = str(result_uuid)

            # Build result entry
            result_entry = {
                "rank": i,
                "content": content,
                "type": result_type,
                "name": getattr(result, "name", ""),
                "relevance_score": relevance_score,
                "source": source_info,
                "uuid": result_uuid,
            }

            structured_results.append(result_entry)

            # Extract graph data for visualization
            if (
                result_type == "relationship"
                and hasattr(result, "source_node_uuid")
                and hasattr(result, "target_node_uuid")
            ):
                # This is an edge
                edge_data = {
                    "uuid": result_uuid,
                    "source_uuid": str(result.source_node_uuid),
                    "target_uuid": str(result.target_node_uuid),
                    "relationship_type": getattr(result, "name", "RELATED_TO"),
                    "fact": content,
                    "created_at": str(getattr(result, "created_at", "")),
                }
                all_edges.append(edge_data)

                # Add source and target nodes (placeholders for now)
                for node_uuid in [result.source_node_uuid, result.target_node_uuid]:
                    if node_uuid and str(node_uuid) not in all_nodes:
                        all_nodes[str(node_uuid)] = {
                            "uuid": str(node_uuid),
                            "name": "Unknown",  # Will be enriched below
                            "type": "Entity",
                        }
                        node_uuids_to_enrich.add(str(node_uuid))

            elif result_type == "entity":
                # This is a node - we already have its data
                node_uuid = result_uuid
                if node_uuid and node_uuid not in all_nodes:
                    all_nodes[node_uuid] = {
                        "uuid": node_uuid,
                        "name": getattr(result, "name", "Unknown"),
                        "type": ", ".join(getattr(result, "labels", ["Entity"])),
                        "summary": content,
                        "created_at": str(getattr(result, "created_at", "")),
                    }

        # Enrich node names by fetching entity data
        if node_uuids_to_enrich:
            await self._enrich_node_names(all_nodes, node_uuids_to_enrich)

        # Aggregate sources
        sources = []
        source_counts = {}
        for result in structured_results:
            if result["source"]:
                source_key = result["source"]["title"]
                if source_key not in source_counts:
                    source_counts[source_key] = {
                        "title": result["source"]["title"],
                        "url": result["source"]["url"],
                        "count": 0,
                    }
                source_counts[source_key]["count"] += 1

        sources = list(source_counts.values())

        return {
            "query": query,
            "search_type": search_type,
            "total_results": len(results),
            "returned_results": len(structured_results),
            "results": structured_results,
            "graph_data": {
                "nodes": list(all_nodes.values()),
                "edges": all_edges,
            },
            "sources": sources,
        }

    def _calculate_relevance_score(self, result, query: str) -> Optional[float]:
        """Calculate relevance score based on query term matching."""
        try:
            # Extract content from result
            if hasattr(result, "fact") and result.fact:
                content = result.fact.lower()
            elif hasattr(result, "summary") and result.summary:
                content = result.summary.lower()
            else:
                return None

            # Tokenize query
            query_terms = set(query.lower().split())

            # Count matching terms
            matches = sum(1 for term in query_terms if term in content)

            # Calculate score as percentage of query terms found
            if query_terms:
                score = matches / len(query_terms)
                return round(score, 3)

            return None
        except Exception as e:
            logger.debug(f"Error calculating relevance score: {e}")
            return None

    def _extract_relevance_score(self, result) -> Optional[float]:
        """Legacy method - kept for backward compatibility in text output."""
        # Note: Graphiti search results don't expose score attributes
        # This method is deprecated in favor of _calculate_relevance_score
        return None

    async def _extract_source_info(self, result) -> Optional[dict[str, str]]:
        """Extract source URL and title from Graphiti result (simplified)."""
        try:
            # Method 1: Try to get episode metadata with YAML frontmatter
            if hasattr(result, "episodes") and result.episodes:
                episode_uuids = [str(episode) for episode in result.episodes]

                # Try to retrieve episode content
                try:
                    episode_data = await self.client.get_nodes_and_edges_by_episode(
                        episode_uuids[:1]
                    )

                    if episode_data and hasattr(episode_data, "nodes"):
                        # Look for episode nodes with YAML frontmatter
                        for node in episode_data.nodes:
                            if hasattr(node, "episode_body") and node.episode_body:
                                source_info = self._parse_yaml_frontmatter(node.episode_body)
                                if source_info:
                                    logger.debug(
                                        f"Found source in episode metadata: {source_info['title']}"
                                    )
                                    return source_info
                except Exception as e:
                    logger.debug(f"Could not retrieve episode content: {e}")

                # Method 2: Parse episode name as fallback
                if hasattr(result, "episode_name"):
                    source_info = self._parse_episode_name(result.episode_name)
                    if source_info:
                        logger.debug(f"Parsed source from episode name: {source_info['title']}")
                        return source_info

                # Try parsing first episode UUID if it looks like a name
                if episode_uuids and "_" in str(episode_uuids[0]):
                    source_info = self._parse_episode_name(str(episode_uuids[0]))
                    if source_info:
                        logger.debug(f"Parsed source from episode UUID: {source_info['title']}")
                        return source_info

            return None

        except Exception as e:
            logger.debug(f"Error extracting source: {e}")
            return None

    def _parse_episode_name(self, episode_name: str) -> Optional[dict[str, str]]:
        """Parse episode name to extract source information."""
        try:
            # Episode names from our ETL follow pattern: YYYYMMDD_domain_title
            parts = episode_name.split("_", 2)
            if len(parts) >= 3:
                date_part = parts[0]
                domain = parts[1].replace("-", ".")
                title_part = parts[2].replace("-", " ").replace(".md", "")

                # Construct likely URL
                url = f"https://{domain}"
                title = f"{domain} - {title_part[:50]}..."

                return {"url": url, "title": title, "date": date_part}

            return None

        except Exception as e:
            logger.warning(f"Could not parse episode name: {e}")
            return None

    def _get_search_config(self, search_type: str):
        """Get appropriate search configuration based on search type."""
        search_configs = {
            "comprehensive": COMBINED_HYBRID_SEARCH_CROSS_ENCODER,
            "relationship_focused": EDGE_HYBRID_SEARCH_NODE_DISTANCE,
            "entity_focused": NODE_HYBRID_SEARCH_RRF,
            "episode_focused": EDGE_HYBRID_SEARCH_EPISODE_MENTIONS,
            "community_focused": COMMUNITY_HYBRID_SEARCH_RRF,
            "mmr_balanced": COMBINED_HYBRID_SEARCH_MMR,
            "rrf_balanced": COMBINED_HYBRID_SEARCH_RRF,
        }

        config = search_configs.get(search_type, COMBINED_HYBRID_SEARCH_CROSS_ENCODER)
        logger.debug(f"Using search config: {config} for type: {search_type}")
        return config

    async def _search_with_temporal_filter(
        self,
        query: str,
        start_date: datetime,
        end_date: datetime,
        config,
        strategy: TemporalFilterStrategy = TemporalFilterStrategy.COMPREHENSIVE,
    ) -> tuple[list, list]:
        """
        Run searches across temporal fields based on strategy and merge results.

        Graphiti's SearchFilters uses AND logic between different temporal fields.
        To achieve OR logic (capture everything that "touched" the date range),
        we run separate searches for each temporal field and merge the results.

        Args:
            query: Search query
            start_date: Filter start date (inclusive)
            end_date: Filter end date (inclusive)
            config: Search configuration
            strategy: Which temporal fields to search (configurable)

        Returns:
            Tuple of (edges, nodes) - deduplicated lists of results
        """
        # Build date range filter: start <= field <= end
        date_range = [
            DateFilter(
                date=start_date, comparison_operator=ComparisonOperator.greater_than_equal
            ),
            DateFilter(
                date=end_date, comparison_operator=ComparisonOperator.less_than_equal
            ),
        ]

        # Get fields for this strategy
        fields_to_search = STRATEGY_FIELDS.get(
            strategy, STRATEGY_FIELDS[TemporalFilterStrategy.COMPREHENSIVE]
        )

        logger.info(
            f"Temporal search strategy: {strategy.value}, fields: {fields_to_search}, "
            f"date range: {start_date.date()} to {end_date.date()}"
        )

        all_edges = []
        all_nodes = []
        seen_edge_uuids: set[str] = set()
        seen_node_uuids: set[str] = set()

        # Search each temporal field in the strategy
        for field_name in fields_to_search:
            try:
                # Build filter with only this temporal field
                filter_kwargs = {field_name: [date_range]}
                search_filter = SearchFilters(**filter_kwargs)

                logger.debug(f"Searching with {field_name} filter...")

                # Use search_ method (note: underscore version with filter support)
                results = await self.client.search_(
                    query=query,
                    config=config,
                    search_filter=search_filter,
                )

                # Deduplicate edges by UUID
                if hasattr(results, "edges") and results.edges:
                    for edge in results.edges:
                        edge_uuid = str(getattr(edge, "uuid", ""))
                        if edge_uuid and edge_uuid not in seen_edge_uuids:
                            seen_edge_uuids.add(edge_uuid)
                            all_edges.append(edge)

                # Deduplicate nodes by UUID
                if hasattr(results, "nodes") and results.nodes:
                    for node in results.nodes:
                        node_uuid = str(getattr(node, "uuid", ""))
                        if node_uuid and node_uuid not in seen_node_uuids:
                            seen_node_uuids.add(node_uuid)
                            all_nodes.append(node)

                logger.debug(
                    f"  {field_name}: found {len(results.edges) if hasattr(results, 'edges') and results.edges else 0} edges, "
                    f"{len(results.nodes) if hasattr(results, 'nodes') and results.nodes else 0} nodes"
                )

            except Exception as e:
                logger.warning(f"Temporal search failed for {field_name}: {e}")
                continue

        logger.info(
            f"Temporal search complete: {len(all_edges)} unique edges, "
            f"{len(all_nodes)} unique nodes across {len(fields_to_search)} fields"
        )

        return all_edges, all_nodes

    def _parse_yaml_frontmatter(self, content: str) -> Optional[dict[str, str]]:
        """Parse YAML frontmatter from episode content to extract source URLs."""
        try:
            import re

            import yaml

            # Check if content starts with YAML frontmatter
            if not content.startswith("---"):
                return None

            # Extract YAML frontmatter
            yaml_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
            if not yaml_match:
                return None

            yaml_content = yaml_match.group(1)
            metadata = yaml.safe_load(yaml_content)

            if not isinstance(metadata, dict):
                return None

            # Extract URL and title from metadata
            url = metadata.get("url") or metadata.get("source_url")
            title = metadata.get("title", "")
            source = metadata.get("source", "")

            if url:
                # Create a readable title
                if title and source:
                    display_title = f"{source}: {title[:60]}..."
                elif title:
                    display_title = title[:60] + "..." if len(title) > 60 else title
                elif source:
                    display_title = source
                else:
                    # Extract domain from URL as fallback
                    try:
                        from urllib.parse import urlparse

                        domain = urlparse(url).netloc
                        display_title = domain
                    except:
                        display_title = "Unknown Source"

                return {
                    "url": url,
                    "title": display_title,
                    "source": source,
                    "original_title": title,
                }

            return None

        except Exception as e:
            logger.warning(f"Could not parse YAML frontmatter: {e}")
            return None

    async def _extract_source_from_episodes(self, result) -> Optional[dict[str, str]]:
        """Extract source information from episode UUIDs using direct Neo4j query."""
        try:
            if not hasattr(result, "episodes") or not result.episodes:
                return None

            # Get episode UUIDs
            episode_uuids = [str(ep) for ep in result.episodes[:1]]  # Check first episode only

            # Query Neo4j directly for Episodic node metadata
            # Format: political_doc_YYYYMMDD_domain_title_timestamp_chunk_N
            query = """
                MATCH (e:Episodic)
                WHERE e.uuid IN $uuids
                RETURN e.uuid AS uuid, e.name AS name, e.source AS source,
                       e.source_description AS source_description
                LIMIT 1
            """

            async with self.client.driver.session() as session:
                result_data = await session.run(query, {"uuids": episode_uuids})
                records = await result_data.data()

                if records:
                    record = records[0]

                    # First priority: Check source property
                    if record.get("source"):
                        source_info = self._parse_source_property(
                            record["source"], record.get("source_description")
                        )
                        if source_info:
                            logger.debug(
                                f"Extracted source from Episodic.source: {source_info['title']}"
                            )
                            return source_info

                    # Second priority: Parse episode name
                    if record.get("name"):
                        source_info = self._parse_episodic_name(record["name"])
                        if source_info:
                            logger.debug(
                                f"Extracted source from Episodic.name: {source_info['title']}"
                            )
                            return source_info

            return None

        except Exception as e:
            logger.debug(f"Error extracting source from episodes: {e}")
            return None

    def _parse_source_property(
        self, source: str, source_description: str = None
    ) -> Optional[dict[str, str]]:
        """Parse source property from Episodic node."""
        try:
            # Source property is usually "text" - not useful
            # Source description has format: "Political document chunk N/M: YYYYMMDD_domain_title.md"
            if not source_description:
                return None

            # Extract filename from source_description
            # Format: "Political document chunk N/M: YYYYMMDD_domain_title.md"
            if ":" in source_description:
                # Split on colon to get filename part
                parts = source_description.split(":", 1)
                if len(parts) == 2:
                    filename = parts[1].strip()

                    # Remove .md extension
                    if filename.endswith(".md"):
                        filename = filename[:-3]

                    # Parse the filename using existing method
                    source_info = self._parse_episodic_name(filename)
                    if source_info:
                        return source_info

            return None

        except Exception as e:
            logger.debug(f"Could not parse source property: {e}")
            return None

    def _parse_episodic_name(self, name: str) -> Optional[dict[str, str]]:
        """Parse Episodic node name to extract source information."""
        try:
            # Expected format: political_doc_YYYYMMDD_domain_title_timestamp_chunk_N
            # Example: political_doc_20250516_abcnews-go-com_long-running-eu-antitrust_20251030_112139_chunk_0

            # Remove 'political_doc_' prefix if present
            if name.startswith("political_doc_"):
                name = name[14:]  # Remove 'political_doc_'

            # Split by underscore
            parts = name.split("_")

            if len(parts) < 3:
                return None

            # First part is date (YYYYMMDD)
            date_part = parts[0] if parts[0].isdigit() and len(parts[0]) == 8 else None

            # Second part is domain (with hyphens)
            domain_part = parts[1].replace("-", ".") if len(parts) > 1 else None

            if not domain_part:
                return None

            # Collect title parts (between domain and timestamp/chunk markers)
            title_parts = []
            for i in range(2, len(parts)):
                part = parts[i]
                # Stop at timestamp (8 digits followed by 6 digits)
                if part.isdigit() and len(part) >= 8:
                    break
                # Stop at 'chunk'
                if part == "chunk":
                    break
                title_parts.append(part)

            # Build title
            title = " ".join(title_parts).replace("-", " ") if title_parts else ""

            # Construct URL
            url = f"https://{domain_part}"

            # Create display title
            if title:
                display_title = f"{domain_part}: {title[:60]}"
                if len(title) > 60:
                    display_title += "..."
            else:
                display_title = domain_part

            return {"url": url, "title": display_title, "date": date_part}

        except Exception as e:
            logger.debug(f"Could not parse Episodic name: {e}")
            return None

    def _parse_episode_path(self, path: str) -> Optional[dict[str, str]]:
        """Legacy method - kept for backward compatibility."""
        # Delegate to _parse_episodic_name since format is similar
        return self._parse_episodic_name(path)

    async def _enrich_node_names(self, all_nodes: dict, node_uuids_to_enrich: set):
        """Enrich node names by querying all nodes at once via Neo4j."""
        try:
            # Get all node UUIDs we need to enrich
            uuid_list = list(node_uuids_to_enrich)

            if not uuid_list:
                return

            # Query Neo4j directly to get node names
            # Use client's internal driver to run Cypher query
            query = """
                MATCH (n:Entity)
                WHERE n.uuid IN $uuids
                RETURN n.uuid AS uuid, n.name AS name, labels(n) AS labels
            """

            # Run query through Graphiti's driver
            async with self.client.driver.session() as session:
                result = await session.run(query, {"uuids": uuid_list})
                records = await result.data()

                # Update node names
                for record in records:
                    node_uuid = str(record["uuid"])
                    if node_uuid in all_nodes:
                        all_nodes[node_uuid]["name"] = record.get("name", "Unknown")
                        labels = record.get("labels", [])
                        if labels:
                            all_nodes[node_uuid]["type"] = ", ".join(labels)

                logger.debug(f"Enriched {len(records)} node names from {len(uuid_list)} requested")

        except Exception as e:
            logger.warning(f"Could not enrich node names: {e}")
            # Silently fail - nodes will keep "Unknown" name
