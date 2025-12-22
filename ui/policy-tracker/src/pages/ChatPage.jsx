import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Plus, Trash2, RefreshCw } from 'lucide-react'
import ChatContainer from '../components/chat/ChatContainer'
import ConversationList from '../components/chat/ConversationList'
import { listSessions, deleteSession } from '../services/chatApi'

function ChatPage() {
  const { sessionId } = useParams()
  const navigate = useNavigate()
  const [conversations, setConversations] = useState([])
  const [currentSession, setCurrentSession] = useState(sessionId || null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  // Fetch conversations from API
  const fetchConversations = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    const result = await listSessions(50)

    if (result.success && result.data) {
      // Transform API response to match UI format
      const sessions = result.data.map((session) => ({
        id: session.session_id,
        title: session.title || 'New Conversation',
        updatedAt: session.last_updated,
        entityCount: session.entity_count,
        toolsUsedCount: session.tools_used_count,
      }))
      setConversations(sessions)
    } else {
      setError(result.error || 'Failed to load conversations')
      // Keep existing conversations on error
    }

    setIsLoading(false)
  }, [])

  // Load conversations on mount
  useEffect(() => {
    fetchConversations()
  }, [fetchConversations])

  // Update current session when URL changes
  useEffect(() => {
    setCurrentSession(sessionId || null)
  }, [sessionId])

  const handleNewChat = () => {
    setCurrentSession(null)
    navigate('/chat')
  }

  const handleSelectConversation = (id) => {
    setCurrentSession(id)
    navigate(`/chat/${id}`)
  }

  const handleDeleteConversation = async (id, e) => {
    e.stopPropagation()

    if (!window.confirm('Delete this conversation?')) {
      return
    }

    const result = await deleteSession(id)

    if (result.success) {
      // Remove from local state
      setConversations((prev) => prev.filter((c) => c.id !== id))

      // If we deleted the current session, navigate to new chat
      if (currentSession === id) {
        setCurrentSession(null)
        navigate('/chat')
      }
    } else {
      alert(result.error || 'Failed to delete conversation')
    }
  }

  const handleSessionCreated = (newSessionId) => {
    // Refresh conversation list when a new session is created
    fetchConversations()

    // Update URL to include session ID
    if (newSessionId && !currentSession) {
      navigate(`/chat/${newSessionId}`, { replace: true })
      setCurrentSession(newSessionId)
    }
  }

  return (
    <div className="flex h-screen">
      {/* Conversation Sidebar */}
      <div className="w-72 border-r border-content-border bg-content-bgAlt flex flex-col">
        {/* New Chat Button */}
        <div className="p-4 border-b border-content-border">
          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-sidebar-bg text-white rounded-lg hover:bg-gray-800 transition-colors"
          >
            <Plus size={18} />
            New Chat
          </button>
        </div>

        {/* Conversations List Header */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-content-border">
          <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">
            History
          </span>
          <button
            onClick={fetchConversations}
            disabled={isLoading}
            className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
            title="Refresh conversations"
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="px-4 py-2 text-xs text-red-600 bg-red-50 border-b border-red-100">
            {error}
          </div>
        )}

        {/* Conversations List */}
        <ConversationList
          conversations={conversations}
          currentSessionId={currentSession}
          onSelect={handleSelectConversation}
          onDelete={handleDeleteConversation}
          isLoading={isLoading}
        />
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        <ChatContainer
          sessionId={currentSession}
          onSessionCreated={handleSessionCreated}
        />
      </div>
    </div>
  )
}

export default ChatPage
