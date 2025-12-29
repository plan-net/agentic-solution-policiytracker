import { useState } from 'react'
import { X, Calendar, FileText, Loader2, Cpu } from 'lucide-react'

const reportTypes = [
  {
    id: 'weekly',
    label: 'Weekly Monitoring',
    description: 'Comprehensive weekly digest of political activities',
  },
  {
    id: 'daily',
    label: 'Daily Focus',
    description: 'Focused summary of a single day\'s events',
  },
  {
    id: 'deep_dive',
    label: 'Deep Dive',
    description: 'In-depth analysis of specific topics or patterns',
  },
  {
    id: 'spotlight',
    label: 'Spotlight',
    description: 'Highlight report for significant events',
  },
]

const claudeModels = [
  {
    id: 'claude-sonnet-4-20250514',
    label: 'Claude Sonnet 4',
    description: 'Fast & cost-effective (Recommended)',
    recommended: true,
  },
  {
    id: 'claude-opus-4-20250514',
    label: 'Claude Opus 4',
    description: 'Higher quality reasoning (Slower)',
    recommended: false,
  },
]

function GenerateReportModal({ isOpen, onClose, onSubmit, isLoading = false }) {
  const [title, setTitle] = useState('')
  const [reportType, setReportType] = useState('weekly')
  const [dateRangeStart, setDateRangeStart] = useState('')
  const [dateRangeEnd, setDateRangeEnd] = useState('')
  const [claudeModel, setClaudeModel] = useState('claude-sonnet-4-20250514')
  const [includeEvents, setIncludeEvents] = useState(true)

  // Set default dates based on report type
  const setDefaultDates = (type) => {
    const today = new Date()
    const formatDate = (d) => d.toISOString().split('T')[0]

    if (type === 'weekly') {
      // Last 2 weeks
      const start = new Date(today)
      start.setDate(start.getDate() - 14)
      setDateRangeStart(formatDate(start))
      setDateRangeEnd(formatDate(today))
    } else if (type === 'daily') {
      // Yesterday
      const yesterday = new Date(today)
      yesterday.setDate(yesterday.getDate() - 1)
      setDateRangeStart(formatDate(yesterday))
      setDateRangeEnd(formatDate(yesterday))
    } else {
      // Last month
      const start = new Date(today)
      start.setMonth(start.getMonth() - 1)
      setDateRangeStart(formatDate(start))
      setDateRangeEnd(formatDate(today))
    }
  }

  const handleTypeChange = (type) => {
    setReportType(type)
    setDefaultDates(type)
  }

  const handleSubmit = (e) => {
    e.preventDefault()

    if (!title.trim()) {
      return
    }

    onSubmit({
      title: title.trim(),
      report_type: reportType,
      date_range_start: dateRangeStart || null,
      date_range_end: dateRangeEnd || null,
      claude_model: claudeModel,
      include_events: includeEvents,
      options: {},
    })
  }

  const handleClose = () => {
    // Reset form
    setTitle('')
    setReportType('weekly')
    setDateRangeStart('')
    setDateRangeEnd('')
    setClaudeModel('claude-sonnet-4-20250514')
    setIncludeEvents(true)
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="relative bg-white rounded-xl shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-accent-primary to-accent-secondary rounded-lg">
              <FileText size={20} className="text-white" />
            </div>
            <h2 className="text-xl font-semibold text-gray-900">New Report</h2>
          </div>
          <button
            onClick={handleClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Title */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Report Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., Monitoring Weeks 30 + 31"
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:border-accent-primary focus:ring-1 focus:ring-accent-primary focus:outline-none"
              required
            />
          </div>

          {/* Report Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Report Type
            </label>
            <div className="grid grid-cols-2 gap-3">
              {reportTypes.map((type) => (
                <button
                  key={type.id}
                  type="button"
                  onClick={() => handleTypeChange(type.id)}
                  className={`
                    p-3 rounded-lg border-2 text-left transition-all
                    ${reportType === type.id
                      ? 'border-accent-primary bg-accent-primary/5'
                      : 'border-gray-200 hover:border-gray-300'
                    }
                  `}
                >
                  <div className={`font-medium ${reportType === type.id ? 'text-accent-primary' : 'text-gray-900'}`}>
                    {type.label}
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    {type.description}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Date Range */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <Calendar size={14} className="inline mr-1" />
              Date Range
            </label>
            <div className="flex items-center gap-3">
              <input
                type="date"
                value={dateRangeStart}
                onChange={(e) => setDateRangeStart(e.target.value)}
                className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg focus:border-accent-primary focus:ring-1 focus:ring-accent-primary focus:outline-none"
              />
              <span className="text-gray-400">to</span>
              <input
                type="date"
                value={dateRangeEnd}
                onChange={(e) => setDateRangeEnd(e.target.value)}
                className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg focus:border-accent-primary focus:ring-1 focus:ring-accent-primary focus:outline-none"
              />
            </div>
          </div>

          {/* Claude Model Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <Cpu size={14} className="inline mr-1" />
              AI Model
            </label>
            <div className="grid grid-cols-2 gap-3">
              {claudeModels.map((model) => (
                <button
                  key={model.id}
                  type="button"
                  onClick={() => setClaudeModel(model.id)}
                  className={`
                    p-3 rounded-lg border-2 text-left transition-all
                    ${claudeModel === model.id
                      ? 'border-accent-primary bg-accent-primary/5'
                      : 'border-gray-200 hover:border-gray-300'
                    }
                  `}
                >
                  <div className={`font-medium ${claudeModel === model.id ? 'text-accent-primary' : 'text-gray-900'}`}>
                    {model.label}
                    {model.recommended && (
                      <span className="ml-1 text-xs text-green-600 font-normal">★</span>
                    )}
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    {model.description}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Include Events Checkbox */}
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="includeEvents"
              checked={includeEvents}
              onChange={(e) => setIncludeEvents(e.target.checked)}
              className="w-4 h-4 text-accent-primary border-gray-300 rounded focus:ring-accent-primary"
            />
            <label htmlFor="includeEvents" className="text-sm text-gray-700">
              Include forward-looking events (next 30-90 days)
            </label>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200">
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              disabled={isLoading}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!title.trim() || isLoading}
              className={`
                px-6 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors
                ${!title.trim() || isLoading
                  ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                  : 'bg-sidebar-bg text-white hover:bg-gray-800'
                }
              `}
            >
              {isLoading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Creating...
                </>
              ) : (
                'Create Report'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default GenerateReportModal
