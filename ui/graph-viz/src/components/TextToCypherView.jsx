import { useState } from 'react'
import { graphApi } from '../services/graphApi'
import GraphVisualization from './GraphVisualization'

const EXAMPLE_QUERIES = [
  "Show me all policies related to AI",
  "Find organizations affected by GDPR",
  "What are the relationships between Meta and EU regulations?",
  "Show me recent policy changes",
  "Find all entities connected to digital markets"
]

function TextToCypherView() {
  const [queryText, setQueryText] = useState('')
  const [limit, setLimit] = useState(50)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [queryHistory, setQueryHistory] = useState([])
  const [showCypher, setShowCypher] = useState(true)

  const executeQuery = async () => {
    if (!queryText.trim()) {
      setError('Please enter a query')
      return
    }

    setIsLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await graphApi.textToCypher(queryText, limit)

      if (response.success) {
        const data = response.data

        if (data.error) {
          setError(data.error)
        } else {
          setResult({
            cypher: data.cypher,
            graphData: {
              nodes: data.nodes || [],
              links: data.links || []
            },
            executionTime: data.execution_time,
            nodeCount: data.nodes?.length || 0,
            edgeCount: data.links?.length || 0
          })

          // Add to history
          setQueryHistory(prev => [{
            query: queryText,
            timestamp: new Date().toISOString(),
            nodeCount: data.nodes?.length || 0,
            edgeCount: data.links?.length || 0
          }, ...prev.slice(0, 9)]) // Keep last 10
        }
      } else {
        setError(response.error || 'Query execution failed')
      }
    } catch (err) {
      console.error('Text-to-Cypher error:', err)
      setError(err.message || 'Failed to execute query')
    } finally {
      setIsLoading(false)
    }
  }

  const handleExampleClick = (example) => {
    setQueryText(example)
  }

  const handleHistoryClick = (historyItem) => {
    setQueryText(historyItem.query)
  }

  const clearResults = () => {
    setResult(null)
    setError(null)
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-gray-800 p-4 rounded-lg">
        <h2 className="text-xl font-semibold text-blue-400 mb-2">
          ✨ Text to Cypher
        </h2>
        <p className="text-sm text-gray-400">
          Ask questions in natural language. GPT-4 will convert your query to Cypher and execute it on the knowledge graph.
        </p>
      </div>

      {/* Safety Warning */}
      <div className="bg-yellow-900/20 border border-yellow-700 p-3 rounded">
        <p className="text-sm text-yellow-400">
          ⚠️ <strong>Safety:</strong> Only read-only queries are allowed. CREATE, DELETE, SET, and MERGE operations are blocked.
        </p>
      </div>

      {/* Query Input */}
      <div className="bg-gray-800 p-4 rounded-lg space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Natural Language Query:
          </label>
          <textarea
            value={queryText}
            onChange={(e) => setQueryText(e.target.value)}
            placeholder="Ask a question about the political monitoring knowledge graph..."
            rows={4}
            className="w-full px-3 py-2 bg-gray-700 text-gray-200 rounded border border-gray-600 focus:border-blue-500 focus:outline-none resize-none"
          />
        </div>

        {/* Limit Control */}
        <div className="flex items-center gap-4">
          <label className="text-sm text-gray-300">Result Limit:</label>
          <input
            type="range"
            min="10"
            max="200"
            step="10"
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="flex-1"
          />
          <span className="text-sm text-gray-400 font-mono">{limit} nodes</span>
        </div>

        {/* Execute Button */}
        <div className="flex items-center gap-3">
          <button
            onClick={executeQuery}
            disabled={!queryText.trim() || isLoading}
            className={`
              flex-1 px-6 py-3 rounded font-medium transition-colors
              ${!queryText.trim() || isLoading
                ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 text-white'
              }
            `}
          >
            {isLoading ? (
              <span className="flex items-center justify-center gap-2">
                <div className="animate-spin h-4 w-4 border-2 border-white rounded-full border-t-transparent"></div>
                Generating & Executing...
              </span>
            ) : (
              '✨ Generate & Execute'
            )}
          </button>

          {result && (
            <button
              onClick={clearResults}
              className="px-4 py-3 bg-gray-700 hover:bg-gray-600 rounded transition-colors"
              title="Clear results"
            >
              🗑️
            </button>
          )}
        </div>

        {/* Example Queries */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Example Queries:
          </label>
          <div className="flex flex-wrap gap-2">
            {EXAMPLE_QUERIES.map((example, idx) => (
              <button
                key={idx}
                onClick={() => handleExampleClick(example)}
                className="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 text-gray-300 rounded transition-colors"
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-4 bg-red-900/20 border border-red-700 rounded">
          <p className="text-red-400">❌ {error}</p>
        </div>
      )}

      {/* Generated Cypher */}
      {result && (
        <div className="bg-gray-800 p-4 rounded-lg space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-200">
              Generated Cypher Query
            </h3>
            <button
              onClick={() => setShowCypher(!showCypher)}
              className="text-sm text-blue-400 hover:text-blue-300"
            >
              {showCypher ? '▼ Hide' : '▶ Show'}
            </button>
          </div>

          {showCypher && (
            <pre className="p-3 bg-gray-900 rounded border border-gray-700 text-sm text-green-400 overflow-auto max-h-48">
              {result.cypher}
            </pre>
          )}

          {/* Execution Stats */}
          <div className="flex items-center gap-4 text-sm text-gray-400 pt-2 border-t border-gray-700">
            <span>
              📊 <strong className="text-white">{result.nodeCount}</strong> nodes
            </span>
            <span>
              🔗 <strong className="text-white">{result.edgeCount}</strong> edges
            </span>
            <span>
              ⏱️ <strong className="text-white">{result.executionTime.toFixed(2)}s</strong> execution time
            </span>
          </div>
        </div>
      )}

      {/* Graph Visualization */}
      {result && result.graphData.nodes.length > 0 ? (
        <div className="bg-gray-800 p-4 rounded-lg">
          <h3 className="text-lg font-semibold text-gray-200 mb-4">
            Graph Visualization
          </h3>
          <GraphVisualization graphData={result.graphData} />
        </div>
      ) : (
        result && result.nodeCount === 0 && (
          <div className="bg-gray-800 p-8 rounded-lg text-center">
            <div className="text-4xl mb-2">🔍</div>
            <p className="text-gray-400">
              No results found for your query. Try rephrasing or broadening your search.
            </p>
          </div>
        )
      )}

      {/* Query History */}
      {queryHistory.length > 0 && (
        <div className="bg-gray-800 p-4 rounded-lg">
          <h3 className="text-lg font-semibold text-gray-200 mb-3">
            📜 Recent Queries
          </h3>
          <div className="space-y-2">
            {queryHistory.map((item, idx) => (
              <div
                key={idx}
                onClick={() => handleHistoryClick(item)}
                className="p-3 bg-gray-700 hover:bg-gray-600 rounded cursor-pointer transition-colors"
              >
                <p className="text-sm text-gray-200 mb-1">{item.query}</p>
                <div className="flex items-center gap-4 text-xs text-gray-400">
                  <span>{new Date(item.timestamp).toLocaleString()}</span>
                  <span>📊 {item.nodeCount} nodes</span>
                  <span>🔗 {item.edgeCount} edges</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {!result && !error && !isLoading && (
        <div className="bg-gray-800 p-12 rounded-lg text-center">
          <div className="text-6xl mb-4">💬</div>
          <p className="text-gray-400 mb-2">
            Ask questions about the political monitoring knowledge graph
          </p>
          <p className="text-sm text-gray-500">
            Try clicking an example query above to get started
          </p>
        </div>
      )}
    </div>
  )
}

export default TextToCypherView
