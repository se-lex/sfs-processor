#!/usr/bin/env python3
"""
Script för att hämta SFS-författningar som uppdaterats efter ett visst datum från Regeringskansliets API
och spara dem som JSON-filer.

Använder Regeringskansliets Elasticsearch API för att hämta författningar som uppdaterats efter
ett specificerat datum och sparar dem som JSON-filer som sedan kan bearbetas med sfs_processor.py.
"""

import requests
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Any
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


def save_document_as_json(document: Dict[str, Any], output_dir: Path) -> bool:
    """
    Sparar ett författningsdokument som JSON-fil.

    Args:
        document (Dict[str, Any]): Författningsdata från API:et
        output_dir (Path): Katalog att spara filen i

    Returns:
        bool: True om sparningen lyckades, False annars

    Raises:
        ValueError: Om beteckning saknas eller är tom
    """
    try:
        # Skapa filnamn baserat på beteckning
        beteckning = document.get('beteckning')
        if not beteckning:
            raise ValueError("Beteckning saknas eller är tom i dokumentet")

        # Konvertera beteckning till filnamn (t.ex. "2024:123" -> "sfs-2024-123.json")
        safe_filename = "sfs-" + re.sub(r'[^\w\-]', '-', beteckning) + '.json'
        output_file = output_dir / safe_filename

        # Kontrollera om filen redan finns
        if output_file.exists():
            print(f"⚠ {output_file.name} finns redan, skriver över")

        # Skriv JSON-filen
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(document, f, ensure_ascii=False, indent=2)

        print(f"✓ Sparade {beteckning} -> {output_file}")
        return True

    except ValueError as e:
        print(f"✗ Fel vid sparning av författning: {e}")
        return False
    except (IOError, KeyError) as e:
        beteckning = document.get('beteckning', 'okänt dokument')
        print(f"✗ Fel vid sparning av författning {beteckning}: {e}")
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
    Huvudfunktion som koordinerar hämtning av författningar och sparning som JSON.
    """
    parser = argparse.ArgumentParser(
        description='Hämta SFS-författningar uppdaterade efter ett visst datum och spara som JSON-filer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exempel:
  %(prog)s --date 2024-01-01
  %(prog)s --date "2024-12-01T10:00:00" --output /path/to/json
  %(prog)s --days 7

Efter att JSON-filerna sparats kan de bearbetas med sfs_processor.py:
  python sfs_processor.py --input /path/to/json --output /path/to/markdown
        """)

    # Datum-alternativ (antingen --date eller --days)
    date_group = parser.add_mutually_exclusive_group(required=True)
    date_group.add_argument(
        '--date',
        help='Hämta författningar uppdaterade efter detta datum (YYYY-MM-DD eller YYYY-MM-DDTHH:MM:SS)')
    date_group.add_argument('--days', type=int,
                            help='Hämta författningar uppdaterade de senaste X dagarna')

    parser.add_argument('--output', '-o', default='sfs_json',
                        help='Mapp att spara JSON-filer i (default: sfs_json)')
    # Remove year folder option since we're saving JSON files directly

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
        print(
            f"Hämtar författningar uppdaterade de senaste {args.days} dagarna (efter {search_date})")

    # Skapa output-katalog tidigt så den finns även om inga dokument hittas
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)

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

    print(f"Sparar JSON-filer till: {output_dir.absolute()}")

    # Konvertera och spara varje författning som JSON
    successful_saves = 0
    failed_saves = 0
    skipped_n = 0

    for i, document in enumerate(documents, 1):
        beteckning = document.get('beteckning')
        if not beteckning:
            print(f"\n[{i}/{len(documents)}] ⚠ Hoppar över dokument {i} - saknar beteckning")
            failed_saves += 1
            continue

        # Skip documents with beteckning starting with 'N' (myndighetsföreskrifter)
        if beteckning.startswith('N'):
            print(
                f"\n[{i}/{len(documents)}] ⚠ Hoppar över {beteckning} - myndighetsföreskrift (N-beteckning)")
            skipped_n += 1
            continue

        print(f"\n[{i}/{len(documents)}] Bearbetar {beteckning}...")

        if save_document_as_json(document, output_dir):
            successful_saves += 1
        else:
            failed_saves += 1

    # Sammanfattning
    print("\n=== Sammanfattning ===")
    print(f"Totalt författningar: {len(documents)}")
    print(f"Överhoppade N-beteckningar: {skipped_n}")
    print(f"Lyckade sparningar: {successful_saves}")
    print(f"Misslyckade sparningar: {failed_saves}")

    if successful_saves > 0:
        print(f"JSON-filer sparade i: {output_dir.absolute()}")
        print("\nFör att konvertera JSON-filerna till Markdown, kör:")
        print(f"python sfs_processor.py --input {output_dir} --output markdown")


if __name__ == "__main__":
    main()
