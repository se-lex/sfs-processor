#!/usr/bin/env python3
"""
Script för att lägga till matchade lagnamn i law-names.json med förbättrad filtrering
"""

import json
from pathlib import Path
from collections import defaultdict

def is_valid_law_type(rubrik, forfattningstyp):
    """
    Kontrollera om detta är en giltig huvudlag/huvudförordning.
    Filtrera bort införandelagar, kungörelser, etc.
    """
    rubrik_lower = rubrik.lower()

    # Filtrera bort dåliga typer
    bad_patterns = [
        'kungörelse',
        'cirkulär',
        'brev',
        'tillkännagivande',
        'införande av',
        'om införande',
        'tillämpning av',
        'om tillämpning',
        'ändr',  # ändringsförfattningar
        'ändring i',
        'om ändring',
    ]

    for pattern in bad_patterns:
        if pattern in rubrik_lower:
            return False

    # Acceptera endast Lag och Förordning
    if forfattningstyp not in ['Lag', 'Förordning']:
        return False

    return True

def score_match(law_name, match):
    """
    Ge poäng till en matchning baserat på hur bra den är.
    Högre poäng = bättre matchning
    """
    score = 0
    rubrik = match['rubrik']
    rubrik_lower = rubrik.lower()
    law_name_lower = law_name.lower()
    search_term = match['search_term']

    # Stor bonus om exakt lagnamn finns i rubriken
    if law_name_lower in rubrik_lower:
        score += 30

    # Bonus om författningstypen matchar lagnamnet
    if 'lag' in law_name_lower and match['forfattningstyp'] == 'Lag':
        score += 15
    elif 'förordning' in law_name_lower and match['forfattningstyp'] == 'Förordning':
        score += 15

    # Stor bonus om lagnamnet är i början av rubriken (efter författningstyp och nummer)
    # T.ex. "Förordning (2019:66) Djurskyddsförordning"
    if rubrik_lower.find(law_name_lower) < 50:
        score += 10

    # Bonus om rubriken är enkel och ren (troligen huvudlagen)
    # T.ex. "Djurskyddslag (2018:1192)" är bättre än "Förordning om tillämpning av..."
    if len(rubrik) < 100 and search_term in rubrik_lower[:50]:
        score += 10

    # Bonus för nyare lagar
    try:
        year = int(match['id'].split(':')[0])
        if year >= 2010:
            score += 5
        elif year >= 2000:
            score += 3
        elif year >= 1990:
            score += 2
    except:
        pass

    # Minus om söktermen är väldigt kort (risk för false positive)
    if len(search_term) < 6:
        score -= 5

    return score

def select_best_matches(matches_file):
    """
    Välj den bästa matchningen för varje lagnamn med förbättrad filtrering
    """
    with open(matches_file, 'r', encoding='utf-8') as f:
        all_matches = json.load(f)

    best_matches = {}
    skipped_names = defaultdict(list)

    for law_name, match_list in all_matches.items():
        if not match_list:
            continue

        # Filtrera bort dåliga matchningar
        filtered = []
        for match in match_list:
            # Skippa om söktermen är för kort och lagnamnet inte finns exakt
            if len(match['search_term']) < 5 and law_name.lower() not in match['rubrik'].lower():
                skipped_names[law_name].append(('short_search_term', match))
                continue

            # Skippa om det inte är en giltig lagtyp
            if not is_valid_law_type(match['rubrik'], match['forfattningstyp']):
                skipped_names[law_name].append(('invalid_type', match))
                continue

            filtered.append(match)

        if not filtered:
            continue

        # Beräkna poäng för varje matchning
        scored_matches = []
        for match in filtered:
            score = score_match(law_name, match)
            # Behåll endast matchningar med positiv poäng
            if score > 10:
                scored_matches.append((score, match))

        if not scored_matches:
            continue

        # Sortera efter poäng (högst först)
        scored_matches.sort(key=lambda x: x[0], reverse=True)

        # Ta den bästa matchningen
        best_score, best_match = scored_matches[0]
        best_matches[law_name] = {
            'match': best_match,
            'score': best_score,
            'alternatives': len(scored_matches)
        }

    return best_matches, skipped_names

def add_to_law_names(best_matches, law_names_file, output_file):
    """
    Lägg till de bästa matchningarna i law-names.json
    """
    # Läs in befintliga lagnamn
    with open(law_names_file, 'r', encoding='utf-8') as f:
        existing_laws = json.load(f)

    # Skapa en uppslagslista för befintliga ID:n och namn
    existing_ids = {law['id'] for law in existing_laws}
    existing_names = {law['name'].lower() for law in existing_laws if law.get('name')}

    # Lägg till nya matchningar
    added_count = 0
    skipped_count = 0

    for law_name, match_info in best_matches.items():
        match = match_info['match']
        law_id = match['id']

        # Skippa om ID:t redan finns
        if law_id in existing_ids:
            skipped_count += 1
            continue

        # Skippa om namnet redan finns
        if law_name.lower() in existing_names:
            skipped_count += 1
            continue

        # Skapa ny post (utan rubrik för att matcha befintligt format)
        new_entry = {
            'id': law_id,
            'name': law_name,
            'type': 'law' if match['forfattningstyp'] == 'Lag' else 'regulation',
            'alternativeNames': []
        }

        existing_laws.append(new_entry)
        existing_ids.add(law_id)
        existing_names.add(law_name.lower())
        added_count += 1

    # Sortera efter ID
    existing_laws.sort(key=lambda x: x['id'])

    # Spara uppdaterad fil
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(existing_laws, f, indent=2, ensure_ascii=False)

    return added_count, skipped_count, len(existing_laws)

def main():
    matches_file = Path("logs/found_law_matches.json")
    law_names_file = Path("data/law-names.json")
    output_file = Path("data/law-names-updated.json")

    print("Analyserar matchningar med förbättrad filtrering...")
    best_matches, skipped = select_best_matches(matches_file)

    print(f"\nValde {len(best_matches)} bästa matchningar")
    print(f"Filtrerade bort matchningar för {len(skipped)} lagnamn")

    # Visa de 30 bästa matchningarna
    print("\nTopp 30 matchningar (sorterade efter poäng):")
    print("=" * 80)

    sorted_matches = sorted(best_matches.items(), key=lambda x: x[1]['score'], reverse=True)
    for law_name, info in sorted_matches[:30]:
        match = info['match']
        print(f"\n{law_name} (poäng: {info['score']}, alternativ: {info['alternatives']})")
        print(f"  -> {match['id']}: {match['rubrik'][:70]}...")

    # Lägg till i law-names.json
    print("\n" + "=" * 80)
    print("Lägger till i law-names.json...")

    added, skipped_count, total = add_to_law_names(best_matches, law_names_file, output_file)

    print(f"\nResultat:")
    print(f"  Tillagda: {added}")
    print(f"  Hoppade över (finns redan eller duplicerat namn): {skipped_count}")
    print(f"  Totalt i fil: {total}")
    print(f"\nUppdaterad fil sparad som: {output_file}")

if __name__ == "__main__":
    main()
