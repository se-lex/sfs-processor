# JSON Schema Validation

## Overview

The SFS Processor now includes automatic JSON schema validation to ensure document integrity before processing. This helps catch malformed documents early and provides clear error messages.

## Features

- **Automatic validation** of all SFS documents during processing
- **Schema-based validation** using JSON Schema Draft 7
- **Flexible error handling** with strict and non-strict modes
- **Validation summary** for batch processing scenarios
- **Format validation** for beteckning field (YYYY:NNN pattern)

## Schema Location

The JSON schema is located at: `data/sfs_document_schema.json`

## Usage

### In Processing Pipeline

Validation happens automatically when processing documents:

```python
from sfs_processor import make_document

# Document is automatically validated
make_document(data, output_dir, formats=["md"])
```

### Manual Validation

You can also validate documents manually:

```python
from util.document_validator import validate_sfs_document, DocumentValidationError

# Strict mode - raises exception on validation failure
try:
    validate_sfs_document(document, strict=True)
except DocumentValidationError as e:
    print(f"Validation failed: {e}")

# Non-strict mode - prints warning but continues
validate_sfs_document(document, strict=False)
```

### Validation Summary

Get detailed validation results without exceptions:

```python
from util.document_validator import get_validation_summary

summary = get_validation_summary(document)

if summary['valid']:
    print("Document is valid")
else:
    print(f"Errors: {summary['errors']}")
    print(f"Warnings: {summary['warnings']}")
```

### Beteckning Format Validation

Validate only the beteckning format:

```python
from util.document_validator import validate_beteckning

if validate_beteckning("2010:800"):
    print("Valid beteckning format")
else:
    print("Invalid beteckning format")
```

## Schema Structure

### Required Fields

- `beteckning` (string): Document identifier in format YYYY:NNN (e.g., "2010:800")
  - Pattern: `^\d{4}:\d+$` or `^N\d{4}:\d+$` (for notifications)

### Optional Fields

- `rubrik` (string): Document title/heading
- `rubrik_after_temporal` (string): Title after temporal processing
- `publiceradDateTime` (string): Publication date
- `tidsbegransadDateTime` (string): Expiration date
- `ikraftDateTime` (string): Entry into force date
- `upphavdDateTime` (string): Repeal date
- `ikraftDenDagenRegeringenBestammer` (boolean): Government-determined entry into force
- `upphavdDenDagenRegeringenBestammer` (boolean): Government-determined repeal
- `celexnummer` (string): CELEX number for EU legislation
- `eUdirektiv` (boolean): EU directive flag
- `publicerad` (boolean): Publication status
- `andringsforfattningar` (array): List of amendments
- `fulltext` (object): Full text content
  - `forfattningstext` (string): Legal text content
  - `utfardadDateTime` (string): Issue date
- `register` (object): Registry information
  - `forarbeten` (string): Preparatory works references
- `organisation` (object): Issuing organization
  - `namn` (string): Organization name

## Validation Modes

### Strict Mode (`strict=True`)

- Raises `DocumentValidationError` on validation failure
- Recommended for critical operations
- Use when you need to halt processing on invalid data

```python
validate_sfs_document(doc, strict=True)  # Raises exception on failure
```

### Non-Strict Mode (`strict=False`)

- Prints warning on validation failure but continues execution
- Default mode in the processing pipeline
- Use for batch processing where you want to continue despite errors

```python
validate_sfs_document(doc, strict=False)  # Prints warning but continues
```

## Error Messages

Validation errors include:

- Missing required fields: `"Document validation failed at 'root': 'beteckning' is a required property"`
- Invalid format: `"Document validation failed at 'beteckning': '2010-800' does not match '^\\d{4}:\\d+$'"`
- Type mismatches: `"Document validation failed at 'eUdirektiv': True is not of type 'boolean'"`

## Testing

Run validation tests:

```bash
python test/test_document_validation.py
```

Tests cover:
- Valid documents
- Missing required fields
- Invalid beteckning formats
- Optional fields
- Validation summary functionality

## Integration Points

Validation is integrated at multiple points:

1. **Document Download** (`downloaders/rkrattsbaser_api.py`)
   - Validates documents before saving to disk
   - Ensures only valid documents are stored

2. **Document Processing** (`sfs_processor.py`)
   - Validates documents before format conversion
   - Catches structural issues early in pipeline

## Benefits

- **Early error detection**: Catch malformed documents before processing
- **Better error messages**: Clear indication of what's wrong and where
- **Data quality**: Ensures consistent document structure
- **Debugging**: Easier to identify source of processing errors
- **Documentation**: Schema serves as documentation of expected structure

## Customization

To modify the schema:

1. Edit `data/sfs_document_schema.json`
2. Update validation as needed
3. Run tests to verify changes

The schema follows JSON Schema Draft 7 specification. See [json-schema.org](https://json-schema.org/) for details.

## Performance

- Schema is loaded once and cached in memory
- Validation adds minimal overhead (<1ms per document)
- No impact on batch processing performance

## Dependencies

Requires: `jsonschema>=4.0.0`

Install with:
```bash
pip install -r requirements.txt
```
