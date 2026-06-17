// Azure Infrastructure for Data Agent
// Deploy with: az deployment group create -g <resource-group> -f infra/main.bicep

@description('Base name for all resources')
param baseName string = 'dataagent'

@description('Azure region for resources')
param location string = resourceGroup().location

@description('Azure OpenAI deployment name')
param openAIDeploymentName string = 'gpt-4o'

@description('Oracle database host')
@secure()
param oracleHost string

@description('Oracle database port')
param oraclePort string = '1521'

@description('Oracle service name')
param oracleServiceName string

@description('Oracle username')
@secure()
param oracleUsername string

@description('Oracle password')
@secure()
param oraclePassword string

// Variables
var functionAppName = '${baseName}-func-${uniqueString(resourceGroup().id)}'
var storageAccountName = '${baseName}st${uniqueString(resourceGroup().id)}'
var appServicePlanName = '${baseName}-plan'
var appInsightsName = '${baseName}-insights'
var openAIName = '${baseName}-openai-${uniqueString(resourceGroup().id)}'
var keyVaultName = '${baseName}-kv-${uniqueString(resourceGroup().id)}'

// Storage Account for Function App
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: take(replace(storageAccountName, '-', ''), 24)
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
  }
}

// Application Insights
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    Request_Source: 'rest'
  }
}

// App Service Plan (Consumption)
resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: appServicePlanName
  location: location
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  properties: {
    reserved: true // Linux
  }
}

// Azure OpenAI
resource openAI 'Microsoft.CognitiveServices/accounts@2023-10-01-preview' = {
  name: openAIName
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: openAIName
    publicNetworkAccess: 'Enabled'
  }
}

// Azure OpenAI Deployment
resource openAIDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-10-01-preview' = {
  parent: openAI
  name: openAIDeploymentName
  sku: {
    name: 'Standard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-05-13'
    }
  }
}

// Key Vault for secrets
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: take(keyVaultName, 24)
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    accessPolicies: []
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
  }
}

// Store Oracle credentials in Key Vault
resource oraclePasswordSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'oracle-password'
  properties: {
    value: oraclePassword
  }
}

resource oracleUsernameSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'oracle-username'
  properties: {
    value: oracleUsername
  }
}

resource oracleHostSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'oracle-host'
  properties: {
    value: oracleHost
  }
}

// Function App
resource functionApp 'Microsoft.Web/sites@2023-01-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      pythonVersion: '3.11'
      linuxFxVersion: 'Python|3.11'
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: appInsights.properties.InstrumentationKey
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsights.properties.ConnectionString
        }
        {
          name: 'AZURE_OPENAI_ENDPOINT'
          value: openAI.properties.endpoint
        }
        {
          name: 'AZURE_OPENAI_API_KEY'
          value: openAI.listKeys().key1
        }
        {
          name: 'AZURE_OPENAI_DEPLOYMENT'
          value: openAIDeploymentName
        }
        {
          name: 'ORACLE_HOST'
          value: '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=oracle-host)'
        }
        {
          name: 'ORACLE_PORT'
          value: oraclePort
        }
        {
          name: 'ORACLE_SERVICE_NAME'
          value: oracleServiceName
        }
        {
          name: 'ORACLE_USERNAME'
          value: '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=oracle-username)'
        }
        {
          name: 'ORACLE_PASSWORD'
          value: '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=oracle-password)'
        }
      ]
      cors: {
        allowedOrigins: [
          'https://portal.azure.com'
        ]
      }
    }
    httpsOnly: true
  }
}

// Key Vault access for Function App
resource keyVaultAccessPolicy 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, functionApp.id, 'Key Vault Secrets User')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6') // Key Vault Secrets User
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Outputs
output functionAppName string = functionApp.name
output functionAppUrl string = 'https://${functionApp.properties.defaultHostName}'
output openAIEndpoint string = openAI.properties.endpoint
output keyVaultName string = keyVault.name
