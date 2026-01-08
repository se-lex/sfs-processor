"""
Functions for tagging Swedish monetary amounts and percentages with <data> elements.

This module contains functions to identify and tag:
1. Swedish currency amounts (kronor, kr, SEK)
2. Percentages (%, procent)

Each match is wrapped in a <data> element with:
- type: "amount" or "percentage"
- value: normalized numeric value
- id: a reference id based on section + position, or a custom slug from reference table

The reference table (data/amount-references.json) maps positional ids to
descriptive slugs like "riksbankens-referensranta".
"""

import re
import json
from pathlib import Path
from typing import Optional, Dict
import unicodedata


# Cache for reference table
_reference_table: Optional[Dict[str, str]] = None


# ============================================================================
# Regex patterns for Swedish amounts
# ============================================================================

# Number patterns - Swedish uses space as thousands separator and comma for decimals
# Matches: 1 000, 1000, 1 000 000, 1,5, 1.5
_NUMBER_PATTERN = r'(\d[\d\s]*(?:[,\.]\d+)?)'

# Currency units
_KRONOR_PATTERN = r'(?:kronor|kr\.?|SEK)'
_MILJON_PATTERN = r'(?:miljon(?:er)?)'
_MILJARD_PATTERN = r'(?:miljard(?:er)?)'
_TUSENTAL_PATTERN = r'(?:tusen)'

# Full amount patterns with lookahead/lookbehind to avoid matching inside tags/links
# Pattern 1: X kronor/kr/SEK
AMOUNT_SIMPLE_PATTERN = re.compile(
    rf'(?<![>\w])({_NUMBER_PATTERN})\s*({_KRONOR_PATTERN})(?![<\w])',
    re.IGNORECASE
)

# Pattern 2: X miljoner/miljarder/tusen kronor
AMOUNT_WITH_MULTIPLIER_PATTERN = re.compile(
    rf'(?<![>\w])({_NUMBER_PATTERN})\s*({_TUSENTAL_PATTERN}|{_MILJON_PATTERN}|{_MILJARD_PATTERN})\s*({_KRONOR_PATTERN})(?![<\w])',
    re.IGNORECASE
)

# ============================================================================
# Regex patterns for percentages
# ============================================================================

# Pattern: X %, X%, X procent
PERCENTAGE_PATTERN = re.compile(
    rf'(?<![>\w])({_NUMBER_PATTERN})\s*(%|procent)(?![<\w])',
    re.IGNORECASE
)


def normalize_number(num_str: str) -> str:
    """
    Normalize a Swedish number string to a standard format.

    Removes spaces (thousands separator) and converts comma to dot for decimals.

    Args:
        num_str: Number string like "1 000 000" or "1,5"

    Returns:
        Normalized number string like "1000000" or "1.5"
    """
    # Remove all whitespace
    normalized = re.sub(r'\s+', '', num_str)
    # Convert Swedish decimal comma to dot
    normalized = normalized.replace(',', '.')
    return normalized


def load_reference_table() -> Dict[str, str]:
    """
    Load the amount reference table from data/amount-references.json.

    The reference table maps positional ids (e.g., "kap5.2-belopp-1") to
    descriptive slugs (e.g., "riksbankens-referensranta").

    Returns:
        Dictionary mapping positional ids to descriptive slugs
    """
    global _reference_table

    if _reference_table is not None:
        return _reference_table

    try:
        current_file = Path(__file__)
        project_root = current_file.parent.parent
        ref_file = project_root / "data" / "amount-references.json"

        if ref_file.exists():
            with open(ref_file, 'r', encoding='utf-8') as f:
                _reference_table = json.load(f)
        else:
            _reference_table = {}

    except Exception as e:
        print(f"Warning: Could not load amount references: {e}")
        _reference_table = {}

    return _reference_table


def generate_positional_id(sfs_id: Optional[str], section_id: Optional[str], data_type: str, position: int) -> str:
    """
    Generate a positional id for a data element.

    Args:
        sfs_id: The SFS designation (e.g., "2024:123") or None
        section_id: The section id (e.g., "kap5.2") or None
        data_type: "belopp" for amounts, "procent" for percentages
        position: 1-based position within the section for this type

    Returns:
        A positional id like "sfs-2024-123-kap5.2-belopp-1"
    """
    parts = []

    if sfs_id:
        # Normalize SFS id: "2024:123" -> "sfs-2024-123"
        normalized_sfs = "sfs-" + sfs_id.replace(":", "-")
        parts.append(normalized_sfs)

    if section_id:
        parts.append(section_id)

    parts.append(f"{data_type}-{position}")

    return "-".join(parts)


def resolve_id(positional_id: str) -> str:
    """
    Resolve a positional id to a descriptive slug using the reference table.

    If no mapping exists, returns the positional id as-is.

    Args:
        positional_id: The positional id (e.g., "kap5.2-belopp-1")

    Returns:
        The descriptive slug if found, otherwise the positional id
    """
    ref_table = load_reference_table()
    return ref_table.get(positional_id, positional_id)


def _slugify(text: str) -> str:
    """
    Convert text to a URL-safe slug.

    Args:
        text: Text to slugify

    Returns:
        Lowercase ASCII slug with hyphens
    """
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)
    # Convert Swedish characters
    text = text.replace('å', 'a').replace('ä', 'a').replace('ö', 'o')
    text = text.replace('Å', 'a').replace('Ä', 'a').replace('Ö', 'o')
    # Remove non-ASCII characters
    text = text.encode('ASCII', 'ignore').decode('ASCII')
    # Convert to lowercase
    text = text.lower()
    # Replace spaces and special chars with hyphens
    text = re.sub(r'[^a-z0-9]+', '-', text)
    # Remove leading/trailing hyphens
    text = text.strip('-')
    # Collapse multiple hyphens
    text = re.sub(r'-+', '-', text)

    return text


def tag_swedish_amounts(text: str, sfs_id: Optional[str] = None, section_id: Optional[str] = None) -> str:
    """
    Tag Swedish monetary amounts and percentages in text with <data> elements.

    Processes text line by line, skipping markdown headers.
    Each amount/percentage is wrapped with a <data> tag containing:
    - id: positional id or resolved slug from reference table
    - type: "amount" or "percentage"
    - value: normalized numeric value

    Args:
        text: The text to process
        sfs_id: Optional SFS designation (e.g., "2024:123") for generating positional ids
        section_id: Optional section id for generating positional ids (e.g., "kap5.2")

    Returns:
        Text with amounts and percentages wrapped in <data> tags

    Example:
        Input: "Avgiften är 1 000 kronor." with sfs_id="2024:123", section_id="kap5.2"
        Output: '<data id="sfs-2024-123-kap5.2-belopp-1" type="amount" value="1000">...</data>'

        With reference table {"sfs-2024-123-kap5.2-belopp-1": "tillstandsavgift"}:
        Output: '<data id="tillstandsavgift" type="amount" value="1000">...</data>'

    Multiple SFS entries can map to the same slug to track changes over time:
        {"sfs-2020-100-kap5.2-belopp-1": "tillstandsavgift",
         "sfs-2024-123-kap5.2-belopp-1": "tillstandsavgift"}
    """
    lines = text.split('\n')
    processed_lines = []

    # Track current SFS, section and counters
    current_sfs = sfs_id
    current_section = section_id
    amount_counter = 0
    percentage_counter = 0

    for line in lines:
        # Skip headers (lines starting with #)
        if line.strip().startswith('#'):
            processed_lines.append(line)
            continue

        # Check for article tags to extract SFS id
        article_match = re.match(r'^\s*<article[^>]*\bselex:id=["\']([^"\']+)["\']', line)
        if article_match:
            # Extract SFS id from selex:id like "lag-2024-123" -> "2024:123"
            selex_id = article_match.group(1)
            sfs_match = re.search(r'(\d{4})-(\d+)', selex_id)
            if sfs_match:
                current_sfs = f"{sfs_match.group(1)}:{sfs_match.group(2)}"
            processed_lines.append(line)
            continue

        # Check for section tags to extract section id
        section_match = re.match(r'^\s*<section[^>]*\bid=["\']([^"\']+)["\']', line)
        if section_match:
            current_section = section_match.group(1)
            amount_counter = 0  # Reset counters for new section
            percentage_counter = 0
            processed_lines.append(line)
            continue

        # Skip lines that are inside XML/HTML tags (section tags, etc.)
        if re.match(r'^\s*</?(?:section|article)[^>]*>\s*$', line):
            processed_lines.append(line)
            continue

        # Process amounts and percentages with counters
        processed_line, new_amount_count = _tag_amounts_in_line(
            line, current_sfs, current_section, amount_counter
        )
        amount_counter = new_amount_count

        processed_line, new_percentage_count = _tag_percentages_in_line(
            processed_line, current_sfs, current_section, percentage_counter
        )
        percentage_counter = new_percentage_count

        processed_lines.append(processed_line)

    return '\n'.join(processed_lines)


def _tag_amounts_in_line(
    line: str,
    sfs_id: Optional[str],
    section_id: Optional[str],
    counter: int
) -> tuple[str, int]:
    """
    Tag monetary amounts in a single line.

    Args:
        line: A single line of text
        sfs_id: Current SFS designation for positional ids
        section_id: Current section id for positional ids
        counter: Current count of amounts in this section

    Returns:
        Tuple of (processed line, updated counter)
    """
    current_counter = counter

    # First, try to match amounts with multipliers (miljoner, miljarder, tusen)
    def replace_amount_with_multiplier(match):
        nonlocal current_counter
        full_match = match.group(0)
        number = match.group(1)

        current_counter += 1
        positional_id = generate_positional_id(sfs_id, section_id, "belopp", current_counter)
        resolved_id = resolve_id(positional_id)

        normalized_value = normalize_number(number)

        return f'<data id="{resolved_id}" type="amount" value="{normalized_value}">{full_match}</data>'

    # Then, match simple amounts (without multipliers)
    def replace_simple_amount(match):
        nonlocal current_counter
        full_match = match.group(0)

        # Skip if already inside a <data> tag
        start_pos = match.start()
        if '<data' in line[max(0, start_pos-50):start_pos]:
            return full_match

        number = match.group(1)

        current_counter += 1
        positional_id = generate_positional_id(sfs_id, section_id, "belopp", current_counter)
        resolved_id = resolve_id(positional_id)

        normalized_value = normalize_number(number)

        return f'<data id="{resolved_id}" type="amount" value="{normalized_value}">{full_match}</data>'

    # Apply patterns
    result = AMOUNT_WITH_MULTIPLIER_PATTERN.sub(replace_amount_with_multiplier, line)
    result = AMOUNT_SIMPLE_PATTERN.sub(replace_simple_amount, result)

    return result, current_counter


def _tag_percentages_in_line(
    line: str,
    sfs_id: Optional[str],
    section_id: Optional[str],
    counter: int
) -> tuple[str, int]:
    """
    Tag percentages in a single line.

    Args:
        line: A single line of text
        sfs_id: Current SFS designation for positional ids
        section_id: Current section id for positional ids
        counter: Current count of percentages in this section

    Returns:
        Tuple of (processed line, updated counter)
    """
    current_counter = counter

    def replace_percentage(match):
        nonlocal current_counter
        full_match = match.group(0)

        # Skip if already inside a <data> tag
        start_pos = match.start()
        if '<data' in line[max(0, start_pos-50):start_pos]:
            return full_match

        number = match.group(1)

        current_counter += 1
        positional_id = generate_positional_id(sfs_id, section_id, "procent", current_counter)
        resolved_id = resolve_id(positional_id)

        normalized_value = normalize_number(number)

        return f'<data id="{resolved_id}" type="percentage" value="{normalized_value}">{full_match}</data>'

    result = PERCENTAGE_PATTERN.sub(replace_percentage, line)
    return result, current_counter
