#!/usr/bin/env python3
"""
Test script for government agency linking functionality.

MIT License - see formatters/apply_agency_links.py for full license text.
"""

import pytest
from formatters.apply_agency_links import (
    apply_agency_links,
    count_agency_mentions,
    get_all_agencies,
    _is_inside_markdown_link,
    _load_agency_data
)


# ===========================================================================
# Basic Agency Linking Tests
# ===========================================================================

@pytest.mark.unit
class TestApplyAgencyLinks:
    """Test the apply_agency_links function."""

    @pytest.mark.parametrize("input_text,expected_agency", [
        ('Skatteverket har meddelat att', 'Skatteverket'),
        ('Enligt Försäkringskassan gäller', 'Försäkringskassan'),
        ('Polismyndigheten utför kontroller', 'Polismyndigheten'),
        ('Arbetsmiljöverket inspekterar', 'Arbetsmiljöverket'),
        ('SCB publicerar statistik', 'SCB'),  # Short name
    ])
    def test_agency_linking_basic(self, input_text, expected_agency):
        """Test that agency names are correctly converted to links."""
        result = apply_agency_links(input_text)

        # Should contain a markdown link with the agency name
        assert f'[{expected_agency}]' in result, \
            f"Expected link with '{expected_agency}' in result: {result}"

        # Should contain 'https://'
        assert 'https://' in result, "Link should contain https://"

    def test_multiple_agencies(self):
        """Test linking multiple agencies in one text."""
        text = "Skatteverket och Försäkringskassan samarbetar med Polismyndigheten."

        result = apply_agency_links(text)

        # All three should be linked
        assert '[Skatteverket]' in result
        assert '[Försäkringskassan]' in result
        assert '[Polismyndigheten]' in result

    def test_skip_headings(self):
        """Test that headings are not linked."""
        text = "## Skatteverket\n\nSkatteverket har meddelat att..."

        result = apply_agency_links(text)

        lines = result.split('\n')
        # Heading should not be linked
        assert lines[0] == "## Skatteverket"
        # Body text should be linked
        assert '[Skatteverket]' in lines[2]

    def test_preserve_context(self):
        """Test that surrounding context is preserved."""
        text = "Enligt Skatteverket gäller följande regler"

        result = apply_agency_links(text)

        assert 'Enligt' in result
        assert 'gäller följande regler' in result
        assert '[Skatteverket]' in result

    def test_no_agency_names(self):
        """Test text without agency names."""
        text = "Just some regular text without any agency references"

        result = apply_agency_links(text)

        assert result == text

    def test_already_linked_text(self):
        """Test that already linked text is not double-linked."""
        text = "[Skatteverket](https://www.skatteverket.se) har meddelat"

        result = apply_agency_links(text)

        # Should not create nested links
        assert result.count('[Skatteverket]') <= 1

    def test_case_insensitive_matching(self):
        """Test case-insensitive matching for agency names."""
        text = "SKATTEVERKET har meddelat"

        result = apply_agency_links(text)

        # Should link even with different case
        assert '[SKATTEVERKET]' in result or '[Skatteverket]' in result

    def test_alternative_names(self):
        """Test linking using alternative names."""
        # AF is an alternative name for Arbetsförmedlingen
        text = "AF kan hjälpa dig hitta jobb"

        result = apply_agency_links(text)

        # Should link the short name
        assert '[AF]' in result

    def test_preserve_swedish_characters(self):
        """Test that Swedish characters are preserved."""
        text = "Försäkringskassan handlägger ärenden"

        result = apply_agency_links(text)

        assert 'Försäkringskassan' in result
        assert 'handlägger' in result
        assert 'ärenden' in result


# ===========================================================================
# Helper Function Tests
# ===========================================================================

@pytest.mark.unit
class TestHelperFunctions:
    """Test helper functions."""

    def test_is_inside_markdown_link_positive(self):
        """Test detection of text inside a markdown link."""
        text = "[Skatteverket](https://www.skatteverket.se)"

        # Position inside the link text
        assert _is_inside_markdown_link(text, 1, 12) is True

    def test_is_inside_markdown_link_negative(self):
        """Test detection of text outside a markdown link."""
        text = "Innan [länk](url) efter"

        # Position before the link
        assert _is_inside_markdown_link(text, 0, 5) is False

        # Position after the link
        assert _is_inside_markdown_link(text, 18, 23) is False

    def test_load_agency_data(self):
        """Test that agency data loads correctly."""
        data = _load_agency_data()

        assert 'by_name' in data
        assert 'patterns' in data
        assert len(data['patterns']) > 0

    def test_get_all_agencies(self):
        """Test getting all agencies."""
        agencies = get_all_agencies()

        assert isinstance(agencies, list)
        assert len(agencies) > 0

        # Check structure of first agency
        if agencies:
            agency = agencies[0]
            assert 'name' in agency
            assert 'website' in agency


# ===========================================================================
# Count Mentions Tests
# ===========================================================================

@pytest.mark.unit
class TestCountAgencyMentions:
    """Test the count_agency_mentions function."""

    def test_count_single_agency(self):
        """Test counting a single agency."""
        text = "Skatteverket har meddelat att Skatteverket kommer att..."

        counts = count_agency_mentions(text)

        assert 'Skatteverket' in counts
        assert counts['Skatteverket'] >= 2

    def test_count_multiple_agencies(self):
        """Test counting multiple agencies."""
        text = "Skatteverket och Försäkringskassan samarbetar."

        counts = count_agency_mentions(text)

        # Both agencies should be counted
        assert len(counts) >= 2

    def test_count_empty_text(self):
        """Test counting in empty text."""
        counts = count_agency_mentions("")

        assert counts == {}

    def test_count_no_agencies(self):
        """Test counting text with no agencies."""
        text = "Just regular text without agencies"

        counts = count_agency_mentions(text)

        assert counts == {}


# ===========================================================================
# Integration Tests
# ===========================================================================

@pytest.mark.integration
class TestAgencyLinkingIntegration:
    """Integration tests for agency linking."""

    def test_agency_linking_in_legal_text(self):
        """Test agency linking in realistic legal text."""
        text = """Enligt 3 § förordningen ska Skatteverket pröva ansökningar.

Försäkringskassan handlägger ärenden enligt lagen (2010:111).

Polismyndigheten utför kontroller i enlighet med 5 §."""

        result = apply_agency_links(text)

        # All agencies should be linked
        assert '[Skatteverket]' in result
        assert '[Försäkringskassan]' in result
        assert '[Polismyndigheten]' in result

        # Legal references should be preserved
        assert '3 §' in result
        assert '5 §' in result
        assert '(2010:111)' in result

    def test_agency_linking_with_other_links(self):
        """Test that agency linking works alongside other link types."""
        # Text with SFS reference that should not interfere
        text = "Skatteverket tillämpar lag (1998:204)."

        result = apply_agency_links(text)

        # Agency should be linked
        assert '[Skatteverket]' in result

        # SFS reference should be preserved (not affected)
        assert '(1998:204)' in result

    def test_complex_document(self):
        """Test with a complex document structure."""
        text = """## 1 kap. Tillämpning

### 1 §

Skatteverket är den myndighet som handlägger skatteärenden.

### 2 §

Försäkringskassan beslutar om socialförsäkringsförmåner.

## 2 kap. Samarbete

### 3 §

Polismyndigheten kan begära uppgifter från Skatteverket."""

        result = apply_agency_links(text)

        # Structure should be preserved
        assert '## 1 kap. Tillämpning' in result
        assert '### 1 §' in result
        assert '## 2 kap. Samarbete' in result

        # Agencies in headings should not be linked
        # but agencies in body text should be
        assert result.count('[Skatteverket]') >= 2


# ===========================================================================
# Edge Cases
# ===========================================================================

@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and corner cases."""

    def test_agency_at_end_of_line(self):
        """Test agency name at end of line."""
        text = "Ansökan skickas till Skatteverket"

        result = apply_agency_links(text)

        assert '[Skatteverket]' in result

    def test_agency_at_start_of_line(self):
        """Test agency name at start of line."""
        text = "Skatteverket handlägger"

        result = apply_agency_links(text)

        assert '[Skatteverket]' in result

    def test_agency_with_punctuation(self):
        """Test agency name followed by punctuation."""
        text = "Kontakta Skatteverket. De kan hjälpa."

        result = apply_agency_links(text)

        assert '[Skatteverket]' in result

    def test_newlines_preserved(self):
        """Test that newlines are preserved."""
        text = "Rad 1\nSkatteverket\nRad 3"

        result = apply_agency_links(text)

        assert '\n' in result
        assert result.count('\n') == text.count('\n')

    def test_empty_string(self):
        """Test with empty string."""
        result = apply_agency_links("")

        assert result == ""

    def test_only_whitespace(self):
        """Test with only whitespace."""
        text = "   \n\t\n   "

        result = apply_agency_links(text)

        # Should return unchanged
        assert result == text
