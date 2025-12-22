import { useState } from 'react'
import { Sparkles, TrendingUp, AlertTriangle, Link2, RefreshCw } from 'lucide-react'
import EntityBadge from '../components/common/EntityBadge'

// Mock data - will be replaced with API
const mockPatterns = [
  {
    id: 1,
    title: 'Regulatory Convergence Pattern',
    type: 'trend',
    description: 'Multiple EU regulations (GDPR, DSA, DMA, AI Act) are converging in their enforcement mechanisms, creating a unified compliance framework for tech companies.',
    confidence: 0.87,
    entities: ['GDPR', 'DSA', 'DMA', 'AI Act'],
    insight: 'Companies may benefit from a unified compliance approach rather than treating each regulation separately.',
  },
  {
    id: 2,
    title: 'Lobbying Cluster Detected',
    type: 'cluster',
    description: 'Banking and financial services associations are forming coordinated lobbying efforts around digital credit regulations.',
    confidence: 0.92,
    entities: ['Banking Association', 'Consumer Credit Directive', 'Digital Finance'],
    insight: 'Expect policy positions to align across these organizations in upcoming consultations.',
  },
  {
    id: 3,
    title: 'Enforcement Acceleration',
    type: 'anomaly',
    description: 'Unusual spike in enforcement actions against major tech platforms in the past 30 days.',
    confidence: 0.78,
    entities: ['Meta', 'Google', 'Amazon', 'EU Commission'],
    insight: 'This may indicate a coordinated enforcement push ahead of upcoming regulatory deadlines.',
  },
  {
    id: 4,
    title: 'Cross-Jurisdiction Influence',
    type: 'relationship',
    description: 'German parliament decisions are increasingly influenced by EU-level policy discussions, with a 3-week lag pattern.',
    confidence: 0.85,
    entities: ['Bundestag', 'EU Parliament', 'Digital Policy'],
    insight: 'Monitor EU discussions to anticipate German legislative priorities.',
  },
]

const patternTypeConfig = {
  trend: {
    icon: TrendingUp,
    color: 'text-blue-600',
    bgColor: 'bg-blue-100',
    label: 'Trend',
  },
  cluster: {
    icon: Link2,
    color: 'text-green-600',
    bgColor: 'bg-green-100',
    label: 'Cluster',
  },
  anomaly: {
    icon: AlertTriangle,
    color: 'text-amber-600',
    bgColor: 'bg-amber-100',
    label: 'Anomaly',
  },
  relationship: {
    icon: Sparkles,
    color: 'text-purple-600',
    bgColor: 'bg-purple-100',
    label: 'Relationship',
  },
}

function InterestingPatternsPage() {
  const [patterns, setPatterns] = useState(mockPatterns)
  const [isLoading, setIsLoading] = useState(false)
  const [selectedType, setSelectedType] = useState('all')

  const filteredPatterns = selectedType === 'all'
    ? patterns
    : patterns.filter(p => p.type === selectedType)

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
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Interesting Patterns</h1>
          <p className="text-gray-500">AI-discovered patterns and insights from the knowledge graph</p>
        </div>
        <button
          onClick={handleRefresh}
          className="flex items-center gap-2 px-4 py-2 bg-white border border-content-border rounded-lg hover:bg-gray-50"
        >
          <RefreshCw size={18} className={isLoading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 mb-6">
        <button
          onClick={() => setSelectedType('all')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            selectedType === 'all'
              ? 'bg-sidebar-bg text-white'
              : 'bg-white border border-content-border hover:bg-gray-50'
          }`}
        >
          All Patterns
        </button>
        {Object.entries(patternTypeConfig).map(([key, config]) => (
          <button
            key={key}
            onClick={() => setSelectedType(key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              selectedType === key
                ? 'bg-sidebar-bg text-white'
                : 'bg-white border border-content-border hover:bg-gray-50'
            }`}
          >
            <config.icon size={16} />
            {config.label}
          </button>
        ))}
      </div>

      {/* Patterns Grid */}
      <div className="grid grid-cols-2 gap-6">
        {filteredPatterns.map((pattern) => {
          const typeConfig = patternTypeConfig[pattern.type]
          const Icon = typeConfig.icon

          return (
            <div
              key={pattern.id}
              className="bg-white rounded-xl border border-content-border p-6 hover:shadow-lg transition-shadow cursor-pointer"
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${typeConfig.bgColor}`}>
                    <Icon size={20} className={typeConfig.color} />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{pattern.title}</h3>
                    <span className={`text-sm ${typeConfig.color}`}>{typeConfig.label}</span>
                  </div>
                </div>
                <div className="flex items-center gap-1 px-2 py-1 bg-gray-100 rounded-full">
                  <span className="text-xs text-gray-600">Confidence:</span>
                  <span className="text-xs font-medium text-gray-900">
                    {Math.round(pattern.confidence * 100)}%
                  </span>
                </div>
              </div>

              {/* Description */}
              <p className="text-gray-600 text-sm mb-4">{pattern.description}</p>

              {/* Related Entities */}
              <div className="flex flex-wrap gap-2 mb-4">
                {pattern.entities.map((entity, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs"
                  >
                    {entity}
                  </span>
                ))}
              </div>

              {/* Insight */}
              <div className="p-3 bg-accent-primary/5 rounded-lg border border-accent-primary/20">
                <div className="flex items-center gap-2 mb-1">
                  <Sparkles size={14} className="text-accent-primary" />
                  <span className="text-xs font-medium text-accent-primary">Insight</span>
                </div>
                <p className="text-sm text-gray-700">{pattern.insight}</p>
              </div>
            </div>
          )
        })}
      </div>

      {filteredPatterns.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          No patterns found for this category
        </div>
      )}

      {/* Placeholder Notice */}
      <div className="mt-8 p-4 bg-amber-50 border border-amber-200 rounded-xl">
        <p className="text-amber-800 text-sm">
          <strong>Note:</strong> This page shows placeholder data. The backend pattern detection
          algorithm will be implemented in a future update using graph analytics.
        </p>
      </div>
    </div>
  )
}

export default InterestingPatternsPage
