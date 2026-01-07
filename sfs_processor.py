#!/usr/bin/env python3
"""
Process Swedish legal documents (SFS) from JSON to various output formats.

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

from downloaders.riksdagen_api import fetch_predocs_details, format_predocs_for_frontmatter
from formatters.format_sfs_text import (
    format_sfs_text_as_markdown,
    parse_logical_sections,
    clean_selex_tags,
    normalize_heading_levels
)
from util.text_utils import clean_text
from formatters.sort_frontmatter import sort_frontmatter_properties
from formatters.add_pdf_url_to_frontmatter import generate_pdf_url
from formatters.frontmatter_manager import add_ikraft_datum_to_frontmatter
from temporal.title_temporal import title_temporal
from temporal.amendments import extract_amendments
from temporal.apply_temporal import apply_temporal, is_document_content_empty, add_empty_document_message
from exporters.git import create_init_git_commit
from util.yaml_utils import format_yaml_value
from util.datetime_utils import format_datetime
from util.file_utils import filter_json_files, save_to_disk
from util.doctype_utils import determine_doctype
from formatters.predocs_parser import parse_predocs_string


def create_safe_filename(beteckning: str, preserve_selex_tags: bool = False) -> str:
    """
    Create a safe filename from beteckning.

    Args:
        beteckning: Document beteckning (e.g., "2024:1000")
        preserve_selex_tags: Whether this is for md-markers mode

    Returns:
        str: Safe filename (e.g., "sfs-2024-1000.md" or "sfs-2024-1000-markers.md")
    """
    safe_beteckning = re.sub(r'[^\w\-]', '-', beteckning)
    if preserve_selex_tags:
        return f"sfs-{safe_beteckning}-markers.md"
    else:
        return f"sfs-{safe_beteckning}.md"


def determine_output_path(data: Dict[str, Any], output_dir: Path, year_as_folder: bool = True) -> Path:
    """
    Determine output directory path from document data.
    
    Args:
        data: JSON data containing document information
        output_dir: Base output directory
        year_as_folder: Whether to organize by year in subdirectories
        
    Returns:
        Path: The output directory path for the document
        
    Raises:
        ValueError: If beteckning is invalid or year cannot be extracted
    """
    # Extract beteckning for validation
    beteckning = data.get('beteckning')
    if not beteckning:
        raise ValueError("Beteckning saknas i dokumentdata")

    # Skip documents with beteckning starting with 'N' (myndighetsföreskrifter)
    # These are agency regulations (föreskrifter utfärdade av myndigheter) which are not
    # part of the main Swedish Code of Statutes (SFS) and follow different numbering conventions.
    # Example: N2025:4 refers to Transportstyrelsens föreskrifter (TSFS 2018:49)
    if beteckning.startswith('N'):
        raise ValueError(f"Hoppar över myndighetsföreskrift (N-beteckning): {beteckning}")

    # Extract year from beteckning (format is typically YYYY:NNN)
    year_match = re.search(r'(\d{4}):', beteckning)
    if not year_match:
        raise ValueError(f"Kunde inte extrahera år från beteckning: {beteckning}")

    year = year_match.group(1)

    # Determine output directory based on year_as_folder setting
    if year_as_folder:
        document_dir = output_dir / year
        document_dir.mkdir(parents=True, exist_ok=True)
    else:
        document_dir = output_dir

    return document_dir


def make_document(data: Dict[str, Any], output_dir: Path, output_modes: List[str] = None, year_as_folder: bool = True, verbose: bool = False, git_mode: bool = False, fetch_predocs_from_api: bool = False, apply_links: bool = False, target_date: Optional[str] = None) -> None:
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
        output_modes: List of formats/modes to use (e.g., ["md-markers", "git"]). If None, defaults to ["md-markers"]
                     Note: "git" mode requires "md" mode to be included as it modifies markdown processing
                     "md" generates clean markdown (section tags removed), "md-markers" preserves section tags
                     "html" generates base document only, "htmldiff" includes amendment versions
                     All HTML output uses ELI directory structure with year-based folders
        year_as_folder: Whether to create year-based subdirectories (default: True)
        verbose: Whether to show verbose output (default: False)
        git_mode: Whether git mode is enabled (commits will be created)
        fetch_predocs_from_api: Whether to fetch detailed information about förarbeten from Riksdagen API. Parsing always happens. (default: False)
        target_date: Optional target date (YYYY-MM-DD) for temporal title processing
    """

    # Default to markdown output if no modes specified
    if output_modes is None:
        output_modes = ["md"]
    
    # Set default target_date to today for md format only
    if target_date is None and 'md' in output_modes:
        target_date = datetime.now().strftime('%Y-%m-%d')
        print(f"Varning: Använder dagens datum ({target_date}) som target_date för 'md' som output format")
    
    # Apply temporal title processing if target_date is provided
    if target_date and data.get('rubrik'):
        rubrik_after_temporal = title_temporal(data['rubrik'], target_date)
        # Create a copy of data with the processed title
        data = data.copy()
        data['rubrik_after_temporal'] = rubrik_after_temporal

    # Git mode requires markdown mode to be active
    if "git" in output_modes and "md" not in output_modes:
        output_modes.append("md")
        if verbose:
            print("Info: Lade till 'md'-läge eftersom 'git'-läge kräver markdown-generering")

    # Determine output path and validate document
    try:
        document_dir = determine_output_path(data, output_dir, year_as_folder)
    except ValueError as e:
        if "md" in output_modes:
            print(f"Varning: {e}")
        return

    # Process markdown format if requested
    if "md" in output_modes:
        _create_markdown_document(data, document_dir, git_mode, False, verbose, fetch_predocs_from_api, apply_links, target_date)

    # Process markdown with section markers if requested
    if "md-markers" in output_modes:
        # Create markdown document with selex tags preserved
        _create_markdown_document(data, document_dir, False, True, verbose, fetch_predocs_from_api, apply_links, target_date)

    # Process HTML format if requested
    if "html" in output_modes:
        from exporters.html.html_export import create_html_documents
        create_html_documents(data, output_dir, include_amendments=False)

    # Process HTML diff format if requested
    if "htmldiff" in output_modes:
        from exporters.html.html_export import create_html_documents
        create_html_documents(data, output_dir, include_amendments=True)


def _create_markdown_document(data: Dict[str, Any], output_path: Path, git_mode: bool = False, preserve_selex_tags: bool = False, verbose: bool = False, fetch_predocs_from_api: bool = False, apply_links: bool = False, target_date: Optional[str] = None) -> str:
    """Internal function to create a markdown document from JSON data.

    Args:
        data: JSON data containing document information
        output_path: Path to the output directory (folder)
        git_mode: Whether git mode is enabled (commits will be created)
        preserve_selex_tags: Whether to preserve selex tags in output (for md-markers mode)
        verbose: Whether to print verbose output
        fetch_predocs_from_api: Whether to fetch detailed information about förarbeten from Riksdagen API. Parsing always happens.

    Returns:
        str: The final markdown content that was written to file
    """

    # Extract beteckning to create safe filename
    beteckning = data.get('beteckning')
    if not beteckning:
        raise ValueError("Beteckning saknas i dokumentdata")
    
    safe_filename = create_safe_filename(beteckning, preserve_selex_tags)
    output_file = output_path / safe_filename

    # Get basic markdown content
    markdown_content = convert_to_markdown(data, fetch_predocs_from_api, apply_links)
    
    # Always normalize heading levels, regardless of whether we keep section tags
    markdown_content = normalize_heading_levels(markdown_content)

    # Extract beteckning for logging  
    beteckning = data.get('beteckning')
    if not beteckning:
        raise ValueError("Beteckning saknas i dokumentdata")

    # Apply temporal processing to handle selex attributes (only if not in git mode and not preserving selex tags)
    if not git_mode and not preserve_selex_tags and target_date:
        markdown_content = apply_temporal(markdown_content, target_date, verbose=verbose)

        # Kontrollera om dokumentet är tomt efter temporal processing och lägg till förklarande meddelande
        if is_document_content_empty(markdown_content):
            markdown_content = add_empty_document_message(markdown_content, data, target_date)
            if verbose:
                print(f"Info: Tomt dokument efter temporal processing för {beteckning}, lade till förklarande meddelande")

    # Extract amendments for git logic (if needed)
    # TODO: amendments = extract_amendments(data.get('andringsforfattningar', []))

    # Add ikraft_datum to front matter if not in Git mode
    if not git_mode:
        ikraft_datum = format_datetime(data.get('ikraftDateTime'))
        if ikraft_datum:
            markdown_content = add_ikraft_datum_to_frontmatter(markdown_content, ikraft_datum)

    # Debug: Check final markdown content length
    if verbose:
        print(f"Debug: Slutlig markdown-innehållslängd för {beteckning}: {len(markdown_content)}")
        if len(markdown_content) < 1000:  # If suspiciously short, show preview
            print(f"Debug: Innehållsförhandsvisning eftersom misstänkt kort:\n{markdown_content[:500]}...")

    # Handle git commits if enabled
    if git_mode:
        # Always create initial commit when git is enabled
        return create_init_git_commit(
            data=data,
            output_file=output_file,
            markdown_content=markdown_content,
            verbose=verbose
        )
    else:
        # No git mode - write the file normally
        # Clean selex tags if not preserving them
        if not preserve_selex_tags:
            markdown_content = clean_selex_tags(markdown_content)
        save_to_disk(output_file, markdown_content)
        print(f"Skapade dokument: {output_file}")

    return markdown_content


def convert_to_markdown(data: Dict[str, Any], fetch_predocs_from_api: bool = False, apply_links: bool = False) -> str:
    """Convert JSON data to Markdown content with YAML front matter.

    This function only handles the conversion from JSON to markdown string format.
    It does NOT apply amendments or handle file operations - use make_document() for that.

    Args:
        data: JSON data for the document
        fetch_predocs_from_api: Whether to fetch detailed information about förarbeten from Riksdag API. Parsing always happens.
        apply_links: Whether to add links to other SFS documents

    Returns:
        str: Markdown content with YAML front matter
    """

    # Extract main document information
    beteckning = data.get('beteckning')
    if not beteckning:
        raise ValueError("Beteckning saknas i dokumentdata")
    
    # Use temporal processed title if available, otherwise use original
    rubrik_original = data.get('rubrik_after_temporal', data.get('rubrik'))
    if not rubrik_original:
        raise ValueError("Rubrik saknas i dokumentdata")
    
    rubrik = clean_text(rubrik_original)    # Clean for front matter

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

    # Determine doctype (grundlag, lag, or förordning)
    forfattningstyp_namn = data.get('forfattningstypNamn')
    doctype = determine_doctype(beteckning, forfattningstyp_namn)

    # Extract the main text content from nested structure
    innehall_text = fulltext_data.get('forfattningstext')

    # Debug: Check if content is empty
    if not innehall_text or not innehall_text.strip():
        print(f"Varning: Tomt innehåll för {beteckning}")
        # Create a minimal valid document for empty content
        yaml_frontmatter = f"""---
beteckning: {beteckning}
rubrik: {rubrik_original}
---
# {rubrik_original}

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
doctype: {format_yaml_value(doctype)}
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
        # ALWAYS parse förarbeten string (fast, no API dependency)
        try:
            parsed_predocs = parse_predocs_string(predocs)

            if parsed_predocs:
                if fetch_predocs_from_api:
                    # Fetch detailed information from Riksdagen API
                    try:
                        detailed_predocs = fetch_predocs_details(parsed_predocs)
                        formatted_predocs = format_predocs_for_frontmatter(detailed_predocs)
                    except Exception as e:
                        print(f"Varning: Kunde inte hämta detaljerad förarbeten-information från API: {e}")
                        # Fallback to parsed data without API details
                        formatted_predocs = [f"{p['type'].upper()} {p['rm']}:{p['bet']}" for p in parsed_predocs]
                else:
                    # Use parsed data without API fetching (fast, structured)
                    formatted_predocs = [f"{p['type'].upper()} {p['rm']}:{p['bet']}" for p in parsed_predocs]

                if formatted_predocs:
                    yaml_front_matter += "forarbeten:\n"
                    for item in formatted_predocs:
                        yaml_front_matter += f"  - {format_yaml_value(item)}\n"
                else:
                    # Fallback to original string if formatting failed
                    yaml_front_matter += f"forarbeten: {format_yaml_value(predocs)}\n"
            else:
                # Parsing returned no results, use original string
                yaml_front_matter += f"forarbeten: {format_yaml_value(predocs)}\n"
        except Exception as e:
            print(f"Varning: Kunde inte parsa förarbeten: {e}")
            # Fallback to original string
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
        formatted_text = format_sfs_text_as_markdown(innehall_text, apply_links=apply_links)

        # Apply section tags
        formatted_text = parse_logical_sections(formatted_text)

        # Debug: Check if formatting resulted in empty text
        if not formatted_text.strip():
            print(f"Varning: Formatering resulterade i tom text för {beteckning}")
            print(f"Ursprunglig innehållslängd: {len(innehall_text)}")
            print(f"Ursprunglig innehållsförhandsvisning: {innehall_text[:200]}...")

        # Create Markdown body (clean the original rubrik for heading)
        clean_heading = clean_text(rubrik_original)
        
        # Create article tag with temporal attributes
        article_attributes = []
        
        # Add utfardad_datum if available
        if utfardad_datum:
            article_attributes.append(f'selex:utfardad_datum="{utfardad_datum}"')
        
        ikraft_datum = format_datetime(data.get('ikraftDateTime'))
        if ikraft_datum:
            article_attributes.append(f'selex:ikraft_datum="{ikraft_datum}"')
        
        # Check for expiration date - distinguish between temporal expiration and active revocation
        upphavd_datum = format_datetime(data.get('upphavdDateTime'))
        if utgar_datum:
            # Temporal expiration (tidsbegransadDateTime)
            article_attributes.append(f'selex:upphor_datum="{utgar_datum}"')
        elif upphavd_datum:
            # Active revocation (upphavdDateTime)
            article_attributes.append(f'selex:upphor_datum="{upphavd_datum}"')
            article_attributes.append('selex:upphavd="true"')
        
        # Check for conditional entry into force
        if data.get('ikraftDenDagenRegeringenBestammer'):
            article_attributes.append(f'selex:ikraft_villkor="Denna lag träder i kraft den dag regeringen bestämmer."')
        
        # Check for conditional expiration
        if data.get('upphavdDenDagenRegeringenBestammer'):
            article_attributes.append(f'selex:upphor_villkor="Denna lag upphör att gälla den dag regeringen bestämmer."')
        
        if article_attributes:
            article_tag = f'<article {" ".join(article_attributes)}>'
        else:
            article_tag = '<article>'
        
        markdown_body = f"{article_tag}\n\n# {clean_heading}\n\n" + formatted_text + "\n\n</article>"

    # Section tags are preserved in markdown_body - they will be cleaned later if needed

    # Return the complete markdown content
    return yaml_front_matter + markdown_body



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
    # Lägg till regler här vid behov

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
    clean_heading = clean_text(rubrik_original)

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
    parser.add_argument('--formats', dest='output_modes', default='md-markers',
                        help='Output formats to generate (comma-separated). Currently supported: md-markers, md, git, html, htmldiff, vector. Default: md-markers. Use "md-markers" to preserve section tags with temporal attributes (standard). Use "md" for clean markdown without section tags. Use "git" to enable Git commits with historical dates. HTML creates documents in ELI directory structure (/eli/sfs/{YEAR}/{lopnummer}). HTMLDIFF includes amendment versions with diff view. VECTOR creates embeddings for semantic search.')
    parser.add_argument('--predocs-fetch', action='store_true', dest='predocs_fetch',
                        help='Fetch detailed information about förarbeten from Riksdagen API. Parsing of förarbeten always happens. This will make processing slower.')
    parser.add_argument('--target-date', dest='target_date', default=None,
                        help='Target date (YYYY-MM-DD) for temporal processing. Used with md, html, and htmldiff formats to filter content based on validity dates. If not specified, today\'s date is used for md format. Example: --target-date 2023-01-01')
    parser.add_argument('--apply-links', action='store_true', default=True,
                        help='Apply internal paragraph links (e.g., [9 §](#9§)), external SFS links (e.g., [2002:43](/sfs/2002:43)), EU legislation links (e.g., [(EU) nr 651/2014](https://eur-lex.europa.eu/...)), and law name links (e.g., [8 kap. 7 § regeringsformen](/sfs/1974/152)) to the document. Default: True')
    # Vector export options
    parser.add_argument('--vector-backend', dest='vector_backend', default='json',
                        choices=['postgresql', 'elasticsearch', 'json'],
                        help='Vector store backend for vector format (default: json)')
    parser.add_argument('--vector-chunking', dest='vector_chunking', default='paragraph',
                        choices=['paragraph', 'chapter', 'section', 'semantic', 'fixed_size'],
                        help='Chunking strategy for vector format (default: paragraph)')
    parser.add_argument('--vector-mock', dest='vector_mock', action='store_true',
                        help='Use mock embeddings for vector format (for testing without OpenAI API)')
    parser.add_argument('--embedding-model', dest='embedding_model', default='text-embedding-3-large',
                        help='Embedding model for vector format (default: text-embedding-3-large)')
    parser.set_defaults(year_folder=True)
    args = parser.parse_args()

    # Parse output modes
    output_modes = [mode.strip() for mode in args.output_modes.split(',') if mode.strip()]
    if not output_modes:
        output_modes = ['md']  # Default to markdown

    # Validate output modes
    supported_formats = ['md', 'md-markers', 'git', 'html', 'htmldiff', 'vector']
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
        # Default input directory is always ../sfs-jsondata
        json_dir = script_dir.parent / 'sfs-jsondata'

    # Check if custom output directory is provided
    if args.output:
        output_dir = Path(args.output)
    else:
        # Default output directory based on primary output format
        primary_format = output_modes[0] if output_modes else 'md'
        output_dir = script_dir.parent / f'sfs-export-{primary_format}'
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
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
    
    # Generate CSS and JS files once for HTML/HTMLDIFF formats
    if "html" in output_modes or "htmldiff" in output_modes:
        from exporters.html.html_export import generate_css_file, generate_js_file
        css_js_dir = output_dir / "eli" / "sfs"
        css_js_dir.mkdir(parents=True, exist_ok=True)
        generate_css_file(css_js_dir)
        generate_js_file(css_js_dir)

    # Handle vector mode with batch processing
    if "vector" in output_modes:
        from exporters.vector import VectorExportConfig, ChunkingStrategy
        from exporters.vector.vector_export import batch_create_vector_documents

        # Build vector config
        backend_config = {}
        if args.vector_backend == "json":
            # Set JSON file path to output directory
            backend_config["file_path"] = str(output_dir / "sfs_vectors.json")

        vector_config = VectorExportConfig(
            embedding_provider="mock" if args.vector_mock else "openai",
            embedding_model=args.embedding_model,
            backend_type=args.vector_backend,
            backend_config=backend_config,
            chunking_strategy=ChunkingStrategy(args.vector_chunking),
            verbose=args.verbose
        )

        # Set target_date to today if not specified
        vector_target_date = args.target_date or datetime.now().strftime('%Y-%m-%d')

        print(f"Skapar vektordata med {args.embedding_model} och {args.vector_chunking}-chunking...")
        batch_create_vector_documents(
            json_files=json_files,
            output_dir=output_dir,
            config=vector_config,
            target_date=vector_target_date,
            show_progress=True
        )

        # Remove 'vector' from output_modes if it's the only one to avoid further processing
        if output_modes == ['vector']:
            print(f"\nVektorbearbetning klar! {len(json_files)} filer bearbetade")
            return

    # Handle git mode with batch processing
    if "git" in output_modes:
        from exporters.git import process_files_with_git_batch
        process_files_with_git_batch(json_files, output_dir, args.verbose, args.predocs_fetch)
    else:
        # Convert each JSON file normally
        for json_file in json_files:
            # Read JSON file
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Fel vid läsning av {json_file}: {e}")
                continue

            # Use make_document to create documents in specified formats
            make_document(data, output_dir, output_modes, args.year_folder, args.verbose, False, args.predocs_fetch, args.apply_links, args.target_date)
    
    print(f"\nBearbetning klar! {len(json_files)} filer sparade i {output_dir} i format: {', '.join(output_modes)}")


if __name__ == "__main__":
    main()
