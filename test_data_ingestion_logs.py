"""Test data ingestion logging."""
import asyncio
import subprocess
import time


async def test_logs():
    """Trigger data ingestion and check logs."""

    print("=" * 60)
    print("Testing Data Ingestion Flow Logging")
    print("=" * 60)

    # Find the latest Ray log file
    find_cmd = "ls -t /tmp/ray/session_*/logs/serve/replica_flow1-data-ingestion_DataIngestionFlow*.log 2>/dev/null | head -1"
    result = subprocess.run(find_cmd, shell=True, capture_output=True, text=True)
    log_file = result.stdout.strip()

    if not log_file:
        print("❌ Could not find DataIngestionFlow log file")
        return

    print(f"📄 Log file: {log_file}")
    print("=" * 60)

    # Get initial log size
    initial_size = subprocess.run(
        f"wc -l {log_file}",
        shell=True,
        capture_output=True,
        text=True
    ).stdout.split()[0]

    print(f"Initial log lines: {initial_size}")
    print("\n🔍 Watching for new log entries...")
    print("You can trigger the flow via Kodosumi UI at http://localhost:3370")
    print("Or via API at http://localhost:8001/data-ingestion/")
    print("\nPress Ctrl+C to stop watching\n")
    print("=" * 60)

    try:
        # Watch logs for changes
        watch_cmd = f"tail -f {log_file}"
        subprocess.run(watch_cmd, shell=True)
    except KeyboardInterrupt:
        print("\n\n✅ Log watching stopped")


if __name__ == "__main__":
    asyncio.run(test_logs())
