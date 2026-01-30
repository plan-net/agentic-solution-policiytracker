import { useState, useMemo } from 'react'
import { User, Bot, ThumbsUp, ThumbsDown, Send } from 'lucide-react'
import { MarkdownRenderer } from '../rich-content'
import ToolCallIndicator from './ToolCallIndicator'
import { parseToolCalls } from '../../utils/parseToolCalls'
import { FEATURES } from '../../config/features'

function ChatMessage({
  role,
  content,
  isStreaming = false,
  messageIndex,
  feedback,
  onFeedback,
}) {
  const isUser = role === 'user'
  const [showCommentBox, setShowCommentBox] = useState(false)
  const [comment, setComment] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Parse tool calls from content (memoized for performance)
  const parsedContent = useMemo(() => {
    if (isUser || !FEATURES.TOOL_CALL_VISUALIZATION) {
      return null
    }
    return parseToolCalls(content)
  }, [content, isUser])

  const handleThumbsUp = async () => {
    if (feedback || isSubmitting) return
    setIsSubmitting(true)
    await onFeedback?.(messageIndex, 'positive', null)
    setIsSubmitting(false)
  }

  const handleThumbsDown = () => {
    if (feedback || isSubmitting) return
    setShowCommentBox(true)
  }

  const handleSubmitNegativeFeedback = async () => {
    if (isSubmitting) return
    setIsSubmitting(true)
    await onFeedback?.(messageIndex, 'negative', comment || null)
    setShowCommentBox(false)
    setIsSubmitting(false)
  }

  const getThumbsUpClass = () => {
    if (feedback === 'positive') {
      return 'p-1 text-green-500 cursor-default'
    }
    if (feedback === 'negative') {
      return 'p-1 text-gray-300 cursor-default'
    }
    return 'p-1 text-gray-400 hover:text-green-500 transition-colors cursor-pointer'
  }

  const getThumbsDownClass = () => {
    if (feedback === 'negative') {
      return 'p-1 text-red-500 cursor-default'
    }
    if (feedback === 'positive') {
      return 'p-1 text-gray-300 cursor-default'
    }
    if (showCommentBox) {
      return 'p-1 text-red-500 cursor-default'
    }
    return 'p-1 text-gray-400 hover:text-red-500 transition-colors cursor-pointer'
  }

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
            <div className="markdown-content">
              {/* Render with tool call visualization if enabled and tools detected */}
              {parsedContent && parsedContent.tools.length > 0 ? (
                <>
                  {parsedContent.before && (
                    <MarkdownRenderer content={parsedContent.before} />
                  )}
                  <ToolCallIndicator
                    tools={parsedContent.tools}
                    isStreaming={isStreaming}
                  />
                  {parsedContent.after && (
                    <MarkdownRenderer content={parsedContent.after} />
                  )}
                </>
              ) : (
                <MarkdownRenderer content={content} />
              )}
              {isStreaming && (
                <span className="inline-block w-2 h-4 bg-accent-primary animate-pulse ml-1" />
              )}
            </div>
          )}
        </div>

        {/* Feedback buttons for assistant messages */}
        {!isUser && !isStreaming && content && (
          <div className="mt-2">
            <div className="flex items-center gap-2">
              <button
                className={getThumbsUpClass()}
                onClick={handleThumbsUp}
                disabled={!!feedback || isSubmitting}
                title={feedback ? 'Feedback submitted' : 'Helpful'}
              >
                <ThumbsUp size={14} fill={feedback === 'positive' ? 'currentColor' : 'none'} />
              </button>
              <button
                className={getThumbsDownClass()}
                onClick={handleThumbsDown}
                disabled={!!feedback || isSubmitting}
                title={feedback ? 'Feedback submitted' : 'Not helpful'}
              >
                <ThumbsDown
                  size={14}
                  fill={feedback === 'negative' || showCommentBox ? 'currentColor' : 'none'}
                />
              </button>
            </div>

            {/* Comment box for negative feedback */}
            {showCommentBox && !feedback && (
              <div className="mt-2 flex items-center gap-2">
                <input
                  type="text"
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="What went wrong? (optional)"
                  className="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent-primary focus:border-transparent"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      handleSubmitNegativeFeedback()
                    }
                  }}
                  disabled={isSubmitting}
                />
                <button
                  onClick={handleSubmitNegativeFeedback}
                  disabled={isSubmitting}
                  className="px-3 py-1.5 bg-accent-primary text-white text-sm rounded-lg hover:bg-accent-primary/90 transition-colors disabled:opacity-50 flex items-center gap-1"
                >
                  <Send size={12} />
                  Submit
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default ChatMessage
