"""
YAML utilities for formatting values according to YAML standards.
"""

import re
from typing import Any


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
        # Contains special characters that could be interpreted as YAML syntax
        any(char in value for char in ['[', ']', '{', '}', ',', '#', '`', '"', "'", '|', '>', '*', '&', '!', '%', '@']) or
        # Contains colon (YAML key-value separator or time format) - always quote SFS beteckning
        ':' in value or
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
