"""
Azure Function App for Data Agent

This module provides HTTP endpoints for the AI Data Agent to run as an Azure Function.
"""

import json
import logging
import os
import azure.functions as func

from data_agent import DataAgent, AgentResponse

# Initialize the function app
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Global agent instance (lazy initialization)
_agent: DataAgent = None


def get_agent() -> DataAgent:
    """Get or create the DataAgent instance."""
    global _agent
    if _agent is None:
        config_path = os.environ.get("AGENT_CONFIG_PATH", "agent_config.ini")
        _agent = DataAgent(config_path)
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
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON in request body"}),
            status_code=400,
            mimetype="application/json",
        )

    question = req_body.get("question")
    if not question:
        return func.HttpResponse(
            json.dumps({"error": "Missing 'question' in request body"}),
            status_code=400,
            mimetype="application/json",
        )

    try:
        agent = get_agent()

        # Reset conversation if requested
        if req_body.get("reset_conversation", False):
            agent.reset_conversation()

        # Ask the question
        response: AgentResponse = agent.ask(question)

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

        return func.HttpResponse(
            json.dumps(result, default=str),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logging.error(f"Error processing query: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
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
        tables_df = agent.oracle.list_tables()

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
        structure_df = agent.oracle.get_table_structure(table_name)

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
