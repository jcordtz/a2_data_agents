# MCP Server for Data Agents

A Model Context Protocol (MCP) server that hosts and orchestrates multiple table-specific data agents across different database types (Oracle, SQL Server, PostgreSQL, IBM DB2), allowing AI models to query databases through a standardized protocol.

> **⚠️ Disclaimer**: This code was generated with AI assistance (AI-generated code). It is provided "AS-IS" under the MIT License without warranty of any kind. Users should review and test thoroughly before production use, validate security implications, and ensure compliance with their organization's policies.

## Features

- **Dynamic Agent Registration**: Register and manage multiple table-specific agents
- **MCP Protocol Support**: Full MCP tools and resources implementation
- **REST API**: Direct HTTP access for non-MCP clients
- **Azure Deployment**: One-click deployment to Azure Container Apps
- **Authentication**: Optional token-based authentication
- **Persistent Registry**: Agents are persisted across restarts

## Quick Start

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start the server:
```bash
python mcp_server.py
```

3. The server will be available at `http://localhost:8080`

### Register an Agent

```bash
./register_agent.sh \
    --agent-id oracle_dbhost_hr_employees \
    --endpoint https://hr-employees-func.azurewebsites.net \
    --api-key your-function-key \
    --table EMPLOYEES \
    --schema HR \
    --db-type oracle \
    --host db.example.com \
    --purview yes \
    --description "Query employee data"
```

> **Note:** The `--purview` flag indicates whether Purview lookup was enabled during agent generation. The actual Purview description lookup requires `db_type`, `host`, `service_name`, `schema`, and `table_name` parameters during agent generation (via `generate_agents.sh`).

### Deploy to Azure

```bash
./deploy.sh \
    --resource-group mcp-rg \
    --location eastus \
    --name my-mcp-server
```

## MCP Tools

| Tool | Description | Arguments |
|------|-------------|-----------|
| `query_table` | Query a table using natural language | `agent_id`, `question` |
| `list_agents` | List all registered agents | none |
| `get_table_info` | Get table metadata and schema | `agent_id` |
| `reset_conversation` | Clear conversation history | `agent_id` |

## MCP Resources

| Resource URI | Description |
|-------------|-------------|
| `agents://list` | List of all registered agents |
| `agents://{id}/info` | Information about a specific agent |
| `agents://{id}/schema` | Table schema for an agent |

## API Endpoints

### MCP Protocol

- `GET /mcp/v1/tools` - List available tools
- `POST /mcp/v1/tools/call` - Execute a tool
- `GET /mcp/v1/resources` - List available resources
- `GET /mcp/v1/resources/read?uri=...` - Read a resource

### REST API

- `POST /api/agents/register` - Register a new agent
- `GET /api/agents` - List all agents
- `GET /api/agents/{id}` - Get agent details
- `DELETE /api/agents/{id}` - Unregister an agent
- `POST /api/query` - Query an agent directly

### Health Check

- `GET /health` - Server health status

## Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `MCP_SERVER_PORT` | Server port | `8080` |
| `MCP_REGISTRY_PATH` | Path to agent registry file | `./agents.json` |
| `MCP_AUTH_TOKEN` | Optional authentication token | none |

## Example: Using with Claude

Configure Claude to use this MCP server by adding it to your MCP configuration:

```json
{
  "mcpServers": {
    "data-agents": {
      "url": "https://your-mcp-server.azurecontainerapps.io/mcp/v1",
      "headers": {
        "Authorization": "Bearer your-token"
      }
    }
  }
}
```

Then you can query data naturally:

> "Using the data-agents server, query the HR employees table to show me the top 10 highest paid employees"

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      AI Model (Claude)                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ MCP Protocol
┌─────────────────────────────────────────────────────────────┐
│                       MCP Server                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Tool Handler │  │   Registry   │  │  Resource    │       │
│  │              │  │   Manager    │  │  Handler     │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ HR_EMPLOYEES │    │ SALES_ORDERS │    │ INVENTORY    │
│    Agent     │    │    Agent     │    │   Agent      │
└──────────────┘    └──────────────┘    └──────────────┘
         │                    │                    │
         └────────────────────┴────────────────────┘
                              │
                              ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
    │  Oracle  │  │SQL Server│  │PostgreSQL│  │ IBM DB2  │
    └──────────┘  └──────────┘  └──────────┘  └──────────┘
```

## Agent Properties

| Property | Description | Example |
|----------|-------------|---------|
| `agent_id` | Unique identifier | `oracle_dbhost_hr_employees` |
| `database_type` | Database type: oracle, mssql, postgres, db2 | `oracle` |
| `host` | Database server hostname | `db.example.com` |
| `schema_name` | Database schema | `HR` |
| `table_name` | Table name | `EMPLOYEES` |
| `purview` | Purview integration enabled (yes/no) | `yes` |
| `endpoint` | Azure Function endpoint URL | `https://...` |
| `api_key` | Azure Function API key | `abc123...` |
| `description` | Human-readable description | `Query employee data` |

## File Structure

```
mcp/
├── mcp_server.py           # Main server implementation
├── register_agent.sh       # Agent registration script
├── deploy.sh               # Azure deployment script
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container image definition
├── __init__.py             # Package init
├── README.md               # This file
└── infra/
    ├── main.bicep          # Azure infrastructure
    └── main.parameters.json
```

## License

MIT License - See LICENSE file for details.
