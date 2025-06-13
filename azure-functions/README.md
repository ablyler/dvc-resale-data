# ROFR Scraper - Azure Functions Deployment

This directory contains the Azure Functions implementation of the ROFR scraper, migrated from SQLite to Azure Table Storage with hourly timer triggers.

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Azure Logic   │    │  Azure Functions │    │ Azure Table     │
│   Apps (Timer)  │───▶│   (Scraper)      │───▶│ Storage         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │   HTTP API       │
                       │   Endpoints      │
                       └──────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │ React Frontend   │
                       │ (Static Web App) │
                       └──────────────────┘
```

## 📋 Components

### Azure Functions
- **Timer Trigger**: Runs every hour to scrape ROFR data
- **HTTP API**: REST endpoints for data access
- **Table Storage**: Persistent data storage

### Key Files
- `function_app.py` - Main Azure Functions app
- `rofr_scraper_azure.py` - Azure-optimized scraper
- `table_storage_manager.py` - Table Storage operations
- `models.py` - Data models and helpers
- `deploy.sh` - Deployment automation script

## 🚀 Quick Deployment

### Prerequisites
1. **Azure CLI** installed and logged in
2. **Azure Functions Core Tools v4**
3. **Python 3.9+**
4. **Active Azure subscription**

### One-Command Deployment
```bash
./deploy.sh
```

This script will:
- Create Azure resource group
- Set up Storage Account
- Deploy Function App
- Configure application settings
- Enable CORS
- Deploy function code

### Manual Deployment Steps

1. **Install Azure Functions Core Tools**
```bash
npm install -g azure-functions-core-tools@4 --unsafe-perm true
```

2. **Create Azure Resources**
```bash
# Create resource group
az group create --name dvc-resale-data --location eastus

# Create storage account
az storage account create \
  --name rofrstorageacct12345 \
  --resource-group dvc-resale-data \
  --location eastus \
  --sku Standard_LRS

# Create function app
az functionapp create \
  --name dvc-resale-data-func \
  --resource-group dvc-resale-data \
  --storage-account rofrstorageacct12345 \
  --consumption-plan-location eastus \
  --runtime python \
  --runtime-version 3.9 \
  --functions-version 4
```

3. **Configure Environment Variables**
```bash
az functionapp config appsettings set \
  --name dvc-resale-data-func \
  --resource-group dvc-resale-data \
  --settings \
  "AZURE_STORAGE_CONNECTION_STRING=<your-connection-string>" \
  "ROFR_TABLE_NAME=rofrdata" \
  "SCRAPER_DELAY=1.0" \
  "SCRAPER_MAX_PAGES=100" \
  "SCRAPER_LOG_LEVEL=INFO"
```

4. **Deploy Function Code**
```bash
func azure functionapp publish dvc-resale-data-func
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AZURE_STORAGE_CONNECTION_STRING` | Azure Storage connection string | Required |
| `ROFR_TABLE_NAME` | Table Storage table name | `rofrdata` |
| `SCRAPER_DELAY` | Delay between requests (seconds) | `1.0` |
| `SCRAPER_MAX_PAGES` | Maximum pages per thread | `100` |
| `SCRAPER_LOG_LEVEL` | Logging level | `INFO` |
| `SCRAPER_USER_AGENT` | HTTP User-Agent string | Chrome default |

### Table Storage Schema

The scraper uses three tables:

#### `rofrdata` - Main ROFR entries
- **PartitionKey**: Resort code (e.g., VGF, BWV)
- **RowKey**: Entry hash (unique identifier)
- **Fields**: username, price_per_point, points, sent_date, result, etc.

#### `rofrdatathreads` - Thread tracking
- **PartitionKey**: `thread`
- **RowKey**: URL hash
- **Fields**: url, title, last_scraped_page, total_pages, etc.

#### `rofrdatasessions` - Scraping sessions
- **PartitionKey**: `session`
- **RowKey**: Session ID (timestamp)
- **Fields**: started_at, completed_at, new_entries, status, etc.

## 📡 API Endpoints

### Base URL
```
https://your-function-app.azurewebsites.net/api
```

### Endpoints

#### `GET /rofr-data`
Get ROFR entries with optional filters
```bash
# Get all entries
curl "https://your-app.azurewebsites.net/api/rofr-data"

# Filter by resort
curl "https://your-app.azurewebsites.net/api/rofr-data?resort=VGF"

# Filter by date range
curl "https://your-app.azurewebsites.net/api/rofr-data?start_date=2024-01-01"

# Filter by result
curl "https://your-app.azurewebsites.net/api/rofr-data?result=passed"
```

**Query Parameters:**
- `resort` - Filter by resort code
- `result` - Filter by result (pending, passed, taken)
- `start_date` - Filter by sent date (YYYY-MM-DD)
- `username` - Filter by username
- `limit` - Limit results (max 5000)

#### `GET /rofr-stats`
Get statistics and summary data
```bash
curl "https://your-app.azurewebsites.net/api/rofr-stats"
```

#### `GET /rofr-export`
Export data in various formats
```bash
# Export as JSON
curl "https://your-app.azurewebsites.net/api/rofr-export?format=json"

# Export as CSV
curl "https://your-app.azurewebsites.net/api/rofr-export?format=csv" > data.csv
```

#### `POST /trigger-scrape`
Manually trigger a scraping session
```bash
curl -X POST "https://your-app.azurewebsites.net/api/trigger-scrape" \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2024-01-01"}'
```

#### `GET /health`
Health check endpoint
```bash
curl "https://your-app.azurewebsites.net/api/health"
```

#### `GET /resorts`
Get valid resort codes and names
```bash
curl "https://your-app.azurewebsites.net/api/resorts"
```

## ⏰ Scheduled Execution

The scraper runs automatically every hour via a timer trigger:
- **Schedule**: `0 0 * * * *` (every hour at minute 0)
- **Function**: `scrape_rofr_hourly`
- **Behavior**: Auto-detects current ROFR thread and scrapes incrementally

### Monitoring Scheduled Runs

1. **Azure Portal**: Function App → Functions → scrape_rofr_hourly → Monitor
2. **Application Insights**: Real-time metrics and logs
3. **Log Stream**: Live log viewing in Azure Portal

## 💰 Cost Estimation

### Monthly Costs (Consumption Plan)
- **Function App**: ~$5-10 (1M executions included)
- **Storage Account**: ~$1-5 (depends on data size)
- **Bandwidth**: ~$1-3 (minimal for API usage)

**Total**: ~$7-18/month

### Cost Optimization Tips
1. Use Consumption plan (pay-per-execution)
2. Monitor execution time and optimize if needed
3. Use Table Storage instead of Cosmos DB
4. Enable request filtering to reduce data transfer

## 🔍 Monitoring & Debugging

### View Logs
```bash
# Stream live logs
func azure functionapp logstream dvc-resale-data-func

# Or view in Azure Portal
# Function App → Functions → scrape_rofr_hourly → Monitor
```

### Common Issues

#### "Connection string not found"
- Verify `AZURE_STORAGE_CONNECTION_STRING` in app settings
- Check storage account exists and key is valid

#### "Timer function not triggering"
- Check Function App is running (not stopped)
- Verify timer schedule syntax
- Check timezone settings (UTC by default)

#### "Scraping errors"
- Check network connectivity
- Verify DisBoards forum structure hasn't changed
- Monitor request delays to avoid rate limiting

### Debug Locally

1. **Set up local.settings.json**
```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AZURE_STORAGE_CONNECTION_STRING": "your-connection-string",
    "ROFR_TABLE_NAME": "rofrdata"
  }
}
```

2. **Run locally**
```bash
func start
```

3. **Test endpoints**
```bash
curl "http://localhost:7071/api/health"
```

## 🔄 Migration from SQLite

If you have existing SQLite data, you can migrate it:

1. **Export SQLite to CSV**
```python
# Use the original rofr_scraper.py
python rofr_scraper.py --export-csv legacy_data.csv
```

2. **Import to Table Storage**
```python
# Create a migration script using table_storage_manager.py
from table_storage_manager import AzureTableStorageManager
import csv

storage = AzureTableStorageManager(connection_string, table_name)
# Process CSV and call storage.upsert_entry() for each row
```

## 📊 Data Analysis Integration

The Table Storage data can be easily consumed by:

1. **Power BI**: Direct connection to Azure Table Storage
2. **Excel**: Azure Tables connector
3. **Custom React App**: Using the HTTP API endpoints
4. **Azure Data Factory**: For ETL pipelines

## 🚀 Next Steps

1. **Deploy the scraper** using `./deploy.sh`
2. **Monitor first execution** in Azure Portal
3. **Test API endpoints** with sample queries
4. **Set up React frontend** (optional)
5. **Configure alerts** for failures or anomalies

## 🤝 Contributing

When contributing to the Azure Functions version:

1. **Test locally** before deploying
2. **Update environment variables** if adding new config
3. **Monitor costs** during development
4. **Follow Azure Functions best practices**

## 📄 License

Same as the main project.