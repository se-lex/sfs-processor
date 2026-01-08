"""
Parser for Swedish legal amendment notes (anteckningar).

This module parses the anteckningar field from ändringsförfattningar to extract
structured information about which paragraphs were repealed, amended, or added.

Example anteckningar:
    "upph. 29 kap. 15, 16 §§, rubr. närmast före 29 kap. 15 §; ändr. 10 kap. 37 §"

Parsed result:
    {
        'repealed': ['29kap15§', '29kap16§'],
        'amended': ['10kap37§'],
        'new': []
    }
"""

import re
from typing import Dict, List


def parse_anteckningar(anteckningar: str) -> Dict[str, List[str]]:
    """
    Parse Swedish amendment notes into structured data.

    Args:
        anteckningar: The anteckningar string from an ändringsförfattning

    Returns:
        Dictionary with keys:
            - 'repealed': List of normalized paragraph references that were repealed (upph.)
            - 'amended': List of normalized paragraph references that were amended (ändr.)
            - 'new': List of normalized paragraph references that were added (ny/nya)

    Example:
        >>> parse_anteckningar("upph. 29 kap. 15, 16 §§; ändr. 10 kap. 37 §")
        {'repealed': ['29kap15§', '29kap16§'], 'amended': ['10kap37§'], 'new': []}
    """
    result = {
        'repealed': [],
        'amended': [],
        'new': []
    }

    if not anteckningar or not anteckningar.strip():
        return result

    # Split on semicolons to separate major clauses
    clauses = anteckningar.split(';')

    for clause in clauses:
        clause = clause.strip()
        if not clause:
            continue

        # Identify action type and extract paragraphs
        if clause.startswith('upph.'):
            paragraphs = _extract_paragraphs(clause[5:].strip())  # Remove 'upph.'
            result['repealed'].extend(paragraphs)
        elif clause.startswith('ändr.'):
            paragraphs = _extract_paragraphs(clause[5:].strip())  # Remove 'ändr.'
            result['amended'].extend(paragraphs)
        elif clause.startswith('ny ') or clause.startswith('nya '):
            # Extract after 'ny ' or 'nya '
            start_idx = 3 if clause.startswith('nya') else 2
            paragraphs = _extract_paragraphs(clause[start_idx:].strip())
            result['new'].extend(paragraphs)

    return result


def _extract_paragraphs(text: str) -> List[str]:
    """
    Extract normalized paragraph references from a text fragment.

    Handles patterns like:
        - "29 kap. 15 §" → ['29kap15§']
        - "29 kap. 15, 16 §§" → ['29kap15§', '29kap16§']
        - "15 §" → ['15§']
        - "23 kap." → ['23kap'] (chapter-level, Phase 2)

    Args:
        text: Text fragment after the action keyword (upph./ändr./ny)

    Returns:
        List of normalized paragraph references
    """
    paragraphs = []

    # Skip patterns we don't handle yet (Phase 2)
    if 'rubr.' in text or 'betecknas' in text or 'nuvarande' in text:
        # Log for future enhancement but don't extract
        # These are complex patterns for Phase 2
        pass

    # Pattern 1: Chapter + paragraphs
    # Examples: "29 kap. 15, 16 §§", "29 kap. 15 §", "2 kap. 32, 33 §§"
    chapter_pattern = r'(\d+(?:\s*[a-z])?)\s*kap\.\s*((?:\d+(?:\s*[a-z])?(?:\s*,\s*)?)+)\s*§'

    for match in re.finditer(chapter_pattern, text, re.IGNORECASE):
        chapter = match.group(1).replace(' ', '').lower()
        para_list = match.group(2)

        # Split on commas to get individual paragraph numbers
        para_numbers = [p.strip().replace(' ', '').lower() for p in para_list.split(',')]

        for para_num in para_numbers:
            if para_num:  # Skip empty strings
                normalized = f"{chapter}kap{para_num}§"
                paragraphs.append(normalized)

    # Pattern 2: Chapter only (for chapter-level changes)
    # Example: "23 kap." (without paragraph reference)
    # Note: This is for Phase 2, but we detect it for completeness
    chapter_only_pattern = r'(\d+(?:\s*[a-z])?)\s*kap\.(?!\s*\d)'

    for match in re.finditer(chapter_only_pattern, text, re.IGNORECASE):
        chapter = match.group(1).replace(' ', '').lower()
        # Chapter-level change - skip for Phase 1
        # In Phase 2, we'd add: paragraphs.append(f"{chapter}kap")
        pass

    # Pattern 3: Paragraph without chapter
    # Examples: "15 §", "15, 16 §§"
    # These references are ambiguous without chapter context
    para_only_pattern = r'(?<!\d\s)(?<!kap\.\s)(\d+(?:\s*[a-z])?(?:\s*,\s*\d+(?:\s*[a-z])?)*)\s*§'

    # Only match if there's no chapter context before it
    if 'kap.' not in text:
        for match in re.finditer(para_only_pattern, text, re.IGNORECASE):
            para_list = match.group(1)
            para_numbers = [p.strip().replace(' ', '').lower() for p in para_list.split(',')]

            for para_num in para_numbers:
                if para_num:
                    normalized = f"{para_num}§"
                    paragraphs.append(normalized)

    return paragraphs


def _normalize_reference(chapter: str, paragraph: str) -> str:
    """
    Create a normalized section reference.

    Args:
        chapter: Chapter number (e.g., '29', '2a')
        paragraph: Paragraph number (e.g., '15', '15a')

    Returns:
        Normalized reference (e.g., '29kap15§', '2akap15a§')
    """
    chapter_clean = chapter.replace(' ', '').lower()
    para_clean = paragraph.replace(' ', '').lower()
    return f"{chapter_clean}kap{para_clean}§"
