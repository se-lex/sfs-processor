# Svensk författningssamling (SFS) till Markdown-filer

Detta repository innehåller Python-script för att konvertera SFS-författningar (Svensk författningssamling) från JSON-format till välformaterade Markdown-filer och andra format.

## Installation

1. Se till att du har Python 3.11 eller senare installerat
2. Installera nödvändiga beroenden:

```bash
pip install -r requirements.txt
```

## Snabbstart

Konvertera JSON-filer med författningar till Markdown:

```bash
python sfs_processor.py --input sfs_json --output SFS --formats md
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
python sfs_processor.py --input sfs_json --output SFS --formats md
```

### Struktur av genererade Markdown-filer

Beroende på vilket format du väljer får du olika strukturer:

#### Format: `md` (standard)

Rena Markdown-filer med normaliserade rubriknivåer:

```markdown
# Lag (2024:123) om exempel

## Inledande bestämmelser

### 1 §

Innehållet i paragrafen...

### 2 §

Mer innehåll...
```

#### Format: `md-markers`

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

- **`md` format**: Tillämpar temporal processing med dagens datum som målpunkt. Selex-taggar tas bort efter filtrering.
- **`md-markers` format**: Bevarar selex-taggar och hoppar över temporal processing. Detta gör att alla temporal attribut behålls för senare bearbetning.
- **`git` format**: Hoppar över temporal processing i huvudbearbetningen. Temporal hantering sköts separat i git-arbetsflödet för att skapa historiska commits.
- **`html` format**: Tillämpar temporal processing med dagens datum innan HTML-generering.
- **`htmldiff` format**: Tillämpar temporal processing med dagens datum innan HTML-generering.

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

## Kommandoradsalternativ

```bash
python sfs_processor.py [--input INPUT] [--output OUTPUT] [--formats FORMATS] [--filter FILTER] [--no-year-folder] [--verbose]
```

### Parametrar

- `--input`: Input-katalog med JSON-filer (default: "sfs_json")
- `--output`: Output-katalog för konverterade filer (default: "SFS")
- `--formats`: Utdataformat att generera, kommaseparerat. Stödjer: md, md-markers, git, html, htmldiff (default: "md")
  - `md`: Generera rena markdown-filer utan section-taggar
  - `md-markers`: Generera markdown-filer med section-taggar bevarade
  - `git`: Aktivera Git-commits med historiska datum
  - `html`: Generera HTML-filer i ELI-struktur (endast grunddokument)
  - `htmldiff`: Generera HTML-filer i ELI-struktur med ändringsversioner
- `--filter`: Filtrera filer efter år (YYYY) eller specifik beteckning (YYYY:NNN). Kan vara kommaseparerad lista.
- `--no-year-folder`: Skapa inte årbaserade undermappar för dokument
- `--verbose`: Visa detaljerad information om bearbetningen

## Tester

Projektet använder pytest för testning med omfattande testsvit som täcker funktionalitet och edge cases.

### Installation av testberoenden

```bash
pip install pytest pytest-cov pytest-mock requests-mock
```

### Köra alla tester

```bash
pytest
```

### Köra tester med täckningsrapport

```bash
pytest --cov=. --cov-report=html
```

### Köra specifika testkategorier

```bash
# Endast unit-tester (snabba, ingen I/O)
pytest -m unit

# Endast integrationstester
pytest -m integration

# Endast API-tester (mockade API-anrop)
pytest -m api

# Hoppa över långsamma tester
pytest -m "not slow"
```

### Köra enskilda testfiler

```bash
pytest test/test_linking.py -v
pytest test/test_title_temporal.py -v
pytest test/test_predocs.py -v
```

### CI/CD

Testerna körs automatiskt vid varje push och pull request via GitHub Actions. Täckningsrapporter genereras och arkiveras som artifacts.

## Bidra

Vi välkomnar bidrag från communityn! 🙌

- Läs [CONTRIBUTING.md](CONTRIBUTING.md) för riktlinjer om hur du bidrar
- Se [DEVELOPMENT.md](DEVELOPMENT.md) för utvecklardokumentation och arkitekturöversikt
- Öppna ett [GitHub Issue](https://github.com/se-lex/sfs-processor/issues) för att rapportera buggar eller föreslå nya funktioner

## Community och support

- **Rapportera buggar**: Öppna ett issue på GitHub med detaljerad beskrivning
- **Föreslå funktioner**: Diskutera nya idéer via GitHub Issues
- **Frågor**: Använd GitHub Issues med etiketten "question"

Se [CONTRIBUTING.md](CONTRIBUTING.md) för mer information om hur du kan hjälpa till.

## Licens

Projektet är licensierat under **Business Source License 1.1 (BSL 1.1)**.

### Sammanfattning

- ✅ **Fritt att använda** för icke-produktionssyfte
- ✅ **Fritt att modifiera och distribuera**
- ✅ **Övergår automatiskt till MIT-licens** 2029-01-01
- ⚠️ **Produktionsanvändning kräver kommersiell licens** (kontakta martin@marca.se)
- 🤖 **AI-träningsanvändning kräver explicit tillstånd**

Se [LICENSE](LICENSE)-filen för fullständiga villkor.

