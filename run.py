#!/usr/bin/env python3
"""
ROFR Scraper Runner

This script provides a convenient way to run both the scraper and analyzer
with a single command, with sensible defaults.
"""

import os
import sys
import argparse
import subprocess
import datetime
from pathlib import Path

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run ROFR scraper and analyzer with one command"
    )
    
    parser.add_argument(
        "--url", "-u", 
        type=str,
        help="Specific DisBoards thread URL to scrape"
    )
    
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default="data",
        help="Directory to save output files (default: data)"
    )
    
    parser.add_argument(
        "--current-thread", "-c",
        type=str,
        help="Current ROFR thread URL to extract all past thread URLs from"
    )
    
    parser.add_argument(
        "--start-date", "-s",
        type=str,
        help="Start date for filtering data (MM/YYYY format, e.g., 01/2023)"
    )
    
    parser.add_argument(
        "--delay", "-d",
        type=float,
        default=1.0,
        help="Delay between requests in seconds (default: 1.0)"
    )
    
    parser.add_argument(
        "--max-pages", "-m",
        type=int,
        default=100,
        help="Maximum pages to scrape per thread (default: 100)"
    )
    
    parser.add_argument(
        "--skip-analysis", "-s",
        action="store_true",
        help="Skip the analysis step"
    )
    
    parser.add_argument(
        "--resort", "-r",
        type=str,
        help="Analyze specific resort only"
    )
    
    parser.add_argument(
        "--docker", 
        action="store_true",
        help="Use Docker instead of direct execution"
    )
    
    return parser.parse_args()

def ensure_directory(directory):
    """Ensure directory exists."""
    Path(directory).mkdir(parents=True, exist_ok=True)
    return directory

def run_command(cmd, shell=False):
    """Run a command with proper error handling."""
    try:
        print(f"Running: {' '.join(cmd) if not shell else cmd}")
        result = subprocess.run(
            cmd,
            shell=shell,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print(f"Command output: {e.stdout}")
        print(f"Command error: {e.stderr}")
        return False

def run_with_pipenv(args):
    """Run commands using Pipenv."""
    # Prepare directories and files
    data_dir = ensure_directory(args.output_dir)
    analysis_dir = ensure_directory(os.path.join(data_dir, "analysis"))
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Set up file paths
    csv_file = os.path.join(data_dir, f"rofr_data_{timestamp}.csv")
    
    # Build scraper command
    scraper_cmd = ["pipenv", "run", "python", "rofr_scraper.py"]
    scraper_cmd.extend(["--output", csv_file])
    scraper_cmd.extend(["--delay", str(args.delay)])
    scraper_cmd.extend(["--max-pages", str(args.max_pages)])
    
    if args.current_thread:
        scraper_cmd.extend(["--current-thread", args.current_thread])
        
    if args.start_date:
        scraper_cmd.extend(["--start-date", args.start_date])
    
    if args.url:
        scraper_cmd.extend(["--urls", args.url])
    
    # Run scraper
    if not run_command(scraper_cmd):
        print("Scraper failed. Exiting.")
        return False
    
    # Skip analysis if requested
    if args.skip_analysis:
        print(f"Scraping complete. Results saved to {csv_file}")
        print("Analysis skipped as requested.")
        return True
    
    # Build analyzer command
    analyzer_cmd = ["pipenv", "run", "python", "analyze_rofr_data.py", csv_file]
    analyzer_cmd.extend(["--output-dir", analysis_dir])
    
    if args.resort:
        analyzer_cmd.extend(["--resort", args.resort])
    
    # Run analyzer
    if not run_command(analyzer_cmd):
        print("Analyzer failed. Scraping was successful, but analysis failed.")
        return False
    
    print(f"Scraping and analysis complete!")
    print(f"Data saved to: {csv_file}")
    print(f"Analysis results saved to: {analysis_dir}")
    return True

def run_with_docker(args):
    """Run commands using Docker."""
    # Prepare directories and files
    data_dir = ensure_directory(args.output_dir)
    analysis_dir = ensure_directory(os.path.join(data_dir, "analysis"))
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Set up file paths
    csv_file = f"rofr_data_{timestamp}.csv"
    csv_path = os.path.join(data_dir, csv_file)
    
    # Print start date if provided
    if args.start_date:
        print(f"Filtering data from {args.start_date} onwards")
    
    # Ensure Docker image is built
    build_cmd = ["docker", "build", "-t", "rofr-scraper", "."]
    if not run_command(build_cmd):
        print("Docker build failed. Exiting.")
        return False
    
    # Build scraper command
    abs_data_dir = os.path.abspath(data_dir)
    scraper_cmd = ["docker", "run", "-v", f"{abs_data_dir}:/data", "rofr-scraper", "rofr_scraper.py"]
    scraper_cmd.extend(["--output", f"/data/{csv_file}"])
    scraper_cmd.extend(["--delay", str(args.delay)])
    scraper_cmd.extend(["--max-pages", str(args.max_pages)])
    
    if args.current_thread:
        scraper_cmd.extend(["--current-thread", args.current_thread])
    
    if args.start_date:
        scraper_cmd.extend(["--start-date", args.start_date])
    
    if args.url:
        scraper_cmd.extend(["--urls", args.url])
    
    # Run scraper
    if not run_command(scraper_cmd):
        print("Scraper failed. Exiting.")
        return False
    
    # Skip analysis if requested
    if args.skip_analysis:
        print(f"Scraping complete. Results saved to {csv_path}")
        print("Analysis skipped as requested.")
        return True
    
    # Build analyzer command
    abs_analysis_dir = os.path.abspath(analysis_dir)
    analyzer_cmd = ["docker", "run", "-v", f"{abs_data_dir}:/data", "rofr-scraper", "analyze_rofr_data.py", f"/data/{csv_file}"]
    analyzer_cmd.extend(["--output-dir", f"/data/analysis"])
    
    if args.resort:
        analyzer_cmd.extend(["--resort", args.resort])
    
    # Run analyzer
    if not run_command(analyzer_cmd):
        print("Analyzer failed. Scraping was successful, but analysis failed.")
        return False
    
    print(f"Scraping and analysis complete!")
    print(f"Data saved to: {csv_path}")
    print(f"Analysis results saved to: {analysis_dir}")
    return True

def main():
    """Main entry point for the script."""
    args = parse_args()
    
    if args.docker:
        return run_with_docker(args)
    else:
        return run_with_pipenv(args)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)