import { User, Bot, ThumbsUp, ThumbsDown } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

function ChatMessage({ role, content, isStreaming = false }) {
  const isUser = role === 'user'

  return (
    <div className={`flex gap-4 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div
        className={`
          w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0
          ${isUser ? 'bg-accent-primary' : 'bg-gradient-to-br from-accent-primary to-accent-secondary'}
        `}
      >
        {isUser ? (
          <User size={16} className="text-white" />
        ) : (
          <Bot size={16} className="text-white" />
        )}
      </div>

      {/* Message Content */}
      <div className={`flex-1 ${isUser ? 'text-right' : ''}`}>
        <div
          className={`
            inline-block max-w-full text-left
            ${isUser
              ? 'bg-accent-primary text-white rounded-2xl rounded-tr-md px-4 py-3'
              : 'bg-content-bgAlt rounded-2xl rounded-tl-md px-4 py-3'
            }
          `}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{content}</p>
          ) : (
            <div className="markdown-content prose prose-sm max-w-none">
              <ReactMarkdown>{content}</ReactMarkdown>
              {isStreaming && (
                <span className="inline-block w-2 h-4 bg-accent-primary animate-pulse ml-1" />
              )}
            </div>
          )}
        </div>

        {/* Feedback buttons for assistant messages */}
        {!isUser && !isStreaming && content && (
          <div className="flex items-center gap-2 mt-2">
            <button className="p-1 text-gray-400 hover:text-gray-600 transition-colors">
              <ThumbsUp size={14} />
            </button>
            <button className="p-1 text-gray-400 hover:text-gray-600 transition-colors">
              <ThumbsDown size={14} />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default ChatMessage
