#!/usr/bin/env python3
"""
Conversion PDF vers texte brut avec conservation de la structure
utilisant pdfplumber, PyMuPDF, et Camelot pour l'extraction de texte.
"""

import sys
import os
from typing import List, Optional
import re
from datetime import datetime

def extract_text_with_pdfplumber(pdf_path: str, page_numbers: Optional[List[int]] = None) -> str:
    """Extrait le texte du PDF avec structure utilisant pdfplumber"""
    try:
        import pdfplumber
        
        print(f"Extraction du texte du PDF avec pdfplumber : {pdf_path}")
        
        with pdfplumber.open(pdf_path) as pdf:
            metadata = pdf.metadata
            page_count = len(pdf.pages)
            
            print(f"Pages dans le document : {page_count}")
            
            if page_numbers is None:
                page_numbers = list(range(page_count))
            
            full_text = []
            
            if metadata:
                full_text.append("--- MÉTADONNÉES DU DOCUMENT ---")
                for key, value in metadata.items():
                    full_text.append(f"{key}: {value}")
                full_text.append("")
            
            for page_idx in page_numbers:
                if page_idx < page_count:
                    page = pdf.pages[page_idx]
                    text = page.extract_text()
                    tables = page.extract_tables()
                    
                    if text.strip():
                        full_text.append(f"--- PAGE {page_idx + 1} ---")
                        full_text.append(text)
                        print(f"  Page {page_idx + 1} extraite ({len(text)} caractères)")
                    
                    if tables:
                        full_text.append(f"--- TABLEAUX PAGE {page_idx + 1} ---")
                        for i, table in enumerate(tables):
                            full_text.append(f"Tableau {i + 1}:")
                            for row in table:
                                full_text.append(" | ".join([str(cell) for cell in row]))
                            full_text.append("")  # Ligne vide entre les tableaux
            
            return "\n".join(full_text)
            
    except Exception as e:
        print(f"Erreur lors de l'extraction avec pdfplumber : {e}")
        return f"Erreur d'extraction avec pdfplumber : {e}"

def extract_text_with_pymupdf(pdf_path: str, page_numbers: Optional[List[int]] = None) -> str:
    """Extrait le texte du PDF avec structure utilisant PyMuPDF"""
    try:
        import fitz  # PyMuPDF
        
        print(f"Extraction du texte du PDF avec PyMuPDF : {pdf_path}")
        
        with fitz.open(pdf_path) as pdf:
            page_count = pdf.page_count
            
            print(f"Pages dans le document : {page_count}")
            
            if page_numbers is None:
                page_numbers = list(range(page_count))
            
            full_text = []
            
            for page_idx in page_numbers:
                if page_idx < page_count:
                    page = pdf.load_page(page_idx)
                    text = page.get_text()
                    
                    if text.strip():
                        full_text.append(f"--- PAGE {page_idx + 1} ---")
                        full_text.append(text)
                        print(f"  Page {page_idx + 1} extraite ({len(text)} caractères)")
            
            return "\n".join(full_text)
            
    except Exception as e:
        print(f"Erreur lors de l'extraction avec PyMuPDF : {e}")
        return f"Erreur d'extraction avec PyMuPDF : {e}"

def extract_text_with_camelot(pdf_path: str, page_numbers: Optional[List[int]] = None) -> str:
    """Extrait le texte du PDF avec structure utilisant Camelot"""
    try:
        import camelot
        
        print(f"Extraction du texte du PDF avec Camelot : {pdf_path}")
        
        if page_numbers is None:
            tables = camelot.read_pdf(pdf_path, flavor='stream')
        else:
            pages_str = ','.join(map(str, page_numbers))
            tables = camelot.read_pdf(pdf_path, flavor='stream', pages=pages_str)
        
        full_text = []
        
        for i, table in enumerate(tables):
            full_text.append(f"--- TABLEAU {i + 1} ---")
            full_text.append(table.df.to_string(index=False, header=False))
            full_text.append("")  # Ligne vide entre les tableaux
        
        return "\n".join(full_text)
        
    except Exception as e:
        print(f"Erreur lors de l'extraction avec Camelot : {e}")
        return f"Erreur d'extraction avec Camelot : {e}"

def merge_extracted_texts(base_name: str) -> None:
    """Fusionne les fichiers texte extraits des trois méthodes en un seul fichier enrichi."""
    try:
        # Lire les contenus des trois fichiers
        with open(f"{base_name}_plumber.txt", 'r', encoding='utf-8') as f:
            plumber_content = f.read()

        with open(f"{base_name}_PyMuPDF.txt", 'r', encoding='utf-8') as f:
            pymupdf_content = f.read()

        with open(f"{base_name}_Camelot.txt", 'r', encoding='utf-8') as f:
            camelot_content = f.read()

        # Fusionner les contenus de manière enrichie
        merged_content = []
        plumber_lines = plumber_content.split('\n')
        pymupdf_lines = pymupdf_content.split('\n')
        camelot_lines = camelot_content.split('\n')
        
        i = 0
        j = 0
        k = 0
        
        while i < len(plumber_lines) or j < len(pymupdf_lines) or k < len(camelot_lines):
            if i < len(plumber_lines) and plumber_lines[i].startswith("--- MÉTADONNÉES DU DOCUMENT ---"):
                merged_content.append(plumber_lines[i])
                i += 1
            elif i < len(plumber_lines) and plumber_lines[i].startswith("--- PAGE"):
                merged_content.append(plumber_lines[i])
                i += 1
                # Ajouter le texte de PyMuPDF pour cette page
                if j < len(pymupdf_lines) and pymupdf_lines[j].startswith("--- PAGE"):
                    merged_content.append(pymupdf_lines[j])
                    j += 1
                # Ajouter les tableaux de Camelot pour cette page
                while k < len(camelot_lines) and camelot_lines[k].startswith("--- TABLEAU"):
                    merged_content.append(camelot_lines[k])
                    k += 1
                    if k < len(camelot_lines):
                        merged_content.append(camelot_lines[k])
                        k += 1
            elif j < len(pymupdf_lines):
                merged_content.append(pymupdf_lines[j])
                j += 1
            else:
                if i < len(plumber_lines):
                    merged_content.append(plumber_lines[i])
                    i += 1
                elif k < len(camelot_lines):
                    merged_content.append(camelot_lines[k])
                    k += 1
        
        # Sauvegarder le fichier final
        final_file = f"{base_name}.txt"
        with open(final_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(merged_content))
        print(f"Fichier final fusionné sauvegardé : {final_file}")
        
    except Exception as e:
        print(f"Erreur lors de la fusion des fichiers : {e}")

def save_files(pdf_path: str, text_content: str, method: str) -> None:
    """Sauvegarde les fichiers texte pour chaque méthode d'extraction"""
    try:
        base_name = os.path.splitext(pdf_path)[0]
        txt_file = f"{base_name}_{method}.txt"
        
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(text_content)
        print(f"Fichier texte brut sauvegardé : {txt_file}")
        
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des fichiers : {e}")

def process_pdf_to_text(pdf_path: str, page_numbers: Optional[List[int]] = None) -> None:
    """Traite un PDF et génère des fichiers texte pour chaque méthode d'extraction"""
    try:
        # Extraire le texte avec pdfplumber
        text_content_plumber = extract_text_with_pdfplumber(pdf_path, page_numbers)
        save_files(pdf_path, text_content_plumber, "plumber")
        
        # Extraire le texte avec PyMuPDF
        text_content_pymupdf = extract_text_with_pymupdf(pdf_path, page_numbers)
        save_files(pdf_path, text_content_pymupdf, "PyMuPDF")
        
        # Extraire le texte avec Camelot
        text_content_camelot = extract_text_with_camelot(pdf_path, page_numbers)
        save_files(pdf_path, text_content_camelot, "Camelot")

        # Fusionner les fichiers extraits
        base_name = os.path.splitext(pdf_path)[0]
        merge_extracted_texts(base_name)

    except Exception as e:
        print(f"Erreur lors du traitement : {e}")

def main():
    """Fonction principale"""
    print("=== Conversion PDF vers TXT ===")
    print("Ce programme extrait le texte brut en utilisant pdfplumber, PyMuPDF, et Camelot")
    print()
    
    # Vérifier les arguments
    if len(sys.argv) < 2:
        print("Usage: python src/pdf_to_txt_and_rtf.py <fichier.pdf> [--pages 1,3-5]")
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
    print(f"Conversion de {input_file} vers TXT...")
    process_pdf_to_text(input_file, page_numbers)
    print("Conversion terminée avec succès !")

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