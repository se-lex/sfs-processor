"""
Frontmatter management utilities for SFS documents.

This module contains functions for manipulating YAML frontmatter in markdown documents.
"""

from util.yaml_utils import format_yaml_value
from formatters.sort_frontmatter import sort_frontmatter_properties
import re
import yaml
from typing import Optional


def add_ikraft_datum_to_frontmatter(markdown_content: str, ikraft_datum: str) -> str:
    """
    Add ikraft_datum to the YAML front matter and sort it.

    Args:
        markdown_content: The markdown content with YAML front matter
        ikraft_datum: The ikraft_datum value to add

    Returns:
        str: Updated markdown content with ikraft_datum added and front matter sorted
    """
    return set_prop_in_frontmatter(markdown_content, "ikraft_datum", ikraft_datum)


def set_prop_in_frontmatter(markdown_content: str, property_name: str, new_value: str) -> str:
    """
    Set a property in the YAML front matter and sort it.

    Args:
        markdown_content: The markdown content with YAML front matter
        property_name: The name of the property to set
        new_value: The new value to set

    Returns:
        str: Updated markdown content with property updated and front matter sorted
    """
    updated_content = markdown_content

    try:
        # Find the frontmatter section
        closing_marker = '\n---\n'
        if closing_marker in markdown_content:
            before_closing, after_closing = markdown_content.split(closing_marker, 1)

            # Check if property already exists and update it
            property_pattern = re.compile(rf'^{re.escape(property_name)}:\s*.*$', re.MULTILINE)
            if property_pattern.search(before_closing):
                # Update existing property
                new_property_line = f"{property_name}: {format_yaml_value(new_value)}"
                updated_front_matter = property_pattern.sub(new_property_line, before_closing)
                updated_content = f"{updated_front_matter}\n---\n{after_closing}"
            else:
                # Add new property
                property_line = f"{property_name}: {format_yaml_value(new_value)}"
                updated_content = f"{before_closing}\n{property_line}\n---\n{after_closing}"

            # Sort the front matter
            try:
                # Extract and sort just the front matter
                front_matter_start = updated_content.find('---\n') + 4
                front_matter_end = updated_content.find('\n---\n', front_matter_start)
                front_matter = updated_content[front_matter_start:front_matter_end]

                # Skip any extra empty lines after the front matter closing marker
                end_of_frontmatter = front_matter_end + 5  # Skip '\n---\n'
                while end_of_frontmatter < len(
                        updated_content) and updated_content[end_of_frontmatter] == '\n':
                    end_of_frontmatter += 1
                rest_of_content = updated_content[end_of_frontmatter:]

                # Sort only the front matter and ensure proper spacing
                # Construct the full frontmatter block with markers for the sorting function
                full_frontmatter_block = f"---\n{front_matter}\n---"
                sorted_front_matter = sort_frontmatter_properties(full_frontmatter_block)
                updated_content = sorted_front_matter + '\n' + rest_of_content
            except ValueError as e:
                print(
                    f"Varning: Kunde inte sortera front matter efter att ha uppdaterat {property_name}: {e}")

    except Exception as e:
        print(f"Varning: Kunde inte uppdatera {property_name} i frontmatter: {e}")

    return updated_content


def remove_prop_from_frontmatter(markdown_content: str, property_name: str) -> str:
    """
    Remove a property from the YAML front matter and sort it.

    Args:
        markdown_content: The markdown content with YAML front matter
        property_name: The name of the property to remove

    Returns:
        str: Updated markdown content with property removed and front matter sorted
    """
    updated_content = markdown_content

    try:
        # Find the frontmatter section
        closing_marker = '\n---\n'
        if closing_marker in markdown_content:
            before_closing, after_closing = markdown_content.split(closing_marker, 1)

            # Remove the property if it exists (including multi-line properties like lists)
            lines = before_closing.split('\n')
            filtered_lines = []
            skip_until_next_property = False

            for line in lines:
                # Check if this is the start of the property to remove
                if line.startswith(f"{property_name}:"):
                    skip_until_next_property = True
                    continue

                # If we're skipping and find a new property (starts at column 0), stop skipping
                if skip_until_next_property:
                    if line and not line.startswith(
                            ' ') and not line.startswith('\t') and ':' in line:
                        skip_until_next_property = False
                        filtered_lines.append(line)
                    # Skip lines that are part of the property (indented or list items)
                    continue

                filtered_lines.append(line)

            # Reconstruct the content if property was found
            if len(filtered_lines) != len(lines):
                updated_content = '\n'.join(filtered_lines) + '\n---\n' + after_closing

                # Sort the front matter
                try:
                    # Extract and sort just the front matter
                    front_matter_start = updated_content.find('---\n') + 4
                    front_matter_end = updated_content.find('\n---\n', front_matter_start)
                    front_matter = updated_content[front_matter_start:front_matter_end]

                    # Skip any extra empty lines after the front matter closing marker
                    end_of_frontmatter = front_matter_end + 5  # Skip '\n---\n'
                    while end_of_frontmatter < len(
                            updated_content) and updated_content[end_of_frontmatter] == '\n':
                        end_of_frontmatter += 1
                    rest_of_content = updated_content[end_of_frontmatter:]

                    # Sort only the front matter and ensure proper spacing
                    # Construct the full frontmatter block with markers for the sorting function
                    full_frontmatter_block = f"---\n{front_matter}\n---"
                    sorted_front_matter = sort_frontmatter_properties(full_frontmatter_block)
                    updated_content = sorted_front_matter + '\n' + rest_of_content
                except ValueError as e:
                    print(
                        f"Varning: Kunde inte sortera front matter efter att ha tagit bort {property_name}: {e}")

    except Exception as e:
        print(f"Varning: Kunde inte ta bort {property_name} från frontmatter: {e}")

    return updated_content


def extract_frontmatter_property(content: str, property_name: str) -> Optional[str]:
    """
    Extract a property from YAML frontmatter in markdown content.

    Args:
        content: The full markdown content with frontmatter
        property_name: The property name to extract from frontmatter

    Returns:
        The property value from frontmatter, or None if not found
    """
    # Check if content starts with YAML frontmatter
    if not content.startswith('---\n'):
        return None

    # Find the end of frontmatter
    end_marker = content.find('\n---\n', 4)
    if end_marker == -1:
        return None

    # Extract frontmatter
    frontmatter_text = content[4:end_marker]

    try:
        frontmatter = yaml.safe_load(frontmatter_text)
        if isinstance(frontmatter, dict):
            return frontmatter.get(property_name)
    except yaml.YAMLError:
        pass

    return None
