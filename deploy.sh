#!/bin/bash
# Azure Deployment Script for Data Agent

set -e

# Configuration
RESOURCE_GROUP="${RESOURCE_GROUP:-dataagent-rg}"
LOCATION="${LOCATION:-eastus}"
SUBSCRIPTION_ID="${SUBSCRIPTION_ID:-$(az account show --query id -o tsv)}"

echo "========================================"
echo "Data Agent Azure Deployment"
echo "========================================"
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo "Subscription: $SUBSCRIPTION_ID"
echo "========================================"

# Login check
if ! az account show &> /dev/null; then
    echo "Please login to Azure first: az login"
    exit 1
fi

# Create resource group
echo "Creating resource group..."
az group create \
    --name "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --output none

# Deploy infrastructure
echo "Deploying infrastructure..."
DEPLOYMENT_OUTPUT=$(az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --template-file infra/main.bicep \
    --parameters @infra/main.parameters.json \
    --query "properties.outputs" \
    --output json)

# Extract outputs
FUNCTION_APP_NAME=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.functionAppName.value')
FUNCTION_APP_URL=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.functionAppUrl.value')

echo "========================================"
echo "Infrastructure deployed!"
echo "Function App: $FUNCTION_APP_NAME"
echo "URL: $FUNCTION_APP_URL"
echo "========================================"

# Deploy function code
echo "Deploying function code..."
func azure functionapp publish "$FUNCTION_APP_NAME" --python

echo "========================================"
echo "Deployment complete!"
echo ""
echo "API Endpoints:"
echo "  POST $FUNCTION_APP_URL/api/query"
echo "  GET  $FUNCTION_APP_URL/api/tables"
echo "  GET  $FUNCTION_APP_URL/api/table/{name}/structure"
echo "  GET  $FUNCTION_APP_URL/api/health"
echo "========================================"
