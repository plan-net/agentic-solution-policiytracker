"""
Test script to verify Flow 5c processor works
"""
import asyncio
from unittest.mock import MagicMock

from src.flows.bundestag_drucksache.processor import process_drucksache_batch


async def main():
    # Mock tracer
    tracer = MagicMock()
    tracer.markdown = MagicMock(return_value=asyncio.Future())
    tracer.markdown.return_value.set_result(None)

    # Minimal test inputs
    inputs = {
        "wahlperioden": ["20"],
        "dokumentart": "Alle",
        "start_date": None,
        "end_date": None,
        "batch_size": 10,
        "max_drucksachen": 1,  # Just 1 document
        "extract_full_text": False,
        "max_concurrent_downloads": 5,
        "create_relationships": False,  # Skip relationships for test
    }

    print("Starting processor test...")
    result = await process_drucksache_batch(inputs, tracer)
    print(f"\nProcessor returned: {type(result)}")
    print(f"Result content preview: {str(result)[:200]}...")
    print("\n✅ Test completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
