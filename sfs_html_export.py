#!/usr/bin/env python3
"""
HTML export functionality for SFS documents.

This module contains functions for converting SFS documents to HTML format,
including support for amendments and ignored documents.
"""
import html
import re
from pathlib import Path
from typing import Dict, Any

# Import required functions from other modules
from format_sfs_text_to_md import format_sfs_text, apply_changes_to_sfs_text


def create_html_documents(data: Dict[str, Any], output_path: Path, verbose: bool = False) -> None:
    """Create HTML documents from JSON data.

    Creates base document and separate documents for each amendment.

    Args:
        data: JSON data containing document information
        output_path: Path to the output directory (folder)
        verbose: Whether to show verbose output (default: False) - currently unused
    """
    # Import required functions (avoiding circular imports)
    from sfs_processor import extract_amendments, save_to_disk

    # Extract basic metadata
    beteckning = data.get('beteckning', '')
    amendments = extract_amendments(data.get('andringsforfattningar', []))

    # Clean beteckning for filename
    safe_beteckning = re.sub(r'[^\w\-]', '-', beteckning)

    # Create base filename (grunddokument)
    base_filename = f"{safe_beteckning}_grund.html"
    base_file = output_path / base_filename

    # Generate base HTML content (without amendments applied)
    base_html_content = convert_to_html(data, apply_amendments=False)
    save_to_disk(base_file, base_html_content)
    print(f"Created HTML base document: {base_file}")

    # Create HTML documents for each amendment stage
    if amendments:
        # Filter amendments that have ikraft_datum (already sorted by extract_amendments)
        sorted_amendments = [a for a in amendments if a.get('ikraft_datum')]

        for i, amendment in enumerate(sorted_amendments):
            amendment_beteckning = amendment.get('beteckning', '')
            safe_amendment_beteckning = re.sub(r'[^\w\-]', '-', amendment_beteckning)

            # Create filename with amendment suffix
            amendment_filename = f"{safe_beteckning}_{safe_amendment_beteckning}.html"
            amendment_file = output_path / amendment_filename

            # Generate HTML content with amendments applied up to this point
            amendment_html_content = convert_to_html(data, apply_amendments=True, up_to_amendment=i+1)
            save_to_disk(amendment_file, amendment_html_content)
            print(f"Created HTML amendment document: {amendment_file}")


def convert_to_html(data: Dict[str, Any], apply_amendments: bool = False, up_to_amendment: int = None) -> str:
    """Convert JSON data to HTML format.

    Args:
        data: JSON data for the document
        apply_amendments: Whether to apply amendments
        up_to_amendment: If applying amendments, apply only up to this amendment index (1-based)

    Returns:
        str: HTML content
    """
    # Import required functions (avoiding circular imports)
    from sfs_processor import (
        format_datetime, clean_text, ignore_rules, extract_amendments
    )

    # Extract main document information
    beteckning = data.get('beteckning', '')
    rubrik_original = data.get('rubrik', '')

    # Extract dates
    publicerad_datum = format_datetime(data.get('publiceradDateTime'))
    fulltext_data = data.get('fulltext', {})
    utfardad_datum = format_datetime(fulltext_data.get('utfardadDateTime'))
    ikraft_datum = format_datetime(data.get('ikraftDateTime'))

    # Extract other metadata
    forarbeten = clean_text(data.get('forarbeten', ''))
    celex_nummer = data.get('celexnummer')
    eu_direktiv = data.get('eUdirektiv', False)
    organisation_data = data.get('organisation', {})
    organisation = organisation_data.get('namn', '') if organisation_data else ''

    # Extract the main text content
    innehall_text = fulltext_data.get('forfattningstext', 'No content available')
    if innehall_text is None:
        innehall_text = 'No content available'

    # Check ignore rules
    should_ignore, ignore_reason = ignore_rules(innehall_text)
    if should_ignore:
        return create_ignored_html_content(data, ignore_reason)

    # Format the content text
    formatted_text = format_sfs_text(innehall_text)

    # Apply amendments if requested
    if apply_amendments and up_to_amendment:
        amendments = extract_amendments(data.get('andringsforfattningar', []))
        if amendments:
            # Filter amendments that have ikraft_datum (already sorted by extract_amendments)
            sorted_amendments = [a for a in amendments if a.get('ikraft_datum')]

            # Apply amendments up to the specified index
            amendments_to_apply = sorted_amendments[:up_to_amendment]
            for amendment in amendments_to_apply:
                ikraft_datum_amendment = amendment.get('ikraft_datum')
                if ikraft_datum_amendment:
                    formatted_text = apply_changes_to_sfs_text(formatted_text, ikraft_datum_amendment, False)

    # Convert markdown-formatted text to HTML
    html_content = markdown_to_html(formatted_text)

    # Create HTML document
    html_doc = f"""<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(rubrik_original)}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
        .metadata {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .metadata dt {{ font-weight: bold; }}
        .metadata dd {{ margin-left: 20px; margin-bottom: 5px; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; border-bottom: 1px solid #bdc3c7; padding-bottom: 5px; }}
        h3 {{ color: #34495e; }}
    </style>
</head>
<body>
    <div class="metadata">
        <dl>
            <dt>Beteckning:</dt>
            <dd>{html.escape(beteckning)}</dd>
            <dt>Rubrik:</dt>
            <dd>{html.escape(rubrik_original)}</dd>"""

    if organisation:
        html_doc += f"""
            <dt>Departement:</dt>
            <dd>{html.escape(organisation)}</dd>"""

    if publicerad_datum:
        html_doc += f"""
            <dt>Publicerad:</dt>
            <dd>{html.escape(publicerad_datum)}</dd>"""

    if utfardad_datum:
        html_doc += f"""
            <dt>Utfärdad:</dt>
            <dd>{html.escape(utfardad_datum)}</dd>"""

    if ikraft_datum:
        html_doc += f"""
            <dt>Ikraft:</dt>
            <dd>{html.escape(ikraft_datum)}</dd>"""

    if forarbeten:
        html_doc += f"""
            <dt>Förarbeten:</dt>
            <dd>{html.escape(forarbeten)}</dd>"""

    if celex_nummer:
        html_doc += f"""
            <dt>CELEX:</dt>
            <dd>{html.escape(celex_nummer)}</dd>"""

    if eu_direktiv:
        html_doc += """
            <dt>EU-direktiv:</dt>
            <dd>Ja</dd>"""

    html_doc += f"""
        </dl>
    </div>

    <h1>{html.escape(rubrik_original)}</h1>

    {html_content}
</body>
</html>"""

    return html_doc


def markdown_to_html(markdown_text: str) -> str:
    """Convert basic markdown formatting to HTML.

    Args:
        markdown_text: Text with markdown formatting

    Returns:
        str: HTML formatted text
    """
    # Escape HTML entities first
    text = html.escape(markdown_text)

    # Convert markdown headers
    text = re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.+)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)

    # Convert paragraphs (double newlines)
    paragraphs = text.split('\n\n')
    html_paragraphs = []

    for para in paragraphs:
        para = para.strip()
        if para:
            # Skip if it's already a header
            if para.startswith('<h') and para.endswith('>'):
                html_paragraphs.append(para)
            else:
                # Convert single newlines to <br> within paragraphs
                para = para.replace('\n', '<br>')
                html_paragraphs.append(f'<p>{para}</p>')

    return '\n\n'.join(html_paragraphs)


def create_ignored_html_content(data: Dict[str, Any], reason: str) -> str:
    """Create simplified HTML for ignored documents.

    Args:
        data: JSON data for the document
        reason: Reason why document was ignored

    Returns:
        str: HTML content for ignored document
    """
    rubrik_original = data.get('rubrik', '')

    return f"""<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(rubrik_original)}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
        .warning {{ background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
    </style>
</head>
<body>
    <h1>{html.escape(rubrik_original)}</h1>

    <div class="warning">
        <h2>Automatisk konvertering inte tillgänglig</h2>
        <p>{html.escape(reason)}</p>
        <p>För att läsa det fullständiga dokumentet, besök den officiella versionen på
        <a href="https://svenskforfattningssamling.se/">svenskforfattningssamling.se</a>.</p>
    </div>
</body>
</html>"""
