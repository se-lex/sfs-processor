"""
Functions for applying internal and external links to SFS documents.

This module contains functions to:
1. Convert SFS references (e.g., "2002:43") to external markdown links
2. Convert paragraph references (e.g., "9 §", "13 a §") to internal markdown links
3. Convert EU legislation references (e.g., "(EU) nr 651/2014") to EUR-Lex links
"""

import re
import os
import json
from pathlib import Path

# Regex patterns
SFS_PATTERN = r'\b(\d{4}):(\d+)\b'
PARAGRAPH_PATTERN = r'(\d+(?:\s*[a-z])?)\s*§'

# EU legislation patterns
# Modern format: (EU) nr XXX/YYYY or (EU) YYYY/XXX
EU_REGULATION_PATTERN = r'\(EU\)(?:\s*[Nn]r)?(?:\s*(\d+)/(\d{4})|\s*(\d{4})/(\d+))'

# Older formats: XX/YY/EEG, XXX/YY/EEG, XX/YYY/EEG, XXX/YYY/EEG
EU_EEG_PATTERN = r'(\d{2,3})/(\d{2,3})/EEG'

# Older formats: XX/YY/EG, XXX/YY/EG, XX/YYY/EG, XXX/YYY/EG  
EU_EG_PATTERN = r'(\d{2,3})/(\d{2,3})/EG'

# Law name pattern - kapitel följt av eventuella paragrafer och lagnamn
# Hanterar olika format som:
# - 2 kap. 10 a–10 c §§ socialförsäkringsbalken  
# - 58 kap. 26 och 27 §§ socialförsäkringsbalken
# - 8 kap. 7 § regeringsformen
# - 8 eller 9 § någonlagen
LAW_NAME_PATTERN = r'(\d+)\s+kap\.\s*([^.]*?)\b([a-zåäöA-ZÅÄÖ-]+(?:lagen|balken|formen|boken|ordningen))\b'


def apply_sfs_links(text: str) -> str:
    """
    Letar efter SFS-beteckningar i texten och konverterar dem till markdown-länkar.

    Söker efter mönster som "YYYY:NNN" (år:löpnummer) och skapar länkar till /sfs/(beteckning).
    
    Använder miljövariabeln INTERNAL_LINKS_BASE_URL för att skapa absoluta länkar om den är satt,
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
    base_url = os.getenv('INTERNAL_LINKS_BASE_URL', '')

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

        # Skippa inte rader med SFS-länkar, bara hantera dem försiktigt
        # Vi behöver bara undvika att länka paragrafer som redan är del av SFS-länkar

        # Regex för att hitta paragrafnummer: siffra, eventuell bokstav, följt av §
        # Matchar mönster som "9 §", "13 a §", "2 b §", "145 c §", etc.
        paragraph_pattern = PARAGRAPH_PATTERN

        # Använd en mer robust approach: ersätt bara paragrafer som inte redan är i markdown-länkar
        
        def replace_paragraph_reference(match):
            """Ersätter en paragrafnummer med en intern markdown-länk"""
            full_match = match.group(0)
            number_and_letter = match.group(1)
            start_pos = match.start()
            end_pos = match.end()
            
            # Kontrollera om denna paragraf är inuti en befintlig markdown-länk
            # Leta efter närmaste [ före denna position och ] efter denna position
            left_bracket = line.rfind('[', 0, start_pos)
            if left_bracket != -1:
                # Hitta matchande ] efter denna position
                bracket_count = 1
                search_pos = left_bracket + 1
                while search_pos < len(line) and bracket_count > 0:
                    if line[search_pos] == '[':
                        bracket_count += 1
                    elif line[search_pos] == ']':
                        bracket_count -= 1
                    search_pos += 1
                
                # Om vi hittade matchande ] och vår paragraf är mellan [ och ]
                if bracket_count == 0 and search_pos > end_pos:
                    # Kontrollera om det finns () direkt efter ]
                    if search_pos < len(line) and line[search_pos] == '(':
                        paren_end = line.find(')', search_pos)
                        if paren_end != -1:
                            return full_match  # Vi är inne i en markdown-länk, skippa
            
            # Extrahera nummer och eventuell bokstav
            parts = number_and_letter.split()
            number = parts[0]
            letter = parts[1] if len(parts) > 1 else ''

            # Skapa länktext och anchor
            link_text = f"{number}{' ' + letter if letter else ''} §"
            # Anchor utan mellanslag och § för URL-kompatibilitet
            anchor = f"{number}{letter}"

            return f"[{link_text}](#{anchor})"

        # Ersätt alla paragrafnummer med interna länkar
        processed_line = re.sub(paragraph_pattern, replace_paragraph_reference, line)
        processed_lines.append(processed_line)

    return '\n'.join(processed_lines)


def apply_law_name_links(text: str) -> str:
    """
    Letar efter lagnamnsreferenser i texten och konverterar dem till SFS markdown-länkar.

    Söker efter mönster som "2 kap. 10 a–10 c §§ socialförsäkringsbalken", 
    "8 kap. 7 § regeringsformen", etc. och skapar länkar till SFS-dokument
    baserat på lagnamn från data/law-names.json.

    Använder miljövariabeln INTERNAL_LINKS_BASE_URL för att skapa absoluta länkar om den är satt,
    annars skapas relativa länkar.

    Args:
        text (str): Texten som ska bearbetas

    Returns:
        str: Texten med lagnamnsreferenser konverterade till markdown-länkar
    """
    # Ladda lagnamn från JSON-fil
    law_names_data = _load_law_names()
    if not law_names_data:
        return text

    # Hämta bas-URL från miljövariabler
    base_url = os.getenv('INTERNAL_LINKS_BASE_URL', '')
    
    # Processar texten rad för rad för att undvika att länka rubriker
    lines = text.split('\n')
    processed_lines = []

    for line in lines:
        # Skippa rubriker (börjar med #)
        if line.strip().startswith('#'):
            processed_lines.append(line)
            continue

        def replace_law_name_reference(match):
            """Ersätter en lagnamnsreferens med en markdown-länk"""
            chapter = match.group(1)
            paragraph_part = match.group(2).strip()
            law_name = match.group(3).lower()
            full_match = match.group(0)
            
            # Leta upp lagnamnet i data
            sfs_id = _lookup_law_name(law_name, law_names_data)
            
            if not sfs_id:
                print(f"Varning: Okänt lagnamn '{law_name}' i referens '{full_match}'")
                return full_match  # Returnera oförändrat om lagnamnet inte hittas
            
            # Extrahera år och nummer från SFS-ID (format: "YYYY:NNN")
            id_parts = sfs_id.split(':')
            if len(id_parts) != 2:
                print(f"Varning: Ogiltigt SFS-ID format '{sfs_id}' för lagnamn '{law_name}'")
                return full_match
            
            year, number = id_parts
            
            # Skapa bas-URL
            if base_url:
                url = f"{base_url}/sfs/{year}/{number}"
            else:
                url = f"/sfs/{year}/{number}"
            
            # Extrahera första paragrafnummer för anchor om det finns
            # För externa länkar (till annan författning) ska formatet vara: #kapX.Y
            # där X är kapitelnummer och Y är paragrafnummer
            first_paragraph = _extract_first_paragraph(paragraph_part)
            if first_paragraph:
                url += f"#kap{chapter}.{first_paragraph}"  # Format: #kap1.2
            
            return f"[{full_match}]({url})"

        # Ersätt alla lagnamnsreferenser med markdown-länkar
        processed_line = re.sub(LAW_NAME_PATTERN, replace_law_name_reference, line)
        processed_lines.append(processed_line)

    return '\n'.join(processed_lines)


def _load_law_names():
    """
    Laddar lagnamn från data/law-names.json.
    
    Returns:
        dict: Dictionary med lagnamn som nycklar och SFS-ID som värden, eller None om fel
    """
    try:
        # Hitta JSON-filen relativt till projektets rot
        current_file = Path(__file__)
        project_root = current_file.parent.parent  # från formatters/ till projektrot
        law_names_file = project_root / "data" / "law-names.json"
        
        if not law_names_file.exists():
            print(f"Varning: Kunde inte hitta {law_names_file}")
            return None
            
        with open(law_names_file, 'r', encoding='utf-8') as f:
            law_data = json.load(f)
        
        # Skapa lookup-dictionary: lagnamn -> SFS-ID
        law_lookup = {}
        for entry in law_data:
            if entry.get('name'):
                law_lookup[entry['name'].lower()] = entry['id']
        
        return law_lookup
        
    except Exception as e:
        print(f"Fel vid laddning av lagnamn: {e}")
        return None


def _lookup_law_name(law_name: str, law_names_data: dict) -> str:
    """
    Slår upp ett lagnamn i lagnamnsdata.
    
    Args:
        law_name (str): Lagnamnet att slå upp (lowercase)
        law_names_data (dict): Dictionary med lagnamn och SFS-ID
        
    Returns:
        str: SFS-ID eller None om lagnamnet inte hittas
    """
    return law_names_data.get(law_name.lower())


def _extract_first_paragraph(paragraph_part: str) -> str:
    """
    Extraherar första paragrafnummer från en paragraftext.
    
    Hanterar format som:
    - "7 §" -> "7"
    - "10 a–10 c §§" -> "10a"
    - "26 och 27 §§" -> "26"
    - "8 eller 9 §" -> "8"
    - "2, 3 och 4 §§" -> "2"
    
    Args:
        paragraph_part (str): Texten mellan kapitel och lagnamn
        
    Returns:
        str: Första paragrafnummer med eventuell bokstav, eller None om inget hittas
    """
    if not paragraph_part:
        return None
    
    # Sök efter första förekomst av paragrafnummer (siffra + eventuell bokstav följt av icke-bokstav)
    # Matchar mönster som "7", "10 a", "26", "8" men inte "26o" från "26 och"
    match = re.search(r'(\d+)(?:\s+([a-z])(?!\w))?', paragraph_part)
    if match:
        number = match.group(1)
        letter = match.group(2) or ''
        return f"{number}{letter}"
    
    return None


def apply_eu_links(text: str) -> str:
    """
    Letar efter EU-lagstiftningsreferenser i texten och konverterar dem till EUR-Lex länkar.

    Hanterar olika format:
    - Modern: "(EU) nr 651/2014", "(EU) 1234/2020" 
    - Äldre: "92/43/EEG", "95/46/EG"

    Args:
        text (str): Texten som ska bearbetas

    Returns:
        str: Texten med EU-referenser konverterade till markdown-länkar
    """
    def replace_eu_reference(match):
        """Ersätter en EU-referens med en markdown-länk till EUR-Lex"""
        full_match = match.group(0)
        
        # Extract year and number from the different capture groups
        if match.group(1) and match.group(2):  # nr 651/2014 format
            number = match.group(1)
            year = match.group(2)
        elif match.group(3) and match.group(4):  # 2014/651 format
            year = match.group(3)
            number = match.group(4)
        else:
            return full_match  # Couldn't parse, return unchanged
        
        # Create CELEX number: 3YYYYRNNNNN (R for regulation)
        celex = f"3{year}R{number.zfill(4)}"
        
        # Create EUR-Lex URL
        url = f"https://eur-lex.europa.eu/legal-content/SV/ALL/?uri=celex%3A{celex}"
        
        return f"[{full_match}]({url})"

    def replace_eeg_reference(match):
        """Ersätter en EEG-referens med en markdown-länk till EUR-Lex"""
        full_match = match.group(0)
        year_part = match.group(1)
        number_part = match.group(2)
        
        # Convert 2-digit year to 4-digit (assumes 19XX for years >= 50, 20XX for < 50)
        if len(year_part) == 2:
            year_int = int(year_part)
            if year_int >= 50:
                year = f"19{year_part}"
            else:
                year = f"20{year_part}"
        else:
            year = year_part
        
        # Create CELEX number: 3YYYYLNNNNN (L for directive)
        celex = f"3{year}L{number_part.zfill(4)}"
        
        # Create EUR-Lex URL
        url = f"https://eur-lex.europa.eu/legal-content/SV/ALL/?uri=celex%3A{celex}"
        
        return f"[{full_match}]({url})"

    def replace_eg_reference(match):
        """Ersätter en EG-referens med en markdown-länk till EUR-Lex"""
        full_match = match.group(0)
        year_part = match.group(1)
        number_part = match.group(2)
        
        # Convert 2-digit year to 4-digit (assumes 19XX for years >= 50, 20XX for < 50)
        if len(year_part) == 2:
            year_int = int(year_part)
            if year_int >= 50:
                year = f"19{year_part}"
            else:
                year = f"20{year_part}"
        else:
            year = year_part
        
        # Create CELEX number: 3YYYYLNNNNN (L for directive)
        celex = f"3{year}L{number_part.zfill(4)}"
        
        # Create EUR-Lex URL
        url = f"https://eur-lex.europa.eu/legal-content/SV/ALL/?uri=celex%3A{celex}"
        
        return f"[{full_match}]({url})"

    # Apply all EU patterns
    text = re.sub(EU_REGULATION_PATTERN, replace_eu_reference, text)
    text = re.sub(EU_EEG_PATTERN, replace_eeg_reference, text)
    text = re.sub(EU_EG_PATTERN, replace_eg_reference, text)
    
    return text
