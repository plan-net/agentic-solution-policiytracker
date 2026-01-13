import api, { handleResponse, handleError } from './api'

/**
 * Submit feedback for a chat message.
 *
 * @param {Object} params - Feedback parameters
 * @param {string} params.sessionId - The chat session ID
 * @param {number} params.messageIndex - Index of the message in the session
 * @param {string} params.rating - Feedback rating: "positive" or "negative"
 * @param {string} [params.comment] - Optional feedback comment
 * @returns {Promise<{success: boolean, data?: object, error?: string}>}
 */
export async function submitFeedback({ sessionId, messageIndex, rating, comment }) {
  try {
    const response = await api.post(`/api/chat/sessions/${sessionId}/feedback`, {
      message_index: messageIndex,
      rating,
      comment: comment || null,
    })
    return handleResponse(response)
  } catch (error) {
    return handleError(error)
  }
}

export default { submitFeedback }
