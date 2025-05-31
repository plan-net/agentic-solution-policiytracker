# Status Command

Perform a comprehensive system health check for the Political Monitoring Agent v0.2.0:

1. Check Docker services status using `docker compose ps` (8 containers should be running)
2. Check Ray cluster status using `uv run --active ray status`
3. Check Ray applications using `uv run --active serve status` (chat-server + flow1-data-ingestion)
4. Check Chat API health by testing `http://localhost:8001/health`
5. Check Kodosumi admin health by testing `http://localhost:3370/health`
6. Check Knowledge Graph connectivity by testing `http://localhost:7474` (Neo4j)
7. Check Langfuse health by testing `http://localhost:3001/api/public/health`
8. Check ETL pipeline health by testing `http://localhost:8080/health` (Airflow)
9. Display a summary with clear ✅/❌ status indicators for each service
10. Show all access URLs at the end:
   - Chat Interface: http://localhost:3000 (Open WebUI)
   - Kodosumi Admin: http://localhost:3370 (admin/admin)
   - Ray Dashboard: http://localhost:8265
   - Neo4j Browser: http://localhost:7474 (neo4j/password123)
   - Langfuse: http://localhost:3001
   - Airflow: http://localhost:8080 (admin/admin)
   - Azurite: http://localhost:10000

Use emojis and clear formatting to make the status report easy to read. If any service is down, provide helpful suggestions for troubleshooting.