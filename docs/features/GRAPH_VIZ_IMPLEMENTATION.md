# Graph Visualization UI - Implementation Status

## ✅ Completed (Backend)

### 1. Backend API Service (`src/graph_viz/`)
- **app.py**: FastAPI server with Ray Serve deployment
  - Health check endpoint
  - Schema query execution
  - Text-to-Cypher conversion
  - Chat context extraction

- **models.py**: Pydantic models for all API contracts
  - GraphNode, GraphEdge, GraphData
  - Request/Response models

- **schema_queries.py**: 10 predefined queries
  - Policy Landscape
  - Organization Network
  - Recent Relationships
  - Most Connected Entities
  - Policy Clusters
  - Company Impact
  - Influence Network
  - Temporal Evolution
  - Community Detection
  - Full Graph Sample

- **text_to_cypher.py**: LangChain integration
  - GraphCypherQAChain for text-to-Cypher
  - Safety validation (read-only queries)
  - Query execution with Neo4j driver

- **context_tracker.py**: Chat session tracking
  - Extract entities from tool results
  - Build subgraph from session context
  - 5-minute TTL caching

### 2. Ray Serve Config
- **config.yaml**: Added graph-viz-server application
  - Route: `/graph-viz`
  - CPU: 1 core
  - Memory: 2GB
  - Autoscaling: 1-2 replicas

## 🚧 To Complete (Frontend)

### Required Files

#### 1. Vite Config (`ui/graph-viz/vite.config.js`)
```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/graph-viz/api')
      }
    }
  }
})
```

#### 2. Tailwind Config (`ui/graph-viz/tailwind.config.js`)
```javascript
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

#### 3. Main Entry (`ui/graph-viz/index.html`)
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Graph Visualization - Political Monitoring</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

#### 4. API Service (`ui/graph-viz/src/services/graphApi.js`)
```javascript
import axios from 'axios';

const API_BASE = '/api/graph';

export const graphApi = {
  // Health check
  async healthCheck() {
    const response = await axios.get(`${API_BASE}/health`);
    return response.data;
  },

  // Get schema queries
  async getSchemaQueries() {
    const response = await axios.get(`${API_BASE}/schema-queries`);
    return response.data;
  },

  // Execute schema query
  async executeSchemaQuery(queryName) {
    const response = await axios.get(`${API_BASE}/schema-query/${queryName}`);
    return response.data;
  },

  // Text to Cypher
  async textToCypher(text, limit = 50) {
    const response = await axios.post(`${API_BASE}/text-to-cypher`, { text, limit });
    return response.data;
  },

  // Get chat context
  async getChatContext(sessionId, query = null) {
    const response = await axios.post(`${API_BASE}/chat-context`, {
      session_id: sessionId,
      query
    });
    return response.data;
  }
};
```

#### 5. Graph Visualization Component (2D/3D!)
See: `ui/graph-viz/src/components/GraphVisualization.jsx` (in plan)

Key features:
- Toggle between 2D and 3D modes
- Auto-rotate in 3D
- VR mode support
- Node coloring by type
- Interactive navigation

#### 6. Main App Component
```jsx
import { useState } from 'react';
import GraphVisualization from './components/GraphVisualization';
import SchemaExplorer from './components/SchemaExplorer';
import TextToCypherView from './components/TextToCypherView';
import ChatContextView from './components/ChatContextView';

function App() {
  const [activeTab, setActiveTab] = useState('schema');
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <header className="bg-gray-800 p-4 border-b border-gray-700">
        <h1 className="text-2xl font-bold">Knowledge Graph Visualization</h1>
        <nav className="flex gap-4 mt-2">
          <button onClick={() => setActiveTab('schema')}>Schema Explorer</button>
          <button onClick={() => setActiveTab('text')}>Text to Cypher</button>
          <button onClick={() => setActiveTab('context')}>Chat Context</button>
        </nav>
      </header>

      <main className="flex h-[calc(100vh-100px)]">
        <div className="w-1/3 p-4 border-r border-gray-700 overflow-y-auto">
          {activeTab === 'schema' && <SchemaExplorer onGraphUpdate={setGraphData} />}
          {activeTab === 'text' && <TextToCypherView onGraphUpdate={setGraphData} />}
          {activeTab === 'context' && <ChatContextView onGraphUpdate={setGraphData} />}
        </div>

        <div className="w-2/3">
          <GraphVisualization graphData={graphData} />
        </div>
      </main>
    </div>
  );
}

export default App;
```

## 📋 Deployment Steps

### 1. Install Frontend Dependencies
```bash
cd ui/graph-viz
npm install
```

### 2. Build Frontend
```bash
npm run build
```

### 3. Deploy Backend
```bash
cd ../..
source .venv/bin/activate
serve deploy config.yaml
```

### 4. Verify Deployment
```bash
# Check Ray Serve status
serve status

# Test API health
curl http://localhost:8001/graph-viz/api/graph/health

# Test schema queries
curl http://localhost:8001/graph-viz/api/graph/schema-queries
```

### 5. Access UI
During development:
```bash
cd ui/graph-viz
npm run dev
# Visit http://localhost:5173
```

Production (static files):
- Build files will be in `ui/graph-viz/dist/`
- Serve via FastAPI StaticFiles or separate Nginx

## 🎮 Features Implemented

### Backend Features
✅ 10 predefined schema queries
✅ Text-to-Cypher with GPT-4
✅ Cypher safety validation (read-only)
✅ Chat context tracking
✅ Session caching (5min TTL)
✅ Ray Serve deployment
✅ Async Neo4j queries
✅ OpenAI API integration

### Frontend Features (To Implement)
🚧 2D force-directed graph
🚧 3D WebGL visualization
🚧 View mode toggle (2D/3D/VR)
🚧 Schema query explorer
🚧 Text-to-Cypher interface
🚧 Chat context viewer
🚧 Node details panel
🚧 Query history
🚧 Auto-rotate in 3D
🚧 VR mode support

## 🔗 API Endpoints

### Base URL
`http://localhost:8001/graph-viz/api/graph`

### Endpoints
1. `GET /health` - Health check
2. `GET /schema-queries` - List all predefined queries
3. `GET /schema-query/{name}` - Execute schema query
4. `POST /text-to-cypher` - Convert text to Cypher and execute
5. `POST /chat-context` - Get graph context from chat session

## 🎯 Next Steps

1. **Complete Frontend Components**:
   - GraphVisualization.jsx (with 2D/3D toggle)
   - SchemaExplorer.jsx
   - TextToCypherView.jsx
   - ChatContextView.jsx

2. **Test Backend**:
   ```bash
   # Test schema query
   curl http://localhost:8001/graph-viz/api/graph/schema-query/policy_landscape

   # Test text-to-Cypher
   curl -X POST http://localhost:8001/graph-viz/api/graph/text-to-cypher \
     -H "Content-Type: application/json" \
     -d '{"text": "Show me all policies related to AI", "limit": 50}'
   ```

3. **Build and Deploy**:
   ```bash
   cd ui/graph-viz && npm install && npm run build
   cd ../.. && serve deploy config.yaml
   ```

4. **Access UI**:
   - Development: http://localhost:5173
   - Production: http://localhost:8001/graph-viz/

## 🎨 Design Notes

### Color Scheme
- Policy entities: Blue (#3b82f6)
- Organization entities: Green (#10b981)
- Person entities: Orange (#f59e0b)
- Event entities: Red (#ef4444)
- Generic entities: Indigo (#6366f1)

### 3D Features
- Sphere geometry for nodes
- Floating text labels
- Directional particles for edges
- Auto-rotate option
- Camera reset button
- VR mode (🥽 button)

### Performance
- 2D: Recommended for 200+ nodes
- 3D: Best for < 200 nodes
- Query timeout: 5 seconds
- Result limit: 200 nodes max

## 🐛 Known Issues

None yet - backend is complete and ready for testing!

## 📚 Resources

- [react-force-graph](https://github.com/vasturiano/react-force-graph)
- [LangChain Text-to-Cypher](https://python.langchain.com/docs/tutorials/graph/)
- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/)
- [Ray Serve](https://docs.ray.io/en/latest/serve/index.html)
