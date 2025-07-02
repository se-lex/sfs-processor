"""
Script för att formattera SFS-dokument (Svensk Författningssamling) i Markdown-format.

Regler som tillämpas:
1. Ta bort alla radbrytningar så att dokumentet blir flytande text (inte "wrappat")
2. Identifiera rader som bara har max två ord och radbryt före och efter som rubriker
   - Rubriker ska ha ## framför (underrubriker i Markdown)
   - Undvik att göra rader till rubriker om de innehåller punkt
3. Paragrafer i formatet "(NUMMER) §" som inleder ett nytt stycke ska fetstilas i Markdown (**text**)
   - Endast paragrafnummer i början av rader efter tomma rader fetstilas

Användning:
    python format_sfs_md.py

Läser: markdown/sfs-2024-11.md
Skriver: markdown/sfs-2024-11.formatted.md
"""

import re

def format_sfs_text_to_md(input_path, output_path):
    """
    Formattera ett SFS-dokument enligt specificerade regler.
    
    Args:
        input_path (str): Sökväg till input-filen (originalfilen)
        output_path (str): Sökväg till output-filen (formaterad fil)
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Steg 1: Bearbeta rader för att slå ihop brutna meningar
    # Varje paragraf avgränsas av tomma rader
    result_lines = []
    current_paragraph = []

    for line in lines:
        line = line.rstrip()

        # Om tom rad, avsluta nuvarande paragraf
        if not line.strip():
            if current_paragraph:
                # Slå ihop rader i paragrafen med mellanslag (ta bort radbrytningar)
                paragraph_text = ' '.join(current_paragraph)
                result_lines.append(paragraph_text)
                current_paragraph = []
            result_lines.append('')  # Behåll tom rad för struktur
        else:
            current_paragraph.append(line.strip())
    
    # Glöm inte sista paragrafen
    if current_paragraph:
        paragraph_text = ' '.join(current_paragraph)
        result_lines.append(paragraph_text)

    # Steg 2: Bearbeta resultatet för rubriker och fetstil-formatering
    formatted = []
    previous_line_empty = True  # Första raden räknas som början av nytt stycke
    
    for line in result_lines:
        if not line.strip():
            formatted.append('')  # Behåll tomma rader
            previous_line_empty = True
        else:
            # Om raden har max två ord OCH inte innehåller punkt, gör till rubrik
            if len(line.split()) <= 2 and '.' not in line:
                formatted.append(f'## {line}')
            else:
                # Fetstila endast (NUMMER) § som inleder ett nytt stycke (efter tom rad)
                if previous_line_empty:
                    line = re.sub(r'^(\d+ ?§)', r'**\1**', line)
                formatted.append(line)
            previous_line_empty = False

    # Steg 3: Skriv det formaterade resultatet till fil
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(formatted) + '\n')

if __name__ == '__main__':
    # Kör formateringen på SFS 2024:11
    format_sfs_text_to_md('markdown/sfs-2024-11.md', 'markdown/sfs-2024-11.formatted.md')
    print("Formatering klar! Resultat sparat i markdown/sfs-2024-11.formatted.md")
