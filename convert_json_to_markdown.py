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
import difflib
from format_sfs_text_to_md import format_sfs_text, apply_changes_to_sfs_text
from sort_frontmatter import sort_frontmatter_properties
from add_pdf_url_to_frontmatter import generate_pdf_url


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

    # Check if value is a URL - URLs should not be quoted
    if re.match(r'^https?://', value):
        return value

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
    cleaned = re.sub(r'\s*\(\d{4}:\d+\)\s*', ' ', rubrik)
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


def create_markdown_content(data: Dict[str, Any], paragraph_as_header: bool = True, enable_git: bool = False, verbose: bool = False) -> str:
    """Create Markdown content with YAML front matter from JSON data."""

    # Extract main document information
    beteckning = data.get('beteckning', '')
    rubrik = clean_rubrik(data.get('rubrik', ''))

    # Extract dates
    publicerad_datum = format_datetime(data.get('publiceradDateTime'))

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

    # Debug: Check if content is empty
    if not innehall_text.strip():
        print(f"Warning: Empty content for {beteckning}")

    # Extract amendments
    amendments = extract_amendments(data.get('andringsforfattningar', []))

    # Create YAML front matter
    yaml_front_matter = f"""---
beteckning: {format_yaml_value(beteckning)}
rubrik: {format_yaml_value(rubrik)}
departement: {format_yaml_value(organisation)}
"""

    # Add dates if they exist (ikraft_datum will be added separately if needed)
    if publicerad_datum:
        yaml_front_matter += f"publicerad_datum: {format_yaml_value(publicerad_datum)}\n"
    if utfardad_datum:
        yaml_front_matter += f"utfardad_datum: {format_yaml_value(utfardad_datum)}\n"

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
            # beteckning should not be quoted (it's in YYYY:NNN format)
            yaml_front_matter += f"  - beteckning: {amendment['beteckning']}\n"
            if amendment['rubrik']:
                yaml_front_matter += f"    rubrik: {format_yaml_value(amendment['rubrik'])}\n"
            if amendment['ikraft_datum']:
                yaml_front_matter += f"    ikraft_datum: {format_yaml_value(amendment['ikraft_datum'])}\n"
            if amendment['anteckningar']:
                yaml_front_matter += f"    anteckningar: {format_yaml_value(amendment['anteckningar'])}\n"
    
    # Generate PDF URL
    try:
        pdf_url = generate_pdf_url(beteckning, utfardad_datum, check_exists=False)
        if pdf_url:
            yaml_front_matter += f"pdf_url: {format_yaml_value(pdf_url)}\n"
    except (ValueError, TypeError, AttributeError) as e:
        print(f"Warning: Could not generate PDF URL for {beteckning}: {e}")

    yaml_front_matter += "---\n\n"
    
    # Sort the front matter properties
    try:
        sorted_yaml = sort_frontmatter_properties(yaml_front_matter.rstrip() + '\n')
        yaml_front_matter = sorted_yaml + "\n\n"
    except ValueError as e:
        # If sorting fails, keep the original format
        print(f"Warning: Could not sort front matter for {beteckning}: {e}")

    # Format the content text before creating the markdown body
    # First apply general SFS formatting
    formatted_text = format_sfs_text(innehall_text, paragraph_as_header)

    # Debug: Check if formatting resulted in empty text
    if not formatted_text.strip():
        print(f"Warning: Formatting resulted in empty text for {beteckning}")
        print(f"Original content length: {len(innehall_text)}")
        print(f"Original content preview: {innehall_text[:200]}...")
    else:
        print(f"Debug: Formatted text length for {beteckning}: {len(formatted_text)}")

    # Then apply changes handling based on amendments
    processed_text = apply_amendments_to_text(formatted_text, amendments, enable_git, verbose)

    print(f"Debug: Processed amendments text length for {beteckning}: {len(processed_text)}")

    # Create Markdown body
    markdown_body = f"# {rubrik}\n\n" + processed_text

    # Final debug check
    final_content = yaml_front_matter + markdown_body
    print(f"Debug: Final content length for {beteckning}: {len(final_content)}")

    return final_content

def convert_json_to_markdown(json_file_path: Path, output_dir: Path, year_as_folder: bool, paragraph_as_header: bool = True, enable_git: bool = False, verbose: bool = False) -> None:
    """Convert a single JSON file to Markdown format."""
    
    # Read JSON file
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error reading {json_file_path}: {e}")
        return
    
    # Create Markdown content
    markdown_content = create_markdown_content(data, paragraph_as_header, enable_git, verbose)

    # Add ikraft_datum to front matter if not in Git mode (Git mode handles this separately)
    if not enable_git:
        ikraft_datum = format_datetime(data.get('ikraftDateTime'))
        if ikraft_datum:
            markdown_content = add_ikraft_datum_to_markdown(markdown_content, ikraft_datum)
            try:
                # Extract just the front matter part for sorting
                if markdown_content.startswith('---'):
                    # Find the end of the front matter
                    front_matter_end = markdown_content.find('\n---\n', 3)
                    if front_matter_end != -1:
                        front_matter = markdown_content[:front_matter_end + 5]  # Include the closing ---\n
                        rest_of_content = markdown_content[front_matter_end + 5:]

                        # Sort only the front matter
                        sorted_front_matter = sort_frontmatter_properties(front_matter)
                        markdown_content = sorted_front_matter + rest_of_content
            except ValueError as e:
                print(f"Warning: Could not sort front matter after adding ikraft_datum for {data.get('beteckning', 'unknown')}: {e}")

    # Debug: Check final markdown content length
    print(f"Debug: Final markdown content length for {data.get('beteckning', 'unknown')}: {len(markdown_content)}")
    if len(markdown_content) < 1000:  # If suspiciously short, show preview
        print(f"Debug: Content preview because suspiciously short:\n{markdown_content[:500]}...")

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

        # Create Git commit if enabled and no amendments were processed
        if enable_git:
            import subprocess

            # Get main document metadata
            rubrik = data.get('rubrik', '')
            if rubrik:
                # Clean rubrik by removing beteckning in parentheses
                rubrik = re.sub(r'\s*\(\d{4}:\d+\)\s*', '', rubrik).strip()

            ikraft_datum = format_datetime(data.get('ikraftDateTime'))
            utfardad_datum = format_datetime(data.get('fulltext', {}).get('utfardadDateTime'))
            amendments = data.get('andringsforfattningar', [])

            # Only create main commits if there are no amendments (they handle their own commits)
            if not amendments and utfardad_datum:
                try:
                    # First commit: without ikraft_datum in front matter, dated utfardad_datum
                    commit_message = rubrik if rubrik else f"SFS {beteckning}"

                    # Stage the current file (which doesn't have ikraft_datum yet)
                    subprocess.run(['git', 'add', str(output_file)], check=True, capture_output=True)

                    # Create first commit with utfardad_datum as date
                    subprocess.run([
                        'git', 'commit',
                        '-m', commit_message,
                        '--date', utfardad_datum
                    ], check=True, capture_output=True)

                    print(f"Git commit created: '{commit_message}' dated {utfardad_datum}")

                    # Second commit: add ikraft_datum to front matter if it exists
                    if ikraft_datum:
                        # Add ikraft_datum to the existing markdown content
                        markdown_content_with_ikraft = add_ikraft_datum_to_markdown(markdown_content, ikraft_datum)

                        # Sort front matter only
                        if markdown_content_with_ikraft.startswith('---'):
                            front_matter_end = markdown_content_with_ikraft.find('\n---\n', 3)
                            if front_matter_end != -1:
                                front_matter = markdown_content_with_ikraft[:front_matter_end + 5]
                                rest_of_content = markdown_content_with_ikraft[front_matter_end + 5:]
                                sorted_front_matter = sort_frontmatter_properties(front_matter)
                                markdown_content_with_ikraft = sorted_front_matter + rest_of_content

                        # Write updated file with ikraft_datum
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write(markdown_content_with_ikraft)

                        # Stage the updated file
                        subprocess.run(['git', 'add', str(output_file)], check=True, capture_output=True)

                        # Create second commit with ikraft_datum as date
                        subprocess.run([
                            'git', 'commit',
                            '-m', f"{beteckning} träder i kraft",
                            '--date', ikraft_datum
                        ], check=True, capture_output=True)

                        print(f"Git commit created: '{beteckning} träder i kraft' dated {ikraft_datum}")

                except subprocess.CalledProcessError as e:
                    print(f"Warning: Git commit failed for {beteckning}: {e}")
                except FileNotFoundError:
                    print("Warning: Git not found. Skipping Git commits.")

    except IOError as e:
        print(f"Error writing {output_file}: {e}")


def apply_amendments_to_text(text: str, amendments: List[Dict[str, Any]], enable_git: bool = False, verbose: bool = False) -> str:
    """
    Apply changes to SFS text based on amendment dates.

    This function processes each amendment in chronological order and applies
    changes using apply_changes_to_sfs_text with the amendment's ikraft_datum
    as the target date. Optionally creates Git commits for each amendment.

    Args:
        text (str): The original SFS text
        amendments (List[Dict[str, Any]]): List of amendments with ikraft_datum
        enable_git (bool): If True, create Git commits for each amendment
        verbose (bool): If True, print smart diff output to console for each amendment

    Returns:
        str: The text with changes applied
    """
    import subprocess

    processed_text = text

    # Sort amendments by ikraft_datum to apply changes in chronological order
    sorted_amendments = sorted(
        [a for a in amendments if a.get('ikraft_datum')],
        key=lambda x: x['ikraft_datum']
    )

    for amendment in sorted_amendments:
        ikraft_datum = amendment.get('ikraft_datum')
        rubrik = amendment.get('rubrik', 'Ändringsförfattning')
        beteckning = amendment.get('beteckning', 'Okänt')

        if ikraft_datum:
            # Store text before changes for debug comparison
            text_before_changes = processed_text

            processed_text = apply_changes_to_sfs_text(processed_text, ikraft_datum)

            # Debug output: show diff if enabled
            if verbose:
                print(f"\n{'='*60}")
                print(f"ÄNDRINGSFÖRFATTNING: {beteckning} ({ikraft_datum})")
                print(f"{'='*60}")

                # Create unified diff
                diff_lines = list(difflib.unified_diff(
                    text_before_changes.splitlines(keepends=True),
                    processed_text.splitlines(keepends=True),
                    fromfile=f"Före ändring {beteckning}",
                    tofile=f"Efter ändring {beteckning}",
                    lineterm=""
                ))

                if diff_lines:
                    print("TEXTÄNDRINGAR:")
                    for line in diff_lines:
                        # Color coding for different types of changes
                        line = line.rstrip()
                        if line.startswith('+++') or line.startswith('---'):
                            print(f"\033[1m{line}\033[0m")  # Bold
                        elif line.startswith('@@'):
                            print(f"\033[36m{line}\033[0m")  # Cyan
                        elif line.startswith('+'):
                            print(f"\033[32m{line}\033[0m")  # Green
                        elif line.startswith('-'):
                            print(f"\033[31m{line}\033[0m")  # Red
                        else:
                            print(line)
                else:
                    print("INGA TEXTÄNDRINGAR FUNNA.")

                print(f"{'='*60}\n")

            if enable_git:
                try:
                    # Throw error if rubrik is empty
                    if not rubrik:
                        raise ValueError("Rubrik cannot be empty for Git commit")

                    # Create Git commit with amendment rubrik and ikraft_datum as date
                    commit_message = rubrik

                    # Stage all changes
                    subprocess.run(['git', 'add', '.'], check=True, capture_output=True)

                    # Create commit with specific date
                    subprocess.run([
                        'git', 'commit',
                        '-m', commit_message,
                        '--date', ikraft_datum
                    ], check=True, capture_output=True)

                    print(f"Git commit created: '{commit_message}' dated {ikraft_datum}")

                except subprocess.CalledProcessError as e:
                    print(f"Warning: Git commit failed for amendment dated {ikraft_datum}: {e}")
                except FileNotFoundError:
                    print("Warning: Git not found. Skipping Git commits.")

    return processed_text


def add_ikraft_datum_to_markdown(markdown_content: str, ikraft_datum: str) -> str:
    """
    Add ikraft_datum to the YAML front matter of existing markdown content.
    Simply inserts the field before the closing --- of the front matter.
    """
    # Find the position of the closing --- and insert before it
    closing_marker = '\n---\n'
    if closing_marker in markdown_content:
        before_closing, after_closing = markdown_content.split(closing_marker, 1)
        ikraft_line = f"ikraft_datum: {format_yaml_value(ikraft_datum)}"
        return f"{before_closing}\n{ikraft_line}\n---\n{after_closing}"

    # Fallback: return original content if no proper front matter found
    return markdown_content

def main():
    """Main function to process all JSON files in the json directory."""
    
    import sys
    import argparse

    # Set up argument parser
    parser = argparse.ArgumentParser(description='Convert SFS JSON files to Markdown.')
    parser.add_argument('--input', '-i', help='Input directory containing JSON files')
    parser.add_argument('--output', '-o', help='Output directory for Markdown files')
    parser.add_argument('--filter', help='Filter files by year (YYYY) or specific beteckning (YYYY:NNN). Can be comma-separated list.')
    parser.add_argument('--no-year-folder', dest='year_folder', action='store_false',
                        help='Do not create year-based subdirectories for documents')
    parser.add_argument('--enable-git', action='store_true',
                        help='Create Git commits for each amendment with their ikraft_datum as commit date')
    parser.add_argument('--verbose', action='store_true',
                        help='Show detailed diff output for each amendment processing')
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
    
    # Apply filter if specified
    if args.filter:
        original_count = len(json_files)
        json_files = filter_json_files(json_files, args.filter)
        print(f"Filter '{args.filter}' applied: {len(json_files)} of {original_count} files selected")

        if not json_files:
            print("No files match the filter criteria")
            return

    print(f"Found {len(json_files)} JSON file(s) to convert from {json_dir}")
    print(f"Output will be saved to {output_dir}")
    
    # Convert each JSON file
    for json_file in json_files:
        convert_json_to_markdown(json_file, output_dir, args.year_folder, True, args.enable_git, args.verbose)
    
    print(f"\nConversion complete! Markdown files saved to {output_dir}")


def filter_json_files(json_files: List[Path], filter_criteria: str) -> List[Path]:
    """
    Filter JSON files based on filename containing year or ID patterns.

    Args:
        json_files: List of JSON file paths
        filter_criteria: Filter string containing years (YYYY) or IDs (YYYY:NNN)
                        Can be comma-separated for multiple criteria

    Returns:
        List[Path]: Filtered list of JSON files
    """
    if not filter_criteria:
        return json_files

    # Parse filter criteria - split by comma and strip whitespace
    criteria = [c.strip() for c in filter_criteria.split(',') if c.strip()]

    filtered_files = []

    for json_file in json_files:
        filename = json_file.stem  # Get filename without extension

        # Check if filename matches any of the criteria
        for criterion in criteria:
            # Check for exact beteckning match (YYYY:NNN format)
            if ':' in criterion and criterion.replace(':', '-') in filename:
                filtered_files.append(json_file)
                break
            # Check for year match (YYYY format)
            elif ':' not in criterion and f"{criterion}-" in filename:
                filtered_files.append(json_file)
                break
            # Check for partial filename match (e.g., "sfs-2024-925" matches "sfs-2024-925.json")
            elif criterion in filename:
                filtered_files.append(json_file)
                break

    return filtered_files


if __name__ == "__main__":
    main()
