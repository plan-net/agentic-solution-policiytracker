import { MoreVertical, FileText, Calendar, Trash2, Play } from 'lucide-react'
import { useState } from 'react'
import StatusBadge from '../common/StatusBadge'
import { formatDate } from '../../utils/formatters'

function ReportCard({
  report,
  onClick,
  onDelete,
  onGenerate,
}) {
  const [showMenu, setShowMenu] = useState(false)

  const handleMenuClick = (e) => {
    e.stopPropagation()
    setShowMenu(!showMenu)
  }

  const handleDelete = (e) => {
    e.stopPropagation()
    setShowMenu(false)
    if (onDelete) {
      onDelete(report.report_id)
    }
  }

  const handleGenerate = (e) => {
    e.stopPropagation()
    setShowMenu(false)
    if (onGenerate) {
      onGenerate(report.report_id)
    }
  }

  // Get report type display label
  const getReportTypeLabel = (type) => {
    const labels = {
      weekly: 'Weekly',
      daily: 'Daily',
      deep_dive: 'Deep Dive',
      spotlight: 'Spotlight',
    }
    return labels[type] || type
  }

  return (
    <tr
      onClick={onClick}
      className="border-b border-content-border last:border-b-0 hover:bg-gray-50 transition-colors cursor-pointer"
    >
      <td className="px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gray-100 rounded-lg">
            <FileText size={18} className="text-gray-600" />
          </div>
          <div>
            <div className="font-medium text-gray-900">{report.title}</div>
            {report.date_range_start && report.date_range_end && (
              <div className="text-sm text-gray-500 flex items-center gap-1 mt-0.5">
                <Calendar size={12} />
                {formatDate(report.date_range_start, 'dd.MM')} - {formatDate(report.date_range_end, 'dd.MM.yy')}
              </div>
            )}
          </div>
        </div>
      </td>
      <td className="px-6 py-4">
        <span className="text-sm text-gray-600 bg-gray-100 px-2 py-1 rounded">
          {getReportTypeLabel(report.report_type)}
        </span>
      </td>
      <td className="px-6 py-4">
        <StatusBadge status={report.status} />
      </td>
      <td className="px-6 py-4 text-gray-500">
        {formatDate(report.updated_at, 'dd MMMM yyyy')}
      </td>
      <td className="px-6 py-4">
        <div className="relative">
          <button
            onClick={handleMenuClick}
            className="p-1 text-gray-400 hover:text-gray-600 rounded hover:bg-gray-100"
          >
            <MoreVertical size={16} />
          </button>

          {showMenu && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setShowMenu(false)}
              />
              <div className="absolute right-0 top-8 z-20 bg-white border border-gray-200 rounded-lg shadow-lg py-1 min-w-[140px]">
                {report.status === 'pending' && (
                  <button
                    onClick={handleGenerate}
                    className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                  >
                    <Play size={14} />
                    Generate
                  </button>
                )}
                <button
                  onClick={handleDelete}
                  className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
                >
                  <Trash2 size={14} />
                  Delete
                </button>
              </div>
            </>
          )}
        </div>
      </td>
    </tr>
  )
}

export default ReportCard
