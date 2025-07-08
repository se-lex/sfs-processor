"""
Functions for applying internal and external links to SFS documents.

This module contains functions to:
1. Convert SFS references (e.g., "2002:43") to external markdown links
2. Convert paragraph references (e.g., "9 §", "13 a §") to internal markdown links
"""

import re
import os

# Regex patterns
SFS_PATTERN = r'\b(\d{4}):(\d+)\b'
PARAGRAPH_PATTERN = r'(\d+(?:\s*[a-z])?)\s*§'


def apply_sfs_links(text: str) -> str:
    """
    Letar efter SFS-beteckningar i texten och konverterar dem till markdown-länkar.

    Söker efter mönster som "YYYY:NNN" (år:löpnummer) och skapar länkar till /sfs/(beteckning).
    
    Använder miljövariabeln LINK_BASE_URL för att skapa absoluta länkar om den är satt,
    annars skapas relativa länkar.

    Args:
        text (str): Texten som ska bearbetas

    Returns:
        str: Texten med SFS-beteckningar konverterade till markdown-länkar
    """
    # Regex för att hitta SFS-beteckningar: år (4 siffror) följt av kolon och löpnummer
    # Matchar mönster som "2002:43", "1970:485", etc.
    sfs_pattern = SFS_PATTERN

    # Hämta bas-URL från miljövariabler (tom sträng som standard för relativa länkar)
    base_url = os.getenv('LINK_BASE_URL', '')

    # TODO: Slå upp SFS-beteckning mot JSON-fil för att verifiera giltighet

    def replace_sfs_designation(match):
        """Ersätter en SFS-beteckning med en markdown-länk"""
        year = match.group(1)
        number = match.group(2)
        designation = f"{year}:{number}"
        url = f"{base_url}/sfs/{year}/{number}"
        return f"[{designation}]({url})"

    # Ersätt alla SFS-beteckningar med markdown-länkar
    return re.sub(sfs_pattern, replace_sfs_designation, text)


def apply_internal_links(text: str) -> str:
    """
    Letar efter paragrafnummer i löpande text (inte i rubriker) och konverterar dem till interna länkar.

    Söker efter mönster som "9 §", "13 a §", "2 b §" etc. och skapar interna länkar
    till [9 §](#9§), [13 a §](#13a§), [2 b §](#2b§).

    Args:
        text (str): Texten som ska bearbetas

    Returns:
        str: Texten med paragrafnummer konverterade till interna markdown-länkar
    """
    lines = text.split('\n')
    processed_lines = []

    for line in lines:
        # Skippa rubriker (börjar med #)
        if line.strip().startswith('#'):
            processed_lines.append(line)
            continue

        # Regex för att hitta paragrafnummer: siffra, eventuell bokstav, följt av §
        # Matchar mönster som "9 §", "13 a §", "2 b §", "145 c §", etc.
        paragraph_pattern = PARAGRAPH_PATTERN

        def replace_paragraph_reference(match):
            """Ersätter en paragrafnummer med en intern markdown-länk"""
            full_match = match.group(0)
            number_and_letter = match.group(1)
            
            # Extrahera nummer och eventuell bokstav
            parts = number_and_letter.split()
            number = parts[0]
            letter = parts[1] if len(parts) > 1 else ''

            # Skapa länktext och anchor
            link_text = f"{number}{' ' + letter if letter else ''} §"
            # Anchor utan mellanslag för URL-kompatibilitet
            anchor = f"{number}{letter}§"

            return f"[{link_text}](#{anchor})"

        # Ersätt alla paragrafnummer med interna länkar
        processed_line = re.sub(paragraph_pattern, replace_paragraph_reference, line)
        processed_lines.append(processed_line)

    return '\n'.join(processed_lines)