"""
Script för att formattera SFS-dokument (Svensk Författningssamling) i Markdown-format.

Regler som tillämpas:
1. Ta bort alla radbrytningar så att dokumentet blir flytande text (inte "wrappat")
2. Identifiera och formattera olika typer av rubriker:
   - Kapitel (ex. "1 kap.") blir H2-rubriker (##)
   - Vanliga rubriker (max två ord, ingen punkt) blir H3-rubriker (###)
   - Paragrafnummer (ex. "13 §") kan bli antingen:
     * H3-rubriker (###) när paragraph_as_header=True (standard)
     * H4-rubriker (####) inom potential_headers-sektionen
     * Fetstil (**text**) när paragraph_as_header=False
3. Hantering av ändringar och upphöranden:
   - Stycken med "/Ny beteckning" efter paragrafer tas bort
   - Stycken med "/Upphör att gälla U:YYYY-MM-DD/" efter paragrafer tas bort

"""

import re

def apply_changes_to_sfs_text(text: str, target_date: str = None) -> str:
    """
    Formattera SFS-text med hantering av ändringar och upphöranden.

    Regler:
    1. Om "/Ny beteckning" förekommer efter en paragraf (ex. **13 §**) ska hela stycket tas bort
    2. Om "/Upphör att gälla U:YYYY-MM-DD/" förekommer efter en paragraf ska hela stycket tas bort
    3. Om "/Rubriken träder i kraft I:YYYY-MM-DD/" förekommer efter en paragraf ska hela stycket tas bort
    4. Om "/Rubriken upphör att gälla U:YYYY-MM-DD/" förekommer före en underrubrik ska hela stycket tas bort

    Om target_date anges, tillämpas reglerna endast om datumet i I: eller U: matchar target_date.

    Args:
        text (str): Texten som ska formateras
        target_date (str, optional): Datum i format YYYY-MM-DD som ska matchas mot I: eller U: datum

    Returns:
        str: Den formaterade texten med ändringar borttagna

    Raises:
        ValueError: Om inga regler kunde tillämpas (inga ändringar gjordes)
    """
    # Dela upp texten i stycken (avgränsade av dubbla radbrytningar)
    paragraphs = text.split('\n\n')

    filtered_paragraphs = []
    changes_applied = 0  # Räkna antal tillämpade ändringar

    for paragraph in paragraphs:
        paragraph_removed = False

        # Kontrollera om stycket innehåller "/Ny beteckning"
        if '/Ny beteckning' in paragraph:
            # Kontrollera om det föregås av en paragraf (innehåller **X §**)
            if re.search(r'\*\*\d+\s*§\*\*', paragraph):
                # Ta bort hela stycket
                changes_applied += 1
                paragraph_removed = True
                continue

        # Kontrollera om stycket innehåller "/Upphör att gälla" med datum
        upphör_match = re.search(r'/Upphör att gälla U:(\d{4}-\d{2}-\d{2})/', paragraph)
        if upphör_match:
            date_in_text = upphör_match.group(1)
            # Om target_date är angivet, kontrollera att det matchar
            if target_date is None or date_in_text == target_date:
                # Kontrollera om det föregås av en paragraf (innehåller **X §**)
                if re.search(r'\*\*\d+\s*§\*\*', paragraph):
                    # Ta bort hela stycket
                    changes_applied += 1
                    paragraph_removed = True
                    continue

        # Kontrollera om det står "/Rubriken träder i kraft" med datum
        träder_match = re.search(r'/Rubriken träder i kraft I:(\d{4}-\d{2}-\d{2})/', paragraph)
        if träder_match:
            date_in_text = träder_match.group(1)
            # Om target_date är angivet, kontrollera att det matchar
            if target_date is None or date_in_text == target_date:
                # Kontrollera om det föregås av en paragraf (innehåller **X §**)
                if re.search(r'\*\*\d+\s*§\*\*', paragraph):
                    # Ta bort hela stycket
                    changes_applied += 1
                    paragraph_removed = True
                    continue

        # Kontrollera om det står "/Rubriken upphör att gälla" med datum
        rubrik_upphör_match = re.search(r'/Rubriken upphör att gälla U:(\d{4}-\d{2}-\d{2})/', paragraph)
        if rubrik_upphör_match:
            date_in_text = rubrik_upphör_match.group(1)
            # Om target_date är angivet, kontrollera att det matchar
            if target_date is None or date_in_text == target_date:
                # Kontrollera om det följs av en underrubrik (innehåller ### )
                if re.search(r'###\s+', paragraph):
                    # Ta bort hela stycket
                    changes_applied += 1
                    paragraph_removed = True
                    continue

        # Om inget av ovanstående matchar, behåll stycket
        if not paragraph_removed:
            filtered_paragraphs.append(paragraph)

    # Kontrollera om inga regler kunde tillämpas
    if changes_applied == 0:
        if target_date:
            raise ValueError(f"Inga regler kunde tillämpas för datum {target_date}. Kontrollera att texten innehåller relevanta ändringsmarkeringar med detta datum. Innehållet: " + text)
        else:
            raise ValueError("Inga regler kunde tillämpas. Kontrollera att texten innehåller relevanta ändringsmarkeringar (/Ny beteckning, /Upphör att gälla, /Rubriken träder i kraft, /Rubriken upphör att gälla).")

    # Sätt ihop styckena igen
    return '\n\n'.join(filtered_paragraphs)


def format_sfs_text(text: str, paragraph_as_header: bool = True) -> str:
    """
    Formattera texten för ett SFS-dokument enligt specificerade regler.

    Args:
        text (str): Texten som ska formateras
        paragraph_as_header (bool): Om True, gör paragrafnummer till H3-rubriker istället för fetstil

    Returns:
        str: Den formaterade texten
    """
    # Dela upp texten i rader
    original_lines = text.splitlines()

    # Steg 0: Skapa rensade rader för rubrikidentifiering (ta bort markeringar inom snedstreck)
    # Detta inkluderar markeringar som "/Träder i kraft/", "/Upphör att gälla/", "/Ny beteckning/" etc.
    temp_cleaned_lines = []
    for line in original_lines:
        # Ta bort alla texter inom snedstreck temporärt för rubrikanalys
        cleaned_line = re.sub(r'/[^/]+/', '', line).strip()
        temp_cleaned_lines.append(cleaned_line)

    # Steg 1: Bearbeta de rensade raderna för att slå ihop brutna meningar och identifiera struktur
    # Varje paragraf avgränsas av tomma rader
    cleaned_result_lines = []
    current_paragraph = []

    for line in temp_cleaned_lines:
        line = line.rstrip()

        # Om tom rad, avsluta nuvarande paragraf
        if not line.strip():
            if current_paragraph:
                # Slå ihop rader i paragrafen med mellanslag (ta bort radbrytningar)
                paragraph_text = ' '.join(current_paragraph)
                cleaned_result_lines.append(paragraph_text)
                current_paragraph = []
            cleaned_result_lines.append('')  # Behåll tom rad för struktur
        else:
            current_paragraph.append(line.strip())

    # Glöm inte sista paragrafen
    if current_paragraph:
        paragraph_text = ' '.join(current_paragraph)
        cleaned_result_lines.append(paragraph_text)

    # Steg 1b: Bearbeta originalraderna på samma sätt för att bevara markeringar
    original_result_lines = []
    current_paragraph = []

    for line in original_lines:
        line = line.rstrip()

        # Om tom rad, avsluta nuvarande paragraf
        if not line.strip():
            if current_paragraph:
                # Slå ihop rader i paragrafen med mellanslag (ta bort radbrytningar)
                paragraph_text = ' '.join(current_paragraph)
                original_result_lines.append(paragraph_text)
                current_paragraph = []
            original_result_lines.append('')  # Behåll tom rad för struktur
        else:
            current_paragraph.append(line.strip())

    # Glöm inte sista paragrafen
    if current_paragraph:
        paragraph_text = ' '.join(current_paragraph)
        original_result_lines.append(paragraph_text)

    # Steg 2: Bearbeta resultatet för rubriker och fetstil-formatering
    formatted = []
    previous_line_empty = True  # Första raden räknas som början av nytt stycke

    # Kontrollera om rader är potentiella rubriker baserat på de rensade raderna
    potential_headers = []
    for i, line in enumerate(cleaned_result_lines):
        is_potential_header = (
            line.strip() and
            len(line) < 300 and
            # Krav på stor bokstav i början av raden (efter eventuella inledande specialtecken)
            re.match(r'^[A-ZÅÄÖ]', line.strip()) and
            # Grundläggande uteslutningar
            not line.strip().endswith(('.', ':')) and
            not line.strip().startswith('-') and  # Uteslut rader som börjar med bindestreck
            not re.match(r'^\d+\.', line.strip())  # Uteslut rader som börjar med siffra följt av punkt
        )
        potential_headers.append(is_potential_header)

    # Använd originalraderna för formatering men tillämpa rubriklogik baserat på rensade rader
    for i, original_line in enumerate(original_result_lines):
        if not original_line.strip():
            formatted.append('')  # Behåll tomma rader
            previous_line_empty = True
        else:
            # Hämta motsvarande rensad rad för rubrikanalys
            cleaned_line = cleaned_result_lines[i] if i < len(cleaned_result_lines) else ''

            # Kontrollera om nästnästa rad börjar med "1." för att undvika att göra en rad till rubrik
            next_is_list_start = False
            if i + 2 < len(cleaned_result_lines) and cleaned_result_lines[i + 2].strip().startswith("1."):
                next_is_list_start = True

            # Kontrollera om det är en rubrik (baserat på rensad rad men använd original för output)
            if potential_headers[i] and not next_is_list_start:
                # Kontrollera om det är ett kapitel (börjar med "X kap.") - använd rensad rad för analys
                if re.match(r'^\d+\s+kap\.', cleaned_line.strip()):
                    formatted.append(f'## {original_line}')
                # Om raden har max två ord OCH inte innehåller punkt, eller uppfyller de andra kriterierna
                elif (len(cleaned_line.split()) <= 2 and '.' not in cleaned_line) or (len(cleaned_line) < 300 and not cleaned_line.strip().endswith(('.', ':'))):
                    # Använd H3-rubrik för rubriker
                    formatted.append(f'### {original_line}')
                else:
                    # Hantera paragrafnummer baserat på parameter
                    if previous_line_empty and paragraph_as_header:
                        # Kontrollera om raden börjar med paragrafnummer (använd original rad)
                        paragraph_match = re.match(r'^(\d+ ?§)(.*)', original_line)
                        if paragraph_match:
                            paragraph_num = paragraph_match.group(1)
                            rest_of_line = paragraph_match.group(2).strip()
                            # Använd H4-rubrik för paragrafnummer, eftersom H2 är kapital och H3 är för rubriker
                            formatted.append(f'#### {paragraph_num}')
                            formatted.append('')  # Tom rad efter rubriken
                            if rest_of_line:
                                formatted.append(rest_of_line)
                        else:
                            formatted.append(original_line)
                    elif previous_line_empty:
                        # Fetstila paragrafnummer som vanligt
                        modified_line = re.sub(r'^(\d+ ?§)', r'**\1**', original_line)
                        formatted.append(modified_line)
                    else:
                        formatted.append(original_line)
            else:
                # Kontrollera om det är ett kapitel (börjar med "X kap.") även utanför potential_headers
                if re.match(r'^\d+\s+kap\.', cleaned_line.strip()):
                    formatted.append(f'## {original_line}')
                # Hantera paragrafnummer baserat på parameter
                elif previous_line_empty and paragraph_as_header:
                    # Kontrollera om raden börjar med paragrafnummer (använd original rad)
                    paragraph_match = re.match(r'^(\d+ ?§)(.*)', original_line)
                    if paragraph_match:
                        paragraph_num = paragraph_match.group(1)
                        rest_of_line = paragraph_match.group(2).strip()
                        formatted.append(f'#### {paragraph_num}')
                        formatted.append('')  # Tom rad efter rubriken
                        if rest_of_line:
                            formatted.append(rest_of_line)
                    else:
                        formatted.append(original_line)
                elif previous_line_empty:
                    # Fetstila paragrafnummer som vanligt
                    modified_line = re.sub(r'^(\d+ ?§)', r'**\1**', original_line)
                    formatted.append(modified_line)
                else:
                    formatted.append(original_line)
            previous_line_empty = False

    # Returnera den formaterade texten
    return '\n'.join(formatted)
