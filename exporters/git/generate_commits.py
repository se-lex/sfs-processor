#!/usr/bin/env python3
"""
Module for generating Git commits based on temporal changes in Swedish legal documents.

This module uses the identify_upcoming_changes function to find all temporal changes
in markdown files and creates Git commits on the appropriate dates with suitable emojis.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from temporal.upcoming_changes import identify_upcoming_changes
from temporal.apply_temporal import apply_temporal
from exporters.git.git_utils import is_file_tracked, has_staged_changes, stage_file, create_commit_with_date
from util.datetime_utils import format_datetime, format_datetime_for_git
from util.yaml_utils import extract_frontmatter_property
from util.file_utils import read_file_content, save_to_disk
from formatters.format_sfs_text import clean_selex_tags


def create_init_git_commit(
    data: dict,
    output_file: Path,
    markdown_content: str,
    verbose: bool = False
) -> str:
    """
    Create the initial git commit for an SFS document.
    
    This function merges functionality from both create_init_git_commit and init_commit.
    It handles creating commits for individual documents and assumes we're already in a 
    git repository and on the correct branch.
    
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
    
    # Always expect utfardad_datum to exist
    utfardad_datum = format_datetime(data.get('fulltext', {}).get('utfardadDateTime'))
    if not utfardad_datum:
        raise ValueError(f"utfardadDateTime saknas för {beteckning}")

    # Prepare final content for local save (always clean selex tags in git mode)
    final_content = clean_selex_tags(markdown_content)

    # Save file locally for reference
    save_to_disk(output_file, final_content)
    print(f"Skapade dokument: {output_file}")

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
    if is_file_tracked(str(relative_path)):
        if verbose:
            print(f"Varning: Filen {relative_path} är redan spårad av git, skippar")
        return final_content

    # Write the file (use clean content without selex tags for git)
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(final_content)

    # Stage the file
    if not stage_file(str(relative_path), verbose):
        return final_content

    # Check if there are any changes to commit
    if not has_staged_changes():
        print(f"Inga ändringar att commita för {beteckning}")
        return final_content

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
    create_commit_with_date(commit_message, commit_date, verbose)

    return final_content


def format_section_list(sections):
    """Format a list of sections with proper Swedish enumeration (commas and 'och' before last)."""
    if not sections:
        return ""
    if len(sections) == 1:
        return sections[0]
    if len(sections) == 2:
        return f"{sections[0]} och {sections[1]}"
    return f"{', '.join(sections[:-1])} och {sections[-1]}"


def generate_descriptive_commit_message(
    doc_name: str,
    changes: List[Dict]
) -> str:
    """
    Generate a descriptive commit message based on the changes.
    
    Args:
        doc_name: The document ID (e.g., "2024:123")
        changes: List of changes for this date
        
    Returns:
        A descriptive commit message with emoji
    """
    has_ikraft = any(c['type'] == 'ikraft' for c in changes)
    has_upphor = any(c['type'] in ['upphor', 'upphor_villkor'] for c in changes)
    
    # Collect sections with titles and check for article-level changes
    ikraft_sections = []
    upphor_sections = []
    upphavd_sections = []  # Sections with selex:upphavd="true"
    has_article_changes = False
    has_article_revoked = False  # Article-level active revocation
    
    for change in changes:
        # Check if this is an article-level change (whole document)
        if change.get('source') == 'article_tag':
            has_article_changes = True
            # Track if this is an active revocation at article level
            if change.get('is_revoked'):
                has_article_revoked = True
            continue
        
        section_id = change.get('section_id')
        section_title = change.get('section_title', section_id or '')
        
        if not section_id:
            continue
            
        # Use section title
        display_text = section_title if section_title else f"{section_id} §"
        
        if change['type'] == 'ikraft':
            ikraft_sections.append(display_text)
        elif change['type'] == 'upphor':
            upphor_sections.append(display_text)
            # Track if this is an active revocation (upphävd)
            if change.get('is_revoked'):
                upphavd_sections.append(display_text)
        elif change['type'] == 'upphor_villkor':
            # Handle conditional expiry - treat similar to upphor but with different messaging
            upphor_sections.append(display_text)
        else:
            raise ValueError(f"Okänd ändringstyp '{change['type']}' för {section_id}. Kända typer: 'ikraft', 'upphor', 'upphor_villkor'")
    
    # Build commit message
    if has_ikraft and has_upphor:
        # Both entry into force and expiration
        emoji = "🔄"
        
        # Check if same sections are both taking effect and expiring
        ikraft_set = set(ikraft_sections)
        upphor_set = set(upphor_sections)
        updated_sections = ikraft_set & upphor_set
        only_ikraft = ikraft_set - upphor_set
        only_upphor = upphor_set - ikraft_set
        
        message_parts = []
        
        if updated_sections:
            sections_str = format_section_list(list(updated_sections))
            message_parts.append(f"{sections_str} uppdateras")
        
        if only_ikraft:
            sections_str = format_section_list(list(only_ikraft))
            message_parts.append(f"{sections_str} träder i kraft")
        
        if only_upphor:
            sections_str = format_section_list(list(only_upphor))
            # Use specific terminology if all are actively revoked
            if set(only_upphor).issubset(set(upphavd_sections)):
                message_parts.append(f"{sections_str} upphävs")
            else:
                message_parts.append(f"{sections_str} upphör att gälla")
        
        if message_parts:
            message = f"{emoji} {doc_name}: {', och '.join(message_parts)}"
        elif has_article_changes:
            # Only article-level changes (whole document changes)
            if has_article_revoked:
                message = f"{emoji} {doc_name} träder i kraft och upphävs"
            else:
                message = f"{emoji} {doc_name} träder i kraft och upphör att gälla"
        else:
            message = f"{emoji} {doc_name} ändringar träder i kraft och upphävs"
            
    elif has_ikraft:
        # Entry into force
        emoji = "✅"
        if ikraft_sections:
            if len(ikraft_sections) == 1:
                message = f"{emoji} {doc_name}: {ikraft_sections[0]} träder i kraft"
            else:
                sections_str = format_section_list(ikraft_sections)
                message = f"{emoji} {doc_name}: {sections_str} träder i kraft"
        elif has_article_changes:
            # Article-level change - whole document comes into force
            message = f"{emoji} {doc_name} träder i kraft"
        else:
            raise ValueError(f"Ikraft-ändringar hittades för {doc_name} men varken sections eller article-ändringar kunde identifieras")
            
    else:  # has_upphor
        # Expiration
        emoji = "🚫"
        if upphor_sections:
            if len(upphor_sections) == 1:
                # For single section, use specific terminology if actively revoked
                if upphor_sections[0] in upphavd_sections:
                    message = f"{emoji} {doc_name}: {upphor_sections[0]} upphävs"
                else:
                    message = f"{emoji} {doc_name}: {upphor_sections[0]} upphör att gälla"
            else:
                sections_str = format_section_list(upphor_sections)
                # Check if all sections are actively revoked
                if set(upphor_sections).issubset(set(upphavd_sections)):
                    message = f"{emoji} {doc_name}: {sections_str} upphävs"
                else:
                    # Mixed or temporal expiration - use general term but indicate if some are actively revoked
                    if upphavd_sections:
                        message = f"{emoji} {doc_name}: {sections_str} upphävs"
                    else:
                        message = f"{emoji} {doc_name}: {sections_str} upphör att gälla"
        elif has_article_changes:
            # Article-level change - whole document expires
            if has_article_revoked:
                message = f"{emoji} {doc_name} upphävs"
            else:
                message = f"{emoji} {doc_name} upphör att gälla"
        else:
            raise ValueError(f"Upphor-ändringar hittades för {doc_name} men varken sections eller article-ändringar kunde identifieras")
    
    return message


def generate_temporal_commits(
    markdown_file: Path,
    doc_name: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    dry_run: bool = False
) -> None:
    """
    Generate Git commits for temporal changes in a markdown file.
    
    This function reads a markdown file, identifies upcoming changes using
    identify_upcoming_changes, and creates Git commits on the appropriate dates
    with suitable emojis.
    
    Args:
        markdown_file: Path to the markdown file to process
        from_date: Start date (inclusive) in YYYY-MM-DD format. If None, no lower bound.
        to_date: End date (inclusive) in YYYY-MM-DD format. If None, no upper bound.
        dry_run: If True, show what would be committed without making actual commits
        
    Raises:
        ValueError: If date format is invalid
        subprocess.CalledProcessError: If git commands fail
    """
    # Validate date formats if provided
    if from_date:
        try:
            datetime.strptime(from_date, '%Y-%m-%d')
        except ValueError:
            raise ValueError(f"Invalid from_date format: {from_date}. Expected YYYY-MM-DD")
    
    if to_date:
        try:
            datetime.strptime(to_date, '%Y-%m-%d')
        except ValueError:
            raise ValueError(f"Invalid to_date format: {to_date}. Expected YYYY-MM-DD")
    
    # Read the markdown file
    if not markdown_file.exists():
        print(f"Fel: Filen {markdown_file} finns inte")
        return
    
    try:
        content = read_file_content(markdown_file)
    except IOError as e:
        print(str(e))
        return
    
    # Identify upcoming changes
    changes = identify_upcoming_changes(content)
    
    if not changes:
        print(f"Inga temporala ändringar hittades i {markdown_file}")
        return
    
    # Filter changes by date range
    filtered_changes = []
    for change in changes:
        change_date = change['date']
        
        # Check if within date range
        if from_date and change_date < from_date:
            continue
        if to_date and change_date > to_date:
            continue
            
        filtered_changes.append(change)
    
    if not filtered_changes:
        print(f"Inga ändringar inom datumintervallet {from_date or 'början'} - {to_date or 'slut'}")
        return
    
    # Extract doc_name from frontmatter
    doc_name = extract_frontmatter_property(content, 'beteckning')
    
    if not doc_name:
        print(f"Varning: Ingen doc_name hittades i frontmatter för {markdown_file}")
        return
    
    print(f"Använder doc_name: {doc_name}")
    
    # Group changes by date
    changes_by_date = {}
    for change in filtered_changes:
        date = change['date']
        if date not in changes_by_date:
            changes_by_date[date] = []
        changes_by_date[date].append(change)
    
    if dry_run:
        # Dry run mode - show what would be committed without actually committing
        print(f"\n{'='*80}")
        print(f"DRY RUN: Visar planerade commits för {markdown_file.name}")
        print(f"{'='*80}")
        
        # Table headers
        print(f"{'Datum':<12} {'Meddelande':<50} {'Tecken ändrade':<15}")
        print(f"{'-'*12} {'-'*50} {'-'*15}")
        
        for date in sorted(changes_by_date.keys()):
            date_changes = changes_by_date[date]
            
            # Apply temporal changes for this date
            try:
                filtered_content = apply_temporal(content, date, False)  # No verbose for dry run
                
                # Calculate character difference
                char_diff = abs(len(filtered_content) - len(content))
                
                # Generate descriptive commit message
                message = generate_descriptive_commit_message(doc_name, date_changes)
                
                # Truncate message if too long for table
                display_message = message[:47] + "..." if len(message) > 50 else message
                
                print(f"{date:<12} {display_message:<50} {char_diff:<15}")
                
            except Exception as e:
                print(f"{date:<12} {'FEL: ' + str(e)[:40]:<50} {'N/A':<15}")
        
        print(f"\nTotalt {len(changes_by_date)} commits skulle skapas.")
        print("Kör utan --dry-run för att utföra commits på riktigt.")
        return
    
    # Normal mode - create actual commits
    original_content = content  # Store original content for restoration
    
    # Create commits for each date
    for date in sorted(changes_by_date.keys()):
        date_changes = changes_by_date[date]
        
        # Apply temporal changes for this date
        try:
            filtered_content = apply_temporal(content, date, False)
            # Write the temporally filtered content to the file
            save_to_disk(markdown_file, filtered_content)
        except Exception as e:
            print(f"Fel vid tillämpning av temporal ändringar för {date}: {e}")
            continue
        
        # Generate descriptive commit message
        message = generate_descriptive_commit_message(doc_name, date_changes)
        
        # Stage the file
        if not stage_file(str(markdown_file)):
            continue
        
        # Check if there are any changes to commit
        if not has_staged_changes():
            print(f"Inga ändringar att committa för {date}")
            continue
        
        # Create commit with the appropriate date
        git_date = format_datetime_for_git(date)
        
        if not create_commit_with_date(message, git_date, verbose=True):
            print(f"Fel vid commit för {date}")
    
    # Restore original content after all commits
    try:
        save_to_disk(markdown_file, original_content)
    except Exception as e:
        print(f"Varning: Kunde inte återställa ursprungligt innehåll: {e}")


def generate_commits_for_directory(
    directory: Path,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    dry_run: bool = False
) -> None:
    """
    Generate Git commits for all markdown files in a directory.
    
    Args:
        directory: Path to directory containing markdown files
        from_date: Start date (inclusive) in YYYY-MM-DD format. If None, no lower bound.
        to_date: End date (inclusive) in YYYY-MM-DD format. If None, no upper bound.
        dry_run: If True, show what would be committed without making actual commits
    """
    if not directory.exists():
        print(f"Fel: Katalogen {directory} finns inte")
        return
    
    if not directory.is_dir():
        print(f"Fel: {directory} är inte en katalog")
        return
    
    # Find all markdown files
    md_files = list(directory.rglob("*.md"))
    
    if not md_files:
        print(f"Inga markdown-filer hittades i {directory}")
        return
    
    print(f"Bearbetar {len(md_files)} markdown-filer...")
    
    for md_file in md_files:
        print(f"\nBearbetar {md_file.name}...")
        
        try:
            generate_temporal_commits(md_file, None, from_date, to_date, dry_run)
        except Exception as e:
            print(f"Fel vid bearbetning av {md_file}: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generera Git-commits baserat på temporala ändringar i svenska lagdokument.'
    )
    parser.add_argument(
        'path',
        help='Sökväg till markdown-fil eller katalog att bearbeta'
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
    
    args = parser.parse_args()
    
    path = Path(args.path)
    
    if path.is_file():
        generate_temporal_commits(path, None, args.from_date, args.to_date, args.dry_run)
    elif path.is_dir():
        generate_commits_for_directory(path, args.from_date, args.to_date, args.dry_run)
    else:
        print(f"Fel: {path} finns inte")