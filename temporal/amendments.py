"""Amendment processing utilities for SFS documents."""

import difflib
from typing import Dict, Any, List
from pathlib import Path
from formatters.format_sfs_text import apply_changes_to_sfs_text


def apply_amendments_to_text(text: str, amendments: List[Dict[str, Any]], git_branch: str = None, verbose: bool = False, output_file: Path = None) -> str:
    """
    Apply changes to SFS text based on amendment dates.

    This function processes each amendment in chronological order and applies
    changes using apply_changes_to_sfs_text with the amendment's ikraft_datum
    as the target date. Optionally creates Git commits for each amendment.

    Args:
        text (str): The original SFS text
        amendments (List[Dict[str, Any]]): List of amendments with ikraft_datum
        git_branch (str): Branch name to use for git commits. If None, no git commits are made.
        verbose (bool): If True, print smart diff output to console for each amendment
        output_file (Path): Output file path (currently unused but kept for compatibility)

    Returns:
        str: The text with changes applied
    """

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
        beteckning = amendment.get('beteckning', '')
        rubrik = amendment.get('rubrik', 'Ändringsförfattning')

        if verbose:
            print(f"\n{'='*60}")
            print(f"Bearbetar ÄNDRINGSFÖRFATTNING: {rubrik} ({ikraft_datum})")
            print(f"{'='*60}")
            print('')

        if ikraft_datum:
            # Store text before changes for debug comparison
            text_before_changes = processed_text

            processed_text = apply_changes_to_sfs_text(processed_text, ikraft_datum, verbose)

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
