#!/usr/bin/env python3
"""
Optimized Azure Table Storage Manager for ROFR Data

This module provides an enhanced table storage manager with:
- Query optimization and indexing strategies
- Connection pooling and retry logic
- Batch operations for better performance
- Memory-efficient data processing
"""

import os
import logging
import hashlib
from datetime import datetime, date
from typing import Optional, Dict, Any, List
import threading
from dataclasses import dataclass
import time

from azure.data.tables import TableServiceClient
from azure.core.exceptions import AzureError, ResourceNotFoundError, HttpResponseError

from models import ROFREntry, ThreadInfo, TableStorageHelper, StatisticsData


@dataclass
class QueryStats:
    """Statistics for query performance monitoring."""
    query_count: int = 0
    total_time: float = 0.0

    last_query_time: Optional[datetime] = None

    @property
    def avg_query_time(self) -> float:
        return self.total_time / self.query_count if self.query_count > 0 else 0.0




class OptimizedAzureTableStorageManager:
    """
    Optimized Azure Table Storage Manager with advanced query optimization
    and performance monitoring.
    """

    def __init__(self, connection_string: str):
        """Initialize the optimized storage manager."""
        self.connection_string = connection_string
        self.logger = logging.getLogger(__name__)

        # Table names for different data types
        self.entries_table_name = os.environ.get("ENTRIES_TABLE_NAME", "entries")
        self.threads_table_name = os.environ.get("THREADS_TABLE_NAME", "threads")
        self.sessions_table_name = os.environ.get("SESSIONS_TABLE_NAME", "sessions")
        self.stats_table_name = os.environ.get("STATS_TABLE_NAME", "stats")

        # Performance monitoring
        self.query_stats = QueryStats()
        self._stats_lock = threading.Lock()

        # Connection management
        self._table_service = None
        self._entries_table_client = None
        self._threads_table_client = None
        self._sessions_table_client = None
        self._stats_table_client = None
        self._connection_lock = threading.Lock()

        # Query optimization settings
        self.max_retry_attempts = 3
        self.retry_delay = 1.0
        self.batch_size = 100
        self.max_concurrent_queries = 5



        # Initialize connections
        self._ensure_connections()
        self._ensure_tables_exist()

        # Initialize session tracking
        self._current_session_id = None

    def _ensure_connections(self):
        """Ensure table service and client connections are established."""
        with self._connection_lock:
            if not self._table_service:
                self._table_service = TableServiceClient.from_connection_string(
                    conn_str=self.connection_string
                )

            if not self._entries_table_client:
                self._entries_table_client = self._table_service.get_table_client(
                    table_name=self.entries_table_name
                )

            if not self._threads_table_client:
                self._threads_table_client = self._table_service.get_table_client(
                    table_name=self.threads_table_name
                )

            if not self._sessions_table_client:
                self._sessions_table_client = self._table_service.get_table_client(
                    table_name=self.sessions_table_name
                )

            if not self._stats_table_client:
                self._stats_table_client = self._table_service.get_table_client(
                    table_name=self.stats_table_name
                )

    def _ensure_tables_exist(self):
        """Ensure all required tables exist."""
        try:
            self._ensure_connections()

            # Create entries table
            if self._entries_table_client:
                self._entries_table_client.create_table()
                self.logger.info(f"Ensured table '{self.entries_table_name}' exists")

            # Create threads table
            if self._threads_table_client:
                self._threads_table_client.create_table()
                self.logger.info(f"Ensured table '{self.threads_table_name}' exists")

            # Create sessions table
            if self._sessions_table_client:
                self._sessions_table_client.create_table()
                self.logger.info(f"Ensured table '{self.sessions_table_name}' exists")

            # Create stats table
            if self._stats_table_client:
                self._stats_table_client.create_table()
                self.logger.info(f"Ensured table '{self.stats_table_name}' exists")

        except Exception as e:
            if "already exists" not in str(e).lower():
                self.logger.warning(f"Could not create tables: {e}")

    def _record_query_stats(self, query_time: float):
        """Record query performance statistics."""
        with self._stats_lock:
            self.query_stats.query_count += 1
            self.query_stats.total_time += query_time
            self.query_stats.last_query_time = datetime.utcnow()



    def _execute_with_retry(self, operation_func, max_retries: Optional[int] = None) -> Any:
        """Execute operation with retry logic."""
        max_retries = max_retries or self.max_retry_attempts
        last_exception = Exception("No attempts made")

        for attempt in range(max_retries):
            try:
                return operation_func()
            except (AzureError, HttpResponseError) as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    self.logger.warning(f"Operation failed (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"Operation failed after {max_retries} attempts: {e}")

        raise last_exception

    def query_entries_optimized(self,
                               resort: Optional[str] = None,
                               result: Optional[str] = None,
                               start_date: Optional[date] = None,
                               end_date: Optional[date] = None,
                               username: Optional[str] = None,
                               use_year: Optional[str] = None,
                               min_price: Optional[float] = None,
                               max_price: Optional[float] = None,
                               min_points: Optional[int] = None,
                               max_points: Optional[int] = None,
                               min_total_cost: Optional[float] = None,
                               exclude_result: Optional[str] = None,
                               sort_by: Optional[str] = None,
                               sort_order: Optional[str] = None,
                               offset: Optional[int] = None,
                               limit: Optional[int] = 1000) -> List[ROFREntry]:
        """
        Optimized query with performance optimizations.

        Key optimizations:
        1. Optimized filter expressions
        2. Projection optimization
        3. Batch processing
        4. Connection pooling
        """
        start_time = time.time()

        try:
            # Execute optimized query
            entries = self._execute_optimized_query(
                resort=resort,
                result=result,
                start_date=start_date,
                end_date=end_date,
                username=username,
                use_year=use_year,
                min_price=min_price,
                max_price=max_price,
                min_points=min_points,
                max_points=max_points,
                min_total_cost=min_total_cost,
                exclude_result=exclude_result,
                sort_by=sort_by,
                sort_order=sort_order,
                offset=offset,
                limit=limit if limit is not None else 10000
            )

            query_time = time.time() - start_time
            self._record_query_stats(query_time)

            self.logger.info(f"Query completed in {query_time:.2f}s, returned {len(entries)} entries")
            return entries

        except Exception as e:
            self.logger.error(f"Optimized query failed: {e}")
            raise

    def query_entries_with_count(self,
                                resort: Optional[str] = None,
                                result: Optional[str] = None,
                                start_date: Optional[date] = None,
                                end_date: Optional[date] = None,
                                username: Optional[str] = None,
                                use_year: Optional[str] = None,
                                min_price: Optional[float] = None,
                                max_price: Optional[float] = None,
                                min_points: Optional[int] = None,
                                max_points: Optional[int] = None,
                                min_total_cost: Optional[float] = None,
                                exclude_result: Optional[str] = None,
                                sort_by: Optional[str] = None,
                                sort_order: Optional[str] = None,
                                offset: Optional[int] = None,
                                limit: Optional[int] = 1000) -> tuple[List[ROFREntry], int]:
        """
        Get both paginated results and total count in one operation.
        Returns (entries, total_count)
        """
        start_time = time.time()

        try:
            # Execute optimized query to get all filtered entries
            all_entries = self._execute_optimized_query_for_count(
                resort=resort,
                result=result,
                start_date=start_date,
                end_date=end_date,
                username=username,
                use_year=use_year,
                min_price=min_price,
                max_price=max_price,
                min_points=min_points,
                max_points=max_points,
                min_total_cost=min_total_cost,
                exclude_result=exclude_result,
                sort_by=sort_by,
                sort_order=sort_order
            )

            total_count = len(all_entries)

            # Apply pagination
            start_index = offset if offset is not None else 0
            end_index = start_index + limit if limit else len(all_entries)
            paginated_entries = all_entries[start_index:end_index]

            query_time = time.time() - start_time
            self._record_query_stats(query_time)

            self.logger.info(f"Query with count completed in {query_time:.2f}s, returned {len(paginated_entries)}/{total_count} entries")
            return paginated_entries, total_count

        except Exception as e:
            self.logger.error(f"Optimized query with count failed: {e}")
            raise

    def _execute_optimized_query(self,
                                resort: Optional[str] = None,
                                result: Optional[str] = None,
                                start_date: Optional[date] = None,
                                end_date: Optional[date] = None,
                                username: Optional[str] = None,
                                use_year: Optional[str] = None,
                                min_price: Optional[float] = None,
                                max_price: Optional[float] = None,
                                min_points: Optional[int] = None,
                                max_points: Optional[int] = None,
                                min_total_cost: Optional[float] = None,
                                exclude_result: Optional[str] = None,
                                sort_by: Optional[str] = None,
                                sort_order: Optional[str] = None,
                                offset: Optional[int] = None,
                                limit: Optional[int] = 1000) -> List[ROFREntry]:
        """Execute the actual optimized query with advanced filtering."""

        def query_operation():
            # Handle None limit
            effective_limit = limit if limit is not None else 10000

            # Build optimized filter expression
            filters = []

            # Resort filter - use partition key when possible for better performance
            if resort:
                sanitized_resort, _ = TableStorageHelper.validate_entity_keys(resort, "dummy")
                # Use partition key filter for maximum efficiency
                filters.append(f"PartitionKey eq '{sanitized_resort}'")
                # Also filter by resort field for data consistency
                filters.append(f"resort eq '{resort}'")

            # Result filter
            if result:
                filters.append(f"result eq '{result}'")

            # Username filter
            if username:
                filters.append(f"username eq '{username}'")

            # Date filters - optimized for Azure Table Storage
            if start_date:
                date_str = start_date.isoformat()
                filters.append(f"sent_date ge '{date_str}'")

            if end_date:
                date_str = end_date.isoformat()
                filters.append(f"sent_date le '{date_str}'")

            # Use year filter
            if use_year:
                filters.append(f"use_year eq '{use_year}'")

            # Price filters - convert to float for comparison
            if min_price is not None:
                filters.append(f"price_per_point ge {min_price}")

            if max_price is not None:
                filters.append(f"price_per_point le {max_price}")

            # Points filters - convert to int for comparison
            if min_points is not None:
                filters.append(f"points ge {min_points}")

            if max_points is not None:
                filters.append(f"points le {max_points}")

            # Total cost filter
            if min_total_cost is not None:
                filters.append(f"total_cost ge {min_total_cost}")

            # Exclude result filter
            if exclude_result:
                filters.append(f"result ne '{exclude_result}'")

            # Combine filters
            filter_expression = " and ".join(filters) if filters else None

            # Execute query with optimization
            self._ensure_connections()
            if not self._entries_table_client:
                raise AzureError("Entries table client not initialized")
            entities = self._entries_table_client.query_entities(
                query_filter=filter_expression or "",
                results_per_page=min(effective_limit, 1000),  # Optimize page size
                select=[
                    'PartitionKey', 'RowKey', 'username', 'price_per_point',
                    'total_cost', 'points', 'resort', 'use_year', 'points_details',
                    'sent_date', 'raw_entry' 'result', 'result_date', 'thread_url'
                ]  # Only select needed columns
            )

            # Process entities efficiently
            entries = []
            processed_count = 0

            for entity in entities:
                try:
                    # Additional client-side filtering for edge cases
                    if self._should_include_entity_advanced(entity, resort, result, start_date, end_date, username,
                                                          use_year, min_price, max_price, min_points, max_points,
                                                          min_total_cost, exclude_result):
                        entries.append(ROFREntry.from_table_entity(entity))

                    processed_count += 1

                    # Prevent runaway queries
                    if processed_count > effective_limit * 3:
                        self.logger.warning(f"Breaking query after processing {processed_count} entities")
                        break

                except Exception as e:
                    self.logger.warning(f"Error processing entity: {e}")
                    continue

            # Apply sorting
            if sort_by and entries:
                reverse_order = sort_order == 'desc' if sort_order else True

                def get_sort_key(entry):
                    if sort_by == 'sent_date':
                        return entry.sent_date or date.min
                    elif sort_by == 'result_date':
                        return entry.result_date or date.min
                    elif sort_by == 'price_per_point':
                        return float(entry.price_per_point) if entry.price_per_point else 0.0
                    elif sort_by == 'total_cost':
                        return float(entry.total_cost) if entry.total_cost else 0.0
                    elif sort_by == 'points':
                        return int(entry.points) if entry.points else 0
                    elif sort_by == 'username':
                        return entry.username or ''
                    elif sort_by == 'resort':
                        return entry.resort or ''
                    else:
                        return entry.sent_date or date.min

                try:
                    entries.sort(key=get_sort_key, reverse=reverse_order)
                except Exception as e:
                    self.logger.warning(f"Error sorting entries: {e}")

            # Apply pagination
            start_index = offset if offset is not None else 0
            end_index = start_index + effective_limit if effective_limit else len(entries)

            paginated_entries = entries[start_index:end_index]

            return paginated_entries

        return self._execute_with_retry(query_operation)

    def _execute_optimized_query_for_count(self,
                                          resort: Optional[str] = None,
                                          result: Optional[str] = None,
                                          start_date: Optional[date] = None,
                                          end_date: Optional[date] = None,
                                          username: Optional[str] = None,
                                          use_year: Optional[str] = None,
                                          min_price: Optional[float] = None,
                                          max_price: Optional[float] = None,
                                          min_points: Optional[int] = None,
                                          max_points: Optional[int] = None,
                                          min_total_cost: Optional[float] = None,
                                          exclude_result: Optional[str] = None,
                                          sort_by: Optional[str] = None,
                                          sort_order: Optional[str] = None) -> List[ROFREntry]:
        """Execute query to get all entries for count and sorting."""

        def query_operation():
            # Build optimized filter expression
            filters = []

            # Resort filter - use partition key when possible for better performance
            if resort:
                sanitized_resort, _ = TableStorageHelper.validate_entity_keys(resort, "dummy")
                # Use partition key filter for maximum efficiency
                filters.append(f"PartitionKey eq '{sanitized_resort}'")
                # Also filter by resort field for data consistency
                filters.append(f"resort eq '{resort}'")

            # Result filter
            if result:
                filters.append(f"result eq '{result}'")

            # Username filter
            if username:
                filters.append(f"username eq '{username}'")

            # Date filters - optimized for Azure Table Storage
            if start_date:
                date_str = start_date.isoformat()
                filters.append(f"sent_date ge '{date_str}'")

            if end_date:
                date_str = end_date.isoformat()
                filters.append(f"sent_date le '{date_str}'")

            # Use year filter
            if use_year:
                filters.append(f"use_year eq '{use_year}'")

            # Price filters - convert to float for comparison
            if min_price is not None:
                filters.append(f"price_per_point ge {min_price}")

            if max_price is not None:
                filters.append(f"price_per_point le {max_price}")

            # Points filters - convert to int for comparison
            if min_points is not None:
                filters.append(f"points ge {min_points}")

            if max_points is not None:
                filters.append(f"points le {max_points}")

            # Total cost filter
            if min_total_cost is not None:
                filters.append(f"total_cost ge {min_total_cost}")

            # Exclude result filter
            if exclude_result:
                filters.append(f"result ne '{exclude_result}'")

            # Combine filters
            filter_expression = " and ".join(filters) if filters else None

            # Execute query with connection management
            self._ensure_connections()
            if not self._entries_table_client:
                raise Exception("Table client not initialized")

            # Query with filter and select optimizations
            entities = list(self._entries_table_client.query_entities(
                query_filter=filter_expression,
                select=[
                    'PartitionKey', 'RowKey', 'username', 'price_per_point',
                    'total_cost', 'points', 'resort', 'use_year', 'points_details',
                    'sent_date', 'result', 'result_date', 'thread_url'
                ]  # Only select needed columns
            ))

            # Process entities efficiently
            entries = []
            processed_count = 0

            for entity in entities:
                try:
                    # Additional client-side filtering for edge cases
                    if self._should_include_entity_advanced(entity, resort, result, start_date, end_date, username,
                                                          use_year, min_price, max_price, min_points, max_points,
                                                          min_total_cost, exclude_result):
                        entries.append(ROFREntry.from_table_entity(entity))

                    processed_count += 1

                    # Prevent runaway queries - but allow more for count operations
                    if processed_count > 50000:
                        self.logger.warning(f"Breaking query after processing {processed_count} entities")
                        break

                except Exception as e:
                    self.logger.warning(f"Error processing entity: {e}")
                    continue

            # Apply sorting if specified
            if sort_by and entries:
                reverse_order = sort_order == 'desc' if sort_order else True

                def get_sort_key(entry):
                    if sort_by == 'sent_date':
                        return entry.sent_date or date.min
                    elif sort_by == 'result_date':
                        return entry.result_date or date.min
                    elif sort_by == 'price_per_point':
                        return float(entry.price_per_point) if entry.price_per_point else 0.0
                    elif sort_by == 'total_cost':
                        return float(entry.total_cost) if entry.total_cost else 0.0
                    elif sort_by == 'points':
                        return int(entry.points) if entry.points else 0
                    elif sort_by == 'username':
                        return entry.username or ''
                    elif sort_by == 'resort':
                        return entry.resort or ''
                    else:
                        return entry.sent_date or date.min

                try:
                    entries.sort(key=get_sort_key, reverse=reverse_order)
                except Exception as e:
                    self.logger.warning(f"Error sorting entries: {e}")

            return entries

        return self._execute_with_retry(query_operation)

    def _should_include_entity_advanced(self, entity: Dict[str, Any],
                                      resort: Optional[str] = None,
                                      result: Optional[str] = None,
                                      start_date: Optional[date] = None,
                                      end_date: Optional[date] = None,
                                      username: Optional[str] = None,
                                      use_year: Optional[str] = None,
                                      min_price: Optional[float] = None,
                                      max_price: Optional[float] = None,
                                      min_points: Optional[int] = None,
                                      max_points: Optional[int] = None,
                                      min_total_cost: Optional[float] = None,
                                      exclude_result: Optional[str] = None) -> bool:
        """Additional client-side filtering for precise results."""

        # Resort filter
        if resort and entity.get('resort') != resort:
            return False

        # Result filter
        if result and entity.get('result') != result:
            return False

        # Username filter
        if username and entity.get('username') != username:
            return False

        # Use year filter
        if use_year and entity.get('use_year') != use_year:
            return False

        # Price filters
        if min_price is not None:
            entity_price = entity.get('price_per_point')
            if not entity_price or float(entity_price) < min_price:
                return False

        if max_price is not None:
            entity_price = entity.get('price_per_point')
            if not entity_price or float(entity_price) > max_price:
                return False

        # Points filters
        if min_points is not None:
            entity_points = entity.get('points')
            if not entity_points or int(entity_points) < min_points:
                return False

        if max_points is not None:
            entity_points = entity.get('points')
            if not entity_points or int(entity_points) > max_points:
                return False

        # Total cost filter
        if min_total_cost is not None:
            entity_cost = entity.get('total_cost')
            if not entity_cost or float(entity_cost) < min_total_cost:
                return False

        # Exclude result filter
        if exclude_result and entity.get('result') == exclude_result:
            return False

        # Date filtering with robust parsing
        if start_date or end_date:
            entity_date_str = entity.get('sent_date', '')
            if entity_date_str:
                try:
                    # Handle different date formats
                    if 'T' in entity_date_str:
                        entity_date = datetime.fromisoformat(entity_date_str.split('T')[0]).date()
                    else:
                        entity_date = datetime.fromisoformat(entity_date_str).date()

                    if start_date and entity_date < start_date:
                        return False
                    if end_date and entity_date > end_date:
                        return False

                except (ValueError, TypeError):
                    # Skip entities with invalid dates
                    return False

        return True

    def get_statistics_optimized(self) -> Dict[str, Any]:
        """Get optimized statistics."""
        start_time = time.time()

        try:
            def stats_operation():
                # Use optimized projection query
                self._ensure_connections()
                if not self._entries_table_client:
                    raise AzureError("Entries table client not initialized")
                entities = list(self._entries_table_client.query_entities(
                    query_filter="",
                    select=['resort', 'result', 'sent_date', 'price_per_point', 'username']
                ))

                # Process statistics efficiently
                stats = self._calculate_statistics_efficiently(entities)
                return stats

            stats = self._execute_with_retry(stats_operation)

            query_time = time.time() - start_time
            self._record_query_stats(query_time)

            return stats

        except Exception as e:
            self.logger.error(f"Error getting optimized statistics: {e}")
            raise

    def _calculate_statistics_efficiently(self, entities) -> Dict[str, Any]:
        """Calculate statistics with memory-efficient processing."""
        total_entries = 0
        resort_counts = {}
        result_counts = {'pending': 0, 'passed': 0, 'taken': 0}
        price_sum = 0.0
        price_count = 0
        latest_entry_date = None
        unique_users = set()

        # Process entities in batches to manage memory
        batch_size = 1000
        batch = []

        for entity in entities:
            batch.append(entity)

            if len(batch) >= batch_size:
                self._process_statistics_batch(
                    batch, resort_counts, result_counts, unique_users
                )
                batch = []

            total_entries += 1

            # Process price data
            price = entity.get('price_per_point')
            if price and isinstance(price, (int, float)) and price > 0:
                price_sum += price
                price_count += 1

            # Process date data
            sent_date_str = entity.get('sent_date', '')
            if sent_date_str:
                try:
                    sent_date = datetime.fromisoformat(sent_date_str.split('T')[0]).date()
                    if latest_entry_date is None:
                        latest_entry_date = sent_date
                    elif sent_date > latest_entry_date:
                        latest_entry_date = sent_date
                except (ValueError, TypeError):
                    pass

        # Process remaining batch
        if batch:
            self._process_statistics_batch(
                batch, resort_counts, result_counts, unique_users
            )

        # Calculate derived statistics
        avg_price_per_point = price_sum / price_count if price_count > 0 else 0
        rofr_rate = (result_counts['taken'] / total_entries * 100) if total_entries > 0 else 0

        # Get top resorts
        top_resorts = sorted(
            [{'resort': k, 'count': v} for k, v in resort_counts.items()],
            key=lambda x: x['count'],
            reverse=True
        )[:10]

        return {
            'total_entries': total_entries,
            'resort_counts': resort_counts,
            'result_counts': result_counts,
            'latest_entry_date': latest_entry_date.isoformat() if latest_entry_date else None,
            'unique_resorts': len(resort_counts),
            'unique_users': len(unique_users),
            'avg_price_per_point': round(avg_price_per_point, 2),
            'rofr_rate': round(rofr_rate, 2),
            'top_resorts': top_resorts,
            'taken_count': result_counts['taken'],
            'passed_count': result_counts['passed'],
            'pending_count': result_counts['pending'],
            'active_resorts': len([r for r, c in resort_counts.items() if c > 0]),
            'last_updated': datetime.utcnow().isoformat() + 'Z'
        }

    def _process_statistics_batch(self, batch: List[Dict[str, Any]],
                                 resort_counts: Dict[str, int],
                                 result_counts: Dict[str, int],
                                 unique_users: set):
        """Process a batch of entities for statistics calculation."""
        for entity in batch:
            # Resort counts
            resort = entity.get('resort', 'Unknown')
            resort_counts[resort] = resort_counts.get(resort, 0) + 1

            # Result counts
            result = entity.get('result', 'pending')
            if result in result_counts:
                result_counts[result] += 1

            # Unique users
            username = entity.get('username')
            if username:
                unique_users.add(username)

    def batch_upsert_entries(self, entries: List[ROFREntry]) -> Dict[str, int]:
        """Optimized batch upsert entries for better performance with reduced error handling overhead."""
        if not entries:
            return {'success': 0, 'failed': 0}

        success_count = 0
        failed_count = 0

        # Deduplicate entries by row key to prevent batch errors
        unique_entries = {}
        duplicate_count = 0
        for entry in entries:
            entity = entry.to_table_entity()
            row_key = entity['RowKey']
            # Keep the latest entry if duplicates exist
            if row_key in unique_entries:
                duplicate_count += 1
            unique_entries[row_key] = entry

        # Convert back to list
        deduplicated_entries = list(unique_entries.values())

        if duplicate_count > 0:
            self.logger.info(f"Deduplicated {duplicate_count} duplicate entries from batch of {len(entries)} entries")

        # Group entries by partition key for better batch performance
        partitioned_entries = {}
        for entry in deduplicated_entries:
            entity = entry.to_table_entity()
            partition_key = entity['PartitionKey']
            if partition_key not in partitioned_entries:
                partitioned_entries[partition_key] = []
            partitioned_entries[partition_key].append(entry)

        # Process each partition separately in batches
        for partition_key, partition_entries in partitioned_entries.items():
            for i in range(0, len(partition_entries), self.batch_size):
                batch = partition_entries[i:i + self.batch_size]

                try:
                    def batch_operation():
                        operations = []
                        batch_row_keys = set()
                        for entry in batch:
                            entity = entry.to_table_entity()
                            row_key = entity['RowKey']
                            # Skip if we've already seen this row key in this batch
                            if row_key not in batch_row_keys:
                                operations.append(('upsert', entity))
                                batch_row_keys.add(row_key)

                        # Submit batch transaction
                        self._ensure_connections()
                        if not self._entries_table_client:
                            raise AzureError("Entries table client not initialized")
                        self._entries_table_client.submit_transaction(operations)
                        return len(operations)

                    batch_success = self._execute_with_retry(batch_operation)
                    success_count += batch_success

                except Exception as e:
                    self.logger.warning(f"Batch upsert failed for partition {partition_key}, batch {i//self.batch_size + 1}: {e}")
                    # Skip individual fallbacks for better performance - just count as failed
                    failed_count += len(batch)

        # Clear caches only once after all batches
        if success_count > 0:
            pass  # Cache clearing removed

        return {'success': success_count, 'failed': failed_count}

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for monitoring."""
        with self._stats_lock:
            return {
                'query_count': self.query_stats.query_count,
                'total_query_time': self.query_stats.total_time,
                'avg_query_time': self.query_stats.avg_query_time,
                'last_query_time': self.query_stats.last_query_time.isoformat() if self.query_stats.last_query_time else None
            }



    def optimize_table_performance(self):
        """Perform table optimization operations."""
        try:
            # Clear expired cache entries
            # Cache optimization removed
            pass

            self.logger.info("Cache optimization skipped - caching disabled")

            # Reset performance statistics periodically
            with self._stats_lock:
                if self.query_stats.query_count > 10000:
                    old_stats = self.query_stats
                    self.query_stats = QueryStats()
                    self.logger.info(f"Reset performance stats. Previous stats: {old_stats.__dict__}")

        except Exception as e:
            self.logger.error(f"Error during table optimization: {e}")

    # Delegate methods to maintain compatibility with original interface
    def upsert_entry(self, entry: ROFREntry) -> tuple:
        """Upsert single entry with existence checking to track new vs updated entries."""
        try:
            def upsert_operation():
                entity = entry.to_table_entity()
                self._ensure_connections()
                if not self._entries_table_client:
                    raise AzureError("Entries table client not initialized")

                # Check if entity exists first to track new vs updated
                existed = False
                try:
                    existing_entity = self._entries_table_client.get_entity(
                        partition_key=entity['PartitionKey'],
                        row_key=entity['RowKey']
                    )
                    existed = True
                    self.logger.debug(f"Found existing entry: {entity['PartitionKey']}/{entity['RowKey']}")
                except ResourceNotFoundError:
                    self.logger.debug(f"Creating new entry: {entity['PartitionKey']}/{entity['RowKey']}")
                    existed = False
                except Exception as e:
                    self.logger.warning(f"Error checking entity existence: {e}, proceeding with upsert")
                    existed = False

                # Perform the upsert
                self._entries_table_client.upsert_entity(entity=entity)

                # Return appropriate tuple based on whether entry existed
                if existed:
                    return (False, True)  # was_new=False, was_updated=True
                else:
                    return (True, False)  # was_new=True, was_updated=False

            result = self._execute_with_retry(upsert_operation)

            # Clear relevant caches less frequently to improve performance
            # With individual operations, clear every 50 operations to balance performance and accuracy
            if not hasattr(self, '_upsert_counter'):
                self._upsert_counter = 0

            self._upsert_counter += 1
            # Cache clearing removed
            pass

            return result

        except Exception as e:
            self.logger.error(f"Error upserting entry: {e}")
            return (False, False)

    def get_entry(self, partition_key: str, row_key: str) -> Optional[ROFREntry]:
        """Get single entry."""
        try:
            def get_operation():
                self._ensure_connections()
                if not self._entries_table_client:
                    raise Exception("Entries table client not initialized")

                try:
                    entity = self._entries_table_client.get_entity(
                        partition_key=partition_key,
                        row_key=row_key
                    )
                    return ROFREntry.from_dict(entity)
                except ResourceNotFoundError:
                    return None

            entry = self._execute_with_retry(get_operation)
            return entry

        except Exception as e:
            self.logger.error(f"Error getting entry {partition_key}/{row_key}: {e}")
            return None

    # Maintain compatibility with original interface
    def query_entries(self, **kwargs) -> List[ROFREntry]:
        """Wrapper for backward compatibility."""
        return self.query_entries_optimized(**kwargs)

    def get_statistics(self) -> Dict[str, Any]:
        """Wrapper for backward compatibility."""
        return self.get_statistics_optimized()

    def get_thread_info(self, thread_url: str) -> Optional[Dict[str, Any]]:
        """Get thread information from storage."""
        try:
            url_hash = hashlib.md5(thread_url.encode()).hexdigest()

            def get_thread_operation():
                self._ensure_connections()
                if not self._threads_table_client:
                    raise AzureError("Threads table client not initialized")
                entity = self._threads_table_client.get_entity(
                    partition_key='thread',
                    row_key=url_hash
                )
                return {
                    'url': entity.get('url', ''),
                    'title': entity.get('title', ''),
                    'start_year': int(entity.get('start_year', 0)) if entity.get('start_year') else None,
                    'end_year': int(entity.get('end_year', 0)) if entity.get('end_year') else None,
                    'start_month': entity.get('start_month', ''),
                    'end_month': entity.get('end_month', ''),
                    'last_scraped_page': int(entity.get('last_scraped_page', 0)),
                    'total_pages': int(entity.get('total_pages', 0)) if entity.get('total_pages') else None,
                    'thread_start_date': entity.get('thread_start_date', ''),
                    'thread_end_date': entity.get('thread_end_date', ''),
                    'created_at': entity.get('created_at', ''),
                    'updated_at': entity.get('updated_at', '')
                }

            return self._execute_with_retry(get_thread_operation)
        except ResourceNotFoundError:
            return None
        except Exception as e:
            self.logger.error(f"Error getting thread info: {e}")
            return None

    def upsert_thread(self, thread_info: 'ThreadInfo') -> str:
        """Upsert thread information and return thread ID."""
        try:
            def upsert_thread_operation():
                entity = thread_info.to_table_entity()
                self._ensure_connections()
                if not self._threads_table_client:
                    raise AzureError("Threads table client not initialized")

                self._threads_table_client.upsert_entity(entity=entity)
                return entity['RowKey']

            return self._execute_with_retry(upsert_thread_operation)
        except Exception as e:
            self.logger.error(f"Error upserting thread: {e}")
            raise

    def update_thread_info(self, thread_info: 'ThreadInfo') -> str:
        """Update thread information by upserting all properties."""
        return self.upsert_thread(thread_info)

    def safe_upsert_thread(self, thread_info: 'ThreadInfo') -> str:
        """Upsert thread information, updating all properties."""
        return self.upsert_thread(thread_info)




    def start_scrape_session(self) -> str:
        """Start a new scraping session and return session ID."""
        import uuid

        # Generate and validate session ID
        session_id = str(uuid.uuid4())
        if not session_id or len(session_id.strip()) == 0:
            raise ValueError("Failed to generate valid session ID")

        session_id = session_id.strip()
        self._current_session_id = session_id

        try:
            def start_session_operation():
                # Create session metadata entry with special RowKey
                session_id_str = str(session_id)

                entity = {
                    'PartitionKey': session_id_str,
                    'RowKey': 'session_metadata',
                    'session_id': session_id_str,
                    'started_at': datetime.utcnow().isoformat() + 'Z',
                    'status': 'initializing',
                    'total_threads': 0,
                    'completed_threads': 0,
                    'total_entries': 0,
                    'new_entries': 0,
                    'updated_entries': 0,
                    'created_by': 'start_scrape_session'
                }

                self._ensure_connections()
                if not self._sessions_table_client:
                    raise AzureError("Sessions table client not initialized")

                self._sessions_table_client.upsert_entity(entity=entity)
                self.logger.info(f"Created session metadata for session: {session_id_str}")

                return session_id_str

            result_session_id = self._execute_with_retry(start_session_operation)

            if not result_session_id or str(result_session_id).strip() == '':
                raise ValueError("Session creation failed: returned empty session ID")

            return result_session_id

        except Exception as e:
            self.logger.error(f"Error starting scrape session: {e}")
            raise

    def update_session_metadata(self, session_id: str, **kwargs):
        """Update session metadata by upserting all properties."""
        try:
            if session_id is None or str(session_id).strip() == '':
                self.logger.error("Cannot update session with empty or None session_id")
                raise ValueError("session_id cannot be None or empty")

            session_id = str(session_id).strip()

            def update_operation():
                self._ensure_connections()
                if not self._sessions_table_client:
                    raise AzureError("Sessions table client not initialized")

                # Create entity with all properties
                entity = {
                    'PartitionKey': session_id,
                    'RowKey': 'session_metadata',
                    'session_id': session_id,
                    'started_at': datetime.utcnow().isoformat() + 'Z',
                    'status': 'running',
                    'total_threads': 0,
                    'completed_threads': 0,
                    'total_entries': 0,
                    'new_entries': 0,
                    'updated_entries': 0
                }

                # Update with provided kwargs
                for key, value in kwargs.items():
                    if key == 'status' and value in ['completed', 'failed']:
                        entity['completed_at'] = datetime.utcnow().isoformat() + 'Z'

                    if value is None:
                        entity[key] = ''
                    else:
                        entity[key] = str(value)

                entity['updated_at'] = datetime.utcnow().isoformat() + 'Z'

                # Always upsert all properties
                self._sessions_table_client.upsert_entity(entity=entity)

            self._execute_with_retry(update_operation)
        except Exception as e:
            self.logger.error(f"Error updating session metadata {session_id}: {e}")
            raise

    def add_thread_to_session(self, session_id: str, thread_url: str, thread_title: str = "",
                             start_page: int = 1, **thread_data):
        """Add a thread entry to the session table."""
        try:
            if not session_id or not thread_url:
                raise ValueError("session_id and thread_url are required")

            session_id = str(session_id).strip()
            thread_url = str(thread_url).strip()

            # Create MD5 hash of thread URL for RowKey
            thread_hash = hashlib.md5(thread_url.encode('utf-8')).hexdigest()

            def add_thread_operation():
                self._ensure_connections()
                if not self._sessions_table_client:
                    raise AzureError("Sessions table client not initialized")

                entity = {
                    'PartitionKey': session_id,
                    'RowKey': thread_hash,
                    'session_id': session_id,
                    'thread_url': thread_url,
                    'thread_title': thread_title,
                    'thread_hash': thread_hash,
                    'status': 'queued',
                    'start_page': str(start_page),
                    'current_page': str(start_page),
                    'pages_processed': '0',
                    'entries_found': '0',
                    'new_entries': '0',
                    'updated_entries': '0',
                    'created_at': datetime.utcnow().isoformat() + 'Z',
                    'updated_at': datetime.utcnow().isoformat() + 'Z'
                }

                # Add any additional thread data
                for key, value in thread_data.items():
                    if value is not None:
                        entity[key] = str(value)

                self._sessions_table_client.upsert_entity(entity=entity)
                self.logger.debug(f"Added thread {thread_hash} to session {session_id}")

            self._execute_with_retry(add_thread_operation)
            return thread_hash

        except Exception as e:
            self.logger.error(f"Error adding thread to session {session_id}: {e}")
            raise

    def update_thread_progress(self, session_id: str, thread_url: str, **progress_data):
        """Update thread processing progress by upserting all properties."""
        # Initialize thread_hash early for error handling
        thread_hash = "unknown"

        try:
            if not session_id or not thread_url:
                raise ValueError("session_id and thread_url are required")

            session_id = str(session_id).strip()
            thread_hash = hashlib.md5(thread_url.encode('utf-8')).hexdigest()

            def update_operation():
                self._ensure_connections()
                if not self._sessions_table_client:
                    raise AzureError("Sessions table client not initialized")

                # Create entity with default values
                entity = {
                    'PartitionKey': session_id,
                    'RowKey': thread_hash,
                    'thread_url': thread_url,
                    'thread_hash': thread_hash,
                    'status': 'processing',
                    'start_page': '1',
                    'current_page': '1',
                    'pages_processed': '0',
                    'entries_found': '0',
                    'new_entries': '0',
                    'updated_entries': '0',
                    'created_at': datetime.utcnow().isoformat() + 'Z',
                    'updated_at': datetime.utcnow().isoformat() + 'Z'
                }

                # Update with progress data
                for key, value in progress_data.items():
                    if value is not None:
                        entity[key] = str(value)

                entity['updated_at'] = datetime.utcnow().isoformat() + 'Z'

                # Always upsert all properties
                self._sessions_table_client.upsert_entity(entity=entity)

            self._execute_with_retry(update_operation)

        except Exception as e:
            self.logger.error(f"Error updating thread progress {thread_hash}: {e}")
            raise

    def update_thread_progress_batch(self, session_id: str, thread_url: str, **progress_data):
        """Update thread processing progress by upserting all properties (batch alias)."""
        return self.update_thread_progress(session_id, thread_url, **progress_data)

    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get aggregated session summary from all thread entries."""
        try:
            if not session_id:
                return None

            session_id = str(session_id).strip()

            def get_summary_operation():
                self._ensure_connections()
                if not self._sessions_table_client:
                    raise AzureError("Sessions table client not initialized")

                # Query all entries for this session
                filter_query = f"PartitionKey eq '{session_id}'"
                entities = list(self._sessions_table_client.query_entities(query_filter=filter_query))

                if not entities:
                    return None

                # Find metadata entry
                metadata = None
                threads = []

                for entity in entities:
                    if entity.get('RowKey') == 'session_metadata':
                        metadata = dict(entity)
                    else:
                        threads.append(dict(entity))

                if not metadata:
                    return None

                # Aggregate thread statistics
                total_threads = len(threads)
                completed_threads = len([t for t in threads if t.get('status') == 'completed'])
                total_entries = sum(int(t.get('entries_found', 0)) for t in threads)
                new_entries = sum(int(t.get('new_entries', 0)) for t in threads)
                updated_entries = sum(int(t.get('updated_entries', 0)) for t in threads)

                return {
                    'session_id': session_id,
                    'status': metadata.get('status'),
                    'started_at': metadata.get('started_at'),
                    'completed_at': metadata.get('completed_at'),
                    'updated_at': metadata.get('updated_at'),
                    'total_threads': total_threads,
                    'completed_threads': completed_threads,
                    'total_entries': total_entries,
                    'new_entries': new_entries,
                    'updated_entries': updated_entries,
                    'threads': threads
                }

            return self._execute_with_retry(get_summary_operation)

        except Exception as e:
            self.logger.error(f"Error getting session summary {session_id}: {e}")
            return None

    def get_session_details(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session metadata safely with validation."""
        try:
            if not session_id or str(session_id).strip() == '':
                self.logger.error("Cannot get session with empty or None session_id")
                return None

            session_id = str(session_id).strip()

            def get_session_operation():
                self._ensure_connections()
                if not self._sessions_table_client:
                    raise AzureError("Sessions table client not initialized")

                try:
                    entity = self._sessions_table_client.get_entity(
                        partition_key=session_id,
                        row_key='session_metadata'
                    )
                    return dict(entity)
                except ResourceNotFoundError:
                    self.logger.debug(f"Session metadata {session_id} not found")
                    return None

            return self._execute_with_retry(get_session_operation)
        except Exception as e:
            self.logger.error(f"Error getting session details for {session_id}: {e}")
            return None

    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists."""
        session_details = self.get_session_details(session_id)
        return session_details is not None

    def check_and_update_session_completion(self, session_id: str) -> bool:
        """Check if all threads in a session are completed and update session status."""
        try:
            if not session_id:
                return False

            session_id = str(session_id).strip()

            def check_completion_operation():
                self._ensure_connections()
                if not self._sessions_table_client:
                    raise AzureError("Sessions table client not initialized")

                # Get all threads for this session
                filter_query = f"PartitionKey eq '{session_id}' and RowKey ne 'session_metadata'"
                thread_entities = list(self._sessions_table_client.query_entities(query_filter=filter_query))

                if not thread_entities:
                    self.logger.warning(f"No threads found for session {session_id}")
                    return False

                # Check completion status
                total_threads = len(thread_entities)
                completed_threads = 0
                total_entries = 0
                new_entries = 0
                updated_entries = 0

                for thread in thread_entities:
                    if thread.get('status') == 'completed':
                        completed_threads += 1

                    total_entries += int(thread.get('entries_found', 0))
                    new_entries += int(thread.get('new_entries', 0))
                    updated_entries += int(thread.get('updated_entries', 0))

                # Update session metadata with current progress
                self.update_session_metadata(
                    session_id,
                    total_threads=total_threads,
                    completed_threads=completed_threads,
                    total_entries=total_entries,
                    new_entries=new_entries,
                    updated_entries=updated_entries
                )

                # Check if session is complete
                if completed_threads == total_threads:
                    self.update_session_metadata(
                        session_id,
                        status='completed',
                        completed_at=datetime.utcnow().isoformat() + 'Z'
                    )
                    self.logger.info(f"Session {session_id} completed: {completed_threads}/{total_threads} threads, {total_entries} total entries")
                    return True
                else:
                    self.logger.debug(f"Session {session_id} progress: {completed_threads}/{total_threads} threads completed")
                    return False

            return self._execute_with_retry(check_completion_operation)

        except Exception as e:
            self.logger.error(f"Error checking session completion {session_id}: {e}")
            return False

    def mark_thread_completed(self, session_id: str, thread_url: str) -> bool:
        """Mark a thread as completed and check if session is done."""
        try:
            # Update thread status to completed
            self.update_thread_progress(
                session_id=session_id,
                thread_url=thread_url,
                status='completed'
            )

            # Check if session is now complete
            return self.check_and_update_session_completion(session_id)

        except Exception as e:
            self.logger.error(f"Error marking thread completed: {e}")
            return False

    def cleanup_invalid_sessions(self) -> Dict[str, int]:
        """Clean up orphaned session entries and invalid data."""
        cleanup_stats = {
            'found_invalid': 0,
            'deleted': 0,
            'errors': 0
        }

        try:
            def cleanup_operation():
                self._ensure_connections()
                if not self._sessions_table_client:
                    raise AzureError("Sessions table client not initialized")

                # Query all entities to find problematic ones
                entities = list(self._sessions_table_client.query_entities())

                for entity in entities:
                    row_key = entity.get('RowKey', '')
                    partition_key = entity.get('PartitionKey', '')

                    # Check for empty RowKey or PartitionKey
                    if not row_key or row_key.strip() == '' or not partition_key or partition_key.strip() == '':
                        cleanup_stats['found_invalid'] += 1
                        try:
                            self._sessions_table_client.delete_entity(
                                partition_key=partition_key,
                                row_key=row_key
                            )
                            cleanup_stats['deleted'] += 1
                            self.logger.info(f"Deleted invalid session entry - PK: '{partition_key}', RK: '{row_key}'")
                        except Exception as delete_error:
                            cleanup_stats['errors'] += 1
                            self.logger.error(f"Failed to delete invalid session: {delete_error}")

                return cleanup_stats

            return self._execute_with_retry(cleanup_operation)

        except Exception as e:
            self.logger.error(f"Error during invalid session cleanup: {e}")
            cleanup_stats['errors'] += 1
            return cleanup_stats

    def get_completed_sessions_for_stats(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get completed sessions that may need statistics calculation."""
        try:
            def get_completed_sessions_operation():
                self._ensure_connections()
                if not self._sessions_table_client:
                    raise AzureError("Sessions table client not initialized")

                # Query for completed session metadata entries
                filter_query = "RowKey eq 'session_metadata' and status eq 'completed'"

                completed_sessions = []
                entities = self._sessions_table_client.query_entities(
                    query_filter=filter_query,
                    select=["PartitionKey", "session_id", "completed_at", "total_entries", "stats_calculated", "stats_calculated_at"]
                )

                for entity in entities:
                    session_data = {
                        'session_id': entity.get('PartitionKey', ''),
                        'completed_at': entity.get('completed_at', ''),
                        'total_entries': entity.get('total_entries', 0),
                        'stats_calculated': entity.get('stats_calculated', False),
                        'stats_calculated_at': entity.get('stats_calculated_at', '')
                    }
                    completed_sessions.append(session_data)

                # Sort by completed_at (most recent first) and limit results
                completed_sessions.sort(key=lambda x: x.get('completed_at', ''), reverse=True)
                return completed_sessions[:limit]

            return self._execute_with_retry(get_completed_sessions_operation)

        except Exception as e:
            self.logger.error(f"Error getting completed sessions for stats: {e}")
            return []

    def mark_session_stats_calculated(self, session_id: str) -> bool:
        """Mark a session as having had its statistics calculated."""
        try:
            self.update_session_metadata(
                session_id,
                stats_calculated=True,
                stats_calculated_at=datetime.utcnow().isoformat() + 'Z'
            )
            return True
        except Exception as e:
            self.logger.error(f"Error marking session stats calculated: {e}")
            return False

    def cleanup_old_completed_sessions(self, days_old: int = 30) -> Dict[str, int]:
        """Clean up old completed sessions to maintain database size."""
        cleanup_stats = {
            'found_old': 0,
            'deleted': 0,
            'errors': 0
        }

        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            cutoff_str = cutoff_date.isoformat() + 'Z'

            def cleanup_old_sessions_operation():
                self._ensure_connections()
                if not self._sessions_table_client:
                    raise AzureError("Sessions table client not initialized")

                # Query for old completed sessions
                filter_query = f"RowKey eq 'session_metadata' and status eq 'completed' and completed_at lt '{cutoff_str}'"

                old_sessions = list(self._sessions_table_client.query_entities(query_filter=filter_query))

                for session_meta in old_sessions:
                    session_id = session_meta.get('PartitionKey', '')
                    if not session_id:
                        continue

                    cleanup_stats['found_old'] += 1

                    try:
                        # Delete all entries for this session (metadata + threads)
                        session_filter = f"PartitionKey eq '{session_id}'"
                        session_entities = list(self._sessions_table_client.query_entities(query_filter=session_filter))

                        for entity in session_entities:
                            self._sessions_table_client.delete_entity(
                                partition_key=entity['PartitionKey'],
                                row_key=entity['RowKey']
                            )

                        cleanup_stats['deleted'] += len(session_entities)
                        self.logger.info(f"Deleted old session {session_id} with {len(session_entities)} entries")

                    except Exception as delete_error:
                        cleanup_stats['errors'] += 1
                        self.logger.error(f"Failed to delete old session {session_id}: {delete_error}")

                return cleanup_stats

            return self._execute_with_retry(cleanup_old_sessions_operation)

        except Exception as e:
            self.logger.error(f"Error during old session cleanup: {e}")
            cleanup_stats['errors'] += 1
            return cleanup_stats

    def upsert_statistics(self, stat_type: str, stat_key: str, stat_value: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Upsert statistics data to separate stats table."""
        try:
            stats_data = StatisticsData(
                stat_type=stat_type,
                stat_key=stat_key,
                stat_value=stat_value,
                calculated_at=datetime.utcnow(),
                metadata=metadata
            )

            def upsert_stats_operation():
                entity = stats_data.to_table_entity()
                self._ensure_connections()
                if not self._stats_table_client:
                    raise AzureError("Stats table client not initialized")

                self._stats_table_client.upsert_entity(entity=entity)
                return True

            result = self._execute_with_retry(upsert_stats_operation)

            # Cache clearing removed

            return result

        except Exception as e:
            self.logger.error(f"Error upserting statistics: {e}")
            return False

    def get_statistics_from_table(self, stat_type: Optional[str] = None) -> List[StatisticsData]:
        """Get statistics data from separate stats table."""
        try:
            def get_stats_operation():
                self._ensure_connections()
                if not self._stats_table_client:
                    raise AzureError("Stats table client not initialized")

                # Build filter if stat_type is specified
                filter_expression = None
                if stat_type:
                    filter_expression = f"PartitionKey eq '{stat_type}'"

                entities = self._stats_table_client.query_entities(
                    query_filter=filter_expression or ""
                )

                return [StatisticsData.from_table_entity(entity) for entity in entities]

            return self._execute_with_retry(get_stats_operation)

        except Exception as e:
            self.logger.error(f"Error getting statistics from table: {e}")
            return []

    def delete_statistics(self, stat_type: str, stat_key: str) -> bool:
        """Delete statistics data from stats table."""
        try:
            def delete_stats_operation():
                self._ensure_connections()
                if not self._stats_table_client:
                    raise AzureError("Stats table client not initialized")

                self._stats_table_client.delete_entity(
                    partition_key=stat_type,
                    row_key=stat_key
                )
                return True

            result = self._execute_with_retry(delete_stats_operation)

            # Cache clearing removed

            return result

        except ResourceNotFoundError:
            self.logger.warning(f"Statistics entry not found: {stat_type}/{stat_key}")
            return True  # Consider it successful if it doesn't exist
        except Exception as e:
            self.logger.error(f"Error deleting statistics: {e}")
            return False

    def batch_upsert_statistics(self, statistics: List[StatisticsData]) -> Dict[str, int]:
        """Batch upsert statistics for better performance."""
        if not statistics:
            return {'success': 0, 'failed': 0}

        success_count = 0
        failed_count = 0

        # Group by partition key for efficient batching
        partitioned_stats = {}
        for stat in statistics:
            if stat.stat_type not in partitioned_stats:
                partitioned_stats[stat.stat_type] = []
            partitioned_stats[stat.stat_type].append(stat)

        # Process each partition separately
        for stat_type, stats_batch in partitioned_stats.items():
            # Process in smaller batches within each partition
            for i in range(0, len(stats_batch), self.batch_size):
                batch = stats_batch[i:i + self.batch_size]

                try:
                    def batch_stats_operation():
                        operations = []
                        for stat in batch:
                            entity = stat.to_table_entity()
                            operations.append(('upsert', entity))

                        # Submit batch transaction
                        self._ensure_connections()
                        if not self._stats_table_client:
                            raise AzureError("Stats table client not initialized")
                        self._stats_table_client.submit_transaction(operations)
                        return len(operations)

                    batch_success = self._execute_with_retry(batch_stats_operation)
                    success_count += batch_success

                except Exception as e:
                    self.logger.error(f"Batch statistics upsert failed for partition {stat_type}: {e}")
                    failed_count += len(batch)

        # Cache clearing removed
        pass

        return {'success': success_count, 'failed': failed_count}

    def get_recent_scrape_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent scraping sessions from the sessions table using new schema."""
        try:
            def get_sessions_operation():
                self._ensure_connections()
                if not self._sessions_table_client:
                    raise AzureError("Sessions table client not initialized")

                # Query for session metadata entries only
                filter_query = "RowKey eq 'session_metadata'"

                sessions = []
                entities = self._sessions_table_client.query_entities(
                    query_filter=filter_query,
                    select=["PartitionKey", "session_id", "started_at", "completed_at", "status", "total_threads", "completed_threads", "total_entries", "new_entries", "updated_entries"]
                )

                # Convert to list with aggregated data
                for entity in entities:
                    session_id = entity.get('PartitionKey', '')

                    # Get aggregated session summary for accurate counts
                    session_summary = self.get_session_summary(session_id)

                    if session_summary:
                        sessions.append(session_summary)
                    else:
                        # Fallback to metadata only if summary fails
                        session_data = {
                            'session_id': session_id,
                            'started_at': entity.get('started_at', ''),
                            'completed_at': entity.get('completed_at', ''),
                            'status': entity.get('status', ''),
                            'total_threads': entity.get('total_threads', 0),
                            'completed_threads': entity.get('completed_threads', 0),
                            'total_entries': entity.get('total_entries', 0),
                            'new_entries': entity.get('new_entries', 0),
                            'updated_entries': entity.get('updated_entries', 0)
                        }
                        sessions.append(session_data)

                # Sort by started_at descending and limit results
                sessions.sort(key=lambda x: x.get('started_at', ''), reverse=True)
                return sessions[:limit]

            return self._execute_with_retry(get_sessions_operation)

        except Exception as e:
            self.logger.error(f"Error getting recent scrape sessions: {e}")
            return []

    def get_latest_entry_timestamp(self) -> Optional[str]:
        """Get the timestamp of the most recently scraped/updated entry."""
        try:
            def get_latest_operation():
                try:
                    self._ensure_connections()
                    if not self._entries_table_client:
                        self.logger.warning("Entries table client not initialized")
                        return None

                    # Use a more efficient approach - query with top parameter and order by Timestamp (RowKey)
                    # This limits the number of entities we need to process
                    entities = list(self._entries_table_client.query_entities(
                        query_filter="",
                        select=['updated_at', 'created_at', 'Timestamp'],
                        results_per_page=1000  # Limit to recent entries for performance
                    ))

                    if not entities:
                        self.logger.info("No entities found for timestamp query")
                        return None

                    # Find the latest timestamp (either updated_at or created_at)
                    latest_timestamp = None
                    valid_timestamps = 0

                    for entity in entities:
                        try:
                            # Check both updated_at and created_at, use whichever is more recent
                            updated_at = entity.get('updated_at', '')
                            created_at = entity.get('created_at', '')

                            # Skip empty timestamps
                            if not updated_at and not created_at:
                                continue

                            # Use the most recent of the two timestamps
                            current_timestamp = None
                            if updated_at and created_at:
                                current_timestamp = max(updated_at, created_at)
                            else:
                                current_timestamp = updated_at or created_at

                            if current_timestamp and current_timestamp.strip():
                                valid_timestamps += 1
                                if not latest_timestamp or current_timestamp > latest_timestamp:
                                    latest_timestamp = current_timestamp

                        except Exception as entity_error:
                            self.logger.warning(f"Error processing entity: {entity_error}")
                            continue

                    self.logger.info(f"Processed {len(entities)} entities, found {valid_timestamps} valid timestamps")
                    return latest_timestamp

                except Exception as op_error:
                    self.logger.error(f"Error in get_latest_operation: {op_error}")
                    return None

            return self._execute_with_retry(get_latest_operation)

        except Exception as e:
            self.logger.error(f"Error getting latest entry timestamp: {e}")
            return None
