import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, RefreshCw, Plus, ChevronDown } from 'lucide-react'
import StatusBadge from '../components/common/StatusBadge'
import { formatDate } from '../utils/formatters'
import { useUIStore } from '../stores/uiStore'

// Mock data - will be replaced with API
const mockAssessments = [
  {
    id: 'assess_1',
    title: 'Monitoring Weeks 32 + 33 (04.08—15.08.25)',
    status: 'complete',
    updatedAt: '2025-08-15',
  },
  {
    id: 'assess_2',
    title: 'Monitoring Weeks 30 + 31 (21.07—03.08.25)',
    status: 'complete',
    updatedAt: '2025-08-05',
  },
  {
    id: 'assess_3',
    title: 'Daily Focus: 04.08.25',
    status: 'working',
    updatedAt: '2025-08-04',
  },
  {
    id: 'assess_4',
    title: 'Monitoring Weeks 28 + 29 (07.07—20.07.25)',
    status: 'working',
    updatedAt: '2025-07-21',
  },
  {
    id: 'assess_5',
    title: 'Deep Dive: Outlier Events Across July',
    status: 'ready',
    updatedAt: '2025-07-21',
  },
  {
    id: 'assess_6',
    title: 'Monitoring Weeks 26 + 27 (23.06—06.07.25)',
    status: 'complete',
    updatedAt: '2025-07-08',
  },
  {
    id: 'assess_7',
    title: 'Spotlight Day: 07.08.25',
    status: 'complete',
    updatedAt: '2025-07-07',
  },
  {
    id: 'assess_8',
    title: 'Monitoring Weeks 24 + 25 (09.06—22.06.25)',
    status: 'complete',
    updatedAt: '2025-06-23',
  },
]

function AssessmentsPage() {
  const navigate = useNavigate()
  const { setRecentAssessments } = useUIStore()
  const [assessments, setAssessments] = useState(mockAssessments)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [isLoading, setIsLoading] = useState(false)
  const [showNewModal, setShowNewModal] = useState(false)

  // Update sidebar recent assessments
  useEffect(() => {
    setRecentAssessments(assessments.slice(0, 7))
  }, [assessments, setRecentAssessments])

  // Filter assessments
  const filteredAssessments = assessments.filter((assessment) => {
    const matchesSearch = assessment.title.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus = statusFilter === 'all' || assessment.status === statusFilter
    return matchesSearch && matchesStatus
  })

  const handleRefresh = async () => {
    setIsLoading(true)
    // TODO: Fetch from API
    setTimeout(() => setIsLoading(false), 1000)
  }

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
            <button className="flex items-center gap-2 px-3 py-2 bg-white border border-content-border rounded-lg text-sm hover:bg-gray-50">
              Status
              <ChevronDown size={16} />
            </button>
            <button className="flex items-center gap-2 px-3 py-2 bg-white border border-content-border rounded-lg text-sm hover:bg-gray-50">
              Date
              <ChevronDown size={16} />
            </button>
          </div>
          <button
            onClick={handleRefresh}
            className="flex items-center gap-2 px-3 py-2 bg-white border border-content-border rounded-lg text-sm hover:bg-gray-50"
          >
            <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Assessments Table */}
      <div className="bg-white rounded-xl border border-content-border overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-content-border">
              <th className="text-left px-6 py-4 text-sm font-medium text-gray-500">Name</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-gray-500">Status</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-gray-500">Updated</th>
              <th className="w-12"></th>
            </tr>
          </thead>
          <tbody>
            {filteredAssessments.map((assessment) => (
              <tr
                key={assessment.id}
                className="border-b border-content-border last:border-b-0 hover:bg-gray-50 transition-colors cursor-pointer"
                onClick={() => navigate(`/assessments/${assessment.id}`)}
              >
                <td className="px-6 py-4">
                  <span className="text-gray-900 hover:text-accent-primary underline-offset-2 hover:underline">
                    {assessment.title}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <StatusBadge status={assessment.status} />
                </td>
                <td className="px-6 py-4 text-gray-500">
                  {formatDate(assessment.updatedAt, 'dd MMMM yyyy')}
                </td>
                <td className="px-6 py-4">
                  <button
                    className="p-1 text-gray-400 hover:text-gray-600"
                    onClick={(e) => e.stopPropagation()}
                  >
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

        {filteredAssessments.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            No assessments found matching your criteria
          </div>
        )}
      </div>

      {/* New Assessment Modal */}
      {showNewModal && (
        <NewAssessmentModal onClose={() => setShowNewModal(false)} />
      )}
    </div>
  )
}

// New Assessment Modal Component
function NewAssessmentModal({ onClose }) {
  const [title, setTitle] = useState('')
  const [prompt, setPrompt] = useState('')
  const [includeWebResearch, setIncludeWebResearch] = useState(false)

  const handleSubmit = (e) => {
    e.preventDefault()
    // TODO: Call API to create assessment
    console.log('Creating assessment:', { title, prompt, includeWebResearch })
    onClose()
  }

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
                  placeholder="eg. New policies"
                  className="w-full px-4 py-2 border border-content-border rounded-lg focus:border-accent-primary focus:ring-1 focus:ring-accent-primary focus:outline-none"
                  required
                />
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
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-red-600 hover:text-red-700"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex items-center gap-2 px-4 py-2 bg-sidebar-bg text-white rounded-lg text-sm font-medium hover:bg-gray-800 transition-colors"
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M1 7l4 4 8-8" />
                </svg>
                Submit
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

export default AssessmentsPage
