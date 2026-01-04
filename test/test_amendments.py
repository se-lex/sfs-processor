#!/usr/bin/env python3
"""
Tests for amendment processing utilities.
"""

import pytest
from temporal.amendments import extract_amendments, process_markdown_amendments


# ===========================================================================
# extract_amendments Tests
# ===========================================================================

@pytest.mark.unit
class TestExtractAmendments:
    """Test the extract_amendments function."""

    def test_extract_single_amendment(self):
        """Test extracting a single amendment."""
        andringar = [
            {
                'beteckning': '2024:100',
                'rubrik': 'Förordning om ändring',
                'ikraftDateTime': '2024-06-01T00:00:00',
                'anteckningar': 'Test notes'
            }
        ]

        result = extract_amendments(andringar)

        assert len(result) == 1
        assert result[0]['beteckning'] == '2024:100'
        assert result[0]['rubrik'] == 'Förordning om ändring'
        assert result[0]['ikraft_datum'] == '2024-06-01'
        assert result[0]['anteckningar'] == 'Test notes'

    def test_extract_multiple_amendments(self):
        """Test extracting multiple amendments."""
        andringar = [
            {
                'beteckning': '2024:100',
                'rubrik': 'First amendment',
                'ikraftDateTime': '2024-06-01T00:00:00',
                'anteckningar': ''
            },
            {
                'beteckning': '2024:200',
                'rubrik': 'Second amendment',
                'ikraftDateTime': '2024-12-01T00:00:00',
                'anteckningar': ''
            }
        ]

        result = extract_amendments(andringar)

        assert len(result) == 2
        assert result[0]['beteckning'] == '2024:100'
        assert result[1]['beteckning'] == '2024:200'

    def test_sort_amendments_chronologically(self):
        """Test that amendments are sorted by ikraft_datum."""
        andringar = [
            {
                'beteckning': '2024:200',
                'rubrik': 'Later',
                'ikraftDateTime': '2024-12-01T00:00:00',
                'anteckningar': ''
            },
            {
                'beteckning': '2023:50',
                'rubrik': 'Earliest',
                'ikraftDateTime': '2023-06-01T00:00:00',
                'anteckningar': ''
            },
            {
                'beteckning': '2024:100',
                'rubrik': 'Middle',
                'ikraftDateTime': '2024-06-01T00:00:00',
                'anteckningar': ''
            }
        ]

        result = extract_amendments(andringar)

        # Should be sorted chronologically
        assert len(result) == 3
        assert result[0]['beteckning'] == '2023:50'  # Earliest
        assert result[1]['beteckning'] == '2024:100'  # Middle
        assert result[2]['beteckning'] == '2024:200'  # Latest

    def test_filter_empty_beteckning(self):
        """Test that amendments without beteckning are filtered out."""
        andringar = [
            {
                'beteckning': '2024:100',
                'rubrik': 'Valid',
                'ikraftDateTime': '2024-06-01T00:00:00',
                'anteckningar': ''
            },
            {
                'beteckning': '',  # Empty beteckning
                'rubrik': 'Invalid',
                'ikraftDateTime': '2024-12-01T00:00:00',
                'anteckningar': ''
            },
            {
                # Missing beteckning
                'rubrik': 'Also invalid',
                'ikraftDateTime': '2024-12-01T00:00:00',
                'anteckningar': ''
            }
        ]

        result = extract_amendments(andringar)

        # Only the valid one should be included
        assert len(result) == 1
        assert result[0]['beteckning'] == '2024:100'

    def test_handle_missing_ikraft_datum(self):
        """Test handling amendments without ikraft_datum."""
        andringar = [
            {
                'beteckning': '2024:100',
                'rubrik': 'With date',
                'ikraftDateTime': '2024-06-01T00:00:00',
                'anteckningar': ''
            },
            {
                'beteckning': '2024:200',
                'rubrik': 'Without date',
                # No ikraftDateTime
                'anteckningar': ''
            }
        ]

        result = extract_amendments(andringar)

        # Both should be included
        assert len(result) == 2
        # The one without date should be sorted to the end
        assert result[0]['beteckning'] == '2024:100'
        assert result[1]['beteckning'] == '2024:200'
        assert result[1]['ikraft_datum'] is None

    def test_clean_text_in_rubrik(self):
        """Test that rubrik text is cleaned."""
        andringar = [
            {
                'beteckning': '2024:100',
                'rubrik': 'Förordning (2024:1)  ',  # Extra spaces
                'ikraftDateTime': '2024-06-01T00:00:00',
                'anteckningar': 'Notes (2023:30)'
            }
        ]

        result = extract_amendments(andringar)

        # clean_text should remove beteckning patterns and trim
        assert result[0]['rubrik'] == 'Förordning'  # (2024:1) removed
        assert result[0]['anteckningar'] == 'Notes'  # (2023:30) removed

    def test_empty_list(self):
        """Test extracting from empty list."""
        result = extract_amendments([])
        assert result == []

    def test_handle_none_values(self):
        """Test handling None values in fields."""
        andringar = [
            {
                'beteckning': '2024:100',
                'rubrik': None,
                'ikraftDateTime': None,
                'anteckningar': None
            }
        ]

        result = extract_amendments(andringar)

        assert len(result) == 1
        assert result[0]['rubrik'] == '' or result[0]['rubrik'] is None


# ===========================================================================
# process_markdown_amendments Tests
# ===========================================================================

@pytest.mark.integration
class TestProcessMarkdownAmendments:
    """Test the process_markdown_amendments function."""

    def test_process_document_without_amendments(self):
        """Test processing document with no amendments."""
        content = """---
rubrik: Test
beteckning: "2024:1"
---

# Test Document

<section>

## 1 kap.

Content here

</section>"""

        data = {
            'beteckning': '2024:1',
            'andringsforfattningar': []  # No amendments
        }

        result = process_markdown_amendments(content, data)

        # Should apply temporal processing with current date
        assert "# Test Document" in result
        assert "rubrik" in result

    def test_process_document_with_amendments(self):
        """Test processing document with amendments (no markers)."""
        content = """---
rubrik: Test
beteckning: "2024:1"
---

# Test Document

<section>

## 1 kap.

Content

</section>"""

        data = {
            'beteckning': '2024:1',
            'andringsforfattningar': [
                {
                    'beteckning': '2024:100',
                    'rubrik': 'Amendment',
                    'ikraftDateTime': '2024-06-01T00:00:00',
                    'anteckningar': ''
                }
            ]
        }

        result = process_markdown_amendments(content, data, verbose=False)

        # Should still process (applies temporal with current date since no markers)
        assert "# Test Document" in result
        assert "rubrik" in result

    def test_preserve_frontmatter(self):
        """Test that frontmatter is preserved."""
        content = """---
rubrik: Test Document
beteckning: "2024:1"
ikraft_datum: "2024-01-01"
---

# Test

Content"""

        data = {
            'beteckning': '2024:1',
            'andringsforfattningar': []
        }

        result = process_markdown_amendments(content, data)

        # Frontmatter should be preserved
        assert "---" in result
        assert "rubrik: Test Document" in result or "rubrik:" in result
        assert "beteckning" in result

    def test_handle_content_without_frontmatter(self):
        """Test handling content without frontmatter."""
        content = "# Just content\n\nNo frontmatter"

        data = {
            'beteckning': '2024:1',
            'andringsforfattningar': []
        }

        result = process_markdown_amendments(content, data, verbose=False)

        # Should return original content unchanged (with warning)
        assert result == content

    def test_handle_malformed_frontmatter(self):
        """Test handling malformed frontmatter."""
        content = """---
rubrik: Test
# Missing closing marker

Content"""

        data = {
            'beteckning': '2024:1',
            'andringsforfattningar': []
        }

        result = process_markdown_amendments(content, data, verbose=False)

        # Should return original content (can't find frontmatter end)
        assert result == content


# ===========================================================================
# Integration Tests
# ===========================================================================

@pytest.mark.integration
class TestAmendmentsIntegration:
    """Integration tests for amendment processing."""

    def test_extract_and_process_complete_workflow(self):
        """Test complete workflow of extracting and processing amendments."""
        # Create amendment data
        andringar = [
            {
                'beteckning': '2024:200',
                'rubrik': 'Later amendment (2024:200)',
                'ikraftDateTime': '2024-12-01T00:00:00',
                'anteckningar': 'Notes'
            },
            {
                'beteckning': '2024:100',
                'rubrik': 'Earlier amendment (2024:100)',
                'ikraftDateTime': '2024-06-01T00:00:00',
                'anteckningar': 'Earlier notes'
            }
        ]

        # Extract amendments
        extracted = extract_amendments(andringar)

        # Should be sorted chronologically
        assert len(extracted) == 2
        assert extracted[0]['beteckning'] == '2024:100'
        assert extracted[1]['beteckning'] == '2024:200'

        # Verify clean_text was applied
        assert '(2024:100)' not in extracted[0]['rubrik']
        assert '(2024:200)' not in extracted[1]['rubrik']

    def test_handle_duplicate_ikraft_datum(self):
        """Test handling duplicate ikraft_datum (should work but warn)."""
        andringar = [
            {
                'beteckning': '2024:100',
                'rubrik': 'First',
                'ikraftDateTime': '2024-06-01T00:00:00',
                'anteckningar': ''
            },
            {
                'beteckning': '2024:101',
                'rubrik': 'Second',
                'ikraftDateTime': '2024-06-01T00:00:00',  # Same date
                'anteckningar': ''
            }
        ]

        result = extract_amendments(andringar)

        # Should include both
        assert len(result) == 2
        # Both should have same ikraft_datum
        assert result[0]['ikraft_datum'] == result[1]['ikraft_datum']

    def test_swedish_characters_in_amendments(self):
        """Test handling Swedish characters in amendments."""
        andringar = [
            {
                'beteckning': '2024:100',
                'rubrik': 'Förordning om ändringar i äldre bestämmelser',
                'ikraftDateTime': '2024-06-01T00:00:00',
                'anteckningar': 'Övergångsbestämmelser'
            }
        ]

        result = extract_amendments(andringar)

        assert len(result) == 1
        assert 'Förordning' in result[0]['rubrik']
        assert 'Övergångsbestämmelser' in result[0]['anteckningar']


# ===========================================================================
# Edge Cases
# ===========================================================================

@pytest.mark.unit
class TestAmendmentsEdgeCases:
    """Test edge cases for amendment processing."""

    def test_very_old_amendment_dates(self):
        """Test handling very old amendment dates."""
        andringar = [
            {
                'beteckning': '1950:100',
                'rubrik': 'Very old',
                'ikraftDateTime': '1950-01-01T00:00:00',
                'anteckningar': ''
            }
        ]

        result = extract_amendments(andringar)

        assert len(result) == 1
        assert result[0]['ikraft_datum'] == '1950-01-01'

    def test_far_future_amendment_dates(self):
        """Test handling far future amendment dates."""
        andringar = [
            {
                'beteckning': '2024:100',
                'rubrik': 'Current',
                'ikraftDateTime': '2024-06-01T00:00:00',
                'anteckningar': ''
            },
            {
                'beteckning': '2100:100',
                'rubrik': 'Far future',
                'ikraftDateTime': '2100-01-01T00:00:00',
                'anteckningar': ''
            }
        ]

        result = extract_amendments(andringar)

        # Should be sorted with future date last
        assert len(result) == 2
        assert result[0]['beteckning'] == '2024:100'
        assert result[1]['beteckning'] == '2100:100'

    def test_amendments_with_same_beteckning_different_dates(self):
        """Test handling amendments with same beteckning but different dates."""
        andringar = [
            {
                'beteckning': '2024:100',
                'rubrik': 'First version',
                'ikraftDateTime': '2024-06-01T00:00:00',
                'anteckningar': ''
            },
            {
                'beteckning': '2024:100',  # Same beteckning
                'rubrik': 'Second version',
                'ikraftDateTime': '2024-12-01T00:00:00',
                'anteckningar': ''
            }
        ]

        result = extract_amendments(andringar)

        # Both should be included and sorted by date
        assert len(result) == 2
        assert result[0]['rubrik'] == 'First version'
        assert result[1]['rubrik'] == 'Second version'

    def test_empty_strings_vs_none(self):
        """Test distinction between empty strings and None values."""
        andringar = [
            {
                'beteckning': '2024:100',
                'rubrik': '',  # Empty string
                'ikraftDateTime': '2024-06-01T00:00:00',
                'anteckningar': ''
            }
        ]

        result = extract_amendments(andringar)

        assert len(result) == 1
        # Empty string should be preserved
        assert result[0]['rubrik'] == '' or result[0]['rubrik'] is not None
