import { useState, useEffect } from 'react'
import { graphApi } from '../services/graphApi'
import GraphVisualization from './GraphVisualization'

const QUERY_CATEGORIES = {
  policy: { name: 'Policy Analysis', icon: '📜' },
  organization: { name: 'Organizations', icon: '🏢' },
  network: { name: 'Network Analysis', icon: '🕸️' },
  temporal: { name: 'Temporal Evolution', icon: '⏱️' }
}

function SchemaExplorer() {
  const [queries, setQueries] = useState([])
  const [selectedCategory, setSelectedCategory] = useState('policy')
  const [selectedQuery, setSelectedQuery] = useState(null)
  const [graphData, setGraphData] = useState({ nodes: [], links: [] })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [executionStats, setExecutionStats] = useState(null)
  const [showCypher, setShowCypher] = useState(false)

  // Load available queries on mount
  useEffect(() => {
    loadQueries()
  }, [])

  const loadQueries = async () => {
    try {
      const result = await graphApi.getSchemaQueries()
      if (result.success) {
        setQueries(result.data)
        // Auto-select first query in policy category
        const firstPolicyQuery = result.data.find(q => q.category === 'policy')
        if (firstPolicyQuery) {
          setSelectedQuery(firstPolicyQuery.name)
        }
      }
    } catch (err) {
      console.error('Failed to load queries:', err)
      setError('Failed to load available queries')
    }
  }

  // Get queries for selected category
  const getQueriesForCategory = () => {
    return queries.filter(q => q.category === selectedCategory)
  }

  // Execute selected query
  const executeQuery = async () => {
    if (!selectedQuery) return

    setIsLoading(true)
    setError(null)
    setExecutionStats(null)

    try {
      const result = await graphApi.executeSchemaQuery(selectedQuery)

      if (result.success) {
        setGraphData({
          nodes: result.data.nodes || [],
          links: result.data.links || []
        })
        setExecutionStats({
          executionTime: result.data.execution_time,
          nodeCount: result.data.nodes?.length || 0,
          edgeCount: result.data.links?.length || 0,
          stats: result.data.stats
        })
      } else {
        setError(result.error || 'Query execution failed')
      }
    } catch (err) {
      console.error('Query execution error:', err)
      setError(err.message || 'Failed to execute query')
    } finally {
      setIsLoading(false)
    }
  }

  // Get current query details
  const getCurrentQueryDetails = () => {
    return queries.find(q => q.name === selectedQuery)
  }

  const currentQuery = getCurrentQueryDetails()
  const categoryQueries = getQueriesForCategory()

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-gray-800 p-4 rounded-lg">
        <h2 className="text-xl font-semibold text-blue-400 mb-2">
          🗺️ Schema Explorer
        </h2>
        <p className="text-sm text-gray-400">
          Explore the knowledge graph using predefined queries optimized for political monitoring analysis.
        </p>
      </div>

      {/* Query Selection */}
      <div className="bg-gray-800 p-4 rounded-lg space-y-4">
        {/* Category Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Category:
          </label>
          <div className="flex flex-wrap gap-2">
            {Object.entries(QUERY_CATEGORIES).map(([key, category]) => (
              <button
                key={key}
                onClick={() => setSelectedCategory(key)}
                className={`
                  px-4 py-2 rounded transition-colors
                  ${selectedCategory === key
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }
                `}
              >
                <span className="mr-2">{category.icon}</span>
                {category.name}
              </button>
            ))}
          </div>
        </div>

        {/* Query Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Query:
          </label>
          <select
            value={selectedQuery || ''}
            onChange={(e) => setSelectedQuery(e.target.value)}
            className="w-full px-3 py-2 bg-gray-700 text-gray-200 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
          >
            <option value="">Select a query...</option>
            {categoryQueries.map(query => (
              <option key={query.name} value={query.name}>
                {query.name}
              </option>
            ))}
          </select>
        </div>

        {/* Query Description */}
        {currentQuery && (
          <div className="p-3 bg-gray-900 rounded border border-gray-700">
            <p className="text-sm text-gray-300">{currentQuery.description}</p>
          </div>
        )}

        {/* Cypher Code Display */}
        {currentQuery && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-gray-300">
                Cypher Query:
              </label>
              <button
                onClick={() => setShowCypher(!showCypher)}
                className="text-sm text-blue-400 hover:text-blue-300"
              >
                {showCypher ? '▼ Hide' : '▶ Show'}
              </button>
            </div>
            {showCypher && (
              <pre className="p-3 bg-gray-900 rounded border border-gray-700 text-xs text-gray-300 overflow-auto max-h-48">
                {currentQuery.cypher}
              </pre>
            )}
          </div>
        )}

        {/* Execute Button */}
        <div className="flex items-center gap-3">
          <button
            onClick={executeQuery}
            disabled={!selectedQuery || isLoading}
            className={`
              flex-1 px-6 py-3 rounded font-medium transition-colors
              ${!selectedQuery || isLoading
                ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 text-white'
              }
            `}
          >
            {isLoading ? (
              <span className="flex items-center justify-center gap-2">
                <div className="animate-spin h-4 w-4 border-2 border-white rounded-full border-t-transparent"></div>
                Executing query...
              </span>
            ) : (
              '🚀 Execute Query'
            )}
          </button>

          {graphData.nodes.length > 0 && (
            <button
              onClick={() => {
                setGraphData({ nodes: [], links: [] })
                setExecutionStats(null)
              }}
              className="px-4 py-3 bg-gray-700 hover:bg-gray-600 rounded transition-colors"
              title="Clear results"
            >
              🗑️
            </button>
          )}
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-4 bg-red-900/20 border border-red-700 rounded">
          <p className="text-red-400">❌ {error}</p>
        </div>
      )}

      {/* Execution Stats */}
      {executionStats && (
        <div className="bg-gray-800 p-4 rounded-lg">
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-4">
              <span className="text-gray-400">
                📊 <strong className="text-white">{executionStats.nodeCount}</strong> nodes
              </span>
              <span className="text-gray-400">
                🔗 <strong className="text-white">{executionStats.edgeCount}</strong> edges
              </span>
              <span className="text-gray-400">
                ⏱️ <strong className="text-white">{executionStats.executionTime.toFixed(2)}s</strong> execution time
              </span>
            </div>

            {executionStats.stats && (
              <div className="text-gray-400 text-xs">
                {executionStats.stats.nodes_created > 0 && (
                  <span className="mr-3">Created: {executionStats.stats.nodes_created} nodes</span>
                )}
                {executionStats.stats.relationships_created > 0 && (
                  <span>Relationships: {executionStats.stats.relationships_created}</span>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Graph Visualization */}
      {graphData.nodes.length > 0 ? (
        <div className="bg-gray-800 p-4 rounded-lg">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-200">
              Graph Visualization
            </h3>
            <div className="text-sm text-gray-400">
              Showing results for: <span className="text-blue-400">{currentQuery?.name}</span>
            </div>
          </div>
          <GraphVisualization graphData={graphData} />
        </div>
      ) : (
        !isLoading && !error && (
          <div className="bg-gray-800 p-12 rounded-lg text-center">
            <div className="text-6xl mb-4">🔍</div>
            <p className="text-gray-400">
              Select a query and click "Execute Query" to explore the knowledge graph
            </p>
          </div>
        )
      )}
    </div>
  )
}

export default SchemaExplorer
