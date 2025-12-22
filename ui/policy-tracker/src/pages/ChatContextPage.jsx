import { useState, useEffect, useCallback } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, RefreshCw, ExternalLink } from 'lucide-react'
import GraphVisualization from '../components/graph/GraphVisualization'
import EntityLegend from '../components/graph/EntityLegend'
import { graphApi } from '../services/graphApi'
import { useUIStore } from '../stores/uiStore'

// Entity categories for legend
const categories = [
  { key: 'Risk', color: '#EC4899' },
  { key: 'Event', color: '#EF4444' },
  { key: 'Associations', color: '#10B981' },
  { key: 'Company', color: '#14B8A6' },
  { key: 'Law', color: '#3B82F6' },
  { key: 'Regulator', color: '#EC4899' },
  { key: 'Official', color: '#10B981' },
  { key: 'Document', color: '#8B5CF6' },
]

function ChatContextPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { openSlideOutPanel } = useUIStore()

  const sessionId = searchParams.get('session')
  const is3D = searchParams.get('mode') === '3d'

  const [graphData, setGraphData] = useState({ nodes: [], links: [] })
  const [metadata, setMetadata] = useState(null)
  const [selectedCategories, setSelectedCategories] = useState(categories.map(c => c.key))
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  // Load chat context when session ID changes
  useEffect(() => {
    if (sessionId) {
      loadChatContext(sessionId)
    }
  }, [sessionId])

  const loadChatContext = async (sid) => {
    if (!sid) {
      setError('No session ID provided')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const result = await graphApi.getChatContext(sid)

      if (result.success) {
        const data = result.data

        if (data.error) {
          setError(data.error)
        } else {
          setGraphData({
            nodes: data.nodes || [],
            links: data.links || [],
          })
          setMetadata(data.metadata || {})
        }
      } else {
        setError(result.error || 'Failed to load chat context')
      }
    } catch (err) {
      console.error('Chat context error:', err)
      setError(err.message || 'Failed to load chat context')
    } finally {
      setIsLoading(false)
    }
  }

  const handleCategoryToggle = (category) => {
    setSelectedCategories(prev => {
      if (prev.includes(category)) {
        return prev.filter(c => c !== category)
      }
      return [...prev, category]
    })
  }

  const handleNodeClick = useCallback((node) => {
    openSlideOutPanel({
      name: node.name,
      type: node.type,
      properties: node.properties || {},
      description: node.properties?.summary || `Entity of type ${node.type} in the knowledge graph.`,
    })
  }, [openSlideOutPanel])

  const handleRefresh = () => {
    if (sessionId) {
      loadChatContext(sessionId)
    }
  }

  const handleBackToChat = () => {
    if (sessionId) {
      navigate(`/chat/${sessionId}`)
    } else {
      navigate('/chat')
    }
  }

  // Filter graph data by selected categories
  const filteredNodes = graphData.nodes.filter(node => {
    const categoryMap = {
      Law: 'Law',
      Regulation: 'Law',
      Policy: 'Law',
      LegalFramework: 'Law',
      Company: 'Company',
      Organization: 'Company',
      Industry: 'Company',
      Event: 'Event',
      Person: 'Official',
      Politician: 'Official',
      Official: 'Official',
      BundestagPerson: 'Official',
      Risk: 'Risk',
      GovernmentAgency: 'Regulator',
      Regulator: 'Regulator',
      LobbyGroup: 'Associations',
      Associations: 'Associations',
      Document: 'Document',
      Vorgang: 'Document',
      CanonicalEntity: 'Company',
    }
    const category = categoryMap[node.type] || node.type
    return selectedCategories.includes(category)
  })

  // Get set of visible node IDs for link filtering
  const visibleNodeIds = new Set(filteredNodes.map(n => n.id))

  // Filter links to only include those connecting visible nodes
  const filteredLinks = graphData.links.filter(link => {
    const sourceId = typeof link.source === 'object' ? link.source.id : link.source
    const targetId = typeof link.target === 'object' ? link.target.id : link.target
    return visibleNodeIds.has(sourceId) && visibleNodeIds.has(targetId)
  })

  const filteredGraphData = {
    nodes: filteredNodes,
    links: filteredLinks,
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <button
            onClick={handleBackToChat}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            title="Back to Chat"
          >
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Chat Context</h1>
            {sessionId && (
              <p className="text-sm text-gray-500 mt-1">
                Session: <code className="bg-gray-100 px-2 py-0.5 rounded">{sessionId}</code>
              </p>
            )}
          </div>
        </div>
        <button
          onClick={handleRefresh}
          disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2 bg-white border border-content-border rounded-lg hover:bg-gray-50 disabled:opacity-50"
        >
          <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-6 px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-red-600">
          {error}
          {error.includes('not found') && (
            <p className="text-sm text-red-400 mt-1">
              Make sure the session ID is correct and that the chat session used knowledge graph tools.
            </p>
          )}
        </div>
      )}

      {/* Metadata Section */}
      {metadata && Object.keys(metadata).length > 0 && (
        <div className="mb-6 bg-white rounded-xl border border-content-border p-4">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Session Details</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {metadata.entity_count !== undefined && (
              <div>
                <p className="text-sm text-gray-500">Entities Tracked</p>
                <p className="text-xl font-bold text-gray-900">{metadata.entity_count}</p>
              </div>
            )}
            {metadata.relationship_count !== undefined && (
              <div>
                <p className="text-sm text-gray-500">Relationships</p>
                <p className="text-xl font-bold text-gray-900">{metadata.relationship_count}</p>
              </div>
            )}
            {metadata.tools_used && metadata.tools_used.length > 0 && (
              <div className="col-span-2">
                <p className="text-sm text-gray-500 mb-2">Tools Used</p>
                <div className="flex flex-wrap gap-2">
                  {metadata.tools_used.map((tool, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded border border-blue-200"
                    >
                      {typeof tool === 'string' ? tool : tool.tool_name}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
          {metadata.query_text && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              <p className="text-sm text-gray-500">Original Query</p>
              <p className="text-gray-900 mt-1">{metadata.query_text}</p>
            </div>
          )}
        </div>
      )}

      {/* Graph Visualization Container */}
      <div className="bg-white rounded-xl border border-content-border overflow-hidden mb-6">
        {/* Legend */}
        <EntityLegend
          categories={categories}
          selectedCategories={selectedCategories}
          onToggle={handleCategoryToggle}
        />

        {/* Graph Canvas */}
        <div className="relative" style={{ height: '600px' }}>
          {isLoading ? (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-50">
              <div className="flex items-center gap-2 text-gray-500">
                <RefreshCw size={20} className="animate-spin" />
                Loading chat context...
              </div>
            </div>
          ) : filteredGraphData.nodes.length === 0 ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-50">
              <div className="text-4xl mb-4">📭</div>
              <p className="text-gray-500 text-center">
                {sessionId
                  ? 'No entities found for this session.'
                  : 'Enter a session ID to view the chat context graph.'}
              </p>
              {sessionId && (
                <p className="text-sm text-gray-400 mt-2">
                  The chat may not have used knowledge graph tools.
                </p>
              )}
            </div>
          ) : (
            <GraphVisualization
              graphData={filteredGraphData}
              onNodeClick={handleNodeClick}
              height={600}
              is3D={is3D}
            />
          )}
        </div>
      </div>

      {/* Entity List */}
      {filteredGraphData.nodes.length > 0 && (
        <div className="bg-white rounded-xl border border-content-border p-4">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Entities in Context ({filteredGraphData.nodes.length})
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {filteredGraphData.nodes.slice(0, 12).map((node, idx) => (
              <div
                key={idx}
                onClick={() => handleNodeClick(node)}
                className="p-3 bg-gray-50 rounded-lg border border-gray-100 hover:border-accent-primary cursor-pointer transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{node.name}</p>
                    <p className="text-xs text-gray-500 mt-1">{node.type}</p>
                  </div>
                  <div
                    className="w-3 h-3 rounded-full ml-2 mt-1 flex-shrink-0"
                    style={{
                      backgroundColor: categories.find(c => {
                        const categoryMap = {
                          Law: 'Law', Regulation: 'Law', Policy: 'Law', LegalFramework: 'Law',
                          Company: 'Company', Organization: 'Company', Industry: 'Company', CanonicalEntity: 'Company',
                          Event: 'Event',
                          Person: 'Official', Politician: 'Official', Official: 'Official', BundestagPerson: 'Official',
                          Risk: 'Risk',
                          GovernmentAgency: 'Regulator', Regulator: 'Regulator',
                          LobbyGroup: 'Associations', Associations: 'Associations',
                          Document: 'Document', Vorgang: 'Document',
                        }
                        return c.key === (categoryMap[node.type] || node.type)
                      })?.color || '#6366f1'
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
          {filteredGraphData.nodes.length > 12 && (
            <p className="text-sm text-gray-500 mt-4 text-center">
              Showing 12 of {filteredGraphData.nodes.length} entities
            </p>
          )}
        </div>
      )}
    </div>
  )
}

export default ChatContextPage
