import axios from 'axios'

// Create axios instance with base configuration
const api = axios.create({
  baseURL: '',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`)
    return config
  },
  (error) => {
    console.error('[API] Request error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    const message = error.response?.data?.detail || error.response?.data?.message || error.message
    console.error('[API] Response error:', message)

    // Handle specific error codes
    if (error.response?.status === 401) {
      // Handle unauthorized
      console.warn('[API] Unauthorized request')
    }

    if (error.response?.status === 503) {
      // Handle service unavailable
      console.warn('[API] Service unavailable')
    }

    return Promise.reject({
      message,
      status: error.response?.status,
      data: error.response?.data,
    })
  }
)

// Helper function for successful response
export const handleResponse = (response) => ({
  success: true,
  data: response.data,
})

// Helper function for error response
export const handleError = (error) => ({
  success: false,
  error: error.message || 'An error occurred',
  status: error.status,
})

export default api
