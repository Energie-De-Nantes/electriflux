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