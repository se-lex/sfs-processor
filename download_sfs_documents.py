#!/usr/bin/env python3
"""
Script för att ladda ner SFS-dokument från Riksdagens öppna data.
Hämtar först en lista med dokument-ID:n och laddar sedan ner textinnehållet för varje dokument.
"""

import requests
import os
import time
import argparse
from typing import List


def fetch_document_ids() -> List[str]:
    """
    Hämtar dokument-ID:n från Riksdagens dokumentlista.
    
    Returns:
        List[str]: Lista med dokument-ID:n
    """
    url = "https://data.riksdagen.se/dokumentlista/?sok=&doktyp=SFS&utformat=iddump&a=s#soktraff"
    
    print(f"Hämtar dokument-ID:n från: {url}")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Parsa kommaseparerade värden och trimma mellanslag
        content = response.text.strip()
        document_ids = [doc_id.strip() for doc_id in content.split(',') if doc_id.strip()]
        
        print(f"Hittade {len(document_ids)} dokument-ID:n")
        return document_ids
        
    except requests.RequestException as e:
        print(f"Fel vid hämtning av dokument-ID:n: {e}")
        return []


def download_document(document_id: str, output_dir: str = "documents") -> bool:
    """
    Laddar ner textinnehållet för ett specifikt dokument-ID.
    
    Args:
        document_id (str): Dokument-ID att ladda ner
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


def main():
    """
    Huvudfunktion som koordinerar hämtning av dokument-ID:n och nedladdning av dokument.
    """
    parser = argparse.ArgumentParser(description='Ladda ner SFS-dokument från Riksdagens öppna data')
    parser.add_argument('--ids', default='all',
                        help='Kommaseparerad lista med dokument-ID:n att ladda ner, eller "all" för att hämta alla från Riksdagen (default: all)')
    parser.add_argument('--out', default='sfs_html',
                        help='Mapp att spara nedladdade dokument i (default: sfs_html)')

    args = parser.parse_args()

    print("=== SFS Dokument Nedladdare ===")
    
    # Hämta dokument-ID:n
    if args.ids == 'all':
        document_ids = fetch_document_ids()
    else:
        # Parsa kommaseparerade dokument-ID:n
        document_ids = [doc_id.strip() for doc_id in args.ids.split(',') if doc_id.strip()]
        print(f"Använder {len(document_ids)} dokument-ID:n från parameter")
    
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
        
        if download_document(document_id, output_dir):
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
