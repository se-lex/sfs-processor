#!/usr/bin/env python3
"""
Tests for upcoming changes extraction and management.
"""

import pytest
import yaml
from pathlib import Path
from temporal.upcoming_changes import (
    identify_upcoming_changes,
    save_upcoming_file,
    get_doc_ids_for_date,
    get_earliest_pending_date,
    extract_doc_id_from_filename,
    UPCOMING_CHANGES_FILE_PATH
)


# ===========================================================================
# identify_upcoming_changes Tests
# ===========================================================================

@pytest.mark.unit
class TestIdentifyUpcomingChanges:
    """Test the identify_upcoming_changes function."""

    def test_extract_ikraft_datum_from_section(self):
        """Test extracting ikraft_datum from section tag."""
        content = '''<section id="1" class="paragraf" selex:ikraft_datum="2025-06-01">

## 1 §

Content here

</section>'''

        result = identify_upcoming_changes(content)

        assert len(result) == 1
        assert result[0]['type'] == 'ikraft'
        assert result[0]['date'] == '2025-06-01'
        assert result[0]['source'] == 'section_tag'
        assert result[0]['section_id'] == '1'
        assert result[0]['section_title'] == '1 §'

    def test_extract_upphor_datum_from_section(self):
        """Test extracting upphor_datum from section tag."""
        content = '''<section id="2" class="paragraf" selex:upphor_datum="2025-12-31">

## 2 §

This section expires.

</section>'''

        result = identify_upcoming_changes(content)

        assert len(result) == 1
        assert result[0]['type'] == 'upphor'
        assert result[0]['date'] == '2025-12-31'
        assert result[0]['section_id'] == '2'

    def test_extract_from_kapital_section(self):
        """Test extracting from chapter (kapital) section."""
        content = '''<section id="1-kap" class="kapital" selex:ikraft_datum="2025-01-01">

## 1 kap. Inledande bestämmelser

Chapter content

</section>'''

        result = identify_upcoming_changes(content)

        assert len(result) == 1
        assert result[0]['type'] == 'ikraft'
        assert result[0]['class_name'] == 'kapital'
        assert result[0]['section_title'] == '1 kap. Inledande bestämmelser'

    def test_extract_ikraft_datum_from_article(self):
        """Test extracting ikraft_datum from article tag."""
        content = '<article selex:ikraft_datum="2025-03-15">Content</article>'

        result = identify_upcoming_changes(content)

        assert len(result) == 1
        assert result[0]['type'] == 'ikraft'
        assert result[0]['date'] == '2025-03-15'
        assert result[0]['source'] == 'article_tag'

    def test_extract_upphor_datum_from_article(self):
        """Test extracting upphor_datum from article tag."""
        content = '<article selex:upphor_datum="2026-12-31">Content</article>'

        result = identify_upcoming_changes(content)

        assert len(result) == 1
        assert result[0]['type'] == 'upphor'
        assert result[0]['date'] == '2026-12-31'
        assert result[0]['source'] == 'article_tag'

    def test_extract_with_upphavd_flag(self):
        """Test that upphavd flag is detected for article tags."""
        content = '<article selex:upphor_datum="2025-12-31" selex:upphavd="true">Content</article>'

        result = identify_upcoming_changes(content)

        assert len(result) == 1
        assert result[0]['type'] == 'upphor'
        assert result[0].get('is_revoked') is True

    def test_multiple_dates_in_document(self):
        """Test extracting multiple dates from one document."""
        content = '''<article selex:ikraft_datum="2025-01-01">Intro</article>

<section id="1" class="paragraf" selex:ikraft_datum="2025-06-01">
## 1 §
Content
</section>

<section id="2" class="paragraf" selex:upphor_datum="2025-12-31">
## 2 §
Expires
</section>'''

        result = identify_upcoming_changes(content)

        assert len(result) == 3
        # Should be sorted by date
        assert result[0]['date'] == '2025-01-01'
        assert result[1]['date'] == '2025-06-01'
        assert result[2]['date'] == '2025-12-31'

    def test_invalid_date_format_ignored(self):
        """Test that invalid date formats are ignored."""
        content = '''<section id="1" class="paragraf" selex:ikraft_datum="2025-13-45">
## 1 §
Invalid date
</section>'''

        result = identify_upcoming_changes(content)

        assert len(result) == 0

    def test_malformed_date_ignored(self):
        """Test that malformed dates are ignored."""
        content = '''<article selex:ikraft_datum="not-a-date">Content</article>'''

        result = identify_upcoming_changes(content)

        assert len(result) == 0

    def test_no_dates_returns_empty_list(self):
        """Test that content without dates returns empty list."""
        content = '''## 1 kap. Test

### 1 §

Just regular content without temporal markers.'''

        result = identify_upcoming_changes(content)

        assert result == []

    def test_duplicate_removal(self):
        """Test that duplicates are removed."""
        # This might happen if same section appears in multiple patterns
        content = '''<section id="1" class="paragraf" selex:status="ikraft" selex:ikraft_datum="2025-06-01">
## 1 §
Content
</section>'''

        result = identify_upcoming_changes(content)

        # Should only have one entry even if matched by multiple patterns
        assert len(result) >= 1
        # Check that all entries have the same date
        dates = [r['date'] for r in result]
        assert all(d == '2025-06-01' for d in dates)

    def test_sorting_by_date(self):
        """Test that results are sorted by date."""
        content = '''<article selex:ikraft_datum="2025-12-01">Content</article>
<article selex:ikraft_datum="2025-01-01">Content</article>
<article selex:ikraft_datum="2025-06-01">Content</article>'''

        result = identify_upcoming_changes(content)

        assert len(result) == 3
        assert result[0]['date'] == '2025-01-01'
        assert result[1]['date'] == '2025-06-01'
        assert result[2]['date'] == '2025-12-01'


# ===========================================================================
# save_upcoming_file Tests
# ===========================================================================

@pytest.mark.unit
class TestSaveUpcomingFile:
    """Test the save_upcoming_file function."""

    def test_save_single_date(self, tmp_path, monkeypatch):
        """Test saving a single date for a document."""
        # Use temporary file
        test_file = tmp_path / "kommande.yaml"
        monkeypatch.setattr('temporal.upcoming_changes.UPCOMING_CHANGES_FILE_PATH', str(test_file))

        save_upcoming_file('2024:1', ['2025-06-01'])

        # Verify file was created
        assert test_file.exists()

        # Read and verify content
        with open(test_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        assert '2025-06-01' in data
        assert '2024:1' in data['2025-06-01']

    def test_save_multiple_dates(self, tmp_path, monkeypatch):
        """Test saving multiple dates for a document."""
        test_file = tmp_path / "kommande.yaml"
        monkeypatch.setattr('temporal.upcoming_changes.UPCOMING_CHANGES_FILE_PATH', str(test_file))

        save_upcoming_file('2024:1', ['2025-01-01', '2025-06-01', '2025-12-01'])

        with open(test_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        assert len(data) == 3
        assert all('2024:1' in data[date] for date in ['2025-01-01', '2025-06-01', '2025-12-01'])

    def test_append_to_existing_date(self, tmp_path, monkeypatch):
        """Test appending a document to an existing date."""
        test_file = tmp_path / "kommande.yaml"
        monkeypatch.setattr('temporal.upcoming_changes.UPCOMING_CHANGES_FILE_PATH', str(test_file))

        # Save first document
        save_upcoming_file('2024:1', ['2025-06-01'])

        # Save second document with same date
        save_upcoming_file('2024:2', ['2025-06-01'])

        with open(test_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        assert '2025-06-01' in data
        assert len(data['2025-06-01']) == 2
        assert '2024:1' in data['2025-06-01']
        assert '2024:2' in data['2025-06-01']

    def test_avoid_duplicate_doc_ids(self, tmp_path, monkeypatch):
        """Test that duplicate doc IDs are not added."""
        test_file = tmp_path / "kommande.yaml"
        monkeypatch.setattr('temporal.upcoming_changes.UPCOMING_CHANGES_FILE_PATH', str(test_file))

        # Save same document twice
        save_upcoming_file('2024:1', ['2025-06-01'])
        save_upcoming_file('2024:1', ['2025-06-01'])

        with open(test_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # Should only appear once
        assert len(data['2025-06-01']) == 1

    def test_dates_are_sorted(self, tmp_path, monkeypatch):
        """Test that dates are sorted chronologically in output."""
        test_file = tmp_path / "kommande.yaml"
        monkeypatch.setattr('temporal.upcoming_changes.UPCOMING_CHANGES_FILE_PATH', str(test_file))

        save_upcoming_file('2024:1', ['2025-12-01', '2025-01-01', '2025-06-01'])

        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Verify dates appear in sorted order in file
        dates = list(yaml.safe_load(content).keys())
        assert dates == ['2025-01-01', '2025-06-01', '2025-12-01']

    def test_invalid_date_format_skipped(self, tmp_path, monkeypatch, capsys):
        """Test that invalid date formats are skipped with warning."""
        test_file = tmp_path / "kommande.yaml"
        monkeypatch.setattr('temporal.upcoming_changes.UPCOMING_CHANGES_FILE_PATH', str(test_file))

        save_upcoming_file('2024:1', ['2025-13-45'])

        captured = capsys.readouterr()
        assert 'Ogiltigt datum' in captured.out

        # File should not be created or should be empty
        if test_file.exists():
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    data = yaml.safe_load(content)
                    assert data is None or len(data) == 0


# ===========================================================================
# get_doc_ids_for_date Tests
# ===========================================================================

@pytest.mark.unit
class TestGetDocIdsForDate:
    """Test the get_doc_ids_for_date function."""

    def test_get_existing_date(self, tmp_path, monkeypatch):
        """Test getting doc IDs for an existing date."""
        test_file = tmp_path / "kommande.yaml"
        monkeypatch.setattr('temporal.upcoming_changes.UPCOMING_CHANGES_FILE_PATH', str(test_file))

        # Create test data
        save_upcoming_file('2024:1', ['2025-06-01'])
        save_upcoming_file('2024:2', ['2025-06-01'])

        result = get_doc_ids_for_date('2025-06-01')

        assert len(result) == 2
        assert '2024:1' in result
        assert '2024:2' in result

    def test_get_nonexistent_date(self, tmp_path, monkeypatch):
        """Test getting doc IDs for a date that doesn't exist."""
        test_file = tmp_path / "kommande.yaml"
        monkeypatch.setattr('temporal.upcoming_changes.UPCOMING_CHANGES_FILE_PATH', str(test_file))

        save_upcoming_file('2024:1', ['2025-06-01'])

        result = get_doc_ids_for_date('2025-12-31')

        assert result == []

    def test_file_not_exists(self, tmp_path, monkeypatch):
        """Test when kommande.yaml doesn't exist."""
        test_file = tmp_path / "nonexistent.yaml"
        monkeypatch.setattr('temporal.upcoming_changes.UPCOMING_CHANGES_FILE_PATH', str(test_file))

        result = get_doc_ids_for_date('2025-06-01')

        assert result == []

    def test_invalid_date_format(self, tmp_path, monkeypatch, capsys):
        """Test with invalid date format."""
        test_file = tmp_path / "kommande.yaml"
        monkeypatch.setattr('temporal.upcoming_changes.UPCOMING_CHANGES_FILE_PATH', str(test_file))

        result = get_doc_ids_for_date('not-a-date')

        captured = capsys.readouterr()
        # "not-a-date" has correct length but invalid date, so gets "Ogiltigt datum"
        assert 'Ogiltigt datum' in captured.out
        assert result == []


# ===========================================================================
# get_earliest_pending_date Tests
# ===========================================================================

@pytest.mark.unit
class TestGetEarliestPendingDate:
    """Test the get_earliest_pending_date function."""

    def test_get_earliest_date(self, tmp_path, monkeypatch):
        """Test getting earliest date before target date."""
        test_file = tmp_path / "kommande.yaml"
        monkeypatch.setattr('temporal.upcoming_changes.UPCOMING_CHANGES_FILE_PATH', str(test_file))

        # Create test data with multiple dates
        save_upcoming_file('2024:1', ['2025-01-15', '2025-06-01', '2025-12-01'])

        result = get_earliest_pending_date('2025-07-01')

        assert result == '2025-01-15'

    def test_filter_future_dates(self, tmp_path, monkeypatch):
        """Test that future dates are filtered out."""
        test_file = tmp_path / "kommande.yaml"
        monkeypatch.setattr('temporal.upcoming_changes.UPCOMING_CHANGES_FILE_PATH', str(test_file))

        save_upcoming_file('2024:1', ['2025-01-15', '2025-06-01', '2025-12-01'])

        result = get_earliest_pending_date('2025-02-01')

        # Should only consider dates <= 2025-02-01
        assert result == '2025-01-15'

    def test_no_dates_before_target(self, tmp_path, monkeypatch):
        """Test when all dates are after target date."""
        test_file = tmp_path / "kommande.yaml"
        monkeypatch.setattr('temporal.upcoming_changes.UPCOMING_CHANGES_FILE_PATH', str(test_file))

        save_upcoming_file('2024:1', ['2025-06-01', '2025-12-01'])

        result = get_earliest_pending_date('2025-01-01')

        assert result is None

    def test_file_not_exists(self, tmp_path, monkeypatch):
        """Test when file doesn't exist."""
        test_file = tmp_path / "nonexistent.yaml"
        monkeypatch.setattr('temporal.upcoming_changes.UPCOMING_CHANGES_FILE_PATH', str(test_file))

        result = get_earliest_pending_date('2025-06-01')

        assert result is None


# ===========================================================================
# extract_doc_id_from_filename Tests
# ===========================================================================

@pytest.mark.unit
class TestExtractDocIdFromFilename:
    """Test the extract_doc_id_from_filename function."""

    def test_extract_from_sfs_filename(self):
        """Test extracting doc ID from sfs-YYYY-NNNN.md format."""
        result = extract_doc_id_from_filename('sfs-2024-1274.md')

        assert result == '2024:1274'

    def test_extract_without_extension(self):
        """Test extracting from filename without .md extension."""
        result = extract_doc_id_from_filename('sfs-2024-1274')

        assert result == '2024:1274'

    def test_extract_with_leading_zeros(self):
        """Test extracting with leading zeros in number."""
        result = extract_doc_id_from_filename('sfs-2024-0001.md')

        assert result == '2024:0001'

    def test_non_sfs_filename(self):
        """Test with non-sfs filename."""
        result = extract_doc_id_from_filename('other-file.md')

        # Should return as-is without .md
        assert result == 'other-file'

    def test_filename_without_dashes(self):
        """Test filename without expected dash format."""
        result = extract_doc_id_from_filename('test.md')

        assert result == 'test'


# ===========================================================================
# Integration Tests
# ===========================================================================

@pytest.mark.integration
class TestUpcomingChangesIntegration:
    """Integration tests for upcoming changes workflow."""

    def test_complete_workflow(self, tmp_path, monkeypatch):
        """Test complete workflow: identify, save, and retrieve."""
        test_file = tmp_path / "kommande.yaml"
        monkeypatch.setattr('temporal.upcoming_changes.UPCOMING_CHANGES_FILE_PATH', str(test_file))

        # Create markdown content with changes
        content = '''<article selex:ikraft_datum="2025-06-01">Intro</article>

<section id="1" class="paragraf" selex:ikraft_datum="2025-12-01">
## 1 §
Content
</section>'''

        # Identify changes
        changes = identify_upcoming_changes(content)
        assert len(changes) == 2

        # Extract dates
        dates = [change['date'] for change in changes]

        # Save to file
        save_upcoming_file('2024:1274', dates)

        # Retrieve for specific date
        docs = get_doc_ids_for_date('2025-06-01')
        assert '2024:1274' in docs

        # Get earliest pending date
        earliest = get_earliest_pending_date('2025-12-31')
        assert earliest == '2025-06-01'

    def test_multiple_documents_same_date(self, tmp_path, monkeypatch):
        """Test handling multiple documents with same effective date."""
        test_file = tmp_path / "kommande.yaml"
        monkeypatch.setattr('temporal.upcoming_changes.UPCOMING_CHANGES_FILE_PATH', str(test_file))

        # Save multiple documents with same date
        save_upcoming_file('2024:1', ['2025-06-01'])
        save_upcoming_file('2024:2', ['2025-06-01'])
        save_upcoming_file('2024:3', ['2025-06-01'])

        # Verify all are saved
        docs = get_doc_ids_for_date('2025-06-01')
        assert len(docs) == 3
        assert all(doc_id in docs for doc_id in ['2024:1', '2024:2', '2024:3'])

    def test_swedish_characters_in_content(self):
        """Test handling Swedish characters in markdown content."""
        content = '''<section id="1" class="paragraf" selex:ikraft_datum="2025-06-01">

## 1 § Övergångsbestämmelser

Äldre förordningar upphävs.

</section>'''

        result = identify_upcoming_changes(content)

        assert len(result) == 1
        assert result[0]['date'] == '2025-06-01'


# ===========================================================================
# Edge Cases
# ===========================================================================

@pytest.mark.unit
class TestUpcomingChangesEdgeCases:
    """Test edge cases for upcoming changes."""

    def test_leap_year_date(self):
        """Test handling leap year dates."""
        content = '<article selex:ikraft_datum="2024-02-29">Leap year</article>'

        result = identify_upcoming_changes(content)

        assert len(result) == 1
        assert result[0]['date'] == '2024-02-29'

    def test_end_of_year_date(self):
        """Test handling end of year dates."""
        content = '<article selex:upphor_datum="2025-12-31">End of year</article>'

        result = identify_upcoming_changes(content)

        assert len(result) == 1
        assert result[0]['date'] == '2025-12-31'

    def test_very_long_section_content(self):
        """Test handling sections with very long content."""
        long_content = "Very long content " * 1000
        content = f'''<section id="1" class="paragraf" selex:ikraft_datum="2025-06-01">

## 1 §

{long_content}

</section>'''

        result = identify_upcoming_changes(content)

        assert len(result) == 1
        assert result[0]['date'] == '2025-06-01'

    def test_empty_kommande_file(self, tmp_path, monkeypatch):
        """Test handling empty kommande.yaml file."""
        test_file = tmp_path / "kommande.yaml"
        test_file.write_text('', encoding='utf-8')
        monkeypatch.setattr('temporal.upcoming_changes.UPCOMING_CHANGES_FILE_PATH', str(test_file))

        result = get_doc_ids_for_date('2025-06-01')

        assert result == []
