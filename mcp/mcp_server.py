#!/usr/bin/env python3
"""
MCP Server for Data Agents
================================================================================

A Model Context Protocol (MCP) server that hosts multiple table-specific data
agents, allowing AI models to query databases (Oracle, SQL Server, PostgreSQL,
IBM DB2) through a standardized protocol.

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
This MCP server provides:
    - Dynamic agent registration and discovery
    - Tool-based access to table queries
    - Resource endpoints for table metadata
    - Multi-agent orchestration

MCP TOOLS PROVIDED
------------------
    query_table(agent_id, question)
        Query a specific table using natural language
    
    list_agents()
        List all registered agents and their capabilities
    
    get_table_info(agent_id)
        Get metadata about a specific table/agent
    
    reset_conversation(agent_id)
        Reset conversation history for an agent

MCP RESOURCES PROVIDED
----------------------
    agents://list
        List of all registered agents
    
    agents://{agent_id}/info
        Information about a specific agent
    
    agents://{agent_id}/schema
        Table schema for a specific agent

USAGE
-----
Start the MCP server:

    python mcp_server.py --port 8080

Or with uvicorn:

    uvicorn mcp_server:app --host 0.0.0.0 --port 8080

Register an agent:

    python agent_registry.py register --agent-id hr_employees \\
        --endpoint https://hr-employees-func.azurewebsites.net \\
        --api-key your-function-key

CONFIGURATION
-------------
Environment variables:
    MCP_SERVER_PORT     - Server port (default: 8080)
    MCP_REGISTRY_PATH   - Path to agent registry file (default: ./agents.json)
    MCP_AUTH_TOKEN      - Optional authentication token

LICENSE
-------
MIT License - Copyright (c) 2026
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class AgentInfo:
    """Information about a registered agent."""
    agent_id: str
    table_name: str
    schema_name: str
    endpoint: str
    api_key: str
    database_type: str = "oracle"  # oracle, mssql, postgres, db2
    host: str = ""  # Database server hostname
    purview: str = "no"  # yes/no - Purview integration enabled
    description: str = ""
    registered_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_used: Optional[str] = None
    status: str = "active"


class QueryRequest(BaseModel):
    """Request model for querying an agent."""
    agent_id: str
    question: str
    reset_conversation: bool = False


class QueryResponse(BaseModel):
    """Response model for query results."""
    agent_id: str
    answer: str
    sql_executed: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


class RegisterAgentRequest(BaseModel):
    """Request model for registering an agent."""
    agent_id: str
    table_name: str
    schema_name: str
    endpoint: str
    api_key: str
    database_type: str = "oracle"  # oracle, mssql, postgres, db2
    host: str = ""  # Database server hostname
    purview: str = "no"  # yes/no - Purview integration enabled
    description: str = ""


class MCPToolCall(BaseModel):
    """MCP tool call request."""
    name: str
    arguments: Dict[str, Any]


class MCPToolResult(BaseModel):
    """MCP tool call result."""
    content: List[Dict[str, Any]]
    isError: bool = False


class MCPResource(BaseModel):
    """MCP resource."""
    uri: str
    name: str
    description: str
    mimeType: str = "application/json"


# =============================================================================
# Agent Registry
# =============================================================================

class AgentRegistry:
    """Registry for managing data agents."""
    
    def __init__(self, registry_path: str = "agents.json"):
        self.registry_path = Path(registry_path)
        self.agents: Dict[str, AgentInfo] = {}
        self._storage_available = True
        self._ensure_storage()
        self._load_registry()
    
    def _ensure_storage(self) -> None:
        """Ensure storage directory exists and is writable."""
        try:
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            # Test write access
            test_file = self.registry_path.parent / ".write_test"
            test_file.touch()
            test_file.unlink()
            logger.info(f"Storage directory ready: {self.registry_path.parent}")
        except Exception as e:
            logger.warning(f"Storage not available, running in memory-only mode: {e}")
            self._storage_available = False
    
    def _load_registry(self) -> None:
        """Load agents from the registry file."""
        if not self._storage_available:
            logger.info("Running in memory-only mode, no agents loaded")
            return
            
        if self.registry_path.exists():
            try:
                with open(self.registry_path, "r") as f:
                    data = json.load(f)
                    for agent_id, agent_data in data.items():
                        self.agents[agent_id] = AgentInfo(**agent_data)
                logger.info(f"Loaded {len(self.agents)} agents from registry")
            except Exception as e:
                logger.error(f"Error loading registry: {e}")
        else:
            logger.info(f"Registry file not found at {self.registry_path}, starting with empty registry")
    
    def _save_registry(self) -> None:
        """Save agents to the registry file."""
        if not self._storage_available:
            logger.debug("Storage not available, skipping save")
            return
            
        try:
            data = {agent_id: asdict(agent) for agent_id, agent in self.agents.items()}
            with open(self.registry_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving registry: {e}")
    
    def register(self, agent: AgentInfo) -> None:
        """Register a new agent."""
        self.agents[agent.agent_id] = agent
        self._save_registry()
        logger.info(f"Registered agent: {agent.agent_id}")
    
    def unregister(self, agent_id: str) -> bool:
        """Unregister an agent."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            self._save_registry()
            logger.info(f"Unregistered agent: {agent_id}")
            return True
        return False
    
    def get(self, agent_id: str) -> Optional[AgentInfo]:
        """Get an agent by ID."""
        return self.agents.get(agent_id)
    
    def list_all(self) -> List[AgentInfo]:
        """List all registered agents."""
        return list(self.agents.values())
    
    def update_last_used(self, agent_id: str) -> None:
        """Update the last used timestamp for an agent."""
        if agent_id in self.agents:
            self.agents[agent_id].last_used = datetime.utcnow().isoformat()
            self._save_registry()


# =============================================================================
# MCP Server
# =============================================================================

# Initialize FastAPI app
app = FastAPI(
    title="Data Agent MCP Server",
    description="Model Context Protocol server for multi-database data agents (Oracle, SQL Server, PostgreSQL, IBM DB2)",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize registry
registry_path = os.environ.get("MCP_REGISTRY_PATH", "agents.json")
registry = AgentRegistry(registry_path)


# Authentication dependency
async def verify_auth(authorization: Optional[str] = Header(None)) -> bool:
    """Verify authentication token if configured."""
    auth_token = os.environ.get("MCP_AUTH_TOKEN")
    # Skip auth if token is not configured or is the placeholder value
    if auth_token and auth_token != "not-configured":
        if not authorization or authorization != f"Bearer {auth_token}":
            raise HTTPException(status_code=401, detail="Unauthorized")
    return True


# =============================================================================
# MCP Protocol Endpoints
# =============================================================================

@app.get("/mcp/v1/tools")
async def list_tools(authorized: bool = Depends(verify_auth)) -> Dict[str, Any]:
    """List available MCP tools."""
    return {
        "tools": [
            {
                "name": "query_table",
                "description": "Query a table using natural language. Returns data and explanation.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "The ID of the agent/table to query"
                        },
                        "question": {
                            "type": "string",
                            "description": "Natural language question about the data"
                        }
                    },
                    "required": ["agent_id", "question"]
                }
            },
            {
                "name": "list_agents",
                "description": "List all available data agents and their tables",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_table_info",
                "description": "Get detailed information about a table including schema and description",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "The ID of the agent/table"
                        }
                    },
                    "required": ["agent_id"]
                }
            },
            {
                "name": "reset_conversation",
                "description": "Reset the conversation history for an agent",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "The ID of the agent"
                        }
                    },
                    "required": ["agent_id"]
                }
            }
        ]
    }


@app.post("/mcp/v1/tools/call")
async def call_tool(
    tool_call: MCPToolCall,
    authorized: bool = Depends(verify_auth)
) -> MCPToolResult:
    """Execute an MCP tool call."""
    try:
        if tool_call.name == "query_table":
            return await _handle_query_table(tool_call.arguments)
        elif tool_call.name == "list_agents":
            return await _handle_list_agents()
        elif tool_call.name == "get_table_info":
            return await _handle_get_table_info(tool_call.arguments)
        elif tool_call.name == "reset_conversation":
            return await _handle_reset_conversation(tool_call.arguments)
        else:
            return MCPToolResult(
                content=[{"type": "text", "text": f"Unknown tool: {tool_call.name}"}],
                isError=True
            )
    except Exception as e:
        logger.error(f"Tool call error: {e}")
        return MCPToolResult(
            content=[{"type": "text", "text": str(e)}],
            isError=True
        )


@app.get("/mcp/v1/resources")
async def list_resources(authorized: bool = Depends(verify_auth)) -> Dict[str, Any]:
    """List available MCP resources."""
    resources = [
        MCPResource(
            uri="agents://list",
            name="Agent List",
            description="List of all registered data agents"
        )
    ]
    
    for agent in registry.list_all():
        resources.append(MCPResource(
            uri=f"agents://{agent.agent_id}/info",
            name=f"{agent.agent_id} Info",
            description=f"Information about [{agent.database_type}] {agent.host}/{agent.schema_name}.{agent.table_name}"
        ))
        resources.append(MCPResource(
            uri=f"agents://{agent.agent_id}/schema",
            name=f"{agent.agent_id} Schema",
            description=f"Schema for [{agent.database_type}] {agent.schema_name}.{agent.table_name}"
        ))
    
    return {"resources": [r.dict() for r in resources]}


@app.get("/mcp/v1/resources/read")
async def read_resource(
    uri: str,
    authorized: bool = Depends(verify_auth)
) -> Dict[str, Any]:
    """Read an MCP resource."""
    if uri == "agents://list":
        agents = [
            {
                "agent_id": a.agent_id,
                "database_type": a.database_type,
                "host": a.host,
                "table": f"{a.schema_name}.{a.table_name}",
                "purview": a.purview,
                "description": a.description,
                "status": a.status
            }
            for a in registry.list_all()
        ]
        return {
            "contents": [{
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps(agents, indent=2)
            }]
        }
    
    # Parse agent-specific URIs
    if uri.startswith("agents://"):
        parts = uri.replace("agents://", "").split("/")
        if len(parts) >= 2:
            agent_id = parts[0]
            resource_type = parts[1]
            
            agent = registry.get(agent_id)
            if not agent:
                raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
            
            if resource_type == "info":
                return {
                    "contents": [{
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(asdict(agent), indent=2)
                    }]
                }
            elif resource_type == "schema":
                # Fetch schema from agent endpoint
                schema_data = await _fetch_table_info(agent)
                return {
                    "contents": [{
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(schema_data, indent=2)
                    }]
                }
    
    raise HTTPException(status_code=404, detail=f"Resource not found: {uri}")


# =============================================================================
# REST API Endpoints (for direct access)
# =============================================================================

@app.post("/api/agents/register")
async def register_agent(
    request: RegisterAgentRequest,
    authorized: bool = Depends(verify_auth)
) -> Dict[str, str]:
    """Register a new agent."""
    agent = AgentInfo(
        agent_id=request.agent_id,
        table_name=request.table_name,
        schema_name=request.schema_name,
        endpoint=request.endpoint,
        api_key=request.api_key,
        database_type=request.database_type,
        host=request.host,
        purview=request.purview,
        description=request.description
    )
    registry.register(agent)
    return {"status": "registered", "agent_id": agent.agent_id}


@app.delete("/api/agents/{agent_id}")
async def unregister_agent(
    agent_id: str,
    authorized: bool = Depends(verify_auth)
) -> Dict[str, str]:
    """Unregister an agent."""
    if registry.unregister(agent_id):
        return {"status": "unregistered", "agent_id": agent_id}
    raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")


@app.get("/api/agents")
async def list_agents_api(authorized: bool = Depends(verify_auth)) -> List[Dict[str, Any]]:
    """List all registered agents."""
    return [asdict(agent) for agent in registry.list_all()]


@app.get("/api/agents/{agent_id}")
async def get_agent_api(
    agent_id: str,
    authorized: bool = Depends(verify_auth)
) -> Dict[str, Any]:
    """Get agent details."""
    agent = registry.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    return asdict(agent)


@app.post("/api/query")
async def query_api(
    request: QueryRequest,
    authorized: bool = Depends(verify_auth)
) -> QueryResponse:
    """Query an agent directly."""
    agent = registry.get(request.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {request.agent_id}")
    
    result = await _query_agent(agent, request.question, request.reset_conversation)
    registry.update_last_used(request.agent_id)
    
    return QueryResponse(
        agent_id=request.agent_id,
        answer=result.get("answer", ""),
        sql_executed=result.get("sql_executed"),
        data=result.get("data"),
        error=result.get("error")
    )


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agents_registered": len(registry.agents),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/diagnostics/{agent_id}")
async def agent_diagnostics(
    agent_id: str,
    authorized: bool = Depends(verify_auth)
) -> Dict[str, Any]:
    """Get diagnostic information about an agent."""
    agent = registry.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    
    diagnostics = {
        "agent_id": agent.agent_id,
        "database_type": agent.database_type,
        "host": agent.host,
        "table": f"{agent.schema_name}.{agent.table_name}",
        "endpoint": agent.endpoint,
        "status": agent.status,
        "registered_at": agent.registered_at,
        "last_used": agent.last_used,
        "tests": {}
    }
    
    # Test endpoint connectivity
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{agent.endpoint}/api/health",
                headers={"x-functions-key": agent.api_key},
            )
            diagnostics["tests"]["endpoint_health"] = {
                "status": "ok" if response.status_code == 200 else "error",
                "status_code": response.status_code,
                "message": response.text[:200] if response.text else ""
            }
    except Exception as e:
        diagnostics["tests"]["endpoint_health"] = {
            "status": "error",
            "message": str(e)
        }
    
    # Test list tables
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{agent.endpoint}/api/tables",
                headers={"x-functions-key": agent.api_key},
            )
            if response.status_code == 200:
                tables = response.json().get("tables", [])
                diagnostics["tests"]["list_tables"] = {
                    "status": "ok",
                    "table_count": len(tables),
                    "tables": tables[:5]  # Show first 5
                }
            else:
                diagnostics["tests"]["list_tables"] = {
                    "status": "error",
                    "status_code": response.status_code
                }
    except Exception as e:
        diagnostics["tests"]["list_tables"] = {
            "status": "error",
            "message": str(e)
        }
    
    return diagnostics


# =============================================================================
# Tool Handlers
# =============================================================================

async def _handle_query_table(arguments: Dict[str, Any]) -> MCPToolResult:
    """Handle query_table tool call."""
    agent_id = arguments.get("agent_id")
    question = arguments.get("question")
    
    if not agent_id or not question:
        return MCPToolResult(
            content=[{"type": "text", "text": "Missing required arguments: agent_id, question"}],
            isError=True
        )
    
    agent = registry.get(agent_id)
    if not agent:
        return MCPToolResult(
            content=[{"type": "text", "text": f"Agent not found: {agent_id}"}],
            isError=True
        )
    
    result = await _query_agent(agent, question)
    registry.update_last_used(agent_id)
    
    content = [{"type": "text", "text": result.get("answer", "")}]
    
    if result.get("sql_executed"):
        content.append({
            "type": "text",
            "text": f"\n\nSQL Executed: {result['sql_executed']}"
        })
    
    if result.get("data"):
        content.append({
            "type": "text",
            "text": f"\n\nData: {json.dumps(result['data'][:10], default=str)}"
        })
    
    return MCPToolResult(content=content, isError=bool(result.get("error")))


async def _handle_list_agents() -> MCPToolResult:
    """Handle list_agents tool call."""
    agents = registry.list_all()
    
    if not agents:
        return MCPToolResult(
            content=[{"type": "text", "text": "No agents registered."}]
        )
    
    agent_list = "\n".join([
        f"- {a.agent_id}: [{a.database_type}] {a.host}/{a.schema_name}.{a.table_name} (Purview: {a.purview}) - {a.description or 'No description'}"
        for a in agents
    ])
    
    return MCPToolResult(
        content=[{"type": "text", "text": f"Registered agents:\n{agent_list}"}]
    )


async def _handle_get_table_info(arguments: Dict[str, Any]) -> MCPToolResult:
    """Handle get_table_info tool call."""
    agent_id = arguments.get("agent_id")
    
    if not agent_id:
        return MCPToolResult(
            content=[{"type": "text", "text": "Missing required argument: agent_id"}],
            isError=True
        )
    
    agent = registry.get(agent_id)
    if not agent:
        return MCPToolResult(
            content=[{"type": "text", "text": f"Agent not found: {agent_id}"}],
            isError=True
        )
    
    try:
        info = await _fetch_table_info(agent)
        return MCPToolResult(
            content=[{"type": "text", "text": json.dumps(info, indent=2, default=str)}]
        )
    except Exception as e:
        return MCPToolResult(
            content=[{"type": "text", "text": f"Error fetching table info: {e}"}],
            isError=True
        )


async def _handle_reset_conversation(arguments: Dict[str, Any]) -> MCPToolResult:
    """Handle reset_conversation tool call."""
    agent_id = arguments.get("agent_id")
    
    if not agent_id:
        return MCPToolResult(
            content=[{"type": "text", "text": "Missing required argument: agent_id"}],
            isError=True
        )
    
    agent = registry.get(agent_id)
    if not agent:
        return MCPToolResult(
            content=[{"type": "text", "text": f"Agent not found: {agent_id}"}],
            isError=True
        )
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{agent.endpoint}/api/reset",
                headers={"x-functions-key": agent.api_key},
                timeout=30.0
            )
            response.raise_for_status()
        
        return MCPToolResult(
            content=[{"type": "text", "text": f"Conversation reset for agent: {agent_id}"}]
        )
    except Exception as e:
        return MCPToolResult(
            content=[{"type": "text", "text": f"Error resetting conversation: {e}"}],
            isError=True
        )


# =============================================================================
# Helper Functions
# =============================================================================

async def _query_agent(
    agent: AgentInfo,
    question: str,
    reset_conversation: bool = False
) -> Dict[str, Any]:
    """Query an agent endpoint."""
    try:
        logger.info(f"Querying agent {agent.agent_id} at {agent.endpoint}")
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{agent.endpoint}/api/query",
                json={
                    "question": question,
                    "reset_conversation": reset_conversation
                },
                headers={"x-functions-key": agent.api_key},
            )
            
            logger.info(f"Agent response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Agent returned error status {response.status_code}")
                try:
                    error_data = response.json()
                    logger.error(f"Error response: {error_data}")
                    return {
                        "error": str(error_data.get("error", "Unknown error")),
                        "answer": f"Error from agent: {error_data.get('error', 'Unknown error')}"
                    }
                except:
                    return {
                        "error": f"HTTP {response.status_code}",
                        "answer": f"Agent returned error: HTTP {response.status_code}"
                    }
            
            result = response.json()
            logger.info(f"Agent response received with answer length: {len(result.get('answer', ''))}")
            return result
            
    except httpx.TimeoutException as e:
        logger.error(f"Timeout querying agent {agent.agent_id}: {e}")
        return {"error": str(e), "answer": f"Timeout: The query took too long to complete"}
    except httpx.HTTPError as e:
        logger.error(f"HTTP error querying agent {agent.agent_id}: {e}")
        return {"error": str(e), "answer": f"Connection error: {str(e)}"}
    except Exception as e:
        logger.error(f"Error querying agent {agent.agent_id}: {e}", exc_info=True)
        return {"error": str(e), "answer": f"Error: {str(e)}"}


async def _fetch_table_info(agent: AgentInfo) -> Dict[str, Any]:
    """Fetch table info from an agent endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{agent.endpoint}/api/table/info",
            headers={"x-functions-key": agent.api_key},
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("MCP_SERVER_PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
