# ADR-001: Markdown som mellanformat

## Status

Accepterad

## Kontext och problembeskrivning

För att konvertera SFS-författningar från källdata (JSON) till olika output-format (HTML, Git, vektorembeddings) behövde vi välja en arkitektur för dataflödet.

Huvudalternativen var:

1. **Direkt konvertering**: JSON → HTML, JSON → Git, JSON → Vector (separata pipelines)
2. **Mellanformat**: JSON → [Mellanformat] → (HTML/Git/Vector/etc)

Utmaningarna var:

- **Code duplication**: Varje exporter skulle behöva implementera samma parsing-logik
- **Konsistens**: Hur garantera att HTML-versionen och Git-versionen är identiska?
- **Mänsklig läsbarhet**: Utvecklare och bidragsgivare måste kunna granska output
- **Versionskontroll**: Ska mellan-representationen kunna versionshanteras?
- **Temporal processing**: Var i kedjan ska temporal filtrering appliceras?
- **Underhållbarhet**: Ändringar i parsing-logik ska inte kräva uppdateringar i alla exporters

## Beslut

Vi använder **Markdown med HTML-taggar** som mellanformat mellan JSON-källdata och alla output-format.

### Arkitektur

```
JSON (Regeringskansliet)
    ↓
[format_sfs_text_as_markdown]
    ↓
Markdown med <section>-taggar och selex:-attribut
    ↓
├─→ [apply_temporal] → Markdown (rent) → HTML
├─→ [apply_temporal] → Markdown (rent) → Git commits
├─→ [apply_temporal] → Markdown (rent) → Vector embeddings
└─→ Markdown (med taggar) → Publiceras som md-markers
```

### Varför Markdown?

**Mänsklig läsbarhet**:
```markdown
## 1 kap. Inledande bestämmelser

### 1 §
Denna författning gäller för...
```

**Semantisk struktur** (behålls via HTML i Markdown):
```html
<section class="kapitel" selex:ikraft_datum="2025-01-01">
## 1 kap. Inledande bestämmelser
...
</section>
```

**Versionskontroll**:
- Markdown är text-baserat → perfekt för Git diff
- Granskare kan läsa ändringar direkt på GitHub
- Merge conflicts är läsbara och lösbara

### Implementation

**Steg 1: JSON → Markdown** (`formatters/format_sfs_text.py`)
- Konverterar JSON-strukturen till Markdown-rubriker
- Lägger till `<section>`-taggar med CSS-klasser
- Extraherar och annoterar temporal metadata som `selex:`-attribut

**Steg 2: Markdown → Output-format**
- **HTML**: `markdown.markdown()` + custom extensions → HTML
- **Git**: Temporal filtrering + commit med markdown-filer
- **Vector**: Temporal filtrering + chunking + embedding
- **md-markers**: Ingen transformation (publiceras som är)

## Konsekvenser

### Positiva

- **Single source of truth**: All parsing-logik finns på ett ställe (`format_sfs_text.py`)
- **Konsistens**: Alla output-format utgår från samma Markdown-representation
- **Granskning**: Pull requests visar Markdown-diff som är läsbar för människor
- **Flexibilitet**: Lätt att lägga till nya output-format
  - Vill du ha PDF? Konvertera Markdown → PDF med pandoc
  - Vill du ha EPUB? Markdown → EPUB med tooling
- **Standard tooling**: Markdown har enormt ekosystem (parsers, linters, previewers)
- **Hybrid format**: HTML-i-Markdown ger både läsbarhet och semantik
- **Debug-vänligt**: Kan inspektera Markdown-filer manuellt vid problem
- **Cacheable**: Markdown-filer kan sparas och återanvändas
- **Testbarhet**: Enkelt att skriva tester mot Markdown-output

### Negativa

- **Extra konverteringssteg**: JSON → Markdown → HTML tar mer tid än direkt JSON → HTML
  - Mitigering: Prestandan är acceptabel, och flexibiliteten väger tyngre

- **HTML-i-Markdown komplexitet**: Inte alla Markdown-renderare hanterar HTML perfekt
  - Mitigering: Vi använder beprövade bibliotek (`markdown` för Python)

- **Temporal metadata i HTML-attribut**: Okonventionellt för Markdown
  - Mitigering: Dokumenterat i ADR-004, fungerar i praktiken

- **Två Markdown-varianter**: `md-markers` (med taggar) vs `md` (rent)
  - Mitigering: Tydlig separation, olika användningsfall

### Tekniska konsekvenser

- **Format-specificering**: `--formats md-markers` vs `--formats md`
  - `md-markers`: Bevarar all metadata, för vidare processing
  - `md`: Rendad version efter temporal filtrering

- **Temporal processing**: Sker EFTER Markdown-generering
  - Markdown → `apply_temporal(target_date)` → Rendad Markdown

- **Lazy evaluation**: Temporal filtrering kan postponas till senare
  - `md-markers` sparar alla möjligheter öppna

## Alternativ som övervägdes

### 1. Direkt JSON → HTML/Git/Vector

**Fördelar**:
- Snabbare (färre steg)
- Enklare arkitektur

**Varför inte valt**:
- Code duplication: Varje exporter måste parsa JSON
- Konsistensproblem: Olika exporters kan tolka JSON olika
- Ingen human-readable mellanrepresentation
- Svårt att granska output (JSON är inte läsbart som Markdown)

### 2. XML som mellanformat (TEI eller custom)

```xml
<law id="2024:100">
  <chapter number="1">
    <heading>Inledande bestämmelser</heading>
    <paragraph number="1">
      <text>Denna författning gäller...</text>
    </paragraph>
  </chapter>
</law>
```

**Fördelar**:
- Strikt struktur med validering
- Etablerad standard (TEI) inom juridisk text

**Varför inte valt**:
- Mindre läsbart för människor
- Högre inlärningströskel
- Mindre ekosystem än Markdown
- Svårare att granska i pull requests
- Overkill för vårt användningsfall

### 3. JSON som mellanformat (normaliserad struktur)

**Varför inte valt**:
- Inte mänskligt läsbart
- Svårt att versionskontrollera (JSON diff är svårläst)
- Inget naturligt sätt att representera flytande text med rubriker

### 4. AST (Abstract Syntax Tree)

```python
{
  "type": "document",
  "children": [
    {"type": "chapter", "number": "1", "heading": "..."},
    {"type": "paragraph", "number": "1", "content": "..."}
  ]
}
```

**Varför inte valt**:
- Rent programmatiskt format, inte läsbart
- Måste serialiseras för att inspekteras
- Ingen standard representation
- Kan inte versionskontrolleras meningsfullt

## Relaterade beslut

- [ADR-004](004-semantiska-temporal-taggar.md) - Selex-attribut i Markdown
- [ADR-003](003-git-commits-historiska-datum.md) - Markdown-filer committas till Git

## Noteringar

- **Implementationer**:
  - `formatters/format_sfs_text.py` - JSON → Markdown konvertering
  - `formatters/frontmatter_manager.py` - YAML frontmatter i Markdown
  - `temporal/apply_temporal.py` - Temporal filtrering av Markdown
  - `exporters/html/html_export.py` - Markdown → HTML med `markdown.markdown()`
  - `exporters/vector/chunking.py` - Markdown → Chunks för embeddings

- **Markdown flavor**: CommonMark-kompatibel med HTML-extension
  - Rubriker: Standard Markdown (`##`, `###`, `####`)
  - Paragrafer: Standard Markdown (dubbla radbrytningar)
  - Semantik: HTML `<section>` och `<article>` taggar
  - Links: Standard Markdown-länkar + auto-linking

- **Frontmatter**: YAML frontmatter för metadata
  ```yaml
  ---
  beteckning: "2024:100"
  rubrik: "Författning om exempel"
  ikraft_datum: "2025-01-01"
  ---
  ```

- **Fördelar med två varianter**:
  - **md-markers**: För vidare processing, AI-analys, temporal queries
  - **md**: För publicering, läsning, GitHub Pages

- **Future-proof**: Om nya output-format behövs (PDF, DOCX, LaTeX):
  - Använd befintlig Markdown → Konvertera med standard tooling
  - Ingen ändring i core parsing-logik behövs

- **Exempel på Markdown-ekosystem som vi drar nytta av**:
  - `python-markdown`: Markdown → HTML konvertering
  - GitHub/GitLab: Automatisk rendering av `.md` filer
  - Markdown linters: Kvalitetskontroll av output
  - Markdown previewers: Live-förhandsvisning under utveckling
  - Pandoc: Potentiell framtida konvertering till andra format
