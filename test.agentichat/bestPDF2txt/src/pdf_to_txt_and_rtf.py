#!/usr/bin/env python3
"""
Conversion PDF vers texte brut et RTF avec conservation de la structure
utilisant pdfplumber pour l'extraction de texte.
"""

import sys
import os
from typing import List, Optional
import re
from datetime import datetime

def create_basic_rtf_header() -> str:
    """Crée l'en-tête RTF basique"""
    return (
        "{\\rtf1\\ansi\\ansicpg1252\\deff0\\deflang1036{\\fonttbl{\\f0\\fnil\\fcharset0 Arial;}}\n"
        "\\viewkind4\\uc1\\pard\\f0\\fs20"
    )

def create_basic_rtf_footer() -> str:
    """Crée le pied de page RTF basique"""
    return "\\par}\n"

def escape_rtf_text(text: str) -> str:
    """Échappe les caractères spéciaux RTF"""
    if not isinstance(text, str):
        text = str(text)
    
    # Remplacer les caractères spéciaux RTF
    replacements = {
        '\\': '\\\\',
        '{': '\\{',
        '}': '\\}',
        '\n': '\\par\n',
        '\r': '',
        '\t': '\\tab '
    }
    
    escaped = text
    for old, new in replacements.items():
        escaped = escaped.replace(old, new)
    
    return escaped

def extract_text_with_structure(pdf_path: str, page_numbers: Optional[List[int]] = None) -> str:
    """
    Extrait le texte du PDF avec structure utilisant pdfplumber
    """
    try:
        import pdfplumber
        
        print(f"Extraction du texte du PDF : {pdf_path}")
        
        # Ouvrir le PDF avec pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            # Obtenir les infos sur le document
            metadata = pdf.metadata
            page_count = len(pdf.pages)
            
            print(f"Pages dans le document : {page_count}")
            
            # Si aucun numéro de page spécifié, utiliser toutes les pages
            if page_numbers is None:
                page_numbers = list(range(page_count))
            
            full_text = []
            
            # Ajout des métadonnées
            if metadata:
                full_text.append("--- MÉTADONNÉES DU DOCUMENT ---")
                for key, value in metadata.items():
                    full_text.append(f"{key}: {value}")
                full_text.append("")
            
            # Extraction par page
            for page_idx in page_numbers:
                if page_idx < page_count:
                    page = pdf.pages[page_idx]
                    text = page.extract_text()
                    
                    if text.strip():
                        full_text.append(f"--- PAGE {page_idx + 1} ---")
                        full_text.append(text)
                        print(f"  Page {page_idx + 1} extraite ({len(text)} caractères)")
            
            return "\n\n".join(full_text)
            
    except Exception as e:
        print(f"Erreur lors de l'extraction : {e}")
        # Retourner un texte de base si erreur
        return f"Erreur d'extraction : {e}"

def create_rtf_content(text_content: str) -> str:
    """Crée le contenu RTF à partir du texte brut"""
    try:
        # Créer le contenu RTF
        rtf_content = create_basic_rtf_header()
        
        # Ajouter les métadonnées
        rtf_content += f"Document extrait le {datetime.now().strftime('%d/%m/%Y')}\\par\n"
        rtf_content += "\\par\n"
        
        # Ajouter le contenu textuel
        rtf_content += escape_rtf_text(text_content)
        
        # Ajouter le pied de page
        rtf_content += create_basic_rtf_footer()
        
        return rtf_content
        
    except Exception as e:
        print(f"Erreur lors de la création du RTF : {e}")
        return ""

def save_files(pdf_path: str, text_content: str, rtf_content: str) -> None:
    """Sauvegarde les fichiers texte et RTF"""
    try:
        # Nom de base pour les fichiers
        base_name = os.path.splitext(pdf_path)[0]
        
        # Sauvegarder le texte brut
        txt_file = f"{base_name}.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(text_content)
        print(f"Fichier texte brut sauvegardé : {txt_file}")
        
        # Sauvegarder le RTF
        rtf_file = f"{base_name}.rtf"
        with open(rtf_file, 'w', encoding='utf-8') as f:
            f.write(rtf_content)
        print(f"Fichier RTF sauvegardé : {rtf_file}")
        
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des fichiers : {e}")

def process_pdf_to_both_formats(pdf_path: str, page_numbers: Optional[List[int]] = None) -> bool:
    """
    Traite un PDF et génère à la fois le texte brut et RTF
    """
    try:
        # Extraire le texte
        text_content = extract_text_with_structure(pdf_path, page_numbers)
        
        if not text_content:
            print("Aucun texte extrait du PDF")
            return False
        
        # Créer le contenu RTF
        rtf_content = create_rtf_content(text_content)
        
        # Sauvegarder les deux fichiers
        save_files(pdf_path, text_content, rtf_content)
        
        return True
        
    except Exception as e:
        print(f"Erreur lors du traitement : {e}")
        return False

def main():
    """Fonction principale"""
    print("=== Conversion PDF vers TXT et RTF ===")
    print("Ce programme extrait le texte brut et génère un RTF")
    print()
    
    # Vérifier les arguments
    if len(sys.argv) < 2:
        print("Usage: python src/pdf_to_txt_and_rtf.py <fichier.pdf> [output_prefix] [--pages 1,3-5]")
        print("Exemple: python src/pdf_to_txt_and_rtf.py document.pdf --pages 1,3-5")
        return
    
    input_file = sys.argv[1]
    
    # Parser les pages si spécifié
    page_numbers = None
    if '--pages' in sys.argv:
        try:
            pages_arg_index = sys.argv.index('--pages')
            pages_str = sys.argv[pages_arg_index + 1]
            page_numbers = parse_page_ranges(pages_str)
            print(f"Pages à extraire : {page_numbers}")
        except (ValueError, IndexError):
            print("Format de pages incorrect. Exemple : --pages 1,3-5")
            return
    
    # Vérifier que le fichier PDF existe
    if not os.path.exists(input_file):
        print(f"Erreur : Le fichier {input_file} n'existe pas.")
        return
    
    # Traiter le PDF
    print(f"Conversion de {input_file} vers TXT et RTF...")
    success = process_pdf_to_both_formats(input_file, page_numbers)
    
    if success:
        print(f"Conversion terminée avec succès !")
        print("Fichiers générés :")
        base_name = os.path.splitext(input_file)[0]
        print(f"  - {base_name}.txt")
        print(f"  - {base_name}.rtf")
    else:
        print("Erreur lors de la conversion.")

def parse_page_ranges(pages_str: str) -> List[int]:
    """
    Parse les plages de pages spécifiées
    Exemples : "1", "1-3", "1,3,5", "1-3,5"
    """
    pages = set()
    parts = pages_str.split(',')
    
    for part in parts:
        part = part.strip()
        if '-' in part:
            start_end = part.split('-')
            if len(start_end) == 2:
                start = int(start_end[0])
                end = int(start_end[1])
                pages.update(range(start, end + 1))
        else:
            pages.add(int(part))
    
    return sorted(list(pages))

if __name__ == "__main__":
    main()