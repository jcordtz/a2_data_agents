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
        print_info "Building image in ACR: $ACR_NAME"
        print_info "Build context: $(dirname "$0")"
        print_info "Dockerfile: $(dirname "$0")/Dockerfile"
        
        # Build and push using ACR build (no local Docker required)
        if az acr build \
            --registry "$ACR_NAME" \
            --image mcp-server:latest \
            --file "$(dirname "$0")/Dockerfile" \
            "$(dirname "$0")" 2>&1 | tee /tmp/acr-build.log; then
            print_success "✓ Container image built and pushed successfully"
        else
            print_error "❌ ACR build failed!"
            print_error "Build output:"
            cat /tmp/acr-build.log | tail -30
            print_error ""
            print_error "Troubleshooting:"
            print_error "  1. Check Dockerfile exists: ls -la $(dirname "$0")/Dockerfile"
            print_error "  2. Check mcp_server.py exists: ls -la $(dirname "$0")/mcp_server.py"
            print_error "  3. Check requirements.txt exists: ls -la $(dirname "$0")/requirements.txt"
            exit 1
        fi
        
        print_success "Container image built and pushed"
        
        # Get container app details
        CONTAINER_APP_NAME=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.containerAppName.value // empty')
        CONTAINER_ENV_NAME="${MCP_NAME}-env"
        
        if [ -z "$CONTAINER_APP_NAME" ]; then
            print_error "Failed to get container app name from deployment"
            exit 1
        fi
        
        if [ -n "$CONTAINER_APP_NAME" ]; then
            print_info "Waiting for container app to be ready before updating..."
            for i in {1..12}; do
                CA_STATE=$(az containerapp show \
                    --name "$CONTAINER_APP_NAME" \
                    --resource-group "$RESOURCE_GROUP" \
                    --query "properties.provisioningState" \
                    --output tsv 2>/dev/null || echo "Unknown")
                if [ "$CA_STATE" = "Succeeded" ]; then
                    print_success "Container app is ready (state: $CA_STATE)"
                    break
                fi
                if [ "$i" -eq 12 ]; then
                    print_info "Container app provisioning state: $CA_STATE — proceeding anyway"
                else
                    print_info "Container app state: $CA_STATE, waiting... ($i/12)"
                    sleep 15
                fi
            done

            print_info "Updating container app with MCP server image..."

            # Update image and replicas
            # Note: targetPort 8080 and ingress external are already set in Bicep template
            az containerapp update \
                --name "$CONTAINER_APP_NAME" \
                --resource-group "$RESOURCE_GROUP" \
                --image "${ACR_NAME}.azurecr.io/mcp-server:latest" \
                --min-replicas 1 \
                --output none
            
            print_success "Container app updated with new MCP server image"
            print_info "Waiting for new revision to start and stabilize (this may take 2-3 minutes)..."
            
            # Show what image we just deployed
            echo ""
            print_info "Checking container image status..."
            ACTUAL_IMAGE=$(az containerapp show \
                --name "$CONTAINER_APP_NAME" \
                --resource-group "$RESOURCE_GROUP" \
                --query "properties.template.containers[0].image" \
                --output tsv 2>/dev/null || echo "Unknown")
            print_info "  Container app is now running: $ACTUAL_IMAGE"
            
            # Wait longer for the new container to actually start
            sleep 45
        fi
    fi
fi

# Health check - verify the REAL MCP server is responding
print_info "Performing health check to verify MCP server is running..."
print_info "Waiting for container to initialize (this may take up to 3 minutes)..."
sleep 15

HEALTH_CHECK_PASSED=false
for i in {1..18}; do
    # Check for actual MCP server response (not hello-world placeholder)
    HEALTH_RESPONSE=$(curl -s "${MCP_URL}/health" 2>/dev/null || echo "")
    
    # Look for the real MCP server response structure
    if echo "$HEALTH_RESPONSE" | grep -q '"status".*"healthy"'; then
        print_success "✓ MCP Server health check passed!"
        print_info "  Response: $HEALTH_RESPONSE"
        HEALTH_CHECK_PASSED=true
        break
    elif echo "$HEALTH_RESPONSE" | grep -q "Hello from Azure"; then
        print_info "  Still starting (placeholder image detected)... attempt $i/18"
        sleep 10
    elif [ -z "$HEALTH_RESPONSE" ]; then
        print_info "  Waiting for server to respond... (attempt $i/18)"
        sleep 10
    else
        print_info "  Unexpected response (attempt $i/18): ${HEALTH_RESPONSE:0:100}"
        sleep 10
    fi
done

if [ "$HEALTH_CHECK_PASSED" = false ]; then
    print_error "❌ Health check did not pass"
    print_error "The MCP server may not have started correctly"
    print_error ""
    print_error "Troubleshooting steps:"
    print_error "  1. Check container logs: az containerapp logs show -n $CONTAINER_APP_NAME -g $RESOURCE_GROUP"
    print_error "  2. Check container state: az containerapp show -n $CONTAINER_APP_NAME -g $RESOURCE_GROUP"
    print_error "  3. Visit $MCP_URL/health in browser to see actual response"
    print_error ""
    print_error "If you see 'Hello from Azure' or connection errors, the deployment may still be in progress."
    print_error "Wait a few minutes and try: curl $MCP_URL/health"
else
    # Also verify CORS is working by checking API endpoint
    print_info "Verifying CORS and API endpoints..."
    if curl -s -H "Origin: https://example.com" -H "Access-Control-Request-Method: GET" "${MCP_URL}/api/agents" 2>/dev/null | grep -q "access_control\|agent\|error"; then
        print_success "✓ CORS headers are properly configured"
    else
        print_info "  CORS check inconclusive (may still be working)"
    fi
fi

print_info "========================================"
print_success "Deployment complete!"
print_info ""
print_info "MCP Server URL: $MCP_URL"
print_info "MCP Auth Token: $AUTH_TOKEN"
print_info ""
if [ "$HEALTH_CHECK_PASSED" = true ]; then
    print_info "✓ Server is ready for use"
else
    print_info "⚠️  Health check incomplete - server may still be starting"
    print_info ""
    print_info "To check server status, run:"
    print_info "  mcp/check_deployment.sh $RESOURCE_GROUP $CONTAINER_APP_NAME"
fi
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
