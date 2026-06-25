#!/bin/bash
# =============================================================================
# Generate Table Agents Script
# =============================================================================
# Creates individual Azure Function agents for each table defined in a CSV file.
# Each agent is deployable to Azure and specializes in querying a specific table.
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
#   ./generate_agents.sh <csv_file> [options]
#
# CSV FORMAT:
#   database_type,host,port,service_name,schema,table_name,purview
#   oracle,db.example.com,1521,ORCL,HR,EMPLOYEES,yes
#   mssql,sql.example.com,1433,mydb,SALES,ORDERS,no
#
# OPTIONS:
#   --output <dir>       Output directory for generated agents (default: ./agents)
#   --deploy             Deploy agents to Azure after generation
#   --resource-group     Azure resource group for deployment
#   --location           Azure location (default: eastus)
#
# EXAMPLES:
#   ./generate_agents.sh tables.csv
#   ./generate_agents.sh tables.csv --output ./my_agents --config my_config.ini
#   ./generate_agents.sh tables.csv --deploy --resource-group mygroup
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
OUTPUT_DIR="./generated_agents"
DEPLOY=false
RESOURCE_GROUP=""
LOCATION="eastus"

# Print usage
usage() {
    echo "Usage: $0 <csv_file> [options]"
    echo ""
    echo "Options:"
    echo "  --output <dir>         Output directory for generated agents (default: ./agents)"
    echo "  --deploy               Deploy agents to Azure after generation"
    echo "  --resource-group <rg>  Azure resource group for deployment"
    echo "  --location <loc>       Azure location (default: eastus)"
    echo "  --help                 Show this help message"
    echo ""
    echo "Note: Config file is automatically selected based on database_type column in CSV:"
    echo "  oracle  -> databases/oracle/oracle_config.ini"
    echo "  mssql   -> databases/mssql/mssql_config.ini"
    echo "  postgres-> databases/postgres/postgres_config.ini"
    echo "  db2     -> databases/ibmdb2/ibmdb2_config.ini"
    exit 1
}

# Print colored message
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Parse arguments
if [ $# -lt 1 ]; then
    usage
fi

CSV_FILE="$1"
shift

while [[ $# -gt 0 ]]; do
    case $1 in
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --deploy)
            DEPLOY=true
            shift
            ;;
        --resource-group)
            RESOURCE_GROUP="$2"
            shift 2
            ;;
        --location)
            LOCATION="$2"
            shift 2
            ;;
        --help)
            usage
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate inputs
if [ ! -f "$CSV_FILE" ]; then
    print_error "CSV file not found: $CSV_FILE"
    exit 1
fi

if [ "$DEPLOY" = true ] && [ -z "$RESOURCE_GROUP" ]; then
    print_error "Resource group required for deployment (--resource-group)"
    exit 1
fi

# Check Python availability
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed"
    exit 1
fi

# Create output directory if it doesn't exist
if [ ! -d "$OUTPUT_DIR" ]; then
    print_info "Creating output directory: $OUTPUT_DIR..."
    mkdir -p "$OUTPUT_DIR"
else
    # Check if output directory is not empty
    if [ -n "$(ls -A "$OUTPUT_DIR" 2>/dev/null)" ]; then
        print_warning "Output directory '$OUTPUT_DIR' is not empty."
        read -p "Do you want to continue? This may overwrite existing agents. (yes/no): " CONFIRM
        if [ "$CONFIRM" != "yes" ]; then
            print_info "Aborted by user."
            exit 0
        fi
    fi
fi

print_info "========================================"
print_info "Table Agent Generator"
print_info "========================================"
print_info "CSV File: $CSV_FILE"
print_info "Output: $OUTPUT_DIR"
print_info "Deploy: $DEPLOY"
print_info "========================================"

# Count tables (excluding header)
TABLE_COUNT=$(tail -n +2 "$CSV_FILE" | grep -v '^[[:space:]]*$' | wc -l | tr -d ' ')
print_info "Found $TABLE_COUNT tables to process"

# Process each table
CURRENT=0
FAILED=0

# Read CSV file (skip header)
tail -n +2 "$CSV_FILE" | while IFS=',' read -r DB_TYPE CSV_HOST CSV_PORT SERVICE_NAME SCHEMA TABLE_NAME PURVIEW || [ -n "$SCHEMA" ]; do
    # Skip empty lines
    if [ -z "$SCHEMA" ] || [ -z "$TABLE_NAME" ]; then
        continue
    fi
    
    # Trim whitespace
    DB_TYPE=$(echo "$DB_TYPE" | xargs)
    CSV_HOST=$(echo "$CSV_HOST" | xargs)
    CSV_PORT=$(echo "$CSV_PORT" | xargs)
    SERVICE_NAME=$(echo "$SERVICE_NAME" | xargs)
    SCHEMA=$(echo "$SCHEMA" | xargs)
    TABLE_NAME=$(echo "$TABLE_NAME" | xargs)
    PURVIEW=$(echo "$PURVIEW" | xargs)
    
    # Default values
    if [ -z "$PURVIEW" ]; then
        PURVIEW="no"
    fi
    if [ -z "$DB_TYPE" ]; then
        print_warning "Missing database type for ${SCHEMA}.${TABLE_NAME}, skipping..."
        FAILED=$((FAILED + 1))
        continue
    fi
    if [ -z "$CSV_HOST" ]; then
        print_warning "Missing host for ${SCHEMA}.${TABLE_NAME}, skipping..."
        FAILED=$((FAILED + 1))
        continue
    fi
    if [ -z "$CSV_PORT" ]; then
        print_warning "Missing port for ${SCHEMA}.${TABLE_NAME}, skipping..."
        FAILED=$((FAILED + 1))
        continue
    fi
    if [ -z "$SERVICE_NAME" ]; then
        print_warning "Missing service_name for ${SCHEMA}.${TABLE_NAME}, skipping..."
        FAILED=$((FAILED + 1))
        continue
    fi
    
    # Set config path based on database type
    case "$DB_TYPE" in
        oracle)
            CONFIG_PATH="databases/oracle/oracle_config.ini"
            ;;
        mssql)
            CONFIG_PATH="databases/mssql/mssql_config.ini"
            ;;
        postgres)
            CONFIG_PATH="databases/postgres/postgres_config.ini"
            ;;
        db2)
            CONFIG_PATH="databases/ibmdb2/ibmdb2_config.ini"
            ;;
        *)
            print_warning "Unknown database type '$DB_TYPE' for ${SCHEMA}.${TABLE_NAME}, skipping..."
            FAILED=$((FAILED + 1))
            continue
            ;;
    esac
    
    # Validate config file exists
    if [ ! -f "$CONFIG_PATH" ]; then
        print_error "Config file not found: $CONFIG_PATH"
        FAILED=$((FAILED + 1))
        continue
    fi
    
    CURRENT=$((CURRENT + 1))
    
    # Sanitize host for use in agent name (replace dots with underscores)
    SANITIZED_HOST=$(echo "${CSV_HOST:-localhost}" | tr '.' '_' | tr '-' '_')
    
    AGENT_NAME="${DB_TYPE}_${SANITIZED_HOST}_${SCHEMA}_${TABLE_NAME}"
    AGENT_DIR="${OUTPUT_DIR}/${AGENT_NAME}"
    

    
    print_info "[$CURRENT] Generating agent for ${DB_TYPE}://${SCHEMA}.${TABLE_NAME} (Host: ${CSV_HOST}:${CSV_PORT}, Service: ${SERVICE_NAME}, Config: ${CONFIG_PATH}, Purview: ${PURVIEW})..."
    
    # Build host argument
    HOST_ARG="--host $CSV_HOST"
    
    # Build port argument
    PORT_ARG="--port $CSV_PORT"
    
    # Build service name argument
    SERVICE_ARG="--service-name $SERVICE_NAME"
    
    # Build database type argument
    DB_TYPE_ARG="--db-type $DB_TYPE"
    
    # Generate agent using Python
    if python3 "$(dirname "$0")/agents/agent_generator.py" \
        --config "$CONFIG_PATH" \
        --schema "$SCHEMA" \
        --table "$TABLE_NAME" \
        --output "$AGENT_DIR" \
        --purview "$PURVIEW" \
        $HOST_ARG \
        $PORT_ARG \
        $SERVICE_ARG \
        $DB_TYPE_ARG; then
        print_success "Created agent: $AGENT_NAME"
    else
        print_error "Failed to create agent for ${SCHEMA}.${TABLE_NAME}"
        FAILED=$((FAILED + 1))
        continue
    fi
    
    # Deploy if requested
    if [ "$DEPLOY" = true ]; then
        print_info "Deploying ${AGENT_NAME}..."
        
        if bash "${AGENT_DIR}/deploy.sh" \
            --resource-group "$RESOURCE_GROUP" \
            --location "$LOCATION"; then
            print_success "Deployed: $AGENT_NAME"
        else
            print_warning "Deployment failed for $AGENT_NAME"
        fi
    fi
done

print_info "========================================"
print_success "Agent generation complete!"
print_info "Generated agents are in: $OUTPUT_DIR"
if [ "$DEPLOY" = true ]; then
    print_info "Agents deployed to resource group: $RESOURCE_GROUP"
fi
print_info "========================================"

# List generated agents
echo ""
print_info "Generated Agents:"
for agent_dir in "$OUTPUT_DIR"/*/; do
    if [ -d "$agent_dir" ]; then
        agent_name=$(basename "$agent_dir")
        echo "  - $agent_name"
    fi
done
