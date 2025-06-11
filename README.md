# DVC ROFR Data Scraper

This script scrapes Right of First Refusal (ROFR) data from Disney Vacation Club (DVC) forum threads on disboards.com. It extracts information about DVC contracts that were sent for ROFR, including price per point, resort, points, and whether Disney waived or exercised their right. The scraper can automatically extract links to all past ROFR threads from the current thread's first post and filter data by start date.

## Quick Start

```bash
# Run the scraper with default settings (all threads from current thread)
./rofr-scraper.sh

# Scrape only data from January 2023 onwards
./rofr-scraper.sh --start-date=01/2023

# Scrape only the current thread
./rofr-scraper.sh --mode=single

# Scrape specific URLs
./rofr-scraper.sh --mode=custom --urls=https://url1.com,https://url2.com
```

## Requirements

- Python 3.9+ and Pipenv (for direct installation)
- OR Docker (for containerized approach)

## Installation

### Method 1: Using Pipenv

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/rofr-disboards-scraper.git
   cd rofr-disboards-scraper
   ```

2. Install dependencies using Pipenv:
   ```
   pipenv install
   ```

   For development (includes testing tools):
   ```
   pipenv install --dev
   ```

### Method 2: Using Docker

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/rofr-disboards-scraper.git
   cd rofr-disboards-scraper
   ```

2. Build the Docker image:
   ```
   docker build -t rofr-scraper .
   ```

   Or use docker-compose:
   ```
   docker-compose build
   ```

## Usage

### Method 1: Using the Consolidated Script

The `rofr-scraper.sh` script combines all functionality in a single, easy-to-use interface:

```bash
# Basic usage (all threads from current thread)
./rofr-scraper.sh

# Different modes
./rofr-scraper.sh --mode=full    # Extract all threads (default)
./rofr-scraper.sh --mode=single  # Only scrape the current thread
./rofr-scraper.sh --mode=custom --urls=URL1,URL2  # Scrape specific URLs

# Date filtering
./rofr-scraper.sh --start-date=01/2023  # Only include data from Jan 2023 onwards

# Custom output
./rofr-scraper.sh --output-dir=my_data --output-file=custom_name.csv

# Skip analysis
./rofr-scraper.sh --no-analyze
```

For a complete list of options, run `./rofr-scraper.sh --help`

### Method 2: Using Pipenv

Run commands within the Pipenv virtual environment:

```
# All-in-one command (scrape and analyze)
pipenv run run --url "https://www.disboards.com/threads/rofr-thread-april-to-june-2025-please-see-first-post-for-instructions-formatting-tool.3965193"

# Scrape data only
pipenv run scrape --output rofr_data.csv

# Analyze data
pipenv run analyze rofr_data.csv
```

Alternatively, activate the Pipenv shell first:

```
pipenv shell
python rofr_scraper.py [options]
python analyze_rofr_data.py [options]
```

### Method 2: Using Docker

Run the scraper with Docker:

```
# Create a data directory for output
mkdir -p data

# Run the scraper
docker run -v $(pwd)/data:/data rofr-scraper rofr_scraper.py --output /data/rofr_data.csv --current-thread "https://www.disboards.com/threads/rofr-thread-april-to-june-2025-please-see-first-post-for-instructions-formatting-tool.3965193"

# Run the analyzer
docker run -v $(pwd)/data:/data rofr-scraper analyze_rofr_data.py /data/rofr_data.csv --output-dir /data/analysis
```

Using docker-compose:

```
# Run the scraper and analyzer in sequence
docker-compose up

# Run just the scraper
docker-compose run scraper

# Run just the analyzer
docker-compose run analyzer
```

The results will be stored in the `./data` directory on your host machine.

### Command Line Options

### Consolidated Script Options

```bash
./rofr-scraper.sh [options]
```

Available options:

- `--mode=MODE`: Scraping mode (`full`, `single`, or `custom`)
- `--url=URL`: URL of the current ROFR thread
- `--urls=URL1,URL2`: Comma-separated list of specific thread URLs to scrape (for custom mode)
- `--output-dir=DIR`: Directory to save output files (default: `data`)
- `--output-file=FILE`: Specific output filename (default: auto-generated based on date)
- `--delay=SECONDS`: Delay between requests in seconds (default: 1.0)
- `--max-pages=NUM`: Maximum pages to scrape per thread (default: 100)
- `--start-date=DATE`: Only include data from this date onwards (MM/YYYY format, e.g., 01/2023)
- `--no-analyze`: Skip the analysis step
- `--help`: Display help message

### All-in-one Python Script

```
python run.py [options]
```

Available options:

- `--url`, `-u`: Specific DisBoards thread URL to scrape
- `--output-dir`, `-o`: Directory to save output files (default: `data`)
- `--current-thread`, `-c`: Current ROFR thread URL to extract all past thread URLs from
- `--start-date`, `-s`: Start date for filtering data (MM/YYYY format, e.g., 01/2023)
- `--delay`, `-d`: Delay between requests in seconds (default: 1.0)
- `--max-pages`, `-m`: Maximum pages to scrape per thread (default: 100)
- `--skip-analysis`: Skip the analysis step
- `--resort`, `-r`: Analyze specific resort only
- `--docker`: Use Docker instead of direct execution

### Scraper Script

```
python rofr_scraper.py [options]
```

Available options:

- `--output`, `-o`: Output CSV file (default: `rofr_data.csv`)
- `--delay`, `-d`: Delay between requests in seconds (default: 1.0)
- `--max-pages`, `-m`: Maximum pages to scrape per thread (default: 100)
- `--current-thread`, `-c`: Current ROFR thread URL to extract all past thread URLs from
- `--start-date`, `-s`: Start date for filtering data (MM/YYYY format, e.g., 01/2023)
- `--urls`, `-u`: Specific thread URLs to scrape (optional)

### Examples

#### Using Consolidated Script

```bash
# Scrape all threads with default settings
./rofr-scraper.sh

# Scrape only the current thread
./rofr-scraper.sh --mode=single

# Scrape specific URLs
./rofr-scraper.sh --mode=custom --urls="https://www.disboards.com/threads/thread1.12345,https://www.disboards.com/threads/thread2.67890"

# Filter data by date
./rofr-scraper.sh --start-date=01/2023

# Custom output location and filename
./rofr-scraper.sh --output-dir=my_data --output-file=dvc_rofr_data.csv

# Change request delay and max pages
./rofr-scraper.sh --delay=2.0 --max-pages=50
```

#### Using Pipenv

```
# Scrape specific thread and analyze
pipenv run run --url "https://www.disboards.com/threads/rofr-thread-april-to-june-2025-please-see-first-post-for-instructions-formatting-tool.3965193"

# Scrape data only from January 2023 onwards
pipenv run run --current-thread "https://www.disboards.com/threads/rofr-thread-april-to-june-2025-please-see-first-post-for-instructions-formatting-tool.3965193" --start-date "01/2023"

# Scrape and analyze only AKV resort data from April 2024 onwards
pipenv run run --current-thread "https://www.disboards.com/threads/rofr-thread-april-to-june-2025-please-see-first-post-for-instructions-formatting-tool.3965193" --start-date "04/2024" --resort AKV

# Use Docker mode
pipenv run run --docker --url "https://www.disboards.com/threads/rofr-thread-april-to-june-2025-please-see-first-post-for-instructions-formatting-tool.3965193"
```

Using the individual scripts:
```
# Scrape specific threads
pipenv run python rofr_scraper.py -u https://www.disboards.com/threads/rofr-thread-april-to-june-2025-please-see-first-post-for-instructions-formatting-tool.3965193

# Scrape threads from 2020 onwards
pipenv run python rofr_scraper.py -y 2020

# Save output to a specific file with increased delay
pipenv run python rofr_scraper.py -o my_rofr_data.csv -d 2.0
```

#### Using Docker

Scrape specific threads:
```
docker run -v $(pwd)/data:/data rofr-scraper rofr_scraper.py --output /data/rofr_data.csv --current-thread "https://www.disboards.com/threads/rofr-thread-april-to-june-2025-please-see-first-post-for-instructions-formatting-tool.3965193"
```

Scrape data from January 2023 onwards:
```
docker run -v $(pwd)/data:/data rofr-scraper rofr_scraper.py --output /data/rofr_data.csv --current-thread "https://www.disboards.com/threads/rofr-thread-april-to-june-2025-please-see-first-post-for-instructions-formatting-tool.3965193" --start-date "01/2023"
```

Scrape specific thread along with current thread:
```
docker run -v $(pwd)/data:/data rofr-scraper rofr_scraper.py --output /data/rofr_data.csv --current-thread "https://www.disboards.com/threads/rofr-thread-april-to-june-2025-please-see-first-post-for-instructions-formatting-tool.3965193" --urls "https://www.disboards.com/threads/specific-rofr-thread-to-include.123456"
```

Save output with increased delay:
```
docker run -v $(pwd)/data:/data rofr-scraper rofr_scraper.py --output /data/rofr_data.csv --delay 2.0
```

## Data Format

The script extracts ROFR data strings in the following format:
```
DISname---$Price per point-$Total cost-# of points-Home resort-Use Year-Points by year- sent date, passed/taken date
```

Example:
```
pangyal---$144-$33296-219-VGF-Aug-113/14, 219/15, 219/16, 219/17- sent 8/24, passed 9/16
```

When using the `--start-date` option, the scraper will filter out any entries with a sent date before the specified date. The date should be in MM/YYYY format (e.g., "01/2023" for January 2023).

The script parses these strings and saves the following fields to the CSV file:

- `username`: DisBoards username
- `price_per_point`: Price per point in USD
- `total_cost`: Total cost of the contract in USD
- `points`: Number of points in the contract
- `resort`: DVC resort code (e.g., AKV, BLT, VGF)
- `use_year`: Use year month (e.g., Feb, Aug)
- `points_details`: Points available by year
- `sent_date`: Date the contract was sent for ROFR (string format)
- `parsed_sent_date`: Date the contract was sent for ROFR (parsed date object)
- `result`: Result of ROFR (passed, taken, or pending)
- `result_date`: Date of the ROFR decision
- `thread_url`: URL of the thread where this data was found
- `raw_entry`: The original data string

## Analysis Features

The analysis script provides:

- Basic statistics on prices, points, and ROFR rates
- Visualizations for price trends and ROFR rates by resort
- Resort-specific analysis
- Temporal analysis of data filtered by start date

See the [DOCS.md](DOCS.md) file for detailed documentation.

## Disclaimer

This script is for educational purposes only. Be respectful of disboards.com's servers and follow their terms of service by not making excessive requests. The default delay between requests (1 second) is set to minimize server load.

## Docker Configuration

The included Docker configuration provides:

- A standardized environment for running the scraper
- Volume mapping for data persistence
- Separate services for scraping and analysis
- Easy deployment on any system with Docker installed

You can use Docker in two ways:
1. Via the all-in-one script with the `--docker` flag:
   ```
   python run.py --docker --url "https://www.disboards.com/threads/rofr-thread-april-to-june-2025-please-see-first-post-for-instructions-formatting-tool.3965193"
   ```

2. Directly with docker commands or docker-compose (see examples above)

See the `Dockerfile` and `docker-compose.yml` for details.

## Script Files

The project includes the following script files:

- `rofr-scraper.sh` - Consolidated script that combines all functionality
- `rofr_scraper.py` - Core Python scraper script
- `analyze_rofr_data.py` - Data analysis script
- `run.py` - All-in-one Python script with Docker support

## License

MIT