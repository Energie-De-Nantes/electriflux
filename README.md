# Electriflux

Electriflux est une bibliothèque Python conçue pour la lecture et l'écriture des flux de données Enedis.

## Fonctionnalités principales

- Téléchargement sécurisé des fichiers via SFTP
- Décryptage des fichiers chiffrés
- Extraction des données XML en DataFrame pandas
- Configuration flexible des flux via des fichiers YAML

## Installation

```bash
pip install electriflux
```

## Utilisation

Il y a deux phases :
1) Récupération et décryptage des fichiers depuis le sFTP :

Assuré par la fonction `download_decrypt_extract_new_files` de `electriflux.utils`. Elle prend notamment en entrée un dictionnaire de configuration, qui doit contenir les clés suivantes :
 - 'FTP_ADDRESS', 
 - 'FTP_USER', 
 - 'FTP_PASSWORD'
 - 'AES_KEY'
 - 'AES_IV'

 A l'issue de cette opération, le dossier local choisi contient les fichiers XML des flux déchiffrés.

 2) Extraction des données XML en DataFrame pandas :
 
 Cette extraction des données est assurée par `process_flux` de `electriflux.simple_reader`. Son principe est simple, un fichier de configuration en YAML permet de définir, pour chaque flux, des couples clé-valeur, la clé représentant le nom de la colonne à remplir, et la valeur le chemin XPATH vers la donnée à extraire. (C'est un poil plus complexe en réalité, mais c'est l'idée).
 Par défaut, le fichier `simple_flux.yaml` est utilisé, mais il est possible d'en utiliser un autre en passant son chemin en argument de `process_flux`.

Exemple type pour récupérer les données du flux C15 sous forme de csv :
 ```python
    df = process_flux('C15', Path('~/data/flux_enedis_v2/C15').expanduser())
    df.to_csv('C15.csv', index=False)
 ```

## Modifier les données à extraire : Configuration YAML

La fonction `xml_to_dataframe` permet de transformer une structure XML en DataFrame de manière entièrement configurable à partir d'un fichier YAML. Cette configuration permet de spécifier différents niveaux d'extraction des données à partir d'un flux XML.

Voici une documentation détaillée sur la manière de personnaliser le fichier YAML pour adapter la transformation à vos besoins.

---

#### Structure du Fichier YAML

Le fichier YAML est organisé en plusieurs sections. Chaque section représente une configuration spécifique pour un type de flux. Voici les sections disponibles :

```yaml
Nom_du_Flux:
  row_level: <xpath>
  metadata_fields: <dictionnaire de métadonnées>
  data_fields: <dictionnaire de données>
  nested_fields: <liste de configurations imbriquées>
```

---

### Détails des Champs

1. **`row_level`** (obligatoire)  
   Définit le niveau de l'arbre XML à partir duquel chaque ligne du DataFrame sera générée.  
   - Type : `str`
   - Valeur : XPath indiquant le niveau de ligne dans le XML.

   **Exemple :**  
   ```yaml
   row_level: './/PRM'
   ```

---

2. **`metadata_fields`** (facultatif)  
   Spécifie les champs à extraire depuis la racine du XML. Ces champs seront recopiés dans chaque ligne générée.  
   - Type : `dict`
   - Clé : Nom de la colonne dans le DataFrame.
   - Valeur : XPath exprimé à partir de la racine du document XML.

   **Exemple :**  
   ```yaml
   metadata_fields:
     Num_Depannage: 'Num_Depannage'
     Date_Fichier: 'Date_Fichier'
   ```

---

3. **`data_fields`** (obligatoire)  
   Définit les champs à extraire relativement à chaque `row_level`.  
   - Type : `dict`
   - Clé : Nom de la colonne dans le DataFrame.
   - Valeur : XPath exprimé relativement au `row_level`.

   **Exemple :**  
   ```yaml
   data_fields:
     pdl: 'Id_PRM'
     Etat_Contractuel: 'Situation_Contractuelle/Etat_Contractuel'
   ```

---

4. **`nested_fields`** (facultatif)  
   Permet d'extraire des données contenues dans des structures imbriquées sous forme de colonnes linéarisées. Cette section prend en charge plusieurs conditions sous forme d'une liste de paires clé-valeur.  
   - Type : `list`
   - Clés disponibles :
     - `prefix` : Préfixe facultatif ajouté au nom de la colonne.
     - `child_path` : XPath relatif au `row_level` pour trouver les nœuds enfants.
     - `id_field` : Nom de l'élément clé.
     - `value_field` : Nom de l'élément contenant la valeur à extraire.
     - `conditions` : Liste de conditions sous forme de paires clé-valeur à respecter pour extraire les données.

   **Exemple :**  
   ```yaml
   nested_fields:
     - prefix: 'CT_'
       child_path: 'Evenement_Declencheur/Releves/Donnees_Releve/Classe_Temporelle_Distributeur'
       id_field: 'Id_Classe_Temporelle'
       value_field: 'Valeur'
       conditions:
         - xpath: '../Code_Qualification'
           value: '2'
         - xpath: 'Classe_Mesure'
           value: '1'
   ```

Dans cet exemple :
- Les données sont extraites uniquement lorsque les conditions suivantes sont remplies :
  - L'élément parent `Code_Qualification` est égal à `2`.
  - Le champ `Classe_Mesure` est égal à `1`.

Les valeurs seront linéarisées avec le préfixe `CT_` suivi de l'ID de la classe temporelle.

---

### Exemple Complet

Voici un exemple complet de configuration YAML pour un flux nommé `C15` :

```yaml
C15:
  row_level: './/PRM'
  metadata_fields:
    Num_Depannage: 'Num_Depannage'
    Date_Fichier: 'Date_Fichier'
  data_fields:
    pdl: 'Id_PRM'
    Etat_Contractuel: 'Situation_Contractuelle/Etat_Contractuel'
    Date_Evenement: 'Evenement_Declencheur/Date_Evenement'
  nested_fields:
    - prefix: ''
      child_path: 'Evenement_Declencheur/Releves/Donnees_Releve/Classe_Temporelle_Distributeur'
      id_field: 'Id_Classe_Temporelle'
      value_field: 'Valeur'
      conditions:
        - xpath: '../Code_Qualification'
          value: '2'
        - xpath: 'Classe_Mesure'
          value: '1'
```

---

### Explications :
- Chaque PRM dans le flux génère une ligne dans le DataFrame.
- Les colonnes `Num_Depannage` et `Date_Fichier` sont extraites depuis la racine et ajoutées à chaque ligne.
- Les champs `pdl`, `Etat_Contractuel` et `Date_Evenement` sont extraits relativement à chaque nœud PRM.
- Les valeurs de `Classe_Temporelle_Distributeur` sont extraites uniquement si les conditions spécifiées sont remplies.

---


