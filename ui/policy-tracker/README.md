# Policy Tracker UI

Modern React-based web interface for the Political Monitoring Agent system. Provides intuitive access to the knowledge graph through interactive visualizations, AI chat, and intelligence reports.

## Features

### 🎯 Core Capabilities

- **Interactive Knowledge Graph** - 3D/2D force-directed visualizations with node exploration
- **AI-Powered Chat** - Conversational queries powered by Claude Agent SDK
- **Intelligence Reports** - Browse, generate, and manage weekly regulatory digests
- **Entity Explorer** - Detailed views of regulations, politicians, organizations, and events
- **Graph Context Visualization** - See entities discussed in chat conversations
- **Recent Activity Tracking** - Monitor new entities and updates
- **Pattern Discovery** - AI-identified trends and relationships

### 🚀 User Experience

- **Responsive Design** - Works on desktop and tablet
- **Real-time Updates** - Streaming responses and live graph updates
- **Dark/Light Theme** - Tailwind-based theming
- **Markdown Support** - Rich text rendering for reports and responses
- **Slide-out Panels** - Non-intrusive detail views
- **Keyboard Navigation** - Accessibility-focused interactions

## Quick Start

### Prerequisites

- Node.js 18+ and npm 9+
- Backend services running (API, Claude Agent, Neo4j)

### Installation

```bash
# Navigate to UI directory
cd ui/policy-tracker

# Install dependencies
npm install

# Start development server
npm run dev
```

The application will open at [http://localhost:5173](http://localhost:5173)

### Production Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview

# Output directory: dist/
```

## Project Structure

```
ui/policy-tracker/
├── src/
│   ├── components/           # React components
│   │   ├── layout/          # Sidebar, panels, navigation
│   │   │   ├── Sidebar.jsx
│   │   │   └── SlideOutPanel.jsx
│   │   ├── graph/           # Graph visualization components
│   │   │   ├── GraphVisualization.jsx
│   │   │   ├── EntityLegend.jsx
│   │   │   └── EntityTable.jsx
│   │   ├── chat/            # Chat interface
│   │   │   ├── ChatContainer.jsx
│   │   │   ├── ChatMessage.jsx
│   │   │   └── ConversationList.jsx
│   │   ├── reports/         # Report management
│   │   │   ├── ReportCard.jsx
│   │   │   └── GenerateReportModal.jsx
│   │   ├── home/            # Homepage components
│   │   │   ├── HeroCard.jsx
│   │   │   ├── QuickActionCard.jsx
│   │   │   └── RecentUpdates.jsx
│   │   └── common/          # Shared components
│   │       ├── EntityBadge.jsx
│   │       └── StatusBadge.jsx
│   ├── pages/               # Route-level pages
│   │   ├── HomePage.jsx
│   │   ├── ChatPage.jsx
│   │   ├── KnowledgeGraphPage.jsx
│   │   ├── WeeklyReportsPage.jsx
│   │   ├── ChatContextPage.jsx
│   │   └── ...
│   ├── services/            # API clients
│   │   ├── api.js          # Backend REST API
│   │   └── graphApi.js     # Graph-specific endpoints
│   ├── stores/              # State management
│   │   └── uiStore.js      # Zustand store for UI state
│   ├── utils/               # Helper functions
│   │   ├── constants.js    # App constants
│   │   └── formatters.js   # Date/text formatting
│   ├── App.jsx              # Root component with routing
│   ├── main.jsx             # Application entry point
│   └── index.css            # Global styles (Tailwind)
├── public/                  # Static assets
│   └── logo.svg
├── index.html               # HTML template
├── package.json             # Dependencies and scripts
├── vite.config.js           # Vite configuration
├── tailwind.config.js       # Tailwind CSS config
└── postcss.config.js        # PostCSS config
```

## Routes

The application uses React Router for navigation:

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | HomePage | Welcome page with quick actions |
| `/chat` | ChatPage | AI chat interface |
| `/chat/:sessionId` | ChatPage | Resume specific chat session |
| `/chat-context` | ChatContextPage | Visualize chat session context |
| `/reports` | WeeklyReportsPage | Browse weekly reports |
| `/reports/:reportId` | ReportDetailPage | View specific report |
| `/assessments` | AssessmentsPage | Entity assessments |
| `/assessments/:id` | AssessmentDetailPage | Assessment details |
| `/knowledge-graph` | KnowledgeGraphPage | Interactive graph visualization |
| `/new-last-7-days` | NewInLast7DaysPage | Recent entity additions |
| `/patterns` | InterestingPatternsPage | AI-identified patterns |
| `/events` | EventsPage | Upcoming deadlines and events |

## Configuration

### Environment Variables

Create a `.env` file in the `ui/policy-tracker` directory:

```bash
# Backend API base URL
VITE_API_URL=http://localhost:5174

# Claude Agent API URL
VITE_CLAUDE_URL=http://localhost:8000

# Optional: Analytics, error tracking, etc.
# VITE_ANALYTICS_ID=...
```

### Backend Endpoints

The UI expects these backend services:

| Service | Default URL | Environment Variable |
|---------|-------------|---------------------|
| Graph API | http://localhost:5174 | `VITE_API_URL` |
| Claude Agent | http://localhost:8000 | `VITE_CLAUDE_URL` |

### API Configuration

Edit [src/services/api.js](src/services/api.js) for custom API configuration:

```javascript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5174'

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})
```

## Key Technologies

### Core Framework

- **React 18.3** - UI framework with concurrent features
- **React Router 6.28** - Client-side routing
- **Vite 5.4** - Build tool and dev server

### State Management

- **Zustand 5.0** - Lightweight state management
- **React Hooks** - Built-in state and effects

### Styling

- **Tailwind CSS 3.4** - Utility-first CSS framework
- **PostCSS** - CSS processing
- **Autoprefixer** - Browser compatibility

### Visualization

- **react-force-graph-3d 1.25** - 3D graph rendering
- **react-force-graph-2d 1.25** - 2D graph rendering
- **Three.js 0.160** - 3D graphics engine
- **three-spritetext 1.8** - Text sprites for 3D labels

### UI Components

- **Lucide React 0.460** - Icon library
- **react-markdown 9.0** - Markdown rendering
- **date-fns 4.1** - Date formatting and manipulation

### HTTP Client

- **Axios 1.7.7** - Promise-based HTTP client

## Development

### Available Scripts

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run linting
npm run lint

# Fix linting issues
npm run lint:fix
```

### Development Server

The Vite dev server includes:
- **Hot Module Replacement (HMR)** - Instant updates without page refresh
- **Fast Refresh** - Preserves component state on edits
- **Source Maps** - Debug original source code
- **Proxy Support** - Configure backend proxies in `vite.config.js`

### Code Style

Follow these conventions:
- Use functional components with hooks
- PascalCase for component files (e.g., `HomePage.jsx`)
- camelCase for utilities and services
- Destructure props at function signature
- Use async/await for asynchronous operations

Example:
```jsx
import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'

function MyComponent({ title, data }) {
  const { id } = useParams()
  const [state, setState] = useState(null)

  useEffect(() => {
    // Side effects here
  }, [id])

  return (
    <div className="container mx-auto">
      <h1 className="text-2xl font-bold">{title}</h1>
      {/* Component content */}
    </div>
  )
}

export default MyComponent
```

## Components

### GraphVisualization

Interactive 3D/2D force-directed graph visualization.

**Props:**
```jsx
<GraphVisualization
  data={{ nodes: [], links: [] }}
  mode="3d"  // or "2d"
  onNodeClick={(node) => console.log(node)}
/>
```

**Features:**
- Automatic layout using force-directed algorithm
- Node coloring by entity type
- Hover tooltips
- Click to select nodes
- Pan, zoom, and rotate controls

### ChatContainer

Conversational interface for querying the knowledge graph.

**Props:**
```jsx
<ChatContainer
  sessionId="optional-session-id"
  onSessionChange={(newSessionId) => console.log(newSessionId)}
/>
```

**Features:**
- Streaming response support
- Markdown rendering
- Code syntax highlighting
- Auto-scroll to latest message
- Session persistence

### Sidebar

Main navigation sidebar.

**Features:**
- Route highlighting
- Icon-based navigation
- Collapsible sections
- Responsive behavior

### SlideOutPanel

Context-sensitive detail panel.

**Usage:**
```javascript
import { useUIStore } from './stores/uiStore'

const { openSlideOutPanel } = useUIStore()

// Open panel with entity details
openSlideOutPanel({
  entityId: 'uuid-here',
  entityName: 'GDPR',
  entityType: 'Regulation'
})
```

## State Management

### UI Store (Zustand)

Global UI state managed with Zustand:

```javascript
import { useUIStore } from './stores/uiStore'

function Component() {
  const {
    slideOutPanel,
    openSlideOutPanel,
    closeSlideOutPanel
  } = useUIStore()

  return (
    <button onClick={() => openSlideOutPanel({ /* ... */ })}>
      Open Panel
    </button>
  )
}
```

**Store Structure:**
```javascript
{
  slideOutPanel: {
    isOpen: boolean,
    entityId: string,
    entityName: string,
    entityType: string
  },
  // Methods
  openSlideOutPanel: (data) => void,
  closeSlideOutPanel: () => void
}
```

## API Integration

### Graph API Client

Located in [src/services/api.js](src/services/api.js):

```javascript
import { api } from './services/api'

// Get entities
const entities = await api.get('/api/graph/entities')

// Search
const results = await api.post('/api/graph/search', { query: 'GDPR' })

// Get entity details
const entity = await api.get(`/api/graph/entities/${uuid}`)
```

### Claude Agent Client

Located in [src/services/graphApi.js](src/services/graphApi.js) (or create separate claude client):

```javascript
import axios from 'axios'

const claudeClient = axios.create({
  baseURL: 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' }
})

// Chat completion
const response = await claudeClient.post('/v1/chat/completions', {
  model: 'claude-policytracker',
  messages: [{ role: 'user', content: 'Your query' }],
  stream: false
})
```

## Styling

### Tailwind CSS

The UI uses Tailwind CSS for styling. Key patterns:

```jsx
// Layout
<div className="flex flex-col items-center justify-center min-h-screen">

// Typography
<h1 className="text-4xl font-bold text-gray-900 mb-4">

// Buttons
<button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">

// Cards
<div className="bg-white rounded-lg shadow-md p-6">

// Spacing
<div className="mt-8 mx-auto max-w-6xl">
```

### Custom Styles

Global styles in [src/index.css](src/index.css):

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer components {
  .btn-primary {
    @apply px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700;
  }
}
```

### Theme Configuration

Edit [tailwind.config.js](tailwind.config.js) to customize:

```javascript
export default {
  theme: {
    extend: {
      colors: {
        'content-bg': '#f9fafb',
        // Add custom colors
      },
    },
  },
}
```

## Performance

### Optimization Tips

1. **Code Splitting** - Lazy load routes
```jsx
import { lazy, Suspense } from 'react'

const KnowledgeGraphPage = lazy(() => import('./pages/KnowledgeGraphPage'))

<Suspense fallback={<Loading />}>
  <KnowledgeGraphPage />
</Suspense>
```

2. **Memoization** - Use React.memo for expensive components
```jsx
import { memo } from 'react'

const EntityCard = memo(({ entity }) => {
  // Component logic
})
```

3. **Virtual Scrolling** - For large lists
```jsx
// Use react-window or similar for large entity lists
```

4. **Graph Performance** - Limit node count
```jsx
// Paginate or filter nodes for large graphs
const visibleNodes = allNodes.slice(0, 500)
```

### Bundle Size

- Production build: ~500KB (gzipped)
- Main chunks: React (~130KB), Three.js (~150KB), App code (~100KB)
- Lazy-loaded routes reduce initial load

### Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

Note: 3D visualization requires WebGL support.

## Testing

### Unit Tests (Future)

```bash
# Run tests
npm test

# Coverage report
npm run test:coverage
```

### E2E Tests (Future)

```bash
# Run Playwright tests
npm run test:e2e
```

### Manual Testing Checklist

- [ ] Graph visualization loads and renders
- [ ] Chat sends messages and receives responses
- [ ] Sidebar navigation works on all routes
- [ ] Reports load and display correctly
- [ ] Entity details open in slide-out panel
- [ ] Session IDs are tracked in chat
- [ ] Responsive layout works on tablet
- [ ] Markdown renders correctly in chat and reports

## Deployment

### Static Site Deployment

The built UI is a static site that can be deployed anywhere:

```bash
# Build
npm run build

# Output: dist/

# Deploy to Netlify
netlify deploy --prod --dir=dist

# Deploy to Vercel
vercel --prod

# Deploy to S3
aws s3 sync dist/ s3://your-bucket/ --acl public-read
```

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name your-domain.com;

    root /var/www/policy-tracker/dist;
    index index.html;

    # SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass http://localhost:5174;
    }

    # Claude Agent proxy
    location /v1/ {
        proxy_pass http://localhost:8000;
    }
}
```

### Docker Deployment

```dockerfile
# Build stage
FROM node:18-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## Troubleshooting

### Common Issues

#### UI not loading

Check backend services:
```bash
curl http://localhost:5174/api/health
curl http://localhost:8000/health
```

#### Graph not rendering

- Verify data format: `{ nodes: [], links: [] }`
- Check browser console for WebGL errors
- Ensure UUIDs are present in node data

#### Chat not working

- Verify Claude Agent is running
- Check CORS configuration
- Ensure `VITE_CLAUDE_URL` is correct
- Review browser network tab for errors

#### Slow performance

- Reduce graph node count (<500 nodes recommended)
- Enable code splitting for routes
- Check for memory leaks in dev tools
- Use production build (optimized)

### Debug Mode

Enable verbose logging:

```javascript
// In src/services/api.js
api.interceptors.request.use(request => {
  console.log('Request:', request)
  return request
})

api.interceptors.response.use(response => {
  console.log('Response:', response)
  return response
})
```

## Contributing

### Adding a New Page

1. Create component in `src/pages/`:
```jsx
// src/pages/NewPage.jsx
function NewPage() {
  return <div>New Page Content</div>
}

export default NewPage
```

2. Add route in `src/App.jsx`:
```jsx
import NewPage from './pages/NewPage'

<Route path="/new-page" element={<NewPage />} />
```

3. Add navigation in `src/components/layout/Sidebar.jsx`

### Adding a New Component

1. Create in appropriate directory (e.g., `src/components/common/`)
2. Follow naming conventions (PascalCase, `.jsx` extension)
3. Export as default
4. Document props with JSDoc or TypeScript

## Future Enhancements

- [ ] TypeScript migration
- [ ] Comprehensive test coverage
- [ ] Accessibility improvements (WCAG 2.1 AA)
- [ ] Mobile-responsive layout
- [ ] Dark mode toggle
- [ ] Advanced graph filtering
- [ ] Real-time WebSocket updates
- [ ] Export to PDF/CSV
- [ ] User preferences persistence
- [ ] Multi-language support

## License

Part of the Political Monitoring Agent project. See main project LICENSE.

---

*Policy Tracker UI v0.1.0 - Built with React, Tailwind, and Three.js*
