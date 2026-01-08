"""
Tests for the anteckningar parser (temporal/parse_anteckningar.py).
"""

import pytest
from temporal.parse_anteckningar import parse_anteckningar


class TestParseAnteckningar:
    """Test parsing of Swedish amendment notes."""

    def test_empty_string(self):
        """Empty anteckningar should return empty lists."""
        result = parse_anteckningar("")
        assert result == {'repealed': [], 'amended': [], 'new': []}

    def test_none_input(self):
        """None input should return empty lists."""
        result = parse_anteckningar(None)
        assert result == {'repealed': [], 'amended': [], 'new': []}

    # --- REPEALED (upph.) Tests ---

    def test_upph_simple_paragraph(self):
        """Parse simple repealed paragraph without chapter."""
        result = parse_anteckningar("upph. 15 §")
        assert '15§' in result['repealed']
        assert len(result['repealed']) == 1

    def test_upph_with_chapter(self):
        """Parse repealed paragraph with chapter."""
        result = parse_anteckningar("upph. 29 kap. 15 §")
        assert '29kap15§' in result['repealed']
        assert len(result['repealed']) == 1

    def test_upph_paragraph_with_letter(self):
        """Parse repealed paragraph with letter suffix."""
        result = parse_anteckningar("upph. 29 kap. 22 a §")
        assert '29kap22a§' in result['repealed']
        assert len(result['repealed']) == 1

    def test_upph_multiple_paragraphs_same_chapter(self):
        """Parse multiple repealed paragraphs in same chapter."""
        result = parse_anteckningar("upph. 29 kap. 15, 16 §§")
        assert '29kap15§' in result['repealed']
        assert '29kap16§' in result['repealed']
        assert len(result['repealed']) == 2

    def test_upph_multiple_paragraphs_with_letters(self):
        """Parse multiple paragraphs including one with letter."""
        result = parse_anteckningar("upph. 2 kap. 32, 33 §§")
        assert '2kap32§' in result['repealed']
        assert '2kap33§' in result['repealed']
        assert len(result['repealed']) == 2

    def test_upph_real_example_1(self):
        """Real example from 2010:800.json."""
        anteckningar = "upph. 29 kap. 15, 16 §§, rubr. närmast före 29 kap. 15 §; ändr. 10 kap. 37 §, 11 kap. 36 §"
        result = parse_anteckningar(anteckningar)

        # Should extract the repealed paragraphs
        assert '29kap15§' in result['repealed']
        assert '29kap16§' in result['repealed']

        # Should also extract the amended paragraphs
        assert '10kap37§' in result['amended']
        assert '11kap36§' in result['amended']

    def test_upph_real_example_2(self):
        """Real example with chapter-level repeal."""
        anteckningar = "upph. 23 kap., 29 kap. 22 a §"
        result = parse_anteckningar(anteckningar)

        # Should extract the paragraph repeal (chapter-level is Phase 2)
        assert '29kap22a§' in result['repealed']

    def test_upph_real_example_3(self):
        """Real example with single paragraph."""
        anteckningar = "upph. 15 kap. 23 §; ändr. 3 kap. 2, 4, 5, 7, 10, 12 i §§"
        result = parse_anteckningar(anteckningar)

        # Should extract the repealed paragraph
        assert '15kap23§' in result['repealed']
        assert len(result['repealed']) == 1

        # Should extract amended paragraphs (note: "12 i" has a letter)
        assert '3kap2§' in result['amended']
        assert '3kap4§' in result['amended']
        assert '3kap5§' in result['amended']

    # --- AMENDED (ändr.) Tests ---

    def test_andr_simple(self):
        """Parse simple amended paragraph."""
        result = parse_anteckningar("ändr. 29 kap. 6 §")
        assert '29kap6§' in result['amended']
        assert len(result['amended']) == 1

    def test_andr_multiple_chapters(self):
        """Parse amended paragraphs from multiple chapters."""
        result = parse_anteckningar("ändr. 15 kap. 19 §, 18 kap. 19 §, 19 kap. 27 §")
        assert '15kap19§' in result['amended']
        assert '18kap19§' in result['amended']
        assert '19kap27§' in result['amended']
        assert len(result['amended']) == 3

    def test_andr_multiple_same_chapter(self):
        """Parse multiple amended paragraphs in same chapter."""
        result = parse_anteckningar("ändr. 10 kap. 4 §, 12 kap. 4 §, 13 kap. 4 §")
        assert '10kap4§' in result['amended']
        assert '12kap4§' in result['amended']
        assert '13kap4§' in result['amended']

    def test_andr_real_example(self):
        """Real example with many amended paragraphs."""
        anteckningar = "ändr. 26 kap. 10, 15, 17, 18 §§, 28 kap. 2, 5 §§"
        result = parse_anteckningar(anteckningar)

        # Chapter 26 paragraphs
        assert '26kap10§' in result['amended']
        assert '26kap15§' in result['amended']
        assert '26kap17§' in result['amended']
        assert '26kap18§' in result['amended']

        # Chapter 28 paragraphs
        assert '28kap2§' in result['amended']
        assert '28kap5§' in result['amended']

    # --- NEW (ny/nya) Tests ---

    def test_nya_simple(self):
        """Parse new paragraphs."""
        result = parse_anteckningar("nya 26 kap. 14 a, 14 b, 14 c §§")
        assert '26kap14a§' in result['new']
        assert '26kap14b§' in result['new']
        assert '26kap14c§' in result['new']

    def test_ny_single(self):
        """Parse single new paragraph with 'ny' (singular)."""
        result = parse_anteckningar("ny 3 kap. 11 a §")
        assert '3kap11a§' in result['new']

    def test_nya_real_example(self):
        """Real example with multiple new paragraphs."""
        anteckningar = "nya 26 kap. 14 a, 14 b, 14 c, 16 a, 16 b, 16 c, 16 d §§"
        result = parse_anteckningar(anteckningar)

        assert '26kap14a§' in result['new']
        assert '26kap14b§' in result['new']
        assert '26kap14c§' in result['new']
        assert '26kap16a§' in result['new']
        assert '26kap16b§' in result['new']
        assert '26kap16c§' in result['new']
        assert '26kap16d§' in result['new']

    # --- MIXED Tests ---

    def test_mixed_upph_and_andr(self):
        """Parse mixed upph and ändr clauses."""
        result = parse_anteckningar("upph. 15 §; ändr. 20 §")
        assert '15§' in result['repealed']
        assert '20§' in result['amended']

    def test_complex_real_example(self):
        """Complex real example with upph, ändr, and nya."""
        anteckningar = ("upph. 29 kap. 15, 16 §§, rubr. närmast före 29 kap. 15 §; "
                       "ändr. 10 kap. 37 §, 11 kap. 36 §, 12 kap. 24 §; "
                       "nya 26 kap. 14 a, 14 b §§")
        result = parse_anteckningar(anteckningar)

        # Repealed
        assert '29kap15§' in result['repealed']
        assert '29kap16§' in result['repealed']

        # Amended
        assert '10kap37§' in result['amended']
        assert '11kap36§' in result['amended']
        assert '12kap24§' in result['amended']

        # New
        assert '26kap14a§' in result['new']
        assert '26kap14b§' in result['new']

    # --- EDGE CASES ---

    def test_whitespace_handling(self):
        """Parser should handle extra whitespace."""
        result = parse_anteckningar("upph.  29  kap.  15  §")
        assert '29kap15§' in result['repealed']

    def test_case_insensitive(self):
        """Parser should handle different cases."""
        # Note: The regex uses re.IGNORECASE
        result = parse_anteckningar("upph. 29 KAP. 15 §")
        assert '29kap15§' in result['repealed']

    def test_ignores_rubr_patterns(self):
        """Parser should skip 'rubr.' patterns (Phase 2)."""
        result = parse_anteckningar("upph. 15 §, rubr. närmast före 15 §")
        # Should extract the paragraph but not process rubr
        assert '15§' in result['repealed']

    def test_ignores_betecknas_patterns(self):
        """Parser should skip 'betecknas' patterns (Phase 2)."""
        anteckningar = "upph. 2 kap. 33 §; nuvarande 2 kap. 32 § betecknas 2 kap. 33 §"
        result = parse_anteckningar(anteckningar)
        # Should extract the repealed paragraph but not process betecknas
        assert '2kap33§' in result['repealed']

    def test_multiple_semicolons(self):
        """Parser should handle multiple semicolons correctly."""
        result = parse_anteckningar("upph. 15 §; ändr. 20 §; nya 25 §")
        assert '15§' in result['repealed']
        assert '20§' in result['amended']
        assert '25§' in result['new']


class TestNormalization:
    """Test that normalization produces consistent format."""

    def test_removes_spaces(self):
        """Normalized references should have no spaces."""
        result = parse_anteckningar("upph. 29 kap. 15 a §")
        assert '29kap15a§' in result['repealed']
        # Verify no spaces
        assert ' ' not in result['repealed'][0]

    def test_lowercase(self):
        """Normalized references should be lowercase."""
        result = parse_anteckningar("upph. 29 KAP. 15 A §")
        assert '29kap15a§' in result['repealed']
        # Verify lowercase
        assert result['repealed'][0] == result['repealed'][0].lower()

    def test_consistent_format(self):
        """All references should follow the same format."""
        result = parse_anteckningar("upph. 29 kap. 15 §, 2 kap. 33 a §")
        for ref in result['repealed']:
            # Should match pattern: \d+kap\d+[a-z]?§
            assert 'kap' in ref
            assert ref.endswith('§')
