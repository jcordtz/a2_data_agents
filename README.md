# Multi-Database Data Agents

**AI-powered natural language querying for Oracle, SQL Server, PostgreSQL, and IBM DB2 databases, deployed as Azure Functions with MCP orchestration.**

An intelligent system that enables natural language querying of databases using Azure OpenAI. Supports **Oracle**, **Microsoft SQL Server**, **PostgreSQL**, and **IBM DB2 LUW**. Generate table-specific agents automatically, deploy them to Azure, and orchestrate them through a Model Context Protocol (MCP) server.

> **⚠️ Disclaimer**: This code was generated with AI assistance (AI-generated code). It is provided "AS-IS" under the MIT License without warranty of any kind. Users should review and test thoroughly before production use, validate security implications for their specific use case, and ensure compliance with their organization's policies. See the [LICENSE](LICENSE) file for full license text.

---

## Features

- **Multi-Database Support**: Connect to Oracle, SQL Server, PostgreSQL, and IBM DB2 LUW
- **Natural Language Queries**: Ask questions in plain English (or 30+ other languages)
- **Automatic SQL Generation**: AI translates questions to optimized database-specific SQL
- **Table-Specific Agents**: Generate dedicated agents for individual tables
- **Azure Functions Deployment**: Serverless, scalable Azure hosting
- **MCP Server Orchestration**: Unified interface for multiple agents
- **SQLAlchemy Integration**: Robust database connectivity with connection pooling
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
                                │ SQLAlchemy
    ┌───────────────────────────┼───────────────────────────┐
    ▼               ▼           ▼           ▼               ▼
┌─────────┐   ┌───────────┐   ┌──────────┐   ┌───────────┐
│ Oracle  │   │SQL Server │   │PostgreSQL│   │ IBM DB2   │
│Database │   │ Database  │   │ Database │   │ Database  │
└─────────┘   └───────────┘   └──────────┘   └───────────┘
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
├── mssql/                         # Microsoft SQL Server Module
│   ├── __init__.py                # Module exports
│   ├── mssql_connector.py         # SQLAlchemy-based connector (pyodbc)
│   └── mssql_config.ini           # Database connection configuration
│
├── postgres/                      # PostgreSQL Module
│   ├── __init__.py                # Module exports
│   ├── postgres_connector.py      # SQLAlchemy-based connector (psycopg2)
│   └── postgres_config.ini        # Database connection configuration
│
├── ibmdb2/                        # IBM DB2 LUW Module
│   ├── __init__.py                # Module exports
│   ├── ibmdb2_connector.py        # SQLAlchemy-based connector (ibm_db_sa)
│   └── ibmdb2_config.ini          # Database connection configuration
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
├── chatbot/                       # Chatbot Web Interface
│   ├── src/                       # React source code
│   │   ├── components/            # UI components (Chat, Header, etc.)
│   │   ├── hooks/                 # Custom React hooks
│   │   ├── services/              # API services
│   │   └── styles/                # CSS styles
│   ├── api/                       # Azure Functions API proxy
│   │   ├── query/                 # Query endpoint
│   │   ├── agents/                # List agents endpoint
│   │   └── health/                # Health check
│   ├── infra/                     # Chatbot infrastructure
│   │   ├── main.bicep             # Static Web Apps + App Insights
│   │   └── main.parameters.json   # Deployment parameters
│   ├── package.json               # Node.js dependencies
│   ├── vite.config.js             # Vite build configuration
│   ├── staticwebapp.config.json   # Azure Static Web Apps config
│   ├── deploy.sh                  # Deployment script
│   └── README.md                  # Chatbot documentation
│
├── infra/                         # Main Infrastructure
│   ├── bicep/                     # Azure Bicep templates
│   │   ├── main.bicep             # Azure Function + OpenAI + Storage + Chatbot
│   │   └── main.parameters.json   # Deployment parameters
│   └── terraform/                 # Terraform configuration
│       ├── main.tf                # Main infrastructure resources
│       ├── variables.tf           # Input variables
│       ├── outputs.tf             # Output values
│       ├── providers.tf           # Provider configuration
│       └── terraform.tfvars.example  # Example variable values
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
- Azure CLI
- Azure subscription with:
  - Azure OpenAI access
  - Permissions to create resources

**Database-specific requirements:**
- **Oracle**: Oracle Instant Client (for thick mode)
- **SQL Server**: Microsoft ODBC Driver 18 for SQL Server
  - macOS: `brew install microsoft/mssql-release/msodbcsql18`
  - Ubuntu: `sudo apt-get install msodbcsql18`
  - Windows: Download from Microsoft
- **PostgreSQL**: No additional drivers required (psycopg2-binary included)
- **IBM DB2**: IBM Data Server Driver Package (clidriver)
  - Download from [IBM Fix Central](https://www.ibm.com/support/fixcentral/)
  - Set `IBM_DB_HOME` environment variable to clidriver path
  - Linux/macOS: Add to `LD_LIBRARY_PATH`/`DYLD_LIBRARY_PATH`

### 1. Clone and Install

```bash
git clone https://github.com/jcordtz/a2_data_agents.git
cd a2_data_agents
pip install -r requirements.txt
```

### 2. Configure Database Connection

Choose the database(s) you want to use:

#### Oracle

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

#### SQL Server

Edit `mssql/mssql_config.ini`:

```ini
[mssql]
host = your-sql-server-host
port = 1433
database = your_database

# SQL Authentication
username = your_username
password = your_password

# OR use Windows/Integrated authentication
# trusted_connection = True

# Schema (defaults to 'dbo')
schema = dbo

# Connection pooling
min_connections = 1
max_connections = 5

# Language for natural language responses
country = US
```

#### PostgreSQL

Edit `postgres/postgres_config.ini`:

```ini
[postgres]
host = your-postgres-host
port = 5432
database = your_database

# Authentication
username = your_username
password = your_password

# Schema (defaults to 'public')
schema = public

# Connection pooling
min_connections = 1
max_connections = 5

# SSL mode (disable, allow, prefer, require, verify-ca, verify-full)
sslmode = prefer

# Language for natural language responses
country = US
```

#### IBM DB2 LUW

Edit `ibmdb2/ibmdb2_config.ini`:

```ini
[ibmdb2]
host = your-db2-host
port = 50000
database = your_database

# Authentication
username = your_username
password = your_password

# Schema (defaults to username if not specified)
schema = 

# Connection pooling
min_connections = 1
max_connections = 5

# SSL (optional)
# ssl = True

# Language for natural language responses
country = US
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

### Chatbot Interface

The chatbot provides a web-based UI for interacting with the MCP server.

```bash
cd chatbot

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Deploy to Azure Static Web Apps
./deploy.sh \
  --resource-group chat-rg \
  --mcp-url https://your-mcp-server.azurecontainer.io \
  --location eastus2
```

Or deploy as part of the main infrastructure:

```bash
# Deploy all infrastructure including chatbot
az deployment group create \
  -g your-resource-group \
  -f infra/main.bicep \
  --parameters deployChatbot=true \
  --parameters chatbotMcpServerUrl=https://your-mcp-server.url
```

---

## Component Documentation

| Component | Description | Documentation |
|-----------|-------------|---------------|
| **Oracle Connector** | SQLAlchemy-based Oracle connectivity with thick mode, connection pooling, and DataFrame support | See docstrings in [oracle/oracle_connector.py](oracle/oracle_connector.py) |
| **MSSQL Connector** | SQLAlchemy-based SQL Server connectivity with pyodbc, connection pooling, and DataFrame support | See docstrings in [mssql/mssql_connector.py](mssql/mssql_connector.py) |
| **PostgreSQL Connector** | SQLAlchemy-based PostgreSQL connectivity with psycopg2, connection pooling, and DataFrame support | See docstrings in [postgres/postgres_connector.py](postgres/postgres_connector.py) |
| **Data Agent** | Azure OpenAI-powered agent for natural language to SQL translation | See docstrings in [agents/data_agent.py](agents/data_agent.py) |
| **Function App** | Azure Function HTTP endpoints for the data agent | See docstrings in [agents/function_app.py](agents/function_app.py) |
| **Agent Generator** | Generates standalone Azure Function agents for specific tables | See docstrings in [agents/agent_generator.py](agents/agent_generator.py) |
| **MCP Server** | FastAPI-based Model Context Protocol server | See [mcp/README.md](mcp/README.md) |
| **Chatbot Interface** | React-based web UI for querying data through MCP server | See [chatbot/README.md](chatbot/README.md) |

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
lib_dir = /path/to/instantclient  # Optional: Oracle Instant Client path
```

### SQL Server Configuration (`mssql/mssql_config.ini`)

```ini
[mssql]
host = localhost          # SQL Server host
port = 1433               # SQL Server port
database = master         # Database name
schema = dbo              # Default schema
username = sa             # Database username
password = secret         # Database password
driver = ODBC Driver 18 for SQL Server  # ODBC driver name
trusted_connection = False  # Use Windows authentication
trust_server_certificate = True  # Trust self-signed certs
```

### PostgreSQL Configuration (`postgres/postgres_config.ini`)

```ini
[postgres]
host = localhost          # PostgreSQL host
port = 5432               # PostgreSQL port
database = postgres       # Database name
schema = public           # Default schema
username = postgres       # Database username
password = secret         # Database password
sslmode = prefer          # SSL mode (disable, allow, prefer, require)
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

**Main Agent (via Bicep or Terraform):**
- Azure Function App (Python 3.11)
- Azure OpenAI Service with GPT-4o
- App Service Plan (Consumption)
- Storage Account
- Application Insights
- Key Vault (for database credentials)
- Optional: Static Web App (for chatbot)

**MCP Server (`mcp/infra/main.bicep`):**
- Azure Container Apps
- Azure Container Registry
- Log Analytics Workspace
- Storage Account (for registry)

### Deployment Options

#### Option 1: Bicep

```bash
# Deploy main agent infrastructure
az deployment group create \
  -g your-resource-group \
  -f infra/bicep/main.bicep \
  --parameters @infra/bicep/main.parameters.json
```

#### Option 2: Terraform

```bash
cd infra/terraform

# Initialize Terraform
terraform init

# Copy example variables file and update with your values
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your settings

# Preview the deployment
terraform plan

# Deploy
terraform apply
```

### Deploy MCP Server

```bash
# Deploy MCP server infrastructure (Bicep)
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

### SQL Server Connection Issues

1. **ODBC Driver not found**: Install Microsoft ODBC Driver for SQL Server (`brew install microsoft/mssql-release/msodbcsql18` on macOS)
2. **Connection timeout**: Check firewall rules and SQL Server Browser service
3. **Certificate errors**: Set `trust_server_certificate = True` for self-signed certificates
4. **Authentication failed**: Verify credentials or use `trusted_connection = True` for Windows auth

### PostgreSQL Connection Issues

1. **psycopg2 not installed**: Install with `pip install psycopg2-binary`
2. **Connection refused**: Check PostgreSQL is running and accepting connections
3. **SSL errors**: Adjust `sslmode` setting (disable, allow, prefer, require)
4. **Authentication failed**: Check pg_hba.conf allows your connection type

### IBM DB2 Connection Issues

1. **ibm_db not installed**: Install with `pip install ibm_db ibm_db_sa`
2. **clidriver not found**: Set `IBM_DB_HOME` environment variable to clidriver path
3. **Library path issues**: Add clidriver lib to `LD_LIBRARY_PATH` (Linux) or `DYLD_LIBRARY_PATH` (macOS)
4. **SQLCODE -30081**: Network issue - check host, port, and firewall settings
5. **SQLCODE -1060**: User/password authentication failed - verify credentials
6. **Catalog not found**: Ensure database is cataloged or use direct connection string

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
