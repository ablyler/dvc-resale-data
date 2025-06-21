#!/usr/bin/env python3
"""
ROFR Parsing Utilities

Shared utilities for parsing ROFR entries from forum posts.
Contains common logic used by both AzureROFRScraper and CompleteThreadProcessor.
"""

import re
import hashlib
import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple
from bs4 import BeautifulSoup

from models import ROFREntry, ThreadInfo


class ROFRParsingUtils:
    """Shared utilities for parsing ROFR entries from forum posts."""

    # Regex pattern for ROFR entries
    ROFR_PATTERN = r'(\w+(?:\s+\w+)?)\s*---\s*\$([0-9.]+)\s*-\s*\$([0-9,.]+)\s*-\s*(\d+)\s*-\s*([A-Z]{2,4}(?:@\w+)?)\s*-\s*(?:([A-Z][a-z]{2})\s*-\s*)?(.*?)-\s*sent\s+(\d+/\d+)(?:,\s*(passed|taken)\s+(\d+/\d+))?'

    def __init__(self):
        """Initialize the parsing utilities."""
        self.logger = logging.getLogger(__name__)

    def extract_points_breakdown(self, raw_entry: str) -> str:
        """
        Extract year-by-year points breakdown from raw forum entry.

        Args:
            raw_entry: The raw forum post text containing the ROFR entry

        Returns:
            String in format "0/13, 77/14, 160/15, 160/16" or "0/24, 250/25, 125/26"
        """
        if not raw_entry:
            return ""

        # Multiple patterns to match different formats of points/year breakdowns
        patterns = [
            # Format: 0/'13, 77/'14, 160/'15, 160/'16 (abbreviated years with apostrophes)
            r"(\d+/'?\d{2}(?:\s*,\s*\d+/'?\d{2}){1,})",
            # Format: 0/24, 250/25, 125/26 (full years)
            r"(\d+/\d{2}(?:\s*,\s*\d+/\d{2}){1,})",
            # Alternative separators
            r"(\d+/'?\d{2}(?:\s*[-;]\s*\d+/'?\d{2}){1,})",
        ]

        for pattern in patterns:
            match = re.search(pattern, raw_entry)
            if match:
                breakdown = match.group(1)
                # Remove apostrophes if present
                breakdown = breakdown.replace("'", "")
                # Normalize spacing around commas
                breakdown = re.sub(r'\s*,\s*', ', ', breakdown)
                breakdown = re.sub(r'\s*[-;]\s*', ', ', breakdown)
                breakdown = breakdown.strip()
                return breakdown

        return ""

    def parse_date_string(self, date_str: str, post_timestamp: str = None) -> Optional[date]:
        """
        Parse date string in format M/D or MM/DD to actual date.

        Uses post timestamp if available for accurate year determination,
        with future date detection and adjustment logic.

        Args:
            date_str: Date string like "12/31" or "6/15"
            post_timestamp: Unix timestamp string from forum post

        Returns:
            Parsed date object or None if parsing fails
        """
        if not date_str:
            return None

        try:
            # Handle formats like "6/18", "12/5", etc.
            parts = date_str.split('/')
            if len(parts) == 2:
                month = int(parts[0])
                day = int(parts[1])

                # Determine year from post_timestamp if available
                year = datetime.now().year
                if post_timestamp:
                    try:
                        # post_timestamp is a Unix timestamp, extract year from it
                        post_datetime = datetime.fromtimestamp(int(post_timestamp))
                        year = post_datetime.year
                        self.logger.debug(f"Using post timestamp {post_timestamp} -> year {year} for date {date_str}")
                    except (ValueError, TypeError):
                        # If post_timestamp parsing fails, fall back to current year
                        self.logger.debug(f"Failed to parse post_timestamp {post_timestamp}, using current year")
                        year = datetime.now().year

                # Create initial date
                parsed_date = date(year, month, day)

                # Check if this date is unreasonably far in the future (more than 30 days)
                # This handles cases where "12/31" in a 2025 thread should be 2024-12-31
                today = date.today()
                days_in_future = (parsed_date - today).days

                if days_in_future > 30:
                    # Try previous year
                    test_date = date(year - 1, month, day)
                    test_days_diff = (test_date - today).days
                    # Use previous year if it's not too far in the past (within 1 year)
                    if test_days_diff >= -365:
                        parsed_date = test_date
                        self.logger.debug(f"Adjusted date '{date_str}' from {year} to {year-1} to avoid future date")

                return parsed_date
            elif len(parts) == 3:
                # MM/DD/YYYY format
                month = int(parts[0])
                day = int(parts[1])
                year = int(parts[2])
                return date(year, month, day)
            else:
                return None
        except (ValueError, IndexError):
            return None

    def parse_date_with_thread_year(self, date_str: str, thread_year: Optional[int]) -> Optional[date]:
        """
        Parse date string using thread year context as fallback.

        This is the legacy approach for backward compatibility when post timestamps
        are not available.

        Args:
            date_str: Date string like "12/31" or "6/15"
            thread_year: Year extracted from thread title

        Returns:
            Parsed date object or None if parsing fails
        """
        if not date_str:
            return None

        try:
            parts = date_str.split('/')
            if len(parts) == 2:
                # MM/DD format
                month = int(parts[0])
                day = int(parts[1])

                # Use thread year if available, otherwise current year
                if thread_year:
                    year = thread_year
                else:
                    year = datetime.now().year

                # Create initial date
                parsed_date = date(year, month, day)

                # Check if this date is unreasonably far in the future (more than 30 days)
                today = date.today()
                days_in_future = (parsed_date - today).days

                if days_in_future > 30:
                    # Try previous year
                    test_date = date(year - 1, month, day)
                    test_days_diff = (test_date - today).days
                    # Use previous year if it's not too far in the past (within 1 year)
                    if test_days_diff >= -365:
                        parsed_date = test_date
                        self.logger.debug(f"Adjusted date '{date_str}' from {year} to {year-1} to avoid future date")

                return parsed_date
            elif len(parts) == 3:
                # MM/DD/YYYY format
                month = int(parts[0])
                day = int(parts[1])
                year = int(parts[2])
                return date(year, month, day)
            else:
                return None
        except (ValueError, IndexError):
            return None

    def validate_username_match(self, extracted_username: str, poster_username: str) -> bool:
        """
        Validate that the extracted username matches the poster username.

        Args:
            extracted_username: Username parsed from ROFR entry text
            poster_username: Actual username of the forum poster

        Returns:
            True if usernames match or poster_username is not available
        """
        if not poster_username:
            # If we don't have poster info, accept the entry (backward compatibility)
            return True

        # Simple exact match (case insensitive)
        return extracted_username.lower() == poster_username.lower()

    def validate_post_timestamp(self, post_timestamp: str) -> bool:
        """
        Validate that a post timestamp is reasonable and parseable.

        Args:
            post_timestamp: Unix timestamp string from forum post

        Returns:
            True if timestamp is valid and within reasonable range
        """
        if not post_timestamp or not post_timestamp.strip():
            return False

        try:
            timestamp_int = int(post_timestamp)
            # Check for reasonable timestamp range (after 2000, before 2100)
            # Unix timestamp for Jan 1, 2000 = 946684800
            # Unix timestamp for Jan 1, 2100 = 4102444800
            if 946684800 <= timestamp_int <= 4102444800:
                datetime.fromtimestamp(timestamp_int)
                return True
            else:
                self.logger.debug(f"post_timestamp {post_timestamp} outside reasonable range")
                return False
        except (ValueError, TypeError, OSError):
            self.logger.debug(f"Failed to parse post_timestamp {post_timestamp}")
            return False

    def extract_post_metadata(self, article) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract post metadata (timestamp and username) from BeautifulSoup article element.

        Args:
            article: BeautifulSoup element representing a forum post article

        Returns:
            Tuple of (post_timestamp, poster_username)
        """
        # Extract data-timestamp from the time element within the post
        post_timestamp = None
        time_element = article.select_one('time.u-dt')
        if time_element:
            post_timestamp = time_element.get('data-timestamp')

        # Extract poster username from the article data-author attribute
        poster_username = article.get('data-author')

        return post_timestamp, poster_username

    def extract_use_year_from_thread(self, thread_info: ThreadInfo) -> str:
        """
        Extract use year from thread information.

        Args:
            thread_info: ThreadInfo object containing thread metadata

        Returns:
            Use year as string
        """
        if thread_info.start_year:
            return str(thread_info.start_year)
        return str(datetime.now().year)

    def adjust_result_date_for_year_rollover(self, sent_date: date, result_date: date) -> date:
        """
        Adjust result date to handle year rollover scenarios.

        Args:
            sent_date: The sent date
            result_date: The initial result date that may need adjustment

        Returns:
            Adjusted result date
        """
        initial_days_diff = (result_date - sent_date).days

        # Case 1: result_date appears before sent_date and has an earlier month
        # This typically happens when result_date should be in the next year
        # Example: sent=12/15, result=1/10 → result should be next year's 1/10
        if (initial_days_diff < 0 and result_date.month < sent_date.month):
            return result_date.replace(year=result_date.year + 1)

        # Case 2: result_date is unreasonably far in the future (>180 days)
        # This may indicate result_date should be in the previous year instead
        # Example: sent=1/5, result=12/20 same year → 350 days difference is suspicious
        elif initial_days_diff > 180:  # More than 6 months later
            # Test if moving result_date to previous year creates a more reasonable timeframe
            test_result_date = result_date.replace(year=result_date.year - 1)
            test_days_diff = (test_result_date - sent_date).days
            # Only adjust if it results in a reasonable positive processing time (0-180 days)
            # This prevents creating impossible negative processing times
            if 0 <= test_days_diff <= 180:
                return test_result_date

        return result_date

    def parse_rofr_entries_from_text(self,
                                   post_text: str,
                                   thread_info: ThreadInfo,
                                   page_number: int = 1,
                                   post_idx: int = 0,
                                   post_timestamp: str = None,
                                   poster_username: str = None,
                                   start_date_filter: Optional[date] = None) -> List[ROFREntry]:
        """
        Parse ROFR entries from post text with full validation and metadata.

        Args:
            post_text: Text content of the forum post
            thread_info: ThreadInfo object containing thread metadata
            page_number: Page number being processed
            post_idx: Index of post on the page
            post_timestamp: Unix timestamp string from forum post
            poster_username: Username of the forum poster
            start_date_filter: Optional filter to skip entries before this date

        Returns:
            List of validated ROFREntry objects
        """
        entries = []
        matches = re.finditer(self.ROFR_PATTERN, post_text, re.IGNORECASE)

        for match in matches:
            try:
                username = match.group(1).strip()
                price_per_point = float(match.group(2))
                total_cost_str = match.group(3).replace(',', '')
                total_cost = float(total_cost_str)
                points = int(match.group(4))
                resort = match.group(5).strip()
                use_year = match.group(6).strip() if match.group(6) else ""
                points_breakdown_raw = match.group(7) if match.group(7) else ""
                sent_date_str = match.group(8)
                result = match.group(9) if match.group(9) else "pending"
                result_date_str = match.group(10) if match.group(10) else None

                # Validate post_timestamp and basic entry criteria
                timestamp_valid = self.validate_post_timestamp(post_timestamp)
                username_matches = self.validate_username_match(username, poster_username)

                if (len(username) > 0 and len(resort) > 0 and
                    points > 0 and price_per_point > 0 and price_per_point < 500 and
                    total_cost > 0 and username_matches):

                    # Parse dates - use post_timestamp if available, otherwise fall back to thread year
                    if timestamp_valid:
                        sent_date = self.parse_date_string(sent_date_str, post_timestamp)
                        result_date = self.parse_date_string(result_date_str, post_timestamp) if result_date_str else None
                    else:
                        # Fall back to thread year method for backward compatibility
                        sent_date = self.parse_date_with_thread_year(sent_date_str, thread_info.start_year)
                        result_date = self.parse_date_with_thread_year(result_date_str, thread_info.start_year) if result_date_str else None

                    # Skip entry if we cannot parse sent_date
                    if not sent_date:
                        self.logger.warning(f"Skipping entry - could not parse sent_date '{sent_date_str}' for user {username}")
                        continue

                    # Handle year rollover for result dates
                    if result_date and sent_date:
                        result_date = self.adjust_result_date_for_year_rollover(sent_date, result_date)

                    # Apply start date filter
                    if start_date_filter and sent_date and sent_date < start_date_filter:
                        continue

                    # Extract year-by-year points breakdown from the captured points breakdown text
                    points_breakdown = self.extract_points_breakdown(points_breakdown_raw)

                    # Set points_details based on whether we found a breakdown
                    if points_breakdown:
                        points_details = points_breakdown
                    else:
                        points_details = f"{points} points per year ({use_year} UY)"

                    # Create entry hash for deduplication
                    entry_key = f"{username.lower()}|{price_per_point}|{points}|{resort}|{use_year}|{sent_date_str}"
                    entry_hash = hashlib.md5(entry_key.encode()).hexdigest()

                    entry = ROFREntry(
                        username=username,
                        price_per_point=price_per_point,
                        total_cost=total_cost,
                        points=points,
                        resort=resort,
                        use_year=use_year,
                        points_details=points_details,
                        sent_date=sent_date,
                        result=result,
                        result_date=result_date,
                        thread_url=thread_info.url,
                        raw_entry=match.group(0),
                        entry_hash=entry_hash
                    )
                    entries.append(entry)

                else:
                    if not username_matches:
                        self.logger.debug(f"Username mismatch: extracted='{username}', poster='{poster_username}'")
                    else:
                        self.logger.debug(f"Entry validation failed for: {username}")

            except Exception as e:
                self.logger.error(f"Error parsing entry: {match.group(0)}")
                self.logger.error(f"Error details: {e}")

        self.logger.debug(f"Parsed {len(entries)} valid entries from post on page {page_number}")
        return entries

    def parse_rofr_entries_from_html(self,
                                   html_content: str,
                                   thread_info: ThreadInfo,
                                   page_number: int,
                                   start_date_filter: Optional[date] = None) -> List[ROFREntry]:
        """
        Parse ROFR entries from HTML content by extracting post metadata and text.

        Args:
            html_content: Raw HTML content of the forum page
            thread_info: ThreadInfo object containing thread metadata
            page_number: Page number being processed
            start_date_filter: Optional filter to skip entries before this date

        Returns:
            List of validated ROFREntry objects
        """
        if not html_content:
            return []

        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            # Look for the full article elements to access data-date
            articles = soup.select('article.message')

            entries = []
            for post_idx, article in enumerate(articles):
                # Extract post metadata
                post_timestamp, poster_username = self.extract_post_metadata(article)

                self.logger.debug(f"Page {page_number}, Post {post_idx}: data-timestamp = {post_timestamp}")
                self.logger.debug(f"Page {page_number}, Post {post_idx}: poster username = {poster_username}")

                # Get the post content
                post_content = article.select_one('.message-body .bbWrapper')
                if post_content:
                    post_text = post_content.get_text()
                    post_entries = self.parse_rofr_entries_from_text(
                        post_text, thread_info, page_number, post_idx,
                        post_timestamp, poster_username, start_date_filter
                    )
                    entries.extend(post_entries)

            return entries

        except Exception as e:
            self.logger.error(f"Error parsing HTML for page {page_number}: {e}")
            return []
