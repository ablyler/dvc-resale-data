#!/bin/bash
#
# Disney Vacation Club ROFR Data Scraper
# 
# This consolidated script provides a simple interface to run the DVC ROFR scraper
# with various options and clear instructions.
#
# Created by combining functionality from:
# - scrape_rofr.sh
# - scrape_all_rofr_threads.sh
# - run_example.sh

# Set default values
CURRENT_THREAD="https://www.disboards.com/threads/rofr-thread-april-to-june-2025-please-see-first-post-for-instructions-formatting-tool.3965193"
OUTPUT_DIR="data"
OUTPUT_FILE=""
OUTPUT_FORMAT="csv" # Options: csv, json
DELAY=1.0
ANALYZE=true
MAX_PAGES=100
START_DATE=""
SPECIFIC_URLS=()
MODE="auto" # Options: full (extract all threads), single (specific thread), custom (specific URLs), auto (auto-detect current thread)
AUTO_DETECT=true

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Display the header
print_header() {
    echo "==================================================="
    echo "  Disney Vacation Club ROFR Data Scraper"
    echo "==================================================="
    echo ""
}

# Display help information
show_help() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --mode=MODE         Scraping mode: full, single, custom, or auto (default: auto)"
    echo "                      full: Extract all ROFR threads from current thread"
    echo "                      single: Only scrape the current thread"
    echo "                      custom: Only scrape the specific URLs provided with --urls"
    echo "                      auto: Auto-detect current thread and scrape all ROFR threads"
    echo "  --url=URL           URL of the current ROFR thread (default: April-June 2025 thread)"
    echo "  --urls=URL1,URL2    Comma-separated list of specific thread URLs to scrape (for custom mode)"
    echo "  --output-dir=DIR    Directory to save output files (default: data)"
    echo "  --output-file=FILE  Specific output filename (default: auto-generated based on date)"
    echo "  --format=FORMAT     Output format: csv or json (default: csv)"
    echo "  --delay=SECONDS     Delay between requests in seconds (default: 1.0)"
    echo "  --max-pages=NUM     Maximum pages to scrape per thread (default: 100)"
    echo "  --start-date=DATE   Only include data from this date onwards (MM/YYYY format, e.g., 01/2023)"
    echo "  --no-analyze        Skip the analysis step"
    echo "  --help              Display this help message"
    echo ""
    echo "Examples:"
    echo "  $0                  # Scrape all ROFR threads using default settings"
    echo "  $0 --mode=auto      # Auto-detect current thread and scrape all ROFR threads"
    echo "  $0 --mode=single    # Scrape only the current thread"
    echo "  $0 --start-date=01/2023  # Scrape all threads but only include data from Jan 2023 onwards"
    echo "  $0 --format=json    # Output data in JSON format instead of CSV"
    echo "  $0 --mode=custom --urls=https://url1.com,https://url2.com  # Scrape specific URLs"
    echo ""
}

# Check if Pipenv is installed
if ! command -v pipenv &> /dev/null; then
    echo "Error: Pipenv is required but not found."
    echo "Install it with: pip install pipenv"
    exit 1
fi

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --mode=*)
            MODE="${1#*=}"
            if [[ "$MODE" != "full" && "$MODE" != "single" && "$MODE" != "custom" && "$MODE" != "auto" ]]; then
                echo "Error: Invalid mode. Must be 'full', 'single', 'custom', or 'auto'."
                exit 1
            fi
            if [[ "$MODE" == "auto" ]]; then
                AUTO_DETECT=true
            fi
            shift
            ;;
        --url=*)
            CURRENT_THREAD="${1#*=}"
            shift
            ;;
        --urls=*)
            IFS=',' read -ra SPECIFIC_URLS <<< "${1#*=}"
            shift
            ;;
        --output-dir=*)
            OUTPUT_DIR="${1#*=}"
            shift
            ;;
        --output-file=*)
            OUTPUT_FILE="${1#*=}"
            shift
            ;;
        --format=*)
            OUTPUT_FORMAT="${1#*=}"
            if [[ "$OUTPUT_FORMAT" != "csv" && "$OUTPUT_FORMAT" != "json" ]]; then
                echo "Error: Invalid format. Must be 'csv' or 'json'."
                exit 1
            fi
            shift
            ;;
        --delay=*)
            DELAY="${1#*=}"
            shift
            ;;
        --max-pages=*)
            MAX_PAGES="${1#*=}"
            shift
            ;;
        --start-date=*)
            START_DATE="${1#*=}"
            shift
            ;;
        --no-analyze)
            ANALYZE=false
            shift
            ;;
        --help)
            print_header
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information."
            exit 1
            ;;
    esac
done

# Set up file names
DATE=$(date +%Y%m%d_%H%M%S)
if [[ -z "$OUTPUT_FILE" ]]; then
    case "$MODE" in
        "full")
            OUTPUT_FILE="rofr_data_all_threads_$DATE.$OUTPUT_FORMAT"
            ;;
        "single")
            OUTPUT_FILE="rofr_data_single_thread_$DATE.$OUTPUT_FORMAT"
            ;;
        "custom")
            OUTPUT_FILE="rofr_data_custom_$DATE.$OUTPUT_FORMAT"
            ;;
        "auto")
            OUTPUT_FILE="rofr_data_auto_$DATE.$OUTPUT_FORMAT"
            ;;
    esac
fi

CSV_FILE="$OUTPUT_DIR/$OUTPUT_FILE"
ANALYSIS_DIR="$OUTPUT_DIR/analysis_$DATE"

# Display configuration
print_header
echo "Mode: $MODE"
if [ "$MODE" != "auto" ]; then
    echo "Current thread URL: $CURRENT_THREAD"
fi
echo "Output file: $CSV_FILE"
echo "Output format: $OUTPUT_FORMAT"
echo "Request delay: $DELAY seconds"
echo "Max pages per thread: $MAX_PAGES"
if [ -n "$START_DATE" ]; then
    echo "Start date filter: $START_DATE"
fi
if [ "$MODE" == "custom" ] && [ ${#SPECIFIC_URLS[@]} -gt 0 ]; then
    echo "Custom URLs to scrape:"
    for url in "${SPECIFIC_URLS[@]}"; do
        echo "  - $url"
    done
fi
if [ "$MODE" == "auto" ]; then
    echo "Auto-detecting current thread URL..."
fi
echo ""

# Install dependencies if needed
echo "Installing dependencies..."
pipenv install

# Build the scraper command based on the mode
echo "Running scraper..."
SCRAPER_CMD=(pipenv run python rofr_scraper.py --output "$CSV_FILE" --format "$OUTPUT_FORMAT" --delay "$DELAY" --max-pages "$MAX_PAGES")

if [ -n "$START_DATE" ]; then
    SCRAPER_CMD+=(--start-date "$START_DATE")
fi

case "$MODE" in
    "full")
        SCRAPER_CMD+=(--current-thread "$CURRENT_THREAD")
        ;;
    "single")
        SCRAPER_CMD+=(--urls "$CURRENT_THREAD")
        ;;
    "custom")
        if [ ${#SPECIFIC_URLS[@]} -gt 0 ]; then
            for url in "${SPECIFIC_URLS[@]}"; do
                SCRAPER_CMD+=(--urls "$url")
            done
        else
            echo "Error: Custom mode selected but no URLs provided."
            echo "Use --urls=URL1,URL2,... to specify URLs."
            exit 1
        fi
        ;;
    "auto")
        SCRAPER_CMD+=(--auto-detect)
        ;;
esac

# Run the scraper
"${SCRAPER_CMD[@]}"

# Check if scraping was successful
if [ ! -f "$CSV_FILE" ]; then
    echo "Error: Scraping failed or no data found."
    exit 1
fi

# Count entries
ENTRIES=$(tail -n +2 "$CSV_FILE" | wc -l)
echo ""
echo "Successfully scraped $ENTRIES ROFR entries!"

# Run analysis if enabled
if [ "$ANALYZE" = true ] && [ "$OUTPUT_FORMAT" = "csv" ]; then
    echo ""
    echo "Running analysis..."
    mkdir -p "$ANALYSIS_DIR"
    
    pipenv run python analyze_rofr_data.py \
        "$CSV_FILE" \
        --output-dir "$ANALYSIS_DIR"
    
    echo ""
    echo "Analysis complete! Results saved in $ANALYSIS_DIR"
elif [ "$ANALYZE" = true ] && [ "$OUTPUT_FORMAT" = "json" ]; then
    echo ""
    echo "Note: Analysis is currently only supported for CSV output format."
    echo "JSON data was saved but no analysis was performed."
fi

echo ""
echo "==================================================="
echo "All done! You can find your data in:"
echo "Raw data: $CSV_FILE"
if [ "$ANALYZE" = true ]; then
    echo "Analysis: $ANALYSIS_DIR"
fi
echo "==================================================="