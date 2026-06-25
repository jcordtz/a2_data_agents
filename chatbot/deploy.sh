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

# Check if logged in
if ! az account show &> /dev/null; then
    echo "Not logged in to Azure. Running 'az login'..."
    az login
fi

# Create resource group if it doesn't exist
echo "Creating resource group if needed..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none 2>/dev/null || true

# Build the frontend
echo "Building frontend..."
npm install
npm run build

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

# Check if SWA CLI is installed
if ! command -v swa &> /dev/null; then
    echo "Installing Azure Static Web Apps CLI..."
    npm install -g @azure/static-web-apps-cli
fi

# Deploy using SWA CLI
swa deploy dist \
    --api-location api \
    --deployment-token "$DEPLOYMENT_TOKEN" \
    --env production

echo ""
echo "============================================="
echo "Deployment Complete!"
echo "============================================="
echo "Chatbot URL: $STATIC_WEB_APP_URL"
echo ""
echo "To view logs:"
echo "  az monitor app-insights query --app $BASE_NAME-insights -g $RESOURCE_GROUP --analytics-query 'traces | order by timestamp desc | take 50'"
echo "============================================="
