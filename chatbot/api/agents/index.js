/**
 * Agents API Endpoint
 * 
 * Lists available agents from the MCP Server.
 * 
 * GET /api/agents
 */

const fetch = require('node-fetch')

const MCP_SERVER_URL = process.env.MCP_SERVER_URL || 'http://localhost:8080'
const MCP_AUTH_TOKEN = process.env.MCP_AUTH_TOKEN || ''

module.exports = async function (context, req) {
  context.log('Agents endpoint called')

  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    context.res = {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      },
    }
    return
  }

  try {
    const headers = {
      'Content-Type': 'application/json',
    }
    
    if (MCP_AUTH_TOKEN) {
      headers['Authorization'] = `Bearer ${MCP_AUTH_TOKEN}`
    }

    // Fetch agents from the direct REST API
    const directResponse = await fetch(`${MCP_SERVER_URL}/api/agents`, {
      method: 'GET',
      headers,
    })

    if (directResponse.ok) {
      const data = await directResponse.json()
      const agents = Array.isArray(data) ? data : data.agents || []
      
      context.res = {
        status: 200,
        body: { agents },
        headers: { 'Content-Type': 'application/json' },
      }
      return
    }

    // If both fail, return empty list
    context.log.warn('Could not fetch agents from MCP server')
    
    context.res = {
      status: 200,
      body: { agents: [] },
      headers: { 'Content-Type': 'application/json' },
    }
  } catch (error) {
    context.log.error('Agents error:', error)
    
    context.res = {
      status: 500,
      body: { 
        error: 'Failed to fetch agents',
        message: error.message,
      },
      headers: { 'Content-Type': 'application/json' },
    }
  }
}
