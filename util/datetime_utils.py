"""Datetime utility functions for SFS document processing."""

from datetime import datetime
from typing import Optional


def get_min_git_year() -> int:
    """
    Get the minimum year for git commits.

    Returns:
        int: Minimum year (default: 1980)

    Note:
        Git/GitHub has problems with very old dates, so we use 1980-01-01 as minimum.
        This can be configured via config.git.min_year.
    """
    try:
        from config import get_config
        return get_config().git.min_year
    except ImportError:
        # Fallback if config module not available
        return 1980


# Backwards compatibility: keep MIN_GIT_YEAR constant
MIN_GIT_YEAR = get_min_git_year()


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

    min_year = get_min_git_year()

    try:
        # Parse the datetime and format it with time for git
        if 'T' in dt_str:
            # Already has time component
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00') if dt_str.endswith('Z') else dt_str)
        else:
            # Just date, add midnight time
            dt = datetime.fromisoformat(dt_str + 'T00:00:00')

        if dt.year < min_year:
            return f"{min_year}-01-01T00:00:00"

        return dt.strftime('%Y-%m-%dT%H:%M:%S')
    except (ValueError, AttributeError):
        # Fallback: try to add time to basic date format
        if dt_str and len(dt_str) == 10:  # YYYY-MM-DD format
            year = int(dt_str[:4])
            if year < min_year:
                return f"{min_year}-01-01T00:00:00"
            return dt_str + 'T00:00:00'
        return dt_str
