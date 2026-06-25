#!/usr/bin/env python3
"""
Agent Generator
================================================================================

Generates an Azure-deployable agent for a specific Oracle table.
This script creates all necessary files for a standalone Azure Function app
that provides natural language querying capabilities for a specific table.

================================================================================
DISCLAIMER
================================================================================
This code was generated with AI assistance (AI-generated code).
It is provided "AS-IS" under the MIT License without warranty of any kind.

Users should:
- Review and test thoroughly before production use
- Validate security implications for their specific use case
- Ensure compliance with their organization's policies

LICENSE: MIT License - Copyright (c) 2026
See LICENSE file in project root for full license text.
================================================================================

USAGE:
    python agent_generator.py --config oracle_config.ini --schema HR --table EMPLOYEES --output ./agents/HR_EMPLOYEES

GENERATED FILES:
    - function_app.py      Azure Function endpoints
    - table_agent.py       Table-specific agent implementation
    - oracle_connector.py  Database connector (copied from main project)
    - requirements.txt     Python dependencies
    - host.json            Azure Functions configuration
    - local.settings.json  Local development settings
    - deploy.sh            Deployment script
    - infra/main.bicep     Infrastructure as code
    - README.md            Agent documentation
"""

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Database connector mapping
DATABASE_CONNECTORS = {
    "oracle": ("databases.oracle", "OracleConnector"),
    "mssql": ("databases.mssql", "MSSQLConnector"),
    "postgres": ("databases.postgres", "PostgresConnector"),
    "db2": ("databases.ibmdb2", "IBMDB2Connector"),
}

# SQL syntax mapping per database type
DATABASE_SQL_SYNTAX = {
    "oracle": "Oracle SQL",
    "mssql": "T-SQL (Microsoft SQL Server)",
    "postgres": "PostgreSQL",
    "db2": "IBM DB2 SQL",
}


def get_database_connector(db_type: str, config_path: str):
    """
    Get the appropriate database connector for the specified database type.
    
    Args:
        db_type: Database type (oracle, mssql, postgres, db2)
        config_path: Path to database config.ini
        
    Returns:
        Database connector instance
    """
    if db_type not in DATABASE_CONNECTORS:
        raise ValueError(f"Unsupported database type: {db_type}. Supported: {list(DATABASE_CONNECTORS.keys())}")
    
    module_name, class_name = DATABASE_CONNECTORS[db_type]
    
    # Dynamic import
    import importlib
    module = importlib.import_module(module_name)
    connector_class = getattr(module, class_name)
    
    return connector_class(config_path)


def generate_agent(
    config_path: str,
    schema: str,
    table_name: str,
    output_dir: str,
    purview: str = "no",
    host: str = None,
    db_type: str = None,
    service_name: str = None,
    port: int = None
) -> bool:
    """
    Generate a complete Azure Function agent for a specific table.
    
    Args:
        config_path: Path to database config.ini
        schema: Database schema name
        table_name: Table name
        output_dir: Output directory for generated agent
        purview: Whether to enable Purview integration ("yes" or "no")
        host: Database server hostname (required)
        db_type: Database type (oracle, mssql, postgres, db2) (required)
        service_name: Service/database name (required)
        port: Database port (required)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Default to oracle if not specified (for backward compatibility)
        effective_db_type = db_type.lower() if db_type else "oracle"
        
        # Connect to database and get table information
        print(f"Connecting to {effective_db_type} database to retrieve table metadata...")
        connector = get_database_connector(effective_db_type, config_path)
        with connector:
            # Get table description
            table_description = connector.get_table_description(table_name, schema)
            
            # Get table structure for schema info
            table_structure = connector.get_table_structure(table_name, schema)
            
            # Get foreign keys
            foreign_keys = connector.get_foreign_keys(table_name, schema)
            
            # Get column list
            columns = []
            if not table_structure.empty:
                col_name_field = "COLUMN_NAME" if "COLUMN_NAME" in table_structure.columns else "column_name"
                columns = table_structure[col_name_field].tolist()
        
        print(f"Retrieved metadata for {schema}.{table_name}")
        
        # Combine with Purview description if available
        combined_description = table_description
        if purview.lower() == "yes":
            print(f"Looking up Purview description for {schema}.{table_name}...")
            if not all([db_type, host, service_name, port]):
                print(f"[WARNING] Purview lookup requires db_type, host, port, and service_name. Using database description only.")
            else:
                try:
                    from purview.purview_handler import lookup_asset_description
                    purview_description = lookup_asset_description(
                        db_type=db_type,
                        host=host,
                        port=port,
                        service_name=service_name,
                        schema=schema,
                        table_name=table_name
                    )
                    if purview_description and purview_description != "N/A":
                        print(f"Purview description found, combining with database description")
                        # Combine database description with Purview description
                        purview_intro = "Additional information was found in Microsoft Purview Data Governance:"
                        if combined_description:
                            combined_description = f"{combined_description}\n\n{purview_intro}\n{purview_description}"
                        else:
                            combined_description = f"{purview_intro}\n{purview_description}"
                    else:
                        print(f"Purview: No description found for {schema}.{table_name}")
                except ImportError as e:
                    print(f"[WARNING] Purview module not found. Using database description only: {e}")
                except Exception as e:
                    print(f"[WARNING] Purview lookup failed. Using database description only: {e}")
        
        # Generate files
        agent_name = f"{schema}_{table_name}".lower()
        full_table_name = f"{schema}.{table_name}"
        
        # 1. Generate function_app.py
        generate_function_app(output_path, agent_name, full_table_name)
        
        # 2. Generate table_agent.py (with combined description and db_type)
        generate_table_agent(output_path, schema, table_name, combined_description, columns, effective_db_type)
        
        # 3. Copy the appropriate database connector
        copy_database_connector(output_path, effective_db_type)
        
        # 4. Generate requirements.txt (with db-specific dependencies)
        generate_requirements(output_path, effective_db_type)
        
        # 5. Generate host.json
        generate_host_json(output_path)
        
        # 6. Generate local.settings.json
        generate_local_settings(output_path, config_path)
        
        # 7. Generate deploy.sh
        generate_deploy_script(output_path, agent_name)
        
        # 8. Generate infra directory and Bicep
        infra_path = output_path / "infra"
        infra_path.mkdir(exist_ok=True)
        generate_bicep(infra_path, agent_name)
        generate_bicep_params(infra_path)
        
        # 9. Generate README.md (with combined description)
        generate_readme(output_path, schema, table_name, combined_description, columns)
        
        # 10. Generate agent config
        generate_agent_config(output_path, config_path, schema, table_name)
        
        print(f"Agent generated successfully in: {output_dir}")
        return True
        
    except Exception as e:
        print(f"Error generating agent: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_function_app(output_path: Path, agent_name: str, full_table_name: str):
    """Generate the Azure Function app."""
    content = f'''"""
Azure Function App for {full_table_name} Agent
================================================================================

Provides RESTful API endpoints for natural language querying of the
{full_table_name} table.

ENDPOINTS:
    POST /api/query          - Query the table using natural language
    GET  /api/table/info     - Get table structure and description
    GET  /api/health         - Health check
    POST /api/reset          - Reset conversation history
"""

import azure.functions as func
import json
import logging
import os

from table_agent import TableAgent

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Global agent instance
_agent: TableAgent = None


def get_agent() -> TableAgent:
    """Get or create the table agent instance."""
    global _agent
    if _agent is None:
        config_path = os.environ.get("AGENT_CONFIG_PATH", "agent_config.ini")
        _agent = TableAgent(config_path)
    return _agent


@app.route(route="query", methods=["POST"])
def query(req: func.HttpRequest) -> func.HttpResponse:
    """
    Query the {full_table_name} table using natural language.
    
    Request body:
        {{"question": "your question", "reset_conversation": false}}
    
    Response:
        {{"answer": "...", "sql_executed": "...", "data": [...]}}
    """
    logging.info("Query request received")
    
    try:
        req_body = req.get_json()
        question = req_body.get("question", "")
        reset = req_body.get("reset_conversation", False)
        
        if not question:
            return func.HttpResponse(
                json.dumps({{"error": "Question is required"}}),
                status_code=400,
                mimetype="application/json"
            )
        
        agent = get_agent()
        
        if reset:
            agent.reset_conversation()
        
        response = agent.ask(question)
        
        result = {{
            "answer": response.answer,
            "sql_executed": response.sql_executed,
            "data": response.data.to_dict(orient="records") if response.data is not None else None
        }}
        
        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Query error: {{e}}")
        return func.HttpResponse(
            json.dumps({{"error": str(e)}}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="table/info", methods=["GET"])
def table_info(req: func.HttpRequest) -> func.HttpResponse:
    """Get table structure and description."""
    logging.info("Table info request received")
    
    try:
        agent = get_agent()
        info = agent.get_table_info()
        
        return func.HttpResponse(
            json.dumps(info, default=str),
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Table info error: {{e}}")
        return func.HttpResponse(
            json.dumps({{"error": str(e)}}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint."""
    return func.HttpResponse(
        json.dumps({{"status": "healthy", "table": "{full_table_name}"}}),
        mimetype="application/json"
    )


@app.route(route="reset", methods=["POST"])
def reset(req: func.HttpRequest) -> func.HttpResponse:
    """Reset conversation history."""
    try:
        agent = get_agent()
        agent.reset_conversation()
        
        return func.HttpResponse(
            json.dumps({{"status": "conversation reset"}}),
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Reset error: {{e}}")
        return func.HttpResponse(
            json.dumps({{"error": str(e)}}),
            status_code=500,
            mimetype="application/json"
        )
'''
    
    (output_path / "function_app.py").write_text(content)


def generate_table_agent(
    output_path: Path,
    schema: str,
    table_name: str,
    table_description: str,
    columns: list,
    db_type: str = "oracle"
):
    """Generate the table-specific agent for any supported database type."""
    column_list = ", ".join(columns) if columns else "all columns"
    
    # Get SQL syntax for this database type
    sql_syntax = DATABASE_SQL_SYNTAX.get(db_type, "SQL")
    
    # Get connector import info
    connector_info = DATABASE_CONNECTORS.get(db_type, ("databases.oracle", "OracleConnector"))
    connector_class = connector_info[1]
    connector_file = f"{db_type}_connector.py" if db_type != "db2" else "ibmdb2_connector.py"
    config_section = db_type if db_type != "db2" else "ibmdb2"
    
    content = f'''"""
Table Agent for {schema}.{table_name}
================================================================================

An AI-powered agent specialized for querying the {schema}.{table_name} table.
This agent understands the table structure and can answer natural language
questions about the data.

DATABASE TYPE: {db_type.upper()}

TABLE DESCRIPTION:
{table_description}

AVAILABLE COLUMNS:
    {column_list}
"""

import configparser
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from openai import AzureOpenAI

from {connector_file.replace('.py', '')} import {connector_class}


@dataclass
class AgentResponse:
    """Response from the table agent."""
    answer: str
    sql_executed: Optional[str] = None
    data: Optional[pd.DataFrame] = None
    error: Optional[str] = None


class TableAgent:
    """
    AI Agent specialized for the {schema}.{table_name} table.
    Database Type: {db_type.upper()}
    """
    
    # Table metadata (embedded at generation time)
    SCHEMA = "{schema}"
    TABLE_NAME = "{table_name}"
    FULL_TABLE_NAME = "{schema}.{table_name}"
    DATABASE_TYPE = "{db_type}"
    SQL_SYNTAX = "{sql_syntax}"
    TABLE_DESCRIPTION = """{table_description}"""
    COLUMNS = {json.dumps(columns)}
    
    def __init__(self, config_path: str = "agent_config.ini"):
        """Initialize the table agent."""
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.db = {connector_class}(config_path)
        self.db.connect()
        
        # Initialize Azure OpenAI client
        self.client = AzureOpenAI(
            api_key=self.config.get("api_key") or os.environ.get("AZURE_OPENAI_API_KEY"),
            api_version=self.config.get("api_version", "2024-02-15-preview"),
            azure_endpoint=self.config.get("endpoint") or os.environ.get("AZURE_OPENAI_ENDPOINT")
        )
        self.deployment = self.config.get("deployment_name") or os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        
        # Conversation history
        self.conversation_history: List[Dict[str, str]] = []
        
        # System prompt
        self.system_prompt = self._build_system_prompt()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from INI file."""
        config = {{}}
        
        if self.config_path.exists():
            parser = configparser.ConfigParser()
            parser.read(self.config_path)
            
            if "azure_openai" in parser.sections():
                config.update(dict(parser["azure_openai"]))
            if "{config_section}" in parser.sections():
                config.update(dict(parser["{config_section}"]))
            if "agent" in parser.sections():
                config.update(dict(parser["agent"]))
        
        return config
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with table context."""
        return f"""You are an AI data analyst assistant specialized in querying the {{self.FULL_TABLE_NAME}} table.

DATABASE TYPE: {{self.DATABASE_TYPE.upper()}}

TABLE INFORMATION:
{{self.TABLE_DESCRIPTION}}

YOUR CAPABILITIES:
1. Answer questions about the data in this table
2. Generate SQL queries to retrieve data
3. Explain the table structure and relationships
4. Provide statistical analysis of the data

RULES:
1. Only query the {{self.FULL_TABLE_NAME}} table and its related tables via joins
2. Always use proper {{self.SQL_SYNTAX}} syntax
3. Limit results to 100 rows unless specifically asked for more
4. Be concise but informative in your responses
5. If you cannot answer a question with the available data, explain why

When you need to execute SQL, respond with a JSON object:
{{"action": "execute_sql", "sql": "YOUR SQL QUERY HERE"}}

When you have the final answer, just respond normally with text."""
    
    def ask(self, question: str) -> AgentResponse:
        """
        Ask a question about the table.
        
        Args:
            question: Natural language question
            
        Returns:
            AgentResponse with answer, SQL, and data
        """
        # Add user message to history
        self.conversation_history.append({{"role": "user", "content": question}})
        
        # Build messages for API call
        messages = [
            {{"role": "system", "content": self.system_prompt}},
            *self.conversation_history
        ]
        
        try:
            # Get response from Azure OpenAI
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=messages,
                temperature=float(self.config.get("temperature", 0.0)),
                max_tokens=2000
            )
            
            assistant_message = response.choices[0].message.content
            
            # Check if response contains SQL to execute
            if '"action": "execute_sql"' in assistant_message or "'action': 'execute_sql'" in assistant_message:
                return self._handle_sql_action(assistant_message)
            
            # Regular text response
            self.conversation_history.append({{"role": "assistant", "content": assistant_message}})
            
            return AgentResponse(answer=assistant_message)
            
        except Exception as e:
            return AgentResponse(
                answer=f"Error processing request: {{str(e)}}",
                error=str(e)
            )
    
    def _handle_sql_action(self, response: str) -> AgentResponse:
        """Handle SQL execution action from the model."""
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\\{{[^{{}}]*"action"[^{{}}]*\\}}', response)
            
            if not json_match:
                return AgentResponse(answer=response)
            
            action_data = json.loads(json_match.group())
            sql = action_data.get("sql", "")
            
            if not sql:
                return AgentResponse(answer=response)
            
            # Execute SQL
            df = self.db.query_to_dataframe(sql)
            
            # Generate summary
            summary = self._summarize_results(df, sql)
            
            self.conversation_history.append({{
                "role": "assistant",
                "content": f"Executed SQL: {{sql}}\\n\\nResults: {{summary}}"
            }})
            
            return AgentResponse(
                answer=summary,
                sql_executed=sql,
                data=df
            )
            
        except Exception as e:
            error_msg = f"Error executing SQL: {{str(e)}}"
            self.conversation_history.append({{"role": "assistant", "content": error_msg}})
            return AgentResponse(answer=error_msg, error=str(e))
    
    def _summarize_results(self, df: pd.DataFrame, sql: str) -> str:
        """Generate a summary of query results."""
        if df.empty:
            return "The query returned no results."
        
        summary_parts = [f"Query returned {{len(df)}} row(s)."]
        
        if len(df) <= 10:
            summary_parts.append(f"\\n\\nResults:\\n{{df.to_string()}}")
        else:
            summary_parts.append(f"\\n\\nFirst 10 rows:\\n{{df.head(10).to_string()}}")
        
        return "\\n".join(summary_parts)
    
    def get_table_info(self) -> Dict[str, Any]:
        """Get table structure and description."""
        structure = self.oracle.get_table_structure(self.TABLE_NAME, self.SCHEMA)
        
        return {{
            "schema": self.SCHEMA,
            "table_name": self.TABLE_NAME,
            "description": self.TABLE_DESCRIPTION,
            "columns": self.COLUMNS,
            "structure": structure.to_dict(orient="records") if not structure.empty else []
        }}
    
    def reset_conversation(self) -> None:
        """Reset conversation history."""
        self.conversation_history = []
    
    def close(self) -> None:
        """Close database connection."""
        self.oracle.disconnect()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
'''
    
    (output_path / "table_agent.py").write_text(content)


def copy_database_connector(output_path: Path, db_type: str):
    """Copy the appropriate database connector to the output directory."""
    # Mapping of db_type to connector file info
    connector_files = {
        "oracle": ("oracle", "oracle_connector.py"),
        "mssql": ("mssql", "mssql_connector.py"),
        "postgres": ("postgres", "postgres_connector.py"),
        "db2": ("ibmdb2", "ibmdb2_connector.py"),
    }
    
    if db_type not in connector_files:
        print(f"[WARNING] Unknown database type: {db_type}. Skipping connector copy.")
        return
    
    subdir, filename = connector_files[db_type]
    source_connector = Path(__file__).parent.parent / "databases" / subdir / filename
    
    if source_connector.exists():
        shutil.copy(source_connector, output_path / filename)
        print(f"Copied {filename} to output directory")
    else:
        print(f"[WARNING] Database connector not found: {source_connector}")


def generate_requirements(output_path: Path, db_type: str = "oracle"):
    """Generate requirements.txt with database-specific dependencies."""
    
    # Database-specific dependencies
    db_dependencies = {
        "oracle": "# Oracle Database\noracledb>=2.0.0",
        "mssql": "# Microsoft SQL Server\npyodbc>=5.0.0",
        "postgres": "# PostgreSQL\npsycopg2-binary>=2.9.0",
        "db2": "# IBM DB2\nibm-db>=3.1.0",
    }
    
    db_dep = db_dependencies.get(db_type, db_dependencies["oracle"])
    
    content = f"""# Azure Functions
azure-functions>=1.17.0

# Azure OpenAI
openai>=1.12.0

{db_dep}
sqlalchemy>=2.0.0

# Data Processing
pandas>=2.0.0

# Configuration
python-dotenv>=1.0.0
"""
    (output_path / "requirements.txt").write_text(content)


def generate_host_json(output_path: Path):
    """Generate host.json."""
    content = """{
    "version": "2.0",
    "logging": {
        "applicationInsights": {
            "samplingSettings": {
                "isEnabled": true,
                "excludedTypes": "Request"
            }
        }
    },
    "extensionBundle": {
        "id": "Microsoft.Azure.Functions.ExtensionBundle",
        "version": "[4.*, 5.0.0)"
    }
}
"""
    (output_path / "host.json").write_text(content)


def generate_local_settings(output_path: Path, config_path: str):
    """Generate local.settings.json."""
    content = """{
    "IsEncrypted": false,
    "Values": {
        "AzureWebJobsStorage": "UseDevelopmentStorage=true",
        "FUNCTIONS_WORKER_RUNTIME": "python",
        "AGENT_CONFIG_PATH": "agent_config.ini"
    }
}
"""
    (output_path / "local.settings.json").write_text(content)


def generate_deploy_script(output_path: Path, agent_name: str):
    """Generate deployment script."""
    content = f'''#!/bin/bash
# Deployment script for {agent_name} agent

set -e

RESOURCE_GROUP="${{RESOURCE_GROUP:-{agent_name}-rg}}"
LOCATION="${{LOCATION:-eastus}}"

while [[ $# -gt 0 ]]; do
    case $1 in
        --resource-group) RESOURCE_GROUP="$2"; shift 2 ;;
        --location) LOCATION="$2"; shift 2 ;;
        *) shift ;;
    esac
done

echo "Deploying {agent_name} agent..."
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"

# Create resource group
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none

# Deploy infrastructure
DEPLOYMENT_OUTPUT=$(az deployment group create \\
    --resource-group "$RESOURCE_GROUP" \\
    --template-file infra/main.bicep \\
    --parameters @infra/main.parameters.json \\
    --query "properties.outputs" \\
    --output json)

FUNCTION_APP_NAME=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.functionAppName.value')

echo "Deploying function code to $FUNCTION_APP_NAME..."
func azure functionapp publish "$FUNCTION_APP_NAME" --python

echo "Deployment complete!"
echo "Function App: $FUNCTION_APP_NAME"
'''
    
    deploy_path = output_path / "deploy.sh"
    deploy_path.write_text(content)
    deploy_path.chmod(0o755)


def generate_bicep(infra_path: Path, agent_name: str):
    """Generate Bicep infrastructure template."""
    content = f'''// Infrastructure for {agent_name} agent

@description('Base name for resources')
param baseName string = '{agent_name}'

@description('Location for resources')
param location string = resourceGroup().location

@secure()
param oracleHost string
param oraclePort string = '1521'
param oracleServiceName string
@secure()
param oracleUsername string
@secure()
param oraclePassword string

var functionAppName = '${{baseName}}-func-${{uniqueString(resourceGroup().id)}}'
var storageAccountName = take(replace('${{baseName}}st${{uniqueString(resourceGroup().id)}}', '-', ''), 24)
var appServicePlanName = '${{baseName}}-plan'
var appInsightsName = '${{baseName}}-insights'

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {{
  name: storageAccountName
  location: location
  sku: {{ name: 'Standard_LRS' }}
  kind: 'StorageV2'
}}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {{
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {{ Application_Type: 'web' }}
}}

resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {{
  name: appServicePlanName
  location: location
  sku: {{ name: 'Y1', tier: 'Dynamic' }}
  properties: {{ reserved: true }}
}}

resource functionApp 'Microsoft.Web/sites@2023-01-01' = {{
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  properties: {{
    serverFarmId: appServicePlan.id
    siteConfig: {{
      pythonVersion: '3.11'
      appSettings: [
        {{ name: 'AzureWebJobsStorage', value: 'DefaultEndpointsProtocol=https;AccountName=${{storageAccount.name}};EndpointSuffix=${{environment().suffixes.storage}};AccountKey=${{storageAccount.listKeys().keys[0].value}}' }}
        {{ name: 'FUNCTIONS_WORKER_RUNTIME', value: 'python' }}
        {{ name: 'FUNCTIONS_EXTENSION_VERSION', value: '~4' }}
        {{ name: 'APPINSIGHTS_INSTRUMENTATIONKEY', value: appInsights.properties.InstrumentationKey }}
        {{ name: 'ORACLE_HOST', value: oracleHost }}
        {{ name: 'ORACLE_PORT', value: oraclePort }}
        {{ name: 'ORACLE_SERVICE_NAME', value: oracleServiceName }}
        {{ name: 'ORACLE_USERNAME', value: oracleUsername }}
        {{ name: 'ORACLE_PASSWORD', value: oraclePassword }}
      ]
    }}
  }}
}}

output functionAppName string = functionApp.name
output functionAppUrl string = 'https://${{functionApp.properties.defaultHostName}}'
'''
    
    (infra_path / "main.bicep").write_text(content)


def generate_bicep_params(infra_path: Path):
    """Generate Bicep parameters file."""
    content = """{
    "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
    "contentVersion": "1.0.0.0",
    "parameters": {
        "oracleHost": { "value": "" },
        "oraclePort": { "value": "1521" },
        "oracleServiceName": { "value": "" },
        "oracleUsername": { "value": "" },
        "oraclePassword": { "value": "" }
    }
}
"""
    (infra_path / "main.parameters.json").write_text(content)


def generate_readme(
    output_path: Path,
    schema: str,
    table_name: str,
    table_description: str,
    columns: list
):
    """Generate README documentation."""
    column_list = "\n".join([f"- {col}" for col in columns]) if columns else "- (columns not available)"
    
    content = f'''# {schema}.{table_name} Agent

An AI-powered Azure Function agent for natural language querying of the {schema}.{table_name} table.

## Table Description

{table_description}

## Available Columns

{column_list}

## API Endpoints

### POST /api/query
Query the table using natural language.

```bash
curl -X POST https://your-function.azurewebsites.net/api/query \\
  -H "Content-Type: application/json" \\
  -H "x-functions-key: your-key" \\
  -d '{{"question": "How many records are in the table?"}}'
```

### GET /api/table/info
Get table structure and description.

### GET /api/health
Health check endpoint.

### POST /api/reset
Reset conversation history.

## Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure `agent_config.ini` with your credentials

3. Start the function:
   ```bash
   func start
   ```

## Deployment

1. Update `infra/main.parameters.json` with your Oracle credentials

2. Run the deployment script:
   ```bash
   ./deploy.sh --resource-group your-rg --location eastus
   ```

## Generated

This agent was auto-generated by the Table Agent Generator.
'''
    
    (output_path / "README.md").write_text(content)


def generate_agent_config(output_path: Path, source_config_path: str, schema: str, table_name: str):
    """Generate agent configuration file."""
    # Read source config
    parser = configparser.ConfigParser()
    parser.read(source_config_path)
    
    # Write new config
    new_config = configparser.ConfigParser()
    
    # Copy oracle section
    if "oracle" in parser.sections():
        new_config["oracle"] = dict(parser["oracle"])
        new_config["oracle"]["schema"] = schema
    
    # Copy azure_openai section
    if "azure_openai" in parser.sections():
        new_config["azure_openai"] = dict(parser["azure_openai"])
    
    # Add agent section
    new_config["agent"] = {
        "table_name": table_name,
        "schema": schema,
        "max_iterations": "10",
        "temperature": "0.0"
    }
    
    with open(output_path / "agent_config.ini", "w") as f:
        new_config.write(f)


def generate_oracle_connector_stub(output_path: Path):
    """Generate a stub oracle_connector.py if source not found."""
    content = '''"""Oracle Connector stub - copy oracle_connector.py from main project."""
raise ImportError("Please copy oracle_connector.py from the main project")
'''
    (output_path / "oracle_connector.py").write_text(content)


def main():
    parser = argparse.ArgumentParser(description="Generate a table-specific Azure Function agent")
    parser.add_argument("--config", required=True, help="Path to database config.ini")
    parser.add_argument("--schema", required=True, help="Database schema name")
    parser.add_argument("--table", required=True, help="Table name")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--purview", default="no", choices=["yes", "no"],
                        help="Enable Purview integration (yes/no)")
    parser.add_argument("--host", required=True,
                        help="Database server hostname (required)")
    parser.add_argument("--db-type", required=True,
                        choices=["oracle", "mssql", "postgres", "db2"],
                        help="Database type (required)")
    parser.add_argument("--service-name", required=True,
                        help="Service name (Oracle) or database name (others) (required)")
    parser.add_argument("--port", type=int, required=True,
                        help="Database port (required)")
    
    args = parser.parse_args()
    
    success = generate_agent(
        config_path=args.config,
        schema=args.schema,
        table_name=args.table,
        output_dir=args.output,
        purview=args.purview,
        host=args.host,
        db_type=args.db_type,
        service_name=args.service_name,
        port=args.port
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
