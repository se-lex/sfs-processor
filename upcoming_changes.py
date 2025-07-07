#!/usr/bin/env python3
"""
Module for identifying upcoming changes in Swedish legal documents in Selex markup.

This module provides functionality to extract effective dates (ikraft) and 
expiration dates (upphor) from Markdown files with Selex section tags and YAML front matter.
"""

import re
import yaml
from datetime import datetime
from typing import List, Dict
from pathlib import Path

UPCOMING_CHANGES_FILE_NAME = "kommande.tsv"


def identify_upcoming_changes(markdown_content: str) -> List[Dict[str, str]]:
    """
    Identify upcoming changes in a markdown document by extracting effective dates
    and expiration dates from both front matter and section tags.
    
    This function searches for:
    1. ikraft_datum in the YAML front matter
    2. selex:ikraft_datum and selex:upphor_datum in section tags
    3. selex:status with corresponding date attributes
    
    Args:
        markdown_content: The markdown content to analyze
        
    Returns:
        List of dictionaries containing date information with keys:
        - 'type': 'ikraft' or 'upphor'
        - 'date': The date in YYYY-MM-DD format
        - 'source': 'frontmatter' or 'section_tag'
        - 'section_id': Section ID if available, None otherwise
        
    Example:
        >>> content = '''---
        ... ikraft_datum: 2025-01-01
        ... ---
        ... <section id="1§" selex:status="ikraft" selex:ikraft_datum="2025-02-01">
        ... '''
        >>> changes = identify_upcoming_changes(content)
        >>> len(changes)
        2
    """
    changes = []
    
    # Extract front matter
    if markdown_content.startswith('---'):
        try:
            # Find the end of front matter
            end_marker = markdown_content.find('\n---\n', 4)
            if end_marker != -1:
                front_matter_text = markdown_content[4:end_marker]
                front_matter = yaml.safe_load(front_matter_text)
                
                # Extract ikraft_datum from front matter
                if 'ikraft_datum' in front_matter and front_matter['ikraft_datum']:
                    ikraft_date = str(front_matter['ikraft_datum'])
                    # Ensure date format is YYYY-MM-DD
                    if len(ikraft_date) == 10 and ikraft_date.count('-') == 2:
                        changes.append({
                            'type': 'ikraft',
                            'date': ikraft_date,
                            'source': 'frontmatter',
                            'section_id': None
                        })
        except yaml.YAMLError:
            pass  # Ignore YAML parsing errors
    
    # Extract dates from section tags using regex
    
    # Pattern for section tags with selex attributes - ikraft_datum and upphor_datum
    section_pattern = r'<section[^>]*selex:(ikraft_datum|upphor_datum)="([^"]+)"[^>]*(?:id="([^"]*)")?[^>]*>'
    section_matches = re.finditer(section_pattern, markdown_content)
    
    for match in section_matches:
        attribute_name = match.group(1)
        date_value = match.group(2)
        section_id = match.group(3) if match.group(3) else None
        
        # Extract ikraft_datum and upphor_datum from section tags
        if attribute_name == 'ikraft_datum':
            date_type = 'ikraft'
        elif attribute_name == 'upphor_datum':
            date_type = 'upphor'
        else:
            continue  # Skip other date types
            
        # Validate date format
        if len(date_value) == 10 and date_value.count('-') == 2:
            try:
                # Verify it's a valid date
                datetime.strptime(date_value, '%Y-%m-%d')
                changes.append({
                    'type': date_type,
                    'date': date_value,
                    'source': 'section_tag',
                    'section_id': section_id
                })
            except ValueError:
                pass  # Skip invalid dates
    
    # Also look for simpler selex:status patterns with dates in separate attributes
    status_pattern = r'<section[^>]*selex:status="(ikraft|upphor)"[^>]*selex:(?:ikraft_datum|upphor_datum)="([^"]+)"[^>]*(?:id="([^"]*)")?[^>]*>'
    status_matches = re.finditer(status_pattern, markdown_content)
    
    for match in status_matches:
        status = match.group(1)
        date_value = match.group(2)
        section_id = match.group(3) if match.group(3) else None
        
        # Only process ikraft and upphor status
        if status not in ['ikraft', 'upphor']:
            continue
        
        # Validate date format
        if len(date_value) == 10 and date_value.count('-') == 2:
            try:
                # Verify it's a valid date
                datetime.strptime(date_value, '%Y-%m-%d')
                # Check if we already have this entry to avoid duplicates
                duplicate = False
                for existing in changes:
                    if (existing['type'] == status and 
                        existing['date'] == date_value and 
                        existing['section_id'] == section_id):
                        duplicate = True
                        break
                
                if not duplicate:
                    changes.append({
                        'type': status,
                        'date': date_value,
                        'source': 'section_tag',
                        'section_id': section_id
                    })
            except ValueError:
                pass  # Skip invalid dates
    
    # Remove duplicates while preserving order
    unique_changes = []
    seen = set()
    for change in changes:
        # Create a key for deduplication (type + date + section_id)
        key = (change['type'], change['date'], change.get('section_id'))
        if key not in seen:
            seen.add(key)
            unique_changes.append(change)
    
    # Sort by date
    unique_changes.sort(key=lambda x: x['date'])
    
    return unique_changes


def save_upcoming_file(doc_id: str, dates: List[str]) -> None:
    """
    Save upcoming changes to a TSV file with dates and document IDs.
    
    The TSV format is:
    - First column: Date (YYYY-MM-DD)
    - Second column: Comma-separated list of document IDs (beteckningar) without quotes
    
    Args:
        doc_id: The document ID (beteckning) to add
        dates: List of dates in YYYY-MM-DD format
    """
    file_path = Path(UPCOMING_CHANGES_FILE_NAME)
    
    # Read existing data if file exists
    existing_data = {}
    if file_path.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and '\t' in line:
                        parts = line.split('\t', 1)  # Split on first tab only
                        if len(parts) >= 2:
                            date = parts[0].strip()
                            # Parse doc_ids from second column (comma-separated)
                            doc_ids = [id.strip() for id in parts[1].split(',') if id.strip()]
                            existing_data[date] = doc_ids
        except IOError as e:
            print(f"Varning: Kunde inte läsa befintlig fil {UPCOMING_CHANGES_FILE_NAME}: {e}")
    
    # Process each date
    for date in dates:
        date = date.strip()
        
        # Validate date format
        if not (len(date) == 10 and date.count('-') == 2):
            print(f"Varning: Ogiltigt datumformat: {date}")
            continue
            
        try:
            # Verify it's a valid date
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            print(f"Varning: Ogiltigt datum: {date}")
            continue
        
        # Add date to existing data or create new entry
        if date in existing_data:
            # Check if doc_id is not already in the list
            if doc_id not in existing_data[date]:
                existing_data[date].append(doc_id)
        else:
            # Create new entry for this date
            existing_data[date] = [doc_id]
    
    # Sort dates chronologically
    sorted_dates = sorted(existing_data.keys())
    
    # Write the updated data back to file
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            for date in sorted_dates:
                doc_ids_str = ','.join(existing_data[date])
                f.write(f"{date}\t{doc_ids_str}\n")
        
    except IOError as e:
        print(f"Fel: Kunde inte skriva till fil {UPCOMING_CHANGES_FILE_NAME}: {e}")


def get_doc_ids_for_date(date: str) -> List[str]:
    """
    Get document IDs that have changes on a specific date.
    
    Args:
        date: The date to look for in YYYY-MM-DD format
        
    Returns:
        List of document IDs (beteckningar) that have changes on the specified date.
        Returns empty list if date not found or file doesn't exist.
        
    Example:
        >>> doc_ids = get_doc_ids_for_date('2025-01-15')
        >>> print(doc_ids)
        ['sfs-2024-1274', 'sfs-2024-1275']
    """
    file_path = Path(UPCOMING_CHANGES_FILE_NAME)
    
    # Validate date format
    if not (len(date) == 10 and date.count('-') == 2):
        print(f"Varning: Ogiltigt datumformat: {date}")
        return []
        
    try:
        # Verify it's a valid date
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        print(f"Varning: Ogiltigt datum: {date}")
        return []
    
    # Check if file exists
    if not file_path.exists():
        return []
    
    # Read file and look for the date
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and '\t' in line:
                    parts = line.split('\t', 1)  # Split on first tab only
                    if len(parts) >= 2:
                        file_date = parts[0].strip()
                        if file_date == date:
                            # Parse doc_ids from second column (comma-separated)
                            doc_ids = [id.strip() for id in parts[1].split(',') if id.strip()]
                            return doc_ids
    except IOError as e:
        print(f"Fel: Kunde inte läsa fil {UPCOMING_CHANGES_FILE_NAME}: {e}")
        return []
    
    # Date not found
    return []


def extract_doc_id_from_filename(filename: str) -> str:
    """
    Extract document ID from filename.
    
    Args:
        filename: The filename (e.g., 'sfs-2024-1274.md')
        
    Returns:
        Document ID without extension (e.g., '2024:1274')
    """
    # Remove .md extension if present
    name = filename
    if name.endswith('.md'):
        name = name[:-3]
    
    # Convert sfs-YYYY-NNNN format to YYYY:NNNN
    if name.startswith('sfs-'):
        parts = name.split('-')
        if len(parts) >= 3:
            year = parts[1]
            number = parts[2]
            return f"{year}:{number}"
    
    return name


def process_markdown_files(input_dir: str) -> None:
    """
    Process all markdown files in the input directory and extract upcoming changes.
    
    Args:
        input_dir: Path to directory containing markdown files
    """
    input_path = Path(input_dir)
    
    if not input_path.exists():
        print(f"Fel: Katalogen {input_dir} finns inte.")
        return
    
    if not input_path.is_dir():
        print(f"Fel: {input_dir} är inte en katalog.")
        return
    
    # Find all .md files recursively
    md_files = list(input_path.rglob("*.md"))
    
    if not md_files:
        print(f"Inga markdown-filer hittades i {input_dir}")
        return
    
    print(f"Hittat {len(md_files)} markdown-filer i {input_dir}")
    
    total_changes = 0
    processed_files = 0
    
    for md_file in md_files:
        try:
            # Read the markdown file
            with open(md_file, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Identify upcoming changes
            file_changes = identify_upcoming_changes(content)
            
            if file_changes:
                # Extract document ID from filename
                doc_id = extract_doc_id_from_filename(md_file.name)
                
                # Extract dates from changes
                change_dates = [change['date'] for change in file_changes]
                
                # Save to TSV file
                save_upcoming_file(doc_id, change_dates)
                
                print(f"Processade {md_file.name}: {len(file_changes)} ändringar hittades")
                for change in file_changes:
                    print(f"  - {change['type']}: {change['date']} ({change['source']})")
                
                total_changes += len(file_changes)
            else:
                print(f"Processade {md_file.name}: inga kommande ändringar")
            
            processed_files += 1
            
        except (IOError, OSError, UnicodeDecodeError) as e:
            print(f"Fel vid processning av {md_file}: {e}")
    
    print("\nSammanfattning:")
    print(f"Processade {processed_files} filer")
    print(f"Totalt {total_changes} kommande ändringar hittades")
    print(f"Resultat sparade i {UPCOMING_CHANGES_FILE_NAME}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Användning: python upcoming_changes.py <input_dir>")
        print("Exempel: python upcoming_changes.py sfs-test/")
        sys.exit(1)
    
    input_directory = sys.argv[1]
    process_markdown_files(input_directory)
