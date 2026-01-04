#!/usr/bin/env python3
"""
Tests for YAML utility functions.
"""

import pytest
from util.yaml_utils import format_yaml_value


# ===========================================================================
# format_yaml_value Tests
# ===========================================================================

@pytest.mark.unit
class TestFormatYamlValue:
    """Test the format_yaml_value function."""

    def test_none_value(self):
        """Test that None is formatted as 'null'."""
        result = format_yaml_value(None)
        assert result == 'null'

    def test_boolean_true(self):
        """Test that True is formatted as 'true'."""
        result = format_yaml_value(True)
        assert result == 'true'

    def test_boolean_false(self):
        """Test that False is formatted as 'false'."""
        result = format_yaml_value(False)
        assert result == 'false'

    def test_integer(self):
        """Test that integers are formatted as strings."""
        result = format_yaml_value(2024)
        assert result == '2024'

    def test_float(self):
        """Test that floats are formatted as strings."""
        result = format_yaml_value(3.14)
        assert result == '3.14'

    def test_simple_string(self):
        """Test that simple strings don't get quotes."""
        result = format_yaml_value("simple text")
        assert result == "simple text"
        assert '"' not in result

    def test_empty_string(self):
        """Test that empty strings get quotes."""
        result = format_yaml_value("")
        assert result == '""'

    def test_url_no_quotes(self):
        """Test that URLs don't get quoted."""
        url = "https://example.com/path"
        result = format_yaml_value(url)
        assert result == url
        assert '"' not in result

    def test_http_url(self):
        """Test that http URLs don't get quoted."""
        url = "http://example.com"
        result = format_yaml_value(url)
        assert result == url

    def test_string_with_colon_needs_quotes(self):
        """Test that strings with colons get quoted (e.g., SFS beteckning)."""
        result = format_yaml_value("2024:1")
        assert result == '"2024:1"'

    def test_sfs_beteckning(self):
        """Test SFS beteckning formatting (contains colon)."""
        result = format_yaml_value("2024:925")
        assert result == '"2024:925"'
        assert result.startswith('"')
        assert result.endswith('"')

    def test_string_with_hash_needs_quotes(self):
        """Test that strings with # get quoted."""
        result = format_yaml_value("text with # comment")
        assert result == '"text with # comment"'

    def test_string_with_brackets(self):
        """Test that strings with brackets get quoted."""
        result = format_yaml_value("text with [brackets]")
        assert result == '"text with [brackets]"'

    def test_string_with_braces(self):
        """Test that strings with braces get quoted."""
        result = format_yaml_value("text with {braces}")
        assert result == '"text with {braces}"'

    def test_yaml_keyword_true(self):
        """Test that YAML keyword 'true' gets quoted."""
        result = format_yaml_value("true")
        assert result == '"true"'

    def test_yaml_keyword_false(self):
        """Test that YAML keyword 'false' gets quoted."""
        result = format_yaml_value("false")
        assert result == '"false"'

    def test_yaml_keyword_null(self):
        """Test that YAML keyword 'null' gets quoted."""
        result = format_yaml_value("null")
        assert result == '"null"'

    def test_yaml_keyword_yes(self):
        """Test that YAML keyword 'yes' gets quoted."""
        result = format_yaml_value("yes")
        assert result == '"yes"'

    def test_yaml_keyword_no(self):
        """Test that YAML keyword 'no' gets quoted."""
        result = format_yaml_value("no")
        assert result == '"no"'

    def test_string_that_looks_like_number(self):
        """Test that strings that look like numbers get quoted."""
        result = format_yaml_value("123")
        assert result == '"123"'

    def test_string_with_leading_whitespace(self):
        """Test that strings with leading whitespace get quoted."""
        result = format_yaml_value("  text")
        assert result == '"  text"'

    def test_string_with_trailing_whitespace(self):
        """Test that strings with trailing whitespace get quoted."""
        result = format_yaml_value("text  ")
        assert result == '"text  "'

    def test_string_with_newline(self):
        """Test that strings with newlines get quoted."""
        result = format_yaml_value("line1\nline2")
        assert result.startswith('"')
        assert result.endswith('"')

    def test_swedish_characters(self):
        """Test that Swedish characters are preserved."""
        result = format_yaml_value("åäö ÅÄÖ")
        assert "åäö ÅÄÖ" in result

    def test_swedish_text_simple(self):
        """Test simple Swedish text without special chars."""
        result = format_yaml_value("Förordning om ändringar")
        assert result == "Förordning om ändringar"
        assert '"' not in result

    def test_string_with_quotes_needs_escaping(self):
        """Test that strings with quotes get properly escaped."""
        result = format_yaml_value('text with "quotes"')
        assert result == '"text with \\"quotes\\""'

    def test_string_starting_with_special_char(self):
        """Test strings starting with special YAML characters."""
        special_chars = ['!', '&', '*', '|', '>', '@', '`', '#', '%']
        for char in special_chars:
            result = format_yaml_value(f"{char}text")
            assert result.startswith('"'), f"String starting with {char} should be quoted"

    def test_string_with_dashes(self):
        """Test string starting with dash and space (YAML list marker)."""
        result = format_yaml_value("- item")
        assert result == '"- item"'

    def test_scientific_notation_string(self):
        """Test strings that look like scientific notation get quoted."""
        result = format_yaml_value("1.5e10")
        assert result == '"1.5e10"'


# ===========================================================================
# Parametrized Tests
# ===========================================================================

@pytest.mark.unit
class TestFormatYamlValueParametrized:
    """Parametrized tests for format_yaml_value."""

    @pytest.mark.parametrize("value,expected", [
        # Simple types
        (None, "null"),
        (True, "true"),
        (False, "false"),
        (42, "42"),
        (3.14, "3.14"),

        # Empty and whitespace
        ("", '""'),
        ("  ", '"  "'),

        # URLs (should not be quoted)
        ("https://example.com", "https://example.com"),
        ("http://data.riksdagen.se", "http://data.riksdagen.se"),

        # SFS beteckningar (need quotes due to colon)
        ("2024:1", '"2024:1"'),
        ("1998:204", '"1998:204"'),

        # YAML keywords (need quotes)
        ("true", '"true"'),
        ("false", '"false"'),
        ("null", '"null"'),
        ("yes", '"yes"'),
        ("no", '"no"'),
        ("on", '"on"'),
        ("off", '"off"'),

        # Numbers as strings (need quotes)
        ("123", '"123"'),
        ("45.67", '"45.67"'),
        ("-100", '"-100"'),

        # Simple strings (no quotes needed)
        ("hello world", "hello world"),
        ("test", "test"),
        ("Förordning", "Förordning"),
    ])
    def test_various_values(self, value, expected):
        """Test various value types and formats."""
        result = format_yaml_value(value)
        assert result == expected


# ===========================================================================
# Edge Cases
# ===========================================================================

@pytest.mark.unit
class TestFormatYamlValueEdgeCases:
    """Test edge cases for format_yaml_value."""

    def test_long_string(self):
        """Test formatting of long strings."""
        long_text = "Detta är en mycket lång text " * 10
        result = format_yaml_value(long_text)
        assert long_text in result

    def test_multiline_text(self):
        """Test multiline text gets quoted."""
        text = """Line 1
Line 2
Line 3"""
        result = format_yaml_value(text)
        assert result.startswith('"')
        assert '\\n' in result or '\n' in result

    def test_mixed_content(self):
        """Test string with mixed special characters."""
        text = "Text with: colon, [brackets], and #hash"
        result = format_yaml_value(text)
        assert result.startswith('"')
        assert result.endswith('"')

    def test_backslash_in_simple_string(self):
        """Test that backslashes in simple strings are preserved."""
        text = r'text with \ backslash'
        result = format_yaml_value(text)
        # Simple string without special YAML chars doesn't need quotes
        # so backslash is NOT escaped
        assert result == text

    def test_yaml_document_markers(self):
        """Test strings that look like YAML document markers."""
        markers = ['---', '...', '<<']
        for marker in markers:
            result = format_yaml_value(marker)
            assert result.startswith('"'), f"{marker} should be quoted"

    def test_string_with_pipe(self):
        """Test string with pipe character (YAML multiline indicator)."""
        result = format_yaml_value("text | with pipe")
        assert result == '"text | with pipe"'

    def test_complex_sfs_title(self):
        """Test complex SFS title with various characters."""
        title = "Förordning (2024:1) om ändring i förvaltningslagen (2017:900)"
        result = format_yaml_value(title)
        # Contains parentheses with colons, should be quoted
        assert result.startswith('"')
        assert "Förordning" in result
