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
