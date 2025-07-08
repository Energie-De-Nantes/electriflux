import pytest
from pathlib import Path
import tempfile
import shutil

@pytest.fixture
def fixtures_path():
    """Retourne le chemin vers le dossier des fixtures."""
    return Path(__file__).parent / "fixtures"

@pytest.fixture
def temp_dir():
    """Crée un répertoire temporaire pour les tests."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

@pytest.fixture
def sample_config_path(temp_dir):
    """Crée un fichier de configuration temporaire pour les tests."""
    config_content = """
C15:
  row_level: './/PRM'
  metadata_fields: {}
  data_fields:
    pdl: Id_PRM
    Etat_Contractuel: Situation_Contractuelle/Etat_Contractuel
  nested_fields:
    - prefix: 'Test_'
      child_path: 'Evenement_Declencheur/Releves/Donnees_Releve/Classe_Temporelle_Distributeur'
      id_field: 'Id_Classe_Temporelle'
      value_field: 'Valeur'
      conditions:
        - xpath: 'Classe_Mesure'
          value: '1'

TEST_FLUX:
  row_level: './/TestRow'
  metadata_fields:
    meta_field: 'MetaData/Field'
  data_fields:
    id: 'Id'
    name: 'Name'
  nested_fields: []
"""
    config_path = temp_dir / "test_config.yaml"
    config_path.write_text(config_content)
    return config_path