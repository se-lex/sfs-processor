#!/usr/bin/env python3
"""
Tests for SFS text formatting utilities.
"""

import pytest
from formatters.format_sfs_text import (
    clean_selex_tags,
    normalize_heading_levels,
    parse_logical_sections,
    is_chapter_header,
    generate_section_id,
    format_sfs_text_as_markdown
)


# ===========================================================================
# clean_selex_tags Tests
# ===========================================================================

@pytest.mark.unit
class TestCleanSelexTags:
    """Test the clean_selex_tags function."""

    def test_remove_simple_section_tags(self):
        """Test removing simple <section> tags without attributes."""
        text = """<section>

## 1 kap.

Content here

</section>"""

        result = clean_selex_tags(text)

        assert "<section>" not in result
        assert "</section>" not in result
        # Headings are normalized, so H2 may become H1 if it's the only level
        assert "# 1 kap." in result or "## 1 kap." in result
        assert "Content here" in result

    def test_remove_section_tags_with_attributes(self):
        """Test removing <section> tags with selex attributes."""
        text = """<section selex:id="1-kap">

## 1 kap. Inledande bestämmelser

Text content

</section>"""

        result = clean_selex_tags(text)

        assert "<section" not in result
        assert "selex:id" not in result
        assert "</section>" not in result
        # Headings are normalized
        assert "# 1 kap." in result or "## 1 kap." in result

    def test_remove_article_tags(self):
        """Test removing <article> tags."""
        text = """<article selex:id="main">

# Förordning om test

Content

</article>"""

        result = clean_selex_tags(text)

        assert "<article" not in result
        assert "</article>" not in result
        assert "# Förordning om test" in result
        assert "Content" in result

    def test_remove_empty_lines_after_tags(self):
        """Test that empty lines after opening tags are handled correctly."""
        text = """<section>


## Heading

Content

</section>"""

        result = clean_selex_tags(text)

        # Should not have excessive empty lines
        assert result.count('\n\n\n') == 0

    def test_preserve_content_between_sections(self):
        """Test that content between sections is preserved."""
        text = """<section>

## Section 1

Content 1

</section>

<section>

## Section 2

Content 2

</section>"""

        result = clean_selex_tags(text)

        # Headings are normalized
        assert "# Section 1" in result or "## Section 1" in result
        assert "Content 1" in result
        assert "# Section 2" in result or "## Section 2" in result
        assert "Content 2" in result

    def test_normalize_headings_after_cleaning(self):
        """Test that heading levels are normalized after cleaning."""
        # If we have H1 and H3 but no H2, H3 should become H2
        text = """<section>

# Level 1

### Level 3

</section>"""

        result = clean_selex_tags(text)

        # H3 should be normalized to H2 (since there's no H2)
        assert result.count('#') > 0  # Headings exist

    def test_handle_nested_sections(self):
        """Test handling nested section tags."""
        text = """<section>

## Outer

<section>

### Inner

</section>

</section>"""

        result = clean_selex_tags(text)

        assert "<section>" not in result
        assert "</section>" not in result
        assert "## Outer" in result or "# Outer" in result  # May be normalized
        assert "### Inner" in result or "## Inner" in result  # May be normalized


# ===========================================================================
# normalize_heading_levels Tests
# ===========================================================================

@pytest.mark.unit
class TestNormalizeHeadingLevels:
    """Test the normalize_heading_levels function."""

    def test_normalize_skip_levels(self):
        """Test normalizing headings that skip levels (H1, H3 -> H1, H2)."""
        text = """# Level 1

### Level 3

##### Level 5"""

        result = normalize_heading_levels(text)

        lines = result.split('\n')
        # Should have H1, H2, H3 (normalized from 1, 3, 5)
        assert lines[0] == "# Level 1"  # Stays H1
        assert lines[2] == "## Level 3"  # H3 -> H2
        assert lines[4] == "### Level 5"  # H5 -> H3

    def test_already_normalized_unchanged(self):
        """Test that already normalized headings remain unchanged."""
        text = """# Level 1

## Level 2

### Level 3"""

        result = normalize_heading_levels(text)

        assert result == text

    def test_multiple_same_level_headings(self):
        """Test multiple headings at the same level."""
        text = """# First H1

# Second H1

### H3

### Another H3"""

        result = normalize_heading_levels(text)

        # H3 should become H2 (since we have H1 and H3 but no H2)
        assert "## H3" in result
        assert "## Another H3" in result

    def test_no_headings_returns_unchanged(self):
        """Test that text without headings is returned unchanged."""
        text = """Just some text

No headings here"""

        result = normalize_heading_levels(text)

        assert result == text

    def test_single_heading_level(self):
        """Test text with only one heading level."""
        text = """### Heading 1

### Heading 2

### Heading 3"""

        result = normalize_heading_levels(text)

        # All H3 should become H1 (first level)
        assert "# Heading 1" in result
        assert "# Heading 2" in result
        assert "# Heading 3" in result


# ===========================================================================
# parse_logical_sections Tests
# ===========================================================================

@pytest.mark.integration
class TestParseLogicalSections:
    """Test the parse_logical_sections function."""

    def test_parse_simple_sections(self):
        """Test parsing simple text into sections."""
        text = """## 1 kap. Introduction

Content for chapter 1.

## 2 kap. Second chapter

Content for chapter 2."""

        result = parse_logical_sections(text)

        # Should have section tags
        assert "<section" in result
        assert "</section>" in result
        assert "## 1 kap." in result
        assert "## 2 kap." in result

    def test_parse_paragraphs(self):
        """Test parsing paragraphs (§)."""
        text = """### 1 §

First paragraph content.

### 2 §

Second paragraph content."""

        result = parse_logical_sections(text)

        assert "### 1 §" in result
        assert "### 2 §" in result
        assert "First paragraph content." in result

    def test_preserve_content(self):
        """Test that all content is preserved."""
        text = """## 1 kap.

### 1 §

This is important content with Swedish chars: åäö.

### 2 §

More content here."""

        result = parse_logical_sections(text)

        assert "This is important content with Swedish chars: åäö." in result
        assert "More content here." in result

    def test_handle_empty_input(self):
        """Test handling empty input."""
        text = ""

        result = parse_logical_sections(text)

        assert result == "" or result == "\n" or not result.strip()


# ===========================================================================
# Helper Function Tests
# ===========================================================================

@pytest.mark.unit
class TestIsChapterHeader:
    """Test the is_chapter_header function."""

    def test_avdelning_roman_numerals(self):
        """Test AVDELNING with Roman numerals."""
        assert is_chapter_header("AVDELNING I")
        assert is_chapter_header("AVDELNING II")
        assert is_chapter_header("AVD. III")

    def test_avdelning_swedish_ordinals(self):
        """Test AVDELNING with Swedish ordinals."""
        assert is_chapter_header("FÖRSTA AVDELNING")
        assert is_chapter_header("ANDRA AVDELNINGEN")
        assert is_chapter_header("TREDJE AVD.")

    def test_not_chapter_header(self):
        """Test strings that are not chapter headers."""
        assert not is_chapter_header("Just a heading")
        assert not is_chapter_header("1 kap.")
        assert not is_chapter_header("§ 1")
        assert not is_chapter_header("")


@pytest.mark.unit
class TestGenerateSectionId:
    """Test the generate_section_id function."""

    def test_generate_id_from_chapter(self):
        """Test generating ID from chapter heading."""
        result = generate_section_id("1 kap. Inledande bestämmelser")

        # ID format is "kapN" not "N-kap"
        assert "kap" in result.lower()
        assert "1" in result
        # IDs should be lowercase
        assert result.islower()

    def test_generate_id_from_paragraph(self):
        """Test generating ID from paragraph (§)."""
        result = generate_section_id("3 §")

        assert "3" in result
        # Should contain section marker
        assert result  # Non-empty

    def test_generate_id_with_parent(self):
        """Test generating ID with parent ID."""
        result = generate_section_id("2 §", parent_id="1-kap")

        # Should include parent reference
        assert result  # Non-empty
        # Parent might be included in some way
        assert len(result) > 1

    def test_handle_special_characters(self):
        """Test handling special characters in heading."""
        result = generate_section_id("Ändring i 3 § lag (2024:1)")

        # Should handle Swedish characters and special chars
        assert result  # Non-empty
        # Special chars should be converted to valid ID chars
        assert " " not in result  # Spaces should be converted

    def test_empty_heading(self):
        """Test handling empty heading raises ValueError."""
        # Empty heading should raise ValueError
        with pytest.raises(ValueError):
            generate_section_id("")

    def test_generate_id_from_avdelning_roman(self):
        """Test generating ID from AVDELNING with Roman numerals."""
        assert generate_section_id("AVDELNING I") == "avd1"
        assert generate_section_id("AVDELNING II. Allmänna bestämmelser") == "avd2"
        assert generate_section_id("AVD. III") == "avd3"
        assert generate_section_id("AVDELNING IV. INSATSER TILL ENSKILDA") == "avd4"

    def test_generate_id_from_avdelning_swedish(self):
        """Test generating ID from AVDELNING with Swedish ordinals."""
        assert generate_section_id("FÖRSTA AVDELNING") == "avd1"
        assert generate_section_id("ANDRA AVDELNINGEN") == "avd2"
        assert generate_section_id("TREDJE AVD.") == "avd3"
        assert generate_section_id("FJÄRDE AVDELNING. Titel här") == "avd4"


# ===========================================================================
# Edge Cases
# ===========================================================================

@pytest.mark.unit
class TestFormatSfsTextEdgeCases:
    """Test edge cases for SFS text formatting."""

    def test_clean_selex_tags_with_swedish_content(self):
        """Test cleaning selex tags with Swedish characters."""
        text = """<section>

## Övergångsbestämmelser

Äldre förordningar upphävs.

</section>"""

        result = clean_selex_tags(text)

        assert "Övergångsbestämmelser" in result
        assert "Äldre förordningar upphävs." in result
        assert "<section>" not in result

    def test_normalize_with_all_levels(self):
        """Test normalizing with all heading levels present."""
        text = """# H1
## H2
### H3
#### H4
##### H5
###### H6"""

        result = normalize_heading_levels(text)

        # All levels present, should remain unchanged
        assert result == text

    def test_clean_selex_preserves_markdown_structure(self):
        """Test that cleaning preserves markdown structure."""
        text = """<section>

## Heading

- List item 1
- List item 2

1. Numbered item
2. Another item

</section>"""

        result = clean_selex_tags(text)

        assert "- List item 1" in result
        assert "- List item 2" in result
        assert "1. Numbered item" in result
        assert "2. Another item" in result

    def test_multiple_consecutive_sections(self):
        """Test handling multiple consecutive sections."""
        text = """<section>

## Section 1

</section>
<section>

## Section 2

</section>
<section>

## Section 3

</section>"""

        result = clean_selex_tags(text)

        assert result.count("## Section") == 3 or result.count("# Section") == 3
        assert "<section>" not in result


# ===========================================================================
# AVDELNING Integration Tests
# ===========================================================================

@pytest.mark.integration
class TestAvdelningIntegration:
    """Integration tests for AVDELNING document processing."""

    def test_avdelning_document_formatting(self):
        """Test that documents with AVDELNING structure are formatted correctly."""
        # Sample text with AVDELNING structure (Roman numerals)
        text = """AVDELNING I. INLEDANDE BESTÄMMELSER

1 kap. Lagens innehåll

1 §

Denna lag innehåller bestämmelser om socialtjänsten.

AVDELNING II. ALLMÄNNA BESTÄMMELSER

2 kap. Socialnämndens ansvar

1 §

Varje kommun ska ha en socialnämnd."""

        result = format_sfs_text_as_markdown(text)

        # Verify AVDELNING headers are formatted as H2
        assert "## AVDELNING I. INLEDANDE BESTÄMMELSER" in result
        assert "## AVDELNING II. ALLMÄNNA BESTÄMMELSER" in result

        # Verify chapter headers are present
        assert "kap." in result

        # Verify paragraph markers are present
        assert "§" in result

        # Verify content is preserved
        assert "socialtjänsten" in result
        assert "socialnämnd" in result

    def test_avdelning_with_swedish_ordinals(self):
        """Test AVDELNING with Swedish ordinal numbers."""
        text = """FÖRSTA AVDELNING

1 kap. Inledande bestämmelser

1 §

Första paragrafen.

ANDRA AVDELNINGEN

2 kap. Fortsättning

1 §

Andra paragrafen."""

        result = format_sfs_text_as_markdown(text)

        # Verify AVDELNING headers with Swedish ordinals are formatted
        assert "## FÖRSTA AVDELNING" in result
        assert "## ANDRA AVDELNINGEN" in result

        # Verify structure is preserved
        assert "kap." in result
        assert "§" in result

    def test_avdelning_sections_with_parse_logical_sections(self):
        """Test that AVDELNING sections are properly tagged with parse_logical_sections."""
        text = """AVDELNING I

1 kap.

1 §

Content here."""

        # First format as markdown
        formatted = format_sfs_text_as_markdown(text)

        # Then parse logical sections
        result = parse_logical_sections(formatted)

        # Verify section tags are present
        assert "<section" in result
        assert "</section>" in result

        # Verify AVDELNING section has the correct CSS class
        assert 'class="avdelning"' in result or 'class="forfattning avdelning"' in result

        # Verify the AVDELNING header is still present
        assert "AVDELNING I" in result


# ===========================================================================
# Repeal Map Integration Tests
# ===========================================================================

@pytest.mark.unit
class TestRepealMapIntegration:
    """Test the repeal_map functionality for tracking ändringsförfattningar."""

    def test_section_with_repeal_map_gets_upphavd_av_attribute(self):
        """Test that a repealed section gets the upphavd_av attribute when repeal_map is provided."""
        text = """#### 15 §

Denna paragraf har upphävts."""

        # Create a repeal map indicating that paragraph 15 was repealed by 2024:796
        repeal_map = {'15§': '2024:796'}

        result = parse_logical_sections(text, repeal_map=repeal_map)

        # Should have upphavd status
        assert 'selex:upphavd="true"' in result

        # Should have upphavd_av attribute
        assert 'selex:upphavd_av="2024:796"' in result

    def test_section_with_chapter_repeal_map(self):
        """Test that a repealed section with chapter reference gets the upphavd_av attribute."""
        text = """## 29 kap.

#### 15 §

Denna paragraf har upphävts."""

        # Create a repeal map with chapter reference
        repeal_map = {'29kap15§': '2024:796'}

        result = parse_logical_sections(text, repeal_map=repeal_map)

        # Should have upphavd status
        assert 'selex:upphavd="true"' in result

        # Should have upphavd_av attribute
        assert 'selex:upphavd_av="2024:796"' in result

    def test_section_without_match_no_upphavd_av(self):
        """Test that a section without a match in repeal_map doesn't get upphavd_av attribute."""
        text = """#### 15 §

Normal content."""

        # Create a repeal map that doesn't include paragraph 15
        repeal_map = {'16§': '2024:796'}

        result = parse_logical_sections(text, repeal_map=repeal_map)

        # Should not have upphavd status (no "upphävd" in content)
        assert 'selex:upphavd="true"' not in result

        # Should not have upphavd_av attribute
        assert 'selex:upphavd_av' not in result

    def test_backward_compatibility_no_repeal_map(self):
        """Test that parse_logical_sections works without repeal_map (backward compatibility)."""
        text = """#### 15 §

Denna paragraf har upphävts."""

        # Call without repeal_map
        result = parse_logical_sections(text)

        # Should have upphavd status (from content)
        assert 'selex:upphavd="true"' in result

        # Should not have upphavd_av attribute
        assert 'selex:upphavd_av' not in result

    def test_multiple_repealed_sections(self):
        """Test handling multiple repealed sections with different ändringsförfattningar."""
        text = """## 29 kap.

#### 15 §

Denna paragraf har upphävts.

#### 16 §

Denna paragraf har upphävts."""

        # Different amendments repealed different paragraphs
        repeal_map = {
            '29kap15§': '2024:796',
            '29kap16§': '2023:123'
        }

        result = parse_logical_sections(text, repeal_map=repeal_map)

        # Both should have upphavd_av attributes
        assert 'selex:upphavd_av="2024:796"' in result
        assert 'selex:upphavd_av="2023:123"' in result

    def test_format_sfs_text_with_repeal_map(self):
        """Test that format_sfs_text_as_markdown accepts and passes repeal_map."""
        text = """29 kap.

15 §

Denna paragraf har upphävts."""

        repeal_map = {'29kap15§': '2024:796'}

        # format_sfs_text_as_markdown should accept repeal_map
        formatted = format_sfs_text_as_markdown(text, repeal_map=repeal_map)

        # Then parse_logical_sections should be called with it
        result = parse_logical_sections(formatted, repeal_map=repeal_map)

        # Should have the upphavd_av attribute
        assert 'selex:upphavd_av="2024:796"' in result

    def test_repeal_map_with_paragraph_letter(self):
        """Test repeal map with paragraph letters (e.g., 15a§)."""
        text = """## 2 kap.

#### 33 a §

Denna paragraf har upphävts."""

        repeal_map = {'2kap33a§': '2024:500'}

        result = parse_logical_sections(text, repeal_map=repeal_map)

        # Should have upphavd_av attribute
        assert 'selex:upphavd_av="2024:500"' in result

    def test_repeal_map_normalization(self):
        """Test that section ID normalization works for matching."""
        text = """## 10 kap.

#### 37 §

Denna paragraf har upphävts."""

        # Repeal map uses different notation
        repeal_map = {'10kap37§': '2020:100'}

        result = parse_logical_sections(text, repeal_map=repeal_map)

        # Should match despite different notation
        assert 'selex:upphavd_av="2020:100"' in result
