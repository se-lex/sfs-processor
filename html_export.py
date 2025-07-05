#!/usr/bin/env python3
"""
HTML export functionality for SFS documents.

This module contains functions for converting SFS documents to HTML format,
including support for amendments and ignored documents.
"""
import html
import re
import difflib
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

# Import required functions from other modules
from format_sfs_text import format_sfs_text_as_markdown, apply_changes_to_sfs_text
from add_pdf_url_to_frontmatter import generate_pdf_url


def create_html_documents(data: Dict[str, Any], output_path: Path, include_amendments: bool = False) -> None:
    """Create HTML documents from JSON data.

    Creates base document and optionally separate documents for each amendment.

    Args:
        data: JSON data containing document information
        output_path: Path to the output directory (folder)
        include_amendments: Whether to generate amendment versions (default: False)
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
    if include_amendments and amendments:
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

            # Create HTML with diff view comparing base and amended content
            amendment_html_with_diff = create_amendment_html_with_diff(
                base_html_content, amendment_html_content, amendment_beteckning, amendment.get('rubrik', ''),
                amendment.get('ikraft_datum', '')
            )

            save_to_disk(amendment_file, amendment_html_with_diff)
            print(f"Created HTML amendment document with diff: {amendment_file}")


def create_eli_html_documents(data: Dict[str, Any], output_path: Path) -> None:
    """Create ELI-formatted HTML documents for SFS documents.

    Creates HTML documents in ELI directory structure: /eli/sfs/{YEAR}/{lopnummer}

    Args:
        data: JSON data containing document information
        output_path: Base path for ELI output (e.g., /eli)
    """
    # Import required functions (avoiding circular imports)
    from sfs_processor import extract_amendments, save_to_disk

    # Extract beteckning and parse year and löpnummer
    beteckning = data.get('beteckning', '')
    if ':' not in beteckning:
        print(f"Warning: Invalid beteckning format '{beteckning}', expected YYYY:NNN")
        return

    try:
        year, lopnummer = beteckning.split(':', 1)
    except ValueError:
        print(f"Warning: Could not parse beteckning '{beteckning}'")
        return

    # Create ELI directory structure: /eli/sfs/{YEAR}/{lopnummer}
    eli_dir = output_path / "eli" / "sfs" / year / lopnummer
    eli_dir.mkdir(parents=True, exist_ok=True)

    # Generate base HTML content (without amendments applied)
    base_html_content = convert_to_html(data, apply_amendments=False, eli_format=True)
    base_file = eli_dir / "index.html"
    save_to_disk(base_file, base_html_content)
    print(f"Created ELI HTML document: {base_file}")

    # Create HTML documents for each amendment stage
    amendments = extract_amendments(data.get('andringsforfattningar', []))
    if amendments:
        # Filter amendments that have ikraft_datum (already sorted by extract_amendments)
        sorted_amendments = [a for a in amendments if a.get('ikraft_datum')]

        for i, amendment in enumerate(sorted_amendments):
            amendment_beteckning = amendment.get('beteckning', '')
            if ':' not in amendment_beteckning:
                continue

            try:
                amend_year, amend_lopnummer = amendment_beteckning.split(':', 1)
            except ValueError:
                continue

            # Create amendment directory: /eli/sfs/{AMEND_YEAR}/{amend_lopnummer}
            amend_eli_dir = output_path / "eli" / "sfs" / amend_year / amend_lopnummer
            amend_eli_dir.mkdir(parents=True, exist_ok=True)

            # Generate HTML content with amendments applied up to this point
            amendment_html_content = convert_to_html(data, apply_amendments=True, up_to_amendment=i+1, eli_format=True)

            # Create HTML with diff view comparing base and amended content
            amendment_html_with_diff = create_amendment_html_with_diff(
                base_html_content, amendment_html_content, amendment_beteckning, amendment.get('rubrik', ''),
                amendment.get('ikraft_datum', '')
            )

            amendment_file = amend_eli_dir / "index.html"
            save_to_disk(amendment_file, amendment_html_with_diff)
            print(f"Created ELI amendment HTML document: {amendment_file}")


def convert_to_html(data: Dict[str, Any], apply_amendments: bool = False, up_to_amendment: int = None, eli_format: bool = False) -> str:
    """Convert JSON data to HTML format.

    Args:
        data: JSON data for the document
        apply_amendments: Whether to apply amendments
        up_to_amendment: If applying amendments, apply only up to this amendment index (1-based)
        eli_format: Whether to generate ELI-compliant HTML with RDFa prefixes

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

    # Generate PDF URL
    pdf_url = generate_pdf_url(beteckning, utfardad_datum, check_exists=False)

    # Extract the main text content
    innehall_text = fulltext_data.get('forfattningstext', 'No content available')
    if innehall_text is None:
        innehall_text = 'No content available'

    # Check ignore rules
    should_ignore, ignore_reason = ignore_rules(innehall_text)
    if should_ignore:
        return create_ignored_html_content(data, ignore_reason)

    # Format the content text
    formatted_text = format_sfs_text_as_markdown(innehall_text)

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

    # Create HTML document with navbar integration
    html_doc = create_html_head(rubrik_original, beteckning, eli_format)
    html_doc += "\n<body>"

    # Always use ELI format with RDFa properties for metadata
    html_doc += f"""
    <div class="metadata">
        <dl>
            <dt>Beteckning:</dt>
            <dd property="eli:id_local" datatype="xsd:string">{html.escape(beteckning)}</dd>
            <dt>Rubrik:</dt>
            <dd property="eli:title" datatype="xsd:string">{html.escape(rubrik_original)}</dd>"""

    if organisation:
        html_doc += f"""
            <dt>Departement:</dt>
            <dd property="eli:passed_by" datatype="xsd:string">{html.escape(organisation)}</dd>"""

    if publicerad_datum:
        html_doc += f"""
            <dt>Publicerad:</dt>
            <dd property="eli:date_publication" datatype="xsd:date">{html.escape(publicerad_datum)}</dd>"""

    if utfardad_datum:
        html_doc += f"""
            <dt>Utfärdad:</dt>
            <dd property="eli:date_document" datatype="xsd:date">{html.escape(utfardad_datum)}</dd>"""

    if ikraft_datum:
        html_doc += f"""
            <dt>Ikraft:</dt>
            <dd property="eli:date_entry-into-force" datatype="xsd:date">{html.escape(ikraft_datum)}</dd>"""

    if forarbeten:
        html_doc += f"""
            <dt>Förarbeten:</dt>
            <dd property="eli:preparatory_act" datatype="xsd:string">{html.escape(forarbeten)}</dd>"""

    if celex_nummer:
        html_doc += f"""
            <dt>CELEX:</dt>
            <dd property="eli:related_to" resource="{html.escape(celex_nummer)}" datatype="xsd:string">{html.escape(celex_nummer)}</dd>"""

    if eu_direktiv:
        html_doc += """
            <dt>EU-direktiv:</dt>
            <dd property="eli:type_document" resource="http://data.europa.eu/eli/ontology#directive" datatype="xsd:boolean">Ja</dd>"""

    if pdf_url:
        html_doc += f"""
            <dt>PDF-fil:</dt>
            <dd><a href="{html.escape(pdf_url)}" property="eli:is_realized_by" datatype="xsd:anyURI">PDF-fil</a></dd>"""

    html_doc += """
        </dl>
    </div>"""

    # Add the rest of the HTML document
    html_doc += f"""
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
    text = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', text, flags=re.MULTILINE)  # Added support for H4
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
    beteckning = data.get('beteckning', '')

    # Additional styles for ignored documents
    ignored_styles = minify_css("""
        .warning { background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin-bottom: 20px; }""")

    html_doc = create_html_head(rubrik_original, beteckning, additional_styles=ignored_styles)
    html_doc += f"""
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

    return html_doc


def create_amendment_html_with_diff(base_html: str, amendment_html: str, amendment_beteckning: str, amendment_rubrik: str, ikraft_datum: str) -> str:
    """Create HTML document with diff view between base and amended content.

    Args:
        base_html: HTML content of the base document
        amendment_html: HTML content of the amended document
        amendment_beteckning: Amendment designation
        amendment_rubrik: Amendment title
        ikraft_datum: Date when amendment takes effect

    Returns:
        str: HTML content with diff view
    """
    # Extract the content part from both HTML documents (everything after <h1> tag)
    def extract_content_from_html(html_content: str) -> str:
        # Find the main content after the first <h1> tag
        h1_match = re.search(r'<h1[^>]*>.*?</h1>\s*', html_content, re.DOTALL)
        if h1_match:
            content = html_content[h1_match.end():]
            # Remove closing body and html tags
            content = re.sub(r'</body>\s*</html>\s*$', '', content, flags=re.DOTALL)
            return content
        return html_content

    base_content = extract_content_from_html(base_html)
    amendment_content = extract_content_from_html(amendment_html)

    # Create HTML diff using difflib
    differ = difflib.HtmlDiff(wrapcolumn=80)

    # Split content into lines for comparison
    base_lines = base_content.splitlines()
    amendment_lines = amendment_content.splitlines()

    # Generate HTML diff
    html_diff = differ.make_file(
        base_lines,
        amendment_lines,
        fromdesc="Före ändringsförfattning",
        todesc="Efter ändringsförfattning",
        context=True,
        numlines=3
    )

    # Extract the diff table from the generated HTML
    start_marker = '<table class="diff"'
    end_marker = '</table>'

    start_index = html_diff.find(start_marker)
    end_index = html_diff.find(end_marker) + len(end_marker)

    diff_table = ""
    if start_index != -1 and end_index != -1:
        diff_table = html_diff[start_index:end_index]
    else:
        diff_table = '<p>Kunde inte generera diff-tabell.</p>'
    
    # Extract metadata from the amendment HTML
    metadata_match = re.search(r'<div class="metadata">.*?</div>', amendment_html, re.DOTALL)
    metadata_section = metadata_match.group(0) if metadata_match else ""

    # Extract title from amendment HTML
    title_match = re.search(r'<title>(.*?)</title>', amendment_html)
    title = title_match.group(1) if title_match else "Ändringsförfattning"

    # Extract beteckning for navbar
    beteckning_match = re.search(r'Beteckning:</dt>\s*<dd[^>]*>([^<]+)</dd>', amendment_html)
    beteckning = beteckning_match.group(1) if beteckning_match else amendment_beteckning

    # Create the combined HTML document
    combined_html = f"""<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)} - Med ändringar</title>
    <script src="https://swebar.netlify.app/navbar.js"></script>
    <style>{get_common_styles()}
        {get_amendment_styles()}
    </style>
    <script>
        function showTab(tabName) {{
            // Hide all tab contents
            const contents = document.querySelectorAll('.tab-content');
            contents.forEach(content => content.classList.remove('active'));

            // Remove active class from all buttons
            const buttons = document.querySelectorAll('.tab-button');
            buttons.forEach(button => button.classList.remove('active'));

            // Show selected tab content
            document.getElementById(tabName).classList.add('active');

            // Mark button as active
            document.querySelector(`[onclick="showTab('${{tabName}}')"]`).classList.add('active');
        }}

        document.addEventListener('DOMContentLoaded', function() {{
            if (typeof SwedacNavbar !== 'undefined') {{
                SwedacNavbar.setHeader("SFS");
                SwedacNavbar.setHeaderChild("{html.escape(beteckning)}");
            }}
        }});
    </script>
</head>
<body>
    {metadata_section}

    <h1>{html.escape(title)}</h1>

    <div class="amendment-info">
        <h3>Ändringsförfattning {html.escape(amendment_beteckning)}</h3>
        <p><strong>Rubrik:</strong> {html.escape(amendment_rubrik)}</p>
        <p><strong>Ikraft datum:</strong> {html.escape(ikraft_datum)}</p>
        <p><strong>Genererad:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>

    <div class="tab-container">
        <div class="tab-buttons">
            <button class="tab-button active" onclick="showTab('diff')">Visa ändringar</button>
            <button class="tab-button" onclick="showTab('final')">Slutlig version</button>
        </div>

        <div id="diff" class="tab-content active">
            <div class="legend">
                <h3>Förklaring av ändringar</h3>
                <div class="legend-item">
                    <span class="legend-color added"></span>
                    <span>Tillagd text</span>
                </div>
                <div class="legend-item">
                    <span class="legend-color removed"></span>
                    <span>Borttagen text</span>
                </div>
                <div class="legend-item">
                    <span class="legend-color changed"></span>
                    <span>Ändrad text</span>
                </div>
            </div>

            <div class="diff-container">
                {diff_table}
            </div>
        </div>

        <div id="final" class="tab-content">
            {amendment_content}
        </div>
    </div>
</body>
</html>"""

    return combined_html


def create_html_head(title: str, beteckning: str, eli_format: bool = False, additional_styles: str = "", additional_scripts: str = "") -> str:
    """Create HTML head section with navbar integration.

    Args:
        title: Page title
        beteckning: Document beteckning for navbar
        eli_format: Whether to include ELI RDFa prefixes
        additional_styles: Additional CSS styles to include
        additional_scripts: Additional JavaScript to include

    Returns:
        str: Complete HTML head section
    """
    # Import ELI utility functions
    from eli_utils import generate_eli_metadata_html, generate_eli_canonical_url

    head_start = """<!DOCTYPE html>
<html lang="sv"
      prefix="og: http://ogp.me/ns#
      eli: http://data.europa.eu/eli/ontology#
      iana: http://www.iana.org/">
"""

    # Common base styles
    base_styles = f"""
    <style>{get_common_styles()}"""
    if additional_styles:
        base_styles += additional_styles
    base_styles += """
    </style>"""

    # Navbar initialization script
    navbar_script = f"""
    <script src=\"https://swebar.netlify.app/navbar.js\"></script>
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            if (typeof SwedacNavbar !== 'undefined') {{
                SwedacNavbar.setHeader(\"SFS\");
                SwedacNavbar.setHeaderChild(\"{html.escape(beteckning)}\");
            }}
        }});"""
    if additional_scripts:
        navbar_script += additional_scripts
    navbar_script += """
    </script>"""

    # Generate ELI canonical URL and metadata
    eli_metadata = ""
    if beteckning:  # Only generate if we have a valid beteckning
        if eli_format:
            # For ELI format, include both canonical link and ELI metadata (default 'html' format)
            eli_metadata_html = generate_eli_metadata_html(beteckning)
            if eli_metadata_html:
                eli_metadata = '\n    ' + eli_metadata_html.replace('\n', '\n    ')
        else:
            # For regular format, only include canonical link (default 'html' format)
            eli_canonical_url = generate_eli_canonical_url(beteckning)
            if eli_canonical_url:
                eli_metadata = f'\n    <link rel="canonical" href="{eli_canonical_url}" />'

    # Build the head section
    head = f"""<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>{eli_metadata}
{navbar_script}
{base_styles}
</head>"""

    return head_start + head


def get_common_styles() -> str:
    """Get common CSS styles for SFS HTML documents.

    Returns:
        str: CSS styles with color variables and common formatting
    """
    styles = """
        :root {
            --selex-dark-blue: #002147;
            --selex-middle-blue: #0056a0;
            --selex-light-blue: #0072c6;
            --selex-yellow: #f1c40f;
            --selex-white: #ffffff;
            --selex-light-grey: #f5f5f5;
            --selex-dark-grey: #bdc3c7;

            --navbar-dark-blue: var(--selex-dark-blue);
            --navbar-middle-blue: var(--selex-middle-blue);
            --navbar-light-blue: var(--selex-light-blue);
            --navbar-yellow: var(--selex-yellow);
            --navbar-white: var(--selex-white);

            --base-font-size: 14px;
        }

        html {
            font-size: var(--base-font-size);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }

        .metadata {
            background-color: var(--selex-light-grey);
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }

        .metadata dt { font-weight: bold; }
        .metadata dd { margin-left: 20px; margin-bottom: 5px; }

        h1 {
            color: var(--selex-dark-blue);
            border-bottom: 2px solid var(--selex-middle-blue);
            padding-bottom: 10px;
        }

        h2 {
            color: var(--selex-middle-blue);
            border-bottom: 1px solid var(--selex-dark-grey);
            padding-bottom: 5px;
        }

        h3 { color: var(--selex-middle-blue); }
        h4 { color: var(--selex-middle-blue); }"""

    # Minify CSS: remove comments, extra whitespace, semicolons before }, etc.
    minified = minify_css(styles)

    return minified


def minify_css(css_text: str) -> str:
    """Minify CSS by removing comments, whitespace, and unnecessary characters.

    Args:
        css_text: Raw CSS text

    Returns:
        str: Minified CSS
    """
    # Remove CSS comments
    minified = re.sub(r'/\*.*?\*/', '', css_text, flags=re.DOTALL)
    # Remove all whitespace (spaces, tabs, newlines)
    minified = re.sub(r'\s+', '', minified)
    # Remove semicolons before closing braces
    minified = re.sub(r';}', '}', minified)

    return minified


def get_amendment_styles() -> str:
    """Get CSS styles specific to amendment/diff view pages.

    Returns:
        str: Minified CSS styles for amendment pages
    """
    styles = """
        /* Override max-width for diff view */
        body { max-width: 1200px; }

        .amendment-info {
            background-color: #e8f4fd;
            border: 1px solid var(--navbar-middle-blue);
            border-radius: 5px;
            padding: 15px;
            margin: 20px 0;
        }

        .content-section {
            margin: 30px 0;
        }

        .diff-container {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
            margin: 20px 0;
        }

        table.diff {
            width: 100%;
            border-collapse: collapse;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }

        .diff_header {
            background-color: #34495e !important;
            color: white !important;
            font-weight: bold;
            text-align: center;
            padding: 10px;
        }

        .diff_next {
            background-color: #3498db;
            color: white;
            font-weight: bold;
            text-align: center;
            cursor: pointer;
            padding: 5px;
        }

        .diff_next:hover {
            background-color: #2980b9;
        }

        .diff_add {
            background-color: #d4edda !important;
            border-left: 4px solid #28a745;
        }

        .diff_chg {
            background-color: #fff3cd !important;
            border-left: 4px solid #ffc107;
        }

        .diff_sub {
            background-color: #f8d7da !important;
            border-left: 4px solid #dc3545;
        }

        td.diff_header {
            padding: 8px 12px;
        }

        td {
            padding: 4px 8px;
            vertical-align: top;
            white-space: pre-wrap;
            word-wrap: break-word;
        }

        .legend {
            margin: 20px 0;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 8px;
            border: 1px solid #dee2e6;
        }

        .legend h3 {
            margin-top: 0;
            color: #2c3e50;
        }

        .legend-item {
            display: inline-block;
            margin-right: 20px;
            margin-bottom: 5px;
        }

        .legend-color {
            display: inline-block;
            width: 20px;
            height: 15px;
            margin-right: 5px;
            vertical-align: middle;
            border-radius: 3px;
        }

        .added { background-color: #d4edda; border-left: 4px solid #28a745; }
        .removed { background-color: #f8d7da; border-left: 4px solid #dc3545; }
        .changed { background-color: #fff3cd; border-left: 4px solid #ffc107; }

        .tab-container {
            margin: 20px 0;
        }

        .tab-buttons {
            border-bottom: 1px solid #dee2e6;
            margin-bottom: 20px;
        }

        .tab-button {
            background: none;
            border: none;
            padding: 10px 20px;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            font-size: 16px;
            margin-right: 10px;
        }

        .tab-button.active {
            border-bottom-color: var(--navbar-light-blue);
            color: var(--navbar-light-blue);
            font-weight: bold;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }"""

    return minify_css(styles)
