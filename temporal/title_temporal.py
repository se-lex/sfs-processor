"""Temporal title selection utility for SFS documents."""

import re
from datetime import datetime
from typing import Optional

from util.text_utils import clean_text


def title_temporal(rubrik: Optional[str], target_date: str) -> str:
    """
    Select the appropriate title variant based on a target date.

    Handles titles with temporal rules like:
    "/Rubriken upphör att gälla U:2025-07-15/"
    "Förordning (2023:30) om statsbidrag..."
    "/Rubriken träder i kraft I:2025-07-15/"
    "Förordning om statsbidrag..."

    Args:
        rubrik: The title string containing temporal variants
        target_date: Date string in YYYY-MM-DD format

    Returns:
        The appropriate title variant for the given date (single line)
    """
    if not rubrik:
        return ""

    # Parse target date
    try:
        target_dt = datetime.strptime(target_date, '%Y-%m-%d')
    except ValueError:
        # If target_date is invalid, return the original rubrik cleaned
        return _process_title(rubrik)

    # Look for temporal markers and extract content between them
    expiry_match = re.search(r'/Rubriken upphör att gälla U:(\d{4}-\d{2}-\d{2})/', rubrik)
    entry_match = re.search(r'/Rubriken träder i kraft I:(\d{4}-\d{2}-\d{2})/', rubrik)

    if not expiry_match or not entry_match:
        # No temporal markers found, return cleaned rubrik
        return _process_title(rubrik)

    expiry_date = datetime.strptime(expiry_match.group(1), '%Y-%m-%d')
    entry_date = datetime.strptime(entry_match.group(1), '%Y-%m-%d')

    # Extract the old and new title parts
    expiry_pos = expiry_match.end()
    entry_pos = entry_match.start()

    # Old title is between expiry marker and entry marker
    old_title = rubrik[expiry_pos:entry_pos].strip()

    # New title is after entry marker
    new_title = rubrik[entry_match.end():].strip()

    # Determine which title to use based on dates
    if target_dt < expiry_date:
        # Before expiry date - use old title if available, otherwise new
        title = old_title if old_title else new_title
    else:
        # On or after expiry date - use new title if available, otherwise old
        title = new_title if new_title else old_title

    return _process_title(title)


def _process_title(text: str) -> str:
    """Process title text: remove temporal markers, line breaks, and clean."""
    if not text:
        return ""

    # Remove any temporal markers that might still be in the text
    text = re.sub(r'/Rubriken (upphör att gälla|träder i kraft) [UI]:\d{4}-\d{2}-\d{2}/', '', text)

    # Replace line breaks with spaces
    text = text.replace('\n', ' ').replace('\r', ' ')

    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()

    # Apply final cleaning (removes document numbers etc.)
    return clean_text(text)
