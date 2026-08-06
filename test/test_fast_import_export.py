#!/usr/bin/env python3
"""Tests for the fast-import based export orchestrator.

These exercise `_init_commit_events` and `_temporal_commit_events` — the
functions that turn source JSON / marker markdown into globally-sortable
`CommitEvent`s — without touching git or a network. `convert_to_markdown` is
monkeypatched since its own parsing behaviour is exercised elsewhere; here we
only care that its output is routed into the right path/date/message.
"""

import json

import pytest

from exporters.git.fast_import_export import _init_commit_events, _temporal_commit_events


def _stub_convert_to_markdown(content: str):
    def _convert(data, fetch_predocs_from_api=False, apply_links=False):
        return content

    return _convert


@pytest.mark.unit
class TestInitCommitEvents:
    def test_produces_one_event_with_expected_path_date_and_message(self, tmp_path, monkeypatch):
        data = {
            "beteckning": "2010:100",
            "beteckningSortable": "2010:100",
            "rubrik": "Test förordning",
            "fulltext": {"utfardadDateTime": "2010-01-15"},
        }
        json_file = tmp_path / "sfs-2010-100.json"
        json_file.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr(
            "sfs_processor.convert_to_markdown", _stub_convert_to_markdown("# Test förordning\n\nInnehåll.\n")
        )

        events = _init_commit_events([json_file], output_dir=None, verbose=False)

        assert len(events) == 1
        event = events[0]
        assert event.date == "2010-01-15"
        assert event.path == "2010/sfs-2010-100.md"
        assert "Test förordning" in event.message
        assert "Innehåll." in event.content

    def test_writes_local_reference_copy_when_output_dir_given(self, tmp_path, monkeypatch):
        data = {
            "beteckning": "2010:100",
            "beteckningSortable": "2010:100",
            "rubrik": "Test förordning",
            "fulltext": {"utfardadDateTime": "2010-01-15"},
        }
        json_file = tmp_path / "sfs-2010-100.json"
        json_file.write_text(json.dumps(data), encoding="utf-8")
        output_dir = tmp_path / "out"
        monkeypatch.setattr(
            "sfs_processor.convert_to_markdown", _stub_convert_to_markdown("# Test förordning\n\nInnehåll.\n")
        )

        _init_commit_events([json_file], output_dir=output_dir, verbose=False)

        assert (output_dir / "2010" / "sfs-2010-100.md").exists()

    def test_skips_document_missing_required_fields(self, tmp_path, monkeypatch):
        # No 'rubrik' -> plan_init_commit raises ValueError, which is caught and skipped.
        data = {"beteckning": "2010:100", "fulltext": {"utfardadDateTime": "2010-01-15"}}
        json_file = tmp_path / "broken.json"
        json_file.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr("sfs_processor.convert_to_markdown", _stub_convert_to_markdown("# X\n\nY\n"))

        events = _init_commit_events([json_file], output_dir=None, verbose=False)

        assert events == []

    def test_skips_unparsable_json_file(self, tmp_path):
        json_file = tmp_path / "not-json.json"
        json_file.write_text("{not valid json", encoding="utf-8")

        events = _init_commit_events([json_file], output_dir=None, verbose=False)

        assert events == []


def _marker_document(*sections: str) -> str:
    body = "\n\n".join(sections)
    return f"""---
beteckning: "2010:100"
rubrik: Test förordning
---

<article>

{body}

</article>
"""


@pytest.mark.unit
class TestTemporalCommitEvents:
    def test_produces_one_event_per_change_date(self, tmp_path):
        year_dir = tmp_path / "2010"
        year_dir.mkdir()
        md_file = year_dir / "sfs-2010-100-markers.md"
        md_file.write_text(
            _marker_document(
                '<section id="1" class="paragraf" selex:ikraft_datum="2015-06-01">\n\n## 1 §\n\nInnehåll.\n\n</section>'
            ),
            encoding="utf-8",
        )

        events = _temporal_commit_events(tmp_path, from_date=None, to_date=None)

        assert len(events) == 1
        assert events[0].date == "2015-06-01"
        assert events[0].path == "2010/sfs-2010-100.md"

    def test_filters_out_of_range_dates(self, tmp_path):
        year_dir = tmp_path / "2010"
        year_dir.mkdir()
        md_file = year_dir / "sfs-2010-100-markers.md"
        md_file.write_text(
            _marker_document(
                '<section id="1" class="paragraf" selex:ikraft_datum="2010-06-01">\n\n## 1 §\n\nA.\n\n</section>',
                '<section id="2" class="paragraf" selex:ikraft_datum="2030-06-01">\n\n## 2 §\n\nB.\n\n</section>',
            ),
            encoding="utf-8",
        )

        events = _temporal_commit_events(tmp_path, from_date="2020-01-01", to_date="2020-12-31")

        assert events == []

    def test_skips_files_without_selex_tags(self, tmp_path):
        md_file = tmp_path / "plain.md"
        md_file.write_text('---\nbeteckning: "2010:1"\n---\n\nNo tags here.\n', encoding="utf-8")

        events = _temporal_commit_events(tmp_path, None, None)

        assert events == []
