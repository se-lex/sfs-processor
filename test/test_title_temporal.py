#!/usr/bin/env python3
"""Test script for title_temporal function."""

import pytest
from temporal.title_temporal import title_temporal


@pytest.mark.unit
def test_title_before_transition_date(sample_temporal_title):
    """Test that the old title is returned for dates before transition."""
    date_before = "2025-07-14"
    result = title_temporal(sample_temporal_title, date_before)

    # Should not contain temporal markers in output
    assert "/Rubriken" not in result, \
        f"Result should not contain temporal markers: {result}"

    # Old title: "...på hälso- och sjukvårdens fastigheter"
    assert "hälso- och sjukvårdens fastigheter" in result, \
        f"Old title should contain old wording: {result}"

    # Should NOT have the new wording
    assert "fastigheter för hälso- och sjukvård" not in result, \
        f"Old title should not contain new wording: {result}"


@pytest.mark.unit
def test_title_on_transition_date(sample_temporal_title):
    """Test that the new title is returned on the transition date."""
    date_on = "2025-07-15"
    result = title_temporal(sample_temporal_title, date_on)

    # Should not contain temporal markers in output
    assert "/Rubriken" not in result, \
        f"Result should not contain temporal markers: {result}"

    # New title: "...på fastigheter för hälso- och sjukvård"
    assert "fastigheter för hälso- och sjukvård" in result, \
        f"New title should contain new wording: {result}"

    # Should NOT have the old wording
    assert "hälso- och sjukvårdens fastigheter" not in result, \
        f"New title should not contain old wording: {result}"


@pytest.mark.unit
def test_title_after_transition_date(sample_temporal_title):
    """Test that the new title is returned for dates after transition."""
    date_after = "2025-07-16"
    result = title_temporal(sample_temporal_title, date_after)

    # Should not contain temporal markers in output
    assert "/Rubriken" not in result, \
        f"Result should not contain temporal markers: {result}"

    # Should have the new wording
    assert "fastigheter för hälso- och sjukvård" in result, \
        f"New title should contain new wording: {result}"

    # Should NOT have the old wording
    assert "hälso- och sjukvårdens fastigheter" not in result, \
        f"New title should not contain old wording: {result}"


@pytest.mark.unit
def test_title_no_temporal_markers():
    """Test with a simple title without temporal markers."""
    simple_title = "Simple title without temporal markers"
    result = title_temporal(simple_title, "2025-01-01")

    # Should return the title unchanged
    assert result == simple_title, f"Simple title should be unchanged: {result}"


@pytest.mark.unit
def test_title_with_none():
    """Test that None input is handled gracefully."""
    result = title_temporal(None, "2025-01-01")

    # Should return empty string
    assert result == "", f"None should return empty string: {result}"


@pytest.mark.unit
def test_title_with_empty_string():
    """Test that empty string is handled gracefully."""
    result = title_temporal("", "2025-01-01")

    # Should return empty string
    assert result == "", f"Empty string should be returned: {result}"


@pytest.mark.unit
def test_title_with_invalid_date(sample_temporal_title):
    """Test that invalid date is handled gracefully."""
    result = title_temporal(sample_temporal_title, "invalid-date")

    # Should return something (implementation dependent)
    # At minimum, should not crash
    assert result is not None, "Should handle invalid date without crashing"
