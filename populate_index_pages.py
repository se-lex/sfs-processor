#!/usr/bin/env python3
"""
Populate index pages with the latest SFS documents.

This script generates an HTML index page showing the 30 most recent SFS documents
based on their ikraft_datum (date when they entered into force), sorted from
today's date backwards.
"""

import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import html

# Import existing functions for consistency
from formatters.add_pdf_url_to_frontmatter import generate_pdf_url


def load_all_documents(json_dir: Path) -> List[Dict[str, Any]]:
    """Load all JSON documents from the specified directory.
    
    Args:
        json_dir: Directory containing JSON files
        
    Returns:
        List of document data dictionaries
    """
    documents = []
    
    if not json_dir.exists():
        print(f"Error: JSON directory {json_dir} does not exist")
        return documents
    
    json_files = list(json_dir.glob('*.json'))
    print(f"Found {len(json_files)} JSON files")
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                documents.append(data)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Warning: Error reading {json_file}: {e}")
            continue
    
    return documents


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse date string to datetime object.
    
    Args:
        date_str: Date string in various formats
        
    Returns:
        datetime object or None if parsing fails
    """
    if not date_str:
        return None
    
    # Extract only the date part (first 10 characters: YYYY-MM-DD)
    date_only = date_str[:10]
    
    try:
        return datetime.strptime(date_only, '%Y-%m-%d')
    except ValueError:
        print(f"Warning: Could not parse date: {date_str}")
        return None


def get_latest_documents(documents: List[Dict[str, Any]], limit: int = 30) -> List[Dict[str, Any]]:
    """Get the latest documents sorted by ikraft_datum.
    
    Args:
        documents: List of document data
        limit: Maximum number of documents to return
        
    Returns:
        List of latest documents sorted by date (newest first)
    """
    # Filter documents with valid ikraft_datum and parse dates
    valid_docs = []
    today = datetime.now()
    
    for doc in documents:
        ikraft_datum_str = doc.get('ikraftDateTime', '')
        ikraft_date = parse_date(ikraft_datum_str)
        
        if ikraft_date and ikraft_date <= today:
            doc['_parsed_ikraft_date'] = ikraft_date
            valid_docs.append(doc)
    
    # Sort by ikraft_datum (newest first)
    valid_docs.sort(key=lambda x: x['_parsed_ikraft_date'], reverse=True)
    
    return valid_docs[:limit]


def format_date_for_display(date_str: str) -> str:
    """Format date string for display.
    
    Args:
        date_str: Date string
        
    Returns:
        Formatted date string
    """
    parsed_date = parse_date(date_str)
    if parsed_date:
        return parsed_date.strftime('%Y-%m-%d')
    return date_str


def create_index_html(documents: List[Dict[str, Any]], output_file: Path) -> None:
    """Create HTML index page with the latest documents.
    
    Args:
        documents: List of document data
        output_file: Path to output HTML file
    """
    # Start building HTML content
    html_content = f'''<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aktuella SFS-författningar</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            color: #333;
        }}
        .header {{
            border-bottom: 2px solid #0066cc;
            margin-bottom: 30px;
            padding-bottom: 20px;
        }}
        .header h1 {{
            color: #0066cc;
            margin: 0;
        }}
        .header p {{
            margin: 10px 0 0 0;
            color: #666;
        }}
        .document {{
            border: 1px solid #ddd;
            border-radius: 8px;
            margin-bottom: 20px;
            padding: 20px;
            background: #fff;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .document h2 {{
            margin: 0 0 10px 0;
            color: #333;
        }}
        .document h2 a {{
            text-decoration: none;
            color: #0066cc;
        }}
        .document h2 a:hover {{
            text-decoration: underline;
        }}
        .meta {{
            display: flex;
            gap: 20px;
            margin: 10px 0;
            font-size: 0.9em;
            color: #666;
        }}
        .meta-item {{
            display: flex;
            flex-direction: column;
        }}
        .meta-label {{
            font-weight: bold;
            color: #333;
        }}
        .summary {{
            margin: 15px 0;
            color: #555;
        }}
        .links {{
            margin-top: 15px;
        }}
        .links a {{
            display: inline-block;
            background: #0066cc;
            color: white;
            padding: 8px 16px;
            text-decoration: none;
            border-radius: 4px;
            margin-right: 10px;
            font-size: 0.9em;
        }}
        .links a:hover {{
            background: #0052a3;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Aktuella SFS-författningar</h1>
        <p>De 30 senaste författningarna från Svensk författningssamling, sorterade efter ikraftträdandedatum</p>
        <p>Uppdaterad: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </div>
    
    <main>
'''

    # Add each document
    for doc in documents:
        beteckning = html.escape(doc.get('beteckning', ''))
        rubrik = html.escape(doc.get('rubrik', ''))
        forfattningstyp = html.escape(doc.get('forfattningstypNamn', 'författning'))
        
        # Extract dates
        ikraft_datum = format_date_for_display(doc.get('ikraftDateTime', ''))
        publicerad_datum = format_date_for_display(doc.get('publiceradDateTime', ''))
        
        # Extract other metadata
        fulltext_data = doc.get('fulltext', {})
        utfardad_datum = format_date_for_display(fulltext_data.get('utfardadDateTime', ''))
        
        organisation_data = doc.get('organisation', {})
        organisation = html.escape(organisation_data.get('namn', '')) if organisation_data else ''
        
        # Generate links
        pdf_url = generate_pdf_url(beteckning, utfardad_datum, check_exists=False)
        
        # Create HTML filename (similar to how it's done in sfs_processor.py)
        import re
        safe_beteckning = re.sub(r'[^\w\-]', '-', beteckning)
        html_link = f"{safe_beteckning}_grund.html"
        
        # Extract a brief summary from the content
        innehall_text = fulltext_data.get('forfattningstext', '')
        summary = ""
        if innehall_text and len(innehall_text) > 200:
            # Take first 200 characters and add ellipsis
            summary = html.escape(innehall_text[:200].strip()) + "..."
        elif innehall_text:
            summary = html.escape(innehall_text.strip())
        
        html_content += f'''
        <article class="document">
            <h2><a href="{html_link}">{beteckning}: {rubrik}</a></h2>
            
            <div class="meta">
                <div class="meta-item">
                    <span class="meta-label">Ikraftträdande:</span>
                    <span>{ikraft_datum}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Utfärdad:</span>
                    <span>{utfardad_datum}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Publicerad:</span>
                    <span>{publicerad_datum}</span>
                </div>
                {f'<div class="meta-item"><span class="meta-label">Organisation:</span><span>{organisation}</span></div>' if organisation else ''}
            </div>
            
            {f'<div class="summary">{summary}</div>' if summary else ''}
            
            <div class="links">
                <a href="{html_link}">Visa {forfattningstyp.lower()}</a>
            </div>
        </article>
'''

    html_content += '''
    </main>
    
    <footer class="footer">
        <p>Genererad från Svensk författningssamling (SFS) data</p>
    </footer>
</body>
</html>
'''

    # Save to file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"Index page created: {output_file}")
    except IOError as e:
        print(f"Error writing {output_file}: {e}")


def main():
    """Main function to generate index pages."""
    parser = argparse.ArgumentParser(description='Generate HTML index pages with latest SFS författningar.')
    parser.add_argument('--input', '-i', help='Input directory containing JSON files', default='sfs_json')
    parser.add_argument('--output', '-o', help='Output HTML file', default='index.html')
    parser.add_argument('--limit', '-l', type=int, help='Maximum number of documents to include', default=30)
    
    args = parser.parse_args()
    
    # Define paths
    script_dir = Path(__file__).parent
    json_dir = script_dir / args.input
    output_file = script_dir / args.output
    
    print(f"Loading documents from: {json_dir}")
    print(f"Output file: {output_file}")
    print(f"Document limit: {args.limit}")
    
    # Load all documents
    documents = load_all_documents(json_dir)
    if not documents:
        print("No documents found or loaded")
        return
    
    # Get latest documents
    latest_docs = get_latest_documents(documents, args.limit)
    print(f"Found {len(latest_docs)} documents with valid ikraft_datum")
    
    if not latest_docs:
        print("No documents with valid dates found")
        return
    
    # Create index HTML
    create_index_html(latest_docs, output_file)
    print(f"Successfully created index with {len(latest_docs)} författningar")


if __name__ == "__main__":
    main()
