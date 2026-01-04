# Bidra till sfs-processor

Tack för ditt intresse att bidra till sfs-processor! Det här dokumentet beskriver hur du kan hjälpa till.

## Snabbstart

1. **Forka och klona** repositoryt
2. **Installera**: `pip install -r requirements.txt`
3. **Testa**: `python -m pytest test/ -v`
4. **Läs**: [DEVELOPMENT.md](DEVELOPMENT.md) för teknisk dokumentation

För detaljerad setup och utvecklingsmiljö, se [DEVELOPMENT.md](DEVELOPMENT.md).

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

Projektet följer **PEP 8-standarden**. Huvudriktlinjer:

- 4 mellanslag för indentering
- Max 100 tecken per rad
- Beskrivande variabelnamn
- Docstrings för alla publika funktioner

För fullständiga kodkonventioner, se [DEVELOPMENT.md](DEVELOPMENT.md#kodkonventioner).

## Frågor?

Om du har frågor som inte täcks här:

- Öppna ett issue med etiketten "question"
- Kontakta projektmaintainer via GitHub

Tack för ditt bidrag! 🙏
