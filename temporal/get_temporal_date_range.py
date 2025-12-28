#!/usr/bin/env python3
"""
Helper script to get the date range for temporal commits processing.

Returns the earliest pending date from kommande.yaml up to today,
which allows the daily workflow to catch up on missed dates.
"""

import sys
from datetime import date
from pathlib import Path

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from temporal.upcoming_changes import get_earliest_pending_date


def main():
    """Print the date range for temporal commits processing."""
    today = date.today().strftime('%Y-%m-%d')
    earliest = get_earliest_pending_date(today)

    if earliest:
        print(f"FROM_DATE={earliest}")
        print(f"TO_DATE={today}")
    else:
        # No pending dates found, use today only
        print(f"FROM_DATE={today}")
        print(f"TO_DATE={today}")


if __name__ == "__main__":
    main()
