/**
 * MCP Service - Communication with MCP Server
 * 
 * Handles all API calls to the MCP server for querying data agents.
 */

const API_BASE_URL = '/api'

/**
 * Fetch list of available agents from the MCP server
 * @returns {Promise<Array>} List of agents
 */
export async function fetchAgents() {
  try {
    const response = await fetch(`${API_BASE_URL}/agents`)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch agents: ${response.status}`)
    }
    
    const data = await response.json()
    return data.agents || data || []
  } catch (error) {
    console.error('Error fetching agents:', error)
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
    const response = await fetch(`${API_BASE_URL}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        agentId,
        question,
      }),
    })
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.error || `Query failed: ${response.status}`)
    }
    
    return await response.json()
  } catch (error) {
    console.error('Error querying agent:', error)
    throw error
  }
}

/**
 * Check health status of the API
 * @returns {Promise<Object>} Health status
 */
export async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`)
    
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.status}`)
    }
    
    return await response.json()
  } catch (error) {
    console.error('Error checking health:', error)
    throw error
  }
}
