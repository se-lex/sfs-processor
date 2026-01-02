# Bidra till SFS-Processor

Tack för ditt intresse att bidra till SFS-Processor! Det här dokumentet beskriver hur du kan hjälpa till med utvecklingen.

## Kom igång

### Förutsättningar

- Python 3.11 eller senare
- Git
- Grundläggande kunskaper om Python och Markdown

### Installera utvecklingsmiljö

1. Forka repositoryt på GitHub
2. Klona din fork lokalt:
   ```bash
   git clone https://github.com/se-lex/sfs-processor.git
   cd sfs-processor
   ```

3. Skapa en virtuell miljö (rekommenderat):
   ```bash
   python -m venv venv
   source venv/bin/activate  # På Windows: venv\Scripts\activate
   ```

4. Installera dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Utvecklingsmiljö

### Installation av dependencies

Projektet har minimala beroenden som specificeras i `requirements.txt`:
```bash
pip install -r requirements.txt
```

### Köra tester

Kör alla tester med:
```bash
python -m pytest test/ -v
```

Enskilda testfiler kan köras direkt:
```bash
python test/test_title_temporal.py
```

### Kodstil

Projektet följer PEP 8-standarden för Python-kod. Några specifika riktlinjer:

- Använd 4 mellanslag för indentering (inga tabs)
- Maximal radlängd: 100 tecken (flexibelt för långa strängar)
- Använd beskrivande variabelnamn
- Svenska termer är OK för domänspecifika begrepp (t.ex. "beteckning", "författning")
- Kommentera komplex logik
- Docstrings för alla publika funktioner

## Bidra med kod

### Arbetsflöde

1. Skapa en feature branch från `main`:
   ```bash
   git checkout -b feature/min-funktion
   ```

   Använd beskrivande branch-namn:
   - `feature/` för nya funktioner
   - `fix/` för buggfixar

2. Gör dina ändringar och commit:
   ```bash
   git add .
   git commit -m "Beskrivande commit-meddelande"
   ```

   Skriv tydliga commit-meddelanden som förklarar *vad* och *varför*.

3. Pusha till din fork:
   ```bash
   git push origin feature/min-funktion
   ```

4. Öppna en Pull Request på GitHub

### Pull Request-process

När du öppnar en Pull Request:

- **Beskriv dina ändringar**: Förklara vad din PR gör och varför ändringen behövs
- **Referera till issues**: Om din PR löser ett issue, länka till det (t.ex. "Fixes #123")
- **Inkludera tester**: Lägg till tester för nya funktioner eller buggfixar
- **Se till att tester passerar**: Alla befintliga tester måste fortfarande fungera
- **Uppdatera dokumentation**: Om du ändrar funktionalitet, uppdatera README eller andra relevanta dokument

Vi kommer att granska din PR och ge feedback. Var beredd på att göra ändringar baserat på code review.

## Rapportera buggar

Hittat en bugg? Hjälp oss att fixa den!

1. **Kontrollera befintliga issues**: Kolla om någon redan rapporterat samma problem
2. **Öppna ett nytt issue** med följande information:
   - **Tydlig titel**: Sammanfatta problemet kortfattat
   - **Beskrivning**: Beskriv vad som händer och vad du förväntade dig
   - **Reproducerbarhet**: Steg för att återskapa problemet
   - **Miljö**: Python-version, operativsystem
   - **Exempel**: Minimal kod eller kommando som visar problemet
   - **Felmeddelanden**: Inkludera fullständiga stack traces om tillämpligt

### Exempel på buggrapport

```markdown
## Titel: Fel vid parsing av dokument med tomma kapitel

**Beskrivning:**
När sfs_processor.py försöker processa ett SFS-dokument som innehåller tomma kapitel
kraschar programmet med ValueError.

**Steg för att reproducera:**
1. Ladda ner SFS 2023:123
2. Kör: `python sfs_processor.py sfs_json/2023/sfs-2023-123.json --output md`

**Förväntat resultat:**
Dokumentet processas korrekt och tomma kapitel ignoreras.

**Faktiskt resultat:**
```
ValueError: Cannot process empty chapter
```

**Miljö:**
- Python 3.11.4
- macOS Sonoma 14.2
- sfs-processor version 1.0.0
```

## Kodstandard

### Allmänna riktlinjer

- **PEP 8**: Följ Python Enhancement Proposal 8 för kodstil
- **Variabelnamn**: Använd beskrivande namn (`document_data` istället för `dd`)
- **Svenska termer**: OK att använda för juridiska/domänspecifika termer (t.ex. `beteckning`, `författning`, `paragraf`)
- **Kommentarer**: Kommentera komplex logik, inte uppenbar kod
- **Docstrings**: Alla publika funktioner ska ha docstrings som beskriver:
  - Vad funktionen gör
  - Parametrar och deras typer
  - Returvärde
  - Eventuella exceptions som kastas

## Licens

Genom att bidra till SFS-Processor accepterar du att ditt bidrag licensieras under **Business Source License 1.1** (samma licens som resten av projektet).

Se [LICENSE](LICENSE)-filen för fullständiga villkor. Observera att projektet övergår till MIT-licens 2029-01-01.

## Frågor?

Om du har frågor som inte täcks här:

- Öppna ett issue med etiketten "question"
- Kontakta projektmaintainer via GitHub

Tack för ditt bidrag! 🙏
