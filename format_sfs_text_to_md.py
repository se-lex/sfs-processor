"""
Script för att formattera SFS-dokument (Svensk Författningssamling) i Markdown-format.

Regler som tillämpas:
1. Ta bort alla radbrytningar så att dokumentet blir flytande text (inte "wrappat")
2. Identifiera och formattera olika typer av rubriker:
   - Kapitel (ex. "1 kap.") blir H2-rubriker (##)
   - Bilagor (ex. "Bilaga A") blir H2-rubriker (##)
   - Vanliga rubriker (max två ord, ingen punkt) blir H3-rubriker (###)
   - Paragrafnummer (ex. "13 §", "3 a §") kan bli antingen:
     * H3-rubriker (###) när paragraph_as_header=True (standard)
     * H4-rubriker (####) inom potential_headers-sektionen
     * Fetstil (**text**) när paragraph_as_header=False
3. Hantering av ändringar och upphöranden:
   - Stycken med "/Ny beteckning" efter paragrafer tas bort
   - Stycken med "/Upphör att gälla U:YYYY-MM-DD/" efter paragrafer tas bort

"""

import re

def apply_changes_to_sfs_text(text: str, target_date: str = None, verbose: bool = False) -> str:
    """
    Formattera SFS-text med hantering av ändringar och upphöranden.

    Regler:
    1. Om "/Ny beteckning" förekommer efter en paragraf (ex. **13 §**) ska hela stycket tas bort
    2. Om "/Upphör att gälla" med datum förekommer efter en paragraf ska hela stycket tas bort
    3. Om "/Rubriken träder i kraft I:YYYY-MM-DD/" förekommer efter en paragraf ska hela stycket tas bort
    4. Om "/Rubriken upphör att gälla U:YYYY-MM-DD/" förekommer före en underrubrik ska hela stycket tas bort

    Om target_date anges, tillämpas reglerna endast om datumet i I: eller U: matchar target_date.

    Args:
        text (str): Texten som ska formateras
        target_date (str, optional): Datum i format YYYY-MM-DD som ska matchas mot I: eller U: datum
        verbose (bool): Om True, skriv ut information när regler tillämpas

    Returns:
        str: Den formaterade texten med ändringar borttagna

    Raises:
        ValueError: Om inga regler kunde tillämpas (inga ändringar gjordes)
    """
    def parse_logical_paragraphs(text: str) -> list:
        """
        Dela upp texten i logiska paragrafer baserat på dubbla radbrytningar,
        men se till att rubriker inkluderas tillsammans med sitt innehåll.
        Slår också ihop rader inom varje paragraf så att markeringar hamnar på samma rad.
        """
        # Dela på dubbla radbrytningar först
        raw_paragraphs = text.split('\n\n')

        logical_paragraphs = []
        i = 0

        while i < len(raw_paragraphs):
            current_paragraph = raw_paragraphs[i]

            # Slå ihop alla rader inom paragrafen med mellanslag (för att hantera markeringar på separata rader)
            paragraph_lines = current_paragraph.split('\n')
            consolidated_paragraph = ' '.join(line.strip() for line in paragraph_lines if line.strip())

            # Om detta stycke är bara en rubrik, kontrollera vad som kommer härnäst
            if (re.match(r'^#{2,4}\s+', consolidated_paragraph.strip()) and
                i + 1 < len(raw_paragraphs)):
                # Konsolidera nästa paragraf för att kontrollera om det också är en rubrik
                next_paragraph = raw_paragraphs[i + 1]
                next_paragraph_lines = next_paragraph.split('\n')
                consolidated_next = ' '.join(line.strip() for line in next_paragraph_lines if line.strip())

                # Om nästa stycke också är en rubrik, behandla denna rubrik som egen paragraf
                if re.match(r'^#{2,4}\s+', consolidated_next.strip()):
                    logical_paragraphs.append(consolidated_paragraph)
                    i += 1  # Gå vidare till nästa stycke utan att slå ihop
                else:
                    # Slå ihop rubriken med nästa stycke som tidigare
                    combined = consolidated_paragraph + '\n\n' + consolidated_next
                    logical_paragraphs.append(combined)
                    i += 2  # Hoppa över nästa stycke eftersom vi redan behandlat det
            else:
                logical_paragraphs.append(consolidated_paragraph)
                i += 1

        return logical_paragraphs

    # Dela upp texten i logiska paragrafer
    paragraphs = parse_logical_paragraphs(text)

    filtered_paragraphs = []
    changes_applied = 0  # Räkna antal tillämpade ändringar

    if verbose:
        print(f"Tillämpar ändringsregler för datum: {target_date if target_date else 'alla datum'}")
        print(f"Antal logiska paragrafer att analysera: {len(paragraphs)}")

    for i, paragraph in enumerate(paragraphs):
        paragraph_removed = False

        # Kontrollera om stycket innehåller "/Ny beteckning"
        if '/Ny beteckning' in paragraph:
            # Ta bort bara markeringen och trimma extra mellanslag
            old_paragraph = paragraph
            paragraph = re.sub(r'\s*/Ny beteckning\s*', ' ', paragraph)
            paragraph = re.sub(r'\s+', ' ', paragraph).strip()  # Normalisera mellanslag
            changes_applied += 1
            if verbose:
                print(f"Regel 1 tillämpas: Tar bort '/Ny beteckning' markering från paragraf {i+1}")
                print(f"\033[32m{paragraph}\033[0m")  # Grön text för det nya resultatet
                print("-" * 80)

        # Kontrollera om stycket innehåller "/Upphör att gälla" med datum
        upphör_match = re.search(r'/Upphör att gälla U:(\d{4}-\d{2}-\d{2})/', paragraph)
        if upphör_match:
            date_in_text = upphör_match.group(1)
            # Om target_date är angivet, kontrollera att det matchar
            if target_date is None or date_in_text == target_date:
                # Kontrollera om det föregås av en paragraf (####)
                if re.search(r'####\s+', paragraph):
                    # Ta bort hela stycket
                    changes_applied += 1
                    paragraph_removed = True
                    if verbose:
                        print(f"Regel 2 tillämpas: Tar bort paragraf {i+1} med '/Upphör att gälla U:{date_in_text}/'")
                        print(f"\033[91m{paragraph}\033[0m")  # Röd text
                        print("-" * 80)
                    continue
                else:
                    # Varna om att det inte föregås av en paragraf
                    if verbose:
                        print(f"Regel 2 varning: '/Upphör att gälla U:{date_in_text}/' i paragraf {i+1} utan föregående paragraf")
                        print(f"\033[93m{paragraph}\033[0m")  # Gul text för varning
                        print("-" * 80)
            else:
                if verbose:
                    print(f"Regel 2 varning: '/Upphör att gälla U:{date_in_text}/' i paragraf {i+1} inte matchar target_date {target_date}")

        # Kontrollera om det står "/Rubriken träder i kraft" med datum
        rubrik_träder_match = re.search(r'/Rubriken träder i kraft I:(\d{4}-\d{2}-\d{2})/', paragraph)
        if rubrik_träder_match:
            date_in_text = rubrik_träder_match.group(1)
            # Om target_date är angivet, kontrollera att det matchar
            if target_date is None or date_in_text == target_date:
                # Ta bort bara markeringen och trimma extra mellanslag
                old_paragraph = paragraph
                paragraph = re.sub(r'\s*/Rubriken träder i kraft I:\d{4}-\d{2}-\d{2}/\s*', ' ', paragraph)
                paragraph = re.sub(r'\s+', ' ', paragraph).strip()  # Normalisera mellanslag
                changes_applied += 1
                if verbose:
                    print(f"Regel 3 tillämpas: Tar bort '/Rubriken träder i kraft I:{date_in_text}/' markering från paragraf {i+1}")
                    print(f"Före: \033[33m{old_paragraph}\033[0m")  # Gul text för före (närmare orange)
                    print(f"Efter: \033[32m{paragraph}\033[0m")  # Grön text för efter
                    print("-" * 80)

        # Kontrollera om det står "/Rubriken upphör att gälla" med datum
        rubrik_upphör_match = re.search(r'/Rubriken upphör att gälla U:(\d{4}-\d{2}-\d{2})/', paragraph)
        if rubrik_upphör_match:
            date_in_text = rubrik_upphör_match.group(1)

            # Om target_date är angivet, kontrollera att det matchar
            if target_date is None or date_in_text == target_date:
                # Hitta rubriknivån för den rubrik som ska upphöra
                header_match = re.search(r'^(#{2,4})\s+', paragraph)
                if header_match:
                    header_level = len(header_match.group(1))  # Antal # tecken

                    # Markera denna paragraf för borttagning
                    changes_applied += 1
                    paragraph_removed = True

                    if verbose:
                        print(f"Regel 4 tillämpas: Tar bort rubriknivå {header_level} med '/Rubriken upphör att gälla U:{date_in_text}/' från paragraf {i+1}")
                        print(f"\033[91m{paragraph}\033[0m")  # Röd text
                        print("-" * 80)

                    # Ta även bort alla efterföljande paragrafer tills nästa rubrik på samma eller högre nivå
                    j = i + 1
                    while j < len(paragraphs):
                        next_paragraph = paragraphs[j]
                        next_header_match = re.search(r'^(#{2,4})\s+', next_paragraph)

                        if next_header_match:
                            next_header_level = len(next_header_match.group(1))
                            # Om vi hittar en rubrik på samma eller högre nivå (färre #), sluta ta bort
                            if next_header_level <= header_level:
                                break

                        # Markera denna paragraf för borttagning också
                        changes_applied += 1
                        if verbose:
                            print(f"Regel 4 tillämpas: Tar bort underordnad paragraf {j+1} under upphörd rubrik")
                            print(f"\033[91m{next_paragraph}\033[0m")  # Röd text
                            print("-" * 80)

                        # Sätt en markering så vi vet att hoppa över denna paragraf i huvudloopen
                        paragraphs[j] = "___REMOVE_THIS_PARAGRAPH___"
                        j += 1

                    continue

        # Skippa paragrafer som markerats för borttagning av regel 4
        if paragraph == "___REMOVE_THIS_PARAGRAPH___":
            continue

        # Om inget av ovanstående matchar, behåll stycket
        if not paragraph_removed:
            filtered_paragraphs.append(paragraph)

    if verbose:
        print(f"Totalt antal tillämpade regler: {changes_applied}")
        print(f"Antal paragrafer kvar efter filtrering: {len(filtered_paragraphs)}")

    # Kontrollera om inga regler kunde tillämpas
    # if changes_applied == 0:
    #      if target_date:
    #          raise ValueError(f"Inga regler kunde tillämpas för datum {target_date}. Kontrollera att texten innehåller relevanta ändringsmarkeringar med detta datum.")
    #      else:
    #          raise ValueError("Inga regler kunde tillämpas. Kontrollera att texten innehåller relevanta ändringsmarkeringar (/Ny beteckning, /Upphör att gälla, /Rubriken träder i kraft, /Rubriken upphör att gälla).")

    # Sätt ihop paragraferna igen med dubbla radbrytningar
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

    # Undvik radbrytningar utan låt dokumentet bli flytande text
    original_result_lines = []
    current_paragraph = []

    for line in original_lines:
        line = line.rstrip()

        # Om tom rad, avsluta nuvarande paragraf
        if not line.strip():
            if current_paragraph:
                # Slå ihop rader i paragrafen med mellanslag (behåll markeringar)
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

    # Använd originalraderna för formatering men tillämpa rubriklogik baserat på rensade rader
    for i, original_line in enumerate(original_result_lines):
        if not original_line.strip():
            formatted.append('')  # Behåll tomma rader
            previous_line_empty = True
        else:
            # Rensa raden för rubrikanalys (ta bort /-markeringar)
            cleaned_line = re.sub(r'/[^/]+/', '', original_line).strip()

            # Kontrollera om nästnästa rad börjar med "1." för att undvika att göra en rad till rubrik
            next_is_list_start = False
            if i + 2 < len(original_result_lines) and original_result_lines[i + 2].strip().startswith("1."):
                next_is_list_start = True

            # Kontrollera om det är en potentiell rubrik (direkt kontroll istället för förberäknad lista)
            is_potential_header = (
                cleaned_line.strip() and
                len(cleaned_line) < 300 and
                # Krav på stor bokstav i början av raden (efter eventuella inledande specialtecken)
                re.match(r'^[A-ZÅÄÖ]', cleaned_line.strip()) and
                # Grundläggande uteslutningar
                not cleaned_line.strip().endswith(('.', ':')) and
                not cleaned_line.strip().startswith('-') and  # Uteslut rader som börjar med bindestreck
                not re.match(r'^\d+\.', cleaned_line.strip())  # Uteslut rader som börjar med siffra följt av punkt
            )

            # Kontrollera om det är en rubrik (baserat på rensad rad men använd original för output)
            if is_potential_header and not next_is_list_start:
                # Kontrollera om det är ett kapitel (börjar med "X kap.") - använd rensad rad för analys
                if re.match(r'^\d+\s+kap\.', cleaned_line.strip()):
                    formatted.append(format_header_with_markings('##', original_line))
                # Kontrollera om det är en bilaga (börjar med "Bilaga ") - använd rensad rad för analys
                elif cleaned_line.strip().startswith('Bilaga '):
                    formatted.append(format_header_with_markings('##', original_line))
                # Om raden har max två ord OCH inte innehåller punkt, eller uppfyller de andra kriterierna
                elif (len(cleaned_line.split()) <= 2 and '.' not in cleaned_line) or (len(cleaned_line) < 300 and not cleaned_line.strip().endswith(('.', ':'))):
                    # Använd H3-rubrik för rubriker
                    formatted.append(format_header_with_markings('###', original_line))
                else:
                    # Hantera paragrafnummer baserat på parameter
                    if previous_line_empty and paragraph_as_header:
                        # Kontrollera om raden börjar med paragrafnummer (använd original rad)
                        paragraph_match = re.match(r'^\d+\s*[a-z]?\s*§', original_line)
                        if paragraph_match:
                            paragraph_num = paragraph_match.group(0)
                            # Placera paragrafnummer på egen rad
                            formatted.append(f'#### {paragraph_num}')
                            formatted.append('')  # Tom rad efter rubriken
                            rest_of_line = original_line[len(paragraph_num):].strip()
                            if rest_of_line:
                                formatted.append(rest_of_line)
                        else:
                            formatted.append(original_line)
                    elif previous_line_empty:
                        # Fetstila paragrafnummer som vanligt
                        modified_line = re.sub(r'^(\d+\s*[a-z]?\s*§)', r'**\1**', original_line)
                        formatted.append(modified_line)
                    else:
                        formatted.append(original_line)
            else:
                # Kontrollera om det är ett kapitel (börjar med "X kap.") även utanför potential_headers
                if re.match(r'^\d+\s+kap\.', cleaned_line.strip()):
                    formatted.append(format_header_with_markings('##', original_line))
                # Kontrollera om det är en bilaga (börjar med "Bilaga ") även utanför potential_headers
                elif cleaned_line.strip().startswith('Bilaga '):
                    formatted.append(format_header_with_markings('##', original_line))
                # Hantera paragrafnummer baserat på parameter
                elif previous_line_empty and paragraph_as_header:
                    # Kontrollera om raden börjar med paragrafnummer (använd original rad)
                    paragraph_match = re.match(r'^\d+\s*[a-z]?\s*§', original_line)
                    if paragraph_match:
                        paragraph_num = paragraph_match.group(0)
                        # Placera paragrafnummer på egen rad
                        formatted.append(f'#### {paragraph_num}')
                        formatted.append('')  # Tom rad efter rubriken
                        rest_of_line = original_line[len(paragraph_num):].strip()
                        if rest_of_line:
                            formatted.append(rest_of_line)
                    else:
                        formatted.append(original_line)
                elif previous_line_empty:
                    # Fetstila paragrafnummer som vanligt
                    modified_line = re.sub(r'^(\d+\s*[a-z]?\s*§)', r'**\1**', original_line)
                    formatted.append(modified_line)
                else:
                    formatted.append(original_line)
            previous_line_empty = False

    # Returnera den formaterade texten
    final_text = '\n'.join(formatted)

    return final_text.strip()  # Ta bort eventuella inledande eller avslutande tomma rader


def format_header_with_markings(header_level: str, text: str) -> str:
    """
    Formattera en rubrik och flytta eventuella markeringar (ex. /Ny beteckning/)
    till direkt efter rubrikmarkören men före rubriktexten.

    Args:
        header_level (str): Rubriknivå som "##" eller "###" eller "####"
        text (str): Texten som kan innehålla markeringar

    Returns:
        str: Formaterad rubrik med markeringar i rätt position
    """
    # Hitta alla markeringar i texten
    markings = re.findall(r'/[^/]+/', text)

    if markings:
        # Ta bort alla markeringar från texten
        cleaned_text = re.sub(r'\s*/[^/]+/\s*', ' ', text)
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

        # Skapa rubriken med markeringar direkt efter rubrikmarkören
        markings_str = ' '.join(markings)
        return f"{header_level} {markings_str} {cleaned_text}"
    else:
        # Ingen markering hittad, returnera som vanligt
        return f"{header_level} {text}"
