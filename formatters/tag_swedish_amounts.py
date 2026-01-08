"""
Functions for tagging Swedish monetary amounts and percentages with <data> elements.

This module contains functions to identify and tag:
1. Swedish currency amounts (kronor, kr, SEK)
2. Percentages (%, procent)

Each match is wrapped in a <data> element with:
- type: "amount" or "percentage"
- value: normalized numeric value
- id: a descriptive slug based on context
"""

import re
from typing import Optional, Tuple
import unicodedata


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


def generate_amount_slug(context: str) -> str:
    """
    Generate a descriptive slug for an amount based on context.

    The slug identifies what the amount represents, not its value.
    This allows tracking changes across law amendments.

    Args:
        context: Surrounding text for context extraction

    Returns:
        A slug like "avgift" or "bidrag" that identifies the amount
    """
    # Extract a descriptive word from context
    prefix = _extract_context_word(context)

    return _slugify(prefix)


def generate_percentage_slug(context: str) -> str:
    """
    Generate a descriptive slug for a percentage based on context.

    The slug identifies what the percentage represents, not its value.
    This allows tracking changes across law amendments.

    Args:
        context: Surrounding text for context extraction

    Returns:
        A slug like "ranta" or "moms" that identifies the percentage
    """
    prefix = _extract_context_word(context)

    return _slugify(prefix)


def _extract_context_word(context: str) -> str:
    """
    Extract a descriptive word from the context preceding the amount/percentage.

    Looks for Swedish financial/legal terms that describe what the amount represents.

    Args:
        context: Text preceding the amount

    Returns:
        A descriptive word or "belopp"/"andel" as default
    """
    # Common Swedish terms that describe amounts
    amount_descriptors = [
        # Fees and charges
        r'(avgift(?:en)?)',
        r'(kostnad(?:en)?)',
        r'(pris(?:et)?)',
        r'(taxa(?:n)?)',
        r'(ers[äa]ttning(?:en)?)',
        r'(bidrag(?:et)?)',
        r'(understöd(?:et)?)',
        r'(arvode(?:t)?)',
        r'(lön(?:en)?)',
        # Limits and thresholds
        r'(gräns(?:en)?)',
        r'(tak(?:et)?)',
        r'(golv(?:et)?)',
        r'(minst)',
        r'(högst)',
        r'(max(?:imum)?)',
        r'(min(?:imum)?)',
        # Financial terms
        r'(kapital(?:et)?)',
        r'(belopp(?:et)?)',
        r'(summa(?:n)?)',
        r'(värde(?:t)?)',
        r'(inkomst(?:en)?)',
        r'(utgift(?:en)?)',
        r'(skatt(?:en)?)',
        r'(moms(?:en)?)',
        r'(böter(?:na)?)',
        r'(vite(?:t)?)',
        r'(skuld(?:en)?)',
        r'(fordran)',
        r'(tillgång(?:ar)?)',
        r'(omsättning(?:en)?)',
        # Insurance/pension
        r'(pension(?:en)?)',
        r'(försäkring(?:en)?)',
        r'(premie(?:n)?)',
        # Interest
        r'(ränt(?:a|an)?)',
        r'(avkastning(?:en)?)',
    ]

    # Percentage-specific descriptors
    percentage_descriptors = [
        r'(ränt(?:a|an|esats)?)',
        r'(andel(?:en)?)',
        r'(procentsats(?:en)?)',
        r'(moms(?:en)?)',
        r'(skatt(?:esats)?(?:en)?)',
        r'(avgift(?:ssats)?(?:en)?)',
        r'(avdrag(?:et)?)',
        r'(påslag(?:et)?)',
        r'(rabatt(?:en)?)',
        r'(höjning(?:en)?)',
        r'(sänkning(?:en)?)',
        r'(ökning(?:en)?)',
        r'(minskning(?:en)?)',
    ]

    all_descriptors = amount_descriptors + percentage_descriptors

    # Search backwards in context for descriptive words
    context_lower = context.lower()

    for pattern in all_descriptors:
        match = re.search(pattern, context_lower)
        if match:
            word = match.group(1)
            # Remove definite article suffixes for cleaner slugs
            # Only remove common Swedish article endings, being careful not to
            # remove parts of the base word (e.g., 't' in 'avgift')
            if word.endswith('erna'):
                word = word[:-4]
            elif word.endswith('arna'):
                word = word[:-4]
            elif word.endswith('en') and len(word) > 3:
                word = word[:-2]
            elif word.endswith('et') and len(word) > 3:
                word = word[:-2]
            elif word.endswith('na') and len(word) > 3:
                word = word[:-2]
            if word:
                return word

    return 'belopp'


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


def tag_swedish_amounts(text: str) -> str:
    """
    Tag Swedish monetary amounts and percentages in text with <data> elements.

    Processes text line by line, skipping markdown headers.
    Each amount/percentage is wrapped with a <data> tag containing:
    - id: descriptive slug
    - type: "amount" or "percentage"
    - value: normalized numeric value

    Args:
        text: The text to process

    Returns:
        Text with amounts and percentages wrapped in <data> tags

    Example:
        Input: "Avgiften är 1 000 kronor per år."
        Output: 'Avgiften är <data id="avgift-1000-kr" type="amount" value="1000">1 000 kronor</data> per år.'
    """
    lines = text.split('\n')
    processed_lines = []

    for line in lines:
        # Skip headers (lines starting with #)
        if line.strip().startswith('#'):
            processed_lines.append(line)
            continue

        # Skip lines that are inside XML/HTML tags (section tags, etc.)
        if re.match(r'^\s*</?(?:section|article)[^>]*>\s*$', line):
            processed_lines.append(line)
            continue

        # Process amounts and percentages
        processed_line = _tag_amounts_in_line(line)
        processed_line = _tag_percentages_in_line(processed_line)

        processed_lines.append(processed_line)

    return '\n'.join(processed_lines)


def _tag_amounts_in_line(line: str) -> str:
    """
    Tag monetary amounts in a single line.

    Args:
        line: A single line of text

    Returns:
        Line with amounts tagged
    """
    # First, try to match amounts with multipliers (miljoner, miljarder, tusen)
    def replace_amount_with_multiplier(match):
        full_match = match.group(0)
        number = match.group(1)

        # Get context (text before match)
        start_pos = match.start()
        context = line[:start_pos]

        normalized_value = normalize_number(number)
        slug = generate_amount_slug(context)

        return f'<data id="{slug}" type="amount" value="{normalized_value}">{full_match}</data>'

    # Then, match simple amounts (without multipliers)
    def replace_simple_amount(match):
        full_match = match.group(0)

        # Skip if already inside a <data> tag
        start_pos = match.start()
        if '<data' in line[max(0, start_pos-50):start_pos]:
            return full_match

        number = match.group(1)

        context = line[:start_pos]

        normalized_value = normalize_number(number)
        slug = generate_amount_slug(context)

        return f'<data id="{slug}" type="amount" value="{normalized_value}">{full_match}</data>'

    # Apply patterns
    result = AMOUNT_WITH_MULTIPLIER_PATTERN.sub(replace_amount_with_multiplier, line)
    result = AMOUNT_SIMPLE_PATTERN.sub(replace_simple_amount, result)

    return result


def _tag_percentages_in_line(line: str) -> str:
    """
    Tag percentages in a single line.

    Args:
        line: A single line of text

    Returns:
        Line with percentages tagged
    """
    def replace_percentage(match):
        full_match = match.group(0)

        # Skip if already inside a <data> tag
        start_pos = match.start()
        if '<data' in line[max(0, start_pos-50):start_pos]:
            return full_match

        number = match.group(1)

        context = line[:start_pos]

        normalized_value = normalize_number(number)
        slug = generate_percentage_slug(context)

        return f'<data id="{slug}" type="percentage" value="{normalized_value}">{full_match}</data>'

    return PERCENTAGE_PATTERN.sub(replace_percentage, line)
