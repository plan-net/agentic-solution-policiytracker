# Political Monitoring Agent - Quick Reference

## 🚀 Essential Commands

### Daily Use
```bash
just start      # Start everything (takes ~1 minute)
just stop       # Stop everything cleanly
just status     # Check what's running
just redeploy   # Quick redeploy after code changes
```

### Testing
```bash
just test-chat        # Test chat API
just test-ingestion   # Test data ingestion
just test            # Run pytest suite
```

### Debugging
```bash
just logs [service]   # View Docker logs
just ray-logs        # View Ray logs
tail -f logs/kodosumi.log  # Kodosumi logs
```

## 🌐 Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Kodosumi Admin | http://localhost:3370 | admin/admin |
| Open WebUI (Chat) | http://localhost:3000 | - |
| Ray Dashboard | http://localhost:8265 | - |
| Neo4j Browser | http://localhost:7474 | neo4j/password123 |
| Langfuse | http://localhost:3001 | Create on first use |
| Airflow | http://localhost:8080 | admin/admin |

## 📁 Key Directories

- `/data/input/` - Input documents for analysis
- `/data/output/` - Generated reports
- `/data/context/` - Client configuration
- `/logs/` - Application logs
- `/src/` - Source code
- `/docs/` - Documentation

## 🔧 Configuration Files

- `.env` - Environment variables (create from .env.template)
- `config.yaml` - Ray Serve config (auto-generated from template)
- `/data/context/client.yaml` - Client-specific settings

## 💡 Common Tasks

### Process Documents
1. Place documents in `/data/input/`
2. Go to Kodosumi: http://localhost:3370
3. Navigate to Flow > Political Analysis
4. Configure and run analysis

### Chat with Knowledge Graph
1. Open http://localhost:3000
2. Select "political-monitoring-agent" model
3. Ask questions about your data

### Check ETL Status
1. Open Airflow: http://localhost:8080
2. View DAG runs and logs
3. Trigger manual runs if needed

## 🐛 Troubleshooting

### Service Won't Start
```bash
just stop           # Clean stop
docker ps -a        # Check for stuck containers
just start          # Try again
```

### Model Not Found in Open WebUI
- Restart Open WebUI: `docker compose restart open-webui`
- Check chat server: `curl http://localhost:8001/chat/v1/models`

### Port Already in Use
```bash
lsof -i :3370      # Find process using port
kill -9 <PID>      # Kill the process
```

## 📚 More Information

- **User Guide**: `/docs/USER_GUIDE.md` - Comprehensive guide for business users
- **Setup Guide**: `/docs/SETUP.md` - Complete installation and configuration
- **Development**: See pattern files in `/.claude/` for development standards