# Troubleshooting: "No Response Returned" Issue

## Problem
When asking questions like "How many employees are there in the employees table?", you get "no response returned".

## Root Causes & Solutions

### 1. **Azure OpenAI Configuration Missing**

The agent cannot communicate with Azure OpenAI to translate natural language to SQL.

**Check:**
```bash
# Verify these environment variables are set in your Azure Function or local.settings.json
- AZURE_OPENAI_ENDPOINT      (e.g., https://your-resource.openai.azure.com/)
- AZURE_OPENAI_API_KEY       (your API key)
- AZURE_OPENAI_API_VERSION   (e.g., 2024-11-01)
- AZURE_OPENAI_DEPLOYMENT    (deployment name, e.g., gpt-4o)
```

**Fix:**
```bash
# For local development, update local.settings.json:
{
  "Values": {
    "AZURE_OPENAI_ENDPOINT": "https://your-resource.openai.azure.com/",
    "AZURE_OPENAI_API_KEY": "your-api-key-here",
    "AZURE_OPENAI_API_VERSION": "2024-11-01",
    "AZURE_OPENAI_DEPLOYMENT": "gpt-4o",
    "DATABASE_HOST": "your-db-host",
    "DATABASE_TYPE": "oracle"
  }
}
```

### 2. **Database Configuration Issues**

The agent can't connect to the database.

**Check:**
```bash
# Verify database environment variables:
- DATABASE_HOST          (hostname, not full connection string)
- DATABASE_TYPE          (oracle, mssql, postgres, or db2)
- CONNECTION_ID          (optional, for security XML files)
- SECURITY_DIR           (optional, path to security directory)
```

**Verify connection:**
```bash
# Test your database connection manually
cd agents/
python -c "
from data_agent import DataAgent
with DataAgent('your-host', db_type='oracle') as agent:
    print('Connection successful!')
"
```

### 3. **Agent Endpoint Not Reachable**

The MCP server can't reach the agent's Azure Function endpoint.

**Check:**
```bash
# Use the diagnostics endpoint:
curl "http://localhost:8080/api/diagnostics/your-agent-id"

# Should return:
{
  "endpoint_health": { "status": "ok", "status_code": 200 },
  "list_tables": { "status": "ok", "table_count": 5, ... }
}
```

**If endpoint_health shows error:**
1. Verify the endpoint URL is correct (should be `https://your-function.azurewebsites.net`)
2. Check the API key (`x-functions-key` header) is correct
3. Ensure the function app is running and accessible

### 4. **Agent Registration Issues**

The agent isn't properly registered in the MCP server.

**Check:**
```bash
# List all registered agents:
curl "http://localhost:8080/api/agents"

# Should show your agent. If empty, register it:
curl -X POST "http://localhost:8080/api/agents/register" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "hr_employees",
    "table_name": "EMPLOYEES",
    "schema_name": "HR",
    "database_type": "oracle",
    "host": "your-host",
    "endpoint": "https://your-function.azurewebsites.net",
    "api_key": "your-function-key"
  }'
```

## Diagnostic Workflow

### Step 1: Check MCP Server Health
```bash
curl http://localhost:8080/health
# Expected: { "status": "healthy", "agents_registered": 1 }
```

### Step 2: Check Agent Registration
```bash
curl http://localhost:8080/api/agents
# Should list your agents with all required fields
```

### Step 3: Test Agent Diagnostics
```bash
curl "http://localhost:8080/api/diagnostics/hr_employees"
# Check all tests pass:
# - endpoint_health: ok
# - list_tables: ok
```

### Step 4: Check Azure Function Logs
In Azure Portal:
1. Go to your Function App
2. Monitor → Log stream
3. Look for error messages when making queries
4. Check for Azure OpenAI authentication errors

### Step 5: Test Agent Directly
```bash
# Call the agent's query endpoint directly
curl -X POST "https://your-function.azurewebsites.net/api/query" \
  -H "x-functions-key: your-function-key" \
  -H "Content-Type: application/json" \
  -d '{"question": "How many tables are in the database?"}'

# Should return:
{
  "answer": "...",
  "sql_executed": "SELECT ...",
  "tool_calls": [...]
}
```

### Step 6: Check Logs for Agent Errors
```bash
# In Azure Function Log Stream, look for:
- "Processing question:" - indicates question received
- "Error in iteration:" - indicates OpenAI call failed
- "Error processing query:" - indicates general error
```

## Common Error Messages

### "Azure OpenAI configuration incomplete"
- Solution: Set all required environment variables
- Check: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_API_VERSION`, `AZURE_OPENAI_DEPLOYMENT`

### "Error querying agent: Connection refused"
- Solution: Verify function URL is correct and publicly accessible
- Check: Function App is running and network allows outbound HTTPS

### "Database connection failed"
- Solution: Verify credentials and connection string in security XML files
- Check: Database host is reachable from Azure Function

### "Tool call failed"
- Solution: Check Azure Function logs for the specific tool error
- Common: Database query syntax error (wrong SQL for your database type)

## Enable Verbose Logging

### For MCP Server
```bash
# Run with debug logging
export LOG_LEVEL=DEBUG
python mcp/mcp_server.py
```

### For Azure Function (local)
```bash
# In local.settings.json
{
  "logging": {
    "level": "debug"
  }
}
```

## Performance Tuning

If queries are slow:

1. **Increase timeouts**
   - MCP server timeout: 120s (already set)
   - Azure Function timeout: increase in host.json
   - Query timeout: adjust in database connector

2. **Monitor Azure OpenAI**
   - Check if calls are being throttled
   - Verify correct deployment is being used

3. **Database optimization**
   - Add indexes on frequently queried columns
   - Check query execution plan in database

## Still Having Issues?

1. Check the session memory: `/memories/session/analysis.md`
2. Review MCP server logs for detailed error information
3. Test each component independently:
   - MCP Server → healthy
   - Agent endpoint → responding
   - Database connection → working
   - Azure OpenAI → configured
