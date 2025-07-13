#!/usr/bin/env python3
"""
Text cleaning and formatting utilities.
"""

import re
from typing import Optional

# Pattern for matching multiple whitespace characters
WHITESPACE_PATTERN = r'\s+'


def clean_text(text: Optional[str]) -> str:
    """Clean text by removing beteckning in parentheses and line breaks."""
    if not text:
        return ""

    # Remove line breaks and carriage returns
    cleaned = re.sub(r'[\r\n]+', ' ', text)
    
    # Remove beteckning pattern in parentheses (e.g., "(1987:1185)")
    # Pattern matches parentheses containing year:number format
    # First remove the parentheses and their content, then clean up extra whitespace
    cleaned = re.sub(r'\s*\(\d{4}:\d+\)\s*', ' ', cleaned)

    # Clean up any multiple spaces that might have been created
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    return cleaned