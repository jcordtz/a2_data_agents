// Infrastructure for hr_departments agent

@description('Base name for resources')
param baseName string = 'hr_departments'

@description('Location for resources')
param location string = resourceGroup().location

@secure()
param oracleHost string
param oraclePort string = '1521'
param oracleServiceName string
@secure()
param oracleUsername string
@secure()
param oraclePassword string

// Sanitize names for Azure resources (no dots allowed)
var sanitizedResourceName = replace(replace(baseName, '.', '-'), '_', '-')
var functionAppName = '${sanitizedResourceName}-func-${uniqueString(resourceGroup().id)}'
// Storage account names: max 24 chars, lowercase letters and numbers only
// Use first 10 chars of sanitized baseName + 'st' + 12 char uniqueString = 24 chars max
var sanitizedBaseName = toLower(replace(replace(replace(baseName, '_', ''), '-', ''), '.', ''))
var storageAccountName = take('${take(sanitizedBaseName, 10)}st${uniqueString(resourceGroup().id)}', 24)
var appServicePlanName = '${sanitizedResourceName}-plan'
var appInsightsName = '${sanitizedResourceName}-insights'
var logAnalyticsName = '${sanitizedResourceName}-logs'

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
}

// Log Analytics Workspace (in the same resource group)
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

// Application Insights (linked to Log Analytics workspace)
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: { Application_Type: 'web', WorkspaceResourceId: logAnalytics.id }
}

resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: appServicePlanName
  location: location
  sku: { name: 'EP1', tier: 'ElasticPremium' }
  properties: { reserved: true, maximumElasticWorkerCount: 20 }
}

resource functionApp 'Microsoft.Web/sites@2023-01-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    publicNetworkAccess: 'Enabled'
    siteConfig: {
      pythonVersion: '3.12'
      linuxFxVersion: 'Python|3.12'
      appSettings: [
        { name: 'AzureWebJobsStorage', value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=core.windows.net;' }
        { name: 'FUNCTIONS_WORKER_RUNTIME', value: 'python' }
        { name: 'FUNCTIONS_EXTENSION_VERSION', value: '~4' }
        { name: 'ENABLE_ORYX_BUILD', value: 'true' }
        { name: 'SCM_DO_BUILD_DURING_DEPLOYMENT', value: 'true' }
        { name: 'APPINSIGHTS_INSTRUMENTATIONKEY', value: appInsights.properties.InstrumentationKey }
        { name: 'ORACLE_HOST', value: oracleHost }
        { name: 'ORACLE_PORT', value: oraclePort }
        { name: 'ORACLE_SERVICE_NAME', value: oracleServiceName }
        { name: 'ORACLE_USERNAME', value: oracleUsername }
        { name: 'ORACLE_PASSWORD', value: oraclePassword }
      ]
    }
  }
}

// Role assignment for Managed Identity to access storage
// Must have explicit dependsOn to ensure proper ordering without circular dependency
resource storageBlobRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storageAccount
  name: guid(functionApp.id, storageAccount.id, 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b')
  properties: {
    principalId: functionApp.identity.principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b')
    principalType: 'ServicePrincipal'
  }
  dependsOn: [
    functionApp
  ]
}

output functionAppName string = functionApp.name
output functionAppUrl string = 'https://${functionApp.properties.defaultHostName}'
