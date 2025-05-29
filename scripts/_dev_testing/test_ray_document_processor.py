#!/usr/bin/env python3
"""
Simple test for Ray document processor.
"""

import asyncio
from pathlib import Path
import sys
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from flows.data_ingestion.document_processor import SimpleDocumentProcessor
from flows.data_ingestion.document_tracker import DocumentTracker


async def test_ray_processor():
    """Test the Ray-based document processor."""
    print("🧪 Testing Ray document processor...")
    
    # Setup
    source_path = Path("data/input/examples")
    if not source_path.exists():
        print(f"❌ Test data not found at {source_path}")
        return
    
    tracker = DocumentTracker()
    processor = SimpleDocumentProcessor(tracker, clear_mode=True)
    
    # Test with a few documents
    print(f"📁 Processing documents from {source_path}")
    
    start_time = time.time()
    results = await processor.process_documents(source_path, document_limit=5)
    end_time = time.time()
    
    # Results
    duration = end_time - start_time
    docs_per_minute = (len(results) / duration) * 60 if duration > 0 else 0
    
    successful = len([r for r in results if r["status"] == "success"])
    failed = len([r for r in results if r["status"] == "failed"])
    
    print(f"\n🎉 Test completed!")
    print(f"⏱️  Duration: {duration:.2f}s")
    print(f"🚀 Speed: {docs_per_minute:.1f} docs/minute")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    
    stats = processor.get_processing_stats()
    print(f"🧠 Total entities: {stats['total_entities']}")
    print(f"🔗 Total relationships: {stats['total_relationships']}")
    
    if docs_per_minute >= 20:
        print("🎯 Target performance achieved!")
    else:
        print("⚠️  Performance below target (20+ docs/min)")


if __name__ == "__main__":
    asyncio.run(test_ray_processor())