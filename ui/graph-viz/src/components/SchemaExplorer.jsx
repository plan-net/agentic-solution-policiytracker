import { useState, useEffect, useCallback } from 'react'
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
  const [showFilters, setShowFilters] = useState(true)
  const [parameterValues, setParameterValues] = useState({})

  // Load available queries on mount
  useEffect(() => {
    loadQueries()
  }, [])

  // Reset parameter values when query changes
  useEffect(() => {
    if (selectedQuery) {
      const query = queries.find(q => q.name === selectedQuery)
      if (query?.parameters) {
        const defaults = {}
        query.parameters.forEach(param => {
          defaults[param.name] = param.default
        })
        setParameterValues(defaults)
      }
    }
  }, [selectedQuery, queries])

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

  // Handle parameter value change
  const handleParameterChange = useCallback((paramName, value) => {
    setParameterValues(prev => ({
      ...prev,
      [paramName]: value
    }))
  }, [])

  // Execute selected query
  const executeQuery = async () => {
    if (!selectedQuery) return

    setIsLoading(true)
    setError(null)
    setExecutionStats(null)

    try {
      // Pass parameters if any are defined
      const hasParams = Object.keys(parameterValues).length > 0
      const result = await graphApi.executeSchemaQuery(
        selectedQuery,
        hasParams ? parameterValues : null
      )

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

  // Render parameter input based on type
  const renderParameterInput = (param) => {
    const value = parameterValues[param.name] ?? param.default

    switch (param.param_type) {
      case 'integer':
        return (
          <div key={param.name} className="flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <label className="text-sm text-gray-400">{param.description}</label>
              <span className="text-sm font-medium text-blue-400">{value}</span>
            </div>
            <input
              type="range"
              min={param.min_value || 1}
              max={param.max_value || 200}
              value={value}
              onChange={(e) => handleParameterChange(param.name, parseInt(e.target.value))}
              className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
            />
            <div className="flex justify-between text-xs text-gray-500">
              <span>{param.min_value || 1}</span>
              <span>{param.max_value || 200}</span>
            </div>
          </div>
        )

      case 'float':
        return (
          <div key={param.name} className="flex flex-col gap-1">
            <label className="text-sm text-gray-400">{param.description}</label>
            <input
              type="number"
              step="0.1"
              min={param.min_value}
              max={param.max_value}
              value={value}
              onChange={(e) => handleParameterChange(param.name, parseFloat(e.target.value))}
              className="w-full px-3 py-2 bg-gray-700 text-gray-200 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
            />
          </div>
        )

      case 'boolean':
        return (
          <div key={param.name} className="flex items-center gap-3">
            <label className="text-sm text-gray-400">{param.description}</label>
            <button
              onClick={() => handleParameterChange(param.name, !value)}
              className={`
                relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                ${value ? 'bg-blue-600' : 'bg-gray-600'}
              `}
            >
              <span
                className={`
                  inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                  ${value ? 'translate-x-6' : 'translate-x-1'}
                `}
              />
            </button>
          </div>
        )

      case 'string':
      default:
        return (
          <div key={param.name} className="flex flex-col gap-1">
            <label className="text-sm text-gray-400">{param.description}</label>
            <input
              type="text"
              value={value}
              onChange={(e) => handleParameterChange(param.name, e.target.value)}
              placeholder={param.description}
              className="w-full px-3 py-2 bg-gray-700 text-gray-200 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
            />
          </div>
        )
    }
  }

  const currentQuery = getCurrentQueryDetails()
  const categoryQueries = getQueriesForCategory()
  const hasParameters = currentQuery?.parameters && currentQuery.parameters.length > 0

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-gray-800 p-4 rounded-lg">
        <h2 className="text-xl font-semibold text-blue-400 mb-2">
          Schema Explorer
        </h2>
        <p className="text-sm text-gray-400">
          Explore the knowledge graph using business-focused queries for regulatory monitoring and compliance tracking.
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
                onClick={() => {
                  setSelectedCategory(key)
                  // Auto-select first query in new category
                  const firstQuery = queries.find(q => q.category === key)
                  if (firstQuery) {
                    setSelectedQuery(firstQuery.name)
                  }
                }}
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

        {/* Query Parameters / Filters */}
        {hasParameters && (
          <div className="border border-gray-700 rounded-lg overflow-hidden">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="w-full flex items-center justify-between p-3 bg-gray-900 hover:bg-gray-800 transition-colors"
            >
              <span className="text-sm font-medium text-gray-300 flex items-center gap-2">
                <span>⚙️</span>
                Query Filters ({currentQuery.parameters.length})
              </span>
              <span className="text-blue-400 text-sm">
                {showFilters ? '▼ Hide' : '▶ Show'}
              </span>
            </button>

            {showFilters && (
              <div className="p-4 bg-gray-900/50 space-y-4">
                {currentQuery.parameters.map(param => renderParameterInput(param))}

                {/* Reset to defaults button */}
                <button
                  onClick={() => {
                    const defaults = {}
                    currentQuery.parameters.forEach(param => {
                      defaults[param.name] = param.default
                    })
                    setParameterValues(defaults)
                  }}
                  className="text-xs text-gray-400 hover:text-gray-300 underline"
                >
                  Reset to defaults
                </button>
              </div>
            )}
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
              'Execute Query'
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
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-4 bg-red-900/20 border border-red-700 rounded">
          <p className="text-red-400">{error}</p>
        </div>
      )}

      {/* Execution Stats */}
      {executionStats && (
        <div className="bg-gray-800 p-4 rounded-lg">
          <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
            <div className="flex flex-wrap items-center gap-4">
              <span className="text-gray-400">
                <strong className="text-white">{executionStats.nodeCount}</strong> nodes
              </span>
              <span className="text-gray-400">
                <strong className="text-white">{executionStats.edgeCount}</strong> edges
              </span>
              <span className="text-gray-400">
                <strong className="text-white">{executionStats.executionTime.toFixed(2)}s</strong> execution
              </span>
            </div>

            {executionStats.stats?.parameters_used && (
              <div className="text-gray-500 text-xs">
                Parameters: {Object.entries(executionStats.stats.parameters_used)
                  .map(([k, v]) => `${k}=${v}`)
                  .join(', ')}
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
