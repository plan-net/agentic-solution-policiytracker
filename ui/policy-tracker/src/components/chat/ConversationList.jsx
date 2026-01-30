import { MessageSquare, Trash2, Loader2 } from 'lucide-react'
import { formatRelativeTime } from '../../utils/formatters'

function ConversationList({
  conversations,
  currentSessionId,
  onSelect,
  onDelete,
  isLoading = false,
  collapsed = false,
}) {
  if (isLoading && conversations.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-4 text-gray-500">
        <Loader2 size={20} className="animate-spin" />
      </div>
    )
  }

  if (conversations.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-4 text-gray-500 text-sm">
        {!collapsed && 'No conversations yet'}
      </div>
    )
  }

  // Collapsed view - show icons only
  if (collapsed) {
    return (
      <div className="flex-1 overflow-y-auto">
        <div className="p-1 space-y-1">
          {conversations.map((conv) => (
            <button
              key={conv.id}
              onClick={() => onSelect(conv.id)}
              title={conv.title}
              className={`
                w-full flex items-center justify-center p-2 rounded-lg transition-colors
                ${currentSessionId === conv.id
                  ? 'bg-white shadow-sm'
                  : 'hover:bg-white/50'
                }
              `}
            >
              <MessageSquare size={18} className="text-gray-500" />
            </button>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="p-2 space-y-1">
        {conversations.map((conv) => (
          <button
            key={conv.id}
            onClick={() => onSelect(conv.id)}
            className={`
              w-full text-left px-3 py-3 rounded-lg transition-colors group relative
              ${currentSessionId === conv.id
                ? 'bg-white shadow-sm'
                : 'hover:bg-white/50'
              }
            `}
          >
            <div className="flex items-start gap-3">
              <MessageSquare size={16} className="text-gray-400 mt-0.5 flex-shrink-0" />
              <div className="flex-1 min-w-0 pr-6">
                <div className="text-sm font-medium text-gray-900 truncate">
                  {conv.title}
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-xs text-gray-500">
                    {formatRelativeTime(conv.updatedAt)}
                  </span>
                  {conv.entityCount > 0 && (
                    <span className="text-xs text-gray-400">
                      · {conv.entityCount} entities
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Delete Button - Only show on hover */}
            {onDelete && (
              <button
                onClick={(e) => onDelete(conv.id, e)}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-md text-gray-400 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-opacity"
                title="Delete conversation"
              >
                <Trash2 size={14} />
              </button>
            )}
          </button>
        ))}
      </div>
    </div>
  )
}

export default ConversationList
