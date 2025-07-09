import pytest
import pandas as pd
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from electriflux.json_reader import json_to_dataframe, find_json_files, process_json_files


class TestJsonToDataframe:
    """Tests pour la fonction json_to_dataframe."""
    
    def test_basic_parsing(self, fixtures_path):
        """Test le parsing basique d'un fichier JSON."""
        json_path = fixtures_path / "rx5_minimal.json"
        row_level = '$.mesures[*]'
        metadata_fields = {
            'codeFlux': '$.header.codeFlux',
            'idDemande': '$.header.idDemande',
            'format': '$.header.format'
        }
        data_fields = {
            'pdl': 'idPrm',
            'dateDebut': 'periode.dateDebut',
            'dateFin': 'periode.dateFin',
            'etapeMetier': 'contexte[0].etapeMetier'
        }
        
        df = json_to_dataframe(json_path, row_level, metadata_fields, data_fields)
        
        # Vérifications
        assert not df.empty
        assert len(df) == 2  # 2 mesures dans le fichier
        assert 'pdl' in df.columns
        assert 'dateDebut' in df.columns
        assert 'dateFin' in df.columns
        assert 'etapeMetier' in df.columns
        assert 'codeFlux' in df.columns
        assert 'idDemande' in df.columns
        assert 'format' in df.columns
        
        # Vérifier les valeurs
        assert df['codeFlux'].iloc[0] == 'RX5'
        assert df['idDemande'].iloc[0] == 'DEM123456'
        assert df['format'].iloc[0] == 'JSON'
        assert df['pdl'].iloc[0] == '12345678901234'
        assert df['etapeMetier'].iloc[0] == 'RELEVE'
        assert df['pdl'].iloc[1] == '98765432109876'
    
    def test_nested_fields(self, fixtures_path):
        """Test l'extraction des champs imbriqués."""
        json_path = fixtures_path / "rx5_minimal.json"
        row_level = '$.mesures[*]'
        nested_fields = [
            {
                'prefix': 'CT_',
                'child_path': 'contexte[*].grandeur[*].calendrier[*].classeTemporelle[*]',
                'id_field': 'idClasseTemporelle',
                'value_field': 'quantite[0].quantite'
            }
        ]
        
        df = json_to_dataframe(json_path, row_level, nested_fields=nested_fields)
        
        assert not df.empty
        assert len(df) == 2  # 2 mesures
        
        # Vérifier les colonnes des classes temporelles
        assert 'CT_HP' in df.columns
        assert 'CT_HC' in df.columns
        assert 'CT_BASE' in df.columns
        
        # Vérifier les valeurs
        first_row = df.iloc[0]
        assert first_row['CT_HP'] == '1234'
        assert first_row['CT_HC'] == '5678'
        
        second_row = df.iloc[1]
        assert second_row['CT_BASE'] == '9876'
    
    def test_nested_fields_with_additional_fields(self, fixtures_path):
        """Test l'extraction des champs imbriqués avec champs additionnels."""
        json_path = fixtures_path / "rx5_minimal.json"
        row_level = '$.mesures[*]'
        nested_fields = [
            {
                'prefix': 'CT_',
                'child_path': 'contexte[*].grandeur[*].calendrier[*].classeTemporelle[*]',
                'id_field': 'idClasseTemporelle',
                'value_field': 'quantite[0].quantite',
                'additional_fields': {
                    'libelleClasseTemporelle': 'libelleClasseTemporelle',
                    'dateCreation': 'quantite[0].dateCreation',
                    'codeNature': 'quantite[0].codeNature'
                }
            }
        ]
        
        df = json_to_dataframe(json_path, row_level, nested_fields=nested_fields)
        
        assert not df.empty
        
        # Vérifier les champs additionnels
        assert 'CT_libelleClasseTemporelle' in df.columns
        assert 'CT_dateCreation' in df.columns
        assert 'CT_codeNature' in df.columns
        
        # Vérifier les valeurs
        first_row = df.iloc[0]
        assert first_row['CT_libelleClasseTemporelle'] == 'Heures Pleines'  # La première classe temporelle
        assert first_row['CT_dateCreation'] == '2024-02-01T08:00:00'
        assert first_row['CT_codeNature'] == 'REEL'
    
    def test_missing_fields(self, fixtures_path):
        """Test le comportement avec des champs manquants."""
        json_path = fixtures_path / "rx5_minimal.json"
        row_level = '$.mesures[*]'
        data_fields = {
            'pdl': 'idPrm',
            'champInexistant': 'champQuiNexistePas',
            'etapeMetier': 'contexte[0].etapeMetier'
        }
        
        df = json_to_dataframe(json_path, row_level, data_fields=data_fields)
        
        assert not df.empty
        assert 'champInexistant' in df.columns
        assert df['champInexistant'].iloc[0] is None
        assert df['pdl'].iloc[0] == '12345678901234'
    
    def test_invalid_json_path(self, fixtures_path):
        """Test le comportement avec des expressions JSONPath invalides."""
        json_path = fixtures_path / "rx5_minimal.json"
        row_level = '$.mesures[*]'
        metadata_fields = {
            'invalidField': '$.invalid[invalid'  # JSONPath invalide
        }
        data_fields = {
            'pdl': 'idPrm'  # Ajout d'un champ valide pour avoir des données
        }
        
        # Ne devrait pas planter, mais le champ ne sera pas extrait
        df = json_to_dataframe(json_path, row_level, metadata_fields=metadata_fields, data_fields=data_fields)
        
        assert not df.empty
        # Le champ invalide ne devrait pas être présent ou être None
        if 'invalidField' in df.columns:
            assert df['invalidField'].iloc[0] is None
        # Le champ valide devrait être extrait correctement
        assert 'pdl' in df.columns
        assert df['pdl'].iloc[0] == '12345678901234'
    
    def test_empty_json_array(self, tmp_path):
        """Test le comportement avec un array vide."""
        json_data = {
            "header": {"codeFlux": "RX5"},
            "mesures": []
        }
        
        json_path = tmp_path / "empty_measures.json"
        with open(json_path, 'w') as f:
            json.dump(json_data, f)
        
        row_level = '$.mesures[*]'
        df = json_to_dataframe(json_path, row_level)
        
        assert df.empty
    
    def test_complex_rx5_structure(self, fixtures_path):
        """Test le parsing d'une structure RX5 complète."""
        json_path = fixtures_path / "rx5_xsd_compliant.json"
        row_level = '$.mesures[*]'
        metadata_fields = {
            'siDemandeur': '$.header.siDemandeur',
            'codeFlux': '$.header.codeFlux',
            'idDemande': '$.header.idDemande'
        }
        data_fields = {
            'pdl': 'idPrm',
            'dateDebut': 'periode.dateDebut',
            'dateFin': 'periode.dateFin',
            'etapeMetier': 'contexte[0].etapeMetier',
            'idMotifReleve': 'contexte[0].idMotifReleve',
            'grandeurMetier': 'contexte[0].grandeur[0].grandeurMetier',
            'unite': 'contexte[0].grandeur[0].unite'
        }
        nested_fields = [
            {
                'prefix': 'CT_',
                'child_path': 'contexte[*].grandeur[*].calendrier[*].classeTemporelle[*]',
                'id_field': 'idClasseTemporelle',
                'value_field': 'quantite[0].quantite',
                'additional_fields': {
                    'libelleClasseTemporelle': 'libelleClasseTemporelle',
                    'codeNature': 'quantite[0].codeNature',
                    'codeStatut': 'quantite[0].codeStatut'
                }
            }
        ]
        
        df = json_to_dataframe(json_path, row_level, metadata_fields, data_fields, nested_fields)
        
        assert not df.empty
        assert len(df) == 2
        
        # Vérifier les métadonnées
        assert df['siDemandeur'].iloc[0] == 'SYSTEM001'
        assert df['codeFlux'].iloc[0] == 'RX5'
        
        # Vérifier les données
        assert df['pdl'].iloc[0] == '12345678901234'
        assert df['grandeurMetier'].iloc[0] == 'ENERGIE_ACTIVE_SOUTIRAGE'
        assert df['unite'].iloc[0] == 'kWh'
        
        # Vérifier les champs imbriqués
        assert 'CT_HP' in df.columns
        assert 'CT_HC' in df.columns
        assert 'CT_BASE' in df.columns
        
        first_row = df.iloc[0]
        assert first_row['CT_HP'] == '1587'
        assert first_row['CT_HC'] == '3421'
        assert first_row['CT_libelleClasseTemporelle'] == 'Heures Pleines'
        assert first_row['CT_codeNature'] == 'REEL'


class TestFindJsonFiles:
    """Tests pour la fonction find_json_files."""
    
    def test_find_json_files_basic(self, tmp_path):
        """Test la recherche basique de fichiers JSON."""
        # Créer des fichiers de test
        (tmp_path / "test1.json").touch()
        (tmp_path / "test2.json").touch()
        (tmp_path / "test.xml").touch()  # Ne devrait pas être trouvé
        
        files = find_json_files(tmp_path)
        
        assert len(files) == 2
        assert all(f.suffix == '.json' for f in files)
        assert any(f.name == 'test1.json' for f in files)
        assert any(f.name == 'test2.json' for f in files)
    
    def test_find_json_files_with_pattern(self, tmp_path):
        """Test la recherche avec un pattern regex."""
        # Créer des fichiers de test
        (tmp_path / "RX5_001_123.json").touch()
        (tmp_path / "RX5_002_456.json").touch()
        (tmp_path / "OTHER_001.json").touch()
        
        files = find_json_files(tmp_path, file_pattern=r'RX5_\d+_\d+\.json$')
        
        assert len(files) == 2
        assert all('RX5_' in f.name for f in files)
        assert not any('OTHER_' in f.name for f in files)
    
    def test_find_json_files_with_exclusion(self, tmp_path):
        """Test la recherche avec exclusion de fichiers."""
        # Créer des fichiers de test
        (tmp_path / "file1.json").touch()
        (tmp_path / "file2.json").touch()
        (tmp_path / "file3.json").touch()
        
        files = find_json_files(tmp_path, exclude_files={'file2.json'})
        
        assert len(files) == 2
        assert not any(f.name == 'file2.json' for f in files)
        assert any(f.name == 'file1.json' for f in files)
        assert any(f.name == 'file3.json' for f in files)


class TestProcessJsonFiles:
    """Tests pour la fonction process_json_files."""
    
    def test_process_json_files_basic(self, fixtures_path):
        """Test le traitement basique de fichiers JSON."""
        json_files = [fixtures_path / "rx5_minimal.json"]
        row_level = '$.mesures[*]'
        data_fields = {
            'pdl': 'idPrm',
            'dateDebut': 'periode.dateDebut'
        }
        
        df = process_json_files(json_files, row_level, data_fields=data_fields)
        
        assert not df.empty
        assert len(df) == 2  # 2 mesures dans rx5_minimal.json
        assert 'pdl' in df.columns
        assert 'dateDebut' in df.columns
    
    def test_process_json_files_multiple(self, fixtures_path):
        """Test le traitement de plusieurs fichiers JSON."""
        json_files = [
            fixtures_path / "rx5_minimal.json",
            fixtures_path / "rx5_xsd_compliant.json"
        ]
        row_level = '$.mesures[*]'
        data_fields = {
            'pdl': 'idPrm',
            'dateDebut': 'periode.dateDebut'
        }
        
        df = process_json_files(json_files, row_level, data_fields=data_fields)
        
        assert not df.empty
        assert len(df) == 4  # 2 mesures dans chaque fichier
        assert 'pdl' in df.columns
        assert 'dateDebut' in df.columns
    
    def test_process_json_files_empty_list(self):
        """Test le traitement d'une liste vide de fichiers."""
        df = process_json_files([], '$.mesures[*]')
        
        assert df.empty
    
    def test_process_json_files_with_error(self, tmp_path):
        """Test le traitement avec un fichier JSON invalide."""
        # Créer un fichier JSON invalide
        invalid_json = tmp_path / "invalid.json"
        invalid_json.write_text("{ invalid json")
        
        json_files = [invalid_json]
        row_level = '$.mesures[*]'
        
        df = process_json_files(json_files, row_level)
        
        assert df.empty  # Devrait retourner un DataFrame vide en cas d'erreur