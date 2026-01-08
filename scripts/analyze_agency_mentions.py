#!/usr/bin/env python3
"""
Analyze mentions of Swedish government agencies in Markdown files.

Generates a report with:
- Top list of most mentioned agencies
- Total mention counts
- Examples of mentions per agency
"""

import json
import re
import argparse
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Add parent directory to path to import formatters
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from formatters.apply_agency_links import _load_agency_data, get_all_agencies


def analyze_agency_mentions(input_dir: Path, output_file: Path, limit: int = 50):
    """
    Analyze agency mentions in all markdown files and generate a report.

    Args:
        input_dir: Directory containing markdown files
        output_file: Path to output markdown report
        limit: Number of top agencies to include in detailed report
    """
    # Load agency data
    agency_data = _load_agency_data()

    if not agency_data['patterns']:
        print("ERROR: Could not load agency data")
        return

    # Find all markdown files
    md_files = list(input_dir.rglob("*.md"))
    print(f"Found {len(md_files)} markdown files to analyze")

    if not md_files:
        print(f"No markdown files found in {input_dir}")
        return

    # Track mentions: agency_name -> [(file, line_content), ...]
    mentions = defaultdict(list)
    total_mentions = 0

    for i, file_path in enumerate(md_files):
        if i % 100 == 0:
            print(f"Processing file {i+1}/{len(md_files)}: {file_path.name}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Analyze each pattern
            for pattern, agency_info in agency_data['patterns']:
                agency_name = agency_info['name']

                for match in pattern.finditer(content):
                    matched_text = match.group(0)
                    start = match.start()

                    # Get line context
                    line_start = content.rfind('\n', 0, start) + 1
                    line_end = content.find('\n', start)
                    if line_end == -1:
                        line_end = len(content)
                    line_content = content[line_start:line_end].strip()

                    # Skip if inside markdown link (already linked)
                    if _is_inside_link(content, start, match.end()):
                        continue

                    # Skip headings
                    if line_content.startswith('#'):
                        continue

                    mentions[agency_name].append({
                        'file': str(file_path.relative_to(input_dir)),
                        'matched_text': matched_text,
                        'line': line_content[:200]  # Truncate long lines
                    })
                    total_mentions += 1

        except Exception as e:
            print(f"ERROR reading {file_path}: {e}")
            continue

    # Generate report
    generate_report(mentions, output_file, total_mentions, len(md_files), limit)


def _is_inside_link(text: str, start: int, end: int) -> bool:
    """Check if position is inside an existing markdown link."""
    bracket_start = text.rfind('[', 0, start)
    if bracket_start != -1:
        bracket_end = text.find(']', bracket_start)
        if bracket_end != -1 and bracket_end >= end:
            if bracket_end + 1 < len(text) and text[bracket_end + 1] == '(':
                return True
    return False


def generate_report(mentions: dict, output_file: Path, total_mentions: int,
                   file_count: int, limit: int):
    """Generate the markdown report."""

    # Sort agencies by mention count
    sorted_agencies = sorted(mentions.items(), key=lambda x: len(x[1]), reverse=True)

    # Get all agencies for statistics
    all_agencies = get_all_agencies()

    report = []
    report.append("# Rapport: Myndighetsnamn i Markdown-filer")
    report.append("")
    report.append(f"*Genererad: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    report.append("")
    report.append("## Sammanfattning")
    report.append("")
    report.append(f"- **Totalt antal Markdown-filer analyserade**: {file_count:,}")
    report.append(f"- **Totalt antal myndighetsnamn i databasen**: {len(all_agencies)}")
    report.append(f"- **Totalt antal omnämnanden hittade**: {total_mentions:,}")
    report.append(f"- **Unika myndigheter omnämnda**: {len(mentions)}")
    report.append("")

    # Top 20 summary
    report.append("## Topp 20 mest omnämnda myndigheter")
    report.append("")
    report.append("| Rang | Myndighet | Antal omnämnanden |")
    report.append("|------|-----------|-------------------|")

    for i, (agency_name, agency_mentions) in enumerate(sorted_agencies[:20], 1):
        report.append(f"| {i} | {agency_name} | {len(agency_mentions):,} |")

    report.append("")

    # Detailed section for top agencies
    report.append(f"## Detaljerad lista (topp {limit})")
    report.append("")

    for agency_name, agency_mentions in sorted_agencies[:limit]:
        report.append(f"### {agency_name}")
        report.append(f"- **Antal omnämnanden**: {len(agency_mentions):,}")
        report.append("")

        # Show examples (max 5)
        examples = agency_mentions[:5]
        if examples:
            report.append("**Exempel:**")
            for ex in examples:
                # Escape special characters
                line = ex['line'].replace('|', '\\|')
                report.append(f"- `{ex['matched_text']}` i `{ex['file']}`")
            report.append("")

    # Summary statistics
    report.append("## Statistik")
    report.append("")

    if sorted_agencies:
        top_10_mentions = sum(len(m) for _, m in sorted_agencies[:10])
        report.append(f"- **Topp 10 myndigheter står för**: {top_10_mentions:,} omnämnanden ({100*top_10_mentions/total_mentions:.1f}%)")

        # Agencies with only 1 mention
        single_mentions = len([a for a, m in sorted_agencies if len(m) == 1])
        report.append(f"- **Myndigheter med endast 1 omnämnande**: {single_mentions}")

        # Average mentions per mentioned agency
        avg_mentions = total_mentions / len(mentions) if mentions else 0
        report.append(f"- **Genomsnittligt antal omnämnanden per myndighet**: {avg_mentions:.1f}")

    # Save report
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))

    print(f"\nReport saved to: {output_file}")
    print(f"Total mentions: {total_mentions:,}")
    print(f"Unique agencies mentioned: {len(mentions)}")


def main():
    parser = argparse.ArgumentParser(
        description='Analyze government agency mentions in Markdown files'
    )
    parser.add_argument(
        '--input', '-i',
        type=Path,
        default=Path('.'),
        help='Input directory containing markdown files (default: current directory)'
    )
    parser.add_argument(
        '--output', '-o',
        type=Path,
        default=Path('data/reports/myndigheter_rapport.md'),
        help='Output report file path (default: data/reports/myndigheter_rapport.md)'
    )
    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=50,
        help='Number of top agencies to include in detailed report (default: 50)'
    )

    args = parser.parse_args()

    analyze_agency_mentions(args.input, args.output, args.limit)


if __name__ == "__main__":
    main()
