#!/bin/bash
# Helper script to view all data ingestion flow logs

echo "=== Data Ingestion Flow Logs ==="
echo ""
echo "📋 Replica Logs (HTTP requests & flow orchestration):"
echo "---------------------------------------------------"
tail -f /tmp/ray/session_latest/logs/serve/replica_flow1-data-ingestion_DataIngestionFlow_*.log &
REPLICA_PID=$!

echo ""
echo "🤖 Worker Logs (Actor processing & Graphiti operations):"
echo "--------------------------------------------------------"

# Find the most recent worker logs for data ingestion
for worker_log in $(ls -t /tmp/ray/session_latest/logs/worker-*-01000000-*.out 2>/dev/null | head -3); do
    if grep -q "DocumentProcessorActor\|Graphiti client" "$worker_log" 2>/dev/null; then
        echo "Following: $worker_log"
        tail -f "$worker_log" &
    fi
done

# Trap to kill background processes on exit
trap "kill $REPLICA_PID; pkill -P $$; exit" INT TERM EXIT

# Wait for user to press Ctrl+C
wait
