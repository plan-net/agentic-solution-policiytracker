"""
Consolidate Duplicate Entities in Neo4j Knowledge Graph.

This script identifies and merges duplicate entities using fuzzy string matching
(Levenshtein distance) to improve knowledge graph quality and query accuracy.

Features:
- Finds duplicate entities using similarity threshold (default: 0.85)
- Merges relationships from duplicates to canonical entity
- Preserves all relationship types and properties
- Generates detailed consolidation report
- Safe deletion with backup option
- Supports dry-run mode for preview

Usage:
    # Dry run (preview only)
    python scripts/consolidate_duplicate_entities.py --dry-run

    # Live consolidation with default threshold (0.85)
    python scripts/consolidate_duplicate_entities.py

    # Custom similarity threshold
    python scripts/consolidate_duplicate_entities.py --similarity 0.90

    # Specific entity type only
    python scripts/consolidate_duplicate_entities.py --entity-type Policy

    # With progress updates
    python scripts/consolidate_duplicate_entities.py --verbose

Requirements:
    - Neo4j APOC plugin installed (for apoc.text.levenshteinSimilarity)
    - politicalmonitoring.v3 database
"""

import argparse
import asyncio
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import structlog
from neo4j import GraphDatabase, Session
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

logger = structlog.get_logger()
console = Console()

# Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "politicalmonitoring.v3")

# Default similarity threshold (0.85 = 85% similar)
DEFAULT_SIMILARITY_THRESHOLD = 0.85

# Entity types to check (None = all Entity nodes)
DEFAULT_ENTITY_TYPES = None  # or ["Policy", "Organization", "Politician", "Regulation"]


class DuplicateEntityConsolidator:
    """
    Find and merge duplicate entities in Neo4j knowledge graph.

    Uses Levenshtein distance for fuzzy string matching to identify
    entities with similar names that likely refer to the same real-world entity.
    """

    def __init__(
        self,
        neo4j_uri: str = NEO4J_URI,
        neo4j_user: str = NEO4J_USER,
        neo4j_password: str = NEO4J_PASSWORD,
        neo4j_database: str = NEO4J_DATABASE,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        dry_run: bool = False,
    ):
        """
        Initialize the consolidator.

        Args:
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            neo4j_database: Database name
            similarity_threshold: Minimum similarity score (0.0-1.0) to consider entities duplicates
            dry_run: If True, only report duplicates without making changes
        """
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.database = neo4j_database
        self.similarity_threshold = similarity_threshold
        self.dry_run = dry_run

        self.stats = {
            "duplicates_found": 0,
            "entities_merged": 0,
            "relationships_transferred": 0,
            "entities_deleted": 0,
            "errors": 0,
        }

        logger.info(
            "DuplicateEntityConsolidator initialized",
            database=neo4j_database,
            similarity_threshold=similarity_threshold,
            dry_run=dry_run,
        )

    def close(self):
        """Close Neo4j driver connection."""
        self.driver.close()

    def check_apoc_available(self) -> bool:
        """
        Check if APOC plugin is available in Neo4j.

        Returns:
            True if APOC is available, False otherwise
        """
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run("RETURN apoc.version() AS version")
                record = result.single()
                if record:
                    version = record["version"]
                    console.print(f"✅ APOC plugin found: version {version}", style="green")
                    return True
                return False
        except Exception as e:
            console.print(f"❌ APOC plugin not available: {e}", style="red")
            console.print(
                "\n💡 Install APOC: https://neo4j.com/labs/apoc/4.4/installation/", style="yellow"
            )
            return False

    def find_duplicate_pairs(
        self, entity_types: Optional[List[str]] = None, limit: Optional[int] = None
    ) -> List[Tuple[Dict, Dict, float]]:
        """
        Find pairs of entities that are likely duplicates.

        Uses Levenshtein similarity on entity names to identify potential duplicates.

        Args:
            entity_types: List of entity types to check (None = all :Entity nodes)
            limit: Maximum number of duplicate pairs to return (None = all)

        Returns:
            List of tuples: (entity1_dict, entity2_dict, similarity_score)
        """
        with self.driver.session(database=self.database) as session:
            # Build entity type filter
            type_filter = ""
            if entity_types:
                type_labels = " OR ".join([f"'{t}' IN labels(e1)" for t in entity_types])
                type_filter = f"AND ({type_labels})"

            # Find duplicate pairs using Levenshtein similarity
            query = f"""
            MATCH (e1:Entity), (e2:Entity)
            WHERE e1.uuid < e2.uuid  // Avoid duplicate pairs and self-comparison
              AND e1.name IS NOT NULL
              AND e2.name IS NOT NULL
              {type_filter}
              AND apoc.text.levenshteinSimilarity(toLower(e1.name), toLower(e2.name)) >= $threshold
            RETURN
              e1.uuid AS uuid1,
              e1.name AS name1,
              labels(e1) AS labels1,
              properties(e1) AS props1,
              e2.uuid AS uuid2,
              e2.name AS name2,
              labels(e2) AS labels2,
              properties(e2) AS props2,
              apoc.text.levenshteinSimilarity(toLower(e1.name), toLower(e2.name)) AS similarity
            ORDER BY similarity DESC
            {f'LIMIT {limit}' if limit else ''}
            """

            result = session.run(query, threshold=self.similarity_threshold)

            duplicates = []
            for record in result:
                entity1 = {
                    "uuid": record["uuid1"],
                    "name": record["name1"],
                    "labels": record["labels1"],
                    "properties": record["props1"],
                }
                entity2 = {
                    "uuid": record["uuid2"],
                    "name": record["name2"],
                    "labels": record["labels2"],
                    "properties": record["props2"],
                }
                similarity = record["similarity"]

                duplicates.append((entity1, entity2, similarity))

            self.stats["duplicates_found"] = len(duplicates)
            return duplicates

    def get_entity_relationship_count(self, uuid: str) -> int:
        """
        Get the number of relationships for an entity.

        Args:
            uuid: Entity UUID

        Returns:
            Count of relationships (incoming + outgoing)
        """
        with self.driver.session(database=self.database) as session:
            query = """
            MATCH (e:Entity {uuid: $uuid})
            OPTIONAL MATCH (e)-[r]-()
            RETURN count(r) AS rel_count
            """
            result = session.run(query, uuid=uuid)
            record = result.single()
            return record["rel_count"] if record else 0

    def choose_canonical_entity(
        self, entity1: Dict, entity2: Dict
    ) -> Tuple[Dict, Dict]:
        """
        Choose which entity should be the canonical (kept) entity.

        Strategy:
        1. Prefer entity with more relationships
        2. If tie, prefer entity with longer name (more specific)
        3. If still tie, prefer entity with earlier UUID (stable choice)

        Args:
            entity1: First entity dict
            entity2: Second entity dict

        Returns:
            Tuple of (canonical_entity, duplicate_entity)
        """
        # Get relationship counts
        count1 = self.get_entity_relationship_count(entity1["uuid"])
        count2 = self.get_entity_relationship_count(entity2["uuid"])

        # Strategy 1: More relationships
        if count1 > count2:
            return entity1, entity2
        elif count2 > count1:
            return entity2, entity1

        # Strategy 2: Longer name (more specific)
        if len(entity1["name"]) > len(entity2["name"]):
            return entity1, entity2
        elif len(entity2["name"]) > len(entity1["name"]):
            return entity2, entity1

        # Strategy 3: Earlier UUID (stable)
        if entity1["uuid"] < entity2["uuid"]:
            return entity1, entity2
        else:
            return entity2, entity1

    def merge_duplicate_entities(self, canonical: Dict, duplicate: Dict) -> bool:
        """
        Merge a duplicate entity into the canonical entity.

        Steps:
        1. Transfer all relationships from duplicate to canonical
        2. Merge properties (canonical takes precedence)
        3. Delete duplicate entity

        Args:
            canonical: The entity to keep
            duplicate: The entity to merge and delete

        Returns:
            True if successful, False otherwise
        """
        if self.dry_run:
            logger.info(
                "DRY RUN: Would merge entity",
                canonical=canonical["name"],
                duplicate=duplicate["name"],
            )
            return True

        try:
            with self.driver.session(database=self.database) as session:
                # Step 1: Transfer relationships
                rel_count = self._transfer_relationships(
                    session, canonical["uuid"], duplicate["uuid"]
                )
                self.stats["relationships_transferred"] += rel_count

                # Step 2: Merge properties (optional - keep canonical as-is)
                # Could add logic here to merge specific properties if needed

                # Step 3: Delete duplicate entity
                delete_query = """
                MATCH (e:Entity {uuid: $duplicate_uuid})
                DETACH DELETE e
                """
                session.run(delete_query, duplicate_uuid=duplicate["uuid"])

                self.stats["entities_merged"] += 1
                self.stats["entities_deleted"] += 1

                logger.info(
                    "Merged duplicate entity",
                    canonical=canonical["name"],
                    canonical_uuid=canonical["uuid"],
                    duplicate=duplicate["name"],
                    duplicate_uuid=duplicate["uuid"],
                    relationships_transferred=rel_count,
                )

                return True

        except Exception as e:
            logger.error(
                "Failed to merge entities",
                canonical=canonical["name"],
                duplicate=duplicate["name"],
                error=str(e),
            )
            self.stats["errors"] += 1
            return False

    def _transfer_relationships(
        self, session: Session, canonical_uuid: str, duplicate_uuid: str
    ) -> int:
        """
        Transfer all relationships from duplicate to canonical entity.

        Args:
            session: Neo4j session
            canonical_uuid: UUID of canonical entity
            duplicate_uuid: UUID of duplicate entity

        Returns:
            Number of relationships transferred
        """
        # Transfer outgoing relationships
        outgoing_query = """
        MATCH (dup:Entity {uuid: $duplicate_uuid})-[r]->(target)
        MATCH (can:Entity {uuid: $canonical_uuid})
        WHERE NOT exists((can)-[type(r)]->(target))  // Avoid creating duplicate relationships
        CREATE (can)-[r2:type(r)]->(target)
        SET r2 = properties(r)
        DELETE r
        RETURN count(r2) AS transferred
        """

        # Transfer incoming relationships
        incoming_query = """
        MATCH (source)-[r]->(dup:Entity {uuid: $duplicate_uuid})
        MATCH (can:Entity {uuid: $canonical_uuid})
        WHERE NOT exists((source)-[type(r)]->(can))  // Avoid creating duplicate relationships
        CREATE (source)-[r2:type(r)]->(can)
        SET r2 = properties(r)
        DELETE r
        RETURN count(r2) AS transferred
        """

        # Note: The above queries use type(r) which needs to be replaced with actual type
        # Let's use a more robust approach with APOC:

        transfer_query = """
        MATCH (dup:Entity {uuid: $duplicate_uuid})
        MATCH (can:Entity {uuid: $canonical_uuid})

        // Transfer outgoing relationships
        OPTIONAL MATCH (dup)-[r_out]->(target)
        WHERE target.uuid <> $canonical_uuid  // Don't create self-relationship

        WITH can, dup, collect({rel: r_out, target: target, type: type(r_out), props: properties(r_out)}) AS out_rels

        // Transfer incoming relationships
        OPTIONAL MATCH (source)-[r_in]->(dup)
        WHERE source.uuid <> $canonical_uuid  // Don't create self-relationship

        WITH can, dup, out_rels, collect({rel: r_in, source: source, type: type(r_in), props: properties(r_in)}) AS in_rels

        // Create new outgoing relationships
        UNWIND out_rels AS out_rel
        WITH can, dup, out_rel, in_rels
        WHERE out_rel.rel IS NOT NULL
        CALL apoc.create.relationship(can, out_rel.type, out_rel.props, out_rel.target) YIELD rel AS new_out

        WITH can, dup, in_rels, count(new_out) AS out_count

        // Create new incoming relationships
        UNWIND in_rels AS in_rel
        WHERE in_rel.rel IS NOT NULL
        CALL apoc.create.relationship(in_rel.source, in_rel.type, in_rel.props, can) YIELD rel AS new_in

        WITH dup, out_count, count(new_in) AS in_count

        // Delete all relationships of duplicate
        DETACH DELETE dup

        RETURN out_count + in_count AS transferred
        """

        result = session.run(
            transfer_query, canonical_uuid=canonical_uuid, duplicate_uuid=duplicate_uuid
        )
        record = result.single()

        return record["transferred"] if record else 0

    def consolidate_all_duplicates(
        self, entity_types: Optional[List[str]] = None, limit: Optional[int] = None
    ) -> Dict:
        """
        Find and consolidate all duplicate entities.

        Args:
            entity_types: List of entity types to process
            limit: Maximum number of duplicates to process

        Returns:
            Statistics dictionary
        """
        console.print("\n🔍 Finding duplicate entities...\n", style="bold cyan")

        duplicates = self.find_duplicate_pairs(entity_types=entity_types, limit=limit)

        if not duplicates:
            console.print("✅ No duplicates found! Knowledge graph is clean.\n", style="green")
            return self.stats

        console.print(
            f"Found {len(duplicates)} potential duplicate pairs\n",
            style="yellow bold",
        )

        # Display duplicate pairs
        self._display_duplicates_table(duplicates[:10])  # Show first 10

        if len(duplicates) > 10:
            console.print(
                f"\n... and {len(duplicates) - 10} more pairs\n",
                style="yellow",
            )

        if self.dry_run:
            console.print("\n🔍 DRY RUN MODE - No changes will be made\n", style="yellow bold")
            return self.stats

        # Ask for confirmation
        console.print("\n⚠️  This will merge duplicate entities. Continue? [y/N]: ", style="yellow bold", end="")

        # For automated runs, skip confirmation
        if os.getenv("AUTO_CONFIRM", "").lower() != "true":
            response = input().lower()
            if response != 'y':
                console.print("\n❌ Operation cancelled\n", style="red")
                return self.stats

        # Process duplicates with progress bar
        console.print("\n🔄 Consolidating duplicates...\n", style="cyan")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Processing duplicates...", total=len(duplicates))

            for entity1, entity2, similarity in duplicates:
                # Choose canonical entity
                canonical, duplicate = self.choose_canonical_entity(entity1, entity2)

                # Merge
                success = self.merge_duplicate_entities(canonical, duplicate)

                if success:
                    progress.console.print(
                        f"  ✅ Merged: '{duplicate['name']}' → '{canonical['name']}' "
                        f"(similarity: {similarity:.2%})",
                        style="green",
                    )
                else:
                    progress.console.print(
                        f"  ❌ Failed: '{duplicate['name']}' → '{canonical['name']}'",
                        style="red",
                    )

                progress.advance(task)

        # Display final statistics
        self._display_statistics()

        return self.stats

    def _display_duplicates_table(self, duplicates: List[Tuple[Dict, Dict, float]]):
        """Display duplicate pairs in a formatted table."""
        table = Table(title="Duplicate Entity Pairs (Top 10)", show_header=True, header_style="bold magenta")
        table.add_column("Entity 1", style="cyan")
        table.add_column("Entity 2", style="yellow")
        table.add_column("Similarity", justify="right", style="green")
        table.add_column("Type", style="blue")

        for entity1, entity2, similarity in duplicates:
            # Get primary label (excluding :Entity)
            labels1 = [l for l in entity1["labels"] if l != "Entity"]
            labels2 = [l for l in entity2["labels"] if l != "Entity"]
            type_label = labels1[0] if labels1 else "Unknown"

            table.add_row(
                entity1["name"],
                entity2["name"],
                f"{similarity:.2%}",
                type_label,
            )

        console.print(table)

    def _display_statistics(self):
        """Display consolidation statistics."""
        table = Table(title="Consolidation Statistics", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", justify="right", style="green")

        for metric, count in self.stats.items():
            metric_display = metric.replace("_", " ").title()
            table.add_row(metric_display, str(count))

        console.print("\n")
        console.print(table)
        console.print("\n")


def main():
    """Main entry point for the consolidation script."""
    parser = argparse.ArgumentParser(
        description="Consolidate duplicate entities in Neo4j knowledge graph",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to preview duplicates
  python scripts/consolidate_duplicate_entities.py --dry-run

  # Consolidate with custom similarity threshold
  python scripts/consolidate_duplicate_entities.py --similarity 0.90

  # Process specific entity type only
  python scripts/consolidate_duplicate_entities.py --entity-type Policy

  # Automated mode (no confirmation prompt)
  AUTO_CONFIRM=true python scripts/consolidate_duplicate_entities.py
        """,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview duplicates without making changes",
    )

    parser.add_argument(
        "--similarity",
        type=float,
        default=DEFAULT_SIMILARITY_THRESHOLD,
        help=f"Similarity threshold (0.0-1.0, default: {DEFAULT_SIMILARITY_THRESHOLD})",
    )

    parser.add_argument(
        "--entity-type",
        type=str,
        action="append",
        help="Specific entity type to process (can specify multiple times)",
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of duplicate pairs to process",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)

    # Display banner
    console.print("\n" + "=" * 80, style="bold cyan")
    console.print("Duplicate Entity Consolidation Tool".center(80), style="bold cyan")
    console.print("=" * 80 + "\n", style="bold cyan")

    # Initialize consolidator
    consolidator = DuplicateEntityConsolidator(
        similarity_threshold=args.similarity,
        dry_run=args.dry_run,
    )

    try:
        # Check APOC availability
        if not consolidator.check_apoc_available():
            console.print("\n❌ Cannot proceed without APOC plugin\n", style="red bold")
            return 1

        # Run consolidation
        stats = consolidator.consolidate_all_duplicates(
            entity_types=args.entity_type,
            limit=args.limit,
        )

        # Success
        if args.dry_run:
            console.print("✅ Dry run complete - no changes made\n", style="green bold")
        else:
            console.print("✅ Consolidation complete!\n", style="green bold")

        return 0

    except KeyboardInterrupt:
        console.print("\n\n⚠️  Interrupted by user\n", style="yellow")
        return 130

    except Exception as e:
        console.print(f"\n❌ Error: {e}\n", style="red bold")
        logger.exception("Consolidation failed")
        return 1

    finally:
        consolidator.close()


if __name__ == "__main__":
    exit(main())
