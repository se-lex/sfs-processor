#!/usr/bin/env python3
"""
Batch export SFS documents to Git repository with initial commits and temporal commits.

This script automates the process of:
1. Creating initial commits for base documents (using utfardad_datum)
2. Creating temporal commits for upcoming changes (using ikraft_datum and upphor_datum)

Usage:
    python batch_export_to_git.py --years 2024-2026 --branch batch-2025-12-28
    python batch_export_to_git.py --filter 2024:1000,2025:500 --branch my-branch
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime

from exporters.git import process_files_with_git_batch, process_temporal_commits_batch
from util.file_utils import filter_json_files


def parse_year_range(year_range: str) -> list[str]:
    """
    Parse year range string and return list of years.

    Args:
        year_range: Year range in format "YYYY-YYYY" or single year "YYYY"

    Returns:
        List of year strings

    Examples:
        "2024-2026" -> ["2024", "2025", "2026"]
        "2024" -> ["2024"]
    """
    if '-' in year_range:
        start_year, end_year = year_range.split('-')
        start = int(start_year)
        end = int(end_year)
        if start > end:
            raise ValueError(f"Start year {start} cannot be greater than end year {end}")
        return [str(year) for year in range(start, end + 1)]
    else:
        return [year_range]


def year_range_to_date_range(year_range: str) -> tuple[str, str]:
    """
    Convert year range to date range for temporal commit filtering.

    Args:
        year_range: Year range in format "YYYY-YYYY" or single year "YYYY"

    Returns:
        Tuple of (from_date, to_date) in YYYY-MM-DD format

    Examples:
        "2024-2026" -> ("2024-01-01", "2026-12-31")
        "2024" -> ("2024-01-01", "2024-12-31")
    """
    if '-' in year_range:
        start_year, end_year = year_range.split('-')
        return (f"{start_year}-01-01", f"{end_year}-12-31")
    else:
        return (f"{year_range}-01-01", f"{year_range}-12-31")


def main():
    parser = argparse.ArgumentParser(
        description='Batch export SFS documents to Git repository with initial and temporal commits.'
    )
    parser.add_argument(
        '--years',
        help='Year range to export (e.g., "2024-2026" or "2024"). Filters both documents and temporal commits (ikraft/upphör dates) to this period.'
    )
    parser.add_argument(
        '--filter',
        help='Filter files by year (YYYY) or specific beteckning (YYYY:NNN). Can be comma-separated list.'
    )
    parser.add_argument(
        '--branch',
        required=True,
        help='Git branch name to use for commits (e.g., "batch-2025-12-28")'
    )
    parser.add_argument(
        '--input',
        '-i',
        help='Input directory containing JSON files (default: ../sfs-jsondata)'
    )
    parser.add_argument(
        '--output',
        '-o',
        help='Output directory for processed files (default: ../sfs-export-git)'
    )
    parser.add_argument(
        '--markers-dir',
        help='Directory containing markdown files with markers for temporal commits (default: ../sfs-export-md-markers)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed output'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Number of files to process per batch (default: 100)'
    )
    parser.add_argument(
        '--skip-initial',
        action='store_true',
        help='Skip initial commits (only do temporal commits)'
    )
    parser.add_argument(
        '--skip-temporal',
        action='store_true',
        help='Skip temporal commits (only do initial commits)'
    )

    args = parser.parse_args()

    # Validate arguments
    if args.skip_initial and args.skip_temporal:
        print("Fel: Kan inte skippa både initial och temporal commits")
        return 1

    # Define paths
    script_dir = Path(__file__).parent

    # Input directory
    if args.input:
        json_dir = Path(args.input)
    else:
        json_dir = script_dir.parent / 'sfs-jsondata'

    # Output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = script_dir.parent / 'sfs-export-git'

    # Markers directory for temporal commits
    if args.markers_dir:
        markers_dir = Path(args.markers_dir)
    else:
        markers_dir = script_dir.parent / 'sfs-export-md-markers'

    # Create output directory if needed
    output_dir.mkdir(exist_ok=True)

    # Check if json directory exists
    if not json_dir.exists():
        print(f"Fel: JSON-katalog {json_dir} finns inte")
        return 1

    # Find all JSON files
    json_files = list(json_dir.glob('*.json'))

    if not json_files:
        print(f"Inga JSON-filer hittades i {json_dir}")
        return 1

    # Apply filter
    filter_str = None
    if args.years:
        # Convert year range to filter string
        years = parse_year_range(args.years)
        filter_str = ','.join(years)
        print(f"Filtrerar för åren: {', '.join(years)}")
    elif args.filter:
        filter_str = args.filter

    if filter_str:
        original_count = len(json_files)
        json_files = filter_json_files(json_files, filter_str)
        print(f"Filter '{filter_str}' tillämpad: {len(json_files)} av {original_count} filer valda")

        if not json_files:
            print("Inga filer matchar filterkriterier")
            return 1

    print(f"\n{'='*80}")
    print(f"BATCH EXPORT TILL GIT")
    print(f"{'='*80}")
    print(f"JSON-katalog: {json_dir}")
    print(f"Utdata-katalog: {output_dir}")
    print(f"Markers-katalog: {markers_dir}")
    print(f"Branch: {args.branch}")
    print(f"Antal filer: {len(json_files)}")
    print(f"Batch-storlek: {args.batch_size}")
    print(f"{'='*80}\n")

    # Step 1: Create initial commits (if not skipped)
    if not args.skip_initial:
        print("\n" + "="*80)
        print("STEG 1: SKAPAR INITIALA COMMITS")
        print("="*80 + "\n")

        try:
            process_files_with_git_batch(
                json_files=json_files,
                output_dir=output_dir,
                verbose=args.verbose,
                fetch_predocs_from_api=False,  # Don't fetch from API for batch processing
                batch_size=args.batch_size,
                branch_name=args.branch
            )
            print("\n✅ Initiala commits skapade och pushade")
        except Exception as e:
            print(f"\n❌ Fel vid skapande av initiala commits: {e}")
            return 1
    else:
        print("\n⏭️  Hoppar över initiala commits (--skip-initial)")

    # Step 2: Create temporal commits (if not skipped)
    if not args.skip_temporal:
        print("\n" + "="*80)
        print("STEG 2: SKAPAR TEMPORAL COMMITS (UPCOMING CHANGES)")
        print("="*80 + "\n")

        # Check if markers directory exists
        if not markers_dir.exists():
            print(f"Varning: Markers-katalogen {markers_dir} finns inte")
            print("Temporal commits kräver markdown-filer med selex-markers")
            print("Kör först: python sfs_processor.py --formats md-markers")
            return 1

        # Calculate date range for temporal commits based on year filter
        temporal_from_date = None
        temporal_to_date = None
        if args.years:
            temporal_from_date, temporal_to_date = year_range_to_date_range(args.years)
            print(f"Filtrerar temporal commits för perioden: {temporal_from_date} till {temporal_to_date}")

        try:
            process_temporal_commits_batch(
                markdown_dir=markers_dir,
                from_date=temporal_from_date,
                to_date=temporal_to_date,
                dry_run=False,
                verbose=args.verbose,
                batch_size=args.batch_size,
                branch_name=args.branch  # Use same branch as initial commits
            )
            print("\n✅ Temporal commits skapade och pushade")
        except Exception as e:
            print(f"\n❌ Fel vid skapande av temporal commits: {e}")
            return 1
    else:
        print("\n⏭️  Hoppar över temporal commits (--skip-temporal)")

    # Summary
    print("\n" + "="*80)
    print("✅ BATCH EXPORT KLAR!")
    print("="*80)
    print(f"Branch: {args.branch}")
    print(f"Antal filer bearbetade: {len(json_files)}")
    print("\nNästa steg:")
    print(f"1. Gå till target repository och skapa en Pull Request från branch '{args.branch}'")
    print(f"2. Granska ändringarna och merga till main")
    print("="*80 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
