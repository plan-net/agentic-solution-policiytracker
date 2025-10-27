#!/usr/bin/env python3
"""
Test concurrent document tracking to simulate Ray actors.
"""
import asyncio
import concurrent.futures
import time
from pathlib import Path

from src.flows.data_ingestion.document_tracker import DocumentTracker


def mark_document(doc_id: int, tracker_file: str = "data/processed_documents.json"):
    """Simulate a Ray actor marking a document as processed."""
    # Each "actor" creates its own tracker instance (like Ray does)
    tracker = DocumentTracker(tracker_file)

    doc_path = f"data/input/policy/doc_{doc_id}.md"
    episode_id = f"episode-{doc_id}"
    entity_count = doc_id * 10
    relationship_count = doc_id * 5

    print(f"Worker {doc_id}: Marking document as processed...")
    tracker.mark_processed(doc_path, episode_id, entity_count, relationship_count)
    print(f"Worker {doc_id}: ✅ Done")

    return doc_id


def mark_failed_document(doc_id: int, tracker_file: str = "data/processed_documents.json"):
    """Simulate a Ray actor marking a document as failed."""
    tracker = DocumentTracker(tracker_file)

    doc_path = f"data/input/policy/failed_doc_{doc_id}.md"
    error = f"Test error for document {doc_id}"

    print(f"Worker {doc_id}: Marking document as failed...")
    tracker.mark_failed(doc_path, error)
    print(f"Worker {doc_id}: ❌ Done")

    return doc_id


def test_concurrent_writes():
    """Test that multiple workers can write concurrently without losing data."""

    print("🧪 Testing Concurrent Document Tracking\n")
    print("=" * 60)

    # Clean up any existing file
    tracking_file = Path("data/processed_documents.json")
    if tracking_file.exists():
        tracking_file.unlink()
        print("🗑️  Cleaned up existing tracking file\n")

    # Simulate 10 Ray actors processing documents concurrently
    num_workers = 10
    num_failed = 3

    print(f"🚀 Starting {num_workers} concurrent workers (simulating Ray actors)...\n")

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        # Submit successful processing tasks
        success_futures = [
            executor.submit(mark_document, i)
            for i in range(num_workers)
        ]

        # Submit failed processing tasks
        failed_futures = [
            executor.submit(mark_failed_document, i)
            for i in range(num_failed)
        ]

        # Wait for all to complete
        all_futures = success_futures + failed_futures
        concurrent.futures.wait(all_futures)

    print("\n" + "=" * 60)
    print("📊 Verification\n")

    # Verify results
    tracker = DocumentTracker("data/processed_documents.json")

    print(f"Total documents tracked: {len(tracker.processed_docs)}")
    print(f"Expected: {num_workers + num_failed}")

    stats = tracker.get_stats()
    print(f"\n📈 Stats:")
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Check completeness
    success_docs = [f"data/input/policy/doc_{i}.md" for i in range(num_workers)]
    failed_docs = [f"data/input/policy/failed_doc_{i}.md" for i in range(num_failed)]

    missing_success = [doc for doc in success_docs if doc not in tracker.processed_docs]
    missing_failed = [doc for doc in failed_docs if doc not in tracker.processed_docs]

    print(f"\n🔍 Data Integrity Check:")
    if not missing_success and not missing_failed:
        print("   ✅ All documents tracked!")
        print("   ✅ No data lost during concurrent writes!")
    else:
        print(f"   ❌ Missing successful documents: {len(missing_success)}")
        print(f"   ❌ Missing failed documents: {len(missing_failed)}")
        if missing_success:
            print(f"      Missing: {missing_success[:3]}...")
        if missing_failed:
            print(f"      Missing: {missing_failed}")

    # Verify failed documents tracking
    failed_list = tracker.get_failed_documents()
    print(f"\n❌ Failed Documents: {len(failed_list)}")
    for failed in failed_list:
        print(f"   • {Path(failed['path']).name}: {failed['error']}")

    # Show sample entry
    if tracker.processed_docs:
        print(f"\n📄 Sample Entry:")
        first_key = list(tracker.processed_docs.keys())[0]
        first_entry = tracker.processed_docs[first_key]
        print(f"   Path: {first_key}")
        for key, value in first_entry.items():
            print(f"   {key}: {value}")


if __name__ == "__main__":
    test_concurrent_writes()
