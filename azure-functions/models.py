#!/usr/bin/env python3
"""
Data Models for ROFR Scraper Azure Table Storage

This module contains data classes and utilities for working with Azure Table Storage
for the ROFR scraper application.
"""

import hashlib
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, Dict, Any


@dataclass
class ROFREntry:
    """Represents a single ROFR (Right of First Refusal) entry."""

    username: str
    price_per_point: float
    total_cost: Optional[float]
    points: int
    resort: str
    use_year: str
    points_details: Optional[str]
    sent_date: Optional[date]
    result: str  # 'pending', 'passed', 'taken'
    result_date: Optional[date]
    thread_url: str
    raw_entry: Optional[str]
    entry_hash: Optional[str] = None

    def __post_init__(self):
        """Generate entry hash if not provided."""
        if not self.entry_hash:
            self.entry_hash = self.generate_hash()

    def generate_hash(self) -> str:
        """Generate a unique hash for this entry for deduplication."""
        entry_key = f"{self.username.lower()}|{self.price_per_point}|{self.total_cost or ''}|{self.points}|{self.resort}|{self.use_year}|{self.sent_date}|{self.result}|{self.result_date or ''}|{self.thread_url}"
        return hashlib.md5(entry_key.encode()).hexdigest()

    def to_table_entity(self) -> Dict[str, Any]:
        """Convert to Azure Table Storage entity format."""
        # Sanitize partition key for Azure Table Storage while preserving original resort code
        entry_hash = self.entry_hash or self.generate_hash()
        partition_key, row_key = TableStorageHelper.validate_entity_keys(self.resort, entry_hash)

        entity = {
            'PartitionKey': partition_key,  # Sanitized partition key
            'RowKey': row_key,             # Sanitized row key
            'username': self.username,
            'price_per_point': self.price_per_point,
            'total_cost': self.total_cost or 0.0,
            'points': self.points,
            'resort': self.resort,         # Keep original resort code
            'use_year': self.use_year,
            'points_details': self.points_details or '',
            'sent_date': self.sent_date.isoformat() if self.sent_date else '',
            'result': self.result,
            'result_date': self.result_date.isoformat() if self.result_date else '',
            'thread_url': self.thread_url,
            'raw_entry': self.raw_entry or '',
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'updated_at': datetime.utcnow().isoformat() + 'Z'
        }
        return entity

    @classmethod
    def from_table_entity(cls, entity: Dict[str, Any]) -> 'ROFREntry':
        """Create ROFREntry from Azure Table Storage entity."""
        return cls(
            username=entity.get('username', ''),
            price_per_point=float(entity.get('price_per_point', 0)),
            total_cost=float(entity.get('total_cost', 0)) if entity.get('total_cost') else None,
            points=int(entity.get('points', 0)),
            resort=entity.get('resort', ''),
            use_year=entity.get('use_year', ''),
            points_details=entity.get('points_details', ''),
            sent_date=datetime.fromisoformat(entity['sent_date']).date() if entity.get('sent_date') else None,
            result=entity.get('result', 'pending'),
            result_date=datetime.fromisoformat(entity['result_date']).date() if entity.get('result_date') else None,
            thread_url=entity.get('thread_url', ''),
            raw_entry=entity.get('raw_entry', ''),
            entry_hash=entity.get('RowKey', '')
        )


@dataclass
class ThreadInfo:
    """Represents information about a ROFR thread."""

    url: str
    title: str
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    start_month: Optional[str] = None
    end_month: Optional[str] = None
    last_scraped_page: int = 0
    total_pages: Optional[int] = None
    thread_start_date: Optional[date] = None
    thread_end_date: Optional[date] = None

    def to_table_entity(self) -> Dict[str, Any]:
        """Convert to Azure Table Storage entity format."""
        # Use URL hash as RowKey since URLs can be too long
        url_hash = hashlib.md5(self.url.encode()).hexdigest()

        entity = {
            'PartitionKey': 'thread',  # All threads in same partition
            'RowKey': url_hash,
            'url': self.url,
            'title': self.title or '',
            'start_year': self.start_year or 0,
            'end_year': self.end_year or 0,
            'start_month': self.start_month or '',
            'end_month': self.end_month or '',
            'last_scraped_page': self.last_scraped_page,
            'total_pages': self.total_pages or 0,
            'thread_start_date': self.thread_start_date.isoformat() if self.thread_start_date else '',
            'thread_end_date': self.thread_end_date.isoformat() if self.thread_end_date else '',
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'updated_at': datetime.utcnow().isoformat() + 'Z'
        }
        return entity

    @classmethod
    def from_table_entity(cls, entity: Dict[str, Any]) -> 'ThreadInfo':
        """Create ThreadInfo from Azure Table Storage entity."""
        return cls(
            url=entity.get('url', ''),
            title=entity.get('title', ''),
            start_year=int(entity.get('start_year', 0)) if entity.get('start_year') else None,
            end_year=int(entity.get('end_year', 0)) if entity.get('end_year') else None,
            start_month=entity.get('start_month', ''),
            end_month=entity.get('end_month', ''),
            last_scraped_page=int(entity.get('last_scraped_page', 0)),
            total_pages=int(entity.get('total_pages', 0)) if entity.get('total_pages') else None,
            thread_start_date=datetime.fromisoformat(entity['thread_start_date']).date() if entity.get('thread_start_date') else None,
            thread_end_date=datetime.fromisoformat(entity['thread_end_date']).date() if entity.get('thread_end_date') else None
        )


@dataclass
class ScrapingSession:
    """Represents a scraping session for tracking and monitoring."""

    session_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_threads: int = 0
    total_entries: int = 0
    new_entries: int = 0
    updated_entries: int = 0
    status: str = 'running'  # 'running', 'completed', 'failed'
    error_message: Optional[str] = None

    def to_table_entity(self) -> Dict[str, Any]:
        """Convert to Azure Table Storage entity format."""
        entity = {
            'PartitionKey': 'session',
            'RowKey': self.session_id,
            'started_at': self.started_at.isoformat() + 'Z',
            'completed_at': self.completed_at.isoformat() + 'Z' if self.completed_at else '',
            'total_threads': self.total_threads,
            'total_entries': self.total_entries,
            'new_entries': self.new_entries,
            'updated_entries': self.updated_entries,
            'status': self.status,
            'error_message': self.error_message or ''
        }
        return entity

    @classmethod
    def from_table_entity(cls, entity: Dict[str, Any]) -> 'ScrapingSession':
        """Create ScrapingSession from Azure Table Storage entity."""
        return cls(
            session_id=entity.get('RowKey', ''),
            started_at=datetime.fromisoformat(entity.get('started_at', datetime.utcnow().isoformat())),
            completed_at=datetime.fromisoformat(entity['completed_at']) if entity.get('completed_at') else None,
            total_threads=int(entity.get('total_threads', 0)),
            total_entries=int(entity.get('total_entries', 0)),
            new_entries=int(entity.get('new_entries', 0)),
            updated_entries=int(entity.get('updated_entries', 0)),
            status=entity.get('status', 'running'),
            error_message=entity.get('error_message', '') or None
        )


class TableStorageHelper:
    """Helper class for common Table Storage operations."""

    @staticmethod
    def create_filter_expression(filters: Dict[str, Any]) -> str:
        """Create OData filter expression for Azure Table Storage queries."""
        conditions = []

        for key, value in filters.items():
            if value is not None:
                if isinstance(value, str):
                    conditions.append(f"{key} eq '{value}'")
                elif isinstance(value, (int, float)):
                    conditions.append(f"{key} eq {value}")
                elif isinstance(value, bool):
                    conditions.append(f"{key} eq {str(value).lower()}")

        return " and ".join(conditions)

    @staticmethod
    def create_date_range_filter(date_field: str, start_date: Optional[date], end_date: Optional[date]) -> str:
        """Create date range filter for Table Storage queries."""
        conditions = []

        if start_date:
            conditions.append(f"{date_field} ge '{start_date.isoformat()}'")

        if end_date:
            conditions.append(f"{date_field} le '{end_date.isoformat()}'")

        return " and ".join(conditions)

    @staticmethod
    def validate_entity_keys(partition_key: str, row_key: str) -> tuple:
        """Validate and sanitize partition and row keys for Table Storage."""
        # Azure Table Storage has restrictions on key characters
        # Replace problematic characters but preserve @ and () for resort codes
        invalid_chars = ['/', '\\', '#', '?', '\t', '\n', '\r']

        sanitized_partition = partition_key
        sanitized_row = row_key

        for char in invalid_chars:
            sanitized_partition = sanitized_partition.replace(char, '_')
            sanitized_row = sanitized_row.replace(char, '_')

        # For resort codes with @ and (), create a safe partition key
        # but preserve the original in the resort field
        if '@' in sanitized_partition:
            sanitized_partition = sanitized_partition.replace('@', '_AT_')
        if '(' in sanitized_partition:
            sanitized_partition = sanitized_partition.replace('(', '_').replace(')', '_')

        # Ensure keys are not empty and within length limits (1024 chars max)
        sanitized_partition = sanitized_partition[:1024] if sanitized_partition else 'default'
        sanitized_row = sanitized_row[:1024] if sanitized_row else 'default'

        return sanitized_partition, sanitized_row


class ResortCodes:
    """Constants for DVC resort codes."""

    # DVC Resort Codes (from ROFR form)
    RESORTS = {
        'AKV': 'Animal Kingdom',
        'AUL': 'Aulani',
        'BLT': 'Bay Lake Tower',
        'BCV': 'Beach Club',
        'BWV': 'Boardwalk',
        'VDH': 'DL Hotel',
        'CFW': 'Fort Wilderness',
        'VGC': 'Grand Californian',
        'VGF': 'Grand Floridian',
        'HH': 'Hilton Head',
        'OKW': 'Old Key West (exp 2042)',
        'OKW(E)': 'Old Key West Extended (exp 2057)',
        'PVB': 'Polynesian',
        'RIV': 'Riviera',
        'SSR': 'Saratoga Springs',
        'VB': 'Vero Beach',
        'BRV@WL': 'Wilderness Lodge: Boulder Ridge',
        'CCV@WL': 'Wilderness Lodge: Copper Creek'
    }

    @classmethod
    def get_resort_name(cls, code: str) -> str:
        """Get full resort name from code."""
        return cls.RESORTS.get(code.upper(), code)

    @classmethod
    def is_valid_resort(cls, code: str) -> bool:
        """Check if resort code is valid."""
        # Handle case sensitivity and exact matching for codes with special chars
        return code in cls.RESORTS or code.upper() in cls.RESORTS

    @classmethod
    def get_all_resorts(cls) -> list:
        """Get all resort codes and names."""
        return [
            {'code': code, 'name': name}
            for code, name in cls.RESORTS.items()
        ]


@dataclass
class StatisticsData:
    """Represents statistics data for separate storage."""

    stat_type: str  # 'overview', 'resort', 'monthly', etc.
    stat_key: str   # specific key for the statistic
    stat_value: Any # the actual statistic value
    calculated_at: datetime
    metadata: Optional[Dict[str, Any]] = None

    def to_table_entity(self) -> Dict[str, Any]:
        """Convert to Azure Table Storage entity format."""
        entity = {
            'PartitionKey': self.stat_type,
            'RowKey': self.stat_key,
            'stat_value': str(self.stat_value),
            'calculated_at': self.calculated_at.isoformat() + 'Z',
            'metadata': str(self.metadata) if self.metadata else '',
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'updated_at': datetime.utcnow().isoformat() + 'Z'
        }
        return entity

    @classmethod
    def from_table_entity(cls, entity: Dict[str, Any]) -> 'StatisticsData':
        """Create StatisticsData from Azure Table Storage entity."""
        import json

        metadata = None
        if entity.get('metadata'):
            try:
                metadata = json.loads(entity['metadata'].replace("'", '"'))
            except:
                metadata = None

        return cls(
            stat_type=entity.get('PartitionKey', ''),
            stat_key=entity.get('RowKey', ''),
            stat_value=entity.get('stat_value', ''),
            calculated_at=datetime.fromisoformat(entity.get('calculated_at', datetime.utcnow().isoformat())),
            metadata=metadata
        )


class UseYearHelper:
    """Helper for use year validation and conversion."""

    VALID_USE_YEARS = [
        'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]

    MONTH_ABBREVIATIONS = {
        'January': 'Jan', 'February': 'Feb', 'March': 'Mar',
        'April': 'Apr', 'May': 'May', 'June': 'Jun',
        'July': 'Jul', 'August': 'Aug', 'September': 'Sep',
        'October': 'Oct', 'November': 'Nov', 'December': 'Dec'
    }

    @classmethod
    def normalize_use_year(cls, use_year: str) -> str:
        """Normalize use year to standard abbreviation."""
        use_year = use_year.strip().title()
        return cls.MONTH_ABBREVIATIONS.get(use_year, use_year)

    @classmethod
    def is_valid_use_year(cls, use_year: str) -> bool:
        """Check if use year is valid."""
        return use_year in cls.VALID_USE_YEARS
