# Oracle Data Agents

**AI-powered natural language querying for Oracle databases, deployed as Azure Functions with MCP orchestration.**

An intelligent system that enables natural language querying of Oracle databases using Azure OpenAI. Generate table-specific agents automatically, deploy them to Azure, and orchestrate them through a Model Context Protocol (MCP) server.

> **⚠️ Disclaimer**: This code was generated with AI assistance (AI-generated code). It is provided "AS-IS" under the MIT License without warranty of any kind. Users should review and test thoroughly before production use, validate security implications for their specific use case, and ensure compliance with their organization's policies. See the [LICENSE](LICENSE) file for full license text.

---

## Features

- **Natural Language Queries**: Ask questions in plain English (or 30+ other languages)
- **Automatic SQL Generation**: AI translates questions to optimized Oracle SQL
- **Table-Specific Agents**: Generate dedicated agents for individual tables
- **Azure Functions Deployment**: Serverless, scalable Azure hosting
- **MCP Server Orchestration**: Unified interface for multiple agents
- **SQLAlchemy + Thick Mode**: Robust Oracle connectivity with connection pooling
- **Infrastructure as Code**: Bicep templates for Azure deployment

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AI Models (Claude, etc.)                        │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │ MCP Protocol
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              MCP Server                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Tool Handler │  │   Registry   │  │  Resources   │  │     Auth     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │ HTTP/REST
          ┌───────────────────────┼───────────────────────┐
          ▼                       ▼                       ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│  HR_EMPLOYEES    │   │   SALES_ORDERS   │   │    INVENTORY     │
│  Azure Function  │   │  Azure Function  │   │  Azure Function  │
│    Data Agent    │   │    Data Agent    │   │    Data Agent    │
└────────┬─────────┘   └────────┬─────────┘   └────────┬─────────┘
         │                      │                      │
         └──────────────────────┼──────────────────────┘
                                │ SQLAlchemy (Thick Mode)
                                ▼
                  ┌─────────────────────────┐
                  │    Oracle Database      │
                  │  (HR, SALES, INVENTORY) │
                  └─────────────────────────┘
```

---

## Project Structure

```
a2_data_agents/
│
├── oracle/                        # Oracle Database Module
│   ├── __init__.py                # Module exports
│   ├── oracle_connector.py        # SQLAlchemy-based connector (thick mode)
│   └── oracle_config.ini          # Database connection configuration
│
├── agents/                        # AI Agent Module
│   ├── __init__.py                # Module exports
│   ├── data_agent.py              # Azure OpenAI-powered data agent
│   ├── function_app.py            # Azure Function HTTP endpoints
│   └── agent_generator.py         # Table-specific agent generator
│
├── mcp/                           # MCP Server Module
│   ├── __init__.py                # Module exports
│   ├── mcp_server.py              # FastAPI MCP server implementation
│   ├── register_agent.sh          # Single agent registration
│   ├── register_all_agents.sh     # Batch agent registration
│   ├── deploy.sh                  # Azure Container Apps deployment
│   ├── Dockerfile                 # Container image definition
│   ├── requirements.txt           # MCP server dependencies
│   ├── README.md                  # MCP server documentation
│   └── infra/                     # MCP infrastructure
│       ├── main.bicep             # Container Apps + ACR + Storage
│       └── main.parameters.json   # Deployment parameters
│
├── infra/                         # Main Infrastructure
│   ├── main.bicep                 # Azure Function + OpenAI + Storage
│   └── main.parameters.json       # Deployment parameters
│
├── agent_config.ini               # Main agent configuration template
├── deploy.sh                      # Main deployment script
├── generate_agents.sh             # Batch agent generation from CSV
├── sample_tables.csv              # Example table list for generation
├── requirements.txt               # Python dependencies
├── Dockerfile                     # Container image for main agent
├── host.json                      # Azure Functions host configuration
├── local.settings.json            # Local development settings
├── LICENSE                        # MIT License
└── README.md                      # This file
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Oracle Instant Client (for thick mode)
- Azure CLI
- Azure subscription with:
  - Azure OpenAI access
  - Permissions to create resources

### 1. Clone and Install

```bash
git clone https://github.com/jcordtz/a2_data_agents.git
cd a2_data_agents
pip install -r requirements.txt
```

### 2. Configure Oracle Connection

Edit `oracle/oracle_config.ini`:

```ini
[oracle]
host = your-oracle-host
port = 1521
service_name = YOUR_SERVICE
schema = YOUR_SCHEMA
username = your_username
password = your_password
```

### 3. Configure Azure OpenAI

Edit `agent_config.ini`:

```ini
[azure_openai]
endpoint = https://your-openai.openai.azure.com/
api_key = your-api-key
deployment_name = gpt-4o
api_version = 2024-02-15-preview

[agent]
language = English
```

### 4. Run Locally

```bash
# Start the main data agent
cd agents
func start
```

---

## Usage Examples

### Query Data via HTTP API

```bash
# Ask a natural language question
curl -X POST http://localhost:7071/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Show me the top 10 employees by salary"}'

# List available tables
curl http://localhost:7071/api/tables

# Get table structure
curl http://localhost:7071/api/table/EMPLOYEES/structure

# Reset conversation
curl -X POST http://localhost:7071/api/reset
```

### Generate Table-Specific Agents

```bash
# Generate a single agent
python agents/agent_generator.py \
  --config oracle/oracle_config.ini \
  --schema HR \
  --table EMPLOYEES \
  --output ./generated_agents/hr_employees

# Generate multiple agents from CSV
./generate_agents.sh sample_tables.csv --output ./generated_agents
```

### Deploy to Azure

```bash
# Deploy main agent
./deploy.sh

# Or with custom settings
RESOURCE_GROUP=mygroup LOCATION=westus2 ./deploy.sh
```

### MCP Server Operations

```bash
cd mcp

# Start MCP server locally
python mcp_server.py

# Register an agent
./register_agent.sh \
  --agent-id hr_employees \
  --endpoint https://hr-employees-func.azurewebsites.net \
  --api-key YOUR_FUNCTION_KEY

# Batch register all generated agents
./register_all_agents.sh --agents-dir ../generated_agents

# Deploy MCP server to Azure
./deploy.sh --resource-group mcp-rg --location eastus
```

### MCP Tool Usage (for AI Models)

```json
// List available tools
GET /mcp/v1/tools

// Query a table
POST /mcp/v1/tools/call
{
  "name": "query_table",
  "arguments": {
    "agent_id": "hr_employees",
    "question": "What is the average salary by department?"
  }
}

// List registered agents
POST /mcp/v1/tools/call
{
  "name": "list_agents",
  "arguments": {}
}
```

---

## Component Documentation

| Component | Description | Documentation |
|-----------|-------------|---------------|
| **Oracle Connector** | SQLAlchemy-based Oracle connectivity with thick mode, connection pooling, and DataFrame support | See docstrings in [oracle/oracle_connector.py](oracle/oracle_connector.py) |
| **Data Agent** | Azure OpenAI-powered agent for natural language to SQL translation | See docstrings in [agents/data_agent.py](agents/data_agent.py) |
| **Function App** | Azure Function HTTP endpoints for the data agent | See docstrings in [agents/function_app.py](agents/function_app.py) |
| **Agent Generator** | Generates standalone Azure Function agents for specific tables | See docstrings in [agents/agent_generator.py](agents/agent_generator.py) |
| **MCP Server** | FastAPI-based Model Context Protocol server | See [mcp/README.md](mcp/README.md) |

---

## Configuration Reference

### Oracle Configuration (`oracle/oracle_config.ini`)

```ini
[oracle]
host = localhost          # Oracle host
port = 1521               # Oracle port
service_name = ORCL       # Oracle service name
schema = HR               # Default schema
username = hr_user        # Database username
password = secret         # Database password
```

### Agent Configuration (`agent_config.ini`)

```ini
[azure_openai]
endpoint = https://your-openai.openai.azure.com/
api_key = your-api-key
deployment_name = gpt-4o
api_version = 2024-02-15-preview

[agent]
language = English        # Response language (30+ supported)
max_tokens = 4096         # Max response tokens
temperature = 0.7         # Response creativity (0-1)

[oracle]
# Can also include Oracle settings here
host = localhost
port = 1521
service_name = ORCL
```

### MCP Server Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_SERVER_PORT` | Server port | `8080` |
| `MCP_REGISTRY_PATH` | Path to agent registry JSON | `./agents.json` |
| `MCP_AUTH_TOKEN` | Optional authentication token | (none) |

---

## API Reference

### Data Agent Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/query` | POST | Query database with natural language |
| `/api/tables` | GET | List available tables |
| `/api/table/{name}/structure` | GET | Get table schema |
| `/api/table/{name}/info` | GET | Get table description |
| `/api/health` | GET | Health check |
| `/api/reset` | POST | Reset conversation history |

### MCP Server Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp/v1/tools` | GET | List available MCP tools |
| `/mcp/v1/tools/call` | POST | Execute an MCP tool |
| `/mcp/v1/resources` | GET | List MCP resources |
| `/mcp/v1/resources/read` | GET | Read an MCP resource |
| `/api/agents/register` | POST | Register a new agent |
| `/api/agents` | GET | List all agents |
| `/api/agents/{id}` | GET/DELETE | Get/remove agent |
| `/api/query` | POST | Direct query endpoint |
| `/health` | GET | Health check |

---

## Development

### Running Tests

```bash
# Install dev dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/
```

### Local Development

```bash
# Start Oracle connector test
python -c "from oracle import OracleConnector; print('OK')"

# Test data agent
python -c "from agents import DataAgent; print('OK')"

# Start Azure Functions locally
cd agents && func start

# Start MCP server locally
cd mcp && python mcp_server.py
```

---

## Deployment

### Azure Resources Created

**Main Agent (`infra/main.bicep`):**
- Azure Function App (Python 3.11)
- Azure OpenAI Service
- App Service Plan
- Storage Account
- Application Insights

**MCP Server (`mcp/infra/main.bicep`):**
- Azure Container Apps
- Azure Container Registry
- Log Analytics Workspace
- Storage Account (for registry)

### Deployment Commands

```bash
# Deploy main agent infrastructure
az deployment group create \
  -g your-resource-group \
  -f infra/main.bicep \
  --parameters @infra/main.parameters.json

# Deploy MCP server infrastructure
az deployment group create \
  -g mcp-resource-group \
  -f mcp/infra/main.bicep \
  --parameters @mcp/infra/main.parameters.json
```

---

## Troubleshooting

### Oracle Connection Issues

1. **Thick mode not initialized**: Ensure Oracle Instant Client is installed and `init_oracle_client()` can find it
2. **Connection timeout**: Check firewall rules and Oracle listener status
3. **Authentication failed**: Verify credentials in `oracle_config.ini`

### Azure OpenAI Issues

1. **Rate limiting**: Reduce request frequency or upgrade quota
2. **Model not found**: Verify deployment name matches your Azure OpenAI deployment
3. **Token limit exceeded**: Reduce `max_tokens` in configuration

### MCP Server Issues

1. **Agent not found**: Verify agent is registered with `GET /api/agents`
2. **Connection refused**: Check agent endpoint is accessible from MCP server
3. **Authentication failed**: Verify API key is correct

---

## License

MIT License - Copyright (c) 2026

This software is provided "AS-IS" without warranty of any kind. See [LICENSE](LICENSE) for full details.

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

Please ensure all code includes appropriate documentation headers with the AI-generated disclaimer.
| `agents/agent_generator.py` | Generates table-specific agents |
| `agent_config.ini` | Configuration template |
| `infra/main.bicep` | Azure infrastructure as code |

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Azure CLI
- Azure Functions Core Tools
- Oracle database access

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure

Copy and edit the configuration:

```bash
cp oracle/oracle_config.ini oracle/my_oracle_config.ini
cp agent_config.ini my_config.ini
# Edit both files with your settings
```

### 4. Local Development

```bash
# Start the function locally
func start
```

### 5. Deploy to Azure

```bash
# Edit infra/main.parameters.json with your values
chmod +x deploy.sh
./deploy.sh
```

## Generating Table-Specific Agents

Create individual agents for specific tables using the generator:

```bash
# Create a CSV with schema and table names
cat > tables.csv << EOF
schema,table_name
HR,EMPLOYEES
SALES,ORDERS
EOF

# Generate agents
./generate_agents.sh tables.csv --output ./generated_agents

# Generate and deploy
./generate_agents.sh tables.csv --deploy --resource-group mygroup
```

## API Endpoints

### POST /api/query
Query the database using natural language.

```json
{
  "question": "What is the average salary by department?",
  "reset_conversation": false
}
```

### GET /api/tables
List all available tables.

### GET /api/table/{table_name}/structure
Get the structure of a specific table.

### GET /api/health
Health check endpoint.

## Usage Examples

### Python Client

```python
import requests

# Query the agent
response = requests.post(
    "https://your-function.azurewebsites.net/api/query",
    json={"question": "Show me the top 10 employees by salary"},
    headers={"x-functions-key": "your-function-key"}
)
print(response.json()["answer"])
```

### cURL

```bash
curl -X POST https://your-function.azurewebsites.net/api/query \
  -H "Content-Type: application/json" \
  -H "x-functions-key: your-function-key" \
  -d '{"question": "How many records are in the EMPLOYEES table?"}'
```

### Local Usage (without Azure)

```python
from data_agent import DataAgent

with DataAgent("agent_config.ini") as agent:
    response = agent.ask("What tables are available?")
    print(response.answer)
    
    response = agent.ask("Show me the structure of EMPLOYEES")
    print(response.answer)
```

## Configuration Reference

### agent_config.ini

```ini
[azure_openai]
endpoint = https://your-resource.openai.azure.com/
api_key = your-api-key
api_version = 2024-02-15-preview
deployment_name = gpt-4o

[oracle]
host = your-oracle-host
port = 1521
service_name = ORCL
username = your_username
password = your_password
schema = your_schema

[agent]
max_iterations = 10
temperature = 0.0
system_prompt = You are a helpful data analyst assistant.
```

## Security Considerations

1. **Secrets**: Store sensitive values in Azure Key Vault (handled by Bicep deployment)
2. **Network**: Consider using Private Endpoints for Oracle connectivity
3. **Authentication**: The function uses function-level auth keys
4. **SQL Injection**: The agent only allows SELECT queries

## License

MIT License

Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

## Disclaimer

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
