#!/bin/bash

# Debug script for Flow 5c - monitors logs in real-time after form submission

echo "🔍 Flow 5c Real-Time Debug Monitor"
echo "===================================="
echo ""
echo "This will monitor:"
echo "1. Flow 5c replica logs (app.py endpoint)"
echo "2. Ray worker logs (processor execution)"
echo "3. Queue actor logs (Launch() job creation)"
echo ""
echo "Press Ctrl+C to stop monitoring"
echo ""
echo "👉 Now submit the form in Kodosumi UI and watch the logs below..."
echo ""
echo "===================================="
echo ""

# Get the latest Flow 5c replica log file
REPLICA_LOG=$(ls -t /tmp/ray/session_latest/logs/serve/replica_flow5c-bundestag-drucksache_BundestagDrucksacheFlow_*.log 2>/dev/null | head -1)

if [ -z "$REPLICA_LOG" ]; then
    echo "❌ No Flow 5c replica log found"
    exit 1
fi

echo "📝 Monitoring replica log: $(basename $REPLICA_LOG)"
echo ""

# Start monitoring in the background
tail -f "$REPLICA_LOG" &
TAIL_PID=$!

# Also monitor for new worker logs
echo ""
echo "👀 Watching for new worker logs..."
echo ""

# Function to monitor new files
monitor_workers() {
    while true; do
        # Check for new worker logs created in the last 5 seconds
        NEW_WORKERS=$(find /tmp/ray/session_latest/logs/ -name "worker-*.out" -mtime -5s 2>/dev/null)

        for worker_log in $NEW_WORKERS; do
            if [ -f "$worker_log" ]; then
                echo ""
                echo "🆕 NEW WORKER LOG: $(basename $worker_log)"
                echo "-----------------------------------"
                cat "$worker_log"
                echo "-----------------------------------"
                echo ""
            fi
        done

        sleep 2
    done
}

# Start worker monitoring in background
monitor_workers &
MONITOR_PID=$!

# Wait for user interrupt
trap "kill $TAIL_PID $MONITOR_PID 2>/dev/null; echo ''; echo '✅ Monitoring stopped'; exit 0" INT

# Keep script running
wait
