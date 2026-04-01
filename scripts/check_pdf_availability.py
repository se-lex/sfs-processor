#!/usr/bin/env python3
"""
Script för att kontrollera tillgänglighet av PDF-filer från markdown-filer.
Extraherar pdf_url från frontmatter och kontrollerar om PDF:erna finns.
"""

import re
import yaml
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict


def extract_frontmatter(content: str) -> Optional[Dict]:
    """
    Extraherar front matter från markdown-innehåll.

    Args:
        content: Markdown-filens innehåll

    Returns:
        Dictionary med frontmatter eller None om ingen finns
    """
    frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n'
    match = re.match(frontmatter_pattern, content, re.DOTALL)

    if match:
        try:
            frontmatter_yaml = match.group(1)
            return yaml.safe_load(frontmatter_yaml) or {}
        except yaml.YAMLError as e:
            print(f"Fel vid parsing av YAML: {e}")
            return None
    return None


def check_pdf_exists(url: str, timeout: int = 10) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Kontrollerar om PDF-filen finns genom att göra en HEAD request.

    Args:
        url: URL till PDF-filen
        timeout: Timeout för request i sekunder

    Returns:
        Tuple: (exists, status_code, error_message)
    """
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        return (response.status_code == 200, response.status_code, None)
    except requests.exceptions.Timeout:
        return (False, None, "Timeout")
    except requests.exceptions.ConnectionError:
        return (False, None, "Connection Error")
    except requests.exceptions.RequestException as e:
        return (False, None, str(e))


def find_markdown_files(directory: Path, recursive: bool = True) -> List[Path]:
    """
    Hittar alla markdown-filer i en katalog.

    Args:
        directory: Katalog att söka i
        recursive: Om sökningen ska vara rekursiv

    Returns:
        Lista med sökvägar till markdown-filer
    """
    if not directory.exists():
        print(f"Katalogen {directory} finns inte")
        return []

    pattern = "**/*.md" if recursive else "*.md"
    return list(directory.glob(pattern))


def process_markdown_files(directory: Path, recursive: bool = True) -> Dict:
    """
    Bearbetar alla markdown-filer och kontrollerar PDF-tillgänglighet.

    Args:
        directory: Katalog att söka i
        recursive: Om sökningen ska vara rekursiv

    Returns:
        Dictionary med resultat
    """
    md_files = find_markdown_files(directory, recursive)

    if not md_files:
        print(f"Inga markdown-filer hittades i {directory}")
        return {
            'total_files': 0,
            'files_with_pdf_url': 0,
            'available_pdfs': 0,
            'unavailable_pdfs': 0,
            'results': []
        }

    print(f"Hittade {len(md_files)} markdown-filer")
    print(f"Kontrollerar PDF-tillgänglighet...")

    results = []
    stats = {
        'total_files': len(md_files),
        'files_with_pdf_url': 0,
        'available_pdfs': 0,
        'unavailable_pdfs': 0,
        'by_status': defaultdict(int),
        'by_database': {'old': 0, 'new': 0}
    }

    for i, md_file in enumerate(md_files, 1):
        if i % 100 == 0:
            print(f"Bearbetat {i}/{len(md_files)} filer...")

        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()

            frontmatter = extract_frontmatter(content)
            if not frontmatter:
                continue

            pdf_url = frontmatter.get('pdf_url')
            if not pdf_url:
                continue

            stats['files_with_pdf_url'] += 1

            beteckning = frontmatter.get('beteckning', 'Unknown')
            rubrik = frontmatter.get('rubrik', '')

            # Avgör vilken databas baserat på URL
            database = 'old' if 'rkrattsdb.gov.se' in pdf_url else 'new'
            stats['by_database'][database] += 1

            # Kontrollera om PDF:en finns
            exists, status_code, error_msg = check_pdf_exists(pdf_url)

            result = {
                'file': str(md_file.relative_to(directory)),
                'beteckning': beteckning,
                'rubrik': rubrik,
                'pdf_url': pdf_url,
                'database': database,
                'exists': exists,
                'status_code': status_code,
                'error': error_msg
            }

            results.append(result)

            if exists:
                stats['available_pdfs'] += 1
            else:
                stats['unavailable_pdfs'] += 1

            # Räkna status codes
            if status_code:
                stats['by_status'][status_code] += 1
            elif error_msg:
                stats['by_status'][error_msg] += 1

        except Exception as e:
            print(f"Fel vid bearbetning av {md_file}: {e}")
            continue

    stats['results'] = results
    return stats


def generate_markdown_report(stats: Dict, output_file: Path):
    """
    Genererar en Markdown-rapport med resultat.

    Args:
        stats: Dictionary med statistik och resultat
        output_file: Sökväg till output-filen
    """
    report = []

    # Header
    report.append("# PDF-tillgänglighetsrapport")
    report.append(f"\nGenererad: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Sammanfattning
    report.append("## Sammanfattning\n")
    report.append(f"- **Totalt antal markdown-filer:** {stats['total_files']}")
    report.append(f"- **Filer med pdf_url:** {stats['files_with_pdf_url']}")
    report.append(f"- **Tillgängliga PDF:er:** {stats['available_pdfs']} ({stats['available_pdfs']/max(stats['files_with_pdf_url'],1)*100:.1f}%)")
    report.append(f"- **Otillgängliga PDF:er:** {stats['unavailable_pdfs']} ({stats['unavailable_pdfs']/max(stats['files_with_pdf_url'],1)*100:.1f}%)")

    # Databas-fördelning
    report.append("\n## Fördelning per databas\n")
    report.append(f"- **Gamla databasen (rkrattsdb.gov.se):** {stats['by_database']['old']}")
    report.append(f"- **Nya databasen (svenskforfattningssamling.se):** {stats['by_database']['new']}")

    # Status code-fördelning
    if stats['by_status']:
        report.append("\n## Status code-fördelning\n")
        for status, count in sorted(stats['by_status'].items()):
            report.append(f"- **{status}:** {count}")

    # Otillgängliga PDF:er
    unavailable = [r for r in stats['results'] if not r['exists']]
    if unavailable:
        report.append(f"\n## Otillgängliga PDF:er ({len(unavailable)})\n")

        # Gruppera per databas
        old_db_unavailable = [r for r in unavailable if r['database'] == 'old']
        new_db_unavailable = [r for r in unavailable if r['database'] == 'new']

        if old_db_unavailable:
            report.append(f"### Gamla databasen ({len(old_db_unavailable)})\n")
            for result in old_db_unavailable:
                status_info = result['status_code'] if result['status_code'] else result['error']
                report.append(f"- **{result['beteckning']}** - {result['rubrik'][:80]}")
                report.append(f"  - Status: {status_info}")
                report.append(f"  - URL: {result['pdf_url']}")
                report.append("")

        if new_db_unavailable:
            report.append(f"### Nya databasen ({len(new_db_unavailable)})\n")
            for result in new_db_unavailable:
                status_info = result['status_code'] if result['status_code'] else result['error']
                report.append(f"- **{result['beteckning']}** - {result['rubrik'][:80]}")
                report.append(f"  - Status: {status_info}")
                report.append(f"  - URL: {result['pdf_url']}")
                report.append("")

    # Tillgängliga PDF:er (urval)
    available = [r for r in stats['results'] if r['exists']]
    if available:
        report.append(f"\n## Tillgängliga PDF:er (urval)\n")
        report.append(f"Visar de första 10 av {len(available)} tillgängliga PDF:er:\n")
        for result in available[:10]:
            report.append(f"- **{result['beteckning']}** - {result['rubrik'][:80]}")
            report.append(f"  - URL: {result['pdf_url']}")
            report.append("")

    # Skriv rapport
    report_content = '\n'.join(report)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report_content)

    print(f"\nRapport skapad: {output_file}")


def main():
    """Huvudfunktion."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Kontrollera tillgänglighet av PDF-filer från markdown-filer"
    )
    parser.add_argument(
        "directory",
        help="Katalog som innehåller markdown-filerna"
    )
    parser.add_argument(
        "-o", "--output",
        default="reports/pdf_availability_report.md",
        help="Output-fil för rapporten (default: reports/pdf_availability_report.md)"
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Sök inte rekursivt i undermappar"
    )

    args = parser.parse_args()

    directory = Path(args.directory)
    output_file = Path(args.output)
    recursive = not args.no_recursive

    # Skapa output-katalog om den inte finns
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"Söker efter markdown-filer i: {directory}")
    print(f"Rekursivt: {'Ja' if recursive else 'Nej'}")

    # Bearbeta filer
    stats = process_markdown_files(directory, recursive)

    # Generera rapport
    if stats['files_with_pdf_url'] > 0:
        generate_markdown_report(stats, output_file)
        print(f"\n✓ Klart!")
    else:
        print("\nInga filer med pdf_url hittades.")


if __name__ == "__main__":
    main()
