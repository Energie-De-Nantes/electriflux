#!/usr/bin/env python3

import json
import re
from pathlib import Path
import pandas as pd
import logging
from typing import Optional
from jsonpath_ng import parse

_logger = logging.getLogger(__name__)

def json_to_dataframe(json_path: Path, row_level: str, 
                     metadata_fields: dict[str, str] = {}, 
                     data_fields: dict[str, str] = {},
                     nested_fields: list[dict] = []) -> pd.DataFrame:
    """
    Convert a JSON structure to a Pandas DataFrame, handling nested structures and multiple conditions.
    
    Parameters:
        json_path (Path): Path to the JSON file.
        row_level (str): JSONPath expression that defines the level in the JSON where each row should be created.
        metadata_fields (dict[str, str]): Dictionary of metadata fields with keys as field names and values as JSONPath expressions.
        data_fields (dict[str, str]): Dictionary of data fields with keys as field names and values as JSONPath expressions.
        nested_fields (list[dict]): List of dictionaries that define how to extract nested fields with optional conditions.
    
    Returns:
        pd.DataFrame: DataFrame representation of the JSON data.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    meta: dict[str, str] = {}
    # Extract metadata fields
    for field_name, field_jsonpath in metadata_fields.items():
        try:
            jsonpath_expr = parse(field_jsonpath)
            matches = jsonpath_expr.find(data)
            if matches:
                meta[field_name] = str(matches[0].value)
        except Exception as e:
            _logger.warning(f"Failed to extract metadata field {field_name} with path {field_jsonpath}: {e}")
    
    # Extract rows based on row_level
    all_rows = []
    try:
        row_expr = parse(row_level)
        rows = row_expr.find(data)
        
        for row_match in rows:
            row_data = {}
            row_obj = row_match.value
            
            # Extract data fields from current row
            for field_name, field_jsonpath in data_fields.items():
                try:
                    # For relative paths, apply to current row object
                    if field_jsonpath.startswith('$.'):
                        # Absolute path from root
                        field_expr = parse(field_jsonpath)
                        field_matches = field_expr.find(data)
                    else:
                        # Relative path from current row
                        field_expr = parse(f"$.{field_jsonpath}" if not field_jsonpath.startswith('$') else field_jsonpath)
                        field_matches = field_expr.find(row_obj)
                    
                    if field_matches:
                        row_data[field_name] = str(field_matches[0].value)
                    else:
                        row_data[field_name] = None
                except Exception as e:
                    _logger.warning(f"Failed to extract field {field_name} with path {field_jsonpath}: {e}")
                    row_data[field_name] = None
            
            # Extract nested fields with conditions
            nested_data = {}
            for nested in nested_fields:
                prefix = nested.get('prefix', '')
                child_path = nested['child_path']
                id_field = nested['id_field']
                value_field = nested['value_field']
                conditions = nested.get('conditions', [])
                
                try:
                    # Apply child_path relative to current row
                    child_expr = parse(child_path)
                    child_matches = child_expr.find(row_obj)
                    
                    for child_match in child_matches:
                        child_obj = child_match.value
                        
                        # Check conditions
                        if conditions:
                            condition_met = True
                            for condition in conditions:
                                cond_expr = parse(condition['jsonpath'])
                                cond_matches = cond_expr.find(child_obj)
                                if not cond_matches or str(cond_matches[0].value) != condition['value']:
                                    condition_met = False
                                    break
                            if not condition_met:
                                continue
                        
                        # Extract id and value
                        id_expr = parse(id_field)
                        value_expr = parse(value_field)
                        
                        id_matches = id_expr.find(child_obj)
                        value_matches = value_expr.find(child_obj)
                        
                        if id_matches and value_matches:
                            key = f"{prefix}{id_matches[0].value}"
                            nested_data[key] = str(value_matches[0].value)
                        
                        # Extract additional fields
                        additional_fields = nested.get('additional_fields', {})
                        for add_field_name, add_field_path in additional_fields.items():
                            add_field_key = f"{prefix}{add_field_name}"
                            if add_field_key not in nested_data:
                                add_expr = parse(add_field_path)
                                add_matches = add_expr.find(child_obj)
                                if add_matches:
                                    nested_data[add_field_key] = str(add_matches[0].value)
                
                except Exception as e:
                    _logger.warning(f"Failed to extract nested field {nested}: {e}")
            
            all_rows.append(row_data | nested_data)
            
    except Exception as e:
        _logger.error(f"Failed to parse row level {row_level}: {e}")
        return pd.DataFrame()
    
    # Create DataFrame
    df = pd.DataFrame(all_rows)
    
    # Add metadata as columns
    for k, v in meta.items():
        df[k] = v
    
    return df


def find_json_files(
    directory: Path,
    file_pattern: Optional[str] = None,
    exclude_files: Optional[set[str]] = None
) -> list[Path]:
    """
    Filter JSON files in a directory according to different criteria.
    
    Parameters:
        directory (Path): Directory containing JSON files.
        file_pattern (str, optional): Regex pattern to filter files.
        exclude_files (set[str], optional): Set of file paths to exclude.
        
    Returns:
        list[Path]: List of filtered JSON files.
    """
    # Find all JSON files in the directory and its subdirectories
    json_files = list(directory.rglob('*.json'))
    
    # Initialize files to exclude if not provided
    if exclude_files is not None:
        # Exclude already processed files
        json_files = [f for f in json_files if f.name not in exclude_files]
    
    # Filter by regex pattern if provided
    if file_pattern is not None:
        regex_pattern = re.compile(file_pattern)
        json_files = [f for f in json_files if regex_pattern.search(f.name)]
    
    _logger.info(f"Found {len(json_files)} JSON files after filtering")
    return json_files


def process_json_files(json_files: list[Path],  
                      row_level: str, 
                      metadata_fields: dict[str, str] = {}, 
                      data_fields: dict[str, str] = {},
                      nested_fields: list[dict] = []) -> pd.DataFrame:
    """
    Process a list of JSON files and combine them into a single DataFrame.
    
    Parameters:
        json_files (list[Path]): List of JSON files to process.
        row_level (str): JSONPath expression for row level.
        metadata_fields (dict[str, str]): Metadata field mappings.
        data_fields (dict[str, str]): Data field mappings.
        nested_fields (list[dict]): Nested field configurations.
        
    Returns:
        pd.DataFrame: Combined DataFrame from all JSON files.
    """
    all_data = []
    
    for json_file in json_files:
        try:
            df = json_to_dataframe(json_file, row_level, metadata_fields, data_fields, nested_fields)
            all_data.append(df)
        except Exception as e:
            _logger.error(f"Error processing {json_file}: {e}")
    
    # Combine all dataframes
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        return combined_df
    else:
        return pd.DataFrame()