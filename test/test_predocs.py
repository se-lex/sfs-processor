#!/usr/bin/env python3
"""
Test script for förarbeten parsing and fetching functionality.
"""

import sys
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from formatters.predocs_parser import parse_predocs_string
from downloaders.riksdagen_api import fetch_predocs_details, format_predocs_for_frontmatter


def test_predocs_functionality():
    """Test the förarbeten parsing and fetching with real examples."""
    
    test_cases = [
        # Recent proposition that should exist
        "Prop. 2024/25:1",
        
        # Multiple documents
        "Prop. 2023/24:144, bet. 2023/24:JuU3, rskr. 2023/24:9",
        
        # Older format
        "Prop. 1966:40; 1LU 1967:53; Rskr 1967:325",
        
        # Committee abbreviations
        "Prop. 1982/83:67, LU 1982/83:33, rskr 1982/83:250",
        
        # Mixed format
        "Prop. 2021/22:136, bet. 2021/22:TU17, rskr. 2021/22:302"
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}: {test_case}")
        print('='*60)
        
        # Parse the string
        print("1. Parsing...")
        parsed = parse_predocs_string(test_case)
        print(f"   Parsed {len(parsed)} references:")
        for j, item in enumerate(parsed, 1):
            print(f"   {j}. {item}")
        
        if not parsed:
            print("   No references could be parsed.")
            continue
        
        # Fetch details for first few items to avoid hitting API too hard
        print("\n2. Fetching details (limited to first 2 items)...")
        limited_parsed = parsed[:2]  # Only test first 2 to be respectful to API
        
        try:
            detailed = fetch_predocs_details(limited_parsed, delay_between_requests=1.0)
            print(f"   Fetched details for {len(detailed)} references:")
            for j, item in enumerate(detailed, 1):
                dokumentnamn = item.get('dokumentnamn', 'N/A')
                titel = item.get('titel', 'N/A')
                original = item.get('original', 'N/A')
                print(f"   {j}. {original}")
                print(f"      -> {dokumentnamn}: {titel}")
        except Exception as e:
            print(f"   Error fetching details: {e}")
            continue
        
        # Format for frontmatter
        print("\n3. Formatting for frontmatter...")
        try:
            formatted = format_predocs_for_frontmatter(detailed)
            print(f"   Formatted {len(formatted)} items:")
            for j, item in enumerate(formatted, 1):
                print(f"   {j}. {item}")
        except Exception as e:
            print(f"   Error formatting: {e}")


def test_api_directly():
    """Test the API directly with some known documents."""
    print(f"\n{'='*60}")
    print("Direct API Test")
    print('='*60)
    
    from downloaders.riksdagen_api import fetch_document_info
    
    # Test cases: (doc_type, rm, bet, expected_to_exist)
    direct_tests = [
        ("prop", "2024/25", "1", True),      # Budget proposition 2025
        ("prop", "2023/24", "144", True),    # Recent proposition
        ("rskr", "2023/24", "9", True),      # Recent riksdagsskrivelse
        ("prop", "1966/67", "40", False),    # Very old, might not exist in API
        ("bet", "2023/24", "JuU3", True),    # Committee report
    ]
    
    for i, (doc_type, rm, bet, expected) in enumerate(direct_tests, 1):
        print(f"\n{i}. Testing {doc_type} {rm}:{bet}")
        try:
            result = fetch_document_info(doc_type, rm, bet)
            if result:
                print(f"   ✓ Found: {result['dokumentnamn']}: {result['titel']}")
            else:
                print(f"   ✗ Not found (expected: {'Yes' if expected else 'No'})")
        except Exception as e:
            print(f"   ✗ Error: {e}")


if __name__ == "__main__":
    print("Testing förarbeten parsing and fetching functionality...")
    
    # First test the API directly
    test_api_directly()
    
    # Then test the full workflow
    test_predocs_functionality()
    
    print(f"\n{'='*60}")
    print("Testing completed!")
    print('='*60)