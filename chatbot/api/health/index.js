/**
 * Health API Endpoint
 * 
 * Health check endpoint for the chatbot API.
 * 
 * GET /api/health
 */

const fetch = require('node-fetch')

const MCP_SERVER_URL = process.env.MCP_SERVER_URL || 'http://localhost:8080'

module.exports = async function (context, req) {
  context.log('Health endpoint called')

  try {
    // Check MCP server connectivity
    let mcpStatus = 'unknown'
    
    try {
      // Simple timeout wrapper for node-fetch
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error('timeout')), 5000)
      )
      const fetchPromise = fetch(`${MCP_SERVER_URL}/health`, { method: 'GET' })
      const mcpResponse = await Promise.race([fetchPromise, timeoutPromise])
      mcpStatus = mcpResponse.ok ? 'healthy' : 'unhealthy'
    } catch (error) {
      mcpStatus = 'unreachable'
    }

    context.res = {
      status: 200,
      body: {
        status: 'healthy',
        timestamp: new Date().toISOString(),
        version: '1.0.0',
        dependencies: {
          mcpServer: {
            url: MCP_SERVER_URL,
            status: mcpStatus,
          },
        },
      },
      headers: { 'Content-Type': 'application/json' },
    }
  } catch (error) {
    context.log.error('Health check error:', error)
    
    context.res = {
      status: 503,
      body: {
        status: 'unhealthy',
        timestamp: new Date().toISOString(),
        error: error.message,
      },
      headers: { 'Content-Type': 'application/json' },
    }
  }
}
