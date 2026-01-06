# sfs-processor - Conversion Tool for Swedish Code of Statutes

🇸🇪 [Byt till Svenska](README.md)

---

This repository contains Python scripts for converting SFS legislation (Swedish Code of Statutes / Svensk författningssamling) from JSON format to Markdown with temporal tags, HTML, Git, and other formats.

> [!NOTE]
> **This is part of [SE-Lex](https://github.com/se-lex)**, read more about [the project here](https://github.com/se-lex).
>
> SFS legislation is exported to [https://github.com/se-lex/sfs](https://github.com/se-lex/sfs) and also published as HTML at [https://selex.se](https://selex.se) with support for the EU's European Legislation Identifier (ELI) standard.

## Installation

1. Ensure you have Python 3.11 or later installed
2. Install required dependencies:

```bash
pip install -r requirements.txt
```

## Quick Start

Convert JSON files containing legislation to Markdown:

```bash
python sfs_processor.py --input sfs_json --output output/md --formats md-markers
```

## Output Formats

The tool can generate legislation in several different formats, depending on use case:

### Markdown Formats

- **`md-markers`** (default): Markdown with semantic `<section>` tags and selex attributes for legal status and temporal handling
- **`md`**: Clean Markdown files with normalized heading levels, suitable for display and reading. Uses a target-date (default: today's date) to show how the law appears at that point in time

### Git Format

- **`git`**: Exports legislation as Git commits with historical dates, creating a version history of the legislation

### HTML Formats

- **`html`**: Generates HTML files in ELI structure (`/eli/sfs/{year}/{number}/index.html`) for web publishing
- **`htmldiff`**: Like HTML but also includes separate versions for each amending law

### Vector Format (for semantic search)

- **`vector`**: Converts legislation to vector embeddings for semantic search and RAG applications. Uses OpenAI's text-embedding-3-large model (3072 dimensions) and supports storage in PostgreSQL (pgvector), Elasticsearch, or JSON file.

Example of combining multiple formats:

```bash
python sfs_processor.py --input sfs_json --output output --formats md,html,git
```

## Fetching Source Data

To convert legislation, you first need to download JSON data:

### Download all legislation from Government Offices

```bash
python downloaders/download_sfs_docs.py --ids all --source rkrattsbaser
```

### Download specific legislation

```bash
python downloaders/download_sfs_docs.py --ids "2024:675,2024:700" --source rkrattsbaser
```

Downloaded files are saved by default in the `sfs_docs` directory. You can specify a different directory with the `--out` parameter.

## Usage

### Basic Conversion

Convert all JSON files in a directory to Markdown:

```bash
python sfs_processor.py --input sfs_json --output output/md --formats md-markers
```

### Structure of Generated Markdown Files

Depending on which format you choose, you get different structures:

#### Format: `md-markers` (default)

Markdown files with preserved semantic structure through `<article>` and `<section>` tags:

- **`<article>`**: Wraps the entire legislation and may contain temporal attributes (ikraft_datum, upphor_datum, etc.)
- **`<section class="avdelning">`**: Wraps divisions (avdelning) as a higher-level structural unit
- **`<section class="kapitel">`**: Wraps chapters (kapitel) as structural units with underlying paragraphs
- **`<section class="paragraf">`**: Wraps each paragraph (§) as a delimited legal provision

```html
<article selex:status="ikraft" selex:ikraft_datum="2025-01-01">

  # Lag (2024:123) om exempel

  <section class="avdelning" id="avd1">
  ## AVDELNING I. ALLMÄNNA BESTÄMMELSER

    <section class="kapitel" id="inledande-bestammelser">
    ### Inledande bestämmelser

      <section class="paragraf" id="inledande-bestammelser.1">
      #### 1 §
      Content of the paragraph...
      </section>

    </section>

  </section>

</article>
```

This semantic structure preserves the document's logical structure and enables automatic processing, analysis, and navigation of the legislation text. ID attributes make it possible to link directly to specific headings and paragraphs (e.g., `#inledande-bestammelser.1`). The tags can also be used for CSS styling and JavaScript functionality.

_Note: Despite the HTML tags, the files are still fully readable as Markdown :)_

#### Format: `md`

Clean Markdown files with normalized heading levels, without section tags:

```markdown
# Lag (2024:123) om exempel

## Inledande bestämmelser

### 1 §

Content of the paragraph...

### 2 §

More content...
```

This format is suitable for simple display and reading, without metadata or temporal handling.

### Selex Attributes for Legal Status and Dates

In addition to CSS classes, `<section>` tags use `selex:` attributes to handle legal status and dates. These attributes enable filtering of content based on entry-into-force and expiration dates:

- **`selex:status`**: Indicates the section's legal status
  - `ikraft`: The section contains entry-into-force rules (converted from e.g., "/Träder i kraft I:2025-01-01")
  - `upphavd`: The section has been repealed (converted if heading contains "upphävd" or "/Upphör att gälla")

- **`selex:ikraft_datum`**: Date when the section enters into force (format: YYYY-MM-DD)
- **`selex:upphor_datum`**: Date when the section ceases to apply (format: YYYY-MM-DD)
- **`selex:ikraft_villkor`**: Condition for entry into force (when no specific date is given)

Example of selex attributes:

```html
<section class="kapitel" selex:status="ikraft" selex:ikraft_datum="2025-01-01">
### 1 § A paragraph
...
</section>

<section class="paragraf" selex:status="upphavd" selex:upphor_datum="2023-12-31">
#### 2 § A paragraph
...
</section>

<section class="kapitel" selex:status="ikraft" selex:ikraft_villkor="den dag regeringen bestämmer">
### 3 § Heading for conditional entry into force
...
</section>
```

These attributes are automatically used by the system's date filtering to create versions of legislation that are valid at specific points in time. Sections with `selex:upphor_datum` that have passed are removed, and sections with `selex:ikraft_datum` that have not yet come are removed from the current version.

### Temporal Processing for Different Formats

The system handles temporal processing (time-based filtering) differently depending on which format is used:

- **`md-markers`** (default): Preserves selex tags and skips temporal processing. This allows all temporal attributes to be retained for later processing. Recommended for preserving all legal metadata.

- **`md`**: Applies temporal processing with **today's date as the target point**. This is important to understand:
  - Repealed provisions (with `selex:upphor_datum` before today's date) are removed
  - Provisions not yet in force (with `selex:ikraft_datum` after today's date) are removed
  - Selex tags are removed after filtering
  - The result is a "clean" Markdown view of how the law appears today
  - **Note:** Since temporal filtering is used automatically, content may disappear if it is repealed or not yet in force

- **`git`**: Skips temporal processing in main processing. Temporal handling is done separately in the git workflow to create historical commits.

- **`html`** and **`htmldiff`**: Apply temporal processing with today's date before HTML generation, similar to `md` format.

- **`vector`**: Applies temporal processing with today's date (or specified `--target-date`) before vector generation. This ensures only current regulations are included in the vector database.

#### Example with target-date

To see how a law appeared at a specific date:

```bash
# See how the law appeared on 2023-01-01
python sfs_processor.py --input sfs_json --output output/md --formats md --target-date 2023-01-01
```

This is useful for creating historical versions or for understanding how the law appeared at a certain point in time.

## Command Line Options

```bash
python sfs_processor.py [--input INPUT] [--output OUTPUT] [--formats FORMATS] [--filter FILTER] [--target-date DATE] [--no-year-folder] [--verbose]
```

### Parameters

- `--input`: Input directory with JSON files (default: "sfs_json")
- `--output`: Output directory for converted files (default: "SFS")
- `--formats`: Output formats to generate, comma-separated. Supports: md-markers, md, git, html, htmldiff, vector (default: "md-markers")
  - `md-markers`: Generate markdown files with section tags preserved
  - `md`: Generate clean markdown files without section tags
  - `git`: Enable Git commits with historical dates
  - `html`: Generate HTML files in ELI structure (basic documents only)
  - `htmldiff`: Generate HTML files in ELI structure with amendment versions
  - `vector`: Generate vector embeddings for semantic search
- `--filter`: Filter files by year (YYYY) or specific reference (YYYY:NNN). Can be comma-separated list.
- `--target-date`: Date (YYYY-MM-DD) for temporal filtering, based on selex tags. Used with `md`, `html`, `htmldiff` and `vector` formats to filter content based on validity dates. If not specified, today's date is used. Example: `--target-date 2023-01-01`
- `--no-year-folder`: Don't create year-based subfolders for documents
- `--verbose`: Display detailed information about processing

### Vector-specific Parameters

- `--vector-backend`: Backend for vector storage (default: "json")
  - `json`: Save to JSON file (for testing/development)
  - `postgresql`: PostgreSQL with pgvector extension
  - `elasticsearch`: Elasticsearch with dense_vector
- `--vector-chunking`: Strategy for document chunking (default: "paragraph")
  - `paragraph`: Split by paragraph (§) - preserves legal structure
  - `chapter`: Split by chapter - larger context
  - `section`: Split by selex section
  - `semantic`: Semantic boundaries with overlap
  - `fixed_size`: Fixed token count with overlap
- `--embedding-model`: Embedding model (default: "text-embedding-3-large")
- `--vector-mock`: Use mock embeddings for testing without OpenAI API key

## Vector Export for Semantic Search

The vector format (`--formats vector`) converts legislation to vector embeddings that can be used for semantic search, RAG applications (Retrieval-Augmented Generation), and AI assistants.

### How It Works

1. **Temporal filtering**: Only current regulations are included (same as `md`/`html` mode)
2. **Intelligent chunking**: Documents are split in a way that preserves legal structure
3. **Embedding generation**: Text is converted to vectors using OpenAI text-embedding-3-large
4. **Storage**: Vectors are saved to selected backend with complete metadata

### Examples

```bash
# Test with mock embeddings (without API key)
python sfs_processor.py --formats vector --vector-mock --filter 2024:100

# Production with OpenAI (requires OPENAI_API_KEY environment variable)
python sfs_processor.py --formats vector --filter 2024

# With PostgreSQL/pgvector backend
python sfs_processor.py --formats vector --vector-backend postgresql

# With chapter chunking for larger context
python sfs_processor.py --formats vector --vector-chunking chapter
```

### Backends

| Backend | Use Case | Requirements |
|---------|----------|--------------|
| `json` | Testing/development | None |
| `postgresql` | Production | PostgreSQL 12+ with pgvector |
| `elasticsearch` | Production | Elasticsearch 8.0+ |

### Metadata Saved

Each vector chunk includes:
- `document_id`: Reference number (e.g., "2024:100")
- `chapter`: Chapter reference (e.g., "1 kap.")
- `paragraph`: Paragraph reference (e.g., "1 §")
- `departement`: Responsible ministry
- `effective_date`: Entry-into-force date

---

## Swedish Legal Terminology

This section explains Swedish legal terms used throughout this tool and in the data. Since the source data comes from Swedish authorities, many field names and concepts remain in Swedish.

### Core Concepts

#### SFS (Svensk Författningssamling)
**English:** Swedish Code of Statutes
**Description:** The official compilation of all Swedish laws and regulations. Each law is identified by a unique reference number.

#### Beteckning
**English:** Reference number / Designation
**Format:** `YYYY:NNN` (e.g., "2024:1274")
**Description:** Unique identifier for each law document, where YYYY is the year of publication and NNN is a sequential number.

#### Lopnummer
**English:** Sequential number / Running number
**Description:** The numeric portion of the beteckning (the NNN part). Used in file organization and ELI structure paths.

#### Rubrik
**English:** Title / Heading
**Description:** The official title of a law document (e.g., "Förordning (2024:1274) om statsbidrag...").

#### Innehåll / Innehållstext / Författningstext
**English:** Content / Content text / Legislation text
**Description:** The main body text of the law document.

---

### Document Lifecycle Terms

#### Ikraft / Ikraftträdande
**English:** Entry into force / Coming into effect
**Description:** The date when a law or provision becomes legally effective.
**JSON field:** `ikraft_datum` (format: YYYY-MM-DD)
**Selex attribute:** `selex:ikraft_datum`

#### Upphor / Upphöra / Upphörande
**English:** Cease / Expiration / When the law expires
**Description:** Date when a law ceases to apply or expires.
**JSON field:** `upphor_datum` (format: YYYY-MM-DD)
**Selex attribute:** `selex:upphor_datum`

#### Upphävd
**English:** Repealed / Revoked / Abolished
**Description:** Status indicating a law or provision has been officially repealed.
**Selex attribute:** `selex:status="upphavd"`

#### Tidsbegränsad
**English:** Time-limited / Temporally limited
**Description:** Used for laws with explicit expiration dates (as opposed to being repealed).
**JSON field:** `tidsbegransadDateTime`

#### Utgår
**English:** Expires / Ceases to apply
**Description:** Temporal expiration (similar to tidsbegränsad).
**JSON field:** `utgar_datum`

---

### Amendments and Modifications

#### Ändringsförfattningar
**English:** Amendment laws / Amending legislation
**Description:** Laws that modify other laws. Stored as a list of amendments.
**JSON structure:** Each amendment includes: `beteckning`, `rubrik`, `ikraft_datum`, and `anteckningar`.

#### Anteckningar
**English:** Notes / Remarks
**Description:** Additional information or comments about an amendment.

#### Övergångsbestämmelser
**English:** Transitional provisions / Interim rules
**Description:** Special rules that apply during the transition period when a law takes effect. Handle cases where implementation requires time or phased application.

#### Upphävd genom
**English:** Repealed by
**Description:** Reference to which law repealed this one.

---

### Document Types and Organization

#### Förordning
**English:** Ordinance / Regulation
**Description:** Type of legal document, usually lower in hierarchy than "lag" (law).

#### Lag
**English:** Law / Act
**Description:** Primary type of legislation, higher in hierarchy than "förordning".

#### Författningstyp
**English:** Legislative type / Document type
**Description:** Classification of the document (e.g., "Förordning", "Lag").

#### Avdelning
**English:** Division / Part
**Description:** Major structural division in a law (e.g., "AVDELNING I").

#### Kapitel
**English:** Chapter
**Description:** Sub-section of an avdelning (e.g., "1 kap.", "2 a kap.").

#### Paragraf / §
**English:** Paragraph / Section
**Description:** Individual legal provision (e.g., "1 §", "3 a §").

#### Bilaga
**English:** Attachment / Appendix
**Description:** Supplementary material attached to a law.

---

### Temporal and Status Attributes (Selex)

These are XML/HTML attributes used to mark legal status and dates in markdown output:

| Attribute | Swedish Term | Description |
|-----------|-------------|-------------|
| `selex:status` | Status | Legal status: `ikraft` (in force) or `upphavd` (repealed) |
| `selex:ikraft_datum` | Ikraftträdandedatum | Entry-into-force date (YYYY-MM-DD) |
| `selex:upphor_datum` | Upphörandedatum | Date when provision ceases (YYYY-MM-DD) |
| `selex:ikraft_villkor` | Ikraftträdandevillkor | Entry-into-force condition (e.g., "den dag regeringen bestämmer") |
| `selex:upphor_villkor` | Upphörandevillkor | Expiration condition |
| `selex:utfardad_datum` | Utfärdandedatum | Date issued/enacted |

---

### Metadata and Frontmatter Fields

These fields appear in JSON metadata and document frontmatter:

| Field Name (Swedish) | English Translation | Description |
|---------------------|-------------------|-------------|
| `departement` | Ministry/Department | Government department responsible (e.g., "Socialdepartementet") |
| `organisation` | Organization/Agency | Entity issuing the regulation |
| `publicerad_datum` | Date published | When document was publicly published |
| `utfardad_datum` | Date issued/enacted | When document was formally signed |
| `forarbeten` | Preparatory materials | Legislative preparatory work/parliamentary reports |
| `celex` / `celex_nummer` | CELEX number | EU legislative reference number |
| `eu_direktiv` / `eUdirektiv` | EU Directive | Boolean flag for EU directive implementation |

---

### Common Swedish Phrases in Content

These phrases frequently appear in the actual legislation text:

| Swedish Phrase | English Translation | Meaning |
|---------------|-------------------|---------|
| "Träder i kraft I:YYYY-MM-DD" | "Enters into force on [date]" | Entry-into-force marker |
| "Upphör att gälla U:YYYY-MM-DD" | "Ceases to apply on [date]" | Expiration marker |
| "Den dag regeringen bestämmer" | "The day the government decides" | Conditional effective date |
| "Denna lag" | "This law" | Standard opening phrase |

---

### File and Directory Naming

- **`sfs-{YYYY}-{NNN}.md`** or **`sfs-{YYYY}-{NNN}-markers.md`**: Standard file naming convention (e.g., "sfs-2024-1274.md")
- **`sfs-jsondata`**: Default input directory name for JSON data
- **`sfs-export-{format}`**: Default output directory names (e.g., "sfs-export-md", "sfs-export-html")

---

### Document Processing Concepts

#### Temporal Processing / Tidsbaserad filtrering
**Description:** The process of showing how a law appeared at specific dates in history. Removes sections that hadn't taken effect yet or had already expired at the target date.

#### Target-date
**Description:** The reference date for temporal processing. Shows how the law appeared on that specific date.

#### md-markers format
**Description:** Markdown with section tags preserved (`<article>`, `<section>`, etc.). Includes all selex attributes for temporal and status information.

#### md format
**Description:** Clean Markdown without section tags. Applies temporal processing (removes future/expired content). Default uses today's date as target date.

#### git format
**Description:** Exports as Git commits with historical dates. Creates version history showing law evolution over time.

#### ELI structure
**Description:** European Legislation Identifier directory structure. Format: `/eli/sfs/{YEAR}/{lopnummer}/index.html`

---

### Example JSON with Explanations

Here's an example of typical JSON data with inline English explanations:

```json
{
  "beteckning": "2024:1274",           // Reference number
  "rubrik": "Förordning om...",         // Official title
  "ikraft_datum": "2025-01-01",         // Entry-into-force date
  "upphor_datum": null,                 // Expiration date (null = still in force)
  "departement": "Socialdepartementet", // Ministry (Health & Social Affairs)
  "utfardad_datum": "2024-12-19",       // Date issued
  "publicerad_datum": "2024-12-20",     // Date published
  "andringsforfattningar": [            // Amending legislation
    {
      "beteckning": "2025:123",
      "rubrik": "Förordning om ändring...",
      "ikraft_datum": "2025-07-01",
      "anteckningar": "Ändr. 5 §"       // Notes: "Amends § 5"
    }
  ]
}
```

---

## Contributing

We welcome contributions from the community! 🙌

- Read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute
- See [DEVELOPMENT.md](DEVELOPMENT.md) for developer documentation and architecture overview
- Contact: Martin Rimskog via [email](mailto:martin@marca.se) or [LinkedIn](https://www.linkedin.com/in/martinrimskog/)
