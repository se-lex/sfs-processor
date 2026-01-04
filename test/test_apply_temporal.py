#!/usr/bin/env python3
"""
Tests for temporal filtering functionality.
"""

import pytest
from temporal.apply_temporal import apply_temporal


# ===========================================================================
# apply_temporal Tests - Basic Functionality
# ===========================================================================

@pytest.mark.unit
class TestApplyTemporalBasic:
    """Test basic temporal filtering functionality."""

    def test_valid_date_format(self):
        """Test that valid date format is accepted."""
        text = """<section>

## 1 kap.

Content

</section>"""

        # Should not raise exception with valid date
        result = apply_temporal(text, "2024-06-01")
        assert result  # Non-empty result

    def test_invalid_date_format_raises_error(self):
        """Test that invalid date format raises ValueError."""
        text = """<section>

## 1 kap.

</section>"""

        with pytest.raises(ValueError) as exc_info:
            apply_temporal(text, "invalid-date")

        assert "YYYY-MM-DD" in str(exc_info.value)

    def test_preserve_content_without_temporal_markers(self):
        """Test that content without temporal markers is preserved."""
        text = """<section>

## 1 kap. Inledande bestämmelser

### 1 §

This is regular content.

</section>"""

        result = apply_temporal(text, "2024-06-01")

        assert "## 1 kap." in result
        assert "### 1 §" in result
        assert "This is regular content." in result


# ===========================================================================
# Status-based Filtering Tests
# ===========================================================================

@pytest.mark.unit
class TestApplyTemporalStatus:
    """Test temporal filtering based on status attribute."""

    def test_remove_upphavd_section(self):
        """Test that sections with status='upphavd' are removed."""
        text = """<section selex:status="upphavd">

## 2 §

This section has been repealed.

</section>

<section>

## 3 §

This section is still valid.

</section>"""

        result = apply_temporal(text, "2024-06-01")

        assert "## 2 §" not in result
        assert "This section has been repealed." not in result
        assert "## 3 §" in result
        assert "This section is still valid." in result

    def test_remove_upphord_section(self):
        """Test that sections with status='upphord' are removed."""
        text = """<section selex:status="upphord">

## Expired section

Content

</section>"""

        result = apply_temporal(text, "2024-06-01")

        assert "## Expired section" not in result
        assert "Content" not in result or "## Expired section" not in result


# ===========================================================================
# Date-based Filtering Tests
# ===========================================================================

@pytest.mark.unit
class TestApplyTemporalDates:
    """Test temporal filtering based on dates."""

    def test_remove_section_with_upphor_datum_before_target(self):
        """Test removing section that expired before target date."""
        text = """<section selex:upphor_datum="2023-12-31">

## Expired section

Content that expired.

</section>

<section>

## Valid section

Still valid content.

</section>"""

        result = apply_temporal(text, "2024-06-01")

        assert "## Expired section" not in result
        assert "Content that expired." not in result
        assert "## Valid section" in result

    def test_remove_section_with_ikraft_datum_after_target(self):
        """Test removing section not yet in force."""
        text = """<section selex:ikraft_datum="2025-01-01">

## Future section

Not yet in force.

</section>

<section>

## Current section

Already in force.

</section>"""

        result = apply_temporal(text, "2024-06-01")

        assert "## Future section" not in result
        assert "Not yet in force." not in result
        assert "## Current section" in result

    def test_keep_section_with_ikraft_datum_before_target(self):
        """Test keeping section that is already in force."""
        text = """<section selex:ikraft_datum="2024-01-01">

## Section in force

This is active.

</section>"""

        result = apply_temporal(text, "2024-06-01")

        # Section should be kept but temporal attributes cleaned
        assert "## Section in force" in result
        assert "This is active." in result

    def test_boundary_upphor_datum_on_target_date(self):
        """Test upphor_datum exactly on target date (should be removed)."""
        text = """<section selex:upphor_datum="2024-06-01">

## Expires today

Content

</section>"""

        result = apply_temporal(text, "2024-06-01")

        # Section expires on target date, should be removed (<= comparison)
        assert "## Expires today" not in result

    def test_boundary_ikraft_datum_on_target_date(self):
        """Test ikraft_datum exactly on target date (should be kept)."""
        text = """<section selex:ikraft_datum="2024-06-01">

## Effective today

Content

</section>"""

        result = apply_temporal(text, "2024-06-01")

        # Section becomes effective on target date, should be kept
        assert "## Effective today" in result


# ===========================================================================
# Temporal Attribute Cleaning Tests
# ===========================================================================

@pytest.mark.unit
class TestApplyTemporalAttributeCleaning:
    """Test cleaning of temporal attributes."""

    def test_clean_ikraft_attributes_when_in_force(self):
        """Test that ikraft attributes are removed when section is in force."""
        text = """<section selex:status="ikraft" selex:ikraft_datum="2024-01-01">

## Section

Content

</section>"""

        result = apply_temporal(text, "2024-06-01")

        # Section should be kept but status and ikraft_datum removed
        assert "## Section" in result
        assert "Content" in result
        assert "selex:status" not in result
        assert "selex:ikraft_datum" not in result

    def test_preserve_non_temporal_attributes(self):
        """Test that non-temporal attributes are preserved."""
        text = """<section selex:id="1-kap" selex:ikraft_datum="2024-01-01">

## 1 kap.

Content

</section>"""

        result = apply_temporal(text, "2024-06-01")

        # selex:id should be preserved, ikraft_datum removed
        assert "selex:id" in result
        assert "selex:ikraft_datum" not in result


# ===========================================================================
# Nested Section Tests
# ===========================================================================

@pytest.mark.integration
class TestApplyTemporalNested:
    """Test handling of nested sections."""

    def test_remove_outer_section_removes_nested(self):
        """Test that removing outer section also removes nested sections."""
        text = """<section selex:status="upphavd">

## Outer (repealed)

<section>

### Inner

Nested content

</section>

</section>"""

        result = apply_temporal(text, "2024-06-01")

        # Both outer and inner should be removed
        assert "## Outer" not in result
        assert "### Inner" not in result
        assert "Nested content" not in result

    def test_keep_outer_remove_inner(self):
        """Test keeping outer section but removing inner."""
        text = """<section>

## Outer (valid)

Outer content

<section selex:status="upphavd">

### Inner (repealed)

Inner content

</section>

More outer content

</section>"""

        result = apply_temporal(text, "2024-06-01")

        assert "## Outer (valid)" in result
        assert "Outer content" in result
        assert "More outer content" in result
        assert "### Inner (repealed)" not in result
        assert "Inner content" not in result


# ===========================================================================
# H1 Heading Processing Tests
# ===========================================================================

@pytest.mark.unit
class TestApplyTemporalH1Processing:
    """Test H1 heading processing with temporal rules."""

    def test_process_h1_with_temporal_rules(self):
        """Test that H1 headings are processed by title_temporal."""
        # H1 heading may have temporal markers that need processing
        text = """# Förordning om test

<section>

## 1 kap.

Content

</section>"""

        result = apply_temporal(text, "2024-06-01")

        # H1 should be processed (exact behavior depends on title_temporal)
        assert "# Förordning" in result or "#" in result

    def test_preserve_h1_without_temporal_markers(self):
        """Test that regular H1 is preserved."""
        text = """# Simple Title

<section>

## Content

</section>"""

        result = apply_temporal(text, "2024-06-01")

        assert "# Simple Title" in result


# ===========================================================================
# Integration Tests
# ===========================================================================

@pytest.mark.integration
class TestApplyTemporalIntegration:
    """Integration tests for temporal filtering."""

    def test_complex_document_filtering(self):
        """Test filtering a complex document with mixed temporal rules."""
        text = """<article>

# Förordning (2024:1)

<section>

## 1 kap. Valid chapter

### 1 §

Active paragraph.

</section>

<section selex:status="upphavd">

## 2 kap. Repealed chapter

### 2 §

Repealed content.

</section>

<section selex:ikraft_datum="2025-01-01">

## 3 kap. Future chapter

### 3 §

Not yet in force.

</section>

<section selex:ikraft_datum="2024-01-01">

## 4 kap. Recently effective

### 4 §

Now in force.

</section>

</article>"""

        result = apply_temporal(text, "2024-06-01")

        # Chapter 1 should be present
        assert "## 1 kap." in result
        assert "Active paragraph." in result

        # Chapter 2 should be removed (upphavd)
        assert "## 2 kap." not in result
        assert "Repealed content." not in result

        # Chapter 3 should be removed (future)
        assert "## 3 kap." not in result
        assert "Not yet in force." not in result

        # Chapter 4 should be present (now in force)
        assert "## 4 kap." in result
        assert "Now in force." in result

    def test_preserve_swedish_characters(self):
        """Test that Swedish characters are preserved during filtering."""
        text = """<section>

## Övergångsbestämmelser

Förordningen träder i kraft den 1 juli 2024.

</section>"""

        result = apply_temporal(text, "2024-06-01")

        assert "Övergångsbestämmelser" in result
        assert "Förordningen" in result
        assert "träder" in result

    def test_empty_document(self):
        """Test handling empty document."""
        text = ""

        result = apply_temporal(text, "2024-06-01")

        assert result == "" or not result.strip()

    def test_document_without_sections(self):
        """Test handling document without section tags."""
        text = """# Just a title

Some content without section tags."""

        result = apply_temporal(text, "2024-06-01")

        assert "# Just a title" in result
        assert "Some content without section tags." in result


# ===========================================================================
# Edge Cases
# ===========================================================================

@pytest.mark.unit
class TestApplyTemporalEdgeCases:
    """Test edge cases for temporal filtering."""

    def test_multiple_status_values(self):
        """Test section with multiple status values."""
        text = """<section selex:status="upphavd ikraft">

## Mixed status

Content

</section>"""

        result = apply_temporal(text, "2024-06-01")

        # Should be removed due to "upphavd" in status
        assert "## Mixed status" not in result

    def test_very_old_date(self):
        """Test filtering with very old dates."""
        text = """<section selex:upphor_datum="1900-01-01">

## Very old section

Content

</section>"""

        result = apply_temporal(text, "2024-06-01")

        # Should be removed (expired long ago)
        assert "## Very old section" not in result

    def test_far_future_date(self):
        """Test filtering with far future dates."""
        text = """<section selex:ikraft_datum="2100-01-01">

## Far future section

Content

</section>"""

        result = apply_temporal(text, "2024-06-01")

        # Should be removed (not yet in force)
        assert "## Far future section" not in result
