import sys
from pathlib import Path
import PyPDF2
import os
import argparse

def get_pdf_info(pdf_path):
    """Récupère les informations sur le PDF"""
    with open(pdf_path, 'rb') as fichier:
        lecteur_pdf = PyPDF2.PdfReader(fichier)
        return len(lecteur_pdf.pages)

def pdf_to_text(pdf_path, pages=None):
    """
    Convertit un fichier PDF en texte.
    
    Args:
        pdf_path (str): Chemin vers le fichier PDF à convertir.
        pages (list): Liste des numéros de pages à extraire (None = toutes les pages).
    """
    # Ouvre le fichier PDF en mode binaire
    with open(pdf_path, 'rb') as fichier:
        lecteur_pdf = PyPDF2.PdfReader(fichier)
        
        # Texte extrait du PDF
        texte = ""
        
        # Détermine les pages à traiter
        if pages is None:
            page_range = range(len(lecteur_pdf.pages))
        else:
            # Valide les numéros de pages
            max_pages = len(lecteur_pdf.pages)
            valid_pages = []
            for page_num in pages:
                if 1 <= page_num <= max_pages:
                    valid_pages.append(page_num - 1)  # Converti en index 0-based
            page_range = valid_pages
        
        # Parcourt les pages spécifiées
        for numero_page in page_range:
            page = lecteur_pdf.pages[numero_page]
            texte += f"--- Page {numero_page + 1} ---\n"
            texte += page.extract_text()
            texte += "\n\n"
            
    return texte

def pdf_to_rtf(pdf_path, output_path, pages=None):
    """
    Convertit un fichier PDF en RTF en préservant au mieux la mise en page.
    
    Args:
        pdf_path (str): Chemin vers le fichier PDF à convertir.
        output_path (str): Chemin du fichier RTF de sortie.
        pages (list): Liste des numéros de pages à extraire (None = toutes les pages).
    """
    try:
        # Ouvre le fichier PDF en mode binaire
        with open(pdf_path, 'rb') as fichier:
            lecteur_pdf = PyPDF2.PdfReader(fichier)
            
            # Crée le contenu RTF avec une structure de base
            rtf_content = "{\\rtf1\\ansi\\ansicpg1252\\deff0\\deflang1036{\\fonttbl{\\f0\\fnil\\fcharset0 Calibri;}}\n"
            rtf_content += "\\viewkind4\\uc1\\pard\\f0\\fs20\n"
            
            # Détermine les pages à traiter
            if pages is None:
                page_range = range(len(lecteur_pdf.pages))
            else:
                # Valide les numéros de pages
                max_pages = len(lecteur_pdf.pages)
                valid_pages = []
                for page_num in pages:
                    if 1 <= page_num <= max_pages:
                        valid_pages.append(page_num - 1)  # Converti en index 0-based
                page_range = valid_pages
            
            # Parcourt les pages spécifiées
            for numero_page in page_range:
                page = lecteur_pdf.pages[numero_page]
                # Ajoute un saut de page après chaque page
                if numero_page > 0:
                    rtf_content += "\\page\n"
                
                # Ajoute le numéro de page
                rtf_content += f"--- Page {numero_page + 1} ---\\par\n"
                
                # Extrait le texte et nettoie les caractères spéciaux
                texte_page = page.extract_text()
                # Nettoyage basique des caractères spéciaux
                texte_nettoye = texte_page.replace('\\', '\\\\').replace('{', '\\{').replace('}', '\\}')
                rtf_content += texte_nettoye + "\\par\\par\n"
            
            rtf_content += "}"
            
            # Écrit le contenu RTF dans le fichier
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(rtf_content)
                
            print(f"Fichier RTF généré avec succès : {output_path}")
            
    except Exception as e:
        print(f"Erreur lors de la génération du fichier RTF : {e}")

def parse_page_ranges(page_arg):
    """Parse les plages de pages spécifiées par l'utilisateur"""
    pages = []
    if not page_arg:
        return None
    
    # Sépare les éléments par des virgules
    parts = page_arg.split(',')
    
    for part in parts:
        part = part.strip()
        if '-' in part:
            # Gestion des plages (ex: 1-5)
            start, end = map(int, part.split('-'))
            pages.extend(range(start, end + 1))
        else:
            # Gestion d'une page unique
            pages.append(int(part))
    
    return pages

def main():
    parser = argparse.ArgumentParser(description='Convertit un fichier PDF en texte ou RTF')
    parser.add_argument('pdf_file', help='Chemin vers le fichier PDF à convertir')
    parser.add_argument('-o', '--output', help='Chemin du fichier de sortie (par défaut: stdout)')
    parser.add_argument('-f', '--format', choices=['txt', 'rtf'], default='txt', 
                       help='Format de sortie (par défaut: txt)')
    parser.add_argument('-p', '--pages', help='Plages de pages à extraire (ex: 1,3-5,10)')
    parser.add_argument('--info', action='store_true', help='Afficher les informations du PDF')
    
    args = parser.parse_args()
    
    # Vérifie que le fichier existe
    if not Path(args.pdf_file).is_file():
        print(f"Erreur : Le fichier {args.pdf_file} n'existe pas.")
        sys.exit(1)
    
    # Affiche les informations du PDF si demandé
    if args.info:
        total_pages = get_pdf_info(args.pdf_file)
        print(f"Informations sur le PDF : {args.pdf_file}")
        print(f"Nombre de pages : {total_pages}")
        sys.exit(0)
    
    # Détermine les pages à extraire
    pages = parse_page_ranges(args.pages)
    
    # Si aucune page spécifiée, on traite toutes les pages
    if pages is None:
        print(f"Extraction de toutes les pages du PDF : {args.pdf_file}")
    else:
        print(f"Extraction des pages {args.pages} du PDF : {args.pdf_file}")
    
    # Génère le fichier de sortie selon le format demandé
    if args.format == "rtf":
        if args.output:
            output_path = args.output
        else:
            # Génère le nom de sortie avec extension .rtf
            base_name = os.path.splitext(args.pdf_file)[0]
            output_path = f"{base_name}.rtf"
        
        pdf_to_rtf(args.pdf_file, output_path, pages)
    else:
        # Convertit le PDF en texte
        texte = pdf_to_text(args.pdf_file, pages)
        
        # Si aucun fichier de sortie spécifié, affiche dans la console
        if args.output is None:
            print(texte)
        else:
            # Écrit dans un fichier texte
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(texte)
            print(f"Fichier texte généré avec succès : {args.output}")

if __name__ == "__main__":
    main()