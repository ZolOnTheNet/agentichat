#!/usr/bin/env python3
"""
Démo de pdfplumber pour explorer les informations supplémentaires 
que l'on peut extraire d'un PDF.
"""

import sys
from typing import List, Dict, Any

def demo_pdfplumber_capabilities():
    """
    Fonction démonstrative des capacités de pdfplumber
    """
    print("=== Démo des capacités de pdfplumber ===")
    print()
    
    # Voici les principales fonctionnalités de pdfplumber :
    print("1. Extraction de texte brut avec position :")
    print("   - pdfplumber.extract_text() : texte avec positions")
    print("   - pdfplumber.extract_words() : mots individuels avec coordonnées")
    print()
    
    print("2. Extraction structurée :")
    print("   - pdfplumber.extract_tables() : extraction de tableaux")
    print("   - pdfplumber.extract_lines() : lignes horizontales/verticales")
    print("   - pdfplumber.extract_curves() : courbes")
    print()
    
    print("3. Informations sur le document :")
    print("   - pdfplumber.metadata : métadonnées du PDF")
    print("   - pdfplumber.pages : information sur les pages")
    print("   - pdfplumber.page_count : nombre de pages")
    print()
    
    print("4. Analyse avancée :")
    print("   - pdfplumber.get_page(0).chars : caractères avec police")
    print("   - pdfplumber.get_page(0).words : mots avec propriétés")
    print("   - pdfplumber.get_page(0).lines : lignes avec style")
    print()
    
    print("Exemple de structure que l'on pourrait utiliser :")
    print()
    print("{")
    print("    'page': 1,")
    print("    'text': 'Contenu du texte',")
    print("    'tables': [")
    print("        [{'col1': 'val1', 'col2': 'val2'}, {'col1': 'val3', 'col2': 'val4'}]")
    print("    ],")
    print("    'words': [")
    print("        {'text': 'mot1', 'x0': 100, 'y0': 200, 'x1': 150, 'y1': 220},")
    print("        ...")
    print("    ],")
    print("    'metadata': {")
    print("        'title': 'Titre du document',")
    print("        'author': 'Auteur'")
    print("    }")
    print("}")

def analyze_pdf_structure(pdf_path: str):
    """
    Fonction pour analyser la structure d'un PDF (simulation)
    """
    print(f"\n=== Analyse du PDF : {pdf_path} ===")
    
    # Simulation de ce que pourrait faire pdfplumber
    print("Simulation des données extraites par pdfplumber :")
    print()
    
    # Données simulées
    simulated_data = {
        'metadata': {
            'Title': 'Document d\'exemple',
            'Author': 'Auteur inconnu',
            'CreationDate': '2023-01-01'
        },
        'page_count': 3,
        'pages': [
            {
                'page_num': 1,
                'width': 612,
                'height': 792,
                'text': 'Ceci est le texte de la première page...',
                'words': [
                    {'text': 'Ceci', 'x0': 100, 'y0': 700, 'x1': 140, 'y1': 720},
                    {'text': 'est', 'x0': 145, 'y0': 700, 'x1': 170, 'y1': 720},
                    {'text': 'le', 'x0': 175, 'y0': 700, 'x1': 190, 'y1': 720}
                ],
                'tables': [
                    {
                        'data': [['Colonne1', 'Colonne2'], ['Valeur1', 'Valeur2']],
                        'bbox': [100, 600, 300, 650]
                    }
                ]
            }
        ]
    }
    
    print("Métadonnées :")
    for key, value in simulated_data['metadata'].items():
        print(f"  {key}: {value}")
    
    print(f"\nNombre de pages : {simulated_data['page_count']}")
    
    print("\nStructure de la première page :")
    first_page = simulated_data['pages'][0]
    print(f"  Numéro de page : {first_page['page_num']}")
    print(f"  Dimensions : {first_page['width']} x {first_page['height']}")
    print(f"  Texte : {first_page['text'][:100]}...")
    
    print("\nMots avec positions :")
    for i, word in enumerate(first_page['words'][:5]):  # Premier 5 mots
        print(f"  Mot {i+1}: '{word['text']}' @ ({word['x0']}, {word['y0']})")
        
    if first_page['tables']:
        print("\nTableaux détectés :")
        for i, table in enumerate(first_page['tables']):
            print(f"  Tableau {i+1}: {table['data'][0]} (bbox: {table['bbox']})")
    else:
        print("\nAucun tableau détecté")

def main():
    """
    Main function
    """
    print("=== Programme d'essai de pdfplumber ===")
    print("Ce programme illustre les capacités de pdfplumber")
    print("pour enrichir le texte extrait d'un PDF.")
    print()
    
    # Afficher les capacités
    demo_pdfplumber_capabilities()
    
    # Simuler l'analyse d'un PDF
    print("\n" + "="*50)
    analyze_pdf_structure("document_exemple.pdf")
    
    print("\n=== Conclusion ===")
    print("pdfplumber permet d'extraire :")
    print("- Texte brut avec position exacte")
    print("- Mots individuels avec coordonnées")
    print("- Tables avec structure")
    print("- Métadonnées du document")
    print("- Informations sur les pages")
    print()
    print("Cela pourrait permettre d'enrichir le texte brut avec :")
    print("- Position des mots pour la mise en page")
    print("- Structure tabulaire pour RTF")
    print("- Informations supplémentaires pour le format RTF")

if __name__ == "__main__":
    main()