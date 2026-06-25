# =============================================================================
# Azure Infrastructure for Data Agent - Terraform Configuration
# =============================================================================
# Deploys the Data Agent Azure Function with supporting resources.
#
# =============================================================================
# DISCLAIMER
# =============================================================================
# This code was generated with AI assistance (AI-generated code).
# It is provided "AS-IS" under the MIT License without warranty of any kind.
#
# Users should:
# - Review and test thoroughly before production use
# - Validate security implications for their specific use case
# - Ensure compliance with their organization's policies
#
# LICENSE: MIT License - Copyright (c) 2026
# See LICENSE file in project root for full license text.
# =============================================================================
#
# Deploy with:
#   terraform init
#   terraform plan -var-file="terraform.tfvars"
#   terraform apply -var-file="terraform.tfvars"
# =============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }

  # Uncomment to use Azure Storage backend for state
  # backend "azurerm" {
  #   resource_group_name  = "terraform-state-rg"
  #   storage_account_name = "tfstate12345"
  #   container_name       = "tfstate"
  #   key                  = "dataagent.tfstate"
  # }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = true
    }
  }
}

provider "random" {}
