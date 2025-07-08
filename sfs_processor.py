#!/usr/bin/env python3
"""
Process Swedish legal documents (SFS) from JSON to         # Create markdown document (git mode is enabled if "git" is in output_modes)
        enable_git = "git" in output_modes
        _create_markdown_document(data, document_dir, enable_git, verbose) output formats.

This script processes JSON files containing Swedish legal documents from the
Swedish Code of Statutes (SFS) and converts them to various output formats
including Markdown with YAML front matter, with optional Git history recreation.

Usage:
    python sfs_processor.py [--input INPUT_DIR] [--output OUTPUT_DIR] [--formats FORMATS] [--no-year-folder]
    
    By default, documents are saved as Markdown files in year-based subdirectories.
    Use --formats to specify output modes (e.g., "md,git,html,htmldiff" or "md-markers" for multiple formats).
    HTML format creates documents in ELI directory structure with year-based folders.
    Use --no-year-folder to save files directly in output directory without year subdirectories.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from formatters.format_sfs_text import format_sfs_text_as_markdown, parse_logical_sections, clean_section_tags, clean_text
from formatters.sort_frontmatter import sort_frontmatter_properties
from formatters.add_pdf_url_to_frontmatter import generate_pdf_url
from formatters.frontmatter_manager import add_ikraft_datum_to_frontmatter
from util.yaml_utils import format_yaml_value
from util.datetime_utils import format_datetime, format_datetime_for_git
from util.file_utils import filter_json_files, save_to_disk
from util.predocs_parser import parse_predocs_string
from downloaders.riksdagen_api import fetch_predocs_details, format_predocs_for_frontmatter
from exporters.git import ensure_git_branch_for_commits, restore_original_branch
from temporal.amendments import process_markdown_amendments, extract_amendments


def make_document(data: Dict[str, Any], output_dir: Path, output_modes: List[str] = None, year_as_folder: bool = True, verbose: bool = False, git_branch: str = None, fetch_predocs: bool = False) -> None:
    """Create documents by converting JSON to specified output formats and applying amendments.

    This is the main function for document creation that handles:
    - Output directory structure based on beteckning year and year_as_folder setting
    - Coordination of different output formats and modes:
      * "md": Generate markdown files with clean output (section tags removed)
      * "md-markers": Generate markdown files with section tags preserved
      * "git": Enable Git commits with historical dates during markdown generation
      * "html": Generate HTML files in ELI structure (base document only)
      * "htmldiff": Generate HTML files in ELI structure (base document plus amendment versions)
    - Delegates actual file creation to format-specific internal functions

    The function extracts the year from the beteckning and creates appropriate directory
    structure, then calls internal creation functions that handle the actual content
    generation and file writing for each requested format.

    Args:
        data: JSON data for the document
        output_dir: Directory where output files should be saved
        output_modes: List of formats/modes to use (e.g., ["md", "git"]). If None, defaults to ["md"]
                     Note: "git" mode requires "md" mode to be included as it modifies markdown processing
                     "md" generates clean markdown (section tags removed), "md-markers" preserves section tags
                     "html" generates base document only, "htmldiff" includes amendment versions
                     All HTML output uses ELI directory structure with year-based folders
        year_as_folder: Whether to create year-based subdirectories (default: True)
        verbose: Whether to show verbose output (default: False)
        git_branch: Branch name to use for git commits. If contains "(date)", it will be replaced
                   with current date. Only used when "git" is in output_modes.
        fetch_predocs: Whether to fetch detailed information about förarbeten from Riksdagen API (default: False)
    """

    # Default to markdown output if no modes specified
    if output_modes is None:
        output_modes = ["md"]

    # Git mode requires markdown mode to be active
    if "git" in output_modes and "md" not in output_modes:
        output_modes.append("md")
        if verbose:
            print("Info: Lade till 'md'-läge eftersom 'git'-läge kräver markdown-generering")

    # Extract beteckning for output file naming
    beteckning = data.get('beteckning', '')

    # Skip documents with beteckning starting with 'N' (notifications etc.)
    if beteckning and beteckning.startswith('N'):
        print(f"Varning: Hoppar över beteckning som börjar med 'N': {beteckning}")
        return

    # Extract year from beteckning (format is typically YYYY:NNN)
    year_match = re.search(r'(\d{4}):', beteckning)
    if not year_match:
        if "md" in output_modes:
            print(f"Fel: Kunde inte extrahera år från beteckning: {beteckning}")
        return

    year = year_match.group(1)

    # Determine output directory based on year_as_folder setting
    if year_as_folder:
        document_dir = output_dir / year
        document_dir.mkdir(exist_ok=True)
    else:
        document_dir = output_dir

    # Process markdown format if requested
    if "md" in output_modes:
        # Create markdown document (pass git_branch if "git" is in output_modes)
        git_branch_param = git_branch if "git" in output_modes else None
        markdown_content = _create_markdown_document(data, document_dir, git_branch_param, False, verbose, fetch_predocs)

    # Process markdown with section markers if requested
    if "md-markers" in output_modes:
        # Create markdown document with section tags preserved
        markdown_content = _create_markdown_document(data, document_dir, None, True, verbose, fetch_predocs)

    # Process HTML format if requested
    if "html" in output_modes:
        from exporters.html.html_export import create_html_documents
        create_html_documents(data, output_dir, include_amendments=False)

    # Process HTML diff format if requested
    if "htmldiff" in output_modes:
        from exporters.html.html_export import create_html_documents
        create_html_documents(data, output_dir, include_amendments=True)


def _create_markdown_document(data: Dict[str, Any], output_path: Path, git_branch: str = None, preserve_section_tags: bool = False, verbose: bool = False, fetch_predocs: bool = False) -> str:
    """Internal function to create a markdown document from JSON data.

    Args:
        data: JSON data containing document information
        output_path: Path to the output directory (folder)
        git_branch: Branch name to use for git commits. If None, no git commits are made.
                   If contains "(date)", it will be replaced with current date.
        preserve_section_tags: Whether to preserve <section> tags in output (for md-markers mode)
        verbose: Whether to print verbose output
        fetch_predocs: Whether to fetch detailed information about förarbeten from Riksdagen API

    Returns:
        str: The final markdown content that was written to file
    """

    # Extract beteckning to create safe filename
    beteckning = data.get('beteckning', '')
    if preserve_section_tags:
        safe_filename = "sfs-" + re.sub(r'[^\w\-]', '-', beteckning) + '-markers.md'
    else:
        safe_filename = "sfs-" + re.sub(r'[^\w\-]', '-', beteckning) + '.md'
    output_file = output_path / safe_filename

    # Get basic markdown content
    markdown_content = convert_to_markdown(data, fetch_predocs)

    # Extract beteckning for logging
    beteckning = data.get('beteckning', '')

    # Process amendments using the temporal module
    markdown_content = process_markdown_amendments(markdown_content, data, git_branch, verbose, output_file)
    
    # Extract amendments for git logic (if needed)
    amendments = extract_amendments(data.get('andringsforfattningar', []))

    # Determine if git functionality is enabled
    git_enabled = git_branch is not None

    # Add ikraft_datum to front matter if not in Git mode
    if not git_enabled:
        ikraft_datum = format_datetime(data.get('ikraftDateTime'))
        if ikraft_datum:
            markdown_content = add_ikraft_datum_to_frontmatter(markdown_content, ikraft_datum, beteckning)

    # Debug: Check final markdown content length
    if verbose:
        print(f"Debug: Slutlig markdown-innehållslängd för {beteckning}: {len(markdown_content)}")
        if len(markdown_content) < 1000:  # If suspiciously short, show preview
            print(f"Debug: Innehållsförhandsvisning eftersom misstänkt kort:\n{markdown_content[:500]}...")

    # Handle git commits if enabled
    final_content = markdown_content
    if git_enabled:
        import subprocess

        # Get main document metadata
        rubrik = data.get('rubrik', '')

        ikraft_datum = format_datetime(data.get('ikraftDateTime'))
        utfardad_datum = format_datetime(data.get('fulltext', {}).get('utfardadDateTime'))

        # Only create main commit if there are no amendments (they handle their own commits)
        if not amendments and utfardad_datum:
            # Ensure commits are made in a different branch
            original_branch, commit_branch = ensure_git_branch_for_commits(git_branch, remove_all_commits_first=True, verbose=verbose)

            # Only proceed with git commits if branch creation was successful
            if original_branch is not None and commit_branch is not None:
                try:
                    # First commit: without ikraft_datum in front matter, dated utfardad_datum
                    commit_message = rubrik if rubrik else f"SFS {beteckning}"
                    
                    # Add förarbeten if available
                    register_data = data.get('register', {})
                    predocs = register_data.get('forarbeten')
                    if predocs:
                        commit_message += f"\n\nHar tillkommit i Svensk författningssamling efter dessa förarbeten: {predocs}"

                    # Write file for first commit (without ikraft_datum)
                    save_to_disk(output_file, markdown_content)
                    
                    # Debug: Check if file exists
                    if verbose and not output_file.exists():
                        print(f"Varning: Filen {output_file} existerar inte efter save_to_disk")

                    # Stage the current file (which doesn't have ikraft_datum yet)
                    subprocess.run(['git', 'add', str(output_file)], check=True, capture_output=True)

                    # Check if there are any changes to commit
                    result = subprocess.run(['git', 'diff', '--cached', '--quiet'], capture_output=True)
                    if result.returncode != 0:  # Non-zero means there are changes
                        # Create first commit with utfardad_datum as date for both author and committer
                        utfardad_datum_git = format_datetime_for_git(utfardad_datum) if utfardad_datum else None
                        env = {**os.environ, 'GIT_AUTHOR_DATE': utfardad_datum_git, 'GIT_COMMITTER_DATE': utfardad_datum_git}
                        subprocess.run([
                            'git', 'commit',
                            '-m', commit_message
                        ], check=True, capture_output=True, env=env)
                        print(f"Git-commit skapad: '{commit_message}' daterad {utfardad_datum_git}")
                    else:
                        print(f"Inga ändringar att commita för första commit av {beteckning}")

                    # Second commit: add ikraft_datum to front matter if it exists
                    if ikraft_datum:
                        # Add ikraft_datum and sort front matter
                        markdown_content_with_ikraft = add_ikraft_datum_to_frontmatter(markdown_content, ikraft_datum, beteckning)

                        # Write updated file with ikraft_datum
                        save_to_disk(output_file, markdown_content_with_ikraft)

                        # Stage the updated file
                        subprocess.run(['git', 'add', str(output_file)], check=True, capture_output=True)

                        # Check if there are any changes to commit
                        result = subprocess.run(['git', 'diff', '--cached', '--quiet'], capture_output=True)
                        if result.returncode != 0:  # Non-zero means there are changes
                            # Create second commit with ikraft_datum as date for both author and committer
                            ikraft_datum_git = format_datetime_for_git(ikraft_datum) if ikraft_datum else None
                            env = {**os.environ, 'GIT_AUTHOR_DATE': ikraft_datum_git, 'GIT_COMMITTER_DATE': ikraft_datum_git}
                            subprocess.run([
                                'git', 'commit',
                                '-m', f"{beteckning} träder i kraft" # TODO: Se till att committa förarbeten först
                            ], check=True, capture_output=True, env=env)
                            print(f"Git-commit skapad: '{beteckning} träder i kraft' daterad {ikraft_datum_git}")
                        else:
                            print(f"Inga ändringar att commita för ikraft_datum av {beteckning}")

                        # Use the content with ikraft_datum as final content
                        final_content = markdown_content_with_ikraft

                    # Push the new branch to remote
                    try:
                        subprocess.run(['git', 'push', 'origin', commit_branch], check=True, capture_output=True)
                        print(f"Pushade branch '{commit_branch}' till remote")
                    except subprocess.CalledProcessError as e:
                        print(f"Varning: Kunde inte pusha branch '{commit_branch}': {e}")

                except subprocess.CalledProcessError as e:
                    print(f"Varning: Git-commit misslyckades för {beteckning}: {e}")
                    # Print stderr output for debugging
                    if hasattr(e, 'stderr') and e.stderr:
                        print(f"Git stderr: {e.stderr.decode('utf-8', errors='replace')}")
                    # Clean section tags if not preserving them
                    final_content = markdown_content
                    if not preserve_section_tags:
                        final_content = clean_section_tags(final_content)
                    # Write the file anyway, without git commits
                    save_to_disk(output_file, final_content)
                    # Restore original branch on error
                    restore_original_branch(original_branch)
                except FileNotFoundError:
                    print("Varning: Git hittades inte. Hoppar över Git-commits.")
                    # Clean section tags if not preserving them
                    final_content = markdown_content
                    if not preserve_section_tags:
                        final_content = clean_section_tags(final_content)
                    # Write the file anyway, without git commits
                    save_to_disk(output_file, final_content)
                    # Restore original branch on error
                    restore_original_branch(original_branch)
            else:
                # Clean section tags if not preserving them
                final_content = markdown_content
                if not preserve_section_tags:
                    final_content = clean_section_tags(final_content)
                # Branch creation failed, write file without git commits
                print(f"Hoppar över Git-commits för {beteckning} på grund av branch-problem")
                save_to_disk(output_file, final_content)
        else:
            # Clean section tags if not preserving them
            final_content = markdown_content
            if not preserve_section_tags:
                final_content = clean_section_tags(final_content)
            # Write file if git is enabled but no commits needed
            save_to_disk(output_file, final_content)
    else:
        # Clean section tags if not preserving them
        final_content = markdown_content
        if not preserve_section_tags:
            final_content = clean_section_tags(final_content)
        # No git mode - write the file normally
        save_to_disk(output_file, final_content)
        print(f"Skapade dokument: {output_file}")

    return final_content


def convert_to_markdown(data: Dict[str, Any], fetch_predocs: bool = False) -> str:
    """Convert JSON data to Markdown content with YAML front matter.

    This function only handles the conversion from JSON to markdown string format.
    It does NOT apply amendments or handle file operations - use make_document() for that.

    Args:
        data: JSON data for the document
        fetch_predocs: Whether to fetch detailed information about förarbeten from Riksdag API

    Returns:
        str: Markdown content with YAML front matter
    """

    # Extract main document information
    beteckning = data.get('beteckning', '')
    rubrik_original = data.get('rubrik', '')  # Keep original for main heading
    rubrik = clean_title(rubrik_original)    # Clean for front matter

    # Extract dates
    publicerad_datum = format_datetime(data.get('publiceradDateTime'))
    utgar_datum = format_datetime(data.get('tidsbegransadDateTime'))

    # Extract utfardad_datum from fulltext
    fulltext_data = data.get('fulltext', {})
    utfardad_datum = format_datetime(fulltext_data.get('utfardadDateTime'))

    # Extract other metadata
    register_data = data.get('register', {})
    predocs = clean_text(register_data.get('forarbeten', ''))
    celex_nummer = data.get('celexnummer')
    eu_direktiv = data.get('eUdirektiv', False)

    # Extract organization information
    organisation_data = data.get('organisation', {})
    organisation = organisation_data.get('namn', '') if organisation_data else ''

    # Extract the main text content from nested structure
    innehall_text = fulltext_data.get('forfattningstext')

    # Debug: Check if content is empty
    if not innehall_text or not innehall_text.strip():
        print(f"Varning: Tomt innehåll för {beteckning}")
        # Create a minimal valid document for empty content
        yaml_frontmatter = f"""---
beteckning: {beteckning}
rubrik: {data.get('rubrik', 'Okänd rubrik')}
---
# {data.get('rubrik', 'Okänd rubrik')}

*Detta dokument har inget innehåll i originalformatet.*
"""
        return yaml_frontmatter

    # Check ignore rules first
    should_ignore, ignore_reason = ignore_rules(innehall_text)
    ignored_body = None  # Ensure variable is always defined
    if should_ignore:
        print(f"Ignorerar {beteckning}: {ignore_reason}")
        # Generate normal front matter but use ignored content body
        ignored_body = create_ignored_markdown_content(data, ignore_reason)
        # Continue with normal front matter generation and use ignored body at the end
        should_use_ignored_body = True
    else:
        should_use_ignored_body = False

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
    if utgar_datum:
        yaml_front_matter += f"utgar_datum: {format_yaml_value(utgar_datum)}\n"

    # Add other metadata
    if predocs:
        if fetch_predocs:
            # Parse förarbeten and fetch detailed information
            try:
                parsed_predocs = parse_predocs_string(predocs)
                if parsed_predocs:
                    detailed_predocs = fetch_predocs_details(parsed_predocs)
                    formatted_predocs = format_predocs_for_frontmatter(detailed_predocs)
                    
                    if formatted_predocs:
                        yaml_front_matter += "forarbeten:\n"
                        for item in formatted_predocs:
                            yaml_front_matter += f"  - {format_yaml_value(item)}\n"
                    else:
                        # Fallback to original string if parsing failed
                        yaml_front_matter += f"forarbeten: {format_yaml_value(predocs)}\n"
                else:
                    # Fallback to original string if parsing failed
                    yaml_front_matter += f"forarbeten: {format_yaml_value(predocs)}\n"
            except Exception as e:
                print(f"Varning: Kunde inte hämta detaljerad förarbeten-information: {e}")
                # Fallback to original string
                yaml_front_matter += f"forarbeten: {format_yaml_value(predocs)}\n"
        else:
            # Just use the original string without fetching details
            yaml_front_matter += f"forarbeten: {format_yaml_value(predocs)}\n"
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
        print(f"Varning: Kunde inte generera PDF-URL för {beteckning}: {e}")

    yaml_front_matter += "---\n\n"

    # Sort the front matter properties
    try:
        sorted_yaml = sort_frontmatter_properties(yaml_front_matter.rstrip() + '\n')
        yaml_front_matter = sorted_yaml + "\n\n"
    except ValueError as e:
        print(f"Varning: Kunde inte sortera front matter för {beteckning}: {e}")

    # Create Markdown body
    if should_use_ignored_body and ignored_body is not None:
        # Use the ignored content body (already includes heading)
        markdown_body = ignored_body
    else:
        # Format the content text to markdown
        formatted_text = format_sfs_text_as_markdown(innehall_text)

        # Apply section tags
        formatted_text = parse_logical_sections(formatted_text)

        # Debug: Check if formatting resulted in empty text
        if not formatted_text.strip():
            print(f"Varning: Formatering resulterade i tom text för {beteckning}")
            print(f"Ursprunglig innehållslängd: {len(innehall_text)}")
            print(f"Ursprunglig innehållsförhandsvisning: {innehall_text[:200]}...")

        # Create Markdown body (clean the original rubrik for heading)
        clean_heading = re.sub(r'[\r\n]+', ' ', rubrik_original) if rubrik_original else ""
        clean_heading = re.sub(r'\s+', ' ', clean_heading).strip()
        markdown_body = f"# {clean_heading}\n\n" + formatted_text

    # Section tags are preserved in markdown_body - they will be cleaned later if needed

    # Return the complete markdown content
    return yaml_front_matter + markdown_body


def clean_title(rubrik: Optional[str]) -> str:
    """Clean rubrik by removing beteckning in parentheses and line breaks."""
    if not rubrik:
        return ""

    # Remove line breaks and carriage returns
    cleaned = re.sub(r'[\r\n]+', ' ', rubrik)
    
    # Remove beteckning pattern in parentheses (e.g., "(1987:1185)")
    # Pattern matches parentheses containing year:number format
    # First remove the parentheses and their content, then clean up extra whitespace
    cleaned = re.sub(r'\s*\(\d{4}:\d+\)\s*', ' ', cleaned)
    # Clean up any multiple spaces that might have been created
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def ignore_rules(innehall_text: str) -> tuple[bool, str]:
    """
    Kontrollera om dokumentet ska ignoreras baserat på specifika regler.

    Args:
        data: JSON-data för dokumentet
        innehall_text: Textinnehållet från dokumentet

    Returns:
        tuple: (should_ignore: bool, reason: str)
               - should_ignore: True om dokumentet ska ignoreras
               - reason: Förklaring till varför dokumentet ignorerades
    """
    # Regel 1: Kontrollera om texten innehåller "AVDELNING" i versaler
    # (inte "avdelning" eller "Avdelning" med gemener)
    if "AVDELNING" in innehall_text:
        return True, "Dokumentet innehåller AVDELNING-struktur som inte stöds för automatisk konvertering."

    # Lägg till fler regler här vid behov

    return False, ""


def create_ignored_markdown_content(data: Dict[str, Any], reason: str) -> str:
    """
    Skapa förenklad markdown-body för ignorerade dokument.

    Returnerar endast huvudinnehållet - YAML front matter hanteras av _create_markdown_document.

    Args:
        data: JSON-data för dokumentet
        reason: Förklaring till varför dokumentet ignorerades

    Returns:
        str: Förenklad markdown-body (utan front matter)
    """
    # Get the original rubrik for the heading and clean it
    rubrik_original = data.get('rubrik', '')
    clean_heading = re.sub(r'[\r\n]+', ' ', rubrik_original) if rubrik_original else ""
    clean_heading = re.sub(r'\s+', ' ', clean_heading).strip()

    # Create simplified body with main heading and explanation
    markdown_body = f"# {clean_heading}\n\n"
    markdown_body += "**Automatisk konvertering inte tillgänglig**\n\n"
    markdown_body += f"{reason}\n\n"
    markdown_body += "För att läsa det fullständiga dokumentet, besök den officiella versionen på "
    markdown_body += "[svenskforfattningssamling.se](https://svenskforfattningssamling.se/) "
    markdown_body += "eller ladda ner PDF:en från länken i front matter ovan.\n"

    return markdown_body


def main():
    """Main function to process all JSON files in the json directory."""
    
    import sys
    import argparse

    # Set up argument parser
    parser = argparse.ArgumentParser(description='Process SFS documents from JSON to various output formats.')
    parser.add_argument('--input', '-i', help='Input directory containing JSON files')
    parser.add_argument('--output', '-o', help='Output directory for processed files')
    parser.add_argument('--filter', help='Filter files by year (YYYY) or specific beteckning (YYYY:NNN). Can be comma-separated list.')
    parser.add_argument('--no-year-folder', dest='year_folder', action='store_false',
                        help='Do not create year-based subdirectories for documents')
    parser.add_argument('--verbose', action='store_true',
                        help='Show detailed diff output for each amendment processing')
    parser.add_argument('--formats', dest='output_modes', default='md',
                        help='Output formats to generate (comma-separated). Currently supported: md, md-markers, git, html, htmldiff. Default: md. Use "md-markers" to preserve section tags. Use "git" to enable Git commits with historical dates. HTML creates documents in ELI directory structure (/eli/sfs/{YEAR}/{lopnummer}). HTMLDIFF includes amendment versions with diff view.')
    parser.add_argument('--git-branch', dest='git_branch', default='sfs-updates-(date)',
                        help='Branch name to use for git commits when "git" format is enabled. Use "(date)" as placeholder for current date. Default: sfs-updates-(date)')
    parser.add_argument('--predocs', action='store_true',
                        help='Fetch detailed information about förarbeten from Riksdagen API. This will make processing slower.')
    parser.set_defaults(year_folder=True)
    args = parser.parse_args()

    # Parse output modes
    output_modes = [mode.strip() for mode in args.output_modes.split(',') if mode.strip()]
    if not output_modes:
        output_modes = ['md']  # Default to markdown

    # Validate output modes
    supported_formats = ['md', 'md-markers', 'git', 'html', 'htmldiff']
    invalid_formats = [mode for mode in output_modes if mode not in supported_formats]
    if invalid_formats:
        print(f"Fel: Ej stödda utdataformat: {', '.join(invalid_formats)}")
        print(f"Stödda format: {', '.join(supported_formats)}")
        return

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
        print(f"Fel: JSON-katalog {json_dir} finns inte")
        return
    
    # Find all JSON files
    json_files = list(json_dir.glob('*.json'))
    
    if not json_files:
        print(f"Inga JSON-filer hittades i {json_dir}")
        return
    
    # Apply filter if specified
    if args.filter:
        original_count = len(json_files)
        json_files = filter_json_files(json_files, args.filter)
        print(f"Filter '{args.filter}' tillämpad: {len(json_files)} av {original_count} filer valda")

        if not json_files:
            print("Inga filer matchar filterkriterier")
            return

    print(f"Hittade {len(json_files)} JSON-fil(er) att konvertera från {json_dir}")
    print(f"Utdata kommer att sparas i {output_dir}")
    
    # Convert each JSON file
    for json_file in json_files:
        # Read JSON file
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Fel vid läsning av {json_file}: {e}")
            continue

        # Use make_document to create documents in specified formats
        make_document(data, output_dir, output_modes, args.year_folder, args.verbose, args.git_branch, args.predocs)
    
    print(f"\nBearbetning klar! {len(json_files)} filer sparade i {output_dir} i format: {', '.join(output_modes)}")


if __name__ == "__main__":
    main()
