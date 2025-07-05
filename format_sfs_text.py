"""
Script för att formattera SFS-författningar (Svensk Författningssamling) i Markdown-format.

Regler som tillämpas:
1. Ta bort alla radbrytningar så att författningar blir flytande text (inte "wrappat")
2. Identifiera och formattera olika typer av rubriker:
   - Kapitel (ex. "1 kap.") blir H2-rubriker (##)
   - Bilagor (ex. "Bilaga A") blir H2-rubriker (##)
   - Vanliga rubriker (max två ord, ingen punkt) blir H3-rubriker (###)
   - Paragrafnummer (ex. "13 §", "3 a §") kan bli antingen:
     * H3-rubriker (###) när paragraph_as_header=True (standard)
     * H4-rubriker (####) inom potential_headers-sektionen
3. Dela in texten i logiska paragrafer och omringa dem med HTML-taggar <section>
   - Rubriker på nivå 2 (##) får CSS-klass "kapitel"
   - Rubriker på nivå 3-4 (###, ####) med § får CSS-klass "paragraf"
   - Innehåll eller rubriker med "upphävd", "har upphävts" eller "har upphävs" (felstavning som förekommer i vissa författningar) får attributet status="upphavd"
   - Innehåll eller rubriker med "/Träder i kraft I:YYYY-MM-DD" eller "/Rubriken träder i kraft I:YYYY-MM-DD" får attributet status="ikraft"
   - Datum parsas från "/Upphör att gälla U:YYYY-MM-DD/" till attributet upphor_datum="YYYY-MM-DD"
   - Datum parsas från "/Träder i kraft I:YYYY-MM-DD/" till attributet ikraft_datum="YYYY-MM-DD"
   - En sektion kan ha både status="upphavd ikraft" om den både träder i kraft och upphör
4. Hantering av ändringar och upphöranden:
   - Stycken med "/Rubriken träder i kraft I:YYYY-MM-DD/" efter rubriker tas bort
   - Stycken med "/Rubriken upphör att gälla U:YYYY-MM-DD/" efter rubriker tas bort
   - Stycken med "/Ny beteckning" efter paragrafer tas bort
   - Stycken med "/Upphör att gälla U:YYYY-MM-DD/" efter paragrafer tas bort

Regler som inte utvecklats än:
    - "Registrerings upphörande m.m." bör bli en rubrik (1970:485)   - Avdelningar (ex. "Avdelning 1") kan bli H2-rubriker (##)
   - Interna länkar till andra paragrafer (ex. "5 §" blir "[5 §](#5§)") formateras som interna markdown-länkar
   - Externa länkar till andra författningar (ex. "2020:123" blir "[2020:123](/sfs/2020:123)") formateras som externa markdown-länkar

"""

import re

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


def apply_changes_to_sfs_text(text: str, target_date: str = None, verbose: bool = False) -> str:
    """
    Formattera SFS-text med hantering av ändringar och upphöranden.

    .. deprecated::
        Denna funktion är obsolet och kommer att tas bort i framtida versioner.
        Använd istället parse_logical_paragraphs_new() som hanterar ändringar och
        upphöranden direkt i section-taggarna med selex: attribut.

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
        # TODO: Ska tas bort om target_date är tidigare än det datumet i texten
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
        # TODO: Ska vara kvar så länge som target_date är senare än det datumet i texten
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

    # Sätt ihop paragraferna igen med dubbla radbrytningar
    return '\n\n'.join(filtered_paragraphs)


def format_sfs_text_as_markdown(text: str, paragraph_as_header: bool = True, apply_links: bool = True) -> str:
    """
    Formattera texten från en författningstext importerad från
    Regeringskansliets rättsdatabas till Markdown-format.

    TODO: Prova att gör motsvarande med Riksdagens HTML-version som input.

    Args:
        text (str): Texten som ska formateras
        paragraph_as_header (bool): Om True, gör paragrafnummer till H3-rubriker istället för fetstil
        apply_links (bool): Om True, konvertera både interna paragrafnummer och SFS-beteckningar till markdown-länkar

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
    
    # Tillämpa interna paragraf-länkar och SFS-länkar om det begärs
    if apply_links:
        final_text = apply_internal_links(final_text)
        final_text = apply_sfs_links(final_text)

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


def apply_sfs_links(text: str) -> str:
    """
    Letar efter SFS-beteckningar i texten och konverterar dem till markdown-länkar.

    Söker efter mönster som "YYYY:NNN" (år:löpnummer) och skapar länkar till /sfs/(beteckning).

    Args:
        text (str): Texten som ska bearbetas

    Returns:
        str: Texten med SFS-beteckningar konverterade till markdown-länkar
    """
    # Regex för att hitta SFS-beteckningar: år (4 siffror) följt av kolon och löpnummer
    # Matchar mönster som "2002:43", "1970:485", etc.
    sfs_pattern = r'\b(\d{4}):(\d+)\b'

    # TODO: Slå upp SFS-beteckning mot JSON-fil för att verifiera giltighet

    def replace_sfs_designation(match):
        """Ersätter en SFS-beteckning med en markdown-länk"""
        year = match.group(1)
        number = match.group(2)
        designation = f"{year}:{number}"
        return f"[{designation}](/sfs/{designation})"

    # Ersätt alla SFS-beteckningar med markdown-länkar
    return re.sub(sfs_pattern, replace_sfs_designation, text)


def _is_section_upphavd(header_line: str, content: str) -> bool:
    """
    Kontrollera om en sektion ska markeras som upphävd baserat på rubrik och innehåll.

    Söker efter "upphävd", "har upphävts", "har upphävs" (felstavning),
    "/Rubriken upphör att gälla ", "/Upphör att gälla ", "/Kapitlet upphör att gälla ",
    eller "/Ny beteckning" i både rubrikens text och det direkta innehållet.
    Sökningen är case-insensitive.

    Args:
        header_line (str): Rubrikraden (med markdown-markeringar som ###)
        content (str): Det direkta innehållet under rubriken (exklusive underrubriker)

    Returns:
        bool: True om sektionen ska markeras som upphävd, False annars
    """
    # Konvertera till lowercase för case-insensitive sökning
    header_lower = header_line.lower()
    content_lower = content.lower()

    # Kontrollera både i rubrik och innehåll efter olika upphävd-markeringar
    # Observera: "har upphävs" är en felstavning som förekommer i vissa SFS-dokument (ex. 2018:263)
    return ('upphävd' in header_lower or
            'har upphävts' in header_lower or
            'har upphävs' in header_lower or
            '/rubriken upphör att gälla ' in header_lower or
            '/upphör att gälla ' in header_lower or
            '/kapitlet upphör att gälla ' in header_lower or
            '/kapitelrubriken upphör att gälla ' in header_lower or
            '/ny beteckning' in header_lower or
            'upphävd' in content_lower or
            'har upphävts' in content_lower or
            'har upphävs' in content_lower or
            '/rubriken upphör att gälla ' in content_lower or
            '/upphör att gälla ' in content_lower or
            '/kapitlet upphör att gälla ' in content_lower or
            '/kapitelrubriken upphör att gälla ' in content_lower or
            '/ny beteckning' in content_lower)


def _is_section_ikraft(header_line: str, content: str) -> bool:
    """
    Kontrollera om en sektion ska markeras som "träder ikraft" baserat på rubrik och innehåll.

    Söker efter "/Träder i kraft I:YYYY-MM-DD", "/Rubriken träder i kraft I:YYYY-MM-DD",
    "/Kapitlet träder i kraft I:YYYY-MM-DD" med giltigt datum, eller
    "/Träder i kraft I:villkor", "/Rubriken träder i kraft I:villkor",
    "/Kapitlet träder i kraft I:villkor" med villkor istället för datum i både
    rubrikens text och det direkta innehållet. Sökningen är case-insensitive.

    Args:
        header_line (str): Rubrikraden (med markdown-markeringar som ###)
        content (str): Det direkta innehållet under rubriken (exklusive underrubriker)

    Returns:
        bool: True om sektionen ska markeras som "träder ikraft", False annars
    """
    # Konvertera till lowercase för case-insensitive sökning
    header_lower = header_line.lower()
    content_lower = content.lower()

    # Kontrollera både i rubrik och innehåll efter ikraft-markeringar med giltigt datum
    # Mönster för "/Träder i kraft I:YYYY-MM-DD" med giltigt datum
    ikraft_datum_pattern = r'/träder i kraft i:\d{4}-\d{2}-\d{2}'
    rubrik_ikraft_datum_pattern = r'/rubriken träder i kraft i:\d{4}-\d{2}-\d{2}'
    kapitlet_ikraft_datum_pattern = r'/kapitlet träder i kraft i:\d{4}-\d{2}-\d{2}'
    kapitelrubriken_ikraft_datum_pattern = r'/kapitelrubriken träder i kraft i:\d{4}-\d{2}-\d{2}'

    # Mönster för "/Träder i kraft I:villkor" (inte datum)
    ikraft_villkor_pattern = r'/träder i kraft i:[^/]+'
    rubrik_ikraft_villkor_pattern = r'/rubriken träder i kraft i:[^/]+'
    kapitlet_ikraft_villkor_pattern = r'/kapitlet träder i kraft i:[^/]+'
    kapitelrubriken_ikraft_villkor_pattern = r'/kapitelrubriken träder i kraft i:[^/]+'

    return (re.search(ikraft_datum_pattern, header_lower) is not None or
            re.search(rubrik_ikraft_datum_pattern, header_lower) is not None or
            re.search(kapitlet_ikraft_datum_pattern, header_lower) is not None or
            re.search(kapitelrubriken_ikraft_datum_pattern, header_lower) is not None or
            re.search(ikraft_datum_pattern, content_lower) is not None or
            re.search(rubrik_ikraft_datum_pattern, content_lower) is not None or
            re.search(kapitlet_ikraft_datum_pattern, content_lower) is not None or
            re.search(kapitelrubriken_ikraft_datum_pattern, content_lower) is not None or
            re.search(ikraft_villkor_pattern, header_lower) is not None or
            re.search(rubrik_ikraft_villkor_pattern, header_lower) is not None or
            re.search(kapitlet_ikraft_villkor_pattern, header_lower) is not None or
            re.search(kapitelrubriken_ikraft_villkor_pattern, header_lower) is not None or
            re.search(ikraft_villkor_pattern, content_lower) is not None or
            re.search(rubrik_ikraft_villkor_pattern, content_lower) is not None or
            re.search(kapitlet_ikraft_villkor_pattern, content_lower) is not None or
            re.search(kapitelrubriken_ikraft_villkor_pattern, content_lower) is not None)


def parse_logical_sections(text: str) -> str:
    """
    Dela upp texten i logiska sektioner baserat på Markdown-rubriker och omslut
    varje rubrik och dess innehåll med <section>-taggar.

    CSS-klass läggs till baserat på sektionen:
    - Rubriknivå 2 (##): class="kapitel"
    - Rubriknivå 3 eller 4 (### eller ####) med § i rubriken: class="paragraf"

    Status-attribut läggs till baserat på sektionens innehåll:
    - Om sektionens innehåll (exklusive underrubriker) eller rubrikens text innehåller "upphävd",
      "har upphävts" eller "har upphävs" (felstavning som förekommer i vissa författningar) läggs
      attributet status="upphavd" till.
    - Om sektionens innehåll eller rubrik innehåller "/Träder i kraft I:YYYY-MM-DD" eller
      "/Rubriken träder i kraft I:YYYY-MM-DD" läggs attributet status="ikraft" till.

    Datum-attribut läggs till baserat på sektionens innehåll:
    - Om sektionens innehåll eller rubrik innehåller "/Upphör att gälla U:YYYY-MM-DD/"
      parsas datumet ut och läggs till som attributet upphor_datum="YYYY-MM-DD".
    - Om sektionens innehåll eller rubrik innehåller "/Träder i kraft I:YYYY-MM-DD/"
      parsas datumet ut och läggs till som attributet ikraft_datum="YYYY-MM-DD".

    Konsistenskontroll:
    - Om upphor_datum hittas men sektionen inte är markerad som upphävd kastas ValueError.
    - Om ikraft_datum hittas men sektionen inte är markerad som ikraft kastas ValueError.
    - En sektion kan ha både status="upphavd ikraft" om den både träder i kraft och upphör.

    Args:
        text (str): Markdown-formaterad text med rubriker

    Returns:
        str: Text med <section>-taggar runt varje rubrik och dess innehåll
    """
    lines = text.split('\n')
    result = []
    current_section = []
    section_stack = []  # Stack för att hålla koll på nestlade sektioner

    def close_sections_to_level(target_level):
        """Stäng alla sektioner ner till målnivån"""
        nonlocal section_stack, result
        while section_stack and section_stack[-1] >= target_level:
            result.append('</section>')
            section_stack.pop()

    def process_current_section():
        """Bearbeta och lägg till nuvarande sektion"""
        nonlocal current_section, result
        if current_section:
            # Hitta rubriknivån för huvudrubriken i denna sektion
            main_header_line = current_section[0] if current_section else ""
            main_header_match = re.match(r'^(#{2,6})\s+(.+)', main_header_line)
            main_header_level = len(main_header_match.group(1)) if main_header_match else 2

            # Extrahera endast det direkta innehållet under huvudrubriken,
            # exklusive alla underrubriker och deras innehåll
            direct_content = []
            i = 1  # Börja efter huvudrubriken

            while i < len(current_section):
                line = current_section[i]
                subheader_match = re.match(r'^(#{2,6})\s+(.+)', line)

                if subheader_match:
                    # Detta är en underrubrik
                    subheader_level = len(subheader_match.group(1))

                    # Om det är en underrubrik (djupare nivå än huvudrubriken)
                    if subheader_level > main_header_level:
                        # Hoppa över denna underrubrik och allt dess innehåll
                        # tills vi hittar nästa rubrik på samma eller högre nivå
                        i += 1
                        while i < len(current_section):
                            next_line = current_section[i]
                            next_header_match = re.match(r'^(#{2,6})\s+(.+)', next_line)

                            if next_header_match:
                                next_header_level = len(next_header_match.group(1))
                                # Om vi hittar en rubrik på samma eller högre nivå, sluta hoppa över
                                if next_header_level <= subheader_level:
                                    break
                            i += 1
                        continue
                    else:
                        # Detta är en rubrik på samma eller högre nivå, så vi är klara
                        break
                else:
                    # Detta är vanligt innehåll, lägg till det
                    direct_content.append(line)

                i += 1

            # Kontrollera "upphävd" i det direkta innehållet OCH i rubrikens text
            filtered_content = '\n'.join(direct_content)
            header_line = current_section[0] if current_section else ""

            # Använd hjälpfunktion för att kontrollera upphävd-status
            has_upphavd = _is_section_upphavd(header_line, filtered_content)

            # Sök efter "U:YYYY-MM-DD" i både rubrik och innehåll
            upphor_datum = None
            all_section_content = '\n'.join(current_section)
            upphor_match = re.search(r'U:(\d{4}-\d{2}-\d{2})', all_section_content)
            if upphor_match:
                upphor_datum = upphor_match.group(1)

                # Kontrollera konsistens: om vi hittar upphor_datum ska sektionen också vara upphävd
                if not has_upphavd:
                    raise ValueError(f"Inkonsistens upptäckt: Sektion har upphor_datum '{upphor_datum}' men är inte markerad som upphävd. Rubrik: '{header_line}', Innehåll: '{filtered_content[:100]}...'")

            # Kontrollera "ikraft" i det direkta innehållet OCH i rubrikens text
            has_ikraft = _is_section_ikraft(header_line, filtered_content)

            # Sök efter "I:YYYY-MM-DD" i både rubrik och innehåll
            ikraft_datum = None
            ikraft_villkor = None

            # Först, sök efter datum
            ikraft_match = re.search(r'I:(\d{4}-\d{2}-\d{2})', all_section_content)
            if ikraft_match:
                ikraft_datum = ikraft_match.group(1)

                # Kontrollera konsistens: om vi hittar ikraft_datum ska sektionen också vara ikraft
                if not has_ikraft:
                    raise ValueError(f"Inkonsistens upptäckt: Sektion har ikraft_datum '{ikraft_datum}' men är inte markerad som ikraft. Rubrik: '{header_line}', Innehåll: '{filtered_content[:100]}...'")
            else:
                # Om inget datum hittas, sök efter villkor
                # Mönster för "/Träder i kraft I:villkor/" eller "/Rubriken träder i kraft I:villkor/" eller "/Kapitlet träder i kraft I:villkor/"
                ikraft_villkor_match = re.search(r'/(?:rubriken |kapitlet )?träder i kraft i:([^/]+)/', all_section_content, re.IGNORECASE)
                if ikraft_villkor_match:
                    ikraft_villkor = ikraft_villkor_match.group(1).strip()

                    # Kontrollera konsistens: om vi hittar ikraft_villkor ska sektionen också vara ikraft
                    if not has_ikraft:
                        raise ValueError(f"Inkonsistens upptäckt: Sektion har ikraft_villkor '{ikraft_villkor}' men är inte markerad som ikraft. Rubrik: '{header_line}', Innehåll: '{filtered_content[:100]}...'")

            # Bestäm CSS-klass baserat på rubriknivå och innehåll
            css_classes = []

            # Hitta rubriken i sektionen för att bestämma nivå och innehåll
            header_line = current_section[0] if current_section else ""
            header_match = re.match(r'^(#{2,6})\s+(.+)', header_line)

            if header_match:
                header_level = len(header_match.group(1))
                header_text = header_match.group(2)

                # Lägg till klasser baserat på rubriknivå och innehåll
                if header_level == 2:
                    if '§' in header_text:
                        css_classes.append('paragraf')
                    else:
                        css_classes.append('kapitel')
                elif (header_level == 3 or header_level == 4) and '§' in header_text:
                    css_classes.append('paragraf')

            # Bygg section-tagg med attribut
            attributes = []
            if css_classes:
                attributes.append(f'class="{" ".join(css_classes)}"')
            
            # Hantera status attribut - en sektion kan ha både upphävd och ikraft
            status_values = []
            if has_upphavd:
                status_values.append('upphavd')
            if has_ikraft:
                status_values.append('ikraft')
            
            if status_values:
                attributes.append(f'selex:status="{" ".join(status_values)}"')
            
            if upphor_datum:
                attributes.append(f'selex:upphor_datum="{upphor_datum}"')
            if ikraft_datum:
                attributes.append(f'selex:ikraft_datum="{ikraft_datum}"')
            if ikraft_villkor:
                attributes.append(f'selex:ikraft_villkor="{ikraft_villkor}"')

            if attributes:
                result.append(f'<section {" ".join(attributes)}>')
            else:
                result.append('<section>')

            # Lägg till innehållet
            result.extend(current_section)

            # Rensa nuvarande sektion
            current_section = []

    for line in lines:
        # Kontrollera om raden är en markdown-rubrik
        header_match = re.match(r'^(#{2,6})\s+(.+)', line)

        if header_match:
            header_level = len(header_match.group(1))  # Antal # tecken

            # Om vi har en pågående sektion, bearbeta den först
            if current_section:
                process_current_section()

            # Stäng sektioner som är på samma eller djupare nivå
            close_sections_to_level(header_level)

            # Starta ny sektion
            current_section = [line]
            section_stack.append(header_level)

        else:
            # Lägg till raden till nuvarande sektion
            current_section.append(line)

    # Bearbeta sista sektionen
    if current_section:
        process_current_section()

    # Stäng alla återstående sektioner
    close_sections_to_level(0)

    return '\n'.join(result)


def apply_internal_links(text: str) -> str:
    """
    Letar efter paragrafnummer i löpande text (inte i rubriker) och konverterar dem till interna länkar.

    Söker efter mönster som "9 §", "13 a §", "2 b §" etc. och skapar interna länkar
    till [9 §](#9§), [13 a §](#13a§), [2 b §](#2b§).

    Args:
        text (str): Texten som ska bearbetas

    Returns:
        str: Texten med paragrafnummer konverterade till interna markdown-länkar
    """
    lines = text.split('\n')
    processed_lines = []

    for line in lines:
        # Skippa rubriker (börjar med #)
        if line.strip().startswith('#'):
            processed_lines.append(line)
            continue

        # Regex för att hitta paragrafnummer: siffra, eventuell bokstav, följt av §
        # Matchar mönster som "9 §", "13 a §", "2 b §", "145 c §", etc.
        paragraph_pattern = r'(\d+)(?:\s+([a-z]))?\s*§'

        def replace_paragraph_reference(match):
            """Ersätter en paragrafnummer med en intern markdown-länk"""
            number = match.group(1)
            letter = match.group(2) if match.group(2) else ''

            # Skapa länktext och anchor
            link_text = f"{number}{' ' + letter if letter else ''} §"
            # Anchor utan mellanslag för URL-kompatibilitet
            anchor = f"{number}{letter if letter else ''}§"

            return f"[{link_text}](#{anchor})"

        # Ersätt alla paragrafnummer med interna länkar
        processed_line = re.sub(paragraph_pattern, replace_paragraph_reference, line)
        processed_lines.append(processed_line)

    return '\n'.join(processed_lines)
