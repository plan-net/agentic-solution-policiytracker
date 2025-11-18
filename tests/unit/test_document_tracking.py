#!/usr/bin/env python3
"""
Test script to verify document tracking works correctly.
"""
import asyncio
from pathlib import Path

from src.flows.data_ingestion.document_tracker import DocumentTracker


def test_document_tracker():
    """Test that document tracker saves data correctly."""

    # Create tracker (will create fresh file since we deleted the old one)
    tracker = DocumentTracker("data/processed_documents.json")

    print("📝 Testing DocumentTracker...")
    print(f"   Initial state: {len(tracker.processed_docs)} documents\n")

    # Test marking documents as processed
    test_docs = [
        ("data/input/policy/doc1.md", "episode-123", 10, 5),
        ("data/input/policy/doc2.md", "episode-456", 15, 8),
        ("data/input/policy/doc3.md", "episode-789", 20, 12),
    ]

    print("✅ Marking documents as processed:")
    for doc_path, episode_id, entities, relationships in test_docs:
        tracker.mark_processed(doc_path, episode_id, entities, relationships)
        print(f"   • {Path(doc_path).name}: {entities} entities, {relationships} relationships")

    print(f"\n📊 Stats after processing:")
    stats = tracker.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Verify the file was created correctly
    tracking_file = Path("data/processed_documents.json")
    if tracking_file.exists():
        print(f"\n✅ Tracking file created: {tracking_file}")
        print(f"   File size: {tracking_file.stat().st_size} bytes")

        # Read and display first entry
        import json
        with open(tracking_file) as f:
            data = json.load(f)

        print(f"\n📄 Sample entry structure:")
        first_key = list(data.keys())[0]
        first_entry = data[first_key]
        print(f"   Path: {first_key}")
        for key, value in first_entry.items():
            print(f"   {key}: {value}")

        # Check structure is correct
        required_fields = ["episode_id", "processed_at", "status", "entity_count", "relationship_count"]
        missing_fields = [f for f in required_fields if f not in first_entry]

        if missing_fields:
            print(f"\n❌ Missing fields: {missing_fields}")
        else:
            print(f"\n✅ All required fields present!")

        # Check no nested dicts
        has_nested = any(isinstance(v, dict) for v in first_entry.values())
        if has_nested:
            print("❌ WARNING: Found nested dictionaries (incorrect structure)")
        else:
            print("✅ No nested dictionaries (correct structure)")
    else:
        print(f"\n❌ Tracking file not created!")


if __name__ == "__main__":
    test_document_tracker()
