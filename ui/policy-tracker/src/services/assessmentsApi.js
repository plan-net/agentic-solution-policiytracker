import api, { handleResponse, handleError } from './api'

/**
 * Assessments API Service
 * Handles CRUD operations for assessments
 */

/**
 * Assessment status enum
 */
export const AssessmentStatus = {
  PENDING: 'pending',
  WORKING: 'working',
  COMPLETE: 'complete',
  FAILED: 'failed',
  READY: 'ready',
}

/**
 * Assessment type enum
 */
export const AssessmentType = {
  MONITORING: 'monitoring',
  DAILY_FOCUS: 'daily_focus',
  DEEP_DIVE: 'deep_dive',
  SPOTLIGHT: 'spotlight',
  CUSTOM: 'custom',
}

/**
 * Get list of assessments
 * @param {Object} options - Query options
 * @param {number} options.limit - Maximum number of assessments to return
 * @param {string} options.status - Filter by status (pending, working, complete, failed, ready)
 * @param {string} options.assessmentType - Filter by assessment type
 * @returns {Promise<{success: boolean, data?: Array, error?: string}>}
 */
export async function listAssessments({ limit = 50, status = null, assessmentType = null } = {}) {
  try {
    const params = { limit }
    if (status) params.status = status
    if (assessmentType) params.assessment_type = assessmentType

    const response = await api.get('/api/assessments', { params })
    return handleResponse(response)
  } catch (error) {
    return handleError(error)
  }
}

/**
 * Get a specific assessment
 * @param {string} assessmentId - The assessment ID
 * @returns {Promise<{success: boolean, data?: Object, error?: string}>}
 */
export async function getAssessment(assessmentId) {
  try {
    const response = await api.get(`/api/assessments/${assessmentId}`)
    return handleResponse(response)
  } catch (error) {
    return handleError(error)
  }
}

/**
 * Create a new assessment
 * @param {Object} data - Assessment data
 * @param {string} data.title - Assessment title
 * @param {string} data.prompt - Assessment prompt/question
 * @param {string} data.assessment_type - Assessment type (monitoring, daily_focus, deep_dive, spotlight, custom)
 * @param {boolean} data.include_web_research - Whether to include web research
 * @param {Object} data.options - Additional options
 * @returns {Promise<{success: boolean, data?: Object, error?: string}>}
 */
export async function createAssessment(data) {
  try {
    const response = await api.post('/api/assessments', data)
    return handleResponse(response)
  } catch (error) {
    return handleError(error)
  }
}

/**
 * Update an assessment
 * @param {string} assessmentId - The assessment ID
 * @param {Object} data - Update data
 * @param {string} data.title - New title
 * @param {string} data.status - New status
 * @param {Array} data.insights - Assessment insights
 * @param {Object} data.related_entity - Related entity data
 * @returns {Promise<{success: boolean, data?: Object, error?: string}>}
 */
export async function updateAssessment(assessmentId, data) {
  try {
    const response = await api.patch(`/api/assessments/${assessmentId}`, data)
    return handleResponse(response)
  } catch (error) {
    return handleError(error)
  }
}

/**
 * Delete an assessment
 * @param {string} assessmentId - The assessment ID to delete
 * @returns {Promise<{success: boolean, data?: Object, error?: string}>}
 */
export async function deleteAssessment(assessmentId) {
  try {
    const response = await api.delete(`/api/assessments/${assessmentId}`)
    return handleResponse(response)
  } catch (error) {
    return handleError(error)
  }
}

/**
 * Start running an assessment
 * @param {string} assessmentId - The assessment ID to run
 * @returns {Promise<{success: boolean, data?: Object, error?: string}>}
 */
export async function runAssessment(assessmentId) {
  try {
    const response = await api.post(`/api/assessments/${assessmentId}/run`)
    return handleResponse(response)
  } catch (error) {
    return handleError(error)
  }
}

/**
 * Send a follow-up chat message for an assessment
 * @param {string} assessmentId - The assessment ID
 * @param {string} message - The chat message
 * @returns {Promise<{success: boolean, data?: Object, error?: string}>}
 */
export async function sendAssessmentChat(assessmentId, message) {
  try {
    const response = await api.post(`/api/assessments/${assessmentId}/chat`, { message })
    return handleResponse(response)
  } catch (error) {
    return handleError(error)
  }
}

export default {
  AssessmentStatus,
  AssessmentType,
  listAssessments,
  getAssessment,
  createAssessment,
  updateAssessment,
  deleteAssessment,
  runAssessment,
  sendAssessmentChat,
}
