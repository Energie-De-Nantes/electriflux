# Gestion de l'évolution des versions XSD Enedis

## 🚨 Problème identifié

### Contexte
Lors des tests de validation XSD, nous avons découvert que les schémas Enedis subissent des **changements cassants** entre versions qui rendent les fichiers existants incompatibles avec les nouvelles versions XSD.

### Exemple concret : C15 v4.0.0 → v5.1.0
- **Fichier réel** : C15 v4.0.0 (structure utilisée en production)
- **XSD disponible** : C15 v5.1.0 (version plus récente)
- **Résultat** : Validation impossible, ordre des éléments différent, champs supprimés/ajoutés

### Impact sur electriflux
- **Configuration unique** : Un seul mapping par type de flux dans `simple_flux.yaml`
- **Pas de détection de version** : Tous les fichiers traités avec la même configuration
- **Risque de régression** : Changement de version peut casser le parsing des fichiers historiques

## 📊 Analyse des changements observés

### Types de changements cassants
1. **Ordre des éléments XML** : Séquence stricte dans les nouveaux XSD
2. **Champs supprimés** : Éléments présents en v4.0.0 mais absents en v5.1.0
3. **Champs ajoutés** : Nouveaux éléments obligatoires dans les versions récentes
4. **Contraintes renforcées** : Énumérations plus strictes, types de données modifiés

### Exemples C15 v4.0.0 → v5.1.0
```diff
- <Point_Sensible>0</Point_Sensible>         # Supprimé
- <Num_Depannage>0100000001</Num_Depannage> # Déplacé
- <Teleoperable>1</Teleoperable>            # Supprimé
+ <Autoproducteur>false</Autoproducteur>    # Position changée
```

## 🎯 Solutions proposées

### Solution 1 : Détection automatique de version + configurations multiples

**Principe** : Détecter automatiquement la version XSD du fichier et appliquer la configuration correspondante.

**Architecture** :
```yaml
# simple_flux.yaml
C15:
  versions:
    "4.0.0":
      row_level: './/PRM'
      metadata_fields:
        # Configuration v4.0.0
      data_fields:
        # Champs spécifiques v4.0.0
    "5.1.0":
      row_level: './/PRM'
      metadata_fields:
        # Configuration v5.1.0
      data_fields:
        # Champs spécifiques v5.1.0
```

**Avantages** :
- ✅ Rétro-compatibilité garantie
- ✅ Support natif des nouvelles versions
- ✅ Configuration explicite par version

**Inconvénients** :
- ❌ Multiplication des configurations à maintenir
- ❌ Complexité accrue du code de parsing

### Solution 2 : Adaptateur de compatibilité

**Principe** : Créer un adaptateur qui transforme les fichiers anciens vers un format standardisé.

**Architecture** :
```python
class VersionAdapter:
    def adapt_c15_v4_to_v5(self, xml_content: str) -> str:
        # Transformation des structures v4.0.0 → v5.1.0
        # Réorganisation des éléments
        # Mapping des champs renommés
```

**Avantages** :
- ✅ Configuration unique maintenue
- ✅ Transformation transparente
- ✅ Isolation de la logique de compatibilité

**Inconvénients** :
- ❌ Risque de perte d'information lors de la transformation
- ❌ Complexité des adaptateurs

### Solution 3 : Architecture modulaire avec plugins

**Principe** : Système de plugins par version avec interface commune.

**Architecture** :
```python
class FluxParserV4:
    def parse_c15(self, xml_path: Path) -> pd.DataFrame:
        # Logique spécifique v4.0.0

class FluxParserV5:
    def parse_c15(self, xml_path: Path) -> pd.DataFrame:
        # Logique spécifique v5.1.0

class FluxParserFactory:
    def get_parser(self, version: str) -> FluxParser:
        # Retourne le parser approprié
```

**Avantages** :
- ✅ Séparation claire des responsabilités
- ✅ Extensibilité pour nouvelles versions
- ✅ Tests isolés par version

**Inconvénients** :
- ❌ Refactoring majeur nécessaire
- ❌ Duplication de code entre versions

### Solution 4 : Migration progressive avec validation

**Principe** : Outil de migration + validation XSD optionnelle.

**Architecture** :
```python
def migrate_flux_files(directory: Path, target_version: str):
    # Migration automatique des fichiers
    # Validation XSD optionnelle
    # Rapport de migration
```

**Avantages** :
- ✅ Approche progressive
- ✅ Validation garantie
- ✅ Contrôle utilisateur

**Inconvénients** :
- ❌ Nécessite intervention manuelle
- ❌ Risque d'erreurs de migration

## 🛠️ Recommandation d'implémentation

### Approche recommandée : **Solution 1 + éléments de Solution 2**

**Phase 1 : Détection de version**
```python
def detect_flux_version(xml_path: Path) -> str:
    """Détecte la version XSD d'un fichier flux."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    version_elem = root.find('En_Tete_Flux/Version_XSD')
    return version_elem.text if version_elem is not None else 'unknown'
```

**Phase 2 : Configuration multi-versions**
```yaml
# simple_flux.yaml
C15:
  default_version: "5.1.0"
  versions:
    "4.0.0":
      # Configuration complète v4.0.0
    "5.1.0":
      # Configuration complète v5.1.0
```

**Phase 3 : Adaptateur pour champs manquants**
```python
class FieldCompatibilityAdapter:
    def adapt_fields(self, data: dict, from_version: str, to_version: str) -> dict:
        # Mapping des champs entre versions
        # Valeurs par défaut pour champs manquants
```

## 🔧 Modifications techniques nécessaires

### 1. Extension du fichier de configuration
```yaml
# Structure proposée
FLUX_TYPE:
  default_version: "version_par_defaut"
  versions:
    "version_1":
      row_level: "xpath"
      metadata_fields: {...}
      data_fields: {...}
      nested_fields: [...]
      compatibility:
        deprecated_fields: [...]
        renamed_fields: {...}
    "version_2":
      # Configuration version 2
```

### 2. Modification du parser principal
```python
# Dans simple_reader.py
def load_flux_config(flux_type: str, version: str = None, config_path: Path = None):
    """Charge la configuration pour un type de flux et une version donnée."""
    
def process_flux(flux_type: str, xml_dir: Path, version: str = None):
    """Traite les flux avec détection automatique de version."""
```

### 3. Nouveaux composants
- `version_detector.py` : Détection automatique de version
- `compatibility_adapter.py` : Adaptation entre versions
- `xsd_validator.py` : Validation XSD optionnelle

## 🧪 Stratégie de tests

### Tests par version
```python
def test_c15_v4_parsing():
    # Test parsing fichiers v4.0.0

def test_c15_v5_parsing():
    # Test parsing fichiers v5.1.0

def test_c15_version_detection():
    # Test détection automatique

def test_c15_compatibility_adapter():
    # Test adaptation entre versions
```

### Fixtures de test
- `c15_v4_sample.xml` : Fichier exemple v4.0.0
- `c15_v5_sample.xml` : Fichier exemple v5.1.0
- `c15_mixed_versions/` : Répertoire avec versions mixtes

## 📅 Roadmap d'implémentation

### Phase 1 : Fondations (2-3 semaines)
- [ ] Détection automatique de version
- [ ] Extension du format de configuration YAML
- [ ] Refactoring du parser principal

### Phase 2 : Configurations multi-versions (2-3 semaines)
- [ ] Configuration C15 v4.0.0 et v5.1.0
- [ ] Configuration F12, F15, R15, R151 (versions multiples)
- [ ] Tests complets par version

### Phase 3 : Adaptateurs de compatibilité (1-2 semaines)
- [ ] Adaptateur de champs manquants
- [ ] Mapping des champs renommés
- [ ] Validation optionnelle XSD

### Phase 4 : Documentation et migration (1 semaine)
- [ ] Guide de migration utilisateur
- [ ] Documentation API
- [ ] Exemples d'utilisation

## ⚠️ Risques et mitigation

### Risques identifiés
1. **Complexité accrue** : Gestion multiple versions
2. **Régression** : Changement de comportement existant
3. **Performance** : Détection de version sur chaque fichier
4. **Maintenance** : Plus de configurations à maintenir

### Mitigation
1. **Tests exhaustifs** : Couverture par version
2. **Migration progressive** : Rétro-compatibilité garantie
3. **Cache de version** : Optimisation des performances
4. **Génération automatique** : Outils pour créer les configurations

## 🔄 Migration utilisateur

### Étapes recommandées
1. **Audit** : Identifier les versions utilisées
2. **Test** : Valider le parsing avec la nouvelle version
3. **Migration** : Mise à jour progressive
4. **Validation** : Vérification des résultats

### Commandes proposées
```bash
# Audit des versions
electriflux audit-versions /path/to/flux/files

# Test de compatibilité
electriflux test-compatibility C15 /path/to/files

# Migration assistée
electriflux migrate-config --from 4.0.0 --to 5.1.0
```

## 📚 Ressources et références

### Documentation Enedis
- `doc/Cxx/Enedis SGE GUI 0300 Flux C15_v5.1.0.pdf`
- `doc/Fxx/Enedis.SGE.GUI.0298.Flux F15_v4.1.1.pdf`
- `doc/Rxx/Enedis.SGE.GUI.0292.Flux R15_soutirage_v3.0.4.pdf`

### Outils de validation
- Validateurs XSD officiels Enedis
- Outils de comparaison de schémas
- Générateurs de fixtures par version

---

**Note** : Ce mémo constitue une base de réflexion pour l'évolution d'electriflux. L'implémentation devra être adaptée selon les priorités métier et les contraintes techniques spécifiques au projet.