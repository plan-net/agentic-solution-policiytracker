import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Send, Paperclip, Share2, Network, Loader2 } from 'lucide-react'
import ChatMessage from './ChatMessage'
import { useStreamingChat } from '../../hooks/useStreamingChat'

function ChatContainer({ sessionId, onSessionCreated }) {
  const navigate = useNavigate()
  const [inputValue, setInputValue] = useState('')
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const prevSessionIdRef = useRef(null)

  const {
    messages,
    isStreaming,
    isLoadingHistory,
    error,
    sendMessage,
    graphSessionId,
    sessionId: currentSessionId,
    clearMessages,
    submitFeedback,
    pendingQuestion,
    answerQuestion,
  } = useStreamingChat(sessionId)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  // Notify parent when a new session is created
  useEffect(() => {
    if (currentSessionId && currentSessionId !== prevSessionIdRef.current) {
      prevSessionIdRef.current = currentSessionId
      if (onSessionCreated) {
        onSessionCreated(currentSessionId)
      }
    }
  }, [currentSessionId, onSessionCreated])

  // Clear messages when session changes to null (new chat)
  useEffect(() => {
    if (!sessionId && prevSessionIdRef.current) {
      clearMessages()
      prevSessionIdRef.current = null
    }
  }, [sessionId, clearMessages])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!inputValue.trim() || isStreaming) return

    const message = inputValue.trim()
    setInputValue('')
    await sendMessage(message)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const handleViewGraphContext = () => {
    if (graphSessionId) {
      // Navigate to chat context page with session
      navigate(`/chat-context?session=${graphSessionId}&mode=3d`)
    }
  }

  return (
    <div className="flex-1 flex flex-col h-full">
      {/* Header with Graph Context Button */}
      {graphSessionId && (
        <div className="flex items-center justify-end px-6 py-2 border-b border-content-border bg-content-bgAlt">
          <button
            onClick={handleViewGraphContext}
            className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 hover:text-accent-primary hover:bg-white rounded-lg transition-colors"
          >
            <Network size={16} />
            View Graph Context
          </button>
        </div>
      )}

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6">
        {isLoadingHistory ? (
          <div className="h-full flex flex-col items-center justify-center text-gray-500">
            <Loader2 size={32} className="animate-spin mb-4" />
            <p>Loading conversation...</p>
          </div>
        ) : messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-gray-500">
            <div className="w-16 h-16 bg-gradient-to-br from-accent-primary to-accent-secondary rounded-2xl flex items-center justify-center mb-4">
              <Share2 size={32} className="text-white" />
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              Chat with the Knowledge Graph
            </h2>
            <p className="text-center max-w-md">
              Ask questions about policies, regulations, organizations, and their relationships.
              The AI agent has access to the full knowledge graph.
            </p>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto space-y-6">
            {messages.map((message, index) => (
              <ChatMessage
                key={message.id || index}
                role={message.role}
                content={message.content}
                isStreaming={isStreaming && index === messages.length - 1 && message.role === 'assistant'}
                messageIndex={index}
                feedback={message.feedback}
                onFeedback={submitFeedback}
                pendingQuestion={isStreaming && index === messages.length - 1 ? pendingQuestion : null}
                onAnswerSubmit={answerQuestion}
              />
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Error Display */}
      {error && (
        <div className="px-6 py-3 bg-red-50 border-t border-red-200">
          <p className="text-red-600 text-sm">{error}</p>
        </div>
      )}

      {/* Input Area */}
      <div className="border-t border-content-border p-4 bg-white">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
          <div className="relative">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question..."
              rows={1}
              className="w-full px-4 py-3 pr-24 bg-content-bgAlt rounded-xl border border-content-border focus:border-accent-primary focus:ring-1 focus:ring-accent-primary focus:outline-none resize-none"
              disabled={isStreaming || isLoadingHistory}
            />
            <div className="absolute right-2 bottom-2 flex items-center gap-2">
              <button
                type="button"
                className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
                title="Add attachment"
              >
                <Paperclip size={18} />
              </button>
              <button
                type="submit"
                disabled={!inputValue.trim() || isStreaming || isLoadingHistory}
                className={`
                  p-2 rounded-lg transition-colors
                  ${inputValue.trim() && !isStreaming && !isLoadingHistory
                    ? 'bg-sidebar-bg text-white hover:bg-gray-800'
                    : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                  }
                `}
              >
                {isStreaming ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : (
                  <Send size={18} />
                )}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}

export default ChatContainer
