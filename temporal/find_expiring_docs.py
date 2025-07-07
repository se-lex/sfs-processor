#!/usr/bin/env python3
"""
Script för att hitta författningar som utgår på ett visst datum.
Söker igenom alla JSON-filer i en mapp som har ett värde (icke-null) 
i JSON-egenskapen "tidsbegransadDateTime".

Användning:
    python temporal/find_expiring_docs.py <input_mapp>

Exempel:
    python temporal/find_expiring_docs.py sfs_json/
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any


def load_json_file(file_path: Path) -> Dict[Any, Any]:
    """Laddar och returnerar innehållet i en JSON-fil."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, UnicodeDecodeError) as e:
        print(f"Varning: Kunde inte läsa {file_path}: {e}", file=sys.stderr)
        return {}


def has_expiring_datetime(data: Dict[Any, Any]) -> bool:
    """Kontrollerar om JSON-data har ett icke-null värde för 'tidsbegransadDateTime'."""
    return (
        'tidsbegransadDateTime' in data and 
        data['tidsbegransadDateTime'] is not None and
        data['tidsbegransadDateTime'] != ""
    )


def find_expiring_files(input_dir: Path) -> List[Dict[str, Any]]:
    """
    Söker igenom en mapp efter JSON-filer med tidsbegransadDateTime-värden.
    
    Returns:
        Lista med dict innehållande filnamn, sökväg och tidsbegransadDateTime-värde
    """
    results = []
    
    if not input_dir.exists():
        print(f"Fel: Mappen {input_dir} finns inte.", file=sys.stderr)
        return results
    
    if not input_dir.is_dir():
        print(f"Fel: {input_dir} är inte en mapp.", file=sys.stderr)
        return results
    
    # Hitta alla JSON-filer i mappen
    json_files = list(input_dir.glob("*.json"))
    
    if not json_files:
        print(f"Inga JSON-filer hittades i {input_dir}")
        return results
    
    print(f"Söker igenom {len(json_files)} JSON-filer i {input_dir}...")
    
    for json_file in json_files:
        data = load_json_file(json_file)
        
        if has_expiring_datetime(data):
            results.append({
                'filename': json_file.name,
                'filepath': str(json_file),
                'tidsbegransadDateTime': data['tidsbegransadDateTime'],
                'beteckning': data['beteckning'],
                'rubrik': data['rubrik']
            })
    
    return results


def print_results(results: List[Dict[str, Any]]) -> None:
    """Skriver ut resultaten i ett läsbart format."""
    if not results:
        print("Inga filer med tidsbegränsad giltighetstid hittades.")
        return
    
    print(f"\nHittade {len(results)} fil(er) med tidsbegränsad giltighetstid:\n")
    print(f"{'Beteckning':<15} {'Tidsbegränsad till':<20} {'Filnamn':<25} {'Rubrik'}")
    print("-" * 120)
    
    # Sortera resultaten efter tidsbegransadDateTime
    sorted_results = sorted(results, key=lambda x: x['tidsbegransadDateTime'])
    
    for result in sorted_results:
        # Formatera datum för bättre läsbarhet
        datetime_str = result['tidsbegransadDateTime']
        if 'T' in datetime_str:
            date_part = datetime_str.split('T')[0]
        else:
            date_part = datetime_str
            
        print(f"{result['beteckning']:<15} {date_part:<20} {result['filename']:<25} {result['rubrik'][:60]}...")


def save_results_to_file(results: List[Dict[str, Any]], output_file: str = "tidsbegransade_filer.txt") -> None:
    """Sparar resultaten till en textfil."""
    if not results:
        return
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Filer med tidsbegränsad giltighetstid - Genererad {Path().cwd()}\n")
        f.write(f"Totalt antal filer: {len(results)}\n\n")
        
        sorted_results = sorted(results, key=lambda x: x['tidsbegransadDateTime'])
        
        for result in sorted_results:
            f.write(f"Beteckning: {result['beteckning']}\n")
            f.write(f"Tidsbegränsad till: {result['tidsbegransadDateTime']}\n")
            f.write(f"Filnamn: {result['filename']}\n")
            f.write(f"Sökväg: {result['filepath']}\n")
            f.write(f"Rubrik: {result['rubrik']}\n")
            f.write("-" * 80 + "\n")
    
    print(f"\nResultaten har sparats till {output_file}")


def main():
    """Huvudfunktion som hanterar kommandoradsargument och kör sökningen."""
    if len(sys.argv) != 2:
        print("Användning: python temporal/find_expiring_docs.py <input_mapp>")
        print("Exempel: python temporal/find_expiring_docs.py sfs_json/")
        sys.exit(1)
    
    input_dir = Path(sys.argv[1])
    
    # Hitta filer med tidsbegränsad giltighetstid
    results = find_expiring_files(input_dir)
    
    # Visa resultaten
    print_results(results)
    
    # Spara resultaten till fil om det finns några
    if results:
        save_results_to_file(results)


if __name__ == "__main__":
    main()
