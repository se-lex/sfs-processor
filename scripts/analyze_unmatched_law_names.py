#!/usr/bin/env python3
"""
Show only unmatched law names for better analysis.
"""

import re
import json
import os
from pathlib import Path
from formatters.apply_links import LAW_NAME_PATTERN, _load_law_names


def analyze_unmatched_only():
    """Show only unmatched law names."""

    # Load the law names data
    law_names_data = _load_law_names()
    if not law_names_data:
        print("ERROR: Could not load law names data")
        return

    # Find all markdown files
    md_files = list(Path(".").rglob("*.md"))
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

                    # Check if law exists in JSON
                    if law_name not in law_names_data:
                        unmatched_laws.append({
                            'law_name': law_name,
                            'full_text': full_text,
                            'file': str(file_path)
                        })

        except Exception as e:
            print(f"ERROR reading {file_path}: {e}")
            continue

    print(f"=== INTE MATCHADE MOT JSON ({len(unmatched_laws)}) ===")
    for law in unmatched_laws:
        print(f"✗ {law['law_name']} (SAKNAS I JSON)")
        print(f"  Text: {law['full_text']}")
        print(f"  Fil: {law['file']}")
        print()

    # Get unique unmatched laws
    unique_unmatched = list(set(law['law_name'] for law in unmatched_laws))
    print(f"=== UNIKA LAGAR SOM SAKNAS I JSON ({len(unique_unmatched)}) ===")
    for law_name in sorted(unique_unmatched):
        print(f"  - {law_name}")


if __name__ == "__main__":
    analyze_unmatched_only()
