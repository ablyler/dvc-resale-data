output "resource_group_name" {
  description = "Name of the resource group"
  value       = data.azurerm_resource_group.main.name
}

output "resource_group_location" {
  description = "Location of the resource group"
  value       = data.azurerm_resource_group.main.location
}

output "function_app_name" {
  description = "Name of the Function App"
  value       = azurerm_linux_function_app.main.name
}

output "function_app_url" {
  description = "URL of the Function App"
  value       = "https://${azurerm_linux_function_app.main.default_hostname}"
}

output "function_app_id" {
  description = "ID of the Function App"
  value       = azurerm_linux_function_app.main.id
}



output "data_storage_account_name" {
  description = "Name of the data storage account"
  value       = azurerm_storage_account.rofr_data.name
}

output "application_insights_name" {
  description = "Name of Application Insights"
  value       = azurerm_application_insights.main.name
}

output "application_insights_instrumentation_key" {
  description = "Application Insights instrumentation key"
  value       = azurerm_application_insights.main.instrumentation_key
  sensitive   = true
}

output "application_insights_connection_string" {
  description = "Application Insights connection string"
  value       = azurerm_application_insights.main.connection_string
  sensitive   = true
}

output "log_analytics_workspace_name" {
  description = "Name of the Log Analytics workspace"
  value       = azurerm_log_analytics_workspace.main.name
}

output "log_analytics_workspace_id" {
  description = "ID of the Log Analytics workspace"
  value       = azurerm_log_analytics_workspace.main.id
}

output "function_app_principal_id" {
  description = "Principal ID of the Function App managed identity"
  value       = azurerm_linux_function_app.main.identity[0].principal_id
}

output "scraper_configuration" {
  description = "Scraper configuration settings"
  value = {
    entries_table_name = var.entries_table_name
    threads_table_name = var.threads_table_name
    stats_table_name   = var.stats_table_name
    scraper_delay      = var.scraper_delay
    scraper_max_pages  = var.scraper_max_pages
    scraper_log_level  = var.scraper_log_level
    enable_compression = var.enable_compression
    enable_caching     = var.enable_caching
    disboards_url      = var.disboards_url
    function_timeout   = var.function_timeout
    batch_size         = var.batch_size
    request_timeout    = var.request_timeout
  }
}

output "deployment_summary" {
  description = "Summary of deployed resources"
  value = {
    function_app_url   = "https://${azurerm_linux_function_app.main.default_hostname}"
  }
}

output "service_plan_sku" {
  description = "SKU of the App Service Plan"
  value       = azurerm_service_plan.main.sku_name
}

output "service_plan_configuration" {
  description = "Service plan configuration details"
  value = {
    sku_name  = azurerm_service_plan.main.sku_name
    os_type   = azurerm_service_plan.main.os_type
    plan_type = var.function_app_sku == "Y1" ? "Consumption" : "Other"
    always_on = var.function_app_sku != "Y1"
  }
}
