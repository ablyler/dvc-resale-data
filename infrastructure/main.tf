# Provider configurations are in versions.tf

# Data sources
data "azurerm_client_config" "current" {}

data "azurerm_resource_group" "main" {
  name = var.resource_group_name
}

# Storage Account for ROFR data
resource "azurerm_storage_account" "rofr_data" {
  name                     = "dvcresaledatastorage3157"
  resource_group_name      = data.azurerm_resource_group.main.name
  location                 = data.azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"

  tags = local.common_tags
}

# Storage Tables
resource "azurerm_storage_table" "rofr_entries" {
  name                 = var.entries_table_name
  storage_account_name = azurerm_storage_account.rofr_data.name
}

resource "azurerm_storage_table" "threads" {
  name                 = var.threads_table_name
  storage_account_name = azurerm_storage_account.rofr_data.name
}

resource "azurerm_storage_table" "statistics" {
  name                 = var.stats_table_name
  storage_account_name = azurerm_storage_account.rofr_data.name
}

resource "azurerm_storage_table" "sessions" {
  name                 = var.sessions_table_name
  storage_account_name = azurerm_storage_account.rofr_data.name
}

# Azure Static Web Apps
resource "azurerm_static_web_app" "main" {
  name                = "dvcresaledata"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = data.azurerm_resource_group.main.location
  sku_tier            = "Free"
  sku_size            = "Free"

  # Optional API configuration to link with Function App
  # This will be configured separately in GitHub Actions

  tags = local.common_tags
}

# Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "main" {
  name                = "dvc-resale-data-logs"
  location            = data.azurerm_resource_group.main.location
  resource_group_name = data.azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = var.log_retention_days

  tags = local.common_tags
}

# Application Insights
resource "azurerm_application_insights" "main" {
  name                = "dvc-resale-data-func"
  location            = data.azurerm_resource_group.main.location
  resource_group_name = data.azurerm_resource_group.main.name
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"

  tags = local.common_tags
}



# App Service Plan for Functions
resource "azurerm_service_plan" "main" {
  name                = "dvc-resale-data-plan"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = data.azurerm_resource_group.main.location
  os_type             = "Linux"
  sku_name            = var.function_app_sku

  tags = local.common_tags
}

# Function App
resource "azurerm_linux_function_app" "main" {
  name                = "dvc-resale-data-func"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = data.azurerm_resource_group.main.location

  storage_account_name       = azurerm_storage_account.rofr_data.name
  storage_account_access_key = azurerm_storage_account.rofr_data.primary_access_key
  service_plan_id            = azurerm_service_plan.main.id

  identity {
    type = "SystemAssigned"
  }

  site_config {
    always_on = var.function_app_sku != "Y1"

    application_stack {
      python_version = "3.12"
    }

    cors {
      allowed_origins     = local.cors_origins
      support_credentials = false
    }

    ftps_state              = "Disabled"
    http2_enabled           = true
    minimum_tls_version     = "1.2"
    scm_minimum_tls_version = "1.2"
  }

  app_settings = local.function_app_settings

  https_only = var.enable_https_only

  tags = local.common_tags
}

# DNS Zone
resource "azurerm_dns_zone" "main" {
  name                = var.domain_name
  resource_group_name = data.azurerm_resource_group.main.name

  tags = local.common_tags
}

# Static Web Apps Custom Domains
resource "azurerm_static_web_app_custom_domain" "apex" {
  static_web_app_id = azurerm_static_web_app.main.id
  domain_name       = var.domain_name
  validation_type   = "dns-txt-token"
}

resource "azurerm_static_web_app_custom_domain" "www" {
  static_web_app_id = azurerm_static_web_app.main.id
  domain_name       = "www.${var.domain_name}"
  validation_type   = "dns-txt-token"
}

# DNS Records for domain validation
resource "azurerm_dns_txt_record" "apex_validation" {
  name                = "asverify"
  zone_name           = azurerm_dns_zone.main.name
  resource_group_name = data.azurerm_resource_group.main.name
  ttl                 = local.dns_records.ttl_short

  record {
    value = azurerm_static_web_app_custom_domain.apex.validation_token
  }

  tags = local.common_tags
}

resource "azurerm_dns_txt_record" "www_validation" {
  name                = "asverify.www"
  zone_name           = azurerm_dns_zone.main.name
  resource_group_name = data.azurerm_resource_group.main.name
  ttl                 = local.dns_records.ttl_short

  record {
    value = azurerm_static_web_app_custom_domain.www.validation_token
  }

  tags = local.common_tags
}

# DNS A record for apex domain (points to Static Web Apps)
data "azurerm_static_web_app" "main_data" {
  name                = azurerm_static_web_app.main.name
  resource_group_name = data.azurerm_resource_group.main.name
  depends_on          = [azurerm_static_web_app_custom_domain.apex]
}

resource "azurerm_dns_a_record" "apex" {
  name                = "@"
  zone_name           = azurerm_dns_zone.main.name
  resource_group_name = data.azurerm_resource_group.main.name
  ttl                 = local.dns_records.ttl_medium
  records             = ["185.199.108.153", "185.199.109.153", "185.199.110.153", "185.199.111.153"]

  depends_on = [azurerm_static_web_app_custom_domain.apex]
  tags       = local.common_tags
}

# DNS CNAME record for www subdomain
resource "azurerm_dns_cname_record" "www" {
  name                = "www"
  zone_name           = azurerm_dns_zone.main.name
  resource_group_name = data.azurerm_resource_group.main.name
  ttl                 = local.dns_records.ttl_medium
  record              = azurerm_static_web_app.main.default_host_name

  depends_on = [azurerm_static_web_app_custom_domain.www]
  tags       = local.common_tags
}

# Function App API domain
resource "azurerm_dns_cname_record" "api" {
  name                = "api"
  zone_name           = azurerm_dns_zone.main.name
  resource_group_name = data.azurerm_resource_group.main.name
  ttl                 = local.dns_records.ttl_medium
  record              = "${azurerm_linux_function_app.main.name}.azurewebsites.net"
}

# Role assignments for Function App managed identity
resource "azurerm_role_assignment" "function_storage_contributor" {
  scope                = azurerm_storage_account.rofr_data.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = azurerm_linux_function_app.main.identity[0].principal_id
}



# Diagnostic settings for Function App
resource "azurerm_monitor_diagnostic_setting" "function_app" {
  count                      = var.enable_diagnostic_logs ? 1 : 0
  name                       = "function-app-diagnostics"
  target_resource_id         = azurerm_linux_function_app.main.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  enabled_log {
    category = "FunctionAppLogs"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}

# Note: Front Door endpoints do not support diagnostic settings
# Diagnostic logs are available at the profile level instead

# Action Group for alerts
resource "azurerm_monitor_action_group" "main" {
  name                = "dvc-resale-data-alerts"
  resource_group_name = data.azurerm_resource_group.main.name
  short_name          = "dvcalerts"

  tags = local.common_tags
}

# Function App availability alert
resource "azurerm_monitor_metric_alert" "function_app_availability" {
  name                = "function-app-availability"
  resource_group_name = data.azurerm_resource_group.main.name
  scopes              = [azurerm_linux_function_app.main.id]
  description         = "Function App availability alert"
  frequency           = "PT1M"
  window_size         = "PT5M"
  severity            = 2

  criteria {
    metric_namespace = "Microsoft.Web/sites"
    metric_name      = "Http5xx"
    aggregation      = "Count"
    operator         = "GreaterThan"
    threshold        = local.alert_thresholds.function_error_rate
  }

  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }

  tags = local.common_tags
}

# Static Web Apps availability alert
resource "azurerm_monitor_metric_alert" "static_web_apps_availability" {
  name                = "static-web-apps-availability"
  resource_group_name = data.azurerm_resource_group.main.name
  scopes              = [azurerm_static_web_app.main.id]
  description         = "Static Web Apps availability alert"
  frequency           = "PT5M"
  window_size         = "PT15M"
  severity            = 1

  criteria {
    metric_namespace = "Microsoft.Web/staticSites"
    metric_name      = "SiteErrors"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 10
  }

  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }

  tags = local.common_tags
}
