import difflib
import html
import re
from datetime import datetime
from pathlib import Path

def create_html_diff(text_before: str, text_after: str, beteckning: str, rubrik: str, ikraft_datum: str, output_dir: Path = None) -> str:
    """
    Create an HTML diff file showing changes between before and after text.

    Args:
        text_before: Text before changes
        text_after: Text after changes
        beteckning: Amendment beteckning (used for filename)
        rubrik: Amendment title
        ikraft_datum: Date when changes take effect
        output_dir: Directory to save HTML file (defaults to current directory)

    Returns:
        str: Path to the created HTML file
    """
    if output_dir is None:
        output_dir = Path('.')

    # Create HTML diff using difflib
    differ = difflib.HtmlDiff(wrapcolumn=80)

    # Split text into lines for comparison
    before_lines = text_before.splitlines()
    after_lines = text_after.splitlines()

    # Generate HTML diff
    html_diff = differ.make_file(
        before_lines,
        after_lines,
        fromdesc=f"Före ändringsförfattning {beteckning}",
        todesc=f"Efter ändringsförfattning {beteckning}",
        context=True,
        numlines=3
    )

    # Add custom styling and metadata
    custom_html = f"""<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ändringsförfattning {beteckning} - Textändringar</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background-color: #2c3e50;
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 24px;
        }}
        .header p {{
            margin: 5px 0;
            opacity: 0.9;
        }}
        .diff-container {{
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        table.diff {{
            width: 100%;
            border-collapse: collapse;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }}
        .diff_header {{
            background-color: #34495e !important;
            color: white !important;
            font-weight: bold;
            text-align: center;
            padding: 10px;
        }}
        .diff_next {{
            background-color: #3498db;
            color: white;
            font-weight: bold;
            text-align: center;
            cursor: pointer;
            padding: 5px;
        }}
        .diff_next:hover {{
            background-color: #2980b9;
        }}
        .diff_add {{
            background-color: #d4edda !important;
            border-left: 4px solid #28a745;
        }}
        .diff_chg {{
            background-color: #fff3cd !important;
            border-left: 4px solid #ffc107;
        }}
        .diff_sub {{
            background-color: #f8d7da !important;
            border-left: 4px solid #dc3545;
        }}
        td.diff_header {{
            padding: 8px 12px;
        }}
        td {{
            padding: 4px 8px;
            vertical-align: top;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .legend {{
            margin-top: 20px;
            padding: 15px;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .legend h3 {{
            margin-top: 0;
            color: #2c3e50;
        }}
        .legend-item {{
            display: inline-block;
            margin-right: 20px;
            margin-bottom: 5px;
        }}
        .legend-color {{
            display: inline-block;
            width: 20px;
            height: 15px;
            margin-right: 5px;
            vertical-align: middle;
            border-radius: 3px;
        }}
        .added {{ background-color: #d4edda; border-left: 4px solid #28a745; }}
        .removed {{ background-color: #f8d7da; border-left: 4px solid #dc3545; }}
        .changed {{ background-color: #fff3cd; border-left: 4px solid #ffc107; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Ändringsförfattning {html.escape(beteckning)}</h1>
        <p><strong>Rubrik:</strong> {html.escape(rubrik)}</p>
        <p><strong>Ikraft datum:</strong> {html.escape(ikraft_datum)}</p>
        <p><strong>Genererad:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>

    <div class="diff-container">
"""

    # Extract the table from the generated HTML diff and add it
    # Remove the generated HTML structure and keep only the diff table
    start_marker = '<table class="diff"'
    end_marker = '</table>'

    start_index = html_diff.find(start_marker)
    end_index = html_diff.find(end_marker) + len(end_marker)

    if start_index != -1 and end_index != -1:
        diff_table = html_diff[start_index:end_index]
        custom_html += diff_table
    else:
        custom_html += '<p>Kunde inte generera diff-tabell.</p>'

    custom_html += """
    </div>

    <div class="legend">
        <h3>Förklaring</h3>
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
</body>
</html>"""

    # Create safe filename from beteckning
    safe_beteckning = re.sub(r'[^\w\-]', '-', beteckning)
    html_filename = f"diff-{safe_beteckning}.html"
    html_filepath = output_dir / html_filename

    # Write HTML file
    try:
        with open(html_filepath, 'w', encoding='utf-8') as f:
            f.write(custom_html)
        print(f"HTML diff saved: {html_filepath}")
        return str(html_filepath)
    except IOError as e:
        print(f"Error writing HTML diff file {html_filepath}: {e}")
        return ""
