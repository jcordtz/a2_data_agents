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
#   schema,table_name
#   HR,EMPLOYEES
#   SALES,ORDERS
#
# OPTIONS:
#   --config <path>      Path to oracle_config.ini (default: oracle_config.ini)
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
CONFIG_PATH="databases/oracle/oracle_config.ini"
OUTPUT_DIR="./generated_agents"
DEPLOY=false
RESOURCE_GROUP=""
LOCATION="eastus"

# Print usage
usage() {
    echo "Usage: $0 <csv_file> [options]"
    echo ""
    echo "Options:"
    echo "  --config <path>        Path to oracle_config.ini (default: databases/oracle/oracle_config.ini)"
    echo "  --output <dir>         Output directory for generated agents (default: ./agents)"
    echo "  --deploy               Deploy agents to Azure after generation"
    echo "  --resource-group <rg>  Azure resource group for deployment"
    echo "  --location <loc>       Azure location (default: eastus)"
    echo "  --help                 Show this help message"
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
        --config)
            CONFIG_PATH="$2"
            shift 2
            ;;
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

if [ ! -f "$CONFIG_PATH" ]; then
    print_error "Config file not found: $CONFIG_PATH"
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

# Create output directory
mkdir -p "$OUTPUT_DIR"

print_info "========================================"
print_info "Table Agent Generator"
print_info "========================================"
print_info "CSV File: $CSV_FILE"
print_info "Config: $CONFIG_PATH"
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
tail -n +2 "$CSV_FILE" | while IFS=',' read -r SCHEMA TABLE_NAME || [ -n "$SCHEMA" ]; do
    # Skip empty lines
    if [ -z "$SCHEMA" ] || [ -z "$TABLE_NAME" ]; then
        continue
    fi
    
    # Trim whitespace
    SCHEMA=$(echo "$SCHEMA" | xargs)
    TABLE_NAME=$(echo "$TABLE_NAME" | xargs)
    
    CURRENT=$((CURRENT + 1))
    AGENT_NAME="${SCHEMA}_${TABLE_NAME}"
    AGENT_DIR="${OUTPUT_DIR}/${AGENT_NAME}"
    
    print_info "[$CURRENT] Generating agent for ${SCHEMA}.${TABLE_NAME}..."
    
    # Generate agent using Python
    if python3 "$(dirname "$0")/agents/agent_generator.py" \
        --config "$CONFIG_PATH" \
        --schema "$SCHEMA" \
        --table "$TABLE_NAME" \
        --output "$AGENT_DIR"; then
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
