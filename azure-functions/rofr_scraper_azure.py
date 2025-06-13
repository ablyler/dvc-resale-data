#!/usr/bin/env python3
"""
ROFR Scraper for Azure Functions with Table Storage

Azure-optimized version of the ROFR scraper that uses Azure Table Storage
instead of SQLite and is designed to run in Azure Functions.
"""

import re
import os
import time
import logging
import hashlib
import calendar
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from models import ROFREntry, ThreadInfo
from table_storage_manager import OptimizedAzureTableStorageManager
from statistics_calculator import StatisticsCalculator
from statistics_manager import StatisticsManager
from rofr_parsing_utils import ROFRParsingUtils


class AzureROFRScraper:
    """Azure Functions optimized ROFR scraper with Table Storage."""

    BASE_URL = "https://www.disboards.com/"

    # Regex patterns - improved to handle more entry variations including missing spaces
    ROFR_PATTERN = r'([A-Za-z0-9_\-\.\s\(\)]+?)---\s*\$(\d+(?:\.\d+)?)(?:-\$(\d+(?:\.\d+)?))?-(\d+)-([A-Z@()\s]+(?:@[A-Z]+)?(?:\s+[A-Za-z\s]+)?)-(?:([A-Za-z]+)-?)?\s*(.*?)-\s*sent (\d+/\d+(?:/\d{4})?)\s*(?:,\s*(passed|taken)\s+(\d+/\d+))?'
    THREAD_DATE_PATTERN = r'(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})[-\s]+(?:to[-\s]+)?(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})'
    THREAD_DATE_PATTERN_SINGLE_YEAR = r'(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(?:\s+to\s+|\s+[-\s]+\s*)(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})'

    MONTH_MAP = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12,
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
        'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'sept': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }

    def __init__(self,
                 connection_string: Optional[str] = None,
                 table_name: str = "rofrdata",
                 delay: float = 0.5,  # Reduced delay for faster processing
                 max_pages: Optional[int] = None,  # Will use environment variable if not specified
                 user_agent: Optional[str] = None,
                 batch_size: int = 25):  # Configurable batch size
        """Initialize the Azure ROFR scraper."""

        # Configuration
        self.delay = delay
        self.max_pages = max_pages if max_pages is not None else int(os.environ.get('SCRAPER_MAX_PAGES', '100'))
        self.batch_size = batch_size
        self.start_date = None

        # Setup logging
        self.logger = logging.getLogger(__name__)

        # Get connection string from environment if not provided
        if connection_string is None:
            connection_string = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
            if connection_string is None:
                raise ValueError("Azure Storage connection string must be provided either as parameter or AZURE_STORAGE_CONNECTION_STRING environment variable")

        # Initialize storage manager with optimized batch size
        self.storage = OptimizedAzureTableStorageManager(
            connection_string=connection_string
        )
        # Set batch size for optimized operations
        self.storage.batch_size = self.batch_size

        # Initialize statistics components
        self.stats_calculator = StatisticsCalculator()
        self.stats_manager = StatisticsManager(
            connection_string=connection_string,
            stats_table_name="stats"
        )

        # Setup HTTP session
        self.session = requests.Session()
        default_user_agent = os.environ.get(
            'SCRAPER_USER_AGENT',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        self.session.headers.update({'User-Agent': user_agent or default_user_agent})

        # Initialize parsing utilities
        self.parsing_utils = ROFRParsingUtils()

        # Log configuration for debugging missing entries issue
        self.logger.info(f"ROFR Scraper initialized with individual entry processing (batch operations disabled)")
        self.logger.info(f"Configuration: max_pages={self.max_pages}, delay={self.delay}s")
        self.logger.info("Using improved ROFR regex pattern to capture more entry variations")

    def get_current_thread_url(self) -> Optional[str]:
        """Auto-detect the current ROFR thread URL."""
        forum_url = "https://www.disboards.com/forums/purchasing-dvc.28/"

        try:
            self.logger.info("Fetching current thread URL from DVC forum...")
            response = self.session.get(forum_url, timeout=30)
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch forum page: {response.status_code}")
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            selectors = [
                '.structItem--sticky .structItem-title a',
                '.structItem-title a',
                'h3 a',
                'a[href*="/threads/"]'
            ]

            for selector in selectors:
                links = soup.select(selector)
                if links:
                    self.logger.debug(f"Found {len(links)} threads using selector: {selector}")

                    for link in links:
                        href = link.get('href')
                        title = link.get_text().strip()

                        if (href and title and
                            'ROFR Thread' in title and
                            'Not ROFR' not in title and
                            'INSTRUCTIONS' in title.upper()):

                            full_url = urljoin(self.BASE_URL, str(href)).rstrip('/')
                            self.logger.info(f"Found current thread: {title}")
                            self.logger.info(f"URL: {full_url}")
                            return full_url
                    break

            self.logger.warning("No current ROFR thread found in forum")
            return None

        except Exception as e:
            self.logger.error(f"Error fetching current thread URL: {e}")
            return None

    def extract_thread_urls_from_first_post(self, current_thread_url: str) -> List[ThreadInfo]:
        """Extract all ROFR thread URLs from the first post of the current thread."""
        self.logger.info(f"Extracting thread URLs from first post of {current_thread_url}")

        thread_infos = []

        try:
            response = self.session.get(current_thread_url, timeout=30)
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch thread: {response.status_code}")
                return thread_infos

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find the first post
            first_post = soup.select_one('article.message--post')
            if not first_post:
                self.logger.error("Could not find the first post")
                return thread_infos

            # Find all links in the first post
            links = first_post.select('.bbWrapper a')

            for link in links:
                href = link.get('href')
                link_text = link.get_text()

                if not href or not link_text:
                    continue

                # Convert href to string to avoid type issues
                href_str = str(href)
                link_text_str = str(link_text)

                # Check if link contains ROFR-related keywords
                rofr_keywords = ['rofr', 'right of first refusal']
                if any(keyword in link_text_str.lower() for keyword in rofr_keywords) or \
                   any(keyword in href_str.lower() for keyword in rofr_keywords):

                    thread_info = self._parse_thread_info(link_text_str, urljoin(self.BASE_URL, href_str).rstrip('/'))
                    if thread_info:
                        thread_infos.append(thread_info)
                        self.logger.debug(f"Found ROFR thread: {link_text} -> {thread_info.url}")

            # Add the current thread to the list
            current_title = soup.select_one('h1.p-title-value')
            if current_title:
                title_text = current_title.get_text().strip()
                thread_info = self._parse_thread_info(title_text, current_thread_url)
                if thread_info:
                    thread_infos.append(thread_info)
                    self.logger.debug(f"Added current thread: {title_text} -> {current_thread_url}")

        except Exception as e:
            self.logger.error(f"Error extracting thread URLs: {e}")

        return thread_infos

    def _parse_thread_info(self, title_text: str, url: str) -> Optional[ThreadInfo]:
        """Parse thread information from title text with improved validation."""
        # Validate URL is a valid ROFR thread
        if not self._is_valid_rofr_thread(url, title_text):
            self.logger.warning(f"Skipping invalid ROFR thread: {url}")
            return None

        # Extract date information from title text
        date_match = re.search(self.THREAD_DATE_PATTERN, title_text, re.IGNORECASE)
        start_year = end_year = None

        if date_match:
            start_year, end_year = date_match.groups()
            start_year = int(start_year) if start_year else None
            end_year = int(end_year) if end_year else None
        else:
            # Try single year pattern
            single_year_match = re.search(self.THREAD_DATE_PATTERN_SINGLE_YEAR, title_text, re.IGNORECASE)
            if single_year_match:
                year = single_year_match.group(1)
                start_year = end_year = int(year) if year else None
            else:
                # Extract any 4-digit years
                years = re.findall(r'\b(20\d{2})\b', title_text)
                if len(years) >= 1:
                    start_year = int(years[0])
                    end_year = int(years[-1]) if len(years) > 1 else start_year

        # Extract months with improved pattern
        months = re.findall(r'\b(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\b', title_text, re.IGNORECASE)
        start_month = months[0].title() if months else None
        end_month = months[-1].title() if len(months) > 1 else start_month

        # Ensure we have valid date components
        if not start_year:
            self.logger.warning(f"Could not extract year from thread title: {title_text}")
            # Use current year as fallback
            start_year = end_year = datetime.now().year

        if not start_month:
            self.logger.warning(f"Could not extract month from thread title: {title_text}")
            # Try to infer from thread URL or use generic fallback
            start_month = end_month = "Jan"

        # Create thread date objects
        thread_start_date = None
        thread_end_date = None
        if start_year and start_month:
            try:
                start_month_num = self.MONTH_MAP.get(start_month.lower(), 1)
                thread_start_date = date(int(start_year), start_month_num, 1)

                if end_month and end_year:
                    end_month_num = self.MONTH_MAP.get(end_month.lower(), 12)
                    last_day = calendar.monthrange(int(end_year), end_month_num)[1]
                    thread_end_date = date(int(end_year), end_month_num, last_day)
                else:
                    # If no end month/year, assume same as start
                    end_month = start_month
                    end_year = start_year
                    end_month_num = self.MONTH_MAP.get(end_month.lower(), 12)
                    last_day = calendar.monthrange(int(end_year), end_month_num)[1]
                    thread_end_date = date(int(end_year), end_month_num, last_day)
            except (ValueError, TypeError) as e:
                self.logger.error(f"Error calculating thread dates: {e}")

        return ThreadInfo(
            url=url,
            title=title_text,
            start_year=start_year,
            end_year=end_year,
            start_month=start_month,
            end_month=end_month,
            thread_start_date=thread_start_date,
            thread_end_date=thread_end_date
        )

    def determine_pages_to_scrape(self, thread_url: str) -> Tuple[int, int, int]:
        """
        Determine which pages need to be scraped for a thread.

        Returns:
            Tuple of (start_page, end_page, total_pages)
        """
        # Get thread info from storage
        thread_info = self.storage.get_thread_info(thread_url)
        last_scraped = thread_info['last_scraped_page'] if thread_info else 0

        # Debug logging for progress tracking
        if thread_info:
            self.logger.debug(f"Thread {thread_url} - Last scraped: {last_scraped}")
        else:
            self.logger.debug(f"Thread {thread_url} - Not found in storage, will start from page 1")

        # Get total pages by checking the first page
        response = self.session.get(thread_url, timeout=30)
        if response.status_code != 200:
            self.logger.error(f"Failed to fetch thread: {response.status_code}")
            return 1, 1, 1

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find total pages
        total_pages = 1
        page_nav = soup.select_one('.pageNav-main')
        if page_nav:
            page_links = page_nav.select('a')
            if page_links:
                try:
                    page_numbers = []
                    for link in page_links:
                        text = link.get_text().strip()
                        if text.isdigit():
                            page_numbers.append(int(text))
                    if page_numbers:
                        total_pages = max(page_numbers)
                except (ValueError, TypeError):
                    pass

        # Update total_pages in thread info as soon as we determine it
        # Get or create thread info to update
        existing_thread = self.storage.get_thread_info(thread_url)
        if existing_thread:
            # Create ThreadInfo from existing data and update total_pages
            updated_thread_info = ThreadInfo.from_table_entity(existing_thread)
            updated_thread_info.total_pages = total_pages
            self.storage.update_thread_info(updated_thread_info)




        # Determine start page
        if last_scraped == 0:
            # Never scraped before, start from page 1
            start_page = 1
        elif last_scraped >= total_pages:
            # Check last page for updates
            start_page = total_pages
        else:
            # Check for new pages
            start_page = last_scraped + 1

        end_page = min(total_pages, self.max_pages)

        # Log scraping plan
        if last_scraped == 0:
            self.logger.info(f"Thread pages - Total: {total_pages}, Last scraped: {last_scraped} (new thread), Will scrape: {start_page}-{end_page}")
        elif start_page > total_pages:
            self.logger.info(f"Thread pages - Total: {total_pages}, Last scraped: {last_scraped} (up to date)")
        elif start_page == total_pages:
            self.logger.info(f"Thread pages - Total: {total_pages}, Last scraped: {last_scraped}, Checking last page for updates: {start_page}")
        else:
            self.logger.info(f"Thread pages - Total: {total_pages}, Last scraped: {last_scraped}, Scraping new pages: {start_page}-{end_page}")

        return start_page, end_page, total_pages

    def _is_valid_rofr_thread(self, url: str, title: str = "") -> bool:
        """Check if a thread URL is a valid ROFR thread."""
        # Known invalid URLs
        invalid_urls = [
            'https://rofr.scubacat.net',
        ]

        if url in invalid_urls:
            return False

        # Valid DISBoards patterns
        valid_patterns = [
            r'https://www\.disboards\.com/.*',
            r'http://www\.disboards\.com/.*',
        ]

        # Check if URL matches valid DISBoards patterns
        for pattern in valid_patterns:
            if re.match(pattern, url, re.IGNORECASE):
                return True

        return False

    def get_total_pages(self, thread_url: str) -> int:
        """
        Get the total number of pages for a thread without determining scraping range.

        This is a simplified version of determine_pages_to_scrape that only returns
        the total page count, used for single page processing validation.

        Returns:
            Total number of pages in the thread
        """
        try:
            # Get total pages by checking the first page
            response = self.session.get(thread_url, timeout=30)
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch thread for page count: {response.status_code}")
                return 1

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find total pages
            total_pages = 1
            page_nav = soup.select_one('.pageNav-main')
            if page_nav:
                page_links = page_nav.select('a')
                if page_links:
                    try:
                        page_numbers = []
                        for link in page_links:
                            text = link.get_text().strip()
                            if text.isdigit():
                                page_numbers.append(int(text))
                        if page_numbers:
                            total_pages = max(page_numbers)
                    except (ValueError, TypeError):
                        pass

            self.logger.debug(f"Thread {thread_url} has {total_pages} total pages")
            return total_pages

        except Exception as e:
            self.logger.error(f"Error getting total pages for {thread_url}: {e}")
            return 1

    def get_next_page_to_scrape(self, thread_url: str) -> int:
        """
        Determine the next page that needs to be scraped for a thread.

        This method checks the last_scraped_page and returns the next page
        that should be processed, suitable for single-page processing.

        Returns:
            Page number to scrape next (1-based), or 0 if all pages are up to date
        """
        try:
            # Get thread info from storage
            thread_info = self.storage.get_thread_info(thread_url)
            last_scraped = thread_info['last_scraped_page'] if thread_info else 0

            # Get total pages
            total_pages = self.get_total_pages(thread_url)

            if last_scraped == 0:
                # Never scraped before, start from page 1
                next_page = 1
                self.logger.info(f"Thread {thread_url} - Never scraped, starting from page 1")
            elif last_scraped >= total_pages:
                # All pages have been scraped, but check the last page for updates
                next_page = total_pages
                self.logger.info(f"Thread {thread_url} - All pages scraped, checking last page {total_pages} for updates")
            else:
                # Continue from next unscraped page
                next_page = last_scraped + 1
                self.logger.info(f"Thread {thread_url} - Continuing from page {next_page} (last scraped: {last_scraped})")

            return next_page

        except Exception as e:
            self.logger.error(f"Error determining next page for {thread_url}: {e}")
            return 1  # Default to page 1 on error

    def scrape_thread(self, thread_info: ThreadInfo) -> Tuple[int, int]:
        """
        Scrape ROFR data from a thread.

        Returns:
            Tuple of (new_entries, updated_entries)
        """
        start_page, end_page, total_pages = self.determine_pages_to_scrape(thread_info.url)

        # Update thread info with correct total_pages before upserting
        thread_info.total_pages = total_pages
        self.storage.safe_upsert_thread(thread_info)

        if start_page > end_page:
            self.logger.info(f"No new pages to scrape for thread {thread_info.url} (already up to date)")
            return 0, 0

        new_entries = 0
        updated_entries = 0

        for page in range(start_page, end_page + 1):
            page_url = f"{thread_info.url}/page-{page}" if page > 1 else thread_info.url
            self.logger.debug(f"Scraping {page_url}")

            try:
                response = self.session.get(page_url, timeout=30)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, 'html.parser')

                # Parse ROFR entries from HTML using shared utilities
                page_entries = self.parsing_utils.parse_rofr_entries_from_html(
                    response.text, thread_info, page, self.start_date
                )

                # Process entries individually for better error visibility and tracking
                if page_entries:
                    page_new_entries = 0
                    page_updated_entries = 0

                    for entry in page_entries:
                        try:
                            was_new, was_updated = self.storage.upsert_entry(entry)
                            if was_new:
                                page_new_entries += 1
                            elif was_updated:
                                page_updated_entries += 1

                            # Log individual entry processing for debugging
                            self.logger.debug(f"Entry processed - {entry.username}: ${entry.price_per_point}/pt, {entry.points}pts, {entry.resort} {'(NEW)' if was_new else '(UPDATED)' if was_updated else '(UNCHANGED)'}")

                        except Exception as e:
                            self.logger.error(f"Failed to process entry {entry.username} (${entry.price_per_point}/pt, {entry.points}pts, {entry.resort}): {e}")
                            continue

                    new_entries += page_new_entries
                    updated_entries += page_updated_entries

                    self.logger.info(f"Page {page} processed: {len(page_entries)} entries found, {page_new_entries} new, {page_updated_entries} updated")

                # Check if this is the last page
                next_page = soup.select_one('a.pageNav-jump--next')
                is_last_page = not next_page

                # Update progress after successfully processing this page
                thread_info.last_scraped_page = page
                thread_info.total_pages = total_pages
                self.storage.update_thread_info(thread_info)
                self.logger.debug(f"Updated progress for thread to page {page}/{total_pages}")

                if is_last_page:
                    self.logger.debug(f"Reached last page {page} for thread {thread_info.url}")
                    break

                # Reduced delay between pages for faster processing
                time.sleep(self.delay * 0.5)

            except Exception as e:
                self.logger.error(f"Error scraping page {page}: {e}")
                # Still update progress for the last successfully processed page
                if page > start_page:
                    thread_info.last_scraped_page = page - 1
                    thread_info.total_pages = total_pages
                    self.storage.update_thread_info(thread_info)
                    self.logger.warning(f"Error occurred on page {page}, saved progress up to page {page - 1}")
                break

        # Log detailed summary statistics for the thread
        total_processed = new_entries + updated_entries
        self.logger.info(f"Thread '{thread_info.title}' completed:")
        self.logger.info(f"  - Pages processed: {start_page} to {end_page} (of {total_pages} total)")
        self.logger.info(f"  - Total entries processed: {total_processed}")
        self.logger.info(f"  - New entries: {new_entries}")
        self.logger.info(f"  - Updated entries: {updated_entries}")

        if total_processed == 0:
            self.logger.warning(f"  - WARNING: No entries processed for this thread - potential parsing issue")

        return new_entries, updated_entries

    def scrape_single_page(self, thread_info: ThreadInfo, page_number: int) -> Tuple[int, int, int]:
        """
        Scrape ROFR data from a single page of a thread.

        Args:
            thread_info: ThreadInfo object containing thread details
            page_number: Specific page number to scrape

        Returns:
            Tuple of (new_entries, updated_entries, total_pages)
        """
        # Get total pages for validation
        total_pages = self.get_total_pages(thread_info.url)

        # Update thread info with correct total_pages before upserting
        thread_info.total_pages = total_pages
        self.storage.safe_upsert_thread(thread_info)

        # total_pages already set and upserted above

        if page_number > total_pages:
            self.logger.warning(f"Requested page {page_number} exceeds total pages {total_pages} for thread {thread_info.url}")
            return 0, 0, total_pages

        # Check if this page might have already been processed
        thread_info_current = self.storage.get_thread_info(thread_info.url)
        last_scraped = thread_info_current['last_scraped_page'] if thread_info_current else 0

        if page_number <= last_scraped and page_number < total_pages:
            self.logger.info(f"Page {page_number} has already been scraped (last scraped: {last_scraped}), processing anyway for data consistency")

        new_entries = 0
        updated_entries = 0

        # Construct page URL
        page_url = f"{thread_info.url}/page-{page_number}" if page_number > 1 else thread_info.url
        self.logger.debug(f"Scraping single page: {page_url}")

        try:
            response = self.session.get(page_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Parse ROFR entries from HTML using shared utilities
            page_entries = self.parsing_utils.parse_rofr_entries_from_html(
                response.text, thread_info, page_number, self.start_date
            )

            # Process entries individually for better error visibility and tracking
            if page_entries:
                for entry in page_entries:
                    try:
                        was_new, was_updated = self.storage.upsert_entry(entry)
                        if was_new:
                            new_entries += 1
                        elif was_updated:
                            updated_entries += 1

                        # Log individual entry processing for debugging
                        self.logger.debug(f"Entry processed - {entry.username}: ${entry.price_per_point}/pt, {entry.points}pts, {entry.resort} {'(NEW)' if was_new else '(UPDATED)' if was_updated else '(UNCHANGED)'}")

                    except Exception as e:
                        self.logger.error(f"Failed to process entry {entry.username} (${entry.price_per_point}/pt, {entry.points}pts, {entry.resort}): {e}")
                        continue

                self.logger.info(f"Page {page_number} processed: {len(page_entries)} entries found, {new_entries} new, {updated_entries} updated")

            # Update progress after successfully processing this page
            thread_info.last_scraped_page = page_number
            thread_info.total_pages = total_pages
            self.storage.update_thread_info(thread_info)
            self.logger.debug(f"Updated progress for thread to page {page_number}/{total_pages}")

        except Exception as e:
            self.logger.error(f"Error scraping page {page_number}: {e}")
            raise

        # Log summary for this page
        self.logger.info(f"Single page processing completed for '{thread_info.title}' page {page_number}/{total_pages}")
        self.logger.info(f"  - New entries: {new_entries}")
        self.logger.info(f"  - Updated entries: {updated_entries}")

        return new_entries, updated_entries, total_pages

    def _parse_rofr_data(self, text: str, thread_info: ThreadInfo) -> List[ROFREntry]:
        """Parse ROFR data strings from text - legacy method for backward compatibility."""
        return self.parsing_utils.parse_rofr_entries_from_text(
            text, thread_info, 1, 0, None, None, self.start_date
        )

    def _get_adjusted_thread_start_date(self, thread_start_date: date) -> date:
        """Calculate adjusted thread start date (3 months earlier)."""
        year = thread_start_date.year
        month = thread_start_date.month - 3
        day = thread_start_date.day

        while month <= 0:
            month += 12
            year -= 1

        try:
            return date(year, month, day)
        except ValueError:
            last_day = calendar.monthrange(year, month)[1]
            return date(year, month, last_day)

    def run_scraping_session(self,
                           current_thread_url: Optional[str] = None,
                           auto_detect_current: bool = False,
                           start_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Run a complete scraping session.

        Returns:
            Dictionary with scraping statistics
        """
        # Set start date filter
        self.start_date = start_date

        # Start scrape session
        session_id = self.storage.start_scrape_session()

        total_threads = 0
        total_new_entries = 0
        total_updated_entries = 0

        try:
            # Get thread URLs
            thread_infos = []

            if auto_detect_current and not current_thread_url:
                current_thread_url = self.get_current_thread_url()
                if not current_thread_url:
                    raise Exception("Failed to auto-detect current thread URL")

            if current_thread_url:
                thread_infos = self.extract_thread_urls_from_first_post(current_thread_url)

                # Filter by start date if provided
                if start_date:
                    filtered_infos = []
                    for info in thread_infos:
                        if info.thread_end_date and info.thread_end_date >= start_date:
                            filtered_infos.append(info)
                            self.logger.debug(f"Including thread {info.title} (ends {info.thread_end_date})")
                        else:
                            self.logger.debug(f"Skipping thread {info.title} (too old)")
                    thread_infos = filtered_infos

            if not thread_infos:
                raise Exception("No thread URLs found or provided")

            self.logger.info(f"Will scrape {len(thread_infos)} ROFR threads")
            total_threads = len(thread_infos)

            # Scrape each thread
            for thread_info in thread_infos:
                self.logger.info(f"Processing thread: {thread_info.title}")

                # Scrape thread
                new_entries, updated_entries = self.scrape_thread(thread_info)
                total_new_entries += new_entries
                total_updated_entries += updated_entries

                time.sleep(self.delay)  # Reduced delay between threads

            # Update session
            self.storage.update_session_metadata(
                session_id,
                total_threads=total_threads,
                total_entries=total_new_entries + total_updated_entries,
                new_entries=total_new_entries,
                updated_entries=total_updated_entries,
                status='completed'
            )

            self.logger.info(f"Scraping completed: {total_new_entries} new, {total_updated_entries} updated entries from {total_threads} threads")

            # Calculate and store statistics after successful scraping
            stats_result = self._calculate_and_store_statistics()

            return {
                'session_id': session_id,
                'total_threads': total_threads,
                'new_entries': total_new_entries,
                'updated_entries': total_updated_entries,
                'total_entries': total_new_entries + total_updated_entries,
                'status': 'completed',
                'statistics_updated': stats_result
            }

        except Exception as e:
            self.logger.error(f"Scraping failed: {e}")
            self.storage.update_session_metadata(
                session_id,
                status='failed',
                error_message=str(e)
            )
            raise

    def run_scrape(self, current_thread_url: Optional[str] = None, auto_detect_current: bool = True):
        """Alias for run_scraping_session to maintain compatibility."""
        return self.run_scraping_session(current_thread_url=current_thread_url, auto_detect_current=auto_detect_current)

    def _calculate_and_store_statistics(self) -> bool:
        """Calculate and store comprehensive statistics after scraping."""
        try:
            self.logger.info("Starting statistics calculation...")

            # Get all entries from storage
            all_entries = self.storage.query_entries_optimized(limit=None)

            if not all_entries:
                self.logger.warning("No entries found for statistics calculation")
                return False

            self.logger.info(f"Calculating statistics for {len(all_entries)} entries")

            # Calculate all statistics
            all_stats = self.stats_calculator.calculate_all_statistics(all_entries)

            # Store global statistics
            global_success = self.stats_manager.store_global_statistics(all_stats['global'])

            # Store resort statistics
            resort_success = self.stats_manager.store_resort_statistics(all_stats['resorts'])

            # Store monthly statistics
            monthly_success = self.stats_manager.store_monthly_statistics(all_stats['monthly'])

            # Store price trends
            trends_success = self.stats_manager.store_price_trends(all_stats['price_trends'])

            success = global_success and resort_success and monthly_success and trends_success

            if success:
                self.logger.info("Successfully calculated and stored all statistics including price trends")
            else:
                self.logger.warning("Some statistics storage operations failed")

            return success

        except Exception as e:
            self.logger.error(f"Error calculating and storing statistics: {str(e)}")
            return False
