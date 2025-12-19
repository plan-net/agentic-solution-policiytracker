import { useState, useEffect } from 'react'
import SchemaExplorer from './components/SchemaExplorer'
import TextToCypherView from './components/TextToCypherView'
import ChatContextView from './components/ChatContextView'
import { graphApi } from './services/graphApi'

function App() {
  const [activeTab, setActiveTab] = useState('schema')
  const [healthStatus, setHealthStatus] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [urlParams, setUrlParams] = useState({})

  useEffect(() => {
    // Parse URL parameters
    const params = new URLSearchParams(window.location.search)
    const sessionId = params.get('session')
    const view = params.get('view')
    const mode = params.get('mode')

    // Store params for passing to components
    setUrlParams({
      session_id: sessionId,
      view_type: view,
      mode: mode
    })

    // Auto-select tab based on URL params
    if (sessionId && view === 'context') {
      setActiveTab('chat-context')
    } else if (view === 'schema') {
      setActiveTab('schema')
    }

    checkHealth()
  }, [])

  const checkHealth = async () => {
    setIsLoading(true)
    try {
      const result = await graphApi.healthCheck()
      if (result.success) {
        setHealthStatus(result.data)
      }
    } catch (error) {
      console.error('Health check failed:', error)
      setHealthStatus({ status: 'unhealthy', error: error.message })
    } finally {
      setIsLoading(false)
    }
  }

  const tabs = [
    { id: 'schema', name: 'Schema Explorer', icon: '🗺️' },
    { id: 'text-to-cypher', name: 'Text to Cypher', icon: '✨' },
    { id: 'chat-context', name: 'Chat Context', icon: '💬' }
  ]

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-blue-400">
                Knowledge Graph Explorer
              </h1>
              <p className="text-sm text-gray-400 mt-1">
                Political Monitoring Agent - Graph Visualization
              </p>
            </div>

            {/* Health Status */}
            <div className="flex items-center gap-3">
              {isLoading ? (
                <div className="flex items-center gap-2 text-sm text-gray-400">
                  <div className="animate-spin h-4 w-4 border-2 border-blue-500 rounded-full border-t-transparent"></div>
                  <span>Checking health...</span>
                </div>
              ) : healthStatus?.status === 'healthy' ? (
                <div className="flex items-center gap-2 text-sm text-green-400">
                  <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span>All systems operational</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-sm text-red-400">
                  <div className="h-2 w-2 bg-red-500 rounded-full"></div>
                  <span>Service unavailable</span>
                </div>
              )}

              <button
                onClick={checkHealth}
                className="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 rounded transition-colors"
                title="Refresh health status"
              >
                🔄
              </button>
            </div>
          </div>

          {/* Tab Navigation */}
          <nav className="flex gap-1 mt-4 border-b border-gray-700">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  px-4 py-2 text-sm font-medium rounded-t transition-colors
                  ${activeTab === tab.id
                    ? 'bg-gray-900 text-blue-400 border-b-2 border-blue-400'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-gray-700'
                  }
                `}
              >
                <span className="mr-2">{tab.icon}</span>
                {tab.name}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {!isLoading && healthStatus?.status === 'unhealthy' && (
          <div className="mb-4 p-4 bg-red-900/20 border border-red-700 rounded">
            <p className="text-red-400">
              ⚠️ Backend service is not available. Please check if the graph visualization server is running.
            </p>
            {healthStatus?.error && (
              <p className="text-sm text-gray-400 mt-2">Error: {healthStatus.error}</p>
            )}
          </div>
        )}

        {!isLoading && healthStatus?.status === 'degraded' && (
          <div className="mb-4 p-4 bg-yellow-900/20 border border-yellow-700 rounded">
            <p className="text-yellow-400">
              ⚠️ Some services are degraded. Neo4j: {healthStatus?.neo4j_connected ? '✅' : '❌'}, LLM: {healthStatus?.llm_available ? '✅' : '❌'}
            </p>
            <p className="text-sm text-gray-400 mt-1">
              Graph visualization will work, but text-to-cypher may be unavailable.
            </p>
          </div>
        )}

        {activeTab === 'schema' && <SchemaExplorer />}
        {activeTab === 'text-to-cypher' && <TextToCypherView />}
        {activeTab === 'chat-context' && <ChatContextView initialSessionId={urlParams.session_id} initialIs3D={urlParams.mode === '3d'} />}
      </main>

      {/* Footer */}
      <footer className="mt-12 py-6 border-t border-gray-800">
        <div className="max-w-7xl mx-auto px-4 text-center text-sm text-gray-500">
          <p>Political Monitoring Agent v0.2.0 - Graph Visualization UI</p>
          <p className="mt-1">
            Powered by Neo4j, React Force Graph, and Ray Serve
          </p>
        </div>
      </footer>
    </div>
  )
}

export default App
