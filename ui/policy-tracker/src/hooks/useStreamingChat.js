import { useState, useCallback, useRef, useEffect } from 'react'
import { getSessionMessages, streamChatMessage } from '../services/chatApi'
import { submitFeedback as submitFeedbackApi } from '../services/feedbackApi'

export function useStreamingChat(initialSessionId = null) {
  const [messages, setMessages] = useState([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [error, setError] = useState(null)
  const [sessionId, setSessionId] = useState(initialSessionId)
  const [graphSessionId, setGraphSessionId] = useState(null)
  const abortControllerRef = useRef(null)

  // Track if we created the session ourselves (to avoid reloading)
  const createdSessionRef = useRef(null)

  // Load existing session messages when sessionId changes
  useEffect(() => {
    async function loadSessionMessages() {
      // If no session ID, clear state
      if (!initialSessionId) {
        setMessages([])
        setSessionId(null)
        setGraphSessionId(null)
        createdSessionRef.current = null
        return
      }

      // If we just created this session, don't try to reload messages
      // (we already have them in state from the streaming)
      if (createdSessionRef.current === initialSessionId) {
        setSessionId(initialSessionId)
        setGraphSessionId(initialSessionId)
        return
      }

      setIsLoadingHistory(true)
      setError(null)

      const result = await getSessionMessages(initialSessionId)

      if (result.success && result.data) {
        // Build a map of feedback by message index
        const feedbackMap = {}
        if (result.data.feedback) {
          result.data.feedback.forEach((fb) => {
            feedbackMap[fb.message_index] = {
              rating: fb.rating,
              comment: fb.comment,
            }
          })
        }

        // Convert messages to the format expected by the UI
        const loadedMessages = result.data.messages.map((msg, index) => ({
          id: `${msg.role}_${index}_${Date.now()}`,
          role: msg.role,
          content: msg.content,
          feedback: feedbackMap[index]?.rating || null,
          feedbackComment: feedbackMap[index]?.comment || null,
        }))
        setMessages(loadedMessages)
        setSessionId(initialSessionId)
        setGraphSessionId(initialSessionId)
      } else if (result.status === 404) {
        // Session not found - this might be a new session that hasn't been persisted yet
        // Don't show error, just keep current messages if any
        console.warn(`Session ${initialSessionId} not found, may be newly created`)
        setSessionId(initialSessionId)
        setGraphSessionId(initialSessionId)
      } else {
        setError(result.error || 'Failed to load conversation')
        setMessages([])
      }

      setIsLoadingHistory(false)
    }

    loadSessionMessages()
  }, [initialSessionId])

  const sendMessage = useCallback(async (content) => {
    if (!content.trim()) return

    setError(null)
    setIsStreaming(true)

    // Add user message
    const userMessage = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: content.trim(),
    }
    setMessages((prev) => [...prev, userMessage])

    // Add placeholder for assistant message
    const assistantMessageId = `assistant_${Date.now()}`
    setMessages((prev) => [
      ...prev,
      { id: assistantMessageId, role: 'assistant', content: '' },
    ])

    let accumulatedContent = ''

    try {
      abortControllerRef.current = new AbortController()

      await streamChatMessage({
        messages: [
          ...messages.map((m) => ({ role: m.role, content: m.content })),
          { role: 'user', content: content.trim() },
        ],
        sessionId,
        signal: abortControllerRef.current.signal,
        onChunk: (chunk) => {
          accumulatedContent += chunk
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMessageId
                ? { ...m, content: accumulatedContent }
                : m
            )
          )
        },
        onSessionId: (newSessionId) => {
          // Mark this session as created by us
          createdSessionRef.current = newSessionId
          setSessionId(newSessionId)
          setGraphSessionId(newSessionId)
        },
        onError: (errorMessage) => {
          setError(errorMessage)
          // Remove the empty assistant message on error
          setMessages((prev) =>
            prev.filter((m) => m.id !== assistantMessageId)
          )
        },
        onDone: () => {
          // Streaming complete
        },
      })
    } catch (err) {
      if (err.name === 'AbortError') {
        console.log('Request aborted')
      } else {
        console.error('Chat error:', err)
        setError(err.message || 'Failed to send message')

        // Remove the empty assistant message on error
        setMessages((prev) =>
          prev.filter((m) => m.id !== assistantMessageId)
        )
      }
    } finally {
      setIsStreaming(false)
      abortControllerRef.current = null
    }
  }, [messages, sessionId])

  const cancelStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
  }, [])

  const clearMessages = useCallback(() => {
    setMessages([])
    setSessionId(null)
    setGraphSessionId(null)
    setError(null)
    createdSessionRef.current = null
  }, [])

  const submitFeedback = useCallback(async (messageIndex, rating, comment) => {
    if (!sessionId) {
      console.error('Cannot submit feedback: no session ID')
      return false
    }

    const result = await submitFeedbackApi({
      sessionId,
      messageIndex,
      rating,
      comment,
    })

    if (result.success) {
      // Update local message state with feedback
      setMessages((prev) =>
        prev.map((msg, index) =>
          index === messageIndex
            ? { ...msg, feedback: rating, feedbackComment: comment }
            : msg
        )
      )
      return true
    } else {
      console.error('Failed to submit feedback:', result.error)
      return false
    }
  }, [sessionId])

  return {
    messages,
    isStreaming,
    isLoadingHistory,
    error,
    sessionId,
    graphSessionId,
    sendMessage,
    cancelStream,
    clearMessages,
    setMessages,
    submitFeedback,
  }
}

export default useStreamingChat
