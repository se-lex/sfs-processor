#!/usr/bin/env python3
"""
Tests for document validation module.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from util.document_validator import (
    validate_sfs_document,
    validate_beteckning,
    get_validation_summary,
    DocumentValidationError
)


def test_valid_document():
    """Test validation of a valid document."""
    print("Test 1: Valid document")
    doc = {
        "beteckning": "2010:800",
        "rubrik": "Skollagen",
        "fulltext": {
            "forfattningstext": "<p>Test content</p>"
        }
    }
    try:
        validate_sfs_document(doc, strict=True)
        print("✓ Valid document passed validation")
    except DocumentValidationError as e:
        print(f"✗ Validation failed: {e}")
        return False
    return True


def test_missing_beteckning():
    """Test validation of document missing beteckning."""
    print("\nTest 2: Missing beteckning")
    doc = {
        "rubrik": "Test Law"
    }
    try:
        validate_sfs_document(doc, strict=True)
        print("✗ Should have failed validation")
        return False
    except DocumentValidationError as e:
        print(f"✓ Correctly caught validation error: {e}")
        return True


def test_invalid_beteckning_format():
    """Test validation of invalid beteckning format."""
    print("\nTest 3: Invalid beteckning format")
    assert validate_beteckning("2010:800") == True, "Valid beteckning should pass"
    assert validate_beteckning("N2010:800") == True, "N-prefixed beteckning should pass"
    assert validate_beteckning("invalid") == False, "Invalid format should fail"
    assert validate_beteckning("2010-800") == False, "Wrong separator should fail"
    print("✓ Beteckning format validation works correctly")
    return True


def test_validation_summary():
    """Test validation summary function."""
    print("\nTest 4: Validation summary")

    # Valid document
    doc_valid = {"beteckning": "2010:800", "rubrik": "Test"}
    summary = get_validation_summary(doc_valid)
    assert summary['valid'] == True, "Valid document should be marked valid"
    assert len(summary['errors']) == 0, "Valid document should have no errors"

    # Invalid document
    doc_invalid = {"rubrik": "Test"}
    summary = get_validation_summary(doc_invalid)
    assert summary['valid'] == False, "Invalid document should be marked invalid"
    assert len(summary['errors']) > 0 or len(summary['warnings']) > 0, "Invalid document should have errors or warnings"

    print("✓ Validation summary works correctly")
    return True


def test_optional_fields():
    """Test that optional fields are accepted."""
    print("\nTest 5: Optional fields")
    doc = {
        "beteckning": "2010:800",
        "rubrik": "Test Law",
        "publiceradDateTime": "2010-07-01",
        "ikraftDateTime": "2010-08-01",
        "fulltext": {
            "forfattningstext": "<p>Content</p>",
            "utfardadDateTime": "2010-06-15"
        },
        "register": {
            "forarbeten": "Prop. 2009/10:165"
        },
        "organisation": {
            "namn": "Utbildningsdepartementet"
        },
        "andringsforfattningar": [
            {"beteckning": "2011:100", "rubrik": "Amendment"}
        ]
    }
    try:
        validate_sfs_document(doc, strict=True)
        print("✓ Document with optional fields passed validation")
    except DocumentValidationError as e:
        print(f"✗ Validation failed: {e}")
        return False
    return True


def run_all_tests():
    """Run all tests and report results."""
    print("=" * 60)
    print("Running Document Validation Tests")
    print("=" * 60)

    tests = [
        test_valid_document,
        test_missing_beteckning,
        test_invalid_beteckning_format,
        test_validation_summary,
        test_optional_fields
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test crashed: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
