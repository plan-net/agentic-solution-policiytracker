import { useState, useEffect, useRef } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { ChevronLeft, Send, Paperclip, ThumbsUp, ThumbsDown, Sparkles, RefreshCw, Play, AlertCircle } from 'lucide-react'
import { useUIStore } from '../stores/uiStore'
import { getAssessment, runAssessment, sendAssessmentChat } from '../services/assessmentsApi'
import StatusBadge from '../components/common/StatusBadge'

function AssessmentDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { openSlideOutPanel } = useUIStore()
  const [assessment, setAssessment] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [inputValue, setInputValue] = useState('')
  const [isSending, setIsSending] = useState(false)
  const messagesEndRef = useRef(null)

  // Load assessment data
  useEffect(() => {
    loadAssessment()
  }, [id])

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [assessment?.messages])

  const loadAssessment = async () => {
    setIsLoading(true)
    setError(null)

    const result = await getAssessment(id)

    if (result.success) {
      setAssessment(result.data)
    } else {
      setError(result.error || 'Failed to load assessment')
    }

    setIsLoading(false)
  }

  const handleEntityClick = () => {
    if (assessment?.related_entity) {
      openSlideOutPanel(assessment.related_entity)
    }
  }

  const handleRunAssessment = async () => {
    const result = await runAssessment(id)
    if (result.success) {
      loadAssessment()
    } else {
      setError(result.error || 'Failed to start assessment')
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!inputValue.trim() || isSending) return

    setIsSending(true)

    const result = await sendAssessmentChat(id, inputValue.trim())

    if (result.success) {
      setInputValue('')
      // Update messages from response
      if (result.data?.messages) {
        setAssessment((prev) => ({
          ...prev,
          messages: result.data.messages,
        }))
      } else {
        // Refresh to get updated messages
        loadAssessment()
      }
    } else {
      setError(result.error || 'Failed to send message')
    }

    setIsSending(false)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <RefreshCw size={32} className="animate-spin mx-auto mb-4 text-gray-400" />
          <p className="text-gray-500">Loading assessment...</p>
        </div>
      </div>
    )
  }

  if (error && !assessment) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <AlertCircle size={48} className="mx-auto mb-4 text-red-400" />
          <p className="text-red-600 mb-4">{error}</p>
          <button
            onClick={() => navigate('/assessments')}
            className="px-4 py-2 bg-sidebar-bg text-white rounded-lg hover:bg-gray-800"
          >
            Back to Assessments
          </button>
        </div>
      </div>
    )
  }

  if (!assessment) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <p className="text-gray-500 mb-4">Assessment not found</p>
          <button
            onClick={() => navigate('/assessments')}
            className="px-4 py-2 bg-sidebar-bg text-white rounded-lg hover:bg-gray-800"
          >
            Back to Assessments
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen">
      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="border-b border-content-border bg-white px-6 py-4">
          <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
            <Link to="/assessments" className="hover:text-gray-700">
              Assessments
            </Link>
            <span>&gt;</span>
            <span>{assessment.title}</span>
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Link
                to="/assessments"
                className="p-1 hover:bg-gray-100 rounded transition-colors"
              >
                <ChevronLeft size={24} />
              </Link>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">{assessment.title}</h1>
                <div className="flex items-center gap-3 mt-1">
                  <StatusBadge status={assessment.status} />
                  <span className="text-sm text-gray-500 capitalize">
                    {(assessment.assessment_type || 'custom').replace('_', ' ')}
                  </span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {assessment.status === 'pending' && (
                <button
                  onClick={handleRunAssessment}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors"
                >
                  <Play size={16} />
                  Run Assessment
                </button>
              )}
              <button className="px-4 py-2 bg-sidebar-bg text-white rounded-lg text-sm font-medium hover:bg-gray-800 transition-colors">
                Generate report
              </button>
            </div>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mx-6 mt-4 px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-red-600">
            {error}
            <button
              onClick={() => setError(null)}
              className="ml-2 text-red-400 hover:text-red-600"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Insights Content */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-3xl">
            {/* Prompt Section */}
            {assessment.prompt && (
              <div className="mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
                <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
                  Assessment Prompt
                </div>
                <p className="text-gray-700">{assessment.prompt}</p>
              </div>
            )}

            {/* Insights */}
            {assessment.insights && assessment.insights.length > 0 ? (
              assessment.insights.map((insight) => (
                <div key={insight.id} className="mb-8">
                  <div className="flex items-center gap-2 text-accent-primary text-sm font-medium mb-3">
                    <Sparkles size={16} />
                    Agent insights
                  </div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">
                    {insight.title}
                  </h2>
                  <div className="space-y-4">
                    {insight.paragraphs.map((paragraph, idx) => (
                      <div key={idx}>
                        <p className="text-gray-700 leading-relaxed">{paragraph}</p>
                        <div className="flex items-center gap-2 mt-2">
                          <button className="p-1 text-gray-400 hover:text-gray-600 transition-colors">
                            <ThumbsUp size={14} />
                          </button>
                          <button className="p-1 text-gray-400 hover:text-gray-600 transition-colors">
                            <ThumbsDown size={14} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-12">
                {assessment.status === 'pending' ? (
                  <>
                    <div className="text-4xl mb-4">📋</div>
                    <p className="text-gray-500 mb-4">This assessment has not been run yet.</p>
                    <button
                      onClick={handleRunAssessment}
                      className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                    >
                      <Play size={16} />
                      Run Assessment
                    </button>
                  </>
                ) : assessment.status === 'working' ? (
                  <>
                    <RefreshCw size={32} className="animate-spin mx-auto mb-4 text-blue-500" />
                    <p className="text-gray-500">Assessment is being processed...</p>
                    <p className="text-sm text-gray-400 mt-2">This may take several minutes.</p>
                  </>
                ) : (
                  <>
                    <div className="text-4xl mb-4">📭</div>
                    <p className="text-gray-500">No insights available yet.</p>
                  </>
                )}
              </div>
            )}

            {/* Chat Messages */}
            {assessment.messages && assessment.messages.length > 0 && (
              <div className="mt-8 pt-8 border-t border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Follow-up Discussion</h3>
                <div className="space-y-4">
                  {assessment.messages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[80%] p-4 rounded-lg ${
                          message.role === 'user'
                            ? 'bg-sidebar-bg text-white'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        <p className="whitespace-pre-wrap">{message.content}</p>
                        {message.timestamp && (
                          <p className={`text-xs mt-2 ${message.role === 'user' ? 'text-gray-300' : 'text-gray-400'}`}>
                            {new Date(message.timestamp).toLocaleTimeString()}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Chat Input */}
        <div className="border-t border-content-border bg-white p-4">
          <form onSubmit={handleSubmit} className="max-w-3xl">
            <div className="relative">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Ask a follow-up question..."
                disabled={isSending}
                className="w-full px-4 py-3 pr-24 bg-content-bgAlt rounded-xl border border-content-border focus:border-accent-primary focus:ring-1 focus:ring-accent-primary focus:outline-none disabled:opacity-50"
              />
              <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-2">
                <button
                  type="button"
                  className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <Paperclip size={18} />
                </button>
                <button
                  type="submit"
                  disabled={!inputValue.trim() || isSending}
                  className={`
                    p-2 rounded-lg transition-colors
                    ${inputValue.trim() && !isSending
                      ? 'bg-sidebar-bg text-white hover:bg-gray-800'
                      : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                    }
                  `}
                >
                  {isSending ? (
                    <RefreshCw size={18} className="animate-spin" />
                  ) : (
                    <Send size={18} />
                  )}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>

      {/* Right Sidebar - Entity Details */}
      <div className="w-96 border-l border-content-border bg-white overflow-y-auto">
        <div className="p-4 border-b border-content-border">
          <div className="flex items-center gap-2 text-accent-primary text-sm font-medium">
            <Sparkles size={16} />
            Agent insights
          </div>
        </div>

        {assessment.related_entity ? (
          <div className="p-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">
              {assessment.related_entity.name}
            </h3>

            <span className="inline-block px-3 py-1 bg-entity-official text-white rounded text-sm font-medium mb-4">
              {assessment.related_entity.type}
            </span>

            {assessment.related_entity.description && (
              <p className="text-sm text-gray-600 leading-relaxed mb-6">
                {assessment.related_entity.description}
              </p>
            )}

            {assessment.related_entity.region && (
              <div className="mb-6">
                <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1">
                  Region / Jurisdiction
                </div>
                <div className="text-gray-700">{assessment.related_entity.region}</div>
              </div>
            )}

            {assessment.related_entity.focus_areas && assessment.related_entity.focus_areas.length > 0 && (
              <div className="mb-6">
                <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
                  Focus area
                </div>
                <ul className="space-y-1.5">
                  {assessment.related_entity.focus_areas.map((area, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                      <span className="w-2 h-2 rounded-full bg-amber-400 mt-1.5 flex-shrink-0" />
                      {area}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {assessment.related_entity.closest_entities && assessment.related_entity.closest_entities.length > 0 && (
              <div>
                <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
                  Closest Entities
                </div>
                <div className="space-y-2">
                  {assessment.related_entity.closest_entities.map((entity, idx) => (
                    <button
                      key={idx}
                      className="w-full text-left px-3 py-2 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors text-sm text-gray-700"
                    >
                      {entity.name}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="p-8 text-center">
            <div className="text-4xl mb-4">🔍</div>
            <p className="text-gray-500 text-sm">
              No related entity information available for this assessment.
            </p>
          </div>
        )}

        {/* Entity UUIDs */}
        {assessment.entity_uuids && assessment.entity_uuids.length > 0 && (
          <div className="p-4 border-t border-content-border">
            <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
              Tracked Entities ({assessment.entity_uuids.length})
            </div>
            <div className="flex flex-wrap gap-1">
              {assessment.entity_uuids.slice(0, 5).map((uuid, idx) => (
                <span
                  key={idx}
                  className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded"
                  title={uuid}
                >
                  {uuid.slice(0, 8)}...
                </span>
              ))}
              {assessment.entity_uuids.length > 5 && (
                <span className="px-2 py-1 text-gray-400 text-xs">
                  +{assessment.entity_uuids.length - 5} more
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default AssessmentDetailPage
