/**
 * Query API Endpoint
 * 
 * Proxies queries to the MCP Server for a specific agent.
 * 
 * POST /api/query
 * Body: { agentId: string, question: string }
 */

const MCP_SERVER_URL = process.env.MCP_SERVER_URL || 'http://localhost:8080'
const MCP_AUTH_TOKEN = process.env.MCP_AUTH_TOKEN || ''

module.exports = async function (context, req) {
  context.log('Query endpoint called')

  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    context.res = {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      },
    }
    return
  }

  try {
    const { agentId, question } = req.body || {}

    if (!agentId) {
      context.res = {
        status: 400,
        body: { error: 'agentId is required' },
        headers: { 'Content-Type': 'application/json' },
      }
      return
    }

    if (!question) {
      context.res = {
        status: 400,
        body: { error: 'question is required' },
        headers: { 'Content-Type': 'application/json' },
      }
      return
    }

    // Call MCP Server
    const headers = {
      'Content-Type': 'application/json',
    }
    
    if (MCP_AUTH_TOKEN) {
      headers['Authorization'] = `Bearer ${MCP_AUTH_TOKEN}`
    }

    const mcpResponse = await fetch(`${MCP_SERVER_URL}/mcp/v1/tools/call`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        name: 'query_table',
        arguments: {
          agent_id: agentId,
          question: question,
        },
      }),
    })

    if (!mcpResponse.ok) {
      const errorText = await mcpResponse.text()
      context.log.error('MCP Server error:', mcpResponse.status, errorText)
      
      context.res = {
        status: mcpResponse.status,
        body: { 
          error: 'Failed to query MCP server',
          details: errorText,
        },
        headers: { 'Content-Type': 'application/json' },
      }
      return
    }

    const data = await mcpResponse.json()
    
    context.res = {
      status: 200,
      body: {
        success: true,
        data: data.content || data,
      },
      headers: { 'Content-Type': 'application/json' },
    }
  } catch (error) {
    context.log.error('Query error:', error)
    
    context.res = {
      status: 500,
      body: { 
        error: 'Internal server error',
        message: error.message,
      },
      headers: { 'Content-Type': 'application/json' },
    }
  }
}
