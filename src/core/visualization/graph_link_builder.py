"""
Graph Link Builder for Report Visualization.

Generates links to the external graph visualization service
for interactive exploration of entities discovered in reports.
"""

import os
from typing import Optional
from urllib.parse import urlencode


class GraphLinkBuilder:
    """
    Build links to the external graph visualization service.

    The graph visualization service provides an interactive 3D/2D
    view of the knowledge graph, allowing users to explore entities
    and relationships discovered during report generation.

    Example:
        builder = GraphLinkBuilder()
        link = builder.build_report_link(
            report_id="weekly_KW48_2025",
            entities=["DSA", "Meta", "European Commission"],
        )
        # Returns: http://localhost:5173?report_id=weekly_KW48_2025&entities=DSA,Meta,...

    Attributes:
        base_url: Base URL of the graph visualization service
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
    ):
        """
        Initialize the graph link builder.

        Args:
            base_url: Base URL for graph visualization service.
                     Defaults to GRAPH_VIZ_URL env var or localhost:5173
        """
        self.base_url = base_url or os.getenv(
            "GRAPH_VIZ_URL", "http://localhost:5173"
        )

    def build_report_link(
        self,
        report_id: str,
        entities: list[str],
        mode: str = "3d",
        view: str = "report-entities",
    ) -> str:
        """
        Generate visualization URL for report entities.

        Creates a link that will open the graph visualization service
        focused on the entities discovered in this report.

        Args:
            report_id: Unique identifier for the report
            entities: List of entity names to visualize
            mode: Visualization mode ("3d" or "2d")
            view: View type ("report-entities", "graph", "timeline")

        Returns:
            Full URL to the graph visualization

        Example:
            >>> builder = GraphLinkBuilder()
            >>> builder.build_report_link("weekly_KW48", ["DSA", "Meta"])
            'http://localhost:5173?report_id=weekly_KW48&entities=DSA,Meta&mode=3d&view=report-entities'
        """
        # Limit entities for URL length (browser limits ~2000 chars)
        limited_entities = entities[:20] if len(entities) > 20 else entities

        # Clean entity names for URL
        clean_entities = [
            self._clean_entity_name(e) for e in limited_entities
        ]

        params = {
            "report_id": report_id,
            "entities": ",".join(clean_entities),
            "mode": mode,
            "view": view,
        }

        return f"{self.base_url}?{urlencode(params)}"

    def build_entity_link(
        self,
        entity_name: str,
        entity_type: Optional[str] = None,
    ) -> str:
        """
        Generate visualization URL for a single entity.

        Args:
            entity_name: Name of the entity to visualize
            entity_type: Optional entity type for filtering

        Returns:
            Full URL to the entity visualization
        """
        params = {
            "entity": self._clean_entity_name(entity_name),
            "view": "entity-detail",
        }

        if entity_type:
            params["type"] = entity_type

        return f"{self.base_url}?{urlencode(params)}"

    def build_relationship_link(
        self,
        source_entity: str,
        target_entity: str,
    ) -> str:
        """
        Generate visualization URL for a relationship between entities.

        Args:
            source_entity: Source entity name
            target_entity: Target entity name

        Returns:
            Full URL to the relationship visualization
        """
        params = {
            "source": self._clean_entity_name(source_entity),
            "target": self._clean_entity_name(target_entity),
            "view": "relationship",
        }

        return f"{self.base_url}?{urlencode(params)}"

    def generate_markdown_section(
        self,
        report_id: str,
        entities: list[str],
        include_entity_list: bool = True,
        max_entities_shown: int = 15,
    ) -> str:
        """
        Generate a markdown section with graph visualization link.

        Creates a formatted markdown section suitable for inclusion
        in the final report, with a link to explore the graph and
        optionally a summary table of discovered entities.

        Args:
            report_id: Unique identifier for the report
            entities: List of entity names discovered
            include_entity_list: Whether to include entity summary table
            max_entities_shown: Maximum entities to show in table

        Returns:
            Markdown-formatted section string

        Example:
            >>> builder = GraphLinkBuilder()
            >>> print(builder.generate_markdown_section("weekly_KW48", ["DSA", "Meta"]))
            ## Entity Relationship Graph

            **[Explore the knowledge graph for this report →](http://localhost:5173?...)**

            *2 entities discovered across all categories.*
        """
        link = self.build_report_link(report_id, entities)

        sections = [
            "## Entity Relationship Graph",
            "",
            f"**[Explore the knowledge graph for this report →]({link})**",
            "",
            f"*{len(entities)} entities discovered across all categories.*",
        ]

        if include_entity_list and entities:
            sections.extend([
                "",
                "### Key Entities",
                "",
                "| Entity | Count |",
                "|--------|-------|",
            ])

            # Count entity occurrences and show top ones
            entity_counts = {}
            for entity in entities:
                clean = self._clean_entity_name(entity)
                entity_counts[clean] = entity_counts.get(clean, 0) + 1

            sorted_entities = sorted(
                entity_counts.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:max_entities_shown]

            for entity, count in sorted_entities:
                sections.append(f"| {entity} | {count} |")

            if len(entity_counts) > max_entities_shown:
                sections.append(
                    f"\n*... and {len(entity_counts) - max_entities_shown} more entities*"
                )

        return "\n".join(sections)

    def _clean_entity_name(self, name: str) -> str:
        """
        Clean an entity name for URL inclusion.

        Removes or replaces characters that might cause URL issues.

        Args:
            name: Raw entity name

        Returns:
            Cleaned entity name safe for URLs
        """
        if not name:
            return ""

        # Replace common problematic characters
        cleaned = name.strip()
        cleaned = cleaned.replace("&", "and")
        cleaned = cleaned.replace("#", "")
        cleaned = cleaned.replace("?", "")

        # Truncate very long names
        if len(cleaned) > 50:
            cleaned = cleaned[:47] + "..."

        return cleaned
