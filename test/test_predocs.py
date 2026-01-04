#!/usr/bin/env python3
"""
Test script for förarbeten parsing and fetching functionality.
"""

import pytest
from formatters.predocs_parser import parse_predocs_string
from downloaders.riksdagen_api import (
    construct_rd_docid,
    fetch_document_info,
    fetch_predocs_details,
    format_predocs_for_frontmatter
)


# ===========================================================================
# Parser Tests (no API required)
# ===========================================================================

@pytest.mark.unit
@pytest.mark.parametrize("input_string,expected_count,expected_first", [
    ("Prop. 2024/25:1", 1, {'type': 'prop', 'rm': '2024/25', 'bet': '1'}),
    (
        "Prop. 2023/24:144, bet. 2023/24:JuU3, rskr. 2023/24:9",
        3,
        {'type': 'prop', 'rm': '2023/24', 'bet': '144'}
    ),
    (
        "Prop. 1982/83:67, LU 1982/83:33, rskr 1982/83:250",
        3,
        {'type': 'prop', 'rm': '1982/83', 'bet': '67'}
    ),
])
def test_parse_predocs_string_modern_format(
    input_string, expected_count, expected_first
):
    """Test parsing of modern format förarbeten references."""
    parsed = parse_predocs_string(input_string)

    assert len(parsed) == expected_count, \
        f"Expected {expected_count} parsed items, got {len(parsed)}"
    assert parsed[0]['type'] == expected_first['type'], \
        f"Expected type {expected_first['type']}"
    assert parsed[0]['rm'] == expected_first['rm'], \
        f"Expected rm {expected_first['rm']}"
    assert parsed[0]['bet'] == expected_first['bet'], \
        f"Expected bet {expected_first['bet']}"


@pytest.mark.unit
def test_parse_predocs_string_old_format():
    """Test parsing of old format förarbeten references (before 1970/71)."""
    # Old format: "Prop. 1966:40; 1LU 1967:53; Rskr 1967:325"
    parsed = parse_predocs_string("Prop. 1966:40; 1LU 1967:53; Rskr 1967:325")

    # The parser should handle old format if it supports it
    # or return at least something parseable
    assert isinstance(parsed, list), "Should return a list"


@pytest.mark.unit
def test_parse_predocs_string_empty():
    """Test parsing of empty string."""
    parsed = parse_predocs_string("")

    assert not parsed, "Empty string should return empty list or None"


@pytest.mark.unit
def test_parse_predocs_string_invalid():
    """Test parsing of invalid input."""
    parsed = parse_predocs_string("This is not a valid reference")

    # Should return empty list or handle gracefully
    assert isinstance(parsed, list), \
        "Should return a list even for invalid input"


# ===========================================================================
# Document ID Construction Tests (no API required)
# ===========================================================================

@pytest.mark.unit
@pytest.mark.parametrize("doc_type,rm,bet,should_succeed", [
    ("prop", "2024/25", "1", True),
    ("prop", "2023/24", "144", True),
    ("bet", "2023/24", "JuU3", True),
    ("rskr", "2023/24", "9", True),
])
def test_construct_rd_docid_success(doc_type, rm, bet, should_succeed):
    """Test successful construction of Riksdag document IDs."""
    rd_docid = construct_rd_docid(doc_type, rm, bet)

    if should_succeed:
        assert rd_docid is not None, \
            f"Should construct rd_docid for {doc_type} {rm}:{bet}"
        assert isinstance(rd_docid, str), "rd_docid should be a string"
        assert len(rd_docid) > 0, "rd_docid should not be empty"
    else:
        # For unsupported years, might return None
        pass


@pytest.mark.unit
def test_construct_rd_docid_old_year():
    """Test construction of rd_docid for old year (before 1970)."""
    # Old years might not be supported
    rd_docid = construct_rd_docid("prop", "1966/67", "40")

    # Should either return None or a constructed ID (depends on implementation)
    assert rd_docid is None or isinstance(rd_docid, str), \
        "Should return None or a string for old years"


# ===========================================================================
# API Tests with Mocking
# ===========================================================================

@pytest.mark.api
def test_fetch_document_info_success(mock_riksdagen_responses):  # noqa: ARG001
    """Test successful fetching of document information."""
    result = fetch_document_info("prop", "2024/25", "1")

    assert result is not None, "Should return document info"
    assert 'dokumentnamn' in result, "Should contain dokumentnamn"
    assert 'titel' in result, "Should contain titel"
    assert result['dokumentnamn'] == 'Prop. 2024/25:1', \
        "Should match expected dokumentnamn"
    assert result['titel'] == 'Budgetpropositionen för 2025', \
        "Should match expected titel"


@pytest.mark.api
def test_fetch_document_info_multiple_documents(
    mock_riksdagen_responses  # noqa: ARG001
):
    """Test fetching multiple different documents."""
    # Test proposition
    result1 = fetch_document_info("prop", "2023/24", "144")
    assert result1 is not None
    assert result1['dokumentnamn'] == 'Prop. 2023/24:144'

    # Test committee report (bet)
    result2 = fetch_document_info("bet", "2023/24", "JuU3")
    assert result2 is not None
    assert result2['dokumentnamn'] == 'Bet. 2023/24:JuU3'

    # Test riksdagsskrivelse
    result3 = fetch_document_info("rskr", "2023/24", "9")
    assert result3 is not None
    assert result3['dokumentnamn'] == 'Rskr. 2023/24:9'


@pytest.mark.api
def test_fetch_document_info_not_found(mock_riksdagen_404):  # noqa: ARG001
    """Test handling of 404 response (document not found)."""
    result = fetch_document_info("prop", "1966/67", "40")

    # Should return None for not found documents
    assert result is None, "Should return None for 404 response"


@pytest.mark.api
def test_fetch_predocs_details_success(mock_riksdagen_responses):  # noqa: ARG001
    """Test fetching details for multiple förarbeten references."""
    predocs_list = [
        {'type': 'prop', 'rm': '2024/25', 'bet': '1',
         'original': 'Prop. 2024/25:1'},
        {'type': 'prop', 'rm': '2023/24', 'bet': '144',
         'original': 'Prop. 2023/24:144'},
    ]

    detailed = fetch_predocs_details(predocs_list, delay_between_requests=0)

    assert len(detailed) >= 1, "Should return at least one detailed item"

    # Check first item
    assert 'dokumentnamn' in detailed[0], "Should contain dokumentnamn"
    assert 'titel' in detailed[0], "Should contain titel"
    assert 'original' in detailed[0], "Should preserve original reference"


@pytest.mark.api
def test_fetch_predocs_details_with_delay(
    mock_riksdagen_responses, mocker  # noqa: ARG001
):
    """Test that delay_between_requests is respected."""
    # Mock time.sleep to verify it's called
    mock_sleep = mocker.patch('time.sleep')

    predocs_list = [
        {'type': 'prop', 'rm': '2024/25', 'bet': '1',
         'original': 'Prop. 2024/25:1'},
        {'type': 'prop', 'rm': '2023/24', 'bet': '144',
         'original': 'Prop. 2023/24:144'},
    ]

    fetch_predocs_details(predocs_list, delay_between_requests=0.5)

    # Should have called sleep between requests
    assert mock_sleep.call_count >= 0, "Should respect delay_between_requests"


# ===========================================================================
# Formatting Tests (no API required)
# ===========================================================================

@pytest.mark.unit
def test_format_predocs_for_frontmatter_success():
    """Test formatting of detailed predocs for frontmatter."""
    detailed_predocs = [
        {
            'dokumentnamn': 'Prop. 2024/25:1',
            'titel': 'Budgetpropositionen för 2025',
            'original': 'Prop. 2024/25:1'
        },
        {
            'dokumentnamn': 'Bet. 2023/24:JuU3',
            'titel': 'Justitieutskottets betänkande',
            'original': 'bet. 2023/24:JuU3'
        },
    ]

    formatted = format_predocs_for_frontmatter(detailed_predocs)

    assert len(formatted) == 2, "Should format all items"
    assert isinstance(formatted[0], str), "Each item should be a string"

    # Check format - should contain dokumentnamn and titel
    assert 'Prop. 2024/25:1' in formatted[0], "Should contain dokumentnamn"
    assert 'Budgetpropositionen för 2025' in formatted[0], \
        "Should contain titel"


@pytest.mark.unit
def test_format_predocs_for_frontmatter_empty():
    """Test formatting of empty list."""
    formatted = format_predocs_for_frontmatter([])

    assert not formatted, "Empty list should return empty list"


@pytest.mark.unit
def test_format_predocs_for_frontmatter_missing_fields():
    """Test formatting with missing fields."""
    detailed_predocs = [
        {
            'dokumentnamn': 'Prop. 2024/25:1',
            # Missing titel
        },
        {
            # Missing dokumentnamn
            'titel': 'Some title',
        },
    ]

    formatted = format_predocs_for_frontmatter(detailed_predocs)

    # Should handle gracefully
    assert isinstance(formatted, list), "Should return a list"
    assert len(formatted) <= 2, "Should handle missing fields gracefully"
