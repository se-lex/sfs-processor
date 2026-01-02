#!/usr/bin/env python3
"""
Tests for datetime utility functions.
"""

import pytest
from util.datetime_utils import format_datetime, format_datetime_for_git, MIN_GIT_YEAR


# ===========================================================================
# format_datetime Tests
# ===========================================================================

@pytest.mark.unit
class TestFormatDatetime:
    """Test the format_datetime function."""

    def test_format_datetime_with_time(self):
        """Test formatting datetime with time component (should strip time)."""
        result = format_datetime("2024-03-15T14:30:00")
        assert result == "2024-03-15"

    def test_format_datetime_date_only(self):
        """Test formatting date without time component."""
        result = format_datetime("2024-03-15")
        assert result == "2024-03-15"

    def test_format_datetime_with_timezone(self):
        """Test formatting datetime with timezone (should strip it)."""
        result = format_datetime("2024-03-15T14:30:00+01:00")
        assert result == "2024-03-15"

    def test_format_datetime_none(self):
        """Test that None input returns None."""
        result = format_datetime(None)
        assert result is None

    def test_format_datetime_empty_string(self):
        """Test that empty string returns None."""
        result = format_datetime("")
        assert result is None

    def test_format_datetime_invalid_format(self):
        """Test invalid datetime format returns original string."""
        invalid_input = "not-a-valid-date"
        result = format_datetime(invalid_input)
        assert result == invalid_input


# ===========================================================================
# format_datetime_for_git Tests
# ===========================================================================

@pytest.mark.unit
class TestFormatDatetimeForGit:
    """Test the format_datetime_for_git function."""

    def test_valid_datetime_with_time(self):
        """Test formatting valid datetime with time component."""
        result = format_datetime_for_git("2024-03-15T14:30:00")
        assert result == "2024-03-15T14:30:00"

    def test_datetime_with_z_timezone(self):
        """Test formatting datetime with Z (Zulu/UTC) timezone."""
        result = format_datetime_for_git("2024-03-15T14:30:00Z")
        assert result == "2024-03-15T14:30:00"

    def test_date_only_adds_midnight_time(self):
        """Test that date without time gets midnight time added."""
        result = format_datetime_for_git("2024-03-15")
        assert result == "2024-03-15T00:00:00"

    def test_date_before_min_git_year(self):
        """Test that dates before MIN_GIT_YEAR are clamped to MIN_GIT_YEAR."""
        # 1969 < MIN_GIT_YEAR (1980)
        result = format_datetime_for_git("1969-01-01")
        assert result == f"{MIN_GIT_YEAR}-01-01T00:00:00"
        assert result.startswith("1980")

    def test_date_before_min_git_year_with_time(self):
        """Test that datetime before MIN_GIT_YEAR is clamped (with time)."""
        result = format_datetime_for_git("1975-06-15T12:30:00")
        assert result == f"{MIN_GIT_YEAR}-01-01T00:00:00"

    def test_very_old_date(self):
        """Test very old dates (e.g., 1800s) are clamped to MIN_GIT_YEAR."""
        result = format_datetime_for_git("1850-01-01")
        assert result == f"{MIN_GIT_YEAR}-01-01T00:00:00"

    def test_none_value(self):
        """Test that None input returns None."""
        result = format_datetime_for_git(None)
        assert result is None

    def test_empty_string(self):
        """Test that empty string returns None."""
        result = format_datetime_for_git("")
        assert result is None

    def test_invalid_format_fallback(self):
        """Test invalid datetime format raises ValueError."""
        # If it's not a valid ISO format and can't be parsed, raises ValueError
        with pytest.raises(ValueError):
            format_datetime_for_git("not-a-date")

    def test_date_at_min_git_year_boundary(self):
        """Test date exactly at MIN_GIT_YEAR boundary."""
        result = format_datetime_for_git(f"{MIN_GIT_YEAR}-01-01")
        assert result == f"{MIN_GIT_YEAR}-01-01T00:00:00"

    def test_date_one_year_before_min(self):
        """Test date one year before MIN_GIT_YEAR."""
        result = format_datetime_for_git(f"{MIN_GIT_YEAR - 1}-12-31")
        assert result == f"{MIN_GIT_YEAR}-01-01T00:00:00"


# ===========================================================================
# Edge Cases
# ===========================================================================

@pytest.mark.unit
class TestDatetimeEdgeCases:
    """Test edge cases for datetime utilities."""

    def test_leap_year_date(self):
        """Test handling of leap year dates."""
        result = format_datetime("2024-02-29")
        assert result == "2024-02-29"

        result_git = format_datetime_for_git("2024-02-29T23:59:59")
        assert result_git == "2024-02-29T23:59:59"

    def test_end_of_year_date(self):
        """Test handling of end-of-year dates."""
        result = format_datetime_for_git("2024-12-31T23:59:59")
        assert result == "2024-12-31T23:59:59"

    def test_various_datetime_formats(self):
        """Test various valid ISO datetime formats."""
        test_cases = [
            ("2024-01-01", "2024-01-01"),
            ("2024-06-15T12:00:00", "2024-06-15"),
            ("2024-12-31T23:59:59Z", "2024-12-31"),
        ]

        for input_dt, expected in test_cases:
            result = format_datetime(input_dt)
            assert result == expected
