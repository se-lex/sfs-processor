#!/usr/bin/env python3
"""
Script för att konvertera HTML-filer till Markdown med hjälp av OpenAI API.
Läser HTML-filer från en mapp och konverterar dem till Markdown-format.
"""

import os
import argparse
import glob
from pathlib import Path
from openai import OpenAI
import time
from typing import Optional


def read_html_file(file_path: str) -> Optional[str]:
    """
    Läser innehållet från en HTML-fil.
    
    Args:
        file_path (str): Sökväg till HTML-filen
        
    Returns:
        Optional[str]: Filens innehåll eller None om fel uppstod
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except IOError as e:
        print(f"✗ Fel vid läsning av {file_path}: {e}")
        return None


def create_prompt(html_content: str) -> str:
    """
    Skapar prompt för OpenAI API-anropet.
    
    Args:
        html_content (str): HTML-innehållet som ska konverteras
        
    Returns:
        str: Färdig prompt för API-anropet
    """
    prompt = """Strukturera texten utifrån dessa regler:

- Använd "front matter" längst upp för metadata som finns inom b-taggar i HTML-dokumentet.
   "ID" (står som "SFS nr" i dokumentet),
   "Departement/myndighet" (är ett datum),
   "Utfärdad" (är ett datum),
   "Upphävd" (är ett datum),
   "Författningen har upphävts genom" (är en annan författning),
   "Källa"
- Front matter ska vara i YAML-format och inledas med "---" på en egen rad före och efter.
- Alla rader i front matter som är tomma efter kolon ska tas bort
- Om "Upphävd" är tom, ta bort raden
- Om "Författningen har upphävts genom" är tom, ta bort raden
- Om "Källa" är tom, ta bort raden
- Alla rader i front matter ska ha formatet "nyckel: värde" och nyckeln ska vara i gemener
- Bortse ifrån "Ändringsregister" och dess URL
- Information som läggs till i "front matter" ska tas bort från texten
- Ta bort alla sidnummer
- Om SFS numret förekommer på egen rad i texten, ta bort det
- Formattera texten så att den INTE har flera mellanslag mellan ord
- Formattera texten så att den INTE radbryter manuellt i stycken
- Behåll paragraf och styckesindelningen
- Använd "#" för huvudrubrik, som finns längst upp inom H2-tagg
- Använd "##" för att påvisa underrubriker
- Vid paragrafnummer med "§" ska dessa INTE inledas med bindestreck utan inleda ett nytt stycke.
- Fetmarkera alla benämningar av paragrafer, alltså nummer följt av tecknet §
- Länkar till andra dokument ska vara i formatet [text](URL)
- Länkar till andra paragrafer ska vara i formatet [text](#paragrafnummer)
- Onumrerade och numrerade listor ska alltid föregås av en blankrad

----
""" + html_content
    
    return prompt


def convert_with_openai(client: OpenAI, html_content: str, model: str = "gpt-4.1") -> Optional[str]:
    """
    Konverterar HTML till Markdown med hjälp av OpenAI API.
    
    Args:
        client (OpenAI): OpenAI klient
        html_content (str): HTML-innehållet som ska konverteras
        model (str): OpenAI-modell att använda
        
    Returns:
        Optional[str]: Konverterat Markdown-innehåll eller None om fel uppstod
    """
    try:
        prompt = create_prompt(html_content)
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1  # Låg temperatur för konsistenta resultat
        )
        
        return response.choices[0].message.content
        
    except (AttributeError, KeyError, ValueError) as e:
        print(f"✗ Fel vid tolkning av OpenAI-svar: {e}")
        return None
    except Exception as e:
        print(f"✗ Oväntat fel vid OpenAI API-anrop: {e}")
        return None


def save_markdown_file(content: str, output_path: str) -> bool:
    """
    Sparar Markdown-innehåll till fil.
    
    Args:
        content (str): Markdown-innehållet som ska sparas
        output_path (str): Sökväg där filen ska sparas
        
    Returns:
        bool: True om sparningen lyckades, False annars
    """
    try:
        # Skapa katalog om den inte finns
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
        
    except IOError as e:
        print(f"✗ Fel vid sparning av {output_path}: {e}")
        return False


def process_html_files(input_dir: str, output_dir: str, api_key: str, model: str = "o3") -> None:
    """
    Bearbetar alla HTML-filer i en katalog och konverterar dem till Markdown.
    
    Args:
        input_dir (str): Katalog med HTML-filer
        output_dir (str): Katalog för utdata-filer
        api_key (str): OpenAI API-nyckel
        model (str): OpenAI-modell att använda
    """
    # Initialisera OpenAI klient
    client = OpenAI(api_key=api_key)
    
    # Hitta alla HTML-filer i input-katalogen
    html_pattern = os.path.join(input_dir, "*.html")
    html_files = glob.glob(html_pattern)
    
    if not html_files:
        print(f"Inga HTML-filer hittades i katalogen: {input_dir}")
        return
    
    print(f"Hittade {len(html_files)} HTML-filer att bearbeta")
    
    successful_conversions = 0
    failed_conversions = 0
    skipped_conversions = 0
    
    for i, html_file in enumerate(html_files, 1):
        filename = os.path.basename(html_file)
        
        # Skapa output-filnamn (byt ut .html med .md)
        markdown_filename = Path(filename).stem + ".md"
        output_path = os.path.join(output_dir, markdown_filename)

        # Kontrollera om Markdown-filen redan finns
        if os.path.exists(output_path):
            print(f"↷ Skippar {markdown_filename} (finns redan)")
            skipped_conversions += 1
            continue

        print(f"[{i}/{len(html_files)}] Bearbetar {filename}...")

        # Läs HTML-fil
        html_content = read_html_file(html_file)
        if html_content is None:
            failed_conversions += 1
            continue
        
        # Konvertera med OpenAI
        markdown_content = convert_with_openai(client, html_content, model)
        if markdown_content is None:
            failed_conversions += 1
            continue
        
        # Spara Markdown-fil
        if save_markdown_file(markdown_content, output_path):
            print(f"✓ Sparade {markdown_filename}")
            successful_conversions += 1
        else:
            failed_conversions += 1
        
        # Kort paus mellan API-anrop för att undvika rate limiting
        time.sleep(5)
    
    # Sammanfattning
    print("\n=== Sammanfattning ===")
    print(f"Totalt HTML-filer: {len(html_files)}")
    print(f"Lyckade konverteringar: {successful_conversions}")
    print(f"Misslyckade konverteringar: {failed_conversions}")
    print(f"Skippade filer (finns redan): {skipped_conversions}")
    
    if successful_conversions > 0:
        print(f"Markdown-filer sparade i katalogen: {os.path.abspath(output_dir)}")


def main():
    """
    Huvudfunktion som hanterar kommandoradsargument och koordinerar konverteringsprocessen.
    """
    parser = argparse.ArgumentParser(description='Konvertera HTML-filer till Markdown med OpenAI API')
    parser.add_argument('--in', dest='input_dir', required=True,
                        help='Katalog med HTML-filer att konvertera')
    parser.add_argument('--out', dest='output_dir', default='md_output',
                        help='Katalog för utdata-filer (default: md_output)')
    parser.add_argument('--apikey', required=True,
                        help='OpenAI API-nyckel')
    parser.add_argument('--model', default='o3',
                        help='OpenAI-modell att använda (default: o3)')

    args = parser.parse_args()

    print("=== HTML till Markdown Konverterare ===")
    print(f"Input-katalog: {args.input_dir}")
    print(f"Output-katalog: {args.output_dir}")
    print(f"OpenAI-modell: {args.model}")
    
    # Kontrollera att input-katalogen finns
    if not os.path.isdir(args.input_dir):
        print(f"Fel: Input-katalogen '{args.input_dir}' finns inte")
        return
    
    # Starta konverteringsprocessen
    process_html_files(args.input_dir, args.output_dir, args.apikey, args.model)


if __name__ == "__main__":
    main()
