"""MAIN acceptance: actual byte limits and original/output isolation."""

from __future__ import annotations

import hashlib
import os
import json
import subprocess
import sys
from pathlib import Path

import pytest

from raw_duplicate_audit import core
from raw_duplicate_audit.assessment import run_assessment
from raw_duplicate_audit.classify import account_group, fill_allocations
from raw_duplicate_audit.core import Budget, BudgetExceeded, hash_file, write_json
from raw_duplicate_audit.verify import verify_group
from raw_duplicate_audit.report import apply_size_cap
from test_raw_duplicate_audit_accounting import _group, _member, _record
from test_raw_duplicate_audit_fixture_set import _run, build_fixture


def test_non_chunk_aligned_read_cap_is_never_exceeded(tmp_path):
    target = tmp_path / "raw.bin"
    target.write_bytes(b"a" * (2 * core.HASH_CHUNK_BYTES))
    budget = Budget(max_read_bytes=123, deadline_seconds=30)
    with pytest.raises(BudgetExceeded):
        hash_file(target, budget)
    assert budget.read_bytes == 123


@pytest.mark.parametrize("size", [0, 123, core.HASH_CHUNK_BYTES])
def test_exact_eof_budget_can_complete_without_an_extra_read(tmp_path, size):
    target = tmp_path / "raw.bin"
    data = b"b" * size
    target.write_bytes(data)
    budget = Budget(max_read_bytes=size, deadline_seconds=30)
    assert hash_file(target, budget) == hashlib.sha256(data).hexdigest()
    assert budget.read_bytes == size
    assert not budget.limits_hit()


@pytest.mark.parametrize("destination", ["raw", "config", "catalog", "same_output"])
def test_local_output_never_writes_protected_inputs(tmp_path, destination):
    fixture = build_fixture(tmp_path, with_duplicates=False)
    output = fixture["out_dir"] / "report.json"
    destinations = {
        "raw": fixture["raw"] / "new_report.json",
        "config": fixture["config_path"],
        "catalog": fixture["catalog_dir"] / "catalog.sqlite3",
        "same_output": output,
    }
    target = destinations[destination]
    before = target.read_bytes() if target.exists() else None
    result = _run(fixture, "scan", output_path=output,
                  local_output_path=target, overwrite=True)
    assert result["status"] == "refused"
    assert (target.read_bytes() if target.exists() else None) == before
    assert not output.exists()


@pytest.mark.parametrize("local", [False, True])
def test_overwrite_does_not_destroy_unknown_old_files(tmp_path, local):
    fixture = build_fixture(tmp_path, with_duplicates=False)
    target = fixture["out_dir"] / "other.json"
    target.write_bytes(b"owner original")
    kwargs = {"local_output_path": target} if local else {"output_path": target}
    result = _run(fixture, "scan", overwrite=True, **kwargs)
    assert result["status"] == "refused"
    assert target.read_bytes() == b"owner original"


def test_atomic_report_does_not_clobber_unknown_adjacent_tmp(tmp_path):
    target = tmp_path / "report.json"
    adjacent = tmp_path / "report.json.tmp"
    adjacent.write_bytes(b"another process owns this")
    write_json(target, {"report": True})
    assert adjacent.read_bytes() == b"another process owns this"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["report.json", "report.json.tmp"]


def test_cloud_candidate_has_no_duplicate_upper_bound_or_allocation(monkeypatch):
    a = _member(_record("a", "a"), normalized="a", identity=(1, 1))
    b = _member(_record("b", "b"), normalized="b", identity=(1, 2))
    a.hydrate_risk = True
    a.path, b.path = Path("a"), Path("b")
    a.allocated_bytes = b.allocated_bytes = None
    group = _group(a, b)
    group.account = account_group(group)
    assert group.account["logical_duplicate_bytes"] is None
    calls = []
    monkeypatch.setattr("raw_duplicate_audit.classify.allocation_size", lambda p: calls.append(p))
    fill_allocations([group])
    assert not calls


def _single_group(target: Path):
    record = _record("a", "raw.bin")
    member = _member(record, normalized=str(core.normalized(target)),
                     identity=core.physical_identity(target))
    member.path = target
    member.size = target.stat().st_size
    member.observed_mtime_ns = target.stat().st_mtime_ns
    member.record = type(record)(**{**record.__dict__,
        "content_sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
    return _group(member)


def test_partial_file_read_is_accounted_in_group_and_file(tmp_path):
    target = tmp_path / "raw.bin"
    target.write_bytes(b"c" * 4096)
    group = _single_group(target)
    budget = Budget(max_read_bytes=321, deadline_seconds=30)
    assert verify_group(group, budget) == "read_bytes"
    assert group.verification["bytes_read"] == budget.read_bytes == 321
    assert group.verification["files"][0]["bytes_read"] == 321
    assert group.verification["status"] != "verified_identical"


def test_cloud_attribute_changed_after_scan_is_not_opened(tmp_path, monkeypatch):
    target = tmp_path / "raw.bin"
    target.write_bytes(b"d" * 1000)
    group = _single_group(target)
    monkeypatch.setattr(core, "file_attributes", lambda _p: core.FILE_ATTRIBUTE_UNPINNED)
    budget = Budget(max_read_bytes=4096, deadline_seconds=30)
    assert verify_group(group, budget) is None
    assert group.verification["status"] == "skipped_cloud_placeholder"
    assert budget.read_bytes == 0


def test_identity_changed_after_scan_is_not_verified(tmp_path):
    target = tmp_path / "raw.bin"
    target.write_bytes(b"e" * 1000)
    group = _single_group(target)
    # Simulate a replacement of equal bytes/mtime; the pinned physical ID differs.
    group.members[0].identity = (-1, -1)
    budget = Budget(max_read_bytes=4096, deadline_seconds=30)
    assert verify_group(group, budget) is None
    assert group.verification["status"] == "changed"
    assert budget.read_bytes == 0


@pytest.mark.skipif(os.name != "nt", reason="Windows allocation metric")
def test_windows_optional_allocation_is_unknown_instead_of_logical_size(tmp_path):
    target = tmp_path / "raw.bin"
    target.write_bytes(b"f" * 1157)
    assert core.allocation_size(target) is None


def test_invalid_config_never_replaced_by_a_refusal_report(tmp_path):
    target = tmp_path / "config.yaml"
    target.write_bytes(b"not valid configuration")
    report = run_assessment(config_path=target, output_path=target, overwrite=True)
    assert report["status"] == "refused"
    assert target.read_bytes() == b"not valid configuration"


@pytest.mark.parametrize("cap, expected", [(321, "partial"), (1024 * 1024, "succeeded")])
def test_actual_cli_readonly_and_budget_contract(tmp_path, cap, expected):
    fixture = build_fixture(tmp_path)
    watched = [*fixture["files"], fixture["config_path"]]
    before = {p: (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_size,
                  p.stat().st_mtime_ns) for p in watched}
    database = fixture["catalog_dir"] / "catalog.sqlite3"
    db_before = (database.stat().st_size, database.stat().st_mtime_ns)
    directory_before = sorted(p.name for p in fixture["catalog_dir"].iterdir())
    output = fixture["out_dir"] / "cli.json"
    local = fixture["out_dir"] / "local.json"
    entry = Path(__file__).resolve().parents[1] / "cli.py"
    result = subprocess.run([sys.executable, "-B", str(entry), "verify",
                             "--config", str(fixture["config_path"]),
                             "--project-root", str(fixture["project"]),
                             "--output", str(output), "--local-output", str(local),
                             "--max-read-bytes", str(cap)],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == expected
    assert report["read_bytes"] <= cap
    assert report["deleted_bytes"] == 0
    assert report["protected_unchanged"] is True
    assert local.is_file()
    if expected == "partial":
        assert report["read_bytes"] == cap
        assert report["verified_duplicate_bytes"] == 0
    else:
        assert report["verified_duplicate_bytes"] > 0
    after = {p: (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_size,
                 p.stat().st_mtime_ns) for p in watched}
    assert before == after
    assert db_before == (database.stat().st_size, database.stat().st_mtime_ns)
    assert directory_before == sorted(p.name for p in fixture["catalog_dir"].iterdir())


def test_io_diagnostic_does_not_put_machine_path_in_git_report(tmp_path, monkeypatch):
    target = tmp_path / "raw.bin"
    target.write_bytes(b"a" * 1000)
    group = _single_group(target)
    def denied(_path, _budget):
        raise PermissionError(13, "denied", str(target))
    monkeypatch.setattr("raw_duplicate_audit.verify.hash_file", denied)
    verify_group(group, Budget(max_read_bytes=4096, deadline_seconds=30))
    assert group.verification["status"] == "acl_denied"
    assert group.verification["files"][0]["detail"] == "PermissionError(errno=13)"


def test_report_byte_cap_also_trims_non_group_diagnostics():
    report = {"duplicate_groups": [], "counts": {},
              "diagnostics": [{"message": "a" * 512}] * 5000,
              "similar_groups": []}
    apply_size_cap(report, limits_hit=[])
    data = json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8")
    assert len(data) <= core.MAX_REPORT_BYTES
    assert report["truncated"]["report_bytes"] == len(data)
    assert report["truncated"]["dropped_diagnostics"] > 0
