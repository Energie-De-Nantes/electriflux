import pytest
import pandas as pd
from pathlib import Path
import tempfile
import shutil
from unittest.mock import patch, MagicMock
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from electriflux.simple_reader import (
    load_flux_config, process_flux, find_xml_files, process_xml_files,
    load_history, append_to_history, load_data, append_to_data,
    reset_flux, iterative_process_flux, get_consumption_names
)


class TestConfigLoading:
    """Tests pour le chargement des configurations."""
    
    def test_load_flux_config_valid(self, sample_config_path):
        """Test le chargement d'une configuration valide."""
        config = load_flux_config('C15', sample_config_path)
        
        assert config['row_level'] == './/PRM'
        assert 'pdl' in config['data_fields']
        assert isinstance(config['nested_fields'], list)
    
    def test_load_flux_config_invalid_flux(self, sample_config_path):
        """Test avec un type de flux invalide."""
        with pytest.raises(ValueError, match="Unknown flux type"):
            load_flux_config('INVALID_FLUX', sample_config_path)
    
    def test_load_flux_config_missing_file(self):
        """Test avec un fichier de configuration manquant."""
        with pytest.raises(FileNotFoundError):
            load_flux_config('C15', Path('/nonexistent/config.yaml'))


class TestFileOperations:
    """Tests pour les opérations sur les fichiers."""
    
    def test_find_xml_files_basic(self, temp_dir):
        """Test la recherche basique de fichiers XML."""
        # Créer quelques fichiers de test
        (temp_dir / "test1.xml").touch()
        (temp_dir / "test2.xml").touch()
        (temp_dir / "test.txt").touch()
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        (subdir / "test3.xml").touch()
        
        files = find_xml_files(temp_dir)
        
        assert len(files) == 3
        assert all(f.suffix == '.xml' for f in files)
    
    def test_find_xml_files_with_pattern(self, temp_dir):
        """Test la recherche avec un motif regex."""
        (temp_dir / "FL_001_123.xml").touch()
        (temp_dir / "FL_002_456.xml").touch()
        (temp_dir / "OTHER_001.xml").touch()
        
        files = find_xml_files(temp_dir, file_pattern=r'FL_\d+_\d+\.xml$')
        
        assert len(files) == 2
        assert all('FL_' in f.name for f in files)
    
    def test_find_xml_files_with_exclusion(self, temp_dir):
        """Test la recherche avec exclusion de fichiers."""
        (temp_dir / "file1.xml").touch()
        (temp_dir / "file2.xml").touch()
        (temp_dir / "file3.xml").touch()
        
        files = find_xml_files(temp_dir, exclude_files={'file2.xml'})
        
        assert len(files) == 2
        assert not any(f.name == 'file2.xml' for f in files)


class TestHistoryManagement:
    """Tests pour la gestion de l'historique."""
    
    def test_load_history_new_file(self, temp_dir):
        """Test le chargement d'un historique inexistant."""
        history_path = temp_dir / "history.csv"
        history = load_history(history_path)
        
        assert history.empty
        assert list(history.columns) == ['file', 'processed_at']
    
    def test_load_history_existing_file(self, temp_dir):
        """Test le chargement d'un historique existant."""
        history_path = temp_dir / "history.csv"
        # Créer un historique de test
        df = pd.DataFrame({
            'file': ['test1.xml', 'test2.xml'],
            'processed_at': ['2024-01-01T12:00:00', '2024-01-02T12:00:00']
        })
        df.to_csv(history_path, index=False)
        
        history = load_history(history_path)
        
        assert len(history) == 2
        assert history['file'].iloc[0] == 'test1.xml'
    
    def test_append_to_history(self, temp_dir):
        """Test l'ajout à l'historique."""
        history_path = temp_dir / "history.csv"
        files = [Path("test1.xml"), Path("test2.xml")]
        
        append_to_history(history_path, files)
        
        history = pd.read_csv(history_path)
        assert len(history) == 2
        assert set(history['file']) == {'test1.xml', 'test2.xml'}
        assert 'processed_at' in history.columns


class TestDataManagement:
    """Tests pour la gestion des données."""
    
    def test_load_data_new_file(self, temp_dir):
        """Test le chargement de données inexistantes."""
        data_path = temp_dir / "data.csv"
        data = load_data(data_path)
        
        assert data.empty
    
    def test_append_to_data(self, temp_dir):
        """Test l'ajout de données."""
        data_path = temp_dir / "data.csv"
        new_data = pd.DataFrame({
            'pdl': ['123', '456'],
            'value': ['10', '20']
        })
        
        result = append_to_data(data_path, new_data)
        
        assert len(result) == 2
        assert data_path.exists()
        
        # Vérifier que les données sont bien sauvegardées
        saved_data = pd.read_csv(data_path, dtype=str)
        assert saved_data.equals(result)
    
    def test_append_to_data_existing(self, temp_dir):
        """Test l'ajout à des données existantes."""
        data_path = temp_dir / "data.csv"
        # Créer des données existantes
        old_data = pd.DataFrame({
            'pdl': ['111', '222'],
            'value': ['5', '15']
        })
        old_data.to_csv(data_path, index=False)
        
        # Ajouter de nouvelles données
        new_data = pd.DataFrame({
            'pdl': ['333', '444'],
            'value': ['25', '35']
        })
        
        result = append_to_data(data_path, new_data)
        
        assert len(result) == 4
        assert result['pdl'].tolist() == ['111', '222', '333', '444']


class TestFluxReset:
    """Tests pour la réinitialisation des flux."""
    
    def test_reset_flux(self, temp_dir):
        """Test la suppression des fichiers de flux."""
        # Créer des fichiers à supprimer
        (temp_dir / "C15.csv").touch()
        (temp_dir / "history.csv").touch()
        
        reset_flux('C15', temp_dir)
        
        assert not (temp_dir / "C15.csv").exists()
        assert not (temp_dir / "history.csv").exists()
    
    def test_reset_flux_missing_files(self, temp_dir):
        """Test la réinitialisation sans fichiers existants."""
        # Ne devrait pas lever d'erreur
        reset_flux('C15', temp_dir)


class TestProcessFlux:
    """Tests pour le traitement des flux."""
    
    def test_process_flux_basic(self, fixtures_path, temp_dir):
        """Test le traitement basique d'un flux."""
        # Copier les fixtures dans le répertoire temporaire
        shutil.copy(fixtures_path / "r15_minimal.xml", temp_dir)
        
        # Créer une config minimale
        config_content = """
R15:
  row_level: './/PRM'
  metadata_fields:
    Unité: 'En_Tete_Flux/Unite_Mesure_Index'
  data_fields:
    pdl: 'Id_PRM'
    Date_Releve: 'Donnees_Releve/Date_Releve'
  nested_fields: []
"""
        config_path = temp_dir / "config.yaml"
        config_path.write_text(config_content)
        
        df = process_flux('R15', temp_dir, config_path)
        
        assert not df.empty
        assert len(df) == 3
        assert 'pdl' in df.columns
        assert 'Date_Releve' in df.columns
        assert 'Unité' in df.columns
    
    def test_process_flux_with_pattern(self, fixtures_path, temp_dir):
        """Test le traitement avec un motif de fichier."""
        # Copier plusieurs fichiers
        shutil.copy(fixtures_path / "f12_minimal.xml", temp_dir / "FL_001_123.xml")
        shutil.copy(fixtures_path / "f12_minimal.xml", temp_dir / "OTHER_001.xml")
        
        config_content = """
F12:
  file_regex: 'FL_\\d+_\\d+\\.xml$'
  row_level: './/Element_Valorise'
  metadata_fields: {}
  data_fields:
    Id_EV: 'Id_EV'
  nested_fields: []
"""
        config_path = temp_dir / "config.yaml"
        config_path.write_text(config_content)
        
        df = process_flux('F12', temp_dir, config_path)
        
        # Ne devrait traiter qu'un seul fichier (FL_001_123.xml)
        assert len(df) == 3  # 3 éléments dans le fichier F12
    
    @patch('electriflux.simple_reader.xml_to_dataframe')
    def test_process_flux_error_handling(self, mock_xml_to_df, temp_dir, caplog):
        """Test la gestion des erreurs lors du traitement."""
        (temp_dir / "test.xml").touch()
        
        # Simuler une erreur lors du parsing
        mock_xml_to_df.side_effect = Exception("Parsing error")
        
        config_content = """
TEST:
  row_level: './/Test'
  metadata_fields: {}
  data_fields: {}
  nested_fields: []
"""
        config_path = temp_dir / "config.yaml"
        config_path.write_text(config_content)
        
        df = process_flux('TEST', temp_dir, config_path)
        
        assert df.empty
        assert "Error processing" in caplog.text


class TestIterativeProcessFlux:
    """Tests pour le traitement itératif des flux."""
    
    def test_iterative_process_flux_first_run(self, fixtures_path, temp_dir):
        """Test le premier traitement itératif."""
        shutil.copy(fixtures_path / "r15_minimal.xml", temp_dir)
        
        config_content = """
R15:
  row_level: './/PRM'
  metadata_fields: {}
  data_fields:
    pdl: 'Id_PRM'
  nested_fields: []
"""
        config_path = temp_dir / "config.yaml"
        config_path.write_text(config_content)
        
        df = iterative_process_flux('R15', temp_dir, config_path)
        
        assert len(df) == 3
        assert (temp_dir / "R15.csv").exists()
        assert (temp_dir / "history.csv").exists()
        
        # Vérifier l'historique
        history = pd.read_csv(temp_dir / "history.csv")
        assert len(history) == 1
        assert history['file'].iloc[0] == 'r15_minimal.xml'
    
    def test_iterative_process_flux_incremental(self, fixtures_path, temp_dir):
        """Test le traitement incrémental."""
        # Premier traitement
        shutil.copy(fixtures_path / "r15_minimal.xml", temp_dir / "file1.xml")
        
        config_content = """
R15:
  row_level: './/PRM'
  metadata_fields: {}
  data_fields:
    pdl: 'Id_PRM'
  nested_fields: []
"""
        config_path = temp_dir / "config.yaml"
        config_path.write_text(config_content)
        
        df1 = iterative_process_flux('R15', temp_dir, config_path)
        initial_count = len(df1)
        
        # Ajouter un nouveau fichier
        shutil.copy(fixtures_path / "r15_minimal.xml", temp_dir / "file2.xml")
        
        # Deuxième traitement
        df2 = iterative_process_flux('R15', temp_dir, config_path)
        
        # Devrait avoir le double de lignes
        assert len(df2) == initial_count * 2
        
        # Vérifier l'historique
        history = pd.read_csv(temp_dir / "history.csv")
        assert len(history) == 2
        assert set(history['file']) == {'file1.xml', 'file2.xml'}


class TestUtilityFunctions:
    """Tests pour les fonctions utilitaires."""
    
    def test_get_consumption_names(self):
        """Test la récupération des noms de consommation."""
        names = get_consumption_names()
        
        assert isinstance(names, list)
        assert 'HP' in names
        assert 'HC' in names
        assert 'BASE' in names
        assert len(names) == 7  # HPH, HPB, HCH, HCB, HP, HC, BASE