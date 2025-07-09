#!/usr/bin/env python3
"""
Unified script för att ladda ner SFS-författningar från olika källor.
Denna fil importerar och koordinerar nedladdning från både Riksdagen och rkrattsbaser.
"""

import os
import time
import argparse
import json
import re
from typing import List

# Importera funktioner från de specifika nedladdningsmodulerna
from riksdagen_api import fetch_document_ids, download_documents as download_riksdagen_documents
from rkrattsbaser_api import (
    fetch_document_by_rkrattsbaser, 
    save_document_from_rkrattsbaser, 
    convert_riksdagen_id_to_rkrattsbaser_format,
    download_documents as download_rkrattsbaser_documents
)


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
    parser = argparse.ArgumentParser(description='Ladda ner SFS-dokument från Regeringskansliets söktjänst eller Riksdagens öppna API')
    parser.add_argument('--ids', default='all',
                        help='Kommaseparerad lista med dokument-ID:n att ladda ner, eller "all" för att hämta alla från Riksdagen (default: all)')
    parser.add_argument('--out', default='sfs_docs',
                        help='Mapp att spara nedladdade dokument i (default: sfs_docs)')
    parser.add_argument('--source', choices=['riksdagen', 'rkrattsbaser'], default='rkrattsbaser',
                        help='Välj källa för nedladdning: riksdagen (HTML) eller rkrattsbaser (JSON via Elasticsearch) (default: rkrattsbaser)')
    parser.add_argument('--year', type=int,
                        help='Filtrera dokument för specifikt årtal (t.ex. 2025 för sfs-2025-xxx). Fungerar endast med --ids all och --source riksdagen')
    parser.add_argument('--test-docs', action='store_true',
                        help='Ladda ner testdokument från data/test-doc-ids.json till data/testdocs')

    args = parser.parse_args()

    # Om --test-docs flaggan är satt, kör download_test_docs och avsluta
    if args.test_docs:
        download_test_docs()
        return

    print("=== SFS-nedladdare ===")
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
    
    # Skapa katalog för nedladdade författningar
    output_dir = args.out
    print(f"\nLaddar ner författningar till katalogen: {output_dir}")

    # Ladda ner författningar baserat på källa
    if args.source == 'riksdagen':
        successful_downloads, failed_downloads = download_riksdagen_documents(document_ids, output_dir)
    elif args.source == 'rkrattsbaser':
        successful_downloads, failed_downloads = download_rkrattsbaser_documents(document_ids, output_dir)
    
    # Sammanfattning
    print("\n=== Sammanfattning ===")
    print(f"Totalt dokument-ID:n: {len(document_ids)}")
    print(f"Lyckade nedladdningar: {successful_downloads}")
    print(f"Misslyckade nedladdningar: {failed_downloads}")
    
    if successful_downloads > 0:
        print(f"Författningar sparade i katalogen: {os.path.abspath(output_dir)}")


if __name__ == "__main__":
    main()