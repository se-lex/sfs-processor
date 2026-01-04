# Utvecklardokumentation

Det här dokumentet ger en djupare översikt över projektets arkitektur, kodstruktur och utvecklingsworkflow.

## Projektöversikt

`sfs-processor` är ett verktyg för att konvertera svensk lagstiftningsdata (Svensk författningssamling) från JSON-format till olika output-format inklusive Markdown-filer, HTML-filer och Git-commits.

### Huvudfunktioner

- Hämta SFS-dokument från RK (Regeringskansliet)
- Konvertera JSON till välformaterad Markdown
- Generera HTML med temporal hantering av ändringar
- Exportera till Git-repository med historik
- Hantera temporala aspekter av lagstiftning (giltighetstider, ändringar)

## Kom igång

### Installation för bidragsgivare

Om du vill bidra till projektet:

1. **Forka repositoryt** på GitHub
2. **Klona din fork** lokalt:
   ```bash
   git clone https://github.com/se-lex/sfs-processor.git
   cd sfs-processor
   ```
3. **Skapa virtuell miljö** (rekommenderat):
   ```bash
   python -m venv venv
   source venv/bin/activate  # På Windows: venv\Scripts\activate
   ```
4. **Installera dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

För bidragsprocess, se [CONTRIBUTING.md](CONTRIBUTING.md).

### Köra tester

**Alla tester**:
```bash
python -m pytest test/ -v
```

**Enskilda testfiler**:
```bash
python test/test_title_temporal.py
```

**Med coverage**:
```bash
pip install pytest-cov
python -m pytest test/ --cov=. --cov-report=html
```

### Köra lokalt

**Processa ett dokument**:
```bash
python sfs_processor.py data/test_docs/sfs-2023-123.json --output md
```

**Ladda ner testdokument**:
```bash
python downloaders/download_sfs_docs.py --year 2023 --number 123
```

**Verbose mode** för detaljerad loggning:
```bash
python sfs_processor.py input.json --output md --verbose
```

### Miljövariabler

Skapa en `.env`-fil för lokal utveckling:

```bash
# GitHub (för Git-export)
GIT_GITHUB_PAT=ghp_your_personal_access_token

# Cloudflare R2 (för HTML-export)
CLOUDFLARE_R2_ACCESS_KEY_ID=your_access_key
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your_secret_key
CLOUDFLARE_R2_BUCKET_NAME=your_bucket
CLOUDFLARE_R2_ACCOUNT_ID=your_account_id

# HTML (ELI) konfiguration
ELI_HOST=selex.se
INTERNAL_LINKS_BASE_URL=https://selex.se/eli
```

**OBS**: `.env`-filen är listad i `.gitignore` och ska ALDRIG committas.

## Arkitektur

### Dataflöde

```
RK API → JSON → Parser → Formatters → Exporters → Output
                                ↓
                         Temporal Processing
```

1. **Nedladdning**: Hämta rådata från Regeringskansliet
2. **Parsing**: Validera och strukturera JSON-data
3. **Formatering**: Konvertera till Markdown/HTML
4. **Temporal processing**: Hantera tidsbaserade aspekter
5. **Export**: Skriv till fil, Git eller cloud storage

## Katalogstruktur

```
sfs-processor/
├── sfs_processor.py          # Huvudskript och entry point
├── downloaders/               # Hämta data från externa källor
│   ├── download_sfs_docs.py  # Ladda ner SFS-dokument
│   ├── fetch_new_sfs_docs.py # Hämta nya dokument (scheduled)
│   └── download_from_gov_api.py # Direkt API-integration
├── formatters/                # Konvertera data till olika format
│   ├── format_sfs_text.py    # JSON → Markdown-konvertering
│   ├── apply_links.py        # Lägg till interna/externa länkar
│   ├── format_html.py        # Markdown → HTML
│   └── format_htmldiff.py    # Generera HTML-diff views
├── exporters/                 # Export till olika destinationer
│   ├── git/                  # Git repository export
│   │   ├── export_to_git.py
│   │   ├── git_utils.py
│   │   └── batch_export_to_git.py
│   └── html/                 # HTML export och upload
│       ├── export_to_html.py
│       ├── upload_to_r2.py
│       └── eli_utils.py
├── temporal/                  # Temporal hantering
│   ├── title_temporal.py     # Temporal titel-processing
│   ├── integrated_title_temporal.py
│   └── apply_temporal.py     # Tillämpa temporala regler
├── data/                      # Konfiguration och patterns
│   ├── document_patterns/    # Regex-patterns för parsing
│   └── test_docs/            # Test-dokument
├── test/                      # Tester
│   ├── test_title_temporal.py
│   ├── test_integrated_title_temporal.py
│   ├── test_predocs.py
│   └── test_linking.py
├── scripts/                   # Hjälpskript
└── .github/workflows/         # CI/CD workflows
```

## Moduler och deras ansvar

### `sfs_processor.py` (Huvudmodul)

**Ansvar**: Orkestrering av hela processen från input till output.

**Viktiga funktioner**:

- `process_sfs_document()`: Huvudfunktion som processar ett dokument
- `determine_output_path()`: Bestämmer output-sökväg baserat på beteckning
- `should_exclude_file()`: Filtrering baserat på konfiguration

**Workflow**:

1. Läs JSON-fil
2. Validera dokumentdata
3. Konvertera till Markdown
4. Applicera temporal processing
5. Exportera till valda format

### `downloaders/` (Nedladdning)

**`download_sfs_docs.py`**:
- Ladda ner specifika SFS-dokument från Regeringskansliets rättsdatabas
- Hantera paginering och rate limiting
- Cacha nedladdad data

**`fetch_new_sfs_docs.py`**:
- Schemalagd hämtning av nya dokument
- Används i GitHub Actions workflow
- Detekterar nya/ändrade dokument

### `formatters/` (Formatering)

**`format_sfs_text.py`**:
- Kärnan i Markdown-konverteringen
- Funktioner:
  - `convert_json_to_markdown()`: Huvudkonvertering
  - `format_stycke()`: Formatera paragrafstycken
  - `format_tabell()`: Hantera tabeller
  - `normalize_heading_levels()`: Normalisera rubriknivåer

**`apply_links.py`**:
- Lägg till interna länkar mellan lagar
- Externa länkar till EU-direktiv via EUR-Lex
- ELI (European Legislation Identifier) URI:er

**`format_html.py`**:
- Konvertera Markdown till HTML med Python Markdown-biblioteket
- Lägg till CSS och navigation
- Hantera YAML frontmatter

### `exporters/` (Export)

**`git/`**:
- Exportera till Git-repository med commits per författning
- Hantera branches för olika tidpunkter
- GitHub integration via Personal Access Token

**`html/`**:
- Generera HTML-filer
- Ladda upp till Cloudflare R2 (S3-kompatibel storage)
- ELI URI-hantering för permalänkar

### `temporal/` (Temporal Processing)

**Temporal hantering** hanterar att lagtext förändras över tid:

**`title_temporal.py`**:
- Extrahera temporal information från titlar
- Patterns för "upphör att gälla", "träder i kraft"
- Regex-baserad parsing av datum och referenser

**`apply_temporal.py`**:
- Applicera temporala regler på dokument
- Filtrera innehåll baserat på target_date
- Hantera `selex:...` attribut för temporal information

**Exempel på temporal attribut**:
```markdown
<section selex:ikraft_datum="2024-01-01" selex:upphor_datum="2024-12-31">
Denna text gäller från 2024-01-01 till 2024-12-31
</section>

<section selex:status="upphavd" selex:upphavd="true">
Denna text är upphävd
</section>
```

## Arbetsflöde för utveckling

### Lägga till ny funktionalitet

1. **Planera**: Diskutera i ett GitHub Issue först
2. **Branching**: Skapa feature branch
3. **Implementera**: Skriv kod + tester
4. **Testa**: Kör alla tester lokalt
5. **Dokumentera**: Uppdatera README/DEVELOPMENT.md
6. **PR**: Öppna Pull Request med beskrivning

### Lägga till nytt output-format

Om du vill lägga till support för ett nytt format (t.ex. PDF):

1. **Skapa formatter**: `formatters/format_pdf.py`
2. **Implementera konvertering**: Funktion som tar Markdown → PDF
3. **Lägg till i main**: Uppdatera `sfs_processor.py` för att hantera `--output pdf`
4. **Tester**: Lägg till test i `test/test_pdf.py`
5. **Dokumentation**: Uppdatera README.md

### Lägga till ny datakälla

För att integrera en ny källa (t.ex. annan myndighet):

1. **Skapa downloader**: `downloaders/download_<källa>.py`
2. **Mappa till JSON**: Konvertera till samma JSON-schema som Riksdagen
3. **Testa**: Verifiera att befintliga formatters fungerar
4. **Dokumentera**: Uppdatera dokumentation

## Debugging

### Verbose mode

Använd `--verbose` för detaljerad loggning:
```bash
python sfs_processor.py input.json --output md --verbose
```

### Temporala problem

Om temporal processing ger oväntat resultat:

1. Kontrollera YAML frontmatter i output
2. Kör utan temporal: `--preserve-selex-tags`
3. Testa med specifikt datum: `--target-date 2024-01-01`

### Git export-problem

Om Git-export inte fungerar:

1. Verifiera `GIT_GITHUB_PAT` är satt
2. Kontrollera behörigheter på target repository
3. Kör med `--verbose` för detaljerad logg
4. Testa GitHub-anslutning: `git ls-remote <repo-url>`

## Testing

### Testfilosofi

- **Unit tests**: Testa enskilda funktioner isolerat
- **Integration tests**: Testa fullständigt dataflöde
- **Fixture data**: Använd riktiga (men små) SFS-dokument

### Skriva tester

Exempel på test:

```python
def test_parse_beteckning():
    """Test parsing av SFS-beteckning."""
    from formatters.format_sfs_text import parse_beteckning

    result = parse_beteckning("SFS 2023:123")
    assert result["year"] == 2023
    assert result["number"] == 123
```

### Test coverage

Kör tester med coverage:
```bash
pip install pytest-cov
python -m pytest test/ --cov=. --cov-report=html
```

## CI/CD Workflows

### `.github/workflows/`

**`testdocs-workflow.yml`**:
- Triggas på varje push/PR
- Processar test-dokument
- Verifierar att processing fungerar

**`fetch-sfs-workflow.yml`**:
- Schemalagd (nightly)
- Hämtar nya SFS-dokument
- Skapar branch med ändringar
- Triggar HTML-export

**`html-export-workflow.yml`**:
- Genererar HTML från Markdown
- Laddar upp till Cloudflare R2
- Kräver R2-credentials i GitHub Secrets

**`upcoming-changes-workflow.yml`**:
- Processar kommande ändringar
- Temporal förhandsvisning

## Kodkonventioner

### Allmänna riktlinjer

Projektet följer **PEP 8-standarden** för Python-kod:

- **Indentering**: 4 mellanslag (inga tabs)
- **Radlängd**: Max 100 tecken (flexibelt för långa strängar)
- **Variabelnamn**: Använd beskrivande namn (`document_data` istället för `dd`)
- **Svenska termer**: OK för domänspecifika begrepp (t.ex. `beteckning`, `författning`, `paragraf`)
- **Kommentarer**: Kommentera komplex logik, inte uppenbar kod
- **Docstrings**: Alla publika funktioner måste ha docstrings som beskriver:
  - Vad funktionen gör
  - Parametrar och deras typer
  - Returvärde
  - Eventuella exceptions som kastas

### Namngivning

- **Filer**: snake_case (t.ex. `format_sfs_text.py`)
- **Funktioner**: snake_case (t.ex. `convert_json_to_markdown()`)
- **Klasser**: PascalCase (t.ex. `SFSDocument`)
- **Konstanter**: UPPER_CASE (t.ex. `DEFAULT_DATE`)

### Imports

Gruppera imports:
```python
# Standard library
import os
import json
from typing import Dict, List

# Third-party
import requests
import yaml

# Local imports
from formatters.format_sfs_text import convert_json_to_markdown
```

### Error handling

```python
try:
    result = risky_operation()
except ValueError as e:
    print(f"Fel vid operation: {e}")
    return None
except Exception as e:
    print(f"Oväntat fel: {e}")
    raise
```

## Vanliga problem och lösningar

### Problem: Git push misslyckas

**Orsak**: Token saknar rätt behörigheter

**Lösning**: Verifiera att `GIT_GITHUB_PAT` har `repo`-scope

### Problem: Temporal processing tar bort allt innehåll

**Orsak**: `target_date` är före dokumentets ikraftträdande

**Lösning**: Kontrollera `target_date` och jämför med `ikraft_datum` i YAML frontmatter

## Säkerhet

### Secrets management

- Använd **miljövariabler** för alla credentials
- **Aldrig** committa `.env`-filer
- GitHub Secrets för CI/CD

### API rate limiting

- Regeringskansliet rättsdatabas & Riksdagens API: Respektera rate limits
- Implementera exponential backoff vid 429-svar
- Cacha data lokalt när möjligt

## Resurser

### Externa APIer

- [Riksdagens öppna data](https://data.riksdagen.se)
- [Regieringskansliets rättsdatabas](https://beta.rkrattsbaser.gov.se)
- [EUR-Lex](https://eur-lex.europa.eu)

### Dokumentation

- [Markdown spec](https://commonmark.org)
- [Python Markdown](https://python-markdown.github.io)
- [ELI standard](https://eur-lex.europa.eu/eli-register/about.html)

## Support

Vid frågor eller problem:

1. Kolla [README.md](README.md) för grundläggande användning
2. Läs [CONTRIBUTING.md](CONTRIBUTING.md) för bidragsriktlinjer
3. Sök i [GitHub Issues](https://github.com/yourusername/sfs-processor/issues)
4. Öppna ett nytt issue om problemet kvarstår

