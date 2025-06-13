# ROFR Scraper Infrastructure

This directory contains the OpenTofu infrastructure-as-code (IaC) configuration for the DVC Resale Data platform, including Azure Functions, storage, Azure Front Door, DNS, and monitoring resources.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     dvcresaledata.com                          │
│                  (Automated SSL + Domain)                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌──────────────┐│
│  │ Static Web Apps │    │ Azure Functions │    │  DNS Zone    ││
│  │(Hosting+CDN+SSL)│    │   (API + Bot)   │    │ (Domain Mgmt)││
│  └─────────────────┘    └─────────────────┘    └──────────────┘│
│           │                       │                             │
│           ▼                       ▼                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌──────────────┐│
│  │  React WebApp   │    │   ROFR Scraper  │    │  Data Storage││
│  │   (Frontend)    │◄───┤   (Scheduled)   │◄───┤  (Table DB)  ││
│  └─────────────────┘    └─────────────────┘    └──────────────┘│
│                                   │                             │
│                          ┌─────────────────┐                   │
│                          │  App Insights   │                   │
│                          │  (Monitoring)   │                   │
│                          └─────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 File Structure

```
infrastructure/
├── main.tf                    # Primary resource definitions
├── variables.tf               # Input variable declarations
├── outputs.tf                 # Output value definitions
├── locals.tf                  # Local values and computed configurations
├── versions.tf                # Provider version constraints
├── .gitignore                 # Git ignore patterns for Terraform
├── init.sh                    # Infrastructure initialization script
├── terraform.tfvars.example   # Example configuration values
└── README.md                  # This file
```

## 🚀 Quick Start

### Prerequisites

1. **Azure CLI** - [Install Guide](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
2. **OpenTofu** - [Install Guide](https://opentofu.org/docs/intro/install/)
3. **Azure Subscription** with Contributor permissions
4. **Domain ownership** for `dvcresaledata.com`
5. **GitHub Repository** with admin access for OIDC setup

### 1. Initialize Infrastructure

```bash
# Make the initialization script executable
chmod +x init.sh

# Run the initialization script
./init.sh
```

This script will:
- ✅ Create Azure resource group
- ✅ Set up OpenTofu backend storage
- ✅ Create service principal with OIDC for GitHub Actions
- ✅ Configure federated credentials for secure authentication
- ✅ Generate GitHub secrets documentation

### 2. Configure Variables (Optional)

```bash
# Copy the example variables file
cp terraform.tfvars.example terraform.tfvars

# Edit with your specific configuration
vim terraform.tfvars
```

### 3. Deploy Infrastructure

```bash
# Initialize OpenTofu (done automatically by init.sh)
tofu init

# Plan the deployment
tofu plan

# Apply the configuration
tofu apply
```

## 🏭 Infrastructure Components

### Core Resources

| Resource | Name | Purpose |
|----------|------|---------|
| **Resource Group** | `dvc-resale-data` | Container for all resources |
| **Function App** | `dvc-resale-data-func` | Azure Functions runtime |
| **App Service Plan** | `dvc-resale-data-plan` | Compute plan for functions |
| **Storage (Data)** | `dvcresaledatastorage3157` | ROFR data storage (existing) |
| **Static Web App** | `dvcresaledata` | Website hosting with built-in CDN |

### Website & CDN

| Resource | Name | Purpose |
|----------|------|---------|
| **Static Web Apps** | `dvcresaledata` | Integrated hosting, CDN, and SSL |
| **DNS Zone** | `dvcresaledata.com` | Domain name management |

### Monitoring & Security

| Resource | Name | Purpose |
|----------|------|---------|
| **Application Insights** | `dvc-resale-data-func` | Application monitoring |
| **Log Analytics** | `dvc-resale-data-logs` | Centralized logging |

### DNS Records Created

| Record Type | Name | Target | Purpose |
|-------------|------|--------|---------|
| **A** | `@` | Static Web Apps IPs | Apex domain (dvcresaledata.com) |
| **CNAME** | `www` | Static Web Apps default host | WWW subdomain |
| **CNAME** | `api` | Function App | API endpoint |
| **TXT** | `asverify` | Validation token | Apex domain verification |
| **TXT** | `asverify.www` | Validation token | WWW domain verification |

### Custom Domain Configuration

Custom domains are **automatically configured** using Terraform:

| Domain | Type | SSL Certificate | Status |
|--------|------|----------------|--------|
| `dvcresaledata.com` | Apex | Auto-provisioned | ✅ Automated |
| `www.dvcresaledata.com` | Subdomain | Auto-provisioned | ✅ Automated |
| `api.dvcresaledata.com` | API | Auto-provisioned | ✅ Automated |

**Key Features:**
- 🔒 **Automatic SSL certificates** - Azure manages certificate lifecycle
- 🌐 **DNS validation** - TXT records automatically created and managed
- ⚡ **Zero manual steps** - Complete automation through Terraform
- 🔄 **Auto-renewal** - SSL certificates renewed automatically
- 📊 **Monitoring included** - Domain status tracked in outputs

**Verification:**
```bash
# Run automated verification script
./infrastructure/verify-custom-domains.sh

# Manual verification commands
curl -I https://dvcresaledata.com
curl -I https://www.dvcresaledata.com
curl -I https://api.dvcresaledata.com/api/health
```

## 🚀 Flex Consumption Plan (FC1)

The Function App now uses the **Flex Consumption Plan (FC1)** for enhanced performance and cost optimization:

### Key Benefits

| Feature | Flex Consumption (FC1) | Traditional Consumption (Y1) |
|---------|------------------------|-------------------------------|
| **Cold Start** | Faster startup times | Standard startup |
| **Scaling** | 0-100 instances | 0-200 instances |
| **Memory** | 2GB or 4GB instances | 1.5GB instances |
| **Cost Model** | Pay per execution + idle time | Pay per execution only |
| **Performance** | Optimized runtime | Standard runtime |
| **Configuration** | Requires function_app_config | Simple configuration |
| **Monitoring** | Enhanced metrics | Standard metrics |

### Configuration

```hcl
# Flex Consumption Plan settings
function_app_sku = "FC1"
max_elastic_worker_count = 100
flex_consumption_instance_memory = 2048
deployment_storage_name = ""  # Uses main storage account if empty
```

### Required Configuration Block

Flex Consumption plans require a `function_app_config` block in the Function App resource:

```hcl
dynamic "function_app_config" {
  for_each = var.function_app_sku == "FC1" ? [1] : []
  content {
    deployment_storage_account_name       = data.azurerm_storage_account.rofr_data.name
    deployment_storage_account_access_key = data.azurerm_storage_account.rofr_data.primary_access_key
    instance_memory_mb                    = var.flex_consumption_instance_memory
    runtime {
      name    = "python"
      version = "3.11"
    }
  }
}
```

### Migration

To migrate from Consumption Plan to Flex Consumption Plan:

```bash
# Run the migration script
./infrastructure/migrate-to-flex-consumption.sh

# Or manually apply with Terraform
cd infrastructure
terraform plan
terraform apply
```

### Monitoring

The Flex Consumption Plan provides additional metrics in Application Insights:
- Instance count over time
- Cold start frequency and duration
- Function execution duration
- Memory usage patterns (2GB or 4GB)
- Enhanced scaling metrics
- Deployment storage performance

### Environment Variables

FC1 plans include additional environment variables:
- `WEBSITE_INSTANCE_MEMORY_MB`: Instance memory allocation
- `FUNCTIONS_WORKER_PROCESS_COUNT`: Worker process configuration
- `FUNCTIONS_WORKER_CONCURRENCY`: Concurrency settings
- `WEBSITE_MAX_DYNAMIC_APPLICATION_SCALE_OUT`: Maximum scaling limit

## ⚙️ Configuration Variables

### Required Variables

```hcl
# Azure Configuration
subscription_id     = "your-azure-subscription-id"
resource_group_name = "dvc-resale-data"
domain_name        = "dvcresaledata.com"
```

### Scraper Configuration

```hcl
# Performance Tuning
scraper_delay     = "1.0"   # Seconds between requests
scraper_max_pages = "50"    # Max pages per thread
scraper_log_level = "INFO"  # DEBUG, INFO, WARNING, ERROR

# Feature Toggles
enable_compression = true   # HTTP response compression
enable_caching     = true   # Response caching

# Timeout Settings
function_timeout = "00:10:00"  # Function execution limit
batch_size       = "25"        # Processing batch size
request_timeout  = "30"        # HTTP request timeout
```

### Advanced Configuration

See `terraform.tfvars.example` for all available variables and performance tuning guidelines.

## 🔑 Environment Variables

The Function App is automatically configured with these environment variables:

### Azure Functions Core
- `FUNCTIONS_EXTENSION_VERSION`: `~4`
- `FUNCTIONS_WORKER_RUNTIME`: `python`
- `APPLICATIONINSIGHTS_CONNECTION_STRING`: Auto-configured
- `AZURE_STORAGE_CONNECTION_STRING`: Auto-configured

### ROFR Scraper Settings
- `ROFR_TABLE_NAME`: `rofrentries`
- `SCRAPER_DELAY`: Configurable delay between requests
- `SCRAPER_MAX_PAGES`: Maximum pages to scrape
- `SCRAPER_LOG_LEVEL`: Logging verbosity
- `SCRAPER_USER_AGENT`: HTTP User-Agent string

### Performance Settings
- `ENABLE_COMPRESSION`: Response compression toggle
- `ENABLE_CACHING`: Response caching toggle
- `BATCH_SIZE`: Processing batch size
- `REQUEST_TIMEOUT`: HTTP request timeout

### Storage Tables
- `THREADS_TABLE_NAME`: `threads`
- `STATISTICS_TABLE_NAME`: `statistics`

## 🌐 URL Structure

After deployment, these URLs will be available:

| URL | Purpose |
|-----|---------|
| `https://dvcresaledata.com` | Main website (Static Web Apps) |
| `https://www.dvcresaledata.com` | WWW redirect to main |
| `https://api.dvcresaledata.com` | API endpoints (Function App) |
| `https://dvc-resale-data-func.azurewebsites.net` | Direct Function App access |
| `https://dvcresaledata.azurestaticapps.net` | Default Static Web Apps URL |

## 📊 Monitoring & Logging

### Application Insights

Access application telemetry:

```bash
# View Application Insights in Azure Portal
az monitor app-insights component show \
  --app "dvc-resale-data-func" \
  --resource-group "dvc-resale-data"
```

### Log Analytics Queries

```kusto
// Recent Function App logs
FunctionAppLogs
| where TimeGenerated > ago(1h)
| order by TimeGenerated desc

// Error tracking
FunctionAppLogs
| where Level == "Error"
| summarize count() by bin(TimeGenerated, 1h)

// Performance monitoring
requests
| where timestamp > ago(24h)
| summarize avg(duration) by bin(timestamp, 1h)
```

### Health Endpoints

```bash
# Function App health check
curl https://dvc-resale-data-func.azurewebsites.net/api/health

# Website availability
curl -I https://dvcresaledata.com

# API endpoints
curl https://api.dvcresaledata.com/api/rofr-stats
```

## 🔧 Management Commands

### OpenTofu Operations

```bash
# Format OpenTofu files
tofu fmt

# Validate configuration
tofu validate

# Plan changes
tofu plan

# Apply changes
tofu apply

# Show current state
tofu show

# List resources
tofu state list

# Import existing resource
tofu import azurerm_resource_group.main /subscriptions/{id}/resourceGroups/{name}
```

### OIDC Authentication

```bash
# Verify OIDC setup
./verify-oidc-setup.sh

# Check federated credentials
az ad app federated-credential list --id $AZURE_CLIENT_ID

# Test authentication (in GitHub Actions)
az account show --output table
```

### Static Web Apps Operations

```bash
# Check Static Web Apps status
az staticwebapp show --name dvcresaledata --resource-group dvc-resale-data

# List environments
az staticwebapp environment list --name dvcresaledata --resource-group dvc-resale-data

# List custom domains
az staticwebapp hostname list --name dvcresaledata --resource-group dvc-resale-data

# Get API key for deployments
az staticwebapp secrets list --name dvcresaledata --resource-group dvc-resale-data

# Show build details
az staticwebapp show --name dvcresaledata --resource-group dvc-resale-data --query "buildProperties"
```

### Azure CLI Operations

```bash
# Check Function App status
az functionapp show \
  --name "dvc-resale-data-func" \
  --resource-group "dvc-resale-data"

# View Function App logs
az functionapp log tail \
  --name "dvc-resale-data-func" \
  --resource-group "dvc-resale-data"

# Check Static Web Apps status
az staticwebapp show \
  --name "dvcresaledata" \
  --resource-group "dvc-resale-data"

# List Static Web Apps environments
az staticwebapp environment list \
  --name "dvcresaledata" \
  --resource-group "dvc-resale-data"
```

## 🚨 Troubleshooting

### Deployment Issues

**1. Resource Already Exists Errors**

If you encounter errors like "A resource with the ID ... already exists", use the comprehensive fix script:

```bash
# Run the comprehensive fix script
./fix-deployment-issues.sh
```

Or manually import resources:
```bash
# Import Static Web Apps
tofu import azurerm_static_site.main \
  "/subscriptions/{subscription-id}/resourceGroups/dvc-resale-data/providers/Microsoft.Web/staticSites/dvcresaledata"

# Import Custom Domain (apex)
tofu import azurerm_static_site_custom_domain.apex \
  "/subscriptions/{subscription-id}/resourceGroups/dvc-resale-data/providers/Microsoft.Web/staticSites/dvcresaledata/customDomains/dvcresaledata.com"

# Import Custom Domain (www)
tofu import azurerm_static_site_custom_domain.www \
  "/subscriptions/{subscription-id}/resourceGroups/dvc-resale-data/providers/Microsoft.Web/staticSites/dvcresaledata/customDomains/www.dvcresaledata.com"

# Import Metric Alert
tofu import azurerm_monitor_metric_alert.static_web_apps_availability \
  "/subscriptions/{subscription-id}/resourceGroups/dvc-resale-data/providers/Microsoft.Insights/metricAlerts/static-web-apps-availability"
```

**2. Static Web Apps Migration**

Error: `the 'managed_rule' field is only supported with the 'Premium_AzureFrontDoor' sku`

This is fixed by migrating to Azure Static Web Apps, which provides built-in CDN, SSL, and hosting without the complexity and costs of Front Door or CDN Classic.

Static Web Apps Free tier includes all necessary features.

**3. App Service Plan Deletion Conflict**

Error: `Server farm 'EastUSLinuxDynamicPlan' cannot be deleted because it has web app(s) assigned to it`

```bash
# Run the service plan migration script
./migrate-service-plan.sh

# Or manually migrate:
# 1. Create new service plan
az appservice plan create \
  --name "dvc-resale-data-plan" \
  --resource-group "dvc-resale-data" \
  --sku "Y1" \
  --is-linux true

# 2. Update function app to use new plan
az functionapp update \
  --name "dvc-resale-data-func" \
  --resource-group "dvc-resale-data" \
  --plan "/subscriptions/{subscription-id}/resourceGroups/dvc-resale-data/providers/Microsoft.Web/serverfarms/dvc-resale-data-plan"

# 3. Delete old service plan
az appservice plan delete \
  --name "EastUSLinuxDynamicPlan" \
  --resource-group "dvc-resale-data" \
  --yes
```

**4. Static Web Apps Configuration**

Error: `The resource type 'microsoft.cdn/profiles/afdendpoints' does not support diagnostic settings`

This is resolved by migrating to Static Web Apps, which has different monitoring capabilities and doesn't require separate diagnostic settings configuration.

**5. Deprecated Retention Policy Warnings**

Warning: `retention_policy has been deprecated in favor of azurerm_storage_management_policy`

These warnings have been addressed by removing the deprecated `retention_policy` blocks from diagnostic settings. Log retention is now managed through Log Analytics workspace settings.

### Common Issues

**1. OpenTofu State Lock**
```bash
# Remove state lock if stuck
az storage blob delete \
  --account-name "{tf-state-storage}" \
  --container-name "tfstate" \
  --name "terraform.tfstate.lock"
```

**2. DNS Propagation**
```bash
# Check DNS status
dig +trace dvcresaledata.com
nslookup dvcresaledata.com 8.8.8.8
```

**3. SSL Certificate Issues**
```bash
# Check custom domain status
az cdn custom-domain show \
  --endpoint-name "dvcresaledata" \
  --name "apex-domain" \
  --profile-name "dvcresaledata-cdn" \
  --resource-group "dvc-resale-data"
```

**4. Function App Issues**
```bash
# Check app settings
az functionapp config appsettings list \
  --name "dvc-resale-data-func" \
  --resource-group "dvc-resale-data"

# Restart Function App
az functionapp restart \
  --name "dvc-resale-data-func" \
  --resource-group "dvc-resale-data"
```

### Debug Commands

```bash
# Test infrastructure components
tofu output

# Check resource status
az resource list \
  --resource-group "dvc-resale-data" \
  --output table

# Test storage endpoints
curl -I https://dvcresaledatawebsite.z13.web.core.windows.net/

# Test CDN endpoint
curl -I https://dvcresaledata.azureedge.net
```

## 💰 Cost Management

### Estimated Monthly Costs

| Service | SKU | Est. Cost |
|---------|-----|-----------|
| Function App | Consumption (Y1) | $0-20 |
| Storage Accounts | Standard LRS | $1-5 |
| Static Web Apps | Free | $0 |
| Application Insights | Pay-as-you-go | $0-5 |
| DNS Zone | Standard | $0.50 |
| **Total** | | **~$2-30/month** |

> **Note**: Static Web Apps Free tier includes 100GB bandwidth, hosting, CDN, SSL certificates, and custom domains at no cost. Provides $10-20/month additional savings over CDN Classic.

### Cost Optimization Tips

1. **Use Consumption Plan**: Default Y1 plan scales to zero
2. **Configure Retention**: Set appropriate log retention periods
3. **Monitor Usage**: Use Azure Cost Management for tracking
4. **Cache Effectively**: Enable caching to reduce compute costs

## 🔒 Security Features

### Infrastructure Security
- **HTTPS Only**: All web resources enforce HTTPS
- **TLS 1.2**: Minimum TLS version enforced
- **RBAC**: Role-based access control for resources
- **Managed Identity**: Function App uses managed identity
- **OIDC Authentication**: Keyless authentication for CI/CD pipelines

### Application Security
- **Security Headers**: CDN adds security headers
- **Rate Limiting**: Configurable via `scraper_delay`
- **User-Agent Rotation**: Configurable user agent
- **Short-lived Tokens**: OIDC provides 15-minute authentication tokens

### Network Security
- **Static Web Apps Protection**: Built-in DDoS protection and global CDN
- **HTTPS Enforcement**: Automatic SSL/TLS certificates for all domains
- **Content Security**: Built-in security headers and CSP
- **Storage Security**: Private blob access for Function App data
- **Function Security**: CORS configuration
- **Cache Control**: Optimized CDN caching for static assets

### Quick Fix Commands

**Complete Deployment Fix (Recommended)**
```bash
# Run the comprehensive fix script for Static Web Apps migration
chmod +x fix-deployment-issues.sh
./fix-deployment-issues.sh

# Then run plan and apply
tofu plan
tofu apply

# Configure GitHub secret for deployments
tofu output static_web_app_api_key
# Add this to GitHub repository secrets as AZURE_STATIC_WEB_APPS_API_TOKEN
```

**Manual Step-by-Step Fix**
```bash
# 1. Import existing resources
./import-existing-resources.sh

# 2. Migrate service plan
./migrate-service-plan.sh

# 3. Apply Static Web Apps infrastructure
tofu plan
tofu apply

# 4. Configure GitHub Actions deployment
# Get API key: tofu output static_web_app_api_key
# Add to GitHub secrets: AZURE_STATIC_WEB_APPS_API_TOKEN

# 5. Deploy website
git push origin main  # Triggers automatic deployment
```

**Emergency Reset (Last Resort)**
```bash
# WARNING: This will destroy all infrastructure
tofu destroy

# Then redeploy from scratch
tofu apply
```

## 📚 Additional Resources

- [Azure Functions Documentation](https://docs.microsoft.com/en-us/azure/azure-functions/)
- [OpenTofu Documentation](https://opentofu.org/docs/)
- [Azure Provider Documentation](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)
- [Azure Static Web Apps Documentation](https://docs.microsoft.com/en-us/azure/static-web-apps/)
- [Static Web Apps Configuration](https://docs.microsoft.com/en-us/azure/static-web-apps/configuration)
- [GitHub Actions for Static Web Apps](https://docs.microsoft.com/en-us/azure/static-web-apps/github-actions-workflow)
- [Azure DNS Documentation](https://docs.microsoft.com/en-us/azure/dns/)
- [Azure OIDC Documentation](https://docs.microsoft.com/en-us/azure/active-directory/develop/workload-identity-federation)
- [GitHub OIDC Documentation](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
- [OpenTofu State Management](https://opentofu.org/docs/language/state/)
- [Static Web Apps Pricing](https://azure.microsoft.com/en-us/pricing/details/app-service/static/)

## 🤝 Contributing

When making infrastructure changes:

1. **Test Locally**: Use `tofu plan` to preview changes
2. **Use Feature Branches**: Create PRs for infrastructure changes
3. **Update Documentation**: Keep this README current
4. **Follow Naming**: Use existing naming conventions in `locals.tf`
5. **Add Variables**: Use variables for configurable values
6. **Tag Resources**: Ensure all resources have appropriate tags

## 📞 Support

For infrastructure issues:

1. Check this documentation first
2. Review OpenTofu plan output
3. Check Azure Portal for resource status
4. Review GitHub Actions logs for deployment issues
5. Create an issue with relevant logs and error messages

---

**Note**: This infrastructure is designed for production use with built-in monitoring, security, and performance optimizations. All resources follow Azure best practices and naming conventions.