#!/bin/bash
# Deployment script for hr_departments agent

set -e

RESOURCE_GROUP="${RESOURCE_GROUP:-hr_departments-rg}"
LOCATION="${LOCATION:-eastus}"
FORCE_REDEPLOY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --resource-group) RESOURCE_GROUP="$2"; shift 2 ;;
        --location) LOCATION="$2"; shift 2 ;;
        --force) FORCE_REDEPLOY=true; shift ;;
        *) shift ;;
    esac
done

# Verify Azure CLI is available
if ! command -v az &> /dev/null; then
    echo "ERROR: Azure CLI (az) not found."
    echo ""
    echo "Please install it:"
    echo "  macOS:   brew install azure-cli"
    echo "  Linux:   curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
    echo "  Windows: winget install Microsoft.AzureCLI"
    exit 1
fi

echo "Deploying hr_departments agent..."
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"

# Create resource group
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none

# Check if function app already exists (look for any function app matching the pattern)
SANITIZED_NAME=$(echo "hr_departments" | tr '.' '-' | tr '_' '-')
EXISTING_FUNC=$(az functionapp list \
    --resource-group "$RESOURCE_GROUP" \
    --query "[?starts_with(name, '$SANITIZED_NAME-func')].name | [0]" \
    --output tsv 2>/dev/null || true)

if [ -n "$EXISTING_FUNC" ] && [ "$FORCE_REDEPLOY" = false ]; then
    echo "Function App already exists: $EXISTING_FUNC"
    echo "Skipping infrastructure deployment, deploying code only..."
    FUNCTION_APP_NAME="$EXISTING_FUNC"
else
    if [ -n "$EXISTING_FUNC" ] && [ "$FORCE_REDEPLOY" = true ]; then
        echo "Force redeploy: deleting existing Function App..."
        az functionapp delete --name "$EXISTING_FUNC" --resource-group "$RESOURCE_GROUP" --output none 2>/dev/null || true
        sleep 10
    fi
    
    # Deploy infrastructure (Elastic Premium plan for remote build support)
    echo "Deploying infrastructure..."
    DEPLOYMENT_OUTPUT=$(az deployment group create \
        --resource-group "$RESOURCE_GROUP" \
        --template-file infra/main.bicep \
        --parameters @infra/main.parameters.json \
        --query "properties.outputs" \
        --output json 2>&1) || {
        echo "ERROR: Infrastructure deployment failed"
        echo "$DEPLOYMENT_OUTPUT"
        exit 1
    }

    # Extract function app name (use jq if available, otherwise grep/sed)
    if command -v jq &> /dev/null; then
        FUNCTION_APP_NAME=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.functionAppName.value')
    else
        FUNCTION_APP_NAME=$(echo "$DEPLOYMENT_OUTPUT" | grep -o '"functionAppName"[^}]*' | grep -o '"value"[^"]*"[^"]*"' | sed 's/.*"\([^"]*\)"$/\1/')
    fi

    # Verify function app name was extracted
    if [ -z "$FUNCTION_APP_NAME" ] || [ "$FUNCTION_APP_NAME" = "null" ]; then
        echo "ERROR: Failed to extract function app name from deployment output"
        echo "Deployment output: $DEPLOYMENT_OUTPUT"
        exit 1
    fi

    echo "Function App Name: $FUNCTION_APP_NAME"

    # Wait for Function App to be ready
    echo "Waiting for Function App to be ready..."
    MAX_RETRIES=30
    RETRY_COUNT=0
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if az functionapp show --name "$FUNCTION_APP_NAME" --resource-group "$RESOURCE_GROUP" --query "state" -o tsv 2>/dev/null | grep -qi "running"; then
            echo "Function App is ready"
            break
        fi
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
            echo "ERROR: Function App not ready after $MAX_RETRIES attempts"
            exit 1
        fi
        echo "Waiting... ($RETRY_COUNT/$MAX_RETRIES)"
        sleep 5
    done
fi

echo "Deploying function code to $FUNCTION_APP_NAME (remote build)..."

# Create deployment package (source code only - dependencies built in Azure)
DEPLOY_ZIP="deploy_package.zip"
rm -f "$DEPLOY_ZIP"
zip -r "$DEPLOY_ZIP" . -x "*.git*" -x "*__pycache__*" -x "*.pyc" -x "infra/*" -x "deploy.sh" -x "*.zip" -x ".venv/*" -x "venv/*" -x ".python_packages/*"

# Deploy with remote build (Elastic Premium plan supports this)
az functionapp deployment source config-zip \
    --name "$FUNCTION_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --src "$DEPLOY_ZIP" \
    --build-remote true \
    --timeout 600

# Cleanup
rm -f "$DEPLOY_ZIP"

echo "Deployment complete!"
echo "Function App: $FUNCTION_APP_NAME"
echo "Function URL: https://$FUNCTION_APP_NAME.azurewebsites.net"
