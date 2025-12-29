import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, RefreshCw, Plus, ChevronDown, Trash2, Play, FileText } from 'lucide-react'
import StatusBadge from '../components/common/StatusBadge'
import { formatDate } from '../utils/formatters'
import { useUIStore } from '../stores/uiStore'
import {
  listAssessments,
  createAssessment,
  deleteAssessment,
  runAssessment,
} from '../services/assessmentsApi'

function AssessmentsPage() {
  const navigate = useNavigate()
  const { setRecentAssessments } = useUIStore()
  const [assessments, setAssessments] = useState([])
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [typeFilter, setTypeFilter] = useState('all')
  const [isLoading, setIsLoading] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [showNewModal, setShowNewModal] = useState(false)
  const [error, setError] = useState(null)
  const [showStatusDropdown, setShowStatusDropdown] = useState(false)
  const [showTypeDropdown, setShowTypeDropdown] = useState(false)

  // Fetch assessments from API
  const fetchAssessments = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    const result = await listAssessments({
      limit: 100,
      status: statusFilter !== 'all' ? statusFilter : null,
      assessmentType: typeFilter !== 'all' ? typeFilter : null,
    })

    if (result.success) {
      setAssessments(result.data || [])
    } else {
      setError(result.error || 'Failed to load assessments')
      setAssessments([])
    }

    setIsLoading(false)
  }, [statusFilter, typeFilter])

  // Load assessments on mount and when filters change
  useEffect(() => {
    fetchAssessments()
  }, [fetchAssessments])

  // Update sidebar recent assessments
  useEffect(() => {
    setRecentAssessments(assessments.slice(0, 7))
  }, [assessments, setRecentAssessments])

  // Filter assessments by search query (client-side)
  const filteredAssessments = assessments.filter((assessment) => {
    const matchesSearch = assessment.title.toLowerCase().includes(searchQuery.toLowerCase())
    return matchesSearch
  })

  const handleRefresh = () => {
    fetchAssessments()
  }

  const handleCreateAssessment = async (data) => {
    setIsCreating(true)
    const result = await createAssessment(data)

    if (result.success) {
      setShowNewModal(false)
      // Refresh the list to show the new assessment
      fetchAssessments()
    } else {
      setError(result.error || 'Failed to create assessment')
    }

    setIsCreating(false)
  }

  const handleDeleteAssessment = async (assessmentId) => {
    if (!window.confirm('Are you sure you want to delete this assessment?')) {
      return
    }

    const result = await deleteAssessment(assessmentId)

    if (result.success) {
      // Remove from local state
      setAssessments((prev) => prev.filter((a) => a.assessment_id !== assessmentId))
    } else {
      setError(result.error || 'Failed to delete assessment')
    }
  }

  const handleRunAssessment = async (assessmentId, e) => {
    e.stopPropagation()
    const result = await runAssessment(assessmentId)

    if (result.success) {
      // Refresh to show updated status
      fetchAssessments()
    } else {
      setError(result.error || 'Failed to start assessment')
    }
  }

  const statusOptions = [
    { value: 'all', label: 'All Statuses' },
    { value: 'pending', label: 'Pending' },
    { value: 'working', label: 'Working' },
    { value: 'complete', label: 'Complete' },
    { value: 'ready', label: 'Ready' },
    { value: 'failed', label: 'Failed' },
  ]

  const typeOptions = [
    { value: 'all', label: 'All Types' },
    { value: 'monitoring', label: 'Monitoring' },
    { value: 'daily_focus', label: 'Daily Focus' },
    { value: 'deep_dive', label: 'Deep Dive' },
    { value: 'spotlight', label: 'Spotlight' },
    { value: 'custom', label: 'Custom' },
  ]

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Assessments</h1>
        <button
          onClick={() => setShowNewModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-sidebar-bg text-white rounded-lg hover:bg-gray-800 transition-colors"
        >
          <Plus size={18} />
          New Assessment
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
            placeholder="Search for an Assessment..."
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

      {/* Assessments Table */}
      <div className="bg-white rounded-xl border border-content-border overflow-hidden">
        {isLoading && assessments.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <RefreshCw size={24} className="animate-spin mx-auto mb-2" />
            Loading assessments...
          </div>
        ) : filteredAssessments.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <FileText size={48} className="mx-auto mb-4 text-gray-300" />
            <p className="text-lg font-medium text-gray-600 mb-2">No assessments found</p>
            <p className="text-gray-500 mb-4">
              {searchQuery || statusFilter !== 'all' || typeFilter !== 'all'
                ? 'Try adjusting your search or filters'
                : 'Create your first assessment to get started'}
            </p>
            {!searchQuery && statusFilter === 'all' && typeFilter === 'all' && (
              <button
                onClick={() => setShowNewModal(true)}
                className="inline-flex items-center gap-2 px-4 py-2 bg-sidebar-bg text-white rounded-lg hover:bg-gray-800 transition-colors"
              >
                <Plus size={18} />
                Create Assessment
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
                <th className="w-24"></th>
              </tr>
            </thead>
            <tbody>
              {filteredAssessments.map((assessment) => (
                <tr
                  key={assessment.assessment_id}
                  className="border-b border-content-border last:border-b-0 hover:bg-gray-50 transition-colors cursor-pointer"
                  onClick={() => navigate(`/assessments/${assessment.assessment_id}`)}
                >
                  <td className="px-6 py-4">
                    <span className="text-gray-900 hover:text-accent-primary underline-offset-2 hover:underline">
                      {assessment.title}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-sm text-gray-600 capitalize">
                      {(assessment.assessment_type || 'custom').replace('_', ' ')}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <StatusBadge status={assessment.status} />
                  </td>
                  <td className="px-6 py-4 text-gray-500">
                    {formatDate(assessment.updated_at, 'dd MMMM yyyy')}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      {assessment.status === 'pending' && (
                        <button
                          className="p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded transition-colors"
                          onClick={(e) => handleRunAssessment(assessment.assessment_id, e)}
                          title="Run Assessment"
                        >
                          <Play size={16} />
                        </button>
                      )}
                      <button
                        className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDeleteAssessment(assessment.assessment_id)
                        }}
                        title="Delete"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* New Assessment Modal */}
      <NewAssessmentModal
        isOpen={showNewModal}
        onClose={() => setShowNewModal(false)}
        onSubmit={handleCreateAssessment}
        isLoading={isCreating}
      />
    </div>
  )
}

// New Assessment Modal Component
function NewAssessmentModal({ isOpen, onClose, onSubmit, isLoading }) {
  const [title, setTitle] = useState('')
  const [prompt, setPrompt] = useState('')
  const [assessmentType, setAssessmentType] = useState('custom')
  const [includeWebResearch, setIncludeWebResearch] = useState(false)

  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit({
      title,
      prompt,
      assessment_type: assessmentType,
      include_web_research: includeWebResearch,
    })
  }

  const resetForm = () => {
    setTitle('')
    setPrompt('')
    setAssessmentType('custom')
    setIncludeWebResearch(false)
  }

  const handleClose = () => {
    resetForm()
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg">
        <div className="p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">New Assessment</h2>
          <p className="text-gray-500 text-sm mb-6">
            Fill out the form below to start a new assessment. You can optionally upload additional
            files to provide context. The assessment process may take up to 60 minutes to complete.
          </p>

          <form onSubmit={handleSubmit}>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Assessment title <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="eg. Monitoring Weeks 32 + 33"
                  className="w-full px-4 py-2 border border-content-border rounded-lg focus:border-accent-primary focus:ring-1 focus:ring-accent-primary focus:outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Assessment Type
                </label>
                <select
                  value={assessmentType}
                  onChange={(e) => setAssessmentType(e.target.value)}
                  className="w-full px-4 py-2 border border-content-border rounded-lg focus:border-accent-primary focus:ring-1 focus:ring-accent-primary focus:outline-none"
                >
                  <option value="custom">Custom</option>
                  <option value="monitoring">Monitoring</option>
                  <option value="daily_focus">Daily Focus</option>
                  <option value="deep_dive">Deep Dive</option>
                  <option value="spotlight">Spotlight</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Question/Prompt <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="eg. Create a weekly assessment covering politics, policy, and technology."
                  rows={4}
                  className="w-full px-4 py-2 border border-content-border rounded-lg focus:border-accent-primary focus:ring-1 focus:ring-accent-primary focus:outline-none resize-none"
                  required
                />
              </div>

              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={includeWebResearch}
                  onChange={(e) => setIncludeWebResearch(e.target.checked)}
                  className="w-4 h-4 rounded border-gray-300 text-accent-primary focus:ring-accent-primary"
                />
                <span className="text-sm text-gray-700">Compile additional web research?</span>
              </label>

              <div className="grid grid-cols-2 gap-4 pt-2">
                <button
                  type="button"
                  className="flex items-center justify-center gap-2 px-4 py-3 bg-content-bgAlt rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-200 transition-colors"
                >
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M8 1v10M4 5l4-4 4 4M1 14h14" />
                  </svg>
                  Add files
                </button>
                <button
                  type="button"
                  className="flex items-center justify-center gap-2 px-4 py-3 bg-content-bgAlt rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-200 transition-colors"
                >
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M2 4h12M2 8h12M2 12h8" />
                  </svg>
                  General requirements
                </button>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 mt-6 pt-4 border-t border-content-border">
              <button
                type="button"
                onClick={handleClose}
                className="px-4 py-2 text-sm font-medium text-red-600 hover:text-red-700"
                disabled={isLoading}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isLoading || !title.trim() || !prompt.trim()}
                className="flex items-center gap-2 px-4 py-2 bg-sidebar-bg text-white rounded-lg text-sm font-medium hover:bg-gray-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <>
                    <RefreshCw size={14} className="animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M1 7l4 4 8-8" />
                    </svg>
                    Submit
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

export default AssessmentsPage
