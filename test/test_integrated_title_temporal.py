#!/usr/bin/env python3
"""Test temporal title processing in the main SFS processor."""

import tempfile
from pathlib import Path
from sfs_processor import make_document


def test_integrated_title_temporal():
    """Test that title temporal processing works in the main processor."""
    # Mock data with temporal title variants
    test_data = {
        'beteckning': '2023:30',
        'rubrik': """/Rubriken upphör att gälla U:2025-07-15/
Förordning (2023:30) om statsbidrag till regioner för åtgärder för att höja driftsäkerheten på hälso- och sjukvårdens fastigheter
/Rubriken träder i kraft I:2025-07-15/
Förordning om statsbidrag till regioner för åtgärder för att höja driftsäkerheten på fastigheter för hälso- och sjukvård""",
        'fulltext': {
            'innehall': 'Test innehåll här...'
        }
    }
    
    print("Testing integrated title temporal processing:")
    print()
    
    # Helper function to create document and read result
    def create_and_read_document(target_date=None):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            make_document(test_data, output_dir, target_date=target_date, verbose=False)
            # Read the generated markdown file
            md_file = output_dir / "2023" / "sfs-2023-30.md"
            if md_file.exists():
                return md_file.read_text()
            else:
                # Try without year folder
                md_file = output_dir / "sfs-2023-30.md"
                return md_file.read_text() if md_file.exists() else ""
    
    # Test with date before transition (should get old title)
    result_before = create_and_read_document("2025-07-14")
    print("Result for 2025-07-14 (before transition):")
    
    # Extract frontmatter and h1 heading
    lines = result_before.split('\n')
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
    
    print(f"  Frontmatter title: {frontmatter_title}")
    print(f"  H1 heading: {h1_heading}")
    
    # Verify old title contains (2023:30)
    assert "(2023:30)" in frontmatter_title, f"Old frontmatter title should contain (2023:30): {frontmatter_title}"
    assert "(2023:30)" in h1_heading, f"Old h1 heading should contain (2023:30): {h1_heading}"
    print("  ✓ Old title correctly contains (2023:30)")
    print()
    
    # Test with date on/after transition (should get new title)
    result_after = create_and_read_document("2025-07-15")
    print("Result for 2025-07-15 (on transition date):")
    
    # Extract frontmatter and h1 heading
    lines = result_after.split('\n')
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
    
    print(f"  Frontmatter title: {frontmatter_title}")
    print(f"  H1 heading: {h1_heading}")
    
    # Verify new title does not contain (2023:30)
    assert "(2023:30)" not in frontmatter_title, f"New frontmatter title should not contain (2023:30): {frontmatter_title}"
    assert "(2023:30)" not in h1_heading, f"New h1 heading should not contain (2023:30): {h1_heading}"
    print("  ✓ New title correctly does not contain (2023:30)")
    print()
    
    # Test without target_date (should get original title with temporal markers)
    result_no_date = create_and_read_document()
    print("Result without target_date (should preserve original):")
    
    # Extract h1 heading
    lines = result_no_date.split('\n')
    h1_heading = None
    
    for line in lines:
        if line.startswith('# '):
            h1_heading = line[2:].strip()
            break
    
    print(f"  H1 heading: {h1_heading[:80]}...")
    
    # Should contain temporal markers when no target_date is provided
    assert "/Rubriken" in h1_heading or "upphör att gälla" in h1_heading, f"Should contain temporal markers: {h1_heading}"
    print("  ✓ Original title preserved when no target_date provided")
    print()
    
    print("✓ All integrated temporal title tests passed!")


if __name__ == "__main__":
    test_integrated_title_temporal()