#!/bin/bash
# =============================================================================
# Deployment Script for Data Agent Chatbot
# =============================================================================
# Deploys the chatbot to Azure Static Web Apps.
#
# Usage: ./deploy.sh [options]
# Options:
#   --resource-group, -g    Resource group name (required)
#   --location, -l          Azure region (default: eastus2)
#   --mcp-url               MCP Server URL (required)
#   --mcp-token             MCP Server auth token (optional)
#   --sku                   Static Web App SKU: Free or Standard (default: Free)
#   --help, -h              Show help
# =============================================================================

set -e

# Default values
LOCATION="eastus2"
SKU="Free"
BASE_NAME="dataagent-chat"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -g|--resource-group)
            RESOURCE_GROUP="$2"
            shift 2
            ;;
        -l|--location)
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
        --sku)
            SKU="$2"
            shift 2
            ;;
        --base-name)
            BASE_NAME="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: ./deploy.sh [options]"
            echo ""
            echo "Options:"
            echo "  --resource-group, -g    Resource group name (required)"
            echo "  --location, -l          Azure region (default: eastus2)"
            echo "  --mcp-url               MCP Server URL (required)"
            echo "  --mcp-token             MCP Server auth token (optional)"
            echo "  --sku                   Static Web App SKU: Free or Standard (default: Free)"
            echo "  --base-name             Base name for resources (default: dataagent-chat)"
            echo "  --help, -h              Show help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate required parameters
if [ -z "$RESOURCE_GROUP" ]; then
    echo "Error: --resource-group is required"
    exit 1
fi

if [ -z "$MCP_URL" ]; then
    echo "Error: --mcp-url is required"
    exit 1
fi

echo "============================================="
echo "Deploying Data Agent Chatbot"
echo "============================================="
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo "MCP Server URL: $MCP_URL"
echo "SKU: $SKU"
echo "============================================="

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "Error: Azure CLI is not installed"
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "Error: npm is not installed"
    echo "Please install Node.js 18+ which includes npm:"
    echo "  macOS:   brew install node"
    echo "  Linux:   curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt-get install -y nodejs"
    echo "  Windows: Download from https://nodejs.org/"
    exit 1
fi

# Check if logged in
if ! az account show &> /dev/null; then
    echo "Not logged in to Azure. Running 'az login'..."
    az login
fi

# Create resource group if it doesn't exist
echo "Creating resource group if needed..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none 2>/dev/null || true

# Clean up existing Static Web App if it exists (allows clean redeployment)
echo "Checking for existing Static Web App..."
EXISTING_SWA=$(az staticwebapp list \
    --resource-group "$RESOURCE_GROUP" \
    --query "[?starts_with(name, '$BASE_NAME')].name" \
    --output tsv 2>/dev/null || true)

if [ -n "$EXISTING_SWA" ]; then
    echo "Found existing Static Web App: $EXISTING_SWA"
    echo "Deleting existing Static Web App for clean redeployment..."
    az staticwebapp delete \
        --name "$EXISTING_SWA" \
        --resource-group "$RESOURCE_GROUP" \
        --yes \
        --output none 2>/dev/null || true
fi

# Build the frontend
echo "Building frontend..."

# Change to chatbot directory (where package.json is located)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

npm install

# Build with MCP server URL and token injected
VITE_MCP_SERVER_URL="$MCP_URL" VITE_MCP_AUTH_TOKEN="${MCP_TOKEN:-}" npm run build

# Copy staticwebapp.config.json to dist folder
cp staticwebapp.config.json dist/

# Deploy infrastructure
echo "Deploying Azure infrastructure..."
DEPLOYMENT_OUTPUT=$(az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --template-file infra/main.bicep \
    --parameters baseName="$BASE_NAME" \
    --parameters location="$LOCATION" \
    --parameters mcpServerUrl="$MCP_URL" \
    --parameters mcpAuthToken="${MCP_TOKEN:-}" \
    --parameters staticWebAppSku="$SKU" \
    --query "properties.outputs" \
    --output json)

# Extract outputs
STATIC_WEB_APP_NAME=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.staticWebAppName.value')
STATIC_WEB_APP_URL=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.staticWebAppUrl.value')

echo ""
echo "Infrastructure deployed successfully!"
echo "Static Web App: $STATIC_WEB_APP_NAME"
echo "URL: $STATIC_WEB_APP_URL"

# Get deployment token
echo "Retrieving deployment token..."
DEPLOYMENT_TOKEN=$(az staticwebapp secrets list --name "$STATIC_WEB_APP_NAME" --query 'properties.apiKey' -o tsv)

# Deploy the application using SWA CLI
echo ""
echo "Deploying application code..."
echo "Note: The chatbot calls the MCP server directly (frontend-only deployment)"

# Check if SWA CLI is installed
if ! command -v swa &> /dev/null; then
    echo "Installing Azure Static Web Apps CLI..."
    npm install -g @azure/static-web-apps-cli
fi

# Deploy using SWA CLI
# Platform and API runtime are configured in staticwebapp.config.json
swa deploy dist \
    --deployment-token "$DEPLOYMENT_TOKEN" \
    --env production

echo ""
echo "============================================="
echo "Deployment Complete!"
echo "============================================="
echo "Chatbot URL: $STATIC_WEB_APP_URL"
echo "MCP Server: $MCP_URL"
echo ""
echo "Note: The chatbot calls the MCP server directly."
echo "============================================="
