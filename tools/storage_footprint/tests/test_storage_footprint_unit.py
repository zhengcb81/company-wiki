"""Unit counter-examples for the N6-FOOTPRINT read-only storage scan (RED first).

Every test here encodes a rule from INPUT_CARD: no double counting, originals
kept apart from tmp material, reparse/cloud entries stay unknown, budgets stop
exactly, partial results are never labelled complete, physical bytes are never
faked, outputs are refused or never clobbered, and zero original body reads.
"""

from __future__ import annotations

import builtins
import io
import json
import os
import sqlite3
from pathlib import Path

import pytest

from storage_footprint import classify, core, report as report_module, scan
from storage_footprint.classify import classify_file, retention_bucket
from storage_footprint.core import MAX_PATH_CHARS, REPORT_SCHEMA, truncate_path
from storage_footprint.report import (
    build_report,
    enforce_report_budget,
    validate_report,
)
from storage_footprint.runner import run_scan
from storage_footprint.scan import scan_tree

from fixtures import (  # noqa: E402
    bucket_of,
    category_bytes,
    category_files,
    limits,
    make_dir_link,
    snapshot_tree,
    write_tree,
)

pytestmark = pytest.mark.unit

BASIC_SPEC = {
    "companies/acme/brief.txt": "0123456789",
    "companies/acme/wiki/timeline.md": "abcdef",
    "tmp/scratch/cache.txt": "1234567",
    "src/mod.py": "print(1)\n",
    "docs/plans/plan.md": "# plan\n",
    ".source_catalog/catalog.sqlite3": "x" * 11,
    ".source_catalog/derived/final.md": "final",
    "unknown_tree/data.bin": "ab",
}


def _scan(root: Path, *, max_files: int = 10000, max_seconds: float = 60.0, clock=None):
    kwargs = {"max_files": max_files, "max_seconds": max_seconds}
    if clock is not None:
        kwargs["clock"] = clock
    return scan_tree(root, **kwargs)


def _report(root: Path, result, *, max_files: int = 10000, max_seconds: float = 60.0):
    return build_report(
        result,
        project_root_text=str(root),
        limits=limits(max_files=max_files, max_seconds=max_seconds),
    )


def test_category_totals_never_double_count(tmp_path):
    root = write_tree(tmp_path / "root", BASIC_SPEC)
    result = _scan(root)
    payload = _report(root, result)

    problems = validate_report(payload)
    assert problems == [], problems
    assert payload["schema_version"] == REPORT_SCHEMA
    assert payload["scope"]["complete"] is True
    assert payload["scope"]["stop_reason"] == "complete"

    assert len(payload["categories"]) == len(classify.CATEGORIES)
    assert (
        sum(item["files"] for item in payload["categories"])
        == payload["totals"]["files_measured"]
    )
    assert (
        sum(item["logical_path_bytes"] for item in payload["categories"])
        == payload["totals"]["logical_path_bytes"]
    )
    assert payload["totals"]["files_measured"] == len(BASIC_SPEC)
    assert payload["totals"]["logical_path_bytes"] == sum(
        len(v) for v in BASIC_SPEC.values()
    )
    assert payload["totals"]["unknown_files"] == 1


def test_originals_final_summaries_and_tmp_stay_separate(tmp_path):
    root = write_tree(tmp_path / "root", BASIC_SPEC)
    payload = _report(root, _scan(root))

    assert category_files(payload, "raw_originals") == 1
    assert category_bytes(payload, "raw_originals") == 10
    assert category_files(payload, "curated_final_summaries") == 2
    assert category_bytes(payload, "curated_final_summaries") == 11
    assert category_bytes(payload, "tmp_test_cache") == 7
    assert category_bytes(payload, "databases") == 11
    assert category_bytes(payload, "plans_reports") == 7
    assert category_bytes(payload, "git_code") == 9
    assert category_bytes(payload, "auto_recovery_materials") == 0

    for note in payload["retention_notes"]:
        if note["category"] == "raw_originals":
            assert note["bucket"] == "keep_now"
            assert note["files"] == 1
            assert note["gain_basis"]


def test_unmatched_path_is_unknown():
    assert classify_file("odd/where/file.bin", auto_dirs=set()) == (
        "unknown",
        "unmatched",
    )
    assert classify_file("companies/acme/note.txt", auto_dirs=set()) == (
        "raw_originals",
        "raw_tree",
    )
    assert classify_file(".source_catalog/derived/final.md", auto_dirs=set()) == (
        "curated_final_summaries",
        "catalog_final_artifacts",
    )
    assert classify_file("tmp/x/job.db", auto_dirs=set()) == ("databases", "db_file")


def test_hardlink_paths_reported_as_metadata_candidate(tmp_path):
    root = tmp_path / "root"
    target = root / "companies" / "a" / "x.txt"
    write_tree(root, {"companies/a/x.txt": "hardlink-target-bytes"})
    alias = root / "companies" / "a" / "y.txt"
    try:
        os.link(target, alias)
    except (OSError, NotImplementedError, AttributeError):
        pytest.skip("hardlinks unavailable on this filesystem")

    payload = _report(root, _scan(root))
    duplicates = payload["duplicate_path_links"]
    assert duplicates["identity_available"] is True
    assert duplicates["groups"] == 1
    assert duplicates["paths"] == 2
    assert duplicates["extra_logical_bytes"] == len("hardlink-target-bytes")
    assert "st_dev" in duplicates["method"] and "st_ino" in duplicates["method"]
    assert "not" in duplicates["note"] or "未" in duplicates["note"]
    assert payload["totals"]["logical_path_bytes"] == 2 * len("hardlink-target-bytes")


def test_hardlink_identity_unknown_without_inode(tmp_path, monkeypatch):
    root = write_tree(tmp_path / "root", {"companies/a/x.txt": "bytes"})
    monkeypatch.setattr(scan, "file_identity", lambda _st: None)
    payload = _report(root, _scan(root))
    duplicates = payload["duplicate_path_links"]
    assert duplicates["identity_available"] is False
    assert duplicates["groups"] == 0
    assert duplicates["paths"] == 0
    assert duplicates["extra_logical_bytes"] == 0
    assert duplicates["unknown_identity_files"] == payload["totals"]["files_measured"]


def test_reparse_link_out_of_root_is_never_followed(tmp_path):
    outside = write_tree(
        tmp_path / "outside", {"secret/keep_out.txt": "OUTSIDE-SECRET"}
    )
    root = write_tree(tmp_path / "root", {"companies/a/keep.txt": "inside"})
    link = root / "companies" / "a" / "escape"
    if not make_dir_link(link, outside):
        pytest.skip("directory links unavailable on this platform")

    payload = _report(root, _scan(root))
    assert payload["totals"]["files_measured"] == 1
    assert payload["totals"]["logical_path_bytes"] == len("inside")
    assert payload["totals"]["skipped_links"] >= 1
    assert payload["totals"]["skipped_files"] >= 1
    assert payload["scope"]["complete"] is True


def test_cloud_placeholder_entry_is_skipped_not_measured(tmp_path, monkeypatch):
    root = write_tree(
        tmp_path / "root",
        {"companies/a/cloudy.bin": "cloud", "companies/a/normal.txt": "normal"},
    )
    real_entry_state = scan.entry_state

    def fake_entry_state(st, name):
        if name == "cloudy.bin":
            return "cloud"
        return real_entry_state(st, name)

    monkeypatch.setattr(scan, "entry_state", fake_entry_state)
    payload = _report(root, _scan(root))

    assert payload["totals"]["skipped_cloud_placeholders"] == 1
    assert payload["totals"]["skipped_files"] == 1
    assert payload["totals"]["files_measured"] == 1
    assert payload["totals"]["logical_path_bytes"] == len("normal")
    assert category_files(payload, "unknown") == 0
    assert any(
        sample == {"path": "companies/a/cloudy.bin", "kind": "cloud"}
        for sample in payload["skipped_samples"]
    ), payload["skipped_samples"]
    assert (
        payload["totals"]["skipped_links"]
        + payload["totals"]["skipped_cloud_placeholders"]
        == payload["totals"]["skipped_files"]
    )


def test_directory_permission_error_marks_partial(tmp_path, monkeypatch):
    root = write_tree(
        tmp_path / "root",
        {"locked/inner.txt": "x", "open/ok.txt": "yy", "top.txt": "zzz"},
    )
    real_scandir = scan._scandir

    def guarded_scandir(path):
        if Path(path).name == "locked":
            raise PermissionError(13, "Permission denied")
        return real_scandir(path)

    monkeypatch.setattr(scan, "_scandir", guarded_scandir)
    output = tmp_path / "out" / "report.json"
    code, stdout = run_scan(
        project_root=root, max_files=1000, max_seconds=60.0, output=output
    )
    assert code == 0, stdout
    assert stdout["status"] == "written"
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["scope"]["complete"] is False
    assert payload["scope"]["stop_reason"] == "errors"
    assert payload["totals"]["files_measured"] == 2
    assert payload["errors"], payload["errors"]
    entry = payload["errors"][0]
    assert entry["path"] == "locked"
    assert "PermissionError" in entry["error"]
    assert str(root) not in entry["error"]
    assert str(root) not in entry["path"]


def test_file_budget_stops_exactly_at_limit(tmp_path):
    spec = {f"docs/file{i:02d}.md": f"body-{i}" for i in range(10)}
    root = write_tree(tmp_path / "root", spec)
    result = _scan(root, max_files=4)
    payload = _report(root, result, max_files=4)

    assert payload["totals"]["files_measured"] + payload["totals"]["skipped_files"] == 4
    assert payload["scope"]["stop_reason"] == "budget"
    assert payload["scope"]["complete"] is False
    assert payload["totals"]["entries_seen"] >= 4
    assert any("partial" in note for note in payload["limitations"])


def test_deadline_budget_stops_scan(tmp_path):
    root = write_tree(tmp_path / "root", {"docs/a.md": "x", "docs/b.md": "y"})

    class SteppingClock:
        def __init__(self, step: float) -> None:
            self.step = step
            self.now = 0.0

        def __call__(self) -> float:
            self.now += self.step
            return self.now

    result = _scan(root, max_seconds=0.5, clock=SteppingClock(1.0))
    payload = _report(root, result, max_seconds=0.5)
    assert payload["scope"]["stop_reason"] == "budget"
    assert payload["scope"]["complete"] is False


def test_partial_report_is_never_labeled_complete(tmp_path):
    root = write_tree(tmp_path / "root", {f"docs/file{i}.md": "x" for i in range(6)})
    payload = _report(root, _scan(root, max_files=2), max_files=2)
    assert payload["scope"]["complete"] is False
    assert payload["scope"]["stop_reason"] == "budget"
    assert payload["limits"] == {"max_files": 2, "max_seconds": 60.0}
    assert any("partial" in note for note in payload["limitations"])


def test_allocated_bytes_stay_null_with_reason(tmp_path):
    root = write_tree(tmp_path / "root", {"companies/a/x.txt": "0123456789"})
    payload = _report(root, _scan(root))
    assert payload["totals"]["allocated_bytes"] is None
    joined = " ".join(payload["limitations"])
    assert "allocated" in joined or "分配" in joined


def test_package_contains_no_physical_size_fakery():
    package_dir = Path(__file__).resolve().parents[1]
    for path in sorted(package_dir.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert "GetCompressedFileSize" not in source, path.name
        assert "st_blocks" not in source, path.name


def test_output_inside_root_is_refused(tmp_path):
    root = write_tree(tmp_path / "root", {"companies/a/x.txt": "0123456789"})
    before = snapshot_tree(root)
    output = root / "report.json"
    code, stdout = run_scan(
        project_root=root, max_files=100, max_seconds=30.0, output=output
    )
    assert code == 2
    assert stdout["status"] == "refused"
    assert stdout["reason"] == "report_path_overlaps_data"
    assert not output.exists()
    assert snapshot_tree(root) == before


def test_unknown_existing_output_is_refused_unchanged(tmp_path):
    root = write_tree(tmp_path / "root", {"companies/a/x.txt": "0123456789"})
    output = tmp_path / "out" / "report.json"
    output.parent.mkdir(parents=True)
    foreign = json.dumps({"schema_version": "someone-elses/9"}).encode("utf-8")
    output.write_bytes(foreign)
    code, stdout = run_scan(
        project_root=root, max_files=100, max_seconds=30.0, output=output
    )
    assert code == 2
    assert stdout["reason"] == "output_exists_unknown"
    assert output.read_bytes() == foreign


def test_own_report_can_be_rewritten(tmp_path):
    root = write_tree(tmp_path / "root", {"companies/a/x.txt": "0123456789"})
    output = tmp_path / "out" / "report.json"
    first, _ = run_scan(
        project_root=root, max_files=100, max_seconds=30.0, output=output
    )
    second, stdout = run_scan(
        project_root=root, max_files=100, max_seconds=30.0, output=output
    )
    assert first == 0 and second == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == REPORT_SCHEMA
    assert stdout["status"] == "written"


def test_report_size_budget_truncates():
    errors = [{"path": "dir/" + "p" * 9000, "error": "E" * 9000} for _ in range(400)]
    payload = {
        "schema_version": REPORT_SCHEMA,
        "scope": {},
        "limits": {},
        "totals": {},
        "categories": [],
        "top_directories": [],
        "retention_notes": [],
        "errors": errors,
        "calls": {},
        "limitations": [],
    }
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    assert len(raw) > core.MAX_REPORT_BYTES
    smaller, notes = enforce_report_budget(payload, max_bytes=core.MAX_REPORT_BYTES)
    assert (
        len(json.dumps(smaller, ensure_ascii=False).encode("utf-8"))
        <= core.MAX_REPORT_BYTES
    )
    assert any("truncated" in note for note in notes)
    assert smaller["limitations"]


def test_error_paths_hard_truncated():
    long_path = "a/" * 400 + "z.txt"
    truncated = truncate_path(long_path)
    assert len(truncated) <= MAX_PATH_CHARS
    assert truncated.endswith("...[truncated]")
    assert len(truncate_path("short.txt")) == len("short.txt")


def test_failed_report_write_leaves_no_temp_output(tmp_path, monkeypatch):
    output = tmp_path / "out" / "report.json"
    output.parent.mkdir(parents=True)
    real_replace = os.replace

    def broken_replace(*_args, **_kwargs):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(os, "replace", broken_replace)
    with pytest.raises(OSError):
        core.write_report(output, {"schema_version": REPORT_SCHEMA})
    monkeypatch.setattr(os, "replace", real_replace)
    assert not output.exists()
    assert list(output.parent.iterdir()) == []


def test_runner_cleans_up_when_report_exceeds_budget(tmp_path, monkeypatch):
    root = write_tree(tmp_path / "root", {"companies/a/x.txt": "0123456789"})
    output = tmp_path / "out" / "report.json"
    monkeypatch.setattr(report_module, "MAX_REPORT_BYTES", 32)
    code, stdout = run_scan(
        project_root=root, max_files=100, max_seconds=30.0, output=output
    )
    assert code == 1
    assert stdout["status"] == "error"
    assert not output.exists()
    assert not output.parent.exists()


def test_scan_never_opens_original_bodies(tmp_path, monkeypatch):
    root = write_tree(tmp_path / "root", BASIC_SPEC)
    real_open = builtins.open

    def guarded_open(file, mode="r", *args, **kwargs):
        text = os.path.realpath(str(file))
        if text.startswith(os.path.realpath(str(root)) + os.sep):
            raise AssertionError(f"body read attempted: {file}")
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(io, "open", guarded_open)
    try:
        payload = _report(root, _scan(root))
    finally:
        monkeypatch.undo()
    assert payload["calls"] == {
        "original_body_reads": 0,
        "llm": 0,
        "network": 0,
        "deleted": 0,
    }


def test_databases_are_measured_but_never_opened(tmp_path, monkeypatch):
    root = write_tree(
        tmp_path / "root",
        {
            ".source_catalog/catalog.sqlite3": "z" * 64,
            "companies/a/x.txt": "0123456789",
        },
    )
    calls = {"connect": 0}

    def forbidden(*_args, **_kwargs):
        calls["connect"] += 1
        raise AssertionError("production SQLite must not be opened")

    monkeypatch.setattr(sqlite3, "connect", forbidden)
    payload = _report(root, _scan(root))
    assert calls["connect"] == 0
    assert category_bytes(payload, "databases") == 64


def test_auto_recovery_materials_are_never_deletable(tmp_path):
    root = write_tree(
        tmp_path / "root",
        {
            "lane/automation.sqlite3": "a" * 32,
            "lane/automation.sqlite3-wal": "",
            "lane/request.json": "{}",
            "lane/work/payload.json": "{'a': 1}",
        },
    )
    payload = _report(root, _scan(root))
    assert category_files(payload, "auto_recovery_materials") == 4
    assert category_files(payload, "databases") == 0
    assert bucket_of(payload, "auto_recovery_materials") == "undetermined"
    note = next(
        n
        for n in payload["retention_notes"]
        if n["category"] == "auto_recovery_materials"
    )
    assert "mtime" in note["reason"]
    assert note["bucket"] != "separate_disposal_review"


def test_calls_counters_are_always_zero(tmp_path):
    root = write_tree(tmp_path / "root", BASIC_SPEC)
    payload = _report(root, _scan(root))
    assert set(payload["calls"]) == {"original_body_reads", "llm", "network", "deleted"}
    assert all(value == 0 for value in payload["calls"].values())


def test_report_paths_are_root_relative(tmp_path):
    root = write_tree(tmp_path / "root", {"companies/a/x.txt": "0123456789"})
    payload = _report(root, _scan(root))
    assert payload["scope"]["project_root"] == str(root)
    for item in payload["top_directories"]:
        assert ":" not in item["path"]
        assert not item["path"].startswith("/")
    for entry in payload["errors"]:
        assert str(root) not in entry["path"]
    for note in payload["retention_notes"]:
        assert "path" not in note


def test_invalid_root_is_refused(tmp_path):
    code, stdout = run_scan(
        project_root=tmp_path / "does-not-exist",
        max_files=10,
        max_seconds=5.0,
        output=tmp_path / "out.json",
    )
    assert code == 2
    assert stdout["reason"] == "invalid_root"


def test_invalid_limits_are_refused(tmp_path):
    root = write_tree(tmp_path / "root", {"companies/a/x.txt": "0123456789"})
    cases = [(0, 5.0), (10, 0.0), (10, -1.0)]
    for index, (files, seconds) in enumerate(cases):
        code, stdout = run_scan(
            project_root=root,
            max_files=files,
            max_seconds=seconds,
            output=tmp_path / f"out-{index}.json",
        )
        assert code == 2, (files, seconds)
        assert stdout["reason"] == "invalid_limits", (files, seconds)


def test_retention_buckets_cover_every_category(tmp_path):
    root = write_tree(tmp_path / "root", BASIC_SPEC)
    payload = _report(root, _scan(root))
    buckets = {note["bucket"] for note in payload["retention_notes"]}
    assert buckets <= {"keep_now", "separate_disposal_review", "undetermined"}
    assert retention_bucket("raw_originals", "companies/a/x.txt") == "keep_now"
    assert (
        retention_bucket("tmp_test_cache", "tmp/x/y.txt") == "separate_disposal_review"
    )
    assert retention_bucket("databases", "tmp/x/y.db") == "separate_disposal_review"
    assert retention_bucket("databases", ".source_catalog/y.sqlite3") == "keep_now"
    assert (
        retention_bucket("auto_recovery_materials", "lane/request.json")
        == "undetermined"
    )
    assert retention_bucket("unknown", "odd/tree/file.bin") == "undetermined"
