# MCP Server to Agent Communication Flow

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Chatbot UI (Web)                        │
│  - Select agent                                                 │
│  - Enter natural language question                              │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      │ POST /mcp/v1/tools/call
                      │ { name: "query_table", arguments: {...} }
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│              MCP Server (Python/FastAPI)                        │
│  - Route query_table tool call                                  │
│  - Lookup agent in registry                                     │
│  - Call agent endpoint                                          │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      │ POST /api/query
                      │ { question: "...", reset_conversation: false }
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│          Agent Azure Function (Node.js/Python)                 │
│  - Receive question                                             │
│  - Initialize or retrieve DataAgent                             │
│  - Call agent.ask(question)                                     │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      │ Chat completion with tools
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│            Azure OpenAI (GPT-4o)                                │
│  - Analyze question                                             │
│  - Select appropriate tools/functions                           │
│  - Generate function calls                                      │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      │ { tool_calls: [...] }
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│              DataAgent (Python)                                 │
│  - Execute tool functions                                       │
│  - Supported tools:                                             │
│    - list_tables()                                              │
│    - get_table_structure(table_name)                            │
│    - execute_query(sql)                                         │
│    - get_table_data(table_name)                                 │
│    - analyze_dataframe(query, analysis_type)                    │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      │ SQL query or pandas operation
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│           Database (Oracle/SQL Server/PostgreSQL/DB2)          │
│  - Execute SQL query                                            │
│  - Return results as DataFrame                                  │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      │ Results
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│              DataAgent (Python)                                 │
│  - Format results                                               │
│  - Generate natural language explanation                        │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      │ { answer: "...", sql_executed: "...", data: [...] }
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│          Agent Azure Function (Node.js/Python)                 │
│  - Return response to caller                                    │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      │ { answer, sql_executed, data }
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│              MCP Server (Python/FastAPI)                        │
│  - Format as MCPToolResult                                      │
│  - Return to caller                                             │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      │ MCPToolResult with answer
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│                        Chatbot UI (Web)                        │
│  - Display answer to user                                       │
│  - Show SQL that was executed                                   │
│  - Show data preview                                            │
└─────────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Chatbot UI (Frontend)
**Location:** `chatbot/src/`

**Flow:**
- User selects an agent from dropdown
- User types a question
- `useChat` hook calls `queryAgent(agentId, question)`
- Question is sent to MCP server

**Key Files:**
- `App.jsx` - Agent selection
- `useChat.js` - Query management
- `mcpService.js` - MCP communication

### 2. MCP Server
**Location:** `mcp/mcp_server.py`

**Responsibilities:**
- Maintain registry of agents (stored in `agents.json`)
- Route MCP tool calls to appropriate handlers
- Call agent endpoints to execute queries
- Provide diagnostics and agent discovery

**Key Functions:**
- `query_table(agent_id, question)` - Main query tool
- `list_agents()` - List available agents
- `get_table_info(agent_id)` - Get table metadata
- `reset_conversation(agent_id)` - Clear conversation history

**Configuration:**
- `MCP_REGISTRY_PATH` - Where to store agent registry
- `MCP_AUTH_TOKEN` - Optional authentication

### 3. Agent (Azure Function)
**Location:** `agents/function_app.py` + `agents/data_agent.py`

**Endpoints:**
- `POST /api/query` - Main query endpoint
- `GET /api/tables` - List tables
- `GET /api/table/{name}/structure` - Get table schema
- `GET /api/health` - Health check
- `POST /api/reset` - Reset conversation

**Initialization:**
- Reads config from environment variables
- Creates DataAgent instance on first request (lazy initialization)
- Maintains conversation history

### 4. DataAgent (Query Engine)
**Location:** `agents/data_agent.py`

**Key Methods:**
- `ask(question)` - Process natural language question
  - Sends question + tools to Azure OpenAI
  - Iterates up to max_iterations times
  - Executes tool calls from OpenAI
  - Returns final answer with SQL and results

**Available Tools:**
1. `list_tables()` - List all tables in database
2. `get_table_structure(table_name)` - Get column info
3. `execute_query(query)` - Execute SELECT query
4. `get_table_data(table_name, ...)` - Get table data
5. `get_table_constraints(table_name)` - Get PK/FK info
6. `analyze_dataframe(query, analysis_type)` - Statistical analysis
7. `describe_table(table_name)` - Natural language description
8. `get_table_comments(table_name)` - Get Oracle comments

## Query Processing Flow

### Example: "How many employees are there in the employees table?"

```
1. Chatbot UI → MCP Server
   POST /mcp/v1/tools/call
   {
     "name": "query_table",
     "arguments": {
       "agent_id": "hr_employees",
       "question": "How many employees are there in the employees table?"
     }
   }

2. MCP Server → Agent Azure Function
   POST /api/query
   {
     "question": "How many employees are there in the employees table?",
     "reset_conversation": false
   }

3. Agent Function → DataAgent
   agent.ask("How many employees are there in the employees table?")

4. DataAgent → Azure OpenAI
   Chat completion with:
   - messages: [
       {"role": "system", "content": "You are a helpful data analyst..."},
       {"role": "user", "content": "How many employees..."}
     ]
   - tools: [list_tables, get_table_structure, execute_query, ...]
   - tool_choice: "auto"

5. Azure OpenAI Response
   {
     "tool_calls": [
       {
         "id": "call_123",
         "function": {
           "name": "execute_query",
           "arguments": "{\"query\": \"SELECT COUNT(*) FROM EMPLOYEES\"}"
         }
       }
     ]
   }

6. DataAgent Executes Tool
   execute_query("SELECT COUNT(*) FROM EMPLOYEES")
   → Returns: "Query returned 100 rows. Result: 100"

7. DataAgent → Azure OpenAI (with tool result)
   Chat completion with:
   - All previous messages
   - Tool result: {"role": "tool", "tool_call_id": "call_123", "content": "100"}

8. Azure OpenAI Response (Final)
   {
     "tool_calls": null,  // No more tools needed
     "content": "There are 100 employees in the EMPLOYEES table."
   }

9. Agent → MCP Server
   {
     "answer": "There are 100 employees in the EMPLOYEES table.",
     "sql_executed": "SELECT COUNT(*) FROM EMPLOYEES",
     "data": [{"COUNT(*)": 100}],
     "tool_calls": [{"tool": "execute_query", "args": {...}}]
   }

10. MCP Server → Chatbot UI
    MCPToolResult with content showing answer, SQL, and data
```

## Configuration

### Azure Function Configuration (local.settings.json or App Settings)

```json
{
  "Values": {
    "AzureWebJobsStorage": "...",
    
    "AZURE_OPENAI_ENDPOINT": "https://your-resource.openai.azure.com/",
    "AZURE_OPENAI_API_KEY": "your-api-key",
    "AZURE_OPENAI_API_VERSION": "2024-11-01",
    "AZURE_OPENAI_DEPLOYMENT": "gpt-4o",
    
    "DATABASE_HOST": "your-db-host",
    "DATABASE_TYPE": "oracle",
    "CONNECTION_ID": "optional-connection-id",
    "SECURITY_DIR": "optional-path-to-security-dir",
    
    "AGENT_CONFIG_PATH": "agent_config.ini"
  }
}
```

### Agent Config File (agent_config.ini)

```ini
[azure_openai]
endpoint = https://your-resource.openai.azure.com/
api_key = your-api-key
api_version = 2024-11-01
deployment_name = gpt-4o

[agent]
max_iterations = 10
temperature = 0.0
system_prompt = You are a helpful data analyst assistant.

[database]
country = US
```

## Error Handling

### In DataAgent.ask()

**Potential errors:**
1. Azure OpenAI not configured → Returns error message
2. OpenAI API error → Returns error wrapped in response
3. Database error in tool execution → Returns error from database
4. Max iterations reached → Returns iteration limit error

**Improvements Made:**
- Better logging at each step
- Detailed error messages with context
- Graceful fallbacks for missing configuration

### In Azure Function

**Improvements Made:**
- Better request validation
- Comprehensive error logging with stack traces
- Proper HTTP status codes
- Error information in response

### In MCP Server

**Improvements Made:**
- HTTP status validation
- Timeout handling (120 second timeout)
- Endpoint connectivity diagnostics
- Detailed error messages

## Testing Each Component

### 1. Test MCP Server
```bash
# Health check
curl http://localhost:8080/health

# List agents
curl http://localhost:8080/api/agents

# Test diagnostics
curl "http://localhost:8080/api/diagnostics/hr_employees"

# Test query
curl -X POST "http://localhost:8080/mcp/v1/tools/call" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "query_table",
    "arguments": {
      "agent_id": "hr_employees",
      "question": "How many tables are in the database?"
    }
  }'
```

### 2. Test Agent Directly
```bash
curl -X POST "https://your-function.azurewebsites.net/api/query" \
  -H "x-functions-key: your-function-key" \
  -H "Content-Type: application/json" \
  -d '{"question": "How many tables are available?"}'
```

### 3. Test DataAgent Locally
```bash
python -c "
from agents.data_agent import DataAgent

agent = DataAgent('your-host', db_type='oracle')
response = agent.ask('How many employees are there?')
print(f'Answer: {response.answer}')
print(f'SQL: {response.sql_executed}')
agent.close()
"
```

## Troubleshooting Checklist

- [ ] MCP Server is running and healthy
- [ ] Agents are registered in MCP registry
- [ ] Agent endpoints are reachable and returning health checks
- [ ] Azure OpenAI credentials are correct
- [ ] Database credentials are correct
- [ ] Azure Function logs show no configuration errors
- [ ] Network allows communication between components
- [ ] Tool definitions are properly formatted
