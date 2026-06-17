# Data Agent - Azure AI Database Query Agent

An AI-powered agent that enables natural language querying of Oracle databases, deployed as an Azure Function.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   User Query    │────▶│  Azure Function  │────▶│  Azure OpenAI   │
│  (Natural Lang) │     │   (Data Agent)   │     │    (GPT-4o)     │
└─────────────────┘     └────────┬─────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │ Oracle Database │
                        └─────────────────┘
```

## Components

| File | Description |
|------|-------------|
| `oracle_connector.py` | Oracle database connection and query utilities |
| `data_agent.py` | AI agent with Azure OpenAI integration |
| `function_app.py` | Azure Function HTTP endpoints |
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
cp agent_config.ini my_config.ini
# Edit my_config.ini with your settings
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

MIT
