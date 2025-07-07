#!/usr/bin/env python3
"""
Script för att ladda ner SFS-författningar från Regeringskansliets rättsdatabas.
Använder Elasticsearch API för att hämta författningar i JSON-format.
"""

import requests
import os
import time
import json
from typing import List, Optional, Dict


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


def download_documents(document_ids: List[str], output_dir: str = "rkrattsbaser") -> tuple[int, int]:
    """
    Laddar ner en lista med dokument från rkrattsbaser.
    
    Args:
        document_ids (List[str]): Lista med dokument-ID:n att ladda ner (i Riksdagen-format)
        output_dir (str): Katalog att spara filerna i
        
    Returns:
        tuple[int, int]: (successful_downloads, failed_downloads)
    """
    successful_downloads = 0
    failed_downloads = 0
    
    for i, document_id in enumerate(document_ids, 1):
        print(f"[{i}/{len(document_ids)}] Laddar ner {document_id}...")
        
        # Konvertera dokument-ID till rätt format för rkrattsbaser
        converted_id = convert_riksdagen_id_to_rkrattsbaser_format(document_id)
        
        # Ladda ner dokumentet från rkrattsbaser
        document_data = fetch_document_by_rkrattsbaser(converted_id)
        if document_data:
            success = save_document_from_rkrattsbaser(document_id, document_data, output_dir)
        else:
            success = False
        
        if success:
            successful_downloads += 1
        else:
            failed_downloads += 1
        
        # Kort paus mellan nedladdningar för att vara snäll mot servern
        time.sleep(0.5)
    
    return successful_downloads, failed_downloads