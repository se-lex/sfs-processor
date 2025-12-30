#!/usr/bin/env python3
"""
Script to process temporal commits in batch mode with git operations.

This script processes markdown files with temporal changes and creates git commits
on the appropriate dates. It can run in dry-run mode for preview or create actual
commits and push to a target repository.
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to Python path so we can import from exporters
sys.path.insert(0, str(Path(__file__).parent.parent))

from exporters.git import process_temporal_commits_batch


def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(
        description='Bearbeta temporal commits i batch-läge med git-operationer.'
    )
    parser.add_argument(
        'markdown_dir',
        help='Sökväg till katalog med markdown-filer att bearbeta'
    )
    parser.add_argument(
        '--from-date',
        help='Startdatum (inklusivt) i formatet YYYY-MM-DD'
    )
    parser.add_argument(
        '--to-date',
        help='Slutdatum (inklusivt) i formatet YYYY-MM-DD'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Visa planerade commits utan att utföra dem'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Visa detaljerad information om bearbetningen'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Antal filer att bearbeta per batch (default: 100)'
    )
    
    args = parser.parse_args()
    
    markdown_dir = Path(args.markdown_dir)
    
    if not markdown_dir.exists():
        print(f"Fel: Katalogen {markdown_dir} finns inte")
        return 1
    
    try:
        process_temporal_commits_batch(
            markdown_dir=markdown_dir,
            from_date=args.from_date,
            to_date=args.to_date,
            dry_run=args.dry_run,
            verbose=args.verbose,
            batch_size=args.batch_size
        )
        return 0
    except Exception as e:
        print(f"Fel vid bearbetning: {e}")
        return 1


if __name__ == "__main__":
    exit(main())