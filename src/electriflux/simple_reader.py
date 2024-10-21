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
                     nested_fields: list[tuple[str, str, str, str]] = {}) -> pd.DataFrame:
    """
    Convert an XML structure to a Pandas DataFrame.
    
    Parameters:
        xml_path (Path): Path to the XML file.
        row_level (str): XPath-like string that defines the level in the XML where each row should be created.
        metadata_fields (Dict[str, str]): Dictionary of metadata fields with keys as field names and values as XPath-like strings.
        data_fields (Dict[str, str]): Dictionary of data fields with keys as field names and values as XPath-like strings.
        nested_fields: list[tuple[str, str, str, str]]: List of tuples where each tuple contains the prefix field name, the path of elements to find key field name, and value field name.
    Returns:
        pd.DataFrame: DataFrame representation of the XML data.
    """
    
    tree = ET.parse(xml_path)
    root = tree.getroot()
    root_tag = root.tag

    meta: dict[str, str] = {}
    # Extract metadata fields
    for field_name, field_xpath in metadata_fields.items():
        field_elem =  root.find(field_xpath)
        if field_elem is not None:
            meta[field_name] = field_elem.text

    all_rows = []
    for row in root.findall(row_level):
        # Extract data fields
        row_data = {field_name: row.find(field_xpath)
                    for field_name, field_xpath in data_fields.items()}

        row_data = {k: v.text if hasattr(v, 'text') else v for k, v in row_data.items()}
        nested_data = {}
        for p, r, k, v in nested_fields:
           for nr in row.findall(r):
                key_elem = nr.find(k)
                value_elem = nr.find(v)
                if key_elem is not None and value_elem is not None:
                    #_logger.debug(f"Key or value element not found for {r}/{k} or {r}/{v}")
                    nested_data[p + key_elem.text] = value_elem.text
                else:
                    _logger.error(f"Key or value element not found for {r}/{k} or {r}/{v}")   
        
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
    
    # Convert nested_fields from list of dicts to list of tuples
    nested_fields = [
        (item['prefix'], item['child_path'], item['id_field'], item['value_field'])
        for item in config['nested_fields']
    ]
        # Use a default file_regex if not specified in the config
    file_regex = config.get('file_regex', None)
    df = process_xml_files(
        xml_dir,
        config['row_level'],
        config['metadata_fields'],
        config['data_fields'],
        nested_fields,
        file_regex
    )
    conso_cols = [c for c in get_consumption_names() if c in df]
    df[conso_cols] = df[conso_cols].apply(pd.to_numeric, errors='coerce')

    date_cols = [col for col in df.columns if col.startswith('Date_')]
    # df[date_cols] = df[date_cols].apply(pd.to_datetime, errors='coerce')
    df[date_cols] = df[date_cols].apply(lambda x: pd.to_datetime(x, errors='coerce', utc=True).dt.tz_localize(None))

    # Conversion automatique des colonnes de type object avec infer_objects()
    df = df.infer_objects()

    # Application de convert_dtypes pour optimiser les types des colonnes
    df = df.convert_dtypes()
    return df

def main():

    df = process_flux('C15', Path('~/data/flux_enedis_v2/C15').expanduser())
    df.to_csv('C15.csv', index=False)
    print(df)
    print(df.dtypes)
if __name__ == "__main__":
    main()

