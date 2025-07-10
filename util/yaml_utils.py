"""
YAML utilities for formatting values according to YAML standards.
"""

import re
import yaml
from typing import Any, Optional


def format_yaml_value(value: Any) -> str:
    """Format a value for YAML output, only adding quotes when necessary according to YAML rules."""
    if value is None:
        return 'null'

    if isinstance(value, bool):
        return 'true' if value else 'false'

    if isinstance(value, (int, float)):
        return str(value)

    # Convert to string if not already
    if not isinstance(value, str):
        value = str(value)

    # Empty string needs quotes
    if not value:
        return '""'

    # Check if value is a URL - URLs should not be quoted
    if re.match(r'^https?://', value):
        return value

    # Check if value needs quotes according to YAML rules
    needs_quotes = (
        # Starts with special YAML characters
        value[0] in '!&*|>@`#%{}[]' or
        # Contains special characters that could be interpreted as YAML syntax (but not simple dates)
        (any(char in value for char in ['[', ']', '{', '}', ',', '#', '`', '"', "'", '|', '>', '*', '&', '!', '%', '@']) or
         (':' in value and not re.match(r'^\d{4}:\d+$', value))) or  # Allow YYYY:NNN format and dates
        # Looks like a number, boolean, or null
        value.lower() in ['true', 'false', 'null', 'yes', 'no', 'on', 'off'] or
        re.match(r'^-?\d+\.?\d*$', value) or  # Numbers
        re.match(r'^-?\d+\.?\d*e[+-]?\d+$', value.lower()) or  # Scientific notation
        # Starts or ends with whitespace
        value != value.strip() or
        # Contains newlines
        '\n' in value or '\r' in value or
        # Starts with special sequences
        value.startswith(('<<', '---', '...', '- '))
    )

    if needs_quotes:
        # Use double quotes and escape any double quotes inside
        escaped_value = value.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{escaped_value}"'

    return value


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
