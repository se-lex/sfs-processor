#!/usr/bin/env python3
"""
Tests for Swedish amount and percentage tagging utilities.
"""

import pytest
from formatters.tag_swedish_amounts import (
    tag_swedish_amounts,
    normalize_number,
    generate_positional_id,
    resolve_id,
    load_reference_table,
    _slugify,
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
# generate_positional_id Tests
# ===========================================================================

@pytest.mark.unit
class TestGeneratePositionalId:
    """Test the generate_positional_id function."""

    def test_with_section_id(self):
        """Test generating positional id with section."""
        result = generate_positional_id("kap5.2", "belopp", 1)
        assert result == "kap5.2-belopp-1"

    def test_with_section_id_multiple(self):
        """Test generating positional id with higher position."""
        result = generate_positional_id("kap5.2", "belopp", 3)
        assert result == "kap5.2-belopp-3"

    def test_without_section_id(self):
        """Test generating positional id without section."""
        result = generate_positional_id(None, "belopp", 1)
        assert result == "belopp-1"

    def test_percentage_type(self):
        """Test generating positional id for percentage."""
        result = generate_positional_id("kap1.5", "procent", 2)
        assert result == "kap1.5-procent-2"


# ===========================================================================
# resolve_id Tests
# ===========================================================================

@pytest.mark.unit
class TestResolveId:
    """Test the resolve_id function."""

    def test_no_mapping_returns_original(self):
        """Test that unmapped ids are returned as-is."""
        result = resolve_id("kap99.99-belopp-99")
        assert result == "kap99.99-belopp-99"

    def test_returns_positional_when_no_table(self):
        """Test fallback when no reference table exists."""
        result = resolve_id("nonexistent-id")
        assert result == "nonexistent-id"


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
# tag_swedish_amounts Tests - Positional ids
# ===========================================================================

@pytest.mark.unit
class TestTagSwedishAmountsPositionalIds:
    """Test that positional ids are generated correctly."""

    def test_simple_positional_id(self):
        """Test positional id without section."""
        result = tag_swedish_amounts("Avgiften är 500 kronor.")
        assert 'id="belopp-1"' in result

    def test_with_section_id(self):
        """Test positional id with section_id parameter."""
        result = tag_swedish_amounts("Avgiften är 500 kronor.", section_id="kap5.2")
        assert 'id="kap5.2-belopp-1"' in result

    def test_multiple_amounts_incrementing(self):
        """Test that multiple amounts get incrementing positions."""
        result = tag_swedish_amounts("Första 500 kr och andra 1000 kr.", section_id="kap1.1")
        assert 'id="kap1.1-belopp-1"' in result
        assert 'id="kap1.1-belopp-2"' in result

    def test_section_tag_resets_counter(self):
        """Test that section tags reset the counter."""
        text = '''<section id="kap1.1">
Belopp 100 kronor.
</section>
<section id="kap1.2">
Belopp 200 kronor.
</section>'''
        result = tag_swedish_amounts(text)
        assert 'id="kap1.1-belopp-1"' in result
        assert 'id="kap1.2-belopp-1"' in result

    def test_percentage_positional_id(self):
        """Test positional id for percentages."""
        result = tag_swedish_amounts("Räntan är 5 procent.", section_id="kap2.3")
        assert 'id="kap2.3-procent-1"' in result

    def test_same_id_across_amendments(self):
        """Test that same position gives same id with different values."""
        result1 = tag_swedish_amounts("Avgiften är 500 kronor.", section_id="kap5.2")
        result2 = tag_swedish_amounts("Avgiften är 1000 kronor.", section_id="kap5.2")
        # Both should have same positional id but different values
        assert 'id="kap5.2-belopp-1"' in result1
        assert 'id="kap5.2-belopp-1"' in result2
        assert 'value="500"' in result1
        assert 'value="1000"' in result2


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
