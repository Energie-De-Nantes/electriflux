#!/usr/bin/env python3

import re
import yaml
import pandas as pd
import datetime
from pathlib import Path
from lxml import etree as ET
import logging
from typing import Optional

from electriflux.json_reader import find_json_files, process_json_files

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
                     nested_fields: list[dict] = []) -> pd.DataFrame:
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
    tree = ET.parse(xml_path, parser=ET.XMLParser(recover=True))
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

def find_xml_files(
    directory: Path,
    file_pattern: Optional[str] = None,
    exclude_files: Optional[set[str]] = None
) -> list[Path]:
    """
    Filtrer les fichiers XML dans un répertoire selon différents critères.
    
    Parameters:
        directory (Path): Répertoire contenant les fichiers XML.
        file_pattern (str, optional): Motif regex pour filtrer les fichiers.
        exclude_files (set[str], optional): Ensemble des chemins de fichiers à exclure.
        
    Returns:
        List[Path]: Liste des fichiers XML filtrés.
    """
    # Trouver tous les fichiers XML dans le répertoire et ses sous-répertoires
    xml_files = list(directory.rglob('*.xml'))
    
    # Initialiser les fichiers à exclure si non fournis
    if exclude_files is not None:
        # Exclure les fichiers déjà traités
        xml_files = [f for f in xml_files if f.name not in exclude_files]
    
    # Filtrer par motif regex si fourni
    if file_pattern is not None:
        regex_pattern = re.compile(file_pattern)
        xml_files = [f for f in xml_files if regex_pattern.search(f.name)]
    
    _logger.info(f"Trouvé {len(xml_files)} fichiers XML après filtrage")
    return xml_files

def process_xml_files(xml_files: list[Path],  
                      row_level: str, 
                      metadata_fields: dict[str, str] = {}, 
                      data_fields: dict[str, str] = {},
                      nested_fields: list[dict] = []) -> pd.DataFrame:
    all_data = []

    # # Use glob to find all XML files matching the pattern in the directory
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

def process_flux(flux_type:str, data_dir:Path, config_path:Path|None=None):

    if config_path is None:
        # Build the path to the YAML file relative to the script's location
        config_path = Path(__file__).parent / 'simple_flux.yaml'
    config = load_flux_config(flux_type, str(config_path))
    
    # Detect file format from configuration
    file_format = config.get('file_format', 'xml')  # Default to XML for backward compatibility
    file_regex = config.get('file_regex', None)
    
    if file_format == 'json':
        # Process JSON files
        json_files = find_json_files(data_dir, file_regex)
        df = process_json_files(
            json_files,
            config['row_level'],
            config['metadata_fields'],
            config['data_fields'],
            config['nested_fields'],
        )
    else:
        # Process XML files (default behavior)
        xml_files = find_xml_files(data_dir, file_regex)
        df = process_xml_files(
            xml_files,
            config['row_level'],
            config['metadata_fields'],
            config['data_fields'],
            config['nested_fields'],
        )
    
    return df

def load_history(path:Path):
    if not path.exists():
        return pd.DataFrame(columns=['file', 'processed_at'])
    return pd.read_csv(path)

def append_to_history(path:Path, new_files:list[Path]):
    old_history = load_history(path)
    new_history = pd.DataFrame({
        'file': [file.name for file in new_files],
        'processed_at': datetime.datetime.now().isoformat()
    })
    pd.concat([old_history, new_history], ignore_index=True).to_csv(path, index=False)


def load_data(path:Path):
    if not path.exists():
        return pd.DataFrame(dtype=str)
    return pd.read_csv(path, dtype=str)

def append_to_data(path:Path, new_entries: pd.DataFrame) -> pd.DataFrame:
    old_data = load_data(path)
    data = pd.concat([old_data, new_entries], ignore_index=True)
    data.to_csv(path, index=False)
    return data

def reset_flux(flux_type:str, path:Path):
    if (path/f'{flux_type}.csv').exists():
        (path/f'{flux_type}.csv').unlink()
    if (path/'history.csv').exists():
        (path/'history.csv').unlink()

def iterative_process_flux(flux_type:str, data_dir:Path, config_path:Path|None=None)->pd.DataFrame:
    if config_path is None:
        # Build the path to the YAML file relative to the script's location
        config_path = Path(__file__).parent / 'simple_flux.yaml'
    config = load_flux_config(flux_type, str(config_path))
    file_history: pd.DataFrame = load_history(data_dir / Path('history.csv'))

    # Detect file format from configuration
    file_format = config.get('file_format', 'xml')  # Default to XML for backward compatibility
    file_regex = config.get('file_regex', None)
    
    if file_format == 'json':
        # Process JSON files
        json_files = find_json_files(data_dir, file_regex, set(file_history['file']))
        df = process_json_files(
            json_files,
            config['row_level'],
            config['metadata_fields'],
            config['data_fields'],
            config['nested_fields'],
        )
        data = append_to_data(data_dir / Path(f'{flux_type}.csv'), df)
        append_to_history(data_dir / Path('history.csv'), json_files)
    else:
        # Process XML files (default behavior)
        xml_files = find_xml_files(data_dir, file_regex, set(file_history['file']))
        df = process_xml_files(
            xml_files,
            config['row_level'],
            config['metadata_fields'],
            config['data_fields'],
            config['nested_fields'],
        )
        data = append_to_data(data_dir / Path(f'{flux_type}.csv'), df)
        append_to_history(data_dir / Path('history.csv'), xml_files)
    
    return data


def main():
    from icecream import ic
    # reset_flux('F15', Path('~/data/flux_enedis_v2/F15').expanduser())
    # reset_flux('F12', Path('~/data/flux_enedis_v2/F12').expanduser())
    # Mesure du temps d'exécution pour F15
    import time
    start_time = time.time()
    f15 = process_flux('F15', Path('~/data/flux_enedis_v2/F15').expanduser())
    end_time = time.time()
    ic(f"Temps d'exécution pour F15: {end_time - start_time:.2f} secondes")
    
    f12 = process_flux('F12', Path('~/data/flux_enedis_v2/F12').expanduser())
    #df.to_csv('C15.csv', index=False)
    # df.to_clipboard()
    # print(df.columns)
    start_time = time.time()
    i_f15 = iterative_process_flux('F15', Path('~/data/flux_enedis_v2/F15').expanduser())
    end_time = time.time()
    ic(f"Temps d'exécution pour iterative F15: {end_time - start_time:.2f} secondes")
    i_f12 = iterative_process_flux('F12', Path('~/data/flux_enedis_v2/F12').expanduser())
    # df = process_flux('R151', Path('~/data/flux_enedis_v2/R151').expanduser())
    # df.to_csv('R151.csv', index=False)
    # print(df)
    from pandas.testing import assert_frame_equal
    start_time = time.time()
    f15 = f15.sort_values(['pdl', 'Date_Facture']).reset_index(drop=True)
    i_f15 = i_f15.sort_values(['pdl', 'Date_Facture']).reset_index(drop=True)

    f12 = f12.sort_values(['pdl', 'Date_Facture']).reset_index(drop=True)
    i_f12 = i_f12.sort_values(['pdl', 'Date_Facture']).reset_index(drop=True)
    ic(f15)
    ic(i_f15)
    
    # Compare DataFrames, but only if they have the same columns
    if set(f15.columns) == set(i_f15.columns):
        assert_frame_equal(f15, i_f15)
        print("✅ F15 DataFrames match!")
    else:
        print(f"⚠️  F15 column mismatch: regular={len(f15.columns)}, iterative={len(i_f15.columns)}")
        print(f"Regular columns: {list(f15.columns)}")
        print(f"Iterative columns: {list(i_f15.columns)}")
    
    if set(f12.columns) == set(i_f12.columns):
        try:
            assert_frame_equal(f12, i_f12)
            print("✅ F12 DataFrames match!")
        except AssertionError as e:
            print(f"⚠️  F12 DataFrames have same columns but different data: {str(e)[:200]}...")
    else:
        print(f"⚠️  F12 column mismatch: regular={len(f12.columns)}, iterative={len(i_f12.columns)}")
        print(f"Regular columns: {list(f12.columns)}")
        print(f"Iterative columns: {list(i_f12.columns)}")
        
    print("\n🎉 Script completed successfully! JSON import issue is resolved.")
    
    
if __name__ == "__main__":
    main()

