#!/usr/bin/env python3
"""
ROFR Scraper for DisBoards DVC Threads

This script scrapes ROFR (Right of First Refusal) data from Disney Vacation Club
forum threads on disboards.com.

The script looks for data strings in the following format:
DISname---$Price per point-$Total cost-# of points-Home resort-Use Year-Points by year- sent date, passed/taken date

Example:
pangyal---$144-$33296-219-VGF-Aug-113/14, 219/15, 219/16, 219/17- sent 8/24, passed 9/16
"""

import re
import csv
import json
import time
import argparse
import datetime
import calendar
from datetime import date
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from typing import List, Dict, Tuple, Optional, Any, Union


class ROFRScraper:
    """Scraper for ROFR threads on disboards.com"""

    BASE_URL = "https://www.disboards.com/"

    # Regex pattern to match ROFR data strings
    ROFR_PATTERN = r'([A-Za-z0-9_\-]+)---\$(\d+(?:\.\d+)?)(?:-\$(\d+(?:\.\d+)?))?-(\d+)-([A-Z@]+)-([A-Za-z]+)(?:-([^-]*))?- sent (\d+/\d+)(?:, (passed|taken) (\d+/\d+))?'

    # Regex pattern to extract date ranges from ROFR thread links
    THREAD_DATE_PATTERN = r'(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})[-\s]+(?:to[-\s]+)?(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})'

    # Alternative pattern for single year format like "April to June 2025"
    THREAD_DATE_PATTERN_SINGLE_YEAR = r'(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(?:\s+to\s+|\s+[-\s]+\s*)(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})'

    # Month name to number mapping
    MONTH_MAP = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12,
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
        'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'sept': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }

    def __init__(self, output_file: str = "rofr_data.csv", delay: float = 1.0, max_pages: int = 100,
                 start_date: Optional[date] = None, output_format: str = "csv"):
        """
        Initialize the scraper.

        Args:
            output_file: Path to save data
            delay: Delay between requests in seconds
            max_pages: Maximum number of pages to scrape per thread
            start_date: Optional start date filter
            output_format: Format to save data (csv or json)
        """
        self.output_file = output_file
        self.delay = delay
        self.max_pages = max_pages
        self.start_date = start_date
        self.output_format = output_format.lower()
        if self.output_format not in ['csv', 'json']:
            raise ValueError("Output format must be 'csv' or 'json'")
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def get_current_thread_url(self) -> Optional[str]:
        """
        Automatically detect the current ROFR thread URL by searching the DVC forum.

        Returns:
            URL of the current ROFR thread or None if not found
        """
        forum_url = "https://www.disboards.com/forums/purchasing-dvc.28/"

        try:
            print(f"Fetching current thread URL from DVC forum...")
            response = self.session.get(forum_url)
            if response.status_code != 200:
                print(f"Failed to fetch forum page: {response.status_code}")
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for sticky/pinned threads first, then regular threads
            selectors = [
                '.structItem--sticky .structItem-title a',  # Sticky threads
                '.structItem-title a',  # All thread titles
                'h3 a',  # Alternative structure
                'a[href*="/threads/"]'  # Any thread links
            ]

            for selector in selectors:
                links = soup.select(selector)
                if links:
                    print(f"Found {len(links)} threads using selector: {selector}")

                    for link in links:
                        href = link.get('href')
                        title = link.get_text().strip()

                        # Look for current ROFR thread (should be recent year and contain ROFR Thread)
                        if (href and title and
                            'ROFR Thread' in title and
                            'Not ROFR' not in title and
                            'INSTRUCTIONS' in title.upper()):

                            # Make sure URL is absolute
                            full_url = urljoin(self.BASE_URL, href).rstrip('/')
                            print(f"Found current thread: {title}")
                            print(f"URL: {full_url}")
                            return full_url
                    break

            print("No current ROFR thread found in forum")
            return None

        except Exception as e:
            print(f"Error fetching current thread URL: {e}")
            return None

    def extract_thread_urls_from_first_post(self, current_thread_url: str) -> List[Dict[str, Any]]:
        """
        Extract all ROFR thread URLs from the first post of the current thread.

        Args:
            current_thread_url: URL of the current ROFR thread

        Returns:
            List of dictionaries containing thread URLs and their date ranges
        """
        print(f"Extracting thread URLs from first post of {current_thread_url}")

        thread_info = []

        try:
            # Fetch the current thread
            response = self.session.get(current_thread_url)
            if response.status_code != 200:
                print(f"Failed to fetch thread: {response.status_code}")
                return thread_info

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find the first post
            first_post = soup.select_one('article.message--post')
            if not first_post:
                print("Could not find the first post")
                return thread_info

            # Find all links in the first post
            links = first_post.select('.bbWrapper a')

            # Process each link to identify ROFR thread links
            for link in links:
                href = link.get('href')
                link_text = link.get_text()

                # Skip links without href or text
                if not href or not link_text:
                    continue

                # Check if link contains ROFR-related keywords
                rofr_keywords = ['rofr', 'right of first refusal']
                if any(keyword in link_text.lower() for keyword in rofr_keywords) or any(keyword in href.lower() for keyword in rofr_keywords):
                    # Extract date information from link text
                    date_match = re.search(self.THREAD_DATE_PATTERN, link_text, re.IGNORECASE)
                    start_year = end_year = None

                    if date_match:
                        # Extract years from date range
                        start_year, end_year = date_match.groups()
                        start_year = int(start_year) if start_year else None
                        end_year = int(end_year) if end_year else None
                    else:
                        # Try single year pattern like "April to June 2025"
                        single_year_match = re.search(self.THREAD_DATE_PATTERN_SINGLE_YEAR, link_text, re.IGNORECASE)
                        if single_year_match:
                            year = int(single_year_match.group(1))
                            start_year = end_year = year
                        else:
                            # Try to extract years from alternative formats
                            years = re.findall(r'\b(20\d\d)\b', link_text)
                            if len(years) >= 1:
                                start_year = int(years[0])
                                end_year = int(years[-1]) if len(years) > 1 else start_year

                    # Extract months if available
                    months = re.findall(r'\b(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\b', link_text, re.IGNORECASE)
                    start_month = months[0] if months else None
                    end_month = months[-1] if len(months) > 1 else start_month

                    # Make sure URL is absolute and doesn't have trailing slashes
                    full_url = urljoin(self.BASE_URL, href).rstrip('/')

                    # Create thread date object for filtering
                    thread_start_date = None
                    thread_end_date = None
                    if start_year and start_month:
                        try:
                            start_month_num = self.MONTH_MAP.get(start_month.lower(), 1)
                            thread_start_date = date(int(start_year), start_month_num, 1)
                            
                            # Calculate end date if we have end month
                            if end_month and end_year:
                                end_month_num = self.MONTH_MAP.get(end_month.lower(), 12)
                                last_day = calendar.monthrange(int(end_year), end_month_num)[1]
                                thread_end_date = date(int(end_year), end_month_num, last_day)
                        except (ValueError, TypeError):
                            pass

                    thread_info.append({
                        'url': full_url,
                        'link_text': link_text,
                        'start_year': start_year,
                        'end_year': end_year,
                        'start_month': start_month,
                        'end_month': end_month,
                        'thread_start_date': thread_start_date,
                        'thread_end_date': thread_end_date
                    })

                    print(f"Found ROFR thread: {link_text} -> {full_url}")

            # Also add the current thread to the list
            current_title = soup.select_one('h1.p-title-value')
            if current_title:
                title_text = current_title.get_text()
                date_match = re.search(self.THREAD_DATE_PATTERN, title_text, re.IGNORECASE)
                start_year = end_year = None

                if date_match:
                    start_year, end_year = date_match.groups()
                    start_year = int(start_year) if start_year else None
                    end_year = int(end_year) if end_year else None
                else:
                    # Try single year pattern like "April to June 2025"
                    single_year_match = re.search(self.THREAD_DATE_PATTERN_SINGLE_YEAR, title_text, re.IGNORECASE)
                    if single_year_match:
                        year = int(single_year_match.group(1))
                        start_year = end_year = year

                months = re.findall(r'\b(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\b', title_text, re.IGNORECASE)
                start_month = months[0] if months else None
                end_month = months[-1] if len(months) > 1 else start_month

                # Create thread date object for filtering
                thread_start_date = None
                thread_end_date = None
                if start_year and start_month:
                    try:
                        start_month_num = self.MONTH_MAP.get(start_month.lower(), 1)
                        thread_start_date = date(int(start_year), start_month_num, 1)
                        
                        # Calculate end date if we have end month
                        if end_month and end_year:
                            end_month_num = self.MONTH_MAP.get(end_month.lower(), 12)
                            last_day = calendar.monthrange(int(end_year), end_month_num)[1]
                            thread_end_date = date(int(end_year), end_month_num, last_day)
                    except (ValueError, TypeError):
                        pass

                thread_info.append({
                    'url': current_thread_url,
                    'link_text': title_text,
                    'start_year': start_year,
                    'end_year': end_year,
                    'start_month': start_month,
                    'end_month': end_month,
                    'thread_start_date': thread_start_date,
                    'thread_end_date': thread_end_date
                })

                print(f"Added current thread: {title_text} -> {current_thread_url}")

        except Exception as e:
            print(f"Error extracting thread URLs: {e}")

        return thread_info

    def scrape_thread(self, thread_url: str) -> List[Dict[str, Any]]:
        """
        Scrape ROFR data from a thread.

        Args:
            thread_url: URL of the thread to scrape

        Returns:
            List of parsed ROFR data entries
        """
        all_entries = []
        page = 1
        thread_year = None

        while page <= self.max_pages:
            # Fix the URL to avoid double slashes by ensuring the thread_url doesn't end with a slash
            base_url = thread_url.rstrip('/')
            page_url = f"{base_url}/page-{page}" if page > 1 else thread_url
            print(f"Scraping {page_url}")

            try:
                response = self.session.get(page_url)
                if response.status_code != 200:
                    print(f"Failed to fetch page {page}: {response.status_code}")
                    break

                soup = BeautifulSoup(response.text, 'html.parser')

                # Extract thread date range from title on first page
                if page == 1 and thread_year is None:
                    title_element = soup.select_one('h1.p-title-value')
                    if title_element:
                        title_text = title_element.get_text()

                        # Extract date range from thread title
                        date_match = re.search(self.THREAD_DATE_PATTERN, title_text, re.IGNORECASE)
                        if date_match:
                            start_year, end_year = date_match.groups()
                            thread_year = int(start_year) if start_year else None
                            print(f"Thread year detected from date pattern: {thread_year}")
                        else:
                            # Fallback to extracting years
                            years = re.findall(r'\b(20\d\d)\b', title_text)
                            if years:
                                thread_year = int(years[0])
                                print(f"Thread year detected: {thread_year}")

                        # Extract months for date range validation
                        months = re.findall(r'\b(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\b', title_text, re.IGNORECASE)
                        if len(months) >= 1 and thread_year:
                            start_month = months[0]
                            end_month = months[-1] if len(months) > 1 else start_month

                            try:
                                start_month_num = self.MONTH_MAP.get(start_month.lower(), 1)
                                end_month_num = self.MONTH_MAP.get(end_month.lower(), 12)
                                thread_start_date = date(thread_year, start_month_num, 1)

                                # Get last day of the end month
                                last_day = calendar.monthrange(thread_year, end_month_num)[1]
                                thread_end_date = date(thread_year, end_month_num, last_day)

                                print(f"Thread date range: {thread_start_date} to {thread_end_date}")
                            except (ValueError, TypeError):
                                pass

                # Check if this is the last page
                next_page = soup.select_one('a.pageNav-jump--next')
                if not next_page:
                    print(f"Reached last page: {page}")

                # Find all posts
                posts = soup.select('article.message-body .bbWrapper')
                if not posts:
                    print(f"No posts found on page {page}")
                    break

                # Extract ROFR data from posts
                for post in posts:
                    post_text = post.get_text()
                    entries = self._parse_rofr_data(post_text, thread_year, thread_start_date, thread_end_date)

                    # Add thread URL to each entry for reference
                    for entry in entries:
                        entry['thread_url'] = thread_url

                    all_entries.extend(entries)

                # Check if we're on the last page
                if not next_page:
                    break

                page += 1
                time.sleep(self.delay)

            except Exception as e:
                print(f"Error scraping page {page}: {e}")
                break

        print(f"Found {len(all_entries)} ROFR entries in thread {thread_url}")
        return all_entries

    def _parse_date(self, date_str: str) -> Optional[date]:
        """
        Parse a date string in MM/YY format to a date object.

        Args:
            date_str: Date string in MM/YY format (e.g., "8/24")

        Returns:
            Date object or None if parsing fails
        """
        if not date_str:
            return None

        try:
            parts = date_str.split('/')
            if len(parts) != 2:
                return None

            month = int(parts[0])
            year = int(parts[1])

            # Assume 20xx for two-digit years
            if year < 100:
                if year < 50:  # Arbitrary cutoff
                    year += 2000
                else:
                    year += 1900

            return date(year, month, 1)  # Use first day of month as we don't have the exact day
        except (ValueError, IndexError):
            return None

    def _parse_date_with_year(self, date_str: str, thread_year: Optional[int]) -> Optional[date]:
        """
        Parse a date string in MM/DD format using thread year context.

        Args:
            date_str: Date string in MM/DD format (e.g., "8/24")
            thread_year: Year from thread title to use for date parsing

        Returns:
            Date object or None if parsing fails
        """
        if not date_str:
            return None

        try:
            parts = date_str.split('/')
            if len(parts) != 2:
                return None

            month = int(parts[0])
            day = int(parts[1])

            # Use thread year if available, otherwise fall back to current year
            if thread_year:
                year = thread_year
            else:
                year = datetime.datetime.now().year

            return date(year, month, day)
        except (ValueError, IndexError):
            return None


    def _format_date(self, date_obj: Optional[date]) -> Optional[str]:
        """
        Format a date object as YYYY-MM-DD string.

        Args:
            date_obj: Date object to format

        Returns:
            Formatted date string or None if date_obj is None
        """
        if date_obj is None:
            return None

        return date_obj.strftime('%Y-%m-%d')

    def _get_adjusted_thread_start_date(self, thread_start_date: date) -> date:
        """
        Calculate the adjusted thread start date allowing sent dates up to 3 months before.
        
        Args:
            thread_start_date: Original thread start date
            
        Returns:
            Adjusted start date (3 months earlier)
        """
        # Calculate 3 months before the thread start date
        year = thread_start_date.year
        month = thread_start_date.month - 3
        day = thread_start_date.day
        
        # Handle year rollover
        while month <= 0:
            month += 12
            year -= 1
        
        # Handle day overflow for months with fewer days
        try:
            return date(year, month, day)
        except ValueError:
            # If the day doesn't exist in the target month, use the last day of that month
            import calendar
            last_day = calendar.monthrange(year, month)[1]
            return date(year, month, last_day)

    def _parse_rofr_data(self, text: str, thread_year: Optional[int] = None,
                        thread_start_date: Optional[date] = None,
                        thread_end_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """
        Parse ROFR data strings from text.

        Args:
            text: Text content to parse
            thread_year: Year extracted from thread title for proper date parsing
            thread_start_date: Start date of the thread for validation
            thread_end_date: End date of the thread for validation

        Returns:
            List of parsed ROFR data entries
        """
        entries = []
        matches = re.finditer(self.ROFR_PATTERN, text, re.MULTILINE)

        for match in matches:
            try:
                username, price_per_point, total_cost, points, resort, use_year, points_details, sent_date, result, result_date = match.groups()

                # Clean up the data
                if total_cost is None:
                    total_cost = ""

                # Some entries may have variations in the format
                if points_details is None:
                    points_details = ""

                # Parse the sent date with thread year context
                parsed_sent_date = self._parse_date_with_year(sent_date.strip(), thread_year)

                # Skip this entry if it's before the start date
                if self.start_date and parsed_sent_date and parsed_sent_date < self.start_date:
                    continue

                # Parse the result date with thread year context and handle year rollover
                parsed_result_date = None
                if result_date:
                    parsed_result_date = self._parse_date_with_year(result_date.strip(), thread_year)
                    # If result date month is less than sent date month, it's likely the next year
                    if (parsed_result_date and parsed_sent_date and
                        parsed_result_date.month < parsed_sent_date.month):
                        parsed_result_date = parsed_result_date.replace(year=parsed_result_date.year + 1)

                # Validate that either sent date or result date is within thread date range (allow up to 3 months before start)
                if thread_start_date and thread_end_date:
                    adjusted_start_date = self._get_adjusted_thread_start_date(thread_start_date)
                    sent_date_in_range = (parsed_sent_date and 
                                        adjusted_start_date <= parsed_sent_date <= thread_end_date)
                    result_date_in_range = (parsed_result_date and 
                                          adjusted_start_date <= parsed_result_date <= thread_end_date)
                    
                    if not (sent_date_in_range or result_date_in_range):
                        print(f"Dropping entry for user {username}: neither sent date {parsed_sent_date} nor result date {parsed_result_date} is within thread range {adjusted_start_date} to {thread_end_date}")
                        continue

                # Format dates as YYYY-MM-DD strings
                formatted_sent_date = self._format_date(parsed_sent_date)
                formatted_result_date = self._format_date(parsed_result_date)

                entry = {
                    'username': username.strip(),
                    'price_per_point': float(price_per_point),
                    'total_cost': float(total_cost) if total_cost and total_cost.strip() else None,
                    'points': int(points),
                    'resort': resort.strip(),
                    'use_year': use_year.strip(),
                    'points_details': points_details.strip(),
                    'sent_date': formatted_sent_date,  # YYYY-MM-DD format
                    'result': result.strip() if result else 'pending',
                    'result_date': formatted_result_date,  # YYYY-MM-DD format
                    'raw_entry': match.group(0)
                }
                entries.append(entry)
            except Exception as e:
                print(f"Error parsing entry: {match.group(0)}")
                print(f"Error details: {e}")

        return entries
    
    def _deduplicate_entries(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate entries, keeping the most recent status.
        
        Handles two cases:
        1. Quoted entries (exact duplicates from people quoting previous messages)
        2. Status updates (same entry with different result status)
        
        Priority order for results: taken > passed > pending
        
        Args:
            entries: List of ROFR data entries
            
        Returns:
            Deduplicated list of entries
        """
        if not entries:
            return entries
        
        # Create a unique key for each entry (excluding result and result_date)
        def create_entry_key(entry):
            return (
                entry['username'].lower(),
                entry['price_per_point'],
                entry['total_cost'],
                entry['points'],
                entry['resort'],
                entry['use_year'],
                entry['sent_date']  # Use formatted date
            )
        
        # Priority mapping for results
        result_priority = {
            'taken': 3,
            'passed': 2,
            'pending': 1
        }
        
        # Group entries by unique key
        entry_groups = {}
        for entry in entries:
            key = create_entry_key(entry)
            if key not in entry_groups:
                entry_groups[key] = []
            entry_groups[key].append(entry)
        
        deduplicated = []
        for key, group in entry_groups.items():
            if len(group) == 1:
                # No duplicates, keep the entry
                deduplicated.append(group[0])
            else:
                # Multiple entries, keep the one with highest priority status
                best_entry = max(group, key=lambda x: result_priority.get(x['result'], 0))
                deduplicated.append(best_entry)
                
                # Log what was deduplicated
                statuses = [entry['result'] for entry in group]
                print(f"Deduplicated {len(group)} entries for {group[0]['username']} "
                      f"(statuses: {', '.join(statuses)}) -> keeping '{best_entry['result']}'")
        
        original_count = len(entries)
        final_count = len(deduplicated)
        if original_count != final_count:
            print(f"Deduplication: {original_count} entries -> {final_count} entries ({original_count - final_count} duplicates removed)")
        
        return deduplicated

    def save_data(self, entries: List[Dict[str, Any]]) -> None:
        """
        Save ROFR data to file in the specified format (CSV or JSON).

        Args:
            entries: List of ROFR data entries
        """
        if not entries:
            print("No entries to save")
            return

        # Deduplicate entries before saving
        deduplicated_entries = self._deduplicate_entries(entries)

        if self.output_format == 'csv':
            self._save_to_csv(deduplicated_entries)
        else:  # json
            self._save_to_json(deduplicated_entries)
            
        print(f"Saved {len(deduplicated_entries)} entries to {self.output_file}")

    def _save_to_csv(self, entries: List[Dict[str, Any]]) -> None:
        """
        Save ROFR data to CSV file.

        Args:
            entries: List of ROFR data entries
        """
        fieldnames = [
            'username', 'price_per_point', 'total_cost', 'points', 'resort',
            'use_year', 'points_details', 'sent_date',
            'result', 'result_date',
            'thread_url', 'raw_entry'
        ]

        with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(entries)

    def _save_to_json(self, entries: List[Dict[str, Any]]) -> None:
        """
        Save ROFR data to JSON file.

        Args:
            entries: List of ROFR data entries
        """
        # Create a serializable version of the data
        serializable_entries = []
        for entry in entries:
            # Create a copy of the entry without parsed_sent_date which isn't JSON serializable
            serializable_entry = {k: v for k, v in entry.items() if k != 'parsed_sent_date'}
            serializable_entries.append(serializable_entry)

        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'count': len(entries),
                    'generated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'scraper_version': '1.1.0'
                },
                'entries': serializable_entries
            }, f, indent=2)

    def run(self, current_thread_url: Optional[str] = None, specific_urls: Optional[List[str]] = None, auto_detect_current: bool = False) -> List[Dict[str, Any]]:
        """
        Run the scraper.

        Args:
            current_thread_url: URL of the current ROFR thread (to extract past thread URLs)
            specific_urls: List of specific thread URLs to scrape (optional)
            auto_detect_current: Whether to automatically detect the current thread URL

        Returns:
            List of ROFR data entries
        """
        all_entries = []
        thread_urls = []

        # Auto-detect current thread URL if requested and no URL provided
        if auto_detect_current and not current_thread_url and not specific_urls:
            current_thread_url = self.get_current_thread_url()
            if not current_thread_url:
                print("Failed to auto-detect current thread URL. Exiting.")
                return []

        # If a current thread URL is provided, extract past thread URLs from it
        if current_thread_url:
            # Ensure URL doesn't have trailing slashes
            clean_url = current_thread_url.rstrip('/')
            thread_info = self.extract_thread_urls_from_first_post(clean_url)

            # Filter threads by date if start_date is provided
            if self.start_date:
                filtered_thread_info = []
                for info in thread_info:
                    # Include threads that overlap with or extend past the start date
                    if info['thread_start_date']:
                        # If we have an end date, check if the thread range overlaps with start_date
                        if info['thread_end_date']:
                            # Thread overlaps if: thread_end_date >= start_date
                            if info['thread_end_date'] >= self.start_date:
                                filtered_thread_info.append(info)
                            else:
                                print(f"Skipping thread {info['link_text']} (before start date)")
                        # If no end date, fall back to checking start date
                        elif info['thread_start_date'] >= self.start_date:
                            filtered_thread_info.append(info)
                        else:
                            print(f"Skipping thread {info['link_text']} (before start date)")
                    else:
                        print(f"Skipping thread {info['link_text']} (unknown date)")
                thread_urls = [info['url'] for info in filtered_thread_info]
            else:
                thread_urls = [info['url'] for info in thread_info]

        # If specific URLs are provided, use those instead or add them to the list
        if specific_urls:
            if not thread_urls:
                # Clean any trailing slashes from specific URLs
                thread_urls = [url.rstrip('/') for url in specific_urls]
            else:
                # Add any specific URLs that aren't already in the list
                for url in specific_urls:
                    clean_url = url.rstrip('/')
                    if clean_url not in thread_urls:
                        thread_urls.append(clean_url)

        # Make sure we have at least one thread to scrape
        if not thread_urls:
            print("No thread URLs found or provided. Exiting.")
            return

        print(f"Will scrape {len(thread_urls)} ROFR threads")

        # Scrape each thread
        for url in thread_urls:
            entries = self.scrape_thread(url)
            all_entries.extend(entries)
            time.sleep(self.delay * 2)  # Longer delay between threads

        # Save the data
        self.save_data(all_entries)
        print(f"Scraped a total of {len(all_entries)} ROFR entries from {len(thread_urls)} threads")

        return all_entries


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Scrape ROFR data from DisBoards')
    parser.add_argument('--output', '-o', type=str, default='rofr_data.csv',
                      help='Output file (default: rofr_data.csv)')
    parser.add_argument('--format', '-f', type=str, choices=['csv', 'json'], default='csv',
                      help='Output format (csv or json, default: csv)')
    parser.add_argument('--delay', '-d', type=float, default=1.0,
                      help='Delay between requests in seconds (default: 1.0)')
    parser.add_argument('--max-pages', '-m', type=int, default=100,
                      help='Maximum pages to scrape per thread (default: 100)')
    parser.add_argument('--current-thread', '-c', type=str,
                      help='Current ROFR thread URL to extract past thread URLs from')
    parser.add_argument('--urls', '-u', type=str, nargs='+',
                      help='Specific thread URLs to scrape')
    parser.add_argument('--auto-detect', '-a', action='store_true',
                      help='Automatically detect the current ROFR thread URL')
    parser.add_argument('--start-date', '-s', type=str,
                      help='Start date for filtering data (MM/YYYY format, e.g., 01/2023)')

    args = parser.parse_args()

    # Parse start date if provided
    start_date = None
    if args.start_date:
        try:
            month, year = args.start_date.split('/')
            start_date = date(int(year), int(month), 1)
            print(f"Filtering data from {start_date.strftime('%B %Y')} onwards")
        except (ValueError, IndexError):
            print(f"Warning: Invalid start date format '{args.start_date}'. Expected MM/YYYY (e.g., 01/2023)")

    scraper = ROFRScraper(
        output_file=args.output,
        delay=args.delay,
        max_pages=args.max_pages,
        start_date=start_date,
        output_format=args.format
    )

    scraper.run(
        current_thread_url=args.current_thread,
        specific_urls=args.urls,
        auto_detect_current=args.auto_detect
    )


if __name__ == "__main__":
    main()
