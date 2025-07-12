#!/usr/bin/env python3
"""
Analyze law name references to identify ones that are mentioned after chapters/paragraphs
but not being matched against the JSON file.
"""

import re
import json
import os
from pathlib import Path
from formatters.apply_links import LAW_NAME_PATTERN, _load_law_names

def analyze_law_name_matches():
    """Analyze law name pattern matches across test files."""
    
    # Load the law names data
    law_names_data = _load_law_names()
    if not law_names_data:
        print("ERROR: Could not load law names data")
        return
    
    print("=== ANALYS AV LAGNAMNSREFERENSER ===")
    print(f"Antal lagar i JSON-fil: {len(law_names_data)}")
    print(f"Aktuellt regex-mönster: {LAW_NAME_PATTERN}")
    print()
    
    # Find all markdown files
    md_files = list(Path(".").rglob("*.md"))
    found_patterns = []
    matched_laws = []
    unmatched_laws = []
    
    for file_path in md_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Find all matches
            matches = re.findall(LAW_NAME_PATTERN, content, re.IGNORECASE)
            
            for match in matches:
                chapter = match[0]
                paragraph_part = match[1].strip()
                law_name = match[2].lower()
                
                # Full match for context
                full_pattern = rf'({re.escape(chapter)})\s+kap\.\s*([^.]*?)\b({re.escape(law_name)})\b'
                full_matches = re.findall(full_pattern, content, re.IGNORECASE)
                
                if full_matches:
                    full_text = f"{chapter} kap. {paragraph_part} {law_name}"
                    found_patterns.append({
                        'file': str(file_path),
                        'chapter': chapter,
                        'paragraph_part': paragraph_part,
                        'law_name': law_name,
                        'full_text': full_text
                    })
                    
                    # Check if law exists in JSON
                    if law_name in law_names_data:
                        matched_laws.append({
                            'law_name': law_name,
                            'sfs_id': law_names_data[law_name],
                            'full_text': full_text,
                            'file': str(file_path)
                        })
                    else:
                        unmatched_laws.append({
                            'law_name': law_name,
                            'full_text': full_text,
                            'file': str(file_path)
                        })
                        
        except Exception as e:
            print(f"ERROR reading {file_path}: {e}")
            continue
    
    # Print results
    print(f"=== HITTADE MÖNSTER ({len(found_patterns)}) ===")
    for pattern in found_patterns:
        print(f"Fil: {pattern['file']}")
        print(f"Text: {pattern['full_text']}")
        print(f"Kapitel: {pattern['chapter']}, Paragraf: '{pattern['paragraph_part']}', Lag: '{pattern['law_name']}'")
        print()
    
    print(f"=== MATCHADE MOT JSON ({len(matched_laws)}) ===")
    for law in matched_laws:
        print(f"✓ {law['law_name']} → {law['sfs_id']}")
        print(f"  Text: {law['full_text']}")
        print(f"  Fil: {law['file']}")
        print()
    
    print(f"=== INTE MATCHADE MOT JSON ({len(unmatched_laws)}) ===")
    for law in unmatched_laws:
        print(f"✗ {law['law_name']} (SAKNAS I JSON)")
        print(f"  Text: {law['full_text']}")
        print(f"  Fil: {law['file']}")
        print()
    
    # Check for potential issues with the regex
    print("=== POTENTIELLA REGEX-PROBLEM ===")
    
    # Look for text that might contain law names after chapters but not match
    test_texts = [
        "8 kap. 7 § regeringsformen",
        "2 kap. 25 § skollagen",
        "2 kap. 10 a–10 c §§ socialförsäkringsbalken",
        "58 kap. 26 och 27 §§ socialförsäkringsbalken",
        "1 kap. 1 § brottsbalken",
        "3 kap. 1-5 §§ förvaltningslagen",
        "4 kap. 1 § första stycket miljöbalken",
        "12 kap. 2 § andra stycket aktiebolagslagen"
    ]
    
    for text in test_texts:
        matches = re.findall(LAW_NAME_PATTERN, text, re.IGNORECASE)
        if matches:
            print(f"✓ Matchar: '{text}' → {matches}")
        else:
            print(f"✗ Matchar INTE: '{text}'")
    
    print()
    print("=== SAMMANFATTNING ===")
    print(f"Totalt antal hittade mönster: {len(found_patterns)}")
    print(f"Matchade mot JSON: {len(matched_laws)}")
    print(f"Inte matchade mot JSON: {len(unmatched_laws)}")
    
    if unmatched_laws:
        unique_unmatched = list(set(law['law_name'] for law in unmatched_laws))
        print(f"Unika lagar som saknas i JSON: {len(unique_unmatched)}")
        print("Dessa är:")
        for law_name in sorted(unique_unmatched):
            print(f"  - {law_name}")

if __name__ == "__main__":
    analyze_law_name_matches()