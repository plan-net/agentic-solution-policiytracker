# Graph Visualization UI - Neo4j Knowledge Graph Explorer

🎮 **2D/3D Interactive Graph Visualization** with Text-to-Cypher and Chat Context

---

## ✅ Implementation Status

### Backend (100% Complete!)
✅ FastAPI service with Ray Serve
✅ 10 predefined schema queries
✅ Text-to-Cypher with GPT-4 (LangChain)
✅ Chat context tracking
✅ Session caching (5min TTL)
✅ Cypher safety validation
✅ Async Neo4j queries

### Frontend Structure (Created)
✅ Vite + React setup
✅ Tailwind CSS configured
✅ Package.json with all dependencies
✅ Proxy configuration for API calls

### Frontend Components (To Implement)
⏭️ API service layer
⏭️ GraphVisualization (2D/3D toggle!)
⏭️ SchemaExplorer
⏭️ TextToCypherView
⏭️ ChatContextView
⏭️ App.jsx + main.jsx

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
npm install
```

This installs:
- `react` + `react-dom` (UI framework)
- `react-force-graph-2d` (2D canvas visualization)
- `react-force-graph-3d` (3D WebGL visualization) 🎮
- `three` + `three-spritetext` (3D rendering)
- `axios` (API client)
- `tailwindcss` (styling)
- `vite` (build tool)

### 2. Start Development Server
```bash
npm run dev
```

Visit: http://localhost:5173

### 3. Build for Production
```bash
npm run build
```

Output: `dist/` directory

---

## 🎯 Features

### Backend API (Already Implemented!)

#### Endpoints
Base URL: `http://localhost:8001/graph-viz/api/graph`

1. **GET /health**
   - Health check for Neo4j and LLM services

2. **GET /schema-queries**
   - List all 10 predefined queries

3. **GET /schema-query/{name}**
   - Execute specific schema query
   - Returns: `{nodes: [...], links: [...], execution_time, stats}`

4. **POST /text-to-cypher**
   - Convert natural language to Cypher
   - Body: `{text: string, limit: number}`
   - Returns: `{cypher, nodes, links, execution_time, error?}`

5. **POST /chat-context**
   - Get graph context from chat session
   - Body: `{session_id: string, query?: string}`
   - Returns: `{nodes, links, metadata}`

### Predefined Queries

1. **Policy Landscape** - Overview of all policy entities
2. **Organization Network** - Company relationships
3. **Recent Relationships** - Latest connections (30 days)
4. **Most Connected Entities** - Central nodes (degree > 3)
5. **Major Policy Clusters** - GDPR, DSA, AI Act networks
6. **Company Impact** - Meta, Google, Amazon, Apple
7. **Influence Network** - AFFECTS/INFLUENCES relationships
8. **Temporal Evolution** - Time-based entity changes
9. **Dense Subgraphs** - Community detection
10. **Full Graph Sample** - Random sample (100 nodes)

### Safety Features

✅ **Read-only queries** - Blocks CREATE, DELETE, SET, MERGE
✅ **Query timeout** - 5 seconds max
✅ **Result limits** - Max 200 nodes
✅ **Cypher validation** - Whitelist approach

---

## 🎮 UI Features (To Implement)

### 1. GraphVisualization Component

**2D Mode**:
- Canvas-based rendering
- Fast for large graphs (200+ nodes)
- Zoom, pan, node dragging

**3D Mode** (COOL!):
- WebGL + THREE.js
- Floating text labels
- Directional edge particles
- Auto-rotate option
- Camera reset button
- **VR Mode Support** 🥽

**Controls**:
- Toggle button: [2D View] [3D View 🎮]
- Node coloring by type
- Interactive tooltips
- Search/filter nodes

### 2. SchemaExplorer Component

**Features**:
- Dropdown of 10 predefined queries
- Category grouping (Policy, Organization, Temporal, Network)
- One-click execution
- Display Cypher code
- Execution statistics

**UI Layout**:
```
┌─────────────────────────────────────┐
│ Category: [Policy ▼]                │
│ Query: [Policy Landscape ▼]        │
│ [Execute] [2D View] [3D View 🎮]    │
├─────────────────────────────────────┤
│ Cypher Query:                       │
│ MATCH (p:Entity)-[r]-(e) ...       │
├─────────────────────────────────────┤
│         Graph Visualization         │
│         (2D or 3D Mode)            │
├─────────────────────────────────────┤
│ Stats: 42 nodes • 89 edges • 1.2s  │
└─────────────────────────────────────┘
```

### 3. TextToCypherView Component

**Features**:
- Natural language textarea
- "Generate & Execute ✨" button
- Show generated Cypher (editable)
- Safety warnings
- Query history with re-execute

**Example Flow**:
```
Input: "Show me all policies related to AI"
  ↓
GPT-4 generates:
MATCH (p:Entity)-[r]-(e:Entity)
WHERE p.name CONTAINS 'AI'
RETURN p, r, e LIMIT 50
  ↓
Display in 3D graph with auto-rotate 🎮
```

### 4. ChatContextView Component

**Features**:
- Session ID input
- Fetch graph context from chat tools
- Side-by-side: graph + response text
- Highlight entities mentioned
- Tool usage statistics

**UI Layout**:
```
┌─────────────────────────────────────┐
│ Session ID: [abc123] [Load]        │
│ [2D View] [3D View 🎮]              │
├───────────────┬─────────────────────┤
│               │                     │
│  Graph Canvas │  Response Text      │
│  (2D or 3D)   │  + Entities Used    │
│               │  + Tool Stats       │
│               │                     │
└───────────────┴─────────────────────┘
```

---

## 📦 File Structure

```
ui/graph-viz/
├── package.json              ✅ Created
├── vite.config.js           ✅ Created
├── tailwind.config.js       ✅ Created
├── postcss.config.js        ✅ Created
├── index.html               ✅ Created
├── src/
│   ├── main.jsx             ⏭️ To create
│   ├── App.jsx              ⏭️ To create
│   ├── index.css            ⏭️ To create
│   ├── components/
│   │   ├── GraphVisualization.jsx  ⏭️ 2D/3D toggle
│   │   ├── SchemaExplorer.jsx      ⏭️ Predefined queries
│   │   ├── TextToCypherView.jsx    ⏭️ Natural language
│   │   ├── ChatContextView.jsx     ⏭️ Session context
│   │   ├── NodeDetailsPanel.jsx    ⏭️ Selected node info
│   │   └── QueryHistory.jsx        ⏭️ Recent queries
│   ├── services/
│   │   └── graphApi.js      ⏭️ Axios API client
│   └── utils/
│       └── graphFormatters.js ⏭️ Data transformations
```

---

## 🎨 Color Scheme

```javascript
const NODE_COLORS = {
  Policy: '#3b82f6',      // Blue
  Organization: '#10b981', // Green
  Person: '#f59e0b',       // Orange
  Event: '#ef4444',        // Red
  Entity: '#6366f1'        // Indigo (fallback)
};
```

---

## 🔧 API Client Example

```javascript
// src/services/graphApi.js
import axios from 'axios';

const API_BASE = '/api/graph';

export const graphApi = {
  async executeSchemaQuery(queryName) {
    const response = await axios.get(`${API_BASE}/schema-query/${queryName}`);
    return response.data;
  },

  async textToCypher(text, limit = 50) {
    const response = await axios.post(`${API_BASE}/text-to-cypher`, {
      text,
      limit
    });
    return response.data;
  },

  async getChatContext(sessionId, query = null) {
    const response = await axios.post(`${API_BASE}/chat-context`, {
      session_id: sessionId,
      query
    });
    return response.data;
  }
};
```

---

## 🚀 Deployment

### Development
```bash
npm run dev
# Visit http://localhost:5173
```

### Production Build
```bash
npm run build
# Output: dist/ directory

# Deploy backend
cd ../..
serve deploy config.yaml

# Access at: http://localhost:8001/graph-viz/
```

---

## 📚 Dependencies

### React Visualization
- `react-force-graph-2d` - 2D canvas graph
- `react-force-graph-3d` - 3D WebGL graph
- `three` - 3D rendering engine
- `three-spritetext` - 3D text labels

### API & Styling
- `axios` - HTTP client
- `tailwindcss` - CSS framework
- `vite` - Build tool

---

## 🎯 Next Steps

1. **Install dependencies**: `npm install`
2. **Create API service**: `src/services/graphApi.js`
3. **Implement GraphVisualization**: With 2D/3D toggle!
4. **Implement SchemaExplorer**: Predefined queries
5. **Implement TextToCypherView**: Natural language
6. **Implement ChatContextView**: Session context
7. **Create App.jsx**: Main component
8. **Build and deploy**: `npm run build`

---

## 🎮 Cool Features to Show Off

✨ **2D/3D Toggle** - Switch visualization modes
✨ **Auto-Rotate in 3D** - Presentation mode
✨ **VR Mode** - Immersive exploration 🥽
✨ **Text-to-Cypher** - Natural language queries
✨ **Chat Context** - Visualize conversation entities
✨ **10 Predefined Queries** - One-click exploration

---

## 📞 API Testing

### Test Schema Query
```bash
curl http://localhost:8001/graph-viz/api/graph/schema-query/policy_landscape
```

### Test Text-to-Cypher
```bash
curl -X POST http://localhost:8001/graph-viz/api/graph/text-to-cypher \
  -H "Content-Type: application/json" \
  -d '{"text": "Show me all policies related to AI", "limit": 50}'
```

### Test Health
```bash
curl http://localhost:8001/graph-viz/api/graph/health
```

---

**Status**: Backend 100% complete, frontend structure ready!
**Next**: Implement React components with amazing 2D/3D visualization 🎮✨
