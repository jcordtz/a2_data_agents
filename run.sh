#!/bin/bash
# =============================================================================
# Master Orchestration Script for Data Agents Solution
# =============================================================================
# Runs different parts of the solution in the correct order.
# Allows selective execution of specific components.
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
#   ./run.sh [options]
#
# STEPS (in execution order):
#   1. generate    - Generate agent code from CSV file
#   2. deploy      - Deploy generated agents to Azure Functions
#   3. mcp         - Deploy MCP server to Azure
#   4. register    - Register agents with MCP server
#   5. chatbot     - Deploy chatbot to Azure Static Web Apps
#
# RESOURCE GROUP:
#   If the specified resource group already exists, you will be prompted to:
#   - Delete and recreate it, OR
#   - Keep existing and continue, OR
#   - Abort
#   Use --yes flag to automatically delete existing resource group.
#
# OPTIONS:
#   --all                   Run all steps (default if no step specified)
#   --generate              Run only agent generation
#   --deploy                Run only agent deployment
#   --mcp                   Run only MCP server deployment
#   --register              Run only agent registration
#   --chatbot               Run only chatbot deployment
#
#   --csv <file>            CSV file for agent generation (default: sample_tables.csv)
#   --output <dir>          Output directory for agents (default: ./generated_agents)
#   --resource-group <rg>   Azure resource group (required for deployment)
#   --location <loc>        Azure location (default: eastus)
#   --mcp-url <url>         MCP server URL (for registration/chatbot)
#   --mcp-token <token>     MCP server auth token
#
#   --yes, -y               Auto-confirm all prompts (including RG deletion)
#   --dry-run               Show what would be done without executing
#   --help                  Show this help message
#
# EXAMPLES:
#   # Run all steps
#   ./run.sh --all --csv tables.csv --resource-group my-rg
#
#   # Generate agents only
#   ./run.sh --generate --csv tables.csv --output ./my_agents
#
#   # Deploy agents and MCP server
#   ./run.sh --deploy --mcp --resource-group my-rg
#
#   # Deploy with auto-confirmation (deletes existing RG if present)
#   ./run.sh --all --resource-group my-rg --yes
#
#   # Register agents with existing MCP server
#   ./run.sh --register --mcp-url https://mcp.example.com
# =============================================================================

set -e

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default configuration
CSV_FILE="sample_tables.csv"
OUTPUT_DIR="./generated_agents"
RESOURCE_GROUP="a2-data-agent-res"
LOCATION="eastus"
MCP_URL=""
MCP_TOKEN=""
DRY_RUN=false
AUTO_YES=false

# Steps to run (default: none, will run all if none specified)
RUN_GENERATE=false
RUN_DEPLOY=false
RUN_MCP=false
RUN_REGISTER=false
RUN_CHATBOT=false
RUN_ALL=false

# Print functions
print_header() {
    echo ""
    echo -e "${CYAN}========================================"
    echo -e "$1"
    echo -e "========================================${NC}"
}

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

print_step() {
    echo ""
    echo -e "${GREEN}────────────────────────────────────────${NC}"
    echo -e "${GREEN}STEP: $1${NC}"
    echo -e "${GREEN}────────────────────────────────────────${NC}"
}

# Print usage
usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Steps (select one or more, or --all):"
    echo "  --all                   Run all steps in order"
    echo "  --generate              Generate agent code from CSV"
    echo "  --deploy                Deploy generated agents to Azure"
    echo "  --mcp                   Deploy MCP server to Azure"
    echo "  --register              Register agents with MCP server"
    echo "  --chatbot               Deploy chatbot to Azure"
    echo ""
    echo "Configuration:"
    echo "  --csv <file>            CSV file for generation (default: sample_tables.csv)"
    echo "  --output <dir>          Output directory for agents (default: ./generated_agents)"
    echo "  --resource-group <rg>   Azure resource group (required for deployment)"
    echo "  --location <loc>        Azure location (default: eastus)"
    echo "  --mcp-url <url>         MCP server URL (for registration/chatbot)"
    echo "  --mcp-token <token>     MCP server auth token"
    echo ""
    echo "Other:"
    echo "  --yes, -y               Auto-confirm all prompts (including RG deletion)"
    echo "  --dry-run               Show what would be done without executing"
    echo "  --help                  Show this help message"
    echo ""
    echo "Resource Group Handling:"
    echo "  If the resource group already exists, you will be prompted to:"
    echo "  - Delete and recreate it (recommended for clean deployment)"
    echo "  - Keep existing and continue"
    echo "  - Abort"
    echo "  With --yes flag, existing RG will be automatically deleted."
    echo ""
    echo "Examples:"
    echo "  $0 --all --csv tables.csv --resource-group my-rg"
    echo "  $0 --generate --csv tables.csv"
    echo "  $0 --deploy --mcp --resource-group my-rg"
    echo "  $0 --all --resource-group my-rg --yes  (auto-delete existing RG)"
    exit 1
}

# Parse arguments
if [ $# -lt 1 ]; then
    usage
fi

while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            RUN_ALL=true
            shift
            ;;
        --generate)
            RUN_GENERATE=true
            shift
            ;;
        --deploy)
            RUN_DEPLOY=true
            shift
            ;;
        --mcp)
            RUN_MCP=true
            shift
            ;;
        --register)
            RUN_REGISTER=true
            shift
            ;;
        --chatbot)
            RUN_CHATBOT=true
            shift
            ;;
        --csv)
            CSV_FILE="$2"
            shift 2
            ;;
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --resource-group)
            RESOURCE_GROUP="$2"
            shift 2
            ;;
        --location)
            LOCATION="$2"
            shift 2
            ;;
        --mcp-url)
            MCP_URL="$2"
            shift 2
            ;;
        --mcp-token)
            MCP_TOKEN="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
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

# If --all is set, enable all steps
if [ "$RUN_ALL" = true ]; then
    RUN_GENERATE=true
    RUN_DEPLOY=true
    RUN_MCP=true
    RUN_REGISTER=true
    RUN_CHATBOT=true
fi

# If no steps selected, show usage
if [ "$RUN_GENERATE" = false ] && [ "$RUN_DEPLOY" = false ] && \
   [ "$RUN_MCP" = false ] && [ "$RUN_REGISTER" = false ] && \
   [ "$RUN_CHATBOT" = false ]; then
    print_error "No steps selected. Use --all or specify steps to run."
    usage
fi

# Validate required parameters
if [ "$RUN_DEPLOY" = true ] || [ "$RUN_MCP" = true ] || [ "$RUN_CHATBOT" = true ]; then
    if [ -z "$RESOURCE_GROUP" ]; then
        print_error "Resource group is required for deployment steps (--resource-group)"
        exit 1
    fi
fi

# Function to check if resource group exists and handle deletion
check_resource_group() {
    local rg_name="$1"
    local skip_check="$2"
    
    if [ -z "$rg_name" ]; then
        return 0
    fi
    
    # Check if resource group exists (requires Azure CLI)
    if ! command -v az &> /dev/null; then
        print_warning "Azure CLI not found. Skipping resource group existence check."
        return 0
    fi
    
    print_info "Checking if resource group exists: $rg_name"
    
    if az group exists --name "$rg_name" --query "value" --output tsv 2>/dev/null | grep -q "true"; then
        print_warning "Resource group '$rg_name' already exists"
        echo ""
        
        # If not skipping check or in dry-run mode, ask user what to do
        if [ "$skip_check" != "skip" ] && [ "$DRY_RUN" = false ]; then
            local delete_choice
            
            if [ "$AUTO_YES" = true ]; then
                print_info "Resource group will be deleted (--yes flag set)"
                delete_choice="yes"
            else
                echo "Options:"
                echo "  1) Delete and recreate the resource group"
                echo "  2) Keep existing resource group and continue"
                echo "  3) Abort"
                echo ""
                read -p "Choose option (1/2/3): " delete_choice
                
                case $delete_choice in
                    1) delete_choice="yes" ;;
                    2) delete_choice="no" ;;
                    3) delete_choice="abort" ;;
                    *)
                        print_error "Invalid option. Aborting."
                        exit 1
                        ;;
                esac
            fi
            
            if [ "$delete_choice" = "yes" ]; then
                print_warning "Deleting resource group: $rg_name"
                
                if ! az group delete \
                    --name "$rg_name" \
                    --yes \
                    --no-wait; then
                    print_error "Failed to delete resource group"
                    exit 1
                fi
                
                print_success "Resource group deletion initiated (running in background)"
                print_info "Waiting for deletion to complete (this may take a few minutes)..."
                
                # Wait for deletion to complete
                local max_attempts=120  # 10 minutes with 5-second intervals
                local attempt=0
                while [ $attempt -lt $max_attempts ]; do
                    if ! az group exists --name "$rg_name" --query "value" --output tsv 2>/dev/null | grep -q "true"; then
                        print_success "Resource group deleted successfully"
                        return 0
                    fi
                    
                    sleep 5
                    attempt=$((attempt + 1))
                    
                    # Print progress every 6 attempts (30 seconds)
                    if [ $((attempt % 6)) -eq 0 ]; then
                        print_info "Still waiting for deletion... (${attempt}0 seconds elapsed)"
                    fi
                done
                
                print_error "Resource group deletion timed out after 10 minutes"
                exit 1
                
            elif [ "$delete_choice" = "no" ]; then
                print_info "Keeping existing resource group"
                return 0
                
            elif [ "$delete_choice" = "abort" ]; then
                print_info "Aborted by user"
                exit 0
            fi
        elif [ "$DRY_RUN" = true ]; then
            print_info "[DRY RUN] Would delete resource group: $rg_name"
            return 0
        fi
        
    else
        print_info "Resource group does not exist. Will be created during deployment."
    fi
}


# Check prerequisites for chatbot deployment
if [ "$RUN_CHATBOT" = true ]; then
    if ! command -v npm &> /dev/null; then
        print_error "npm is required for chatbot deployment but not found"
        print_info "Install Node.js 18+ which includes npm:"
        print_info "  macOS:   brew install node"
        print_info "  Linux:   curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt-get install -y nodejs"
        print_info "  Windows: Download from https://nodejs.org/"
        exit 1
    fi
fi

if [ "$RUN_REGISTER" = true ] || [ "$RUN_CHATBOT" = true ]; then
    if [ -z "$MCP_URL" ] && [ "$RUN_MCP" = false ]; then
        print_warning "MCP URL not specified. Will use localhost or deploy first."
    fi
fi

# Print configuration
print_header "Data Agents Solution - Master Script"

echo ""
print_info "Configuration:"
echo "  CSV File:       $CSV_FILE"
echo "  Output Dir:     $OUTPUT_DIR"
echo "  Resource Group: ${RESOURCE_GROUP:-"(not set)"}"
echo "  Location:       $LOCATION"
echo "  MCP URL:        ${MCP_URL:-"(will be determined after MCP deployment)"}"
echo "  Dry Run:        $DRY_RUN"
echo "  Auto-confirm:   $AUTO_YES"
echo ""
print_info "Steps to run:"
[ "$RUN_GENERATE" = true ] && echo "  [1] Generate agents from CSV"
[ "$RUN_DEPLOY" = true ] && echo "  [2] Deploy agents to Azure"
[ "$RUN_MCP" = true ] && echo "  [3] Deploy MCP server"
[ "$RUN_REGISTER" = true ] && echo "  [4] Register agents with MCP"
[ "$RUN_CHATBOT" = true ] && echo "  [5] Deploy chatbot"
echo ""

if [ "$DRY_RUN" = true ]; then
    print_warning "DRY RUN MODE - No changes will be made"
    echo ""
fi

# Check resource group if deployment steps are requested
if [ "$RUN_DEPLOY" = true ] || [ "$RUN_MCP" = true ] || [ "$RUN_CHATBOT" = true ]; then
    echo ""
    check_resource_group "$RESOURCE_GROUP"
    echo ""
fi

# Confirm before proceeding (skip if --yes flag is set)
if [ "$AUTO_YES" = true ]; then
    print_info "Auto-confirming (--yes flag set)"
else
    read -p "Continue? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        print_info "Aborted by user."
        exit 0
    fi
fi

# Track deployed MCP URL for later steps
DEPLOYED_MCP_URL=""

# =============================================================================
# STEP 1: Generate Agents
# =============================================================================
if [ "$RUN_GENERATE" = true ]; then
    print_step "1. Generate Agents"
    
    if [ ! -f "$CSV_FILE" ]; then
        print_error "CSV file not found: $CSV_FILE"
        exit 1
    fi
    
    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY RUN] Would run: ./generate_agents.sh --csv $CSV_FILE --output $OUTPUT_DIR"
    else
        print_info "Generating agents from $CSV_FILE..."
        
        # Build generate args
        GENERATE_ARGS="--csv $CSV_FILE --output $OUTPUT_DIR"
        if [ "$AUTO_YES" = true ]; then
            GENERATE_ARGS="$GENERATE_ARGS --yes"
        fi
        
        "$SCRIPT_DIR/generate_agents.sh" $GENERATE_ARGS
        
        print_success "Agent generation complete!"
    fi
fi

# =============================================================================
# STEP 2: Deploy Agents to Azure
# =============================================================================
if [ "$RUN_DEPLOY" = true ]; then
    print_step "2. Deploy Agents to Azure"
    
    if [ ! -d "$OUTPUT_DIR" ]; then
        print_error "Output directory not found: $OUTPUT_DIR"
        print_info "Run with --generate first or specify existing directory with --output"
        exit 1
    fi
    
    # Count agents to deploy
    AGENT_COUNT=$(find "$OUTPUT_DIR" -maxdepth 1 -type d | wc -l)
    AGENT_COUNT=$((AGENT_COUNT - 1))  # Subtract 1 for the directory itself
    
    if [ "$AGENT_COUNT" -eq 0 ]; then
        print_warning "No agents found in $OUTPUT_DIR"
    else
        print_info "Found $AGENT_COUNT agents to deploy"
        
        DEPLOYED=0
        FAILED=0
        
        for agent_dir in "$OUTPUT_DIR"/*/; do
            if [ -d "$agent_dir" ]; then
                agent_name=$(basename "$agent_dir")
                
                if [ "$DRY_RUN" = true ]; then
                    print_info "[DRY RUN] Would deploy: $agent_name"
                else
                    print_info "Deploying $agent_name..."
                    
                    if [ -f "${agent_dir}deploy.sh" ]; then
                        # Export environment variables for the deploy script
                        export RESOURCE_GROUP="$RESOURCE_GROUP"
                        export LOCATION="$LOCATION"
                        
                        # Change to agent directory before running deploy.sh
                        # (deploy.sh uses relative paths like infra/main.bicep)
                        pushd "$agent_dir" > /dev/null
                        if bash deploy.sh; then
                            print_success "Deployed: $agent_name"
                            DEPLOYED=$((DEPLOYED + 1))
                        else
                            print_warning "Failed to deploy: $agent_name"
                            FAILED=$((FAILED + 1))
                        fi
                        popd > /dev/null
                    else
                        print_warning "No deploy.sh found in $agent_dir"
                        FAILED=$((FAILED + 1))
                    fi
                fi
            fi
        done
        
        if [ "$DRY_RUN" = false ]; then
            print_info "Deployment summary: $DEPLOYED succeeded, $FAILED failed"
        fi
    fi
fi

# =============================================================================
# STEP 3: Deploy MCP Server
# =============================================================================
if [ "$RUN_MCP" = true ]; then
    print_step "3. Deploy MCP Server"
    
    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY RUN] Would run: mcp/deploy.sh --resource-group $RESOURCE_GROUP --location $LOCATION"
    else
        print_info "Deploying MCP server..."
        
        MCP_DEPLOY_ARGS="--resource-group $RESOURCE_GROUP --location $LOCATION"
        
        if [ -n "$MCP_TOKEN" ]; then
            MCP_DEPLOY_ARGS="$MCP_DEPLOY_ARGS --auth-token $MCP_TOKEN"
        fi
        
        # Capture the MCP URL and auth token from deployment output
        MCP_OUTPUT=$(bash "$SCRIPT_DIR/mcp/deploy.sh" $MCP_DEPLOY_ARGS 2>&1 | tee /dev/tty)
        
        # Extract structured output between markers (most reliable)
        if echo "$MCP_OUTPUT" | grep -q "MCP_DEPLOYMENT_OUTPUT_START"; then
            DEPLOYED_MCP_URL=$(echo "$MCP_OUTPUT" | sed -n '/MCP_DEPLOYMENT_OUTPUT_START/,/MCP_DEPLOYMENT_OUTPUT_END/p' | grep "MCP_URL=" | cut -d'=' -f2-)
            DEPLOYED_MCP_TOKEN=$(echo "$MCP_OUTPUT" | sed -n '/MCP_DEPLOYMENT_OUTPUT_START/,/MCP_DEPLOYMENT_OUTPUT_END/p' | grep "MCP_AUTH_TOKEN=" | cut -d'=' -f2-)
        else
            # Fallback: extract from "MCP Server URL:" line - more specific than grepping all URLs
            DEPLOYED_MCP_URL=$(echo "$MCP_OUTPUT" | grep "^.*MCP Server URL:" | sed -E 's/.*MCP Server URL: //' | tail -1)
        fi
        
        # Validate extracted URL is a real Azure Container Apps URL (not a docs link)
        if [ -n "$DEPLOYED_MCP_URL" ]; then
            if echo "$DEPLOYED_MCP_URL" | grep -qE '^https://.*\.azurecontainerapps\.io'; then
                print_success "MCP server deployed at: $DEPLOYED_MCP_URL"
                # Use deployed URL for subsequent steps if not explicitly provided
                if [ -z "$MCP_URL" ]; then
                    MCP_URL="$DEPLOYED_MCP_URL"
                fi
                # Use deployed token if not explicitly provided
                if [ -z "$MCP_TOKEN" ] && [ -n "$DEPLOYED_MCP_TOKEN" ]; then
                    MCP_TOKEN="$DEPLOYED_MCP_TOKEN"
                    print_info "Using generated auth token for subsequent steps"
                fi
            else
                print_error "Invalid MCP URL extracted: $DEPLOYED_MCP_URL"
                print_info "Expected format: https://<name>.azurecontainerapps.io"
                print_info "Full MCP output:"
                echo "$MCP_OUTPUT" | tail -50
                exit 1
            fi
        else
            print_error "Failed to extract MCP Server URL from deployment output"
            print_info "Full output (last 50 lines):"
            echo "$MCP_OUTPUT" | tail -50
            exit 1
        fi
    fi
fi

# =============================================================================
# STEP 4: Register Agents with MCP
# =============================================================================
if [ "$RUN_REGISTER" = true ]; then
    print_step "4. Register Agents with MCP Server"
    
    if [ ! -d "$OUTPUT_DIR" ]; then
        print_error "Output directory not found: $OUTPUT_DIR"
        exit 1
    fi
    
    # Use provided MCP URL or default to localhost
    EFFECTIVE_MCP_URL="${MCP_URL:-http://localhost:8080}"
    
    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY RUN] Would run: mcp/register_all_agents.sh --agents-dir $OUTPUT_DIR --mcp-server $EFFECTIVE_MCP_URL"
    else
        print_info "Registering agents with MCP server at $EFFECTIVE_MCP_URL..."
        
        REGISTER_ARGS="--agents-dir $OUTPUT_DIR --mcp-server $EFFECTIVE_MCP_URL"
        
        if [ -n "$MCP_TOKEN" ]; then
            REGISTER_ARGS="$REGISTER_ARGS --mcp-token $MCP_TOKEN"
        fi
        
        bash "$SCRIPT_DIR/mcp/register_all_agents.sh" $REGISTER_ARGS
        
        print_success "Agent registration complete"
    fi
fi

# =============================================================================
# STEP 5: Deploy Chatbot
# =============================================================================
if [ "$RUN_CHATBOT" = true ]; then
    print_step "5. Deploy Chatbot"
    
    # Use provided MCP URL or deployed URL
    EFFECTIVE_MCP_URL="${MCP_URL:-$DEPLOYED_MCP_URL}"
    
    if [ -z "$EFFECTIVE_MCP_URL" ]; then
        print_error "MCP URL is required for chatbot deployment"
        print_info "Either deploy MCP server first (--mcp) or provide URL (--mcp-url)"
        exit 1
    fi
    
    # Validate the MCP URL format
    if ! echo "$EFFECTIVE_MCP_URL" | grep -qE '^https?://'; then
        print_error "Invalid MCP URL: $EFFECTIVE_MCP_URL"
        print_info "URL must start with http:// or https://"
        exit 1
    fi
    
    print_info "Using MCP Server URL: $EFFECTIVE_MCP_URL"
    
    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY RUN] Would run: chatbot/deploy.sh --resource-group $RESOURCE_GROUP --location westeurope --mcp-url $EFFECTIVE_MCP_URL"
    else
        print_info "Deploying chatbot (always to westeurope for Static Web Apps)..."
        
        # Chatbot (Static Web Apps) always deploys to westeurope
        CHATBOT_ARGS="--resource-group $RESOURCE_GROUP --location westeurope --mcp-url $EFFECTIVE_MCP_URL"
        
        if [ -n "$MCP_TOKEN" ]; then
            CHATBOT_ARGS="$CHATBOT_ARGS --mcp-token $MCP_TOKEN"
        fi
        
        bash "$SCRIPT_DIR/chatbot/deploy.sh" $CHATBOT_ARGS
        
        print_success "Chatbot deployment complete"
    fi
fi

# =============================================================================
# Summary
# =============================================================================
print_header "Execution Complete"

echo ""
print_info "Summary of executed steps:"
[ "$RUN_GENERATE" = true ] && echo "  ✓ Generate agents"
[ "$RUN_DEPLOY" = true ] && echo "  ✓ Deploy agents"
[ "$RUN_MCP" = true ] && echo "  ✓ Deploy MCP server"
[ "$RUN_REGISTER" = true ] && echo "  ✓ Register agents"
[ "$RUN_CHATBOT" = true ] && echo "  ✓ Deploy chatbot"
echo ""

if [ -n "$MCP_URL" ] || [ -n "$DEPLOYED_MCP_URL" ]; then
    print_info "MCP Server URL: ${MCP_URL:-$DEPLOYED_MCP_URL}"
fi

if [ -n "$MCP_TOKEN" ]; then
    print_info "MCP Auth Token: $MCP_TOKEN"
fi

print_success "All requested steps completed successfully!"
