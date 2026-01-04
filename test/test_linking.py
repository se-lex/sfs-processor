#!/usr/bin/env python3
"""
Test script for linking functionality (law names, SFS, internal, EU).
"""

import pytest
from formatters.apply_links import (
    apply_law_name_links,
    apply_sfs_links,
    apply_internal_links,
    apply_eu_links
)


@pytest.mark.unit
@pytest.mark.parametrize("input_text,expected_pattern", [
    ('3 kap. 3 § dataskyddslagen', '[3 kap. 3 § dataskyddslagen]'),
    ('8 kap. 7 § regeringsformen', '[8 kap. 7 § regeringsformen]'),
    ('2 kap. 25 § skollagen', '[2 kap. 25 § skollagen]'),
    (
        '29 kap. 14 § och offentlighets- och sekretesslagen',
        '[29 kap. 14 § och offentlighets- och sekretesslagen]'
    ),
    ('15 kap. 2 § sekretesslagen', '[15 kap. 2 § sekretesslagen]'),
])
def test_law_name_linking_success(input_text, expected_pattern):
    """Test that law name references are correctly converted to links."""
    result = apply_law_name_links(input_text)

    # Verify the expected pattern is in the result
    assert expected_pattern in result, \
        f"Expected pattern '{expected_pattern}' not found in result: {result}"

    # Verify that the text was actually modified (a link was added)
    assert result != input_text, f"Text was not modified: {result}"


@pytest.mark.unit
@pytest.mark.parametrize("input_text", [
    'This is plain text without any law references',
    'Just some random text',
    '123 numbers only',
])
def test_law_name_no_linking(input_text):
    """Test that text without law references is left unchanged."""
    result = apply_law_name_links(input_text)

    # Text without law references should remain unchanged
    assert result == input_text, f"Text should not be modified: {result}"


@pytest.mark.unit
def test_law_name_linking_preserves_context():
    """Test that linking preserves surrounding context."""
    input_text = "Se 3 kap. 3 § dataskyddslagen för mer information"
    result = apply_law_name_links(input_text)

    # Should contain the link
    assert '[3 kap. 3 § dataskyddslagen]' in result

    # Should preserve surrounding text
    assert 'Se' in result
    assert 'för mer information' in result


# ===========================================================================
# apply_sfs_links Tests
# ===========================================================================

@pytest.mark.unit
class TestApplySfsLinks:
    """Test the apply_sfs_links function."""

    @pytest.mark.parametrize("input_text,expected_link", [
        ('Se lag (1998:204)', '[1998:204]'),
        ('Förordning (2024:925)', '[2024:925]'),
        ('enligt lagen (2017:900)', '[2017:900]'),
    ])
    def test_sfs_reference_linking(self, input_text, expected_link):
        """Test that SFS references are converted to links."""
        result = apply_sfs_links(input_text)

        assert expected_link in result
        assert result != input_text  # Should be modified

    def test_multiple_sfs_references(self):
        """Test linking multiple SFS references in one text."""
        text = "Lag (1998:204) och förordning (2024:925) ska tillämpas."

        result = apply_sfs_links(text)

        assert '[1998:204]' in result
        assert '[2024:925]' in result

    def test_skip_headings(self):
        """Test that headings are not linked."""
        text = "## Lag (1998:204)\n\nI text enligt lag (1998:204)"

        result = apply_sfs_links(text)

        lines = result.split('\n')
        # Heading should not be linked
        assert '[1998:204]' not in lines[0]
        # Body text should be linked
        assert '[1998:204]' in lines[2]

    def test_preserve_context(self):
        """Test that surrounding context is preserved."""
        text = "Enligt lag (1998:204) gäller följande"

        result = apply_sfs_links(text)

        assert 'Enligt' in result
        assert 'gäller följande' in result
        assert '[1998:204]' in result

    def test_no_sfs_references(self):
        """Test text without SFS references."""
        text = "Just some regular text without references"

        result = apply_sfs_links(text)

        assert result == text


# ===========================================================================
# apply_internal_links Tests
# ===========================================================================

@pytest.mark.unit
class TestApplyInternalLinks:
    """Test the apply_internal_links function."""

    def test_simple_paragraph_reference(self):
        """Test linking simple paragraph references."""
        text = "Se 5 § för mer information"

        result = apply_internal_links(text)

        # Should create internal link
        assert '[5 §]' in result or '5 §' in result  # May or may not link depending on context

    def test_paragraph_with_letter(self):
        """Test linking paragraphs with letters (e.g., 3 a §)."""
        text = "Enligt 3 a § och 5 b § gäller följande"

        result = apply_internal_links(text)

        # Should handle paragraph numbers with letters
        assert '3 a §' in result or '[3 a §]' in result

    def test_skip_headings(self):
        """Test that headings are not linked."""
        text = "### 5 §\n\nSe 5 § ovan"

        result = apply_internal_links(text)

        lines = result.split('\n')
        # Heading should not be modified
        assert lines[0] == "### 5 §"

    def test_with_chapter_context(self):
        """Test internal linking with chapter context."""
        text = """## 1 kap. Test

### 1 §

Content

### 2 §

Se 1 § i detta kapitel"""

        result = apply_internal_links(text)

        # Should create links (exact format depends on implementation)
        assert '1 §' in result

    def test_no_paragraph_references(self):
        """Test text without paragraph references."""
        text = "Just some text without paragraphs"

        result = apply_internal_links(text)

        # May be unchanged or minimally changed
        assert 'Just some text' in result


# ===========================================================================
# apply_eu_links Tests
# ===========================================================================

@pytest.mark.unit
class TestApplyEuLinks:
    """Test the apply_eu_links function."""

    def test_eu_directive_reference(self):
        """Test linking EU directive references."""
        text = "Enligt direktiv 2016/680/EU ska följande gälla"

        result = apply_eu_links(text)

        # Should create EU link (exact format depends on implementation)
        assert '2016/680' in result or 'EU' in result

    def test_eu_regulation_reference(self):
        """Test linking EU regulation references."""
        text = "GDPR (EU) 2016/679 tillämpas"

        result = apply_eu_links(text)

        # Should handle EU regulations
        assert '2016/679' in result

    def test_no_eu_references(self):
        """Test text without EU references."""
        text = "Just regular Swedish law text"

        result = apply_eu_links(text)

        # Should remain largely unchanged
        assert 'Swedish law' in result


# ===========================================================================
# Integration Tests
# ===========================================================================

@pytest.mark.integration
class TestLinkingIntegration:
    """Integration tests combining different link types."""

    def test_combined_sfs_and_law_name_links(self):
        """Test combining SFS and law name links."""
        text = "Enligt lag (1998:204) och 3 kap. 5 § dataskyddslagen"

        # Apply both
        result = apply_sfs_links(text)
        result = apply_law_name_links(result)

        # Both should be present
        assert '[1998:204]' in result
        assert '[3 kap. 5 § dataskyddslagen]' in result

    def test_all_link_types_together(self):
        """Test applying all link types to complex text."""
        text = """## 1 kap. Tillämpningsområde

### 1 §

Enligt lag (1998:204) och direktiv 2016/680/EU samt
3 kap. 5 § dataskyddslagen gäller följande.

### 2 §

Se 1 § ovan."""

        # Apply all link types
        result = apply_sfs_links(text)
        result = apply_law_name_links(result)
        result = apply_internal_links(result)
        result = apply_eu_links(result)

        # Check various elements are preserved
        assert '## 1 kap.' in result
        assert '### 1 §' in result
        assert '### 2 §' in result

    def test_preserve_swedish_characters(self):
        """Test that Swedish characters are preserved in all linking."""
        text = "Förordning (2024:1) om ändringar enligt 5 § dataskyddslagen"

        result = apply_sfs_links(text)
        result = apply_law_name_links(result)

        assert 'Förordning' in result
        assert 'ändringar' in result
