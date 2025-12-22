import { useState, useEffect, useCallback } from 'react'
import { Search, RefreshCw, Plus, Minus, Maximize2, ChevronDown } from 'lucide-react'
import GraphVisualization from '../components/graph/GraphVisualization'
import EntityLegend from '../components/graph/EntityLegend'
import EntityTable from '../components/graph/EntityTable'
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
]

// Mock data for initial display
const mockGraphData = {
  nodes: [
    { id: '1', name: 'GDPR', type: 'Law', val: 10 },
    { id: '2', name: 'Meta', type: 'Company', val: 8 },
    { id: '3', name: 'DSA', type: 'Law', val: 9 },
    { id: '4', name: 'EU Commission', type: 'Regulator', val: 7 },
    { id: '5', name: 'Bitkom Conference', type: 'Event', val: 5 },
    { id: '6', name: 'Data Protection', type: 'Risk', val: 6 },
    { id: '7', name: 'Lars Klingbeil', type: 'Official', val: 4 },
    { id: '8', name: 'Banking Association', type: 'Associations', val: 5 },
  ],
  links: [
    { source: '1', target: '2', type: 'REGULATES' },
    { source: '3', target: '2', type: 'REGULATES' },
    { source: '4', target: '1', type: 'ENFORCES' },
    { source: '4', target: '3', type: 'ENFORCES' },
    { source: '5', target: '1', type: 'DISCUSSES' },
    { source: '6', target: '1', type: 'RELATES_TO' },
    { source: '7', target: '4', type: 'WORKS_FOR' },
    { source: '8', target: '3', type: 'LOBBIES' },
  ],
}

// Mock table data
const mockTableData = [
  { id: '1', name: 'Meta', category: 'Company', impactType: 'Digital Policy', updatedAt: '2025-07-21' },
  { id: '2', name: 'Lars Klingbeil (Finanzen)', category: 'Official', impactType: 'Economic', updatedAt: '2025-07-08' },
  { id: '3', name: 'GDPR Enforcement', category: 'Risk', impactType: 'Compliance', updatedAt: '2025-07-05' },
  { id: '4', name: 'Banking Association', category: 'Associations', impactType: 'Financial', updatedAt: '2025-07-01' },
]

function KnowledgeGraphPage() {
  const { openSlideOutPanel } = useUIStore()
  const [searchQuery, setSearchQuery] = useState('')
  const [graphData, setGraphData] = useState(mockGraphData)
  const [tableData, setTableData] = useState(mockTableData)
  const [selectedCategories, setSelectedCategories] = useState(categories.map(c => c.key))
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  // Load initial graph data
  useEffect(() => {
    loadGraphData()
  }, [])

  const loadGraphData = async () => {
    setIsLoading(true)
    setError(null)
    try {
      // Try to load from API
      const result = await graphApi.executeSchemaQuery('Full Graph Sample')
      if (result.success && result.data.nodes?.length > 0) {
        setGraphData({
          nodes: result.data.nodes,
          links: result.data.links || [],
        })
      }
    } catch (err) {
      console.error('Failed to load graph data:', err)
      // Keep mock data on error
    } finally {
      setIsLoading(false)
    }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) return

    setIsLoading(true)
    try {
      const result = await graphApi.textToCypher(searchQuery)
      if (result.success && result.data.nodes?.length > 0) {
        setGraphData({
          nodes: result.data.nodes,
          links: result.data.links || [],
        })
      }
    } catch (err) {
      setError('Search failed. Please try again.')
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
      description: `Entity of type ${node.type} in the knowledge graph.`,
    })
  }, [openSlideOutPanel])

  const handleRefresh = () => {
    loadGraphData()
  }

  // Filter graph data by selected categories
  const filteredNodes = graphData.nodes.filter(node => {
    // Map node types to category keys
    const categoryMap = {
      Law: 'Law',
      Regulation: 'Law',
      Policy: 'Law',
      Company: 'Company',
      Organization: 'Company',
      Event: 'Event',
      Person: 'Official',
      Politician: 'Official',
      Official: 'Official',
      Risk: 'Risk',
      GovernmentAgency: 'Regulator',
      Regulator: 'Regulator',
      LobbyGroup: 'Associations',
      Associations: 'Associations',
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
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Knowledge Graph</h1>

      {/* Search */}
      <div className="relative mb-6">
        <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          placeholder="Search for an Entity..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          className="w-full pl-11 pr-4 py-3 bg-white border border-content-border rounded-xl focus:border-accent-primary focus:ring-1 focus:ring-accent-primary focus:outline-none"
        />
      </div>

      {/* Graph Visualization Container */}
      <div className="bg-white rounded-xl border border-content-border overflow-hidden mb-6">
        {/* Legend */}
        <EntityLegend
          categories={categories}
          selectedCategories={selectedCategories}
          onToggle={handleCategoryToggle}
        />

        {/* Graph Canvas */}
        <div className="relative" style={{ height: '500px' }}>
          {isLoading ? (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-50">
              <div className="flex items-center gap-2 text-gray-500">
                <RefreshCw size={20} className="animate-spin" />
                Loading graph...
              </div>
            </div>
          ) : (
            <GraphVisualization
              graphData={filteredGraphData}
              onNodeClick={handleNodeClick}
              height={500}
            />
          )}

          {/* Zoom Controls */}
          <div className="absolute top-4 right-4 flex flex-col gap-2">
            <button className="p-2 bg-white border border-content-border rounded-lg hover:bg-gray-50 shadow-sm">
              <Plus size={16} />
            </button>
            <button className="p-2 bg-white border border-content-border rounded-lg hover:bg-gray-50 shadow-sm">
              <Minus size={16} />
            </button>
            <button className="p-2 bg-white border border-content-border rounded-lg hover:bg-gray-50 shadow-sm">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M2 8h12M8 2v12" />
              </svg>
            </button>
            <button className="p-2 bg-white border border-content-border rounded-lg hover:bg-gray-50 shadow-sm">
              <Maximize2 size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Entity Table */}
      <EntityTable
        data={tableData}
        onRefresh={handleRefresh}
        isLoading={isLoading}
      />
    </div>
  )
}

export default KnowledgeGraphPage
