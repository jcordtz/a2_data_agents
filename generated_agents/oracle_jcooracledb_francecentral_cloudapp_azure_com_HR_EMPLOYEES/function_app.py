"""
Azure Function App for HR.EMPLOYEES Agent
================================================================================

Provides RESTful API endpoints for natural language querying of the
HR.EMPLOYEES table.

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
    Query the HR.EMPLOYEES table using natural language.
    
    Request body:
        {"question": "your question", "reset_conversation": false}
    
    Response:
        {"answer": "...", "sql_executed": "...", "data": [...]}
    """
    logging.info("Query request received")
    
    try:
        req_body = req.get_json()
        question = req_body.get("question", "")
        reset = req_body.get("reset_conversation", False)
        
        if not question:
            return func.HttpResponse(
                json.dumps({"error": "Question is required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        agent = get_agent()
        
        if reset:
            agent.reset_conversation()
        
        response = agent.ask(question)
        
        result = {
            "answer": response.answer,
            "sql_executed": response.sql_executed,
            "data": response.data.to_dict(orient="records") if response.data is not None else None
        }
        
        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Query error: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
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
        logging.error(f"Table info error: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint."""
    return func.HttpResponse(
        json.dumps({"status": "healthy", "table": "HR.EMPLOYEES"}),
        mimetype="application/json"
    )


@app.route(route="reset", methods=["POST"])
def reset(req: func.HttpRequest) -> func.HttpResponse:
    """Reset conversation history."""
    try:
        agent = get_agent()
        agent.reset_conversation()
        
        return func.HttpResponse(
            json.dumps({"status": "conversation reset"}),
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Reset error: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
