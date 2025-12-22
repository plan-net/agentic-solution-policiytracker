import { useState, useEffect } from 'react'
import { Building2, Calendar, ChevronDown } from 'lucide-react'
import EntityBadge from '../common/EntityBadge'
import { formatRelativeTime } from '../../utils/formatters'

// Mock data - will be replaced with API call
const mockUpdates = [
  {
    id: 1,
    type: 'entity_updated',
    title: 'Entity updated',
    description: 'New Developments: US government keeps blocking trade agreement over DSA.',
    entityType: 'Law',
    timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
  },
  {
    id: 2,
    type: 'new_event',
    title: 'New Event',
    description: 'Sept 10, 2025 - Bitkom Privacy Conference (Berlin). Annual conference on data protection, the Data Act & AI regulation.',
    entityType: 'Event',
    timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(), // Yesterday
  },
  {
    id: 3,
    type: 'new_relationship',
    title: 'New Relationship',
    description: 'Connection discovered between GDPR enforcement and Big Tech compliance patterns.',
    entityType: 'Regulation',
    timestamp: new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString(), // 2 days ago
  },
]

function RecentUpdates() {
  const [updates, setUpdates] = useState(mockUpdates)
  const [timeFilter, setTimeFilter] = useState('This week')
  const [isLoading, setIsLoading] = useState(false)

  // TODO: Fetch from API
  // useEffect(() => {
  //   fetchRecentUpdates()
  // }, [timeFilter])

  const getUpdateIcon = (type) => {
    switch (type) {
      case 'entity_updated':
        return Building2
      case 'new_event':
        return Calendar
      default:
        return Building2
    }
  }

  return (
    <div className="mt-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Recent Graph updates</h2>
        <button className="flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900">
          {timeFilter}
          <ChevronDown size={16} />
        </button>
      </div>

      {/* Updates List */}
      <div className="space-y-3">
        {updates.map((update) => {
          const Icon = getUpdateIcon(update.type)
          return (
            <div
              key={update.id}
              className="p-4 bg-content-bgAlt rounded-xl hover:bg-gray-100 transition-colors cursor-pointer"
            >
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center shadow-sm">
                  <Icon size={18} className="text-gray-500" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium text-gray-900">{update.title}</span>
                  </div>
                  <p className="text-sm text-gray-600 mb-2">{update.description}</p>
                  <EntityBadge type={update.entityType} size="small" />
                </div>
                <div className="text-sm text-gray-400 whitespace-nowrap">
                  {formatRelativeTime(update.timestamp)}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {updates.length === 0 && !isLoading && (
        <div className="text-center py-12 text-gray-500">
          No recent updates found
        </div>
      )}
    </div>
  )
}

export default RecentUpdates
