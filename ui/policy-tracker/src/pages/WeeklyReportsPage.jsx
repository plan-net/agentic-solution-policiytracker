import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, RefreshCw, Plus, ChevronDown, FileText } from 'lucide-react'
import ReportCard from '../components/reports/ReportCard'
import GenerateReportModal from '../components/reports/GenerateReportModal'
import { listReports, createReport, deleteReport, generateReport } from '../services/reportsApi'

function WeeklyReportsPage() {
  const navigate = useNavigate()
  const [reports, setReports] = useState([])
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [typeFilter, setTypeFilter] = useState('all')
  const [isLoading, setIsLoading] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [showNewReportModal, setShowNewReportModal] = useState(false)
  const [error, setError] = useState(null)
  const [showStatusDropdown, setShowStatusDropdown] = useState(false)
  const [showTypeDropdown, setShowTypeDropdown] = useState(false)

  // Fetch reports from API
  const fetchReports = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    const result = await listReports({
      limit: 100,
      status: statusFilter !== 'all' ? statusFilter : null,
      reportType: typeFilter !== 'all' ? typeFilter : null,
    })

    if (result.success) {
      setReports(result.data || [])
    } else {
      setError(result.error || 'Failed to load reports')
      setReports([])
    }

    setIsLoading(false)
  }, [statusFilter, typeFilter])

  // Load reports on mount and when filters change
  useEffect(() => {
    fetchReports()
  }, [fetchReports])

  // Filter reports by search query (client-side)
  const filteredReports = reports.filter((report) => {
    const matchesSearch = report.title.toLowerCase().includes(searchQuery.toLowerCase())
    return matchesSearch
  })

  const handleRefresh = () => {
    fetchReports()
  }

  const handleCreateReport = async (data) => {
    setIsCreating(true)
    const result = await createReport(data)

    if (result.success) {
      setShowNewReportModal(false)
      // Refresh the list to show the new report
      fetchReports()
    } else {
      setError(result.error || 'Failed to create report')
    }

    setIsCreating(false)
  }

  const handleDeleteReport = async (reportId) => {
    if (!window.confirm('Are you sure you want to delete this report?')) {
      return
    }

    const result = await deleteReport(reportId)

    if (result.success) {
      // Remove from local state
      setReports((prev) => prev.filter((r) => r.report_id !== reportId))
    } else {
      setError(result.error || 'Failed to delete report')
    }
  }

  const handleGenerateReport = async (reportId) => {
    const result = await generateReport(reportId)

    if (result.success) {
      // Refresh to show updated status
      fetchReports()
    } else {
      setError(result.error || 'Failed to start report generation')
    }
  }

  const handleReportClick = (reportId) => {
    navigate(`/reports/${reportId}`)
  }

  const statusOptions = [
    { value: 'all', label: 'All Statuses' },
    { value: 'pending', label: 'Pending' },
    { value: 'working', label: 'Working' },
    { value: 'complete', label: 'Complete' },
    { value: 'failed', label: 'Failed' },
  ]

  const typeOptions = [
    { value: 'all', label: 'All Types' },
    { value: 'weekly', label: 'Weekly' },
    { value: 'daily', label: 'Daily' },
    { value: 'deep_dive', label: 'Deep Dive' },
    { value: 'spotlight', label: 'Spotlight' },
  ]

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Weekly Reports</h1>
        <button
          onClick={() => setShowNewReportModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-sidebar-bg text-white rounded-lg hover:bg-gray-800 transition-colors"
        >
          <Plus size={18} />
          New Report
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-4 px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-red-600">
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-2 text-red-400 hover:text-red-600"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Search and Filters */}
      <div className="mb-6">
        <div className="relative mb-4">
          <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search for a Report..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-11 pr-4 py-3 bg-white border border-content-border rounded-xl focus:border-accent-primary focus:ring-1 focus:ring-accent-primary focus:outline-none"
          />
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Status Filter */}
            <div className="relative">
              <button
                onClick={() => {
                  setShowStatusDropdown(!showStatusDropdown)
                  setShowTypeDropdown(false)
                }}
                className="flex items-center gap-2 px-3 py-2 bg-white border border-content-border rounded-lg text-sm hover:bg-gray-50"
              >
                {statusOptions.find((o) => o.value === statusFilter)?.label || 'Status'}
                <ChevronDown size={16} />
              </button>
              {showStatusDropdown && (
                <>
                  <div
                    className="fixed inset-0 z-10"
                    onClick={() => setShowStatusDropdown(false)}
                  />
                  <div className="absolute top-full mt-1 left-0 z-20 bg-white border border-gray-200 rounded-lg shadow-lg py-1 min-w-[140px]">
                    {statusOptions.map((option) => (
                      <button
                        key={option.value}
                        onClick={() => {
                          setStatusFilter(option.value)
                          setShowStatusDropdown(false)
                        }}
                        className={`
                          w-full px-4 py-2 text-left text-sm hover:bg-gray-50
                          ${statusFilter === option.value ? 'text-accent-primary font-medium' : 'text-gray-700'}
                        `}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>

            {/* Type Filter */}
            <div className="relative">
              <button
                onClick={() => {
                  setShowTypeDropdown(!showTypeDropdown)
                  setShowStatusDropdown(false)
                }}
                className="flex items-center gap-2 px-3 py-2 bg-white border border-content-border rounded-lg text-sm hover:bg-gray-50"
              >
                {typeOptions.find((o) => o.value === typeFilter)?.label || 'Type'}
                <ChevronDown size={16} />
              </button>
              {showTypeDropdown && (
                <>
                  <div
                    className="fixed inset-0 z-10"
                    onClick={() => setShowTypeDropdown(false)}
                  />
                  <div className="absolute top-full mt-1 left-0 z-20 bg-white border border-gray-200 rounded-lg shadow-lg py-1 min-w-[140px]">
                    {typeOptions.map((option) => (
                      <button
                        key={option.value}
                        onClick={() => {
                          setTypeFilter(option.value)
                          setShowTypeDropdown(false)
                        }}
                        className={`
                          w-full px-4 py-2 text-left text-sm hover:bg-gray-50
                          ${typeFilter === option.value ? 'text-accent-primary font-medium' : 'text-gray-700'}
                        `}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>

          <button
            onClick={handleRefresh}
            disabled={isLoading}
            className="flex items-center gap-2 px-3 py-2 bg-white border border-content-border rounded-lg text-sm hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Reports Table */}
      <div className="bg-white rounded-xl border border-content-border overflow-hidden">
        {isLoading && reports.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <RefreshCw size={24} className="animate-spin mx-auto mb-2" />
            Loading reports...
          </div>
        ) : filteredReports.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <FileText size={48} className="mx-auto mb-4 text-gray-300" />
            <p className="text-lg font-medium text-gray-600 mb-2">No reports found</p>
            <p className="text-gray-500 mb-4">
              {searchQuery || statusFilter !== 'all' || typeFilter !== 'all'
                ? 'Try adjusting your search or filters'
                : 'Create your first report to get started'}
            </p>
            {!searchQuery && statusFilter === 'all' && typeFilter === 'all' && (
              <button
                onClick={() => setShowNewReportModal(true)}
                className="inline-flex items-center gap-2 px-4 py-2 bg-sidebar-bg text-white rounded-lg hover:bg-gray-800 transition-colors"
              >
                <Plus size={18} />
                Create Report
              </button>
            )}
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-content-border">
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-500">Name</th>
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-500">Type</th>
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-500">Status</th>
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-500">Updated</th>
                <th className="w-12"></th>
              </tr>
            </thead>
            <tbody>
              {filteredReports.map((report) => (
                <ReportCard
                  key={report.report_id}
                  report={report}
                  onClick={() => handleReportClick(report.report_id)}
                  onDelete={handleDeleteReport}
                  onGenerate={handleGenerateReport}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* New Report Modal */}
      <GenerateReportModal
        isOpen={showNewReportModal}
        onClose={() => setShowNewReportModal(false)}
        onSubmit={handleCreateReport}
        isLoading={isCreating}
      />
    </div>
  )
}

export default WeeklyReportsPage
