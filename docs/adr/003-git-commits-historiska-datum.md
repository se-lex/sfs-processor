# ADR-003: Git-commits med historiska datum för versionshistorik

## Status

Accepterad

## Kontext och problembeskrivning

Lagstiftning har en inneboende temporal dimension - lagar stiftas, ändras och upphävs vid specifika datum. För att göra denna historik tillgänglig och navigerbar behövde vi ett sätt att representera hur en lag såg ut vid olika tidpunkter genom historien.

Utmaningarna var:

1. **Historisk representation**: Hur visar vi hur en lag såg ut 2010 vs 2024?
2. **Navigerbarhet**: Användare ska kunna "scrolla" bakåt i tiden
3. **Versionshantering**: Varje ändring ska vara spårbar med exakt datum
4. **Teknisk enkelhet**: Systemet ska vara lätt att förstå och använda
5. **Standardverktyg**: Helst undvika custom databaser eller proprietära system

Alternativen inkluderade:

- Separata filer per version med datum i filnamn
- Databas med temporal data (PostgreSQL temporal tables)
- Custom versionshanteringssystem
- Git med manipulerade commit-datum

## Beslut

Vi använder **Git med backdated commits** där varje författning och ändring får en commit med det faktiska historiska datumet då den trädde i kraft eller utfärdades.

### Teknisk implementation

**Miljövariabler för datum**:
```python
env = {
    'GIT_AUTHOR_DATE': '2010-01-01 12:00:00 +0100',
    'GIT_COMMITTER_DATE': '2010-01-01 12:00:00 +0100'
}
subprocess.run(['git', 'commit', '-m', message], env=env)
```

**Commit-strategi**:

1. **Initial commit**: Skapas med `utfardadDateTime` (utfärdandedatum)
   - Innehåller ursprungsversionen av författningen
   - Temporal filtrering appliceras upp till utfärdandedatumet

2. **Ändrings-commits**: Skapas med respektive `ikraft_datum`
   - Varje ändring får en separat commit
   - Commiten visar hur lagen ser ut efter ändringen trätt i kraft

3. **Upphävande-commits**: Skapas när en författning upphävs
   - Markerar när en lag slutar gälla

**Branch-struktur**:
- Commits skapas på en dedikerad branch (t.ex. `git-export-YYYYMMDD`)
- Branch kan pushas till separat repository (`se-lex/sfs`)

### Exempel på commit-historik

```
2024-07-01  ✏️ Ändra Lag (2010:100) - SFS 2024:500
2023-01-01  ✏️ Ändra Lag (2010:100) - SFS 2023:50
2010-01-15  📜 Lag (2010:100) om exempel
```

När man gör `git checkout <commit>` får man exakt hur lagen såg ut vid det datumet.

## Konsekvenser

### Positiva

- **Git som tidsmaskin**: `git log --since="2015-01-01" --until="2016-01-01"` visar alla ändringar under ett år
- **Diff mellan versioner**: `git diff <commit1> <commit2>` visar exakt vad som ändrats
- **Standardverktyg**: Alla Git-klienter fungerar (GitHub, GitLab, gitk, SourceTree, etc.)
- **Gratis hosting**: GitHub/GitLab tillhandahåller gratis hosting och webb-UI
- **Blame-funktion**: `git blame` visar exakt när varje rad ändrades
- **Decentraliserat**: Varje klon innehåller hela historiken
- **Visuell representation**: GitHub/GitLab visar automatiskt commit-graf och tidslinje
- **API-tillgång**: Git-hostar erbjuder REST API:er för att hämta historiska versioner

### Negativa

- **Okonventionell användning**: Git är inte designat för backdated commits
  - Mitigering: Tydlig dokumentation, separata branches för Git-export

- **Commit-ordning**: Git sorterar efter commit-datum, inte när commiten skapades
  - Mitigering: Detta är faktiskt önskat beteende - vi vill ha kronologisk ordning

- **Merge-komplexitet**: Svårt att merge:a historiska branches
  - Mitigering: Git-export är en one-way operation, inget merging behövs

- **Repository-storlek**: Många commits kan göra repositoryt stort
  - Mitigering: SFS har ~50 000 författningar, hanteras fint av Git

- **Author vs Committer**: Båda datum sätts till historiskt datum
  - Mitigering: Konsekvent beteende, men metadata om faktiskt skapandedatum går förlorad

- **Duplicate-hantering**: Risk för dubbla commits med samma meddelande
  - Mitigering: Implementerad check i `check_duplicate_commit_message()`

### Tekniska konsekvenser

- **Temporal processing**: Varje commit-punkt kräver temporal filtrering upp till det datumet
- **Branch-isolation**: Git-commits måste ske på dedikerad branch
- **Clean state**: Branchen rensas innan ny export (`remove_all_commits_on_branch`)
- **Performance**: Sekventiell processning av alla författningar tar tid
  - Optimering: Batch-processing i `temporal_commits_batch_processor.py`

## Alternativ som övervägdes

### 1. Separata filer med datum i namn

```
2010-100/2010-01-15.md
2010-100/2023-01-01.md
2010-100/2024-07-01.md
```

**Varför inte valt**:

- Ingen inbyggd diff-funktionalitet
- Svårt att navigera mellan versioner
- Ingen standardiserad tooling
- Måste bygga custom UI för att visa ändringar

### 2. PostgreSQL temporal tables

```sql
CREATE TABLE laws (
    id INT,
    content TEXT,
    valid_from DATE,
    valid_to DATE
);
```

**Varför inte valt**:

- Kräver databas-infrastruktur
- Mindre tillgängligt för användare (kräver SQL-kunskap)
- Ingen visuell representation utan custom UI
- Svårare att hosta och dela publikt

### 3. Custom versionshanteringssystem

**Varför inte valt**:

- Reinventing the wheel
- Måste bygga all tooling från grunden
- Ingen befintlig community eller ekosystem
- Högre underhållskostnad

### 4. Git tags istället för commits

```
git tag "2010-100-v1" <commit>
git tag "2010-100-v2" <commit>
```

**Varför inte valt**:

- Tags visar inte temporal progression lika tydligt
- Inget naturligt sätt att se alla ändringar kronologiskt
- `git log` blir mindre användbart
- Tags är metadata, inte innehåll

### 5. Separata branches per författning

```
branches: 2010-100, 2010-101, 2010-102, ...
```

**Varför inte valt**:

- 50 000+ branches blir ohanterbart
- Svårt att se alla lagändringar kronologiskt
- Branch-explosion överbelastar Git-UI:s

## Relaterade beslut

- [ADR-004](004-semantiska-temporal-taggar.md) - Temporal metadata som driver commit-genereringen
- [ADR-002](002-import-fran-regeringskansliet.md) - Källdata för utfärdande- och ikraftträdandedatum

## Noteringar

- **Implementationer**:
  - `exporters/git/generate_commits.py` - Skapar initial och ändrings-commits
  - `exporters/git/git_utils.py` - Git-operationer med `GIT_AUTHOR_DATE` och `GIT_COMMITTER_DATE`
  - `exporters/git/temporal_commits_batch_processor.py` - Batch-processing för prestanda

- **Användning**:

  ```bash
  # Exportera till Git med historiska commits
  python sfs_processor.py --formats git --filter 2024

  # Efter export, navigera i historiken
  cd <git-repo>
  git log --oneline --since="2020-01-01"
  git show <commit-hash>
  git diff <old-commit> <new-commit>
  ```

- **Output-repository**: https://github.com/se-lex/sfs
  - Innehåller all SFS-lagstiftning med historiska commits
  - Publikt tillgänglig för utvecklare och jurister
  - API-åtkomst via GitHub REST API

- **Commit-meddelanden**: Använder emojis för att indikera typ av ändring
  - 📜 Initial författning
  - ✏️ Ändring av författning
  - 🗑️ Upphävande

- **Performance**: ~50 000 författningar tar flera timmar att processa
  - Optimering: Batch-processing, parallellisering övervägs

- **Framtida förbättringar**:
  - Metadata-fil per commit för att bevara faktiskt skapandedatum
  - Signerade commits för autenticitet
  - Incremental updates istället för full rebuild
