#!/bin/bash
# Deploy Bundestag Ingestion Flow (Flow 5) to Ray Serve
# Part of Political Monitoring Agent v0.2.0

set -e

echo "=================================================="
echo "Bundestag Ingestion Flow Deployment"
echo "=================================================="
echo ""

# Check if Ray is running
echo "Checking Ray cluster status..."
if ! uv run --active ray status &> /dev/null; then
    echo "ERROR: Ray cluster is not running"
    echo "Please start Ray with: just start"
    exit 1
fi
echo "✓ Ray cluster is running"
echo ""

# Sync environment variables to config
echo "Syncing configuration..."
uv run python scripts/sync_env_to_config.py
echo "✓ Configuration synced"
echo ""

# Deploy the Bundestag ingestion flow
echo "Deploying flow5-bundestag-ingestion..."
uv run --active serve deploy config.yaml --app flow5-bundestag-ingestion

# Wait for deployment to complete
echo ""
echo "Waiting for deployment to stabilize..."
sleep 5

# Check deployment status
echo ""
echo "Checking deployment status..."
uv run --active serve status

# Health check
echo ""
echo "Performing health check..."
HEALTH_CHECK_URL="http://localhost:8001/bundestag-ingestion/health"
HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_CHECK_URL" || echo "000")

if [ "$HEALTH_RESPONSE" = "200" ]; then
    echo "✓ Health check passed (HTTP 200)"
else
    echo "⚠ Health check returned HTTP $HEALTH_RESPONSE"
    echo "  The service might still be starting up."
fi

echo ""
echo "=================================================="
echo "Deployment Summary"
echo "=================================================="
echo "Service Name:     flow5-bundestag-ingestion"
echo "Route Prefix:     /bundestag-ingestion"
echo "Replicas:         1"
echo "CPU Allocation:   2 cores"
echo "Memory:           4GB"
echo "Max Concurrency:  2 requests"
echo ""
echo "Access URLs:"
echo "  Flow Endpoint:  http://localhost:8001/bundestag-ingestion"
echo "  Health Check:   http://localhost:8001/bundestag-ingestion/health"
echo "  Kodosumi Admin: http://localhost:3370 (admin/admin)"
echo "  Ray Dashboard:  http://localhost:8265"
echo ""
echo "Data Collection Endpoints:"
echo "  - Vorgang (Legislative processes)"
echo "  - Vorgangsposition (Process positions, 604k+ records)"
echo "  - Drucksache (Parliamentary documents)"
echo "  - Plenarprotokoll (Plenary protocols)"
echo "  - Aktivitaet (Activities)"
echo "  - Person (Members of Parliament)"
echo ""
echo "API Configuration:"
echo "  Base URL:       https://search.dip.bundestag.de/api/v1/"
echo "  Default Period: Wahlperiode 20 (2021-2025)"
echo "  Batch Size:     100 records per request"
echo ""
echo "Next Steps:"
echo "  1. Access Kodosumi admin at http://localhost:3370"
echo "  2. Navigate to Bundestag Ingestion flow"
echo "  3. Configure collection parameters"
echo "  4. Start data ingestion"
echo ""
echo "Monitor with:"
echo "  just bundestag-status    # Check flow health"
echo "  just ray-logs            # View Ray logs"
echo "  just status              # Overall system status"
echo "=================================================="
