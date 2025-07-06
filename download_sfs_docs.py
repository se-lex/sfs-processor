#!/usr/bin/env python3
"""
Script för att ladda ner SFS-författningar från Riksdagens öppna data.
Hämtar först en lista med författnings-ID:n och laddar sedan ner textinnehållet för varje författning.
"""

import requests
import os
import time
import argparse
import json
from typing import List, Optional, Dict


def fetch_document_ids(year: Optional[int] = None) -> List[str]:
    """
    Hämtar författnings-ID:n från Riksdagens dokumentlista.
    
    Args:
        year (Optional[int]): Filtrera författningar för specifikt årtal (t.ex. 2025 för sfs-2025-xxx)

    Returns:
        List[str]: Lista med författnings-ID:n
    """
    url = "https://data.riksdagen.se/dokumentlista/?sok=&doktyp=SFS&utformat=iddump&a=s#soktraff"
    
    print(f"Hämtar författnings-ID:n från: {url}")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Parsa kommaseparerade värden och trimma mellanslag
        content = response.text.strip()
        document_ids = [doc_id.strip() for doc_id in content.split(',') if doc_id.strip()]
        
        # Filtrera baserat på årtal om specificerat
        if year is not None:
            original_count = len(document_ids)
            document_ids = [doc_id for doc_id in document_ids if doc_id.startswith(f"sfs-{year}-")]
            print(f"Filtrerade för år {year}: {len(document_ids)} av {original_count} författningar")

        print(f"Hittade {len(document_ids)} författnings-ID:n")
        return document_ids
        
    except requests.RequestException as e:
        print(f"Fel vid hämtning av författnings-ID:n: {e}")
        return []


def download_document(document_id: str, output_dir: str = "documents") -> bool:
    """
    Laddar ner textinnehållet för en specifik författning.
    
    Args:
        document_id (str): Författnings-ID att ladda ner
        output_dir (str): Katalog att spara filen i
        
    Returns:
        bool: True om nedladdningen lyckades, False annars
    """
    url = f"https://data.riksdagen.se/dokument/{document_id}.html"
    filename = f"{document_id}.html"
    filepath = os.path.join(output_dir, filename)
    
    # Kontrollera om filen redan finns
    if os.path.exists(filepath):
        print(f"⚠ {filename} finns redan, hoppar över")
        return True

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Skapa katalog om den inte finns
        os.makedirs(output_dir, exist_ok=True)
        
        # Spara textinnehållet till fil
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        print(f"✓ Sparade {filename}")
        return True
        
    except requests.RequestException as e:
        print(f"✗ Fel vid hämtning av {document_id}: {e}")
        return False
    except IOError as e:
        print(f"✗ Fel vid sparning av {filename}: {e}")
        return False


def fetch_document_by_rkrattsbaser(doc_id: str) -> Optional[Dict]:
    """
    Hämtar en SFS-författning via Regeringskansliets Elasticsearch API baserat på författnings-ID.

    Args:
        doc_id (str): Författnings-ID i Regeringskansliets format som "2009:907"

    Returns:
        Optional[Dict]: Författningsdata om den hittas, None annars
    """
    url = "https://beta.rkrattsbaser.gov.se/elasticsearch/SearchEsByRawJson"

    headers = {
        'content-type': 'application/json',
        'referer': f'https://beta.rkrattsbaser.gov.se/sfs/item?bet={doc_id.replace(":", "%3A")}&tab=forfattningstext'
    }

    payload = {
        "searchIndexes": ["Sfs"],
        "api": "search",
        "json": {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"beteckning.keyword": doc_id}},
                        {"term": {"publicerad": True}}
                    ]
                }
            },
            "size": 1
        }
    }

    print(f"Hämtar dokument {doc_id} via Regeringskansliets Elasticsearch API...")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        data = response.json()

        # Kontrollera om vi fick några träffar
        if 'hits' in data and 'hits' in data['hits'] and len(data['hits']['hits']) > 0:
            document = data['hits']['hits'][0]['_source']
            print(f"✓ Hittade dokument: {doc_id}")
            return document
        else:
            print(f"⚠ Inget dokument hittades för ID: {doc_id}")
            return None

    except requests.RequestException as e:
        print(f"✗ Fel vid hämtning av dokument {doc_id} via Elasticsearch: {e}")
        return None
    except (KeyError, json.JSONDecodeError) as e:
        print(f"✗ Fel vid parsing av svar för dokument {doc_id}: {e}")
        return None


def save_document_from_rkrattsbaser(doc_id: str, document_data: Dict, output_dir: str = "rkrattsbaser") -> bool:
    """
    Sparar dokumentdata från Regeringskansliets API till fil.

    Args:
        doc_id (str): Dokument-ID
        document_data (Dict): Dokumentdata från API:et
        output_dir (str): Katalog att spara filen i

    Returns:
        bool: True om sparningen lyckades, False annars
    """
    filename = f"{doc_id}.json"
    filepath = os.path.join(output_dir, filename)

    # Kontrollera om filen redan finns
    if os.path.exists(filepath):
        print(f"⚠ {filename} finns redan, hoppar över")
        return True

    try:
        # Skapa katalog om den inte finns
        os.makedirs(output_dir, exist_ok=True)

        # Spara JSON-data till fil
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(document_data, f, ensure_ascii=False, indent=2)

        print(f"✓ Sparade {filename}")
        return True

    except IOError as e:
        print(f"✗ Fel vid sparning av {filename}: {e}")
        return False


def convert_riksdagen_id_to_rkrattsbaser_format(doc_id: str) -> str:
    """
    Konverterar dokument-ID från Riksdagens format (sfs-2009-907) till Regeringskansliets format (2009:907).

    Args:
        doc_id (str): Dokument-ID i Riksdagens format (t.ex. "sfs-2009-907")

    Returns:
        str: Dokument-ID i Regeringskansliets format (t.ex. "2009:907")
    """
    # Ta bort "sfs-" prefix och ersätt första bindestreck med kolon
    if doc_id.startswith("sfs-"):
        # Dela upp efter "sfs-", ta bort första delen och ersätt första bindestreck med kolon
        parts = doc_id[4:]  # Ta bort "sfs-"
        # Hitta första bindestreck och ersätt med kolon
        first_dash = parts.find("-")
        if first_dash != -1:
            return parts[:first_dash] + ":" + parts[first_dash + 1:]

    # Om formatet inte matchar förvåntat format, returnera som det är
    return doc_id


def download_test_docs():
    """
    Laddar ner testdokument som specificeras i data/test-doc-ids.json.
    Dokumenten sparas i katalogen data/testdocs.
    """
    test_docs_file = "data/test-doc-ids.json"
    output_dir = "data/testdocs"
    
    print("=== Laddar ner testdokument ===")
    
    # Kontrollera att filen med test-dokument-ID:n finns
    if not os.path.exists(test_docs_file):
        print(f"✗ Filen {test_docs_file} hittades inte.")
        return False
    
    try:
        # Läs test-dokument-ID:n från JSON-filen (med kommentarstöd)
        with open(test_docs_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Enkel lösning: ta bort kommentarer med regex
        import re
        # Ta bort /* */ kommentarer
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        # Ta bort // kommentarer (endast från början av rad eller efter whitespace)
        content = re.sub(r'^\s*//.*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'\s+//.*$', '', content, flags=re.MULTILINE)
        
        test_docs = json.loads(content)
        
        if not test_docs:
            print("Inga testdokument att ladda ner.")
            return True
        
        print(f"Hittade {len(test_docs)} testdokument att ladda ner")
        print(f"Sparar i katalog: {output_dir}")
        
        # Skapa katalog om den inte finns
        os.makedirs(output_dir, exist_ok=True)
        
        successful_downloads = 0
        failed_downloads = 0
        
        # Ladda ner varje testdokument
        for i, doc_info in enumerate(test_docs, 1):
            document_id = doc_info.get("document_id")
            comment = doc_info.get("comment", "")
            
            if not document_id:
                print(f"⚠ Dokument {i} saknar document_id, hoppar över")
                failed_downloads += 1
                continue
            
            print(f"[{i}/{len(test_docs)}] {document_id}")
            if comment:
                print(f"    Kommentar: {comment}")

            # Konvertera dokument-ID till rätt format för Regeringskansliet
            converted_id = convert_riksdagen_id_to_rkrattsbaser_format(document_id)
            
            # Ladda ner dokumentet från Regeringskansliet
            document_data = fetch_document_by_rkrattsbaser(converted_id)
            if document_data:
                rkrattsbaser_dir = os.path.join(output_dir, "rkrattsbaser")
                success = save_document_from_rkrattsbaser(document_id, document_data, rkrattsbaser_dir)
            else:
                success = False
            
            if success:
                successful_downloads += 1
            else:
                failed_downloads += 1
            
            # Kort paus mellan nedladdningar
            time.sleep(0.5)
        
        # Sammanfattning
        print("\n=== Sammanfattning testdokument ===")
        print(f"Totalt testdokument: {len(test_docs)}")
        print(f"Lyckade nedladdningar: {successful_downloads}")
        print(f"Misslyckade nedladdningar: {failed_downloads}")
        
        if successful_downloads > 0:
            print(f"Testdokument sparade i: {os.path.abspath(output_dir)}")
        
        return failed_downloads == 0
        
    except json.JSONDecodeError as e:
        print(f"✗ Fel vid parsing av {test_docs_file}: {e}")
        return False
    except IOError as e:
        print(f"✗ Fel vid läsning av {test_docs_file}: {e}")
        return False


def main():
    """
    Huvudfunktion som koordinerar hämtning av dokument-ID:n och nedladdning av dokument.
    """
    parser = argparse.ArgumentParser(description='Ladda ner SFS-dokument från Riksdagens öppna data')
    parser.add_argument('--ids', default='all',
                        help='Kommaseparerad lista med dokument-ID:n att ladda ner, eller "all" för att hämta alla från Riksdagen (default: all)')
    parser.add_argument('--out', default='sfs_docs',
                        help='Mapp att spara nedladdade dokument i (default: sfs_docs)')
    parser.add_argument('--source', choices=['riksdagen', 'rkrattsbaser'], default='riksdagen',
                        help='Välj källa för nedladdning: riksdagen (HTML) eller rkrattsbaser (JSON via Elasticsearch) (default: riksdagen)')
    parser.add_argument('--year', type=int,
                        help='Filtrera dokument för specifikt årtal (t.ex. 2025 för sfs-2025-xxx). Fungerar endast med --ids all och --source riksdagen')
    parser.add_argument('--test-docs', action='store_true',
                        help='Ladda ner testdokument från data/test-doc-ids.json till data/testdocs')

    args = parser.parse_args()

    # Om --test-docs flaggan är satt, kör download_test_docs och avsluta
    if args.test_docs:
        download_test_docs()
        return

    print("=== SFS Dokument Nedladdare ===")
    print(f"Källa: {args.source}")
    if args.year:
        print(f"Filtrerar för år: {args.year}")
    
    # Hämta dokument-ID:n
    if args.ids == 'all':
        document_ids = fetch_document_ids(args.year)
    else:
        # Parsa kommaseparerade dokument-ID:n
        document_ids = [doc_id.strip() for doc_id in args.ids.split(',') if doc_id.strip()]
        print(f"Använder {len(document_ids)} dokument-ID:n från parameter")

        # Varning om --year används med specifika IDs
        if args.year:
            print("⚠ --year parameter ignoreras när specifika dokument-ID:n anges med --ids.")
    
    if not document_ids:
        print("Inga dokument-ID:n hittades. Avslutar.")
        return
    
    # Skapa katalog för nedladdade dokument
    output_dir = args.out
    print(f"\nLaddar ner dokument till katalogen: {output_dir}")
    
    # Ladda ner varje dokument
    successful_downloads = 0
    failed_downloads = 0
    
    for i, document_id in enumerate(document_ids, 1):
        print(f"[{i}/{len(document_ids)}] Laddar ner {document_id}...")

        success = False
        if args.source == 'riksdagen':
            success = download_document(document_id, output_dir)
        elif args.source == 'rkrattsbaser':
            # Konvertera dokument-ID till rätt format för rkrattsbaser
            converted_id = convert_riksdagen_id_to_rkrattsbaser_format(document_id)
            document_data = fetch_document_by_rkrattsbaser(converted_id)
            if document_data:
                success = save_document_from_rkrattsbaser(document_id, document_data, output_dir)

        if success:
            successful_downloads += 1
        else:
            failed_downloads += 1
        
        # Kort paus mellan nedladdningar för att vara snäll mot servern
        time.sleep(0.5)
    
    # Sammanfattning
    print("\n=== Sammanfattning ===")
    print(f"Totalt dokument-ID:n: {len(document_ids)}")
    print(f"Lyckade nedladdningar: {successful_downloads}")
    print(f"Misslyckade nedladdningar: {failed_downloads}")
    
    if successful_downloads > 0:
        print(f"Dokument sparade i katalogen: {os.path.abspath(output_dir)}")


if __name__ == "__main__":
    main()
