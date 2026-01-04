#!/usr/bin/env python3
"""
Tests for frontmatter management utilities.
"""

import pytest
from formatters.frontmatter_manager import (
    set_prop_in_frontmatter,
    add_ikraft_datum_to_frontmatter,
    remove_prop_from_frontmatter,
    extract_frontmatter_property
)


# ===========================================================================
# set_prop_in_frontmatter Tests
# ===========================================================================

@pytest.mark.unit
class TestSetPropInFrontmatter:
    """Test the set_prop_in_frontmatter function."""

    def test_set_new_property(self):
        """Test setting a new property in frontmatter."""
        content = """---
rubrik: Test förordning
beteckning: "2024:1"
---

# Test förordning

Content here"""

        result = set_prop_in_frontmatter(content, "ny_prop", "värde")

        assert "ny_prop:" in result
        assert "värde" in result
        assert "Content here" in result  # Body preserved
        assert "# Test förordning" in result

    def test_update_existing_property(self):
        """Test updating an existing property in frontmatter."""
        content = """---
rubrik: Old title
beteckning: "2024:1"
---

Content"""

        result = set_prop_in_frontmatter(content, "rubrik", "New title")

        assert "rubrik: New title" in result or "rubrik: \"New title\"" in result
        assert "Old title" not in result

    def test_preserve_other_properties(self):
        """Test that other properties are preserved when updating."""
        content = """---
rubrik: Test
beteckning: "2024:1"
ikraft_datum: "2024-01-01"
---

Content"""

        result = set_prop_in_frontmatter(content, "rubrik", "New title")

        assert "beteckning" in result
        assert "2024:1" in result
        assert "ikraft_datum" in result

    def test_preserve_document_body(self):
        """Test that document body with multiple paragraphs is preserved."""
        content = """---
rubrik: Test
---

# First section

Some content here.

## Second section

More content."""

        result = set_prop_in_frontmatter(content, "ny_prop", "value")

        assert "# First section" in result
        assert "## Second section" in result
        assert "Some content here." in result
        assert "More content." in result

    def test_handle_swedish_characters(self):
        """Test handling of Swedish characters in property values."""
        content = """---
rubrik: Test
---

Content"""

        result = set_prop_in_frontmatter(content, "beskrivning", "Förordning om ändringar")

        assert "beskrivning:" in result
        assert "Förordning om ändringar" in result

    def test_handle_sfs_beteckning(self):
        """Test handling of SFS beteckning format (with colon)."""
        content = """---
rubrik: Test
---

Content"""

        result = set_prop_in_frontmatter(content, "beteckning", "2024:925")

        assert "beteckning:" in result
        # Should be quoted because it contains colon
        assert '"2024:925"' in result

    def test_update_property_with_special_chars(self):
        """Test updating property with special YAML characters."""
        content = """---
rubrik: Test
special: "old:value"
---

Content"""

        result = set_prop_in_frontmatter(content, "special", "new:value")

        assert "old:value" not in result
        assert "new:value" in result

    def test_handle_empty_property_value(self):
        """Test setting property to empty string."""
        content = """---
rubrik: Test
---

Content"""

        result = set_prop_in_frontmatter(content, "empty_prop", "")

        assert "empty_prop:" in result

    def test_no_frontmatter_returns_unchanged(self):
        """Test that content without frontmatter is returned unchanged."""
        content = "# Just a heading\n\nNo frontmatter here"

        result = set_prop_in_frontmatter(content, "prop", "value")

        # Should return original content since no frontmatter exists
        assert result == content or "---" in result  # Either unchanged or frontmatter added


# ===========================================================================
# add_ikraft_datum_to_frontmatter Tests
# ===========================================================================

@pytest.mark.unit
class TestAddIkraftDatumToFrontmatter:
    """Test the add_ikraft_datum_to_frontmatter function."""

    def test_add_ikraft_datum(self):
        """Test adding ikraft_datum to frontmatter."""
        content = """---
rubrik: Test
beteckning: "2024:1"
---

Content"""

        result = add_ikraft_datum_to_frontmatter(content, "2024-06-01")

        assert "ikraft_datum:" in result
        assert "2024-06-01" in result

    def test_update_existing_ikraft_datum(self):
        """Test updating existing ikraft_datum."""
        content = """---
rubrik: Test
ikraft_datum: "2024-01-01"
---

Content"""

        result = add_ikraft_datum_to_frontmatter(content, "2024-06-01")

        assert "2024-06-01" in result
        # Old date should be replaced (but might still appear in sorting order check)
        assert result.count("ikraft_datum:") == 1


# ===========================================================================
# remove_prop_from_frontmatter Tests
# ===========================================================================

@pytest.mark.unit
class TestRemovePropFromFrontmatter:
    """Test the remove_prop_from_frontmatter function."""

    def test_remove_simple_property(self):
        """Test removing a simple property from frontmatter."""
        content = """---
rubrik: Test
beteckning: "2024:1"
to_remove: value
---

Content"""

        result = remove_prop_from_frontmatter(content, "to_remove")

        assert "to_remove" not in result
        assert "rubrik: Test" in result
        assert "beteckning" in result
        assert "Content" in result

    def test_remove_nonexistent_property(self):
        """Test removing a property that doesn't exist."""
        content = """---
rubrik: Test
beteckning: "2024:1"
---

Content"""

        result = remove_prop_from_frontmatter(content, "nonexistent")

        # Should return content unchanged (or minimally changed by sorting)
        assert "rubrik" in result
        assert "beteckning" in result

    def test_remove_multiline_property(self):
        """Test removing a multi-line property (like a list)."""
        content = """---
rubrik: Test
list_property:
  - item1
  - item2
  - item3
beteckning: "2024:1"
---

Content"""

        result = remove_prop_from_frontmatter(content, "list_property")

        assert "list_property" not in result
        assert "item1" not in result
        assert "item2" not in result
        assert "item3" not in result
        assert "rubrik" in result
        assert "beteckning" in result

    def test_preserve_other_properties_after_removal(self):
        """Test that other properties are preserved after removal."""
        content = """---
rubrik: Test
prop_to_remove: value
beteckning: "2024:1"
ikraft_datum: "2024-01-01"
---

Content"""

        result = remove_prop_from_frontmatter(content, "prop_to_remove")

        assert "prop_to_remove" not in result
        assert "rubrik" in result
        assert "beteckning" in result
        assert "ikraft_datum" in result

    def test_preserve_body_after_removal(self):
        """Test that document body is preserved after property removal."""
        content = """---
rubrik: Test
to_remove: value
---

# Section 1

Content here

## Section 2

More content"""

        result = remove_prop_from_frontmatter(content, "to_remove")

        assert "# Section 1" in result
        assert "## Section 2" in result
        assert "Content here" in result
        assert "More content" in result


# ===========================================================================
# extract_frontmatter_property Tests
# ===========================================================================

@pytest.mark.unit
class TestExtractFrontmatterProperty:
    """Test the extract_frontmatter_property function."""

    def test_extract_existing_string_property(self):
        """Test extracting an existing string property."""
        content = """---
rubrik: Test förordning
beteckning: "2024:1"
---

Content"""

        result = extract_frontmatter_property(content, "rubrik")

        assert result == "Test förordning"

    def test_extract_existing_quoted_property(self):
        """Test extracting a quoted property value."""
        content = """---
rubrik: Test
beteckning: "2024:1"
---

Content"""

        result = extract_frontmatter_property(content, "beteckning")

        assert result == "2024:1"

    def test_extract_nonexistent_property(self):
        """Test extracting a property that doesn't exist."""
        content = """---
rubrik: Test
---

Content"""

        result = extract_frontmatter_property(content, "nonexistent")

        assert result is None

    def test_extract_from_content_without_frontmatter(self):
        """Test extracting from content without frontmatter."""
        content = "# Just a heading\n\nNo frontmatter"

        result = extract_frontmatter_property(content, "rubrik")

        assert result is None

    def test_extract_from_invalid_frontmatter(self):
        """Test extracting from content with invalid YAML frontmatter."""
        content = """---
broken: yaml: structure: invalid
---

Content"""

        result = extract_frontmatter_property(content, "broken")

        # Should return None due to YAML parse error
        assert result is None

    def test_extract_list_property(self):
        """Test extracting a list property."""
        content = """---
rubrik: Test
items:
  - item1
  - item2
  - item3
---

Content"""

        result = extract_frontmatter_property(content, "items")

        assert isinstance(result, list)
        assert len(result) == 3
        assert "item1" in result

    def test_extract_with_swedish_characters(self):
        """Test extracting property with Swedish characters."""
        content = """---
rubrik: Förordning om ändringar
---

Content"""

        result = extract_frontmatter_property(content, "rubrik")

        assert result == "Förordning om ändringar"
        assert "Förordning" in result

    def test_extract_date_property(self):
        """Test extracting a date property."""
        content = """---
rubrik: Test
ikraft_datum: "2024-06-01"
---

Content"""

        result = extract_frontmatter_property(content, "ikraft_datum")

        assert result == "2024-06-01"


# ===========================================================================
# Integration Tests
# ===========================================================================

@pytest.mark.integration
class TestFrontmatterIntegration:
    """Integration tests for frontmatter management."""

    def test_set_and_extract_property(self):
        """Test setting a property and then extracting it."""
        content = """---
rubrik: Test
---

Content"""

        # Set property
        updated = set_prop_in_frontmatter(content, "beteckning", "2024:925")

        # Extract it back
        extracted = extract_frontmatter_property(updated, "beteckning")

        assert extracted == "2024:925"

    def test_multiple_property_updates(self):
        """Test multiple property updates in sequence."""
        content = """---
rubrik: Original
---

Content"""

        # Update multiple times
        result = set_prop_in_frontmatter(content, "rubrik", "First update")
        result = set_prop_in_frontmatter(result, "beteckning", "2024:1")
        result = set_prop_in_frontmatter(result, "ikraft_datum", "2024-01-01")

        # Verify all properties
        assert extract_frontmatter_property(result, "rubrik") == "First update"
        assert extract_frontmatter_property(result, "beteckning") == "2024:1"
        # YAML parser returns datetime.date object for dates
        ikraft = extract_frontmatter_property(result, "ikraft_datum")
        assert str(ikraft) == "2024-01-01" or ikraft == "2024-01-01"

    def test_set_remove_and_verify(self):
        """Test setting, removing, and verifying a property."""
        content = """---
rubrik: Test
---

Content"""

        # Add property
        with_prop = set_prop_in_frontmatter(content, "temp_prop", "value")
        assert extract_frontmatter_property(with_prop, "temp_prop") == "value"

        # Remove property
        without_prop = remove_prop_from_frontmatter(with_prop, "temp_prop")
        assert extract_frontmatter_property(without_prop, "temp_prop") is None

        # Original property should still exist
        assert extract_frontmatter_property(without_prop, "rubrik") == "Test"

    def test_complex_document_manipulation(self):
        """Test complex document with multiple operations."""
        content = """---
rubrik: Original title
beteckning: "2024:1"
---

# Förordning om test

## 1 kap. Inledande bestämmelser

### 1 §

This is the content.

### 2 §

More content here."""

        # Perform multiple operations
        result = set_prop_in_frontmatter(content, "rubrik", "Updated title")
        result = add_ikraft_datum_to_frontmatter(result, "2024-06-01")
        result = set_prop_in_frontmatter(result, "status", "active")

        # Verify frontmatter
        assert extract_frontmatter_property(result, "rubrik") == "Updated title"
        # YAML parser returns datetime.date object for dates
        ikraft = extract_frontmatter_property(result, "ikraft_datum")
        assert str(ikraft) == "2024-06-01" or ikraft == "2024-06-01"
        assert extract_frontmatter_property(result, "status") == "active"
        assert extract_frontmatter_property(result, "beteckning") == "2024:1"

        # Verify body is intact
        assert "# Förordning om test" in result
        assert "## 1 kap." in result
        assert "### 1 §" in result
        assert "### 2 §" in result
        assert "This is the content." in result
        assert "More content here." in result
