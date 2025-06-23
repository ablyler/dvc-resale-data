import azure.functions as func
import asyncio
import aiohttp
import json
import logging
import os
import time
import gzip
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Tuple, Optional
from functools import wraps
from bs4 import BeautifulSoup
import hashlib
import re
import base64
import binascii

from models import ThreadInfo, ROFREntry, ResortCodes
from table_storage_manager import OptimizedAzureTableStorageManager
from statistics_manager import StatisticsManager
from statistics_calculator import StatisticsCalculator
from queue_manager import ROFRQueueManager
from rofr_scraper_azure import AzureROFRScraper
from rofr_parsing_utils import ROFRParsingUtils

# Initialize Function App
app = func.FunctionApp()

# Configure logging with environment variable control
log_level_str = os.environ.get('LOG_LEVEL', 'INFO').upper()
log_level = getattr(logging, log_level_str, logging.INFO)
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)



# Global flag for statistics calculation
_stats_calculation_in_progress = False

def get_config():
    """Get configuration from environment variables."""
    return {
        'connection_string': os.environ.get('AZURE_STORAGE_CONNECTION_STRING'),
        'table_name': os.environ.get('ROFR_TABLE_NAME', 'rofrdata'),
        'delay': float(os.environ.get('SCRAPER_DELAY', '0.05')),
        'batch_size': int(os.environ.get('BATCH_SIZE', '200')),
        'chunk_size': int(os.environ.get('SCRAPER_CHUNK_SIZE', '2')),
        'max_retries': int(os.environ.get('MAX_RETRIES', '3')),
        'max_pages': int(os.environ.get('SCRAPER_MAX_PAGES', '10')),
        'enable_caching': os.environ.get('ENABLE_CACHING', 'true').lower() == 'true'
    }



def compress_response(function):
    """Decorator to compress HTTP responses."""
    @wraps(function)
    def wrapper(*args, **kwargs):
        response = function(*args, **kwargs)
        if isinstance(response, func.HttpResponse):
            request = args[0] if args else None
            if request and hasattr(request, 'headers'):
                accept_encoding = request.headers.get('Accept-Encoding', '')
                if 'gzip' in accept_encoding:
                    try:
                        body = response.get_body()
                        if body:
                            compressed_body = gzip.compress(body)
                            if len(compressed_body) < len(body):
                                headers = dict(response.headers) if response.headers else {}
                                headers['Content-Encoding'] = 'gzip'
                                headers['Content-Length'] = str(len(compressed_body))
                                return func.HttpResponse(
                                    body=compressed_body,
                                    status_code=response.status_code,
                                    headers=headers,
                                    mimetype=response.mimetype,
                                    charset=response.charset
                                )
                    except Exception as e:
                        logger.warning(f"Compression failed: {e}")
        return response
    return wrapper

def create_error_response(message: str, status_code: int = 500) -> func.HttpResponse:
    """Create standardized error response."""
    return func.HttpResponse(
        json.dumps({
            'error': message,
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'error'
        }),
        status_code=status_code,
        headers={
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, Accept-Encoding'
        }
    )

def create_success_response(data, message: Optional[str] = None) -> func.HttpResponse:
    """Create standardized success response."""
    response_data = {
        'data': data,
        'timestamp': datetime.utcnow().isoformat(),
        'status': 'success'
    }
    if message:
        response_data['message'] = message
    return func.HttpResponse(
        json.dumps(response_data, default=str),
        status_code=200,
        headers={
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, Accept-Encoding'
        }
    )

def get_storage_manager() -> OptimizedAzureTableStorageManager:
    """Get storage manager instance."""
    config = get_config()
    return OptimizedAzureTableStorageManager(config['connection_string'])

def get_statistics_manager() -> StatisticsManager:
    """Get statistics manager instance."""
    config = get_config()
    return StatisticsManager(config['connection_string'])

class CompleteThreadProcessor:
    """Process an entire thread (all pages) in a single function execution."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.storage = OptimizedAzureTableStorageManager(
            connection_string=config['connection_string']
        )
        self.session = None
        self.batch_size = config.get('batch_size', 200)
        self.chunk_size = config.get('chunk_size', 50)
        self.delay_between_requests = config.get('delay', 0.05)
        self.max_retries = config.get('max_retries', 3)
        self.parsing_utils = ROFRParsingUtils()

    async def initialize_session(self):
        """Initialize async HTTP session with optimized settings."""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            connector = aiohttp.TCPConnector(
                limit=50,
                limit_per_host=20,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30
            )
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )

    async def close_session(self):
        """Close async HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None

    async def get_total_pages(self, thread_url: str) -> int:
        """Get total number of pages in the thread."""
        try:
            if not self.session:
                await self.initialize_session()

            async with self.session.get(thread_url) as response:
                response.raise_for_status()
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Try multiple approaches to find pagination
                total_pages = 1

                # Approach 1: pageNavWrapper with data-page attributes
                page_nav = soup.find('nav', class_='pageNavWrapper')
                if page_nav and hasattr(page_nav, 'find_all'):
                    page_links = page_nav.find_all('a', {'data-page': True})
                    if page_links:
                        total_pages = max(int(link.get('data-page', 1)) for link in page_links)
                        logger.debug(f"Found {total_pages} pages using pageNavWrapper data-page")
                        return total_pages

                    page_text = page_nav.get_text()
                    numbers = re.findall(r'Page \d+ of (\d+)', page_text)
                    if numbers:
                        total_pages = int(numbers[0])
                        logger.debug(f"Found {total_pages} pages using pageNavWrapper regex")
                        return total_pages

                # Approach 2: pageNav-main with text parsing (like AzureROFRScraper)
                page_nav = soup.select_one('.pageNav-main')
                if page_nav and hasattr(page_nav, 'select'):
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
                                logger.debug(f"Found {total_pages} pages using pageNav-main text parsing")
                                return total_pages
                        except (ValueError, TypeError):
                            pass

                # Approach 3: Look for any pagination indicators
                page_indicators = soup.find_all(text=re.compile(r'Page \d+ of (\d+)'))
                for indicator in page_indicators:
                    numbers = re.findall(r'Page \d+ of (\d+)', indicator)
                    if numbers:
                        total_pages = int(numbers[0])
                        logger.debug(f"Found {total_pages} pages using text indicator")
                        return total_pages

                logger.debug(f"No pagination found, assuming single page for {thread_url}")
                return 1
        except Exception as e:
            logger.error(f"Error getting total pages for {thread_url}: {e}")
            return 1

    async def scrape_page_content(self, thread_url: str, page_number: int) -> Tuple[str, int]:
        """Scrape content from a single page."""
        if not self.session:
            await self.initialize_session()

        page_url = f"{thread_url}/page-{page_number}" if page_number > 1 else thread_url

        for attempt in range(self.max_retries):
            try:
                await asyncio.sleep(self.delay_between_requests)

                async with self.session.get(page_url) as response:
                    response.raise_for_status()
                    html_content = await response.text()

                    soup = BeautifulSoup(html_content, 'html.parser')
                    total_pages = self._extract_total_pages_from_soup(soup)

                    return html_content, total_pages

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for page {page_number}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.error(f"Failed to scrape page {page_number} after {self.max_retries} attempts")
                    return "", 0

    def _extract_total_pages_from_soup(self, soup: BeautifulSoup) -> int:
        """Extract total pages from BeautifulSoup object."""
        try:
            # Approach 1: pageNavWrapper with data-page attributes
            page_nav = soup.find('nav', class_='pageNavWrapper')
            if page_nav and hasattr(page_nav, 'find_all'):
                page_links = page_nav.find_all('a', {'data-page': True})
                if page_links:
                    return max(int(link.get('data-page', 1)) for link in page_links)

                page_text = page_nav.get_text()
                numbers = re.findall(r'Page \d+ of (\d+)', page_text)
                if numbers:
                    return int(numbers[0])

            # Approach 2: pageNav-main with text parsing
            page_nav = soup.select_one('.pageNav-main')
            if page_nav and hasattr(page_nav, 'select'):
                page_links = page_nav.select('a')
                if page_links:
                    try:
                        page_numbers = []
                        for link in page_links:
                            text = link.get_text().strip()
                            if text.isdigit():
                                page_numbers.append(int(text))
                        if page_numbers:
                            return max(page_numbers)
                    except (ValueError, TypeError):
                        pass

            # Approach 3: Look for any pagination indicators in text
            page_indicators = soup.find_all(text=re.compile(r'Page \d+ of (\d+)'))
            for indicator in page_indicators:
                numbers = re.findall(r'Page \d+ of (\d+)', indicator)
                if numbers:
                    return int(numbers[0])

        except Exception:
            pass
        return 0

    def parse_rofr_entries_from_html(self, html_content: str, thread_info: ThreadInfo, page_number: int) -> List[ROFREntry]:
        """Parse ROFR entries from HTML content."""
        return self.parsing_utils.parse_rofr_entries_from_html(
            html_content, thread_info, page_number
        )

    def _parse_rofr_data_from_text(self, post_text: str, thread_info: ThreadInfo, page_number: int, post_idx: int, post_timestamp: str = None, poster_username: str = None) -> List[ROFREntry]:
        """Parse ROFR data from post text using shared parsing utilities."""
        return self.parsing_utils.parse_rofr_entries_from_text(
            post_text, thread_info, page_number, post_idx, post_timestamp, poster_username
        )

    def _extract_date_from_thread(self, thread_info: ThreadInfo) -> date:
        """Extract date from thread info or use current date."""
        if thread_info.start_year:
            try:
                return date(int(thread_info.start_year), 1, 1)
            except:
                pass
        return date.today()







    async def process_page_chunk(self, thread_info: ThreadInfo, page_numbers: List[int]) -> Tuple[List[ROFREntry], Dict[str, int]]:
        """Process a chunk of pages concurrently."""
        logger.info(f"Processing pages {page_numbers[0]}-{page_numbers[-1]} for thread: {thread_info.title}")

        scrape_tasks = [
            self.scrape_page_content(thread_info.url, page_num)
            for page_num in page_numbers
        ]

        scrape_results = await asyncio.gather(*scrape_tasks, return_exceptions=True)

        all_entries = []
        stats = {'pages_processed': 0, 'pages_failed': 0, 'total_pages': 0}

        for i, result in enumerate(scrape_results):
            page_number = page_numbers[i]

            if isinstance(result, Exception):
                logger.error(f"Failed to scrape page {page_number}: {result}")
                stats['pages_failed'] += 1
                continue

            html_content, total_pages = result
            if total_pages > 0:
                stats['total_pages'] = max(stats['total_pages'], total_pages)

            if html_content:
                page_entries = self.parse_rofr_entries_from_html(html_content, thread_info, page_number)
                all_entries.extend(page_entries)
                stats['pages_processed'] += 1

                logger.debug(f"Page {page_number}: {len(page_entries)} entries found")
            else:
                stats['pages_failed'] += 1

        return all_entries, stats

    async def process_complete_thread(self, thread_info: ThreadInfo, session_id: str) -> Dict[str, Any]:
        """Process all pages of a thread in a single execution with optimizations."""
        logger.info(f"Starting complete thread processing: {thread_info.title}")
        processing_start = time.time()

        await self.initialize_session()

        try:
            # Get existing thread info from storage to check current state
            existing_thread_data = self.storage.get_thread_info(thread_info.url)
            if existing_thread_data:
                existing_thread = ThreadInfo.from_table_entity(existing_thread_data)

                # Check if thread is completed and old (skip optimization)
                cutoff_date = date.today() - timedelta(days=90)
                if (existing_thread.thread_end_date and
                    existing_thread.thread_end_date < cutoff_date and
                    existing_thread.last_scraped_page and
                    existing_thread.total_pages and
                    existing_thread.last_scraped_page >= existing_thread.total_pages):

                    logger.info(f"Skipping thread '{thread_info.title}' - completed and older than 90 days "
                               f"(ended {existing_thread.thread_end_date}, last scraped page {existing_thread.last_scraped_page}/{existing_thread.total_pages})")
                    return {
                        'success': True,
                        'skipped': True,
                        'reason': 'completed_and_old',
                        'thread_title': thread_info.title,
                        'total_pages': existing_thread.total_pages,
                        'pages_processed': 0,
                        'pages_failed': 0,
                        'entries_found': 0,
                        'new_entries': 0,
                        'updated_entries': 0,
                        'processing_time': 0
                    }

                # Update thread_info with existing values
                if existing_thread.last_scraped_page:
                    thread_info.last_scraped_page = existing_thread.last_scraped_page
                if existing_thread.total_pages:
                    thread_info.total_pages = existing_thread.total_pages

            total_pages = await self.get_total_pages(thread_info.url)
            logger.info(f"Thread has {total_pages} pages to process")

            if total_pages == 0:
                logger.warning(f"Could not determine total pages for thread: {thread_info.url}")
                return {'success': False, 'error': 'Could not determine total pages'}

            thread_info.total_pages = total_pages
            self.storage.safe_upsert_thread(thread_info)

            # Determine start page based on last_scraped_page
            start_page = 1
            if thread_info.last_scraped_page and thread_info.last_scraped_page > 0:
                start_page = thread_info.last_scraped_page
                logger.info(f"Resuming from page {start_page} (last scraped: {thread_info.last_scraped_page})")
            else:
                logger.info("Starting fresh scrape from page 1")

            total_stats = {
                'pages_processed': 0,
                'pages_failed': 0,
                'entries_found': 0,
                'new_entries': 0,
                'updated_entries': 0,
                'processing_time': 0
            }

            # Create page range from start_page to total_pages
            page_numbers = list(range(start_page, total_pages + 1))
            if not page_numbers:
                logger.info(f"No pages to process (start_page: {start_page}, total_pages: {total_pages})")
                return {
                    'success': True,
                    'thread_title': thread_info.title,
                    'total_pages': total_pages,
                    'skipped': True,
                    'reason': 'no_pages_to_process',
                    **total_stats
                }

            page_chunks = [page_numbers[i:i + self.chunk_size] for i in range(0, len(page_numbers), self.chunk_size)]

            logger.info(f"Processing {len(page_chunks)} chunks starting from page {start_page} ({len(page_numbers)} total pages)")

            for chunk_idx, page_chunk in enumerate(page_chunks):
                chunk_start = time.time()

                elapsed_time = time.time() - processing_start
                if elapsed_time > 480:
                    logger.warning(f"Approaching timeout, processed {chunk_idx} chunks out of {len(page_chunks)}")
                    break

                try:
                    chunk_entries, chunk_stats = await self.process_page_chunk(thread_info, page_chunk)

                    if chunk_entries:
                        batch_results = self.storage.batch_upsert_entries(chunk_entries)
                        total_stats['new_entries'] += batch_results.get('new', 0)
                        total_stats['updated_entries'] += batch_results.get('updated', 0)
                        total_stats['entries_found'] += len(chunk_entries)

                    total_stats['pages_processed'] += chunk_stats['pages_processed']
                    total_stats['pages_failed'] += chunk_stats['pages_failed']

                    progress_percentage = ((chunk_idx + 1) / len(page_chunks)) * 100

                    # Update session progress tracking
                    self.storage.update_thread_progress_batch(
                        session_id=session_id,
                        thread_url=thread_info.url,
                        current_page=str(page_chunk[-1]),
                        pages_processed=str(total_stats['pages_processed']),
                        entries_found=str(total_stats['entries_found']),
                        new_entries=str(total_stats['new_entries']),
                        updated_entries=str(total_stats['updated_entries']),
                        status=f'processing_{progress_percentage:.1f}%'
                    )

                    # Update thread info with last scraped page
                    thread_info.last_scraped_page = page_chunk[-1]
                    self.storage.safe_upsert_thread(thread_info)

                    chunk_time = time.time() - chunk_start
                    logger.info(f"Chunk {chunk_idx + 1}/{len(page_chunks)} completed in {chunk_time:.2f}s: "
                              f"{len(chunk_entries)} entries, {chunk_stats['pages_processed']} pages")

                except Exception as e:
                    logger.error(f"Error processing chunk {chunk_idx}: {e}")
                    total_stats['pages_failed'] += len(page_chunk)

            total_stats['processing_time'] = time.time() - processing_start

            # Update session progress tracking
            self.storage.update_thread_progress_batch(
                session_id=session_id,
                thread_url=thread_info.url,
                current_page=str(total_pages),
                pages_processed=str(total_stats['pages_processed']),
                entries_found=str(total_stats['entries_found']),
                new_entries=str(total_stats['new_entries']),
                updated_entries=str(total_stats['updated_entries']),
                status='completed'
            )

            # Mark thread as completed with final page count
            thread_info.last_scraped_page = total_pages
            self.storage.safe_upsert_thread(thread_info)

            logger.info(f"Thread processing completed: {total_stats}")
            return {
                'success': True,
                'thread_title': thread_info.title,
                'total_pages': total_pages,
                **total_stats
            }

        except Exception as e:
            logger.error(f"Error in complete thread processing: {e}")
            return {
                'success': False,
                'error': str(e),
                'thread_title': thread_info.title
            }

        finally:
            await self.close_session()

# Timer-triggered function
@app.function_name(name="scrape_rofr_timer")
@app.schedule(schedule="0 0,15,30,45 * * * *", arg_name="myTimer", run_on_startup=False)
async def scrape_rofr_timer(myTimer: func.TimerRequest) -> None:
    """Scheduled function to scrape ROFR data every 15 minutes - processes all threads inline."""
    scrape_start_time = time.time()

    try:
        logger.info("Starting scheduled ROFR scrape with inline thread processing")

        config = get_config()
        scraper = AzureROFRScraper(
            connection_string=config['connection_string'],
            table_name=config['table_name'],
            delay=config['delay'],
            max_pages=config['max_pages']
        )

        current_thread_url = scraper.get_current_thread_url()
        if not current_thread_url:
            logger.error("Could not determine current thread URL")
            return

        thread_infos = scraper.extract_thread_urls_from_first_post(current_thread_url)
        logger.info(f"Discovered {len(thread_infos)} threads")

        if not thread_infos:
            logger.warning("No threads found to process")
            return

        session_id = scraper.storage.start_scrape_session()
        total_threads = len(thread_infos)

        # Update session metadata
        import json
        pending_threads = []
        for thread_info in thread_infos:
            thread_dict = {
                'url': thread_info.url,
                'title': thread_info.title,
                'start_year': thread_info.start_year,
                'end_year': thread_info.end_year
            }
            pending_threads.append(thread_dict)

        scraper.storage.update_session_metadata(
            session_id,
            total_threads=total_threads,
            status='processing',
            pending_threads=json.dumps(pending_threads),
            current_thread_index=0
        )

        # Initialize complete thread processor
        processor = CompleteThreadProcessor(config)
        await processor.initialize_session()

        total_stats = {
            'threads_processed': 0,
            'threads_failed': 0,
            'total_entries_found': 0,
            'total_new_entries': 0,
            'total_updated_entries': 0,
            'total_pages_processed': 0
        }

        try:
            # Process each thread inline
            for thread_idx, thread_info in enumerate(thread_infos):
                thread_start_time = time.time()

                # Check timeout (8 minutes max for timer functions)
                elapsed_time = time.time() - scrape_start_time
                if elapsed_time > 480:
                    logger.warning(f"Approaching timeout, processed {thread_idx} threads out of {total_threads}")
                    break

                logger.info(f"Processing thread {thread_idx + 1}/{total_threads}: {thread_info.title}")

                # Validate thread info
                if not thread_info.url or not thread_info.title:
                    logger.error(f"Invalid thread info: {thread_info}")
                    total_stats['threads_failed'] += 1
                    continue

                try:
                    # Process the complete thread
                    result = await processor.process_complete_thread(thread_info, session_id)

                    if result['success']:
                        total_stats['threads_processed'] += 1
                        total_stats['total_entries_found'] += result.get('entries_found', 0)
                        total_stats['total_new_entries'] += result.get('new_entries', 0)
                        total_stats['total_updated_entries'] += result.get('updated_entries', 0)
                        total_stats['total_pages_processed'] += result.get('pages_processed', 0)

                        thread_time = time.time() - thread_start_time
                        logger.info(f"Thread {thread_idx + 1} completed in {thread_time:.2f}s: "
                                   f"Pages: {result.get('pages_processed', 0)}, "
                                   f"Entries: {result.get('entries_found', 0)}, "
                                   f"New: {result.get('new_entries', 0)}, "
                                   f"Updated: {result.get('updated_entries', 0)}")
                    else:
                        total_stats['threads_failed'] += 1
                        logger.error(f"Thread {thread_idx + 1} failed: {result.get('error', 'Unknown error')}")

                except Exception as e:
                    total_stats['threads_failed'] += 1
                    logger.error(f"Error processing thread {thread_idx + 1} '{thread_info.title}': {e}")

                # Update session progress
                try:
                    scraper.storage.update_session_metadata(
                        session_id,
                        current_thread_index=thread_idx + 1,
                        status=f'processing_{((thread_idx + 1) / total_threads * 100):.1f}%'
                    )
                except Exception as e:
                    logger.warning(f"Failed to update session progress: {e}")

        finally:
            await processor.close_session()

        # Complete the session
        total_processing_time = time.time() - scrape_start_time

        try:
            scraper.storage.update_session_metadata(
                session_id,
                status='completed',
                processing_time=total_processing_time,
                threads_processed=total_stats['threads_processed'],
                threads_failed=total_stats['threads_failed'],
                total_entries=total_stats['total_entries_found'],
                new_entries=total_stats['total_new_entries'],
                updated_entries=total_stats['total_updated_entries']
            )
        except Exception as e:
            logger.warning(f"Failed to update final session metadata: {e}")

        # Trigger statistics update
        try:
            queue_manager = ROFRQueueManager(config['connection_string'])
            queue_manager.add_stats_update_task(f"timer_scrape_{session_id}")
        except Exception as e:
            logger.error(f"Error triggering stats update: {e}")

        # Final summary
        logger.info(f"Scheduled scrape completed in {total_processing_time:.2f}s:")
        logger.info(f"  - Threads processed: {total_stats['threads_processed']}/{total_threads}")
        logger.info(f"  - Threads failed: {total_stats['threads_failed']}")
        logger.info(f"  - Total pages processed: {total_stats['total_pages_processed']}")
        logger.info(f"  - Total entries found: {total_stats['total_entries_found']}")
        logger.info(f"  - New entries: {total_stats['total_new_entries']}")
        logger.info(f"  - Updated entries: {total_stats['total_updated_entries']}")

    except Exception as e:
        logger.error(f"Error in scheduled scrape: {str(e)}", exc_info=True)

# Queue-triggered function for statistics calculation
@app.function_name(name="update_statistics_task")
@app.queue_trigger(arg_name="msg", queue_name="rofr-statistics-update", connection="AzureWebJobsStorage")
def update_statistics_task(msg: func.QueueMessage) -> None:
    """Update statistics by recalculating from Azure storage entries table."""
    try:
        logger.info("Processing statistics update task from queue trigger")

        config = get_config()

        scraper = AzureROFRScraper(
            connection_string=config['connection_string'],
            table_name=config['table_name'],
            delay=config['delay'],
            max_pages=config['max_pages']
        )

        logger.info("Recalculating statistics from Azure storage entries table")
        stats_result = scraper._calculate_and_store_statistics()

        logger.info(f"Statistics recalculation completed. Result: {stats_result}")
    except Exception as e:
        logger.error(f"Error updating statistics: {str(e)}", exc_info=True)
        raise

# HTTP endpoints
@app.function_name(name="get_rofr_stats")
@app.route(route="rofr-stats", auth_level=func.AuthLevel.ANONYMOUS)
@compress_response
def get_rofr_stats(req: func.HttpRequest) -> func.HttpResponse:
    """Get pre-calculated ROFR statistics."""
    try:
        stats_manager = get_statistics_manager()
        stats = stats_manager.get_global_statistics()

        if not stats:
            return create_error_response("No statistics available", 404)

        return create_success_response(stats)

    except Exception as e:
        logger.error(f"Error in get_rofr_stats: {str(e)}", exc_info=True)
        return create_error_response("Internal server error")

@app.function_name(name="get_rofr_data")
@app.route(route="rofr-data", auth_level=func.AuthLevel.ANONYMOUS)
@compress_response
def get_rofr_data(req: func.HttpRequest) -> func.HttpResponse:
    """Get ROFR data with filtering and sorting."""
    try:
        # Extract all filter parameters
        resort = req.params.get('resort')
        result = req.params.get('result')
        username = req.params.get('username')
        use_year = req.params.get('use_year')

        # Date filters
        start_date = req.params.get('start_date')
        end_date = req.params.get('end_date')

        # Numeric filters
        min_price = float(req.params.get('min_price')) if req.params.get('min_price') else None
        max_price = float(req.params.get('max_price')) if req.params.get('max_price') else None
        min_points = int(req.params.get('min_points')) if req.params.get('min_points') else None
        max_points = int(req.params.get('max_points')) if req.params.get('max_points') else None
        min_total_cost = float(req.params.get('min_total_cost')) if req.params.get('min_total_cost') else None

        # Other filters
        exclude_result = req.params.get('exclude_result')

        # Pagination and sorting
        limit = min(int(req.params.get('limit', '1000')), 10000)
        offset = int(req.params.get('offset', '0'))
        sort_by = req.params.get('sort_by', 'sent_date')
        sort_order = req.params.get('sort_order', 'desc')

        # Convert date strings to date objects
        start_date_obj = None
        end_date_obj = None
        if start_date:
            try:
                start_date_obj = datetime.fromisoformat(start_date).date()
            except ValueError:
                pass
        if end_date:
            try:
                end_date_obj = datetime.fromisoformat(end_date).date()
            except ValueError:
                pass

        # Get paginated results and total count in one operation
        storage = get_storage_manager()
        entries, total_count = storage.query_entries_with_count(
            resort=resort,
            result=result,
            username=username,
            use_year=use_year,
            start_date=start_date_obj,
            end_date=end_date_obj,
            min_price=min_price,
            max_price=max_price,
            min_points=min_points,
            max_points=max_points,
            min_total_cost=min_total_cost,
            exclude_result=exclude_result,
            sort_by=sort_by,
            sort_order=sort_order,
            offset=offset,
            limit=limit
        )

        # Convert to response format
        data = []
        for entry in entries:
            data.append({
                'username': entry.username,
                'resort': entry.resort,
                'price_per_point': entry.price_per_point,
                'points': entry.points,
                'total_cost': entry.total_cost,
                'use_year': entry.use_year,
                'points_details': entry.points_details,
                'result': entry.result,
                'sent_date': entry.sent_date.isoformat() if entry.sent_date else None,
                'result_date': entry.result_date.isoformat() if entry.result_date else None,
                'thread_url': entry.thread_url,
                'raw_entry': entry.raw_entry
            })

        return create_success_response({
            'entries': data,
            'count': len(data),
            'total_count': total_count,
            'filters': {
                'resort': resort,
                'result': result,
                'username': username,
                'use_year': use_year,
                'start_date': start_date,
                'end_date': end_date,
                'min_price': min_price,
                'max_price': max_price,
                'min_points': min_points,
                'max_points': max_points,
                'min_total_cost': min_total_cost,
                'exclude_result': exclude_result,
                'sort_by': sort_by,
                'sort_order': sort_order,
                'limit': limit,
                'offset': offset
            }
        })

    except Exception as e:
        logger.error(f"Error in get_rofr_data: {str(e)}", exc_info=True)
        return create_error_response("Internal server error")

@app.function_name(name="get_resorts")
@app.route(route="resorts", auth_level=func.AuthLevel.ANONYMOUS)
@compress_response
def get_resorts(req: func.HttpRequest) -> func.HttpResponse:
    """Get list of available resorts."""
    try:
        storage = get_storage_manager()

        # Get unique resorts from the entries
        entries = storage.query_entries_optimized(limit=10000)
        resorts = set()
        for entry in entries:
            if entry.resort:
                resorts.add(entry.resort)

        resort_list = sorted(list(resorts))

        return create_success_response(resort_list)

    except Exception as e:
        logger.error(f"Error in get_resorts: {str(e)}", exc_info=True)
        return create_error_response("Internal server error")


@app.route(route="usernames", auth_level=func.AuthLevel.ANONYMOUS)
@compress_response
def get_usernames(req: func.HttpRequest) -> func.HttpResponse:
    """Get list of available usernames."""
    try:
        storage = get_storage_manager()

        # Get unique usernames from the entries
        entries = storage.query_entries_optimized(limit=10000)
        usernames = set()
        for entry in entries:
            if entry.username and entry.username.strip():
                usernames.add(entry.username.strip())

        username_list = sorted(list(usernames))

        return create_success_response(username_list)

    except Exception as e:
        logger.error(f"Error in get_usernames: {str(e)}", exc_info=True)
        return create_error_response("Internal server error")

@app.function_name(name="get_rofr_monthly_stats")
@app.route(route="rofr-monthly-stats", auth_level=func.AuthLevel.ANONYMOUS)
@compress_response
def get_rofr_monthly_stats(req: func.HttpRequest) -> func.HttpResponse:
    """Get monthly ROFR statistics."""
    try:
        months = int(req.params.get('months', '12'))
        months = min(months, 36)  # Limit to 3 years max

        stats_manager = get_statistics_manager()
        monthly_stats = stats_manager.get_monthly_statistics(months)

        return create_success_response(monthly_stats)

    except Exception as e:
        logger.error(f"Error in get_rofr_monthly_stats: {str(e)}", exc_info=True)
        return create_error_response("Internal server error")

@app.function_name(name="get_dashboard_data")
@app.route(route="dashboard-data", auth_level=func.AuthLevel.ANONYMOUS)
@compress_response
def get_dashboard_data(req: func.HttpRequest) -> func.HttpResponse:
    """Get consolidated dashboard data with optional time range filtering."""
    try:
        # Get time range parameter (default to 3months)
        time_range = req.params.get('time_range', '3months')

        # Debug logging to verify parameter is received
        logger.info(f"Dashboard API called with time_range parameter: '{time_range}'")
        logger.info(f"All request params: {dict(req.params)}")

        # Validate time range
        valid_ranges = ['3months', '6months', '1year', 'all']
        if time_range not in valid_ranges:
            logger.warning(f"Invalid time range '{time_range}', defaulting to '3months'")
            time_range = '3months'
        else:
            logger.info(f"Using validated time range: '{time_range}'")

        storage = get_storage_manager()

        # Get all entries for statistics calculation
        all_entries = storage.query_entries_optimized(limit=None)

        if not all_entries:
            logger.warning("No entries found for dashboard data")
            return create_error_response("No data available", 404)

        # Calculate filtered statistics
        from statistics_calculator import StatisticsCalculator
        calc = StatisticsCalculator()
        all_stats = calc.calculate_all_statistics(all_entries, time_range)

        global_stats = all_stats['global']
        monthly_stats = all_stats['monthly']

        # Get resort data from filtered entries
        filtered_entries = calc._filter_entries_by_time_range(all_entries, time_range)
        resorts = set()
        for entry in filtered_entries:
            if entry.resort:
                resorts.add(entry.resort)

        # Fix last_updated field mapping
        if 'latest_entry_date' in global_stats and global_stats['latest_entry_date']:
            global_stats['last_updated'] = global_stats['latest_entry_date']

        # Ensure monthly_stats is always an array, sorted by month
        if not monthly_stats:
            monthly_stats = []
        elif isinstance(monthly_stats, dict):
            # Convert dict to sorted list by month key and map field names for frontend compatibility
            monthly_stats_list = []
            for month in sorted(monthly_stats.keys()):
                month_data = monthly_stats[month]
                # Map field names to match PriceTrendChart expectations
                mapped_data = {
                    'month': month_data.get('month', month),
                    'averagePrice': month_data.get('avg_price_per_point', 0),
                    'minPrice': month_data.get('min_price_per_point', 0),
                    'maxPrice': month_data.get('max_price_per_point', 0),
                    'total': month_data.get('total_entries', 0),
                    'taken': month_data.get('taken_count', 0),
                    'passed': month_data.get('passed_count', 0),
                    'pending': month_data.get('pending_count', 0),
                    'rofrRate': month_data.get('rofr_rate', 0),
                    'unique_resorts': month_data.get('unique_resorts', 0),
                    'unique_users': month_data.get('unique_users', 0),
                    'top_resorts': month_data.get('top_resorts', []),
                    'last_calculated': month_data.get('last_calculated')
                }
                monthly_stats_list.append(mapped_data)
            monthly_stats = monthly_stats_list
        elif not isinstance(monthly_stats, list):
            monthly_stats = []

        dashboard_data = {
            'global_stats': global_stats,
            'monthly_stats': monthly_stats,
            'recent_entries_count': len(filtered_entries),
            'resort_count': len(resorts),
            'top_resorts': sorted(list(resorts))[:10],
            'time_range': time_range,
            'total_entries_available': len(all_entries)
        }

        # Add debug logging for troubleshooting
        logger.info(f"Dashboard data prepared: global_stats keys: {list(global_stats.keys())}")
        logger.info(f"Monthly stats count: {len(monthly_stats)}")
        logger.info(f"Last updated field: {global_stats.get('last_updated', 'NOT FOUND')}")

        return create_success_response(dashboard_data)

    except Exception as e:
        logger.error(f"Error in get_dashboard_data: {str(e)}", exc_info=True)
        return create_error_response("Internal server error")

@app.function_name(name="get_rofr_analytics")
@app.route(route="rofr-analytics", auth_level=func.AuthLevel.ANONYMOUS)
@compress_response
def get_rofr_analytics(req: func.HttpRequest) -> func.HttpResponse:
    """Get ROFR analytics with filtering."""
    try:
        resort = req.params.get('resort')
        result = req.params.get('result')
        months = int(req.params.get('months', '12'))



        storage = get_storage_manager()

        # Get filtered entries
        entries = storage.query_entries_optimized(
            resort=resort,
            result=result,
            limit=5000
        )

        if not entries:
            return create_success_response({
                'total_entries': 0,
                'analytics': {},
                'filters': {'resort': resort, 'result': result, 'months': months}
            })

        # Calculate analytics
        total_entries = len(entries)
        total_points = sum(entry.points for entry in entries if entry.points)
        avg_price = sum(entry.price_per_point for entry in entries if entry.price_per_point) / total_entries if total_entries > 0 else 0

        # Group by result
        result_counts = {}
        for entry in entries:
            result_key = entry.result or 'unknown'
            result_counts[result_key] = result_counts.get(result_key, 0) + 1

        # Group by resort
        resort_counts = {}
        for entry in entries:
            resort_key = entry.resort or 'unknown'
            resort_counts[resort_key] = resort_counts.get(resort_key, 0) + 1

        analytics = {
            'total_entries': total_entries,
            'total_points': total_points,
            'average_price_per_point': round(avg_price, 2),
            'result_breakdown': result_counts,
            'resort_breakdown': resort_counts,
            'price_range': {
                'min': min(entry.price_per_point for entry in entries if entry.price_per_point) if entries else 0,
                'max': max(entry.price_per_point for entry in entries if entry.price_per_point) if entries else 0
            }
        }

        response_data = {
            'entries': [
                {
                    'username': entry.username,
                    'resort': entry.resort,
                    'price_per_point': entry.price_per_point,
                    'points': entry.points,
                    'result': entry.result,
                    'sent_date': entry.sent_date.isoformat() if entry.sent_date else None,
                    'result_date': entry.result_date.isoformat() if entry.result_date else None
                }
                for entry in entries[:100]  # Limit to first 100 for response size
            ],
            'analytics': analytics,
            'filters': {'resort': resort, 'result': result, 'months': months}
        }



        return create_success_response(response_data)

    except Exception as e:
        logger.error(f"Error in get_rofr_analytics: {str(e)}", exc_info=True)
        return create_error_response("Internal server error")

@app.function_name(name="trigger_stats_calculation")
@app.route(route="trigger-stats", methods=["POST"])
def trigger_stats_calculation(req: func.HttpRequest) -> func.HttpResponse:
    """Manually trigger statistics calculation."""
    try:
        logger.info("Manual statistics calculation trigger requested")

        config = get_config()
        queue_manager = ROFRQueueManager(config['connection_string'])

        success = queue_manager.add_stats_update_task("manual_trigger")

        if success:
            return create_success_response({
                'message': 'Statistics recalculation trigger queued successfully',
                'queued': True
            })
        else:
            return create_error_response("Failed to queue statistics recalculation trigger")

    except Exception as e:
        logger.error(f"Error queuing statistics trigger: {str(e)}", exc_info=True)
        return create_error_response(f"Failed to queue statistics trigger: {str(e)}")

@app.function_name(name="trigger_stats_calculation_immediate")
@app.route(route="trigger-stats-immediate", methods=["POST"])
def trigger_stats_calculation_immediate(req: func.HttpRequest) -> func.HttpResponse:
    """Immediately trigger statistics calculation (synchronous)."""
    global _stats_calculation_in_progress

    if _stats_calculation_in_progress:
        return create_error_response("Statistics calculation already in progress")

    _stats_calculation_in_progress = True

    try:
        logger.info("Immediate statistics calculation triggered")

        config = get_config()
        scraper = AzureROFRScraper(
            connection_string=config['connection_string'],
            table_name=config['table_name'],
            delay=config['delay'],
            max_pages=config['max_pages']
        )

        # Calculate and store statistics
        stats_result = scraper._calculate_and_store_statistics()

        return create_success_response({
            'statistics_updated': stats_result,
            'message': 'Statistics calculation completed successfully'
        })

    except Exception as e:
        logger.error(f"Error in immediate statistics calculation: {str(e)}", exc_info=True)
        return create_error_response(f"Failed to calculate statistics: {str(e)}")
    finally:
        _stats_calculation_in_progress = False

@app.function_name(name="debug_data")
@app.route(route="debug-data", auth_level=func.AuthLevel.ANONYMOUS)
def debug_data(req: func.HttpRequest) -> func.HttpResponse:
    """Debug endpoint to check data availability."""
    try:
        storage = get_storage_manager()
        entries = storage.query_entries_optimized(limit=100)

        # Check BWV entries specifically
        bwv_entries = [e for e in entries if e.resort == "BWV"]

        debug_info = {
            'total_entries': len(entries),
            'bwv_entries': len(bwv_entries),
            'sample_resorts': list(set([e.resort for e in entries[:20]])),
            'sample_bwv_prices': [e.price_per_point for e in bwv_entries[:5]],
            'sample_bwv_dates': [e.sent_date.isoformat() if e.sent_date else None for e in bwv_entries[:5]],
            'raw_entry_samples': [e.raw_entry for e in entries[:5]],
            'raw_entry_lengths': [len(e.raw_entry) if e.raw_entry else 0 for e in entries[:5]],
            'entries_with_raw_data': len([e for e in entries if e.raw_entry])
        }

        return create_success_response(debug_info)
    except Exception as e:
        logger.error(f"Debug endpoint error: {str(e)}")
        return create_error_response(str(e))

@app.function_name(name="get_price_trends_analysis")
@app.route(route="price-trends-analysis", auth_level=func.AuthLevel.ANONYMOUS)
@compress_response
def get_price_trends_analysis(req: func.HttpRequest) -> func.HttpResponse:
    """Get price trends analysis with filtering."""
    try:
        # Extract parameters
        time_range = int(req.params.get('timeRange', '12'))
        min_price = float(req.params.get('minPrice', '0'))
        max_price = float(req.params.get('maxPrice', '1000'))
        resort = req.params.get('resort')

        # Limit time range to reasonable values
        time_range = min(time_range, 36)  # Max 3 years

        logger.info(f"Price trends analysis requested: timeRange={time_range}, minPrice={min_price}, maxPrice={max_price}, resort={resort}")

        # Get storage manager and fetch data
        storage = get_storage_manager()

        # Get entries for the specified time range (in months)
        from datetime import datetime, timedelta
        cutoff_date = datetime.now().date() - timedelta(days=time_range * 30)

        entries = storage.query_entries_optimized(
            limit=10000,
            sort_by='sent_date',
            sort_order='desc'
        )

        logger.info(f"Retrieved {len(entries)} total entries from storage")

        # Debug: Check a few sample entries
        if entries:
            sample_entry = entries[0]
            logger.info(f"Sample entry: resort='{sample_entry.resort}', price_per_point={sample_entry.price_per_point}, sent_date={sample_entry.sent_date}")

        # Filter entries by date, price range, and resort
        filtered_entries = []
        date_filtered = 0
        price_filtered = 0
        resort_filtered = 0

        for entry in entries:
            # Check date filter
            if not entry.sent_date or entry.sent_date < cutoff_date:
                date_filtered += 1
                continue

            # Check price filter
            if not entry.price_per_point or entry.price_per_point <= 0:
                price_filtered += 1
                continue

            if entry.price_per_point < min_price or entry.price_per_point > max_price:
                price_filtered += 1
                continue

            # Check resort filter
            if resort and entry.resort != resort:
                resort_filtered += 1
                continue

            filtered_entries.append(entry)

        logger.info(f"Filtering results: date_filtered={date_filtered}, price_filtered={price_filtered}, resort_filtered={resort_filtered}")
        logger.info(f"Final filtered entries: {len(filtered_entries)} entries matching criteria")

        # Debug: If we have resort filter, check what entries we found
        if resort and len(filtered_entries) > 0:
            resort_prices = [e.price_per_point for e in filtered_entries[:5]]
            resort_results = [e.result for e in filtered_entries[:5]]
            resort_dates = [e.sent_date.strftime('%Y-%m-%d') if e.sent_date else 'No date' for e in filtered_entries[:5]]
            logger.info(f"First 5 {resort} prices: {resort_prices}")
            logger.info(f"First 5 {resort} results: {resort_results}")
            logger.info(f"First 5 {resort} dates: {resort_dates}")

            # Count result types for the filtered resort
            taken_count = len([e for e in filtered_entries if e.result == 'taken'])
            passed_count = len([e for e in filtered_entries if e.result == 'passed'])
            pending_count = len([e for e in filtered_entries if e.result == 'pending'])
            logger.info(f"{resort} result summary: taken={taken_count}, passed={passed_count}, pending={pending_count}")
        elif resort and len(filtered_entries) == 0:
            logger.warning(f"No entries found for resort '{resort}' - checking if resort exists in data")
            # Get a sample of all resorts from the first 100 entries to help debug
            sample_resorts = list(set([e.resort for e in entries[:100] if e.resort]))
            logger.info(f"Sample resorts in data: {sorted(sample_resorts)}")

        # Calculate statistics manager for trends
        stats_manager = get_statistics_manager()
        price_trends = stats_manager.get_price_trends()

        # If no stored trends, calculate basic trends from filtered data
        if not price_trends and filtered_entries:
            calc = StatisticsCalculator()
            for entry in filtered_entries:
                calc.add_entry(entry)
            price_trends = calc.calculate_price_trends(days=time_range * 30)

        # Create time-based trends data from entries (monthly aggregation)
        trends_data = []
        if filtered_entries:
            logger.info(f"Processing {len(filtered_entries)} filtered entries for monthly aggregation")

            # Group entries by month
            monthly_data = {}
            valid_entries = 0
            for entry in filtered_entries:
                if entry.sent_date and entry.price_per_point and entry.price_per_point > 0:
                    month_key = entry.sent_date.strftime("%Y-%m")
                    if month_key not in monthly_data:
                        monthly_data[month_key] = []
                    monthly_data[month_key].append(entry)
                    valid_entries += 1

            logger.info(f"Valid entries for monthly aggregation: {valid_entries} out of {len(filtered_entries)}")
            logger.info(f"Created monthly data for {len(monthly_data)} months: {sorted(monthly_data.keys())}")

            # Calculate monthly statistics
            for month_key in sorted(monthly_data.keys()):
                entries = monthly_data[month_key]
                prices = [e.price_per_point for e in entries if e.price_per_point and e.price_per_point > 0]

                logger.info(f"Month {month_key}: {len(entries)} entries, {len(prices)} valid prices")

                if prices:
                    # Calculate result counts
                    taken = len([e for e in entries if e.result == 'taken'])
                    passed = len([e for e in entries if e.result == 'passed'])
                    pending = len([e for e in entries if e.result == 'pending'])
                    total = len(entries)

                    # Calculate ROFR rate - only include resolved entries (taken + passed) in calculation
                    # Pending entries are excluded since their outcome is unknown
                    resolved_entries = taken + passed
                    rofr_rate = (taken / resolved_entries * 100) if resolved_entries > 0 else 0

                    # Add detailed logging for debugging ROFR rate issues
                    logger.info(f"Month {month_key} ROFR breakdown: taken={taken}, passed={passed}, pending={pending}, total={total}")
                    logger.info(f"Month {month_key} resolved_entries={resolved_entries}, rofr_rate={rofr_rate}%")

                    # Log sample results for debugging
                    sample_results = [e.result for e in entries[:5]]
                    logger.info(f"Month {month_key} sample results: {sample_results}")

                    avg_price = round(sum(prices) / len(prices), 2)
                    min_price_val = round(min(prices), 2)
                    max_price_val = round(max(prices), 2)

                    # Calculate alternative ROFR rate including pending entries for comparison
                    total_non_pending = taken + passed
                    rofr_rate_with_pending = (taken / total * 100) if total > 0 else 0

                    logger.info(f"Month {month_key} stats: avg=${avg_price}, min=${min_price_val}, max=${max_price_val}")
                    logger.info(f"Month {month_key} ROFR rate (resolved only): {rofr_rate}% (taken={taken}, resolved={total_non_pending})")
                    logger.info(f"Month {month_key} ROFR rate (incl pending): {rofr_rate_with_pending:.2f}% (taken={taken}, total={total})")
                    logger.info(f"Month {month_key} sample prices: {prices[:3] if len(prices) > 3 else prices}")

                    trends_data.append({
                        'month': month_key,
                        'averagePrice': avg_price,
                        'minPrice': min_price_val,
                        'maxPrice': max_price_val,
                        'total': total,
                        'taken': taken,
                        'passed': passed,
                        'pending': pending,
                        'rofrRate': round(rofr_rate, 2),
                        'rofrRateWithPending': round(rofr_rate_with_pending, 2),
                        'resolvedEntries': total_non_pending
                    })

        logger.info(f"Generated {len(trends_data)} monthly trend data points")

        # Calculate overall statistics for summary
        overall_stats = {}
        if filtered_entries:
            all_prices = [e.price_per_point for e in filtered_entries if e.price_per_point and e.price_per_point > 0]
            if all_prices:
                # Calculate overall ROFR statistics
                overall_taken = len([e for e in filtered_entries if e.result == 'taken'])
                overall_passed = len([e for e in filtered_entries if e.result == 'passed'])
                overall_pending = len([e for e in filtered_entries if e.result == 'pending'])
                overall_resolved = overall_taken + overall_passed
                overall_rofr_rate = (overall_taken / overall_resolved * 100) if overall_resolved > 0 else 0

                logger.info(f"Overall ROFR stats: taken={overall_taken}, passed={overall_passed}, pending={overall_pending}")
                logger.info(f"Overall ROFR rate: {overall_rofr_rate:.2f}% (resolved entries only)")

                overall_stats = {
                    'averagePrice': round(sum(all_prices) / len(all_prices), 2),
                    'minPrice': round(min(all_prices), 2),
                    'maxPrice': round(max(all_prices), 2),
                    'overallROFRRate': round(overall_rofr_rate, 2),
                    'totalTaken': overall_taken,
                    'totalPassed': overall_passed,
                    'totalPending': overall_pending,
                    'totalResolved': overall_resolved
                }

        # Prepare response data in expected frontend format
        response_data = {
            'trends': trends_data,
            'summary': {
                'totalEntries': len(filtered_entries),
                'timeRangeMonths': time_range,
                'filtersApplied': {
                    'minPrice': min_price,
                    'maxPrice': max_price,
                    'resort': resort
                },
                'filters': {
                    'resort': resort
                },
                'dateRange': {
                    'from': cutoff_date.isoformat(),
                    'to': datetime.now().date().isoformat()
                },
                **overall_stats
            }
        }

        return create_success_response(response_data)

    except Exception as e:
        logger.error(f"Error in get_price_trends_analysis: {str(e)}", exc_info=True)
        return create_error_response("Internal server error")

@app.function_name(name="debug_resort_data")
@app.route(route="debug-resort-data", auth_level=func.AuthLevel.ANONYMOUS)
def debug_resort_data(req: func.HttpRequest) -> func.HttpResponse:
    """Debug endpoint to check resort data and ROFR entries."""
    try:
        resort = req.params.get('resort', 'VGC')
        limit = int(req.params.get('limit', '50'))

        logger.info(f"Debug resort data requested: resort={resort}, limit={limit}")

        # Get storage manager and fetch data
        storage = get_storage_manager()

        # Get all entries for the resort
        entries = storage.query_entries_optimized(
            limit=10000,
            sort_by='sent_date',
            sort_order='desc'
        )

        # Filter by resort
        resort_entries = [e for e in entries if e.resort == resort]

        logger.info(f"Found {len(resort_entries)} entries for resort {resort}")

        # Get recent entries within last 2 years
        from datetime import datetime, timedelta
        cutoff_date = datetime.now().date() - timedelta(days=24 * 30)  # 24 months
        recent_entries = [e for e in resort_entries if e.sent_date and e.sent_date >= cutoff_date]

        logger.info(f"Found {len(recent_entries)} recent entries (last 24 months) for resort {resort}")

        # Analyze results
        taken_entries = [e for e in recent_entries if e.result == 'taken']
        passed_entries = [e for e in recent_entries if e.result == 'passed']
        pending_entries = [e for e in recent_entries if e.result == 'pending']

        # Get sample entries for debugging
        sample_entries = recent_entries[:limit]
        sample_data = []

        for entry in sample_entries:
            sample_data.append({
                'username': entry.username,
                'price_per_point': entry.price_per_point,
                'points': entry.points,
                'resort': entry.resort,
                'sent_date': entry.sent_date.isoformat() if entry.sent_date else None,
                'result': entry.result,
                'result_date': entry.result_date.isoformat() if entry.result_date else None,
                'use_year': entry.use_year
            })

        # Check for other resort variations
        all_resorts = list(set([e.resort for e in entries if e.resort]))
        vgc_variations = [r for r in all_resorts if 'vgc' in r.lower() or 'grand' in r.lower() or 'californian' in r.lower()]

        response_data = {
            'resort_searched': resort,
            'total_entries_for_resort': len(resort_entries),
            'recent_entries_count': len(recent_entries),
            'result_breakdown': {
                'taken': len(taken_entries),
                'passed': len(passed_entries),
                'pending': len(pending_entries)
            },
            'rofr_rate_resolved_only': (len(taken_entries) / (len(taken_entries) + len(passed_entries)) * 100) if (len(taken_entries) + len(passed_entries)) > 0 else 0,
            'sample_entries': sample_data,
            'all_resort_codes_in_db': sorted(all_resorts),
            'possible_vgc_variations': vgc_variations,
            'cutoff_date': cutoff_date.isoformat(),
            'debug_info': {
                'total_entries_in_db': len(entries),
                'query_limit': limit
            }
        }

        return create_success_response(response_data)

    except Exception as e:
        logger.error(f"Error in debug_resort_data: {str(e)}", exc_info=True)
        return create_error_response("Internal server error")

@app.function_name(name="health_check")
@app.route(route="health", auth_level=func.AuthLevel.ANONYMOUS)
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint."""
    try:
        config = get_config()

        # Test database connection
        storage = get_storage_manager()
        _ = storage.query_entries_optimized(limit=1)

        return create_success_response({
            'status': 'healthy',
            'database': 'connected',
            'processor': 'complete_thread_processor',
            'config': {
                'caching_enabled': config['enable_caching'],
                'max_pages': config['max_pages'],
                'delay': config.get('delay', 0.05),
                'batch_size': config.get('batch_size', 200),
                'chunk_size': config.get('chunk_size', 50)
            }
        })

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return create_error_response(f"Health check failed: {str(e)}")

@app.function_name(name="handle_cors_preflight")
@app.route(route="{*path}", auth_level=func.AuthLevel.ANONYMOUS, methods=["OPTIONS"])
def handle_cors_preflight(req: func.HttpRequest) -> func.HttpResponse:
    """Handle CORS preflight requests."""
    return func.HttpResponse(
        "",
        status_code=200,
        headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, Accept-Encoding',
            'Access-Control-Max-Age': '86400'
        }
    )
