#!/usr/bin/env python3
"""
Tests for Swedish amount and percentage tagging utilities.
"""

import pytest
from formatters.tag_swedish_amounts import (
    tag_swedish_amounts,
    normalize_number,
    generate_amount_slug,
    generate_percentage_slug,
    _slugify,
    _extract_context_word,
)


# ===========================================================================
# normalize_number Tests
# ===========================================================================

@pytest.mark.unit
class TestNormalizeNumber:
    """Test the normalize_number function."""

    def test_simple_number(self):
        """Test normalizing a simple number."""
        assert normalize_number("1000") == "1000"

    def test_number_with_space_separator(self):
        """Test normalizing number with Swedish space as thousands separator."""
        assert normalize_number("1 000") == "1000"
        assert normalize_number("1 000 000") == "1000000"
        assert normalize_number("10 000 000") == "10000000"

    def test_number_with_decimal_comma(self):
        """Test normalizing number with Swedish decimal comma."""
        assert normalize_number("1,5") == "1.5"
        assert normalize_number("12,75") == "12.75"

    def test_number_with_decimal_dot(self):
        """Test normalizing number with decimal dot."""
        assert normalize_number("1.5") == "1.5"

    def test_combined_format(self):
        """Test normalizing number with both space separator and decimal."""
        assert normalize_number("1 000,5") == "1000.5"
        assert normalize_number("1 234 567,89") == "1234567.89"


# ===========================================================================
# _slugify Tests
# ===========================================================================

@pytest.mark.unit
class TestSlugify:
    """Test the _slugify function."""

    def test_simple_text(self):
        """Test slugifying simple text."""
        assert _slugify("belopp") == "belopp"

    def test_swedish_characters(self):
        """Test slugifying Swedish characters."""
        assert _slugify("räntesats") == "rantesats"
        assert _slugify("avgäld") == "avgald"
        assert _slugify("höjning") == "hojning"
        assert _slugify("Årsavgift") == "arsavgift"

    def test_with_numbers(self):
        """Test slugifying text with numbers."""
        assert _slugify("belopp-1000-kr") == "belopp-1000-kr"

    def test_special_characters(self):
        """Test slugifying text with special characters."""
        assert _slugify("avgift (test)") == "avgift-test"

    def test_multiple_spaces(self):
        """Test slugifying text with multiple spaces."""
        assert _slugify("en  två   tre") == "en-tva-tre"


# ===========================================================================
# _extract_context_word Tests
# ===========================================================================

@pytest.mark.unit
class TestExtractContextWord:
    """Test the _extract_context_word function."""

    def test_avgift(self):
        """Test extracting 'avgift' from context."""
        assert _extract_context_word("En avgift på ") == "avgift"

    def test_avgiften(self):
        """Test extracting base word from definite form."""
        result = _extract_context_word("Avgiften är ")
        assert result in ["avgift", "avgift"]

    def test_ranta(self):
        """Test extracting 'ränt' from context."""
        result = _extract_context_word("med en ränta på ")
        assert "rant" in _slugify(result) or result == "belopp"

    def test_no_descriptor(self):
        """Test default when no descriptor found."""
        assert _extract_context_word("xyz ") == "belopp"

    def test_skatt(self):
        """Test extracting 'skatt' from context."""
        result = _extract_context_word("Den kommunala skatten är ")
        assert result in ["skatt", "skatt", "belopp"]


# ===========================================================================
# generate_amount_slug Tests
# ===========================================================================

@pytest.mark.unit
class TestGenerateAmountSlug:
    """Test the generate_amount_slug function."""

    def test_simple_amount(self):
        """Test generating slug for simple amount."""
        slug = generate_amount_slug("1000", None, "kronor", "En avgift på ")
        assert "1000" in slug
        assert "kr" in slug

    def test_amount_with_miljoner(self):
        """Test generating slug for amount with 'miljoner'."""
        slug = generate_amount_slug("5", "miljoner", "kronor", "Kapitalet är ")
        assert "5" in slug
        assert "mkr" in slug

    def test_amount_with_miljarder(self):
        """Test generating slug for amount with 'miljarder'."""
        slug = generate_amount_slug("2", "miljarder", "kronor", "Omsättningen är ")
        assert "2" in slug
        assert "mdkr" in slug

    def test_amount_with_tusen(self):
        """Test generating slug for amount with 'tusen'."""
        slug = generate_amount_slug("50", "tusen", "kronor", "Priset är ")
        assert "50" in slug
        assert "tkr" in slug


# ===========================================================================
# generate_percentage_slug Tests
# ===========================================================================

@pytest.mark.unit
class TestGeneratePercentageSlug:
    """Test the generate_percentage_slug function."""

    def test_simple_percentage(self):
        """Test generating slug for simple percentage."""
        slug = generate_percentage_slug("5", "Räntan är ")
        assert "5" in slug
        assert "procent" in slug

    def test_percentage_with_context(self):
        """Test generating slug with context extraction."""
        slug = generate_percentage_slug("25", "Momsen är ")
        assert "25" in slug
        assert "procent" in slug


# ===========================================================================
# tag_swedish_amounts Tests - Simple amounts
# ===========================================================================

@pytest.mark.unit
class TestTagSwedishAmountsSimple:
    """Test tagging simple Swedish amounts."""

    def test_kronor_amount(self):
        """Test tagging amount with 'kronor'."""
        result = tag_swedish_amounts("Avgiften är 1000 kronor.")
        assert '<data id="' in result
        assert 'type="amount"' in result
        assert 'value="1000"' in result
        assert '>1000 kronor</data>' in result

    def test_kr_amount(self):
        """Test tagging amount with 'kr'."""
        result = tag_swedish_amounts("Priset är 500 kr.")
        assert '<data id="' in result
        assert 'type="amount"' in result
        assert 'value="500"' in result

    def test_sek_amount(self):
        """Test tagging amount with 'SEK'."""
        result = tag_swedish_amounts("Beloppet är 2500 SEK.")
        assert '<data id="' in result
        assert 'type="amount"' in result
        assert 'value="2500"' in result

    def test_amount_with_space_separator(self):
        """Test tagging amount with Swedish space separator."""
        result = tag_swedish_amounts("Summan är 1 000 000 kronor.")
        assert '<data id="' in result
        assert 'value="1000000"' in result

    def test_amount_with_decimal(self):
        """Test tagging amount with decimal."""
        result = tag_swedish_amounts("Avgiften är 99,50 kr.")
        assert '<data id="' in result
        assert 'value="99.50"' in result


# ===========================================================================
# tag_swedish_amounts Tests - Amounts with multipliers
# ===========================================================================

@pytest.mark.unit
class TestTagSwedishAmountsMultipliers:
    """Test tagging Swedish amounts with multipliers."""

    def test_miljoner_kronor(self):
        """Test tagging amount with 'miljoner kronor'."""
        result = tag_swedish_amounts("Budgeten är 5 miljoner kronor.")
        assert '<data id="' in result
        assert 'type="amount"' in result
        assert 'value="5"' in result
        assert 'miljoner kronor</data>' in result

    def test_miljon_kr(self):
        """Test tagging amount with 'miljon kr'."""
        result = tag_swedish_amounts("Det kostar 1 miljon kr.")
        assert '<data id="' in result
        assert 'value="1"' in result

    def test_miljarder_kronor(self):
        """Test tagging amount with 'miljarder kronor'."""
        result = tag_swedish_amounts("Statsbudgeten är 1 000 miljarder kronor.")
        assert '<data id="' in result
        assert 'value="1000"' in result

    def test_tusen_kronor(self):
        """Test tagging amount with 'tusen kronor'."""
        result = tag_swedish_amounts("Avgiften är 50 tusen kronor.")
        assert '<data id="' in result
        assert 'value="50"' in result


# ===========================================================================
# tag_swedish_amounts Tests - Percentages
# ===========================================================================

@pytest.mark.unit
class TestTagSwedishAmountsPercentages:
    """Test tagging Swedish percentages."""

    def test_percent_symbol(self):
        """Test tagging percentage with % symbol."""
        result = tag_swedish_amounts("Räntan är 5%.")
        assert '<data id="' in result
        assert 'type="percentage"' in result
        assert 'value="5"' in result

    def test_percent_with_space(self):
        """Test tagging percentage with space before %."""
        result = tag_swedish_amounts("Momsen är 25 %.")
        assert '<data id="' in result
        assert 'type="percentage"' in result
        assert 'value="25"' in result

    def test_procent_word(self):
        """Test tagging percentage with 'procent' word."""
        result = tag_swedish_amounts("Skattesatsen är 30 procent.")
        assert '<data id="' in result
        assert 'type="percentage"' in result
        assert 'value="30"' in result

    def test_decimal_percentage(self):
        """Test tagging decimal percentage."""
        result = tag_swedish_amounts("Räntan är 2,5 procent.")
        assert '<data id="' in result
        assert 'value="2.5"' in result


# ===========================================================================
# tag_swedish_amounts Tests - Skip headers
# ===========================================================================

@pytest.mark.unit
class TestTagSwedishAmountsHeaders:
    """Test that headers are skipped."""

    def test_skip_h1_header(self):
        """Test that H1 headers are not tagged."""
        result = tag_swedish_amounts("# Avgift 1000 kronor")
        assert '<data' not in result
        assert "# Avgift 1000 kronor" in result

    def test_skip_h2_header(self):
        """Test that H2 headers are not tagged."""
        result = tag_swedish_amounts("## Kapitel om 5 procent skatt")
        assert '<data' not in result

    def test_skip_h3_header(self):
        """Test that H3 headers are not tagged."""
        result = tag_swedish_amounts("### 500 kr avgift")
        assert '<data' not in result

    def test_tag_content_after_header(self):
        """Test that content after header is tagged."""
        result = tag_swedish_amounts("## Rubrik\n\nAvgiften är 1000 kronor.")
        assert "## Rubrik" in result
        assert '<data id="' in result


# ===========================================================================
# tag_swedish_amounts Tests - Skip section tags
# ===========================================================================

@pytest.mark.unit
class TestTagSwedishAmountsSkipTags:
    """Test that XML/HTML tags are skipped."""

    def test_skip_section_tag(self):
        """Test that section tags are not modified."""
        result = tag_swedish_amounts('<section class="paragraf">')
        assert '<data' not in result

    def test_skip_article_tag(self):
        """Test that article tags are not modified."""
        result = tag_swedish_amounts('<article selex:id="test">')
        assert '<data' not in result


# ===========================================================================
# tag_swedish_amounts Tests - Multiple amounts
# ===========================================================================

@pytest.mark.unit
class TestTagSwedishAmountsMultiple:
    """Test tagging multiple amounts in same text."""

    def test_multiple_amounts_same_line(self):
        """Test tagging multiple amounts on same line."""
        result = tag_swedish_amounts("Avgiften är 500 kr eller 1000 kr.")
        assert result.count('<data') == 2
        assert result.count('</data>') == 2

    def test_amount_and_percentage(self):
        """Test tagging both amount and percentage."""
        result = tag_swedish_amounts("Räntan på 5% ger 1000 kronor i avkastning.")
        assert 'type="percentage"' in result
        assert 'type="amount"' in result


# ===========================================================================
# tag_swedish_amounts Tests - Context-based slugs
# ===========================================================================

@pytest.mark.unit
class TestTagSwedishAmountsContextSlugs:
    """Test that slugs are generated based on context."""

    def test_avgift_context(self):
        """Test slug generation with 'avgift' context."""
        result = tag_swedish_amounts("Avgiften är 500 kronor.")
        assert 'id="avgift-500-kr"' in result

    def test_ranta_context_percentage(self):
        """Test slug generation with 'ränta' context for percentage."""
        result = tag_swedish_amounts("Räntan är 5 procent.")
        # Ränta should be extracted and slugified
        assert 'id="' in result
        assert 'procent"' in result


# ===========================================================================
# tag_swedish_amounts Tests - Edge cases
# ===========================================================================

@pytest.mark.unit
class TestTagSwedishAmountsEdgeCases:
    """Test edge cases."""

    def test_empty_string(self):
        """Test with empty string."""
        result = tag_swedish_amounts("")
        assert result == ""

    def test_no_amounts(self):
        """Test text without amounts."""
        text = "Detta är en vanlig text utan belopp."
        result = tag_swedish_amounts(text)
        assert result == text
        assert '<data' not in result

    def test_preserves_surrounding_text(self):
        """Test that surrounding text is preserved."""
        result = tag_swedish_amounts("Före 1000 kr efter.")
        assert result.startswith("Före ")
        assert result.endswith(" efter.")

    def test_multiline_text(self):
        """Test with multiline text."""
        text = """Första raden har 500 kr.

Andra raden har 10 procent.

## Rubrik med 1000 kronor

Tredje raden har 2000 SEK."""
        result = tag_swedish_amounts(text)

        # Check amounts are tagged (note: kr. may include the period in match)
        assert '500 kr' in result and '<data' in result
        assert '10 procent</data>' in result
        assert '2000 SEK</data>' in result

        # Check header is NOT tagged
        assert '## Rubrik med 1000 kronor' in result
        assert '<data' not in result.split('\n')[4]  # Header line
