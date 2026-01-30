import { useState } from 'react'
import {
  Search,
  Globe,
  FileText,
  Share2,
  Wrench,
  ChevronDown,
  ChevronUp,
  Loader2,
} from 'lucide-react'
import { groupToolCalls, getToolDisplayName } from '../../utils/parseToolCalls'

// Map tool categories to icons and colors
const TOOL_CONFIG = {
  search: {
    icon: Search,
    color: 'bg-blue-100 text-blue-600',
    borderColor: 'border-blue-200',
  },
  web: {
    icon: Globe,
    color: 'bg-green-100 text-green-600',
    borderColor: 'border-green-200',
  },
  entity: {
    icon: FileText,
    color: 'bg-purple-100 text-purple-600',
    borderColor: 'border-purple-200',
  },
  graph: {
    icon: Share2,
    color: 'bg-pink-100 text-pink-600',
    borderColor: 'border-pink-200',
  },
  default: {
    icon: Wrench,
    color: 'bg-gray-100 text-gray-600',
    borderColor: 'border-gray-200',
  },
}

/**
 * ToolCallIndicator - Visual representation of tool calls in chat
 *
 * Shows a compact badge by default with tool count, expandable to see
 * the full flow of tools with icons.
 */
function ToolCallIndicator({ tools, isStreaming = false }) {
  const [expanded, setExpanded] = useState(false)

  if (!tools || tools.length === 0) {
    return null
  }

  const groupedTools = groupToolCalls(tools)

  // Streaming state - show animated indicator
  if (isStreaming) {
    return (
      <div className="tool-call-badge streaming">
        <Loader2 size={14} className="animate-spin" />
        <span>Using tools... ({tools.length})</span>
      </div>
    )
  }

  // Collapsed state - show count badge
  if (!expanded) {
    return (
      <button
        onClick={() => setExpanded(true)}
        className="tool-call-badge"
        title="Click to expand tool details"
      >
        <Wrench size={14} />
        <span>Used {tools.length} tool{tools.length !== 1 ? 's' : ''}</span>
        <ChevronDown size={14} className="ml-1 opacity-60" />
      </button>
    )
  }

  // Collect all messages from all tool groups
  const allMessages = groupedTools.flatMap(group => group.messages || [])

  // Expanded state - show full tool flow
  return (
    <div className="tool-call-expanded">
      <button
        onClick={() => setExpanded(false)}
        className="tool-call-badge mb-2"
        title="Click to collapse"
      >
        <Wrench size={14} />
        <span>Used {tools.length} tool{tools.length !== 1 ? 's' : ''}</span>
        <ChevronUp size={14} className="ml-1 opacity-60" />
      </button>

      <div className="tool-call-flow">
        {groupedTools.map((group, index) => {
          const config = TOOL_CONFIG[group.category] || TOOL_CONFIG.default
          const Icon = config.icon

          return (
            <div key={index} className="tool-call-item">
              {index > 0 && <div className="tool-call-connector" />}
              <div
                className={`tool-call-icon ${config.color}`}
                title={getToolDisplayName(group.name)}
              >
                <Icon size={12} />
                {group.count > 1 && (
                  <span className="tool-call-count">{group.count}</span>
                )}
              </div>
            </div>
          )
        })}
      </div>

      <div className="tool-call-labels">
        {groupedTools.map((group, index) => (
          <span key={index} className="tool-call-label">
            {getToolDisplayName(group.name)}
            {group.count > 1 && ` ×${group.count}`}
          </span>
        ))}
      </div>

      {/* Display agent messages if any */}
      {allMessages.length > 0 && (
        <div className="tool-call-messages">
          {allMessages.map((message, index) => (
            <div key={index} className="tool-call-message">
              {message}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ToolCallIndicator
