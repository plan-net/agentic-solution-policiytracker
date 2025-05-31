"""LangChain tools for Graphiti knowledge graph search."""

import logging
from typing import Optional

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
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SearchInput(BaseModel):
    """Input schema for search tool."""

    query: str = Field(description="Search query for the knowledge graph")
    limit: int = Field(default=5, description="Maximum number of results to return")
    search_type: str = Field(
        default="comprehensive",
        description="Type of search: 'comprehensive', 'relationship_focused', 'entity_focused', or 'episode_focused'",
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
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute the search asynchronously using advanced Graphiti search configs."""
        try:
            logger.info(f"Searching knowledge graph for: {query} (type: {search_type})")

            # Select search configuration based on search type
            search_config = self._get_search_config(search_type)

            # Use the advanced _search() method with proper configuration
            search_results = await self.client._search(query=query, config=search_config)

            # Extract facts from the search results
            results = []
            if hasattr(search_results, "edges") and search_results.edges:
                results.extend(search_results.edges)
            if hasattr(search_results, "nodes") and search_results.nodes:
                results.extend(search_results.nodes)

            if not results:
                return f"No results found for query: {query}"

            # Format results for LLM consumption with source information
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

                fact_text = f"{i}. {content}"
                if hasattr(result, "name") and result.name:
                    fact_text += f" ({content_type}: {result.name})"

                # Extract source information from episodes
                source_info = await self._extract_source_info(result)
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

        except Exception as e:
            logger.error(f"Search error: {e}")
            return f"Search error: {str(e)}"

    async def _extract_source_info(self, result) -> Optional[dict[str, str]]:
        """Extract source URL and title from Graphiti result by retrieving episode content."""
        try:
            # Get episode UUIDs from the result
            if not hasattr(result, "episodes") or not result.episodes:
                logger.debug("No episodes found in result")
                return None

            # Get the first episode UUID
            episode_uuids = [str(episode) for episode in result.episodes]
            logger.debug(f"Found episode UUIDs: {episode_uuids}")

            # Retrieve episode content using Graphiti API
            episode_data = await self.client.get_nodes_and_edges_by_episode(episode_uuids[:1])

            if not episode_data or not hasattr(episode_data, "nodes"):
                logger.debug("No episode data returned")
                return None

            # Look for episode nodes that contain the original content
            for node in episode_data.nodes:
                if hasattr(node, "episode_body") and node.episode_body:
                    # Parse the YAML frontmatter from the episode body
                    source_info = self._parse_yaml_frontmatter(node.episode_body)
                    if source_info:
                        logger.info(f"Extracted source from episode content: {source_info}")
                        return source_info

            logger.debug("No source info found in episode content")
            return None

        except Exception as e:
            logger.error(f"Error extracting source from episode: {e}")
            return None

    def _parse_filename_to_url(self, filename: str) -> Optional[dict[str, str]]:
        """Parse filename to extract source URL and title."""
        try:
            # Our filenames follow pattern: YYYYMMDD_domain-with-hyphens_title-with-hyphens.md
            # Example: 20250527_reuters-com_eu-warns-shein-of-fines-in-consumer-protection-pro.md

            if not filename.endswith(".md"):
                return None

            basename = filename.replace(".md", "")
            parts = basename.split("_", 2)

            if len(parts) >= 3:
                date_part = parts[0]
                domain_part = parts[1].replace("-", ".")
                title_part = parts[2].replace("-", " ")

                # Construct the likely original URL
                url = f"https://{domain_part}"
                title = f"{domain_part} - {title_part[:60]}..."

                return {"url": url, "title": title, "date": date_part}

            return None

        except Exception as e:
            logger.warning(f"Could not parse filename: {e}")
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

    def _parse_source_description(self, description: str) -> Optional[dict[str, str]]:
        """Parse source description for URL information."""
        try:
            # Look for URL patterns in description
            import re

            url_pattern = r"https?://[^\s]+"
            urls = re.findall(url_pattern, description)

            if urls:
                url = urls[0]
                domain = url.split("/")[2] if "/" in url else url
                return {"url": url, "title": domain, "date": "unknown"}

            return None

        except Exception as e:
            logger.warning(f"Could not parse source description: {e}")
            return None

    def _extract_domain_from_fact(self, fact: str) -> Optional[dict[str, str]]:
        """Try to extract domain information from the fact text itself."""
        try:
            # Look for mentions of news sources, domains, or publications
            import re

            # Common news domain patterns
            domain_patterns = [
                r"(reuters\.com|politico\.eu|bloomberg\.com|ft\.com|techcrunch\.com)",
                r"(euronews\.com|dw\.com|bbc\.com|cnn\.com)",
                r"(ec\.europa\.eu|eur-lex\.europa\.eu)",
                r"([a-z]+\-[a-z]+\.com|[a-z]+\.eu|[a-z]+\.org)",
            ]

            for pattern in domain_patterns:
                matches = re.findall(pattern, fact.lower())
                if matches:
                    domain = matches[0] if isinstance(matches[0], str) else matches[0][0]
                    return {
                        "url": f"https://{domain}",
                        "title": f"{domain} (extracted from content)",
                        "date": "unknown",
                    }

            return None

        except Exception as e:
            logger.warning(f"Could not extract domain from fact: {e}")
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
