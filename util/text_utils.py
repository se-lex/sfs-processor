#!/usr/bin/env python3
"""
Text cleaning and formatting utilities.
"""

import re
from typing import Optional

# Pattern for matching multiple whitespace characters
WHITESPACE_PATTERN = r'\s+'


def clean_text(text: Optional[str]) -> str:
    """Clean and format text content."""
    if not text:
        return ""

    # Remove extra whitespace and normalize line breaks
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(WHITESPACE_PATTERN, ' ', text).strip()
    return text