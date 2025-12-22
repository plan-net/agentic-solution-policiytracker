import api, { handleResponse, handleError } from './api'

/**
 * Chat Sessions API Service
 * Handles CRUD operations for chat sessions and message streaming
 */

/**
 * Get list of chat sessions
 * @param {number} limit - Maximum number of sessions to return
 * @returns {Promise<{success: boolean, data?: Array, error?: string}>}
 */
export async function listSessions(limit = 50) {
  try {
    const response = await api.get('/api/chat/sessions', {
      params: { limit },
    })
    return handleResponse(response)
  } catch (error) {
    return handleError(error)
  }
}

/**
 * Get a specific chat session with details
 * @param {string} sessionId - The session ID
 * @returns {Promise<{success: boolean, data?: Object, error?: string}>}
 */
export async function getSession(sessionId) {
  try {
    const response = await api.get(`/api/chat/sessions/${sessionId}`)
    return handleResponse(response)
  } catch (error) {
    return handleError(error)
  }
}

/**
 * Get messages for a chat session
 * @param {string} sessionId - The session ID
 * @returns {Promise<{success: boolean, data?: Object, error?: string}>}
 */
export async function getSessionMessages(sessionId) {
  try {
    const response = await api.get(`/api/chat/sessions/${sessionId}/messages`)
    return handleResponse(response)
  } catch (error) {
    return handleError(error)
  }
}

/**
 * Delete a chat session
 * @param {string} sessionId - The session ID to delete
 * @returns {Promise<{success: boolean, data?: Object, error?: string}>}
 */
export async function deleteSession(sessionId) {
  try {
    const response = await api.delete(`/api/chat/sessions/${sessionId}`)
    return handleResponse(response)
  } catch (error) {
    return handleError(error)
  }
}

/**
 * Update a chat session's title
 * @param {string} sessionId - The session ID
 * @param {string} title - New title for the session
 * @returns {Promise<{success: boolean, data?: Object, error?: string}>}
 */
export async function updateSessionTitle(sessionId, title) {
  try {
    const response = await api.patch(`/api/chat/sessions/${sessionId}/title`, null, {
      params: { title },
    })
    return handleResponse(response)
  } catch (error) {
    return handleError(error)
  }
}

/**
 * Stream a chat message using Server-Sent Events
 * @param {Object} options - Streaming options
 * @param {Array} options.messages - Array of messages [{role, content}]
 * @param {string} options.sessionId - Optional session ID for continuing a conversation
 * @param {AbortSignal} options.signal - Optional abort signal for cancellation
 * @param {function} options.onChunk - Callback for each content chunk
 * @param {function} options.onSessionId - Callback when session ID is received
 * @param {function} options.onError - Callback for errors
 * @param {function} options.onDone - Callback when streaming is complete
 * @returns {Promise<void>}
 */
export async function streamChatMessage({
  messages,
  sessionId = null,
  signal = null,
  onChunk = () => {},
  onSessionId = () => {},
  onError = () => {},
  onDone = () => {},
}) {
  try {
    const response = await fetch('/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'claude-policytracker',
        messages,
        stream: true,
        session_id: sessionId,
      }),
      signal,
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value, { stream: true })
      const lines = chunk.split('\n')

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)

          if (data === '[DONE]') {
            continue
          }

          try {
            const parsed = JSON.parse(data)

            // Extract content from SSE response
            if (parsed.choices?.[0]?.delta?.content) {
              onChunk(parsed.choices[0].delta.content)
            }

            // Extract session ID if provided
            if (parsed.session_id) {
              onSessionId(parsed.session_id)
            }
          } catch (e) {
            // Ignore JSON parse errors for incomplete chunks
            console.debug('Skipping non-JSON chunk:', data)
          }
        }
      }
    }

    onDone()
  } catch (error) {
    if (error.name === 'AbortError') {
      console.log('Stream aborted')
    } else {
      console.error('Stream error:', error)
      onError(error.message || 'Failed to stream message')
    }
  }
}

export default {
  listSessions,
  getSession,
  getSessionMessages,
  deleteSession,
  updateSessionTitle,
  streamChatMessage,
}
