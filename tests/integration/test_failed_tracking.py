#!/usr/bin/env python3
"""
Test that failed document tracking works correctly.
"""
from pathlib import Path
from src.flows.data_ingestion.document_tracker import DocumentTracker


def test_failed_document_tracking():
    """Test that mark_failed works correctly."""

    # Clean up existing file
    tracking_file = Path("data/test_failed_tracking.json")
    if tracking_file.exists():
        tracking_file.unlink()

    print("🧪 Testing Failed Document Tracking\n")
    print("=" * 60)

    # Create tracker
    tracker = DocumentTracker(str(tracking_file))

    # Test 1: Mark some documents as successful
    print("\n✅ Test 1: Mark successful documents")
    tracker.mark_processed("data/input/doc1.md", "episode-1", 10, 5)
    tracker.mark_processed("data/input/doc2.md", "episode-2", 15, 8)
    print(f"   Tracked: {len(tracker.processed_docs)} documents")

    # Test 2: Mark some documents as failed
    print("\n❌ Test 2: Mark failed documents")
    tracker.mark_failed("data/input/failed_doc1.md", "Test error 1")
    tracker.mark_failed("data/input/failed_doc2.md", "Test error 2")
    print(f"   Tracked: {len(tracker.processed_docs)} documents")

    # Test 3: Verify stats
    print("\n📊 Test 3: Verify stats")
    stats = tracker.get_stats()
    print(f"   Total: {stats['total_processed']}")
    print(f"   Completed: {stats['completed']}")
    print(f"   Failed: {stats['failed']}")
    print(f"   Success rate: {stats['success_rate']:.1f}%")

    # Test 4: Get failed documents
    print("\n🔍 Test 4: Get failed documents list")
    failed_docs = tracker.get_failed_documents()
    print(f"   Found {len(failed_docs)} failed documents:")
    for doc in failed_docs:
        print(f"   - {Path(doc['path']).name}: {doc['error']}")

    # Test 5: Verify file contents
    print("\n📄 Test 5: Verify file structure")
    import json
    with open(tracking_file) as f:
        data = json.load(f)

    for path, entry in data.items():
        status = entry.get('status', 'unknown')
        name = Path(path).name
        if status == 'failed':
            print(f"   ❌ {name}: {entry.get('error', 'no error')}")
        else:
            print(f"   ✅ {name}: {entry.get('entity_count', 0)} entities")

    # Assertions
    print("\n" + "=" * 60)
    print("🎯 Validation")

    assert stats['total_processed'] == 4, f"Expected 4 total, got {stats['total_processed']}"
    assert stats['completed'] == 2, f"Expected 2 completed, got {stats['completed']}"
    assert stats['failed'] == 2, f"Expected 2 failed, got {stats['failed']}"
    assert len(failed_docs) == 2, f"Expected 2 failed docs, got {len(failed_docs)}"

    print("✅ All validations passed!")
    print("✅ Failed document tracking is working correctly!")

    # Cleanup
    tracking_file.unlink()


if __name__ == "__main__":
    test_failed_document_tracking()
