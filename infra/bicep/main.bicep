// =============================================================================
// Azure Infrastructure for Data Agent
// =============================================================================
// Deploys the Data Agent Azure Function with supporting resources.
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
// Deploy with: az deployment group create -g <resource-group> -f infra/main.bicep
// =============================================================================

@description('Base name for all resources')
param baseName string = 'dataagent'

@description('Azure region for resources')
param location string = resourceGroup().location

@description('Azure OpenAI deployment name')
param openAIDeploymentName string = 'gpt-4o'

// =============================================================================
// Oracle Database Parameters
// =============================================================================
@description('Oracle database host')
@secure()
param oracleHost string = ''

@description('Oracle database port')
param oraclePort string = '1521'

@description('Oracle service name')
param oracleServiceName string = ''

@description('Oracle username')
@secure()
param oracleUsername string = ''

@description('Oracle password')
@secure()
param oraclePassword string = ''

// =============================================================================
// Microsoft SQL Server Parameters
// =============================================================================
@description('SQL Server database host')
@secure()
param mssqlHost string = ''

@description('SQL Server database port')
param mssqlPort string = '1433'

@description('SQL Server database name')
param mssqlDatabase string = ''

@description('SQL Server username')
@secure()
param mssqlUsername string = ''

@description('SQL Server password')
@secure()
param mssqlPassword string = ''

@description('Use Windows/Integrated authentication for SQL Server')
param mssqlTrustedConnection bool = false

// =============================================================================
// PostgreSQL Parameters
// =============================================================================
@description('PostgreSQL database host')
@secure()
param postgresHost string = ''

@description('PostgreSQL database port')
param postgresPort string = '5432'

@description('PostgreSQL database name')
param postgresDatabase string = ''

@description('PostgreSQL username')
@secure()
param postgresUsername string = ''

@description('PostgreSQL password')
@secure()
param postgresPassword string = ''

// =============================================================================
// IBM DB2 LUW Parameters
// =============================================================================
@description('IBM DB2 database host')
@secure()
param ibmdb2Host string = ''

@description('IBM DB2 database port')
param ibmdb2Port string = '50000'

@description('IBM DB2 database name')
param ibmdb2Database string = ''

@description('IBM DB2 username')
@secure()
param ibmdb2Username string = ''

@description('IBM DB2 password')
@secure()
param ibmdb2Password string = ''

// =============================================================================
// Chatbot Parameters
// =============================================================================
@description('Deploy the chatbot interface')
param deployChatbot bool = false

@description('MCP Server URL for the chatbot')
param chatbotMcpServerUrl string = ''

@description('Chatbot Static Web App SKU')
@allowed(['Free', 'Standard'])
param chatbotSku string = 'Free'

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

// Store MSSQL credentials in Key Vault
resource mssqlPasswordSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(mssqlPassword)) {
  parent: keyVault
  name: 'mssql-password'
  properties: {
    value: mssqlPassword
  }
}

resource mssqlUsernameSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(mssqlUsername)) {
  parent: keyVault
  name: 'mssql-username'
  properties: {
    value: mssqlUsername
  }
}

resource mssqlHostSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(mssqlHost)) {
  parent: keyVault
  name: 'mssql-host'
  properties: {
    value: mssqlHost
  }
}

// Store PostgreSQL credentials in Key Vault
resource postgresPasswordSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(postgresPassword)) {
  parent: keyVault
  name: 'postgres-password'
  properties: {
    value: postgresPassword
  }
}

resource postgresUsernameSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(postgresUsername)) {
  parent: keyVault
  name: 'postgres-username'
  properties: {
    value: postgresUsername
  }
}

resource postgresHostSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(postgresHost)) {
  parent: keyVault
  name: 'postgres-host'
  properties: {
    value: postgresHost
  }
}

// Store IBM DB2 credentials in Key Vault
resource ibmdb2PasswordSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(ibmdb2Password)) {
  parent: keyVault
  name: 'ibmdb2-password'
  properties: {
    value: ibmdb2Password
  }
}

resource ibmdb2UsernameSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(ibmdb2Username)) {
  parent: keyVault
  name: 'ibmdb2-username'
  properties: {
    value: ibmdb2Username
  }
}

resource ibmdb2HostSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(ibmdb2Host)) {
  parent: keyVault
  name: 'ibmdb2-host'
  properties: {
    value: ibmdb2Host
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
        // MSSQL Configuration
        {
          name: 'MSSQL_HOST'
          value: !empty(mssqlHost) ? '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=mssql-host)' : ''
        }
        {
          name: 'MSSQL_PORT'
          value: mssqlPort
        }
        {
          name: 'MSSQL_DATABASE'
          value: mssqlDatabase
        }
        {
          name: 'MSSQL_USERNAME'
          value: !empty(mssqlUsername) ? '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=mssql-username)' : ''
        }
        {
          name: 'MSSQL_PASSWORD'
          value: !empty(mssqlPassword) ? '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=mssql-password)' : ''
        }
        {
          name: 'MSSQL_TRUSTED_CONNECTION'
          value: string(mssqlTrustedConnection)
        }
        // PostgreSQL Configuration
        {
          name: 'POSTGRES_HOST'
          value: !empty(postgresHost) ? '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=postgres-host)' : ''
        }
        {
          name: 'POSTGRES_PORT'
          value: postgresPort
        }
        {
          name: 'POSTGRES_DATABASE'
          value: postgresDatabase
        }
        {
          name: 'POSTGRES_USERNAME'
          value: !empty(postgresUsername) ? '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=postgres-username)' : ''
        }
        {
          name: 'POSTGRES_PASSWORD'
          value: !empty(postgresPassword) ? '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=postgres-password)' : ''
        }
        // IBM DB2 Configuration
        {
          name: 'IBMDB2_HOST'
          value: !empty(ibmdb2Host) ? '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=ibmdb2-host)' : ''
        }
        {
          name: 'IBMDB2_PORT'
          value: ibmdb2Port
        }
        {
          name: 'IBMDB2_DATABASE'
          value: ibmdb2Database
        }
        {
          name: 'IBMDB2_USERNAME'
          value: !empty(ibmdb2Username) ? '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=ibmdb2-username)' : ''
        }
        {
          name: 'IBMDB2_PASSWORD'
          value: !empty(ibmdb2Password) ? '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=ibmdb2-password)' : ''
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

// =============================================================================
// Chatbot (Optional)
// =============================================================================
// Chatbot Static Web App
var chatbotStaticWebAppName = '${baseName}-chat-swa-${uniqueString(resourceGroup().id)}'

resource chatbotStaticWebApp 'Microsoft.Web/staticSites@2023-01-01' = if (deployChatbot) {
  name: chatbotStaticWebAppName
  location: location
  sku: {
    name: chatbotSku
    tier: chatbotSku
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

// Chatbot Static Web App Settings
resource chatbotStaticWebAppSettings 'Microsoft.Web/staticSites/config@2023-01-01' = if (deployChatbot) {
  parent: chatbotStaticWebApp
  name: 'appsettings'
  properties: {
    MCP_SERVER_URL: !empty(chatbotMcpServerUrl) ? chatbotMcpServerUrl : 'https://${functionApp.properties.defaultHostName}'
    APPINSIGHTS_INSTRUMENTATIONKEY: appInsights.properties.InstrumentationKey
    APPLICATIONINSIGHTS_CONNECTION_STRING: appInsights.properties.ConnectionString
  }
}

// Outputs
output functionAppName string = functionApp.name
output functionAppUrl string = 'https://${functionApp.properties.defaultHostName}'
output openAIEndpoint string = openAI.properties.endpoint
output keyVaultName string = keyVault.name
output chatbotStaticWebAppName string = deployChatbot ? chatbotStaticWebApp.name : ''

// Note: To get the chatbot URL and deployment token after deployment, run:
// az staticwebapp show --name <static-web-app-name> --query 'defaultHostname' -o tsv
// az staticwebapp secrets list --name <static-web-app-name> --query 'properties.apiKey' -o tsv
