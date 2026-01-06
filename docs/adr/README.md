# Architecture Decision Records (ADR)

Denna katalog innehåller Architecture Decision Records (ADR) för sfs-processor projektet.

## Vad är ADR?

Architecture Decision Records är dokument som fångar viktiga arkitektoniska beslut som fattats under projektets utveckling, tillsammans med kontexten och konsekvenserna av dessa beslut.

## Format

Vi använder [MADR](https://adr.github.io/madr/) (Markdown Any Decision Records) som mall för våra ADR:er. Varje ADR följer denna struktur:

- **Titel**: Kort beskrivning av beslutet
- **Status**: Föreslagen, Accepterad, Avvisad, eller Föråldrad
- **Kontext**: Bakgrund och problemställning
- **Beslut**: Vad har vi bestämt
- **Konsekvenser**: Positiva och negativa effekter av beslutet

## Index över ADR:er

| ADR | Titel | Status |
|-----|-------|--------|
| [ADR-001](001-semantiska-temporal-taggar.md) | Semantiskt val av taggar för temporal data | Accepterad |
| [ADR-002](002-import-fran-regeringskansliet.md) | Import från Regeringskansliet istället för PDF-crawling | Accepterad |
| [ADR-003](003-git-commits-historiska-datum.md) | Git-commits med historiska datum för versionshistorik | Accepterad |
| [ADR-004](004-markdown-som-mellanformat.md) | Markdown som mellanformat | Accepterad |

## Skapa en ny ADR

När du fattar ett nytt viktigt arkitektoniskt beslut:

1. Skapa en ny fil med nästa nummer: `XXX-kort-beskrivning.md`
2. Använd MADR-mallen
3. Uppdatera index-tabellen ovan
4. Commit gärna filen tillsammans med koden som implementerar beslutet
