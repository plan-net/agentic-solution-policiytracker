/**
 * Parse tool calls from message content
 *
 * Detects patterns like "*Using search_knowledge_graph...*" and extracts them
 * into a structured format for visualization.
 * Also captures any trailing agent message after the "..."
 *
 * Supports both plain and markdown italic formats:
 * - Using tool_name...
 * - *Using tool_name...*
 */

// Pattern to match tool call lines with optional markdown asterisks
// Matches: "Using tool_name..." or "*Using tool_name...*" with optional trailing message
const TOOL_CALL_PATTERN = /^\*?Using\s+([\w_]+)\.\.\.\*?\s*(.*)$/gm

/**
 * Parse message content to extract tool calls
 *
 * @param {string} content - The full message content
 * @returns {{ before: string, tools: { name: string, message: string | null }[], after: string }}
 */
export function parseToolCalls(content) {
  if (!content) {
    return { before: '', tools: [], after: '' }
  }

  const lines = content.split('\n')
  const tools = []
  let beforeLines = []
  let afterLines = []
  let inToolSection = false
  let toolSectionEnded = false

  for (const line of lines) {
    // Match "Using tool_name..." or "*Using tool_name...*" with optional trailing message
    const match = line.match(/^\*?Using\s+([\w_]+)\.\.\.\*?\s*(.*)$/m)

    if (match) {
      tools.push({
        name: match[1],
        message: match[2].trim() || null
      })
      inToolSection = true
    } else if (inToolSection && line.trim() === '') {
      // Empty line after tool calls - could be separator
      continue
    } else if (inToolSection && !match) {
      // Non-tool line after tools started - tools section ended
      toolSectionEnded = true
      inToolSection = false
      afterLines.push(line)
    } else if (toolSectionEnded) {
      afterLines.push(line)
    } else {
      beforeLines.push(line)
    }
  }

  return {
    before: beforeLines.join('\n').trim(),
    tools,
    after: afterLines.join('\n').trim(),
  }
}

/**
 * Group consecutive identical tools for cleaner display
 *
 * @param {{ name: string, message: string | null }[]} tools - Array of tool objects
 * @returns {{ name: string, count: number, category: string, messages: string[] }[]}
 */
export function groupToolCalls(tools) {
  if (!tools || tools.length === 0) {
    return []
  }

  const groups = []
  let currentGroup = null

  for (const tool of tools) {
    // Handle both old format (string) and new format (object)
    const toolName = typeof tool === 'string' ? tool : tool.name
    const toolMessage = typeof tool === 'string' ? null : tool.message
    const category = getToolCategory(toolName)

    if (currentGroup && currentGroup.name === toolName) {
      currentGroup.count++
      if (toolMessage) {
        currentGroup.messages.push(toolMessage)
      }
    } else {
      if (currentGroup) {
        groups.push(currentGroup)
      }
      currentGroup = {
        name: toolName,
        count: 1,
        category,
        messages: toolMessage ? [toolMessage] : []
      }
    }
  }

  if (currentGroup) {
    groups.push(currentGroup)
  }

  return groups
}

/**
 * Determine the category of a tool based on its name
 *
 * @param {string} toolName - The tool name
 * @returns {string} - Category: 'search', 'web', 'entity', 'graph', or 'default'
 */
export function getToolCategory(toolName) {
  const name = toolName.toLowerCase()

  if (name.includes('search') || name.includes('query')) {
    return 'search'
  }
  if (name.includes('web') || name.startsWith('mcp__web')) {
    return 'web'
  }
  if (name.includes('entity') || name.includes('_info')) {
    return 'entity'
  }
  if (name.includes('graph') || name.includes('knowledge')) {
    return 'graph'
  }

  return 'default'
}

/**
 * Get a human-readable short name for a tool
 *
 * @param {string} toolName - The full tool name
 * @returns {string} - Short display name
 */
export function getToolDisplayName(toolName) {
  // Remove common prefixes
  let name = toolName
    .replace(/^mcp__\w+__/, '') // Remove MCP prefixes like mcp__web_search__
    .replace(/^get_/, '')
    .replace(/_/g, ' ')

  // Capitalize first letter
  return name.charAt(0).toUpperCase() + name.slice(1)
}
