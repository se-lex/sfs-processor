"""
EUR-Lex API för att hämta europeiska lagar och förordningar.

Detta modul innehåller funktioner för att:
1. Konvertera EU-förordningsreferenser till CELEX-nummer
2. Hämta dokumentinformation från EUR-Lex
3. Generera URL:er till EUR-Lex-dokument

CELEX-nummerformat:
- Sektor (1 siffra): 3 = lagstiftning, 2 = rättspraxis, osv.
- År (4 siffror): t.ex. 2014
- Typ (1 bokstav): R = regulation/förordning, L = directive/direktiv, D = decision/beslut
- Löpnummer (4 siffror med fyllnad): t.ex. 0651

Exempel: "(EU) nr 651/2014" -> CELEX: 32014R0651
URL: https://eur-lex.europa.eu/legal-content/SV/ALL/?uri=celex%3A32014R0651
"""

import re
from typing import Optional, Dict, Any
import requests
from urllib.parse import quote


def parse_eu_regulation_to_celex(regulation_text: str) -> Optional[str]:
    """
    Konverterar EU-förordningstext till CELEX-nummer.
    
    Stöder format som:
    - "(EU) nr 651/2014"
    - "(EU) Nr 651/2014"
    - "(EU) 651/2014"
    - "651/2014"
    - "Förordning (EU) nr 651/2014"
    - "Rådets förordning (EU) nr 651/2014"
    
    Returnerar CELEX-nummer med sektor 3 (lagstiftning) som standard.
    fetch_eur_lex_document_info() kommer att försöka med sektor 2 (rättspraxis) om det inte hittas.
    
    Args:
        regulation_text (str): Text som innehåller EU-förordningsreferens
        
    Returns:
        Optional[str]: CELEX-nummer (t.ex. "32014R0651") eller None om inget hittas
    """
    # Normalisera texten
    text = regulation_text.strip()
    
    # Mönster för att hitta EU-förordningar
    # Matchar olika format av EU-förordningar
    patterns = [
        # "(EU) nr 651/2014" eller "(EU) Nr 651/2014"
        r'\(EU\)\s*[Nn]r\s*(\d+)/(\d{4})',
        # "(EU) 651/2014" (utan "nr")
        r'\(EU\)\s*(\d+)/(\d{4})',
        # "651/2014" (bara numret)
        r'^(\d+)/(\d{4})$',
        # "Förordning (EU) nr 651/2014" etc.
        r'[Ff]örordning\s*\(EU\)\s*[Nn]r\s*(\d+)/(\d{4})',
        # "Rådets förordning (EU) nr 651/2014" etc.
        r'[Rr]ådets\s*förordning\s*\(EU\)\s*[Nn]r\s*(\d+)/(\d{4})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            number = match.group(1)
            year = match.group(2)
            
            # Konvertera till CELEX-format (börjar alltid med sektor 3)
            return eu_regulation_to_celex(number, year)
    
    return None


def eu_regulation_to_celex(number: str, year: str, regulation_type: str = "R") -> str:
    """
    Konverterar EU-förordningsnummer och år till CELEX-format.
    
    Args:
        number (str): Förordningsnummer (t.ex. "651")
        year (str): År (t.ex. "2014")
        regulation_type (str): Typ av förordning ("R" för regulation, "L" för directive, "D" för decision)
        
    Returns:
        str: CELEX-nummer (t.ex. "32014R0651")
    """
    # Sektor 3 för lagstiftning
    sector = "3"
    
    # Formatera löpnummer med fyllnad till 4 siffror
    formatted_number = number.zfill(4)
    
    # Bygga CELEX-nummer: sektor + år + typ + löpnummer
    celex = f"{sector}{year}{regulation_type}{formatted_number}"
    
    return celex


def generate_eur_lex_url(celex_number: str, language: str = "SV") -> str:
    """
    Genererar URL till EUR-Lex-dokument baserat på CELEX-nummer.
    
    Args:
        celex_number (str): CELEX-nummer (t.ex. "32014R0651")
        language (str): Språkkod (t.ex. "SV" för svenska, "EN" för engelska)
        
    Returns:
        str: URL till EUR-Lex-dokument
    """
    # URL-koda CELEX-numret
    encoded_celex = quote(celex_number)
    
    # Bygga URL
    url = f"https://eur-lex.europa.eu/legal-content/{language}/ALL/?uri=celex%3A{encoded_celex}"
    
    return url


def fetch_eur_lex_document_info(celex_number: str, language: str = "SV") -> Optional[Dict[str, Any]]:
    """
    Hämtar grundläggande information om ett EUR-Lex-dokument.
    
    Om det ursprungliga CELEX-numret (med sektor 3 för lagstiftning) inte hittas,
    försöker funktionen med sektor 2 (rättspraxis).
    
    Args:
        celex_number (str): CELEX-nummer (t.ex. "32014R0651")
        language (str): Språkkod (t.ex. "SV" för svenska, "EN" för engelska)
        
    Returns:
        Optional[Dict[str, Any]]: Grundläggande dokumentinformation eller None om misslyckad
    """
    # Försök först med det ursprungliga CELEX-numret
    url = generate_eur_lex_url(celex_number, language)
    
    try:
        response = requests.get(url, timeout=30)
        
        # Om det fungerar, använd det ursprungliga numret
        if response.status_code == 200:
            return _create_document_info(celex_number, url, language, response.status_code)
        
        # Om vi får 404 eller 400 och det är sektor 3 (lagstiftning), försök med sektor 2 (rättspraxis)
        elif response.status_code in [400, 404] and celex_number.startswith('3'):
            print(f"CELEX {celex_number} (lagstiftning) hittades inte, försöker med rättspraxis...")
            
            # Skapa nytt CELEX-nummer med sektor 2 istället för 3
            alternative_celex = '2' + celex_number[1:]
            alternative_url = generate_eur_lex_url(alternative_celex, language)
            
            # Försök med det alternativa numret
            alt_response = requests.get(alternative_url, timeout=30)
            alt_response.raise_for_status()
            
            print(f"Hittade dokument med CELEX {alternative_celex} (rättspraxis)")
            return _create_document_info(alternative_celex, alternative_url, language, alt_response.status_code)
        
        else:
            # Försök att göra normal error handling
            response.raise_for_status()
            
    except requests.exceptions.RequestException as e:
        print(f"Fel vid hämtning av EUR-Lex-dokument {celex_number}: {e}")
        return None


def _create_document_info(celex_number: str, url: str, language: str, status_code: int) -> Dict[str, Any]:
    """
    Hjälpfunktion för att skapa dokumentinformation baserat på CELEX-nummer.
    
    Args:
        celex_number (str): CELEX-nummer
        url (str): URL till dokumentet
        language (str): Språkkod
        status_code (int): HTTP-statuskod
        
    Returns:
        Dict[str, Any]: Dokumentinformation
    """
    # Grundläggande information
    info = {
        "celex_number": celex_number,
        "url": url,
        "language": language,
        "status": "found" if status_code == 200 else "not_found"
    }
    
    # Extrahera år och typ från CELEX-numret
    if len(celex_number) >= 8:
        sector = celex_number[0]
        year = celex_number[1:5]
        regulation_type = celex_number[5]
        number = celex_number[6:].lstrip('0')
        
        info.update({
            "sector": sector,
            "year": year,
            "type": regulation_type,
            "number": number,
            "formatted_reference": f"(EU) nr {number}/{year}" if regulation_type == "R" else f"(EU) {number}/{year}",
            "sector_description": "lagstiftning" if sector == "3" else "rättspraxis" if sector == "2" else "okänd"
        })
    
    return info


def validate_celex_number(celex_number: str) -> bool:
    """
    Validerar att ett CELEX-nummer har korrekt format.
    
    Args:
        celex_number (str): CELEX-nummer att validera
        
    Returns:
        bool: True om giltigt format, False annars
    """
    # CELEX-nummer ska ha format: sektor (1) + år (4) + typ (1) + löpnummer (4)
    pattern = r'^[1-9]\d{4}[A-Z]\d{4}$'
    
    return bool(re.match(pattern, celex_number))


# Exempel på användning
if __name__ == "__main__":
    # Test med exempel från beskrivningen
    test_regulation = "(EU) nr 651/2014"
    
    print(f"Input: {test_regulation}")
    
    # Konvertera till CELEX
    celex = parse_eu_regulation_to_celex(test_regulation)
    print(f"CELEX: {celex}")
    
    if celex:
        # Generera URL
        url = generate_eur_lex_url(celex)
        print(f"URL: {url}")
        
        # Validera CELEX-numret
        is_valid = validate_celex_number(celex)
        print(f"Giltigt CELEX: {is_valid}")
        
        # Hämta dokumentinformation (med automatisk fallback till sektor 2 om sektor 3 inte hittas)
        print("Hämtar dokumentinformation...")
        info = fetch_eur_lex_document_info(celex)
        if info:
            print("Dokumentinfo:")
            for key, value in info.items():
                print(f"  {key}: {value}")
        else:
            print("Kunde inte hämta dokumentinformation")
    
    # Test med flera format
    print("\n" + "="*50)
    print("Test med olika format:")
    
    test_cases = [
        "(EU) nr 651/2014",
        "(EU) Nr 1234/2020", 
        "Rådets förordning (EU) nr 999/2023"
    ]
    
    for test in test_cases:
        celex = parse_eu_regulation_to_celex(test)
        print(f"{test:<35} -> {celex}")