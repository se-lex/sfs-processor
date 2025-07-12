#!/usr/bin/env python3
"""
Module for generating initial Git commits for SFS documents.

This module handles creating commits for SFS documents without managing
the overall git workflow (branching, pushing, etc).
"""

import os
import re
import subprocess
from pathlib import Path

from exporters.git.git_utils import GIT_TIMEOUT
from formatters.format_sfs_text import clean_selex_tags
from util.datetime_utils import format_datetime, format_datetime_for_git
from util.file_utils import save_to_disk


def init_commit(
    data: dict,
    output_file: Path,
    markdown_content: str,
    verbose: bool = False
) -> str:
    """
    Generate initial git commit for an SFS document.

    This function handles creating commits for individual documents.
    It assumes we're already in a git repository and on the correct branch.

    Args:
        data: JSON data containing document information
        output_file: Path to the output markdown file (for local reference)
        markdown_content: The markdown content to commit and save
        verbose: Enable verbose output

    Returns:
        str: The final markdown content (cleaned, without selex tags)
    """
    # Extract document metadata
    beteckning = data.get('beteckning')
    if not beteckning:
        raise ValueError("Beteckning saknas i dokumentdata")
    
    rubrik = data.get('rubrik')
    if not rubrik:
        raise ValueError("Rubrik saknas i dokumentdata")
    
    utfardad_datum = format_datetime(data.get('fulltext', {}).get('utfardadDateTime'))

    # Prepare final content for local save (always clean selex tags in git mode)
    final_content = clean_selex_tags(markdown_content)

    # Save file locally for reference
    save_to_disk(output_file, final_content)
    print(f"Skapade dokument: {output_file}")

    # Create git commit if we have utfardad_datum
    if utfardad_datum:
        # Extract year from beteckning for directory structure
        year_match = re.search(r'(\d{4}):', beteckning)
        if year_match:
            year = year_match.group(1)
            relative_path = Path(year) / output_file.name
        else:
            relative_path = Path(output_file.name)

        # Create directory structure if needed
        target_file = Path.cwd() / relative_path
        target_file.parent.mkdir(parents=True, exist_ok=True)

        # Check if file already exists in git repository
        if target_file.exists():
            if verbose:
                print(f"Varning: Filen {relative_path} finns redan i git repository, skippar")
            return final_content
        
        # Also check if file is already tracked by git (in case it was deleted locally)
        try:
            result = subprocess.run(['git', 'ls-files', str(relative_path)], 
                                  capture_output=True, text=True, timeout=GIT_TIMEOUT)
            if result.returncode == 0 and result.stdout.strip():
                if verbose:
                    print(f"Varning: Filen {relative_path} är redan spårad av git, skippar")
                return final_content
        except subprocess.CalledProcessError:
            pass  # File is not tracked, continue

        # Write the file (use clean content without selex tags for git)
        clean_content = clean_selex_tags(markdown_content)
        
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(clean_content)

        # Stage the file
        subprocess.run(['git', 'add', str(relative_path)],
                     check=True, capture_output=True, timeout=GIT_TIMEOUT)

        # Prepare commit message
        commit_message = rubrik

        # Add förarbeten if available
        register_data = data.get('register', {})
        predocs = register_data.get('forarbeten')
        if predocs:
            commit_message += (f"\n\nHar tillkommit i Svensk författningssamling "
                             f"efter dessa förarbeten: {predocs}")

        # Format date for git
        commit_date = format_datetime_for_git(utfardad_datum)

        # Create commit with specified date
        env = {**os.environ, 'GIT_AUTHOR_DATE': commit_date, 'GIT_COMMITTER_DATE': commit_date}
        subprocess.run([
            'git', 'commit', '-m', commit_message
        ], check=True, capture_output=True, env=env, timeout=GIT_TIMEOUT)

        if verbose:
            print(f"Git-commit skapad: '{commit_message}' daterad {commit_date}")

    elif not utfardad_datum:
        if verbose:
            print(f"Hoppade över git-commit (inget utfärdandedatum): {beteckning}")

    return final_content