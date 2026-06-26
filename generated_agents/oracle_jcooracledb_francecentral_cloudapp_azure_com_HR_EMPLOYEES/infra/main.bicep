// Infrastructure for hr_employees agent

@description('Base name for resources')
param baseName string = 'hr_employees'

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

var functionAppName = '${baseName}-func-${uniqueString(resourceGroup().id)}'
var storageAccountName = take(replace('${baseName}st${uniqueString(resourceGroup().id)}', '-', ''), 24)
var appServicePlanName = '${baseName}-plan'
var appInsightsName = '${baseName}-insights'

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: { Application_Type: 'web' }
}

resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: appServicePlanName
  location: location
  sku: { name: 'Y1', tier: 'Dynamic' }
  properties: { reserved: true }
}

resource functionApp 'Microsoft.Web/sites@2023-01-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      pythonVersion: '3.11'
      appSettings: [
        { name: 'AzureWebJobsStorage', value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}' }
        { name: 'FUNCTIONS_WORKER_RUNTIME', value: 'python' }
        { name: 'FUNCTIONS_EXTENSION_VERSION', value: '~4' }
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

output functionAppName string = functionApp.name
output functionAppUrl string = 'https://${functionApp.properties.defaultHostName}'
