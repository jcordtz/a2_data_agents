# =============================================================================
# Main Infrastructure Configuration
# =============================================================================
#
# =============================================================================
# PREREQUISITES (Must exist before deployment)
# =============================================================================
# This infrastructure assumes the following resources ALREADY EXIST and are
# accessible from the deployed Azure Function:
#
# 1. KEY VAULT with database secrets:
#    The following secrets must be pre-configured in the Key Vault:
#    - Oracle: oracle-host, oracle-username, oracle-password
#    - MSSQL: mssql-host, mssql-username, mssql-password
#    - PostgreSQL: postgres-host, postgres-username, postgres-password
#    - IBM DB2: ibmdb2-host, ibmdb2-username, ibmdb2-password
#
# 2. DATABASE(S) - At least one of the following must be accessible:
#    - Oracle Database (on-premises or cloud)
#    - Microsoft SQL Server (on-premises, Azure SQL, or VM)
#    - PostgreSQL (on-premises, Azure Database for PostgreSQL, or VM)
#    - IBM DB2 LUW (on-premises or cloud)
#
# 3. MICROSOFT PURVIEW (required for Purview integration):
#    - Microsoft Purview account with Data Catalog enabled
#    - Service principal with appropriate permissions
#    - Tables registered as data assets in Purview
#
# This Terraform configuration does NOT create Key Vault, secrets, databases,
# or Purview. It deploys the application and grants it access to existing
# Key Vault secrets.
# =============================================================================

data "azurerm_client_config" "current" {}

data "azurerm_resource_group" "main" {
  name = var.resource_group_name
}

# Reference existing Key Vault
data "azurerm_key_vault" "main" {
  name                = var.key_vault_name
  resource_group_name = var.key_vault_resource_group != "" ? var.key_vault_resource_group : var.resource_group_name
}

# Random suffix for globally unique names
resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

# Local variables for resource names
locals {
  suffix                      = random_string.suffix.result
  function_app_name           = "${var.base_name}-func-${local.suffix}"
  storage_account_name        = substr(replace("${var.base_name}st${local.suffix}", "-", ""), 0, 24)
  app_service_plan_name       = "${var.base_name}-plan"
  app_insights_name           = "${var.base_name}-insights"
  openai_name                 = "${var.base_name}-openai-${local.suffix}"
  chatbot_static_web_app_name = "${var.base_name}-chat-swa-${local.suffix}"
}

# =============================================================================
# Storage Account
# =============================================================================
resource "azurerm_storage_account" "main" {
  name                     = local.storage_account_name
  resource_group_name      = data.azurerm_resource_group.main.name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  tags = var.tags
}

# =============================================================================
# Application Insights
# =============================================================================
resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.base_name}-law-${local.suffix}"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = var.tags
}

resource "azurerm_application_insights" "main" {
  name                = local.app_insights_name
  resource_group_name = data.azurerm_resource_group.main.name
  location            = var.location
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"

  tags = var.tags
}

# =============================================================================
# App Service Plan (Elastic Premium - supports remote build)
# =============================================================================
resource "azurerm_service_plan" "main" {
  name                         = local.app_service_plan_name
  resource_group_name          = data.azurerm_resource_group.main.name
  location                     = var.location
  os_type                      = "Linux"
  sku_name                     = "EP1"
  maximum_elastic_worker_count = 20

  tags = var.tags
}

# =============================================================================
# Azure OpenAI
# =============================================================================
resource "azurerm_cognitive_account" "openai" {
  name                  = local.openai_name
  resource_group_name   = data.azurerm_resource_group.main.name
  location              = var.location
  kind                  = "OpenAI"
  sku_name              = "S0"
  custom_subdomain_name = local.openai_name

  tags = var.tags
}

resource "azurerm_cognitive_deployment" "gpt" {
  name                 = var.openai_deployment_name
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = var.openai_model_name
    version = var.openai_model_version
  }

  scale {
    type     = "Standard"
    capacity = var.openai_capacity
  }
}

# =============================================================================
# Function App
# =============================================================================
resource "azurerm_linux_function_app" "main" {
  name                       = local.function_app_name
  resource_group_name        = data.azurerm_resource_group.main.name
  location                   = var.location
  storage_account_name       = azurerm_storage_account.main.name
  storage_account_access_key = azurerm_storage_account.main.primary_access_key
  service_plan_id            = azurerm_service_plan.main.id
  public_network_access_enabled = true

  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_stack {
      python_version = "3.12"
    }

    cors {
      allowed_origins = ["https://portal.azure.com"]
    }
  }

  app_settings = {
    FUNCTIONS_WORKER_RUNTIME              = "python"
    FUNCTIONS_EXTENSION_VERSION           = "~4"
    ENABLE_ORYX_BUILD                     = "true"
    SCM_DO_BUILD_DURING_DEPLOYMENT        = "true"
    APPINSIGHTS_INSTRUMENTATIONKEY        = azurerm_application_insights.main.instrumentation_key
    APPLICATIONINSIGHTS_CONNECTION_STRING = azurerm_application_insights.main.connection_string
    AZURE_OPENAI_ENDPOINT                 = azurerm_cognitive_account.openai.endpoint
    AZURE_OPENAI_API_KEY                  = azurerm_cognitive_account.openai.primary_access_key
    AZURE_OPENAI_DEPLOYMENT               = var.openai_deployment_name

    # Oracle Configuration (secrets from existing Key Vault)
    ORACLE_HOST         = "@Microsoft.KeyVault(VaultName=${data.azurerm_key_vault.main.name};SecretName=oracle-host)"
    ORACLE_PORT         = var.oracle_port
    ORACLE_SERVICE_NAME = var.oracle_service_name
    ORACLE_USERNAME     = "@Microsoft.KeyVault(VaultName=${data.azurerm_key_vault.main.name};SecretName=oracle-username)"
    ORACLE_PASSWORD     = "@Microsoft.KeyVault(VaultName=${data.azurerm_key_vault.main.name};SecretName=oracle-password)"

    # MSSQL Configuration (secrets from existing Key Vault)
    MSSQL_HOST               = "@Microsoft.KeyVault(VaultName=${data.azurerm_key_vault.main.name};SecretName=mssql-host)"
    MSSQL_PORT               = var.mssql_port
    MSSQL_DATABASE           = var.mssql_database
    MSSQL_USERNAME           = "@Microsoft.KeyVault(VaultName=${data.azurerm_key_vault.main.name};SecretName=mssql-username)"
    MSSQL_PASSWORD           = "@Microsoft.KeyVault(VaultName=${data.azurerm_key_vault.main.name};SecretName=mssql-password)"
    MSSQL_TRUSTED_CONNECTION = tostring(var.mssql_trusted_connection)

    # PostgreSQL Configuration (secrets from existing Key Vault)
    POSTGRES_HOST     = "@Microsoft.KeyVault(VaultName=${data.azurerm_key_vault.main.name};SecretName=postgres-host)"
    POSTGRES_PORT     = var.postgres_port
    POSTGRES_DATABASE = var.postgres_database
    POSTGRES_USERNAME = "@Microsoft.KeyVault(VaultName=${data.azurerm_key_vault.main.name};SecretName=postgres-username)"
    POSTGRES_PASSWORD = "@Microsoft.KeyVault(VaultName=${data.azurerm_key_vault.main.name};SecretName=postgres-password)"

    # IBM DB2 Configuration (secrets from existing Key Vault)
    IBMDB2_HOST     = "@Microsoft.KeyVault(VaultName=${data.azurerm_key_vault.main.name};SecretName=ibmdb2-host)"
    IBMDB2_PORT     = var.ibmdb2_port
    IBMDB2_DATABASE = var.ibmdb2_database
    IBMDB2_USERNAME = "@Microsoft.KeyVault(VaultName=${data.azurerm_key_vault.main.name};SecretName=ibmdb2-username)"
    IBMDB2_PASSWORD = "@Microsoft.KeyVault(VaultName=${data.azurerm_key_vault.main.name};SecretName=ibmdb2-password)"
  }

  https_only = true

  tags = var.tags
}

# Key Vault access for Function App (grant access to existing Key Vault)
resource "azurerm_role_assignment" "function_kv_secrets" {
  scope                = data.azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_linux_function_app.main.identity[0].principal_id
}

# =============================================================================
# Chatbot (Optional)
# =============================================================================
resource "azurerm_static_web_app" "chatbot" {
  count = var.deploy_chatbot ? 1 : 0

  name                = local.chatbot_static_web_app_name
  resource_group_name = data.azurerm_resource_group.main.name
  location            = var.location
  sku_tier            = var.chatbot_sku
  sku_size            = var.chatbot_sku

  tags = var.tags
}

# Note: Static Web App app settings require GitHub Actions or Azure DevOps deployment
# The following local-exec provisioner sets the app settings after creation
resource "null_resource" "chatbot_settings" {
  count = var.deploy_chatbot ? 1 : 0

  triggers = {
    static_web_app_id = azurerm_static_web_app.chatbot[0].id
    mcp_server_url    = var.chatbot_mcp_server_url != "" ? var.chatbot_mcp_server_url : "https://${azurerm_linux_function_app.main.default_hostname}"
  }

  provisioner "local-exec" {
    command = <<-EOT
      az staticwebapp appsettings set \
        --name ${azurerm_static_web_app.chatbot[0].name} \
        --resource-group ${data.azurerm_resource_group.main.name} \
        --setting-names \
          MCP_SERVER_URL="${var.chatbot_mcp_server_url != "" ? var.chatbot_mcp_server_url : "https://${azurerm_linux_function_app.main.default_hostname}"}" \
          APPINSIGHTS_INSTRUMENTATIONKEY="${azurerm_application_insights.main.instrumentation_key}" \
          APPLICATIONINSIGHTS_CONNECTION_STRING="${azurerm_application_insights.main.connection_string}"
    EOT
  }

  depends_on = [azurerm_static_web_app.chatbot]
}
