import argparse
import PyPDF2
import re

def compress_text(text):
    # Split the text into lines
    lines = text.split("\n")
    compressed_lines = []
    for line in lines:
        if line.strip():
            compressed_lines.append(line)
    # Join the lines with a single space, but preserve paragraphs and important spacing
    compressed_text = "\n".join([" ".join(line.split()) for line in compressed_lines])
    
    # Traitement des listes à puces
    # Remplacer les lignes vides avant les listes à puces par un saut de ligne simple
    compressed_text = re.sub(r'\n\s*\n(•|•\s)', r'\n\1', compressed_text)
    
    # Traitement des titres
    # Coller les titres au texte précédent
    compressed_text = re.sub(r'(\w)\n(INTRODUCTION|WHAT IS THIS?|THE BASICS|CHARACTER CREATION|STEP \d)', r'\1 \2', compressed_text)
    
    # Supprimer les espaces supplémentaires
    compressed_text = re.sub(r'\n\s+', '\n', compressed_text)
    compressed_text = re.sub(r'\s+', ' ', compressed_text)
    
    return compressed_text

def extract_text_from_pdf(pdf_path):
    pdf_file = open(pdf_path, 'rb')
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    pdf_file.close()
    return text

def main():
    parser = argparse.ArgumentParser(description='Compress text from a file.')
    parser.add_argument('--compresse', '-c', action='store_true', help='Compress the text')
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('file_path', help='Path to the input file')
    args = parser.parse_args()

    if args.compresse:
        if args.file_path.lower().endswith('.pdf'):
            content = extract_text_from_pdf(args.file_path)
        else:
            with open(args.file_path, 'r', encoding='latin-1') as file:
                content = file.read()
        compressed_content = compress_text(content)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as output_file:
                output_file.write(compressed_content)
            print(f"Compressed text saved to {args.output}")
        else:
            print(compressed_content)
    else:
        print("No compression option selected.")

if __name__ == "__main__":
    main()