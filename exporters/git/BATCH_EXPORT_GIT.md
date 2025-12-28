# Batch Export till Git-repository

Detta dokument beskriver hur batch-exporten av SFS-dokument till Git-repository fungerar.

## Översikt

Batch-export-processen automatiserar skapandet av Git-commits för SFS-dokument i två steg:

1. **Initiala commits**: Skapar ett initial commit för varje förordning/lag med innehållet som det såg ut vid utfärdandedatum
2. **Temporal commits**: Skapar commits för framtida ändringar (upcoming changes) baserat på ikraft-datum och upphor-datum

## Hur det fungerar

### Steg 1: Initiala commits

För varje SFS-dokument:

1. Läser JSON-data från `sfs-jsondata`
2. Tillämpar temporal filtrering med `utfardad_datum` som måldag
   - Detta ger dokumentet som det såg ut vid utfärdandet
   - Sektioner med senare ikraft-datum filtreras bort
3. Skapar ett Git commit med:
   - **Commit message**: Rubriken på förordningen/lagen
   - **Commit datum**: Utfärdandedatum (`utfardad_datum`)
   - **Innehåll**: Dokumentet filtrerat till utfärdandedatumet

**Exempel:**
- För SFS 2024:1230 (utfärdad 2024-12-05, ikraft 2025-01-01):
  - Initial commit skapas med datum 2024-12-05
  - Innehållet är tomt eftersom ikraft-datum är senare
  - Ett förklarande meddelande läggs till

### Steg 2: Temporal commits (Upcoming Changes)

För varje SFS-dokument med temporal ändringar:

1. Läser markdown-filen med selex-markers från `sfs-export-md-markers`
2. Identifierar alla framtida ändringar (upcoming changes):
   - Sektioner med `selex:ikraft_datum` i framtiden
   - Sektioner med `selex:upphor_datum` i framtiden
   - Hela dokument med framtida ikraft/upphor
3. Grupperar ändringar per datum
4. För varje datum:
   - Tillämpar temporal filtrering med datumet som måldag
   - Skapar ett Git commit med:
     - **Commit message**: Beskrivande meddelande med emoji (✅ för ikraft, 🚫 för upphor, 🔄 för båda)
     - **Commit datum**: Ändringsdatumet (ikraft eller upphor)
     - **Innehåll**: Dokumentet filtrerat till det datumet

**Exempel av commit messages:**
- `✅ 2024:1230 träder i kraft` - Hela dokumentet träder i kraft
- `✅ 2024:123: 3 § träder i kraft` - En specifik paragraf träder i kraft
- `🚫 2024:456: 5 § och 7 § upphör att gälla` - Två paragrafer upphör
- `🔄 2024:789: 2 § uppdateras` - En paragraf upphävs och ny träder i kraft samma dag

## Användning

### Grundläggande användning

```bash
python batch_export_to_git.py --years 2024-2026 --branch batch-2025-12-28
```

### Alla parametrar

```bash
python batch_export_to_git.py \
  --years 2024-2026 \              # Årsspann att exportera
  --branch batch-2025-12-28 \      # Git branch-namn
  --input ../sfs-jsondata \        # JSON-katalog (default)
  --output ../sfs-export-git \     # Output-katalog (default)
  --markers-dir ../sfs-export-md-markers \  # Markers-katalog (default)
  --batch-size 100 \               # Antal filer per batch
  --verbose                        # Visa detaljerad output
```

### Hoppa över steg

```bash
# Endast initiala commits (hoppa över temporal)
python batch_export_to_git.py --years 2024-2026 --branch my-branch --skip-temporal

# Endast temporal commits (hoppa över initiala)
python batch_export_to_git.py --years 2024-2026 --branch my-branch --skip-initial
```

## Krav

### 1. JSON-data
Kräver JSON-filer i `sfs-jsondata` (eller angiven katalog).

### 2. Markers-filer
För temporal commits krävs markdown-filer med selex-markers i `sfs-export-md-markers`.

Generera markers om de saknas:
```bash
python sfs_processor.py --formats md-markers --filter 2024,2025,2026
```

### 3. GitHub PAT (Personal Access Token)

För att pusha till GitHub behövs en PAT token:

1. Skapa en PAT på GitHub:
   - Gå till Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Klicka "Generate new token (classic)"
   - Välj scope: `repo` (full control of private repositories)
   - Kopiera token

2. Sätt miljövariabel:
   ```bash
   export GIT_GITHUB_PAT="ghp_your_token_here"
   ```

   Eller skapa `.env`-fil:
   ```bash
   GIT_GITHUB_PAT=ghp_your_token_here
   ```

### 4. Target Repository

Default är `https://github.com/se-lex/sfs.git`.

Ändra via miljövariabel:
```bash
export GIT_TARGET_REPO="https://github.com/your-user/your-repo.git"
```

## Teknisk implementation

### Temporal filtrering

Scriptet använder `apply_temporal()` för att filtrera dokument till ett specifikt datum:

1. **Initial commit (utfärdad_datum)**:
   - Tar bort alla sektioner med `ikraft_datum > utfärdad_datum`
   - Tar bort alla sektioner med `upphor_datum < utfärdad_datum`

2. **Temporal commits (ändringsdatum)**:
   - Tar bort alla sektioner med `ikraft_datum > ändringsdatum`
   - Tar bort alla sektioner med `upphor_datum < ändringsdatum`

### Git-operationer

1. **Klona repository** till temporär katalog
2. **Skapa branch** med angivet namn
3. **Bearbeta filer i batcher**:
   - Default: 100 filer per batch
   - Varje batch pushas direkt efter bearbetning
4. **Pusha till origin** efter varje batch

### Batch-processering

Filer delas upp i batcher för att:
- Undvika minnesproblem med stora dataset
- Möjliggöra inkrementell push (återhämtning vid fel)
- Visa progress under bearbetning

## Exempel: Export för 2024-2026

```bash
python batch_export_to_git.py --years 2024-2026 --branch batch-2025-12-28
```

### Output

```
================================================================================
BATCH EXPORT TILL GIT
================================================================================
JSON-katalog: /path/to/sfs-jsondata
Utdata-katalog: /path/to/sfs-export-git
Markers-katalog: /path/to/sfs-export-md-markers
Branch: batch-2025-12-28
Antal filer: 268
Batch-storlek: 100
================================================================================

================================================================================
STEG 1: SKAPAR INITIALA COMMITS
================================================================================

Klonar https://github.com/se-lex/sfs.git till temporär katalog...
Skapade och bytte till branch 'batch-2025-12-28'
Delar upp 268 filer i batcher om 100 filer var
Skapade 3 batcher

Bearbetar batch 1/3 (100 filer)...
[... bearbetning ...]
Pushar batch 1/3 till target repository...
Batch 1/3 pushad till target repository som branch 'batch-2025-12-28'

[... batch 2 och 3 ...]

✅ Initiala commits skapade och pushade

================================================================================
STEG 2: SKAPAR TEMPORAL COMMITS (UPCOMING CHANGES)
================================================================================

Hittade 846 markdown-filer att bearbeta
Delar upp 846 filer i batcher om 100 filer var
Skapade 9 batcher

Bearbetar temporal batch 1/9 (100 filer)...
[... bearbetning ...]
Pushar temporal batch 1/9 till target repository...
Temporal batch 1/9 pushad till target repository som branch 'batch-2025-12-28'

[... batch 2-9 ...]

✅ Temporal commits skapade och pushade

================================================================================
✅ BATCH EXPORT KLAR!
================================================================================
Branch: batch-2025-12-28
Antal filer bearbetade: 268

Nästa steg:
1. Gå till target repository och skapa en Pull Request från branch 'batch-2025-12-28'
2. Granska ändringarna och merga till main
================================================================================
```

## Nästa steg efter export

1. **Gå till GitHub repository**: `https://github.com/se-lex/sfs`
2. **Skapa Pull Request** från branch `batch-2025-12-28` till `main`
3. **Granska ändringar**:
   - Kontrollera att commits har korrekta datum
   - Verifiera att temporal commits skapades korrekt
   - Kolla att commit messages är beskrivande
4. **Merge Pull Request** när allt ser bra ut

## Felsökning

### Problem: "Ingen PAT token hittades"

**Lösning**: Sätt `GIT_GITHUB_PAT` miljövariabel (se ovan)

### Problem: "Markers-katalogen finns inte"

**Lösning**: Generera markers först:
```bash
python sfs_processor.py --formats md-markers --filter 2024,2025,2026
```

### Problem: "Inga selex-taggar hittades"

Detta händer om dokumentet redan bearbetats utan selex-taggar. Temporal commits kräver att selex-taggar är kvar.

**Lösning**: Generera om markers-filerna:
```bash
python sfs_processor.py --formats md-markers --filter [beteckning]
```

### Problem: Push misslyckades

**Möjliga orsaker:**
1. Ingen PAT token
2. PAT token har inte `repo` scope
3. Ingen skrivrättighet till repository
4. Branch redan finns och har konflikter

**Lösning**:
- Kontrollera PAT token permissions
- Använd unikt branch-namn
- Kolla GitHub för eventuella felmeddelanden

## Kodstruktur

### Huvudscript
- `batch_export_to_git.py` - Huvudscript för batch-export

### Moduler
- `exporters/git/init_commits_batch_processor.py` - Hanterar initiala commits
- `exporters/git/temporal_commits_batch_processor.py` - Hanterar temporal commits
- `exporters/git/generate_commits.py` - Skapar individuella commits
- `exporters/git/git_utils.py` - Git-hjälpfunktioner
- `temporal/apply_temporal.py` - Temporal filtrering
- `temporal/upcoming_changes.py` - Identifierar framtida ändringar

## Se också

- [sfs_processor.py](./sfs_processor.py) - Huvudprocessor för SFS-dokument
- [exporters/git/](./exporters/git/) - Git-export implementationer
- [temporal/](./temporal/) - Temporal processing
