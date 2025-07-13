#!/usr/bin/env python3
"""
Funktion för att tillämpa temporal filtrering på SFS markdown-text.

Funktionen tar bort sektioner baserat på selex:status, selex:upphor_datum och selex:ikraft_datum
relativt till ett angivet target datum.

Regler:
1. Sektioner med selex:status="upphavd" eller "gammal upphord" tas bort helt
2. Sektioner med selex:status="ikraft" och selex:ikraft_datum > target_date tas bort helt
3. Sektioner med selex:status="ikraft" och selex:ikraft_datum <= target_date får sina temporal attribut borttagna
4. Sektioner med selex:upphor_datum som är <= target_date tas bort helt
5. Sektioner med selex:ikraft_datum som är > target_date tas bort helt
6. Nestlade sektioner hanteras korrekt - om en överordnad sektion tas bort, 
   tas alla underordnade sektioner också bort
"""

import re
from datetime import datetime
from typing import Optional
from temporal.title_temporal import title_temporal


def _process_h1_heading(lines: list, i: int, target_date: str, verbose: bool = False) -> tuple:
    """
    Process H1 heading with temporal rules.
    
    Args:
        lines: List of markdown lines
        i: Current line index (pointing to H1 line)
        target_date: Target date for temporal processing
        verbose: Enable verbose output
        
    Returns:
        Tuple of (processed_line, next_index, changes_applied)
    """
    line = lines[i]
    h1_content = line.strip()[2:].strip()  # Remove "# " from beginning
    
    # Check if there are more lines that belong to the same title (multiline)
    multiline_title = [h1_content]
    j = i + 1
    while j < len(lines) and not lines[j].strip().startswith('#') and not lines[j].strip().startswith('<'):
        if lines[j].strip():  # Add non-empty lines
            multiline_title.append(lines[j].strip())
        elif multiline_title:  # If we already have content, break at empty line
            break
        j += 1
    
    full_title = '\n'.join(multiline_title)
    
    # Apply temporal title rules
    processed_title = title_temporal(full_title, target_date)
    
    changes_applied = 0
    if processed_title != full_title:
        if verbose:
            print("Regel tillämpas: Bearbetar H1-rubrik med temporal regler")
            print(f"Original: {full_title}")
            print(f"Bearbetad: {processed_title}")
            print("-" * 80)
        changes_applied = 1
    
    # Replace H1 line with processed title
    processed_line = f"# {processed_title}"
    
    return processed_line, j, changes_applied


def apply_temporal(markdown_text: str, target_date: str, verbose: bool = False) -> str:
    """
    Tillämpar temporal filtrering på markdown-text baserat på selex-attribut.
    
    Tar bort sektioner som har upphävts, utgått eller ännu inte trätt ikraft på target_date.

    Args:
        markdown_text (str): Markdown-texten med section-taggar och selex-attribut
        target_date (str): Datum i format YYYY-MM-DD som ska jämföras mot
        verbose (bool): Om True, skriv ut information när regler tillämpas

    Returns:
        str: Den filtrerade markdown-texten med borttagna sektioner

    Raises:
        ValueError: Om target_date inte är i rätt format (YYYY-MM-DD)
    """
    # Validera target_date format
    try:
        target_datetime = datetime.strptime(target_date, '%Y-%m-%d')
    except ValueError as exc:
        raise ValueError(f"target_date måste vara i format YYYY-MM-DD, fick: {target_date}") from exc
    
    if verbose:
        print(f"Tillämpar temporal filtrering för datum: {target_date}")
    
    lines = markdown_text.split('\n')
    result = []
    i = 0
    changes_applied = 0
    sections_removed = 0
    attributes_cleaned = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Kolla om raden är en H1-rubrik som kan innehålla temporal regler
        if line.strip().startswith('# '):
            processed_line, next_i, h1_changes = _process_h1_heading(lines, i, target_date, verbose)
            result.append(processed_line)
            changes_applied += h1_changes
            i = next_i
            continue
        
        # Kolla om raden är en section- eller article-öppning
        section_match = re.match(r'<(section|article)(.*)>', line)
        if section_match:
            tag_type = section_match.group(1)
            attributes = section_match.group(2)
            
            # Extrahera datum-attribut och status-attribut
            upphor_match = re.search(r'selex:upphor_datum="(\d{4}-\d{2}-\d{2})"', attributes)
            ikraft_match = re.search(r'selex:ikraft_datum="(\d{4}-\d{2}-\d{2})"', attributes)
            status_match = re.search(r'selex:status="([^"]+)"', attributes)
            ikraft_villkor_match = re.search(r'selex:ikraft_villkor="([^"]+)"', attributes)
            upphor_villkor_match = re.search(r'selex:upphor_villkor="([^"]+)"', attributes)
            
            should_remove = False
            remove_reason = ""
            
            # Kontrollera status-attribut
            if status_match:
                status_value = status_match.group(1)
                if "upphavd" in status_value or "upphord" in status_value:
                    should_remove = True
                    remove_reason = f"status '{status_value}'"
                elif "ikraft" in status_value and ikraft_match:
                    # För status="ikraft" med ikraft_datum, använd datum-logiken
                    ikraft_date = ikraft_match.group(1)
                    ikraft_datetime = datetime.strptime(ikraft_date, '%Y-%m-%d')
                    if ikraft_datetime > target_datetime:
                        should_remove = True
                        remove_reason = f"status '{status_value}' med ikraft_datum {ikraft_date} > {target_date}"
            
            # Kontrollera upphor_datum - ta bort om <= target_date
            if upphor_match and not should_remove:
                upphor_date = upphor_match.group(1)
                upphor_datetime = datetime.strptime(upphor_date, '%Y-%m-%d')
                if upphor_datetime <= target_datetime:
                    should_remove = True
                    remove_reason = f"upphor_datum {upphor_date} <= {target_date}"
            
            # Kontrollera ikraft_datum - ta bort om > target_date  
            if ikraft_match and not should_remove:
                ikraft_date = ikraft_match.group(1)
                ikraft_datetime = datetime.strptime(ikraft_date, '%Y-%m-%d')
                if ikraft_datetime > target_datetime:
                    should_remove = True
                    remove_reason = f"ikraft_datum {ikraft_date} > {target_date}"
            
            if should_remove:
                # Hitta den matchande </section> taggen och skippa hela sektionen
                section_depth = 1
                i += 1  # Gå förbi öppningstaggen
                
                # Hitta rubriken för verbose output
                section_header = ""
                temp_i = i
                while temp_i < len(lines) and not section_header.strip():
                    if lines[temp_i].strip().startswith('#'):
                        section_header = lines[temp_i].strip()
                        break
                    temp_i += 1
                
                # Hitta slutet av sektionen/artikeln
                while i < len(lines) and section_depth > 0:
                    current_line = lines[i]
                    if current_line.strip().startswith('<section') or current_line.strip().startswith('<article'):
                        section_depth += 1
                    elif current_line.strip() == '</section>' or current_line.strip() == '</article>':
                        section_depth -= 1
                    i += 1
                
                changes_applied += 1
                sections_removed += 1
                
                if verbose:
                    print(f"Regel tillämpas: Tar bort sektion med {remove_reason}")
                    if section_header:
                        print(f"Rubrik: {section_header}")
                    print(f"Attribut: {attributes}")
                    print("-" * 80)
                
                # Fortsätt till nästa rad (i är redan rätt position efter while-loopen)
                continue
            else:
                # Behåll sektionen men kolla om vi ska ta bort temporal attribut
                should_clean_attributes = False
                clean_reason = ""
                
                # Om status="ikraft" och ikraft_datum <= target_date, ta bort temporal attribut
                if status_match and "ikraft" in status_match.group(1) and ikraft_match:
                    ikraft_date = ikraft_match.group(1)
                    ikraft_datetime = datetime.strptime(ikraft_date, '%Y-%m-%d')
                    if ikraft_datetime <= target_datetime:
                        should_clean_attributes = True
                        clean_reason = f"status 'ikraft' har trätt i kraft ({ikraft_date} <= {target_date})"
                
                # Om ikraft_datum <= target_date (utan status), ta bort temporal attribut
                if ikraft_match and not should_clean_attributes and not status_match:
                    ikraft_date = ikraft_match.group(1)
                    ikraft_datetime = datetime.strptime(ikraft_date, '%Y-%m-%d')
                    if ikraft_datetime <= target_datetime:
                        should_clean_attributes = True
                        clean_reason = f"ikraft_datum har trätt i kraft ({ikraft_date} <= {target_date})"
                
                # Om status="ikraft" med ikraft_villkor (utan specifikt datum), ta bort temporal attribut
                if status_match and "ikraft" in status_match.group(1) and ikraft_villkor_match and not ikraft_match and not should_clean_attributes:
                    should_clean_attributes = True
                    clean_reason = f"status 'ikraft' med villkor är conditional, rensar temporal attribut"
                
                if should_clean_attributes:
                    # Ta bort temporal attribut från section/article-taggen
                    cleaned_line = re.sub(r'\s*selex:status="[^"]*"', '', line)
                    cleaned_line = re.sub(r'\s*selex:ikraft_datum="[^"]*"', '', cleaned_line)
                    cleaned_line = re.sub(r'\s*selex:upphor_datum="[^"]*"', '', cleaned_line)
                    cleaned_line = re.sub(r'\s*selex:ikraft_villkor="[^"]*"', '', cleaned_line)
                    cleaned_line = re.sub(r'\s*selex:upphor_villkor="[^"]*"', '', cleaned_line)
                    # Rensa upp extra mellanslag
                    cleaned_line = re.sub(r'\s+>', '>', cleaned_line)
                    cleaned_line = re.sub(r'<section\s+>', '<section>', cleaned_line)
                    cleaned_line = re.sub(r'<article\s+>', '<article>', cleaned_line)
                    
                    result.append(cleaned_line)
                    changes_applied += 1
                    attributes_cleaned += 1
                    
                    if verbose:
                        print(f"Regel tillämpas: Rensar temporal attribut - {clean_reason}")
                        print(f"Original: {line}")
                        print(f"Rensad: {cleaned_line}")
                        print("-" * 80)
                else:
                    # Behåll raden som den är
                    result.append(line)
                
                i += 1
        else:
            # Vanlig rad, behåll den
            result.append(line)
            i += 1
    
    if verbose:
        print(f"Totalt antal tillämpade regler: {changes_applied}")
        print(f"Antal sektioner borttagna: {sections_removed}")
        print(f"Antal attribut rensade: {attributes_cleaned}")
    
    return '\n'.join(result)


def apply_temporal_to_file(file_path: str, target_date: str, output_path: Optional[str] = None, verbose: bool = False) -> None:
    """
    Tillämpar temporal filtrering på en markdown-fil.
    
    Args:
        file_path (str): Sökväg till markdown-filen som ska bearbetas
        target_date (str): Datum i format YYYY-MM-DD som ska jämföras mot
        output_path (Optional[str]): Sökväg för utdatafilen. Om None, skrivs resultatet tillbaka till samma fil
        verbose (bool): Om True, skriv ut information när regler tillämpas
        
    Raises:
        FileNotFoundError: Om filen inte finns
        ValueError: Om target_date inte är i rätt format
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Filen {file_path} finns inte") from exc
    
    # Tillämpa temporal filtrering
    filtered_content = apply_temporal(content, target_date, verbose)
    
    # Skriv resultatet
    output_file = output_path if output_path else file_path
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(filtered_content)
    
    if verbose:
        print(f"Temporal filtrering tillämpad och sparad till: {output_file}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Användning: python temporal/apply_temporal.py <markdown_fil> <target_date> [output_fil] [--verbose]")
        print("Exempel: python temporal/apply_temporal.py dokument.md 2024-06-01")
        print("Exempel: python temporal/apply_temporal.py dokument.md 2024-06-01 output.md --verbose")
        sys.exit(1)
    
    input_file = sys.argv[1]
    target_date_arg = sys.argv[2]
    output_file_arg = None
    verbose_arg = False
    
    # Hantera optional argument
    if len(sys.argv) > 3:
        for arg in sys.argv[3:]:
            if arg == "--verbose":
                verbose_arg = True
            elif not output_file_arg and not arg.startswith("-"):
                output_file_arg = arg
    
    try:
        apply_temporal_to_file(input_file, target_date_arg, output_file_arg, verbose_arg)
        print(f"Temporal filtrering slutförd för {input_file} med datum {target_date_arg}")
        if output_file_arg:
            print(f"Resultat sparat till: {output_file_arg}")
    except (FileNotFoundError, ValueError, IOError) as e:
        print(f"Fel: {e}", file=sys.stderr)
        sys.exit(1)
