"""
Test if Flow 5c processor can be invoked through Kodosumi Launch.
"""
import asyncio
import ray
from unittest.mock import AsyncMock

# Initialize Ray
if not ray.is_initialized():
    ray.init(address="auto")

async def test_launch():
    """Test launching Flow 5c processor directly."""

    # Import the processor
    from src.flows.bundestag_drucksache.processor import process_drucksache_batch

    # Create mock tracer
    tracer = AsyncMock()

    # Test inputs
    inputs = {
        "wahlperioden": ["20"],
        "dokumentart": "Drucksache",
        "batch_size": 5,
        "max_drucksachen": 5,
        "extract_full_text": False,
        "max_concurrent_downloads": 3,
        "create_relationships": False,
    }

    print("Calling processor directly...")
    try:
        result = await process_drucksache_batch(inputs, tracer)
        print(f"\n✅ Processor returned successfully!")
        print(f"Result type: {type(result)}")
        print(f"Tracer called {tracer.markdown.call_count} times")
        return True
    except Exception as e:
        print(f"\n❌ Processor failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_launch())
    print(f"\nTest {'PASSED' if success else 'FAILED'}")
