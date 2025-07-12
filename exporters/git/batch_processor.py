#!/usr/bin/env python3
"""
Batch processing functionality for git exports.

This module handles batch processing of multiple SFS documents to git repository.
"""

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
import random
import json

from exporters.git import clone_target_repository_to_temp
from exporters.git.git_utils import GIT_TIMEOUT


def process_files_with_git_batch(json_files, output_dir, verbose, predocs):
    """Process files with git batch workflow."""
    # Clone target repository once for all documents
    repo_dir, original_cwd = clone_target_repository_to_temp(verbose=verbose)
    if repo_dir is None:
        raise RuntimeError("Failed to clone target repository")

    try:
        # Change to cloned repository directory
        os.chdir(repo_dir)

        # Create unique branch name for this batch
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = random.randint(1000, 9999)
        unique_branch = f"batch_{timestamp}_{random_suffix}"

        # Create and checkout new branch directly
        try:
            subprocess.run(['git', 'checkout', '-b', unique_branch],
                         check=True, capture_output=True, timeout=GIT_TIMEOUT)
            if verbose:
                print(f"Skapade och bytte till branch '{unique_branch}' för batch-commits")
        except subprocess.CalledProcessError as e:
            print(f"Fel: Kunde inte skapa git branch: {e}")
            return

        # Process each JSON file
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

            # Create documents in the cloned repository
            make_document(data, output_dir, ["git"], True, verbose, True, predocs, True)

        # Push all commits to target repository
        if verbose:
            print(f"Pushar batch till target repository...")

        subprocess.run(['git', 'push', 'origin', unique_branch],
                     check=True, capture_output=True, timeout=GIT_TIMEOUT)

        print(f"Batch pushad till target repository som branch '{unique_branch}'")

    except subprocess.CalledProcessError as e:
        print(f"Fel vid git batch processing: {e}")
        if hasattr(e, 'stderr') and e.stderr:
            print(f"Git stderr: {e.stderr.decode('utf-8', errors='replace')}")
    except Exception as e:
        print(f"Oväntat fel vid git batch processing: {e}")
    finally:
        # Always change back to original directory
        os.chdir(original_cwd)
        # Clean up temporary directory
        try:
            shutil.rmtree(repo_dir.parent)
        except Exception as e:
            if verbose:
                print(f"Varning: Kunde inte rensa temporär katalog: {e}")