#!/usr/bin/env python3
"""
Test script for law name linking functionality.
"""

import pytest
from formatters.apply_links import apply_law_name_links


@pytest.mark.unit
@pytest.mark.parametrize("input_text,expected_pattern", [
    ('3 kap. 3 § dataskyddslagen', '[3 kap. 3 § dataskyddslagen]'),
    ('8 kap. 7 § regeringsformen', '[8 kap. 7 § regeringsformen]'),
    ('2 kap. 25 § skollagen', '[2 kap. 25 § skollagen]'),
    (
        '29 kap. 14 § och offentlighets- och sekretesslagen',
        '[29 kap. 14 § och offentlighets- och sekretesslagen]'
    ),
    ('15 kap. 2 § sekretesslagen', '[15 kap. 2 § sekretesslagen]'),
])
def test_law_name_linking_success(input_text, expected_pattern):
    """Test that law name references are correctly converted to links."""
    result = apply_law_name_links(input_text)

    # Verify the expected pattern is in the result
    assert expected_pattern in result, \
        f"Expected pattern '{expected_pattern}' not found in result: {result}"

    # Verify that the text was actually modified (a link was added)
    assert result != input_text, f"Text was not modified: {result}"


@pytest.mark.unit
@pytest.mark.parametrize("input_text", [
    'This is plain text without any law references',
    'Just some random text',
    '123 numbers only',
])
def test_law_name_no_linking(input_text):
    """Test that text without law references is left unchanged."""
    result = apply_law_name_links(input_text)

    # Text without law references should remain unchanged
    assert result == input_text, f"Text should not be modified: {result}"


@pytest.mark.unit
def test_law_name_linking_preserves_context():
    """Test that linking preserves surrounding context."""
    input_text = "Se 3 kap. 3 § dataskyddslagen för mer information"
    result = apply_law_name_links(input_text)

    # Should contain the link
    assert '[3 kap. 3 § dataskyddslagen]' in result

    # Should preserve surrounding text
    assert 'Se' in result
    assert 'för mer information' in result
