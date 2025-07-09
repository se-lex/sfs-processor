# Svensk författningssamling (SFS) som Markdown-filer

Detta repository innehåller Python-script för att ladda ner och konvertera SFS-författningar (Svensk författningssamling) från antingen Regeringskansliets publika söktjänst eller Riksdagens öppna API. Konvertering till Markdown sker med en uppsättning regler.

1. Se till att du har Python 3.6+ installerat
2. Installera nödvändiga beroenden:

```bash
pip install -r requirements.txt
```

## Status

[![Hämta nya SFS-författningar från Regeringskansliets publika söktjänst](https://github.com/marcarl/sfs-processor/actions/workflows/fetch-sfs-workflow.yml/badge.svg)](https://github.com/marcarl/sfs-processor/actions/workflows/fetch-sfs-workflow.yml)

## Användning

### Välj källa för nedladdning

Scriptet stöder två olika källor:

- **rkrattsbaser** (standard): Hämtar strukturerad JSON-data från Regeringskansliets Elasticsearch API
- **riksdagen**: Hämtar HTML-filer från Riksdagens öppna data

### Ladda ner från Regeringskansliet (standard)

#### Ladda ner alla SFS-författningar

```bash
python downloaders/download_sfs_docs.py
```

eller explicit:

```bash
python downloaders/download_sfs_docs.py --source rkrattsbaser
```

**Observera:** För rkrattsbaser måste du ange specifika författnings-ID:n med `--ids` parametern.

#### Ladda ner specifika författningar från Regeringskansliet

```bash
python downloaders/download_sfs_docs.py --ids "2025:764,2025:765"
```

### Ladda ner från Riksdagen

#### Ladda ner alla SFS-författningar från Riksdagen

```bash
python downloaders/download_sfs_docs.py --ids all --source riksdagen
```

#### Ladda ner specifika författningar från Riksdagen

```bash
python downloaders/download_sfs_docs.py --ids "sfs-2017-900,sfs-2009-400,sfs-2011-791" --source riksdagen
```

#### Med anpassad output-mapp

```bash
python downloaders/download_sfs_docs.py --source rkrattsbaser --ids "2025:764" --out "sfs_json"
```

### Ange output-mapp

Du kan ange vilken mapp författningarna ska sparas i med `--out` parametern:

```bash
python downloaders/download_sfs_docs.py --out "sfs_docs"
```

Eller kombinera med specifika författnings-ID:n:

```bash
python downloaders/download_sfs_docs.py --ids "sfs-2017-900,sfs-2009-400" --out "mina_favorit_lagar"
```

### Exempel med Swedac-lagar

För att ladda ner alla lagar som styr Swedac till en specifik mapp:

```bash
python downloaders/download_sfs_docs.py --ids "sfs-2017-900,sfs-2009-400,sfs-2009-641,sfs-2021-1252,sfs-2011-791,sfs-2011-811,sfs-2019-16,sfs-1991-93,sfs-1993-1634,sfs-2014-864,sfs-2002-574,sfs-2009-211,sfs-2006-985,sfs-2006-1592,sfs-2016-1128,sfs-2009-1079,sfs-2009-1078,sfs-2010-900,sfs-2011-338,sfs-2011-1244,sfs-2011-1261,sfs-1992-1514,sfs-1993-1066,sfs-1994-99,sfs-1997-857,sfs-1999-716,sfs-2005-403,sfs-2006-1043,sfs-2011-318,sfs-2011-345,sfs-2011-1200,sfs-2011-1480,sfs-2012-211,sfs-2012-238,sfs-1975-49,sfs-1999-779,sfs-1999-780" --out "swedac_lagar"
```

## Konvertering till olika format

Efter nedladdning kan du konvertera JSON-filerna till olika format:

### Konvertering till Markdown

```bash
python sfs_processor.py --input sfs_json --output SFS --formats md
```

### Automatisk tabellkonvertering

Processorn konverterar automatiskt tabellstrukturer i juridiska dokument till proper Markdown-tabeller:

- **Tab-separerade tabeller**: Vanliga i skattescheman och juridiska referenstabeller
- **Mellanslag-separerade tabeller**: Ofta i regleringsspecifikationer och näringsdeklarationer
- **Automatisk detektering**: Ingen manuell intervention krävs
- **Rensning av tomma kolumner**: Städar upp inkonsekvent spacing

Exempel på konverterade tabeller:
- Skatte-/avgiftsscheman med produktkoder och satser
- Internationella fördragstabeller med länder och reservationer
- Juridiska referenstabeller med lagcitat och beskrivningar
- Tekniska specifikationer med mätvärden

### Struktur av genererade Markdown-filer

De genererade Markdown-filerna innehåller strukturerad markup med `<section>`-taggar:

- **`<section class="kapitel">`**: Omsluter kapitel med underliggande paragrafer
- **`<section class="paragraf">`**: Omsluter varje paragraf (§) med rubrik och innehåll

Exempel på struktur:

```html
<section class="kapitel">
### 1 kap. Inledande bestämmelser
<section class="paragraf">
#### 1 §
Innehållet i paragrafen...
</section>
</section>
```

Denna struktur gör det möjligt att skapa avancerad CSS-styling och JavaScript-funktionalitet för navigation och presentation av författningstexten.

### Selex-attribut för juridisk status och datum

Förutom CSS-klasser använder `<section>`-taggarna även `selex:`-attribut för att hantera juridisk status och datum. Dessa attribut möjliggör filtrering av innehåll baserat på ikraftträdande- och upphörandedatum:

- **`selex:status`**: Anger sektionens juridiska status
  - `ikraft`: Sektionen innehåller ikraftträdanderegler (t.ex. "/Träder i kraft I:2024-01-01")
  - `upphavd`: Sektionen är upphävd (t.ex. innehåller "upphävd" eller "/Upphör att gälla")

- **`selex:ikraft_datum`**: Datum då sektionen träder ikraft (format: YYYY-MM-DD)
- **`selex:upphor_datum`**: Datum då sektionen upphör att gälla (format: YYYY-MM-DD)  
- **`selex:ikraft_villkor`**: Villkor för ikraftträdande (när inget specifikt datum anges)

Exempel på selex-attribut:

```html
<section class="kapitel" selex:status="ikraft" selex:ikraft_datum="2024-01-01">
### Övergångsbestämmelser
/Träder i kraft I:2024-01-01/
...
</section>

<section class="paragraf" selex:status="upphavd" selex:upphor_datum="2023-12-31">
####  1 § En paragraf
/Upphör att gälla U:2023-12-31/
...
</section>

<section class="kapitel" selex:status="ikraft" selex:ikraft_villkor="den dag regeringen bestämmer">
### Villkorad ikraftträdande
/Träder i kraft I:bestämmelse om något/
...
</section>
```

Dessa attribut används automatiskt av systemets datumfiltrering för att skapa versioner av författningar som gäller vid specifika tidpunkter. Sektioner med `selex:upphor_datum` som har passerat tas bort, och sektioner med `selex:ikraft_datum` som ännu inte har kommit tas bort från den aktuella versionen.

### Konvertering till HTML med ELI-struktur

```bash
python sfs_processor.py --input sfs_json --output output --formats html
```

Detta skapar HTML-filer i ELI-strukturen: `/eli/sfs/{artal}/{lopnummer}/index.html`

### HTML med ändringsversioner

För att inkludera separata versioner för varje ändringsförfattning:

```bash
python sfs_processor.py --input sfs_json --output output --formats htmldiff
```

### Kombinera flera format

```bash
python sfs_processor.py --input sfs_json --output output --formats md,html,htmldiff
```

## Kommandoradsalternativ för nedladdning

```bash
python downloaders/download_sfs_docs.py [--ids IDS] [--out MAPP] [--source KÄLLA]
```

### Parametrar för nedladdning

- `--ids`: Kommaseparerad lista med dokument-ID:n att ladda ner, eller "all" för att hämta alla från Riksdagen (default: "all")
- `--out`: Mapp att spara nedladdade dokument i (default: "sfs_docs")
- `--source`: Välj källa - "riksdagen" för HTML-format eller "rkrattsbaser" för JSON-format (default: "riksdagen")

## Kommandoradsalternativ för konvertering

```bash
python sfs_processor.py [--input INPUT] [--output OUTPUT] [--formats FORMATS] [--filter FILTER] [--no-year-folder] [--verbose]
```

### Parametrar för konvertering

- `--input`: Input-katalog med JSON-filer (default: "sfs_json")
- `--output`: Output-katalog för konverterade filer (default: "SFS")
- `--formats`: Utdataformat att generera, kommaseparerat. Stödda: md, git, html, htmldiff (default: "md")
  - `md`: Generera markdown-filer
  - `git`: Aktivera Git-commits med historiska datum (kräver md)
  - `html`: Generera HTML-filer i ELI-struktur (endast grunddokument)
  - `htmldiff`: Generera HTML-filer i ELI-struktur med ändringsversioner
- `--filter`: Filtrera filer efter år (YYYY) eller specifik beteckning (YYYY:NNN). Kan vara kommaseparerad lista.
- `--no-year-folder`: Skapa inte årbaserade undermappar för dokument
- `--verbose`: Visa detaljerad diff-utdata för varje ändringsbearbetning
