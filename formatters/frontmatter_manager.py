"""
Frontmatter management utilities for SFS documents.

This module contains functions for manipulating YAML frontmatter in markdown documents.
"""

from util.yaml_utils import format_yaml_value
from formatters.sort_frontmatter import sort_frontmatter_properties


def add_ikraft_datum_to_frontmatter(markdown_content: str, ikraft_datum: str, beteckning: str = "") -> str:
    """
    Add ikraft_datum to the YAML front matter and sort it.
    
    Args:
        markdown_content: The markdown content with YAML front matter
        ikraft_datum: The ikraft_datum value to add
        beteckning: Document identifier for error messages (optional)
    
    Returns:
        str: Updated markdown content with ikraft_datum added and front matter sorted
    """
    # Add ikraft_datum to front matter
    # Find the position of the closing --- and insert before it
    closing_marker = '\n---\n'
    if closing_marker in markdown_content:
        before_closing, after_closing = markdown_content.split(closing_marker, 1)
        ikraft_line = f"ikraft_datum: {format_yaml_value(ikraft_datum)}"
        # Preserve the original spacing after the front matter
        updated_content = f"{before_closing}\n{ikraft_line}\n---\n{after_closing}"
    else:
        # Fallback: return original content if no proper front matter found
        updated_content = markdown_content

    try:
        # Extract and sort front matter if it exists
        if updated_content.startswith('---'):
            # Find the end of the front matter
            front_matter_end = updated_content.find('\n---\n', 3)
            if front_matter_end != -1:
                # Extract front matter and content, preserving spacing
                end_of_frontmatter = front_matter_end + 4  # Position after \n---
                while end_of_frontmatter < len(updated_content) and updated_content[end_of_frontmatter] == '\n':
                    end_of_frontmatter += 1

                front_matter = updated_content[:front_matter_end + 4]  # Include up to \n---
                rest_of_content = updated_content[end_of_frontmatter:]

                # Sort only the front matter and ensure proper spacing
                sorted_front_matter = sort_frontmatter_properties(front_matter + '\n')
                updated_content = sorted_front_matter + '\n' + rest_of_content
    except ValueError as e:
        error_context = f" för {beteckning}" if beteckning else ""
        print(f"Varning: Kunde inte sortera front matter efter att ha lagt till ikraft_datum{error_context}: {e}")

    return updated_content
