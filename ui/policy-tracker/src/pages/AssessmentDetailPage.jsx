import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ChevronLeft, FileText, Send, Paperclip, ThumbsUp, ThumbsDown, Sparkles } from 'lucide-react'
import { useUIStore } from '../stores/uiStore'

// Mock data - will be replaced with API
const mockAssessment = {
  id: 'assess_1',
  title: 'Monitoring Weeks 32 + 33 (04.08—15.08.25)',
  status: 'complete',
  insights: [
    {
      id: 1,
      title: 'Implementation of the Consumer Credit Directive: Banking Association calls for one-to-one implementation and strengthening of digital processes',
      paragraphs: [
        'The Banking Association supports the draft bill from the Federal Ministry of Justice to implement the EU Consumer Credit Directive but demands strict one-to-one transposition into German law.',
        'National special rules would endanger the goal of harmonizing the European credit market and lead to additional complexity. The association particularly welcomes the planned abolition of the written form requirement for general consumer loans in favor of a digital text form, as this modernizes and accelerates credit processes.',
        'However, for fully seamless processes, a legal upgrading of digital identification procedures would also be necessary. The association likewise welcomes the planned limitation of the withdrawal right to twelve months and 14 days, as this creates legal certainty and sufficiently protects against rash decisions.',
        'Given the profound transformation processes in the financial sector, the Banking Association sees a modern, digitally oriented legal framework not only as a regulatory necessity but also as economically imperative.',
      ],
    },
  ],
  relatedEntity: {
    name: 'DR Stefanie Hubig (BMJ, SPD)',
    type: 'Official',
    image: '/placeholder-person.jpg',
    description: 'Dr. Hubig promotes a pragmatic, digital-friendly approach to consumer protection that challenges fashion e-commerce platforms to adapt while balancing safeguards with business viability, reflecting her "easy as ordering" philosophy.',
    region: 'Germany, Europe',
    focusAreas: [
      'Pro-digitalisation advocate',
      'Consumer protection focus',
      'Pragmatic approach ("as easy as ordering")',
      'Balance between protection and business needs',
    ],
    closestEntities: [
      { name: 'Verbraucherkredit-richtlinie' },
      { name: 'CPC - Verbraucherschutz - Ko...' },
    ],
  },
}

function AssessmentDetailPage() {
  const { id } = useParams()
  const { openSlideOutPanel } = useUIStore()
  const [assessment, setAssessment] = useState(mockAssessment)
  const [inputValue, setInputValue] = useState('')

  const handleEntityClick = () => {
    openSlideOutPanel(assessment.relatedEntity)
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!inputValue.trim()) return
    // TODO: Send follow-up message
    console.log('Sending:', inputValue)
    setInputValue('')
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
              <h1 className="text-xl font-semibold text-gray-900">{assessment.title}</h1>
            </div>
            <button className="px-4 py-2 bg-sidebar-bg text-white rounded-lg text-sm font-medium hover:bg-gray-800 transition-colors">
              Generate report
            </button>
          </div>
        </div>

        {/* Insights Content */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-3xl">
            {assessment.insights.map((insight) => (
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
            ))}
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
                placeholder="Ask a question..."
                className="w-full px-4 py-3 pr-24 bg-content-bgAlt rounded-xl border border-content-border focus:border-accent-primary focus:ring-1 focus:ring-accent-primary focus:outline-none"
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
                  disabled={!inputValue.trim()}
                  className={`
                    p-2 rounded-lg transition-colors
                    ${inputValue.trim()
                      ? 'bg-sidebar-bg text-white hover:bg-gray-800'
                      : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                    }
                  `}
                >
                  <Send size={18} />
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

        <div className="p-4">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">
            {assessment.relatedEntity.name}
          </h3>

          <span className="inline-block px-3 py-1 bg-entity-official text-white rounded text-sm font-medium mb-4">
            {assessment.relatedEntity.type}
          </span>

          {assessment.relatedEntity.image && (
            <div className="rounded-lg overflow-hidden border border-content-border mb-4">
              <div className="w-full h-48 bg-gray-200 flex items-center justify-center">
                <span className="text-gray-400">Photo placeholder</span>
              </div>
            </div>
          )}

          <p className="text-sm text-gray-600 leading-relaxed mb-6">
            {assessment.relatedEntity.description}
          </p>

          <div className="mb-6">
            <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1">
              Region / Jurisdiction
            </div>
            <div className="text-gray-700">{assessment.relatedEntity.region}</div>
          </div>

          <div className="mb-6">
            <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
              Focus area
            </div>
            <ul className="space-y-1.5">
              {assessment.relatedEntity.focusAreas.map((area, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                  <span className="w-2 h-2 rounded-full bg-amber-400 mt-1.5 flex-shrink-0" />
                  {area}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
              Closest Entities
            </div>
            <div className="space-y-2">
              {assessment.relatedEntity.closestEntities.map((entity, idx) => (
                <button
                  key={idx}
                  className="w-full text-left px-3 py-2 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors text-sm text-gray-700"
                >
                  {entity.name}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default AssessmentDetailPage
