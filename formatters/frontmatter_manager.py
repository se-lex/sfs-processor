"""
Frontmatter management utilities for SFS documents.

This module contains functions for manipulating YAML frontmatter in markdown documents.
"""

from util.yaml_utils import format_yaml_value
from formatters.sort_frontmatter import sort_frontmatter_properties
import re
import yaml
from typing import Optional


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
                # The front_matter already includes the full block with markers, so use it directly
                sorted_front_matter = sort_frontmatter_properties(front_matter + '\n')
                updated_content = sorted_front_matter + '\n' + rest_of_content
    except ValueError as e:
        error_context = f" för {beteckning}" if beteckning else ""
        print(f"Varning: Kunde inte sortera front matter efter att ha lagt till ikraft_datum{error_context}: {e}")

    return updated_content


def set_prop_in_frontmatter(markdown_content: str, property_name: str, new_value: str, beteckning: str = "") -> str:
    """
    Set a property in the YAML front matter and sort it.
    
    Args:
        markdown_content: The markdown content with YAML front matter
        property_name: The name of the property to set
        new_value: The new value to set
        beteckning: Document identifier for error messages (optional)
    
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
                while end_of_frontmatter < len(updated_content) and updated_content[end_of_frontmatter] == '\n':
                    end_of_frontmatter += 1
                rest_of_content = updated_content[end_of_frontmatter:]
                
                # Sort only the front matter and ensure proper spacing
                # Construct the full frontmatter block with markers for the sorting function
                full_frontmatter_block = f"---\n{front_matter}\n---"
                sorted_front_matter = sort_frontmatter_properties(full_frontmatter_block)
                updated_content = sorted_front_matter + '\n' + rest_of_content
            except ValueError as e:
                error_context = f" för {beteckning}" if beteckning else ""
                print(f"Varning: Kunde inte sortera front matter efter att ha uppdaterat {property_name}{error_context}: {e}")
    
    except Exception as e:
        error_context = f" för {beteckning}" if beteckning else ""
        print(f"Varning: Kunde inte uppdatera {property_name} i frontmatter{error_context}: {e}")
    
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
