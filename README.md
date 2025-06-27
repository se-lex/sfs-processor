# Ladda ner SFS som textfiler från Riksdagens öppna API

Skapades med följande prompt mot Claude Sonnet 4 agent mode:

```txt
Skapa ett python-script som kör HTTP GET och läser textinnehållet på följande URL:

https://data.riksdagen.se/dokumentlista/?sok=&doktyp=SFS&utformat=iddump&a=s#soktraff

Innehållet är en kommasepararerad lista på dokument-IDn. Parsa det och se till att trimma bort alla mellanslag.

Låt sedan scriptet använda varje dokument-ID för att skapa en textfil, genom att ladda ner innehållet på följande URL för varje dokument-ID:

https://data.riksdagen.se/dokument/%DOKUMENTID%.text

%DOKUMENTID% ersätts alltså med respektive dokument-ID.

Markdown-filen som sparas ska heta samma som Dokument-ID och ha filändelsen .txt
```

# Beskrivning

Detta Python-script laddar ner SFS-dokument (Svensk författningssamling) från Riksdagens öppna data.

## Funktionalitet

Scriptet gör följande:

1. Hämtar en lista med dokument-ID:n från Riksdagens dokumentlista
2. Parsar kommaseparerade värden och trimmar mellanslag
3. För varje dokument-ID, hämtar textinnehållet från Riksdagens API
4. Sparar varje dokument som en .txt-fil med dokument-ID som filnamn

## Installation

1. Se till att du har Python 3.6+ installerat
2. Installera nödvändiga beroenden:

```bash
pip install -r requirements.txt
```

## Användning

Kör scriptet med:

```bash
python download_sfs_documents.py
```

## Output

- Dokument sparas i katalogen `documents/`
- Varje fil får namnet `[DOKUMENT-ID].txt`
- Scriptet visar progress och en sammanfattning när det är klart

## Funktioner

- **Felhantering**: Hanterar nätverksfel och filfel gracefullt
- **Progress-indikator**: Visar framsteg under nedladdning
- **Throttling**: Kort paus mellan nedladdningar för att vara snäll mot servern
- **UTF-8 encoding**: Korrekt hantering av svenska tecken

## API-endpoints

- **Dokument-lista**: `https://data.riksdagen.se/dokumentlista/?sok=&doktyp=SFS&utformat=iddump&a=s#soktraff`
- **Dokument-text**: `https://data.riksdagen.se/dokument/[DOKUMENT-ID].text`
