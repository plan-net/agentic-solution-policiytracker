"""
Test calling the processor through a Runner actor directly.
"""
import asyncio

import ray

# Initialize Ray
if not ray.is_initialized():
    ray.init(address="auto")


async def test_via_runner():
    """Test via Kodosumi Runner actor."""
    from kodosumi.runner.main import create_runner

    print("Creating Runner actor...")
    fid, runner = create_runner(
        username="test_user",
        base_url="/bundestag-drucksache",
        entry_point="src.flows.bundestag_drucksache.processor:process_drucksache_batch",
        inputs={
            "wahlperioden": ["20"],
            "dokumentart": "Drucksache",
            "batch_size": 5,
            "max_drucksachen": 5,
            "extract_full_text": False,
            "max_concurrent_downloads": 3,
            "create_relationships": False,
        },
    )

    print(f"Runner created with fid: {fid}")
    print("Calling runner.run.remote()...")

    # This is what Launch() does
    runner.run.remote()

    print("Waiting for runner to complete...")
    # Wait a bit to see if it executes
    await asyncio.sleep(5)

    print("Checking if processor was called...")
    # Check logs for "PROCESSOR STARTED"
    import subprocess

    result = subprocess.run(
        ["grep", "-r", "PROCESSOR STARTED", "/tmp/ray/session_latest/logs/"],
        capture_output=True,
        text=True,
    )

    if result.stdout:
        print("✅ PROCESSOR WAS CALLED!")
        print(result.stdout)
    else:
        print("❌ PROCESSOR WAS NOT CALLED")

    return fid


if __name__ == "__main__":
    fid = asyncio.run(test_via_runner())
    print(f"\nTest completed. Runner FID: {fid}")
    print("Check logs in /tmp/ray/session_latest/logs/ for output")
