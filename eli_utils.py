"""
Utility-funktioner för ELI (European Legislation Identifier) URLs.

ELI är en standardiserad identifierare för juridiska dokument i Europa som definierar
en strukturerad URL-format för att referera till lagstiftning.

För svensk lagstiftning (SFS) är formatet:
http://selex.se/eli/sfs/{YEAR}/{NUMMER}[/{FORMAT:html|md}]

Läs mer: https://eur-lex.europa.eu/eli-register/about.html
"""

from typing import Optional
import re
import os


def get_eli_host() -> str:
    """
    Returnerar ELI host från environment variabel eller default.
    
    Returns:
        str: ELI host (default: selex.se)
    """
    return os.getenv('ELI_HOST', 'selex.se')


def get_eli_base_url() -> str:
    """
    Returnerar bas-URL:en för ELI-systemet.
    
    Returns:
        str: ELI bas-URL
    """
    return f"http://{get_eli_host()}/eli"


def get_sfs_eli_namespace() -> str:
    """
    Returnerar namespace för SFS-dokument i ELI-systemet.
    
    Returns:
        str: SFS namespace inom ELI
    """
    return f"{get_eli_base_url()}/sfs"


def generate_eli_canonical_url(beteckning: str, output_format: str = 'html') -> Optional[str]:
    """
    Genererar en ELI canonical URL för ett SFS-dokument.
    
    Args:
        beteckning (str): Dokument beteckning i format "YYYY:NNN" (t.ex. "2024:1000")
        output_format (str): Format för URL:en ('html', 'pdf', etc). 'html' ger bas-URL utan suffix.
        
    Returns:
        Optional[str]: ELI URL eller None om beteckningen är ogiltig
        
    Example:
        >>> generate_eli_canonical_url("2024:1000")
        'http://selex.se/eli/sfs/2024/1000/'

        >>> generate_eli_canonical_url("2024:1000", output_format='pdf')
        'http://selex.se/eli/sfs/2024/1000/pdf'
    """
    if not beteckning or not isinstance(beteckning, str):
        return None
        
    # Validera format med regex
    pattern = r'^(\d{4}):(\d+)$'
    match = re.match(pattern, beteckning.strip())
    
    if not match:
        return None
        
    year, nummer = match.groups()
    
    # Bygg bas-URL med konfigurerad host
    base_url = f"{get_sfs_eli_namespace()}/{year}/{nummer}"
    
    # För 'html' format, lägg bara till avslutande slash
    if output_format == 'html':
        base_url += "/"
    elif output_format:
        # För andra format, lägg till format-suffix
        base_url += f"/{output_format}"
        
    return base_url


def generate_eli_canonical_url_from_data(data: dict, output_format: str = 'html') -> Optional[str]:
    """
    Genererar en ELI canonical URL från SFS-dokumentdata.
    
    Args:
        data (dict): SFS-dokumentdata med 'beteckning' fält
        output_format (str): Format för URL:en ('html', 'pdf', 'oj/swe')
        
    Returns:
        Optional[str]: ELI URL eller None om beteckningen saknas eller är ogiltig

    Example:
        >>> data = {"beteckning": "2024:1000", "rubrik": "Förordning..."}
        >>> generate_eli_canonical_url_from_data(data)
        'http://selex.se/eli/sfs/2024/1000/'
    """
    if not isinstance(data, dict):
        return None
        
    beteckning = data.get('beteckning')
    if not beteckning:
        return None

    return generate_eli_canonical_url(beteckning, output_format)


def validate_eli_url(url: str) -> bool:
    """
    Validerar om en URL följer ELI-standarden för SFS-dokument.
    
    Args:
        url (str): URL att validera
        
    Returns:
        bool: True om URL:en är en giltig ELI URL för SFS
        
    Example:
        >>> validate_eli_url("http://selex.se/eli/sfs/2024/1000/")
        True
        
        >>> validate_eli_url("https://example.com/doc")
        False
    """
    if not url or not isinstance(url, str):
        return False
        
    # Få aktuell host från konfiguration
    current_host = get_eli_host().replace('.', r'\.')
    
    # Regex för att matcha ELI SFS URL-format med konfigurerad host och tillåtna format (html, pdf, md)
    pattern = f'^https?://{current_host}/eli/sfs/\\d{{4}}/\\d+(?:/(html|pdf|md))?/?$'
    return bool(re.match(pattern, url.strip()))


def extract_beteckning_from_eli_url(url: str) -> Optional[str]:
    """
    Extraherar beteckning (YYYY:NNN) från en ELI URL.
    
    Args:
        url (str): ELI URL att parsa
        
    Returns:
        Optional[str]: Beteckning i format "YYYY:NNN" eller None om URL:en är ogiltig
    """
    if not validate_eli_url(url):
        return None
        
    # Få aktuell host från konfiguration
    current_host = get_eli_host().replace('.', r'\.')
    
    # Regex för att extrahera år och nummer med konfigurerad host
    pattern = f'https?://{current_host}/eli/sfs/(\\d{{4}})/(\\d+)'
    match = re.search(pattern, url.strip())
    
    if match:
        year, nummer = match.groups()
        return f"{year}:{nummer}"
        
    return None


def generate_eli_metadata_html(beteckning: str, output_format: str = 'html') -> Optional[str]:
    """
    Genererar HTML meta-taggar för ELI canonical URL.
    
    Args:
        beteckning (str): Dokument beteckning i format "YYYY:NNN"
        output_format (str): Format för URL:en ('html', 'pdf', etc). 'html' ger bas-URL utan suffix.
        
    Returns:
        Optional[str]: HTML meta-taggar eller None om beteckningen är ogiltig

    Example:
        >>> generate_eli_metadata_html("2024:1000")
        '<link rel="canonical" href="http://selex.se/eli/sfs/2024/1000/" />\\n<meta property="eli:id_local" content="2024:1000" />'
    """
    eli_url = generate_eli_canonical_url(beteckning, output_format)
    if not eli_url:
        return None
        
    html_parts = [
        f'<link rel="canonical" href="{eli_url}" />',
        f'<meta property="eli:id_local" content="{beteckning}" />'
    ]
    
    return '\n'.join(html_parts)