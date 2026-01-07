# ADR-002: Import från Regeringskansliet istället för PDF-crawling

## Status

Accepterad

## Kontext och problembeskrivning

För att konvertera SFS-författningar till olika format behövde vi en källdatakälla. Det finns två huvudsakliga alternativ för att få tillgång till författningstexter:

1. **PDF-crawling**: Ladda ner publicerade PDF:er från olika källor och extrahera text
2. **Strukturerad data-import**: Använda API:er som tillhandahåller strukturerad data (JSON/XML)

Utmaningarna med PDF-crawling:

- Text extraction från PDF är opålitlig (tabeller, fotnoter, formatering går förlorad)
- Ingen semantisk struktur (kapitel, paragrafer, rubriker måste detekteras heuristiskt)
- Temporal metadata (ikraftträdandedatum, upphävanden) finns inte i PDF:en
- OCR-fel vid scannade dokument
- Layout-beroende parsing (när PDF-layouten ändras, bryts parsern)

Alternativen för strukturerad data:

- **Riksdagens API** (`data.riksdagen.se`) - XML-format, fokus på riksdagsarbete
- **Regeringskansliets rättsdatabas** (`beta.rkrattsbaser.gov.se`) - JSON via Elasticsearch API

## Beslut

Vi använder **Regeringskansliets Elasticsearch API** (`beta.rkrattsbaser.gov.se`) som primär källdatakälla för SFS-författningar.

### API-detaljer

- **Endpoint**: `https://beta.rkrattsbaser.gov.se/elasticsearch/SearchEsByRawJson`
- **Format**: JSON via Elasticsearch queries
- **Innehåll**: Fullständig författningstext med strukturerad metadata
- **Metadataexempel**:
  - Beteckning (`2024:100`)
  - Departement
  - Ikraftträdandedatum
  - Ändringshistorik
  - Rubrikstruktur (avdelningar, kapitel, paragrafer)

## Konsekvenser

### Positiva

- **Strukturerad data**: JSON med tydlig hierarki (avdelningar → kapitel → paragrafer)
- **Rik metadata**: Departement, datum, ändringshistorik inkluderad
- **Tillförlitlighet**: Officiell källa från Regeringskansliet
- **Automatisering**: Enkel att hämta via HTTP POST requests
- **Versionshantering**: Ändringsförfattningar och ursprungsdokument finns
- **Undviker PDF-problem**: Ingen text extraction, ingen OCR, ingen layout-parsing
- **Temporal data**: Ikraftträdande och upphävanden finns i metadata
- **Konsistent format**: Alla författningar i samma JSON-schema

### Negativa

- **Beta-status**: API:et är markerat som "beta", kan förändras
  - Mitigering: Versionshantering av downloader-skript, tester för att upptäcka breaking changes
- **Ingen SLA**: Inget officiellt servicenivåavtal eller versionsstöd
  - Mitigering: Lokalt cachning av nedladdad JSON i `data/sfs_json/`
- **Proprietärt API**: Regeringskansliets eget format, inte en öppen standard
  - Mitigering: Abstraktionslager i `downloaders/` gör byte av källa möjligt
- **Nätverksberoende**: Kräver internetanslutning för initial hämtning
  - Mitigering: Offline-körning möjlig med lokalt cachad data

### Tekniska konsekvenser

- **Downloader-arkitektur**: Implementationen i `downloaders/rkrattsbaser_api.py` abstraherar API-anrop
- **Fallback**: `downloaders/riksdagen_api.py` finns som backup-källa vid behov
- **Caching-strategi**: JSON sparas lokalt för att undvika upprepade API-anrop
- **Rate limiting**: Implementerad delay mellan requests för att respektera servern

## Alternativ som övervägdes

### 1. PDF-crawling från Regeringskansliets webbplats

**Varför inte valt**:

- Opålitlig text extraction
- Ingen strukturerad metadata
- Kräver komplex layout-parsing
- Temporal information måste extraheras heuristiskt från text
- Högre underhållskostnad när PDF-format ändras

### 2. Riksdagens API (data.riksdagen.se)

```xml
<dokument>
  <beteckning>2024:100</beteckning>
  <text>...</text>
</dokument>
```

**Fördelar**:

- Officiellt API med stabil uptime
- XML-format

**Varför inte valt**:

- Fokus på riksdagsarbete, inte konsoliderade författningar
- Mindre detaljerad metadata för författningar
- XML-parsing mer komplext än JSON
- Regeringskansliets data är mer författningsfokuserad

**Notering**: Vi behåller `riksdagen_api.py` som fallback-källa

### 3. Scraping från [svenskforfattningssamling.se](https://svenskforfattningssamling.se/)

**Varför inte valt**:

- Lagrummet.se aggregerar data från andra källor (sekundärkälla)
- Inget officiellt API
- Scraping kan bryta när webbplatsen uppdateras

## Relaterade beslut

- [ADR-004](004-semantiska-temporal-taggar.md) - Temporal metadata kommer från Regeringskansliets API

## Noteringar

- **Implementationer**:
  - `downloaders/rkrattsbaser_api.py` - Primär implementation
  - `downloaders/riksdagen_api.py` - Backup-källa
  - `downloaders/download_sfs_docs.py` - CLI för att hämta författningar

- **Användning**:

  ```bash
  # Hämta specifik författning
  python downloaders/download_sfs_docs.py --ids "2024:100" --source rkrattsbaser

  # Hämta alla författningar
  python downloaders/download_sfs_docs.py --ids all --source rkrattsbaser
  ```

- **Caching**: Nedladdad JSON sparas i `data/sfs_json/` för offline-användning

- **Rate limiting**: Implementerad 1-sekunds delay mellan requests för att respektera servern

- **Framtidsutsikter**: Om API:et tas bort eller ändras drastiskt kan vi falla tillbaka på Riksdagens API eller implementera en hybrid-lösning
