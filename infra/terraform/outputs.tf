# =============================================================================
# Outputs
# =============================================================================

output "function_app_name" {
  description = "Name of the Function App"
  value       = azurerm_linux_function_app.main.name
}

output "function_app_url" {
  description = "URL of the Function App"
  value       = "https://${azurerm_linux_function_app.main.default_hostname}"
}

output "openai_endpoint" {
  description = "Azure OpenAI endpoint"
  value       = azurerm_cognitive_account.openai.endpoint
}

output "key_vault_name" {
  description = "Name of the Key Vault"
  value       = azurerm_key_vault.main.name
}

output "storage_account_name" {
  description = "Name of the Storage Account"
  value       = azurerm_storage_account.main.name
}

output "app_insights_instrumentation_key" {
  description = "Application Insights instrumentation key"
  value       = azurerm_application_insights.main.instrumentation_key
  sensitive   = true
}

output "chatbot_static_web_app_name" {
  description = "Name of the Chatbot Static Web App (if deployed)"
  value       = var.deploy_chatbot ? azurerm_static_web_app.chatbot[0].name : ""
}

output "chatbot_static_web_app_url" {
  description = "Default hostname of the Chatbot Static Web App (if deployed)"
  value       = var.deploy_chatbot ? "https://${azurerm_static_web_app.chatbot[0].default_host_name}" : ""
}

# Note: To get the deployment token for the Static Web App, run:
# az staticwebapp secrets list --name <static-web-app-name> --query 'properties.apiKey' -o tsv
