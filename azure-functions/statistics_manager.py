"""
Statistics Manager for pre-calculated ROFR statistics.
Handles storing and retrieving statistics from Azure Table Storage.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from azure.data.tables import TableServiceClient, TableClient
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
import json

logger = logging.getLogger(__name__)

class StatisticsManager:
    """Manages pre-calculated statistics in Azure Table Storage."""

    def __init__(self, connection_string: str, stats_table_name: str = "stats"):
        self.connection_string = connection_string
        self.stats_table_name = stats_table_name
        self.table_service_client = None
        self.stats_table_client = None
        self._ensure_connections()

    def _ensure_connections(self):
        """Ensure table service and table clients are initialized."""
        if not self.table_service_client:
            self.table_service_client = TableServiceClient.from_connection_string(
                self.connection_string
            )

        if not self.stats_table_client:
            self.stats_table_client = self.table_service_client.get_table_client(
                table_name=self.stats_table_name
            )
            self._ensure_stats_table_exists()

    def _ensure_stats_table_exists(self):
        """Ensure the statistics table exists."""
        try:
            self.stats_table_client.create_table()
            logger.info(f"Created statistics table: {self.stats_table_name}")
        except ResourceExistsError:
            logger.debug(f"Statistics table already exists: {self.stats_table_name}")
        except Exception as e:
            logger.error(f"Error creating statistics table: {str(e)}")
            raise

    def store_global_statistics(self, stats: Dict[str, Any]) -> bool:
        """Store global statistics with timestamp."""
        try:
            entity = {
                "PartitionKey": "global",
                "RowKey": "latest",
                "timestamp": datetime.utcnow().isoformat(),
                "total_entries": stats.get("total_entries", 0),
                "unique_resorts": stats.get("unique_resorts", 0),
                "unique_users": stats.get("unique_users", 0),
                "avg_price_per_point": stats.get("avg_price_per_point", 0.0),
                "rofr_rate": stats.get("rofr_rate", 0.0),
                "taken_count": stats.get("taken_count", 0),
                "passed_count": stats.get("passed_count", 0),
                "pending_count": stats.get("pending_count", 0),
                "latest_entry_date": stats.get("latest_entry_date"),
                "resort_counts": json.dumps(stats.get("resort_counts", {})),
                "top_resorts": json.dumps(stats.get("top_resorts", [])),
                "active_resorts": stats.get("active_resorts", 0),
                "avg_days_to_result": stats.get("avg_days_to_result"),
                "days_to_result_count": stats.get("days_to_result_count", 0),
                "last_updated": datetime.utcnow().isoformat()
            }

            self.stats_table_client.upsert_entity(entity=entity)
            logger.info("Successfully stored global statistics")
            return True

        except Exception as e:
            logger.error(f"Error storing global statistics: {str(e)}")
            return False

    def store_resort_statistics(self, resort_stats: Dict[str, Dict[str, Any]]) -> bool:
        """Store per-resort statistics."""
        try:
            entities = []
            timestamp = datetime.utcnow().isoformat()

            for resort_code, stats in resort_stats.items():
                entity = {
                    "PartitionKey": "resort",
                    "RowKey": resort_code,
                    "timestamp": timestamp,
                    "resort_code": resort_code,
                    "total_entries": stats.get("total_entries", 0),
                    "avg_price_per_point": stats.get("avg_price_per_point", 0.0),
                    "rofr_rate": stats.get("rofr_rate", 0.0),
                    "taken_count": stats.get("taken_count", 0),
                    "passed_count": stats.get("passed_count", 0),
                    "pending_count": stats.get("pending_count", 0),
                    "min_price": stats.get("min_price", 0.0),
                    "max_price": stats.get("max_price", 0.0),
                    "latest_entry_date": stats.get("latest_entry_date"),
                    "last_updated": timestamp
                }
                entities.append(entity)

            # Batch upsert resort statistics
            for entity in entities:
                self.stats_table_client.upsert_entity(entity=entity)

            logger.info(f"Successfully stored statistics for {len(entities)} resorts")
            return True

        except Exception as e:
            logger.error(f"Error storing resort statistics: {str(e)}")
            return False

    def store_monthly_statistics(self, monthly_stats: Dict[str, Dict[str, Any]]) -> bool:
        """Store monthly aggregated statistics."""
        try:
            entities = []
            timestamp = datetime.utcnow().isoformat()

            for month_key, stats in monthly_stats.items():
                entity = {
                    "PartitionKey": "monthly",
                    "RowKey": month_key,  # Format: YYYY-MM
                    "timestamp": timestamp,
                    "month": month_key,
                    "total_entries": stats.get("total_entries", 0),
                    "avg_price_per_point": stats.get("avg_price_per_point", 0.0),
                    "min_price": stats.get("min_price_per_point", 0.0),
                    "max_price": stats.get("max_price_per_point", 0.0),
                    "rofr_rate": stats.get("rofr_rate", 0.0),
                    "taken_count": stats.get("taken_count", 0),
                    "passed_count": stats.get("passed_count", 0),
                    "pending_count": stats.get("pending_count", 0),
                    "unique_resorts": stats.get("unique_resorts", 0),
                    "top_resorts": json.dumps(stats.get("top_resorts", [])),
                    "last_updated": timestamp
                }
                entities.append(entity)

            # Batch upsert monthly statistics
            for entity in entities:
                self.stats_table_client.upsert_entity(entity=entity)

            logger.info(f"Successfully stored statistics for {len(entities)} months")
            return True

        except Exception as e:
            logger.error(f"Error storing monthly statistics: {str(e)}")
            return False

    def store_price_trends(self, price_trends: Dict[str, Any]) -> bool:
        """Store price trend data."""
        try:
            entity = {
                "PartitionKey": "trends",
                "RowKey": "price_trends",
                "timestamp": datetime.utcnow().isoformat(),
                "trend_period_days": price_trends.get("trend_period_days", 90),
                "total_entries": price_trends.get("total_entries", 0),
                "trends": json.dumps(price_trends.get("trends", {})),
                "last_calculated": price_trends.get("last_calculated"),
                "last_updated": datetime.utcnow().isoformat()
            }

            self.stats_table_client.upsert_entity(entity=entity)
            logger.info("Successfully stored price trends")
            return True

        except Exception as e:
            logger.error(f"Error storing price trends: {str(e)}")
            return False

    def get_global_statistics(self) -> Optional[Dict[str, Any]]:
        """Retrieve the latest global statistics."""
        try:
            entity = self.stats_table_client.get_entity(
                partition_key="global",
                row_key="latest"
            )

            # Parse JSON fields back to objects
            resort_counts = json.loads(entity.get("resort_counts", "{}"))
            top_resorts = json.loads(entity.get("top_resorts", "[]"))

            return {
                "total_entries": entity.get("total_entries", 0),
                "unique_resorts": entity.get("unique_resorts", 0),
                "unique_users": entity.get("unique_users", 0),
                "avg_price_per_point": entity.get("avg_price_per_point", 0.0),
                "rofr_rate": entity.get("rofr_rate", 0.0),
                "taken_count": entity.get("taken_count", 0),
                "passed_count": entity.get("passed_count", 0),
                "pending_count": entity.get("pending_count", 0),
                "latest_entry_date": entity.get("latest_entry_date"),
                "resort_counts": resort_counts,
                "top_resorts": top_resorts,
                "active_resorts": len([r for r, c in resort_counts.items() if c > 0]),
                "avg_days_to_result": entity.get("avg_days_to_result"),
                "days_to_result_count": entity.get("days_to_result_count", 0),
                "last_updated": entity.get("last_updated")
            }

        except ResourceNotFoundError:
            logger.warning("No global statistics found")
            return None
        except Exception as e:
            logger.error(f"Error retrieving global statistics: {str(e)}")
            return None

    def get_resort_statistics(self, resort_code: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve resort-specific statistics."""
        try:
            if resort_code:
                # Get specific resort statistics
                entity = self.stats_table_client.get_entity(
                    partition_key="resort",
                    row_key=resort_code
                )
                return {
                    "resort_code": entity.get("resort_code"),
                    "total_entries": entity.get("total_entries", 0),
                    "avg_price_per_point": entity.get("avg_price_per_point", 0.0),
                    "rofr_rate": entity.get("rofr_rate", 0.0),
                    "taken_count": entity.get("taken_count", 0),
                    "passed_count": entity.get("passed_count", 0),
                    "pending_count": entity.get("pending_count", 0),
                    "min_price": entity.get("min_price", 0.0),
                    "max_price": entity.get("max_price", 0.0),
                    "latest_entry_date": entity.get("latest_entry_date"),
                    "last_updated": entity.get("last_updated")
                }
            else:
                # Get all resort statistics
                entities = self.stats_table_client.query_entities(
                    query_filter="PartitionKey eq 'resort'"
                )

                resort_stats = {}
                for entity in entities:
                    resort_code = entity.get("RowKey")
                    resort_stats[resort_code] = {
                        "resort_code": entity.get("resort_code"),
                        "total_entries": entity.get("total_entries", 0),
                        "avg_price_per_point": entity.get("avg_price_per_point", 0.0),
                        "rofr_rate": entity.get("rofr_rate", 0.0),
                        "taken_count": entity.get("taken_count", 0),
                        "passed_count": entity.get("passed_count", 0),
                        "pending_count": entity.get("pending_count", 0),
                        "min_price": entity.get("min_price", 0.0),
                        "max_price": entity.get("max_price", 0.0),
                        "latest_entry_date": entity.get("latest_entry_date"),
                        "last_updated": entity.get("last_updated")
                    }

                return resort_stats

        except ResourceNotFoundError:
            logger.warning(f"No statistics found for resort: {resort_code}")
            return {}
        except Exception as e:
            logger.error(f"Error retrieving resort statistics: {str(e)}")
            return {}

    def get_monthly_statistics(self, months: int = 12) -> List[Dict[str, Any]]:
        """Retrieve monthly statistics for the last N months."""
        try:
            # Generate month keys for the last N months
            month_keys = []
            current_date = datetime.now().replace(day=1)

            for i in range(months):
                month_key = current_date.strftime("%Y-%m")
                month_keys.append(month_key)
                # Go back one month
                if current_date.month == 1:
                    current_date = current_date.replace(year=current_date.year - 1, month=12)
                else:
                    current_date = current_date.replace(month=current_date.month - 1)

            monthly_stats = []
            for month_key in month_keys:
                try:
                    entity = self.stats_table_client.get_entity(
                        partition_key="monthly",
                        row_key=month_key
                    )

                    top_resorts = json.loads(entity.get("top_resorts", "[]"))

                    # Transform to chart-compatible format
                    avg_price = entity.get("avg_price_per_point", 0.0)
                    min_price = entity.get("min_price", 0.0)
                    max_price = entity.get("max_price", 0.0)

                    monthly_stats.append({
                        "month": entity.get("month"),
                        "total": entity.get("total_entries", 0),
                        "taken": entity.get("taken_count", 0),
                        "passed": entity.get("passed_count", 0),
                        "pending": entity.get("pending_count", 0),
                        "rofrRate": entity.get("rofr_rate", 0.0),
                        "averagePrice": avg_price,
                        "minPrice": min_price,
                        "maxPrice": max_price,
                        "priceCount": entity.get("total_entries", 0),
                        "unique_resorts": entity.get("unique_resorts", 0),
                        "top_resorts": top_resorts,
                        "last_updated": entity.get("last_updated")
                    })
                except ResourceNotFoundError:
                    # Month doesn't exist, skip
                    continue

            return sorted(monthly_stats, key=lambda x: x["month"], reverse=True)

        except Exception as e:
            logger.error(f"Error retrieving monthly statistics: {str(e)}")
            return []

    def is_statistics_fresh(self, max_age_hours: int = 3) -> bool:
        """Check if statistics are fresh (within max_age_hours)."""
        try:
            global_stats = self.get_global_statistics()
            if not global_stats or not global_stats.get("last_updated"):
                return False

            last_updated = datetime.fromisoformat(global_stats["last_updated"])
            age = datetime.utcnow() - last_updated

            return age < timedelta(hours=max_age_hours)

        except Exception as e:
            logger.error(f"Error checking statistics freshness: {str(e)}")
            return False

    def get_price_trends(self) -> Optional[Dict[str, Any]]:
        """Retrieve pre-calculated price trends."""
        try:
            entity = self.stats_table_client.get_entity(
                partition_key="trends",
                row_key="price_trends"
            )

            trends = json.loads(entity.get("trends", "{}"))

            return {
                "trend_period_days": entity.get("trend_period_days", 90),
                "total_entries": entity.get("total_entries", 0),
                "trends": trends,
                "last_calculated": entity.get("last_calculated"),
                "last_updated": entity.get("last_updated")
            }

        except ResourceNotFoundError:
            logger.warning("No price trends found")
            return None
        except Exception as e:
            logger.error(f"Error retrieving price trends: {str(e)}")
            return None

    def get_statistics_age(self) -> Optional[timedelta]:
        """Get the age of the current statistics."""
        try:
            global_stats = self.get_global_statistics()
            if not global_stats or not global_stats.get("last_updated"):
                return None

            last_updated = datetime.fromisoformat(global_stats["last_updated"])
            return datetime.utcnow() - last_updated

        except Exception as e:
            logger.error(f"Error getting statistics age: {str(e)}")
            return None
