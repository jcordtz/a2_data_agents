// =============================================================================
// Azure Infrastructure for Data Agent
// =============================================================================
// Deploys the Data Agent Azure Function with supporting resources.
//
// =============================================================================
// PREREQUISITES (Must exist before deployment)
// =============================================================================
// This infrastructure assumes the following resources ALREADY EXIST and are
// accessible from the deployed Azure Function:
//
// 1. KEY VAULT with database secrets:
//    The following secrets must be pre-configured in the Key Vault:
//    - Oracle: oracle-host, oracle-username, oracle-password
//    - MSSQL: mssql-host, mssql-username, mssql-password
//    - PostgreSQL: postgres-host, postgres-username, postgres-password
//    - IBM DB2: ibmdb2-host, ibmdb2-username, ibmdb2-password
//
// 2. DATABASE(S) - At least one of the following must be accessible:
//    - Oracle Database (on-premises or cloud)
//    - Microsoft SQL Server (on-premises, Azure SQL, or VM)
//    - PostgreSQL (on-premises, Azure Database for PostgreSQL, or VM)
//    - IBM DB2 LUW (on-premises or cloud)
//
// 3. MICROSOFT PURVIEW (required for Purview integration):
//    - Microsoft Purview account with Data Catalog enabled
//    - Service principal with appropriate permissions
//    - Tables registered as data assets in Purview
//
// This template does NOT create Key Vault, secrets, databases, or Purview.
// It deploys the application and grants it access to the existing Key Vault.
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
// Existing Key Vault (Required)
// =============================================================================
@description('Name of the existing Key Vault containing database secrets')
param keyVaultName string

// =============================================================================
// Oracle Database Connection Parameters
// =============================================================================
@description('Oracle database port')
param oraclePort string = '1521'

@description('Oracle service name')
param oracleServiceName string = ''

// =============================================================================
// Microsoft SQL Server Connection Parameters
// =============================================================================
@description('SQL Server database port')
param mssqlPort string = '1433'

@description('SQL Server database name')
param mssqlDatabase string = ''

@description('Use Windows/Integrated authentication for SQL Server')
param mssqlTrustedConnection bool = false

// =============================================================================
// PostgreSQL Connection Parameters
// =============================================================================
@description('PostgreSQL database port')
param postgresPort string = '5432'

@description('PostgreSQL database name')
param postgresDatabase string = ''

// =============================================================================
// IBM DB2 LUW Connection Parameters
// =============================================================================
@description('IBM DB2 database port')
param ibmdb2Port string = '50000'

@description('IBM DB2 database name')
param ibmdb2Database string = ''

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

// Reference existing Key Vault
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

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
        // Oracle Configuration (secrets from existing Key Vault)
        {
          name: 'ORACLE_HOST'
          value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=oracle-host)'
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
          value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=oracle-username)'
        }
        {
          name: 'ORACLE_PASSWORD'
          value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=oracle-password)'
        }
        // MSSQL Configuration (secrets from existing Key Vault)
        {
          name: 'MSSQL_HOST'
          value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=mssql-host)'
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
          value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=mssql-username)'
        }
        {
          name: 'MSSQL_PASSWORD'
          value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=mssql-password)'
        }
        {
          name: 'MSSQL_TRUSTED_CONNECTION'
          value: string(mssqlTrustedConnection)
        }
        // PostgreSQL Configuration (secrets from existing Key Vault)
        {
          name: 'POSTGRES_HOST'
          value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=postgres-host)'
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
          value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=postgres-username)'
        }
        {
          name: 'POSTGRES_PASSWORD'
          value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=postgres-password)'
        }
        // IBM DB2 Configuration (secrets from existing Key Vault)
        {
          name: 'IBMDB2_HOST'
          value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=ibmdb2-host)'
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
          value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=ibmdb2-username)'
        }
        {
          name: 'IBMDB2_PASSWORD'
          value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=ibmdb2-password)'
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

// Key Vault access for Function App (grant access to existing Key Vault)
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
output keyVaultNameUsed string = keyVaultName
output chatbotStaticWebAppName string = deployChatbot ? chatbotStaticWebApp.name : ''

// Note: To get the chatbot URL and deployment token after deployment, run:
// az staticwebapp show --name <static-web-app-name> --query 'defaultHostname' -o tsv
// az staticwebapp secrets list --name <static-web-app-name> --query 'properties.apiKey' -o tsv
