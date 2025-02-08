#!/usr/bin/env python3

import re
import yaml
import polars as pl

from pathlib import Path
from lxml import etree as ET
import logging

_logger = logging.getLogger(__name__)

def get_consumption_names() -> list[str]:
    return ['HPH', 'HPB', 'HCH', 'HCB', 'HP', 'HC', 'BASE']

def xml_to_dataframe(xml_path: Path, row_level: str, 
                     metadata_fields: dict[str, str] = {}, 
                     data_fields: dict[str, str] = {},
                     nested_fields: list[tuple[str, str, str, str]] = {}) -> pl.DataFrame:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    meta = {}
    for field_name, field_xpath in metadata_fields.items():
        field_elem = root.find(field_xpath)
        if field_elem is not None:
            meta[field_name] = field_elem.text
    
    all_rows = []
    for row in root.findall(row_level):
        row_data = {field_name: row.find(field_xpath)
                    for field_name, field_xpath in data_fields.items()}
        row_data = {k: v.text if hasattr(v, 'text') else v for k, v in row_data.items()}
        
        nested_data = {}
        for p, r, k, v in nested_fields:
            for nr in row.findall(r):
                key_elem = nr.find(k)
                value_elem = nr.find(v)
                if key_elem is not None and value_elem is not None:
                    nested_data[p + key_elem.text] = value_elem.text
                else:
                    _logger.error(f"Key or value element not found for {r}/{k} or {r}/{v}")   
        
        all_rows.append(row_data | nested_data)
    
    df = pl.DataFrame(all_rows).with_columns([pl.all().cast(pl.Utf8)])
    for k, v in meta.items():
        df = df.with_columns(pl.lit(v).cast(pl.Utf8).alias(k))
    
    return df

def enforce_expected_types(df: pl.DataFrame, expected_types: dict[str, str]) -> pl.DataFrame:
    """
    Enforce expected types on a DataFrame after processing.
    """
    type_mapping = {
        "String": pl.Utf8,
        "Float64": pl.Float64,
        "Int64": pl.Int64,
        "Date": pl.Date,
        "DateTime": pl.Datetime
    }
    
    for col, dtype in expected_types.items():
        if col in df.columns and dtype in type_mapping:
            if dtype in ["Date", "Datetime"]:
                df = df.with_columns(
                    pl.col(col)
                    .str.strip_chars().str.strptime(type_mapping[dtype], strict=False).dt.replace_time_zone('Europe/Paris')
                )
            else:
                df = df.with_columns(
                    pl.col(col)
                    .replace("", None)  # Remplacer les chaînes vides par null
                    .cast(type_mapping[dtype], strict=False)  # Casting en mode tolérant
                )
    return df

def process_xml_files(directory: Path,  
                      row_level: str, 
                      metadata_fields: dict[str, str] = {}, 
                      data_fields: dict[str, str] = {},
                      nested_fields: list[tuple[str, str, str, str]] = {},
                      file_pattern: str | None=None) -> pl.DataFrame:
    all_data = []
    xml_files = [f for f in directory.rglob('*.xml')]
    
    if file_pattern is not None:
        regex_pattern = re.compile(file_pattern)
        xml_files = [f for f in xml_files if regex_pattern.search(f.name)]
    
    _logger.info(f"Found {len(xml_files)} files matching pattern {file_pattern}")
    for xml_file in xml_files:
        try:
            df = xml_to_dataframe(xml_file, row_level, metadata_fields, data_fields, nested_fields)
            all_data.append(df)
        except Exception as e:
            _logger.error(f"Error processing {xml_file}: {e}")
    
    if not all_data:
        return pl.DataFrame()
    
    all_columns = set(col for df in all_data for col in df.columns)
    standardized_data = [df.with_columns([pl.lit("").cast(pl.Utf8).alias(col) for col in all_columns if col not in df.columns]) for df in all_data]
    
    return pl.concat(standardized_data, how="diagonal").with_columns([pl.all().cast(pl.Utf8)])

def load_flux_config(flux_type, config_path='flux_configs.yaml'):
    with open(config_path, 'r') as file:
        configs = yaml.safe_load(file)
    
    if flux_type not in configs:
        raise ValueError(f"Unknown flux type: {flux_type}")
    
    return configs[flux_type]

def process_flux(flux_type: str, xml_dir: Path, config_path: Path | None = None) -> pl.DataFrame:
    if config_path is None:
        config_path = Path(__file__).parent / 'simple_flux.yaml'
    
    config = load_flux_config(flux_type, config_path)
    
    nested_fields = [
        (item['prefix'], item['child_path'], item['id_field'], item['value_field'])
        for item in config['nested_fields']
    ]
    file_regex = config.get('file_regex', None)
    expected_types = config.get('expected_types', {})
    
    df = process_xml_files(
        xml_dir,
        config['row_level'],
        config['metadata_fields'],
        config['data_fields'],
        nested_fields,
        file_regex
    )
    
    df = enforce_expected_types(df, expected_types)
    
    return df

def main():
    df = process_flux('C15', Path('~/data/flux_enedis_v2/C15').expanduser())
    df.write_csv('C15.csv')
    print(df)
    print(df.schema)

    df = process_flux('R151', Path('~/data/flux_enedis_v2/R151').expanduser())
    df.write_csv('R151.csv')
    print(df)
    print(df.schema)

if __name__ == "__main__":
    main()
