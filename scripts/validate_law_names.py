#!/usr/bin/env python3
"""
Script to validate law names and detect missing entries in law-names.json.

This script scans through SFS markdown files and identifies law name references
that follow the pattern "X kap. Y § lagnamn" but are not found in the law-names.json file.
"""

import re
import json
import os
from pathlib import Path
from collections import defaultdict, Counter

# Regex pattern for law name references (same as in apply_links.py)
LAW_NAME_PATTERN = r'(\d+)\s+kap\.\s*([^.]*?)\b([a-zåäöA-ZÅÄÖ-]+(?:lagen|balken|formen|boken|ordningen))\b'


def load_law_names(json_file_path):
    """Load law names from JSON file."""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            law_data = json.load(f)

        # Create lookup dictionary: lagnamn -> SFS-ID
        law_lookup = {}
        for entry in law_data:
            if entry.get('name'):
                law_lookup[entry['name'].lower()] = entry['id']

        return law_lookup, law_data

    except Exception as e:
        print(f"Fel vid laddning av lagnamn: {e}")
        return {}, []


def scan_markdown_files(directory):
    """Scan markdown files for law name references."""
    references = []

    # Find all markdown files
    md_files = list(Path(directory).rglob("*.md"))

    for md_file in md_files:
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find all law name references
            matches = re.findall(LAW_NAME_PATTERN, content)
            for match in matches:
                chapter, paragraph_part, law_name = match
                references.append({
                    'file': str(md_file),
                    'chapter': chapter,
                    'paragraph': paragraph_part.strip(),
                    'law_name': law_name.lower(),
                    'full_match': f"{chapter} kap. {paragraph_part.strip()} {law_name}"
                })

        except Exception as e:
            print(f"Varning: Kunde inte läsa fil {md_file}: {e}")

    return references


def analyze_references(references, law_lookup):
    """Analyze references and find missing law names."""
    matched = []
    unmatched = []

    for ref in references:
        if ref['law_name'] in law_lookup:
            matched.append(ref)
        else:
            unmatched.append(ref)

    return matched, unmatched


def generate_report(matched, unmatched, law_lookup):
    """Generate a detailed report."""
    report = []

    report.append("# Rapport: Validering av lagnamn i SFS-filer")
    report.append("")
    report.append("## Sammanfattning")
    report.append("")

    total_refs = len(matched) + len(unmatched)
    match_percentage = (len(matched) / total_refs * 100) if total_refs > 0 else 0

    report.append(f"- **Totalt antal lagnamnsreferenser**: {total_refs}")
    report.append(f"- **Matchade mot JSON-fil**: {len(matched)} ({match_percentage:.1f}%)")
    report.append(f"- **Ej matchade**: {len(unmatched)} ({100-match_percentage:.1f}%)")

    if unmatched:
        # Count unique law names
        unique_unmatched = Counter([ref['law_name'] for ref in unmatched])
        report.append(f"- **Unika ej matchade lagnamn**: {len(unique_unmatched)}")
        report.append("")

        report.append("## Ej matchade lagnamn")
        report.append("")

        for law_name, count in unique_unmatched.most_common():
            report.append(f"### {law_name}")
            report.append(f"- **Antal förekomster**: {count}")
            report.append("- **Exempel**:")

            # Show up to 5 examples
            examples = [ref for ref in unmatched if ref['law_name'] == law_name][:5]
            for example in examples:
                report.append(
                    f"  - `{example['full_match']}` i `{os.path.basename(example['file'])}`")

            report.append("")
    else:
        report.append("")
        report.append("✅ **Alla lagnamn matchas korrekt mot JSON-filen!**")
        report.append("")

    # Statistics about available law names
    report.append("## Statistik om tillgängliga lagnamn")
    report.append("")
    report.append(f"- **Antal lagnamn i JSON-fil**: {len(law_lookup)}")

    if matched:
        used_laws = Counter([ref['law_name'] for ref in matched])
        report.append(f"- **Antal använda lagnamn**: {len(used_laws)}")
        report.append(f"- **Mest refererade lagnamn**:")
        for law_name, count in used_laws.most_common(10):
            sfs_id = law_lookup.get(law_name, "Okänt")
            report.append(f"  - {law_name} ({sfs_id}): {count} förekomster")

    return "\n".join(report)


def main():
    """Main function."""
    # Paths
    script_dir = Path(__file__).parent
    json_file = script_dir / "data" / "law-names.json"
    markdown_dir = script_dir / "../sfs-export"  # Use the full export directory

    # Alternative directories to check
    if not markdown_dir.exists():
        alternative_dirs = [
            script_dir / "sfs-export",
            script_dir / "sfs-test",
            script_dir
        ]
        for alt_dir in alternative_dirs:
            if alt_dir.exists() and list(alt_dir.rglob("*.md")):
                markdown_dir = alt_dir
                print(f"Använder katalog: {markdown_dir}")
                break

    if not markdown_dir.exists():
        print(f"Fel: Kunde inte hitta katalog med markdown-filer. Försökte: {markdown_dir}")
        return

    print("Laddar lagnamn från JSON-fil...")
    law_lookup, law_data = load_law_names(json_file)

    if not law_lookup:
        print("Fel: Kunde inte ladda lagnamn från JSON-fil")
        return

    print(f"Laddat {len(law_lookup)} lagnamn från JSON-fil")

    print("Skannar markdown-filer...")
    references = scan_markdown_files(markdown_dir)

    print(f"Hittade {len(references)} lagnamnsreferenser")

    print("Analyserar referenser...")
    matched, unmatched = analyze_references(references, law_lookup)

    print("Genererar rapport...")
    report = generate_report(matched, unmatched, law_lookup)

    # Write report to file
    report_file = script_dir / "lagnamn_validering_rapport.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"Rapport sparad till: {report_file}")

    # Print summary
    total_refs = len(matched) + len(unmatched)
    if total_refs > 0:
        match_percentage = len(matched) / total_refs * 100
        print(f"\nSammanfattning:")
        print(f"- Totalt: {total_refs} referenser")
        print(f"- Matchade: {len(matched)} ({match_percentage:.1f}%)")
        print(f"- Ej matchade: {len(unmatched)} ({100-match_percentage:.1f}%)")

        if unmatched:
            unique_unmatched = set(ref['law_name'] for ref in unmatched)
            print(f"- Unika ej matchade: {len(unique_unmatched)}")
            print("- Exempel på ej matchade:")
            for law_name in sorted(unique_unmatched)[:5]:
                print(f"  - {law_name}")


if __name__ == "__main__":
    main()
