#!/usr/bin/env python3
"""
Downloader for Swedish Parliament (Riksdag) documents via the Riksdag API.

This module fetches document information from the Swedish Parliament's open data API
for legislative preparatory works (förarbeten) and full SFS documents.
"""

import json
import os
import requests
import time
from typing import List, Dict, Optional, Tuple
# Removed unused import: from urllib.parse import quote


class RiksdagenAPIError(Exception):
    """Custom exception for Riksdag API errors."""
    pass


def construct_rd_docid(doc_type: str, rm: str, bet: str) -> Optional[str]:
    """
    Construct a Riksdag document ID (rd_docid) from document type, riksmötesår and beteckning.
    
    Args:
        doc_type: Document type ('prop', 'bet', 'rskr', etc.)
        rm: Riksmötesår (e.g., "2024/25")
        bet: Beteckning (document number/designation)
    
    Returns:
        Constructed rd_docid string or None if construction fails
    """
    # Mapping from riksmötesår to two-character year codes
    # Based on Swedish parliamentary year system
    year_mappings = {
        "2024/25": "HB", "2023/24": "HA", "2022/23": "H9", "2021/22": "H8",
        "2020/21": "H7", "2019/20": "H6", "2018/19": "H5", "2017/18": "H4",
        "2016/17": "H3", "2015/16": "H2", "2014/15": "H1", "2013/14": "H0",
        "2012/13": "GZ", "2011/12": "GY", "2010/11": "GX", "2009/10": "GW",
        "2008/09": "GV", "2007/08": "GU", "2006/07": "GT", "2005/06": "GS",
        "2004/05": "GR", "2003/04": "GQ", "2002/03": "GP", "2001/02": "GO",
        "2000/01": "GN", "1999/00": "GM", "1998/99": "GL", "1997/98": "GK",
        "1996/97": "GJ", "1995/96": "GI", "1994/95": "GH", "1993/94": "GG"
    }
    
    # Mapping from document types to series codes
    doc_type_mappings = {
        'prop': '03',  # Government propositions
        'bet': '01',   # Committee reports
        'rskr': '04',  # Riksdagsskrivelser
        'mot': '02',   # Motions
        'ip': '10',    # Interpellations
        'fr': '11',    # Questions
    }
    
    # Get year code
    year_code = year_mappings.get(rm)
    if not year_code:
        return None
    
    # Get document series code
    series_code = doc_type_mappings.get(doc_type)
    if not series_code:
        return None
    
    # Construct the rd_docid
    # Format: [year_code][series_code][beteckning]
    rd_docid = f"{year_code}{series_code}{bet}"
    
    return rd_docid


def fetch_document_info(doc_type: str, rm: str, bet: str, max_retries: int = 3, delay: float = 0.5) -> Optional[Dict[str, str]]:
    """
    Fetch document information from Riksdag API using document type, riksmötesår and beteckning.
    
    Args:
        doc_type: Document type ('prop', 'bet', 'rskr', etc.)
        rm: Riksmötesår (e.g., "2024/25")
        bet: Beteckning (document number)
        max_retries: Maximum number of retry attempts
        delay: Delay between requests in seconds
    
    Returns:
        Dictionary with document info: {'dokumentnamn': '...', 'titel': '...'}
        Returns None if document not found or on error.
    """
    # Construct the rd_docid
    rd_docid = construct_rd_docid(doc_type, rm, bet)
    if not rd_docid:
        print(f"Varning: Kunde inte konstruera rd_docid för {doc_type} {rm}:{bet}")
        return None
    
    url = f"https://data.riksdagen.se/dokument/{rd_docid}.json"
    
    for attempt in range(max_retries):
        try:
            # Add delay to be respectful to the API
            if attempt > 0:
                time.sleep(delay)
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract document information from JSON response
            if 'dokumentstatus' in data and 'dokument' in data['dokumentstatus']:
                doc = data['dokumentstatus']['dokument']
                
                # Extract the information we need
                dokumentnamn = doc.get('dokumentnamn', '')
                titel = doc.get('titel', '')
                
                if dokumentnamn and titel:
                    return {
                        'dokumentnamn': dokumentnamn,
                        'titel': titel
                    }
            
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"Varning: HTTP-fel vid hämtning av {rd_docid} ({doc_type} {rm}:{bet}): {e}")
            if attempt == max_retries - 1:
                return None
        except json.JSONDecodeError as e:
            print(f"Varning: JSON-parsing misslyckades för {rd_docid} ({doc_type} {rm}:{bet}): {e}")
            if attempt == max_retries - 1:
                return None
        except Exception as e:
            print(f"Varning: Oväntat fel vid hämtning av {rd_docid} ({doc_type} {rm}:{bet}): {e}")
            if attempt == max_retries - 1:
                return None
    
    return None


def fetch_predocs_details(predocs_list: List[Dict[str, str]], 
                        delay_between_requests: float = 0.5) -> List[Dict[str, str]]:
    """
    Fetch detailed information for a list of förarbeten references.
    
    Args:
        predocs_list: List of parsed förarbeten dictionaries
        delay_between_requests: Delay between requests in seconds
    
    Returns:
        List of dictionaries with detailed information:
        [
            {
                'type': 'prop',
                'rm': '2024/25', 
                'bet': '1',
                'original': 'Prop. 2024/25:1',
                'dokumentnamn': 'Prop. 2024/25:1',
                'titel': 'Statsbudget för 2025'
            },
            ...
        ]
    """
    detailed_results = []
    
    for i, predoc in enumerate(predocs_list):
        # Add delay between requests to be respectful
        if i > 0:
            time.sleep(delay_between_requests)
        
        rm = predoc.get('rm')
        bet = predoc.get('bet')
        
        if not all([rm, bet]):
            # Keep original entry if we can't fetch details
            detailed_results.append(predoc)
            continue
        
        print(f"Hämtar information för {rm}:{bet}...")
        
        doc_info = fetch_document_info(predoc.get('type'), rm, bet)
        
        if doc_info:
            # Merge the original information with the fetched details
            result = predoc.copy()
            result.update(doc_info)
            detailed_results.append(result)
            print(f"  - Hittade: {doc_info['dokumentnamn']}: {doc_info['titel']}")
        else:
            # Keep original entry if we couldn't fetch details
            detailed_results.append(predoc)
            print(f"  - Kunde inte hämta information för {predoc['original']}")
    
    return detailed_results


def format_predocs_for_frontmatter(detailed_predocs: List[Dict[str, str]]) -> List[str]:
    """
    Format detailed förarbeten information for use in frontmatter.
    
    Args:
        detailed_predocs: List of dictionaries with document details
    
    Returns:
        List of formatted strings in the format "(Dokumentnamn): (titel)"
    """
    formatted = []
    
    for predoc in detailed_predocs:
        dokumentnamn = predoc.get('dokumentnamn', '')
        titel = predoc.get('titel', '')
        original = predoc.get('original', '')
        
        if titel:
            if dokumentnamn:
                # Extract part after the first period from original
                import re
                after_period = re.sub(r'^[^.]*\.?\s*', '', original)
                formatted.append(f"{dokumentnamn} {after_period}: {titel}")
            else:
                formatted.append(f"{original}: {titel}")
        else:
            # Fallback to original reference if we don't have full details
            formatted.append(original)
    
    return formatted


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


def download_doc_as_html(document_id: str, output_dir: str = "documents") -> bool:
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


def download_documents(document_ids: List[str], output_dir: str = "documents") -> Tuple[int, int]:
    """
    Laddar ner en lista med dokument från Riksdagen.
    
    Args:
        document_ids (List[str]): Lista med dokument-ID:n att ladda ner
        output_dir (str): Katalog att spara filerna i
        
    Returns:
        Tuple[int, int]: (successful_downloads, failed_downloads)
    """
    successful_downloads = 0
    failed_downloads = 0
    
    for i, document_id in enumerate(document_ids, 1):
        print(f"[{i}/{len(document_ids)}] Laddar ner {document_id}...")
        
        success = download_doc_as_html(document_id, output_dir)
        
        if success:
            successful_downloads += 1
        else:
            failed_downloads += 1
        
        # Kort paus mellan nedladdningar för att vara snäll mot servern
        time.sleep(0.5)
    
    return successful_downloads, failed_downloads


if __name__ == "__main__":
    # Test the API functions
    from formatters.predocs_parser import parse_predocs_string
    
    test_string = "Prop. 2024/25:1, bet. 2024/25:FiU1"
    print(f"Testing with: {test_string}")
    
    parsed = parse_predocs_string(test_string)
    print(f"Parsed: {parsed}")
    
    if parsed:
        detailed = fetch_predocs_details(parsed)
        print(f"Detailed: {detailed}")
        
        formatted = format_predocs_for_frontmatter(detailed)
        print(f"Formatted for frontmatter:")
        for item in formatted:
            print(f"  - {item}")