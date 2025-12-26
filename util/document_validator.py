#!/usr/bin/env python3
"""
Document validation module for SFS documents.

Provides JSON schema validation to ensure document structure integrity
before processing.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from jsonschema import validate, ValidationError, SchemaError


class DocumentValidationError(Exception):
    """Raised when document validation fails."""
    pass


class SchemaLoadError(Exception):
    """Raised when schema file cannot be loaded."""
    pass


# Cache the loaded schema to avoid repeated file I/O
_SCHEMA_CACHE: Optional[Dict[str, Any]] = None


def load_schema() -> Dict[str, Any]:
    """
    Load the SFS document JSON schema.

    Returns:
        Dict containing the JSON schema

    Raises:
        SchemaLoadError: If schema file cannot be loaded or parsed
    """
    global _SCHEMA_CACHE

    if _SCHEMA_CACHE is not None:
        return _SCHEMA_CACHE

    schema_path = Path(__file__).parent.parent / "data" / "sfs_document_schema.json"

    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            _SCHEMA_CACHE = json.load(f)
        return _SCHEMA_CACHE
    except FileNotFoundError:
        raise SchemaLoadError(f"Schema file not found: {schema_path}")
    except json.JSONDecodeError as e:
        raise SchemaLoadError(f"Invalid JSON in schema file: {e}")
    except Exception as e:
        raise SchemaLoadError(f"Failed to load schema: {e}")


def validate_sfs_document(document: Dict[str, Any], strict: bool = False) -> None:
    """
    Validate an SFS document against the JSON schema.

    Args:
        document: The document data to validate
        strict: If True, raises exception on validation failure.
                If False, prints warning and continues.

    Raises:
        DocumentValidationError: If strict=True and validation fails
        SchemaLoadError: If schema cannot be loaded

    Example:
        >>> doc = {"beteckning": "2010:800", "rubrik": "Test Law"}
        >>> validate_sfs_document(doc, strict=True)
        >>> # No exception raised - document is valid
    """
    try:
        schema = load_schema()
    except SchemaLoadError as e:
        error_msg = f"Schema validation skipped: {e}"
        if strict:
            raise DocumentValidationError(error_msg) from e
        else:
            print(f"Varning: {error_msg}")
            return

    try:
        validate(instance=document, schema=schema)
    except ValidationError as e:
        # Extract the most relevant error information
        error_path = ".".join(str(p) for p in e.absolute_path) if e.absolute_path else "root"
        error_msg = f"Document validation failed at '{error_path}': {e.message}"

        if strict:
            raise DocumentValidationError(error_msg) from e
        else:
            print(f"Varning: {error_msg}")
    except SchemaError as e:
        error_msg = f"Invalid schema definition: {e.message}"
        if strict:
            raise DocumentValidationError(error_msg) from e
        else:
            print(f"Varning: {error_msg}")


def validate_beteckning(beteckning: str) -> bool:
    """
    Validate beteckning format without full schema validation.

    Args:
        beteckning: The beteckning string to validate

    Returns:
        True if valid, False otherwise

    Example:
        >>> validate_beteckning("2010:800")
        True
        >>> validate_beteckning("invalid")
        False
    """
    import re
    pattern = r'^(\d{4}:\d+|N\d{4}:\d+)$'
    return bool(re.match(pattern, beteckning))


def get_validation_summary(document: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get a summary of document validation without raising exceptions.

    Args:
        document: The document data to validate

    Returns:
        Dictionary with keys:
        - 'valid': bool indicating if document is valid
        - 'errors': list of validation error messages
        - 'warnings': list of warning messages

    Example:
        >>> doc = {"invalid": "data"}
        >>> summary = get_validation_summary(doc)
        >>> summary['valid']
        False
        >>> len(summary['errors']) > 0
        True
    """
    result = {
        'valid': True,
        'errors': [],
        'warnings': []
    }

    try:
        schema = load_schema()
    except SchemaLoadError as e:
        result['valid'] = False
        result['errors'].append(f"Failed to load schema: {e}")
        return result

    try:
        validate(instance=document, schema=schema)
    except ValidationError as e:
        result['valid'] = False
        error_path = ".".join(str(p) for p in e.absolute_path) if e.absolute_path else "root"
        result['errors'].append(f"Validation failed at '{error_path}': {e.message}")
    except SchemaError as e:
        result['valid'] = False
        result['errors'].append(f"Invalid schema: {e.message}")

    # Check for common issues
    if 'beteckning' not in document:
        result['warnings'].append("Missing required field 'beteckning'")
    elif not validate_beteckning(document['beteckning']):
        result['warnings'].append(f"Invalid beteckning format: {document['beteckning']}")

    if 'fulltext' in document and 'forfattningstext' not in document['fulltext']:
        result['warnings'].append("Field 'fulltext.forfattningstext' is missing")

    return result
