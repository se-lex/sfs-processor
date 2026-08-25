"""
Government Agency Linking for Swedish Legal Documents.

MIT License

Copyright (c) 2025 Martin Rimskog

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

This module provides functions to link mentions of Swedish government agencies
(myndigheter) to their official websites. Agency data is sourced from:
https://github.com/civictechsweden/myndighetsdata

Usage:
    from formatters.apply_agency_links import apply_agency_links

    text = "Skatteverket har meddelat att..."
    linked_text = apply_agency_links(text)
    # Result: "[Skatteverket](https://www.skatteverket.se) har meddelat att..."
"""

import json
import re
import urllib.request
from pathlib import Path
from typing import Optional


# Cache for loaded agency data
_agency_data_cache: Optional[dict] = None

# URL to download agency data from (using handlingar.json for simpler structure)
AGENCY_DATA_URL = "https://raw.githubusercontent.com/civictechsweden/myndighetsdata/master/data/handlingar.json"


def _download_agency_data(agencies_file: Path, fallback_file: Path) -> bool:
    """
    Download agency data from GitHub, use fallback if download fails.

    Always attempts to download fresh data. If download fails, uses the
    committed fallback file if available.

    Args:
        agencies_file: Path to save the downloaded data (not in git)
        fallback_file: Path to fallback file (committed to git)

    Returns:
        True if file exists (downloaded or fallback), False otherwise
    """
    # Always try to download fresh data
    try:
        print(f"Laddar ner myndighetsdata från {AGENCY_DATA_URL}...")
        agencies_file.parent.mkdir(parents=True, exist_ok=True)

        with urllib.request.urlopen(AGENCY_DATA_URL, timeout=10) as response:
            data = response.read()

        with open(agencies_file, 'wb') as f:
            f.write(data)

        print(f"✓ Myndighetsdata nedladdad till {agencies_file}")
        return True

    except Exception as e:
        print(f"⚠ Varning: Kunde inte ladda ner myndighetsdata från {AGENCY_DATA_URL}: {e}")

        # Try to use fallback file
        if fallback_file.exists():
            print(f"  Använder fallback-fil: {fallback_file}")
            return True
        else:
            print("  Ingen fallback-fil hittades. Myndighetslänkar kommer inte att skapas.")
            return False


def _convert_handlingar_format(handlingar_data: dict) -> list:
    """
    Convert handlingar.json format to the expected agencies format.

    Input format (handlingar.json):
    {
        "Myndighet": {
            "short_name": "XX",
            "website": "https://...",
            ...
        }
    }

    Output format:
    [
        {
            "name": "Myndighet",
            "website": "https://...",
            "shortName": "XX",
            "alternativeNames": []
        }
    ]
    """
    agencies = []
    for name, data in handlingar_data.items():
        website = data.get('website', '')
        short_name = data.get('short_name', '')

        if not website:  # Skip agencies without websites
            continue

        agencies.append({
            'name': name,
            'website': website,
            'shortName': short_name,
            'alternativeNames': []
        })

    return agencies


def _load_agency_data() -> dict:
    """
    Load agency data from downloaded file or fallback.

    Returns a dictionary with:
    - 'by_name': dict mapping lowercase names to agency info
    - 'patterns': list of (regex_pattern, agency_info) tuples sorted by length (longest first)
    """
    global _agency_data_cache

    if _agency_data_cache is not None:
        return _agency_data_cache

    try:
        current_file = Path(__file__)
        project_root = current_file.parent.parent
        agencies_file = project_root / "data" / "agencies.json"
        fallback_file = project_root / "data" / "myndighetsdata_fallback.json"

        # Try to download, fall back to committed file if needed
        if not _download_agency_data(agencies_file, fallback_file):
            return {'by_name': {}, 'patterns': []}

        # Use downloaded file if it exists, otherwise use fallback
        file_to_load = agencies_file if agencies_file.exists() else fallback_file

        with open(file_to_load, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        # Convert from handlingar.json format if needed
        if isinstance(raw_data, dict) and not isinstance(raw_data, list):
            agencies = _convert_handlingar_format(raw_data)
        else:
            agencies = raw_data

        # Build lookup structures
        by_name = {}
        all_names = []  # (name, agency_info) tuples

        for agency in agencies:
            name = agency.get('name', '')
            website = agency.get('website', '')
            short_name = agency.get('shortName', '')
            alt_names = agency.get('alternativeNames', [])

            if not name or not website:
                continue

            agency_info = {
                'name': name,
                'website': website,
                'shortName': short_name
            }

            # Add primary name
            by_name[name.lower()] = agency_info
            all_names.append((name, agency_info))

            # Add short name if it's meaningful (more than 1 character)
            if short_name and len(short_name) > 1:
                by_name[short_name.lower()] = agency_info
                all_names.append((short_name, agency_info))

            # Add alternative names
            for alt_name in alt_names:
                if alt_name and len(alt_name) > 2:  # Skip very short abbreviations
                    by_name[alt_name.lower()] = agency_info
                    # Don't add all-caps versions that are just the same as primary name
                    if alt_name.upper() != name.upper():
                        all_names.append((alt_name, agency_info))

        # Sort names by length (longest first) to match longer names before shorter ones
        all_names.sort(key=lambda x: len(x[0]), reverse=True)

        # Build regex patterns
        patterns = []
        for name, info in all_names:
            # Escape special regex characters and create word boundary pattern
            escaped_name = re.escape(name)
            # Use word boundaries but handle Swedish characters
            pattern = rf'\b{escaped_name}\b'
            try:
                compiled = re.compile(pattern, re.IGNORECASE)
                patterns.append((compiled, info))
            except re.error:
                continue

        _agency_data_cache = {
            'by_name': by_name,
            'patterns': patterns
        }

        return _agency_data_cache

    except Exception as e:
        print(f"Fel vid laddning av myndighetsdata: {e}")
        return {'by_name': {}, 'patterns': []}


def apply_agency_links(text: str) -> str:
    """
    Find mentions of Swedish government agencies and convert them to markdown links.

    Searches for agency names (including alternative names and abbreviations) and
    creates links to their official websites.

    Args:
        text: The text to process

    Returns:
        Text with agency mentions converted to markdown links

    Example:
        >>> apply_agency_links("Enligt Skatteverket ska...")
        "[Skatteverket](https://www.skatteverket.se) ska..."
    """
    agency_data = _load_agency_data()

    if not agency_data['patterns']:
        return text

    lines = text.split('\n')
    processed_lines = []

    for line in lines:
        # Skip headings (lines starting with #)
        if line.strip().startswith('#'):
            processed_lines.append(line)
            continue

        # Skip lines that are already fully linked (simple heuristic)
        # Process each pattern
        processed_line = line

        for pattern, agency_info in agency_data['patterns']:
            # Find all matches first, then replace from end to start to preserve positions
            matches = list(pattern.finditer(processed_line))

            for match in reversed(matches):
                matched_text = match.group(0)
                start, end = match.start(), match.end()

                # Check if this match is already inside a markdown link
                # Look for [...] or (...) surrounding this match
                if _is_inside_markdown_link(processed_line, start, end):
                    continue

                # Create the link
                website = agency_info['website']
                link = f"[{matched_text}]({website})"

                # Replace this occurrence
                processed_line = processed_line[:start] + link + processed_line[end:]

        processed_lines.append(processed_line)

    return '\n'.join(processed_lines)


def _is_inside_markdown_link(text: str, start: int, end: int) -> bool:
    """
    Check if the given position range is inside an existing markdown link.

    Markdown links have format: [text](url)
    We need to avoid linking text that's already part of a link.
    """
    # Check if we're inside square brackets of a link
    # Find the nearest [ before our position
    bracket_start = text.rfind('[', 0, start)
    if bracket_start != -1:
        # Find matching ]
        bracket_end = text.find(']', bracket_start)
        if bracket_end != -1 and bracket_end >= end:
            # Check if there's a ( immediately after ]
            if bracket_end + 1 < len(text) and text[bracket_end + 1] == '(':
                # We're inside the link text
                return True

    # Check if we're inside parentheses of a link (the URL part)
    paren_start = text.rfind('](', 0, start)
    if paren_start != -1:
        paren_end = text.find(')', paren_start)
        if paren_end != -1 and paren_end >= end:
            return True

    return False


def count_agency_mentions(text: str) -> dict:
    """
    Count mentions of each agency in the text.

    Args:
        text: The text to analyze

    Returns:
        Dictionary mapping agency names to mention counts
    """
    agency_data = _load_agency_data()

    if not agency_data['patterns']:
        return {}

    counts = {}

    for pattern, agency_info in agency_data['patterns']:
        # Use the primary agency name as key
        agency_name = agency_info['name']

        matches = pattern.findall(text)
        if matches:
            if agency_name not in counts:
                counts[agency_name] = 0
            counts[agency_name] += len(matches)

    return counts


def get_all_agencies() -> list:
    """
    Get a list of all agencies with their information.

    Returns:
        List of agency dictionaries with name, website, shortName, and alternativeNames
    """
    try:
        current_file = Path(__file__)
        project_root = current_file.parent.parent
        agencies_file = project_root / "data" / "agencies.json"
        fallback_file = project_root / "data" / "myndighetsdata_fallback.json"

        # Try to download, fall back to committed file if needed
        if not _download_agency_data(agencies_file, fallback_file):
            return []

        # Use downloaded file if it exists, otherwise use fallback
        file_to_load = agencies_file if agencies_file.exists() else fallback_file

        with open(file_to_load, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        # Convert from handlingar.json format if needed
        if isinstance(raw_data, dict) and not isinstance(raw_data, list):
            return _convert_handlingar_format(raw_data)
        else:
            return raw_data
    except Exception:
        return []
