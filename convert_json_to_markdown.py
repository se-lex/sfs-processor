#!/usr/bin/env python3
"""
Convert Swedish legal documents from JSON to Markdown with YAML front matter.

This script processes JSON files containing Swedish legal documents (SFS) and
converts them to Markdown format with structured YAML front matter.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


def clean_text(text: Optional[str]) -> str:
    """Clean and format text content."""
    if not text:
        return ""
    
    # Remove extra whitespace and normalize line breaks
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def format_datetime(dt_str: Optional[str]) -> Optional[str]:
    """Format datetime string to ISO format without timezone."""
    if not dt_str:
        return None
    
    try:
        # Parse the datetime and format it without timezone info
        dt = datetime.fromisoformat(dt_str.replace('T00:00:00', ''))
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
            'anteckningar': clean_text(amendment.get('anteckningar')),
            'ikraft_datum': format_datetime(amendment.get('ikraftDateTime')),
            'publicerings_ar': amendment.get('publiceringsar'),
            'lopnummer': amendment.get('lopnummer')
        }
        
        # Only include non-empty amendments
        if amendment_data['beteckning']:
            amendments.append(amendment_data)
    
    return amendments


def create_markdown_content(data: Dict[str, Any]) -> str:
    """Create Markdown content with YAML front matter from JSON data."""

    # Extract main document information
    beteckning = data.get('beteckning', '')
    rubrik = clean_text(data.get('rubrik', ''))
    departement = clean_text(data.get('departement', ''))

    # Extract dates
    beslutad_datum = format_datetime(data.get('beslutadDateTime'))
    publicerad_datum = format_datetime(data.get('publiceradDateTime'))
    ikraft_datum = format_datetime(data.get('ikraftDateTime'))

    # Extract other metadata
    forarbeten = clean_text(data.get('forarbeten', ''))
    celex_nummer = data.get('celexnummer')
    eu_direktiv = data.get('eUdirektiv', False)
    dokumenttyp = data.get('dokumenttyp', 'SFS')

    # Extract the main text content from nested structure
    fulltext_data = data.get('fulltext', {})
    innehall_text = fulltext_data.get('forfattningstext', 'No content available')

    # Extract amendments
    amendments = extract_amendments(data.get('andringsforfattningar', []))

    # Create YAML front matter
    yaml_front_matter = f"""---
beteckning: "{beteckning}"
rubrik: "{rubrik}"
departement: "{departement}"
dokumenttyp: "{dokumenttyp}"
"""

    # Add dates if they exist
    if beslutad_datum:
        yaml_front_matter += f"beslutad_datum: {beslutad_datum}\n"
    if publicerad_datum:
        yaml_front_matter += f"publicerad_datum: {publicerad_datum}\n"
    if ikraft_datum:
        yaml_front_matter += f"ikraft_datum: {ikraft_datum}\n"

    # Add other metadata
    if forarbeten:
        yaml_front_matter += f"forarbeten: \"{forarbeten}\"\n"
    if celex_nummer:
        yaml_front_matter += f"celex: \"{celex_nummer}\"\n"

    yaml_front_matter += f"eu_direktiv: {str(eu_direktiv).lower()}\n"

    # Add amendments if they exist
    if amendments:
        yaml_front_matter += "andringsforfattningar:\n"
        for amendment in amendments:
            yaml_front_matter += f"  - beteckning: \"{amendment['beteckning']}\"\n"
            if amendment['rubrik']:
                yaml_front_matter += f"    rubrik: \"{amendment['rubrik']}\"\n"
            if amendment['anteckningar']:
                yaml_front_matter += f"    anteckningar: \"{amendment['anteckningar']}\"\n"
            if amendment['ikraft_datum']:
                yaml_front_matter += f"    ikraft_datum: {amendment['ikraft_datum']}\n"
            if amendment['publicerings_ar']:
                yaml_front_matter += f"    publicerings_ar: \"{amendment['publicerings_ar']}\"\n"
            if amendment['lopnummer']:
                yaml_front_matter += f"    lopnummer: \"{amendment['lopnummer']}\"\n"
    
    yaml_front_matter += "---\n\n"
    
    # Create Markdown body
    markdown_body = f"# {rubrik}\n\n" + innehall_text

    return yaml_front_matter + markdown_body

def convert_json_to_markdown(json_file_path: Path, output_dir: Path) -> None:
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
    safe_filename = re.sub(r'[^\w\-]', '-', beteckning) + '.md'
    output_file = output_dir / safe_filename
    
    # Write Markdown file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"Converted {json_file_path.name} -> {output_file.name}")
    except IOError as e:
        print(f"Error writing {output_file}: {e}")


def main():
    """Main function to process all JSON files in the json directory."""
    
    # Define paths
    script_dir = Path(__file__).parent
    json_dir = script_dir / 'json'
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
    
    print(f"Found {len(json_files)} JSON file(s) to convert")
    
    # Convert each JSON file
    for json_file in json_files:
        convert_json_to_markdown(json_file, output_dir)
    
    print(f"\nConversion complete! Markdown files saved to {output_dir}")


if __name__ == "__main__":
    main()
