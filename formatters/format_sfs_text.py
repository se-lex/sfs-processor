"""
Script för att formattera SFS-författningar (Svensk Författningssamling) i Markdown-format.

Regler som tillämpas:
1. Ta bort alla radbrytningar så att författningar blir flytande text (inte "wrappat")
2. Identifiera och formattera olika typer av rubriker:
   - Kapitel (ex. "1 kap.") blir H2-rubriker (##)
   - Bilagor (ex. "Bilaga A") blir H2-rubriker (##)
   - Vanliga rubriker (max två ord, ingen punkt) blir H3-rubriker (###)
   - Paragrafnummer (ex. "13 §", "3 a §") blir H4-rubriker (####)
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
from typing import Optional
from .apply_links import apply_sfs_links, apply_internal_links, apply_eu_links, apply_law_name_links
from util.text_utils import WHITESPACE_PATTERN

# Regex patterns as constants
PARAGRAPH_PATTERN = r'(\d+(?:\s*[a-z])?)\s*§'
CHAPTER_PATTERN = r'^(\d+)(?:\s*([a-zA-Z]))?\s*[Kk]ap\.?'  # t.ex. 1 kap., 2 a kap.
DIVISION_PATTERN_1 = r'^(?:AVDELNING|AVD\.)\s*[IVX]+(?:\.|$|\s)'
DIVISION_PATTERN_2 = r'^(?:FÖRSTA|ANDRA|TREDJE|FJÄRDE|FEMTE|SJÄTTE|SJUNDE|ÅTTONDE|NIONDE|TIONDE)\s+(?:AVDELNING|AVD\.)'
ARTIKEL_PATTERN = r'^Artikel\s+\d+$'
ATTACHMENT_PREFIX = 'Bilaga '

HEADER_LEVEL_PATTERN = r'^(#{2,6})\s+(.+)'
LIST_NUMBERED_PATTERN = r'^\d+\.'
LIST_BULLET_PREFIX = '-'
TEMPORAL_MARKER_PATTERN = r'/[^/]+/'
# SFS_PATTERN moved to apply_links.py
CAPITALIZED_PATTERN = r'^[A-ZÅÄÖ]'

# Section and article tag patterns
SECTION_TAG_PATTERN = r'^\s*<section[^>]*>\s*$'
SECTION_CLOSE_TAG_PATTERN = r'^\s*</section>\s*$'
ARTICLE_TAG_PATTERN = r'^\s*<article[^>]*>\s*$'
ARTICLE_CLOSE_TAG_PATTERN = r'^\s*</article>\s*$'

# Temporal patterns
INTOFORCE_ANY_PATTERN = r'/(?:rubriken |kapitlet |kapitelrubriken )?träder i kraft [Ii]:[^/]+'
INTOFORCE_FULL_TEMPORAL_TAG_PATTERN = r'/(?:rubriken |kapitlet |kapitelrubriken )?träder i kraft [Ii]:[^/]+/\s*'
INTOFORCE_DATE_EXTRACT_PATTERN = r'[Ii]:(\d{4}-\d{2}-\d{2})'

REVOKE_FULL_TEMPORAL_TAG_PATTERN = r'/(?:rubriken |kapitlet |kapitelrubriken )?upphör att gälla [Uu]:[^/]+/\s*'
REVOKE_DATE_EXTRACT_PATTERN = r'[Uu]:(\d{4}-\d{2}-\d{2})'

# Exclusion patterns
DEFINITION_PATTERN = r'^I denna (förordning|lag) avses med$'
ADMIN_PATTERN = r'^(Lagen|Myndigheten|Utbildningen) (gäller|ska)$'
JURIDIC_PHRASE_PATTERN = r'^(Genom|Enligt|Om (?!det)|För att|Till böter|Vid|På begäran|När|Under|Efter|Med (?!det)|Av (?!det)|Till (?!det)|I (?:denna|detta|enlighet|den|det|fråga|samma)|Från|På grund av|Dessa )'
SPECIFIC_JURIDIC_PATTERN = r'^(Denna lag gäller inte|Denna lag träder i kraft|Denna konvention tillämpas|Konventionen upphör)$'


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
        if (re.match(HEADER_LEVEL_PATTERN, consolidated_paragraph.strip()) and
            i + 1 < len(raw_paragraphs)):
            # Konsolidera nästa paragraf för att kontrollera om det också är en rubrik
            next_paragraph = raw_paragraphs[i + 1]
            next_paragraph_lines = next_paragraph.split('\n')
            consolidated_next = ' '.join(line.strip() for line in next_paragraph_lines if line.strip())

            # Om nästa stycke också är en rubrik, behandla denna rubrik som egen paragraf
            if re.match(HEADER_LEVEL_PATTERN, consolidated_next.strip()):
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





def _add_header_with_blank_line(formatted: list, header_level: str, original_line: str) -> None:
    """
    Lägg till en rubrik med tom rad före om nödvändigt enligt markdown-standarden.
    
    Args:
        formatted (list): Lista med formaterade rader
        header_level (str): Rubriknivå som "##" eller "###" eller "####"
        original_line (str): Originalraden som ska formateras
    """
    # Lägg till tom rad före rubrik om föregående rad inte är tom
    if formatted and formatted[-1].strip():
        formatted.append('')
    formatted.append(format_header_with_markings(header_level, original_line))


def format_sfs_text_as_markdown(text: str, apply_links: bool = False) -> str:
    """
    Formattera texten från en författningstext importerad från
    Regeringskansliets rättsdatabas till Markdown-format.

    TODO: Prova att gör motsvarande med Riksdagens HTML-version som input.

    Args:
        text (str): Texten som ska formateras
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
            cleaned_line = re.sub(TEMPORAL_MARKER_PATTERN, '', original_line).strip()

            # Kontrollera om nästnästa rad börjar med "1." för att undvika att göra en rad till rubrik
            next_is_list_start = False
            if i + 2 < len(original_result_lines) and original_result_lines[i + 2].strip().startswith("1."):
                next_is_list_start = True

            # Kontrollera om det är en potentiell rubrik (kombinerad logik)
            is_potential_header = (
                cleaned_line.strip() and
                len(cleaned_line) < 300 and
                # Krav på stor bokstav i början av raden
                re.match(CAPITALIZED_PATTERN, cleaned_line.strip()) and
                # Uteslut definitionsfraser
                not re.match(DEFINITION_PATTERN, cleaned_line.strip(), re.IGNORECASE) and
                # Uteslut korta administrativa uttryck
                not re.match(ADMIN_PATTERN, cleaned_line.strip(), re.IGNORECASE) and
                # Uteslut rader som börjar med siffra följt av punkt (listor)
                not re.match(LIST_NUMBERED_PATTERN, cleaned_line.strip()) and
                # Uteslut rader som börjar med bindestreck
                not cleaned_line.strip().startswith(LIST_BULLET_PREFIX) and
                # Uteslut rader som slutar med punkt eller kolon (troligen mening/definition)
                not cleaned_line.strip().endswith(('.', ':')) and
                # Uteslut rader som är för långa för att vara rubriker (över 100 tecken)
                len(cleaned_line.strip()) <= 100 and
                # Uteslut rader som börjar med vanliga juridiska fraser
                not re.match(JURIDIC_PHRASE_PATTERN, cleaned_line.strip(), re.IGNORECASE) and
                # Uteslut specifika juridiska fraser som inte ska bli rubriker
                not re.match(SPECIFIC_JURIDIC_PATTERN, cleaned_line.strip(), re.IGNORECASE)
            )

            # Kontrollera om det är en rubrik (baserat på rensad rad men använd original för output)
            # Specialfall som alltid ska bli rubriker (även utanför standardkriterier)
            if not next_is_list_start:
                # Kontrollera först om det är en avdelningsrubrik (nivå 2 ##)
                if is_chapter_header(cleaned_line.strip()):
                    _add_header_with_blank_line(formatted, '##', original_line)
                # Kontrollera om det är ett kapitel (börjar med "X kap." eller "X Kap" eller "X A Kap")
                elif re.match(CHAPTER_PATTERN, cleaned_line.strip()):
                    _add_header_with_blank_line(formatted, '##', original_line)
                # Kontrollera om det är en bilaga (börjar med "Bilaga ")
                elif cleaned_line.strip().startswith(ATTACHMENT_PREFIX):
                    _add_header_with_blank_line(formatted, '##', original_line)
                # Kontrollera om det är en artikel (börjar med "Artikel X")
                elif re.match(ARTIKEL_PATTERN, cleaned_line.strip()):
                    _add_header_with_blank_line(formatted, '###', original_line)
                # Potentiella rubriker enligt standardkriterier
                elif is_potential_header:
                    # Om raden har max två ord OCH inte innehåller punkt, eller uppfyller de andra kriterierna
                    if (len(cleaned_line.split()) <= 2 and '.' not in cleaned_line) or (len(cleaned_line) < 300 and not cleaned_line.strip().endswith(('.', ':'))):
                        # Använd H3-rubrik för rubriker
                        _add_header_with_blank_line(formatted, '###', original_line)
                    else:
                        # Hantera paragrafnummer som rubriker
                        if previous_line_empty:
                            # Kontrollera om raden börjar med paragrafnummer (använd rensad rad)
                            paragraph_match = re.match(r'^' + PARAGRAPH_PATTERN, cleaned_line)
                            if paragraph_match:
                                paragraph_num = paragraph_match.group(0)
                                
                                # Extrahera markeringar från originalraden
                                markings = re.findall(TEMPORAL_MARKER_PATTERN, original_line)
                                
                                # Skapa rubrik med bara markeringar och paragrafnummer
                                if markings:
                                    markings_str = ' '.join(markings)
                                    formatted.append(f'#### {markings_str} {paragraph_num}')
                                else:
                                    formatted.append(f'#### {paragraph_num}')
                                
                                formatted.append('')  # Tom rad efter rubriken
                                
                                # Hitta resten av texten efter paragrafnumret i rensad rad
                                rest_of_line = cleaned_line[len(paragraph_num):].strip()
                                if rest_of_line:
                                    formatted.append(rest_of_line)
                            else:
                                formatted.append(original_line)
                        else:
                            formatted.append(original_line)
                else:
                    if is_chapter_header(cleaned_line.strip()):
                        # Hantera avdelningsrubriker
                        _add_header_with_blank_line(formatted, '##', original_line)
                    elif previous_line_empty:
                        # Kontrollera om raden börjar med paragrafnummer (använd rensad rad)
                        paragraph_match = re.match(r'^' + PARAGRAPH_PATTERN, cleaned_line)
                        if paragraph_match:
                            paragraph_num = paragraph_match.group(0)
                            
                            # Extrahera markeringar från originalraden
                            markings = re.findall(TEMPORAL_MARKER_PATTERN, original_line)
                            
                            # Skapa rubrik med bara markeringar och paragrafnummer
                            if markings:
                                markings_str = ' '.join(markings)
                                formatted.append(f'#### {markings_str} {paragraph_num}')
                            else:
                                formatted.append(f'#### {paragraph_num}')
                            
                            formatted.append('')  # Tom rad efter rubriken
                            
                            # Hitta resten av texten efter paragrafnumret i rensad rad
                            rest_of_line = cleaned_line[len(paragraph_num):].strip()
                            if rest_of_line:
                                formatted.append(rest_of_line)
                        else:
                            formatted.append(original_line)
                    else:
                        formatted.append(original_line)
            else:
                # Hantera AVDELNING-rubriker och paragrafnummer som rubriker även när övriga kriterier inte uppfylls
                if is_chapter_header(cleaned_line.strip()):
                    _add_header_with_blank_line(formatted, '##', original_line)
                elif previous_line_empty:
                    # Kontrollera om raden börjar med paragrafnummer (använd rensad rad)
                    paragraph_match = re.match(r'^' + PARAGRAPH_PATTERN, cleaned_line)
                    if paragraph_match:
                        paragraph_num = paragraph_match.group(0)
                        
                        # Extrahera markeringar från originalraden
                        markings = re.findall(TEMPORAL_MARKER_PATTERN, original_line)
                        
                        # Skapa rubrik med bara markeringar och paragrafnummer
                        if markings:
                            markings_str = ' '.join(markings)
                            formatted.append(f'#### {markings_str} {paragraph_num}')
                        else:
                            formatted.append(f'#### {paragraph_num}')
                        
                        formatted.append('')  # Tom rad efter rubriken
                        
                        # Hitta resten av texten efter paragrafnumret i rensad rad
                        rest_of_line = cleaned_line[len(paragraph_num):].strip()
                        if rest_of_line:
                            formatted.append(rest_of_line)
                    else:
                        formatted.append(original_line)
                else:
                    formatted.append(original_line)
            previous_line_empty = False

    # Returnera den formaterade texten
    final_text = '\n'.join(formatted)
    
    # Tillämpa externa länkar först (lagnamn, SFS, EU), sedan interna paragraf-länkar
    if apply_links:
        final_text = apply_law_name_links(final_text)
        final_text = apply_sfs_links(final_text)
        final_text = apply_eu_links(final_text)
        final_text = apply_internal_links(final_text)

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
    markings = re.findall(TEMPORAL_MARKER_PATTERN, text)

    if markings:
        # Ta bort alla markeringar från texten
        cleaned_text = re.sub(r'\s*' + TEMPORAL_MARKER_PATTERN + r'\s*', ' ', text)
        cleaned_text = re.sub(WHITESPACE_PATTERN, ' ', cleaned_text).strip()

        # Skapa rubriken med markeringar direkt efter rubrikmarkören
        markings_str = ' '.join(markings)
        return f"{header_level} {markings_str} {cleaned_text}"
    else:
        # Ingen markering hittad, returnera som vanligt
        return f"{header_level} {text}"


# Moved to apply_links.py


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

    # Kontrollera både i rubrik och innehåll efter ikraft-markeringar med giltigt datum eller villkor
    return (re.search(INTOFORCE_ANY_PATTERN, header_lower) is not None or
            re.search(INTOFORCE_ANY_PATTERN, content_lower) is not None)


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
    parent_stack = []  # Stack för att hålla koll på föräldrasektioner: [(level, section_id), ...]

    def close_sections_to_level(target_level):
        """Stäng alla sektioner ner till målnivån"""
        nonlocal section_stack, result, parent_stack
        while section_stack and section_stack[-1] >= target_level:
            # Lägg endast till en tom rad före </section> taggen om den sista raden inte redan är tom
            if result and result[-1].strip() != '':
                result.append('')
            result.append('</section>')
            section_stack.pop()
            # Ta även bort från parent_stack om den finns
            if parent_stack and parent_stack[-1][0] >= target_level:
                parent_stack.pop()

    def process_current_section():
        """Bearbeta och lägg till nuvarande sektion"""
        nonlocal current_section, result
        if current_section:
            # Hitta rubriknivån för huvudrubriken i denna sektion
            main_header_line = current_section[0] if current_section else ""
            main_header_match = re.match(HEADER_LEVEL_PATTERN, main_header_line)
            
            # Om det inte finns en rubrik i sektionen, lägg bara till innehållet utan section-taggar
            if not main_header_match:
                result.extend(current_section)
                current_section = []
                return
                
            main_header_level = len(main_header_match.group(1))

            # Extrahera endast det direkta innehållet under huvudrubriken,
            # exklusive alla underrubriker och deras innehåll
            direct_content = []
            i = 1  # Börja efter huvudrubriken

            while i < len(current_section):
                line = current_section[i]
                subheader_match = re.match(HEADER_LEVEL_PATTERN, line)

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
                            next_header_match = re.match(HEADER_LEVEL_PATTERN, next_line)

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
            upphor_match = re.search(REVOKE_DATE_EXTRACT_PATTERN, all_section_content)
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
            ikraft_match = re.search(INTOFORCE_DATE_EXTRACT_PATTERN, all_section_content)
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
            header_match = re.match(HEADER_LEVEL_PATTERN, header_line)

            if header_match:
                header_level = len(header_match.group(1))
                header_text = header_match.group(2)

                # Lägg till klasser baserat på rubriknivå och innehåll
                if header_level == 1:
                    css_classes.append('forfattning')
                elif header_level == 2:
                    # Kontrollera om det är en avdelningsrubrik
                    if is_chapter_header(header_text):
                        css_classes.append('avdelning')
                    elif '§' in header_text:
                        css_classes.append('paragraf')
                    else:
                        css_classes.append('kapitel')
                elif (header_level == 3 or header_level == 4) and '§' in header_text:
                    css_classes.append('paragraf')

            # Bygg section-tagg med attribut
            attributes = []
            
            # Lägg till id-attribut baserat på rubriken
            if header_match:
                # Hitta lämplig förälder baserat på rubriknivå - endast kapitel kan vara föräldrar
                parent_id = None
                for level, pid in reversed(parent_stack):
                    # För paragrafer, endast kapitel (kap1, kap2, etc.) kan vara föräldrar
                    # Inte underrubriker som kap1.inledande-bestämmelser
                    if level < main_header_level and re.match(r'^kap\d+[a-z]?$', pid):
                        parent_id = pid
                        break
                
                section_id = generate_section_id(header_text, parent_id)
                attributes.append(f'id="{section_id}"')
            
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
            
            if ikraft_datum:
                attributes.append(f'selex:ikraft_datum="{ikraft_datum}"')
            if upphor_datum:
                attributes.append(f'selex:upphor_datum="{upphor_datum}"')
            if ikraft_villkor:
                attributes.append(f'selex:ikraft_villkor="{ikraft_villkor}"')

            if attributes:
                result.append(f'<section {" ".join(attributes)}>')
            else:
                result.append('<section>')
            
            # Lägg alltid till en tom rad efter <section> taggen
            result.append('')

            # Ta bort ikraft- och upphör-markeringar från innehållet innan det läggs till resultatet
            cleaned_section = []
            for line in current_section:
                # Ta bort ikraft-markeringar
                cleaned_line = re.sub(INTOFORCE_FULL_TEMPORAL_TAG_PATTERN, '', line, flags=re.IGNORECASE)
                # Ta bort upphör-markeringar
                cleaned_line = re.sub(REVOKE_FULL_TEMPORAL_TAG_PATTERN, '', cleaned_line, flags=re.IGNORECASE)
                cleaned_section.append(cleaned_line)

            # Lägg till det rensade innehållet
            result.extend(cleaned_section)

            # Lägg till denna sektion i parent_stack för eventuella underliggande sektioner
            if header_match:
                parent_stack.append((main_header_level, section_id))

            # Rensa nuvarande sektion
            current_section = []

    for line in lines:
        # Kontrollera om raden är en markdown-rubrik
        header_match = re.match(HEADER_LEVEL_PATTERN, line)

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




def check_unprocessed_temporal_sections(text: str) -> None:
    """
    Kontrollera att inga sektioner med temporal status-attribut finns kvar.
    
    Denna funktion säkerställer att alla temporala sektioner har behandlats korrekt
    av temporal processing innan selex tags tas bort.
    
    Obs: Eftersom artikel-temporala attribut (selex:ikraft_datum, selex:upphor_datum, etc.)
    läggs till i frontmatter och hanteras inte här, så kontrolleras endast
    <section> och </section> taggar för obehandlade status-attribut.
    
    Args:
        text (str): Text som ska kontrolleras
        
    Raises:
        ValueError: Om sektioner med obehandlade status-attribut hittas
    """
    # Sök efter section- och article-taggar med temporal attribut som indikerar obehandlad status
    temporal_patterns = [
        r'<section[^>]*selex:ikraft_datum=',  # Section ikraftträdandedatum
        r'<section[^>]*selex:upphor_datum=',  # Section upphörandedatum  
        r'<section[^>]*selex:status=',        # Section status attribut
        # Note: Article temporal attributes are handled in frontmatter, not in temporal processing
    ]
    
    found_issues = []
    for pattern in temporal_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            # Extrahera sektionens början för felsökning
            section_start = match.start()
            section_end = text.find('</section>', section_start)
            if section_end == -1:
                section_content = text[section_start:section_start + 200] + "..."
            else:
                section_content = text[section_start:section_end + 10]
            
            found_issues.append(section_content)
    
    if found_issues:
        error_msg = (
            "Fel: Sektioner eller artiklar med obehandlade temporal attribut hittades. "
            "Dessa borde ha behandlats av temporal processing före borttagning av selex tags.\n\n"
            "Hittade element:\n" + 
            "\n".join(f"- {issue}" for issue in found_issues[:5])  # Visa max 5 exempel
        )
        if len(found_issues) > 5:
            error_msg += f"\n... och {len(found_issues) - 5} till"
        
        raise ValueError(error_msg)


def clean_selex_tags(text: str) -> str:
    """
    Rensa bort alla selex-taggar (<section>, </section>, <article>, </article>) och deras associerade tomma rader.
    Normaliserar också rubriknivåer så att de inte hoppar över nivåer.
    
    Funktionen kontrollerar först att inga obehandlade temporal sektioner finns,
    sedan rensar den:
    1. Alla <section> taggar (med eller utan attribut)
    2. Alla </section> taggar
    3. Alla <article> taggar (med eller utan attribut) - artikelattribut hanteras i frontmatter
    4. Alla </article> taggar
    5. Tomma rader som kommer direkt efter <section> eller <article> taggar
    6. Tomma rader som kommer direkt före </section> eller </article> taggar
    7. Eventuella överflödiga dubletter av tomma rader
    8. Normaliserar rubriknivåer så att de följer en logisk hierarki (1, 2, 3, 4...)
    
    Obs: Artikel-temporala attribut (selex:ikraft_datum, selex:upphor_datum, etc.) läggas också
    till i frontmatter och hanteras inte här. Därför tas <article>-taggen bort bort 
    här utan att kontrollera dess attribut.
    
    Args:
        text (str): Text med selex-taggar och tomma rader
        
    Returns:
        str: Rensat text utan selex-taggar och deras associerade tomma rader,
             med normaliserade rubriknivåer
        
    Raises:
        ValueError: Om obehandlade temporal sektioner hittas
    """
    # Kontrollera först att inga obehandlade temporal sektioner finns
    check_unprocessed_temporal_sections(text)
    lines = text.split('\n')
    result = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Kontrollera om raden är en <section> eller <article> tagg
        if re.match(SECTION_TAG_PATTERN, line) or re.match(ARTICLE_TAG_PATTERN, line):
            # Hoppa över taggen
            i += 1
            # Behåll den tomma raden efter taggen för markdown-standard om nästa rad är en rubrik
            if (i < len(lines) and lines[i].strip() == '' and 
                i + 1 < len(lines) and re.match(r'#{1,6}\s', lines[i + 1].strip())):
                # Den tomma raden följs av en rubrik, behåll den
                result.append('')
                i += 1
            elif i < len(lines) and lines[i].strip() == '':
                # Hoppa över tomma rader som inte följs av rubriker
                i += 1
            continue
            
        # Kontrollera om raden är en </section> eller </article> tagg
        elif re.match(SECTION_CLOSE_TAG_PATTERN, line) or re.match(ARTICLE_CLOSE_TAG_PATTERN, line):
            # Ta bort föregående tom rad om den finns (eftersom vi lägger till tom rad före sluttaggen)
            if result and result[-1].strip() == '':
                result.pop()
            # Hoppa över sluttaggen utan att lägga till den
            i += 1
            continue
            
        else:
            # Vanlig rad - lägg till den
            result.append(line)
            i += 1
    
    # Ta bort eventuella dubletter av tomma rader och rensa slutresultatet
    cleaned_result = []
    prev_empty = False
    
    for line in result:
        is_empty = line.strip() == ''
        
        # Lägg endast till tomma rader om föregående rad inte var tom
        if is_empty and prev_empty:
            continue  # Hoppa över dublett av tom rad
        else:
            cleaned_result.append(line)
            prev_empty = is_empty
    
    # Ta bort inledande och avslutande tomma rader
    while cleaned_result and cleaned_result[0].strip() == '':
        cleaned_result.pop(0)
    while cleaned_result and cleaned_result[-1].strip() == '':
        cleaned_result.pop()
    
    # Normalisera rubriknivåer så att de inte hoppar över nivåer
    final_text = '\n'.join(cleaned_result)
    final_text = normalize_heading_levels(final_text)
    
    return final_text


def generate_section_id(header_text: str, parent_id: str = None) -> str:
    """
    Genererar ett id-attribut för section-taggar baserat på rubrik eller paragrafnummer.
    
    Regler:
    - Om rubriken innehåller paragrafnummer (t.ex. "5 §", "13 a §"), använd bara paragrafnumret
    - Om rubriken är ett kapitel (t.ex. "1 kap.", "2 a kap."), använd formatet "kap1", "kap2a"
    - Om parent_id finns och rubriken är en paragraf, lägg till parent som prefix: "kap1.1"
    - Annars skapa en slug från rubriken (max 30 tecken)
    - Ta bort markeringar (text inom //) innan slug-generering
    
    Args:
        header_text (str): Rubriktext (utan # tecken)
        parent_id (str, optional): ID för överordnad sektion
        
    Returns:
        str: ID som kan användas som HTML id-attribut
    """
    # Ta bort markeringar (text inom //) från rubriken
    cleaned_header = re.sub(TEMPORAL_MARKER_PATTERN, '', header_text).strip()
    
    # Kontrollera om det finns paragrafnummer i rubriken
    paragraph_match = re.search(PARAGRAPH_PATTERN, cleaned_header)
    if paragraph_match:
        # Extrahera paragrafnumret utan mellanslag
        paragraph_num = paragraph_match.group(1).replace(' ', '')
        if parent_id:
            return f"{parent_id}.{paragraph_num}"
        return f"{paragraph_num}"
    
    # Kontrollera om det är ett kapitel (använd samma mönster som i format_sfs_text_as_markdown)
    kapitel_match = re.match(CHAPTER_PATTERN, cleaned_header)
    if kapitel_match:
        # Extrahera kapitelnummer och eventuell bokstav
        kapitel_num = kapitel_match.group(1)
        kapitel_letter = kapitel_match.group(2) if kapitel_match.group(2) else ''
        return f"kap{kapitel_num}{kapitel_letter.lower()}"
    
    # Om inget paragrafnummer eller kapitel, skapa slug från rubriken
    # Ta bort alla icke-alfanumeriska tecken och ersätt med bindestreck
    slug = re.sub(r'[^\w\s-]', '', cleaned_header)
    slug = re.sub(r'\s+', '-', slug)
    slug = slug.lower().strip('-')
    
    # Begränsa till max 30 tecken
    if len(slug) > 30:
        slug = slug[:30].rstrip('-')
    
    if not slug:
        raise ValueError(f"Kan inte generera giltigt ID från rubriktext: '{header_text}'")
    
    if parent_id:
        return f"{parent_id}.{slug}"
    else:
        return slug


def normalize_heading_levels(text: str) -> str:
    """
    Normalisera rubriknivåer så att de inte hoppar över nivåer.
    
    Om det finns rubriker på nivå 1 och 3 men inte nivå 2, kommer nivå 3 att 
    justeras till nivå 2. Detta säkerställer valid Markdown där rubriknivåer 
    följer en logisk hierarki utan hopp.
    
    Args:
        text (str): Markdown-text med rubriker
        
    Returns:
        str: Text med normaliserade rubriknivåer
    """
    lines = text.split('\n')
    
    # Först, hitta alla rubriknivåer som används i dokumentet
    used_levels = set()
    for line in lines:
        match = re.match(r'^(#{1,6})\s+', line)
        if match:
            level = len(match.group(1))
            used_levels.add(level)
    
    if not used_levels:
        return text  # Inga rubriker att normalisera
    
    # Skapa mappning från gamla nivåer till nya nivåer
    sorted_levels = sorted(used_levels)
    level_mapping = {}
    
    # Börja från nivå 1 och tilldela nya nivåer sekventiellt
    new_level = 1
    for old_level in sorted_levels:
        level_mapping[old_level] = new_level
        new_level += 1
    
    # Tillämpa den nya nivåmappningen
    result_lines = []
    for line in lines:
        match = re.match(r'^(#{1,6})(\s+.*)$', line)
        if match:
            old_level = len(match.group(1))
            new_level = level_mapping.get(old_level, old_level)
            new_hashes = '#' * new_level
            result_lines.append(new_hashes + match.group(2))
        else:
            result_lines.append(line)
    
    return '\n'.join(result_lines)



def is_chapter_header(line: str) -> bool:
    """
    Kontrollera om en rad är en AVDELNING-rubrik som ska få nivå 2 (##).
    
    AVDELNING-rubriker identifieras med två mönster:
    1. AVDELNING eller AVD. följt av romerska siffror (I, II, III, IV, V, X, etc.)
    2. Svenska ordningstal (FÖRSTA, ANDRA, etc.) följt av AVDELNING eller AVD.
    
    Exempel:
    - "AVDELNING I. INLEDANDE BESTÄMMELSER"
    - "AVD. I SKATTEFRIA INKOMSTER OCH INTE AVDRAGSGILLA UTGIFTER"  
    - "AVDELNING I"
    - "FÖRSTA AVDELNINGEN"
    - "ANDRA AVDELNINGEN"
    - "AVD. II KAPITALVINSTER OCH KAPITALFÖRLUSTER"
    
    Args:
        line (str): Raden som ska kontrolleras
        
    Returns:
        bool: True om raden är en AVDELNING-rubrik, False annars
    """
    line = line.strip()
    if not line:
        return False
    
    # Mönster 1: AVDELNING/AVD. följt av romerska siffror
    # Mönster 2: Svenska ordningstal följt av AVDELNING/AVD.
    return (re.match(DIVISION_PATTERN_1, line, re.IGNORECASE) is not None or 
            re.match(DIVISION_PATTERN_2, line, re.IGNORECASE) is not None)
