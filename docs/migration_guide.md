# Migration Guide - Övergång till ny projektstruktur

## Bakgrund

Detta dokument beskriver hur du kan migrera från den nuvarande filen-baserade strukturen till en mer professionell paketstruktur.

## Steg för migration

### 1. Installera paketet i utvecklingsläge

```bash
# Från projektets rotmapp
pip install -e .

# Eller med utvecklingsberoenden
pip install -e ".[dev]"
```

### 2. Flytta existerande kod

#### Kärn-funktionalitet
```bash
# Flytta huvudfiler till nya platser
mv sfs_processor.py src/sfs_md/core/processor.py
mv format_sfs_text.py src/sfs_md/core/formatter.py

# Flytta utilities
mv sort_frontmatter.py src/sfs_md/utils/frontmatter.py
mv add_pdf_url_to_frontmatter.py src/sfs_md/utils/pdf.py
```

#### Nedladdare
```bash
mv download_sfs_docs.py src/sfs_md/downloaders/main.py
mv fetch_new_sfs_docs.py src/sfs_md/downloaders/updater.py
```

#### Exporters
```bash
mv html_export.py src/sfs_md/exporters/html.py
mv populate_index_pages.py src/sfs_md/exporters/index.py
```

### 3. Uppdatera imports

I varje flyttad fil, uppdatera imports för att matcha nya struktur:

```python
# Gamla imports
from format_sfs_text import format_sfs_text_as_markdown

# Nya imports  
from sfs_md.core.formatter import format_sfs_text_as_markdown
```

### 4. Testa nya CLI-kommandon

```bash
# Istället för: python download_sfs_docs.py --ids "2025:123"
sfs-download --ids "2025:123"

# Istället för: python sfs_processor.py --input json --output markdown  
sfs-process --input json --output markdown
```

### 5. Kör tester

```bash
# Kör alla tester
pytest

# Med coverage
pytest --cov=src/sfs_md

# Kör specifik test
pytest tests/test_basic.py -v
```

### 6. Kodkvalitet

```bash
# Formatera kod
black src/ tests/

# Sortera imports
isort src/ tests/

# Linting
flake8 src/ tests/

# Type checking
mypy src/
```

## Fördelar efter migration

### Pakethantering
- ✅ Enkel installation med `pip install -e .`
- ✅ Versionhantering med setup.py
- ✅ Entry points för CLI-kommandon

### Utveckling
- ✅ Modulär kod-organisation
- ✅ Enhetestester med pytest
- ✅ Automatisk kodformatering
- ✅ Type hints och mypy-kontroller

### Distribution
- ✅ Kan byggas som Python wheel
- ✅ Kan publiceras på PyPI
- ✅ Enkel installation för andra användare

## Behålla backward compatibility

Under migration kan du behålla de gamla script-filerna och låta dem importera från nya strukturen:

```python
# download_sfs_docs.py (legacy wrapper)
#!/usr/bin/env python3
"""Legacy wrapper - använd 'sfs-download' istället."""

import sys
from sfs_md.cli.download import main

if __name__ == "__main__":
    print("⚠️  Denna fil är föråldrad. Använd 'sfs-download' istället.")
    main()
```
