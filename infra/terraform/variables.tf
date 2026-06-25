# =============================================================================
# Variables for Data Agent Infrastructure
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
# The database connection variables below are for configuration only.
# Sensitive credentials (hosts, usernames, passwords) must be stored
# in the existing Key Vault as secrets.
# =============================================================================

# -----------------------------------------------------------------------------
# General Settings
# -----------------------------------------------------------------------------
variable "base_name" {
  description = "Base name for all resources"
  type        = string
  default     = "dataagent"
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "eastus"
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Environment = "Development"
    Project     = "DataAgent"
    ManagedBy   = "Terraform"
  }
}

# -----------------------------------------------------------------------------
# Existing Key Vault (Required)
# -----------------------------------------------------------------------------
variable "key_vault_name" {
  description = "Name of the existing Key Vault containing database secrets"
  type        = string
}

variable "key_vault_resource_group" {
  description = "Resource group of the existing Key Vault (defaults to resource_group_name if not specified)"
  type        = string
  default     = ""
}

# -----------------------------------------------------------------------------
# Azure OpenAI Settings
# -----------------------------------------------------------------------------
variable "openai_deployment_name" {
  description = "Azure OpenAI deployment name"
  type        = string
  default     = "gpt-4o"
}

variable "openai_model_name" {
  description = "Azure OpenAI model name"
  type        = string
  default     = "gpt-4o"
}

variable "openai_model_version" {
  description = "Azure OpenAI model version"
  type        = string
  default     = "2024-05-13"
}

variable "openai_capacity" {
  description = "Azure OpenAI deployment capacity (tokens per minute in thousands)"
  type        = number
  default     = 10
}

# -----------------------------------------------------------------------------
# Oracle Database Connection Settings
# -----------------------------------------------------------------------------
variable "oracle_port" {
  description = "Oracle database port"
  type        = string
  default     = "1521"
}

variable "oracle_service_name" {
  description = "Oracle service name"
  type        = string
  default     = ""
}

# -----------------------------------------------------------------------------
# Microsoft SQL Server Connection Settings
# -----------------------------------------------------------------------------
variable "mssql_port" {
  description = "SQL Server database port"
  type        = string
  default     = "1433"
}

variable "mssql_database" {
  description = "SQL Server database name"
  type        = string
  default     = ""
}

variable "mssql_trusted_connection" {
  description = "Use Windows/Integrated authentication for SQL Server"
  type        = bool
  default     = false
}

# -----------------------------------------------------------------------------
# PostgreSQL Connection Settings
# -----------------------------------------------------------------------------
variable "postgres_port" {
  description = "PostgreSQL database port"
  type        = string
  default     = "5432"
}

variable "postgres_database" {
  description = "PostgreSQL database name"
  type        = string
  default     = ""
}

# -----------------------------------------------------------------------------
# IBM DB2 LUW Connection Settings
# -----------------------------------------------------------------------------
variable "ibmdb2_port" {
  description = "IBM DB2 database port"
  type        = string
  default     = "50000"
}

variable "ibmdb2_database" {
  description = "IBM DB2 database name"
  type        = string
  default     = ""
}

# -----------------------------------------------------------------------------
# Chatbot Settings
# -----------------------------------------------------------------------------
variable "deploy_chatbot" {
  description = "Deploy the chatbot interface"
  type        = bool
  default     = false
}

variable "chatbot_mcp_server_url" {
  description = "MCP Server URL for the chatbot"
  type        = string
  default     = ""
}

variable "chatbot_sku" {
  description = "Chatbot Static Web App SKU"
  type        = string
  default     = "Free"

  validation {
    condition     = contains(["Free", "Standard"], var.chatbot_sku)
    error_message = "chatbot_sku must be either 'Free' or 'Standard'."
  }
}
