#!/usr/bin/env python3
"""
Convert Swedish legal documents from JSON to Markdown with YAML front matter.

This script processes JSON files containing Swedish legal documents (SFS) and
converts them to Markdown format with structured YAML front matter.

Usage:
    python convert_json_to_markdown.py [--input INPUT_DIR] [--output OUTPUT_DIR] [--no-year-folder]
    
    By default, all Markdown files are saved in year-based subdirectories in the output directory.
    Use the --no-year-folder flag to save all files directly in the output directory without creating
    year-based subdirectories.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from format_sfs_text_to_md import format_sfs_text
from sort_frontmatter import sort_frontmatter_properties


def format_yaml_value(value: Any) -> str:
    """Format a value for YAML output, only adding quotes when necessary according to YAML rules."""
    if value is None:
        return 'null'

    if isinstance(value, bool):
        return 'true' if value else 'false'

    if isinstance(value, (int, float)):
        return str(value)

    # Convert to string if not already
    if not isinstance(value, str):
        value = str(value)

    # Empty string needs quotes
    if not value:
        return '""'

    # Check if value needs quotes according to YAML rules
    needs_quotes = (
        # Starts with special YAML characters
        value[0] in '!&*|>@`#%{}[]' or
        # Contains special characters that could be interpreted as YAML syntax (but not simple dates)
        (any(char in value for char in ['[', ']', '{', '}', ',', '#', '`', '"', "'", '|', '>', '*', '&', '!', '%', '@']) or
         (':' in value and not re.match(r'^\d{4}:\d+$', value))) or  # Allow YYYY:NNN format and dates
        # Looks like a number, boolean, or null
        value.lower() in ['true', 'false', 'null', 'yes', 'no', 'on', 'off'] or
        re.match(r'^-?\d+\.?\d*$', value) or  # Numbers
        re.match(r'^-?\d+\.?\d*e[+-]?\d+$', value.lower()) or  # Scientific notation
        # Starts or ends with whitespace
        value != value.strip() or
        # Contains newlines
        '\n' in value or '\r' in value or
        # Starts with special sequences
        value.startswith(('<<', '---', '...', '- '))
    )

    if needs_quotes:
        # Use double quotes and escape any double quotes inside
        escaped_value = value.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{escaped_value}"'

    return value


def clean_text(text: Optional[str]) -> str:
    """Clean and format text content."""
    if not text:
        return ""
    
    # Remove extra whitespace and normalize line breaks
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def clean_rubrik(rubrik: Optional[str]) -> str:
    """Clean rubrik by removing beteckning in parentheses."""
    if not rubrik:
        return ""

    # Remove beteckning pattern in parentheses (e.g., "(1987:1185)")
    # Pattern matches parentheses containing year:number format
    cleaned = re.sub(r'\s*\(\d{4}:\d+\)\s*', '', rubrik)
    return clean_text(cleaned)


def format_datetime(dt_str: Optional[str]) -> Optional[str]:
    """Format datetime string to ISO format without timezone."""
    if not dt_str:
        return None
    
    try:
        # Parse the datetime and format it as date only
        if 'T' in dt_str:
            dt = datetime.fromisoformat(dt_str.split('T')[0])
        else:
            dt = datetime.fromisoformat(dt_str)
        return dt.strftime('%Y-%m-%d')
    except (ValueError, AttributeError):
        return dt_str


def extract_amendments(andringsforfattningar: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract and format amendment information."""
    amendments = []
    
    for amendment in andringsforfattningar:
        amendment_data = {
            'beteckning': amendment.get('beteckning'),
            'rubrik': clean_text(amendment.get('rubrik')),
            'ikraft_datum': format_datetime(amendment.get('ikraftDateTime')),
            'anteckningar': clean_text(amendment.get('anteckningar'))
        }
        
        # Only include non-empty amendments
        if amendment_data['beteckning']:
            amendments.append(amendment_data)
    
    return amendments


def create_markdown_content(data: Dict[str, Any]) -> str:
    """Create Markdown content with YAML front matter from JSON data."""

    # Extract main document information
    beteckning = data.get('beteckning', '')
    rubrik = clean_rubrik(data.get('rubrik', ''))

    # Extract dates
    publicerad_datum = format_datetime(data.get('publiceradDateTime'))
    ikraft_datum = format_datetime(data.get('ikraftDateTime'))

    # Extract utfardad_datum from fulltext
    fulltext_data = data.get('fulltext', {})
    utfardad_datum = format_datetime(fulltext_data.get('utfardadDateTime'))

    # Extract other metadata
    forarbeten = clean_text(data.get('forarbeten', ''))
    celex_nummer = data.get('celexnummer')
    eu_direktiv = data.get('eUdirektiv', False)

    # Extract organization information
    organisation_data = data.get('organisation', {})
    organisation = organisation_data.get('namn', '') if organisation_data else ''

    # Extract the main text content from nested structure
    innehall_text = fulltext_data.get('forfattningstext', 'No content available')

    # Ensure innehall_text is a string
    if innehall_text is None:
        innehall_text = 'No content available'

    # Extract amendments
    amendments = extract_amendments(data.get('andringsforfattningar', []))

    # Create YAML front matter
    yaml_front_matter = f"""---
beteckning: {format_yaml_value(beteckning)}
rubrik: {format_yaml_value(rubrik)}
departement: {format_yaml_value(organisation)}
"""

    # Add dates if they exist
    if publicerad_datum:
        yaml_front_matter += f"publicerad_datum: {format_yaml_value(publicerad_datum)}\n"
    if utfardad_datum:
        yaml_front_matter += f"utfardad_datum: {format_yaml_value(utfardad_datum)}\n"
    if ikraft_datum:
        yaml_front_matter += f"ikraft_datum: {format_yaml_value(ikraft_datum)}\n"

    # Add other metadata
    if forarbeten:
        yaml_front_matter += f"forarbeten: {format_yaml_value(forarbeten)}\n"
    if celex_nummer:
        yaml_front_matter += f"celex: {format_yaml_value(celex_nummer)}\n"

    # Add eu_direktiv only if it's true
    if eu_direktiv:
        yaml_front_matter += f"eu_direktiv: {format_yaml_value(eu_direktiv)}\n"

    # Add amendments if they exist
    if amendments:
        yaml_front_matter += "andringsforfattningar:\n"
        for amendment in amendments:
            yaml_front_matter += f"  - beteckning: {format_yaml_value(amendment['beteckning'])}\n"
            if amendment['rubrik']:
                yaml_front_matter += f"    rubrik: {format_yaml_value(amendment['rubrik'])}\n"
            if amendment['ikraft_datum']:
                yaml_front_matter += f"    ikraft_datum: {format_yaml_value(amendment['ikraft_datum'])}\n"
            if amendment['anteckningar']:
                yaml_front_matter += f"    anteckningar: {format_yaml_value(amendment['anteckningar'])}\n"
    
    yaml_front_matter += "---\n\n"
    
    # Sort the front matter properties
    try:
        yaml_front_matter = sort_frontmatter_properties(yaml_front_matter.rstrip() + '\n')
        yaml_front_matter += "\n\n"
    except ValueError as e:
        # If sorting fails, keep the original format
        print(f"Warning: Could not sort front matter: {e}")

    # Format the content text before creating the markdown body
    formatted_text = format_sfs_text(innehall_text)

    # Create Markdown body
    markdown_body = f"# {rubrik}\n\n" + formatted_text

    return yaml_front_matter + markdown_body

def convert_json_to_markdown(json_file_path: Path, output_dir: Path, year_as_folder: bool) -> None:
    """Convert a single JSON file to Markdown format."""
    
    # Read JSON file
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error reading {json_file_path}: {e}")
        return
    
    # Create Markdown content
    markdown_content = create_markdown_content(data)
    
    # Create output filename based on beteckning
    beteckning = data.get('beteckning', json_file_path.stem)

    # Extract year from beteckning (format is typically YYYY:NNN)
    year_match = re.search(r'(\d{4}):', beteckning)
    if not year_match:
        print(f"Error: Could not extract year from beteckning: {beteckning}")
        return

    year = year_match.group(1)

    if year_as_folder:
        # Create a subdirectory for each document based on year
        document_dir = output_dir / year
        document_dir.mkdir(exist_ok=True)
    else:
        document_dir = output_dir

    safe_filename = "sfs-" + re.sub(r'[^\w\-]', '-', beteckning) + '.md'
    output_file = document_dir / safe_filename
    
    # Write Markdown file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"Converted {json_file_path.name} -> {output_file}")
    except IOError as e:
        print(f"Error writing {output_file}: {e}")


def main():
    """Main function to process all JSON files in the json directory."""
    
    import sys
    import argparse

    # Set up argument parser
    parser = argparse.ArgumentParser(description='Convert SFS JSON files to Markdown.')
    parser.add_argument('--input', '-i', help='Input directory containing JSON files')
    parser.add_argument('--output', '-o', help='Output directory for Markdown files')
    parser.add_argument('--no-year-folder', dest='year_folder', action='store_false',
                        help='Do not create year-based subdirectories for documents')
    parser.set_defaults(year_folder=True)
    args = parser.parse_args()

    # Define paths
    script_dir = Path(__file__).parent

    # Check if custom input directory is provided as argument
    if args.input:
        json_dir = Path(args.input)
    elif len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        # For backward compatibility
        json_dir = Path(sys.argv[1])
    else:
        json_dir = script_dir / 'json'

    # Check if custom output directory is provided
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = script_dir / 'markdown'
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True)
    
    # Check if json directory exists
    if not json_dir.exists():
        print(f"Error: JSON directory {json_dir} does not exist")
        return
    
    # Find all JSON files
    json_files = list(json_dir.glob('*.json'))
    
    if not json_files:
        print(f"No JSON files found in {json_dir}")
        return
    
    print(f"Found {len(json_files)} JSON file(s) to convert from {json_dir}")
    print(f"Output will be saved to {output_dir}")
    
    # Convert each JSON file
    for json_file in json_files:
        convert_json_to_markdown(json_file, output_dir, args.year_folder)
    
    print(f"\nConversion complete! Markdown files saved to {output_dir}")


if __name__ == "__main__":
    main()
