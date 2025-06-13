variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the Azure resource group"
  type        = string
  default     = "dvc-resale-data"
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "Central US"
}

variable "domain_name" {
  description = "Custom domain name for the website"
  type        = string
  default     = "dvcresaledata.com"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "dvc-resale-data"
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Environment = "production"
    Project     = "dvc-resale-data"
    ManagedBy   = "terraform"
  }
}

variable "function_app_sku" {
  description = "SKU for the Function App service plan"
  type        = string
  default     = "Y1"
  validation {
    condition     = contains(["Y1", "EP1", "EP2", "EP3"], var.function_app_sku)
    error_message = "Function App SKU must be one of: Y1, EP1, EP2, EP3."
  }
}

variable "static_web_app_sku" {
  description = "SKU for the Azure Static Web App"
  type        = string
  default     = "Free"
  validation {
    condition     = contains(["Free", "Standard"], var.static_web_app_sku)
    error_message = "Static Web App SKU must be either Free or Standard."
  }
}

variable "log_retention_days" {
  description = "Number of days to retain logs"
  type        = number
  default     = 30
  validation {
    condition     = var.log_retention_days >= 30 && var.log_retention_days <= 730
    error_message = "Log retention days must be between 30 and 730."
  }
}

variable "enable_https_only" {
  description = "Enable HTTPS only for web resources"
  type        = bool
  default     = true
}

variable "enable_diagnostic_logs" {
  description = "Enable diagnostic logging for resources"
  type        = bool
  default     = true
}

# Scraper Configuration Variables
variable "scrapper_chunk_size" {
  description = "Number of items to process in each chunk"
  type        = number
  default     = 2
}

variable "scraper_delay" {
  description = "Delay between scraper requests in seconds"
  type        = string
  default     = "0.1"
}

variable "scraper_max_pages" {
  description = "Maximum pages to scrape per thread"
  type        = string
  default     = "1000"
}

variable "scraper_log_level" {
  description = "Logging level for the scraper"
  type        = string
  default     = "INFO"
  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR"], var.scraper_log_level)
    error_message = "Log level must be one of: DEBUG, INFO, WARNING, ERROR."
  }
}

variable "scraper_user_agent" {
  description = "User agent string for scraper requests"
  type        = string
  default     = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

variable "enable_compression" {
  description = "Enable response compression for Function App"
  type        = bool
  default     = true
}

variable "enable_caching" {
  description = "Enable caching for Function App responses"
  type        = bool
  default     = true
}

variable "disboards_url" {
  description = "Base URL for Disboards scraping"
  type        = string
  default     = "https://www.disboards.com/"
}

variable "function_timeout" {
  description = "Function App timeout in HH:MM:SS format"
  type        = string
  default     = "00:10:00"
}

variable "batch_size" {
  description = "Batch size for processing operations"
  type        = string
  default     = "25"
}

variable "request_timeout" {
  description = "HTTP request timeout in seconds"
  type        = string
  default     = "30"
}

variable "entries_table_name" {
  description = "Name of the ROFR entries table"
  type        = string
  default     = "entries"
}

variable "threads_table_name" {
  description = "Name of the threads tracking table"
  type        = string
  default     = "threads"
}

variable "stats_table_name" {
  description = "Name of the statistics table"
  type        = string
  default     = "stats"
}

variable "sessions_table_name" {
  description = "Name of the sessions tracking table"
  type        = string
  default     = "sessions"
}
