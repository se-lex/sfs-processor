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
    
    # Kontrollera om rader är potentiella rubriker
    potential_headers = []
    for i, line in enumerate(result_lines):
        is_potential_header = (
            line.strip() and
            len(line) < 300 and
            not line.strip().endswith(('.', ':')) and
            not re.match(r'^\d+\.', line.strip()) and  # Uteslut rader som börjar med siffra följt av punkt
            # Kontrollera om det är max två ord eller om det uppfyller de andra kriterierna
            (len(line.split()) <= 2 or True)
        )
        potential_headers.append(is_potential_header)

    for i, line in enumerate(result_lines):
        if not line.strip():
            formatted.append('')  # Behåll tomma rader
            previous_line_empty = True
        else:
            # Kontrollera om nästnästa rad börjar med "1." för att undvika att göra en rad till rubrik
            next_is_list_start = False
            if i + 2 < len(result_lines) and result_lines[i + 2].strip().startswith("1."):
                next_is_list_start = True

            # Kontrollera om det är en rubrik
            if potential_headers[i] and not next_is_list_start:
                # Om raden har max två ord OCH inte innehåller punkt, eller uppfyller de andra kriterierna
                if (len(line.split()) <= 2 and '.' not in line) or (len(line) < 300 and not line.strip().endswith(('.', ':'))):
                    formatted.append(f'## {line}')
                else:
                    # Fetstila endast (NUMMER) § som inleder ett nytt stycke (efter tom rad)
                    if previous_line_empty:
                        line = re.sub(r'^(\d+ ?§)', r'**\1**', line)
                    formatted.append(line)
            else:
                # Fetstila endast (NUMMER) § som inleder ett nytt stycke (efter tom rad)
                if previous_line_empty:
                    line = re.sub(r'^(\d+ ?§)', r'**\1**', line)
                formatted.append(line)
            previous_line_empty = False

    # Steg 3: Skriv det formaterade resultatet till fil
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(formatted) + '\n')

def format_sfs_text(text: str) -> str:
    """
    Formattera texten för ett SFS-dokument enligt specificerade regler.

    Args:
        text (str): Texten som ska formateras

    Returns:
        str: Den formaterade texten
    """
    # Dela upp texten i rader
    lines = text.splitlines()

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

    # Kontrollera om rader är potentiella rubriker
    potential_headers = []
    for i, line in enumerate(result_lines):
        is_potential_header = (
            line.strip() and
            len(line) < 300 and
            not line.strip().endswith(('.', ':')) and
            not re.match(r'^\d+\.', line.strip()) and  # Uteslut rader som börjar med siffra följt av punkt
            # Kontrollera om det är max två ord eller om det uppfyller de andra kriterierna
            (len(line.split()) <= 2 or True)
        )
        potential_headers.append(is_potential_header)

    for i, line in enumerate(result_lines):
        if not line.strip():
            formatted.append('')  # Behåll tomma rader
            previous_line_empty = True
        else:
            # Kontrollera om nästnästa rad börjar med "1." för att undvika att göra en rad till rubrik
            next_is_list_start = False
            if i + 2 < len(result_lines) and result_lines[i + 2].strip().startswith("1."):
                next_is_list_start = True

            # Kontrollera om det är en rubrik
            if potential_headers[i] and not next_is_list_start:
                # Om raden har max två ord OCH inte innehåller punkt, eller uppfyller de andra kriterierna
                if (len(line.split()) <= 2 and '.' not in line) or (len(line) < 300 and not line.strip().endswith(('.', ':'))):
                    formatted.append(f'## {line}')
                else:
                    # Fetstila endast (NUMMER) § som inleder ett nytt stycke (efter tom rad)
                    if previous_line_empty:
                        line = re.sub(r'^(\d+ ?§)', r'**\1**', line)
                    formatted.append(line)
            else:
                # Fetstila endast (NUMMER) § som inleder ett nytt stycke (efter tom rad)
                if previous_line_empty:
                    line = re.sub(r'^(\d+ ?§)', r'**\1**', line)
                formatted.append(line)
            previous_line_empty = False

    # Steg 3: Ta bort text som börjar med "/Träder i kraft" upp till nästa "/" och mellanslaget efter
    formatted_text = '\n'.join(formatted)
    formatted_text = re.sub(r'/Träder i kraft[^/]*/\s*', '/', formatted_text)

    # Returnera den formaterade texten
    return formatted_text
