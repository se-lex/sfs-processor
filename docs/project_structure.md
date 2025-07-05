# Projektstruktur för SFS-MD

## Rekommenderad mapplayout

```
sfs-md/
├── src/sfs_md/              # Huvudkällkod (paketstruktur)
│   ├── __init__.py          # Paket init
│   ├── cli/                 # Kommandoradsgränssnitt
│   │   ├── __init__.py
│   │   ├── download.py      # sfs-download kommando
│   │   ├── process.py       # sfs-process kommando
│   │   └── fetch_new.py     # sfs-fetch-new kommando
│   ├── core/                # Kärnfunktionalitet
│   │   ├── __init__.py
│   │   ├── processor.py     # Huvudprocesser (från sfs_processor.py)
│   │   └── formatter.py     # Textformatering (från format_sfs_text.py)
│   ├── downloaders/         # Nedladdningsfunktioner
│   │   ├── __init__.py
│   │   ├── base.py          # Basklasser
│   │   ├── riksdagen.py     # Riksdagens API
│   │   └── rkrattsbaser.py  # Regeringskansliets API
│   ├── exporters/           # Export-funktioner
│   │   ├── __init__.py
│   │   ├── markdown.py      # Markdown export
│   │   ├── html.py          # HTML export (från html_export.py)
│   │   └── pdf.py           # PDF-relaterade funktioner
│   └── utils/               # Hjälpfunktioner
│       ├── __init__.py
│       ├── frontmatter.py   # YAML frontmatter hantering
│       ├── dates.py         # Datumhantering
│       └── text.py          # Textprocessering
├── tests/                   # Enhetstester
│   ├── conftest.py          # Test-konfiguration
│   ├── test_processor.py    # Tester för processor
│   ├── test_formatter.py    # Tester för formatter
│   └── test_downloaders.py  # Tester för nedladdare
├── docs/                    # Dokumentation
│   ├── usage.md             # Användningsguide
│   └── api.md               # API-dokumentation
├── scripts/                 # Legacy scripts och verktyg
│   ├── download_years.sh    # Flyttat från root
│   └── migration/           # Migreringsscript
├── examples/                # Exempel och demos
├── data/                    # Data-katalog
│   ├── sfs_docs/           # Nedladdade dokument
│   ├── json/               # JSON-filer
│   └── markdown/           # Konverterade markdown-filer
├── .github/                # GitHub Actions CI/CD
│   └── workflows/
│       └── tests.yml
├── setup.py                # Paketinstallation
├── pyproject.toml          # Projektkonfiguration
├── requirements.txt        # Produktionsberoenden
├── requirements-dev.txt    # Utvecklingsberoenden
├── README.md               # Huvuddokumentation
└── .gitignore             # Git ignore-regler
```

## Fördelar med denna struktur

### 1. **Paketstruktur (src/)**
- Klar separation mellan källkod och andra filer
- Möjliggör enkel installation med pip
- Förhindrar importproblem

### 2. **Modulär design**
- **cli/**: Alla kommandoradsgränssnitt samlat
- **core/**: Kärnlogik isolerad från I/O
- **downloaders/**: Tydlig separation av olika datakällor
- **exporters/**: Olika exportformat separerade
- **utils/**: Återanvändbar hjälpkod

### 3. **Testbarhet**
- Dedicated tests/-katalog
- Enkel att köra tester med pytest
- Test fixtures i conftest.py

### 4. **Utvecklarvänlig**
- Tydlig konfiguration i pyproject.toml
- Separata requirements för utveckling
- Linting och formattering konfigurerat

## Migration från nuvarande struktur

1. **Flytta nuvarande Python-filer till src/sfs_md/**
2. **Dela upp stora filer** i modulära komponenter
3. **Skapa CLI-wrappers** för befintliga script
4. **Lägg till tester** för kritisk funktionalitet
5. **Uppdatera imports** för att använda nya struktur

## CLI-användning efter migration

```bash
# Istället för: python download_sfs_docs.py
sfs-download --ids "2025:123,2025:456"

# Istället för: python sfs_processor.py
sfs-process --input json/ --output markdown/

# Istället för: python fetch_new_sfs_docs.py
sfs-fetch-new --days 7
```
