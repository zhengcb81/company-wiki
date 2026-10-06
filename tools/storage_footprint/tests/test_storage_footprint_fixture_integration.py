"""Fixture integration: exact known trees driven through the public runner.

The committed static fixture and the runtime fixture are scanned with generous
budgets; expectations are hand-written (not derived from the classifier) so a
rule regression cannot silently redefine success. Every run must leave the
fixture byte- and mtime-identical and produce only the report file.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from storage_footprint.classify import CATEGORIES
from storage_footprint.report import validate_report
from storage_footprint.runner import run_scan

from fixtures import (  # noqa: E402
    bucket_of,
    buckets_of,
    limits,
    snapshot_tree,
    write_tree,
)

pytestmark = pytest.mark.integration

STATIC_CATEGORIES = {
    "companies/demo/annual_note.txt": "raw_originals",
    "companies/demo/wiki/demo_timeline.md": "curated_final_summaries",
    "docs/plans/n6_note.md": "plans_reports",
    "README.md": "git_code",
    "src/app_module.py": "git_code",
    ".pytest_cache/scratch.txt": "tmp_test_cache",
    "mystery/thing.bin": "unknown",
}

RUNTIME_SPEC = {
    "companies/acme/brief.txt": "0123456789",
    "companies/acme/wiki/page.md": "abcdef",
    ".source_catalog/catalog.sqlite3": "y" * 16,
    ".source_catalog/staging/incoming.txt": "stage",
    "tmp/pytest-run/db.sqlite3": "z" * 8,
    "tmp/pytest-run/log.txt": "log",
    "lane/automation.sqlite3": "a" * 8,
    "lane/work/payload.json": "{}",
    "docs/plans/p.md": "#p",
    "src/mod.py": "V=1",
    "odd/tree/file.bin": "zz",
}

RUNTIME_CATEGORIES = {
    "companies/acme/brief.txt": "raw_originals",
    ".source_catalog/staging/incoming.txt": "raw_originals",
    "companies/acme/wiki/page.md": "curated_final_summaries",
    ".source_catalog/catalog.sqlite3": "databases",
    "tmp/pytest-run/db.sqlite3": "databases",
    "lane/automation.sqlite3": "auto_recovery_materials",
    "lane/work/payload.json": "auto_recovery_materials",
    "tmp/pytest-run/log.txt": "tmp_test_cache",
    "docs/plans/p.md": "plans_reports",
    "src/mod.py": "git_code",
    "odd/tree/file.bin": "unknown",
}


def _expected(spec_categories: dict[str, str], root: Path) -> dict[str, dict[str, int]]:
    expected = {name: {"files": 0, "logical_path_bytes": 0} for name in CATEGORIES}
    for rel, category in spec_categories.items():
        size = (root / rel).stat().st_size
        expected[category]["files"] += 1
        expected[category]["logical_path_bytes"] += size
    return expected


def test_static_fixture_scan_is_complete_exact_and_non_mutating(static_root, tmp_path):
    before = snapshot_tree(static_root)
    output = tmp_path / "out" / "report.json"
    code, stdout = run_scan(
        project_root=static_root, max_files=10000, max_seconds=60.0, output=output
    )
    assert code == 0, stdout
    assert stdout["status"] == "written"

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert validate_report(payload) == []
    assert payload["scope"]["complete"] is True
    assert payload["scope"]["stop_reason"] == "complete"
    assert payload["limits"] == limits(max_files=10000, max_seconds=60.0)

    expected = _expected(STATIC_CATEGORIES, static_root)
    for item in payload["categories"]:
        assert item["files"] == expected[item["category"]]["files"], item
        assert (
            item["logical_path_bytes"]
            == expected[item["category"]]["logical_path_bytes"]
        ), item
    total_files = sum(value["files"] for value in expected.values())
    total_bytes = sum(value["logical_path_bytes"] for value in expected.values())
    assert payload["totals"]["files_measured"] == total_files == 7
    assert payload["totals"]["logical_path_bytes"] == total_bytes
    assert payload["totals"]["unknown_files"] == 1
    assert payload["totals"]["skipped_files"] == 0
    assert payload["calls"] == {
        "original_body_reads": 0,
        "llm": 0,
        "network": 0,
        "deleted": 0,
    }

    assert snapshot_tree(static_root) == before
    assert [path.name for path in output.parent.iterdir()] == ["report.json"]


def test_runtime_fixture_all_categories_and_buckets(tmp_path):
    root = write_tree(tmp_path / "root", RUNTIME_SPEC)
    before = snapshot_tree(root)
    output = tmp_path / "out" / "report.json"
    code, stdout = run_scan(
        project_root=root, max_files=10000, max_seconds=60.0, output=output
    )
    assert code == 0, stdout
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert validate_report(payload) == []

    expected = _expected(RUNTIME_CATEGORIES, root)
    for item in payload["categories"]:
        assert item["files"] == expected[item["category"]]["files"], item
        assert (
            item["logical_path_bytes"]
            == expected[item["category"]]["logical_path_bytes"]
        ), item
    assert payload["totals"]["files_measured"] == len(RUNTIME_SPEC) == 11

    assert bucket_of(payload, "raw_originals") == "keep_now"
    assert bucket_of(payload, "curated_final_summaries") == "keep_now"
    assert bucket_of(payload, "auto_recovery_materials") == "undetermined"
    assert bucket_of(payload, "unknown") == "undetermined"
    assert bucket_of(payload, "tmp_test_cache") == "separate_disposal_review"
    assert buckets_of(payload, "databases") == {
        "keep_now",
        "separate_disposal_review",
    }

    for note in payload["retention_notes"]:
        assert note["reason"]
        assert note["gain_basis"]
        assert note["cost_or_condition"]
        if note["bucket"] == "separate_disposal_review":
            assert "上界" in note["gain_basis"]

    assert snapshot_tree(root) == before


def test_runtime_fixture_budget_stop_is_partial(tmp_path):
    root = write_tree(
        tmp_path / "root",
        {f"docs/plans/note-{index}.md": f"note-{index}" for index in range(6)},
    )
    before = snapshot_tree(root)
    output = tmp_path / "out" / "report.json"
    code, stdout = run_scan(
        project_root=root, max_files=3, max_seconds=60.0, output=output
    )
    assert code == 0, stdout
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert validate_report(payload) == []
    assert payload["scope"]["complete"] is False
    assert payload["scope"]["stop_reason"] == "budget"
    assert payload["totals"]["files_measured"] + payload["totals"]["skipped_files"] == 3
    assert any("partial" in note for note in payload["limitations"])
    assert snapshot_tree(root) == before


def test_directory_permission_failure_is_reported_not_hidden(tmp_path, monkeypatch):
    from storage_footprint import scan as scan_module

    root = write_tree(
        tmp_path / "root",
        {
            "companies/locked/report.txt": "x",
            "companies/open/note.txt": "yy",
            "docs/plans/p.md": "zzz",
        },
    )
    before = snapshot_tree(root)
    real_scandir = scan_module._scandir

    def guarded_scandir(path):
        if Path(path).name == "locked":
            raise PermissionError(13, "Permission denied")
        return real_scandir(path)

    monkeypatch.setattr(scan_module, "_scandir", guarded_scandir)
    output = tmp_path / "out" / "report.json"
    code, stdout = run_scan(
        project_root=root, max_files=1000, max_seconds=60.0, output=output
    )
    assert code == 0, stdout
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert validate_report(payload) == []
    assert payload["scope"]["stop_reason"] == "errors"
    assert payload["scope"]["complete"] is False
    assert payload["totals"]["files_measured"] == 2
    assert payload["errors"][0]["path"] == "companies/locked"
    assert snapshot_tree(root) == before
