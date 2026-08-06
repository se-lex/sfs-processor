"""Writer for the git-fast-import stream format.

`git fast-import` builds commits directly into the object database from a
single stdin stream, without ever touching the working tree or the index.
For a history that is generated wholesale from another data source (like the
SFS git export, which backdates every commit) that avoids the per-commit
`git add` / `git commit` subprocess overhead of the porcelain-based exporter
in `generate_commits.py` / `git_utils.py`.

Only the subset of the fast-import grammar SFS export needs is implemented:
commits with inline file blobs on a single branch, in strictly increasing
commit order, optionally rooted onto an existing branch tip via `from`.

See `git help fast-import` for the full protocol.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import BinaryIO
from zoneinfo import ZoneInfo

# Swedish legislation dates are inherently Swedish local time; converting via
# this zone (rather than relying on the exporting machine's local timezone,
# as the current GIT_AUTHOR_DATE-env-var approach implicitly does) keeps DST
# offsets correct and makes the result independent of where export runs.
SFS_TIMEZONE = ZoneInfo("Europe/Stockholm")

DEFAULT_COMMIT_TIME = "00:00:00"


@dataclass
class FileChange:
    """A single file's content at a commit. `content is None` means delete."""

    path: str
    content: bytes | None

    @classmethod
    def write(cls, path: str, content: str) -> FileChange:
        return cls(path=path, content=content.encode("utf-8"))

    @classmethod
    def delete(cls, path: str) -> FileChange:
        return cls(path=path, content=None)


def to_raw_git_date(iso_date: str, time_str: str = DEFAULT_COMMIT_TIME, tz: ZoneInfo = SFS_TIMEZONE) -> str:
    """Convert a 'YYYY-MM-DD' date into fast-import's raw date format.

    Raw format is '<seconds-since-epoch> <+/-HHMM>', which is what
    `git fast-import` expects by default for `author`/`committer` lines.
    """
    naive = datetime.fromisoformat(f"{iso_date}T{time_str}")
    aware = naive.replace(tzinfo=tz)
    epoch = int(aware.timestamp())
    offset_minutes = int(aware.utcoffset().total_seconds() // 60)
    sign = "+" if offset_minutes >= 0 else "-"
    offset_minutes = abs(offset_minutes)
    return f"{epoch} {sign}{offset_minutes // 60:02d}{offset_minutes % 60:02d}"


def _quote_path(path: str) -> str:
    """Quote a path per fast-import's C-style path quoting.

    Always quoting (rather than only when a special character is present)
    is valid per the grammar and avoids having to special-case spaces, etc.
    """
    escaped = path.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


class FastImportWriter:
    """Writes a git-fast-import stream to a live `git fast-import` process
    (or, for inspection/testing, to a plain file)."""

    def __init__(self, stream: BinaryIO, process: subprocess.Popen | None = None):
        self._stream = stream
        self._process = process
        self._commit_count = 0

    @classmethod
    def to_repo(cls, repo_dir: Path, verbose: bool = False) -> FastImportWriter:
        """Start `git fast-import` inside `repo_dir`, fed via its stdin.

        The resulting commits land as real refs in `repo_dir`'s object
        database as soon as `close()` returns successfully — no checkout or
        `git add` involved.
        """
        process = subprocess.Popen(
            ["git", "fast-import", "--stats" if verbose else "--quiet"],
            cwd=repo_dir,
            stdin=subprocess.PIPE,
        )
        return cls(process.stdin, process)

    @classmethod
    def to_file(cls, path: Path) -> FastImportWriter:
        """Write the stream to a plain file instead of a live process.

        Useful to inspect a generated stream, or to feed it into
        `git fast-import` later by hand (`git fast-import < path`).
        """
        return cls(open(path, "wb"))

    def _write_text(self, text: str) -> None:
        self._stream.write(text.encode("utf-8"))

    def _write_data(self, content: bytes) -> None:
        self._write_text(f"data {len(content)}\n")
        self._stream.write(content)
        # Trailing LF is optional per the grammar but recommended when the
        # raw data doesn't already end in one; harmless either way.
        self._write_text("\n")

    def commit(
        self,
        branch: str,
        message: str,
        author_date: str,
        committer_date: str,
        changes: list[FileChange],
        author_name: str = "SFS Processor",
        author_email: str = "sfs-processor@localhost",
        from_ref: str | None = None,
    ) -> None:
        """Emit one commit onto `refs/heads/<branch>`.

        `author_date`/`committer_date` must already be in fast-import's raw
        format (see `to_raw_git_date`). `from_ref` should only be passed for
        the very first commit written to a given branch in this stream —
        subsequent commits on the same branch chain automatically. Pass it
        when the branch should start from an existing commit (e.g. the
        target repo's `main` tip) rather than as a fresh root commit.
        """
        self._write_text(f"commit refs/heads/{branch}\n")
        self._write_text(f"author {author_name} <{author_email}> {author_date}\n")
        self._write_text(f"committer {author_name} <{author_email}> {committer_date}\n")
        self._write_data(message.encode("utf-8"))

        if from_ref is not None:
            self._write_text(f"from {from_ref}\n")

        for change in changes:
            quoted_path = _quote_path(change.path)
            if change.content is None:
                self._write_text(f"D {quoted_path}\n")
            else:
                self._write_text(f"M 100644 inline {quoted_path}\n")
                self._write_data(change.content)

        self._write_text("\n")
        self._commit_count += 1

    @property
    def commit_count(self) -> int:
        return self._commit_count

    def close(self, timeout: int = 3600) -> None:
        """Flush and close the stream, waiting for `git fast-import` to finish."""
        self._stream.close()
        if self._process is not None:
            returncode = self._process.wait(timeout=timeout)
            if returncode != 0:
                raise RuntimeError(f"git fast-import misslyckades med exit code {returncode}")
