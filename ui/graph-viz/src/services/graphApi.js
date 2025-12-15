/**
 * API service for graph visualization backend
 */

import axios from 'axios';

const API_BASE = '/api/graph';

export const graphApi = {
  /**
   * Health check for backend services
   */
  async healthCheck() {
    try {
      const response = await axios.get(`${API_BASE}/health`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  },

  /**
   * Get list of all available schema queries
   */
  async getSchemaQueries() {
    try {
      const response = await axios.get(`${API_BASE}/schema-queries`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  },

  /**
   * Execute a predefined schema query with optional parameters
   * @param {string} queryName - Name of the schema query
   * @param {Object} parameters - Optional query parameters (e.g., { limit: 100, days_back: 30 })
   */
  async executeSchemaQuery(queryName, parameters = null) {
    try {
      // Use POST if parameters provided, GET otherwise
      if (parameters && Object.keys(parameters).length > 0) {
        const response = await axios.post(`${API_BASE}/schema-query/${queryName}`, {
          parameters
        });
        return { success: true, data: response.data };
      } else {
        const response = await axios.get(`${API_BASE}/schema-query/${queryName}`);
        return { success: true, data: response.data };
      }
    } catch (error) {
      return { success: false, error: error.message };
    }
  },

  /**
   * Convert natural language to Cypher and execute
   * @param {string} text - Natural language query
   * @param {number} limit - Maximum number of nodes to return
   */
  async textToCypher(text, limit = 50) {
    try {
      const response = await axios.post(`${API_BASE}/text-to-cypher`, {
        text,
        limit
      });
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  },

  /**
   * Get graph context from a chat session
   * @param {string} sessionId - Chat session ID
   * @param {string|null} query - Optional query text
   */
  async getChatContext(sessionId, query = null) {
    try {
      const response = await axios.post(`${API_BASE}/chat-context`, {
        session_id: sessionId,
        query
      });
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }
};
