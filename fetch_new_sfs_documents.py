#!/usr/bin/env python3
"""
Script för att hämta SFS-författningar som uppdaterats efter ett visst datum från Regeringskansliets API
och konvertera dem direkt till Markdown-format.

Använder Regeringskansliets Elasticsearch API för att hämta författningar som uppdaterats efter
ett specificerat datum och konverterar dem automatiskt till Markdown med YAML front matter.
"""

import requests
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Any
from convert_json_to_markdown import create_markdown_content
import re


def _post(payload_dict: Dict[str, Any]) -> Optional[Dict]:
    """
    Gör en POST-förfrågan till Regeringskansliets Elasticsearch API.
    
    Args:
        payload_dict (Dict[str, Any]): Payload för API-anropet
        
    Returns:
        Optional[Dict]: API-svar eller None vid fel
    """
    url = "https://beta.rkrattsbaser.gov.se/elasticsearch/SearchEsByRawJson"
    
    headers = {
        'content-type': 'application/json'
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload_dict, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"✗ Fel vid API-anrop: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"✗ Fel vid parsing av API-svar: {e}")
        return None


def get_newer_items(date: str) -> Optional[Dict]:
    """
    Hämtar SFS-författningar som uppdaterats efter ett specificerat datum.

    Args:
        date (str): Datum i ISO-format (YYYY-MM-DD eller YYYY-MM-DDTHH:MM:SS)
        
    Returns:
        Optional[Dict]: API-svar med författningar eller None vid fel
    """
    payload_dict = {
        "searchIndexes": ["Sfs"],
        "api": "search",
        "json": {
            "sort": [{"beteckningSortable.sort": {"order": "asc"}}],
            "query": {
                "bool": {
                    "must": [
                        {"range": {"uppdateradDateTime": {"gt": date}}},
                        {"term": {"publicerad": True}},
                    ]
                }
            },
            "size": 10000,
            "from": 0,
        },
    }

    return _post(payload_dict)


def save_document_as_markdown(document: Dict[str, Any], output_dir: Path, year_as_folder: bool = True) -> bool:
    """
    Konverterar ett författning till Markdown och sparar det.

    Args:
        document (Dict[str, Any]): Författningsdata från API:et
        output_dir (Path): Katalog att spara filen i
        year_as_folder (bool): Om True, skapa årsmappar
        
    Returns:
        bool: True om sparningen lyckades, False annars
    """
    try:
        # Konvertera dokumentet till Markdown
        markdown_content = create_markdown_content(document)
        
        # Skapa filnamn baserat på beteckning
        beteckning = document.get('beteckning', 'unknown')
        
        # Extrahera år från beteckning (format är typiskt YYYY:NNN)
        year_match = re.search(r'(\d{4}):', beteckning)
        if not year_match:
            print(f"⚠ Kunde inte extrahera år från beteckning: {beteckning}")
            year = 'unknown'
        else:
            year = year_match.group(1)

        if year_as_folder and year != 'unknown':
            # Skapa en undermapp för varje år
            document_dir = output_dir / year
            document_dir.mkdir(exist_ok=True)
        else:
            document_dir = output_dir

        safe_filename = "sfs-" + re.sub(r'[^\w\-]', '-', beteckning) + '.md'
        output_file = document_dir / safe_filename
        
        # Kontrollera om filen redan finns
        if output_file.exists():
            print(f"⚠ {output_file.name} finns redan, skriver över")
        
        # Skriv Markdown-filen
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"✓ Sparade {beteckning} -> {output_file}")
        return True
        
    except (IOError, ValueError, KeyError) as e:
        print(f"✗ Fel vid sparning av författning {document.get('beteckning', 'unknown')}: {e}")
        return False


def parse_date(date_str: str) -> str:
    """
    Parsar och validerar ett datumformat.
    
    Args:
        date_str (str): Datum som sträng
        
    Returns:
        str: Validerat datum i ISO-format
        
    Raises:
        ValueError: Om datumet inte kan parsas
    """
    # Försök parsa olika datumformat
    formats = [
        '%Y-%m-%d',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M:%S'
    ]
    
    for fmt in formats:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            return parsed_date.isoformat()
        except ValueError:
            continue
    
    raise ValueError(f"Kunde inte parsa datum: {date_str}")


def main():
    """
    Huvudfunktion som koordinerar hämtning och konvertering av författning.
    """
    parser = argparse.ArgumentParser(
        description='Hämta SFS-författning uppdaterade efter ett visst datum och konvertera till Markdown',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exempel:
  %(prog)s --date 2024-01-01
  %(prog)s --date "2024-12-01T10:00:00" --output /path/to/markdown
  %(prog)s --days 7 --no-year-folder
        """
    )
    
    # Datum-alternativ (antingen --date eller --days)
    date_group = parser.add_mutually_exclusive_group(required=True)
    date_group.add_argument('--date', 
                           help='Hämta författningar uppdaterade efter detta datum (YYYY-MM-DD eller YYYY-MM-DDTHH:MM:SS)')
    date_group.add_argument('--days', type=int,
                           help='Hämta författningar uppdaterade de senaste X dagarna')

    parser.add_argument('--output', '-o', default='markdown',
                        help='Mapp att spara Markdown-filer i (default: markdown)')
    parser.add_argument('--no-year-folder', dest='year_folder', action='store_false',
                        help='Skapa inte årsmappar för författningar')
    parser.set_defaults(year_folder=True)
    
    args = parser.parse_args()

    print("=== Dokumenthämtare (nya/uppdaterade) ===")
    
    # Bestäm datum att söka från
    if args.date:
        try:
            search_date = parse_date(args.date)
            print(f"Hämtar författningar uppdaterade efter: {search_date}")
        except ValueError as e:
            print(f"✗ {e}")
            return
    else:  # args.days
        cutoff_date = datetime.now() - timedelta(days=args.days)
        search_date = cutoff_date.isoformat()
        print(f"Hämtar författningar uppdaterade de senaste {args.days} dagarna (efter {search_date})")

    # Hämta författningar från API:et
    print("\nSöker efter författningar i Regeringskansliets databas...")
    api_response = get_newer_items(search_date)
    
    if not api_response:
        print("✗ Kunde inte hämta data från API:et")
        return

    # Extrahera författningar från API-svaret
    try:
        hits = api_response.get('hits', {}).get('hits', [])
        documents = [hit['_source'] for hit in hits]

        print(f"✓ Hittade {len(documents)} författningar uppdaterade efter {search_date}")
        
        if not documents:
            print("Inga nya författningar hittades för det angivna datumet.")
            return
            
    except (KeyError, TypeError) as e:
        print(f"✗ Fel vid parsing av API-svar: {e}")
        return
    
    # Skapa output-katalog
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)
    print(f"Sparar författningar till: {output_dir.absolute()}")

    # Konvertera och spara varje författning
    successful_conversions = 0
    failed_conversions = 0
    
    for i, document in enumerate(documents, 1):
        beteckning = document.get('beteckning', f'dokument-{i}')
        print(f"\n[{i}/{len(documents)}] Bearbetar {beteckning}...")
        
        if save_document_as_markdown(document, output_dir, args.year_folder):
            successful_conversions += 1
        else:
            failed_conversions += 1
    
    # Sammanfattning
    print("\n=== Sammanfattning ===")
    print(f"Totalt författningar: {len(documents)}")
    print(f"Lyckade konverteringar: {successful_conversions}")
    print(f"Misslyckade konverteringar: {failed_conversions}")
    
    if successful_conversions > 0:
        print(f"Markdown-filer sparade i: {output_dir.absolute()}")


if __name__ == "__main__":
    main()
