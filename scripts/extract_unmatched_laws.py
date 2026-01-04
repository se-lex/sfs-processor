#!/usr/bin/env python3
"""
Script för att extrahera alla omatchade lagnamn från valideringsrapporten.
"""

import re


def extract_unmatched_laws():
    """Extrahera alla omatchade lagnamn från rapporten."""

    # Läs rapportfilen
    with open('lagnamn_validering_rapport.md', 'r', encoding='utf-8') as f:
        content = f.read()

    # Extrahera alla omatchade lagnamn och deras antal
    # Mönster: ### lagnamn\n- **Antal förekomster**: antal
    pattern = r'### (.+?)\n- \*\*Antal förekomster\*\*: (\d+)'
    matches = re.findall(pattern, content)

    print('ALLA LAGNAMN SOM INTE MATCHADE MOT JSON-FILEN')
    print('=' * 60)
    print(f'Totalt: {len(matches)} unika lagnamn som inte matchas')
    print()

    # Sortera efter frekvens (högst först)
    matches_sorted = sorted(matches, key=lambda x: int(x[1]), reverse=True)

    print('LISTA (sorterad efter antal förekomster):')
    print('-' * 40)

    for i, (law_name, count) in enumerate(matches_sorted, 1):
        print(f'{i:3d}. {law_name:<35} {count:>6} förekomster')


if __name__ == "__main__":
    extract_unmatched_laws()
