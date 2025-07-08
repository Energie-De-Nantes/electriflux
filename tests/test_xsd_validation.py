import pytest
from pathlib import Path
from lxml import etree
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestXSDValidation:
    """Tests de validation XSD pour les fixtures."""
    
    @pytest.fixture
    def xsd_paths(self):
        """Retourne les chemins vers les XSD officiels."""
        doc_path = Path(__file__).parent.parent / "doc"
        return {
            'c15': doc_path / "Cxx" / "GRD.XSD.0301.Flux_C15_v5.1.0.xsd",
            'f12_detail': doc_path / "Fxx" / "Enedis.SGE.XSD.0126.F12_Donnees_Detail_1.10.4.xsd",
            'f15_detail': doc_path / "Fxx" / "GRD.XSD.0299.Flux_F15_Donnees_Detail_v4.0.3.xsd",
            'r15': doc_path / "Rxx" / "ENEDIS.SGE.XSD.0293.Flux_R15_v2.3.2.xsd",
            'r151': doc_path / "Rxx" / "Enedis.SGE.XSD.0315.Flux_R151_v1.2.0.xsd"
        }
    
    @pytest.fixture  
    def fixture_paths(self, fixtures_path):
        """Retourne les chemins vers les fixtures XSD-compliant."""
        return {
            'c15': fixtures_path / "c15_xsd_compliant.xml",
            'f12': fixtures_path / "f12_xsd_compliant.xml", 
            'f15': fixtures_path / "f15_xsd_compliant.xml",
            'r15': fixtures_path / "r15_xsd_compliant.xml",
            'r151': fixtures_path / "r151_xsd_compliant.xml"
        }
    
    def validate_xml_against_xsd(self, xml_path, xsd_path):
        """Valide un fichier XML contre un XSD."""
        try:
            # Parser le XSD
            with open(xsd_path, 'r', encoding='utf-8') as xsd_file:
                xsd_doc = etree.parse(xsd_file)
                xsd_schema = etree.XMLSchema(xsd_doc)
            
            # Parser le XML
            with open(xml_path, 'r', encoding='utf-8') as xml_file:
                xml_doc = etree.parse(xml_file)
            
            # Valider
            is_valid = xsd_schema.validate(xml_doc)
            
            if not is_valid:
                # Retourner les erreurs pour debug
                errors = []
                for error in xsd_schema.error_log:
                    errors.append(f"Line {error.line}: {error.message}")
                return False, errors
            
            return True, []
            
        except Exception as e:
            return False, [f"Exception during validation: {str(e)}"]
    
    def test_c15_xsd_validation(self, xsd_paths, fixture_paths):
        """Test de validation XSD pour C15."""
        if not xsd_paths['c15'].exists():
            pytest.skip(f"XSD file not found: {xsd_paths['c15']}")
        
        is_valid, errors = self.validate_xml_against_xsd(
            fixture_paths['c15'], 
            xsd_paths['c15']
        )
        
        if not is_valid:
            pytest.fail(f"C15 fixture validation failed:\n" + "\n".join(errors))
    
    def test_f12_xsd_validation(self, xsd_paths, fixture_paths):
        """Test de validation XSD pour F12."""
        if not xsd_paths['f12_detail'].exists():
            pytest.skip(f"XSD file not found: {xsd_paths['f12_detail']}")
        
        is_valid, errors = self.validate_xml_against_xsd(
            fixture_paths['f12'], 
            xsd_paths['f12_detail']
        )
        
        if not is_valid:
            pytest.fail(f"F12 fixture validation failed:\n" + "\n".join(errors))
    
    def test_f15_xsd_validation(self, xsd_paths, fixture_paths):
        """Test de validation XSD pour F15."""
        if not xsd_paths['f15_detail'].exists():
            pytest.skip(f"XSD file not found: {xsd_paths['f15_detail']}")
        
        is_valid, errors = self.validate_xml_against_xsd(
            fixture_paths['f15'], 
            xsd_paths['f15_detail']
        )
        
        if not is_valid:
            pytest.fail(f"F15 fixture validation failed:\n" + "\n".join(errors))
    
    def test_r15_xsd_validation(self, xsd_paths, fixture_paths):
        """Test de validation XSD pour R15."""
        if not xsd_paths['r15'].exists():
            pytest.skip(f"XSD file not found: {xsd_paths['r15']}")
        
        is_valid, errors = self.validate_xml_against_xsd(
            fixture_paths['r15'], 
            xsd_paths['r15']
        )
        
        if not is_valid:
            pytest.fail(f"R15 fixture validation failed:\n" + "\n".join(errors))
    
    def test_r151_xsd_validation(self, xsd_paths, fixture_paths):
        """Test de validation XSD pour R151."""
        if not xsd_paths['r151'].exists():
            pytest.skip(f"XSD file not found: {xsd_paths['r151']}")
        
        is_valid, errors = self.validate_xml_against_xsd(
            fixture_paths['r151'], 
            xsd_paths['r151']
        )
        
        if not is_valid:
            pytest.fail(f"R151 fixture validation failed:\n" + "\n".join(errors))
    
    def test_all_fixtures_exist(self, fixture_paths):
        """Vérifie que toutes les fixtures XSD-compliant existent."""
        missing_fixtures = []
        for flux_type, path in fixture_paths.items():
            if not path.exists():
                missing_fixtures.append(f"{flux_type}: {path}")
        
        if missing_fixtures:
            pytest.fail(f"Missing XSD-compliant fixtures:\n" + "\n".join(missing_fixtures))
    
    def test_all_xsd_files_exist(self, xsd_paths):
        """Vérifie que tous les XSD sont disponibles."""
        missing_xsd = []
        for flux_type, path in xsd_paths.items():
            if not path.exists():
                missing_xsd.append(f"{flux_type}: {path}")
        
        if missing_xsd:
            pytest.skip(f"Missing XSD files (tests will be skipped):\n" + "\n".join(missing_xsd))


class TestStructuralCompliance:
    """Tests de conformité structurelle sans validation XSD complète."""
    
    def test_c15_root_element(self, fixtures_path):
        """Vérifie que C15 utilise le bon élément racine."""
        xml_path = fixtures_path / "c15_xsd_compliant.xml"
        tree = etree.parse(xml_path)
        assert tree.getroot().tag == "C15"
    
    def test_f12_root_element(self, fixtures_path):
        """Vérifie que F12 utilise le bon élément racine."""
        xml_path = fixtures_path / "f12_xsd_compliant.xml"
        tree = etree.parse(xml_path)
        assert tree.getroot().tag == "Detail_Facturation"
    
    def test_f15_root_element(self, fixtures_path):
        """Vérifie que F15 utilise le bon élément racine."""
        xml_path = fixtures_path / "f15_xsd_compliant.xml"
        tree = etree.parse(xml_path)
        assert tree.getroot().tag == "F15_Detail_Facturation"
    
    def test_r15_root_element(self, fixtures_path):
        """Vérifie que R15 utilise le bon élément racine."""
        xml_path = fixtures_path / "r15_xsd_compliant.xml"
        tree = etree.parse(xml_path)
        assert tree.getroot().tag == "R15"
    
    def test_r151_root_element(self, fixtures_path):
        """Vérifie que R151 utilise le bon élément racine."""
        xml_path = fixtures_path / "r151_xsd_compliant.xml"
        tree = etree.parse(xml_path)
        assert tree.getroot().tag == "R151"
    
    def test_all_have_en_tete_flux(self, fixtures_path):
        """Vérifie que toutes les fixtures ont un En_Tete_Flux."""
        fixtures = [
            "c15_xsd_compliant.xml",
            "f12_xsd_compliant.xml", 
            "f15_xsd_compliant.xml",
            "r15_xsd_compliant.xml",
            "r151_xsd_compliant.xml"
        ]
        
        for fixture_name in fixtures:
            xml_path = fixtures_path / fixture_name
            tree = etree.parse(xml_path)
            en_tete = tree.find('.//En_Tete_Flux')
            assert en_tete is not None, f"Missing En_Tete_Flux in {fixture_name}"
            
            # Vérifier les champs obligatoires
            identifiant_flux = en_tete.find('Identifiant_Flux')
            assert identifiant_flux is not None, f"Missing Identifiant_Flux in {fixture_name}"
            assert identifiant_flux.text is not None, f"Empty Identifiant_Flux in {fixture_name}"