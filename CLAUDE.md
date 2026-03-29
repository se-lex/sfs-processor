# Claude Code guidance for sfs-processor

## Commit messages

Write commit messages in English, imperative mood, sentence case, no trailing period.

Follow the pattern established in this repo:

- Bug fixes: `Fix: <what was broken and how>`
- New additions: `Add <thing being added>`
- Updates/changes: `Update <thing being changed>`
- Improvements: `Improve <what improved>`
- Renames/moves: `Rename <old> to <new>`

When a commit closes a GitHub issue, append `(#N)` at the end.

Examples from this repo:

```text
Fix: YAML list corruption for forarbeten in frontmatter
Add GitHub Pages publishing workflow
Update README.md: Clarify target-date usage
Improve HTML site upload scripts
```

## Code style

- Python 3.10+ — use `match`, `X | Y` union types, and other modern syntax freely.
- Line length: 120 characters (configured in `pyproject.toml`).
- Lint and format with `ruff` before committing:

```sh
ruff check . --fix
ruff format .
```

## Tests

```sh
python -m pytest test/ -v
```

All existing tests must pass. Tag new tests with the appropriate marker: `unit`, `integration`, `api`, or `slow`.

## Architecture decisions

Significant architectural choices are documented as ADRs in `docs/adr/`. If a change involves a non-obvious architectural trade-off, add or update an ADR.

## Domain language

`sfs-processor` converts Swedish legislation (SFS — Svensk författningssamling) from JSON to Markdown, HTML, and Git-history formats. Terms like *forarbeten*, *normtyp*, *giltighetstid*, and *SFS-nummer* are intentional Swedish legal vocabulary — do not translate or alter them.
