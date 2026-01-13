import { useState, useEffect, useCallback } from 'react'
import { Play, RotateCcw, ChevronDown, ChevronRight, Settings, Code, X } from 'lucide-react'
import { graphApi } from '../../services/graphApi'
import GraphVisualization from './GraphVisualization'
import { useUIStore } from '../../stores/uiStore'

const QUERY_CATEGORIES = {
  policy: { name: 'Policy Analysis', icon: '📜' },
  organization: { name: 'Organizations', icon: '🏢' },
  network: { name: 'Network Analysis', icon: '🕸️' },
  temporal: { name: 'Temporal Evolution', icon: '⏱️' }
}

function SchemaExplorer() {
  const { openSlideOutPanel } = useUIStore()
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

  // Handle node click
  const handleNodeClick = useCallback((node) => {
    openSlideOutPanel({
      name: node.name,
      type: node.type,
      properties: node.properties || {},
      description: `Entity of type ${node.type} in the knowledge graph.`,
    })
  }, [openSlideOutPanel])

  // Render parameter input based on type
  const renderParameterInput = (param) => {
    const value = parameterValues[param.name] ?? param.default

    switch (param.param_type) {
      case 'integer':
        return (
          <div key={param.name} className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm text-gray-600">{param.description}</label>
              <span className="text-sm font-medium text-accent-primary">{value}</span>
            </div>
            <input
              type="range"
              min={param.min_value || 1}
              max={param.max_value || 200}
              value={value}
              onChange={(e) => handleParameterChange(param.name, parseInt(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-accent-primary"
            />
            <div className="flex justify-between text-xs text-gray-400">
              <span>{param.min_value || 1}</span>
              <span>{param.max_value || 200}</span>
            </div>
          </div>
        )

      case 'float':
        return (
          <div key={param.name} className="space-y-1">
            <label className="text-sm text-gray-600">{param.description}</label>
            <input
              type="number"
              step="0.1"
              min={param.min_value}
              max={param.max_value}
              value={value}
              onChange={(e) => handleParameterChange(param.name, parseFloat(e.target.value))}
              className="w-full px-3 py-2 bg-white text-gray-900 rounded-lg border border-content-border focus:border-accent-primary focus:ring-1 focus:ring-accent-primary focus:outline-none"
            />
          </div>
        )

      case 'boolean':
        return (
          <div key={param.name} className="flex items-center justify-between">
            <label className="text-sm text-gray-600">{param.description}</label>
            <button
              onClick={() => handleParameterChange(param.name, !value)}
              className={`
                relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                ${value ? 'bg-accent-primary' : 'bg-gray-300'}
              `}
            >
              <span
                className={`
                  inline-block h-4 w-4 transform rounded-full bg-white transition-transform shadow
                  ${value ? 'translate-x-6' : 'translate-x-1'}
                `}
              />
            </button>
          </div>
        )

      case 'string':
      default:
        return (
          <div key={param.name} className="space-y-1">
            <label className="text-sm text-gray-600">{param.description}</label>
            <input
              type="text"
              value={value}
              onChange={(e) => handleParameterChange(param.name, e.target.value)}
              placeholder={param.description}
              className="w-full px-3 py-2 bg-white text-gray-900 rounded-lg border border-content-border focus:border-accent-primary focus:ring-1 focus:ring-accent-primary focus:outline-none"
            />
          </div>
        )
    }
  }

  const currentQuery = getCurrentQueryDetails()
  const categoryQueries = getQueriesForCategory()
  const hasParameters = currentQuery?.parameters && currentQuery.parameters.length > 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl border border-content-border p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          Schema Explorer
        </h2>
        <p className="text-sm text-gray-500">
          Explore the knowledge graph using prepopulated queries for regulatory monitoring and compliance tracking.
        </p>
      </div>

      {/* Query Selection */}
      <div className="bg-white rounded-xl border border-content-border p-6 space-y-6">
        {/* Category Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">
            Category
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
                  px-4 py-2 rounded-lg text-sm font-medium transition-colors
                  ${selectedCategory === key
                    ? 'bg-accent-primary text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
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
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Query
          </label>
          <div className="relative">
            <select
              value={selectedQuery || ''}
              onChange={(e) => setSelectedQuery(e.target.value)}
              className="w-full px-4 py-3 bg-white text-gray-900 rounded-xl border border-content-border focus:border-accent-primary focus:ring-1 focus:ring-accent-primary focus:outline-none appearance-none cursor-pointer"
            >
              <option value="">Select a query...</option>
              {categoryQueries.map(query => (
                <option key={query.name} value={query.name}>
                  {query.name}
                </option>
              ))}
            </select>
            <ChevronDown size={18} className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
          </div>
        </div>

        {/* Query Description */}
        {currentQuery && (
          <div className="p-4 bg-gray-50 rounded-xl border border-content-border">
            <p className="text-sm text-gray-600">{currentQuery.description}</p>
          </div>
        )}

        {/* Query Parameters / Filters */}
        {hasParameters && (
          <div className="border border-content-border rounded-xl overflow-hidden">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 transition-colors"
            >
              <span className="text-sm font-medium text-gray-700 flex items-center gap-2">
                <Settings size={16} />
                Query Filters ({currentQuery.parameters.length})
              </span>
              {showFilters ? (
                <ChevronDown size={18} className="text-accent-primary" />
              ) : (
                <ChevronRight size={18} className="text-accent-primary" />
              )}
            </button>

            {showFilters && (
              <div className="p-4 bg-white space-y-4">
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
                  className="text-xs text-gray-500 hover:text-accent-primary flex items-center gap-1"
                >
                  <RotateCcw size={12} />
                  Reset to defaults
                </button>
              </div>
            )}
          </div>
        )}

        {/* Cypher Code Display */}
        {currentQuery && (
          <div>
            <button
              onClick={() => setShowCypher(!showCypher)}
              className="flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-accent-primary transition-colors mb-2"
            >
              <Code size={16} />
              Cypher Query
              {showCypher ? (
                <ChevronDown size={16} />
              ) : (
                <ChevronRight size={16} />
              )}
            </button>
            {showCypher && (
              <pre className="p-4 bg-gray-900 rounded-xl text-xs text-gray-300 overflow-auto max-h-48 font-mono">
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
              flex-1 px-6 py-3 rounded-xl font-medium transition-colors flex items-center justify-center gap-2
              ${!selectedQuery || isLoading
                ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                : 'bg-accent-primary hover:bg-accent-primary/90 text-white'
              }
            `}
          >
            {isLoading ? (
              <>
                <div className="animate-spin h-4 w-4 border-2 border-white rounded-full border-t-transparent"></div>
                Executing query...
              </>
            ) : (
              <>
                <Play size={18} />
                Execute Query
              </>
            )}
          </button>

          {graphData.nodes.length > 0 && (
            <button
              onClick={() => {
                setGraphData({ nodes: [], links: [] })
                setExecutionStats(null)
              }}
              className="px-4 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl transition-colors text-gray-700"
              title="Clear results"
            >
              <X size={18} />
            </button>
          )}
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl">
          <p className="text-red-600 text-sm">{error}</p>
        </div>
      )}

      {/* Execution Stats */}
      {executionStats && (
        <div className="bg-white rounded-xl border border-content-border p-4">
          <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
            <div className="flex flex-wrap items-center gap-4">
              <span className="text-gray-500">
                <strong className="text-gray-900">{executionStats.nodeCount}</strong> nodes
              </span>
              <span className="text-gray-500">
                <strong className="text-gray-900">{executionStats.edgeCount}</strong> edges
              </span>
              <span className="text-gray-500">
                <strong className="text-gray-900">{executionStats.executionTime?.toFixed(2) || '0.00'}s</strong> execution
              </span>
            </div>

            {executionStats.stats?.parameters_used && (
              <div className="text-gray-400 text-xs">
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
        <div className="bg-white rounded-xl border border-content-border overflow-hidden">
          <div className="flex items-center justify-between p-4 border-b border-content-border bg-gray-50">
            <h3 className="text-lg font-semibold text-gray-900">
              Graph Visualization
            </h3>
            <div className="text-sm text-gray-500">
              Results for: <span className="text-accent-primary font-medium">{currentQuery?.name}</span>
            </div>
          </div>
          <div style={{ height: '500px' }}>
            <GraphVisualization
              graphData={graphData}
              onNodeClick={handleNodeClick}
              height={500}
            />
          </div>
        </div>
      ) : (
        !isLoading && !error && (
          <div className="bg-white rounded-xl border border-content-border p-12 text-center">
            <div className="text-6xl mb-4">🔍</div>
            <p className="text-gray-500">
              Select a query and click "Execute Query" to explore the knowledge graph
            </p>
          </div>
        )
      )}
    </div>
  )
}

export default SchemaExplorer
