/**
 * MCP Service - Communication with MCP Server
 * 
 * Handles all API calls to the MCP server for querying data agents.
 * Calls MCP server directly (no backend API layer needed).
 */

// MCP server URL - injected at build time or from environment
const MCP_SERVER_URL = import.meta.env.VITE_MCP_SERVER_URL || ''
const MCP_AUTH_TOKEN = import.meta.env.VITE_MCP_AUTH_TOKEN || ''

// Validate and warn about suspicious URLs
if (MCP_SERVER_URL) {
  console.log('MCP Service initialized:', {
    serverUrl: MCP_SERVER_URL,
    hasAuthToken: MCP_AUTH_TOKEN ? `yes (${MCP_AUTH_TOKEN.slice(0, 8)}...)` : 'no',
  })
  
  // Warn if URL looks suspicious (documentation links, localhost when deployed, etc)
  if (MCP_SERVER_URL.includes('aka.ms') || MCP_SERVER_URL.includes('docs.microsoft')) {
    console.error('❌ ERROR: MCP_SERVER_URL appears to be a documentation link:', MCP_SERVER_URL)
    console.error('   This usually means the build did not receive the correct MCP URL')
    console.error('   The chatbot needs to be rebuilt with the correct VITE_MCP_SERVER_URL')
  } else if (MCP_SERVER_URL.includes('localhost') || MCP_SERVER_URL.includes('127.0.0.1')) {
    console.warn('⚠️  Warning: MCP_SERVER_URL points to localhost')
    console.warn('   This will not work when accessed from a browser (need Azure-hosted MCP server)')
  } else if (!MCP_SERVER_URL.includes('https://')) {
    console.warn('⚠️  Warning: MCP_SERVER_URL does not use HTTPS:', MCP_SERVER_URL)
    console.warn('   This may cause mixed content errors in production')
  }
} else {
  console.warn('⚠️  MCP Server URL is not configured')
}

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
    console.error('MCP Server URL not configured')
    console.error('  VITE_MCP_SERVER_URL env var:', process.env.VITE_MCP_SERVER_URL)
    console.error('  import.meta.env.VITE_MCP_SERVER_URL:', import.meta.env.VITE_MCP_SERVER_URL)
    throw new Error('MCP Server URL is not configured. Check build environment variables and rebuild.')
  }
  
  try {
    const url = `${MCP_SERVER_URL}/api/agents`
    console.log('🔍 Fetching agents from:', url)
    console.log('   Authorization header:', getMcpHeaders().Authorization ? 'Bearer token set' : 'No auth')
    
    const response = await fetch(url, {
      method: 'GET',
      headers: getMcpHeaders(),
    })
    
    if (!response.ok) {
      const errorText = await response.text().catch(() => '(no response body)')
      console.error(`❌ HTTP ${response.status}: ${errorText}`)
      
      if (response.status === 401) {
        throw new Error('Authentication failed (401). Check MCP auth token.')
      } else if (response.status === 403) {
        throw new Error('Access denied (403). Check CORS and authentication.')
      } else if (response.status >= 500) {
        throw new Error(`MCP Server error (${response.status}). Server may be down.`)
      } else {
        throw new Error(`Failed to fetch agents: ${response.status} - ${errorText}`)
      }
    }
    
    const data = await response.json()
    console.log('✅ Agents received:', data)

    // Normalize agent fields: MCP server uses agent_id; UI expects id and name
    const agents = Array.isArray(data) ? data : data.agents || []
    return agents.map(a => ({
      ...a,
      id: a.agent_id || a.id,
      name: a.description || `${a.schema_name}.${a.table_name}` || a.agent_id,
    }))
  } catch (error) {
    console.error('❌ Error fetching agents:', error.message)
    
    if (error.message.includes('Failed to fetch')) {
      console.error('   Network error - Server may be unreachable')
      throw new Error(`Cannot connect to MCP server at ${MCP_SERVER_URL}.\n\nPossible causes:\n• Server is offline\n• Network/firewall blocking access\n• CORS not enabled\n• Wrong URL configured`)
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
