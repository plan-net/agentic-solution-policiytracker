#!/usr/bin/env python3
"""
Fix embedding dimension mismatch in Neo4j Entity nodes AND relationships.

Re-embeds entities (name_embedding) and relationships (fact_embedding) with 1024-dim
embeddings to 1536-dim using text-embedding-3-small. This fixes the Neo4j vector
search error: "The supplied vectors do not have the same number of dimensions."

Features:
- Fixes BOTH entity name_embedding AND relationship fact_embedding
- Batch processing with configurable batch size
- Dry-run mode (default) for safe preview
- Checkpoint/resume support for interrupted migrations
- Progress tracking with Rich console
- APISIX routing for cost tracking

Usage:
    # Dry run (default) - shows what would be changed
    python scripts/fix_embedding_dimensions.py

    # Execute migration (entities only - default)
    python scripts/fix_embedding_dimensions.py --execute

    # Fix relationships only
    python scripts/fix_embedding_dimensions.py --execute --relationships

    # Fix both entities and relationships
    python scripts/fix_embedding_dimensions.py --execute --all

    # Resume from checkpoint
    python scripts/fix_embedding_dimensions.py --execute --resume

    # Verify after migration
    python scripts/fix_embedding_dimensions.py --verify

    # Custom batch size
    python scripts/fix_embedding_dimensions.py --execute --batch-size 50
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from openai import AsyncOpenAI
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

# Load environment variables
load_dotenv()

logger = structlog.get_logger()
console = Console()

# Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "politicalmonitoring.v3")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
APISIX_GATEWAY_URL = os.getenv("APISIX_GATEWAY_URL", "http://localhost:9080/v1")

# Embedding configuration (must match data ingestion)
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
SOURCE_DIM = 1024  # Dimension to fix

# Batch configuration
DEFAULT_BATCH_SIZE = 100  # Entities per batch
API_BATCH_SIZE = 50  # Texts per OpenAI API call
RATE_LIMIT_DELAY = 0.1  # Seconds between API calls

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 5  # Seconds between retries

# Checkpoint configuration
CHECKPOINT_DIR = Path("data/migration")
CHECKPOINT_FILE = CHECKPOINT_DIR / "embedding_fix_checkpoint.json"


class EmbeddingFixer:
    """Fix embedding dimensions in Neo4j Entity nodes and relationships."""

    def __init__(
        self,
        batch_size: int = DEFAULT_BATCH_SIZE,
        dry_run: bool = True,
    ):
        """
        Initialize the embedding fixer.

        Args:
            batch_size: Number of entities/relationships to process per batch
            dry_run: If True, only preview changes without modifying data
        """
        self.batch_size = batch_size
        self.dry_run = dry_run

        # Initialize Neo4j driver
        self.driver = AsyncGraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
        )

        # Initialize OpenAI client with APISIX routing for cost tracking
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.openai_client = AsyncOpenAI(
            api_key=OPENAI_API_KEY,
            base_url=APISIX_GATEWAY_URL,
        )

        # Statistics
        self.stats = {
            "total_mismatched": 0,
            "processed": 0,
            "updated": 0,
            "failed": 0,
            "failed_uuids": [],
        }

    async def close(self):
        """Close database connections."""
        await self.driver.close()

    async def reconnect(self):
        """Reconnect to Neo4j after connection failure."""
        try:
            await self.driver.close()
        except Exception:
            pass
        console.print("[yellow]Reconnecting to Neo4j...[/yellow]")
        await asyncio.sleep(RETRY_DELAY)
        self.driver = AsyncGraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
        )
        console.print("[green]Reconnected to Neo4j[/green]")

    async def execute_with_retry(self, coro_func, *args, **kwargs):
        """Execute an async function with retry logic for connection failures."""
        for attempt in range(MAX_RETRIES):
            try:
                return await coro_func(*args, **kwargs)
            except (ServiceUnavailable, SessionExpired, OSError) as e:
                if attempt < MAX_RETRIES - 1:
                    console.print(f"[yellow]Connection error (attempt {attempt + 1}/{MAX_RETRIES}): {e}[/yellow]")
                    await self.reconnect()
                else:
                    raise

    async def _count_by_dimension_internal(self) -> dict[int, int]:
        """Internal: Count entities by embedding dimension."""
        query = """
        MATCH (e:Entity)
        WHERE e.name_embedding IS NOT NULL
        RETURN size(e.name_embedding) AS dim, count(*) AS count
        ORDER BY dim
        """
        async with self.driver.session(database=NEO4J_DATABASE) as session:
            result = await session.run(query)
            records = await result.data()
            return {r["dim"]: r["count"] for r in records}

    async def count_by_dimension(self) -> dict[int, int]:
        """Count entities by embedding dimension (with retry)."""
        return await self.execute_with_retry(self._count_by_dimension_internal)

    async def _count_relationships_by_dimension_internal(self) -> dict[int, int]:
        """Internal: Count relationships by fact_embedding dimension."""
        query = """
        MATCH ()-[r]->()
        WHERE r.fact_embedding IS NOT NULL
        RETURN size(r.fact_embedding) AS dim, count(*) AS count
        ORDER BY dim
        """
        async with self.driver.session(database=NEO4J_DATABASE) as session:
            result = await session.run(query)
            records = await result.data()
            return {r["dim"]: r["count"] for r in records}

    async def count_relationships_by_dimension(self) -> dict[int, int]:
        """Count relationships by fact_embedding dimension (with retry)."""
        return await self.execute_with_retry(self._count_relationships_by_dimension_internal)

    async def _get_mismatched_relationships_batch_internal(self, limit: int) -> list[dict[str, Any]]:
        """Internal: Fetch a batch of relationships with wrong embedding dimensions."""
        query = """
        MATCH (s)-[r]->(t)
        WHERE r.fact_embedding IS NOT NULL
          AND size(r.fact_embedding) = $source_dim
        RETURN id(r) AS rel_id, r.uuid AS uuid, r.fact AS fact, type(r) AS rel_type
        ORDER BY id(r)
        LIMIT $limit
        """
        async with self.driver.session(database=NEO4J_DATABASE) as session:
            result = await session.run(query, source_dim=SOURCE_DIM, limit=limit)
            return await result.data()

    async def get_mismatched_relationships_batch(self, limit: int) -> list[dict[str, Any]]:
        """Fetch a batch of relationships with wrong embedding dimensions (with retry)."""
        return await self.execute_with_retry(self._get_mismatched_relationships_batch_internal, limit)

    async def _update_relationship_embeddings_batch_internal(self, updates: list[dict[str, Any]]) -> int:
        """Internal: Update multiple relationships with new embeddings."""
        query = """
        UNWIND $batch AS item
        MATCH ()-[r]->()
        WHERE id(r) = item.rel_id
        SET r.fact_embedding = item.embedding
        RETURN count(*) AS updated
        """
        async with self.driver.session(database=NEO4J_DATABASE) as session:
            result = await session.run(query, batch=updates)
            record = await result.single()
            return record["updated"] if record else 0

    async def update_relationship_embeddings_batch(self, updates: list[dict[str, Any]]) -> int:
        """Update multiple relationships with new embeddings (with retry)."""
        return await self.execute_with_retry(self._update_relationship_embeddings_batch_internal, updates)

    async def get_mismatched_batch(self, limit: int) -> list[dict[str, Any]]:
        """Fetch a batch of entities with wrong embedding dimensions.

        Note: Always fetches from the beginning since processed entities
        no longer match the dimension filter condition.
        """
        query = """
        MATCH (e:Entity)
        WHERE e.name_embedding IS NOT NULL
          AND size(e.name_embedding) = $source_dim
        RETURN e.uuid AS uuid, e.name AS name, labels(e) AS labels
        ORDER BY e.uuid
        LIMIT $limit
        """
        async with self.driver.session(database=NEO4J_DATABASE) as session:
            result = await session.run(query, source_dim=SOURCE_DIM, limit=limit)
            return await result.data()

    async def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts in a single API call."""
        try:
            response = await self.openai_client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=texts,
            )

            embeddings = [item.embedding for item in response.data]

            # Validate dimensions
            for i, emb in enumerate(embeddings):
                if len(emb) != EMBEDDING_DIM:
                    raise ValueError(f"Entity {i}: Expected {EMBEDDING_DIM} dims, got {len(emb)}")

            return embeddings

        except Exception as e:
            logger.error("Failed to generate embeddings batch", error=str(e))
            raise

    async def update_embeddings_batch(self, updates: list[dict[str, Any]]) -> int:
        """Update multiple entities with new embeddings in a single transaction."""
        query = """
        UNWIND $batch AS item
        MATCH (e:Entity {uuid: item.uuid})
        SET e.name_embedding = item.embedding
        RETURN count(*) AS updated
        """
        async with self.driver.session(database=NEO4J_DATABASE) as session:
            result = await session.run(query, batch=updates)
            record = await result.single()
            return record["updated"] if record else 0

    def load_checkpoint(self) -> dict[str, Any] | None:
        """Load checkpoint from file if exists."""
        if CHECKPOINT_FILE.exists():
            with open(CHECKPOINT_FILE) as f:
                return json.load(f)
        return None

    def save_checkpoint(self, processed: int, failed_uuids: list[str]):
        """Save checkpoint to file."""
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

        checkpoint = {
            "timestamp": datetime.now().isoformat(),
            "processed": processed,
            "failed_uuids": failed_uuids,
            "source_dim": SOURCE_DIM,
            "target_dim": EMBEDDING_DIM,
        }

        with open(CHECKPOINT_FILE, "w") as f:
            json.dump(checkpoint, f, indent=2)

    def clear_checkpoint(self):
        """Remove checkpoint file after successful completion."""
        if CHECKPOINT_FILE.exists():
            CHECKPOINT_FILE.unlink()

    async def run(self, resume: bool = False) -> dict[str, Any]:
        """
        Execute the embedding fix migration.

        Args:
            resume: If True, resume from checkpoint

        Returns:
            Dictionary with migration statistics
        """
        console.print("\n[bold blue]Embedding Dimension Fix Migration[/bold blue]")
        console.print(f"Source dimension: {SOURCE_DIM} → Target dimension: {EMBEDDING_DIM}")
        console.print(f"Mode: {'[yellow]DRY RUN[/yellow]' if self.dry_run else '[green]EXECUTE[/green]'}")
        console.print()

        # Get dimension counts
        dim_counts = await self.count_by_dimension()

        # Display current state
        table = Table(title="Current Embedding Dimensions")
        table.add_column("Dimension", style="cyan")
        table.add_column("Count", style="magenta")
        table.add_column("Status", style="green")

        for dim, count in sorted(dim_counts.items()):
            status = "[green]OK[/green]" if dim == EMBEDDING_DIM else "[red]NEEDS FIX[/red]"
            table.add_row(str(dim), str(count), status)

        console.print(table)
        console.print()

        # Get count of entities to fix
        total_mismatched = dim_counts.get(SOURCE_DIM, 0)
        self.stats["total_mismatched"] = total_mismatched

        if total_mismatched == 0:
            console.print("[green]No entities need fixing![/green]")
            return self.stats

        console.print(f"[yellow]Entities to fix: {total_mismatched}[/yellow]")

        if self.dry_run:
            console.print("\n[yellow]DRY RUN - No changes will be made[/yellow]")

            # Show sample of entities to be fixed
            sample = await self.get_mismatched_batch(5)
            if sample:
                console.print("\n[bold]Sample entities to be fixed:[/bold]")
                for entity in sample:
                    labels = ", ".join(entity["labels"])
                    console.print(f"  - {entity['name'][:50]}... ({labels})")

            console.print(f"\n[bold]To execute migration, run:[/bold]")
            console.print("  python scripts/fix_embedding_dimensions.py --execute")
            return self.stats

        # Resume from checkpoint if requested
        start_offset = 0
        if resume:
            checkpoint = self.load_checkpoint()
            if checkpoint:
                start_offset = checkpoint["processed"]
                self.stats["failed_uuids"] = checkpoint.get("failed_uuids", [])
                console.print(f"[cyan]Resuming from checkpoint: {start_offset} already processed[/cyan]")

        # Process in batches
        processed = start_offset
        updated = 0
        failed = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("[cyan]{task.completed}/{task.total}[/cyan]"),
            console=console,
        ) as progress:
            task = progress.add_task(
                "Processing entities...",
                total=total_mismatched,
                completed=start_offset,
            )

            while True:
                # Fetch batch (always from beginning since processed entities no longer match)
                batch = await self.get_mismatched_batch(self.batch_size)
                if not batch:
                    break  # No more entities to process

                # Process batch in smaller API chunks
                batch_updates = []
                batch_failed = []

                for i in range(0, len(batch), API_BATCH_SIZE):
                    chunk = batch[i : i + API_BATCH_SIZE]
                    texts = [e["name"] or "" for e in chunk]

                    try:
                        # Generate embeddings
                        embeddings = await self.generate_embeddings_batch(texts)

                        # Prepare updates
                        for j, entity in enumerate(chunk):
                            batch_updates.append(
                                {
                                    "uuid": entity["uuid"],
                                    "embedding": embeddings[j],
                                }
                            )

                        # Rate limiting
                        await asyncio.sleep(RATE_LIMIT_DELAY)

                    except Exception as e:
                        logger.error(
                            "Failed to process chunk",
                            offset=processed + i,
                            error=str(e),
                        )
                        for entity in chunk:
                            batch_failed.append(entity["uuid"])

                # Update database
                if batch_updates:
                    try:
                        batch_updated = await self.update_embeddings_batch(batch_updates)
                        updated += batch_updated
                    except Exception as e:
                        logger.error("Failed to update batch", error=str(e))
                        failed += len(batch_updates)
                        for u in batch_updates:
                            batch_failed.append(u["uuid"])

                # Update stats
                processed += len(batch)
                failed += len(batch_failed)
                self.stats["failed_uuids"].extend(batch_failed)

                # Save checkpoint
                self.save_checkpoint(processed, self.stats["failed_uuids"])

                # Update progress
                progress.update(task, completed=processed)

        # Final stats
        self.stats["processed"] = processed
        self.stats["updated"] = updated
        self.stats["failed"] = failed

        # Clear checkpoint on success
        if failed == 0:
            self.clear_checkpoint()

        # Display results
        console.print()
        results_table = Table(title="Migration Results")
        results_table.add_column("Metric", style="cyan")
        results_table.add_column("Value", style="magenta")

        results_table.add_row("Total to fix", str(total_mismatched))
        results_table.add_row("Processed", str(processed))
        results_table.add_row("Updated", str(updated))
        results_table.add_row("Failed", str(failed))

        console.print(results_table)

        if failed > 0:
            console.print(f"\n[red]Failed UUIDs saved to checkpoint file[/red]")
        else:
            console.print("\n[green]Migration completed successfully![/green]")

        return self.stats

    async def run_relationships(self, resume: bool = False) -> dict[str, Any]:
        """
        Execute the relationship embedding fix migration.

        Args:
            resume: If True, resume from checkpoint

        Returns:
            Dictionary with migration statistics
        """
        console.print("\n[bold blue]Relationship Embedding Dimension Fix Migration[/bold blue]")
        console.print(f"Source dimension: {SOURCE_DIM} → Target dimension: {EMBEDDING_DIM}")
        console.print(f"Mode: {'[yellow]DRY RUN[/yellow]' if self.dry_run else '[green]EXECUTE[/green]'}")
        console.print()

        # Get dimension counts for relationships
        dim_counts = await self.count_relationships_by_dimension()

        # Display current state
        table = Table(title="Current Relationship Embedding Dimensions (fact_embedding)")
        table.add_column("Dimension", style="cyan")
        table.add_column("Count", style="magenta")
        table.add_column("Status", style="green")

        for dim, count in sorted(dim_counts.items()):
            status = "[green]OK[/green]" if dim == EMBEDDING_DIM else "[red]NEEDS FIX[/red]"
            table.add_row(str(dim), str(count), status)

        console.print(table)
        console.print()

        # Get count of relationships to fix
        total_mismatched = dim_counts.get(SOURCE_DIM, 0)
        self.stats["total_mismatched"] = total_mismatched

        if total_mismatched == 0:
            console.print("[green]No relationships need fixing![/green]")
            return self.stats

        console.print(f"[yellow]Relationships to fix: {total_mismatched}[/yellow]")

        if self.dry_run:
            console.print("\n[yellow]DRY RUN - No changes will be made[/yellow]")

            # Show sample of relationships to be fixed
            sample = await self.get_mismatched_relationships_batch(5)
            if sample:
                console.print("\n[bold]Sample relationships to be fixed:[/bold]")
                for rel in sample:
                    fact = (rel.get("fact") or "")[:50]
                    console.print(f"  - [{rel['rel_type']}] {fact}...")

            console.print(f"\n[bold]To execute migration, run:[/bold]")
            console.print("  python scripts/fix_embedding_dimensions.py --execute --relationships")
            return self.stats

        # Process in batches
        processed = 0
        updated = 0
        failed = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("[cyan]{task.completed}/{task.total}[/cyan]"),
            console=console,
        ) as progress:
            task = progress.add_task(
                "Processing relationships...",
                total=total_mismatched,
                completed=0,
            )

            while True:
                # Fetch batch
                batch = await self.get_mismatched_relationships_batch(self.batch_size)
                if not batch:
                    break

                # Process batch in smaller API chunks
                batch_updates = []
                batch_failed = []

                for i in range(0, len(batch), API_BATCH_SIZE):
                    chunk = batch[i : i + API_BATCH_SIZE]
                    texts = [r.get("fact") or "" for r in chunk]

                    # Skip empty texts
                    if not any(texts):
                        for rel in chunk:
                            batch_failed.append(rel["rel_id"])
                        continue

                    try:
                        # Generate embeddings
                        embeddings = await self.generate_embeddings_batch(texts)

                        # Prepare updates
                        for j, rel in enumerate(chunk):
                            batch_updates.append(
                                {
                                    "rel_id": rel["rel_id"],
                                    "embedding": embeddings[j],
                                }
                            )

                        # Rate limiting
                        await asyncio.sleep(RATE_LIMIT_DELAY)

                    except Exception as e:
                        logger.error(
                            "Failed to process relationship chunk",
                            offset=processed + i,
                            error=str(e),
                        )
                        for rel in chunk:
                            batch_failed.append(rel["rel_id"])

                # Update database
                if batch_updates:
                    try:
                        batch_updated = await self.update_relationship_embeddings_batch(batch_updates)
                        updated += batch_updated
                    except Exception as e:
                        logger.error("Failed to update relationship batch", error=str(e))
                        failed += len(batch_updates)

                # Update stats
                processed += len(batch)
                failed += len(batch_failed)

                # Update progress
                progress.update(task, completed=processed)

        # Final stats
        self.stats["processed"] = processed
        self.stats["updated"] = updated
        self.stats["failed"] = failed

        # Display results
        console.print()
        results_table = Table(title="Relationship Migration Results")
        results_table.add_column("Metric", style="cyan")
        results_table.add_column("Value", style="magenta")

        results_table.add_row("Total to fix", str(total_mismatched))
        results_table.add_row("Processed", str(processed))
        results_table.add_row("Updated", str(updated))
        results_table.add_row("Failed", str(failed))

        console.print(results_table)

        if failed > 0:
            console.print(f"\n[red]Some relationships failed to update[/red]")
        else:
            console.print("\n[green]Relationship migration completed successfully![/green]")

        return self.stats

    async def verify(self) -> bool:
        """Verify all embeddings have the correct dimension."""
        console.print("\n[bold blue]Verifying Embedding Dimensions[/bold blue]")

        # Check entity embeddings
        entity_dim_counts = await self.count_by_dimension()

        table = Table(title="Entity Embedding Dimensions (name_embedding)")
        table.add_column("Dimension", style="cyan")
        table.add_column("Count", style="magenta")
        table.add_column("Status", style="green")

        entities_correct = True
        for dim, count in sorted(entity_dim_counts.items()):
            if dim != EMBEDDING_DIM:
                entities_correct = False
                status = "[red]INCORRECT[/red]"
            else:
                status = "[green]CORRECT[/green]"
            table.add_row(str(dim), str(count), status)

        console.print(table)

        # Check relationship embeddings
        rel_dim_counts = await self.count_relationships_by_dimension()

        if rel_dim_counts:
            table2 = Table(title="Relationship Embedding Dimensions (fact_embedding)")
            table2.add_column("Dimension", style="cyan")
            table2.add_column("Count", style="magenta")
            table2.add_column("Status", style="green")

            rels_correct = True
            for dim, count in sorted(rel_dim_counts.items()):
                if dim != EMBEDDING_DIM:
                    rels_correct = False
                    status = "[red]INCORRECT[/red]"
                else:
                    status = "[green]CORRECT[/green]"
                table2.add_row(str(dim), str(count), status)

            console.print(table2)
        else:
            rels_correct = True
            console.print("\n[dim]No relationship embeddings found.[/dim]")

        all_correct = entities_correct and rels_correct

        if all_correct:
            console.print("\n[green]All embeddings have correct dimensions![/green]")
        else:
            console.print(
                f"\n[red]Some embeddings have incorrect dimensions. Run migration to fix.[/red]"
            )
            if not entities_correct:
                console.print("  - Run: python scripts/fix_embedding_dimensions.py --execute")
            if not rels_correct:
                console.print("  - Run: python scripts/fix_embedding_dimensions.py --execute --relationships")

        return all_correct


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fix embedding dimension mismatch in Neo4j Entity nodes and relationships",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Dry run (preview only)
    python scripts/fix_embedding_dimensions.py

    # Execute entity migration
    python scripts/fix_embedding_dimensions.py --execute

    # Execute relationship migration
    python scripts/fix_embedding_dimensions.py --execute --relationships

    # Execute both entities and relationships
    python scripts/fix_embedding_dimensions.py --execute --all

    # Resume interrupted migration
    python scripts/fix_embedding_dimensions.py --execute --resume

    # Verify after migration
    python scripts/fix_embedding_dimensions.py --verify
        """,
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform updates (default: dry-run)",
    )
    parser.add_argument(
        "--relationships",
        action="store_true",
        help="Fix relationship embeddings (fact_embedding) instead of entity embeddings",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Fix both entity and relationship embeddings",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint if available",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify all embeddings have correct dimensions",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Entities/relationships per batch (default: {DEFAULT_BATCH_SIZE})",
    )

    args = parser.parse_args()

    # Check for OpenAI API key
    if not OPENAI_API_KEY:
        console.print("[red]Error: OPENAI_API_KEY environment variable not set[/red]")
        sys.exit(1)

    try:
        fixer = EmbeddingFixer(
            batch_size=args.batch_size,
            dry_run=not args.execute,
        )

        if args.verify:
            success = await fixer.verify()
            await fixer.close()
            sys.exit(0 if success else 1)
        elif args.all:
            # Fix both entities and relationships
            console.print("[bold]Running migration for BOTH entities and relationships[/bold]\n")
            entity_stats = await fixer.run(resume=args.resume)
            rel_stats = await fixer.run_relationships(resume=False)
            await fixer.close()

            total_failed = entity_stats.get("failed", 0) + rel_stats.get("failed", 0)
            if total_failed > 0:
                sys.exit(1)
        elif args.relationships:
            # Fix relationships only
            stats = await fixer.run_relationships(resume=args.resume)
            await fixer.close()

            if stats["failed"] > 0:
                sys.exit(1)
        else:
            # Fix entities only (default)
            stats = await fixer.run(resume=args.resume)
            await fixer.close()

            if stats["failed"] > 0:
                sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Migration failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
