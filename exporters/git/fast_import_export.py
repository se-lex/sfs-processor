#!/usr/bin/env python3
"""Fast-import based export pipeline — an alternative to `batch_export_to_git.py`.

`batch_export_to_git.py` creates every commit via `git add` / `git commit`
subprocess calls: once per document for initial commits, once per date per
document for temporal (ikraft/upphör) commits, across two separate
porcelain-driven passes. Each of those calls rewrites the index and touches
the working tree, which dominates wall-clock time once you're generating on
the order of tens of thousands of commits (see ADR-003 and `sfs_processor.py`
`--formats git`, where SFS has ~50 000 författningar).

This module instead:

  1. Computes every commit's plan (path, content, message, date) up front,
     for every document, by reusing the exact same content-generation logic
     as the subprocess-based exporter (`generate_commits.plan_init_commit`
     / `plan_temporal_commits`) — no legal-content logic is duplicated.
  2. Sorts all of those plans, across ALL documents, into one single
     chronological sequence.
  3. Streams them through one `git fast-import` invocation, which builds the
     commits directly in the object database — no working tree, no index,
     no per-commit subprocess call, no branch checkout.

A side effect of step 2 is a genuine improvement in history shape: because
every commit (initial + temporal, across every document) is globally
date-sorted before being written, the branch's parent chain matches real
chronological order — rather than being grouped document-by-document with
backdated timestamps layered on top of creation order, as the current
exporter produces (still visually chronological in `git log`, since that
sorts by date regardless of parent order, but the underlying graph isn't).

Usage:
    python -m exporters.git.fast_import_export --years 2024-2026 --branch fast-import-2025-12-28
"""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from exporters.git.fast_import_writer import FastImportWriter, FileChange, to_raw_git_date
from exporters.git.generate_commits import plan_init_commit, plan_temporal_commits
from exporters.git.git_utils import GIT_TIMEOUT, clone_target_repository_to_temp, push_to_target_repository
from formatters.frontmatter_manager import extract_frontmatter_property
from temporal.upcoming_changes import identify_upcoming_changes
from util.file_utils import filter_json_files, read_file_content, save_to_disk


@dataclass
class CommitEvent:
    """One globally-ordered commit: a full rewrite of a single file's content."""

    date: str  # ISO date, e.g. "2010-01-15"
    message: str
    path: str  # repo-relative path, e.g. "2010/sfs-2010-100.md"
    content: str


def _init_commit_events(json_files: list[Path], output_dir: Path | None, verbose: bool) -> list[CommitEvent]:
    """Build one CommitEvent per document's initial (utfärdande) commit."""
    # Deferred import: sfs_processor imports from exporters.git at module
    # level, so importing it back at *this* module's top level would be
    # circular. By the time this function runs, sfs_processor is fully
    # loaded — same pattern as init_commits_batch_processor.py.
    from formatters.format_sfs_text import normalize_heading_levels
    from sfs_processor import convert_to_markdown, create_id_slug, create_safe_filename

    events = []
    for json_file in json_files:
        try:
            data = json.loads(read_file_content(json_file))
        except (OSError, json.JSONDecodeError) as e:
            print(f"Fel vid läsning av {json_file}: {e}")
            continue

        markdown_content = convert_to_markdown(data, fetch_predocs_from_api=False, apply_links=True)
        markdown_content = normalize_heading_levels(markdown_content)

        try:
            plan = plan_init_commit(data, markdown_content, verbose)
        except ValueError as e:
            print(f"Fel vid planering av {json_file}: {e}")
            continue

        id_slug = create_id_slug(data.get("beteckningSortable", plan.beteckning))
        filename = create_safe_filename(id_slug, preserve_selex_tags=False)
        relative_path = Path(plan.year) / filename if plan.year else Path(filename)

        if output_dir is not None:
            reference_file = output_dir / relative_path
            reference_file.parent.mkdir(parents=True, exist_ok=True)
            save_to_disk(reference_file, plan.content)

        events.append(
            CommitEvent(
                date=plan.commit_date, message=plan.commit_message, path=str(relative_path), content=plan.content
            )
        )

    return events


def _temporal_commit_events(markdown_dir: Path, from_date: str | None, to_date: str | None) -> list[CommitEvent]:
    """Build one CommitEvent per date with temporal changes, per document.

    Mirrors the path convention in `temporal_commits_batch_processor.py`:
    the file lands at `<year>/<name-without-"-markers">.md`, where `<year>`
    is the marker file's parent directory name.
    """
    events = []
    for md_file in sorted(markdown_dir.rglob("*.md")):
        try:
            content = read_file_content(md_file)
        except OSError as e:
            print(f"Fel vid läsning av {md_file}: {e}")
            continue

        if "<article" not in content:
            continue  # no selex tags left, nothing temporal to extract

        changes = identify_upcoming_changes(content)
        if not changes:
            continue

        changes_by_date: dict[str, list] = {}
        for change in changes:
            change_date = change["date"]
            if from_date and change_date < from_date:
                continue
            if to_date and change_date > to_date:
                continue
            changes_by_date.setdefault(change_date, []).append(change)

        if not changes_by_date:
            continue

        doc_name = extract_frontmatter_property(content, "beteckning")
        rubrik = extract_frontmatter_property(content, "rubrik")
        if not doc_name:
            print(f"Varning: Ingen doc_name hittades i frontmatter för {md_file}")
            continue

        year_dir = md_file.parent.name
        filename = md_file.name.replace("-markers", "")
        relative_path = Path(year_dir) / filename

        for plan in plan_temporal_commits(content, doc_name, rubrik, changes_by_date):
            events.append(
                CommitEvent(date=plan.date, message=plan.message, path=str(relative_path), content=plan.content)
            )

    return events


def _resolve_ref(repo_dir: Path, ref: str) -> str | None:
    """Resolve `ref` to a commit sha in `repo_dir`, or None if it doesn't exist."""
    result = subprocess.run(
        ["git", "rev-parse", "--verify", ref], cwd=repo_dir, capture_output=True, text=True, timeout=GIT_TIMEOUT
    )
    return result.stdout.strip() if result.returncode == 0 else None


def export_to_git_fast_import(
    json_files: list[Path],
    markers_dir: Path | None,
    branch_name: str,
    output_dir: Path | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    base_ref: str = "refs/heads/main",
    verbose: bool = False,
) -> int:
    """Generate the full SFS git export (initial + temporal commits) as one
    globally date-sorted `git fast-import` stream, then push once.

    Returns the number of commits written.
    """
    repo_dir, _original_cwd = clone_target_repository_to_temp(verbose=verbose)
    if repo_dir is None:
        raise RuntimeError("Failed to clone target repository")

    print(f"Bygger commit-plan för {len(json_files)} dokument...")
    events = _init_commit_events(json_files, output_dir, verbose)

    if markers_dir is not None and markers_dir.exists():
        print(f"Bygger temporal commit-plan från {markers_dir}...")
        events += _temporal_commit_events(markers_dir, from_date, to_date)

    if not events:
        print("Inga commits att generera.")
        return 0

    # Global chronological order across every document — the point of doing
    # this in one fast-import pass instead of per-document porcelain commits.
    events.sort(key=lambda e: (e.date, e.path))
    print(f"Totalt {len(events)} commits, sorterade kronologiskt {events[0].date} .. {events[-1].date}")

    from_ref = _resolve_ref(repo_dir, base_ref) if base_ref else None
    if base_ref and verbose:
        print(
            f"Ny branch rotas i {base_ref} ({from_ref})" if from_ref else f"{base_ref} finns inte, skapar rot-historik"
        )

    writer = FastImportWriter.to_repo(repo_dir, verbose=verbose)
    for i, event in enumerate(events):
        raw_date = to_raw_git_date(event.date)
        writer.commit(
            branch=branch_name,
            message=event.message,
            author_date=raw_date,
            committer_date=raw_date,
            changes=[FileChange.write(event.path, event.content)],
            from_ref=from_ref if i == 0 else None,
        )
        if verbose and (i + 1) % 1000 == 0:
            print(f"  ... {i + 1}/{len(events)} commits skrivna")

    writer.close()
    print(f"✅ {writer.commit_count} commits skapade i branch '{branch_name}' (en enda fast-import-pass)")

    if not push_to_target_repository(branch_name, "origin", verbose):
        raise RuntimeError(f"Misslyckades med att pusha branch '{branch_name}'")

    print(f"✅ Branch '{branch_name}' pushad till target repository")
    return writer.commit_count


def main() -> int:
    from exporters.git.batch_export_to_git import parse_year_range, year_range_to_date_range

    parser = argparse.ArgumentParser(
        description="Exportera SFS-dokument till Git via en enda git-fast-import-ström (prototyp, se ADR-003)."
    )
    parser.add_argument("--years", help='Årsintervall att exportera (t.ex. "2024-2026" eller "2024").')
    parser.add_argument("--filter", help="Filtrera filer på år (YYYY) eller beteckning (YYYY:NNN), kommaseparerat.")
    parser.add_argument("--branch", required=True, help="Git-branchnamn att skapa commits på.")
    parser.add_argument("--input", "-i", help="Katalog med JSON-filer (default: ../sfs-jsondata)")
    parser.add_argument("--output", "-o", help="Katalog för lokala referenskopior (utelämna för att hoppa över)")
    parser.add_argument("--markers-dir", help="Katalog med markdown-filer med selex-markers för temporal commits")
    parser.add_argument(
        "--base-ref", default="refs/heads/main", help="Ref att rota exportbranchen i (default: refs/heads/main)"
    )
    parser.add_argument("--verbose", action="store_true", help="Visa detaljerad output")

    args = parser.parse_args()

    script_dir = Path(__file__).parent
    json_dir = Path(args.input) if args.input else script_dir.parent / "sfs-jsondata"
    output_dir = Path(args.output) if args.output else None
    markers_dir = Path(args.markers_dir) if args.markers_dir else script_dir.parent / "sfs-export-md-markers"

    if not json_dir.exists():
        print(f"Fel: JSON-katalog {json_dir} finns inte")
        return 1

    json_files = list(json_dir.glob("*.json"))
    if not json_files:
        print(f"Inga JSON-filer hittades i {json_dir}")
        return 1

    filter_str = None
    from_date = to_date = None
    if args.years:
        years = parse_year_range(args.years)
        filter_str = ",".join(years)
        from_date, to_date = year_range_to_date_range(args.years)
    elif args.filter:
        filter_str = args.filter

    if filter_str:
        original_count = len(json_files)
        json_files = filter_json_files(json_files, filter_str)
        print(f"Filter '{filter_str}' tillämpad: {len(json_files)} av {original_count} filer valda")
        if not json_files:
            print("Inga filer matchar filterkriterier")
            return 1

    try:
        export_to_git_fast_import(
            json_files=json_files,
            markers_dir=markers_dir,
            branch_name=args.branch,
            output_dir=output_dir,
            from_date=from_date,
            to_date=to_date,
            base_ref=args.base_ref,
            verbose=args.verbose,
        )
    except Exception as e:
        print(f"❌ Fel vid fast-import-export: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
