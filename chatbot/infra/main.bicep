// =============================================================================
// Azure Infrastructure for Data Agent Chatbot
// =============================================================================
// Deploys the chatbot interface using Azure Static Web Apps.
//
// =============================================================================
// DISCLAIMER
// =============================================================================
// This code was generated with AI assistance (AI-generated code).
// It is provided "AS-IS" under the MIT License without warranty of any kind.
//
// Users should:
// - Review and test thoroughly before production use
// - Validate security implications for their specific use case
// - Ensure compliance with their organization's policies
//
// LICENSE: MIT License - Copyright (c) 2026
// See LICENSE file in project root for full license text.
// =============================================================================
//
// Deploy with: az deployment group create -g <resource-group> -f chatbot/infra/main.bicep
// =============================================================================

@description('Base name for all resources')
param baseName string = 'dataagent-chat'

@description('Azure region for resources')
param location string = resourceGroup().location

@description('MCP Server URL')
param mcpServerUrl string

@description('Optional: MCP Server authentication token')
@secure()
param mcpAuthToken string = ''

@description('SKU for Static Web App')
@allowed(['Free', 'Standard'])
param staticWebAppSku string = 'Free'

@description('Optional: Custom domain for the chatbot')
param customDomain string = ''

// Variables
var staticWebAppName = '${baseName}-swa-${uniqueString(resourceGroup().id)}'
var appInsightsName = '${baseName}-insights'
var logAnalyticsName = '${baseName}-logs-${uniqueString(resourceGroup().id)}'

// Log Analytics Workspace (for Application Insights)
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// Application Insights
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    Request_Source: 'rest'
  }
}

// Azure Static Web App
resource staticWebApp 'Microsoft.Web/staticSites@2023-01-01' = {
  name: staticWebAppName
  location: location
  sku: {
    name: staticWebAppSku
    tier: staticWebAppSku
  }
  properties: {
    stagingEnvironmentPolicy: 'Enabled'
    allowConfigFileUpdates: true
    buildProperties: {
      appLocation: '/'
      apiLocation: 'api'
      outputLocation: 'dist'
      appBuildCommand: 'npm run build'
      apiBuildCommand: ''
    }
  }
}

// Static Web App Settings (API Environment Variables)
resource staticWebAppSettings 'Microsoft.Web/staticSites/config@2023-01-01' = {
  parent: staticWebApp
  name: 'appsettings'
  properties: {
    MCP_SERVER_URL: mcpServerUrl
    MCP_AUTH_TOKEN: mcpAuthToken
    APPINSIGHTS_INSTRUMENTATIONKEY: appInsights.properties.InstrumentationKey
    APPLICATIONINSIGHTS_CONNECTION_STRING: appInsights.properties.ConnectionString
  }
}

// Custom domain (if provided)
resource customDomainResource 'Microsoft.Web/staticSites/customDomains@2023-01-01' = if (!empty(customDomain)) {
  parent: staticWebApp
  name: customDomain
  properties: {}
}

// Outputs
output staticWebAppName string = staticWebApp.name
output staticWebAppUrl string = 'https://${staticWebApp.properties.defaultHostname}'
output appInsightsInstrumentationKey string = appInsights.properties.InstrumentationKey
output appInsightsConnectionString string = appInsights.properties.ConnectionString

// Note: To get the deployment token after deployment, run:
// az staticwebapp secrets list --name <static-web-app-name> --query 'properties.apiKey' -o tsv
