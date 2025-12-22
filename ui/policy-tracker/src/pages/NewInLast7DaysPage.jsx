import { useState, useEffect } from 'react'
import { Clock, TrendingUp, Users, FileText, RefreshCw } from 'lucide-react'
import EntityBadge from '../components/common/EntityBadge'
import { formatRelativeTime } from '../utils/formatters'

// Mock data - will be replaced with API
const mockNewNodes = [
  {
    id: 1,
    name: 'Consumer Credit Directive Implementation',
    type: 'Policy',
    description: 'New EU directive implementation being discussed in German parliament.',
    createdAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    connections: 5,
  },
  {
    id: 2,
    name: 'Bitkom Privacy Conference 2025',
    type: 'Event',
    description: 'Annual conference on data protection, AI regulation, and the Data Act.',
    createdAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    connections: 8,
  },
  {
    id: 3,
    name: 'Banking Association',
    type: 'Associations',
    description: 'German banking industry association lobbying for digital-first regulations.',
    createdAt: new Date(Date.now() - 4 * 24 * 60 * 60 * 1000).toISOString(),
    connections: 12,
  },
  {
    id: 4,
    name: 'Digital Markets Act Enforcement',
    type: 'Law',
    description: 'First enforcement actions under the DMA against major tech platforms.',
    createdAt: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    connections: 15,
  },
]

const mockNewRelationships = [
  {
    id: 1,
    source: 'GDPR',
    target: 'Meta',
    type: 'ENFORCES',
    description: 'New enforcement action initiated',
    createdAt: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 2,
    source: 'Banking Association',
    target: 'Consumer Credit Directive',
    type: 'LOBBIES_FOR',
    description: 'Position paper submitted',
    createdAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 3,
    source: 'EU Commission',
    target: 'Digital Markets Act',
    type: 'IMPLEMENTS',
    description: 'New implementation guidelines published',
    createdAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
  },
]

function NewInLast7DaysPage() {
  const [newNodes, setNewNodes] = useState(mockNewNodes)
  const [newRelationships, setNewRelationships] = useState(mockNewRelationships)
  const [isLoading, setIsLoading] = useState(false)

  // Stats
  const stats = {
    totalNodes: newNodes.length,
    totalRelationships: newRelationships.length,
    topType: 'Policy',
    avgConnections: Math.round(newNodes.reduce((sum, n) => sum + n.connections, 0) / newNodes.length),
  }

  const handleRefresh = () => {
    setIsLoading(true)
    // TODO: Fetch from API
    setTimeout(() => setIsLoading(false), 1000)
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">New in Last 7 Days</h1>
          <p className="text-gray-500">Summary of new nodes and relationships added to the knowledge graph</p>
        </div>
        <button
          onClick={handleRefresh}
          className="flex items-center gap-2 px-4 py-2 bg-white border border-content-border rounded-lg hover:bg-gray-50"
        >
          <RefreshCw size={18} className={isLoading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className="bg-white rounded-xl border border-content-border p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <FileText size={20} className="text-blue-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">{stats.totalNodes}</div>
              <div className="text-sm text-gray-500">New Entities</div>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-content-border p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <TrendingUp size={20} className="text-green-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">{stats.totalRelationships}</div>
              <div className="text-sm text-gray-500">New Relationships</div>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-content-border p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              <Clock size={20} className="text-purple-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">{stats.topType}</div>
              <div className="text-sm text-gray-500">Top Entity Type</div>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-content-border p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center">
              <Users size={20} className="text-amber-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">{stats.avgConnections}</div>
              <div className="text-sm text-gray-500">Avg. Connections</div>
            </div>
          </div>
        </div>
      </div>

      {/* New Entities Section */}
      <div className="mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">New Entities</h2>
        <div className="grid grid-cols-2 gap-4">
          {newNodes.map((node) => (
            <div
              key={node.id}
              className="bg-white rounded-xl border border-content-border p-4 hover:shadow-md transition-shadow cursor-pointer"
            >
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-medium text-gray-900">{node.name}</h3>
                <EntityBadge type={node.type} size="small" />
              </div>
              <p className="text-sm text-gray-500 mb-3">{node.description}</p>
              <div className="flex items-center justify-between text-xs text-gray-400">
                <span>{node.connections} connections</span>
                <span>{formatRelativeTime(node.createdAt)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* New Relationships Section */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">New Relationships</h2>
        <div className="bg-white rounded-xl border border-content-border overflow-hidden">
          {newRelationships.map((rel, idx) => (
            <div
              key={rel.id}
              className={`p-4 hover:bg-gray-50 transition-colors cursor-pointer ${
                idx !== newRelationships.length - 1 ? 'border-b border-content-border' : ''
              }`}
            >
              <div className="flex items-center gap-3 mb-2">
                <span className="font-medium text-gray-900">{rel.source}</span>
                <span className="px-2 py-0.5 bg-gray-100 rounded text-xs text-gray-600">
                  {rel.type}
                </span>
                <span className="font-medium text-gray-900">{rel.target}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500">{rel.description}</span>
                <span className="text-xs text-gray-400">{formatRelativeTime(rel.createdAt)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Placeholder Notice */}
      <div className="mt-8 p-4 bg-amber-50 border border-amber-200 rounded-xl">
        <p className="text-amber-800 text-sm">
          <strong>Note:</strong> This page shows placeholder data. The backend API for tracking new entities
          and relationships will be implemented in a future update.
        </p>
      </div>
    </div>
  )
}

export default NewInLast7DaysPage
