#!/usr/bin/env python3
"""
Module for generating initial Git commits for SFS documents.

This module handles the complete git workflow for creating initial commits
for SFS documents, including branch management and cleanup.
"""

from pathlib import Path
from typing import Optional

from exporters.git import ensure_git_branch_for_commits, restore_original_branch
from exporters.git.generate_commits import create_init_git_commit
from util.file_utils import save_to_disk
from formatters.format_sfs_text import clean_selex_tags
from util.datetime_utils import format_datetime


def generate_init_commit_for_document(
    data: dict,
    output_file: Path,
    markdown_content: str,
    git_branch: str,
    preserve_section_tags: bool = False,
    verbose: bool = False
) -> str:
    """
    Generate initial git commit for an SFS document with proper branch handling.
    
    This function handles the complete git workflow:
    1. Creates a separate git branch for commits
    2. Creates the initial commit with document metadata
    3. Restores the original branch
    4. Writes the final file content
    
    Args:
        data: JSON data containing document information
        output_file: Path to the output markdown file
        markdown_content: The markdown content to commit and save
        git_branch: Branch name to use for git commits
        preserve_section_tags: Whether to preserve <section> tags in final output
        verbose: Enable verbose output
        
    Returns:
        str: The final markdown content (cleaned if preserve_section_tags is False)
    """
    # Extract document metadata
    beteckning = data.get('beteckning', 'Unknown')
    rubrik = data.get('rubrik', '')
    utfardad_datum = format_datetime(data.get('fulltext', {}).get('utfardadDateTime'))
    
    # Ensure commits are made in a different branch
    original_branch, commit_branch = ensure_git_branch_for_commits(
        git_branch, 
        remove_all_commits_first=True, 
        verbose=verbose
    )
    
    # Ensure branch creation was successful
    if original_branch is None or commit_branch is None:
        raise RuntimeError(f"Misslyckades att skapa git branch för {beteckning}")
    
    try:
        # Only create main commit if we have utfardad_datum
        if utfardad_datum:
            # Get förarbeten if available
            register_data = data.get('register', {})
            predocs = register_data.get('forarbeten')
            
            # Create initial git commit
            success = create_init_git_commit(
                output_file=output_file,
                markdown_content=markdown_content,
                beteckning=beteckning,
                rubrik=rubrik,
                utfardad_datum=utfardad_datum,
                predocs=predocs,
                verbose=verbose
            )
            
            if not success:
                print(f"Git-commit misslyckades för {beteckning}")
        else:
            # Write file if no utfardad_datum available
            save_to_disk(output_file, markdown_content)
            print(f"Skrev fil utan git-commit (inget utfärdandedatum): {output_file}")
        
    finally:
        # Always restore original branch after git operations
        restore_original_branch(original_branch)
    
    # Prepare final content for return
    final_content = markdown_content
    if not preserve_section_tags:
        final_content = clean_selex_tags(final_content)
    
    return final_content