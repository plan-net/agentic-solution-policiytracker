import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, RefreshCw, Play, Calendar, Clock, Cpu, FileText, CheckCircle, XCircle, Loader2 } from 'lucide-react'
import { MarkdownRenderer } from '../components/rich-content'
import { getReport, generateReport } from '../services/reportsApi'

const statusConfig = {
  pending: {
    label: 'Pending',
    icon: Clock,
    color: 'text-gray-500',
    bgColor: 'bg-gray-100',
  },
  working: {
    label: 'Working',
    icon: Loader2,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    animate: true,
  },
  complete: {
    label: 'Complete',
    icon: CheckCircle,
    color: 'text-green-600',
    bgColor: 'bg-green-50',
  },
  failed: {
    label: 'Failed',
    icon: XCircle,
    color: 'text-red-600',
    bgColor: 'bg-red-50',
  },
}

function ReportDetailPage() {
  const { reportId } = useParams()
  const navigate = useNavigate()
  const [report, setReport] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError] = useState(null)

  const fetchReport = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    const result = await getReport(reportId)

    if (result.success) {
      setReport(result.data)
    } else {
      setError(result.error || 'Failed to load report')
    }

    setIsLoading(false)
  }, [reportId])

  useEffect(() => {
    fetchReport()
  }, [fetchReport])

  // Auto-refresh while report is working
  useEffect(() => {
    if (report?.status === 'working') {
      const interval = setInterval(fetchReport, 5000) // Refresh every 5 seconds
      return () => clearInterval(interval)
    }
  }, [report?.status, fetchReport])

  const handleGenerate = async () => {
    setIsGenerating(true)
    const result = await generateReport(reportId)

    if (result.success) {
      // Refresh to show updated status
      fetchReport()
    } else {
      setError(result.error || 'Failed to start report generation')
    }

    setIsGenerating(false)
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A'
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
    } catch {
      return dateStr
    }
  }

  const formatDateTime = (dateStr) => {
    if (!dateStr) return 'N/A'
    try {
      return new Date(dateStr).toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return dateStr
    }
  }

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="flex items-center justify-center py-20">
          <RefreshCw size={32} className="animate-spin text-gray-400" />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-8">
        <button
          onClick={() => navigate('/reports')}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
        >
          <ArrowLeft size={20} />
          Back to Reports
        </button>
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <XCircle size={48} className="mx-auto mb-4 text-red-400" />
          <p className="text-red-600 font-medium">{error}</p>
          <button
            onClick={fetchReport}
            className="mt-4 px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  if (!report) {
    return (
      <div className="p-8">
        <button
          onClick={() => navigate('/reports')}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
        >
          <ArrowLeft size={20} />
          Back to Reports
        </button>
        <div className="text-center py-20 text-gray-500">
          Report not found
        </div>
      </div>
    )
  }

  const status = statusConfig[report.status] || statusConfig.pending
  const StatusIcon = status.icon
  const metadata = report.sections?.find(s => s.type === 'metadata') || {}

  return (
    <div className="p-8 max-w-5xl">
      {/* Back button */}
      <button
        onClick={() => navigate('/reports')}
        className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
      >
        <ArrowLeft size={20} />
        Back to Reports
      </button>

      {/* Header */}
      <div className="bg-white rounded-xl border border-content-border p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-gradient-to-br from-accent-primary to-accent-secondary rounded-lg">
              <FileText size={24} className="text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{report.title}</h1>
              <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                <span className="capitalize">{report.report_type?.replace('_', ' ')} Report</span>
                {report.date_range_start && report.date_range_end && (
                  <>
                    <span>|</span>
                    <span className="flex items-center gap-1">
                      <Calendar size={14} />
                      {formatDate(report.date_range_start)} - {formatDate(report.date_range_end)}
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Status Badge */}
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${status.bgColor}`}>
            <StatusIcon size={16} className={`${status.color} ${status.animate ? 'animate-spin' : ''}`} />
            <span className={`text-sm font-medium ${status.color}`}>{status.label}</span>
          </div>
        </div>

        {/* Metadata row */}
        <div className="flex items-center gap-6 text-sm text-gray-500 border-t border-gray-100 pt-4">
          <span className="flex items-center gap-1">
            <Clock size={14} />
            Updated: {formatDateTime(report.updated_at)}
          </span>
          {metadata.model && (
            <span className="flex items-center gap-1">
              <Cpu size={14} />
              {metadata.model?.includes('opus') ? 'Claude Opus 4' : 'Claude Sonnet 4'}
            </span>
          )}
          {metadata.turns && (
            <span>Turns: {metadata.turns}</span>
          )}
          {metadata.tool_calls_count && (
            <span>Tool Calls: {metadata.tool_calls_count}</span>
          )}
        </div>

        {/* Action buttons */}
        {(report.status === 'pending' || report.status === 'failed') && (
          <div className="mt-4 pt-4 border-t border-gray-100">
            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="flex items-center gap-2 px-4 py-2 bg-sidebar-bg text-white rounded-lg hover:bg-gray-800 disabled:opacity-50"
            >
              {isGenerating ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Starting...
                </>
              ) : (
                <>
                  <Play size={16} />
                  Generate Report
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {/* Report Content */}
      <div className="bg-white rounded-xl border border-content-border p-6">
        {report.status === 'working' ? (
          <div className="text-center py-12">
            <Loader2 size={48} className="animate-spin mx-auto mb-4 text-blue-500" />
            <p className="text-lg font-medium text-gray-700">Generating Report...</p>
            <p className="text-gray-500 mt-2">This may take a few minutes. The page will auto-refresh.</p>
          </div>
        ) : report.status === 'pending' ? (
          <div className="text-center py-12 text-gray-500">
            <FileText size={48} className="mx-auto mb-4 text-gray-300" />
            <p className="text-lg font-medium text-gray-600">Report Not Generated Yet</p>
            <p className="mt-2">Click "Generate Report" to start the AI-powered report generation.</p>
          </div>
        ) : report.status === 'failed' ? (
          <div className="text-center py-12">
            <XCircle size={48} className="mx-auto mb-4 text-red-400" />
            <p className="text-lg font-medium text-red-600">Report Generation Failed</p>
            <p className="text-gray-500 mt-2">Click "Generate Report" to try again.</p>
          </div>
        ) : report.content ? (
          <div className="prose prose-gray max-w-none">
            <MarkdownRenderer content={report.content} variant="report" />
          </div>
        ) : (
          <div className="text-center py-12 text-gray-500">
            <FileText size={48} className="mx-auto mb-4 text-gray-300" />
            <p>No content available</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default ReportDetailPage
