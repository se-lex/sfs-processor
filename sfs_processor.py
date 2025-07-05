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
    Use --formats to specify output modes (e.g., "md,git,html,htmldiff" for multiple formats).
    HTML format creates documents in ELI directory structure with year-based folders.
    Use --no-year-folder to save files directly in output directory without year subdirectories.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import difflib
from format_sfs_text import format_sfs_text_as_markdown, apply_changes_to_sfs_text, parse_logical_sections
from sort_frontmatter import sort_frontmatter_properties
from add_pdf_url_to_frontmatter import generate_pdf_url


def ensure_git_branch_for_commits():
    """
    Ensures that git commits are made in a different branch than the current one.
    Creates a new branch if needed and switches to it.
    Returns the original branch name to allow switching back later.
    """
    import subprocess

    try:
        # Get current branch name
        result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
                              capture_output=True, text=True, check=True)
        current_branch = result.stdout.strip()

        # Generate a unique branch name for commits
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        commit_branch = f"sfs_commits_{timestamp}"

        # Create and switch to the new branch
        subprocess.run(['git', 'checkout', '-b', commit_branch], 
                      check=True, capture_output=True)

        print(f"Skapade och bytte till branch '{commit_branch}' för git-commits")
        return current_branch, commit_branch

    except subprocess.CalledProcessError as e:
        print(f"Varning: Kunde inte skapa ny branch för git-commits: {e}")
        return None, None
    except FileNotFoundError:
        print("Varning: Git hittades inte.")
        return None, None


def restore_original_branch(original_branch):
    """
    Switches back to the original branch after commits are done.
    """
    import subprocess
    
    if not original_branch:
        return
        
    try:
        subprocess.run(['git', 'checkout', original_branch], 
                      check=True, capture_output=True)
        print(f"Bytte tillbaka till ursprunglig branch '{original_branch}'")
    except subprocess.CalledProcessError as e:
        print(f"Varning: Kunde inte byta tillbaka till ursprunglig branch: {e}")
    except FileNotFoundError:
        print("Varning: Git hittades inte.")


def make_document(data: Dict[str, Any], output_dir: Path, output_modes: List[str] = None, year_as_folder: bool = True, verbose: bool = False) -> None:
    """Create documents by converting JSON to specified output formats and applying amendments.

    This is the main function for document creation that handles:
    - Output directory structure based on beteckning year and year_as_folder setting
    - Coordination of different output formats and modes:
      * "md": Generate markdown files (required for other modes)
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
                     "html" generates base document only, "htmldiff" includes amendment versions
                     All HTML output uses ELI directory structure with year-based folders
        year_as_folder: Whether to create year-based subdirectories (default: True)
        verbose: Whether to show verbose output (default: False)
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
        # Create markdown document (git mode is enabled if "git" is in output_modes)
        enable_git = "git" in output_modes
        markdown_content = _create_markdown_document(data, document_dir, enable_git, verbose)

    # Process HTML format if requested
    if "html" in output_modes:
        from html_export import create_html_documents
        create_html_documents(data, output_dir, include_amendments=False)

    # Process HTML diff format if requested
    if "htmldiff" in output_modes:
        from html_export import create_html_documents
        create_html_documents(data, output_dir, include_amendments=True)


def _create_markdown_document(data: Dict[str, Any], output_path: Path, enable_git: bool = False, verbose: bool = False) -> str:
    """Internal function to create a markdown document from JSON data.

    Args:
        data: JSON data containing document information
        output_path: Path to the output directory (folder)
        enable_git: Whether to create git commits during processing
        verbose: Whether to print verbose output

    Returns:
        str: The final markdown content that was written to file
    """

    # Extract beteckning to create safe filename
    beteckning = data.get('beteckning', '')
    safe_filename = "sfs-" + re.sub(r'[^\w\-]', '-', beteckning) + '.md'
    output_file = output_path / safe_filename

    # Get basic markdown content
    markdown_content = convert_to_markdown(data)

    # Extract metadata for processing
    beteckning = data.get('beteckning', '')
    fulltext_data = data.get('fulltext', {})
    innehall_text = fulltext_data.get('forfattningstext', '')
    amendments = extract_amendments(data.get('andringsforfattningar', []))

    # Check for amendment markers and process amendments if they exist
    has_amendment_markers = False # re.search(r'/.*?I:\d{4}-\d{2}-\d{2}/', innehall_text)
    if verbose and amendments and not has_amendment_markers:
        print(f"Varning: Inga ändringsmarkeringar hittades i {beteckning} men ändringar finns.")

    # Apply amendments if they exist
    if has_amendment_markers and amendments:
        # Extract the markdown body (everything after the front matter)
        if markdown_content.startswith('---'):
            front_matter_end = markdown_content.find('\n---\n', 3)
            if front_matter_end != -1:
                front_matter = markdown_content[:front_matter_end + 5]  # Include the closing ---\n
                markdown_body = markdown_content[front_matter_end + 5:]

                # Process amendments on the entire markdown body (including heading)
                processed_text = apply_amendments_to_text(markdown_body, amendments, enable_git, verbose, output_file)

                # Reconstruct the full content
                markdown_content = front_matter + "\n\n" + processed_text
                print(f"Debug: Bearbetad textlängd för {beteckning}: {len(processed_text)}")
    else:
        print(f"Info: Inga ändringsmarkeringar eller ändringar att bearbeta för {beteckning}")

    # Add ikraft_datum to front matter if not in Git mode
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
                        # Extract front matter and content, preserving spacing
                        end_of_frontmatter = front_matter_end + 4  # Position after \n---
                        while end_of_frontmatter < len(markdown_content) and markdown_content[end_of_frontmatter] == '\n':
                            end_of_frontmatter += 1

                        front_matter = markdown_content[:front_matter_end + 4]  # Include up to \n---
                        rest_of_content = markdown_content[end_of_frontmatter:]

                        # Sort only the front matter and ensure proper spacing
                        sorted_front_matter = sort_frontmatter_properties(front_matter + '\n')
                        markdown_content = sorted_front_matter + '\n' + rest_of_content
            except ValueError as e:
                print(f"Varning: Kunde inte sortera front matter efter att ha lagt till ikraft_datum för {beteckning}: {e}")

    # Debug: Check final markdown content length
    print(f"Debug: Slutlig markdown-innehållslängd för {beteckning}: {len(markdown_content)}")
    if len(markdown_content) < 1000:  # If suspiciously short, show preview
        print(f"Debug: Innehållsförhandsvisning eftersom misstänkt kort:\n{markdown_content[:500]}...")

    # Handle git commits if enabled
    final_content = markdown_content
    if enable_git:
        import subprocess

        # Get main document metadata
        rubrik = data.get('rubrik', '')

        ikraft_datum = format_datetime(data.get('ikraftDateTime'))
        utfardad_datum = format_datetime(data.get('fulltext', {}).get('utfardadDateTime'))

        # Only create main commits if there are no amendments (they handle their own commits)
        if not amendments and utfardad_datum:
            # Ensure commits are made in a different branch
            original_branch = ensure_git_branch_for_commits()
            
            try:
                # First commit: without ikraft_datum in front matter, dated utfardad_datum
                commit_message = rubrik if rubrik else f"SFS {beteckning}"

                # Write file for first commit (without ikraft_datum)
                save_to_disk(output_file, markdown_content)

                # Stage the current file (which doesn't have ikraft_datum yet)
                subprocess.run(['git', 'add', str(output_file)], check=True, capture_output=True)

                # Check if there are any changes to commit
                result = subprocess.run(['git', 'diff', '--cached', '--quiet'], capture_output=True)
                if result.returncode != 0:  # Non-zero means there are changes
                    # Create first commit with utfardad_datum as date
                    subprocess.run([
                        'git', 'commit',
                        '-m', commit_message,
                        '--date', utfardad_datum
                    ], check=True, capture_output=True)
                    print(f"Git-commit skapad: '{commit_message}' daterad {utfardad_datum}")
                else:
                    print(f"Inga ändringar att commita för första commit av {beteckning}")

                # Second commit: add ikraft_datum to front matter if it exists
                if ikraft_datum:
                    # Add ikraft_datum to the existing markdown content
                    markdown_content_with_ikraft = add_ikraft_datum_to_markdown(markdown_content, ikraft_datum)

                    # Sort front matter only
                    if markdown_content_with_ikraft.startswith('---'):
                        front_matter_end = markdown_content_with_ikraft.find('\n---\n', 3)
                        if front_matter_end != -1:
                            # Include the complete front matter block with proper spacing
                            # Find where the actual content starts (after potential newlines following ---)
                            end_of_frontmatter = front_matter_end + 4  # Position after \n---
                            while end_of_frontmatter < len(markdown_content_with_ikraft) and markdown_content_with_ikraft[end_of_frontmatter] == '\n':
                                end_of_frontmatter += 1

                            front_matter = markdown_content_with_ikraft[:front_matter_end + 4]  # Include up to \n---
                            rest_of_content = markdown_content_with_ikraft[end_of_frontmatter:]
                            sorted_front_matter = sort_frontmatter_properties(front_matter + '\n')  # Add the closing newline
                            # Ensure there's always exactly one empty line between front matter and content
                            markdown_content_with_ikraft = sorted_front_matter + '\n' + rest_of_content

                    # Write updated file with ikraft_datum
                    save_to_disk(output_file, markdown_content_with_ikraft)

                    # Stage the updated file
                    subprocess.run(['git', 'add', str(output_file)], check=True, capture_output=True)

                    # Check if there are any changes to commit
                    result = subprocess.run(['git', 'diff', '--cached', '--quiet'], capture_output=True)
                    if result.returncode != 0:  # Non-zero means there are changes
                        # Create second commit with ikraft_datum as date
                        subprocess.run([
                            'git', 'commit',
                            '-m', f"{beteckning} träder i kraft", # TODO: Se till att committa förarbeten först
                            '--date', ikraft_datum
                        ], check=True, capture_output=True)
                        print(f"Git-commit skapad: '{beteckning} träder i kraft' daterad {ikraft_datum}")
                    else:
                        print(f"Inga ändringar att commita för ikraft_datum av {beteckning}")

                    # Use the content with ikraft_datum as final content
                    final_content = markdown_content_with_ikraft

            except subprocess.CalledProcessError as e:
                print(f"Varning: Git-commit misslyckades för {beteckning}: {e}")
                # Write the file anyway, without git commits
                save_to_disk(output_file, markdown_content)
            except FileNotFoundError:
                print("Varning: Git hittades inte. Hoppar över Git-commits.")
                # Write the file anyway, without git commits
                save_to_disk(output_file, markdown_content)
            finally:
                # Always restore original branch
                restore_original_branch(original_branch)
        else:
            # Write file if git is enabled but no commits needed
            save_to_disk(output_file, markdown_content)
    else:
        # No git mode - write the file normally
        save_to_disk(output_file, markdown_content)
        print(f"Skapade dokument: {output_file}")

    return final_content


def convert_to_markdown(data: Dict[str, Any]) -> str:
    """Convert JSON data to Markdown content with YAML front matter.

    This function only handles the conversion from JSON to markdown string format.
    It does NOT apply amendments or handle file operations - use make_document() for that.

    Args:
        data: JSON data for the document

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
    forarbeten = clean_text(data.get('forarbeten', ''))
    celex_nummer = data.get('celexnummer')
    eu_direktiv = data.get('eUdirektiv', False)

    # Extract organization information
    organisation_data = data.get('organisation', {})
    organisation = organisation_data.get('namn', '') if organisation_data else ''

    # Extract the main text content from nested structure
    innehall_text = fulltext_data.get('forfattningstext')

    # Debug: Check if content is empty
    if not innehall_text.strip():
        raise ValueError(f"Varning: Tomt innehåll för {beteckning}")

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

        # Create Markdown body
        markdown_body = f"# {rubrik_original}\n\n" + formatted_text

    # Return the complete markdown content
    return yaml_front_matter + markdown_body


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


def clean_title(rubrik: Optional[str]) -> str:
    """Clean rubrik by removing beteckning in parentheses."""
    if not rubrik:
        return ""

    # Remove beteckning pattern in parentheses (e.g., "(1987:1185)")
    # Pattern matches parentheses containing year:number format
    # First remove the parentheses and their content, then clean up extra whitespace
    cleaned = re.sub(r'\s*\(\d{4}:\d+\)\s*', ' ', rubrik)
    # Clean up any multiple spaces that might have been created
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


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
    """Extract and format amendment information, sorted chronologically by ikraft_datum."""
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
    
    # Sort amendments chronologically by ikraft_datum
    # Amendments without ikraft_datum will be sorted to the end
    amendments.sort(key=lambda x: x['ikraft_datum'] or '9999-12-31')

    return amendments


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
        # Preserve the original spacing after the front matter
        return f"{before_closing}\n{ikraft_line}\n---\n{after_closing}"

    # Fallback: return original content if no proper front matter found
    return markdown_content


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
    # Get the original rubrik for the heading
    rubrik_original = data.get('rubrik', '')

    # Create simplified body with main heading and explanation
    markdown_body = f"# {rubrik_original}\n\n"
    markdown_body += "**Automatisk konvertering inte tillgänglig**\n\n"
    markdown_body += f"{reason}\n\n"
    markdown_body += "För att läsa det fullständiga dokumentet, besök den officiella versionen på "
    markdown_body += "[svenskforfattningssamling.se](https://svenskforfattningssamling.se/) "
    markdown_body += "eller ladda ner PDF:en från länken i front matter ovan.\n"

    return markdown_body


def apply_amendments_to_text(text: str, amendments: List[Dict[str, Any]], enable_git: bool = False, verbose: bool = False, output_file: Path = None) -> str:
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

    def parse_overgangsbestammelser(text: str, amendments: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Parse 'Övergångsbestämmelser' section and organize by amendment beteckning.

        Returns:
            Dict mapping beteckning to its övergångsbestämmelser content
        """
        overgangs_dict = {}

        # Find the Övergångsbestämmelser section
        overgangs_match = re.search(r'### Övergångsbestämmelser\s*\n\n(.*?)(?=\n### |\n## |\Z)', text, re.DOTALL)
        if not overgangs_match:
            if verbose:
                print("Ingen 'Övergångsbestämmelser'-sektion hittades")
            return overgangs_dict

        overgangs_content = overgangs_match.group(1).strip()

        # Get all betecknings from amendments
        betecknings = [a.get('beteckning') for a in amendments if a.get('beteckning')]

        if not betecknings:
            return overgangs_dict

        # Create regex pattern to match any beteckning
        betecknings_pattern = '|'.join(re.escape(b) for b in betecknings)

        # Split content by betecknings
        split_pattern = f'({betecknings_pattern})'
        parts = re.split(split_pattern, overgangs_content)

        current_beteckning = None
        for part in parts:
            part = part.strip()
            if not part:
                continue

            if part in betecknings:
                current_beteckning = part
                overgangs_dict[current_beteckning] = ""
            elif current_beteckning and part:
                # Add content to current beteckning
                if overgangs_dict[current_beteckning]:
                    overgangs_dict[current_beteckning] += "\n\n" + part
                else:
                    overgangs_dict[current_beteckning] = part

        if verbose:
            print(f"Hittade övergångsbestämmelser för dessa författningar: {list(overgangs_dict.keys())}")
            for beteckning, content in overgangs_dict.items():
                print(f"  {beteckning}: {len(content)} tecken")

        return overgangs_dict

    processed_text = text

    # Parse övergångsbestämmelser early to have it available
    overgangs_dict = parse_overgangsbestammelser(processed_text, amendments)

    # Check if there are any markers for the amendments in the text
    if not re.search(r'/.*?I:\d{4}-\d{2}-\d{2}/', processed_text):
        print("Varning: Inga ändringsmarkeringar hittades i texten. Hoppar över bearbetning av ändringar.")
        # Even without amendments, return the text as-is (övergångsbestämmelser already preserved in original text)
        return text

    # Clear content under Övergångsbestämmelser heading but keep the heading itself
    overgangs_match = re.search(r'(### Övergångsbestämmelser\s*\n\n).*?(?=\n### |\n## |\Z)', processed_text, re.DOTALL)
    if overgangs_match:
        # Keep the heading but remove all content after it
        heading_with_newlines = overgangs_match.group(1)
        processed_text = processed_text[:overgangs_match.start()] + heading_with_newlines + processed_text[overgangs_match.end():]
        if verbose:
            print("Rensade innehåll under rubriken 'Övergångsbestämmelser'")

    # Filter amendments that have ikraft_datum (already sorted by extract_amendments)
    sorted_amendments = [a for a in amendments if a.get('ikraft_datum')]

    # Print number of amendments found
    if verbose:
        print(f"Hittade {len(sorted_amendments)} ändringar att bearbeta.")

    # Kolla så det är lika många amenedments som ikraft_datum
    if len(sorted_amendments) != len(set(a['ikraft_datum'] for a in sorted_amendments)):
        print("Varning: Duplicerade ikraft_datum hittades i ändringar. Detta kan orsaka oväntat beteende.")

    try:
        for amendment in sorted_amendments:
            ikraft_datum = amendment.get('ikraft_datum')
            beteckning = amendment.get('beteckning', '')
            rubrik = amendment.get('rubrik', 'Ändringsförfattning')

            if verbose:
                print(f"\n{'='*60}")
                print(f"Bearbetar ÄNDRINGSFÖRFATTNING: {rubrik} ({ikraft_datum})")
                if beteckning in overgangs_dict:
                    print(f"Övergångsbestämmelser för {beteckning}:")
                    print(f"\033[94m{overgangs_dict[beteckning]}\033[0m")  # Blue text for övergångsbestämmelser
                print(f"{'='*60}")
                print('')

            if ikraft_datum:
                # Store text before changes for debug comparison
                text_before_changes = processed_text

                processed_text = apply_changes_to_sfs_text(processed_text, ikraft_datum, verbose)

                # Add relevant Övergångsbestämmelser content under the existing heading
                if beteckning in overgangs_dict and overgangs_dict[beteckning]:
                    # Format the content with the beteckning as a bold heading
                    formatted_overgangs_content = f"**{beteckning}**\n\n{overgangs_dict[beteckning]}"

                    # Find the existing Övergångsbestämmelser heading and any existing content
                    overgangs_section_match = re.search(r'(### Övergångsbestämmelser\s*\n\n)(.*?)(?=\n### |\n## |\Z)', processed_text, re.DOTALL)
                    if overgangs_section_match:
                        heading_part = overgangs_section_match.group(1)
                        existing_content = overgangs_section_match.group(2).strip()

                        if existing_content:
                            # There's already content under the heading, add after it
                            content_to_insert = f"\n\n{formatted_overgangs_content}"
                            insert_pos = overgangs_section_match.end() - len(overgangs_section_match.group(0)) + len(heading_part) + len(existing_content)
                            processed_text = processed_text[:insert_pos] + content_to_insert + processed_text[insert_pos:]

                            if verbose:
                                print(f"Lade till övergångsbestämmelser för {beteckning} efter befintligt innehåll")
                        else:
                            # No existing content, add directly after heading
                            insert_pos = overgangs_section_match.start() + len(heading_part)
                            content_to_insert = f"{formatted_overgangs_content}\n\n"
                            processed_text = processed_text[:insert_pos] + content_to_insert + processed_text[insert_pos:]

                            if verbose:
                                print(f"Lade till övergångsbestämmelser för {beteckning} under rubrik (inget befintligt innehåll)")
                    else:
                        # Fallback: add the section at the end if heading doesn't exist
                        overgangs_section = f"\n\n### Övergångsbestämmelser\n\n{formatted_overgangs_content}\n"
                        processed_text = processed_text.rstrip() + overgangs_section

                        if verbose:
                            print(f"Skapade ny övergångsbestämmelser-sektion för {beteckning} (rubrik hittades inte)")

                # ...existing diff code...
                show_diff = True
                if show_diff:
                    # Create unified diff
                    diff_lines = list(difflib.unified_diff(
                        text_before_changes.splitlines(keepends=True),
                        processed_text.splitlines(keepends=True),
                        #fromfile=f"Före ändring {beteckning}",
                        #tofile=f"Efter ändring {beteckning}",
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

    finally:
        # Always restore original branch if we switched
        if original_branch:
            restore_original_branch(original_branch)

    return processed_text

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
                        help='Output formats to generate (comma-separated). Currently supported: md, git, html, htmldiff. Default: md. Use "git" to enable Git commits with historical dates. HTML creates documents in ELI directory structure (/eli/sfs/{YEAR}/{lopnummer}). HTMLDIFF includes amendment versions with diff view.')
    parser.set_defaults(year_folder=True)
    args = parser.parse_args()

    # Parse output modes
    output_modes = [mode.strip() for mode in args.output_modes.split(',') if mode.strip()]
    if not output_modes:
        output_modes = ['md']  # Default to markdown

    # Validate output modes
    supported_formats = ['md', 'git', 'html', 'htmldiff']
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
        make_document(data, output_dir, output_modes, args.year_folder, args.verbose)
    
    print(f"\nBearbetning klar! Filer sparade i {output_dir} i format: {', '.join(output_modes)}")


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


def save_to_disk(file_path: Path, content: str) -> None:
    """Save content to disk with proper error handling.

    Args:
        file_path: Path where to save the file
        content: Content to write to the file
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    except IOError as e:
        print(f"Fel vid skrivning av {file_path}: {e}")


if __name__ == "__main__":
    main()
