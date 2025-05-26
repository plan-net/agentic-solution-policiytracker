# Status Command

Perform a comprehensive system health check for the Political Monitoring Agent:

1. Check Docker services status using `docker compose ps`
2. Check Ray cluster status using `uv run --active ray status`
3. Check Kodosumi health by testing http://localhost:3370/health
4. Check Azure Storage connectivity by running a quick connection test
5. Check Langfuse health by testing http://localhost:3001/api/public/health
6. Display a summary with clear ✅/❌ status indicators for each service
7. Show all access URLs at the end:
   - Kodosumi Admin: http://localhost:3370 (admin/admin)
   - Ray Dashboard: http://localhost:8265
   - App Endpoint: http://localhost:8001/political-analysis  
   - Langfuse: http://localhost:3001
   - Azurite: http://localhost:10000

Use emojis and clear formatting to make the status report easy to read. If any service is down, provide helpful suggestions for troubleshooting.