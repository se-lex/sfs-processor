#!/usr/bin/env python3
"""
Script to run init commits and temporal commits on a 3-year period.

This script processes SFS documents by:
1. Creating initial commits for all documents
2. Processing temporal commits over a 3-year period
3. Supporting dry run mode with verbose logging to a .log file

Usage:
    python scripts/run_3year_commits.py [--dry-run] [--verbose] [--start-year YYYY] [--json-dir PATH] [--output-dir PATH]
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

# Add the parent directory to the path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from exporters.git.init_commits_batch_processor import process_files_with_git_batch
from exporters.git.temporal_commits_batch_processor import process_temporal_commits_batch
from util.file_utils import filter_json_files


def setup_logging(verbose: bool, log_file: str) -> logging.Logger:
    """Setup logging configuration."""
    logger = logging.getLogger('run_3year_commits')
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # File handler
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler (only for INFO and above unless verbose)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


def get_3year_period(start_year: int) -> tuple[str, str]:
    """Get the start and end dates for a 3-year period."""
    start_date = f"{start_year}-01-01"
    end_date = f"{start_year + 2}-12-31"
    return start_date, end_date


def find_json_files(json_dir: Path, logger: logging.Logger) -> List[Path]:
    """Find all JSON files in the input directory."""
    if not json_dir.exists():
        logger.error(f"JSON directory {json_dir} does not exist")
        return []
    
    json_files = list(json_dir.glob('*.json'))
    if not json_files:
        logger.warning(f"No JSON files found in {json_dir}")
        return []
    
    logger.info(f"Found {len(json_files)} JSON files in {json_dir}")
    return json_files


def run_init_commits(json_files: List[Path], output_dir: Path, start_year: int, dry_run: bool, verbose: bool, logger: logging.Logger) -> bool:
    """Run initial commits for documents from the specified 3-year period."""
    logger.info(f"Starting init commits processing for years {start_year}-{start_year+2}...")
    
    # Filter JSON files to only include those from the 3-year period
    year_filter = f"{start_year},{start_year+1},{start_year+2}"
    filtered_json_files = filter_json_files(json_files, year_filter)
    
    logger.info(f"Filtered to {len(filtered_json_files)} files from years {start_year}-{start_year+2}")
    
    if not filtered_json_files:
        logger.warning(f"No files found for the specified period {start_year}-{start_year+2}")
        return False
    
    try:
        if dry_run:
            logger.info("DRY RUN: Would process init commits for the following files:")
            for json_file in filtered_json_files:
                logger.info(f"  - {json_file.name}")
            return True
        else:
            process_files_with_git_batch(
                json_files=filtered_json_files,
                output_dir=output_dir,
                verbose=verbose,
                predocs=False,
                batch_size=50
            )
            logger.info("Init commits processing completed successfully")
            return True
    except Exception as e:
        logger.error(f"Error during init commits processing: {e}")
        return False


def run_temporal_commits(markers_dir: Path, start_date: str, end_date: str, dry_run: bool, verbose: bool, logger: logging.Logger) -> bool:
    """Run temporal commits for the 3-year period."""
    logger.info(f"Starting temporal commits processing for period {start_date} to {end_date}...")
    logger.info(f"Reading marker files from: {markers_dir}")
    
    try:
        process_temporal_commits_batch(
            markdown_dir=markers_dir,
            from_date=start_date,
            to_date=end_date,
            dry_run=dry_run,
            verbose=verbose,
            batch_size=50
        )
        logger.info("Temporal commits processing completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error during temporal commits processing: {e}")
        return False


def main():
    """Main function to run the 3-year commits script."""
    parser = argparse.ArgumentParser(
        description='Run init commits and temporal commits on a 3-year period.'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Run in dry-run mode (no actual git operations, only logging)'
    )
    parser.add_argument(
        '--verbose', 
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--start-year', 
        type=int,
        default=datetime.now().year - 2,
        help='Starting year for the 3-year period (default: current year - 2)'
    )
    parser.add_argument(
        '--json-dir',
        type=Path,
        help='Directory containing JSON files (default: ../sfs-jsondata)'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        help='Output directory for processed files (default: ../sfs-export-git)'
    )
    parser.add_argument(
        '--markers-dir',
        type=Path,
        help='Directory containing markdown files with selex markers (default: ../sfs-export-md-markers)'
    )
    parser.add_argument(
        '--log-file',
        default='logs/3year_commits.log',
        help='Log file name (default: logs/3year_commits.log)'
    )
    
    args = parser.parse_args()
    
    # Setup paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    json_dir = args.json_dir or project_root.parent / 'sfs-jsondata'
    output_dir = args.output_dir or project_root.parent / 'sfs-export-git'
    markers_dir = args.markers_dir or project_root.parent / 'sfs-export-md-markers'
    
    # Create logs directory if it doesn't exist
    log_file_path = Path(args.log_file)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Setup logging
    logger = setup_logging(args.verbose, args.log_file)
    
    # Log configuration
    start_date, end_date = get_3year_period(args.start_year)
    
    logger.info("=== 3-Year Commits Script Configuration ===")
    logger.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    logger.info(f"Verbose: {args.verbose}")
    logger.info(f"Start year: {args.start_year}")
    logger.info(f"Period: {start_date} to {end_date}")
    logger.info(f"JSON directory: {json_dir}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Markers directory: {markers_dir}")
    logger.info(f"Log file: {args.log_file}")
    logger.info("=" * 50)
    
    # Create output directory if it doesn't exist
    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find JSON files
    json_files = find_json_files(json_dir, logger)
    if not json_files:
        logger.error("No JSON files found, exiting")
        return 1
    
    # Step 1: Run init commits
    logger.info("Step 1: Processing init commits...")
    if not run_init_commits(json_files, output_dir, args.start_year, args.dry_run, args.verbose, logger):
        logger.error("Init commits processing failed, exiting")
        return 1
    
    # Step 2: Run temporal commits
    logger.info("Step 2: Processing temporal commits...")
    if not run_temporal_commits(markers_dir, start_date, end_date, args.dry_run, args.verbose, logger):
        logger.error("Temporal commits processing failed, exiting")
        return 1
    
    logger.info("=== 3-Year Commits Script Completed Successfully ===")
    logger.info(f"Log saved to: {args.log_file}")
    
    if args.dry_run:
        print(f"\nDRY RUN completed. Check {args.log_file} for detailed log.")
    else:
        print(f"\nProcessing completed. Check {args.log_file} for detailed log.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())