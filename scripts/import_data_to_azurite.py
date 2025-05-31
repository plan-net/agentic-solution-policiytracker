#!/usr/bin/env python3
"""
Import Local Data to Azurite Helper Script
==========================================

This script helps developers import data from the local data folder
into Azurite (Azure Storage Emulator) for development and testing.

Usage:
    python scripts/import_data_to_azurite.py [options]

Examples:
    # Import all data
    python scripts/import_data_to_azurite.py

    # Import only input documents
    python scripts/import_data_to_azurite.py --input-only

    # Import with custom job ID
    python scripts/import_data_to_azurite.py --job-id custom_job_123

    # Dry run (show what would be imported)
    python scripts/import_data_to_azurite.py --dry-run
"""

import argparse
import asyncio
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import structlog

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import settings
from src.integrations.azure_storage import get_azure_storage_client

logger = structlog.get_logger()


class DataImporter:
    """Import local development data to Azurite."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.base_path = Path(__file__).parent.parent
        self.data_path = self.base_path / "data"
        self.stats = {
            "input_documents": 0,
            "context_files": 0,
            "reports": 0,
            "cache_files": 0,
            "total_size": 0,
            "errors": [],
        }

    async def import_all(self, job_id: Optional[str] = None) -> dict:
        """Import all data from local data folder."""
        if not self.data_path.exists():
            logger.error("Data folder not found", path=str(self.data_path))
            return self.stats

        # Generate job ID if not provided
        if not job_id:
            job_id = f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info(
            "Starting data import",
            job_id=job_id,
            dry_run=self.dry_run,
            data_path=str(self.data_path),
        )

        # Import different types of data
        await self._import_input_documents(job_id)
        await self._import_context_files()
        await self._import_existing_reports(job_id)
        await self._create_sample_cache()

        # Print summary
        self._print_summary(job_id)
        return self.stats, job_id

    async def _import_input_documents(self, job_id: str):
        """Import documents from data/input folder."""
        input_path = self.data_path / "input"
        if not input_path.exists():
            logger.warning("Input folder not found", path=str(input_path))
            return

        logger.info("Importing input documents", path=str(input_path))

        # Supported document extensions
        supported_extensions = {".txt", ".md", ".pdf", ".docx", ".html", ".csv", ".json"}

        for file_path in input_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                relative_path = file_path.relative_to(input_path)
                blob_name = f"jobs/{job_id}/input/{relative_path}"

                await self._upload_file(
                    "input-documents",
                    blob_name,
                    file_path,
                    {
                        "original_path": str(relative_path),
                        "file_type": file_path.suffix.lower(),
                        "job_id": job_id,
                    },
                )
                self.stats["input_documents"] += 1

    async def _import_context_files(self):
        """Import context files from data/context folder."""
        context_path = self.data_path / "context"
        if not context_path.exists():
            logger.warning("Context folder not found", path=str(context_path))
            return

        logger.info("Importing context files", path=str(context_path))

        for file_path in context_path.glob("*.yaml"):
            context_id = file_path.stem
            blob_name = f"{context_id}/context.yaml"

            await self._upload_file(
                "contexts", blob_name, file_path, {"context_id": context_id, "file_type": "yaml"}
            )
            self.stats["context_files"] += 1

    async def _import_existing_reports(self, job_id: str):
        """Import any existing reports from data/output folder."""
        output_path = self.data_path / "output"
        if not output_path.exists():
            logger.info("No output folder found, skipping reports import")
            return

        logger.info("Importing existing reports", path=str(output_path))

        for file_path in output_path.rglob("*.md"):
            relative_path = file_path.relative_to(output_path)
            blob_name = f"jobs/{job_id}/{relative_path}"

            await self._upload_file(
                "reports",
                blob_name,
                file_path,
                {"imported_from": str(relative_path), "file_type": "report", "format": "markdown"},
            )
            self.stats["reports"] += 1

    async def _create_sample_cache(self):
        """Create sample cache entries for testing."""
        logger.info("Creating sample cache entries")

        sample_cache_data = [
            {
                "doc_hash": "sample_doc_123",
                "content": {
                    "processed_text": "Sample processed document content for testing",
                    "metadata": {
                        "word_count": 100,
                        "language": "en",
                        "processed_at": datetime.now().isoformat(),
                    },
                },
            },
            {
                "doc_hash": "sample_doc_456",
                "content": {
                    "processed_text": "Another sample document for cache testing",
                    "metadata": {
                        "word_count": 75,
                        "language": "en",
                        "processed_at": datetime.now().isoformat(),
                    },
                },
            },
        ]

        azure_client = get_azure_storage_client()
        for cache_entry in sample_cache_data:
            if not self.dry_run:
                await azure_client.upload_json(
                    "cache", f"processed/{cache_entry['doc_hash']}.json", cache_entry["content"]
                )
            self.stats["cache_files"] += 1

    async def _upload_file(
        self, container_type: str, blob_name: str, file_path: Path, metadata: dict
    ):
        """Upload a single file to Azure Storage."""
        try:
            file_size = file_path.stat().st_size
            self.stats["total_size"] += file_size

            if self.dry_run:
                logger.info(
                    "Would upload file",
                    container=container_type,
                    blob_name=blob_name,
                    file_path=str(file_path),
                    size=file_size,
                )
                return True

            # Read and upload file
            azure_client = get_azure_storage_client()
            with open(file_path, "rb") as f:
                success = await azure_client.upload_blob(
                    container_type, blob_name, f, metadata=metadata
                )

            if success:
                logger.info(
                    "Uploaded file", container=container_type, blob_name=blob_name, size=file_size
                )
            else:
                self.stats["errors"].append(f"Failed to upload {file_path}")

            return success

        except Exception as e:
            error_msg = f"Error uploading {file_path}: {str(e)}"
            logger.error(error_msg)
            self.stats["errors"].append(error_msg)
            return False

    def _print_summary(self, job_id: str):
        """Print import summary."""
        print("\n" + "=" * 60)
        print("📊 IMPORT SUMMARY")
        print("=" * 60)
        print(f"Job ID: {job_id}")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE IMPORT'}")
        print(f"Data Path: {self.data_path}")
        print()
        print("📈 Statistics:")
        print(f"  Input Documents: {self.stats['input_documents']}")
        print(f"  Context Files: {self.stats['context_files']}")
        print(f"  Reports: {self.stats['reports']}")
        print(f"  Cache Files: {self.stats['cache_files']}")
        print(f"  Total Size: {self.stats['total_size']:,} bytes")
        print()

        if self.stats["errors"]:
            print("❌ Errors:")
            for error in self.stats["errors"]:
                print(f"  - {error}")
        else:
            print("✅ No errors!")

        print()
        print("🌐 Access your data:")
        print("  Azurite Dashboard: Use Azure Storage Explorer")
        print(f"  Connection: {settings.AZURE_STORAGE_CONNECTION_STRING[:50]}...")
        print()

        if not self.dry_run:
            print("🚀 Next steps:")
            print("  1. Run 'just services-status' to check Azurite")
            print("  2. Use Azure Storage Explorer to browse containers")
            print("  3. Test your application with the imported data")
            print(f"  4. Submit a job with job_id='{job_id}' to test processing")

        print("=" * 60)


async def verify_azurite_connection():
    """Verify that Azurite is running and accessible."""
    try:
        # Try to list containers
        azure_client = get_azure_storage_client()
        await azure_client.ensure_container_exists("input-documents")
        logger.info("✅ Azurite connection verified")
        return True
    except Exception as e:
        logger.error("❌ Cannot connect to Azurite", error=str(e))
        print("\n🚨 Azurite Connection Failed!")
        print("Please ensure Azurite is running:")
        print("  1. Run: just services-up")
        print("  2. Check: just services-status")
        print("  3. Verify Azurite is healthy on port 10000")
        return False


async def create_test_data():
    """Create additional test data for development."""
    logger.info("Creating additional test data")

    # Create sample documents
    sample_docs = [
        {
            "name": "ai_regulation_sample.md",
            "content": """# AI Regulation Proposal

## Overview
This document outlines new regulations for artificial intelligence systems in healthcare.

## Key Points
- Mandatory bias testing for AI models
- Transparency requirements for algorithmic decisions
- Data protection standards for patient information

## Timeline
Implementation deadline: December 2024
""",
        },
        {
            "name": "privacy_policy_update.txt",
            "content": """Privacy Policy Update Notice

Effective Date: January 1, 2025

Changes to data collection practices:
1. Enhanced user consent mechanisms
2. Improved data anonymization procedures
3. Extended data retention policies

Impact: All user-facing applications must comply by Q2 2025.
""",
        },
    ]

    job_id = f"test_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    azure_client = get_azure_storage_client()

    for doc in sample_docs:
        blob_name = f"jobs/{job_id}/input/{doc['name']}"
        await azure_client.upload_blob(
            "input-documents",
            blob_name,
            doc["content"].encode("utf-8"),
            metadata={"source": "test_data_generator", "job_id": job_id},
        )

    # Create sample context
    sample_context = {
        "company_terms": ["TechCorp", "TechCorp Inc"],
        "core_industries": ["technology", "software"],
        "primary_markets": ["united-states", "european-union"],
        "strategic_themes": ["ai-regulation", "data-privacy", "compliance"],
    }

    await azure_client.upload_json("contexts", "test-client/context.yaml", sample_context)

    logger.info("Created test data", job_id=job_id)
    return job_id


def update_env_file_with_azure_paths(job_id: str, env_file_path: str = ".env"):
    """Update .env file with Azure paths after successful import."""
    try:
        env_path = Path(env_file_path)
        if not env_path.exists():
            logger.warning("No .env file found", path=str(env_path))
            return False

        # Read current .env content
        content = env_path.read_text(encoding="utf-8")

        # Update Azure configuration values
        azure_updates = {
            "AZURE_JOB_ID": job_id,
            "AZURE_INPUT_PATH": f"jobs/{job_id}/input",
            "AZURE_CONTEXT_PATH": "test-client/context.yaml",
            "AZURE_OUTPUT_PATH": f"jobs/{job_id}/output",
        }

        # Apply updates
        for key, value in azure_updates.items():
            # Pattern to match the existing line
            pattern = rf"^{key}=.*$"
            replacement = f"{key}={value}"

            if re.search(pattern, content, re.MULTILINE):
                # Update existing line
                content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            else:
                # Add new line if it doesn't exist
                azure_section = "# Azure Storage paths (used when USE_AZURE_STORAGE=true)"
                if azure_section in content:
                    content = content.replace(azure_section, f"{azure_section}\n{replacement}")

        # Write updated content back to file
        env_path.write_text(content, encoding="utf-8")

        logger.info("Updated .env file with Azure paths", job_id=job_id, env_file=str(env_path))

        print("\n✅ Updated .env file with Azure paths:")
        print(f"   AZURE_JOB_ID={job_id}")
        print(f"   AZURE_INPUT_PATH=jobs/{job_id}/input")
        print("   AZURE_CONTEXT_PATH=test-client/context.yaml")
        print(f"   AZURE_OUTPUT_PATH=jobs/{job_id}/output")

        return True

    except Exception as e:
        logger.error("Failed to update .env file", error=str(e))
        print(f"\n❌ Failed to update .env file: {e}")
        return False


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Import local data to Azurite for development",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--job-id", help="Custom job ID for imported documents (default: auto-generated)"
    )

    parser.add_argument(
        "--input-only",
        action="store_true",
        help="Import only input documents, skip other data types",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be imported without actually uploading",
    )

    parser.add_argument(
        "--create-test-data",
        action="store_true",
        help="Create additional test data for development",
    )

    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify Azurite connection, do not import data",
    )

    args = parser.parse_args()

    # Setup logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    print("🚀 Azurite Data Import Tool")
    print("=" * 50)

    # Verify Azurite connection
    if not await verify_azurite_connection():
        return 1

    if args.verify_only:
        print("✅ Azurite connection verified successfully!")
        return 0

    # Create test data if requested
    if args.create_test_data:
        test_job_id = await create_test_data()
        print(f"✅ Created test data with job_id: {test_job_id}")
        if not args.job_id and not args.input_only:
            return 0

    # Import data
    importer = DataImporter(dry_run=args.dry_run)

    if args.input_only:
        job_id = args.job_id or f"input_only_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        await importer._import_input_documents(job_id)
        importer._print_summary(job_id)

        # Update .env file if not dry run
        if not args.dry_run:
            update_env_file_with_azure_paths(job_id)
    else:
        stats, job_id = await importer.import_all(args.job_id)

        # Update .env file if not dry run
        if not args.dry_run:
            update_env_file_with_azure_paths(job_id)

    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n❌ Import cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)
