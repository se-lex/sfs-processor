#!/usr/bin/env python3
"""
Temporal commits batch processing functionality for git exports.

This module handles batch processing of temporal commits for multiple SFS documents
in a git repository, with support for date filtering and dry-run mode.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from exporters.git import clone_target_repository_to_temp
from exporters.git.git_utils import checkout_branch, push_to_target_repository
from exporters.git.generate_commits import generate_temporal_commits


def _create_temporal_branch_name(from_date: Optional[str], to_date: Optional[str]) -> str:
    """
    Create a descriptive branch name based on the date range.

    Args:
        from_date: Start date in YYYY-MM-DD format
        to_date: End date in YYYY-MM-DD format

    Returns:
        str: Branch name for temporal commits
    """
    if from_date and to_date:
        # Format: temporal_20240101-20241231
        from_formatted = from_date.replace('-', '')
        to_formatted = to_date.replace('-', '')
        return f"temporal_{from_formatted}-{to_formatted}"
    elif from_date:
        # Format: temporal_from_20240101
        from_formatted = from_date.replace('-', '')
        return f"temporal_from_{from_formatted}"
    elif to_date:
        # Format: temporal_to_20241231
        to_formatted = to_date.replace('-', '')
        return f"temporal_to_{to_formatted}"
    else:
        # Fallback to timestamp if no dates provided
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"temporal_{timestamp}"


def process_temporal_commits_batch(
    markdown_dir: Path,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    dry_run: bool = False,
    verbose: bool = False,
    batch_size: int = 100,
    branch_name: Optional[str] = None
) -> None:
    """
    Process temporal commits for markdown files in batch, with git operations.

    Args:
        markdown_dir: Directory containing markdown files to process
        from_date: Start date (inclusive) in YYYY-MM-DD format
        to_date: End date (inclusive) in YYYY-MM-DD format
        dry_run: If True, show what would be committed without making actual commits
        verbose: Enable verbose output
        batch_size: Number of files to process per batch
    """
    if not markdown_dir.exists():
        print(f"Fel: Markdown-katalogen {markdown_dir} finns inte")
        return

    if not markdown_dir.is_dir():
        print(f"Fel: {markdown_dir} är inte en katalog")
        return

    # Find all markdown files
    md_files = list(markdown_dir.rglob("*.md"))

    if not md_files:
        print(f"Inga markdown-filer hittades i {markdown_dir}")
        return

    print(f"Hittade {len(md_files)} markdown-filer att bearbeta")

    if dry_run:
        print("KÖR I DRY-RUN LÄGE - inga commits kommer att skapas")
        _process_temporal_commits_dry_run(md_files, from_date, to_date)
    else:
        _process_temporal_commits_with_git(
            md_files, from_date, to_date, verbose, batch_size, branch_name)


def _process_temporal_commits_dry_run(
    md_files: List[Path],
    from_date: Optional[str],
    to_date: Optional[str]
) -> None:
    """Process temporal commits in dry-run mode (no git operations)."""
    print(f"\n{'='*80}")
    print(f"DRY RUN: Visar planerade temporal commits")
    print(f"{'='*80}")

    for md_file in md_files:
        print(f"\nBearbetar {md_file.name}...")
        try:
            # Run generate_temporal_commits in dry-run mode
            generate_temporal_commits(md_file, None, from_date, to_date, dry_run=True)
            # Note: generate_temporal_commits handles its own dry-run output
        except Exception as e:
            print(f"Fel vid bearbetning av {md_file}: {e}")

    print(f"\nDRY RUN KLAR")


def _process_temporal_commits_with_git(
    md_files: List[Path],
    from_date: Optional[str],
    to_date: Optional[str],
    verbose: bool,
    batch_size: int,
    branch_name: Optional[str] = None
) -> None:
    """Process temporal commits with actual git operations."""
    # Clone target repository once for all batches
    repo_dir, original_cwd = clone_target_repository_to_temp(verbose=verbose)
    if repo_dir is None:
        raise RuntimeError("Failed to clone target repository")

    try:
        # Change to cloned repository directory
        os.chdir(repo_dir)

        # Use provided branch name or create one based on date range
        if branch_name:
            unique_branch = branch_name
        else:
            unique_branch = _create_temporal_branch_name(from_date, to_date)

        # Create and checkout new branch
        if not checkout_branch(unique_branch, create_if_missing=True, verbose=verbose):
            print(f"Fel: Kunde inte skapa git branch: {unique_branch}")
            return

        # Split files into batches
        total_files = len(md_files)
        if total_files > batch_size:
            print(f"Delar upp {total_files} filer i batcher om {batch_size} filer var")
            batches = [md_files[i:i + batch_size] for i in range(0, total_files, batch_size)]
            print(f"Skapade {len(batches)} batcher")

            # Process each batch in the same repository and branch, pushing after each
            for i, batch in enumerate(batches, 1):
                print(f"\nBearbetar temporal batch {i}/{len(batches)} ({len(batch)} filer)...")
                _process_temporal_batch_files(
                    batch, from_date, to_date, verbose, original_cwd, i, len(batches))

                # Push after each batch
                print(f"Pushar temporal batch {i}/{len(batches)} till target repository...")
                if push_to_target_repository(unique_branch, 'origin', verbose):
                    print(
                        f"Temporal batch {i}/{len(batches)} pushad till target repository som branch '{unique_branch}'")
                else:
                    print(
                        f"Misslyckades med att pusha temporal batch {i}/{len(batches)} till target repository")
        else:
            print(f"Bearbetar {total_files} filer i en enda temporal batch...")
            _process_temporal_batch_files(md_files, from_date, to_date, verbose, original_cwd, 1, 1)

            # Push the single batch
            print(f"Pushar alla {total_files} temporal commits till target repository...")
            if push_to_target_repository(unique_branch, 'origin', verbose):
                print(
                    f"Alla {total_files} temporal commits pushade till target repository som branch '{unique_branch}'")
            else:
                print(f"Misslyckades med att pusha temporal commits till target repository")

    except Exception as e:
        print(f"Fel vid temporal commits batch processing: {e}")
        raise  # Re-raise the exception so temporal processing errors are visible
    finally:
        # Always change back to original directory
        os.chdir(original_cwd)


def _process_temporal_batch_files(
    md_files: List[Path],
    from_date: Optional[str],
    to_date: Optional[str],
    verbose: bool,
    original_cwd: str,
    batch_num: int,
    total_batches: int
) -> None:
    """Process batch of markdown files for temporal commits in the current repository."""
    import shutil

    for md_file in md_files:
        # Use absolute path since we changed working directory
        abs_md_file = Path(original_cwd) / md_file

        # Copy file to year folder in cloned repo and remove -markers from filename
        # Extract year from file path (e.g., 2013/sfs-2013-xxx-markers.md -> 2013)
        year_dir = md_file.parent.name
        filename = md_file.name

        # Remove -markers from filename if present
        if "-markers" in filename:
            filename = filename.replace("-markers", "")

        # Target structure: year/filename (directly in year folder at root)
        target_file = Path.cwd() / year_dir / filename

        # Create directory structure if needed
        target_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Copy the file to the git repo
            shutil.copy2(abs_md_file, target_file)

            print(f"Bearbetar {md_file.name} för temporal commits...")
            # Run generate_temporal_commits on the copied file in the repo
            generate_temporal_commits(target_file, None, from_date, to_date, dry_run=False)
        except Exception as e:
            print(f"Fel vid temporal bearbetning av {abs_md_file}: {e}")
            continue

    if verbose:
        print(f"Temporal batch {batch_num}/{total_batches} bearbetad ({len(md_files)} filer)")
