#!/bin/bash
# =============================================================================
# Batch Register Agents Script
# =============================================================================
# Registers all generated agents with the MCP server.
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
#   ./register_all_agents.sh --agents-dir <path> [options]
#
# OPTIONS:
#   --agents-dir <path>     Directory containing generated agents (required)
#   --mcp-server <url>      MCP server URL (default: http://localhost:8080)
#   --mcp-token <token>     MCP server auth token
#   --api-keys-file <file>  JSON file mapping agent_id to api_key
#   --dry-run               Show what would be registered without registering
#
# EXAMPLES:
#   ./register_all_agents.sh --agents-dir ./generated_agents
#   ./register_all_agents.sh --agents-dir ./generated_agents \
#       --mcp-server https://mcp.example.com \
#       --api-keys-file ./keys.json
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default values
AGENTS_DIR=""
MCP_SERVER="http://localhost:8080"
MCP_TOKEN=""
API_KEYS_FILE=""
DRY_RUN=false

# Print functions
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }

# Usage
usage() {
    echo "Usage: $0 --agents-dir <path> [options]"
    echo ""
    echo "Options:"
    echo "  --agents-dir <path>     Directory containing generated agents"
    echo "  --mcp-server <url>      MCP server URL (default: http://localhost:8080)"
    echo "  --mcp-token <token>     MCP server auth token"
    echo "  --api-keys-file <file>  JSON file mapping agent_id to api_key"
    echo "  --dry-run               Show what would be registered"
    echo "  --help                  Show this help"
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --agents-dir) AGENTS_DIR="$2"; shift 2 ;;
        --mcp-server) MCP_SERVER="$2"; shift 2 ;;
        --mcp-token) MCP_TOKEN="$2"; shift 2 ;;
        --api-keys-file) API_KEYS_FILE="$2"; shift 2 ;;
        --dry-run) DRY_RUN=true; shift ;;
        --help) usage ;;
        *) print_error "Unknown option: $1"; usage ;;
    esac
done

# Validate
if [ -z "$AGENTS_DIR" ]; then
    print_error "Agents directory is required (--agents-dir)"
    usage
fi

if [ ! -d "$AGENTS_DIR" ]; then
    print_error "Agents directory not found: $AGENTS_DIR"
    exit 1
fi

# Function to get API key for an agent
get_api_key() {
    local agent_id=$1
    
    if [ -n "$API_KEYS_FILE" ] && [ -f "$API_KEYS_FILE" ]; then
        # Try to read from JSON file
        local key=$(python3 -c "import json; print(json.load(open('$API_KEYS_FILE')).get('$agent_id', ''))" 2>/dev/null)
        if [ -n "$key" ]; then
            echo "$key"
            return
        fi
    fi
    
    # Check for key file in agent directory
    local key_file="$AGENTS_DIR/$agent_id/.api_key"
    if [ -f "$key_file" ]; then
        cat "$key_file"
        return
    fi
    
    # Generate placeholder
    echo "REPLACE_WITH_ACTUAL_KEY"
}

# Get endpoint from deployment output or config
get_endpoint() {
    local agent_id=$1
    local agent_dir="$AGENTS_DIR/$agent_id"
    
    # Check for deployment output
    local output_file="$agent_dir/.deployment_output.json"
    if [ -f "$output_file" ]; then
        local url=$(python3 -c "import json; print(json.load(open('$output_file')).get('functionAppUrl', {}).get('value', ''))" 2>/dev/null)
        if [ -n "$url" ]; then
            echo "$url"
            return
        fi
    fi
    
    # Check config for endpoint
    local config_file="$agent_dir/agent_config.ini"
    if [ -f "$config_file" ]; then
        local endpoint=$(grep -E "^endpoint" "$config_file" | cut -d'=' -f2 | tr -d ' ')
        if [ -n "$endpoint" ]; then
            echo "$endpoint"
            return
        fi
    fi
    
    # Generate default Azure Functions URL
    echo "https://${agent_id}-func.azurewebsites.net"
}

print_info "========================================"
print_info "Batch Agent Registration"
print_info "========================================"
print_info "Agents Directory: $AGENTS_DIR"
print_info "MCP Server: $MCP_SERVER"
[ "$DRY_RUN" = true ] && print_warning "DRY RUN - No changes will be made"
print_info "========================================"

# Count agents
AGENT_COUNT=0
REGISTERED_COUNT=0
FAILED_COUNT=0

# Process each agent directory
for agent_dir in "$AGENTS_DIR"/*/; do
    if [ ! -d "$agent_dir" ]; then
        continue
    fi
    
    agent_id=$(basename "$agent_dir")
    config_file="$agent_dir/agent_config.ini"
    
    if [ ! -f "$config_file" ]; then
        print_warning "Skipping $agent_id - no config file"
        continue
    fi
    
    AGENT_COUNT=$((AGENT_COUNT + 1))
    
    # Extract info from config
    table_name=$(grep -E "^table_name" "$config_file" | cut -d'=' -f2 | tr -d ' ')
    schema_name=$(grep -E "^schema" "$config_file" | head -1 | cut -d'=' -f2 | tr -d ' ')
    host=$(grep -E "^host" "$config_file" | head -1 | cut -d'=' -f2 | tr -d ' ')
    purview=$(grep -E "^purview" "$config_file" 2>/dev/null | cut -d'=' -f2 | tr -d ' ')
    [ -z "$purview" ] && purview="no"
    
    # Detect database type from config file path or agent_id
    database_type="oracle"
    if echo "$agent_id" | grep -qi "^mssql"; then
        database_type="mssql"
    elif echo "$agent_id" | grep -qi "^postgres"; then
        database_type="postgres"
    elif echo "$agent_id" | grep -qi "^db2"; then
        database_type="db2"
    fi
    
    # Get endpoint and API key
    endpoint=$(get_endpoint "$agent_id")
    api_key=$(get_api_key "$agent_id")
    
    # Get description from README
    description=""
    if [ -f "$agent_dir/README.md" ]; then
        description=$(head -3 "$agent_dir/README.md" | tail -1)
    fi
    
    print_info ""
    print_info "Processing: $agent_id"
    print_info "  Database Type: $database_type"
    print_info "  Host: ${host:-not specified}"
    print_info "  Table: $schema_name.$table_name"
    print_info "  Purview: $purview"
    print_info "  Endpoint: $endpoint"
    
    if [ "$DRY_RUN" = true ]; then
        print_info "  [DRY RUN] Would register agent"
        continue
    fi
    
    # Register agent
    JSON_PAYLOAD=$(cat <<EOF
{
    "agent_id": "$agent_id",
    "table_name": "$table_name",
    "schema_name": "$schema_name",
    "endpoint": "$endpoint",
    "api_key": "$api_key",
    "database_type": "$database_type",
    "host": "$host",
    "purview": "$purview",
    "description": "$description"
}
EOF
)
    
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
        "${MCP_SERVER}/api/agents/register" \
        -H "Content-Type: application/json" \
        ${MCP_TOKEN:+-H "Authorization: Bearer $MCP_TOKEN"} \
        -d "$JSON_PAYLOAD")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_success "  Registered successfully"
        REGISTERED_COUNT=$((REGISTERED_COUNT + 1))
    else
        print_error "  Registration failed (HTTP $HTTP_CODE)"
        FAILED_COUNT=$((FAILED_COUNT + 1))
    fi
done

print_info ""
print_info "========================================"
print_info "Summary"
print_info "========================================"
print_info "Total agents found: $AGENT_COUNT"
if [ "$DRY_RUN" = false ]; then
    print_success "Successfully registered: $REGISTERED_COUNT"
    if [ "$FAILED_COUNT" -gt 0 ]; then
        print_error "Failed: $FAILED_COUNT"
    fi
fi
print_info "========================================"

if [ "$api_key" = "REPLACE_WITH_ACTUAL_KEY" ]; then
    print_warning ""
    print_warning "Note: Some agents have placeholder API keys."
    print_warning "Update them with actual keys using:"
    print_warning "  ./register_agent.sh --agent-id <id> --api-key <real-key> ..."
fi
