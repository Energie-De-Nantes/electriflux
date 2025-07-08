import pytest
import pandas as pd
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from electriflux.simple_reader import xml_to_dataframe


class TestXmlToDataframe:
    """Tests pour la fonction xml_to_dataframe."""
    
    def test_basic_parsing(self, fixtures_path):
        """Test le parsing basique d'un fichier XML."""
        xml_path = fixtures_path / "r15_minimal.xml"
        row_level = './/PRM'
        metadata_fields = {'Unité': 'En_Tete_Flux/Unite_Mesure_Index'}
        data_fields = {
            'pdl': 'Id_PRM',
            'Date_Releve': 'Donnees_Releve/Date_Releve',
            'Type_Compteur': 'Donnees_Releve/Type_Compteur'
        }
        
        df = xml_to_dataframe(xml_path, row_level, metadata_fields, data_fields)
        
        # Vérifications
        assert not df.empty
        assert len(df) == 3  # 3 PRM dans le fichier
        assert 'pdl' in df.columns
        assert 'Date_Releve' in df.columns
        assert 'Type_Compteur' in df.columns
        assert 'Unité' in df.columns
        
        # Vérifier les valeurs
        assert df['Unité'].iloc[0] == 'KWH'
        assert df['pdl'].iloc[0] == '12345678901234'
        assert df['Type_Compteur'].iloc[1] == 'ELECTRONIQUE'
    
    def test_nested_fields(self, fixtures_path):
        """Test l'extraction des champs imbriqués."""
        xml_path = fixtures_path / "r15_minimal.xml"
        row_level = './/PRM'
        nested_fields = [
            {
                'prefix': '',
                'child_path': 'Donnees_Releve/Classe_Temporelle_Distributeur',
                'id_field': 'Id_Classe_Temporelle',
                'value_field': 'Valeur'
            }
        ]
        
        df = xml_to_dataframe(xml_path, row_level, data_fields={'pdl': 'Id_PRM'}, nested_fields=nested_fields)
        
        # Vérifier que les colonnes des classes temporelles existent
        assert 'HP' in df.columns
        assert 'HC' in df.columns
        assert 'BASE' in df.columns
        
        # Vérifier les valeurs
        assert df.loc[df['pdl'] == '12345678901234', 'HP'].iloc[0] == '12500'
        assert df.loc[df['pdl'] == '12345678901234', 'HC'].iloc[0] == '8900'
        assert df.loc[df['pdl'] == '98765432109876', 'BASE'].iloc[0] == '45000'
    
    def test_nested_fields_with_conditions(self, fixtures_path):
        """Test l'extraction des champs imbriqués avec conditions."""
        xml_path = fixtures_path / "c15_minimal.xml"
        row_level = './/PRM'
        nested_fields = [
            {
                'prefix': 'Avant_',
                'child_path': 'Evenement_Declencheur/Releves/Donnees_Releve/Classe_Temporelle_Distributeur',
                'id_field': 'Id_Classe_Temporelle',
                'value_field': 'Valeur',
                'conditions': [
                    {'xpath': '../Code_Qualification', 'value': '1'},
                    {'xpath': 'Classe_Mesure', 'value': '1'}
                ]
            },
            {
                'prefix': 'Après_',
                'child_path': 'Evenement_Declencheur/Releves/Donnees_Releve/Classe_Temporelle_Distributeur',
                'id_field': 'Id_Classe_Temporelle',
                'value_field': 'Valeur',
                'conditions': [
                    {'xpath': '../Code_Qualification', 'value': '2'},
                    {'xpath': 'Classe_Mesure', 'value': '1'}
                ]
            }
        ]
        
        df = xml_to_dataframe(xml_path, row_level, data_fields={'pdl': 'Id_PRM'}, nested_fields=nested_fields)
        
        # Vérifier les colonnes avec préfixes
        assert 'Avant_HP' in df.columns
        assert 'Avant_HC' in df.columns
        assert 'Après_HP' in df.columns
        assert 'Après_HC' in df.columns
        
        # Vérifier que les conditions sont respectées
        first_row = df.iloc[0]
        assert first_row['Avant_HP'] == '1234'
        assert first_row['Avant_HC'] == '5678'
        assert first_row['Après_HP'] == '1250'
        assert first_row['Après_HC'] == '5700'
    
    def test_nested_fields_with_additional_fields(self, fixtures_path):
        """Test l'extraction de champs additionnels dans les nested fields."""
        xml_path = fixtures_path / "c15_minimal.xml"
        row_level = './/PRM'
        nested_fields = [
            {
                'prefix': 'Avant_',
                'child_path': 'Evenement_Declencheur/Releves/Donnees_Releve/Classe_Temporelle_Distributeur',
                'id_field': 'Id_Classe_Temporelle',
                'value_field': 'Valeur',
                'conditions': [
                    {'xpath': '../Code_Qualification', 'value': '1'}
                ],
                'additional_fields': {
                    'Date_Releve': '../Date_Releve',
                    'Nature_Index': '../Nature_Index'
                }
            }
        ]
        
        df = xml_to_dataframe(xml_path, row_level, data_fields={'pdl': 'Id_PRM'}, nested_fields=nested_fields)
        
        # Vérifier les champs additionnels
        assert 'Avant_Date_Releve' in df.columns
        assert 'Avant_Nature_Index' in df.columns
        
        first_row = df.iloc[0]
        assert first_row['Avant_Date_Releve'] == '2024-01-10'
        assert first_row['Avant_Nature_Index'] == 'REEL'
    
    def test_empty_xml(self, fixtures_path):
        """Test avec un fichier XML vide."""
        xml_path = fixtures_path / "empty.xml"
        row_level = './/NonExistent'
        
        df = xml_to_dataframe(xml_path, row_level, data_fields={'id': 'Id'})
        
        assert df.empty
        assert len(df) == 0
    
    def test_missing_fields(self, fixtures_path):
        """Test avec des champs manquants dans le XML."""
        xml_path = fixtures_path / "r15_minimal.xml"
        row_level = './/PRM'
        data_fields = {
            'pdl': 'Id_PRM',
            'missing_field': 'NonExistent/Field'
        }
        
        df = xml_to_dataframe(xml_path, row_level, data_fields=data_fields)
        
        assert not df.empty
        assert 'pdl' in df.columns
        assert 'missing_field' in df.columns
        assert df['missing_field'].isna().all()
    
    def test_complex_f12_structure(self, fixtures_path):
        """Test avec la structure complexe du flux F12."""
        xml_path = fixtures_path / "f12_minimal.xml"
        row_level = './/Element_Valorise'
        metadata_fields = {
            'Flux': 'En_Tete_Flux/Identifiant_Flux',
            'Num_Facture': 'Rappel_En_Tete/Num_Facture',
            'Date_Facture': 'Rappel_En_Tete/Date_Facture'
        }
        data_fields = {
            'pdl': '../Id_PRM',
            'Id_EV': 'Id_EV',
            'Quantite': 'Acheminement/Quantite',
            'Montant_HT': 'Acheminement/Montant_HT'
        }
        
        df = xml_to_dataframe(xml_path, row_level, metadata_fields, data_fields)
        
        assert len(df) == 3  # 3 éléments valorisés
        assert df['Flux'].iloc[0] == 'F12_202401_001'
        assert df['Num_Facture'].iloc[0] == 'FACT123456'
        assert df['pdl'].iloc[0] == '12345678901234'
        assert float(df['Montant_HT'].iloc[0]) == 13.95
    
    def test_complex_f15_structure(self, fixtures_path):
        """Test avec la structure complexe du flux F15."""
        xml_path = fixtures_path / "f15_minimal.xml"
        row_level = './/Element_Valorise'
        metadata_fields = {
            'Flux': 'En_Tete_Flux/Identifiant_Flux',
            'Date_Facture': 'Rappel_En_Tete/Date_Facture'
        }
        data_fields = {
            'pdl': '../../Donnees_PRM/Id_PRM',
            'Type_Facturation': '../../../Type_Facturation',
            'Id_EV': 'Id_EV',
            'Nature_EV': '../Nature_EV',
            'Quantite': 'Quantite',
            'Montant_HT': 'Montant_HT'
        }
        
        df = xml_to_dataframe(xml_path, row_level, metadata_fields, data_fields)
        
        assert len(df) == 4  # 4 éléments valorisés
        assert df['Type_Facturation'].iloc[0] == 'NORMALE'
        assert df['Nature_EV'].iloc[0] == 'CONSOMMATION'
        assert float(df['Quantite'].iloc[-1]) == -50  # Rectification négative
    
    def test_invalid_xml(self, fixtures_path):
        """Test avec un fichier XML invalide."""
        xml_path = fixtures_path / "invalid.xml"
        row_level = './/Data'
        
        with pytest.raises(Exception):  # lxml devrait lever une exception
            xml_to_dataframe(xml_path, row_level, data_fields={'data': 'text()'})
    
    def test_performance_with_multiple_rows(self, fixtures_path):
        """Test de performance avec plusieurs lignes."""
        xml_path = fixtures_path / "r151_minimal.xml"
        row_level = './/PRM'
        data_fields = {'pdl': 'Id_PRM'}
        nested_fields = [
            {
                'prefix': '',
                'child_path': 'Donnees_Releve/Classe_Temporelle_Distributeur',
                'id_field': 'Id_Classe_Temporelle',
                'value_field': 'Valeur'
            }
        ]
        
        df = xml_to_dataframe(xml_path, row_level, data_fields=data_fields, nested_fields=nested_fields)
        
        # Vérifier que toutes les lignes sont traitées
        assert len(df) == 3
        
        # Vérifier que le dernier PRM a bien toutes ses classes temporelles
        last_row = df[df['pdl'] == '22222222222222'].iloc[0]
        assert last_row['HPH'] == '6000'
        assert last_row['HCH'] == '4000'
        assert last_row['HPB'] == '5500'
        assert last_row['HCB'] == '3500'