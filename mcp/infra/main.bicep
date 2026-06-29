// =============================================================================
// MCP Server Infrastructure
// =============================================================================
// Deploys the MCP server to Azure Container Apps with supporting resources.
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
// Resources created:
//   - Azure Container Registry (for container images)
//   - Azure Container Apps Environment
//   - Azure Container App (MCP server)
//   - Log Analytics Workspace
//   - Storage Account (for agent registry)
//
// Deploy with:
//   az deployment group create -g <resource-group> -f infra/main.bicep
// =============================================================================

@description('Base name for all resources')
param baseName string = 'mcp-data-agents'

@description('Azure region for resources')
param location string = resourceGroup().location

@description('Optional authentication token for the MCP server')
@secure()
param authToken string = ''

// Variables
var uniqueSuffix = uniqueString(resourceGroup().id)
var sanitizedBaseName = replace(replace(baseName, '-', ''), '_', '')
var acrName = '${take(sanitizedBaseName, 30)}acr${uniqueSuffix}'
var logAnalyticsName = '${baseName}-logs'
var containerEnvName = '${baseName}-env'
var containerAppName = '${baseName}-app'
// Storage account: 3-24 chars, lowercase alphanumeric only
// uniqueSuffix is 13 chars, 'st' is 2 chars, so we have 9 chars for base name
var storageName = toLower(take('${take(sanitizedBaseName, 9)}st${uniqueSuffix}', 24))
// Azure Container Apps requires non-empty secret values
var effectiveAuthToken = empty(authToken) ? 'not-configured' : authToken

// Log Analytics Workspace
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

// Azure Container Registry
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
}

// Storage Account for agent registry
resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageName
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

// File share for persistent storage
resource fileService 'Microsoft.Storage/storageAccounts/fileServices@2023-01-01' = {
  parent: storage
  name: 'default'
}

resource fileShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-01-01' = {
  parent: fileService
  name: 'mcp-data'
  properties: {
    shareQuota: 1
  }
}

// Container Apps Environment
resource containerEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: containerEnvName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// Storage mount for Container Apps
resource storageMount 'Microsoft.App/managedEnvironments/storages@2023-05-01' = {
  parent: containerEnv
  name: 'mcp-storage'
  properties: {
    azureFile: {
      accountName: storage.name
      accountKey: storage.listKeys().keys[0].value
      shareName: fileShare.name
      accessMode: 'ReadWrite'
    }
  }
}

// Container App - MCP Server
resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: containerAppName
  location: location
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8080
        transport: 'http'
        allowInsecure: false
      }
      registries: [
        {
          server: acr.properties.loginServer
          username: acr.listCredentials().username
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        {
          name: 'acr-password'
          value: acr.listCredentials().passwords[0].value
        }
        {
          name: 'auth-token'
          value: effectiveAuthToken
        }
        {
          name: 'storage-connection'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storage.name};AccountKey=${storage.listKeys().keys[0].value};EndpointSuffix=${environment().suffixes.storage}'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'mcp-server'
          // Initial placeholder image - will be replaced after ACR build
          // Using a simple nginx image that starts quickly without volume dependencies
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'MCP_SERVER_PORT'
              value: '8080'
            }
            {
              name: 'MCP_REGISTRY_PATH'
              value: '/data/agents.json'
            }
            {
              name: 'MCP_AUTH_TOKEN'
              secretRef: 'auth-token'
            }
          ]
          // Note: Volume mounts will be added when updating with actual MCP server image
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 3
        rules: [
          {
            name: 'http-rule'
            http: {
              metadata: {
                concurrentRequests: '100'
              }
            }
          }
        ]
      }
    }
  }
}

// Outputs
output mcpServerUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
output mcpServerFqdn string = containerApp.properties.configuration.ingress.fqdn
output containerAppName string = containerApp.name
output acrName string = acr.name
output acrLoginServer string = acr.properties.loginServer
output storageAccountName string = storage.name
