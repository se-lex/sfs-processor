#!/usr/bin/env python3
"""
Funktion för att markera SFS-dokument som utgångna.

Funktionen tar bort allt innehåll i markdown-filen förutom huvudrubriken 
och ersätter med texten "Har utgått.".
"""

import re
from pathlib import Path
from typing import Union


def apply_expiration(content: str) -> str:
    """
    Tar bort innehållet i markdown förutom huvudrubriken och ersätter med "Har utgått.".
    
    Args:
        content (str): Markdown-innehållet som ska bearbetas
        
    Returns:
        str: Bearbetat markdown-innehåll med endast huvudrubrik och "Har utgått."
    """
    
    # Hitta slutet på YAML front matter
    front_matter_match = re.match(r'^---\n.*?\n---\n\n', content, re.DOTALL)
    
    if not front_matter_match:
        # Om inget front matter hittas, försök hitta huvudrubriken direkt
        main_heading_match = re.match(r'^(# .+)\n', content, re.MULTILINE)
        if main_heading_match:
            main_heading = main_heading_match.group(1)
            return f"{main_heading}\n\nHar utgått.\n"
        else:
            # Om ingen huvudrubrik hittas, returnera bara meddelandet
            return "Har utgått.\n"
    
    front_matter = front_matter_match.group(0)
    remaining_content = content[front_matter_match.end():]
    
    # Hitta huvudrubriken (första raden som börjar med #)
    main_heading_match = re.match(r'^(# .+)\n', remaining_content, re.MULTILINE)
    
    if main_heading_match:
        main_heading = main_heading_match.group(1)
        # Returnera front matter + huvudrubrik + utgångsmeddelande
        return f"{front_matter}{main_heading}\n\nHar utgått.\n"
    else:
        # Om ingen huvudrubrik hittas efter front matter, lägg till bara meddelandet
        return f"{front_matter}Har utgått.\n"


def apply_expiration_to_file(file_path: Union[str, Path]) -> None:
    """
    Tillämpar expiration på en markdown-fil och skriver resultatet tillbaka till filen.
    
    Args:
        file_path (Union[str, Path]): Sökväg till markdown-filen som ska bearbetas
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Filen {file_path} finns inte")
    
    if not file_path.suffix.lower() == '.md':
        raise ValueError(f"Filen {file_path} är inte en markdown-fil (.md)")
    
    # Läs innehållet
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Tillämpa expiration
    expired_content = apply_expiration(content)
    
    # Skriv tillbaka till filen
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(expired_content)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Användning: python apply_expiration.py <markdown_fil>")
        sys.exit(1)
    
    try:
        apply_expiration_to_file(sys.argv[1])
        print(f"Tidsbestämd utgått tillämpad på {sys.argv[1]}")
    except (FileNotFoundError, ValueError, IOError) as e:
        print(f"Fel: {e}", file=sys.stderr)
        sys.exit(1)
