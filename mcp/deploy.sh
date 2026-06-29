#!/bin/bash
# =============================================================================
# MCP Server Deployment Script
# =============================================================================
# Deploys the MCP server to Azure Container Apps or App Service.
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
#   ./deploy.sh [options]
#
# OPTIONS:
#   --resource-group <rg>   Azure resource group (required)
#   --location <loc>        Azure location (default: eastus)
#   --name <name>           MCP server name (default: mcp-data-agents)
#   --auth-token <token>    Optional authentication token
#   --use-container-apps    Deploy to Container Apps (default)
#   --use-app-service       Deploy to App Service instead
#
# EXAMPLES:
#   ./deploy.sh --resource-group mcp-rg --location westus2
#   ./deploy.sh --resource-group mcp-rg --auth-token mysecret
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default values
RESOURCE_GROUP=""
LOCATION="eastus"
MCP_NAME="mcp-data-agents"
AUTH_TOKEN=""
USE_CONTAINER_APPS=true

# Print functions
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Usage
usage() {
    echo "Usage: $0 --resource-group <rg> [options]"
    echo ""
    echo "Options:"
    echo "  --resource-group <rg>   Azure resource group (required)"
    echo "  --location <loc>        Azure location (default: eastus)"
    echo "  --name <name>           MCP server name (default: mcp-data-agents)"
    echo "  --auth-token <token>    Optional authentication token"
    echo "  --use-container-apps    Deploy to Container Apps (default)"
    echo "  --use-app-service       Deploy to App Service"
    echo "  --help                  Show this help"
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --resource-group) RESOURCE_GROUP="$2"; shift 2 ;;
        --location) LOCATION="$2"; shift 2 ;;
        --name) MCP_NAME="$2"; shift 2 ;;
        --auth-token) AUTH_TOKEN="$2"; shift 2 ;;
        --use-container-apps) USE_CONTAINER_APPS=true; shift ;;
        --use-app-service) USE_CONTAINER_APPS=false; shift ;;
        --help) usage ;;
        *) print_error "Unknown option: $1"; usage ;;
    esac
done

# Validate
if [ -z "$RESOURCE_GROUP" ]; then
    print_error "Resource group is required (--resource-group)"
    usage
fi

# Check Azure CLI
if ! command -v az &> /dev/null; then
    print_error "Azure CLI is not installed"
    exit 1
fi

if ! az account show &> /dev/null; then
    print_error "Please login to Azure: az login"
    exit 1
fi

print_info "========================================"
print_info "MCP Server Deployment"
print_info "========================================"
print_info "Resource Group: $RESOURCE_GROUP"
print_info "Location: $LOCATION"
print_info "Name: $MCP_NAME"
print_info "Deployment: $([ "$USE_CONTAINER_APPS" = true ] && echo 'Container Apps' || echo 'App Service')"
print_info "========================================"

# Generate auth token if not provided
if [ -z "$AUTH_TOKEN" ]; then
    print_info "Generating authentication token..."
    AUTH_TOKEN=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)
    print_info "Auth token generated (will be displayed at the end)"
fi

# Create resource group
print_info "Creating resource group..."
az group create \
    --name "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --output none

# Clean up existing resources that can't be updated in place
CONTAINER_ENV_NAME="${MCP_NAME}-env"
CONTAINER_APP_NAME="${MCP_NAME}-app"

# Delete existing Container App if it exists (allows clean redeployment)
print_info "Checking for existing Container App..."
if az containerapp show \
    --name "$CONTAINER_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --output none 2>/dev/null; then
    print_info "Deleting existing Container App (will be recreated)..."
    az containerapp delete \
        --name "$CONTAINER_APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --yes \
        --output none 2>/dev/null || true
fi

# Clean up existing storage mount if it exists (workaround for Azure Container Apps limitation)
# Azure Container Apps storage mounts can't be updated, only the account key can be changed
print_info "Checking for existing storage mount..."
if az containerapp env storage show \
    --name "$CONTAINER_ENV_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --storage-name "mcp-storage" \
    --output none 2>/dev/null; then
    print_info "Removing existing storage mount (will be recreated)..."
    az containerapp env storage remove \
        --name "$CONTAINER_ENV_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --storage-name "mcp-storage" \
        --yes \
        --output none 2>/dev/null || true
fi

# Deploy infrastructure
print_info "Deploying infrastructure..."

# Prepare parameters
PARAMS="baseName=$MCP_NAME"
if [ -n "$AUTH_TOKEN" ]; then
    PARAMS="$PARAMS authToken=$AUTH_TOKEN"
fi

DEPLOYMENT_OUTPUT=$(az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --template-file "$(dirname "$0")/infra/main.bicep" \
    --parameters $PARAMS \
    --query "properties.outputs" \
    --output json)

# Extract outputs
if [ "$USE_CONTAINER_APPS" = true ]; then
    MCP_URL=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.mcpServerUrl.value // empty')
    MCP_FQDN=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.mcpServerFqdn.value // empty')
else
    MCP_URL=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.appServiceUrl.value // empty')
fi

if [ -z "$MCP_URL" ]; then
    print_error "Failed to get deployment outputs"
    echo "$DEPLOYMENT_OUTPUT"
    exit 1
fi

print_success "Infrastructure deployed!"
print_info "MCP Server URL: $MCP_URL"

# Build and push container (for Container Apps)
if [ "$USE_CONTAINER_APPS" = true ]; then
    print_info "Building container image..."
    
    # Get ACR name from deployment
    ACR_NAME=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.acrName.value // empty')
    
    if [ -n "$ACR_NAME" ]; then
        # Login to ACR
        az acr login --name "$ACR_NAME"
        
        # Build and push
        az acr build \
            --registry "$ACR_NAME" \
            --image mcp-server:latest \
            --file "$(dirname "$0")/Dockerfile" \
            "$(dirname "$0")"
        
        print_success "Container image built and pushed"
        
        # Update container app with new image and volume mount
        CONTAINER_APP_NAME=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.containerAppName.value // empty')
        CONTAINER_ENV_NAME="${MCP_NAME}-env"
        
        if [ -n "$CONTAINER_APP_NAME" ]; then
            print_info "Updating container app with MCP server image..."
            
            # Update with the new image, volume mount, and min replicas
            az containerapp update \
                --name "$CONTAINER_APP_NAME" \
                --resource-group "$RESOURCE_GROUP" \
                --image "${ACR_NAME}.azurecr.io/mcp-server:latest" \
                --min-replicas 1 \
                --output none
            
            print_success "Container app updated"
            print_info "Waiting for new revision to deploy..."
            sleep 20
        fi
    fi
fi

# Health check
print_info "Performing health check..."
print_info "Waiting for container to start (this may take up to 2 minutes)..."
sleep 30

for i in {1..12}; do
    if curl -s "${MCP_URL}/health" | grep -q "healthy"; then
        print_success "Health check passed!"
        break
    fi
    if [ $i -eq 12 ]; then
        print_info "Health check did not pass yet, but deployment may still be in progress."
        print_info "Check Azure portal for container status."
    else
        print_info "Waiting for server to be ready... (attempt $i/12)"
        sleep 10
    fi
done

print_info "========================================"
print_success "Deployment complete!"
print_info ""
print_info "MCP Server URL: $MCP_URL"
print_info "MCP Auth Token: $AUTH_TOKEN"
print_info ""
print_info "To register an agent:"
print_info "  ./register_agent.sh --agent-id <id> \\"
print_info "      --endpoint <function-url> \\"
print_info "      --api-key <key> \\"
print_info "      --mcp-server $MCP_URL"
print_info ""
print_info "MCP Tools endpoint: ${MCP_URL}/mcp/v1/tools"
print_info "Health check: ${MCP_URL}/health"
print_info "========================================"

# Output structured data for automation (can be parsed by calling scripts)
echo ""
echo "MCP_DEPLOYMENT_OUTPUT_START"
echo "MCP_URL=$MCP_URL"
echo "MCP_AUTH_TOKEN=$AUTH_TOKEN"
echo "MCP_DEPLOYMENT_OUTPUT_END"
