#!/usr/bin/env python3
"""
Script för att hitta och lägga till saknade lagnamn i law-names.json
genom att söka i alla JSON-filer från SFS-databasen.
"""

import json
import re
from pathlib import Path
from collections import defaultdict

def normalize_law_name(name):
    """Normalisera lagnamn för bättre matchning"""
    if not name:
        return ""
    # Ta bort extra whitespace och konvertera till lowercase
    name = name.lower().strip()
    # Ta bort bindestreck som kan vara felstavningar
    name = name.replace('-', '')
    return name

def extract_search_term(law_name):
    """
    Extrahera sökterm från ett lagnamn.
    T.ex. "brottsdatalagen" -> "brottsdata"
    """
    # Ta bort vanliga suffix
    suffixes = ['lagen', 'förordningen', 'balken', 'ordningen', 'boken']
    search_term = law_name.lower()

    for suffix in suffixes:
        if search_term.endswith(suffix):
            search_term = search_term[:-len(suffix)]
            break

    return search_term.strip()

def find_matching_laws(missing_names, json_dir):
    """
    Sök genom alla JSON-filer och hitta lagar som matchar de saknade namnen
    """
    json_files = list(Path(json_dir).glob("*.json"))
    matches = defaultdict(list)

    print(f"Söker genom {len(json_files)} JSON-filer...")

    processed = 0
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Kontrollera rubrik
            rubrik = data.get('rubrik', '').lower()
            beteckning = data.get('beteckning', '')

            if not rubrik or not beteckning:
                continue

            # För varje saknat lagnamn, kolla om det matchar
            for missing_name in missing_names:
                search_term = extract_search_term(missing_name)

                # Skippa för korta söktermer (för många false positives)
                if len(search_term) < 4:
                    continue

                # Kolla om söktermen finns i rubriken
                if search_term in rubrik:
                    matches[missing_name].append({
                        'id': beteckning,
                        'rubrik': data.get('rubrik', '').strip(),
                        'search_term': search_term,
                        'forfattningstyp': data.get('forfattningstypNamn', ''),
                        'file': json_file.name
                    })

            processed += 1
            if processed % 1000 == 0:
                print(f"Bearbetat {processed}/{len(json_files)} filer...")

        except (json.JSONDecodeError, IOError) as e:
            print(f"Fel vid läsning av {json_file}: {e}")
            continue

    return matches

def main():
    # Läs in saknade lagnamn
    missing_file = Path("logs/missing_law_names.txt")
    with open(missing_file, 'r', encoding='utf-8') as f:
        missing_names = [line.strip() for line in f if line.strip()]

    print(f"Hittade {len(missing_names)} saknade lagnamn")

    # Sök i JSON-katalogen
    json_dir = Path("../sfs-jsondata")
    if not json_dir.exists():
        print(f"Fel: Katalogen {json_dir} finns inte!")
        return

    matches = find_matching_laws(missing_names, json_dir)

    print(f"\nHittade matchningar för {len(matches)} lagnamn:")
    print("=" * 80)

    # Spara resultaten
    output_file = Path("logs/found_law_matches.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(matches, f, indent=2, ensure_ascii=False)

    print(f"\nResultat sparat till: {output_file}")

    # Visa statistik
    total_matches = sum(len(v) for v in matches.values())
    print(f"\nTotalt: {total_matches} matchningar för {len(matches)} unika lagnamn")

    # Visa några exempel
    print("\nExempel på matchningar:")
    print("=" * 80)
    for name, law_list in list(matches.items())[:15]:
        if law_list:
            print(f"\n'{name}' (sökterm: '{extract_search_term(name)}'):")
            for law in law_list[:2]:  # Visa max 2 matchningar per namn
                print(f"  - {law['id']}: {law['rubrik'][:80]}...")

if __name__ == "__main__":
    main()
