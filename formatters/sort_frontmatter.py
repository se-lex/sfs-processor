#!/usr/bin/env python3
"""
Modul för att sortera properties i YAML front matter.

Denna modul innehåller funktioner för att sortera front matter properties
enligt en specificerad ordning för SFS-dokument.
"""

import re
import warnings
from typing import Dict


def sort_amendments_list(amendment_lines: list) -> str:
    """
    Sorterar innehållet i en andringsforfattningar-lista.

    Args:
        amendment_lines: Lista med rader som representerar andringsforfattningar

    Returns:
        str: Sorterad YAML-representation av andringsforfattningar
    """
    AMENDMENT_ORDER = ['beteckning', 'rubrik', 'ikraft_datum', 'anteckningar']

    # Hantera det felaktiga formatet där första raden börjar direkt efter kolon
    processed_lines = []
    for i, line in enumerate(amendment_lines):
        if i == 0 and line.strip().startswith('-'):
            # Första raden börjar direkt efter kolon, lägg till med korrekt indentation
            processed_lines.append('  ' + line.strip())
        else:
            processed_lines.append(line)

    # Parsa amendment items
    amendments = []
    current_amendment = {}

    for line in processed_lines:
        stripped = line.strip()

        # Ny amendment item (börjar med -)
        if stripped.startswith('-'):
            # Spara föregående amendment om den finns
            if current_amendment:
                amendments.append(current_amendment)

            # Starta ny amendment
            current_amendment = {}

            # Kolla om det finns data på samma rad som -
            if ':' in stripped:
                parts = stripped[1:].split(':', 1)  # Ta bort - först
                key = parts[0].strip()
                value = parts[1].strip() if len(parts) > 1 else ''
                current_amendment[key] = value

        # Property inom amendment item
        elif ':' in line and (line.startswith('    ') or line.startswith('  ')):
            parts = line.strip().split(':', 1)
            key = parts[0].strip()
            value = parts[1].strip() if len(parts) > 1 else ''
            if key:
                current_amendment[key] = value

    # Spara sista amendment
    if current_amendment:
        amendments.append(current_amendment)

    # Bygg sorterad YAML med korrekt indentation
    if not amendments:
        return ''

    result_lines = []
    for i, amendment in enumerate(amendments):
        # Lägg till första property med - prefix
        first_prop = True
        for prop in AMENDMENT_ORDER:
            if prop in amendment:
                value = amendment[prop]
                # Lägg till citattecken runt värden som innehåller kolon eller speciella tecken
                if ':' in value or value.startswith('"') or '"' in value:
                    if not (value.startswith('"') and value.endswith('"')):
                        value = f'"{value}"'

                if first_prop:
                    result_lines.append(f"  - {prop}: {value}")
                    first_prop = False
                else:
                    result_lines.append(f"    {prop}: {value}")

        # Lägg till okända properties sist
        unknown_props = [k for k in amendment.keys() if k not in AMENDMENT_ORDER]
        for prop in unknown_props:
            value = amendment[prop]
            # Lägg till citattecken runt värden som innehåller kolon eller speciella tecken
            if ':' in value or value.startswith('"') or '"' in value:
                if not (value.startswith('"') and value.endswith('"')):
                    value = f'"{value}"'

            if first_prop:
                result_lines.append(f"  - {prop}: {value}")
                first_prop = False
            else:
                result_lines.append(f"    {prop}: {value}")

    return '\n' + '\n'.join(result_lines)


def sort_frontmatter_properties(frontmatter_content: str) -> str:
    """
    Sorterar properties i YAML front matter enligt specificerad ordning.

    Args:
        frontmatter_content: Innehållet i front matter (inklusive --- markörer)

    Returns:
        str: Front matter med sorterade properties

    Raises:
        ValueError: Om front matter inte har korrekt format
    """
    # Definiera den önskade ordningen för properties
    PROPERTY_ORDER = [
        'beteckning',
        'rubrik',
        'departement',
        'utfardad_datum',
        'ikraft_datum',
        'publicerad_datum',
        'utgar_datum',
        'forarbeten',
        'celex',
        'eu_direktiv',
        'pdf_url',
        'andringsforfattningar'
    ]

    # Extrahera front matter innehåll
    # Försök först med front matter + innehåll, sedan bara front matter
    match = re.match(r'^---\s*\n([\s\S]*?)\n---\s*(?:\n[\s\S]*)?$', frontmatter_content, re.DOTALL)
    if not match:
        # Försök med bara front matter block
        match = re.match(r'^---\s*\n([\s\S]*?)\n---\s*$', frontmatter_content, re.DOTALL)
    if not match:
        raise ValueError("Ogiltigt front matter format. Måste börja och sluta med ---")

    yaml_content = match.group(1)

    # Parsa YAML-liknande innehåll manuellt (förbättrad implementation)
    properties = {}
    unknown_properties = []

    # Dela upp i rader och bearbeta
    lines = yaml_content.split('\n')
    current_property = None
    current_value = []
    in_list = False

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped_line = line.strip()

        # Hoppa över tomma rader
        if not stripped_line:
            i += 1
            continue

        # Kontrollera om det är en ny property (inte indenterad eller med kolon)
        if ':' in line and not line.startswith(' ') and not line.startswith('\t'):
            # Spara föregående property om den finns
            if current_property:
                if current_property == 'andringsforfattningar' and current_value:
                    # Speciell hantering för andringsforfattningar - sortera dess innehåll
                    sorted_amendments = sort_amendments_list(current_value)
                    properties[current_property] = sorted_amendments
                elif in_list and current_value:
                    # Behandla som YAML-lista
                    properties[current_property] = '\n'.join(current_value)
                else:
                    properties[current_property] = '\n'.join(current_value).strip()

            # Starta ny property
            parts = line.split(':', 1)
            current_property = parts[0].strip()
            current_value = []
            in_list = False

            # Kontrollera om det är en känd property
            if current_property not in PROPERTY_ORDER:
                unknown_properties.append(current_property)

            # Om värdet finns på samma rad
            if len(parts) > 1 and parts[1].strip():
                value_on_same_line = parts[1].strip()
                # Specialhantering för andringsforfattningar som har felaktigt format
                if current_property == 'andringsforfattningar' and value_on_same_line.startswith(
                        '-'):
                    # Detta är en felformaterad YAML-lista som börjar på samma rad
                    current_value.append(value_on_same_line)
                    in_list = True
                else:
                    current_value.append(value_on_same_line)
                    in_list = False
            # Kontrollera om nästa rad är en lista
            elif i + 1 < len(lines):
                next_line = lines[i + 1]
                if next_line.strip().startswith('-') or (current_property ==
                                                         'andringsforfattningar' and next_line.startswith(' ')):
                    in_list = True
                elif next_line.startswith('  ') or next_line.startswith('\t'):
                    # Multi-line värde (inte lista)
                    in_list = False
                else:
                    # Enkelt värde på samma rad (utan värde efter kolon)
                    current_value.append('')
                    in_list = False

        # Hantera indenterade rader (listor eller multi-line värden)
        elif (line.startswith('  ') or line.startswith('\t') or line.startswith('-')) and current_property:
            current_value.append(line)

        i += 1

    # Spara sista property
    if current_property:
        if current_property == 'andringsforfattningar' and current_value:
            # Speciell hantering för andringsforfattningar
            sorted_amendments = sort_amendments_list(current_value)
            properties[current_property] = sorted_amendments
        elif in_list and current_value:
            properties[current_property] = '\n'.join(current_value)
        else:
            properties[current_property] = '\n'.join(current_value).strip()

    # Varna för okända properties
    if unknown_properties:
        warnings.warn(f"Okända properties hittades i front matter: {', '.join(unknown_properties)}")

    # Bygg upp sorterat front matter
    sorted_content = ["---"]

    # Lägg till properties i specificerad ordning
    for prop in PROPERTY_ORDER:
        if prop in properties:
            value = properties[prop]
            if value:
                if prop == 'andringsforfattningar':
                    # Specialhantering för andringsforfattningar
                    sorted_content.append(f"{prop}:{value}")
                elif prop == 'forarbeten' and value.startswith('\n'):
                    # Specialhantering för förarbeten som lista
                    sorted_content.append(f"{prop}:{value}")
                else:
                    sorted_content.append(f"{prop}: {value}")
            else:
                sorted_content.append(f"{prop}:")

    # Lägg till okända properties sist
    for prop in unknown_properties:
        if prop in properties:
            value = properties[prop]
            if value:
                sorted_content.append(f"{prop}: {value}")
            else:
                sorted_content.append(f"{prop}:")

    sorted_content.append("---")

    return '\n'.join(sorted_content)


def sort_frontmatter_in_file(filepath: str, backup: bool = True) -> bool:
    """
    Sorterar front matter properties i en markdown-fil.

    Args:
        filepath: Sökväg till markdown-filen
        backup: Om True, skapar en backup av originalfilen (.bak)

    Returns:
        bool: True om sortering lyckades, False annars
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Hitta front matter
        match = re.match(r'^(---\s*\n[\s\S]*?\n---)\s*\n(.*)$', content, re.DOTALL)
        if not match:
            warnings.warn(f"Ingen front matter hittades i {filepath}")
            return False

        frontmatter = match.group(1)
        body = match.group(2)

        # Sortera front matter
        sorted_frontmatter = sort_frontmatter_properties(frontmatter)

        # Skapa backup om önskat
        if backup:
            backup_path = filepath + '.bak'
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)

        # Skriv tillbaka med sorterat front matter
        new_content = sorted_frontmatter + '\n\n' + body
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return True

    except (IOError, OSError, ValueError) as e:
        warnings.warn(f"Fel vid sortering av {filepath}: {str(e)}")
        return False


def sort_frontmatter_in_directory(
        directory_path: str, pattern: str = "*.md", backup: bool = True) -> Dict[str, bool]:
    """
    Sorterar front matter properties i alla markdown-filer i en katalog.

    Args:
        directory_path: Sökväg till katalogen
        pattern: Filnamns-pattern för att filtrera filer (standard: "*.md")
        backup: Om True, skapar backup av originalfilerna (.bak)

    Returns:
        Dict[str, bool]: Dictionary med filnamn som nycklar och resultat (True/False) som värden
    """
    from pathlib import Path as PathLib

    directory = PathLib(directory_path)
    if not directory.exists() or not directory.is_dir():
        raise ValueError(f"Katalogen {directory_path} finns inte eller är inte en katalog")

    file_results = {}

    for md_file in directory.rglob(pattern):
        if md_file.is_file():
            result = sort_frontmatter_in_file(str(md_file), backup)
            file_results[str(md_file)] = result

    return file_results


if __name__ == "__main__":
    # Exempel på användning
    import argparse

    parser = argparse.ArgumentParser(description="Sortera front matter properties i markdown-filer")
    parser.add_argument("input", help="Fil eller katalog att bearbeta")
    parser.add_argument("--no-backup", action="store_true", help="Skapa inte backup-filer")
    parser.add_argument("--pattern", default="*.md", help="Filnamns-pattern för katalogbearbetning")

    args = parser.parse_args()

    from pathlib import Path
    input_path = Path(args.input)

    if input_path.is_file():
        # Bearbeta en enda fil
        success = sort_frontmatter_in_file(str(input_path), backup=not args.no_backup)
        if success:
            print(f"Front matter sorterat i {input_path}")
        else:
            print(f"Kunde inte sortera front matter i {input_path}")

    elif input_path.is_dir():
        # Bearbeta alla filer i katalogen
        results = sort_frontmatter_in_directory(
            str(input_path), args.pattern, backup=not args.no_backup)

        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)

        print(f"Bearbetade {total_count} filer, {success_count} lyckades")

        # Visa filer som misslyckades
        failed_files = [path for path, success in results.items() if not success]
        if failed_files:
            print("\nFiler som misslyckades:")
            for file_item in failed_files:
                print(f"  - {file_item}")

    else:
        print(f"Fel: {args.input} är varken en fil eller katalog")
