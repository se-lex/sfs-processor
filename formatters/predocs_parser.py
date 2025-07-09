#!/usr/bin/env python3
"""
Parser for förarbeten (preparatory works) references.

This module parses Swedish legislative preparatory work references and extracts
structured information like document type, year, and number.
"""

import re
from typing import List, Dict, Optional, Tuple


def parse_predocs_string(predocs_str: str) -> List[Dict[str, str]]:
    """
    Parse a förarbeten string and extract individual references.
    
    Args:
        predocs_str: String containing förarbeten references, e.g.,
                    "Prop. 2024/25:1, Bet. 2024/25:FiU1, Rskr 2024/25:59"
    
    Returns:
        List of dictionaries with parsed information:
        [
            {'type': 'prop', 'rm': '2024/25', 'bet': '1', 'original': 'Prop. 2024/25:1'},
            {'type': 'bet', 'rm': '2024/25', 'bet': 'FiU1', 'original': 'Bet. 2024/25:FiU1'},
            {'type': 'rskr', 'rm': '2024/25', 'bet': '59', 'original': 'Rskr 2024/25:59'}
        ]
    """
    if not predocs_str or predocs_str == 'null':
        return []
    
    # Common document type mappings
    type_mappings = {
        'prop': 'prop',
        'proposition': 'prop',
        'bet': 'bet',
        'betänkande': 'bet',
        'rskr': 'rskr',
        'riksdagsskrivelse': 'rskr',
        'lu': 'bet',  # Lagutskottet
        '1lu': 'bet', # Första lagutskottet
        '2lu': 'bet', # Andra lagutskottet
        '3lu': 'bet', # Tredje lagutskottet
        '4lu': 'bet', # Fjärde lagutskottet
        '5lu': 'bet', # Femte lagutskottet
        'fiu': 'bet',  # Finansutskottet
        'ju': 'bet',   # Justitieutskottet
        'sou': 'bet',  # Socialutskottet
        'nu': 'bet',   # Näringsutskottet
        'ku': 'bet',   # Konstitutionsutskottet
        'sku': 'bet',  # Skatteutskottet
        'tu': 'bet',   # Trafikutskottet
        'ceu': 'bet',  # Civilutskottet
        'uu': 'bet',   # Utrikesutskottet
        'föu': 'bet',  # Försvarsutskottet
        'mju': 'bet',  # Miljö- och jordbruksutskottet
        'au': 'bet',   # Arbetsmarknadsutskottet
        'sfu': 'bet',  # Socialförsäkringsutskottet
        'kru': 'bet',  # Kulturutskottet
        'ubu': 'bet',  # Utbildningsutskottet
    }
    
    results = []
    
    # Split by common separators (comma, semicolon, and 'och'/'and')
    parts = re.split(r'[,;]|\s+och\s+|\s+and\s+', predocs_str)
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        # Try to match different patterns
        # Pattern 1: Type. YYYY/YY:NNN or Type YYYY/YY:NNN
        match = re.match(r'(\w+)\.?\s+(\d{4}/\d{2,4}):(\w+)', part, re.IGNORECASE)
        if match:
            doc_type = match.group(1).lower()
            rm = match.group(2)
            bet = match.group(3)
            
            # Map to standard document type
            mapped_type = type_mappings.get(doc_type, doc_type)
            
            results.append({
                'type': mapped_type,
                'rm': rm,
                'bet': bet,
                'original': part
            })
            continue
        
        # Pattern 2: Type YYYY:NNN (older format)
        match = re.match(r'(\w+)\.?\s+(\d{4}):(\w+)', part, re.IGNORECASE)
        if match:
            doc_type = match.group(1).lower()
            year = match.group(2)
            bet = match.group(3)
            
            # Convert to YYYY/YY format
            rm = f"{year}/{str(int(year) + 1)[2:]}"
            
            # Map to standard document type
            mapped_type = type_mappings.get(doc_type, doc_type)
            
            results.append({
                'type': mapped_type,
                'rm': rm,
                'bet': bet,
                'original': part
            })
            continue
        
        # Pattern 3: Committee abbreviation with year and number (e.g., "1LU 1967:53")
        match = re.match(r'(\d?\w+)\s+(\d{4}):(\d+)', part, re.IGNORECASE)
        if match:
            doc_type = match.group(1).lower()
            year = match.group(2)
            bet = match.group(3)
            
            # Convert to YYYY/YY format
            rm = f"{year}/{str(int(year) + 1)[2:]}"
            
            # Map to standard document type
            mapped_type = type_mappings.get(doc_type, doc_type)
            
            results.append({
                'type': mapped_type,
                'rm': rm,
                'bet': bet,
                'original': part
            })
            continue
        
        # Pattern 4: Just "rskr NNN" without year
        match = re.match(r'(\w+)\.?\s+(\d+)$', part, re.IGNORECASE)
        if match:
            doc_type = match.group(1).lower()
            bet = match.group(2)
            
            # Map to standard document type
            mapped_type = type_mappings.get(doc_type, doc_type)
            
            # We don't have a year, so we'll skip this one
            # or could try to infer from context
            continue
    
    return results




if __name__ == "__main__":
    # Test the parser
    test_cases = [
        "Prop. 2024/25:1, Bet. 2024/25:FiU1, Rskr 2024/25:59",
        "Prop. 1966:40; 1LU 1967:53; Rskr 1967:325",
        "Prop. 2023/24:144, bet. 2024/25:JuU3, rskr. 2024/25:9",
        "Prop. 1982/83:67, LU 1982/83:33, rskr 1982/83:250",
        "Prop. 1971:30, KU 36, rskr 222",
    ]
    
    for test in test_cases:
        print(f"\nParsing: {test}")
        results = parse_predocs_string(test)
        for result in results:
            print(f"  - {result}")