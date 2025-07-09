#!/usr/bin/env python3
"""Test script for title_temporal function."""

from temporal.title_temporal import title_temporal


def test_example():
    """Test with the provided example."""
    rubrik = """/Rubriken upphör att gälla U:2025-07-15/
Förordning (2023:30) om statsbidrag till regioner för åtgärder för att höja driftsäkerheten \
på hälso- och sjukvårdens fastigheter
/Rubriken träder i kraft I:2025-07-15/
Förordning om statsbidrag till regioner för åtgärder för att höja driftsäkerheten \
på fastigheter för hälso- och sjukvård"""

    print("Testing title_temporal function with provided example:")
    print()

    # Test dates before transition
    date_before = "2025-07-14"
    result_before = title_temporal(rubrik, date_before)
    print(f"Result for {date_before} (before transition):")
    print(f"  {result_before}")

    # Test dates on transition date
    date_on = "2025-07-15"
    result_on = title_temporal(rubrik, date_on)
    print(f"Result for {date_on} (on transition date):")
    print(f"  {result_on}")

    # Test dates after transition
    date_after = "2025-07-16"
    result_after = title_temporal(rubrik, date_after)
    print(f"Result for {date_after} (after transition):")
    print(f"  {result_after}")
    print()

    # Verify correct behavior
    expected_old = ("Förordning (2023:30) om statsbidrag till regioner för åtgärder "
                    "för att höja driftsäkerheten på hälso- och sjukvårdens fastigheter")
    expected_new = ("Förordning om statsbidrag till regioner för åtgärder "
                    "för att höja driftsäkerheten på fastigheter för hälso- och sjukvård")

    print("Verification:")
    print(f"✓ Before transition: {'PASS' if result_before == expected_old else 'FAIL'}")
    print(f"✓ On transition:     {'PASS' if result_on == expected_new else 'FAIL'}")
    print(f"✓ After transition:  {'PASS' if result_after == expected_new else 'FAIL'}")

    # Additional verification
    assert "(2023:30)" in result_before, "Old title should contain (2023:30)"
    assert "(2023:30)" not in result_on, "New title should not contain (2023:30)"
    assert "(2023:30)" not in result_after, "New title should not contain (2023:30)"
    print("✓ All assertions passed!")


def test_edge_cases():
    """Test edge cases."""
    print("\n" + "="*60)
    print("Testing edge cases:")

    # Test with no temporal markers
    simple_title = "Simple title without temporal markers"
    result = title_temporal(simple_title, "2025-01-01")
    print(f"Simple title: {result}")

    # Test with None
    result = title_temporal(None, "2025-01-01")
    print(f"None title: '{result}'")

    # Test with empty string
    result = title_temporal("", "2025-01-01")
    print(f"Empty title: '{result}'")

    # Test with invalid date
    result = title_temporal(simple_title, "invalid-date")
    print(f"Invalid date: {result}")


if __name__ == "__main__":
    test_example()
    test_edge_cases()