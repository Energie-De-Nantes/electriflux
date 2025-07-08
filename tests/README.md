# Documentation des Tests Electriflux

Ce document décrit la structure et l'approche des tests pour le projet Electriflux.

## Structure des Tests

```
tests/
├── __init__.py
├── conftest.py           # Fixtures pytest partagées
├── fixtures/             # Fichiers XML de test
│   ├── __init__.py
│   ├── c15_minimal.xml   # Fixture minimale pour flux C15
│   ├── f12_minimal.xml   # Fixture minimale pour flux F12
│   ├── f15_minimal.xml   # Fixture minimale pour flux F15
│   ├── r15_minimal.xml   # Fixture minimale pour flux R15
│   ├── r151_minimal.xml  # Fixture minimale pour flux R151
│   ├── empty.xml         # XML vide pour tests limites
│   └── invalid.xml       # XML invalide pour tests d'erreur
├── test_xml_parsing.py   # Tests unitaires pour xml_to_dataframe
├── test_simple_reader.py # Tests unitaires pour les fonctions du module
└── test_integration.py   # Tests d'intégration des workflows complets
```

## Approche des Tests

### 1. Fixtures XML Synthétiques

Les fixtures XML ont été créées sans utiliser de XSD propriétaires. Elles contiennent :
- La structure minimale nécessaire pour chaque type de flux
- Des données fictives mais réalistes (PDL, dates, valeurs)
- Des cas de test variés (multiples PRM, différentes classes temporelles)
- Des cas limites (fichiers vides, XML invalide)

### 2. Tests Unitaires

#### `test_xml_parsing.py`
Tests isolés de la fonction `xml_to_dataframe` :
- Parsing basique avec métadonnées et données
- Extraction de champs imbriqués (nested fields)
- Gestion des conditions multiples
- Champs additionnels dans les nested fields
- Cas d'erreur (XML invalide, champs manquants)
- Performance avec plusieurs lignes

#### `test_simple_reader.py`
Tests des fonctions individuelles :
- Chargement de configuration YAML
- Recherche de fichiers XML avec patterns
- Gestion de l'historique des fichiers traités
- Gestion des données (chargement, ajout)
- Réinitialisation des flux

### 3. Tests d'Intégration

#### `test_integration.py`
Tests des workflows complets :
- Traitement complet de chaque type de flux (C15, F12, F15, R15, R151)
- Workflow itératif avec historique
- Réinitialisation et retraitement
- Gestion de multiples types de flux
- Récupération après erreurs
- Performance avec grands datasets

## Exécution des Tests

```bash
# Installer les dépendances de développement
poetry install

# Exécuter tous les tests
poetry run pytest

# Exécuter avec couverture
poetry run pytest --cov=electriflux

# Exécuter un fichier spécifique
poetry run pytest tests/test_xml_parsing.py

# Exécuter avec verbosité
poetry run pytest -v

# Exécuter un test spécifique
poetry run pytest tests/test_xml_parsing.py::TestXmlToDataframe::test_nested_fields
```

## Structure des Données XML

### Flux C15
- Niveau de ligne : `.//PRM`
- Contient : informations contractuelles, compteur, événements
- Particularité : nested fields avec conditions (Avant/Après)

### Flux F12
- Niveau de ligne : `.//Element_Valorise`
- Contient : factures TURPE, éléments valorisés
- Pattern de fichier : `FL_\d+_\d+\.xml$`

### Flux F15
- Niveau de ligne : `.//Element_Valorise`
- Contient : consommations détaillées, taxes
- Structure imbriquée complexe avec `Donnees_Generales_Facture`

### Flux R15
- Niveau de ligne : `.//PRM`
- Contient : relevés avec classes temporelles
- Classes : HP, HC, BASE, HPH, HCH, HPB, HCB

### Flux R151
- Niveau de ligne : `.//PRM`
- Similaire à R15 mais avec calendriers fournisseur/distributeur

## Ajout de Nouveaux Tests

Pour ajouter de nouveaux cas de test :

1. **Pour une nouvelle structure XML** :
   - Créer une fixture dans `tests/fixtures/`
   - Ajouter des tests dans `test_xml_parsing.py`

2. **Pour une nouvelle fonctionnalité** :
   - Ajouter des tests unitaires dans le fichier approprié
   - Ajouter un test d'intégration si nécessaire

3. **Pour un nouveau type de flux** :
   - Créer une fixture XML minimale
   - Ajouter la configuration dans `conftest.py`
   - Ajouter des tests spécifiques

## Considérations de Sécurité

- Les fixtures ne contiennent aucune donnée réelle
- Les PDL et autres identifiants sont fictifs
- Aucun XSD propriétaire n'est inclus
- Les tests utilisent des répertoires temporaires isolés

## Maintenance

- Mettre à jour les fixtures si la structure XML évolue
- Ajouter des tests pour toute nouvelle fonctionnalité
- Maintenir une couverture de code élevée (objectif > 80%)
- Documenter les cas de test complexes