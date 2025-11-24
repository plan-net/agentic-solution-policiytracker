# Graph Visualization UI - Deployment Guide

## 🎉 Implementation Complete!

All frontend components have been created. The UI features 2D/3D graph visualization with toggle support.

---

## 📋 Prerequisites

Before running the frontend, fix npm cache permissions:

```bash
# Fix npm cache permissions (macOS/Linux)
sudo chown -R $(whoami) ~/.npm

# Or for the specific user:
sudo chown -R 501:20 "/Users/mangeshkarangutkar/.npm"
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd ui/graph-viz
npm install
```

This will install all required packages:
- React + React DOM
- react-force-graph-2d (2D canvas visualization)
- react-force-graph-3d (3D WebGL visualization) 🎮
- three + three-spritetext (3D rendering)
- axios (API communication)
- Tailwind CSS (styling)
- Vite (dev server + build tool)

### 2. Start Backend Services

```bash
# From project root
cd ../..

# Start all services (Docker + Ray)
just start

# Deploy graph visualization backend
just deploy-all
```

### 3. Start Development Server

```bash
cd ui/graph-viz
npm run dev
```

Visit: http://localhost:5173

### 4. Build for Production

```bash
npm run build
```

Output: `dist/` directory ready for deployment

---

## 🎯 Features Implemented

### ✅ Backend API (100% Complete)
- **FastAPI Server** with Ray Serve deployment
- **10 Predefined Schema Queries** for political analysis
- **Text-to-Cypher Conversion** using GPT-4 via LangChain
- **Chat Context Tracking** with 5-minute TTL caching
- **Cypher Safety Validation** (read-only enforcement)
- **Async Neo4j Queries** with connection pooling

### ✅ Frontend UI (100% Complete)

#### **1. Schema Explorer** 🗺️
- Category-based query selection (Policy, Organization, Network, Temporal)
- Dropdown of 10 predefined queries
- Cypher code display (show/hide)
- Execution statistics (nodes, edges, time)
- Graph visualization with 2D/3D toggle

#### **2. Text to Cypher** ✨
- Natural language query input
- GPT-4 conversion to Cypher
- Result limit slider (10-200 nodes)
- Example query buttons
- Generated Cypher display
- Query history (last 10 queries)
- Safety warnings for read-only enforcement

#### **3. Chat Context Visualization** 💬
- Session ID input
- Optional query filter
- Session metadata display (tools used, entity count)
- Entity list with type coloring
- Timestamp tracking
- Graph visualization with 2D/3D toggle

#### **4. Graph Visualization Component** 🎮
**2D Mode** (Canvas-based):
- Fast rendering for large graphs (200+ nodes)
- Zoom, pan, node dragging
- Search and filter nodes
- Highlight connected nodes on click

**3D Mode** (WebGL/THREE.js):
- Stunning 3D visualization with depth
- Auto-rotate option for presentations
- 3D text labels using SpriteText
- Directional edge particles
- Camera reset button
- **VR Mode Support** 🥽 (built-in to react-force-graph-3d)

**Shared Features**:
- One-click 2D/3D toggle
- Node coloring by entity type
- Interactive tooltips with properties
- Real-time search/filter
- Node click details panel
- Color-coded legend
- Connection highlighting

---

## 📦 File Structure

```
ui/graph-viz/
├── package.json              ✅ Dependencies configured
├── vite.config.js           ✅ Dev server + API proxy
├── tailwind.config.js       ✅ Dark theme styling
├── postcss.config.js        ✅ CSS processing
├── index.html               ✅ HTML entry point
├── src/
│   ├── main.jsx            ✅ React root
│   ├── App.jsx             ✅ Main app with tabs
│   ├── index.css           ✅ Tailwind + custom styles
│   ├── components/
│   │   ├── GraphVisualization.jsx  ✅ 2D/3D graph
│   │   ├── SchemaExplorer.jsx      ✅ Predefined queries
│   │   ├── TextToCypherView.jsx    ✅ Natural language
│   │   └── ChatContextView.jsx     ✅ Session context
│   └── services/
│       └── graphApi.js     ✅ API client
└── DEPLOYMENT.md           ✅ This file
```

---

## 🔧 API Endpoints

Base URL: `http://localhost:8001/graph-viz/api/graph`

### 1. Health Check
```bash
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "neo4j": "connected",
  "llm": "available"
}
```

### 2. List Schema Queries
```bash
GET /schema-queries
```

**Response:**
```json
[
  {
    "name": "policy_landscape",
    "description": "Overview of all policy entities",
    "category": "policy",
    "cypher": "MATCH (p:Entity)-[r]-(e:Entity)..."
  }
]
```

### 3. Execute Schema Query
```bash
GET /schema-query/{query_name}
```

**Example:**
```bash
curl http://localhost:8001/graph-viz/api/graph/schema-query/policy_landscape
```

**Response:**
```json
{
  "nodes": [
    {
      "id": "uuid-123",
      "name": "EU AI Act",
      "type": "Policy",
      "properties": {},
      "val": 5
    }
  ],
  "links": [
    {
      "source": "uuid-123",
      "target": "uuid-456",
      "type": "AFFECTS",
      "value": 1.0
    }
  ],
  "execution_time": 1.23,
  "stats": {
    "nodes_returned": 42,
    "relationships_returned": 89
  }
}
```

### 4. Text to Cypher
```bash
POST /text-to-cypher
Content-Type: application/json

{
  "text": "Show me all policies related to AI",
  "limit": 50
}
```

**Response:**
```json
{
  "cypher": "MATCH (p:Entity)-[r]-(e:Entity)\nWHERE p.name CONTAINS 'AI'\nRETURN p, r, e LIMIT 50",
  "nodes": [...],
  "links": [...],
  "execution_time": 2.45,
  "error": null
}
```

### 5. Chat Context
```bash
POST /chat-context
Content-Type: application/json

{
  "session_id": "abc123-session-id",
  "query": "optional query filter"
}
```

**Response:**
```json
{
  "nodes": [...],
  "links": [...],
  "metadata": {
    "tools_used": ["entity_details", "entity_relationships"],
    "entity_count": 15,
    "relationship_count": 28,
    "query_text": "What is the EU AI Act?",
    "created_at": "2025-11-20T06:00:00Z"
  }
}
```

---

## 🎨 Color Scheme

```javascript
const NODE_COLORS = {
  Policy: '#3b82f6',        // Blue
  Organization: '#10b981',   // Green
  Person: '#f59e0b',         // Orange
  Event: '#ef4444',          // Red
  Entity: '#6366f1'          // Indigo (fallback)
}
```

---

## 🔒 Safety Features

### Read-Only Cypher Enforcement
The backend validates all generated Cypher queries to ensure they are read-only:

**Allowed Keywords:**
- MATCH, RETURN, WHERE, WITH, ORDER BY, LIMIT, SKIP
- UNION, UNWIND, DISTINCT, AS
- AND, OR, NOT, IN, CONTAINS, STARTS WITH, ENDS WITH

**Forbidden Keywords (Blocked):**
- CREATE, DELETE, REMOVE, SET, MERGE
- DROP, DETACH, CALL

**Additional Safety:**
- 5-second query timeout
- Maximum 200 nodes per query
- Session TTL (5 minutes) for context caching

---

## 🐛 Troubleshooting

### Frontend Won't Start

**Issue:** npm permissions error
```bash
npm error code EACCES
```

**Solution:**
```bash
sudo chown -R $(whoami) ~/.npm
cd ui/graph-viz
rm -rf node_modules package-lock.json
npm install
```

### Backend Not Available

**Issue:** Health check fails in UI
```
⚠️ Backend service is not available
```

**Solution:**
```bash
# Check Ray status
uv run --active ray status

# Check Ray Serve applications
uv run --active serve status

# Redeploy if needed
just deploy-all
```

### Neo4j Connection Error

**Issue:** Backend health shows `neo4j: disconnected`

**Solution:**
```bash
# Check Neo4j is running
docker ps | grep neo4j

# Restart Neo4j if needed
docker compose restart neo4j

# Verify connection
curl http://localhost:7474
```

### 3D Visualization Not Working

**Issue:** 3D mode shows black screen or doesn't render

**Solution:**
- Check browser WebGL support: Visit https://get.webgl.org/
- Try a different browser (Chrome, Firefox, Edge)
- Disable browser extensions that might block WebGL
- Check console for THREE.js errors

---

## 📊 Performance Tips

### For Large Graphs (500+ nodes)
- Use **2D mode** for better performance
- Limit query results to 100 nodes
- Use search/filter to focus on specific entities

### For Best Visuals
- Use **3D mode** for smaller graphs (<100 nodes)
- Enable **auto-rotate** for presentations
- Adjust camera position by clicking nodes

### For Chat Context Visualization
- Sessions expire after 5 minutes of inactivity
- Use query filter to narrow down results
- Check session metadata for tool usage stats

---

## 🚢 Production Deployment

### 1. Build Frontend
```bash
cd ui/graph-viz
npm run build
```

### 2. Serve Static Files

**Option A: Via Ray Serve (Recommended)**
```python
# Add static file serving to FastAPI app
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="ui/graph-viz/dist", html=True), name="static")
```

**Option B: Via Nginx**
```nginx
server {
    listen 80;
    server_name graph-viz.yourdomain.com;

    root /path/to/ui/graph-viz/dist;
    index index.html;

    location /api {
        proxy_pass http://localhost:8001/graph-viz/api;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

**Option C: Via Python HTTP Server**
```bash
cd ui/graph-viz/dist
python -m http.server 5173
```

### 3. Environment Configuration

Create `.env` file in `ui/graph-viz/`:
```bash
VITE_API_BASE_URL=http://your-backend-url:8001
```

Update `vite.config.js` to use environment variable:
```javascript
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001',
        changeOrigin: true
      }
    }
  }
})
```

---

## 🎉 Next Steps

1. **Fix npm permissions:**
   ```bash
   sudo chown -R $(whoami) ~/.npm
   ```

2. **Install dependencies:**
   ```bash
   cd ui/graph-viz
   npm install
   ```

3. **Start backend services:**
   ```bash
   cd ../..
   just start
   just deploy-all
   ```

4. **Start development server:**
   ```bash
   cd ui/graph-viz
   npm run dev
   ```

5. **Open browser:**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8001/graph-viz/api/graph/health
   - Ray Dashboard: http://localhost:8265

6. **Test features:**
   - Schema Explorer: Try "Policy Landscape" query
   - Text to Cypher: Ask "Show me all policies related to AI"
   - Chat Context: Use a session ID from Open WebUI chat

---

## 📞 Access URLs

- **Graph Viz UI**: http://localhost:5173
- **Chat Interface**: http://localhost:3000 (Open WebUI)
- **Backend API**: http://localhost:8001/graph-viz/api/graph
- **Ray Dashboard**: http://localhost:8265
- **Neo4j Browser**: http://localhost:7474 (neo4j/password123)
- **Kodosumi Admin**: http://localhost:3370 (admin/admin)

---

**Status**: ✅ Implementation 100% Complete!
**Next**: Fix npm permissions and run `npm install`
**Version**: 0.2.0
