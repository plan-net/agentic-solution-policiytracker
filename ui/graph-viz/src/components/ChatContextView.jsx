import { useState, useEffect } from 'react'
import { graphApi } from '../services/graphApi'
import GraphVisualization from './GraphVisualization'

function ChatContextView({ initialSessionId = null }) {
  const [sessionId, setSessionId] = useState(initialSessionId || '')
  const [queryText, setQueryText] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [showMetadata, setShowMetadata] = useState(true)

  // Auto-load if initialSessionId is provided via URL
  useEffect(() => {
    if (initialSessionId) {
      loadChatContext()
    }
  }, [initialSessionId])

  const loadChatContext = async () => {
    if (!sessionId.trim()) {
      setError('Please enter a session ID')
      return
    }

    setIsLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await graphApi.getChatContext(
        sessionId.trim(),
        queryText.trim() || null
      )

      if (response.success) {
        const data = response.data

        if (data.error) {
          setError(data.error)
        } else {
          setResult({
            graphData: {
              nodes: data.nodes || [],
              links: data.links || []
            },
            metadata: data.metadata || {},
            nodeCount: data.nodes?.length || 0,
            edgeCount: data.links?.length || 0
          })
        }
      } else {
        setError(response.error || 'Failed to load chat context')
      }
    } catch (err) {
      console.error('Chat context error:', err)
      setError(err.message || 'Failed to load chat context')
    } finally {
      setIsLoading(false)
    }
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
          💬 Chat Context Visualization
        </h2>
        <p className="text-sm text-gray-400">
          Visualize the entities and relationships extracted during a chat conversation.
          Enter a session ID to see what knowledge graph elements were used as context.
        </p>
      </div>

      {/* Input Section */}
      <div className="bg-gray-800 p-4 rounded-lg space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Session ID: <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            value={sessionId}
            onChange={(e) => setSessionId(e.target.value)}
            placeholder="Enter chat session ID (e.g., abc123-session-id)"
            className="w-full px-3 py-2 bg-gray-700 text-gray-200 rounded border border-gray-600 focus:border-blue-500 focus:outline-none font-mono text-sm"
          />
          <p className="text-xs text-gray-500 mt-1">
            💡 Session IDs are tracked when using the chat interface with knowledge graph tools
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Optional Query Filter:
          </label>
          <input
            type="text"
            value={queryText}
            onChange={(e) => setQueryText(e.target.value)}
            placeholder="Filter by specific query text (optional)"
            className="w-full px-3 py-2 bg-gray-700 text-gray-200 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
          />
        </div>

        {/* Load Button */}
        <div className="flex items-center gap-3">
          <button
            onClick={loadChatContext}
            disabled={!sessionId.trim() || isLoading}
            className={`
              flex-1 px-6 py-3 rounded font-medium transition-colors
              ${!sessionId.trim() || isLoading
                ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 text-white'
              }
            `}
          >
            {isLoading ? (
              <span className="flex items-center justify-center gap-2">
                <div className="animate-spin h-4 w-4 border-2 border-white rounded-full border-t-transparent"></div>
                Loading context...
              </span>
            ) : (
              '🔍 Load Chat Context'
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
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-4 bg-red-900/20 border border-red-700 rounded">
          <p className="text-red-400">❌ {error}</p>
          {error.includes('not found') && (
            <p className="text-sm text-gray-400 mt-2">
              💡 Make sure the session ID is correct and that the chat session used knowledge graph tools.
            </p>
          )}
        </div>
      )}

      {/* Results */}
      {result && (
        <>
          {/* Metadata Section */}
          {result.metadata && Object.keys(result.metadata).length > 0 && (
            <div className="bg-gray-800 p-4 rounded-lg">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-lg font-semibold text-gray-200">
                  📋 Session Metadata
                </h3>
                <button
                  onClick={() => setShowMetadata(!showMetadata)}
                  className="text-sm text-blue-400 hover:text-blue-300"
                >
                  {showMetadata ? '▼ Hide' : '▶ Show'}
                </button>
              </div>

              {showMetadata && (
                <div className="space-y-3">
                  {/* Tools Used */}
                  {result.metadata.tools_used && result.metadata.tools_used.length > 0 && (
                    <div>
                      <label className="text-sm font-medium text-gray-400">Tools Used:</label>
                      <div className="flex flex-wrap gap-2 mt-2">
                        {result.metadata.tools_used.map((tool, idx) => (
                          <span
                            key={idx}
                            className="px-2 py-1 bg-blue-900/30 text-blue-300 text-xs rounded border border-blue-700"
                            title={tool.timestamp ? `Executed at ${new Date(tool.timestamp).toLocaleString()}` : undefined}
                          >
                            {typeof tool === 'string' ? tool : tool.tool_name || JSON.stringify(tool)}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Entity Count */}
                  {result.metadata.entity_count !== undefined && (
                    <div className="flex items-center gap-4 text-sm">
                      <span className="text-gray-400">
                        Entities Tracked: <strong className="text-white">{result.metadata.entity_count}</strong>
                      </span>
                      {result.metadata.relationship_count !== undefined && (
                        <span className="text-gray-400">
                          Relationships: <strong className="text-white">{result.metadata.relationship_count}</strong>
                        </span>
                      )}
                    </div>
                  )}

                  {/* Query Text */}
                  {result.metadata.query_text && (
                    <div>
                      <label className="text-sm font-medium text-gray-400">Original Query:</label>
                      <p className="mt-1 p-2 bg-gray-900 rounded text-sm text-gray-300">
                        {result.metadata.query_text}
                      </p>
                    </div>
                  )}

                  {/* Timestamps */}
                  {result.metadata.created_at && (
                    <div className="text-xs text-gray-500">
                      Session created: {new Date(result.metadata.created_at).toLocaleString()}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Stats Bar */}
          <div className="bg-gray-800 p-4 rounded-lg">
            <div className="flex items-center gap-4 text-sm">
              <span className="text-gray-400">
                📊 <strong className="text-white">{result.nodeCount}</strong> nodes
              </span>
              <span className="text-gray-400">
                🔗 <strong className="text-white">{result.edgeCount}</strong> edges
              </span>
            </div>
          </div>

          {/* Graph Visualization */}
          {result.graphData.nodes.length > 0 ? (
            <div className="bg-gray-800 p-4 rounded-lg">
              <h3 className="text-lg font-semibold text-gray-200 mb-4">
                Graph Visualization
              </h3>
              <GraphVisualization graphData={result.graphData} />

              {/* Entity List */}
              <div className="mt-6 pt-6 border-t border-gray-700">
                <h4 className="text-md font-semibold text-gray-300 mb-3">
                  Entities in Context:
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {result.graphData.nodes.slice(0, 10).map((node, idx) => (
                    <div
                      key={idx}
                      className="p-3 bg-gray-900 rounded border border-gray-700"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <p className="text-sm font-medium text-gray-200">{node.name}</p>
                          <p className="text-xs text-gray-400 mt-1">{node.type}</p>
                        </div>
                        <div
                          className="w-3 h-3 rounded-full ml-2 mt-1"
                          style={{
                            backgroundColor: node.type === 'Policy' ? '#3b82f6'
                              : node.type === 'Organization' ? '#10b981'
                              : node.type === 'Person' ? '#f59e0b'
                              : node.type === 'Event' ? '#ef4444'
                              : '#6366f1'
                          }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
                {result.graphData.nodes.length > 10 && (
                  <p className="text-sm text-gray-500 mt-3 text-center">
                    Showing 10 of {result.graphData.nodes.length} entities
                  </p>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-gray-800 p-8 rounded-lg text-center">
              <div className="text-4xl mb-2">📭</div>
              <p className="text-gray-400">
                No entities found for this session. The chat may not have used knowledge graph tools yet.
              </p>
            </div>
          )}
        </>
      )}

      {/* Empty State */}
      {!result && !error && !isLoading && (
        <div className="bg-gray-800 p-12 rounded-lg text-center">
          <div className="text-6xl mb-4">💬</div>
          <p className="text-gray-400 mb-2">
            Enter a chat session ID to visualize the knowledge graph context
          </p>
          <p className="text-sm text-gray-500">
            Session IDs are generated when users interact with the chat interface
          </p>
        </div>
      )}
    </div>
  )
}

export default ChatContextView
