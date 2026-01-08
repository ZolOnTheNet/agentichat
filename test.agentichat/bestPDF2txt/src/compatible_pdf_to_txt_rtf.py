#!/usr/bin/env python3
"""
Conversion compatible PDF vers texte brut et RTF avec PyPDF2
"""

import sys
import os
from datetime import datetime

def create_basic_rtf_header():
    return "{\\rtf1\\ansi\\ansicpg1252\\deff0\\deflang1036{\\fonttbl{\\f0\\fnil\\fcharset0 Arial;}}\\viewkind4\\uc1\\pard\\f0\\fs20"

def create_basic_rtf_footer():
    return "\\par}\n"

def escape_rtf_text(text):
    if not isinstance(text, str):
        text = str(text)
    
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

def extract_text_with_structure(pdf_path):
    """Extrait le texte du PDF avec PyPDF2"""
    try:
        import PyPDF2
        
        print("Extraction du texte du PDF : " + pdf_path)
        
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            metadata = reader.metadata
            page_count = len(reader.pages)
            
            print("Pages dans le document : " + str(page_count))
            
            full_text = []
            
            # Ajouter les métadonnées
            if metadata:
                full_text.append("--- MÉTADONNÉES DU DOCUMENT ---")
                for key, value in metadata.items():
                    if value:
                        full_text.append(key + ": " + str(value))
                full_text.append("")
            
            # Extraction de toutes les pages
            for i in range(page_count):
                page = reader.pages[i]
                text = page.extract_text()
                if text.strip():
                    full_text.append("--- PAGE " + str(i + 1) + " ---")
                    full_text.append(text)
                    print("  Page " + str(i + 1) + " extraite (" + str(len(text)) + " caractères)")
            
            result = "\n\n".join(full_text)
            print("Total caractères extraits : " + str(len(result)))
            return result
            
    except Exception as e:
        print("Erreur lors de l'extraction : " + str(e))
        import traceback
        traceback.print_exc()
        return "Erreur d'extraction : " + str(e)

def create_rtf_content(text_content):
    """Crée le contenu RTF"""
    try:
        rtf_content = create_basic_rtf_header()
        rtf_content += "Document extrait le " + datetime.now().strftime('%d/%m/%Y') + "\\par\n"
        rtf_content += "\\par\n"
        rtf_content += escape_rtf_text(text_content)
        rtf_content += create_basic_rtf_footer()
        return rtf_content
    except Exception as e:
        print("Erreur lors de la création du RTF : " + str(e))
        return ""

def main():
    """Fonction principale"""
    print("=== Conversion PDF vers TXT et RTF ===")
    
    if len(sys.argv) < 2:
        print("Usage: python src/compatible_pdf_to_txt_rtf.py <fichier.pdf>")
        return
    
    input_file = sys.argv[1]
    
    if not os.path.exists(input_file):
        print("Erreur : Le fichier " + input_file + " n'existe pas.")
        return
    
    print("Traitement du fichier : " + input_file)
    
    # Extraire le texte
    text_content = extract_text_with_structure(input_file)
    
    if not text_content:
        print("Aucun texte extrait")
        return
    
    # Créer le RTF
    rtf_content = create_rtf_content(text_content)
    
    # Noms des fichiers de sortie
    base_name = os.path.splitext(input_file)[0]
    txt_file = base_name + ".txt"
    rtf_file = base_name + ".rtf"
    
    # Sauvegarder les fichiers
    try:
        # Sauvegarder le texte brut
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(text_content)
        print("Fichier texte brut créé : " + txt_file)
        
        # Sauvegarder le RTF
        with open(rtf_file, 'w', encoding='utf-8') as f:
            f.write(rtf_content)
        print("Fichier RTF créé : " + rtf_file)
        
        print("Conversion terminée avec succès !")
        
    except Exception as e:
        print("Erreur lors de la sauvegarde des fichiers : " + str(e))
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()