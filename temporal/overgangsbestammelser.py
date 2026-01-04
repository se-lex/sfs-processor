"""Övergångsbestämmelser processing utilities for SFS documents."""

import re
from typing import Dict, Any, List


def add_overgangsbestammelser_for_amendment_to_text(
        text: str,
        beteckning: str,
        overgangs_content: str,
        verbose: bool = False) -> str:
    """
    Add Övergångsbestämmelser content for a specific beteckning to the text.

    Args:
        text: The markdown text to modify
        beteckning: The beteckning identifier
        overgangs_content: The övergångsbestämmelser content to add
        verbose: Whether to print verbose output

    Returns:
        str: The text with övergångsbestämmelser content added
    """
    # Format the content with the beteckning as a bold heading
    formatted_overgangs_content = f"**{beteckning}**\n\n{overgangs_content}"

    # Find the existing Övergångsbestämmelser heading and any existing content
    overgangs_section_match = re.search(
        r'(### Övergångsbestämmelser\s*\n\n)(.*?)(?=\n### |\n## |\Z)', text, re.DOTALL)
    if overgangs_section_match:
        heading_part = overgangs_section_match.group(1)
        existing_content = overgangs_section_match.group(2).strip()

        if existing_content:
            # There's already content under the heading, add after it
            content_to_insert = f"\n\n{formatted_overgangs_content}"
            insert_pos = overgangs_section_match.end() - len(overgangs_section_match.group(0)) + \
                len(heading_part) + len(existing_content)
            text = text[:insert_pos] + content_to_insert + text[insert_pos:]

            if verbose:
                print(f"Lade till övergångsbestämmelser för {beteckning} efter befintligt innehåll")
        else:
            # No existing content, add directly after heading
            insert_pos = overgangs_section_match.start() + len(heading_part)
            content_to_insert = f"{formatted_overgangs_content}\n\n"
            text = text[:insert_pos] + content_to_insert + text[insert_pos:]

            if verbose:
                print(
                    f"Lade till övergångsbestämmelser för {beteckning} under rubrik (inget befintligt innehåll)")
    else:
        # Fallback: add the section at the end if heading doesn't exist
        overgangs_section = f"\n\n### Övergångsbestämmelser\n\n{formatted_overgangs_content}\n"
        text = text.rstrip() + overgangs_section

        if verbose:
            print(
                f"Skapade ny övergångsbestämmelser-sektion för {beteckning} (rubrik hittades inte)")

    return text


def parse_overgangsbestammelser(
        text: str, amendments: List[Dict[str, Any]], verbose: bool = False) -> Dict[str, str]:
    """
    Parse 'Övergångsbestämmelser' section and organize by amendment beteckning.

    Args:
        text: The markdown text to parse
        amendments: List of amendments with beteckning information
        verbose: Whether to print verbose output

    Returns:
        Dict mapping beteckning to its övergångsbestämmelser content
    """
    overgangs_dict = {}

    # Find the Övergångsbestämmelser section
    overgangs_match = re.search(
        r'### Övergångsbestämmelser\s*\n\n(.*?)(?=\n### |\n## |\Z)',
        text,
        re.DOTALL)
    if not overgangs_match:
        if verbose:
            print("Ingen 'Övergångsbestämmelser'-sektion hittades")
        return overgangs_dict

    overgangs_content = overgangs_match.group(1).strip()

    # Get all betecknings from amendments
    betecknings = [a.get('beteckning') for a in amendments if a.get('beteckning')]

    if not betecknings:
        return overgangs_dict

    # Create regex pattern to match any beteckning
    betecknings_pattern = '|'.join(re.escape(b) for b in betecknings)

    # Split content by betecknings
    split_pattern = f'({betecknings_pattern})'
    parts = re.split(split_pattern, overgangs_content)

    current_beteckning = None
    for part in parts:
        part = part.strip()
        if not part:
            continue

        if part in betecknings:
            current_beteckning = part
            overgangs_dict[current_beteckning] = ""
        elif current_beteckning and part:
            # Add content to current beteckning
            if overgangs_dict[current_beteckning]:
                overgangs_dict[current_beteckning] += "\n\n" + part
            else:
                overgangs_dict[current_beteckning] = part

    if verbose:
        print(
            f"Hittade övergångsbestämmelser för dessa författningar: {list(overgangs_dict.keys())}")
        for beteckning, content in overgangs_dict.items():
            print(f"  {beteckning}: {len(content)} tecken")

    return overgangs_dict
