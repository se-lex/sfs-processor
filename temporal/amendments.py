"""Amendment processing utilities for SFS documents."""

import difflib
from typing import Dict, Any, List
from pathlib import Path
from .apply_temporal import apply_temporal
from util.text_utils import clean_text


def extract_amendments(andringsforfattningar: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract and format amendment information, sorted chronologically by ikraft_datum."""
    from util.datetime_utils import format_datetime  # Import to avoid circular imports
    import re

    amendments = []

    for amendment in andringsforfattningar:
        amendment_data = {
            'beteckning': amendment.get('beteckning'),
            'rubrik': clean_text(amendment.get('rubrik')),
            'ikraft_datum': format_datetime(amendment.get('ikraftDateTime')),
            'anteckningar': clean_text(amendment.get('anteckningar'))
        }

        # Handle CELEX numbers (can be comma-separated or space-separated)
        celex_nummer = amendment.get('celexnummer')
        if celex_nummer:
            # Parse CELEX numbers - split by comma and/or whitespace
            celex_list = [celex.strip() for celex in re.split(r'[,\s]+', celex_nummer) if celex.strip()]

            if len(celex_list) == 1:
                amendment_data['celex'] = celex_list[0]
            elif len(celex_list) > 1:
                amendment_data['celex'] = celex_list

        # Only include non-empty amendments
        if amendment_data['beteckning']:
            amendments.append(amendment_data)

    # Sort amendments chronologically by ikraft_datum
    # Amendments without ikraft_datum will be sorted to the end
    amendments.sort(key=lambda x: x['ikraft_datum'] or '9999-12-31')

    return amendments


def process_markdown_amendments(markdown_content: str, data: Dict[str, Any], git_branch: str = None, verbose: bool = False, output_file: Path = None) -> str:
    """
    Process amendments on markdown content by checking for amendment markers and applying changes.

    This function handles the complete workflow of:
    1. Extracting amendments from document data
    2. Checking for amendment markers in the original text
    3. Splitting markdown content into front matter and body
    4. Applying amendments to the markdown body
    5. Reconstructing the full markdown content

    Args:
        markdown_content (str): The complete markdown content including front matter
        data (Dict[str, Any]): Document data containing amendment information
        git_branch (str): Branch name to use for git commits. If None, no git commits are made.
        verbose (bool): If True, print detailed output during processing
        output_file (Path): Output file path for potential git operations

    Returns:
        str: The processed markdown content with amendments applied, or original content if no processing needed
    """
    
    # Extract beteckning for logging
    beteckning = data.get('beteckning', '')
    
    # Extract the original text content to check for amendment markers
    amendments = extract_amendments(data.get('andringsforfattningar', []))

    # Check for amendment markers and process amendments if they exist
    has_amendment_markers = False  # re.search(r'/.*?I:\d{4}-\d{2}-\d{2}/', innehall_text)
    if verbose and amendments and not has_amendment_markers:
        print(f"Varning: Inga ändringsmarkeringar hittades i {beteckning} men ändringar finns.")

    # Always process temporal sections, even for documents without amendments
    # Extract the markdown body (everything after the front matter)
    if markdown_content.startswith('---'):
        front_matter_end = markdown_content.find('\n---\n', 3)
        if front_matter_end != -1:
            front_matter = markdown_content[:front_matter_end + 5]  # Include the closing ---\n
            markdown_body = markdown_content[front_matter_end + 5:]

            # Apply amendments if they exist, otherwise just apply temporal processing
            if has_amendment_markers and amendments:
                processed_text = apply_amendments_to_text(markdown_body, amendments, git_branch, verbose, output_file)
                if verbose:
                    print(f"Debug: Bearbetad textlängd för {beteckning}: {len(processed_text)}")
            else:
                # No amendments, but still apply temporal processing for current date
                from datetime import date
                current_date = date.today().strftime('%Y-%m-%d')
                processed_text = apply_temporal(markdown_body, current_date)
                if verbose:
                    print(f"Info: Temporal processing tillämpat på {beteckning} utan ändringar för datum {current_date}")

            # Reconstruct the full content
            processed_markdown = front_matter + "\n\n" + processed_text
            return processed_markdown
        else:
            print(f"Varning: Kunde inte hitta slutet på front matter för {beteckning}")
            return markdown_content
    else:
        print(f"Varning: Markdown-innehåll börjar inte med front matter för {beteckning}")
        return markdown_content


def apply_amendments_to_text(text: str, amendments: List[Dict[str, Any]], git_branch: str = None, verbose: bool = False, output_file: Path = None) -> str:
    """
    Apply changes to SFS text based on amendment dates.

    This function processes each amendment in chronological order and applies
    changes using apply_temporal with the amendment's ikraft_datum
    as the target date. Optionally creates Git commits for each amendment.

    Args:
        text (str): The original SFS text
        amendments (List[Dict[str, Any]]): List of amendments with ikraft_datum
        git_branch (str): Branch name to use for git commits. Currently unused but kept for compatibility.
        verbose (bool): If True, print smart diff output to console for each amendment
        output_file (Path): Output file path. Currently unused but kept for compatibility.

    Returns:
        str: The text with changes applied
    """
    # Mark unused parameters as intentionally unused
    _ = git_branch
    _ = output_file

    processed_text = text

    # Filter amendments that have ikraft_datum (already sorted by extract_amendments)
    sorted_amendments = [a for a in amendments if a.get('ikraft_datum')]

    # Print number of amendments found
    if verbose:
        print(f"Hittade {len(sorted_amendments)} ändringar att bearbeta.")

    # Kolla så det är lika många amenedments som ikraft_datum
    if len(sorted_amendments) != len(set(a['ikraft_datum'] for a in sorted_amendments)):
        print("Varning: Duplicerade ikraft_datum hittades i ändringar. Detta kan orsaka oväntat beteende.")

    for amendment in sorted_amendments:
        ikraft_datum = amendment.get('ikraft_datum')
        rubrik = amendment.get('rubrik', 'Ändringsförfattning')

        if verbose:
            print(f"\n{'='*60}")
            print(f"Bearbetar ÄNDRINGSFÖRFATTNING: {rubrik} ({ikraft_datum})")
            print(f"{'='*60}")
            print('')

        if ikraft_datum:
            # Store text before changes for debug comparison
            text_before_changes = processed_text

            processed_text = apply_temporal(processed_text, ikraft_datum, verbose)

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

    return processed_text
