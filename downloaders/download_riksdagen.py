#!/usr/bin/env python3
"""
Script för att ladda ner SFS-författningar från Riksdagens öppna data.
Hämtar först en lista med författnings-ID:n och laddar sedan ner textinnehållet för varje författning.
"""

import requests
import os
import time
from typing import List, Optional


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


def download_documents(document_ids: List[str], output_dir: str = "documents") -> tuple[int, int]:
    """
    Laddar ner en lista med dokument från Riksdagen.
    
    Args:
        document_ids (List[str]): Lista med dokument-ID:n att ladda ner
        output_dir (str): Katalog att spara filerna i
        
    Returns:
        tuple[int, int]: (successful_downloads, failed_downloads)
    """
    successful_downloads = 0
    failed_downloads = 0
    
    for i, document_id in enumerate(document_ids, 1):
        print(f"[{i}/{len(document_ids)}] Laddar ner {document_id}...")
        
        success = download_document(document_id, output_dir)
        
        if success:
            successful_downloads += 1
        else:
            failed_downloads += 1
        
        # Kort paus mellan nedladdningar för att vara snäll mot servern
        time.sleep(0.5)
    
    return successful_downloads, failed_downloads