# =============================================================================
# Variables for Data Agent Infrastructure
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
# Oracle Database Settings
# -----------------------------------------------------------------------------
variable "oracle_host" {
  description = "Oracle database host"
  type        = string
  default     = ""
  sensitive   = true
}

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

variable "oracle_username" {
  description = "Oracle username"
  type        = string
  default     = ""
  sensitive   = true
}

variable "oracle_password" {
  description = "Oracle password"
  type        = string
  default     = ""
  sensitive   = true
}

# -----------------------------------------------------------------------------
# Microsoft SQL Server Settings
# -----------------------------------------------------------------------------
variable "mssql_host" {
  description = "SQL Server database host"
  type        = string
  default     = ""
  sensitive   = true
}

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

variable "mssql_username" {
  description = "SQL Server username"
  type        = string
  default     = ""
  sensitive   = true
}

variable "mssql_password" {
  description = "SQL Server password"
  type        = string
  default     = ""
  sensitive   = true
}

variable "mssql_trusted_connection" {
  description = "Use Windows/Integrated authentication for SQL Server"
  type        = bool
  default     = false
}

# -----------------------------------------------------------------------------
# PostgreSQL Settings
# -----------------------------------------------------------------------------
variable "postgres_host" {
  description = "PostgreSQL database host"
  type        = string
  default     = ""
  sensitive   = true
}

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

variable "postgres_username" {
  description = "PostgreSQL username"
  type        = string
  default     = ""
  sensitive   = true
}

variable "postgres_password" {
  description = "PostgreSQL password"
  type        = string
  default     = ""
  sensitive   = true
}

# -----------------------------------------------------------------------------
# IBM DB2 LUW Settings
# -----------------------------------------------------------------------------
variable "ibmdb2_host" {
  description = "IBM DB2 database host"
  type        = string
  default     = ""
  sensitive   = true
}

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

variable "ibmdb2_username" {
  description = "IBM DB2 username"
  type        = string
  default     = ""
  sensitive   = true
}

variable "ibmdb2_password" {
  description = "IBM DB2 password"
  type        = string
  default     = ""
  sensitive   = true
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
