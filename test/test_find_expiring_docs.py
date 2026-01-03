#!/usr/bin/env python3
"""
Tests for finding expiring documents functionality.
"""

import pytest
import json
from pathlib import Path
from temporal.find_expiring_docs import (
    load_json_file,
    has_expiring_datetime,
    find_expiring_files,
    print_results,
    save_results_to_file
)


# ===========================================================================
# load_json_file Tests
# ===========================================================================

@pytest.mark.unit
class TestLoadJsonFile:
    """Test the load_json_file function."""

    def test_load_valid_json(self, tmp_path):
        """Test loading a valid JSON file."""
        test_file = tmp_path / "test.json"
        data = {
            "beteckning": "2024:1",
            "rubrik": "Test förordning",
            "tidsbegransadDateTime": "2025-12-31T23:59:59"
        }
        test_file.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

        result = load_json_file(test_file)

        assert result == data
        assert result['beteckning'] == "2024:1"

    def test_load_empty_json_object(self, tmp_path):
        """Test loading empty JSON object."""
        test_file = tmp_path / "empty.json"
        test_file.write_text('{}', encoding='utf-8')

        result = load_json_file(test_file)

        assert result == {}

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading file that doesn't exist."""
        test_file = tmp_path / "nonexistent.json"

        result = load_json_file(test_file)

        assert result == {}

    def test_load_invalid_json(self, tmp_path):
        """Test loading file with invalid JSON."""
        test_file = tmp_path / "invalid.json"
        test_file.write_text('{ invalid json }', encoding='utf-8')

        result = load_json_file(test_file)

        assert result == {}

    def test_load_json_with_swedish_characters(self, tmp_path):
        """Test loading JSON with Swedish characters."""
        test_file = tmp_path / "swedish.json"
        data = {
            "beteckning": "2024:1",
            "rubrik": "Förordning om ändringar i äldre bestämmelser"
        }
        test_file.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

        result = load_json_file(test_file)

        assert result['rubrik'] == "Förordning om ändringar i äldre bestämmelser"

    def test_load_json_with_nested_data(self, tmp_path):
        """Test loading JSON with nested structures."""
        test_file = tmp_path / "nested.json"
        data = {
            "beteckning": "2024:1",
            "andringsforfattningar": [
                {"beteckning": "2024:100"},
                {"beteckning": "2024:200"}
            ]
        }
        test_file.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

        result = load_json_file(test_file)

        assert len(result['andringsforfattningar']) == 2


# ===========================================================================
# has_expiring_datetime Tests
# ===========================================================================

@pytest.mark.unit
class TestHasExpiringDatetime:
    """Test the has_expiring_datetime function."""

    def test_has_valid_datetime(self):
        """Test data with valid tidsbegransadDateTime."""
        data = {
            "beteckning": "2024:1",
            "tidsbegransadDateTime": "2025-12-31T23:59:59"
        }

        result = has_expiring_datetime(data)

        assert result is True

    def test_has_datetime_date_only(self):
        """Test data with date-only tidsbegransadDateTime."""
        data = {
            "beteckning": "2024:1",
            "tidsbegransadDateTime": "2025-12-31"
        }

        result = has_expiring_datetime(data)

        assert result is True

    def test_datetime_is_none(self):
        """Test data with None tidsbegransadDateTime."""
        data = {
            "beteckning": "2024:1",
            "tidsbegransadDateTime": None
        }

        result = has_expiring_datetime(data)

        assert result is False

    def test_datetime_is_empty_string(self):
        """Test data with empty string tidsbegransadDateTime."""
        data = {
            "beteckning": "2024:1",
            "tidsbegransadDateTime": ""
        }

        result = has_expiring_datetime(data)

        assert result is False

    def test_datetime_field_missing(self):
        """Test data without tidsbegransadDateTime field."""
        data = {
            "beteckning": "2024:1",
            "rubrik": "Test"
        }

        result = has_expiring_datetime(data)

        assert result is False

    def test_empty_dict(self):
        """Test empty dictionary."""
        result = has_expiring_datetime({})

        assert result is False


# ===========================================================================
# find_expiring_files Tests
# ===========================================================================

@pytest.mark.integration
class TestFindExpiringFiles:
    """Test the find_expiring_files function."""

    def test_find_files_with_expiring_datetime(self, tmp_path):
        """Test finding files with tidsbegransadDateTime."""
        # Create test files
        file1 = tmp_path / "sfs-2024-1.json"
        file1.write_text(json.dumps({
            "beteckning": "2024:1",
            "rubrik": "First regulation",
            "tidsbegransadDateTime": "2025-12-31T23:59:59"
        }, ensure_ascii=False), encoding='utf-8')

        file2 = tmp_path / "sfs-2024-2.json"
        file2.write_text(json.dumps({
            "beteckning": "2024:2",
            "rubrik": "Second regulation",
            "tidsbegransadDateTime": None
        }, ensure_ascii=False), encoding='utf-8')

        file3 = tmp_path / "sfs-2024-3.json"
        file3.write_text(json.dumps({
            "beteckning": "2024:3",
            "rubrik": "Third regulation",
            "tidsbegransadDateTime": "2026-06-30T00:00:00"
        }, ensure_ascii=False), encoding='utf-8')

        result = find_expiring_files(tmp_path)

        # Should find files 1 and 3 (both have non-null tidsbegransadDateTime)
        assert len(result) == 2
        beteckningar = [r['beteckning'] for r in result]
        assert '2024:1' in beteckningar
        assert '2024:3' in beteckningar

    def test_find_in_empty_directory(self, tmp_path):
        """Test finding files in empty directory."""
        result = find_expiring_files(tmp_path)

        assert result == []

    def test_directory_not_exists(self, tmp_path):
        """Test with directory that doesn't exist."""
        nonexistent = tmp_path / "nonexistent"

        result = find_expiring_files(nonexistent)

        assert result == []

    def test_path_is_file_not_directory(self, tmp_path):
        """Test with path that is a file, not directory."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("test", encoding='utf-8')

        result = find_expiring_files(test_file)

        assert result == []

    def test_result_includes_all_fields(self, tmp_path):
        """Test that result includes all expected fields."""
        test_file = tmp_path / "sfs-2024-1.json"
        test_file.write_text(json.dumps({
            "beteckning": "2024:1",
            "rubrik": "Test regulation",
            "tidsbegransadDateTime": "2025-12-31T23:59:59"
        }, ensure_ascii=False), encoding='utf-8')

        result = find_expiring_files(tmp_path)

        assert len(result) == 1
        assert 'filename' in result[0]
        assert 'filepath' in result[0]
        assert 'tidsbegransadDateTime' in result[0]
        assert 'beteckning' in result[0]
        assert 'rubrik' in result[0]

    def test_ignore_invalid_json_files(self, tmp_path):
        """Test that invalid JSON files are ignored."""
        # Valid file
        valid_file = tmp_path / "valid.json"
        valid_file.write_text(json.dumps({
            "beteckning": "2024:1",
            "rubrik": "Valid",
            "tidsbegransadDateTime": "2025-12-31T23:59:59"
        }, ensure_ascii=False), encoding='utf-8')

        # Invalid JSON file
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("{ invalid json }", encoding='utf-8')

        result = find_expiring_files(tmp_path)

        # Should only find the valid file
        assert len(result) == 1
        assert result[0]['beteckning'] == '2024:1'

    def test_swedish_characters_in_rubrik(self, tmp_path):
        """Test handling Swedish characters in rubrik."""
        test_file = tmp_path / "sfs-2024-1.json"
        test_file.write_text(json.dumps({
            "beteckning": "2024:1",
            "rubrik": "Förordning om ändringar i äldre bestämmelser",
            "tidsbegransadDateTime": "2025-12-31T23:59:59"
        }, ensure_ascii=False), encoding='utf-8')

        result = find_expiring_files(tmp_path)

        assert len(result) == 1
        assert "Förordning" in result[0]['rubrik']
        assert "ändringar" in result[0]['rubrik']


# ===========================================================================
# print_results Tests
# ===========================================================================

@pytest.mark.unit
class TestPrintResults:
    """Test the print_results function."""

    def test_print_empty_results(self, capsys):
        """Test printing empty results."""
        print_results([])

        captured = capsys.readouterr()
        assert "Inga filer med tidsbegränsad giltighetstid hittades" in captured.out

    def test_print_single_result(self, capsys):
        """Test printing single result."""
        results = [{
            'beteckning': '2024:1',
            'tidsbegransadDateTime': '2025-12-31T23:59:59',
            'filename': 'sfs-2024-1.json',
            'rubrik': 'Test regulation'
        }]

        print_results(results)

        captured = capsys.readouterr()
        assert '2024:1' in captured.out
        assert '2025-12-31' in captured.out
        assert 'Test regulation' in captured.out

    def test_print_multiple_results(self, capsys):
        """Test printing multiple results."""
        results = [
            {
                'beteckning': '2024:1',
                'tidsbegransadDateTime': '2025-06-01T00:00:00',
                'filename': 'sfs-2024-1.json',
                'rubrik': 'First regulation'
            },
            {
                'beteckning': '2024:2',
                'tidsbegransadDateTime': '2025-12-31T23:59:59',
                'filename': 'sfs-2024-2.json',
                'rubrik': 'Second regulation'
            }
        ]

        print_results(results)

        captured = capsys.readouterr()
        assert '2024:1' in captured.out
        assert '2024:2' in captured.out

    def test_results_sorted_by_date(self, capsys):
        """Test that results are sorted by tidsbegransadDateTime."""
        results = [
            {
                'beteckning': '2024:2',
                'tidsbegransadDateTime': '2025-12-31T23:59:59',
                'filename': 'sfs-2024-2.json',
                'rubrik': 'Later'
            },
            {
                'beteckning': '2024:1',
                'tidsbegransadDateTime': '2025-01-01T00:00:00',
                'filename': 'sfs-2024-1.json',
                'rubrik': 'Earlier'
            }
        ]

        print_results(results)

        captured = capsys.readouterr()
        # Earlier date should appear first in output
        earlier_pos = captured.out.find('2025-01-01')
        later_pos = captured.out.find('2025-12-31')
        assert earlier_pos < later_pos

    def test_date_format_extraction(self, capsys):
        """Test that date is extracted from datetime string."""
        results = [{
            'beteckning': '2024:1',
            'tidsbegransadDateTime': '2025-12-31T23:59:59',
            'filename': 'test.json',
            'rubrik': 'Test'
        }]

        print_results(results)

        captured = capsys.readouterr()
        # Should show date part only
        assert '2025-12-31' in captured.out
        # Should not show the time part in the main output
        assert 'T23:59:59' not in captured.out or '23:59:59' not in captured.out

    def test_long_rubrik_truncation(self, capsys):
        """Test that long rubriks are truncated."""
        long_rubrik = "A" * 100  # Very long title
        results = [{
            'beteckning': '2024:1',
            'tidsbegransadDateTime': '2025-12-31T23:59:59',
            'filename': 'test.json',
            'rubrik': long_rubrik
        }]

        print_results(results)

        captured = capsys.readouterr()
        # Should show truncated version with ellipsis
        assert '...' in captured.out


# ===========================================================================
# save_results_to_file Tests
# ===========================================================================

@pytest.mark.integration
class TestSaveResultsToFile:
    """Test the save_results_to_file function."""

    def test_save_single_result(self, tmp_path):
        """Test saving single result to file."""
        output_file = tmp_path / "output.txt"
        results = [{
            'beteckning': '2024:1',
            'tidsbegransadDateTime': '2025-12-31T23:59:59',
            'filename': 'sfs-2024-1.json',
            'filepath': '/path/to/sfs-2024-1.json',
            'rubrik': 'Test regulation'
        }]

        save_results_to_file(results, str(output_file))

        assert output_file.exists()
        content = output_file.read_text(encoding='utf-8')
        assert '2024:1' in content
        assert 'Test regulation' in content
        assert '2025-12-31T23:59:59' in content

    def test_save_multiple_results(self, tmp_path):
        """Test saving multiple results."""
        output_file = tmp_path / "output.txt"
        results = [
            {
                'beteckning': '2024:1',
                'tidsbegransadDateTime': '2025-01-01T00:00:00',
                'filename': 'sfs-2024-1.json',
                'filepath': '/path/to/sfs-2024-1.json',
                'rubrik': 'First'
            },
            {
                'beteckning': '2024:2',
                'tidsbegransadDateTime': '2025-12-31T23:59:59',
                'filename': 'sfs-2024-2.json',
                'filepath': '/path/to/sfs-2024-2.json',
                'rubrik': 'Second'
            }
        ]

        save_results_to_file(results, str(output_file))

        content = output_file.read_text(encoding='utf-8')
        assert '2024:1' in content
        assert '2024:2' in content

    def test_save_empty_results(self, tmp_path):
        """Test saving empty results (should not create file)."""
        output_file = tmp_path / "output.txt"

        save_results_to_file([], str(output_file))

        # File should not be created for empty results
        assert not output_file.exists()

    def test_save_sorted_by_date(self, tmp_path):
        """Test that saved results are sorted by date."""
        output_file = tmp_path / "output.txt"
        results = [
            {
                'beteckning': '2024:2',
                'tidsbegransadDateTime': '2025-12-31T23:59:59',
                'filename': 'sfs-2024-2.json',
                'filepath': '/path/to/sfs-2024-2.json',
                'rubrik': 'Later'
            },
            {
                'beteckning': '2024:1',
                'tidsbegransadDateTime': '2025-01-01T00:00:00',
                'filename': 'sfs-2024-1.json',
                'filepath': '/path/to/sfs-2024-1.json',
                'rubrik': 'Earlier'
            }
        ]

        save_results_to_file(results, str(output_file))

        content = output_file.read_text(encoding='utf-8')
        # Earlier date should appear before later date in file
        earlier_pos = content.find('2025-01-01')
        later_pos = content.find('2025-12-31')
        assert earlier_pos < later_pos

    def test_save_with_swedish_characters(self, tmp_path):
        """Test saving results with Swedish characters."""
        output_file = tmp_path / "output.txt"
        results = [{
            'beteckning': '2024:1',
            'tidsbegransadDateTime': '2025-12-31T23:59:59',
            'filename': 'sfs-2024-1.json',
            'filepath': '/path/to/sfs-2024-1.json',
            'rubrik': 'Förordning om ändringar i äldre bestämmelser'
        }]

        save_results_to_file(results, str(output_file))

        content = output_file.read_text(encoding='utf-8')
        assert 'Förordning' in content
        assert 'ändringar' in content
        assert 'äldre' in content

    def test_file_includes_metadata(self, tmp_path):
        """Test that file includes count and header."""
        output_file = tmp_path / "output.txt"
        results = [{
            'beteckning': '2024:1',
            'tidsbegransadDateTime': '2025-12-31T23:59:59',
            'filename': 'test.json',
            'filepath': '/path/to/test.json',
            'rubrik': 'Test'
        }]

        save_results_to_file(results, str(output_file))

        content = output_file.read_text(encoding='utf-8')
        assert 'Totalt antal filer: 1' in content


# ===========================================================================
# Integration Tests
# ===========================================================================

@pytest.mark.integration
class TestFindExpiringDocsIntegration:
    """Integration tests for complete workflow."""

    def test_complete_workflow(self, tmp_path, capsys):
        """Test complete workflow: find files, print, and save."""
        # Create test JSON files
        file1 = tmp_path / "sfs-2024-1.json"
        file1.write_text(json.dumps({
            "beteckning": "2024:1",
            "rubrik": "First regulation",
            "tidsbegransadDateTime": "2025-12-31T23:59:59"
        }, ensure_ascii=False), encoding='utf-8')

        file2 = tmp_path / "sfs-2024-2.json"
        file2.write_text(json.dumps({
            "beteckning": "2024:2",
            "rubrik": "No expiry",
            "tidsbegransadDateTime": None
        }, ensure_ascii=False), encoding='utf-8')

        # Find expiring files
        results = find_expiring_files(tmp_path)
        assert len(results) == 1

        # Print results
        print_results(results)
        captured = capsys.readouterr()
        assert '2024:1' in captured.out

        # Save to file
        output_file = tmp_path / "results.txt"
        save_results_to_file(results, str(output_file))
        assert output_file.exists()

    def test_mixed_valid_invalid_files(self, tmp_path):
        """Test handling mix of valid and invalid files."""
        # Valid expiring file
        (tmp_path / "valid.json").write_text(json.dumps({
            "beteckning": "2024:1",
            "rubrik": "Valid",
            "tidsbegransadDateTime": "2025-12-31T23:59:59"
        }), encoding='utf-8')

        # Invalid JSON
        (tmp_path / "invalid.json").write_text("{ invalid }", encoding='utf-8')

        # No expiry
        (tmp_path / "no-expiry.json").write_text(json.dumps({
            "beteckning": "2024:2",
            "rubrik": "No expiry",
            "tidsbegransadDateTime": None
        }), encoding='utf-8')

        # Not a JSON file
        (tmp_path / "readme.txt").write_text("Not JSON", encoding='utf-8')

        results = find_expiring_files(tmp_path)

        # Should only find the valid expiring file
        assert len(results) == 1
        assert results[0]['beteckning'] == '2024:1'


# ===========================================================================
# Edge Cases
# ===========================================================================

@pytest.mark.unit
class TestFindExpiringDocsEdgeCases:
    """Test edge cases for finding expiring documents."""

    def test_very_long_rubrik(self, tmp_path):
        """Test handling very long rubrik."""
        long_rubrik = "A" * 1000
        test_file = tmp_path / "test.json"
        test_file.write_text(json.dumps({
            "beteckning": "2024:1",
            "rubrik": long_rubrik,
            "tidsbegransadDateTime": "2025-12-31T23:59:59"
        }), encoding='utf-8')

        result = find_expiring_files(tmp_path)

        assert len(result) == 1
        assert len(result[0]['rubrik']) == 1000

    def test_special_characters_in_filename(self, tmp_path):
        """Test handling special characters in filename."""
        test_file = tmp_path / "sfs-2024-100.json"
        test_file.write_text(json.dumps({
            "beteckning": "2024:100",
            "rubrik": "Test",
            "tidsbegransadDateTime": "2025-12-31T23:59:59"
        }), encoding='utf-8')

        result = find_expiring_files(tmp_path)

        assert len(result) == 1
        assert result[0]['filename'] == "sfs-2024-100.json"

    def test_multiple_expiry_dates_sorting(self, tmp_path):
        """Test correct sorting of multiple expiry dates."""
        files_data = [
            ("sfs-2024-3.json", "2024:3", "2026-12-31T23:59:59"),
            ("sfs-2024-1.json", "2024:1", "2025-01-01T00:00:00"),
            ("sfs-2024-2.json", "2024:2", "2025-06-30T12:00:00"),
        ]

        for filename, beteckning, datetime_val in files_data:
            file_path = tmp_path / filename
            file_path.write_text(json.dumps({
                "beteckning": beteckning,
                "rubrik": f"Regulation {beteckning}",
                "tidsbegransadDateTime": datetime_val
            }), encoding='utf-8')

        results = find_expiring_files(tmp_path)

        assert len(results) == 3
        # Results should exist (sorting tested in print_results)
        beteckningar = [r['beteckning'] for r in results]
        assert '2024:1' in beteckningar
        assert '2024:2' in beteckningar
        assert '2024:3' in beteckningar
