#!/bin/bash
# Diagnostic script to check MCP server deployment status

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[!]${NC} $1"; }

# Parse arguments
RESOURCE_GROUP="${1:-}"
CONTAINER_APP_NAME="${2:-}"

if [ -z "$RESOURCE_GROUP" ] || [ -z "$CONTAINER_APP_NAME" ]; then
    echo "Usage: $0 <resource-group> <container-app-name>"
    echo ""
    echo "Example:"
    echo "  $0 my-rg mcp-data-agents-app"
    exit 1
fi

print_info "========================================"
print_info "MCP Server Deployment Diagnostic"
print_info "========================================"
print_info "Resource Group: $RESOURCE_GROUP"
print_info "Container App: $CONTAINER_APP_NAME"
print_info ""

# 1. Check if container app exists
print_info "1. Checking container app status..."
if ! az containerapp show \
    --name "$CONTAINER_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --output none 2>/dev/null; then
    print_error "Container app not found: $CONTAINER_APP_NAME"
    exit 1
fi
print_success "Container app exists"

# 2. Get container app details
print_info "2. Retrieving container app details..."
APP_DETAILS=$(az containerapp show \
    --name "$CONTAINER_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "{state: properties.provisioningState, image: properties.template.containers[0].image, replicas: properties.template.scale.minReplicas, fqdn: properties.configuration.ingress.fqdn}" \
    --output json)

PROV_STATE=$(echo "$APP_DETAILS" | jq -r '.state')
CURRENT_IMAGE=$(echo "$APP_DETAILS" | jq -r '.image')
MIN_REPLICAS=$(echo "$APP_DETAILS" | jq -r '.replicas')
FQDN=$(echo "$APP_DETAILS" | jq -r '.fqdn')

print_info "  Provisioning State: $PROV_STATE"
print_info "  Current Image: $CURRENT_IMAGE"
print_info "  Min Replicas: $MIN_REPLICAS"
print_info "  FQDN: $FQDN"

if [[ "$CURRENT_IMAGE" == *"hello"* ]]; then
    print_error "❌ Still running PLACEHOLDER image (hello-world)!"
    print_error "   The real MCP server image has NOT been deployed"
    print_error "   Run: mcp/deploy.sh --resource-group $RESOURCE_GROUP"
    exit 1
elif [[ "$CURRENT_IMAGE" == *"mcp-server"* ]]; then
    print_success "Running MCP server image (correct)"
else
    print_warning "Unknown image: $CURRENT_IMAGE"
fi

echo ""

# 3. Test health endpoint
print_info "3. Testing health endpoint..."
HEALTH_URL="https://$FQDN/health"
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "$HEALTH_URL" 2>/dev/null || echo "error\n000")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -1)
BODY=$(echo "$HEALTH_RESPONSE" | head -n -1)

print_info "  URL: $HEALTH_URL"
print_info "  HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_success "Health endpoint responding (HTTP 200)"
    if echo "$BODY" | grep -q "healthy"; then
        print_success "Server reports: healthy"
    else
        print_warning "Response body: $BODY"
    fi
else
    print_error "Health endpoint returned HTTP $HTTP_CODE"
    print_info "  Response: $BODY"
fi

echo ""

# 4. Test CORS headers
print_info "4. Testing CORS headers..."
CORS_URL="https://$FQDN/api/agents"
print_info "  URL: $CORS_URL"

CORS_RESPONSE=$(curl -s -i -X OPTIONS "$CORS_URL" 2>/dev/null || echo "Connection failed")
CORS_HEADER=$(echo "$CORS_RESPONSE" | grep -i "access-control-allow-origin" || echo "(not found)")

print_info "  OPTIONS preflight response:"
echo "$CORS_RESPONSE" | head -10 | sed 's/^/    /'

if echo "$CORS_HEADER" | grep -q "access-control"; then
    print_success "CORS header found: $CORS_HEADER"
else
    print_error "❌ NO CORS header in response!"
    print_error "   This is why the browser is blocking requests"
    print_error "   The MCP server may have crashed or is not responding properly"
fi

echo ""

# 5. Check container logs
print_info "5. Checking container logs..."
LOGS=$(az containerapp logs show \
    --name "$CONTAINER_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --tail 50 2>&1 || echo "Could not retrieve logs")

if echo "$LOGS" | grep -q "ERROR\|error\|Exception\|FAILED"; then
    print_error "Errors found in logs:"
    echo "$LOGS" | grep -i "error\|exception\|failed" | head -10 | sed 's/^/    /'
else
    print_success "No obvious errors in recent logs"
fi

if echo "$LOGS" | grep -q "Uvicorn running"; then
    print_success "MCP server (Uvicorn) is running"
elif echo "$LOGS" | grep -q "Hello from Azure\|listening\|started"; then
    print_error "Container started but wrong image (not MCP server)"
else
    print_warning "Could not determine container startup status from logs"
fi

echo ""

# 6. Summary
print_info "========================================"
print_info "Diagnostic Summary"
print_info "========================================"

if [ "$HTTP_CODE" = "200" ] && echo "$CORS_HEADER" | grep -q "access-control"; then
    print_success "✓ MCP server is running and responding correctly"
    print_success "✓ CORS headers are being sent"
    print_success "The chatbot should be able to connect"
elif [ "$HTTP_CODE" = "200" ]; then
    print_warning "Server is responding but CORS headers missing"
    print_error "This will cause browser to block requests"
    print_error "Possible causes:"
    print_error "  1. Wrong application running (not real MCP server)"
    print_error "  2. MCP server crashed and placeholder restarted"
    print_error "  3. CORS middleware not working"
    print_error ""
    print_error "Solution: Redeploy MCP server"
    print_error "  ./mcp/deploy.sh --resource-group $RESOURCE_GROUP"
else
    print_error "Server is not responding to health checks"
    print_error "Possible causes:"
    print_error "  1. Container hasn't started yet (wait 2-3 minutes)"
    print_error "  2. Container crashed on startup"
    print_error "  3. Container app misconfigured"
    print_error ""
    print_error "Check container logs:"
    print_error "  az containerapp logs show -n $CONTAINER_APP_NAME -g $RESOURCE_GROUP --tail 100"
fi

print_info "========================================"
