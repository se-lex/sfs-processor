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
import markdown

# Import required functions from other modules
from formatters.format_sfs_text import format_sfs_text_as_markdown
from formatters.add_pdf_url_to_frontmatter import generate_pdf_url
from temporal.apply_temporal import apply_temporal
from exporters.html.styling_constants import get_css_variables
from downloaders.eur_lex_api import generate_eur_lex_url


def format_celex_as_links(celex_numbers: str) -> str:
    """
    Convert Celex numbers to clickable EUR-Lex links.
    
    Handles multiple Celex numbers separated by commas or spaces.
    
    Args:
        celex_numbers (str): One or more Celex numbers (e.g., "32001L0083, 32004L0027")
        
    Returns:
        str: HTML string with clickable links to EUR-Lex
    """
    if not celex_numbers:
        return ""
    
    # Split by comma and/or whitespace, filter out empty strings
    celex_list = [celex.strip() for celex in re.split(r'[,\s]+', celex_numbers) if celex.strip()]
    
    # Convert each Celex number to a link
    links = []
    for celex in celex_list:
        url = generate_eur_lex_url(celex)
        links.append(f'<a href="{html.escape(url)}" target="_blank">{html.escape(celex)}</a>')
    
    return ', '.join(links)


def create_html_documents(data: Dict[str, Any], output_path: Path, include_amendments: bool = False) -> None:
    """Create HTML documents from JSON data using ELI directory structure.

    Creates documents in ELI directory structure: /eli/sfs/{YEAR}/{lopnummer}
    and optionally separate documents for each amendment.

    Args:
        data: JSON data containing document information
        output_path: Base path for output (will create eli/sfs/{YEAR}/{lopnummer} subdirectory)
        include_amendments: Whether to generate amendment versions (default: False)
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

    # Create directory structure: /eli/sfs/{YEAR}/{lopnummer}
    eli_dir = output_path / "eli" / "sfs" / year / lopnummer
    eli_dir.mkdir(parents=True, exist_ok=True)

    # Generate base HTML content (without amendments applied)
    base_html_content = convert_to_html(data, apply_amendments=False)
    base_file = eli_dir / "index.html"
    save_to_disk(base_file, base_html_content)
    print(f"Created HTML document: {base_file}")

    # Create HTML documents for each amendment stage
    if include_amendments:
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
                amendment_html_content = convert_to_html(data, apply_amendments=True, up_to_amendment=i+1)

                # Create HTML with diff view comparing base and amended content
                amendment_html_with_diff = create_amendment_html_with_diff(
                    base_html_content, amendment_html_content, amendment_beteckning, amendment.get('rubrik', ''),
                    amendment.get('ikraft_datum', '')
                )

                amendment_file = amend_eli_dir / "index.html"
                save_to_disk(amendment_file, amendment_html_with_diff)
                print(f"Created amendment HTML document: {amendment_file}")


def generate_css_file(css_dir: Path) -> None:
    """Generate the shared CSS file for HTML documents.
    
    Creates a styles.css file in the specified directory containing all
    CSS styles and variables used by HTML documents.
    
    Args:
        css_dir: Directory where the CSS file should be created
    """
    from sfs_processor import save_to_disk
    
    css_file_path = css_dir / "styles.css"
    
    # Only generate if it doesn't exist to avoid regenerating on every document
    if css_file_path.exists():
        return
    
    # Generate the complete CSS content
    css_content = get_common_styles()
    
    # Save the CSS file
    save_to_disk(css_file_path, css_content)
    print(f"Generated CSS file: {css_file_path}")


def generate_js_file(js_dir: Path) -> None:
    """Generate the shared JavaScript file for HTML documents.
    
    Creates a selex-init.js file in the specified directory by copying
    the source JavaScript file from the html exporter directory.
    
    Args:
        js_dir: Directory where the JS file should be created
    """
    import shutil
    
    js_file_path = js_dir / "selex-init.js"
    
    # Only generate if it doesn't exist to avoid regenerating on every document
    if js_file_path.exists():
        return
    
    # Get the source JS file path (same directory as this module)
    source_js_path = Path(__file__).parent / "selex-init.js"
    
    if not source_js_path.exists():
        print(f"Warning: Source JS file not found: {source_js_path}")
        return
    
    # Copy the JS file
    try:
        shutil.copy2(source_js_path, js_file_path)
        print(f"Generated JS file: {js_file_path}")
    except Exception as e:
        print(f"Error copying JS file: {e}")



def convert_to_html(data: Dict[str, Any], apply_amendments: bool = False, up_to_amendment: int = None) -> str:
    """Convert JSON data to HTML format with ELI structure.

    Args:
        data: JSON data for the document
        apply_amendments: Whether to apply amendments
        up_to_amendment: If applying amendments, apply only up to this amendment index (1-based)

    Returns:
        str: HTML content
    """
    # Import required functions (avoiding circular imports)
    from sfs_processor import (
        format_datetime, ignore_rules, extract_amendments
    )
    from util.text_utils import clean_text

    # Extract main document information
    beteckning = data.get('beteckning', '')
    rubrik_original = data.get('rubrik', '')

    # Extract dates
    publicerad_datum = format_datetime(data.get('publiceradDateTime'))
    fulltext_data = data.get('fulltext', {})
    utfardad_datum = format_datetime(fulltext_data.get('utfardadDateTime'))
    ikraft_datum = format_datetime(data.get('ikraftDateTime'))

    # Extract other metadata
    register_data = data.get('register', {})
    forarbeten = clean_text(register_data.get('forarbeten', ''))
    celex_nummer = data.get('celexnummer')
    eu_direktiv = data.get('eUdirektiv', False)
    organisation_data = data.get('organisation', {})
    organisation = organisation_data.get('namn', '') if organisation_data else ''

    # Determine doctype (grundlag, lag, or förordning)
    from util.doctype_utils import determine_doctype
    forfattningstyp_namn = data.get('forfattningstypNamn')
    doctype = determine_doctype(beteckning, forfattningstyp_namn)

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
    formatted_text = format_sfs_text_as_markdown(innehall_text, apply_links=True)
    
    # Apply section tags for HTML export (preserve selex tags)
    from formatters.format_sfs_text import parse_logical_sections
    formatted_text = parse_logical_sections(formatted_text)

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
                    formatted_text = apply_temporal(formatted_text, ikraft_datum_amendment, False)

    # Convert markdown-formatted text to HTML
    html_content = markdown_to_html(formatted_text)
    
    # Strip base URL from links to make them relative for HTML export
    html_content = make_links_relative(html_content)

    # Create HTML document with navbar integration and ELI format
    html_doc = create_html_head(rubrik_original, beteckning)
    html_doc += f"\n<body data-beteckning=\"{html.escape(beteckning)}\">"

    # Build metadata in two columns
    column1_items = []
    column2_items = []
    
    # Column 1: Basic document info
    column1_items.append(f"""
            <dt>Beteckning:</dt>
            <dd property="eli:id_local" datatype="xsd:string">{html.escape(beteckning)}</dd>""")

    if organisation:
        column1_items.append(f"""
            <dt>Departement:</dt>
            <dd property="eli:passed_by" datatype="xsd:string">{html.escape(organisation)}</dd>""")

    if doctype:
        column1_items.append(f"""
            <dt>Doctype:</dt>
            <dd property="eli:type_document" datatype="xsd:string">{html.escape(doctype)}</dd>""")
    
    if pdf_url:
        column1_items.append(f"""
            <dt>PDF-fil:</dt>
            <dd><a href="{html.escape(pdf_url)}" property="eli:is_realized_by" datatype="xsd:anyURI">PDF-fil</a></dd>""")
    
    if forarbeten:
        column1_items.append(f"""
            <dt>Förarbeten:</dt>
            <dd property="eli:preparatory_act" datatype="xsd:string">{html.escape(forarbeten)}</dd>""")
    
    if celex_nummer:
        celex_links = format_celex_as_links(celex_nummer)
        column1_items.append(f"""
            <dt>CELEX:</dt>
            <dd property="eli:related_to" resource="{html.escape(celex_nummer)}" datatype="xsd:string">{celex_links}</dd>""")
    
    if eu_direktiv:
        column1_items.append("""
            <dt>EU-direktiv:</dt>
            <dd property="eli:type_document" resource="http://data.europa.eu/eli/ontology#directive" datatype="xsd:boolean">Ja</dd>""")
    
    # Column 2: Dates and links
    if publicerad_datum:
        column2_items.append(f"""
            <dt>Publicerad:</dt>
            <dd property="eli:date_publication" datatype="xsd:date">{html.escape(publicerad_datum)}</dd>""")
    
    if utfardad_datum:
        column2_items.append(f"""
            <dt>Utfärdad:</dt>
            <dd property="eli:date_document" datatype="xsd:date">{html.escape(utfardad_datum)}</dd>""")
    
    if ikraft_datum:
        column2_items.append(f"""
            <dt>Ikraft:</dt>
            <dd property="eli:date_entry-into-force" datatype="xsd:date">{html.escape(ikraft_datum)}</dd>""")
    
    html_doc += f"""
    <div class="metadata">
        <div class="metadata-column">
            <dl>
                {''.join(column1_items)}
            </dl>
        </div>
        <div class="metadata-column">
            <dl>
                {''.join(column2_items)}
            </dl>
        </div>
    </div>"""

    # Add the rest of the HTML document
    html_doc += f"""
    <article>
    <h1>{html.escape(rubrik_original)}</h1>

    {html_content}
    </article>
</body>
</html>"""

    return html_doc



def make_links_relative(html_content: str) -> str:
    """
    Strip base URL from links to make them relative for HTML export.
    
    Removes https://selex.se/eli from links to make them relative.
    
    Args:
        html_content (str): HTML content with potentially absolute links
        
    Returns:
        str: HTML content with relative links
    """
    # Pattern to match https://selex.se/eli in href attributes
    pattern = r'href="https://selex\.se/eli(/[^"]*)"'
    replacement = r'href="\1"'
    
    return re.sub(pattern, replacement, html_content)


def markdown_to_html(markdown_text: str) -> str:
    """Convert markdown formatting to HTML using the markdown library.
    
    Preserves selex tags (<section>, <article>) and their attributes.

    Args:
        markdown_text: Text with markdown formatting

    Returns:
        str: HTML formatted text
    """
    # Pre-process: Mark selex tags for markdown processing
    processed_text = prepare_markdown_with_selex_tags(markdown_text)
    
    # Configure markdown with useful extensions
    md = markdown.Markdown(
        extensions=[
            'tables',          # Support for tables
            'attr_list',       # Support for {: .class} attributes
            'md_in_html',      # Allow markdown inside HTML blocks
        ]
    )
    
    # Convert markdown to HTML
    html_content = md.convert(processed_text)
    
    return html_content


def prepare_markdown_with_selex_tags(markdown_text: str) -> str:
    """
    Prepare markdown text with selex tags for proper markdown processing.
    
    The md_in_html extension requires markdown="1" attribute on HTML block elements
    to process markdown content inside them.
    """
    # Add markdown="1" to section and article tags
    processed = re.sub(r'<(section[^>]*)>', r'<\1 markdown="1">', markdown_text)
    processed = re.sub(r'<(article[^>]*)>', r'<\1 markdown="1">', processed)
    
    return processed


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
        .warning { background-color: var(--warning-yellow-bg); border: 1px solid var(--warning-yellow); padding: 15px; border-radius: 5px; margin-bottom: 20px; }""")

    # Use external CSS for ignored documents as well
    html_doc = create_html_head(rubrik_original, beteckning, additional_styles=ignored_styles, use_external_css=True)
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
    <script>
        window.NAVBAR_CONFIG = {{
            logoUrl: "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 300 70'><text x='0' y='60' font-family='Inter, sans-serif' font-size='70' fill='%23f1c40f'>SE-Lex</text></svg>",
            drawerEnabled: false,
        }};
    </script>
    <script src="../../selex-init.js" defer></script>
    <style>{get_common_styles()}
        {get_amendment_styles()}
    </style>
</head>
<body data-beteckning="{html.escape(beteckning)}">
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
            <button class="tab-button active" data-tab="diff">Visa ändringar</button>
            <button class="tab-button" data-tab="final">Slutlig version</button>
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


def create_html_head(title: str, beteckning: str, additional_styles: str = "", additional_scripts: str = "", use_external_css: bool = True, css_relative_path: str = "../../styles.css", js_relative_path: str = "../../selex-init.js") -> str:
    """Create HTML head section with navbar integration.

    Args:
        title: Page title
        beteckning: Document beteckning for navbar
        additional_styles: Additional CSS styles to include inline
        additional_scripts: Additional JavaScript to include
        use_external_css: Whether to use external CSS file (default: True)
        css_relative_path: Relative path to CSS file from HTML document (default: "../../styles.css")
        js_relative_path: Relative path to JS file from HTML document (default: "../../selex-init.js")

    Returns:
        str: Complete HTML head section
    """
    # Import ELI utility functions
    from exporters.html.eli_utils import generate_eli_metadata_html, generate_eli_canonical_url

    head_start = """<!DOCTYPE html>
<html lang="sv"
      prefix="og: http://ogp.me/ns#
      eli: http://data.europa.eu/eli/ontology#
      iana: http://www.iana.org/">
"""

    # CSS styles - either external link or inline
    if use_external_css:
        base_styles = f"""
    <link rel="stylesheet" href="{css_relative_path}">"""
        if additional_styles:
            # Only add inline styles if there are additional styles
            base_styles += f"""
    <style>{additional_styles}</style>"""
    else:
        # Fallback to inline styles (for ignored documents or special cases)
        base_styles = f"""
    <style>{get_common_styles()}"""
        if additional_styles:
            base_styles += additional_styles
        base_styles += """
    </style>"""

    # Navbar configuration and external scripts
    navbar_script = f"""
    <script>
        window.NAVBAR_CONFIG = {{
            logoUrl: "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 300 70'><text x='0' y='60' font-family='Inter, sans-serif' font-size='70' fill='%23f1c40f'>SE-Lex</text></svg>",
            drawerEnabled: false,
        }};
    </script>
    <script src=\"{js_relative_path}\" defer></script>"""
    if additional_scripts:
        navbar_script += f"""
    <script>
{additional_scripts}
    </script>"""

    # Generate ELI canonical URL and metadata
    eli_metadata = ""
    # For ELI format, include both canonical link and ELI metadata (default 'html' format)
    eli_metadata_html = generate_eli_metadata_html(beteckning)
    if eli_metadata_html:
        eli_metadata = '\n    ' + eli_metadata_html.replace('\n', '\n    ')
    # Generate canonical URL for ELI
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
    # Get CSS variables from styling constants
    css_vars = get_css_variables()
    
    styles = f"""
        {css_vars}

        html {{
            font-size: var(--base-font-size);
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: var(--font-primary);
            max-width: 700px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            background-color: var(--selex-white);
            -webkit-text-size-adjust: 100%;
            -webkit-font-smoothing: antialiased;
            text-rendering: optimizeLegibility;
        }}

        .metadata {{
            background-color: var(--selex-light-grey);
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}

        .metadata-column {{
            display: flex;
            flex-direction: column;
        }}

        .metadata dt {{ font-weight: bold; }}
        .metadata dd {{ margin-left: 20px; margin-bottom: 5px; }}
        
        @media (max-width: 768px) {{
            .metadata {{
                grid-template-columns: 1fr;
                gap: 10px;
            }}
        }}

        h1 {{
            color: var(--selex-dark-blue);
            padding: 15px 0 8px 0;
            font-size: var(--h1-font-size);
        }}

        h2 {{
            color: var(--selex-dark-blue);
            border-bottom: 1px solid var(--selex-dark-grey);
            padding: 12px 0 4px 0;
        }}

        h3 {{ 
            color: var(--selex-dark-blue); 
            padding: 10px 0 6px 0;
        }}
        
        h4 {{ 
            color: #333; 
            display: inline;
            padding-right: 20px;
            margin: 0;
            font-weight: bold;
        }}
        
        /* Make p tags that follow h4 display inline */
        h4 + p {{
            display: inline;
        }}
        
        /* Ensure proper spacing after inline paragraph */
        section.paragraf p {{
            margin-bottom: 1em;
        }}

        /* Selex section styling */
        article {{
            margin: 20px 0;
            padding-bottom: 60px;
        }}

        section.kapitel {{
            margin: 20px 0;
            padding: 10px 0;
        }}
        
        section.paragraf {{
            margin: 0 0 10px 0;
        }}
        
        section[status="upphavd"] {{
            opacity: 0.6;
            text-decoration: line-through;
        }}
        
        section[status="ikraft"] {{
            border-left: 3px solid var(--selex-light-blue);
            padding-left: 15px;
        }}

        /* Markdown content styling */
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        
        th, td {{
            border: 1px solid var(--border-grey);
            padding: 8px 12px;
            text-align: left;
        }}
        
        th {{
            background-color: var(--selex-light-grey);
            font-weight: bold;
            color: var(--selex-dark-blue);
        }}
        
        code {{
            background-color: var(--selex-light-grey);
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}
        
        pre {{
            background-color: var(--selex-light-grey);
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            border-left: 4px solid var(--selex-light-blue);
        }}
        
        pre code {{
            background-color: transparent;
            padding: 0;
        }}
        
        blockquote {{
            border-left: 4px solid var(--selex-light-blue);
            padding-left: 15px;
            margin: 15px 0;
            color: var(--text-muted);
            font-style: italic;
        }}
        
        ul, ol {{
            margin: 15px 0;
            padding-left: 30px;
        }}
        
        li {{
            margin: 5px 0;
        }}
        
        /* Link styling */
        a {{
            color: var(--selex-middle-blue);
        }}
        
        a:hover {{
            color: var(--selex-middle-blue-hover);
        }}"""

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
    
    # Remove newlines and extra whitespace, but keep necessary spaces
    minified = re.sub(r'\s+', ' ', minified)  # Replace multiple whitespace with single space
    minified = re.sub(r'\s*{\s*', '{', minified)  # Remove spaces around {
    minified = re.sub(r'\s*}\s*', '}', minified)  # Remove spaces around }
    minified = re.sub(r'\s*;\s*', ';', minified)  # Remove spaces around ;
    minified = re.sub(r'\s*:\s*', ':', minified)  # Remove spaces around :
    minified = re.sub(r'\s*,\s*', ',', minified)  # Remove spaces around ,
    
    # Remove semicolons before closing braces
    minified = re.sub(r';}', '}', minified)
    
    # Trim leading/trailing whitespace
    minified = minified.strip()

    return minified


def get_amendment_styles() -> str:
    """Get CSS styles specific to amendment/diff view pages.

    Returns:
        str: Minified CSS styles for amendment pages
    """
    styles = """
        /* Override max-width for diff view */
        body { max-width: 1000px; }

        .amendment-info {
            background-color: var(--selex-light-grey);
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
            background-color: var(--selex-middle-blue) !important;
            color: white !important;
            font-weight: bold;
            text-align: center;
            padding: 10px;
        }

        .diff_next {
            background-color: var(--selex-light-blue);
            color: white;
            font-weight: bold;
            text-align: center;
            cursor: pointer;
            padding: 5px;
        }

        .diff_next:hover {
            background-color: var(--selex-light-blue-hover);
        }

        .diff_add {
            background-color: var(--success-green-bg) !important;
            border-left: 4px solid var(--success-green);
        }

        .diff_chg {
            background-color: var(--warning-yellow-bg) !important;
            border-left: 4px solid var(--warning-yellow);
        }

        .diff_sub {
            background-color: var(--danger-red-bg) !important;
            border-left: 4px solid var(--danger-red);
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
            background-color: var(--bg-light-grey);
            border-radius: 8px;
            border: 1px solid var(--border-light-grey);
        }

        .legend h3 {
            margin-top: 0;
            color: var(--selex-dark-blue);
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

        .added { background-color: var(--success-green-bg); border-left: 4px solid var(--success-green); }
        .removed { background-color: var(--danger-red-bg); border-left: 4px solid var(--danger-red); }
        .changed { background-color: var(--warning-yellow-bg); border-left: 4px solid var(--warning-yellow); }

        .tab-container {
            margin: 20px 0;
        }

        .tab-buttons {
            border-bottom: 1px solid var(--border-light-grey);
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
