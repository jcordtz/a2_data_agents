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
#   ./generate_agents.sh --csv <csv_file> [options]
#
# CSV FORMAT:
#   database_type,host,port,service_name,schema,table_name,purview
#   oracle,db.example.com,1521,ORCL,HR,EMPLOYEES,yes
#   mssql,sql.example.com,1433,mydb,SALES,ORDERS,no
#
# OPTIONS:
#   --csv, -c <file>     CSV file with table definitions (required)
#   --output, -o <dir>   Output directory for generated agents (default: ./generated_agents)
#   --yes, -y            Auto-confirm all prompts
#
# EXAMPLES:
#   ./generate_agents.sh --csv tables.csv
#   ./generate_agents.sh --output ./my_agents --csv tables.csv --yes
#   ./generate_agents.sh -c tables.csv -o ./my_agents -y
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
AUTO_YES=false

# Print usage
usage() {
    echo "Usage: $0 --csv <csv_file> [options]"
    echo ""
    echo "Options:"
    echo "  --csv, -c <file>       CSV file with table definitions (required)"
    echo "  --output, -o <dir>     Output directory for generated agents (default: ./generated_agents)"
    echo "  --yes, -y              Auto-confirm all prompts"
    echo "  --help, -h             Show this help message"
    echo ""
    echo "Note: Database connections are looked up from security/ XML files based on hostname."
    echo "      Use deploy_agents.sh to deploy generated agents to Azure."
    exit 1
}

# Print colored message
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Parse arguments
CSV_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --csv|-c)
            CSV_FILE="$2"
            shift 2
            ;;
        --output|-o)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --yes|-y)
            AUTO_YES=true
            shift
            ;;
        --help|-h)
            usage
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate inputs
if [ -z "$CSV_FILE" ]; then
    print_error "CSV file is required. Use --csv <file>"
    usage
fi

if [ ! -f "$CSV_FILE" ]; then
    print_error "CSV file not found: $CSV_FILE"
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
        if [ "$AUTO_YES" = true ]; then
            print_info "Auto-confirming: emptying output directory (--yes flag set)"
            rm -rf "${OUTPUT_DIR:?}"/*
        else
            echo "Options:"
            echo "  1) Empty the directory and continue"
            echo "  2) Continue without emptying (may overwrite)"
            echo "  3) Abort"
            read -p "Choose an option (1/2/3): " CHOICE
            case "$CHOICE" in
                1)
                    print_info "Emptying output directory..."
                    rm -rf "${OUTPUT_DIR:?}"/*
                    ;;
                2)
                    print_info "Continuing without emptying..."
                    ;;
                *)
                    print_info "Aborted by user."
                    exit 0
                    ;;
            esac
        fi
    fi
fi

print_info "========================================"
print_info "Table Agent Generator"
print_info "========================================"
print_info "CSV File: $CSV_FILE"
print_info "Output: $OUTPUT_DIR"
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
    
    # Validate database type
    case "$DB_TYPE" in
        oracle|mssql|postgres|db2)
            # Valid database type
            ;;
        *)
            print_warning "Unknown database type '$DB_TYPE' for ${SCHEMA}.${TABLE_NAME}, skipping..."
            FAILED=$((FAILED + 1))
            continue
            ;;
    esac
    
    CURRENT=$((CURRENT + 1))
    
    # Sanitize host for use in agent name (replace dots with underscores)
    SANITIZED_HOST=$(echo "${CSV_HOST:-localhost}" | tr '.' '_' | tr '-' '_')
    
    AGENT_NAME="${DB_TYPE}_${SANITIZED_HOST}_${SCHEMA}_${TABLE_NAME}"
    AGENT_DIR="${OUTPUT_DIR}/${AGENT_NAME}"
    

    
    print_info "[$CURRENT] Generating agent for ${DB_TYPE}://${SCHEMA}.${TABLE_NAME} (Host: ${CSV_HOST}:${CSV_PORT}, Service: ${SERVICE_NAME}, Purview: ${PURVIEW})..."
    
    # Build host argument
    HOST_ARG="--host $CSV_HOST"
    
    # Build port argument
    PORT_ARG="--port $CSV_PORT"
    
    # Build service name argument
    SERVICE_ARG="--service-name $SERVICE_NAME"
    
    # Build database type argument
    DB_TYPE_ARG="--db-type $DB_TYPE"
    
    # Generate agent using Python (connection looked up from security/ XML files)
    if python3 "$(dirname "$0")/agents/agent_generator.py" \
        --host "$CSV_HOST" \
        --schema "$SCHEMA" \
        --table "$TABLE_NAME" \
        --output "$AGENT_DIR" \
        --purview "$PURVIEW" \
        $PORT_ARG \
        $SERVICE_ARG \
        $DB_TYPE_ARG; then
        print_success "Created agent: $AGENT_NAME"
    else
        print_error "Failed to create agent for ${SCHEMA}.${TABLE_NAME}"
        FAILED=$((FAILED + 1))
        continue
    fi
done

print_info "========================================"
print_success "Agent generation complete!"
print_info "Generated agents are in: $OUTPUT_DIR"
print_info "Use deploy_agents.sh to deploy agents to Azure."
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
