import { ChevronDown, RefreshCw } from 'lucide-react'
import EntityBadge from '../common/EntityBadge'
import { formatDate } from '../../utils/formatters'

function EntityTable({ data, onRefresh, isLoading }) {
  return (
    <div className="bg-white rounded-xl border border-content-border overflow-hidden">
      {/* Filters Row */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-content-border">
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 px-3 py-2 bg-white border border-content-border rounded-lg text-sm hover:bg-gray-50">
            Category
            <ChevronDown size={16} />
          </button>
          <button className="flex items-center gap-2 px-3 py-2 bg-white border border-content-border rounded-lg text-sm hover:bg-gray-50">
            Impact type
            <ChevronDown size={16} />
          </button>
          <button className="flex items-center gap-2 px-3 py-2 bg-white border border-content-border rounded-lg text-sm hover:bg-gray-50">
            Updated
            <ChevronDown size={16} />
          </button>
        </div>
        <button
          onClick={onRefresh}
          className="flex items-center gap-2 px-3 py-2 bg-white border border-content-border rounded-lg text-sm hover:bg-gray-50"
        >
          <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Table */}
      <table className="w-full">
        <thead>
          <tr className="border-b border-content-border">
            <th className="text-left px-6 py-4 text-sm font-medium text-gray-500">Entity</th>
            <th className="text-left px-6 py-4 text-sm font-medium text-gray-500">Category</th>
            <th className="text-left px-6 py-4 text-sm font-medium text-gray-500">Impact type</th>
            <th className="text-left px-6 py-4 text-sm font-medium text-gray-500">Updated</th>
            <th className="w-12"></th>
          </tr>
        </thead>
        <tbody>
          {data.map((entity) => (
            <tr
              key={entity.id}
              className="border-b border-content-border last:border-b-0 hover:bg-gray-50 transition-colors cursor-pointer"
            >
              <td className="px-6 py-4">
                <span className="text-gray-900 font-medium hover:text-accent-primary">
                  {entity.name}
                </span>
              </td>
              <td className="px-6 py-4">
                <EntityBadge type={entity.category} size="small" />
              </td>
              <td className="px-6 py-4">
                <span className="inline-block px-2.5 py-1 bg-gray-100 text-gray-700 rounded text-sm">
                  {entity.impactType}
                </span>
              </td>
              <td className="px-6 py-4 text-gray-500">
                {formatDate(entity.updatedAt, 'dd MMMM yyyy')}
              </td>
              <td className="px-6 py-4">
                <button className="p-1 text-gray-400 hover:text-gray-600">
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                    <circle cx="8" cy="3" r="1.5" />
                    <circle cx="8" cy="8" r="1.5" />
                    <circle cx="8" cy="13" r="1.5" />
                  </svg>
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {data.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          No entities found
        </div>
      )}
    </div>
  )
}

export default EntityTable
