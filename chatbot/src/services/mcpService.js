/**
 * MCP Service - Communication with MCP Server
 * 
 * Handles all API calls to the MCP server for querying data agents.
 * Calls MCP server directly (no backend API layer needed).
 */

// MCP server URL - injected at build time or from environment
const MCP_SERVER_URL = import.meta.env.VITE_MCP_SERVER_URL || ''
const MCP_AUTH_TOKEN = import.meta.env.VITE_MCP_AUTH_TOKEN || ''

// Log configuration for debugging (token is partially hidden)
console.log('MCP Service initialized:', {
  serverUrl: MCP_SERVER_URL || '(not configured)',
  hasAuthToken: MCP_AUTH_TOKEN ? `yes (${MCP_AUTH_TOKEN.slice(0, 8)}...)` : 'no',
})

/**
 * Get headers for MCP requests
 */
function getMcpHeaders() {
  const headers = {
    'Content-Type': 'application/json',
  }
  if (MCP_AUTH_TOKEN && MCP_AUTH_TOKEN !== 'not-configured') {
    headers['Authorization'] = `Bearer ${MCP_AUTH_TOKEN}`
  }
  return headers
}

/**
 * Fetch list of available agents from the MCP server
 * @returns {Promise<Array>} List of agents
 */
export async function fetchAgents() {
  if (!MCP_SERVER_URL) {
    throw new Error('MCP Server URL is not configured. Check build environment variables.')
  }
  
  try {
    console.log('Fetching agents from:', `${MCP_SERVER_URL}/mcp/v1/tools/call`)
    const response = await fetch(`${MCP_SERVER_URL}/mcp/v1/tools/call`, {
      method: 'POST',
      headers: getMcpHeaders(),
      body: JSON.stringify({
        name: 'list_agents',
        arguments: {},
      }),
    })
    
    if (!response.ok) {
      const errorText = await response.text().catch(() => '')
      console.error('Failed to fetch agents:', response.status, errorText)
      throw new Error(`Failed to fetch agents: ${response.status} - ${errorText || 'Server error'}`)
    }
    
    const data = await response.json()
    console.log('Agents response:', data)
    return data.content?.agents || data.agents || []
  } catch (error) {
    console.error('Error fetching agents:', error)
    if (error.message.includes('Failed to fetch')) {
      throw new Error(`Cannot connect to MCP server at ${MCP_SERVER_URL}. Check if the server is running and CORS is enabled.`)
    }
    throw error
  }
}

/**
 * Send a query to a specific agent
 * @param {string} agentId - The ID of the agent to query
 * @param {string} question - The natural language question
 * @returns {Promise<Object>} The response from the agent
 */
export async function queryAgent(agentId, question) {
  try {
    const response = await fetch(`${MCP_SERVER_URL}/mcp/v1/tools/call`, {
      method: 'POST',
      headers: getMcpHeaders(),
      body: JSON.stringify({
        name: 'query_table',
        arguments: {
          agent_id: agentId,
          question: question,
        },
      }),
    })
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.error || `Query failed: ${response.status}`)
    }
    
    const data = await response.json()
    return {
      success: true,
      data: data.content || data,
    }
  } catch (error) {
    console.error('Error querying agent:', error)
    throw error
  }
}

/**
 * Check health status of the MCP server
 * @returns {Promise<Object>} Health status
 */
export async function checkHealth() {
  try {
    const response = await fetch(`${MCP_SERVER_URL}/health`)
    
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.status}`)
    }
    
    return await response.json()
  } catch (error) {
    console.error('Error checking health:', error)
    throw error
  }
}
