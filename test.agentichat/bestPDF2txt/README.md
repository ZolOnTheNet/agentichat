# PDF to Text Converter

Ce programme permet de convertir un fichier PDF en texte.

## Prérequis

- Python 3.x
- PyPDF2 (peut être installé via pip)

## Installation

1. Clonez ce dépôt ou téléchargez le fichier `main.py`.
2. Installez la dépendance requise:
   ```
   pip install PyPDF2
   ```

## Utilisation

Exécutez le script en passant le chemin vers le fichier PDF que vous souhaitez convertir en argument:

```
python src/main.py chemin/vers/votre/fichier.pdf
```

## Description du code

Le programme contient deux fonctions principales :

1. `pdf_to_text(pdf_path)`:
   - Ouvre le fichier PDF spécifié.
   - Extrait le texte de chaque page du PDF.
   - Retourne le texte combiné de toutes les pages.

2. `main()`:
   - Vérifie que le nom du fichier PDF est fourni en argument.
   - Vérifie que le fichier existe.
   - Appelle la fonction `pdf_to_text` pour convertir le PDF en texte.
   - Affiche le texte extrait.

## Exemple

Si vous avez un fichier PDF nommé `document.pdf`, vous pouvez l'exécuter comme suit :

```
python src/main.py document.pdf
```

Le programme affichera le contenu textuel de `document.pdf`.

## Auteur

Ce programme a été créé par ZOL.
