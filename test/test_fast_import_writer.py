#!/usr/bin/env python3
"""Tests for the git-fast-import stream writer.

These are integration tests in the literal sense of exercising a real `git`
binary against a scratch repository in `tmp_path` — no SFS data involved,
just verifying the fast-import stream round-trips correctly.
"""

import subprocess
from pathlib import Path

import pytest

from exporters.git.fast_import_writer import FastImportWriter, FileChange, to_raw_git_date


def run_git(repo_dir: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo_dir, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


@pytest.fixture
def empty_repo(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    run_git(repo_dir, "init", "--quiet", "-b", "main")
    run_git(repo_dir, "config", "user.email", "test@example.com")
    run_git(repo_dir, "config", "user.name", "Test")
    return repo_dir


@pytest.mark.unit
class TestToRawGitDate:
    def test_winter_date_uses_cet_offset(self):
        # Sweden is UTC+1 (CET) outside DST.
        assert to_raw_git_date("2010-01-15") == "1263510000 +0100"

    def test_summer_date_uses_cest_offset(self):
        # Sweden is UTC+2 (CEST) during DST.
        raw = to_raw_git_date("2024-07-01")
        assert raw.endswith("+0200")

    def test_explicit_time_is_respected(self):
        midnight = to_raw_git_date("2010-01-15", "00:00:00")
        noon = to_raw_git_date("2010-01-15", "12:00:00")
        midnight_epoch = int(midnight.split()[0])
        noon_epoch = int(noon.split()[0])
        assert noon_epoch - midnight_epoch == 12 * 3600


@pytest.mark.unit
@pytest.mark.slow
class TestFastImportWriterRootHistory:
    """Building a brand new branch from nothing (no `from_ref`)."""

    def test_single_commit_lands_with_content_message_and_date(self, empty_repo):
        writer = FastImportWriter.to_repo(empty_repo)
        writer.commit(
            branch="export",
            message="Initial SFS document",
            author_date=to_raw_git_date("2010-01-15"),
            committer_date=to_raw_git_date("2010-01-15"),
            changes=[FileChange.write("2010/2010-100.md", "# Test\n\nInnehåll.\n")],
        )
        writer.close()

        assert writer.commit_count == 1

        log = run_git(empty_repo, "log", "refs/heads/export", "--format=%s|%ad", "--date=short")
        assert log == "Initial SFS document|2010-01-15"

        content = run_git(empty_repo, "show", "refs/heads/export:2010/2010-100.md")
        assert content == "# Test\n\nInnehåll."

    def test_sequential_commits_chain_as_parent_child(self, empty_repo):
        writer = FastImportWriter.to_repo(empty_repo)
        writer.commit(
            branch="export",
            message="v1",
            author_date=to_raw_git_date("2010-01-15"),
            committer_date=to_raw_git_date("2010-01-15"),
            changes=[FileChange.write("doc.md", "version 1\n")],
        )
        writer.commit(
            branch="export",
            message="v2",
            author_date=to_raw_git_date("2015-06-01"),
            committer_date=to_raw_git_date("2015-06-01"),
            changes=[FileChange.write("doc.md", "version 2\n")],
        )
        writer.close()

        assert writer.commit_count == 2

        # oldest first
        subjects = run_git(
            empty_repo, "log", "refs/heads/export", "--format=%s", "--reverse"
        ).splitlines()
        assert subjects == ["v1", "v2"]

        parents = run_git(empty_repo, "log", "refs/heads/export", "--format=%P", "-1").strip()
        assert parents  # v2 has one parent, v1's sha

        content = run_git(empty_repo, "show", "refs/heads/export:doc.md")
        assert content == "version 2"

    def test_delete_removes_file_in_later_commit(self, empty_repo):
        writer = FastImportWriter.to_repo(empty_repo)
        writer.commit(
            branch="export",
            message="add",
            author_date=to_raw_git_date("2010-01-01"),
            committer_date=to_raw_git_date("2010-01-01"),
            changes=[FileChange.write("doc.md", "content\n")],
        )
        writer.commit(
            branch="export",
            message="remove",
            author_date=to_raw_git_date("2020-01-01"),
            committer_date=to_raw_git_date("2020-01-01"),
            changes=[FileChange.delete("doc.md")],
        )
        writer.close()

        files = run_git(empty_repo, "ls-tree", "-r", "--name-only", "refs/heads/export")
        assert files == ""

    def test_unicode_content_round_trips(self, empty_repo):
        writer = FastImportWriter.to_repo(empty_repo)
        writer.commit(
            branch="export",
            message="Förordning träder i kraft ✅",
            author_date=to_raw_git_date("2010-01-01"),
            committer_date=to_raw_git_date("2010-01-01"),
            changes=[FileChange.write("2010/åäö.md", "Författningssamling – ändrad §3.\n")],
        )
        writer.close()

        message = run_git(empty_repo, "log", "refs/heads/export", "-1", "--format=%s")
        assert message == "Förordning träder i kraft ✅"

        content = run_git(empty_repo, "show", "refs/heads/export:2010/åäö.md")
        assert content == "Författningssamling – ändrad §3."


@pytest.mark.unit
@pytest.mark.slow
class TestFastImportWriterFromExistingBranch:
    """Rooting a new export branch onto an existing `main` tip via `from_ref`."""

    def test_new_branch_starts_from_main_tip_and_leaves_main_untouched(self, empty_repo):
        (empty_repo / "README.md").write_text("hello\n")
        run_git(empty_repo, "add", "README.md")
        run_git(empty_repo, "commit", "--quiet", "-m", "initial")
        main_tip = run_git(empty_repo, "rev-parse", "HEAD")

        writer = FastImportWriter.to_repo(empty_repo)
        writer.commit(
            branch="export",
            message="first export commit",
            author_date=to_raw_git_date("2010-01-01"),
            committer_date=to_raw_git_date("2010-01-01"),
            changes=[FileChange.write("doc.md", "content\n")],
            from_ref=main_tip,
        )
        writer.close()

        # main is untouched
        assert run_git(empty_repo, "rev-parse", "main") == main_tip
        assert run_git(empty_repo, "ls-tree", "-r", "--name-only", "main") == "README.md"

        # export branch has both README.md (inherited) and doc.md (new)
        export_files = set(
            run_git(empty_repo, "ls-tree", "-r", "--name-only", "refs/heads/export").splitlines()
        )
        assert export_files == {"README.md", "doc.md"}

        parent = run_git(empty_repo, "log", "refs/heads/export", "--format=%P", "-1").strip()
        assert parent == main_tip
