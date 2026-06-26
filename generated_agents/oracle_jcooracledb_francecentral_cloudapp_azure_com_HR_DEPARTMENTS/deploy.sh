#!/bin/bash
# Deployment script for hr_departments agent

set -e

RESOURCE_GROUP="${RESOURCE_GROUP:-hr_departments-rg}"
LOCATION="${LOCATION:-eastus}"

while [[ $# -gt 0 ]]; do
    case $1 in
        --resource-group) RESOURCE_GROUP="$2"; shift 2 ;;
        --location) LOCATION="$2"; shift 2 ;;
        *) shift ;;
    esac
done

echo "Deploying hr_departments agent..."
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"

# Create resource group
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none

# Deploy infrastructure
DEPLOYMENT_OUTPUT=$(az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --template-file infra/main.bicep \
    --parameters @infra/main.parameters.json \
    --query "properties.outputs" \
    --output json)

FUNCTION_APP_NAME=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.functionAppName.value')

echo "Deploying function code to $FUNCTION_APP_NAME..."
func azure functionapp publish "$FUNCTION_APP_NAME" --python

echo "Deployment complete!"
echo "Function App: $FUNCTION_APP_NAME"
