# sfs-processor - Verktyg för konvertering av Svensk författningssamling

Detta repository innehåller Python-script för att konvertera SFS-författningar (Svensk författningssamling) från JSON-format till Markdown med temporala taggar, HTML, Git och andra format.

> [!NOTE]
> **Detta är en del av [SE-Lex](https://github.com/se-lex)**, läs mer om [projektet här](https://github.com/se-lex).
>
> SFS-författningar exporteras till [https://github.com/se-lex/sfs](https://github.com/se-lex/sfs) och publiceras också som HTML på [https://selex.se](https://selex.se) med stöd för EU:s juridiska identifieringsstandard (ELI).

## Installation

1. Se till att du har Python 3.11 eller senare installerat
2. Installera nödvändiga beroenden:

```bash
pip install -r requirements.txt
```

## Snabbstart

Konvertera JSON-filer med författningar till Markdown:

```bash
python sfs_processor.py --input sfs_json --output output/md --formats md-markers
```

## Output-format

Verktyget kan generera författningar i flera olika format, beroende på användningsområde:

### Markdown-format

- **`md-markers`** (förvalt): Markdown med semantiska `<section>`-taggar och selex-attribut för juridisk status och temporal hantering
- **`md`**: Rena Markdown-filer med normaliserade rubriknivåer, lämpliga för visning och läsning

### Git-format

- **`git`**: Exporterar författningar som Git-commits med historiska datum, vilket skapar en versionshistorik av lagstiftningen

### HTML-format

- **`html`**: Genererar HTML-filer i ELI-struktur (`/eli/sfs/{år}/{nummer}/index.html`) för webbpublicering
- **`htmldiff`**: Som HTML men inkluderar även separata versioner för varje ändringsförfattning

Exempel på att kombinera flera format:

```bash
python sfs_processor.py --input sfs_json --output output --formats md,html,git
```

## Hämta källdata

För att konvertera författningar behöver du först ladda ner JSON-data:

### Ladda ner alla författningar från Regeringskansliet

```bash
python downloaders/download_sfs_docs.py --ids all --source rkrattsbaser
```

### Ladda ner specifika författningar

```bash
python downloaders/download_sfs_docs.py --ids "2024:675,2024:700" --source rkrattsbaser
```

Nedladdade filer sparas som standard i katalogen `sfs_docs`. Du kan ange annan katalog med `--out` parametern.

## Användning

### Grundläggande konvertering

Konvertera alla JSON-filer i en katalog till Markdown:

```bash
python sfs_processor.py --input sfs_json --output output/md --formats md-markers
```

### Struktur av genererade Markdown-filer

Beroende på vilket format du väljer får du olika strukturer:

#### Format: `md-markers` (förvalt)

Markdown-filer med bevarad semantisk struktur genom `<section>`-taggar:

- **`<section class="kapitel">`**: Omsluter kapitel som strukturell enhet med underliggande paragrafer
- **`<section class="paragraf">`**: Omsluter varje paragraf (§) som en avgränsad juridisk bestämmelse

```html
<section class="kapitel">
## Inledande bestämmelser
<section class="paragraf">
### 1 §
Innehållet i paragrafen...
</section>
</section>
```

Denna semantiska struktur bevarar dokumentets logiska uppbyggnad och möjliggör automatisk bearbetning, analys, och navigation av författningstexten. Section-taggarna kan även användas för CSS-styling och JavaScript-funktionalitet.

#### Format: `md`

Rena Markdown-filer med normaliserade rubriknivåer, utan section-taggar:

```markdown
# Lag (2024:123) om exempel

## Inledande bestämmelser

### 1 §

Innehållet i paragrafen...

### 2 §

Mer innehåll...
```

Detta format är lämpligt för enkel visning och läsning, utan metadata eller temporal hantering.

### Selex-attribut för juridisk status och datum

Förutom CSS-klasser använder `<section>`-taggarna även `selex:`-attribut för att hantera juridisk status och datum. Dessa attribut möjliggör filtrering av innehåll baserat på ikraftträdande- och upphörandedatum:

- **`selex:status`**: Anger sektionens juridiska status
  - `ikraft`: Sektionen innehåller ikraftträdanderegler (konverterat från t.ex. "/Träder i kraft I:2024-01-01")
  - `upphavd`: Sektionen är upphävd (konverterad från ifall rubrik innehåller "upphävd" eller "/Upphör att gälla")

- **`selex:ikraft_datum`**: Datum då sektionen träder ikraft (format: YYYY-MM-DD)
- **`selex:upphor_datum`**: Datum då sektionen upphör att gälla (format: YYYY-MM-DD)  
- **`selex:ikraft_villkor`**: Villkor för ikraftträdande (när inget specifikt datum anges)

Exempel på selex-attribut:

```html
<section class="kapitel" selex:status="ikraft" selex:ikraft_datum="2024-01-01">
### 1 § En paragraf
...
</section>

<section class="paragraf" selex:status="upphavd" selex:upphor_datum="2023-12-31">
#### 2 § En paragraf 
...
</section>

<section class="kapitel" selex:status="ikraft" selex:ikraft_villkor="den dag regeringen bestämmer">
### 3 § Rubrik på villkorad ikraftträdande
...
</section>
```

Dessa attribut används automatiskt av systemets datumfiltrering för att skapa versioner av författningar som gäller vid specifika tidpunkter. Sektioner med `selex:upphor_datum` som har passerat tas bort, och sektioner med `selex:ikraft_datum` som ännu inte har kommit tas bort från den aktuella versionen.

### Temporal processing för olika format

Systemet hanterar temporal processing (tidsbaserad filtrering) olika beroende på vilket format som används:

- **`md-markers`** (förvalt): Bevarar selex-taggar och hoppar över temporal processing. Detta gör att alla temporal attribut behålls för senare bearbetning. Rekommenderas för att bevara all juridisk metadata.

- **`md`**: Tillämpar temporal processing med **dagens datum som målpunkt**. Detta är viktigt att förstå:
  - Upphävda bestämmelser (med `selex:upphor_datum` före dagens datum) tas bort
  - Bestämmelser som ännu inte trätt i kraft (med `selex:ikraft_datum` efter dagens datum) tas bort
  - Selex-taggar tas bort efter filtrering
  - Resultatet blir en "ren" Markdown-vy av hur lagen ser ut idag
  - **Obs:** Eftersom temporal filtrering används automatiskt, kan innehåll försvinna om det är upphävt eller ej ikraftträtt

- **`git`**: Hoppar över temporal processing i huvudbearbetningen. Temporal hantering sköts separat i git-arbetsflödet för att skapa historiska commits.

- **`html`** och **`htmldiff`**: Tillämpar temporal processing med dagens datum innan HTML-generering, liknande `md`-format.

#### Exempel med target-date

För att se hur en lag såg ut vid ett specifikt datum:

```bash
# Se hur lagen såg ut 2023-01-01
python sfs_processor.py --input sfs_json --output output/md --formats md --target-date 2023-01-01
```

Detta är användbart för att skapa historiska versioner eller för att förstå hur lagen såg ut vid en viss tidpunkt.

## Kommandoradsalternativ

```bash
python sfs_processor.py [--input INPUT] [--output OUTPUT] [--formats FORMATS] [--filter FILTER] [--target-date DATE] [--no-year-folder] [--verbose]
```

### Parametrar

- `--input`: Input-katalog med JSON-filer (default: "sfs_json")
- `--output`: Output-katalog för konverterade filer (default: "SFS")
- `--formats`: Utdataformat att generera, kommaseparerat. Stödjer: md-markers, md, git, html, htmldiff (default: "md-markers")
  - `md-markers`: Generera markdown-filer med section-taggar bevarade
  - `md`: Generera rena markdown-filer utan section-taggar
  - `git`: Aktivera Git-commits med historiska datum
  - `html`: Generera HTML-filer i ELI-struktur (endast grunddokument)
  - `htmldiff`: Generera HTML-filer i ELI-struktur med ändringsversioner
- `--filter`: Filtrera filer efter år (YYYY) eller specifik beteckning (YYYY:NNN). Kan vara kommaseparerad lista.
- `--target-date`: Datum (YYYY-MM-DD) för temporal filtrering, baserat på selex-taggar. Används med `md`, `html` och `htmldiff` format för att filtrera innehåll baserat på giltighetsdatum. Om inte angivet används dagens datum för `md`-format. Exempel: `--target-date 2023-01-01`
- `--no-year-folder`: Skapa inte årbaserade undermappar för dokument
- `--verbose`: Visa detaljerad information om bearbetningen

## Bidra

Vi välkomnar bidrag från communityn! 🙌

- Läs [CONTRIBUTING.md](CONTRIBUTING.md) för riktlinjer om hur du bidrar
- Se [DEVELOPMENT.md](DEVELOPMENT.md) för utvecklardokumentation och arkitekturöversikt
- Kontakt: Martin Rimskog via [e-post](mailto:martin@marca.se) eller [LinkedIn](https://www.linkedin.com/in/martinrimskog/)
