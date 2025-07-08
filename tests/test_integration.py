import pytest
import pandas as pd
from pathlib import Path
import shutil
from pandas.testing import assert_frame_equal
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from electriflux.simple_reader import (
    process_flux, iterative_process_flux, reset_flux, 
    convert_flux, convert_flux_iterate, append_data
)


class TestIntegrationWorkflows:
    """Tests d'intégration pour les workflows complets."""
    
    def test_complete_c15_workflow(self, fixtures_path, temp_dir):
        """Test le workflow complet pour un flux C15."""
        # Copier la nouvelle fixture XSD-compliant
        shutil.copy(fixtures_path / "c15_xsd_compliant.xml", temp_dir)
        
        # Utiliser la configuration par défaut
        df = convert_flux('C15', temp_dir)
        
        # Vérifications complètes
        assert not df.empty
        assert len(df) == 2  # 2 PRM dans le fichier
        
        # Vérifier les métadonnées du flux
        assert df['Flux'].iloc[0] == 'C15'
        assert df['Version_XSD'].iloc[0] == '5.1.0'
        assert df['Nature_Contrat'].iloc[0] == 'Contrat de fourniture'
        
        # Vérifier les colonnes principales mises à jour
        expected_columns = [
            'pdl', 'Segment_Clientele', 'Categorie', 'Etat_Contractuel',
            'Puissance_Souscrite', 'Type_Compteur', 'Nature_Evenement',
            'Etat_Alimentation', 'Mode_Alimentation', 'Refus_Pose_AMM'
        ]
        for col in expected_columns:
            assert col in df.columns
        
        # Vérifier les colonnes des classes temporelles avec conditions
        assert 'Avant_HP' in df.columns
        assert 'Avant_HC' in df.columns
        assert 'Après_HP' in df.columns
        
        # Vérifier les valeurs avec la nouvelle structure
        first_row = df[df['pdl'] == '12345678901234'].iloc[0]
        assert first_row['Categorie'] == 'PARTICULIER'
        assert first_row['Type_Compteur'] == 'LINKY'
        assert first_row['Etat_Alimentation'] == 'ALIM'
        assert first_row['Refus_Pose_AMM'] == 'false'  # XSD boolean as string
        assert first_row['Avant_HP'] == '1234'
        assert first_row['Après_HP'] == '1250'
        
        # Vérifier le deuxième PRM
        second_row = df[df['pdl'] == '98765432109876'].iloc[0]
        assert second_row['Categorie'] == 'PROFESSIONNEL'
        assert second_row['Type_Compteur'] == 'ELECTRONIQUE'
        assert second_row['Mode_Alimentation'] == 'TRI'
        assert second_row['Autoproducteur'] == 'true'
    
    def test_complete_f12_workflow(self, fixtures_path, temp_dir):
        """Test le workflow complet pour un flux F12."""
        # Copier la nouvelle fixture XSD-compliant avec le bon pattern
        shutil.copy(fixtures_path / "f12_xsd_compliant.xml", temp_dir / "FL_001_123.xml")
        
        df = convert_flux('F12', temp_dir)
        
        assert not df.empty
        assert len(df) == 5  # 5 éléments valorisés dans la nouvelle fixture
        
        # Vérifier les métadonnées XSD-compliant
        assert df['Flux'].iloc[0] == 'F12'
        assert df['Version_XSD'].iloc[0] == '1.10.4'
        assert df['Identifiant_Emetteur'].iloc[0] == 'Enedis'
        assert df['Num_Facture'].iloc[0] == 'F240150001'
        assert df['Id_Contrat'].iloc[0] == '123456789'
        assert df['Devise'].iloc[0] == 'EUR'
        
        # Vérifier les données
        expected_ev_ids = ['TURPE_FIXE', 'TURPE_VAR', 'CTA', 'TURPE_FIXE', 'PRESTATIONS']
        assert df['Id_EV'].tolist() == expected_ev_ids
        
        # Vérifier les types de facturation
        assert df['Type_Facturation'].iloc[0] == 'CYCL'  # Cyclique
        assert df['Type_Facturation'].iloc[3] == 'RECT'  # Rectification
        
        # Vérifier les montants
        assert float(df['Montant_HT'].iloc[0]) == 13.96
        assert float(df['Montant_HT'].iloc[3]) == -13.51  # Rectification négative
        assert float(df['Montant_HT'].iloc[4]) == 50.00   # Prestation
        
        # Vérifier les agences ERDF conformes au pattern
        assert df['Agence_ERDF'].iloc[0] == '0321'
        assert df['Agence_ERDF'].iloc[3] == '0322'
        
        # Vérifier les tarifs souscrits
        assert df['Tarif_Souscrit'].iloc[0] == 'BTSUPLU'
        assert df['Tarif_Souscrit'].iloc[3] == 'HTA5'
    
    def test_complete_f15_workflow(self, fixtures_path, temp_dir):
        """Test le workflow complet pour un flux F15."""
        # Copier la nouvelle fixture XSD-compliant avec le pattern F15
        shutil.copy(fixtures_path / "f15_xsd_compliant.xml", temp_dir / "F15_001_456.xml")
        
        df = convert_flux('F15', temp_dir)
        
        assert not df.empty
        assert len(df) == 4  # 4 éléments valorisés dans la nouvelle fixture
        
        # Vérifier les métadonnées XSD-compliant
        assert df['Flux'].iloc[0] == 'F15'
        assert df['Version_XSD'].iloc[0] == '4.0.3'
        assert df['Identifiant_Emetteur'].iloc[0] == 'Enedis'
        assert df['Num_Facture'].iloc[0] == 'F150240001'
        assert df['Identifiant_Contrat'].iloc[0] == '987654321'
        assert df['Devise'].iloc[0] == 'EUR'
        
        # Vérifier la structure avec types XSD-compliant
        assert df['Type_Facturation'].iloc[0] == 'C'  # Cyclique (XSD value)
        assert df['Type_Facturation'].iloc[3] == 'R'  # Rectification (XSD value)
        assert df['Nature_EV'].iloc[0] == '01'  # Consommation (XSD value)
        assert df['Nature_EV'].iloc[2] == '04'  # Contributions (XSD value)
        
        # Vérifier les éléments valorisés
        expected_ev_ids = ['CONSO_HP', 'CONSO_HC', 'CSPE', 'CONSO_BASE']
        assert df['Id_EV'].tolist() == expected_ev_ids
        
        # Vérifier les PDL
        assert df['pdl'].iloc[0] == '12345678901234'
        assert df['pdl'].iloc[3] == '98765432109876'
        
        # Vérifier les nouveaux champs XSD
        assert df['Code_Type_TVA_Applicable'].iloc[0] == 'S'  # Soumis
        assert df['Code_Type_TVA_Applicable'].iloc[2] == 'E'  # Exonéré
        assert df['Categorie'].iloc[0] == 'CONSO'
        assert df['Categorie'].iloc[2] == 'CONTRIB'
        
        # Vérifier les montants
        assert float(df['Montant_HT'].iloc[0]) == 27.00
        assert float(df['Montant_HT'].iloc[3]) == -6.00  # Rectification négative
        
        # Vérifier les codes communes
        assert df['Code_Commune'].iloc[0] == '75001'
        assert df['Code_Departement'].iloc[0] == '75'
    
    def test_complete_r15_r151_workflows(self, fixtures_path, temp_dir):
        """Test les workflows R15 et R151."""
        # R15 avec nouvelle fixture XSD-compliant
        r15_dir = temp_dir / "r15"
        r15_dir.mkdir()
        shutil.copy(fixtures_path / "r15_xsd_compliant.xml", r15_dir)
        df_r15 = convert_flux('R15', r15_dir)
        
        # Vérifications R15
        assert len(df_r15) == 3
        assert df_r15['Flux'].iloc[0] == 'R15'
        assert df_r15['Version_XSD'].iloc[0] == '2.3.2'
        assert df_r15['Identifiant_Emetteur'].iloc[0] == 'ENEDIS'
        assert df_r15['Nature_Contrat'].iloc[0] == 'Contrat de fourniture'
        
        # Vérifier les classes temporelles avec nouveaux préfixes
        assert 'Dist_HP' in df_r15.columns
        assert 'Dist_HC' in df_r15.columns
        assert 'Dist_BASE' in df_r15.columns
        assert 'Temp_HP' in df_r15.columns
        assert 'Temp_HC' in df_r15.columns
        
        # Vérifier les valeurs
        assert df_r15[df_r15['pdl'] == '11111111111111']['Dist_HPH'].iloc[0] == '5000'
        assert df_r15[df_r15['pdl'] == '12345678901234']['Dist_HP'].iloc[0] == '12500'
        
        # R151 dans un répertoire séparé pour éviter la confusion
        r151_dir = temp_dir / "r151"
        r151_dir.mkdir()
        shutil.copy(fixtures_path / "r151_xsd_compliant.xml", r151_dir / "r151_test.xml")
        df_r151 = convert_flux('R151', r151_dir)
        
        # Vérifications R151
        assert len(df_r151) == 3
        assert df_r151['Flux'].iloc[0] == 'R151'
        assert df_r151['Version_XSD'].iloc[0] == '1.2.0'
        assert df_r151['Identifiant_Emetteur'].iloc[0] == 'ERDF'
        assert df_r151['Numero_Abonnement'].iloc[0] == 'ABO987654321'
        assert df_r151['Unite_Mesure_Index'].iloc[0] == 'kWh'
        
        # Vérifier les champs spécifiques R151
        assert 'Id_Calendrier_Fournisseur' in df_r151.columns
        assert 'Id_Calendrier_Distributeur' in df_r151.columns
        assert 'Puissance_Maximale' in df_r151.columns
        
        # Vérifier les valeurs spécifiques
        assert df_r151[df_r151['pdl'] == '22222222222222']['Dist_HPH'].iloc[0] == '6000'
        assert df_r151[df_r151['pdl'] == '12345678901234']['Puissance_Maximale'].iloc[0] == '6800'
    
    def test_iterative_workflow_with_history(self, fixtures_path, temp_dir):
        """Test le workflow itératif avec gestion de l'historique."""
        # Étape 1: Premier fichier
        shutil.copy(fixtures_path / "r15_minimal.xml", temp_dir / "batch1.xml")
        
        df1 = convert_flux_iterate('R15', temp_dir)
        assert len(df1) == 3
        assert (temp_dir / "R15.csv").exists()
        assert (temp_dir / "history.csv").exists()
        
        # Étape 2: Ajouter un deuxième fichier
        shutil.copy(fixtures_path / "r15_minimal.xml", temp_dir / "batch2.xml")
        
        df2 = convert_flux_iterate('R15', temp_dir)
        assert len(df2) == 6  # 3 + 3 lignes
        
        # Vérifier que batch1.xml n'est pas retraité
        history = pd.read_csv(temp_dir / "history.csv")
        assert len(history) == 2
        assert set(history['file']) == {'batch1.xml', 'batch2.xml'}
        
        # Étape 3: Relancer sans nouveau fichier
        df3 = convert_flux_iterate('R15', temp_dir)
        assert len(df3) == 6  # Pas de nouvelles données
    
    def test_reset_and_reprocess_workflow(self, fixtures_path, temp_dir):
        """Test la réinitialisation et le retraitement."""
        # Traitement initial
        shutil.copy(fixtures_path / "f12_minimal.xml", temp_dir / "FL_001_123.xml")
        df1 = convert_flux_iterate('F12', temp_dir)
        assert len(df1) == 3
        
        # Réinitialiser
        reset_flux('F12', temp_dir)
        assert not (temp_dir / "F12.csv").exists()
        assert not (temp_dir / "history.csv").exists()
        
        # Retraiter
        df2 = convert_flux_iterate('F12', temp_dir)
        assert len(df2) == 3
        assert_frame_equal(df1.sort_index(axis=1), df2.sort_index(axis=1))
    
    def test_append_data_workflow(self, fixtures_path, temp_dir):
        """Test le workflow d'ajout de données."""
        # Créer des données initiales
        initial_data = pd.DataFrame({
            'pdl': ['111', '222'],
            'value': ['10', '20']
        })
        data_path = temp_dir / "test_data.csv"
        initial_data.to_csv(data_path, index=False)
        
        # Ajouter de nouvelles données
        new_data = pd.DataFrame({
            'pdl': ['333', '444'],
            'value': ['30', '40']
        })
        
        result = append_data(data_path, new_data)
        
        # Vérifier le résultat
        assert len(result) == 4
        assert result['pdl'].tolist() == ['111', '222', '333', '444']
        
        # Vérifier la persistance
        saved_data = pd.read_csv(data_path, dtype=str)
        assert_frame_equal(result, saved_data)
    
    def test_mixed_flux_types_workflow(self, fixtures_path, temp_dir):
        """Test avec plusieurs types de flux dans le même répertoire."""
        # Créer des sous-répertoires pour chaque type
        c15_dir = temp_dir / "c15"
        r15_dir = temp_dir / "r15"
        f12_dir = temp_dir / "f12"
        c15_dir.mkdir()
        r15_dir.mkdir()
        f12_dir.mkdir()
        
        # Copier différents types de flux dans leurs répertoires
        shutil.copy(fixtures_path / "c15_minimal.xml", c15_dir)
        shutil.copy(fixtures_path / "r15_minimal.xml", r15_dir)
        shutil.copy(fixtures_path / "f12_minimal.xml", f12_dir / "FL_001_123.xml")
        
        # Traiter chaque type
        df_c15 = convert_flux('C15', c15_dir)
        df_r15 = convert_flux('R15', r15_dir)
        df_f12 = convert_flux('F12', f12_dir)
        
        # Vérifier que chaque flux est traité correctement
        assert len(df_c15) == 2  # Seulement C15
        assert len(df_r15) == 3  # Seulement R15
        assert len(df_f12) == 3  # Seulement F12 avec pattern
        
        # Vérifier que les colonnes sont différentes
        assert 'Avant_HP' in df_c15.columns
        assert 'Avant_HP' not in df_r15.columns
        assert 'Montant_HT' in df_f12.columns
        assert 'Montant_HT' not in df_c15.columns
    
    def test_error_recovery_workflow(self, fixtures_path, temp_dir, caplog):
        """Test la récupération après erreurs."""
        # Copier un fichier valide et un invalide
        shutil.copy(fixtures_path / "r15_minimal.xml", temp_dir / "valid.xml")
        shutil.copy(fixtures_path / "invalid.xml", temp_dir / "invalid.xml")
        
        # Le traitement devrait continuer malgré l'erreur
        df = convert_flux('R15', temp_dir)
        
        # Devrait traiter seulement le fichier valide
        assert len(df) == 3
        assert "Error processing" in caplog.text
    
    def test_performance_large_dataset(self, fixtures_path, temp_dir):
        """Test de performance avec plusieurs fichiers."""
        # Créer 10 copies du fichier R151
        for i in range(10):
            shutil.copy(
                fixtures_path / "r151_minimal.xml", 
                temp_dir / f"batch_{i:03d}.xml"
            )
        
        # Traiter tous les fichiers
        import time
        start_time = time.time()
        df = convert_flux('R151', temp_dir)
        elapsed_time = time.time() - start_time
        
        # Vérifier le résultat
        assert len(df) == 30  # 3 PRM * 10 fichiers
        assert elapsed_time < 5  # Devrait être rapide
        
        # Vérifier que toutes les classes temporelles sont présentes
        pdl_22 = df[df['pdl'] == '22222222222222']
        assert len(pdl_22) == 10  # Une ligne par fichier
        assert all(pdl_22['HPH'] == '6000')


# Alias pour la compatibilité avec les noms de fonctions
def test_convert_flux_alias():
    """Test que convert_flux est un alias de process_flux."""
    assert convert_flux == process_flux

def test_convert_flux_iterate_alias():
    """Test que convert_flux_iterate est un alias de iterative_process_flux."""
    assert convert_flux_iterate == iterative_process_flux