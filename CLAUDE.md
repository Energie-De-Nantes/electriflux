# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Electriflux is a Python library for processing Enedis (French electricity distribution) data flows. It handles secure SFTP downloads, AES decryption, and both XML and JSON data extraction into pandas/polars DataFrames.

## Development Commands

```bash
# Install dependencies
poetry install

# Install package in development mode (needed for absolute imports)
pip install -e .

# Run all tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=electriflux

# Run specific test file
poetry run pytest tests/test_xml_parsing.py

# Run JSON parsing tests
poetry run pytest tests/test_json_parsing.py

# Build the package
poetry build

# Publish to PyPI
poetry publish
```

## Architecture

The project has three main processing approaches:

1. **Pandas-based processing** (`src/electriflux/simple_reader.py`):
   - Primary implementation using pandas DataFrames
   - Functions: `convert_flux()`, `convert_flux_iterate()`, `append_data()`
   - Supports iterative processing for large files
   - Auto-detects file format (XML/JSON) based on configuration

2. **Polars-based processing** (`src/electriflux/polars_reader.py`):
   - Alternative implementation for better performance
   - Same interface as pandas version

3. **JSON processing** (`src/electriflux/json_reader.py`):
   - Dedicated module for JSON flux processing
   - Functions: `json_to_dataframe()`, `find_json_files()`, `process_json_files()`
   - Uses JSONPath expressions for data extraction
   - Supports nested field extraction with additional fields

Key components:
- **utils.py**: SFTP operations, AES encryption/decryption
- **simple_flux.yaml**: Configuration defining extraction rules for flux types (C15, F12, F15, R15, R151, RX5)
- **json_reader.py**: JSON-specific processing functions with JSONPath support

## Data Processing Flow

1. **Download & Decrypt Phase**:
   - Connect to SFTP server using paramiko
   - Download encrypted files
   - Decrypt using AES with provided key

2. **Extract & Transform Phase**:
   - Parse XML using lxml (for XML flux types)
   - Parse JSON using jsonpath-ng (for JSON flux types like RX5)
   - Extract data based on YAML configuration
   - Transform to DataFrame format

## Configuration Structure

YAML configurations define:
- `metadata_fields`: Fields extracted once per file (header information)
- `data_fields`: Fields extracted for each record (row-level data)
- `nested_fields`: Complex nested structures with conditions
- `file_format`: 'xml' (default) or 'json' for format detection
- `file_regex`: Pattern for matching relevant files
- `row_level`: XPath (XML) or JSONPath (JSON) expression for row iteration

For XML flux types:
- XPath expressions for data location
- Optional conditions and transformations
- Nested field extraction with multiple conditions

For JSON flux types (e.g., RX5):
- JSONPath expressions for data extraction
- Nested field extraction with additional_fields support
- Complex hierarchical data flattening

## JSON Support

The library supports JSON flux processing through a dedicated module:

### Supported JSON Flux Types
- **RX5**: Energy consumption data with nested classe temporelle structures

### Key Features
- **JSONPath expressions**: Navigate complex nested JSON structures
- **Nested field extraction**: Extract and flatten hierarchical data
- **Additional fields**: Support for extracting related fields from nested structures
- **File format detection**: Automatic routing to JSON processing based on configuration
- **Unified interface**: Same API as XML processing for consistency

### Configuration Example (RX5)
```yaml
RX5:
  file_format: 'json'
  file_regex: 'RX5_.*\.json$'
  row_level: '$.mesures[*]'
  metadata_fields:
    siDemandeur: '$.header.siDemandeur'
    codeFlux: '$.header.codeFlux'
  data_fields:
    pdl: 'idPrm'
    dateDebut: 'periode.dateDebut'
    etapeMetier: 'contexte[0].etapeMetier'
  nested_fields:
    - prefix: 'CT_'
      child_path: 'contexte[*].grandeur[*].calendrier[*].classeTemporelle[*]'
      id_field: 'idClasseTemporelle'
      value_field: 'quantite[0].quantite'
      additional_fields:
        libelleClasseTemporelle: 'libelleClasseTemporelle'
        codeNature: 'quantite[0].codeNature'
```

### Dependencies
- **jsonpath-ng**: JSONPath expression parsing and evaluation
- **pandas**: DataFrame operations and data manipulation

## Testing

Comprehensive test suite available in `tests/` directory:
- Unit tests for XML parsing (`test_xml_parsing.py`)
- Unit tests for JSON parsing (`test_json_parsing.py`)
- Unit tests for module functions (`test_simple_reader.py`) 
- Integration tests for complete workflows (`test_integration.py`)
- Synthetic XML fixtures for all flux types (no real data)
- Synthetic JSON fixtures for RX5 flux type
- XSD validation tests for XML compliance

## Important Considerations

- This library handles sensitive data (encryption keys, SFTP credentials)
- Supports French energy sector specific flux types
- Multiple DataFrame implementations allow performance/compatibility trade-offs
- Hybrid architecture supports both XML and JSON flux formats
- Comprehensive test coverage with synthetic fixtures
- JSONPath expressions enable complex nested data extraction
- Automatic file format detection based on configuration