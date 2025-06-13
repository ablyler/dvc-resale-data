# Local values for computed configurations
locals {
  # Common naming conventions
  resource_prefix = "${var.project_name}-${var.environment}"

  # Static Web App naming
  static_web_app_name = "dvcresaledata"

  # Common tags to be applied to all resources
  common_tags = merge(var.tags, {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    DeployedBy  = "github-actions"
    Domain      = var.domain_name
  })

  # Function App settings
  function_app_settings = {
    # Azure Functions Core Settings
    "FUNCTIONS_EXTENSION_VERSION"           = "~4"
    "FUNCTIONS_WORKER_RUNTIME"              = "python"
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = azurerm_application_insights.main.connection_string
    "AZURE_STORAGE_CONNECTION_STRING"       = azurerm_storage_account.rofr_data.primary_connection_string
    "SCM_DO_BUILD_DURING_DEPLOYMENT"        = "true"
    "ENABLE_ORYX_BUILD"                     = "true"
    "ENVIRONMENT"                           = var.environment
    "AzureWebJobsDisableHomepage"           = "true"

    # ROFR Scraper Configuration
    "SCRAPER_DELAY"      = var.scraper_delay
    "SCRAPER_MAX_PAGES"  = var.scraper_max_pages
    "SCRAPER_LOG_LEVEL"  = var.scraper_log_level
    "SCRAPER_USER_AGENT" = var.scraper_user_agent
    "SCRAPER_CHUNK_SIZE" = var.scrapper_chunk_size

    # Performance and Feature Toggles
    "ENABLE_COMPRESSION" = tostring(var.enable_compression)
    "ENABLE_CACHING"     = tostring(var.enable_caching)

    # Scraper URLs and Endpoints
    "DISBOARDS_URL" = var.disboards_url
    "BASE_URL"      = var.disboards_url

    # Timeout and Performance Settings
    "FUNCTION_TIMEOUT" = var.function_timeout
    "BATCH_SIZE"       = var.batch_size
    "REQUEST_TIMEOUT"  = var.request_timeout

    # Table Storage Configuration
    "ENTRIES_TABLE_NAME"  = var.entries_table_name
    "THREADS_TABLE_NAME"  = var.threads_table_name
    "SESSIONS_TABLE_NAME" = var.sessions_table_name
    "STATS_TABLE_NAME"    = var.stats_table_name
  }

  # CORS origins for Function App
  cors_origins = [
    "https://${var.domain_name}",
    "https://www.${var.domain_name}",
    "https://portal.azure.com",
    "https://functions.azure.com",
    "https://functions-staging.azure.com",
    "https://functions-next.azure.com"
  ]

  # CDN compression content types
  cdn_compression_types = [
    "application/eot",
    "application/font",
    "application/font-sfnt",
    "application/javascript",
    "application/json",
    "application/opentype",
    "application/otf",
    "application/pkcs7-mime",
    "application/truetype",
    "application/ttf",
    "application/vnd.ms-fontobject",
    "application/xhtml+xml",
    "application/xml",
    "application/xml+rss",
    "application/x-font-opentype",
    "application/x-font-truetype",
    "application/x-font-ttf",
    "application/x-httpd-cgi",
    "application/x-javascript",
    "application/x-mpegurl",
    "application/x-opentype",
    "application/x-otf",
    "application/x-perl",
    "application/x-ttf",
    "font/eot",
    "font/ttf",
    "font/otf",
    "font/opentype",
    "image/svg+xml",
    "text/css",
    "text/csv",
    "text/html",
    "text/javascript",
    "text/js",
    "text/plain",
    "text/richtext",
    "text/tab-separated-values",
    "text/xml",
    "text/x-script",
    "text/x-component",
    "text/x-java-source"
  ]

  # Security headers for CDN
  security_headers = {
    "X-Content-Type-Options"    = "nosniff"
    "X-Frame-Options"           = "DENY"
    "X-XSS-Protection"          = "1; mode=block"
    "Referrer-Policy"           = "strict-origin-when-cross-origin"
    "Permissions-Policy"        = "geolocation=(), microphone=(), camera=()"
    "Strict-Transport-Security" = "max-age=31536000; includeSubDomains"
  }

  # DNS record configurations
  dns_records = {
    ttl_short  = 300   # 5 minutes
    ttl_medium = 3600  # 1 hour
    ttl_long   = 86400 # 24 hours
  }

  # Monitoring and diagnostics
  diagnostic_logs = {
    function_app = [
      {
        category = "FunctionAppLogs"
        enabled  = true
      }
    ]
    cdn_endpoint = [
      {
        category = "CoreAnalytics"
        enabled  = true
      }
    ]
  }

  # Alert thresholds
  alert_thresholds = {
    function_error_rate    = 5
    function_response_time = 5000
    cdn_error_rate         = 5
    storage_availability   = 99.9
  }
}

# Get current subscription for role assignments
data "azurerm_subscription" "current" {}
