#!/usr/bin/env python3
"""Test temporal title processing in the main SFS processor."""

import pytest
from pathlib import Path
from sfs_processor import make_document


def extract_frontmatter_and_heading(content: str) -> tuple:
    """
    Extract frontmatter title and H1 heading from markdown content.

    Returns:
        tuple: (frontmatter_title, h1_heading)
    """
    lines = content.split('\n')
    in_frontmatter = False
    frontmatter_title = None
    h1_heading = None

    for line in lines:
        if line.strip() == '---':
            in_frontmatter = not in_frontmatter
        elif in_frontmatter and line.startswith('rubrik:'):
            frontmatter_title = line.split('rubrik:', 1)[1].strip().strip('"')
        elif line.startswith('# '):
            h1_heading = line[2:].strip()
            break

    return frontmatter_title, h1_heading


@pytest.mark.integration
def test_integrated_temporal_before_date(sample_sfs_document, tmp_path):
    """Test that old title is used for dates before transition."""
    # Create document with date before transition
    make_document(
        sample_sfs_document, tmp_path, target_date="2025-07-14", verbose=False
    )

    # Read the generated markdown file
    md_file = tmp_path / "2023" / "sfs-2023-30.md"
    if not md_file.exists():
        # Try without year folder
        md_file = tmp_path / "sfs-2023-30.md"

    assert md_file.exists(), f"Markdown file not created at {md_file}"

    content = md_file.read_text()
    frontmatter_title, h1_heading = extract_frontmatter_and_heading(content)

    # Verify old title has the old wording (beteckning may be removed)
    assert frontmatter_title is not None, "Frontmatter title not found"
    assert h1_heading is not None, "H1 heading not found"

    # Old wording: "hälso- och sjukvårdens fastigheter"
    assert ("hälso- och sjukvårdens fastigheter" in frontmatter_title or
            "sjukvårdens fastigheter" in frontmatter_title), \
        f"Old frontmatter title should contain old wording: {frontmatter_title}"
    assert ("hälso- och sjukvårdens fastigheter" in h1_heading or
            "sjukvårdens fastigheter" in h1_heading), \
        f"Old h1 heading should contain old wording: {h1_heading}"


@pytest.mark.integration
def test_integrated_temporal_on_transition_date(sample_sfs_document, tmp_path):
    """Test that new title is used on the transition date."""
    # Create document with date on transition
    make_document(
        sample_sfs_document, tmp_path, target_date="2025-07-15", verbose=False
    )

    # Read the generated markdown file
    md_file = tmp_path / "2023" / "sfs-2023-30.md"
    if not md_file.exists():
        # Try without year folder
        md_file = tmp_path / "sfs-2023-30.md"

    assert md_file.exists(), f"Markdown file not created at {md_file}"

    content = md_file.read_text()
    frontmatter_title, h1_heading = extract_frontmatter_and_heading(content)

    # Verify new title has the new wording
    assert frontmatter_title is not None, "Frontmatter title not found"
    assert h1_heading is not None, "H1 heading not found"

    # New wording: "fastigheter för hälso- och sjukvård"
    assert "fastigheter för hälso- och sjukvård" in frontmatter_title, \
        f"New frontmatter title should contain new wording: {frontmatter_title}"
    assert "fastigheter för hälso- och sjukvård" in h1_heading, \
        f"New h1 heading should contain new wording: {h1_heading}"


@pytest.mark.integration
def test_integrated_temporal_after_date(sample_sfs_document, tmp_path):
    """Test that new title is used for dates after transition."""
    # Create document with date after transition
    make_document(
        sample_sfs_document, tmp_path, target_date="2025-07-16", verbose=False
    )

    # Read the generated markdown file
    md_file = tmp_path / "2023" / "sfs-2023-30.md"
    if not md_file.exists():
        # Try without year folder
        md_file = tmp_path / "sfs-2023-30.md"

    assert md_file.exists(), f"Markdown file not created at {md_file}"

    content = md_file.read_text()
    frontmatter_title, h1_heading = extract_frontmatter_and_heading(content)

    # Verify new title has the new wording
    assert frontmatter_title is not None, "Frontmatter title not found"
    assert h1_heading is not None, "H1 heading not found"

    # New wording: "fastigheter för hälso- och sjukvård"
    assert "fastigheter för hälso- och sjukvård" in frontmatter_title, \
        f"New frontmatter title should contain new wording: {frontmatter_title}"
    assert "fastigheter för hälso- och sjukvård" in h1_heading, \
        f"New h1 heading should contain new wording: {h1_heading}"


@pytest.mark.integration
def test_integrated_temporal_no_target_date(sample_sfs_document, tmp_path):
    """Test that a sensible title is returned when no target_date is provided."""
    # Create document without target_date
    make_document(sample_sfs_document, tmp_path, verbose=False)

    # Read the generated markdown file
    md_file = tmp_path / "2023" / "sfs-2023-30.md"
    if not md_file.exists():
        # Try without year folder
        md_file = tmp_path / "sfs-2023-30.md"

    assert md_file.exists(), f"Markdown file not created at {md_file}"

    content = md_file.read_text()
    _, h1_heading = extract_frontmatter_and_heading(content)

    assert h1_heading is not None, "H1 heading not found"

    # Should have some reasonable title
    assert len(h1_heading) > 0, "Should have a title"
    assert "statsbidrag" in h1_heading, "Should contain key text from the title"


@pytest.mark.integration
def test_frontmatter_matches_heading(sample_sfs_document, tmp_path):
    """Test that frontmatter title matches H1 heading."""
    # Create document with a specific date
    make_document(
        sample_sfs_document, tmp_path, target_date="2025-07-14", verbose=False
    )

    # Read the generated markdown file
    md_file = tmp_path / "2023" / "sfs-2023-30.md"
    if not md_file.exists():
        # Try without year folder
        md_file = tmp_path / "sfs-2023-30.md"

    assert md_file.exists(), f"Markdown file not created at {md_file}"

    content = md_file.read_text()
    frontmatter_title, h1_heading = extract_frontmatter_and_heading(content)

    # Verify both exist
    assert frontmatter_title is not None, "Frontmatter title not found"
    assert h1_heading is not None, "H1 heading not found"

    # Verify they match
    assert frontmatter_title == h1_heading, \
        (f"Frontmatter title and H1 heading should match:\n"
         f"  Frontmatter: {frontmatter_title}\n  H1: {h1_heading}")
