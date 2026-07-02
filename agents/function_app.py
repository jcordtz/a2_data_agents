"""
Azure Function App for Data Agent
================================================================================

An Azure Functions application that exposes the AI Data Agent as RESTful HTTP
endpoints, enabling natural language database querying via web API calls.
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
FUNCTIONALITY
-------------
This module provides the following HTTP endpoints:

    POST /api/query
        Query the database using natural language.
        Request body: {"question": "your question", "reset_conversation": false}
        Response: {"answer": "...", "sql_executed": "...", "data": [...]}

    GET /api/tables
        List all available tables in the database.
        Response: {"tables": ["TABLE1", "TABLE2", ...]}

    GET /api/table/{table_name}/structure
        Get the structure/schema of a specific table.
        Response: {"table_name": "...", "columns": [...]}

    GET /api/health
        Health check endpoint.
        Response: {"status": "healthy"}

    POST /api/reset
        Reset the agent's conversation history.
        Response: {"status": "conversation reset"}

USAGE
-----
Local development:

    # Install Azure Functions Core Tools
    # https://docs.microsoft.com/azure/azure-functions/functions-run-local
    
    func start

Deployment to Azure:

    # Using Azure CLI
    func azure functionapp publish <your-function-app-name>

    # Or use the provided deploy.sh script
    ./deploy.sh

API Example (cURL):

    curl -X POST https://your-function.azurewebsites.net/api/query \
      -H "Content-Type: application/json" \
      -H "x-functions-key: your-function-key" \
      -d '{"question": "How many employees are there?"}'

API Example (Python):

    import requests
    
    response = requests.post(
        "https://your-function.azurewebsites.net/api/query",
        json={"question": "What is the average salary?"},
        headers={"x-functions-key": "your-function-key"}
    )
    print(response.json()["answer"])

ENVIRONMENT VARIABLES
---------------------
Configure via local.settings.json (local) or Application Settings (Azure):

    AGENT_CONFIG_PATH      - Path to agent configuration file
    AZURE_OPENAI_ENDPOINT  - Azure OpenAI endpoint URL
    AZURE_OPENAI_API_KEY   - Azure OpenAI API key
    AZURE_OPENAI_DEPLOYMENT - Model deployment name
    DATABASE_TYPE          - Database type: oracle, mssql, postgres, db2
    
    # Oracle-specific:
    ORACLE_HOST            - Oracle database host
    ORACLE_PORT            - Oracle database port
    ORACLE_SERVICE_NAME    - Oracle service name
    ORACLE_USERNAME        - Oracle username
    ORACLE_PASSWORD        - Oracle password
    
    # SQL Server-specific:
    MSSQL_HOST             - SQL Server host
    MSSQL_PORT             - SQL Server port
    MSSQL_DATABASE         - Database name
    MSSQL_USERNAME         - SQL Server username
    MSSQL_PASSWORD         - SQL Server password
    
    # PostgreSQL-specific:
    POSTGRES_HOST          - PostgreSQL host
    POSTGRES_PORT          - PostgreSQL port
    POSTGRES_DATABASE      - Database name
    POSTGRES_USERNAME      - PostgreSQL username
    POSTGRES_PASSWORD      - PostgreSQL password
    
    # IBM DB2-specific:
    DB2_HOST               - DB2 host
    DB2_PORT               - DB2 port
    DB2_DATABASE           - Database name
    DB2_USERNAME           - DB2 username
    DB2_PASSWORD           - DB2 password

DEPENDENCIES
------------
    - azure-functions >= 1.17.0
    - openai >= 1.12.0
    - pandas >= 2.0.0
    
    Database-specific drivers (install one based on your database):
    - Oracle: oracledb >= 2.0.0
    - SQL Server: pyodbc >= 5.0.0
    - PostgreSQL: psycopg2-binary >= 2.9.0
    - IBM DB2: ibm-db >= 3.1.0

Install with: pip install -r requirements.txt

LICENSE
-------
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

DISCLAIMER
----------
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import json
import logging
import os
import azure.functions as func

from .data_agent import DataAgent, AgentResponse

# Initialize the function app
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Global agent instance (lazy initialization)
_agent: DataAgent = None


def get_agent() -> DataAgent:
    """Get or create the DataAgent instance."""
    global _agent
    if _agent is None:
        host = os.environ.get("DATABASE_HOST")
        db_type = os.environ.get("DATABASE_TYPE", "oracle")
        config_path = os.environ.get("AGENT_CONFIG_PATH", "agent_config.ini")
        security_dir = os.environ.get("SECURITY_DIR")
        connection_id = os.environ.get("CONNECTION_ID")
        
        if not host:
            raise ValueError("DATABASE_HOST environment variable is required")
        
        _agent = DataAgent(
            host=host,
            db_type=db_type,
            config_path=config_path,
            security_dir=security_dir,
            connection_id=connection_id
        )
    return _agent


@app.route(route="query", methods=["POST"])
def query_data(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP endpoint to query the database using natural language.

    Request body:
    {
        "question": "What is the average salary by department?",
        "reset_conversation": false  // optional
    }

    Response:
    {
        "answer": "The average salary by department is...",
        "sql_executed": "SELECT ...",
        "row_count": 10,
        "tool_calls": [...]
    }
    """
    logging.info("Query endpoint called")

    try:
        req_body = req.get_json()
    except ValueError as e:
        logging.error(f"Invalid JSON in request: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON in request body"}),
            status_code=400,
            mimetype="application/json",
        )

    question = req_body.get("question")
    if not question:
        logging.error("Missing 'question' in request body")
        return func.HttpResponse(
            json.dumps({"error": "Missing 'question' in request body"}),
            status_code=400,
            mimetype="application/json",
        )

    try:
        logging.info(f"Processing question: {question}")
        agent = get_agent()

        # Reset conversation if requested
        if req_body.get("reset_conversation", False):
            logging.info("Resetting conversation history")
            agent.reset_conversation()

        # Ask the question
        logging.info("Calling agent.ask()")
        response: AgentResponse = agent.ask(question)
        
        logging.info(f"Agent response received. Answer length: {len(response.answer) if response.answer else 0}")

        # Prepare response
        result = {
            "answer": response.answer,
            "sql_executed": response.sql_executed,
            "row_count": len(response.data) if response.data is not None else None,
            "tool_calls": response.tool_calls,
        }

        # Include data preview if small enough
        if response.data is not None and len(response.data) <= 100:
            result["data"] = response.data.to_dict(orient="records")

        logging.info("Returning successful response")
        return func.HttpResponse(
            json.dumps(result, default=str),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logging.error(f"Error processing query: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e), "answer": f"Error: {str(e)}"}),
            status_code=500,
            mimetype="application/json",
        )


@app.route(route="tables", methods=["GET"])
def list_tables(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP endpoint to list available tables.

    Response:
    {
        "tables": ["TABLE1", "TABLE2", ...]
    }
    """
    logging.info("List tables endpoint called")

    try:
        agent = get_agent()
        tables_df = agent.db.list_tables()

        return func.HttpResponse(
            json.dumps({
                "tables": tables_df["TABLE_NAME"].tolist() if not tables_df.empty else []
            }),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logging.error(f"Error listing tables: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json",
        )


@app.route(route="table/{table_name}/structure", methods=["GET"])
def get_table_structure(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP endpoint to get the structure of a specific table.

    Response:
    {
        "table_name": "EMPLOYEES",
        "columns": [
            {"name": "ID", "type": "NUMBER", "nullable": "N", ...},
            ...
        ]
    }
    """
    table_name = req.route_params.get("table_name")
    logging.info(f"Get table structure endpoint called for: {table_name}")

    try:
        agent = get_agent()
        structure_df = agent.db.get_table_structure(table_name)

        return func.HttpResponse(
            json.dumps({
                "table_name": table_name,
                "columns": structure_df.to_dict(orient="records") if not structure_df.empty else []
            }, default=str),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logging.error(f"Error getting table structure: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json",
        )


@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint."""
    return func.HttpResponse(
        json.dumps({"status": "healthy"}),
        status_code=200,
        mimetype="application/json",
    )


@app.route(route="reset", methods=["POST"])
def reset_conversation(req: func.HttpRequest) -> func.HttpResponse:
    """Reset the agent's conversation history."""
    try:
        agent = get_agent()
        agent.reset_conversation()
        return func.HttpResponse(
            json.dumps({"status": "conversation reset"}),
            status_code=200,
            mimetype="application/json",
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json",
        )
