# ADR-004: Semantiskt val av taggar för temporal data

## Status

Accepterad

## Kontext och problembeskrivning

Författningar i SFS förändras över tid - paragrafer träder i kraft vid olika datum, upphävs, eller ändras. För att korrekt kunna:

- Visa hur en författning såg ut vid ett specifikt datum
- Filtrera bort upphävda bestämmelser
- Hantera ikraftträdanderegler
- Skapa historiska versioner i Git
- Generera semantiska vektorembeddings för endast gällande regelverk

...behövde vi ett semantiskt system för att märka upp temporal information i Markdown-filerna.

Utmaningarna var:

1. **Bevara temporal metadata** genom hela processing-kedjan (JSON → Markdown → HTML/Git/Vector)
2. **Standardkompatibilitet**: Markdown ska vara läsbart både för människor och maskiner
3. **Filtreringslogik**: Enkelt att identifiera och filtrera baserat på datum
4. **Namnrymd**: Undvika kollisioner med standard HTML-attribut
5. **Juridisk precision**: Fånga skillnaden mellan "upphävd", "ännu ej ikraftträdd", och "gällande"

## Beslut

Vi använder **custom HTML-attribut med `selex:`-prefix** för temporal metadata i Markdown-filer.

### Attributschema

```html
<section class="paragraf" selex:status="ikraft" selex:ikraft_datum="2025-01-01">
#### 1 §
...
</section>

<section class="kapitel" selex:status="upphavd" selex:upphor_datum="2023-12-31">
### Upphävda bestämmelser
...
</section>

<section class="paragraf" selex:status="ikraft" selex:ikraft_villkor="den dag regeringen bestämmer">
#### 5 §
...
</section>
```

### Attributdefinitioner

| Attribut | Typ | Beskrivning | Exempel |
|----------|-----|-------------|---------|
| `selex:status` | Enum | Juridisk status: `ikraft`, `upphavd`, `upphord` | `selex:status="ikraft"` |
| `selex:ikraft_datum` | Date (ISO 8601) | Datum då sektionen träder i kraft | `selex:ikraft_datum="2025-01-01"` |
| `selex:upphor_datum` | Date (ISO 8601) | Datum då sektionen upphör att gälla | `selex:upphor_datum="2023-12-31"` |
| `selex:ikraft_villkor` | String | Villkor för ikraftträdande (vid avsaknad av exakt datum) | `selex:ikraft_villkor="den dag regeringen bestämmer"` |

### Filtreringslogik

`temporal/apply_temporal.py` implementerar följande regler för ett givet `target_date`:

1. Sektioner med `selex:status="upphavd"` eller `"upphord"` → **tas bort helt**
2. Sektioner med `selex:upphor_datum <= target_date` → **tas bort helt**
3. Sektioner med `selex:ikraft_datum > target_date` → **tas bort helt** (ej ikraftträtt ännu)
4. Sektioner med `selex:ikraft_datum <= target_date` → **behålls, temporal attribut tas bort**
5. Nestlade sektioner: Om överordnad sektion tas bort → alla underordnade tas också bort

## Konsekvenser

### Positiva

- **Bevarad semantik**: Temporal metadata följer med genom hela kedjan
- **Enkel parsing**: Standard regex kan extrahera `selex:*` attribut
- **Markdown-kompatibilitet**: Filerna är fortfarande läsbara Markdown (HTML i Markdown är standard)
- **Namnrymdsseparation**: `selex:`-prefix undviker kollisioner med andra attribut
- **Precision**: Distinkt hantering av olika temporala tillstånd
- **Testbarhet**: Lätt att verifiera filtreringslogik med unit tests
- **ISO 8601-datum**: Standardiserat datumformat (`YYYY-MM-DD`) som är sorterbara och internationellt vedertagna

### Negativa

- **Custom schema**: Inte en etablerad standard som TEI eller Akoma Ntoso
  - Mitigering: Dokumenterat schema, möjligt att konvertera till andra format senare
- **Markdown rendering**: Vissa Markdown-renderare visar attributen synligt
  - Mitigering: I `md`-format rensas attributen bort, `md-markers` är för vidare bearbetning
- **Manuell synk**: Attributen måste hållas konsistenta med källdata (JSON från Regeringskansliet)
  - Mitigering: Automatisk generering från JSON i `formatters/format_sfs_text.py`

### Teknisk skuld

- **Framtida standardisering**: Om juridisk XML-standard blir vedertagen (TEI, Akoma Ntoso) kan migration behövas
- **Valideringsschema**: Inget formellt XML-schema för `selex:`-attributen ännu
  - Åtgärd: Överväg JSON Schema eller XML Schema för validering i framtiden

## Alternativ som övervägdes

### 1. YAML frontmatter per sektion

```markdown
---
status: ikraft
ikraft_datum: 2025-01-01
---
#### 1 §
...
```

**Varför inte valt**:

- Frontmatter är per-fil, inte per-sektion
- Svårare att parsa med regex
- Bryter Markdown-flödet

### 2. Kommentarbaserad metadata

```markdown
<!-- temporal: status=ikraft, ikraft_datum=2025-01-01 -->
#### 1 §
...
```

**Varför inte valt**:

- Osynlig i vissa renderare (svårare att debugga)
- Ingen semantisk koppling mellan kommentar och innehåll
- Svårare att matcha sektion till metadata

### 3. Standard HTML data-attribut

```html
<section data-status="ikraft" data-ikraft-datum="2025-01-01">
```

**Varför inte valt**:

- `data-*` attribut är för custom application data, inte domain-specifik semantik
- Vi ville tydligt signalera att detta är Selex-specifik metadata

### 4. TEI (Text Encoding Initiative) XML

```xml
<div type="paragraph" ana="#inforce" notBefore="2025-01-01">
```

**Varför inte valt**:

- Mycket tungt för vårt användningsfall
- Kräver komplett XML-struktur, inte kompatibelt med Markdown
- Högre inlärningströskel

## Relaterade beslut

- [ADR-002](002-import-fran-regeringskansliet.md) - Källdata för temporal information

## Noteringar

- Implementationen finns i:
  - `temporal/apply_temporal.py` - Filtreringslogik
  - `formatters/format_sfs_text.py` - Generering av attribut från JSON
  - `temporal/title_temporal.py` - Temporal bearbetning av titlar
- Testad med 100+ författningar från SFS
- Datumsystemet hanterar både absoluta datum (ISO 8601) och villkor (text)
