# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Electriflux is a Python library for processing Enedis (French electricity distribution) data flows. It handles secure SFTP downloads, AES decryption, and XML data extraction into pandas/polars DataFrames.

## Development Commands

```bash
# Install dependencies
poetry install

# Run all tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=electriflux

# Run specific test file
poetry run pytest tests/test_xml_parsing.py

# Build the package
poetry build

# Publish to PyPI
poetry publish
```

## Architecture

The project has two main processing approaches:

1. **Pandas-based processing** (`src/electriflux/simple_reader.py`):
   - Primary implementation using pandas DataFrames
   - Functions: `convert_flux()`, `convert_flux_iterate()`, `append_data()`
   - Supports iterative processing for large files

2. **Polars-based processing** (`src/electriflux/polars_reader.py`):
   - Alternative implementation for better performance
   - Same interface as pandas version

Key components:
- **utils.py**: SFTP operations, AES encryption/decryption
- **simple_flux.yaml**: Configuration defining extraction rules for flux types (C15, F12, F15, R15, R151)

## Data Processing Flow

1. **Download & Decrypt Phase**:
   - Connect to SFTP server using paramiko
   - Download encrypted files
   - Decrypt using AES with provided key

2. **Extract & Transform Phase**:
   - Parse XML using lxml
   - Extract data based on YAML configuration
   - Transform to DataFrame format

## Configuration Structure

YAML configurations define:
- `metadata`: Fields extracted once per file
- `data`: Fields extracted for each record
- XPath expressions for data location
- Optional conditions and transformations

## Testing

Comprehensive test suite available in `tests/` directory:
- Unit tests for XML parsing (`test_xml_parsing.py`)
- Unit tests for module functions (`test_simple_reader.py`) 
- Integration tests for complete workflows (`test_integration.py`)
- Synthetic XML fixtures for all flux types (no real data)

## Important Considerations

- This library handles sensitive data (encryption keys, SFTP credentials)
- Supports French energy sector specific flux types
- Two DataFrame implementations allow performance/compatibility trade-offs
- Comprehensive test coverage with synthetic fixtures