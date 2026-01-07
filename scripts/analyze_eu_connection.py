#!/usr/bin/env python3
"""
Analysera koppling till EU-lagstiftning i SFS-dokument.

Detta script analyserar hur mycket svensk lagstiftning som är kopplad till EU-dokument genom:
1. Metadata: CELEX-nummer och EU-direktiv flaggor
2. Textinnehåll: Referenser till EU-förordningar, direktiv och dokument
"""

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional


def format_beteckning_as_link(
    beteckning: str, base_url: str = "https://selex.se"
) -> str:
    """
    Formatera beteckning som klickbar länk till selex.se.

    Args:
        beteckning: SFS-beteckning (format: YYYY:NNN)
        base_url: Bas-URL för länkar (default: https://selex.se)

    Returns:
        str: Markdown-länk till dokumentet
    """
    if ':' not in beteckning:
        return beteckning

    try:
        year, number = beteckning.split(':', 1)
        # ELI-struktur: /eli/sfs/{year}/{number}
        url = f"{base_url}/eli/sfs/{year}/{number}"
        return f"[{beteckning}]({url})"
    except Exception:
        return beteckning


class EUReference:
    """Representerar en referens till ett EU-dokument."""

    def __init__(self, ref_type: str, text: str, context: str = ""):
        self.ref_type = ref_type  # 'forordning', 'direktiv', 'celex', etc.
        self.text = text
        self.context = context

    def __repr__(self):
        return f"EUReference({self.ref_type}, {self.text[:50]}...)"


def extract_eu_references_from_text(text: str) -> list[EUReference]:
    """
    Extrahera EU-referenser från författningstext.

    Letar efter:
    - Förordningar: "förordning (EU) YYYY/NNNN"
    - Direktiv: "direktiv (EU) YYYY/NNNN"
    - CELEX-nummer: format som "32023R2831"
    - EUR-Lex länkar
    - "Europaparlamentets och rådets förordning/direktiv"
    - "kommissionens förordning/direktiv"
    """
    references = []

    if not text:
        return references

    # Pattern 1: Förordning (EU) YYYY/NNNN eller (EU) nr NNNN/YYYY
    forordning_patterns = [
        r'förordning(?:en)?\s+\(EU\)\s+(?:nr\s+)?(\d{4}/\d+|\d+/\d{4})',
        r'förordning(?:en)?\s+\(EG\)\s+(?:nr\s+)?(\d{4}/\d+|\d+/\d{4})',
        r'förordning(?:en)?\s+\(EEG\)\s+(?:nr\s+)?(\d{4}/\d+|\d+/\d{4})',
    ]

    for pattern in forordning_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            context_start = max(0, match.start() - 50)
            context_end = min(len(text), match.end() + 50)
            context = text[context_start:context_end]
            references.append(EUReference('förordning', match.group(0), context))

    # Pattern 2: Direktiv (EU) YYYY/NNNN
    direktiv_patterns = [
        r'direktiv(?:et)?\s+\(EU\)\s+(?:nr\s+)?(\d{4}/\d+|\d+/\d{4})',
        r'direktiv(?:et)?\s+\(EG\)\s+(?:nr\s+)?(\d{4}/\d+|\d+/\d{4})',
        r'direktiv(?:et)?\s+\(EEG\)\s+(?:nr\s+)?(\d{4}/\d+|\d+/\d{4})',
    ]

    for pattern in direktiv_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            context_start = max(0, match.start() - 50)
            context_end = min(len(text), match.end() + 50)
            context = text[context_start:context_end]
            references.append(EUReference('direktiv', match.group(0), context))

    # Pattern 3: CELEX-nummer (format: 32023R2831, 32023L0970, etc.)
    celex_pattern = r'\b[1-9]\d{4}[LRDCKE]\d{4}\b'
    for match in re.finditer(celex_pattern, text):
        context_start = max(0, match.start() - 50)
        context_end = min(len(text), match.end() + 50)
        context = text[context_start:context_end]
        references.append(EUReference('celex', match.group(0), context))

    # Pattern 4: EUR-Lex länkar
    eurlex_pattern = r'eur-lex\.europa\.eu/[^\s]+'
    for match in re.finditer(eurlex_pattern, text, re.IGNORECASE):
        references.append(EUReference('eurlex_url', match.group(0)))

    # Pattern 5: "Europaparlamentets och rådets" (indikerar EU-dokument)
    if re.search(r'Europaparlamentets\s+och\s+rådets', text, re.IGNORECASE):
        pattern = r'Europaparlamentets\s+och\s+rådets\s+(förordning|direktiv)'
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        for match in matches[:3]:  # Max 3 exempel per dokument
            context_start = max(0, match.start() - 30)
            context_end = min(len(text), match.end() + 80)
            context = text[context_start:context_end]
            references.append(EUReference('eu_institution', match.group(0), context))

    # Pattern 6: "kommissionens förordning/direktiv"
    if re.search(r'kommissionens\s+(förordning|direktiv)', text, re.IGNORECASE):
        pattern = r'kommissionens\s+(förordning|direktiv)\s+\([^)]+\)\s+[^\r\n]{0,100}'
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        for match in matches[:3]:  # Max 3 exempel per dokument
            context = match.group(0)
            references.append(EUReference('kommissionen', match.group(0), context))

    return references


def analyze_sfs_document(
    json_file: Path, year_range: Optional[tuple[int, int]] = None
) -> Optional[dict]:
    """
    Analysera ett enskilt SFS-dokument för EU-kopplingar.

    Args:
        json_file: Path till JSON-filen
        year_range: Tuple med (min_år, max_år) för filtrering, eller None för alla år

    Returns:
        Dict med analysresultat, eller None om dokumentet filtrerades bort
    """
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return {
            'error': str(e),
            'file': str(json_file)
        }

    beteckning = data.get('beteckning', 'unknown')
    rubrik = data.get('rubrik', '')

    # Filtrera på årsspann om angivet
    if year_range:
        min_year, max_year = year_range
        # Extrahera år från beteckning (format: YYYY:NNN)
        year_match = re.match(r'(\d{4}):', beteckning)
        if year_match:
            year = int(year_match.group(1))
            if year < min_year or year > max_year:
                return None  # Filtrera bort detta dokument

    # Metadata-analys
    register = data.get('register', {})
    eu_direktiv = register.get('eUdirektiv', False)
    celexnummer = register.get('celexnummer')

    # Text-analys
    fulltext = data.get('fulltext', {})
    forfattningstext = fulltext.get('forfattningstext', '')

    text_references = extract_eu_references_from_text(forfattningstext)

    # Räkna olika typer av referenser
    ref_counts = Counter([ref.ref_type for ref in text_references])

    has_eu_connection = (
        eu_direktiv or
        celexnummer is not None or
        len(text_references) > 0
    )

    return {
        'beteckning': beteckning,
        'rubrik': rubrik,
        'file': str(json_file),
        'metadata': {
            'eu_direktiv': eu_direktiv,
            'celexnummer': celexnummer,
        },
        'text_references': text_references,
        'ref_counts': dict(ref_counts),
        'total_references': len(text_references),
        'has_eu_connection': has_eu_connection,
    }


def generate_report(
    results: list[dict], output_path: Optional[Path] = None
) -> str:
    """
    Generera en rapport över EU-kopplingarna.
    """
    total_docs = len(results)
    docs_with_errors = [r for r in results if 'error' in r]
    valid_results = [r for r in results if 'error' not in r]

    docs_with_eu = [r for r in valid_results if r['has_eu_connection']]
    docs_with_metadata = [r for r in valid_results if r['metadata']['eu_direktiv'] or r['metadata']['celexnummer']]
    docs_with_text_refs = [r for r in valid_results if r['total_references'] > 0]

    # Samla statistik om referenstyper
    all_ref_types = Counter()
    for result in valid_results:
        for ref_type, count in result['ref_counts'].items():
            all_ref_types[ref_type] += count

    # Bygg rapport
    report_lines = []
    report_lines.append("# Analys av EU-koppling i SFS-dokument")
    report_lines.append("")
    report_lines.append(f"**Genererad:** {Path(__file__).name}")
    report_lines.append("")

    # Översikt
    report_lines.append("## Översikt")
    report_lines.append("")
    report_lines.append(f"- **Totalt antal dokument:** {total_docs}")
    report_lines.append(f"- **Dokument med EU-koppling:** {len(docs_with_eu)} ({len(docs_with_eu)/len(valid_results)*100:.1f}%)")
    report_lines.append(f"- **Dokument med metadata-koppling:** {len(docs_with_metadata)} ({len(docs_with_metadata)/len(valid_results)*100:.1f}%)")
    report_lines.append(f"- **Dokument med textreferenser:** {len(docs_with_text_refs)} ({len(docs_with_text_refs)/len(valid_results)*100:.1f}%)")
    report_lines.append("")

    # Metadata-statistik
    report_lines.append("## Metadata-koppling")
    report_lines.append("")
    eu_direktiv_count = sum(1 for r in valid_results if r['metadata']['eu_direktiv'])
    celex_count = sum(1 for r in valid_results if r['metadata']['celexnummer'] is not None)

    report_lines.append(f"- **EU-direktiv flagga:** {eu_direktiv_count} dokument")
    report_lines.append(f"- **CELEX-nummer angivet:** {celex_count} dokument")
    report_lines.append("")

    # Visa exempel på dokument med CELEX-nummer
    docs_with_celex = [r for r in valid_results if r['metadata']['celexnummer']]
    if docs_with_celex:
        report_lines.append("### Exempel på dokument med CELEX-nummer:")
        report_lines.append("")
        for result in docs_with_celex[:10]:
            celex = result['metadata']['celexnummer']
            beteckning_link = format_beteckning_as_link(result['beteckning'])
            report_lines.append(f"- **{beteckning_link}**: {celex}")
            report_lines.append(f"  _{result['rubrik'][:100]}_")
        if len(docs_with_celex) > 10:
            report_lines.append(f"- ... och {len(docs_with_celex) - 10} dokument till")
        report_lines.append("")

    # Textreferens-statistik
    report_lines.append("## Textreferenser")
    report_lines.append("")
    report_lines.append(f"- **Totalt antal referenser:** {sum(all_ref_types.values())}")
    report_lines.append("")
    report_lines.append("### Fördelning per typ:")
    report_lines.append("")
    for ref_type, count in all_ref_types.most_common():
        report_lines.append(f"- **{ref_type}**: {count} referenser")
    report_lines.append("")

    # Top 20 dokument med flest referenser
    docs_by_refs = sorted([r for r in valid_results if r['total_references'] > 0],
                          key=lambda x: x['total_references'], reverse=True)

    if docs_by_refs:
        report_lines.append("## Top 20 dokument med flest EU-referenser")
        report_lines.append("")
        for i, result in enumerate(docs_by_refs[:20], 1):
            beteckning_link = format_beteckning_as_link(result['beteckning'])
            report_lines.append(f"{i}. **{beteckning_link}** - {result['total_references']} referenser")
            report_lines.append(f"   _{result['rubrik'][:100]}_")

            # Visa fördelning av referenstyper
            ref_types = ', '.join([f"{k}: {v}" for k, v in result['ref_counts'].items()])
            report_lines.append(f"   Typer: {ref_types}")
            report_lines.append("")

    # Exempel på specifika referenser
    report_lines.append("## Exempel på EU-referenser i text")
    report_lines.append("")

    # Gruppera exempel per typ
    examples_by_type = defaultdict(list)
    for result in valid_results:
        for ref in result['text_references']:
            if len(examples_by_type[ref.ref_type]) < 5:  # Max 5 exempel per typ
                examples_by_type[ref.ref_type].append({
                    'beteckning': result['beteckning'],
                    'text': ref.text,
                    'context': ref.context
                })

    for ref_type in ['förordning', 'direktiv', 'kommissionen', 'eu_institution']:
        if ref_type in examples_by_type:
            report_lines.append(f"### {ref_type.title()}-referenser")
            report_lines.append("")
            for example in examples_by_type[ref_type]:
                beteckning_link = format_beteckning_as_link(example['beteckning'])
                report_lines.append(f"- **{beteckning_link}**")
                if example['context']:
                    report_lines.append(f"  > ...{example['context']}...")
                else:
                    report_lines.append(f"  > {example['text']}")
                report_lines.append("")

    # Felrapportering
    if docs_with_errors:
        report_lines.append("## Fel vid bearbetning")
        report_lines.append("")
        report_lines.append(f"**Antal fel:** {len(docs_with_errors)}")
        report_lines.append("")
        for error in docs_with_errors[:10]:
            report_lines.append(f"- {error['file']}: {error['error']}")
        if len(docs_with_errors) > 10:
            report_lines.append(f"- ... och {len(docs_with_errors) - 10} fel till")
        report_lines.append("")

    report_text = '\n'.join(report_lines)

    # Spara rapport om path angivet
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, encoding='utf-8', mode='w') as f:
            f.write(report_text)
        print(f"\n✓ Rapport sparad till: {output_path}")

    return report_text


def main():
    parser = argparse.ArgumentParser(
        description='Analysera EU-koppling i SFS-dokument',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exempel:
  # Analysera testdokument
  python scripts/analyze_eu_connection.py --input data/testdocs/rkrattsbaser

  # Analysera alla SFS-dokument
  python scripts/analyze_eu_connection.py --input sfs_json

  # Spara rapport till fil
  python scripts/analyze_eu_connection.py --input sfs_json --output reports/eu_analysis.md

  # Begränsa antal dokument (för test)
  python scripts/analyze_eu_connection.py --input sfs_json --limit 1000

  # Filtrera på årsspann (senaste 10 åren)
  python scripts/analyze_eu_connection.py --input ../sfs-jsondata --year-range 2015-2025 --output reports/eu_analysis_2015-2025.md
        """
    )

    parser.add_argument(
        '--input',
        default='data/testdocs/rkrattsbaser',
        help='Katalog med SFS JSON-filer (default: data/testdocs/rkrattsbaser)'
    )

    parser.add_argument(
        '--output',
        help='Output-fil för rapporten (default: skriver till stdout)'
    )

    parser.add_argument(
        '--limit',
        type=int,
        help='Begränsa antal dokument att analysera (för test)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Visa detaljerad information under bearbetning'
    )

    parser.add_argument(
        '--year-range',
        help='Filtrera på årsspann (format: YYYY-YYYY, t.ex. 2015-2025)'
    )

    args = parser.parse_args()

    input_dir = Path(args.input)

    if not input_dir.exists():
        print(f"❌ Input-katalog finns inte: {input_dir}")
        return 1

    # Parsa year-range om angivet
    year_range = None
    if args.year_range:
        try:
            parts = args.year_range.split('-')
            if len(parts) != 2:
                print(f"❌ Ogiltigt årsspann format: {args.year_range}. Använd format YYYY-YYYY")
                return 1
            min_year = int(parts[0])
            max_year = int(parts[1])
            year_range = (min_year, max_year)
            print(f"📅 Filtrerar på årsspann: {min_year}-{max_year}")
        except ValueError:
            print(f"❌ Ogiltigt årsspann format: {args.year_range}")
            return 1

    # Hitta alla JSON-filer
    json_files = list(input_dir.glob('**/*.json'))

    if args.limit:
        json_files = json_files[:args.limit]

    print(f"📊 Analyserar {len(json_files)} SFS-dokument för EU-koppling...")
    print()

    results = []

    for i, json_file in enumerate(json_files, 1):
        if args.verbose and i % 100 == 0:
            print(f"  Bearbetar dokument {i}/{len(json_files)}...")

        result = analyze_sfs_document(json_file, year_range)
        if result is not None:  # None betyder filtrerad bort
            results.append(result)

    print(f"✓ Analyserade {len(results)} dokument")
    print()

    # Generera rapport
    output_path = Path(args.output) if args.output else None
    report = generate_report(results, output_path)

    # Skriv till stdout om ingen output-fil angavs
    if not output_path:
        print(report)

    # Snabb sammanfattning
    valid_results = [r for r in results if 'error' not in r]
    docs_with_eu = [r for r in valid_results if r['has_eu_connection']]

    print()
    print("=" * 70)
    print("SAMMANFATTNING")
    print("=" * 70)
    print(f"Totalt antal dokument:       {len(valid_results)}")
    print(f"Dokument med EU-koppling:    {len(docs_with_eu)} ({len(docs_with_eu)/len(valid_results)*100:.1f}%)")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    exit(main())
