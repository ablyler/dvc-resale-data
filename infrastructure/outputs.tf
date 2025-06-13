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

output "static_web_app_name" {
  description = "Name of the Static Web App"
  value       = azurerm_static_web_app.main.name
}

output "static_web_app_url" {
  description = "Default URL of the Static Web App"
  value       = "https://${azurerm_static_web_app.main.default_host_name}"
}

output "static_web_app_id" {
  description = "ID of the Static Web App"
  value       = azurerm_static_web_app.main.id
}

output "data_storage_account_name" {
  description = "Name of the data storage account"
  value       = azurerm_storage_account.rofr_data.name
}

output "static_web_app_api_key" {
  description = "API key for Static Web App deployment"
  value       = azurerm_static_web_app.main.api_key
  sensitive   = true
}

output "static_web_app_default_host_name" {
  description = "Default host name of the Static Web App"
  value       = azurerm_static_web_app.main.default_host_name
}

output "custom_domain_url" {
  description = "Custom domain URL"
  value       = "https://${var.domain_name}"
}

output "www_domain_url" {
  description = "WWW domain URL"
  value       = "https://www.${var.domain_name}"
}

output "api_domain_url" {
  description = "API domain URL"
  value       = "https://api.${var.domain_name}"
}

output "dns_zone_name" {
  description = "Name of the DNS zone"
  value       = azurerm_dns_zone.main.name
}

output "dns_zone_name_servers" {
  description = "Name servers for the DNS zone"
  value       = azurerm_dns_zone.main.name_servers
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
    custom_domain_url  = "https://${var.domain_name}"
    www_domain_url     = "https://www.${var.domain_name}"
    api_url            = "https://api.${var.domain_name}"
    function_app_url   = "https://${azurerm_linux_function_app.main.default_hostname}"
    static_web_app_url = "https://${azurerm_static_web_app.main.default_host_name}"
    dns_name_servers   = azurerm_dns_zone.main.name_servers
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

output "custom_domain_status" {
  description = "Status of custom domain configuration"
  sensitive   = true
  value = {
    apex_domain = {
      domain           = var.domain_name
      validation_type  = azurerm_static_web_app_custom_domain.apex.validation_type
      validation_token = azurerm_static_web_app_custom_domain.apex.validation_token
    }
    www_domain = {
      domain           = "www.${var.domain_name}"
      validation_type  = azurerm_static_web_app_custom_domain.www.validation_type
      validation_token = azurerm_static_web_app_custom_domain.www.validation_token
    }
    dns_validation_records = {
      apex_txt_record = "asverify.${var.domain_name}"
      www_txt_record  = "asverify.www.${var.domain_name}"
    }
  }
}

output "domain_verification_status" {
  description = "Domain verification and SSL certificate status"
  value       = <<-EOT
    🌐 Custom Domain Configuration Status:

    Apex Domain: ${var.domain_name}
    - Status: Configured with Terraform
    - DNS Validation: TXT record 'asverify' created automatically
    - A Record: Points to Static Web Apps IP addresses

    WWW Domain: www.${var.domain_name}
    - Status: Configured with Terraform
    - DNS Validation: TXT record 'asverify.www' created automatically
    - CNAME Record: Points to ${azurerm_static_web_app.main.default_host_name}

    🔒 SSL Certificate:
    - SSL certificates will be automatically provisioned by Azure
    - This process may take up to 24 hours after DNS propagation

    ✅ Verification Steps:
    1. Wait for DNS propagation (5-10 minutes)
    2. Check domain status: az staticwebapp show --name dvcresaledata --resource-group dvc-resale-data
    3. Test endpoints:
       - curl -I https://${var.domain_name}
       - curl -I https://www.${var.domain_name}
  EOT
}

output "validation_tokens" {
  description = "Domain validation tokens for troubleshooting"
  value = {
    apex_validation_token = azurerm_static_web_app_custom_domain.apex.validation_token
    www_validation_token  = azurerm_static_web_app_custom_domain.www.validation_token
  }
  sensitive = true
}

output "dns_records_created" {
  description = "DNS records created for custom domains"
  sensitive   = true
  value = {
    apex_txt_record = {
      name  = azurerm_dns_txt_record.apex_validation.name
      value = tolist(azurerm_dns_txt_record.apex_validation.record)[0].value
      ttl   = azurerm_dns_txt_record.apex_validation.ttl
    }
    www_txt_record = {
      name  = azurerm_dns_txt_record.www_validation.name
      value = tolist(azurerm_dns_txt_record.www_validation.record)[0].value
      ttl   = azurerm_dns_txt_record.www_validation.ttl
    }
    apex_a_record = {
      name    = azurerm_dns_a_record.apex.name
      records = azurerm_dns_a_record.apex.records
      ttl     = azurerm_dns_a_record.apex.ttl
    }
    www_cname_record = {
      name   = azurerm_dns_cname_record.www.name
      record = azurerm_dns_cname_record.www.record
      ttl    = azurerm_dns_cname_record.www.ttl
    }
  }
}
