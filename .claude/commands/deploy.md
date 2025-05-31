# Deploy Command

Perform a quick deployment cycle for the Political Monitoring Agent v0.2.0:

1. Run `just deploy-all` to redeploy Ray Serve applications (chat-server + flow1-data-ingestion)
2. Wait a few seconds for deployment to complete
3. Check Ray applications status using `uv run --active serve status`
4. Check if Chat API is responding at `http://localhost:8001/health`
5. Check if Kodosumi flows are responding at `http://localhost:3370/health`
6. Display the deployment status and access URLs:
   - Chat Interface: http://localhost:3000 (Open WebUI)
   - Chat API: http://localhost:8001/v1/chat/completions
   - Data Ingestion Flow: http://localhost:8001/data-ingestion
   - Kodosumi Admin: http://localhost:3370 (admin/admin)
   - Ray Dashboard: http://localhost:8265
7. If deployment fails, show the recent Ray logs using `just ray-logs | tail -20`

Provide clear status messages throughout the process and use appropriate emojis (🚀, ✅, ❌) to indicate success or failure states.