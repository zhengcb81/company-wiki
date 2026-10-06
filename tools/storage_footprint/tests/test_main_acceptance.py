"""MAIN counterexamples for original protection and bounded metadata scans."""

import json
import os

import pytest

from storage_footprint import scan
from storage_footprint.classify import classify_file, retention_bucket
from storage_footprint.runner import run_scan
from fixtures import make_dir_link, write_tree


@pytest.mark.parametrize("rel", [
    "companies/acme/tmp/report.pdf", "companies/acme/build/report.pdf",
    "sectors/demo/.pytest_cache/source.txt", ".source_catalog/staging/tmp/call.txt",
    ".source_catalog/staging/database.db", "companies/acme/tmp/source.db",
])
def test_known_originals_never_get_disposal_advice(rel):
    category, _ = classify_file(rel, auto_dirs=set())
    assert category == "raw_originals"
    assert retention_bucket(category, rel) == "keep_now"


def test_root_auto_marker_cannot_reclassify_the_entire_repository(tmp_path):
    root = write_tree(tmp_path / "root", {
        "automation.log": "not a Store", "companies/acme/source.txt": "raw",
        "src/module.py": "code", "lane/automation.sqlite3": "store",
        "lane/work/prepared.json": "pending",
    })
    result = scan.scan_tree(root, max_files=100, max_seconds=5)
    assert result.category_files["raw_originals"] == 1
    assert result.category_files["git_code"] == 1
    assert result.category_files["auto_recovery_materials"] == 2


@pytest.mark.parametrize("seconds", [float("nan"), float("inf")])
def test_nonfinite_deadline_refused(tmp_path, seconds):
    root = write_tree(tmp_path / "root", {"x.txt": "x"})
    output = tmp_path / "report.json"
    code, _ = run_scan(project_root=root, max_files=10, max_seconds=seconds, output=output)
    assert code == 2
    assert not output.exists()


def test_directory_enumeration_checks_the_deadline(tmp_path, monkeypatch):
    root = write_tree(tmp_path / "root", {"x.txt": "x"})
    visited = []

    with os.scandir(root) as entries:
        real_entry = next(entries)

    class SlowDirectory:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def __iter__(self):
            for index in range(100):
                visited.append(index)
                yield real_entry

    ticks = iter(range(1000))
    monkeypatch.setattr(scan.os, "scandir", lambda _path: SlowDirectory())
    result = scan.scan_tree(root, max_files=10, max_seconds=3, clock=lambda: next(ticks))
    assert not result.complete
    assert result.stop_reason == "budget"
    assert len(visited) < 10


def test_explicit_root_link_is_refused_without_scanning_the_target(tmp_path, monkeypatch):
    outside = write_tree(tmp_path / "outside", {"data.txt": "outside"})
    link = tmp_path / "link"
    if not make_dir_link(link, outside):
        pytest.skip("directory links unavailable")

    def forbidden(*_args, **_kwargs):
        pytest.fail("root link target must not be traversed")

    monkeypatch.setattr(scan, "_scandir", forbidden)
    output = tmp_path / "report.json"
    code, _ = run_scan(project_root=link, max_files=10, max_seconds=5, output=output)
    assert code == 2
    assert not output.exists()


def test_classifier_rules_and_accounting_through_runner(tmp_path):
    spec = {
        "companies/acme/tmp/report.pdf": "original",
        ".source_catalog/staging/tmp/source.txt": "pending acquisition",
        "tmp/test/cache.txt": "scratch", "automation.log": "log",
    }
    root = write_tree(tmp_path / "root", spec)
    output = tmp_path / "report.json"
    code, _ = run_scan(project_root=root, max_files=100, max_seconds=5, output=output)
    assert code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    by_category = {row["category"]: row for row in payload["categories"]}
    assert by_category["raw_originals"]["files"] == 2
    assert by_category["tmp_test_cache"]["logical_path_bytes"] == len("scratch")
    assert sum(row["logical_path_bytes"] for row in payload["categories"]) == sum(map(len, spec.values()))
    assert payload["calls"]["deleted"] == 0
    assert all("审批" not in row["cost_or_condition"] for row in payload["retention_notes"])
