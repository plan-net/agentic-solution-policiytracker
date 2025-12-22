import api, { handleResponse, handleError } from './api'

export const graphApi = {
  // Health check
  healthCheck: async () => {
    try {
      const response = await api.get('/api/graph/health')
      return handleResponse(response)
    } catch (error) {
      return handleError(error)
    }
  },

  // Get available schema queries
  getSchemaQueries: async () => {
    try {
      const response = await api.get('/api/graph/schema-queries')
      return handleResponse(response)
    } catch (error) {
      return handleError(error)
    }
  },

  // Execute a schema query
  executeSchemaQuery: async (queryName, parameters = null) => {
    try {
      const url = `/api/graph/schema-query/${encodeURIComponent(queryName)}`
      const response = parameters
        ? await api.post(url, { parameters })
        : await api.get(url)
      return handleResponse(response)
    } catch (error) {
      return handleError(error)
    }
  },

  // Text to Cypher conversion
  textToCypher: async (query) => {
    try {
      const response = await api.post('/api/graph/text-to-cypher', { query })
      return handleResponse(response)
    } catch (error) {
      return handleError(error)
    }
  },

  // Get chat context (graph data from chat session)
  getChatContext: async (sessionId) => {
    try {
      const response = await api.post('/api/graph/chat-context', { session_id: sessionId })
      return handleResponse(response)
    } catch (error) {
      return handleError(error)
    }
  },

  // Get entity details
  getEntityDetails: async (entityId) => {
    try {
      const response = await api.get(`/api/graph/entity/${encodeURIComponent(entityId)}`)
      return handleResponse(response)
    } catch (error) {
      return handleError(error)
    }
  },

  // Search entities
  searchEntities: async (query, limit = 20) => {
    try {
      const response = await api.get('/api/graph/search', {
        params: { q: query, limit }
      })
      return handleResponse(response)
    } catch (error) {
      return handleError(error)
    }
  },

  // Get recent graph updates (new in last 7 days)
  getRecentUpdates: async (days = 7, limit = 20) => {
    try {
      const response = await api.get('/api/graph/recent-updates', {
        params: { days, limit }
      })
      return handleResponse(response)
    } catch (error) {
      return handleError(error)
    }
  },

  // Get interesting patterns (placeholder)
  getPatterns: async () => {
    try {
      const response = await api.get('/api/graph/patterns')
      return handleResponse(response)
    } catch (error) {
      return handleError(error)
    }
  },
}

export default graphApi
