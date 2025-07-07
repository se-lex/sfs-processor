"""Datetime utility functions for SFS document processing."""

from datetime import datetime
from typing import Optional


def format_datetime(dt_str: Optional[str]) -> Optional[str]:
    """Format datetime string to ISO format without timezone."""
    if not dt_str:
        return None
    
    try:
        # Parse the datetime and format it as date only
        if 'T' in dt_str:
            dt = datetime.fromisoformat(dt_str.split('T')[0])
        else:
            dt = datetime.fromisoformat(dt_str)
        return dt.strftime('%Y-%m-%d')
    except (ValueError, AttributeError):
        return dt_str


def format_datetime_for_git(dt_str: Optional[str]) -> Optional[str]:
    """Format datetime string to full ISO format for git commits."""
    if not dt_str:
        return None
    
    try:
        # Parse the datetime and format it with time for git
        if 'T' in dt_str:
            # Already has time component
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00') if dt_str.endswith('Z') else dt_str)
        else:
            # Just date, add midnight time
            dt = datetime.fromisoformat(dt_str + 'T00:00:00')
        return dt.strftime('%Y-%m-%dT%H:%M:%S')
    except (ValueError, AttributeError):
        # Fallback: try to add time to basic date format
        if dt_str and len(dt_str) == 10:  # YYYY-MM-DD format
            return dt_str + 'T00:00:00'
        return dt_str
