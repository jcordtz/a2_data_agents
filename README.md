# Multi-Database Data Agents

**AI-powered natural language querying for Oracle, SQL Server, PostgreSQL, and IBM DB2 databases, with a chatbot interface, Azure Functions deployment, and MCP orchestration.**

## Overview

This solution enables natural language querying of enterprise databases using Azure OpenAI, designed for organizations that need flexible, adaptive access to their data across multiple database systems.

### The Problem

Traditional ERP and database systems assume predictable, repeatable workflows—but many organizations face dynamic challenges where "doing it the same way as last time" simply isn't possible. Crisis response organizations, for example, handle unique situations where data requirements vary dramatically from case to case. They need to quickly access and combine information from various enterprise tables (vendors, items, personnel, etc.) in ways that can't be anticipated in advance.

### The Solution

This system takes a different approach: rather than building rigid interfaces, it lets important database tables "surface themselves" as individual AI agents. Each table-specific agent uses:

- **Table documentation** (comments on tables and columns) to understand what the data represents
- **Relationship metadata** (foreign keys, references) to know how tables can be combined
- **Natural language understanding** to translate questions into optimized SQL

An overall **chatbot interface** then orchestrates these agents through a Model Context Protocol (MCP) server, allowing users to ask complex questions that span multiple tables and databases—without needing to know SQL or understand the underlying schema.

### Supported Databases

- **Oracle** (with thick mode support)
- **Microsoft SQL Server** (via pyodbc)
- **PostgreSQL** (via psycopg2)
- **IBM DB2 LUW** (via ibm_db)

---

## Features

- **Multi-Database Support**: Connect to Oracle, SQL Server, PostgreSQL, and IBM DB2 LUW
- **Natural Language Queries**: Ask questions in plain English (or 30+ other languages)
- **Automatic SQL Generation**: AI translates questions to optimized database-specific SQL
- **Table-Specific Agents**: Generate dedicated agents for individual tables
- **Azure Functions Deployment**: Serverless, scalable Azure hosting
- **MCP Server Orchestration**: Unified interface for multiple agents
- **SQLAlchemy Integration**: Robust database connectivity with connection pooling
- **Microsoft Purview Integration**: Optional data governance with asset tracking and metadata management
- **Infrastructure as Code**: Bicep templates for Azure deployment

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AI Models (Claude, etc.)                       │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │ MCP Protocol
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              MCP Server                                     │
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
    ┌───────────────────────────┼───────────────────┐
    ▼               ▼               ▼               ▼
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
├── security/                      # Security Configuration
│   ├── connection_loader.py       # XML connection configuration loader
│   ├── oracle_connections.xml     # Oracle connection definitions
│   ├── mssql_connections.xml      # SQL Server connection definitions
│   ├── postgres_connections.xml   # PostgreSQL connection definitions
│   ├── ibmdb2_connections.xml     # IBM DB2 connection definitions
│   └── README.md                  # Security configuration documentation
│
├── databases/                     # Database Connectors Package
│   ├── __init__.py                # Package exports (all connectors)
│   │
│   ├── oracle/                    # Oracle Database Module
│   │   ├── __init__.py            # Module exports
│   │   └── oracle_connector.py    # SQLAlchemy-based connector (thick mode)
│   │
│   ├── mssql/                     # Microsoft SQL Server Module
│   │   ├── __init__.py            # Module exports
│   │   └── mssql_connector.py     # SQLAlchemy-based connector (pyodbc)
│   │
│   ├── postgres/                  # PostgreSQL Module
│   │   ├── __init__.py            # Module exports
│   │   └── postgres_connector.py  # SQLAlchemy-based connector (psycopg2)
│   │
│   └── ibmdb2/                    # IBM DB2 LUW Module
│       ├── __init__.py            # Module exports
│       └── ibmdb2_connector.py    # SQLAlchemy-based connector (ibm_db_sa)
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
├── purview/                       # Microsoft Purview Integration
│   ├── __init__.py                # Module exports
│   ├── purview_handler.py         # Purview Data Governance client
│   └── purview_config.ini         # Purview configuration
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
├── agent_config.ini               # Azure OpenAI configuration template
├── run.sh                         # Master orchestration script
├── deploy.sh                      # Main deployment script
├── generate_agents.sh             # Agent generation from CSV
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

### 2. Configure Database Connections

Database connections are configured via XML files in the `security/` directory. Each database type has its own XML file with connection definitions.

#### Oracle

Edit `security/oracle_connections.xml`:

```xml
<connections>
    <connection id="oracle_myhost_hr" type="oracle" auth="password">
        <host>your-oracle-host</host>
        <port>1521</port>
        <service_name>YOUR_SERVICE</service_name>
        <schema>YOUR_SCHEMA</schema>
        <credentials>
            <username>your-username</username>
            <password>your-password</password>
        </credentials>
    </connection>
</connections>
```

#### SQL Server

Edit `security/mssql_connections.xml`:

```xml
<connections>
    <connection id="mssql_myhost_hr" type="mssql" auth="sql_password">
        <host>your-sql-server-host</host>
        <port>1433</port>
        <database>your_database</database>
        <schema>dbo</schema>
        <credentials>
            <username>your-username</username>
            <password>your-password</password>
        </credentials>
    </connection>
</connections>
```

#### PostgreSQL

Edit `security/postgres_connections.xml`:

```xml
<connections>
    <connection id="postgres_myhost_sales" type="postgres" auth="password">
        <host>your-postgres-host</host>
        <port>5432</port>
        <database>your_database</database>
        <schema>public</schema>
        <credentials>
            <username>your-username</username>
            <password>your-password</password>
        </credentials>
    </connection>
</connections>
```

#### IBM DB2 LUW

Edit `security/ibmdb2_connections.xml`:

```xml
<connections>
    <connection id="db2_myhost_sales" type="db2" auth="password">
        <host>your-db2-host</host>
        <port>50000</port>
        <database>your_database</database>
        <schema>YOUR_SCHEMA</schema>
        <credentials>
            <username>your-username</username>
            <password>your-password</password>
        </credentials>
    </connection>
</connections>
```

See [security/README.md](security/README.md) for advanced authentication options including Azure Key Vault, Entra ID, Kerberos, and certificate-based authentication.

### 3. Configure Azure OpenAI

Azure OpenAI settings can be provided via environment variables or `agent_config.ini`:

**Option 1: Environment Variables (recommended for production)**

```bash
export AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
export AZURE_OPENAI_API_KEY=your-api-key
export AZURE_OPENAI_DEPLOYMENT=gpt-4o
export AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

**Option 2: Configuration File**

Edit `agent_config.ini`:

```ini
[azure_openai]
endpoint = https://your-openai.openai.azure.com/
api_key = your-api-key
deployment_name = gpt-4o
api_version = 2024-02-15-preview
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
# Generate a single agent (connection looked up from security/ XML files)
python agents/agent_generator.py \
  --host db.example.com \
  --schema HR \
  --table EMPLOYEES \
  --output ./generated_agents/hr_employees \
  --purview yes \
  --port 1521 \
  --db-type oracle \
  --service-name ORCL

# Generate multiple agents from CSV
# CSV format: database_type,host,port,service_name,schema,table_name,purview
./generate_agents.sh sample_tables.csv --output ./generated_agents
```

### Master Orchestration Script

The `run.sh` script orchestrates all solution components in the correct order:

```bash
# Run all steps (generate, deploy agents, deploy MCP, register, deploy chatbot)
./run.sh --all --csv sample_tables.csv --resource-group my-rg

# Run only agent generation
./run.sh --generate --csv tables.csv

# Deploy agents and MCP server only
./run.sh --deploy --mcp --resource-group my-rg

# Register agents with existing MCP server
./run.sh --register --mcp-url https://mcp.example.com

# Preview without executing (dry run)
./run.sh --all --resource-group my-rg --dry-run
```

**Available steps:**
- `--generate` - Generate agent code from CSV
- `--deploy` - Deploy generated agents to Azure Functions
- `--mcp` - Deploy MCP server to Azure
- `--register` - Register agents with MCP server
- `--chatbot` - Deploy chatbot to Azure Static Web Apps
- `--all` - Run all steps in order

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
| **Oracle Connector** | SQLAlchemy-based Oracle connectivity with thick mode, connection pooling, and DataFrame support | See docstrings in [databases/oracle/oracle_connector.py](databases/oracle/oracle_connector.py) |
| **MSSQL Connector** | SQLAlchemy-based SQL Server connectivity with pyodbc, connection pooling, and DataFrame support | See docstrings in [databases/mssql/mssql_connector.py](databases/mssql/mssql_connector.py) |
| **PostgreSQL Connector** | SQLAlchemy-based PostgreSQL connectivity with psycopg2, connection pooling, and DataFrame support | See docstrings in [databases/postgres/postgres_connector.py](databases/postgres/postgres_connector.py) |
| **IBM DB2 Connector** | SQLAlchemy-based IBM DB2 LUW connectivity with ibm_db_sa, connection pooling, and DataFrame support | See docstrings in [databases/ibmdb2/ibmdb2_connector.py](databases/ibmdb2/ibmdb2_connector.py) |
| **Connection Loader** | XML-based connection configuration with Key Vault integration | See [security/README.md](security/README.md) |
| **Data Agent** | Azure OpenAI-powered agent for natural language to SQL translation | See docstrings in [agents/data_agent.py](agents/data_agent.py) |
| **Function App** | Azure Function HTTP endpoints for the data agent | See docstrings in [agents/function_app.py](agents/function_app.py) |
| **Agent Generator** | Generates standalone Azure Function agents for specific tables | See docstrings in [agents/agent_generator.py](agents/agent_generator.py) |
| **Purview Handler** | Microsoft Purview Data Governance integration for asset description lookup | See docstrings in [purview/purview_handler.py](purview/purview_handler.py) |
| **MCP Server** | FastAPI-based Model Context Protocol server | See [mcp/README.md](mcp/README.md) |
| **Chatbot Interface** | React-based web UI for querying data through MCP server | See [chatbot/README.md](chatbot/README.md) |

---

## Configuration Reference

### Security Configuration (`security/*.xml`)

Database connections are defined in XML files with support for multiple authentication methods:

```xml
<!-- Password authentication -->
<connection id="oracle_prod" type="oracle" auth="password">
    <host>db.example.com</host>
    <port>1521</port>
    <service_name>ORCL</service_name>
    <schema>HR</schema>
    <credentials>
        <username>hr_user</username>
        <password>secret123</password>
    </credentials>
</connection>

<!-- Azure Key Vault authentication -->
<connection id="oracle_prod_keyvault" type="oracle" auth="azure_keyvault">
    <host>db.example.com</host>
    <port>1521</port>
    <service_name>ORCL</service_name>
    <schema>HR</schema>
    <keyvault>
        <vault_url>https://my-vault.vault.azure.net/</vault_url>
        <username_secret>oracle-username</username_secret>
        <password_secret>oracle-password</password_secret>
        <auth_method>managed_identity</auth_method>
    </keyvault>
</connection>
```

See [security/README.md](security/README.md) for all supported authentication methods.

### Agent Configuration (`agent_config.ini`)

```ini
[azure_openai]
endpoint = https://your-openai.openai.azure.com/
api_key = your-api-key
deployment_name = gpt-4o
api_version = 2024-02-15-preview
```
```

### Purview Configuration (`purview/purview_config.ini`)

```ini
[purview]
account_name = your-purview-account   # Microsoft Purview account name (required)
tenant_id = your-tenant-id             # Azure AD tenant ID (required)
client_id = your-client-id             # Service principal client ID (required)
client_secret = your-client-secret     # Service principal client secret (required)
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
# Test database connectors (using from_host() with security XML files)
python -c "from databases.oracle import OracleConnector; c = OracleConnector.from_host('db.example.com'); print('OK')"
python -c "from databases.mssql import MSSQLConnector; c = MSSQLConnector.from_host('sql.example.com'); print('OK')"
python -c "from databases.postgres import PostgresConnector; c = PostgresConnector.from_host('pg.example.com'); print('OK')"
python -c "from databases.ibmdb2 import IBMDB2Connector; c = IBMDB2Connector.from_host('db2.example.com'); print('OK')"

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

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

Please ensure all code includes appropriate documentation headers.

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Azure CLI
- Azure Functions Core Tools
- Database access (Oracle, SQL Server, PostgreSQL, or IBM DB2)

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Connections

Add your database connection to the appropriate XML file in `security/`:

```bash
# Edit the XML file for your database type
# See security/README.md for authentication options
nano security/oracle_connections.xml
```

### 4. Configure Azure OpenAI

```bash
# Set environment variables
export AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
export AZURE_OPENAI_API_KEY=your-api-key
export AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

### 5. Run Everything

```bash
# Use the master script to run all components
./run.sh --all --csv sample_tables.csv --resource-group my-rg

# Or run individual steps
./run.sh --generate --csv sample_tables.csv  # Generate agents only
```

## Generating Table-Specific Agents

Create individual agents for specific tables using the generator:

```bash
# Create a CSV with database_type, host, port, service_name, schema, table_name, purview columns
cat > tables.csv << EOF
database_type,host,port,service_name,schema,table_name,purview
oracle,db.example.com,1521,ORCL,HR,EMPLOYEES,yes
mssql,sqlserver.example.com,1433,mydb,HR,DEPARTMENTS,no
postgres,pghost.example.com,5432,salesdb,SALES,ORDERS,yes
db2,db2host.example.com,50000,DWDB,ANALYTICS,REPORTS,no
EOF

# Generate agents (connections looked up from security/ XML files)
./generate_agents.sh tables.csv --output ./generated_agents

# Deploy using the master script
./run.sh --deploy --resource-group mygroup --output ./generated_agents

# Or run all steps at once
./run.sh --all --csv tables.csv --resource-group mygroup

# Note: If the output directory exists and is not empty, you will be
# prompted to confirm before continuing.
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
api_key = <your-api-key>
api_version = 2024-02-15-preview
deployment_name = gpt-4o

[oracle]
host = your-oracle-host
port = 1521
service_name = ORCL
username = <your-username>
password = <your-password>
schema = your_schema

[mssql]
host = your-sql-server-host
port = 1433
database = your_database
username = <your-username>
password = <your-password>
schema = dbo
driver = ODBC Driver 18 for SQL Server
trusted_connection = False
trust_server_certificate = True

[postgres]
host = your-postgres-host
port = 5432
database = your_database
username = <your-username>
password = <your-password>
schema = public
sslmode = prefer

[ibmdb2]
host = your-db2-host
port = 50000
database = your_database
username = <your-username>
password = <your-password>
schema = 

[agent]
max_iterations = 10
temperature = 0.0
system_prompt = You are a helpful data analyst assistant.
```

## Security Considerations

### Secrets Management
- **Azure Key Vault**: Store database credentials and API keys in Key Vault (handled by Bicep and Terraform deployments)
- **Environment Variables**: Never commit credentials to source control; use environment variables or Key Vault references
- **Config Files**: Add `*_config.ini` files to `.gitignore` to prevent accidental commits

### Network Security
- **Private Endpoints**: Consider using Azure Private Endpoints for database connectivity:
  - Oracle: Private Link or VPN/ExpressRoute
  - SQL Server: Azure Private Link for Azure SQL, or VPN for on-premises
  - PostgreSQL: Azure Private Link for Azure Database for PostgreSQL
  - IBM DB2: VPN or ExpressRoute for secure connectivity
- **Firewall Rules**: Restrict database access to Azure Function outbound IPs
- **SSL/TLS**: Enable encrypted connections for all database types

### Authentication
- **Function Auth**: Azure Functions use function-level keys for API authentication
- **Database Auth**: 
  - SQL Server: Use SQL authentication or Azure AD (Managed Identity where supported)
  - PostgreSQL: Use SSL mode `require` or higher for production
  - IBM DB2: Use encrypted connections with SSL enabled
  - Oracle: Consider using wallets for secure credential storage

### SQL Injection Prevention
- The agent only allows SELECT queries (no INSERT, UPDATE, DELETE, DROP)
- Parameterized queries via SQLAlchemy prevent SQL injection
- User input is validated before query generation

### Infrastructure as Code Security
- **Bicep**: Uses secure parameters for sensitive values (`@secure()` decorator)
- **Terraform**: Use `sensitive = true` for credential variables; store state securely (Azure Storage with encryption)
- **State Files**: Never commit Terraform state files; use remote backends with encryption

## License and Disclaimer

### MIT License

Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

### Disclaimer

> **⚠️ AI-Generated Code Notice**: This code was generated with AI assistance. Users should review and test thoroughly before production use, validate security implications for their specific use case, and ensure compliance with their organization's policies.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

See the [LICENSE](LICENSE) file for full license text.
