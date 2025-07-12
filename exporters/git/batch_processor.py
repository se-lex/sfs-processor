#!/usr/bin/env python3
"""
Batch processing functionality for git exports.

This module handles batch processing of multiple SFS documents to git repository.
"""

import os
from datetime import datetime
from pathlib import Path
import random
import json

from exporters.git import clone_target_repository_to_temp
from exporters.git.git_utils import checkout_branch, push_to_target_repository
from sfs_processor import make_document


def process_files_with_git_batch(json_files, output_dir, verbose, predocs, batch_size=10):
    """Process files with git batch workflow, using same branch but pushing after each batch."""
    # Clone target repository once for all batches
    repo_dir, original_cwd = clone_target_repository_to_temp(verbose=verbose)
    if repo_dir is None:
        raise RuntimeError("Failed to clone target repository")

    try:
        # Change to cloned repository directory
        os.chdir(repo_dir)

        # Create unique branch name for this entire operation
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = random.randint(1000, 9999)
        unique_branch = f"batch_{timestamp}_{random_suffix}"

        # Create and checkout new branch
        if not checkout_branch(unique_branch, create_if_missing=True, verbose=verbose):
            print(f"Fel: Kunde inte skapa git branch: {unique_branch}")
            return

        # Split files into batches
        total_files = len(json_files)
        if total_files > batch_size:
            print(f"Delar upp {total_files} filer i batcher om {batch_size} filer var")
            batches = [json_files[i:i + batch_size] for i in range(0, total_files, batch_size)]
            print(f"Skapade {len(batches)} batcher")
            
            # Process each batch in the same repository and branch, pushing after each
            for i, batch in enumerate(batches, 1):
                print(f"\nBearbetar batch {i}/{len(batches)} ({len(batch)} filer)...")
                _process_batch_files(batch, output_dir, verbose, predocs, original_cwd, i, len(batches))
                
                # Push after each batch
                print(f"Pushar batch {i}/{len(batches)} till target repository...")
                if push_to_target_repository(unique_branch, 'origin', verbose):
                    print(f"Batch {i}/{len(batches)} pushad till target repository som branch '{unique_branch}'")
                else:
                    print(f"Misslyckades med att pusha batch {i}/{len(batches)} till target repository")
        else:
            print(f"Bearbetar {total_files} filer i en enda batch...")
            _process_batch_files(json_files, output_dir, verbose, predocs, original_cwd, 1, 1)
            
            # Push the single batch
            print(f"Pushar alla {total_files} filer till target repository...")
            if push_to_target_repository(unique_branch, 'origin', verbose):
                print(f"Alla {total_files} filer pushade till target repository som branch '{unique_branch}'")
            else:
                print(f"Misslyckades med att pusha till target repository")

    except Exception as e:
        print(f"Oväntat fel vid git batch processing: {e}")
    finally:
        # Always change back to original directory
        os.chdir(original_cwd)


def _process_batch_files(json_files, output_dir, verbose, predocs, original_cwd, batch_num, total_batches):
    """Process batch files in the current repository without creating new branches."""
    # Process each JSON file in the current git repository
    from sfs_processor import make_document
    for json_file in json_files:
        # Use absolute path since we changed working directory
        abs_json_file = Path(original_cwd) / json_file
        try:
            with open(abs_json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Fel vid läsning av {abs_json_file}: {e}")
            continue

        # Create documents in the cloned repository AND save to original output directory
        # First convert to absolute path since we changed working directory
        if not Path(output_dir).is_absolute():
            original_output_dir = Path(original_cwd) / Path(output_dir).name
        else:
            original_output_dir = Path(output_dir)
        make_document(data, original_output_dir, ["git"], True, verbose, True, predocs, True)
    
    if verbose:
        print(f"Batch {batch_num}/{total_batches} bearbetad ({len(json_files)} filer)")


