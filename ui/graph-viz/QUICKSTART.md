# Graph Visualization - Quick Start Checklist

## ✅ Setup Checklist (5 minutes)

### Step 1: Fix npm Permissions
```bash
# Run this command to fix npm cache permissions
sudo chown -R $(whoami) ~/.npm

# Or specifically for your user:
sudo chown -R 501:20 "/Users/mangeshkarangutkar/.npm"
```

### Step 2: Install Dependencies
```bash
cd ui/graph-viz
npm install
```

Expected output:
- ✅ react@18.3.1
- ✅ react-force-graph-2d@1.25.4
- ✅ react-force-graph-3d@1.25.4 🎮
- ✅ three@0.160.0
- ✅ axios@1.7.2
- ✅ tailwindcss@3.4.1
- ✅ vite@5.1.0

### Step 3: Start Backend Services
```bash
# From project root
cd ../..

# Start all services
just start

# Deploy graph visualization backend
just deploy-all

# Verify services are running
just status
```

Expected services:
- ✅ Docker containers (8 running)
- ✅ Ray cluster (healthy)
- ✅ Ray Serve apps (chat-server, flow1-data-ingestion, graph-viz-server)

### Step 4: Start Frontend
```bash
cd ui/graph-viz
npm run dev
```

Expected output:
```
VITE v5.1.0  ready in X ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
➜  press h + enter to show help
```

### Step 5: Open Browser
Visit: http://localhost:5173

You should see:
- 🗺️ Schema Explorer tab
- ✨ Text to Cypher tab
- 💬 Chat Context tab
- Health status: "All systems operational" (green)

---

## 🧪 Quick Test (2 minutes)

### Test 1: Schema Explorer
1. Click "Schema Explorer" tab
2. Select category: **Policy**
3. Select query: **Policy Landscape**
4. Click "🚀 Execute Query"
5. ✅ Should show graph with policy entities
6. Click "3D View 🎮" button
7. ✅ Should switch to 3D visualization

### Test 2: Text to Cypher
1. Click "Text to Cypher" tab
2. Click example: **"Show me all policies related to AI"**
3. Click "✨ Generate & Execute"
4. ✅ Should show generated Cypher code
5. ✅ Should display graph results
6. Toggle between 2D and 3D

### Test 3: Chat Context (Optional)
1. Click "Chat Context" tab
2. Get a session ID from Open WebUI chat (http://localhost:3000)
3. Enter session ID
4. Click "🔍 Load Chat Context"
5. ✅ Should show entities used in that chat

---

## 🎮 Cool Features to Try

### 2D/3D Visualization Toggle
- Click "3D View 🎮" to see stunning 3D visualization
- Enable "Auto-rotate" for presentation mode
- Click nodes to highlight connections
- Use search to filter nodes
- Try VR mode (if you have a VR headset)

### Schema Explorer
- Try all 10 predefined queries
- Switch between categories (Policy, Organization, Network, Temporal)
- Click "▶ Show" to view Cypher code
- Watch execution statistics

### Text to Cypher
- Try example queries
- Write your own natural language questions
- Adjust result limit slider (10-200 nodes)
- View query history
- Re-execute previous queries

---

## 🐛 Troubleshooting

### npm permissions error?
```bash
sudo chown -R $(whoami) ~/.npm
rm -rf node_modules package-lock.json
npm install
```

### Backend not available?
```bash
# Check Ray status
uv run --active ray status

# Redeploy if needed
just deploy-all
```

### 3D mode not working?
- Check WebGL support: https://get.webgl.org/
- Try Chrome, Firefox, or Edge
- Disable browser extensions

### Neo4j connection error?
```bash
docker ps | grep neo4j
docker compose restart neo4j
```

---

## 📊 What to Expect

### 2D Mode
- Fast, smooth rendering
- Good for large graphs (200+ nodes)
- Canvas-based

### 3D Mode
- Stunning visuals with depth
- Auto-rotate option
- Good for smaller graphs (<100 nodes)
- WebGL-based

### Performance
- Schema queries: <2 seconds
- Text-to-Cypher: <5 seconds (GPT-4 generation)
- Chat context: <1 second

---

## 🎯 Quick Commands Reference

```bash
# Frontend
cd ui/graph-viz
npm install          # Install dependencies
npm run dev          # Start dev server
npm run build        # Build for production

# Backend
cd ../..
just start           # Start all services
just deploy-all      # Deploy Ray services
just status          # Check service status
just ray-logs        # View Ray logs

# Docker
docker compose up -d      # Start containers
docker compose ps         # Check containers
docker compose restart    # Restart services
```

---

## 📞 Access URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Graph Viz UI | http://localhost:5173 | - |
| Backend API | http://localhost:8001/graph-viz/api/graph | - |
| Chat Interface | http://localhost:3000 | - |
| Ray Dashboard | http://localhost:8265 | - |
| Neo4j Browser | http://localhost:7474 | neo4j/password123 |
| Kodosumi Admin | http://localhost:3370 | admin/admin |

---

## ✨ That's It!

You now have a fully functional graph visualization UI with:
- ✅ 2D/3D visualization toggle
- ✅ 10 predefined schema queries
- ✅ Natural language to Cypher conversion
- ✅ Chat context visualization
- ✅ Interactive graph exploration
- ✅ Dark theme styling

**Enjoy exploring your knowledge graph! 🎉**

---

**Need Help?**
- See full documentation: `DEPLOYMENT.md`
- Implementation details: `../GRAPH_VIZ_IMPLEMENTATION.md`
- Complete summary: `../GRAPH_VIZ_COMPLETE.md`
