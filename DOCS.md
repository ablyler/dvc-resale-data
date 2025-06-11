# DVC ROFR Data Scraper: Detailed Documentation

This document provides detailed information about the ROFR scraper functionality, data format, and analysis capabilities, including the date filtering feature.

## Table of Contents

1. [ROFR Format](#rofr-format)
2. [Data Fields](#data-fields)
3. [Resort Codes](#resort-codes)
4. [Analysis Features](#analysis-features)
5. [Technical Details](#technical-details)
6. [Troubleshooting](#troubleshooting)

## ROFR Format

The DVC ROFR (Right of First Refusal) data follows a specific format on the DisBoards forums:

```
DISname---$Price per point-$Total cost-# of points-Home resort-Use Year-Points availability- sent date, result date
```

Example:
```
pangyal---$144-$33296-219-VGF-Aug-113/14, 219/15, 219/16, 219/17- sent 8/24, passed 9/16
```

This information represents a DVC contract that was submitted for ROFR review, including its key details and the final decision by Disney (whether they exercised their right of first refusal or waived it).

## Data Fields

The scraper extracts the following data fields:

| Field | Description | Example |
|-------|-------------|---------|
| `username` | DisBoards username | "pangyal" |
| `price_per_point` | Price per point in USD | 144.0 |
| `total_cost` | Total cost of the contract in USD | 33296.0 |
| `points` | Number of points in the contract | 219 |
| `resort` | DVC resort code | "VGF" |
| `use_year` | Use year month | "Aug" |
| `points_details` | Points available by year | "113/14, 219/15, 219/16, 219/17" |
| `sent_date` | Date the contract was sent for ROFR (string format) | "8/24" |
| `parsed_sent_date` | Date object parsed from sent_date | datetime.date(2024, 8, 1) |
| `result` | Result of ROFR | "passed" |
| `result_date` | Date of the ROFR decision | "9/16" |
| `thread_url` | URL of the thread where this data was found | "https://www.disboards.com/threads/rofr-thread..." |
| `raw_entry` | The original data string | "pangyal---$144-$33296-219-VGF-Aug-113/14, 219/15, 219/16, 219/17- sent 8/24, passed 9/16" |

Additional calculated fields in the analysis:

| Field | Description |
|-------|-------------|
| `year` | Year the contract was sent for ROFR |
| `quarter` | Quarter and year (e.g., "Q2-2025") |
| `decision_days` | Number of days between sent and result dates |
| `thread_start_date` | Start date of the thread where data was found |

## Resort Codes

Common DVC resort codes found in the data:

| Code | Resort |
|------|--------|
| AKV | Animal Kingdom Villas |
| AUL | Aulani |
| BCV | Beach Club Villas |
| BLT | Bay Lake Tower |
| BWV | BoardWalk Villas |
| CCV | Copper Creek Villas |
| BRV | Boulder Ridge Villas |
| GFV or VGF | Grand Floridian Villas |
| HH | Hilton Head Island Resort |
| OKW | Old Key West |
| PVB | Polynesian Villas & Bungalows |
| RIV | Riviera Resort |
| SSR | Saratoga Springs Resort |
| VGC | Grand Californian |
| VB | Vero Beach |
| VDH | Disney's Hotel |

## Analysis Features

The analysis script (`analyze_rofr_data.py`) provides the following features:

### Basic Statistics

- Total number of contracts
- Breakdown by result (passed, taken, pending)
- Overall ROFR rate
- Resort distribution
- Price statistics (mean, median, min, max)
- Points statistics
- Decision time statistics

### Visualizations

1. **Price Trends**
   - Tracks average price per point over time by resort
   - Identifies pricing trends and seasonality

2. **ROFR Rates by Resort**
   - Shows which resorts have the highest ROFR rates
   - Includes sample size information

3. **Price Distribution**
   - Box plots showing price distribution by resort
   - Individual data points overlaid for detailed view

### Resort-Specific Analysis

For each resort, the analyzer can provide:
- Total number of contracts
- Results breakdown and ROFR rate
- Price statistics
- Comparison of passed vs. taken contract prices
- Points statistics
- Decision time statistics

## Technical Details

### Data Parsing

The scraper uses regular expressions to extract ROFR data from forum posts. The main pattern is:

```python
ROFR_PATTERN = r'([A-Za-z0-9_\-]+)---\$(\d+(?:\.\d+)?)(?:-\$(\d+(?:\.\d+)?))?-(\d+)-([A-Z@]+)-([A-Za-z]+)(?:-([^-]*))?- sent (\d+/\d+)(?:, (passed|taken) (\d+/\d+))?'
```

This pattern handles variations in the format while ensuring all key data is captured.

### Date Filtering

The scraper supports filtering data by a start date in MM/YYYY format (e.g., "01/2023" for January 2023). When a start date is provided:

1. Thread filtering: Threads with start dates before the specified date may be skipped entirely if they don't contain relevant data
2. Entry filtering: Individual ROFR entries with sent dates before the specified date are filtered out
3. Date parsing: The scraper converts MM/YY format dates (e.g., "8/24" for August 2024) to full date objects for comparison

### Thread Discovery

The scraper can find ROFR threads using several approaches:
1. Using known thread URLs directly
2. Following links from the current thread to previous threads
3. Extracting date ranges from thread titles to organize data chronologically

The threads typically follow quarterly naming patterns like:
- "ROFR Thread January to March 2024"
- "ROFR Thread April to June 2024"

When a start date filter is applied, the scraper analyzes thread titles to determine if the thread might contain relevant data before processing it, which improves performance.

### Date Handling

The script handles various date formats, including:
- MM/YY (e.g., "8/24")
- MM/DD/YY
- MM/YYYY (for start date filtering)
- Written dates

Dates are converted to datetime objects for proper analysis and comparison. The start date filter uses the first day of the specified month as the cutoff point for filtering data.

When parsing MM/YY format dates:
- For years below 50, the script assumes 20xx (e.g., "8/24" becomes August 2024)
- For years 50 and above, the script assumes 19xx (though this is rarely used in current ROFR data)

## Troubleshooting

### Common Issues

1. **No Data Found**
   - Check that the URL is correct
   - Verify that the forum thread contains properly formatted ROFR data
   - Inspect the HTML structure to ensure the scraper is targeting the right elements
   - If using a start date filter, ensure that the date range includes data (try with an earlier date)

2. **Parse Errors**
   - Some users may not follow the standard format
   - The regex pattern might need adjustment for certain edge cases
   - Check for unusual characters or formatting in the raw data
   - Date parsing issues may occur with non-standard date formats

3. **Rate Limiting**
   - The scraper uses delays between requests to avoid overloading the server
   - If you encounter connection issues, try increasing the delay parameter

### Logging

The script provides console output to track progress and identify issues. For more detailed logging, you can add the following to the beginning of your script:

```python
import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
```

This will provide more detailed information about the scraping process, including date filtering decisions.

## Command Line Options

The scraper supports the following command line options:

```
--output, -o           Output CSV file (default: rofr_data.csv)
--current-thread, -c   Current ROFR thread URL to extract past thread URLs from
--start-date, -s       Start date for filtering data (MM/YYYY format, e.g., 01/2023)
--delay, -d            Delay between requests in seconds (default: 1.0)
--max-pages, -m        Maximum pages to scrape per thread (default: 100)
--urls, -u             Specific thread URLs to scrape (optional)
```

### Example Commands

```bash
# Scrape all ROFR data from January 2023 onwards
python rofr_scraper.py --current-thread "https://www.disboards.com/threads/rofr-thread-april-to-june-2025-please-see-first-post-for-instructions-formatting-tool.3965193" --start-date "01/2023"

# Scrape specific thread with custom output file
python rofr_scraper.py --output "custom_output.csv" --urls "https://www.disboards.com/threads/specific-rofr-thread.12345"
```