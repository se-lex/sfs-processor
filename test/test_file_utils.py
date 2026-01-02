#!/usr/bin/env python3
"""
Tests for file utility functions.
"""

import pytest
from pathlib import Path
from util.file_utils import filter_json_files, read_file_content, save_to_disk


# ===========================================================================
# filter_json_files Tests
# ===========================================================================

@pytest.mark.unit
class TestFilterJsonFiles:
    """Test the filter_json_files function."""

    def test_filter_by_year(self, tmp_path):
        """Test filtering JSON files by year."""
        # Create test JSON files
        (tmp_path / "sfs-2024-1.json").touch()
        (tmp_path / "sfs-2024-100.json").touch()
        (tmp_path / "sfs-2023-50.json").touch()
        (tmp_path / "sfs-2025-1.json").touch()

        json_files = list(tmp_path.glob("*.json"))
        result = filter_json_files(json_files, "2024")

        assert len(result) == 2
        filenames = [f.name for f in result]
        assert "sfs-2024-1.json" in filenames
        assert "sfs-2024-100.json" in filenames

    def test_filter_by_beteckning(self, tmp_path):
        """Test filtering JSON files by SFS beteckning (YYYY:NNN)."""
        # Create test JSON files
        (tmp_path / "sfs-2024-1.json").touch()
        (tmp_path / "sfs-2024-100.json").touch()
        (tmp_path / "sfs-2023-50.json").touch()

        json_files = list(tmp_path.glob("*.json"))
        # Filter for beteckning 2024:100 (filename format: sfs-2024-100.json)
        # Note: 2024:1 would match both sfs-2024-1.json and sfs-2024-100.json (partial match)
        result = filter_json_files(json_files, "2024:100")

        assert len(result) == 1
        assert result[0].name == "sfs-2024-100.json"

    def test_filter_multiple_criteria(self, tmp_path):
        """Test filtering with multiple comma-separated criteria."""
        # Create test JSON files
        (tmp_path / "sfs-2024-1.json").touch()
        (tmp_path / "sfs-2024-100.json").touch()
        (tmp_path / "sfs-2023-50.json").touch()
        (tmp_path / "sfs-2025-1.json").touch()

        json_files = list(tmp_path.glob("*.json"))
        # Filter for multiple years
        result = filter_json_files(json_files, "2024, 2025")

        assert len(result) == 3  # All 2024 and 2025 files
        filenames = [f.name for f in result]
        assert "sfs-2023-50.json" not in filenames

    def test_filter_with_partial_match(self, tmp_path):
        """Test filtering with partial filename match."""
        # Create test JSON files
        (tmp_path / "sfs-2024-925.json").touch()
        (tmp_path / "sfs-2024-92.json").touch()
        (tmp_path / "sfs-2024-100.json").touch()

        json_files = list(tmp_path.glob("*.json"))
        # Filter for partial match "925"
        result = filter_json_files(json_files, "sfs-2024-925")

        assert len(result) == 1
        assert result[0].name == "sfs-2024-925.json"

    def test_filter_empty_criteria(self, tmp_path):
        """Test that empty filter criteria returns all files."""
        # Create test JSON files
        (tmp_path / "file1.json").touch()
        (tmp_path / "file2.json").touch()

        json_files = list(tmp_path.glob("*.json"))
        result = filter_json_files(json_files, "")

        assert len(result) == 2

    def test_filter_no_matches(self, tmp_path):
        """Test filtering with criteria that matches no files."""
        # Create test JSON files
        (tmp_path / "sfs-2024-1.json").touch()
        (tmp_path / "sfs-2024-2.json").touch()

        json_files = list(tmp_path.glob("*.json"))
        result = filter_json_files(json_files, "2025")

        assert len(result) == 0

    def test_filter_empty_file_list(self):
        """Test filtering an empty file list."""
        result = filter_json_files([], "2024")
        assert result == []

    def test_filter_with_whitespace(self, tmp_path):
        """Test that whitespace in criteria is handled properly."""
        # Create test JSON files
        (tmp_path / "sfs-2024-1.json").touch()
        (tmp_path / "sfs-2023-1.json").touch()

        json_files = list(tmp_path.glob("*.json"))
        # Filter with extra whitespace
        result = filter_json_files(json_files, " 2024 , 2023 ")

        assert len(result) == 2


# ===========================================================================
# read_file_content Tests
# ===========================================================================

@pytest.mark.unit
class TestReadFileContent:
    """Test the read_file_content function."""

    def test_read_valid_file(self, tmp_path):
        """Test reading a valid text file."""
        file_path = tmp_path / "test.txt"
        expected_content = "Test content with Swedish chars: åäö ÅÄÖ"
        file_path.write_text(expected_content, encoding='utf-8')

        result = read_file_content(file_path)
        assert result == expected_content

    def test_read_empty_file(self, tmp_path):
        """Test reading an empty file."""
        file_path = tmp_path / "empty.txt"
        file_path.write_text("", encoding='utf-8')

        result = read_file_content(file_path)
        assert result == ""

    def test_read_file_with_newlines(self, tmp_path):
        """Test reading file with multiple lines."""
        file_path = tmp_path / "multiline.txt"
        expected_content = "Line 1\nLine 2\nLine 3"
        file_path.write_text(expected_content, encoding='utf-8')

        result = read_file_content(file_path)
        assert result == expected_content
        assert result.count('\n') == 2

    def test_read_nonexistent_file(self, tmp_path):
        """Test that reading nonexistent file raises IOError."""
        file_path = tmp_path / "nonexistent.txt"

        with pytest.raises(IOError) as exc_info:
            read_file_content(file_path)

        assert "Fel vid läsning av" in str(exc_info.value)

    def test_read_file_with_swedish_characters(self, tmp_path):
        """Test reading file with Swedish characters (UTF-8 encoding)."""
        file_path = tmp_path / "swedish.txt"
        expected_content = "Förordning om ändringar i äldre bestämmelser"
        file_path.write_text(expected_content, encoding='utf-8')

        result = read_file_content(file_path)
        assert result == expected_content
        assert "Förordning" in result


# ===========================================================================
# save_to_disk Tests
# ===========================================================================

@pytest.mark.unit
class TestSaveToDisk:
    """Test the save_to_disk function."""

    def test_save_valid_content(self, tmp_path):
        """Test saving valid content to a file."""
        file_path = tmp_path / "output.txt"
        content = "Test content to save"

        save_to_disk(file_path, content)

        # Verify file was created and contains correct content
        assert file_path.exists()
        assert file_path.read_text(encoding='utf-8') == content

    def test_save_empty_content(self, tmp_path):
        """Test saving empty content to a file."""
        file_path = tmp_path / "empty.txt"

        save_to_disk(file_path, "")

        assert file_path.exists()
        assert file_path.read_text(encoding='utf-8') == ""

    def test_save_with_swedish_characters(self, tmp_path):
        """Test saving content with Swedish characters."""
        file_path = tmp_path / "swedish.txt"
        content = "Innehåll med svenska tecken: åäö ÅÄÖ"

        save_to_disk(file_path, content)

        assert file_path.exists()
        saved_content = file_path.read_text(encoding='utf-8')
        assert saved_content == content
        assert "åäö" in saved_content

    def test_save_multiline_content(self, tmp_path):
        """Test saving multi-line content."""
        file_path = tmp_path / "multiline.txt"
        content = "Line 1\nLine 2\nLine 3"

        save_to_disk(file_path, content)

        saved_content = file_path.read_text(encoding='utf-8')
        assert saved_content == content
        assert saved_content.count('\n') == 2

    def test_save_overwrites_existing_file(self, tmp_path):
        """Test that saving overwrites existing file content."""
        file_path = tmp_path / "overwrite.txt"
        file_path.write_text("Old content", encoding='utf-8')

        new_content = "New content"
        save_to_disk(file_path, new_content)

        assert file_path.read_text(encoding='utf-8') == new_content
        assert "Old content" not in file_path.read_text(encoding='utf-8')

    def test_save_creates_file_if_not_exists(self, tmp_path):
        """Test that save_to_disk creates file if it doesn't exist."""
        file_path = tmp_path / "new_file.txt"
        assert not file_path.exists()

        save_to_disk(file_path, "New content")

        assert file_path.exists()

    def test_save_to_invalid_path(self, tmp_path):
        """Test saving to invalid path (should handle gracefully)."""
        # Try to save to a directory that doesn't exist
        invalid_path = tmp_path / "nonexistent_dir" / "file.txt"

        # The function prints error but doesn't raise exception
        # Just verify it doesn't crash
        save_to_disk(invalid_path, "content")
        # File should not be created
        assert not invalid_path.exists()


# ===========================================================================
# Integration Tests
# ===========================================================================

@pytest.mark.integration
class TestFileUtilsIntegration:
    """Integration tests combining multiple file utilities."""

    def test_save_and_read_roundtrip(self, tmp_path):
        """Test saving content and reading it back."""
        file_path = tmp_path / "roundtrip.txt"
        original_content = "Original content with åäö"

        # Save content
        save_to_disk(file_path, original_content)

        # Read it back
        read_content = read_file_content(file_path)

        assert read_content == original_content

    def test_filter_and_read_files(self, tmp_path):
        """Test filtering files and reading their content."""
        # Create test files with content
        (tmp_path / "sfs-2024-1.json").write_text('{"beteckning": "2024:1"}')
        (tmp_path / "sfs-2024-2.json").write_text('{"beteckning": "2024:2"}')
        (tmp_path / "sfs-2023-1.json").write_text('{"beteckning": "2023:1"}')

        # Filter for 2024 files
        json_files = list(tmp_path.glob("*.json"))
        filtered = filter_json_files(json_files, "2024")

        # Read each filtered file
        assert len(filtered) == 2
        for file_path in filtered:
            content = read_file_content(file_path)
            assert '"beteckning": "2024:' in content
