#!/usr/bin/env python3
"""
Module for generating Git commits based on temporal changes in Swedish legal documents.

This module uses the identify_upcoming_changes function to find all temporal changes
in markdown files and creates Git commits on the appropriate dates with suitable emojis.
"""

import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from temporal.upcoming_changes import identify_upcoming_changes
from temporal.apply_temporal import apply_temporal
from exporters.git.git_utils import GIT_TIMEOUT
from util.datetime_utils import format_datetime_for_git
from util.yaml_utils import extract_frontmatter_property


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
    has_article_changes = False
    
    for change in changes:
        # Check if this is an article-level change (whole document)
        if change.get('source') == 'article_tag':
            has_article_changes = True
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
            message_parts.append(f"{sections_str} upphävs")
        
        if message_parts:
            message = f"{emoji} {doc_name}: {', och '.join(message_parts)}"
        elif has_article_changes:
            # Only article-level changes (whole document changes)
            message = f"{emoji} {doc_name} träder i kraft och upphävs"
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
                message = f"{emoji} {doc_name}: {upphor_sections[0]} upphävs"
            else:
                sections_str = format_section_list(upphor_sections)
                message = f"{emoji} {doc_name}: {sections_str} upphävs"
        elif has_article_changes:
            # Article-level change - whole document expires
            message = f"{emoji} {doc_name} upphävs"
        else:
            raise ValueError(f"Upphor-ändringar hittades för {doc_name} men varken sections eller article-ändringar kunde identifieras")
    
    return message


def generate_commits(
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
        with open(markdown_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except (IOError, UnicodeDecodeError) as e:
        print(f"Fel vid läsning av {markdown_file}: {e}")
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
            with open(markdown_file, 'w', encoding='utf-8') as f:
                f.write(filtered_content)
        except Exception as e:
            print(f"Fel vid tillämpning av temporal ändringar för {date}: {e}")
            continue
        
        # Generate descriptive commit message
        message = generate_descriptive_commit_message(doc_name, date_changes)
        
        # Stage the file
        try:
            subprocess.run(['git', 'add', str(markdown_file)], check=True, capture_output=True, timeout=GIT_TIMEOUT)
        except subprocess.CalledProcessError as e:
            print(f"Fel vid staging av {markdown_file}: {e}")
            if hasattr(e, 'stderr') and e.stderr:
                print(f"Git stderr: {e.stderr.decode('utf-8', errors='replace')}")
            continue
        
        # Check if there are any changes to commit
        result = subprocess.run(['git', 'diff', '--cached', '--quiet'], capture_output=True, timeout=GIT_TIMEOUT)
        if result.returncode == 0:  # No changes
            print(f"Inga ändringar att committa för {date}")
            continue
        
        # Create commit with the appropriate date
        git_date = format_datetime_for_git(date)
        env = {**os.environ, 'GIT_AUTHOR_DATE': git_date, 'GIT_COMMITTER_DATE': git_date}
        
        try:
            subprocess.run([
                'git', 'commit',
                '-m', message
            ], check=True, capture_output=True, env=env, timeout=GIT_TIMEOUT)
            
            print(f"Git-commit skapad: '{message}' daterad {git_date}")
            
        except subprocess.CalledProcessError as e:
            print(f"Fel vid commit för {date}: {e}")
            if hasattr(e, 'stderr') and e.stderr:
                print(f"Git stderr: {e.stderr.decode('utf-8', errors='replace')}")
    
    # Restore original content after all commits
    try:
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(original_content)
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
            generate_commits(md_file, None, from_date, to_date, dry_run)
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
        generate_commits(path, None, args.from_date, args.to_date, args.dry_run)
    elif path.is_dir():
        generate_commits_for_directory(path, args.from_date, args.to_date, args.dry_run)
    else:
        print(f"Fel: {path} finns inte")