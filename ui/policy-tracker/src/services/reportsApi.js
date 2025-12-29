import api, { handleResponse, handleError } from './api'

/**
 * Reports API Service
 * Handles CRUD operations for weekly reports
 */

/**
 * Report status enum
 */
export const ReportStatus = {
  PENDING: 'pending',
  WORKING: 'working',
  COMPLETE: 'complete',
  FAILED: 'failed',
}

/**
 * Report type enum
 */
export const ReportType = {
  WEEKLY: 'weekly',
  DAILY: 'daily',
  DEEP_DIVE: 'deep_dive',
  SPOTLIGHT: 'spotlight',
}

/**
 * Claude model enum
 */
export const ClaudeModel = {
  SONNET_4: 'claude-sonnet-4-20250514',
  OPUS_4: 'claude-opus-4-20250514',
}

/**
 * Get list of reports
 * @param {Object} options - Query options
 * @param {number} options.limit - Maximum number of reports to return
 * @param {string} options.status - Filter by status (pending, working, complete, failed)
 * @param {string} options.reportType - Filter by report type (weekly, daily, deep_dive, spotlight)
 * @returns {Promise<{success: boolean, data?: Array, error?: string}>}
 */
export async function listReports({ limit = 50, status = null, reportType = null } = {}) {
  try {
    const params = { limit }
    if (status) params.status = status
    if (reportType) params.report_type = reportType

    const response = await api.get('/api/reports', { params })
    return handleResponse(response)
  } catch (error) {
    return handleError(error)
  }
}

/**
 * Get a specific report
 * @param {string} reportId - The report ID
 * @returns {Promise<{success: boolean, data?: Object, error?: string}>}
 */
export async function getReport(reportId) {
  try {
    const response = await api.get(`/api/reports/${reportId}`)
    return handleResponse(response)
  } catch (error) {
    return handleError(error)
  }
}

/**
 * Create a new report
 * @param {Object} data - Report data
 * @param {string} data.title - Report title
 * @param {string} data.report_type - Report type (weekly, daily, deep_dive, spotlight)
 * @param {string} data.date_range_start - Start date (YYYY-MM-DD)
 * @param {string} data.date_range_end - End date (YYYY-MM-DD)
 * @param {string} data.claude_model - Claude model to use (claude-sonnet-4-20250514, claude-opus-4-20250514)
 * @param {boolean} data.include_events - Whether to include forward-looking events
 * @param {Object} data.options - Additional options
 * @returns {Promise<{success: boolean, data?: Object, error?: string}>}
 */
export async function createReport(data) {
  try {
    const response = await api.post('/api/reports', data)
    return handleResponse(response)
  } catch (error) {
    return handleError(error)
  }
}

/**
 * Update a report
 * @param {string} reportId - The report ID
 * @param {Object} data - Update data
 * @param {string} data.title - New title
 * @param {string} data.status - New status
 * @param {string} data.content - Report content
 * @param {Array} data.sections - Report sections
 * @returns {Promise<{success: boolean, data?: Object, error?: string}>}
 */
export async function updateReport(reportId, data) {
  try {
    const response = await api.patch(`/api/reports/${reportId}`, data)
    return handleResponse(response)
  } catch (error) {
    return handleError(error)
  }
}

/**
 * Delete a report
 * @param {string} reportId - The report ID to delete
 * @returns {Promise<{success: boolean, data?: Object, error?: string}>}
 */
export async function deleteReport(reportId) {
  try {
    const response = await api.delete(`/api/reports/${reportId}`)
    return handleResponse(response)
  } catch (error) {
    return handleError(error)
  }
}

/**
 * Start generating a report
 * @param {string} reportId - The report ID to generate
 * @returns {Promise<{success: boolean, data?: Object, error?: string}>}
 */
export async function generateReport(reportId) {
  try {
    const response = await api.post(`/api/reports/${reportId}/generate`)
    return handleResponse(response)
  } catch (error) {
    return handleError(error)
  }
}

export default {
  ReportStatus,
  ReportType,
  ClaudeModel,
  listReports,
  getReport,
  createReport,
  updateReport,
  deleteReport,
  generateReport,
}
