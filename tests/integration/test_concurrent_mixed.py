#!/usr/bin/env python3
"""
Test concurrent document tracking with mixed success/failure.
This simulates the real scenario where some documents succeed and some fail.
"""
import concurrent.futures
from pathlib import Path

from src.flows.data_ingestion.document_tracker import DocumentTracker


def process_document(doc_id: int, should_fail: bool, tracker_file: str = "data/test_mixed.json"):
    """Simulate a Ray actor processing a document (success or failure)."""
    # Each "actor" creates its own tracker instance (like Ray does)
    tracker = DocumentTracker(tracker_file)

    doc_path = f"data/input/policy/doc_{doc_id}.md"

    if should_fail:
        print(f"Worker {doc_id}: Processing document... ❌ FAILED")
        tracker.mark_failed(doc_path, f"Test error for document {doc_id}")
    else:
        print(f"Worker {doc_id}: Processing document... ✅ SUCCESS")
        episode_id = f"episode-{doc_id}"
        entity_count = doc_id * 10
        relationship_count = doc_id * 5
        tracker.mark_processed(doc_path, episode_id, entity_count, relationship_count)

    return doc_id


def test_concurrent_mixed():
    """Test that mixed success/failure works correctly with concurrent writes."""

    print("🧪 Testing Concurrent Mixed Success/Failure\n")
    print("=" * 60)

    # Clean up any existing file
    tracking_file = Path("data/test_mixed.json")
    if tracking_file.exists():
        tracking_file.unlink()
        print("🗑️  Cleaned up existing tracking file\n")

    # Simulate 10 documents: 8 succeed, 2 fail (like user's scenario)
    num_workers = 10
    failed_docs = {2, 7}  # Documents 2 and 7 will fail

    print(f"🚀 Starting {num_workers} concurrent workers...")
    print("   Expected: 8 success, 2 failures\n")

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        # Submit all tasks
        futures = [
            executor.submit(
                process_document, i, should_fail=(i in failed_docs), tracker_file=str(tracking_file)
            )
            for i in range(num_workers)
        ]

        # Wait for all to complete
        concurrent.futures.wait(futures)

    print("\n" + "=" * 60)
    print("📊 Verification\n")

    # Verify results
    tracker = DocumentTracker(str(tracking_file))

    print(f"Total documents tracked: {len(tracker.processed_docs)}")
    print(f"Expected: {num_workers}")

    stats = tracker.get_stats()
    print("\n📈 Stats:")
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Get successful and failed documents
    successful_docs = [
        doc for path, doc in tracker.processed_docs.items() if doc.get("status") == "completed"
    ]
    failed_docs_list = tracker.get_failed_documents()

    print(f"\n✅ Successful Documents: {len(successful_docs)}")
    for doc in successful_docs[:3]:  # Show first 3
        print(f"   • Document with {doc.get('entity_count', 0)} entities")

    print(f"\n❌ Failed Documents: {len(failed_docs_list)}")
    for failed in failed_docs_list:
        print(f"   • {Path(failed['path']).name}: {failed['error']}")

    print("\n🔍 Data Integrity Check:")
    if len(tracker.processed_docs) == num_workers:
        print("   ✅ All documents tracked!")
    else:
        print(f"   ❌ Missing {num_workers - len(tracker.processed_docs)} documents")

    if len(successful_docs) == 8:
        print("   ✅ Correct number of successful documents!")
    else:
        print(f"   ❌ Expected 8 successful, got {len(successful_docs)}")

    if len(failed_docs_list) == 2:
        print("   ✅ Correct number of failed documents!")
    else:
        print(f"   ❌ Expected 2 failed, got {len(failed_docs_list)}")

    # Verify specific failed documents
    failed_paths = [Path(f["path"]).name for f in failed_docs_list]
    if "doc_2.md" in failed_paths and "doc_7.md" in failed_paths:
        print("   ✅ Correct documents marked as failed!")
    else:
        print(f"   ❌ Wrong documents failed: {failed_paths}")

    # Cleanup
    tracking_file.unlink()

    print("\n" + "=" * 60)
    if stats["completed"] == 8 and stats["failed"] == 2:
        print("✅ SUCCESS: Mixed concurrent tracking working correctly!")
    else:
        print("❌ FAILURE: Some documents were lost or incorrectly tracked")


if __name__ == "__main__":
    test_concurrent_mixed()
