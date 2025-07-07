#!/usr/bin/env python3
"""
Script för att lägga till pdf_url property i front matter för alla markdown-filer i en mapp.
"""

import re
import argparse
import datetime
import requests
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
from .sort_frontmatter import sort_frontmatter_properties


def check_pdf_exists(url: str) -> bool:
    """
    Kontrollerar om PDF-filen finns genom att göra en HEAD request.
    
    Args:
        url: URL till PDF-filen
        
    Returns:
        bool: True om filen finns, False annars
    """
    try:
        response = requests.head(url, timeout=10)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def generate_pdf_url(beteckning: str, utfardad_datum: str = None, check_exists: bool = True) -> str:
    """
    Genererar PDF URL baserat på beteckning och utfardad_datum.
    
    Args:
        beteckning: Dokument beteckning (format: YEAR:SEQNUMBER)
        utfardad_datum: Utfärdandedatum (ISO format: YYYY-MM-DD)
        check_exists: Om True, kontrollera att PDF:en faktiskt finns
        
    Returns:
        str: Genererad PDF URL eller None om URL inte kan genereras
    """

    # URL-konstanter
    OLD_DOMAIN = "https://rkrattsdb.gov.se"
    NEW_DOMAIN = "https://svenskforfattningssamling.se"
    
    try:
        # Konvertera till sträng om det är en integer
        if isinstance(beteckning, int):
            beteckning = str(beteckning)
        
        if ':' not in beteckning:
            print(f"Felaktig beteckning format: {beteckning}")
            return None
        
        year, seq_number = beteckning.split(':', 1)
        
        # Kontrollera om detta tillhör den gamla databasen (1998:306 till 2018:159)
        year_int = int(year)
        seq_int = int(seq_number)
        
        is_old_database = False
        if year_int == 1998 and seq_int >= 306:
            is_old_database = True
        elif 1999 <= year_int <= 2017:
            is_old_database = True
        elif year_int == 2018 and seq_int <= 159:
            is_old_database = True
        
        # Bygg URL:en baserat på vilken databas som ska användas
        if is_old_database:
            # Gamla databasen: https://rkrattsdb.gov.se/SFSdoc/{YY}/{YY}{SEQNUMBER}.pdf
            # YY ska vara de två sista siffrorna från året (t.ex. 98 för 1998) och SEQNUMBER ska vara 4 siffror (04d)
            year_2digits = str(year_int)[-2:]  # Ta de två sista siffrorna
            seq_padded = f"{seq_int:04d}"
            url = f"{OLD_DOMAIN}/SFSdoc/{year_2digits}/{year_2digits}{seq_padded}.pdf"
        else:
            # Nya databasen kräver utfardad_datum
            if not utfardad_datum:
                print(f"Saknar utfardad_datum för {beteckning}, hoppar över")
                return None

            # Hantera olika datumformat (ISO 8601 eller andra format)
            try:
                # Försök att parsa som ISO 8601 datum (YYYY-MM-DD)
                if isinstance(utfardad_datum, str):
                    if 'T' in utfardad_datum:
                        # Datum med tid: 2023-12-15T10:30:00
                        pub_date = datetime.datetime.fromisoformat(utfardad_datum.replace('Z', '+00:00'))
                    else:
                        # Endast datum: 2023-12-15
                        pub_date = datetime.datetime.strptime(utfardad_datum, '%Y-%m-%d')
                else:
                    # Om det redan är ett datetime-objekt
                    pub_date = utfardad_datum

                published_year = str(pub_date.year)
                published_month = f"{pub_date.month:02d}"  # Nollpaddat månadsnummer
                
            except (ValueError, TypeError):
                print(f"Kunde inte parsa utfardad_datum '{utfardad_datum}' för {beteckning}, hoppar över")
                return None
            
            # Nya databasen: https://svenskforfattningssamling.se/sites/default/files/sfs/{PUBLISHED_YEAR}-{PUBLISHED_MONTH}/SFS{YEAR}-{SEQNUMBER}.pdf
            url = f"{NEW_DOMAIN}/sites/default/files/sfs/{published_year}-{published_month}/SFS{year}-{seq_number}.pdf"
        
        # Kontrollera om PDF:en faktiskt finns (om aktiverat)
        if check_exists and not check_pdf_exists(url):
            database_type = "gamla databasen" if is_old_database else "nya databasen"
            print(f"VARNING: PDF:en finns inte på {url} ({database_type}) för {beteckning}")
            return None

        return url

    except (ValueError, TypeError) as e:
        print(f"Fel vid parsing av beteckning eller sekvens nummer: {e}")
        return None
    except Exception as e:
        print(f"Fel vid generering av PDF URL: {e}")
        return None



def extract_frontmatter(content: str) -> tuple[Optional[Dict[Any, Any]], str]:
    """
    Extraherar front matter från markdown-innehåll.
    
    Args:
        content: Markdown-filens innehåll
        
    Returns:
        tuple: (frontmatter_dict, remaining_content)
    """
    # Matcha YAML front matter mellan --- linjer
    frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n'
    match = re.match(frontmatter_pattern, content, re.DOTALL)
    
    if match:
        try:
            frontmatter_yaml = match.group(1)
            frontmatter = yaml.safe_load(frontmatter_yaml) or {}
            remaining_content = content[match.end():]
            return frontmatter, remaining_content
        except yaml.YAMLError as e:
            print(f"Fel vid parsing av YAML: {e}")
            return None, content
    else:
        # Ingen front matter hittades
        return {}, content


def create_frontmatter_content(frontmatter: Dict[Any, Any]) -> str:
    """
    Skapar front matter innehåll från dictionary.
    
    Args:
        frontmatter: Dictionary med front matter data
        
    Returns:
        str: Formaterat YAML front matter
    """
    if not frontmatter:
        return ""
    
    yaml_content = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
    frontmatter_text = f"---\n{yaml_content}---\n"

    # Sortera front matter properties
    try:
        sorted_frontmatter = sort_frontmatter_properties(frontmatter_text.rstrip() + '\n')
        return sorted_frontmatter + '\n'
    except ValueError as e:
        # If sorting fails, keep the original format
        print(f"Warning: Could not sort front matter: {e}")
        return frontmatter_text


def add_pdf_url_to_file(file_path: Path, force_update: bool = False, check_exists: bool = True) -> bool:
    """
    Lägger till pdf_url property i front matter för en specifik markdown-fil.
    
    Args:
        file_path: Sökväg till markdown-filen
        
    Returns:
        bool: True om filen uppdaterades, False annars
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extrahera front matter
        frontmatter, remaining_content = extract_frontmatter(content)
        
        if frontmatter is None:
            print(f"Kunde inte läsa front matter från {file_path}")
            return False
        
        # Generera PDF URL
        beteckning = frontmatter.get('beteckning', '')
        utfardad_datum = frontmatter.get('utfardad_datum', '')
        pdf_url = generate_pdf_url(beteckning, utfardad_datum, check_exists)
        
        # Om PDF URL inte kunde genereras (t.ex. PDF:en finns inte), hoppa över
        if pdf_url is None:
            print(f"Kunde inte generera giltig PDF URL för {file_path}, hoppar över")
            return False
        
        # Kontrollera om pdf_url redan finns och är samma
        existing_pdf_url = frontmatter.get('pdf_url')
        if existing_pdf_url == pdf_url and not force_update:
            print(f"pdf_url är redan uppdaterad i {file_path}, hoppar över")
            return False
        
        # Lägg till eller uppdatera pdf_url property
        action = "Uppdaterade" if 'pdf_url' in frontmatter else "Lade till"
        frontmatter['pdf_url'] = pdf_url
        
        # Skapa nytt innehåll
        new_frontmatter = create_frontmatter_content(frontmatter)
        new_content = new_frontmatter + remaining_content
        
        # Skriv tillbaka filen
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"{action} pdf_url i {file_path}")
        return True
        
    except (IOError, OSError, yaml.YAMLError) as e:
        print(f"Fel vid bearbetning av {file_path}: {e}")
        return False


def process_directory(directory: Path, recursive: bool = True, force_update: bool = False, check_exists: bool = True) -> int:
    """
    Bearbetar alla markdown-filer i en mapp.
    
    Args:
        directory: Sökväg till mappen som ska bearbetas
        recursive: Om sökandet ska vara rekursivt
        
    Returns:
        int: Antal filer som uppdaterades
    """
    if not directory.exists():
        print(f"Mappen {directory} finns inte")
        return 0
    
    if not directory.is_dir():
        print(f"{directory} är inte en mapp")
        return 0
    
    # Hitta alla markdown-filer
    pattern = "**/*.md" if recursive else "*.md"
    md_files = list(directory.glob(pattern))
    
    if not md_files:
        print(f"Inga markdown-filer hittades i {directory}")
        return 0
    
    print(f"Hittade {len(md_files)} markdown-filer")
    
    updated_count = 0
    for md_file in md_files:
        if add_pdf_url_to_file(md_file, force_update, check_exists):
            updated_count += 1
    
    return updated_count


def main():
    """Huvudfunktion för scriptet."""
    parser = argparse.ArgumentParser(
        description="Lägg till pdf_url property i front matter för markdown-filer"
    )
    parser.add_argument(
        "directory",
        help="Mapp som innehåller markdown-filerna som ska uppdateras"
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Sök inte rekursivt i undermappar"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Uppdatera pdf_url även om den redan existerar"
    )
    parser.add_argument(
        "--no-check",
        action="store_true",
        help="Hoppa över kontroll om PDF:en faktiskt finns online"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Visa vad som skulle göras utan att faktiskt uppdatera filer"
    )
    
    args = parser.parse_args()
    
    directory = Path(args.directory)
    recursive = not args.no_recursive
    force_update = args.force
    check_exists = not args.no_check
    
    if args.dry_run:
        print("DRY RUN - inga filer kommer att uppdateras")
        # För dry run, visa bara vilka filer som skulle bearbetas
        pattern = "**/*.md" if recursive else "*.md"
        md_files = list(directory.glob(pattern))
        print(f"Skulle bearbeta {len(md_files)} filer:")
        for md_file in md_files:
            print(f"  - {md_file}")
        return
    
    print(f"Bearbetar markdown-filer i: {directory}")
    print(f"Rekursivt: {'Ja' if recursive else 'Nej'}")
    print(f"Tvinga uppdatering: {'Ja' if force_update else 'Nej'}")
    print(f"Kontrollera PDF existens: {'Ja' if check_exists else 'Nej'}")
    
    updated_count = process_directory(directory, recursive, force_update, check_exists)
    
    print(f"\nKlart! Uppdaterade {updated_count} filer.")


if __name__ == "__main__":
    main()
