import { format, formatDistanceToNow, parseISO, isValid } from 'date-fns'

/**
 * Format a date for display
 * @param {string|Date} date - The date to format
 * @param {string} formatStr - The format string (default: 'dd MMMM yyyy')
 * @returns {string} Formatted date string
 */
export function formatDate(date, formatStr = 'dd MMMM yyyy') {
  if (!date) return ''

  const dateObj = typeof date === 'string' ? parseISO(date) : date
  if (!isValid(dateObj)) return ''

  return format(dateObj, formatStr)
}

/**
 * Format a date as relative time (e.g., "2 hours ago")
 * @param {string|Date} date - The date to format
 * @returns {string} Relative time string
 */
export function formatRelativeTime(date) {
  if (!date) return ''

  const dateObj = typeof date === 'string' ? parseISO(date) : date
  if (!isValid(dateObj)) return ''

  return formatDistanceToNow(dateObj, { addSuffix: true })
}

/**
 * Format a week range
 * @param {number} week - Week number
 * @param {number} year - Year
 * @returns {string} Formatted week range (e.g., "KW48/2025")
 */
export function formatWeek(week, year) {
  return `KW${week.toString().padStart(2, '0')}/${year}`
}

/**
 * Truncate text to a maximum length
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length
 * @returns {string} Truncated text with ellipsis if needed
 */
export function truncateText(text, maxLength = 100) {
  if (!text || text.length <= maxLength) return text
  return text.slice(0, maxLength).trim() + '...'
}

/**
 * Format a number with comma separators
 * @param {number} num - Number to format
 * @returns {string} Formatted number
 */
export function formatNumber(num) {
  if (num === null || num === undefined) return ''
  return num.toLocaleString()
}

/**
 * Convert entity type to display name
 * @param {string} type - Entity type (e.g., 'GovernmentAgency')
 * @returns {string} Display name (e.g., 'Government Agency')
 */
export function formatEntityType(type) {
  if (!type) return ''
  // Add space before capital letters
  return type.replace(/([A-Z])/g, ' $1').trim()
}

/**
 * Format file size
 * @param {number} bytes - Size in bytes
 * @returns {string} Formatted size (e.g., '1.5 MB')
 */
export function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes'

  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

/**
 * Generate initials from a name
 * @param {string} name - Full name
 * @returns {string} Initials (e.g., 'JD' for 'John Doe')
 */
export function getInitials(name) {
  if (!name) return ''

  return name
    .split(' ')
    .map(word => word[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

/**
 * Slugify a string for URLs
 * @param {string} text - Text to slugify
 * @returns {string} Slugified string
 */
export function slugify(text) {
  if (!text) return ''

  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')
}
