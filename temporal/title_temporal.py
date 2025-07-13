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
        The appropriate title variant for the given date
    """
    if not rubrik:
        return ""
    
    # Parse target date
    try:
        target_dt = datetime.strptime(target_date, '%Y-%m-%d')
    except ValueError:
        # If target_date is invalid, return the original rubrik cleaned
        result = _clean_temporal_markers(rubrik)
        return clean_text(result)
    
    # Split the rubrik into lines to process temporal variants
    lines = rubrik.split('\n')
    
    # Parse the structure: expiry marker, old content, entry marker, new content
    old_title_lines = []
    new_title_lines = []
    expiry_date = None
    entry_date = None
    section = 'start'  # 'start', 'old', 'new'
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check for temporal markers
        expiry_match = re.match(r'/Rubriken upphör att gälla U:(\d{4}-\d{2}-\d{2})/', line)
        entry_match = re.match(r'/Rubriken träder i kraft I:(\d{4}-\d{2}-\d{2})/', line)
        
        if expiry_match:
            expiry_date = datetime.strptime(expiry_match.group(1), '%Y-%m-%d')
            section = 'old'
        elif entry_match:
            entry_date = datetime.strptime(entry_match.group(1), '%Y-%m-%d')
            section = 'new'
        else:
            # Regular content line
            if section == 'old':
                old_title_lines.append(line)
            elif section == 'new':
                new_title_lines.append(line)
    
    # Determine which title to use based on dates
    if expiry_date and entry_date:
        if target_dt < expiry_date:
            # Before expiry date - use old title
            result = _clean_temporal_markers('\n'.join(old_title_lines))
            return clean_text(result)
        elif target_dt >= entry_date:
            # On or after entry date - use new title
            result = _clean_temporal_markers('\n'.join(new_title_lines))
            return clean_text(result)
    
    # Fallback: clean the entire rubrik and return
    result = _clean_temporal_markers(rubrik)
    return clean_text(result)


def _clean_temporal_markers(text: str) -> str:
    """Remove temporal markers from text."""
    if not text:
        return ""
    
    # Remove temporal marker lines
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        # Skip temporal marker lines
        if not re.match(r'/Rubriken (upphör att gälla|träder i kraft)', line):
            cleaned_lines.append(line)
    
    # Join lines and clean up whitespace
    result = '\n'.join(cleaned_lines).strip()
    
    # Remove any remaining temporal markers that might be inline
    result = re.sub(r'/Rubriken (upphör att gälla|träder i kraft) [UI]:\d{4}-\d{2}-\d{2}/', '', result)
    
    # Clean up extra whitespace and line breaks
    result = re.sub(r'\n\s*\n', '\n', result)  # Remove empty lines
    result = re.sub(r'\s+', ' ', result)  # Normalize spaces
    
    return result.strip()