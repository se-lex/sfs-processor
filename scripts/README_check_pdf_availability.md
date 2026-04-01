# PDF Tillgänglighets-kontroll

Script för att kontrollera tillgänglighet av PDF-filer från markdown-filer med `pdf_url` i frontmatter.

## Beskrivning

Scriptet `check_pdf_availability.py` gör följande:

1. Söker igenom en katalog med markdown-filer
2. Extraherar `pdf_url` från frontmatter i varje fil
3. Kontrollerar om varje PDF är tillgänglig via HTTP HEAD request
4. Genererar en detaljerad Markdown-rapport med resultat

## Användning

### Grundläggande användning

```bash
python3 scripts/check_pdf_availability.py <katalog> [alternativ]
```

### Exempel

#### Kontrollera alla filer i sfs-export-md-markers

```bash
python3 scripts/check_pdf_availability.py ../sfs-export-md-markers
```

Detta skapar rapporten i `reports/pdf_availability_report.md` (standardplats).

#### Specificera output-fil

```bash
python3 scripts/check_pdf_availability.py ../sfs-export-md-markers -o reports/min_rapport.md
```

#### Sök endast i toppnivå (inte rekursivt)

```bash
python3 scripts/check_pdf_availability.py ../sfs-export-md-markers --no-recursive
```

## Alternativ

- `directory` (krävs): Katalog som innehåller markdown-filerna
- `-o`, `--output`: Output-fil för rapporten (default: `reports/pdf_availability_report.md`)
- `--no-recursive`: Sök inte rekursivt i undermappar

## Vad rapporten innehåller

Rapporten inkluderar:

### 1. Sammanfattning
- Totalt antal markdown-filer bearbetade
- Antal filer med `pdf_url`
- Antal tillgängliga PDF:er (med procent)
- Antal otillgängliga PDF:er (med procent)

### 2. Fördelning per databas
- Gamla databasen (rkrattsdb.gov.se)
- Nya databasen (svenskforfattningssamling.se)

### 3. Status code-fördelning
- HTTP status codes (200, 404, etc.)
- Felmeddelanden (Timeout, Connection Error, etc.)

### 4. Detaljerade listor

#### Otillgängliga PDF:er
Grupperat per databas, med:
- Beteckning (t.ex. "2024:123")
- Rubrik (förkortad)
- Status code eller felmeddelande
- Fullständig URL

#### Tillgängliga PDF:er (urval)
De första 10 tillgängliga PDF:erna för verifiering.

## Prestanda

### Bearbetningstid
- **~11 000 filer**: Ca 30-60 minuter (beroende på nätverkshastighet)
- Scriptet gör en HTTP HEAD request per PDF-URL
- Timeout: 10 sekunder per request

### Tips för snabbare körning
Om du vill testa scriptet först på ett mindre dataset:

```bash
# Skapa en testkatalog med bara 100 filer
mkdir -p test_sample
find ../sfs-export-md-markers -name "*.md" | head -100 | xargs -I {} cp {} test_sample/

# Kör scriptet på testdatasetet
python3 scripts/check_pdf_availability.py test_sample -o reports/test_rapport.md
```

## Exempel på rapport-output

```markdown
# PDF-tillgänglighetsrapport

Genererad: 2025-12-30 17:30:00

## Sammanfattning

- **Totalt antal markdown-filer:** 10913
- **Filer med pdf_url:** 8542
- **Tillgängliga PDF:er:** 7823 (91.6%)
- **Otillgängliga PDF:er:** 719 (8.4%)

## Fördelning per databas

- **Gamla databasen (rkrattsdb.gov.se):** 3421
- **Nya databasen (svenskforfattningssamling.se):** 5121

## Status code-fördelning

- **200:** 7823
- **404:** 651
- **Timeout:** 45
- **Connection Error:** 23
```

## Felsökning

### Problem: "Katalogen finns inte"
- Kontrollera att sökvägen till katalogen är korrekt
- Använd relativ eller absolut sökväg

### Problem: "Inga markdown-filer hittades"
- Kontrollera att katalogen innehåller `.md`-filer
- Använd `--no-recursive` om filerna ligger i toppnivå

### Problem: "Connection Error" för många PDF:er
- Kontrollera din internetanslutning
- Servern kan vara tillfälligt nere
- För många requests kan ha utlöst rate limiting

### Problem: Scriptet tar för lång tid
- Detta är normalt för stora dataset (11 000+ filer)
- Testa först på ett mindre dataset (se "Tips för snabbare körning" ovan)
- Kör scriptet i bakgrunden:
  ```bash
  nohup python3 scripts/check_pdf_availability.py ../sfs-export-md-markers > check_pdf.log 2>&1 &
  ```

## Tekniska detaljer

### HTTP HEAD Request
Scriptet använder HTTP HEAD istället för GET för att:
- Minimera bandbredd (hämtar inte hela filen)
- Snabbare kontroll (endast headers)
- Mindre belastning på servern

### Timeout
- Standard timeout: 10 sekunder per request
- Justeras i `check_pdf_exists()` funktionen om behov finns

### Databas-identifiering
Scriptet identifierar vilken databas baserat på domänen i URL:en:
- `rkrattsdb.gov.se` = Gamla databasen (1998:306 - 2018:159)
- `svenskforfattningssamling.se` = Nya databasen (2018:160 - )

## Relaterade script

- `formatters/add_pdf_url_to_frontmatter.py`: Lägger till `pdf_url` i frontmatter
- `formatters/sort_frontmatter.py`: Sorterar frontmatter properties

## Support

Vid problem eller frågor, kontrollera:
1. Att alla dependencies är installerade (`pip install -r requirements.txt`)
2. Att du har internetanslutning
3. Att sökvägen till katalogen är korrekt
