#!/usr/bin/env python3

import re
import yaml
import pandas as pd

from pathlib import Path
from lxml import etree as ET
import logging

_logger = logging.getLogger(__name__)
def get_consumption_names() -> list[str]:
    """
    Retourne une liste des noms de consommation utilisés.

    Returns:
        list[str]: Liste des noms de consommation.
    """
    return ['HPH', 'HPB', 'HCH', 'HCB', 'HP', 'HC', 'BASE']

def xml_to_dataframe(xml_path: Path, row_level: str, 
                     metadata_fields: dict[str, str] = {}, 
                     data_fields: dict[str, str] = {},
                     nested_fields: list[dict] = {}) -> pd.DataFrame:
    """
    Convert an XML structure to a Pandas DataFrame, handling nested structures and multiple conditions.

    Parameters:
        xml_path (Path): Path to the XML file.
        row_level (str): XPath-like string that defines the level in the XML where each row should be created.
        metadata_fields (Dict[str, str]): Dictionary of metadata fields with keys as field names and values as XPath-like strings.
        data_fields (Dict[str, str]): Dictionary of data fields with keys as field names and values as XPath-like strings.
        nested_fields: list[dict]: List of dictionaries that define how to extract nested fields with optional conditions.

    Returns:
        pd.DataFrame: DataFrame representation of the XML data.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    meta: dict[str, str] = {}
    # Extract metadata fields
    for field_name, field_xpath in metadata_fields.items():
        field_elem = root.find(field_xpath)
        if field_elem is not None:
            meta[field_name] = field_elem.text

    all_rows = []
    for row in root.findall(row_level):
        # Extract data fields
        row_data = {field_name: row.find(field_xpath)
                    for field_name, field_xpath in data_fields.items()}
        row_data = {k: v.text if hasattr(v, 'text') else v for k, v in row_data.items()}
        
        # Extract nested fields with multiple conditions
        nested_data = {}
        for nested in nested_fields:
            prefix = nested.get('prefix', '')
            child_path = nested['child_path']
            id_field = nested['id_field']
            value_field = nested['value_field']
            conditions = nested.get('conditions', [])

            for nr in row.findall(child_path):
                key_elem = nr.find(id_field)
                value_elem = nr.find(value_field)

                # Collect all condition results
                condition_results = [nr.find(cond['xpath']).text == cond['value'] for cond in conditions if nr.find(cond['xpath']) is not None]
                if all(condition_results):
                    if key_elem is not None and value_elem is not None:
                        nested_data[f"{prefix}{key_elem.text}"] = value_elem.text
                
                        additional_fields = nested.get('additional_fields', {})
                        # Extract additional fields.
                        for add_field_name, add_field_xpath in additional_fields.items():
                            if f"{prefix}{add_field_name}" not in nested_data: # On évite d'aller cherche plusieurs fois là même info, on prend juste la première
                                add_elem = nr.find(add_field_xpath)
                                if add_elem is not None:
                                    nested_data[f"{prefix}{add_field_name}"] = add_elem.text

        all_rows.append(row_data | nested_data)

    df = pd.DataFrame(all_rows)
    for k, v in meta.items():
        df[k] = v
    return df

def process_xml_files(directory: Path,  
                      row_level: str, 
                      metadata_fields: dict[str, str] = {}, 
                      data_fields: dict[str, str] = {},
                      nested_fields: list[tuple[str, str, str, str]] = {},
                      file_pattern: str | None=None) -> pd.DataFrame:
    all_data = []

    xml_files = [f for f in directory.rglob('*.xml')]

    if file_pattern is not None:
        regex_pattern = re.compile(file_pattern)
        xml_files = [f for f in xml_files if regex_pattern.search(f.name)]
    
    
    _logger.info(f"Found {len(xml_files)} files matching pattern {file_pattern}")
    # Use glob to find all XML files matching the pattern in the directory
    for xml_file in xml_files:
        try:
            df = xml_to_dataframe(xml_file, row_level, metadata_fields, data_fields, nested_fields)
            all_data.append(df)
        except Exception as e:
            _logger.error(f"Error processing {xml_file}: {e}")
    # Combine all dataframes
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        return combined_df
    else:
        return pd.DataFrame()
    
def load_flux_config(flux_type, config_path='flux_configs.yaml'):
    with open(config_path, 'r') as file:
        configs = yaml.safe_load(file)
    
    if flux_type not in configs:
        raise ValueError(f"Unknown flux type: {flux_type}")
    
    return configs[flux_type]

def process_flux(flux_type:str, xml_dir:Path, config_path:Path|None=None):

    if config_path is None:
        # Build the path to the YAML file relative to the script's location
        config_path = Path(__file__).parent / 'simple_flux.yaml'
    config = load_flux_config(flux_type, config_path)
    
    
    # Use a default file_regex if not specified in the config
    file_regex = config.get('file_regex', None)
    
    df = process_xml_files(
        xml_dir,
        config['row_level'],
        config['metadata_fields'],
        config['data_fields'],
        config['nested_fields'],
        file_regex
    )
    return df

def main():

    df = process_flux('C15', Path('~/data/flux_enedis_v2/C15').expanduser())
    df.to_csv('C15.csv', index=False)
    # df.to_clipboard()
    print(df)
    df = process_flux('R151', Path('~/data/flux_enedis_v2/R151').expanduser())
    df.to_csv('R151.csv', index=False)
    print(df)
if __name__ == "__main__":
    main()

