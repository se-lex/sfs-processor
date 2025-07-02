# Svensk författningssamling (SFS) - från Riksdagens öppna API till Markdown-filer

Detta repository innehåller Python-script för att ladda ner och konvertera SFS-dokument (Svensk författningssamling) från Riksdagens öppna data. Konvertering till Markdown sker med LLM-anrop.

## Några Python-grunkor

### 1. download_sfs_documents.py

Laddar ner SFS-dokument från antingen Riksdagens öppna API (som HTML-filer) eller Regeringskansliets Elasticsearch API (som strukturerad JSON-data).

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

Scriptet har senare utökats med stöd för Regeringskansliets API och gör följande:

**För Riksdagens API (standard):**

1. Hämtar en lista med dokument-ID:n från Riksdagens dokumentlista
2. Parsar kommaseparerade värden och trimmar mellanslag
3. För varje dokument-ID, hämtar HTML-innehållet från Riksdagens API
4. Sparar varje dokument som en .html-fil med dokument-ID som filnamn

**För Regeringskansliets API:**

1. Använder specifika dokument-ID:n (automatisk hämtning av alla ID:n stöds ej)
2. Hämtar strukturerad data via Elasticsearch API
3. Sparar varje dokument som en .json-fil med fullständig metadata

### 2. convert_html_to_markdown.py

Detta script konverterar HTML-filer till Markdown-format med hjälp av OpenAI API.

### 3. convert_json_to_markdown.py

Detta script konverterar JSON-filer (från Regeringskansliets API) till Markdown-format med strukturerad YAML front matter.

**Funktioner:**

- Extraherar relevant metadata från JSON-strukturen
- Skapar strukturerad YAML front matter med alla viktiga fält
- Formaterar innehållet som läsbar Markdown
- Hanterar ändringsförfattningar i strukturerat format
- Rensar och normaliserar textinnehåll
- Konverterar datum till ISO-format

**Användning:**

```bash
python convert_json_to_markdown.py
```

Scriptet läser alla .json-filer från `json/`-mappen och skapar motsvarande .md-filer i `markdown/`-mappen.

## Installation

1. Se till att du har Python 3.6+ installerat
2. Installera nödvändiga beroenden:

```bash
pip install -r requirements.txt
```

## Användning

### Välj källa för nedladdning

Scriptet stöder två olika källor:

- **riksdagen** (standard): Hämtar HTML-filer från Riksdagens öppna data
- **rkrattsbaser**: Hämtar strukturerad JSON-data från Regeringskansliets Elasticsearch API

### Ladda ner från Riksdagen (standard)

#### Ladda ner alla SFS-dokument

```bash
python download_sfs_documents.py
```

eller explicit:

```bash
python download_sfs_documents.py --ids all --source riksdagen
```

#### Ladda ner specifika dokument från Riksdagen

```bash
python download_sfs_documents.py --ids "sfs-2017-900,sfs-2009-400,sfs-2011-791" --source riksdagen
```

### Ladda ner från Regeringskansliets API

**Observera:** Automatisk hämtning av alla dokument-ID:n (`--ids all`) stöds inte för rkrattsbaser. Du måste ange specifika dokument-ID:n.

#### Ladda ner specifika dokument från rkrattsbaser

```bash
python download_sfs_documents.py --source rkrattsbaser --ids "2025:764,2025:765"
```

#### Med anpassad output-mapp

```bash
python download_sfs_documents.py --source rkrattsbaser --ids "2025:764" --out "sfs_json"
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

## Funktioner

- **Två datakällor**: Välj mellan Riksdagens HTML-data eller Regeringskansliets strukturerade JSON-data
- **Flexibel input**: Kan ladda ner antingen alla SFS-dokument (endast Riksdagen) eller en specificerad lista
- **Konfigurerbar output**: Ange vilken mapp dokumenten ska sparas i med `--out` parametern
- **Kommandoradsparametrar**:
  - `--ids`: Ange specifika dokument-ID:n eller "all" för alla (endast Riksdagen)
  - `--source`: Välj mellan "riksdagen" (HTML) eller "rkrattsbaser" (JSON)
  - `--out`: Ange output-mapp
- **Felhantering**: Hanterar nätverksfel och filfel gracefullt
- **Progress-indikator**: Visar framsteg under nedladdning
- **Throttling**: Kort paus mellan nedladdningar för att vara snäll mot servern
- **UTF-8 encoding**: Korrekt hantering av svenska tecken

## Kommandoradsalternativ

```bash
python download_sfs_documents.py [--ids IDS] [--out MAPP] [--source KÄLLA]
```

### Parametrar

- `--ids`: Kommaseparerad lista med dokument-ID:n att ladda ner, eller "all" för att hämta alla från Riksdagen (default: "all")
- `--out`: Mapp att spara nedladdade dokument i (default: "sfs_docs")
- `--source`: Välj källa - "riksdagen" för HTML-format eller "rkrattsbaser" för JSON-format (default: "riksdagen")

## Output

### Riksdagen (HTML)

- Dokument sparas i den angivna katalogen (default: `sfs_docs/`)
- Varje fil får namnet `[DOKUMENT-ID].html`
- Innehåller HTML-formaterat lagtext

### Regeringskansliet (JSON)

- Dokument sparas i den angivna katalogen (default: `sfs_docs/`)
- Varje fil får namnet `[DOKUMENT-ID].json`
- Innehåller strukturerad metadata och lagtext i JSON-format

## Konvertera HTML till Markdown

### convert_html_to_markdown.py

Detta script konverterar HTML-filer till Markdown-format med hjälp av OpenAI API.

#### Installation

Installera nödvändiga beroenden (inklusive OpenAI):

```bash
pip install -r requirements.txt
```

#### Användning

##### Grundläggande användning

```bash
python convert_html_to_markdown.py --in sfs_docs --apikey YOUR_OPENAI_API_KEY
```

##### Alla parametrar

```bash
python convert_html_to_markdown.py --in INPUT_MAPP --out OUTPUT_MAPP --apikey YOUR_OPENAI_API_KEY --model MODELL
```

#### Parametrar

- `--in`: **Obligatorisk**. Mapp med HTML-filer att konvertera
- `--out`: Output-mapp för Markdown-filer (default: `md_output`)
- `--apikey`: **Obligatorisk**. Din OpenAI API-nyckel
- `--model`: OpenAI-modell att använda (default: `o3`)

#### Exempel

Konvertera alla HTML-filer i `sfs_docs` mappen till Markdown:

```bash
python convert_html_to_markdown.py --in sfs_docs --apikey sk-your-api-key-here
```

Använda en specifik modell och output-mapp:

```bash
python convert_html_to_markdown.py --in sfs_docs --out markdown_documents --apikey sk-your-api-key-here --model gpt-4
```

#### Komplett arbetsflöde

1. Ladda ner SFS-dokument som HTML:

```bash
python download_sfs_documents.py --out sfs_docs
```

2. Konvertera HTML till Markdown:

```bash
python convert_html_to_markdown.py --in sfs_docs --apikey YOUR_API_KEY
```

Detta skapar en komplett pipeline från Riksdagens öppna data till Markdown-filer redo för vidare bearbetning.
