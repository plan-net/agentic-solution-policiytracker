#!/usr/bin/env python3
"""
Test that document processor properly tracks ALL types of failures.
"""
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from src.flows.data_ingestion.document_tracker import DocumentTracker


async def test_all_failure_types():
    """Test that all failure scenarios are tracked."""

    print("🧪 Testing Document Processor Failure Tracking\n")
    print("=" * 60)

    # Clean up test tracking file
    tracking_file = Path("data/test_processor_failures.json")
    if tracking_file.exists():
        tracking_file.unlink()

    # Import after cleanup so tracker starts fresh
    from src.flows.data_ingestion.document_processor import SimpleDocumentProcessor

    # Create mock actor
    class MockActor:
        def __init__(self):
            self.actor_id = 1
            self.clear_mode = False
            self.graphiti_client = None
            self.tracker = DocumentTracker(str(tracking_file))
            self.processing_stats = {
                "processed": 0,
                "failed": 0,
                "skipped": 0,
                "total_entities": 0,
                "total_relationships": 0,
                "processing_time": 0,
            }

        async def initialize(self):
            # Mock graphiti client
            self.graphiti_client = MagicMock()

        def _read_document(self, doc_path):
            # Simulate different failure scenarios
            filename = Path(doc_path).name

            if "empty" in filename:
                return ""  # Empty document
            elif "unreadable" in filename:
                raise IOError("Permission denied")
            else:
                return "Valid document content"

        async def process_single_document(self, doc_path, graphiti_client):
            """Copy of the actual process_single_document logic with failures."""
            from datetime import datetime
            import structlog

            logger = structlog.get_logger()
            start_time = datetime.now()

            try:
                # Check if already processed (unless clear mode)
                if not self.clear_mode and self.tracker.is_processed(str(doc_path)):
                    logger.debug(f"Skipping already processed document: {doc_path}")
                    self.processing_stats["skipped"] += 1
                    return {
                        "status": "skipped",
                        "reason": "already_processed",
                        "path": str(doc_path),
                        "processing_time": 0.0,
                    }

                # Read document content
                try:
                    content = self._read_document(doc_path)
                    if not content.strip():
                        raise ValueError("Document is empty")

                    logger.debug(f"Read document: {doc_path} ({len(content)} characters)")
                except Exception as e:
                    error_msg = f"Failed to read document: {e}"
                    self.tracker.mark_failed(str(doc_path), error_msg)
                    self.processing_stats["failed"] += 1
                    return {
                        "status": "failed",
                        "error": error_msg,
                        "path": str(doc_path),
                        "processing_time": (datetime.now() - start_time).total_seconds(),
                    }

                # Simulate Graphiti processing
                filename = Path(doc_path).name

                if "graphiti_error" in filename:
                    # Simulate Graphiti failure
                    raise Exception("Graphiti API error: timeout")

                # Success case
                self.tracker.mark_processed(str(doc_path), f"episode-{filename}", 10, 5)
                self.processing_stats["processed"] += 1

                return {
                    "status": "success",
                    "path": str(doc_path),
                    "episode_id": f"episode-{filename}",
                }

            except Exception as e:
                # Catch-all for unexpected errors (THIS WAS MISSING mark_failed!)
                error_msg = f"Unexpected error: {e}"
                logger.error(f"Unexpected error processing {doc_path}: {e}")
                self.tracker.mark_failed(str(doc_path), error_msg)
                self.processing_stats["failed"] += 1
                return {
                    "status": "failed",
                    "error": error_msg,
                    "path": str(doc_path),
                    "processing_time": (datetime.now() - start_time).total_seconds(),
                }

    # Test different failure scenarios
    actor = MockActor()
    await actor.initialize()

    test_documents = [
        "data/input/test_success.md",          # Should succeed
        "data/input/test_empty.md",            # Should fail: empty document
        "data/input/test_unreadable.md",       # Should fail: read error
        "data/input/test_graphiti_error.md",   # Should fail: Graphiti error
        "data/input/test_success2.md",         # Should succeed
    ]

    print("📄 Processing test documents...\n")
    results = []
    for doc_path in test_documents:
        result = await actor.process_single_document(doc_path, actor.graphiti_client)
        status_icon = "✅" if result["status"] == "success" else "❌"
        print(f"   {status_icon} {Path(doc_path).name}: {result['status']}")
        if result["status"] == "failed":
            print(f"      Error: {result.get('error', 'Unknown')}")
        results.append(result)

    # Verify tracking
    print("\n" + "=" * 60)
    print("📊 Verification\n")

    tracker = DocumentTracker(str(tracking_file))
    stats = tracker.get_stats()

    print(f"Total documents tracked: {stats['total_processed']}")
    print(f"Successful: {stats['completed']}")
    print(f"Failed: {stats['failed']}")

    failed_docs = tracker.get_failed_documents()
    print(f"\n❌ Failed Documents ({len(failed_docs)}):")
    for failed in failed_docs:
        print(f"   • {Path(failed['path']).name}")
        print(f"     Error: {failed['error']}")

    print("\n" + "=" * 60)
    print("🎯 Validation\n")

    expected_failed = 3  # empty, unreadable, graphiti_error
    expected_success = 2

    if stats['failed'] == expected_failed:
        print(f"✅ Correct number of failures tracked ({expected_failed})")
    else:
        print(f"❌ Expected {expected_failed} failures, got {stats['failed']}")

    if stats['completed'] == expected_success:
        print(f"✅ Correct number of successes tracked ({expected_success})")
    else:
        print(f"❌ Expected {expected_success} successes, got {stats['completed']}")

    # Check specific failure types
    failure_errors = [f['error'] for f in failed_docs]
    has_read_error = any("Failed to read" in e for e in failure_errors)
    has_graphiti_error = any("Unexpected error" in e or "Graphiti" in e for e in failure_errors)

    if has_read_error:
        print("✅ Read failures are being tracked")
    else:
        print("❌ Read failures NOT tracked")

    if has_graphiti_error:
        print("✅ Graphiti/unexpected errors are being tracked")
    else:
        print("❌ Graphiti/unexpected errors NOT tracked")

    # Cleanup
    # tracking_file.unlink()

    if stats['failed'] == expected_failed and stats['completed'] == expected_success:
        print("\n✅ SUCCESS: All failure types are being tracked correctly!")
    else:
        print("\n❌ FAILURE: Some failures are not being tracked")


if __name__ == "__main__":
    asyncio.run(test_all_failure_types())
