"""
Statistics Calculator for ROFR data.
Calculates comprehensive statistics from ROFR entries for pre-storage.
"""

import logging
from datetime import datetime, timedelta, date
from typing import Dict, Any, List
import statistics
from models import ROFREntry

logger = logging.getLogger(__name__)

class StatisticsCalculator:
    """Calculates comprehensive statistics from ROFR entries."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset all counters and collections."""
        self.total_entries = 0
        self.resort_data: Dict[str, Dict[str, Any]] = {}
        self.monthly_data: Dict[str, Dict[str, Any]] = {}
        self.global_data: Dict[str, Any] = {
            'entries': [],
            'prices': [],
            'results': {'taken': 0, 'passed': 0, 'pending': 0},
            'resorts': set(),
            'users': set(),
            'dates': [],
            'days_to_result': []
        }

    def _init_resort_data(self, resort: str) -> Dict[str, Any]:
        """Initialize data structure for a resort."""
        return {
            'entries': [],
            'prices': [],
            'results': {'taken': 0, 'passed': 0, 'pending': 0},
            'dates': [],
            'days_to_result': []
        }

    def _init_monthly_data(self, month_key: str) -> Dict[str, Any]:
        """Initialize data structure for a month."""
        return {
            'entries': [],
            'prices': [],
            'results': {'taken': 0, 'passed': 0, 'pending': 0},
            'resorts': set(),
            'users': set(),
            'days_to_result': []
        }

    def add_entry(self, entry: ROFREntry):
        """Add an entry to the statistics calculation."""
        try:
            if not entry:
                logger.warning("Attempted to add None entry to statistics")
                return

            self.total_entries += 1

            # Normalize data with additional validation
            resort = entry.resort or 'Unknown'
            result = entry.result or 'pending'

            # Validate result is in expected values
            if result not in ['taken', 'passed', 'pending']:
                logger.warning(f"Unexpected result value: {result}, defaulting to pending")
                result = 'pending'

            # Validate and clean price data
            price = None
            if hasattr(entry, 'price_per_point') and entry.price_per_point is not None:
                try:
                    price_val = float(entry.price_per_point)
                    if price_val > 0 and price_val < 1000:  # Reasonable price range
                        price = price_val
                except (ValueError, TypeError):
                    logger.warning(f"Invalid price_per_point value: {entry.price_per_point}")

            username = entry.username or 'Unknown'

            # Global data
            self.global_data['entries'].append(entry)
            self.global_data['results'][result] += 1
            self.global_data['resorts'].add(resort)
            self.global_data['users'].add(username)

            if price is not None:
                self.global_data['prices'].append(price)

            if entry.sent_date:
                self.global_data['dates'].append(entry.sent_date)

            # Calculate days between sent_date and result_date
            if entry.sent_date and entry.result_date:
                days_diff = (entry.result_date - entry.sent_date).days
                if days_diff >= 0:  # Only count positive differences
                    self.global_data['days_to_result'].append(days_diff)

            # Resort-specific data
            if resort not in self.resort_data:
                self.resort_data[resort] = self._init_resort_data(resort)

            resort_info = self.resort_data[resort]
            resort_info['entries'].append(entry)
            resort_info['results'][result] += 1

            if price is not None:
                resort_info['prices'].append(price)

            if entry.sent_date:
                resort_info['dates'].append(entry.sent_date)

            # Calculate days between sent_date and result_date for resort
            if entry.sent_date and entry.result_date:
                days_diff = (entry.result_date - entry.sent_date).days
                if days_diff >= 0:  # Only count positive differences
                    resort_info['days_to_result'].append(days_diff)

            # Monthly data
            if entry.sent_date:
                try:
                    month_key = entry.sent_date.strftime("%Y-%m")
                    if month_key not in self.monthly_data:
                        self.monthly_data[month_key] = self._init_monthly_data(month_key)

                    monthly_info = self.monthly_data[month_key]
                    monthly_info['entries'].append(entry)
                    monthly_info['results'][result] += 1
                    monthly_info['resorts'].add(resort)
                    monthly_info['users'].add(username)

                    if price is not None:
                        monthly_info['prices'].append(price)

                    # Calculate days between sent_date and result_date for monthly data
                    if entry.result_date:
                        days_diff = (entry.result_date - entry.sent_date).days
                        if days_diff >= 0:  # Only count positive differences
                            monthly_info['days_to_result'].append(days_diff)
                except Exception as e:
                    logger.warning(f"Error processing monthly data for entry: {e}")

        except Exception as e:
            logger.error(f"Error adding entry to statistics: {str(e)}")

    def calculate_global_statistics(self) -> Dict[str, Any]:
        """Calculate global statistics."""
        try:
            data = self.global_data

            # Basic counts
            total_entries = len(data['entries'])
            if total_entries == 0:
                return self._empty_global_stats()

            # Price statistics
            price_stats = self._calculate_price_stats(data['prices'])

            # Result statistics
            taken_count = data['results']['taken']
            passed_count = data['results']['passed']
            pending_count = data['results']['pending']
            rofr_rate = (taken_count / total_entries * 100) if total_entries > 0 else 0

            # Resort counts
            resort_counts = {}
            for resort in data['resorts']:
                if resort in self.resort_data:
                    resort_counts[resort] = len(self.resort_data[resort]['entries'])
                else:
                    resort_counts[resort] = 0

            # Top resorts
            top_resorts = sorted(
                [{'resort': k, 'count': v} for k, v in resort_counts.items()],
                key=lambda x: x['count'],
                reverse=True
            )[:10]

            # Date statistics
            latest_entry_date = None
            if data['dates']:
                latest_entry_date = max(data['dates'])

            # Days to result statistics
            avg_days_to_result = None
            if data['days_to_result']:
                avg_days_to_result = sum(data['days_to_result']) / len(data['days_to_result'])

            return {
                'total_entries': total_entries,
                'unique_resorts': len(data['resorts']),
                'unique_users': len(data['users']),
                'avg_price_per_point': price_stats['avg'],
                'min_price_per_point': price_stats['min'],
                'max_price_per_point': price_stats['max'],
                'price_count': price_stats['count'],
                'rofr_rate': round(rofr_rate, 2),
                'taken_count': taken_count,
                'passed_count': passed_count,
                'pending_count': pending_count,
                'latest_entry_date': latest_entry_date.isoformat() if latest_entry_date else None,
                'resort_counts': resort_counts,
                'top_resorts': top_resorts,
                'active_resorts': len([r for r, c in resort_counts.items() if c > 0]),
                'avg_days_to_result': round(avg_days_to_result, 1) if avg_days_to_result is not None else None,
                'days_to_result_count': len(data['days_to_result']),
                'last_calculated': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error calculating global statistics: {str(e)}")
            return self._empty_global_stats()

    def calculate_resort_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Calculate per-resort statistics."""
        try:
            resort_stats = {}

            for resort, data in self.resort_data.items():
                entries = data['entries']
                if not entries:
                    continue

                total_entries = len(entries)
                price_stats = self._calculate_price_stats(data['prices'])

                # Result statistics
                taken_count = data['results']['taken']
                passed_count = data['results']['passed']
                pending_count = data['results']['pending']
                rofr_rate = (taken_count / total_entries * 100) if total_entries > 0 else 0

                # Date statistics
                latest_entry_date = None
                if data['dates']:
                    latest_entry_date = max(data['dates'])

                resort_stats[resort] = {
                    'resort_code': resort,
                    'total_entries': total_entries,
                    'avg_price_per_point': price_stats['avg'],
                    'min_price': price_stats['min'],
                    'max_price': price_stats['max'],
                    'price_count': price_stats['count'],
                    'rofr_rate': round(rofr_rate, 2),
                    'taken_count': taken_count,
                    'passed_count': passed_count,
                    'pending_count': pending_count,
                    'latest_entry_date': latest_entry_date.isoformat() if latest_entry_date else None,
                    'last_calculated': datetime.utcnow().isoformat()
                }

            return resort_stats

        except Exception as e:
            logger.error(f"Error calculating resort statistics: {str(e)}")
            return {}

    def calculate_monthly_statistics(self, months: int = 24) -> Dict[str, Dict[str, Any]]:
        """Calculate monthly statistics for the last N months."""
        try:
            monthly_stats = {}

            for month_key, data in self.monthly_data.items():
                entries = data['entries']
                if not entries:
                    continue

                total_entries = len(entries)
                price_stats = self._calculate_price_stats(data['prices'])

                # Result statistics
                taken_count = data['results']['taken']
                passed_count = data['results']['passed']
                pending_count = data['results']['pending']
                rofr_rate = (taken_count / total_entries * 100) if total_entries > 0 else 0

                # Resort counts for this month
                resort_counts = {}
                for resort in data['resorts']:
                    resort_entries = [e for e in entries if (e.resort or 'Unknown') == resort]
                    resort_counts[resort] = len(resort_entries)

                # Top resorts for this month
                top_resorts = sorted(
                    [{'resort': k, 'count': v} for k, v in resort_counts.items()],
                    key=lambda x: x['count'],
                    reverse=True
                )[:10]

                monthly_stats[month_key] = {
                    'month': month_key,
                    'total_entries': total_entries,
                    'unique_resorts': len(data['resorts']),
                    'unique_users': len(data['users']),
                    'avg_price_per_point': price_stats['avg'],
                    'min_price_per_point': price_stats['min'],
                    'max_price_per_point': price_stats['max'],
                    'price_count': price_stats['count'],
                    'rofr_rate': round(rofr_rate, 2),
                    'taken_count': taken_count,
                    'passed_count': passed_count,
                    'pending_count': pending_count,
                    'top_resorts': top_resorts,
                    'last_calculated': datetime.utcnow().isoformat()
                }

            return monthly_stats

        except Exception as e:
            logger.error(f"Error calculating monthly statistics: {str(e)}")
            return {}

    def calculate_price_trends(self, days: int = 90) -> Dict[str, Any]:
        """Calculate price trends over time."""
        try:
            cutoff_date = datetime.now().date() - timedelta(days=days)
            recent_entries = [
                entry for entry in self.global_data['entries']
                if entry.sent_date and entry.sent_date >= cutoff_date
                and entry.price_per_point and entry.price_per_point > 0
            ]

            if not recent_entries:
                return {
                    'trend_period_days': days,
                    'total_entries': 0,
                    'trends': {},
                    'overall_trend': None
                }

            # Group by resort
            resort_trends = {}
            for entry in recent_entries:
                resort = entry.resort or 'Unknown'
                if resort not in resort_trends:
                    resort_trends[resort] = []

                resort_trends[resort].append({
                    'date': entry.sent_date,
                    'price': entry.price_per_point
                })

            # Calculate trends per resort
            trends = {}
            for resort, price_data in resort_trends.items():
                if len(price_data) < 3:  # Need at least 3 points for trend
                    continue

                # Sort by date
                price_data.sort(key=lambda x: x['date'])

                # Calculate simple trend (first half vs second half average)
                mid_point = len(price_data) // 2
                if mid_point > 0:
                    first_half_avg = sum(p['price'] for p in price_data[:mid_point]) / mid_point
                    second_half_avg = sum(p['price'] for p in price_data[mid_point:]) / (len(price_data) - mid_point)

                    trend_direction = 'increasing' if second_half_avg > first_half_avg else 'decreasing'
                    trend_percentage = ((second_half_avg - first_half_avg) / first_half_avg * 100) if first_half_avg > 0 else 0

                    trends[resort] = {
                        'entry_count': len(price_data),
                        'first_half_avg': round(first_half_avg, 2),
                        'second_half_avg': round(second_half_avg, 2),
                        'trend_direction': trend_direction,
                        'trend_percentage': round(trend_percentage, 2),
                        'latest_price': price_data[-1]['price'],
                        'earliest_price': price_data[0]['price']
                    }

            return {
                'trend_period_days': days,
                'total_entries': len(recent_entries),
                'trends': trends,
                'last_calculated': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error calculating price trends: {str(e)}")
            return {
                'trend_period_days': days,
                'total_entries': 0,
                'trends': {},
                'last_calculated': datetime.utcnow().isoformat()
            }

    def _calculate_price_stats(self, prices: List[float]) -> Dict[str, float]:
        """Calculate price statistics from a list of prices."""
        if not prices:
            return {'avg': 0.0, 'min': 0.0, 'max': 0.0, 'count': 0, 'median': 0.0}

        try:
            # Filter out None values and invalid prices
            valid_prices = [p for p in prices if p is not None and isinstance(p, (int, float)) and p > 0]

            if not valid_prices:
                return {'avg': 0.0, 'min': 0.0, 'max': 0.0, 'count': 0, 'median': 0.0}

            return {
                'avg': round(sum(valid_prices) / len(valid_prices), 2),
                'min': round(min(valid_prices), 2),
                'max': round(max(valid_prices), 2),
                'count': len(valid_prices),
                'median': round(statistics.median(valid_prices), 2) if len(valid_prices) > 0 else 0.0
            }
        except Exception as e:
            logger.error(f"Error calculating price statistics: {e}")
            return {'avg': 0.0, 'min': 0.0, 'max': 0.0, 'count': 0, 'median': 0.0}

    def _empty_global_stats(self) -> Dict[str, Any]:
        """Return empty global statistics structure."""
        return {
            'total_entries': 0,
            'unique_resorts': 0,
            'unique_users': 0,
            'avg_price_per_point': 0.0,
            'min_price_per_point': 0.0,
            'max_price_per_point': 0.0,
            'price_count': 0,
            'rofr_rate': 0.0,
            'taken_count': 0,
            'passed_count': 0,
            'pending_count': 0,
            'latest_entry_date': None,
            'resort_counts': {},
            'top_resorts': [],
            'active_resorts': 0,
            'last_calculated': datetime.utcnow().isoformat()
        }

    def _filter_entries_by_time_range(self, entries: List[ROFREntry], time_range: str) -> List[ROFREntry]:
        """Filter entries based on time range."""
        if not time_range or time_range == 'all':
            return entries

        try:
            cutoff_date = None
            today = date.today()

            if time_range == '3months':
                cutoff_date = today - timedelta(days=90)
            elif time_range == '6months':
                cutoff_date = today - timedelta(days=180)
            elif time_range == '1year':
                cutoff_date = today - timedelta(days=365)
            else:
                logger.warning(f"Unknown time range: {time_range}, using all entries")
                return entries

            # Filter entries by sent_date
            filtered_entries = []
            for entry in entries:
                if entry.sent_date and entry.sent_date >= cutoff_date:
                    filtered_entries.append(entry)

            logger.info(f"Filtered {len(entries)} entries to {len(filtered_entries)} for time range: {time_range}")
            return filtered_entries

        except Exception as e:
            logger.error(f"Error filtering entries by time range {time_range}: {str(e)}")
            return entries

    def calculate_all_statistics(self, entries: List[ROFREntry], time_range: str = None) -> Dict[str, Any]:
        """Calculate all statistics from a list of entries with optional time filtering."""
        try:
            self.reset()

            # Filter entries by time range if specified
            filtered_entries = self._filter_entries_by_time_range(entries, time_range) if time_range else entries

            # Process filtered entries
            for entry in filtered_entries:
                self.add_entry(entry)

            # Calculate all statistics
            global_stats = self.calculate_global_statistics()
            resort_stats = self.calculate_resort_statistics()
            monthly_stats = self.calculate_monthly_statistics()
            price_trends = self.calculate_price_trends()

            return {
                'global': global_stats,
                'resorts': resort_stats,
                'monthly': monthly_stats,
                'price_trends': price_trends,
                'calculation_time': datetime.utcnow().isoformat(),
                'total_entries_processed': len(filtered_entries),
                'time_range': time_range or 'all',
                'original_entries_count': len(entries)
            }

        except Exception as e:
            logger.error(f"Error calculating all statistics: {str(e)}")
            return {
                'global': self._empty_global_stats(),
                'resorts': {},
                'monthly': {},
                'price_trends': {},
                'calculation_time': datetime.utcnow().isoformat(),
                'total_entries_processed': 0,
                'time_range': time_range or 'all',
                'original_entries_count': len(entries) if entries else 0,
                'error': str(e)
            }
