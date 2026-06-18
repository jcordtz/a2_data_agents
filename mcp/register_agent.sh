#!/bin/bash
# =============================================================================
# Register Agent Script
# =============================================================================
# Registers a data agent with the MCP server.
#
# =============================================================================
# DISCLAIMER
# =============================================================================
# This code was generated with AI assistance (AI-generated code).
# It is provided "AS-IS" under the MIT License without warranty of any kind.
#
# Users should:
# - Review and test thoroughly before production use
# - Validate security implications for their specific use case
# - Ensure compliance with their organization's policies
#
# LICENSE: MIT License - Copyright (c) 2026
# See LICENSE file in project root for full license text.
# =============================================================================
#
# USAGE:
#   ./register_agent.sh --agent-id <id> --endpoint <url> --api-key <key> [options]
#
# OPTIONS:
#   --agent-id <id>        Unique identifier for the agent (required)
#   --endpoint <url>       Azure Function endpoint URL (required)
#   --api-key <key>        Azure Function API key (required)
#   --table <name>         Table name (default: extracted from agent-id)
#   --schema <name>        Schema name (default: extracted from agent-id)
#   --description <text>   Agent description
#   --mcp-server <url>     MCP server URL (default: http://localhost:8080)
#   --mcp-token <token>    MCP server auth token (optional)
#   --from-config <path>   Load settings from generated agent config
#
# EXAMPLES:
#   # Register a single agent
#   ./register_agent.sh --agent-id hr_employees \
#       --endpoint https://hr-employees-func.azurewebsites.net \
#       --api-key abc123
#
#   # Register from generated agent directory
#   ./register_agent.sh --from-config ./generated_agents/hr_employees/
#
#   # Register with custom MCP server
#   ./register_agent.sh --agent-id sales_orders \
#       --endpoint https://sales-orders-func.azurewebsites.net \
#       --api-key xyz789 \
#       --mcp-server https://mcp.example.com \
#       --mcp-token mytoken
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default values
MCP_SERVER="http://localhost:8080"
MCP_TOKEN=""
AGENT_ID=""
ENDPOINT=""
API_KEY=""
TABLE_NAME=""
SCHEMA_NAME=""
DESCRIPTION=""
FROM_CONFIG=""

# Print functions
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }

# Usage
usage() {
    echo "Usage: $0 --agent-id <id> --endpoint <url> --api-key <key> [options]"
    echo ""
    echo "Options:"
    echo "  --agent-id <id>        Unique identifier for the agent"
    echo "  --endpoint <url>       Azure Function endpoint URL"
    echo "  --api-key <key>        Azure Function API key"
    echo "  --table <name>         Table name"
    echo "  --schema <name>        Schema name"
    echo "  --description <text>   Agent description"
    echo "  --mcp-server <url>     MCP server URL (default: http://localhost:8080)"
    echo "  --mcp-token <token>    MCP server auth token"
    echo "  --from-config <path>   Load from generated agent config directory"
    echo "  --help                 Show this help"
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --agent-id) AGENT_ID="$2"; shift 2 ;;
        --endpoint) ENDPOINT="$2"; shift 2 ;;
        --api-key) API_KEY="$2"; shift 2 ;;
        --table) TABLE_NAME="$2"; shift 2 ;;
        --schema) SCHEMA_NAME="$2"; shift 2 ;;
        --description) DESCRIPTION="$2"; shift 2 ;;
        --mcp-server) MCP_SERVER="$2"; shift 2 ;;
        --mcp-token) MCP_TOKEN="$2"; shift 2 ;;
        --from-config) FROM_CONFIG="$2"; shift 2 ;;
        --help) usage ;;
        *) print_error "Unknown option: $1"; usage ;;
    esac
done

# Load from config directory if specified
if [ -n "$FROM_CONFIG" ]; then
    CONFIG_DIR="$FROM_CONFIG"
    
    if [ ! -d "$CONFIG_DIR" ]; then
        print_error "Config directory not found: $CONFIG_DIR"
        exit 1
    fi
    
    CONFIG_FILE="$CONFIG_DIR/agent_config.ini"
    if [ ! -f "$CONFIG_FILE" ]; then
        print_error "Config file not found: $CONFIG_FILE"
        exit 1
    fi
    
    # Extract agent info from config
    if [ -z "$AGENT_ID" ]; then
        AGENT_ID=$(basename "$CONFIG_DIR")
    fi
    
    if [ -z "$TABLE_NAME" ]; then
        TABLE_NAME=$(grep -E "^table_name" "$CONFIG_FILE" | cut -d'=' -f2 | tr -d ' ')
    fi
    
    if [ -z "$SCHEMA_NAME" ]; then
        SCHEMA_NAME=$(grep -E "^schema" "$CONFIG_FILE" | head -1 | cut -d'=' -f2 | tr -d ' ')
    fi
    
    # Try to read README for description
    if [ -z "$DESCRIPTION" ] && [ -f "$CONFIG_DIR/README.md" ]; then
        DESCRIPTION=$(head -3 "$CONFIG_DIR/README.md" | tail -1)
    fi
    
    print_info "Loaded config from: $CONFIG_DIR"
fi

# Extract table and schema from agent_id if not provided
if [ -z "$TABLE_NAME" ] && [ -n "$AGENT_ID" ]; then
    # Assume format: schema_table
    TABLE_NAME=$(echo "$AGENT_ID" | cut -d'_' -f2- | tr '[:lower:]' '[:upper:]')
fi

if [ -z "$SCHEMA_NAME" ] && [ -n "$AGENT_ID" ]; then
    SCHEMA_NAME=$(echo "$AGENT_ID" | cut -d'_' -f1 | tr '[:lower:]' '[:upper:]')
fi

# Validate required fields
if [ -z "$AGENT_ID" ]; then
    print_error "Agent ID is required (--agent-id)"
    usage
fi

if [ -z "$ENDPOINT" ]; then
    print_error "Endpoint URL is required (--endpoint)"
    usage
fi

if [ -z "$API_KEY" ]; then
    print_error "API key is required (--api-key)"
    usage
fi

# Build auth header
AUTH_HEADER=""
if [ -n "$MCP_TOKEN" ]; then
    AUTH_HEADER="-H \"Authorization: Bearer $MCP_TOKEN\""
fi

print_info "========================================"
print_info "Registering Agent with MCP Server"
print_info "========================================"
print_info "Agent ID:    $AGENT_ID"
print_info "Table:       $SCHEMA_NAME.$TABLE_NAME"
print_info "Endpoint:    $ENDPOINT"
print_info "MCP Server:  $MCP_SERVER"
print_info "========================================"

# Build JSON payload
JSON_PAYLOAD=$(cat <<EOF
{
    "agent_id": "$AGENT_ID",
    "table_name": "$TABLE_NAME",
    "schema_name": "$SCHEMA_NAME",
    "endpoint": "$ENDPOINT",
    "api_key": "$API_KEY",
    "description": "$DESCRIPTION"
}
EOF
)

# Register agent
print_info "Sending registration request..."

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "${MCP_SERVER}/api/agents/register" \
    -H "Content-Type: application/json" \
    ${MCP_TOKEN:+-H "Authorization: Bearer $MCP_TOKEN"} \
    -d "$JSON_PAYLOAD")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    print_success "Agent registered successfully!"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
else
    print_error "Registration failed (HTTP $HTTP_CODE)"
    echo "$BODY"
    exit 1
fi

# Verify registration
print_info "Verifying registration..."

VERIFY_RESPONSE=$(curl -s -w "\n%{http_code}" \
    "${MCP_SERVER}/api/agents/${AGENT_ID}" \
    ${MCP_TOKEN:+-H "Authorization: Bearer $MCP_TOKEN"})

VERIFY_CODE=$(echo "$VERIFY_RESPONSE" | tail -1)

if [ "$VERIFY_CODE" = "200" ]; then
    print_success "Agent verified in registry"
else
    print_warning "Could not verify agent (HTTP $VERIFY_CODE)"
fi

print_info "========================================"
print_success "Registration complete!"
print_info ""
print_info "To query this agent via MCP:"
print_info "  Tool: query_table"
print_info "  Arguments: {\"agent_id\": \"$AGENT_ID\", \"question\": \"...\"}"
print_info "========================================"
