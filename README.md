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

## Beskrivning

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

### Ladda ner alla SFS-dokument (standard)

```bash
python download_sfs_documents.py
```

eller explicit:

```bash
python download_sfs_documents.py --ids all
```

### Ladda ner specifika dokument

Du kan också ange en kommaseparerad lista med specifika dokument-ID:n:

```bash
python download_sfs_documents.py --ids "sfs-2017-900,sfs-2009-400,sfs-2011-791"
```

### Ange output-mapp

Du kan ange vilken mapp dokumenten ska sparas i med `--out` parametern:

```bash
python download_sfs_documents.py --out "mina_dokument"
```

Eller kombinera med specifika dokument-ID:n:

```bash
python download_sfs_documents.py --ids "sfs-2017-900,sfs-2009-400" --out "mina_favorit_lagar"
```

### Exempel med Swedac-lagar

För att ladda ner alla lagar som styr Swedac till en specifik mapp:

```bash
python download_sfs_documents.py --ids "sfs-2017-900,sfs-2009-400,sfs-2009-641,sfs-2021-1252,sfs-2011-791,sfs-2011-811,sfs-2019-16,sfs-1991-93,sfs-1993-1634,sfs-2014-864,sfs-2002-574,sfs-2009-211,sfs-2006-985,sfs-2006-1592,sfs-2016-1128,sfs-2009-1079,sfs-2009-1078,sfs-2010-900,sfs-2011-338,sfs-2011-1244,sfs-2011-1261,sfs-1992-1514,sfs-1993-1066,sfs-1994-99,sfs-1997-857,sfs-1999-716,sfs-2005-403,sfs-2006-1043,sfs-2011-318,sfs-2011-345,sfs-2011-1200,sfs-2011-1480,sfs-2012-211,sfs-2012-238,sfs-1975-49,sfs-1999-779,sfs-1999-780" --out "swedac_lagar"
```

## Output

- Dokument sparas i den angivna katalogen (default: `sfs_html/`)
- Varje fil får namnet `[DOKUMENT-ID].html`
- Scriptet visar progress och en sammanfattning när det är klart

## Funktioner

- **Flexibel input**: Kan ladda ner antingen alla SFS-dokument eller en specificerad lista
- **Konfigurerbar output**: Ange vilken mapp dokumenten ska sparas i med `--out` parametern
- **Kommandoradsparametrar**: Använd `--ids` för att ange specifika dokument-ID:n
- **Felhantering**: Hanterar nätverksfel och filfel gracefullt
- **Progress-indikator**: Visar framsteg under nedladdning
- **Throttling**: Kort paus mellan nedladdningar för att vara snäll mot servern
- **UTF-8 encoding**: Korrekt hantering av svenska tecken

## API-endpoints

- **Dokument-lista**: `https://data.riksdagen.se/dokumentlista/?sok=&doktyp=SFS&utformat=iddump&a=s#soktraff`
- **Dokument-text**: `https://data.riksdagen.se/dokument/[DOKUMENT-ID].text`
