"""Integration: isolated real-schema catalog, real files and a real hardlink.

The card-required shapes live in one fixture: one file with three location
references, a hardlink with two names, two distinct physical copies with
identical bytes, same size but different bytes, a wrong registered SHA, a file
that changes after the scan, and a file whose read access is denied.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from company_wiki.source_catalog.store import CatalogStore
from company_wiki.source_contract.source_manifest import source_id_for_sha256
from raw_duplicate_audit.assessment import run_assessment
from raw_duplicate_audit.catalog import load_inputs, open_reader, read_locations
from raw_duplicate_audit.classify import (
    account_group,
    build_groups,
    enforce_containment,
    fill_allocations,
    observe,
)
from raw_duplicate_audit.core import Budget, sha256_file
from raw_duplicate_audit.report import report_contains_forbidden_claims
from raw_duplicate_audit.verify import verify_group

NOW = "2026-01-01T00:00:00Z"
ROOT_ID = "root_a"
WRONG_SHA = "c" * 64

SIZE_SAME_PATH = 1000
SIZE_HARDLINK = 2000
SIZE_COPIES = 3000
SIZE_SIMILAR = 777
SIZE_WRONG_SHA = 5000
SIZE_CHANGING = 6000
SIZE_ACL = 7000

EXPECTED_UPPER_BOUND = SIZE_COPIES + SIZE_WRONG_SHA + SIZE_CHANGING + SIZE_ACL

CONFIG_TEXT = """schema_version: "1.0"
catalog_dir: "${PROJECT_ROOT}/catalog"
reusable_root_kinds: [company_raw, directory]
roots:
  - root_id: root_a
    kind: company_raw
    path: "${PROJECT_ROOT}/raw"
    priority: 10
"""


def _insert(connection, table: str, values: dict) -> None:
    have = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    use = {key: value for key, value in values.items() if key in have}
    connection.execute(
        f"INSERT OR IGNORE INTO {table} ({','.join(use)})"
        f" VALUES ({','.join('?' * len(use))})",
        tuple(use.values()),
    )


def _write(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def build_fixture(tmp_path: Path, *, with_duplicates: bool = True) -> dict:
    project = tmp_path / "proj"
    raw = project / "raw"
    catalog_dir = project / "catalog"
    out_dir = project / "out"
    raw.mkdir(parents=True)
    out_dir.mkdir(parents=True)
    config_path = project / "config" / "source_catalog.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(CONFIG_TEXT, encoding="utf-8")

    store = CatalogStore(catalog_dir / "catalog.sqlite3")
    fixture = {
        "project": project,
        "raw": raw,
        "catalog_dir": catalog_dir,
        "out_dir": out_dir,
        "config_path": config_path,
        "store": store,
        "hardlink": False,
        "files": [],
        "sequence": 0,
    }

    def add_source(sha: str, size: int, title: str) -> tuple[str, str]:
        source_id = source_id_for_sha256(sha)
        document_id = "urn:company-wiki:document:sha256:" + sha
        with store.transaction() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO roots (root_id,path,kind,priority)"
                " VALUES (?,?,?,?)",
                (ROOT_ID, str(raw), "company_raw", 10),
            )
            _insert(
                connection,
                "sources",
                {
                    "source_id": source_id,
                    "content_sha256": sha,
                    "byte_size": size,
                    "mime_type": "application/octet-stream",
                    "first_seen_at": NOW,
                },
            )
            _insert(
                connection,
                "documents",
                {
                    "document_id": document_id,
                    "primary_source_id": source_id,
                    "title": title,
                    "source_type": "regulatory_filing",
                    "document_kind": "filing",
                    "source_status": "active",
                    "metadata_priority": 1,
                    "metadata_json": "{}",
                    "first_seen_at": NOW,
                    "last_seen_at": NOW,
                },
            )
        return source_id, document_id

    def add_locations(
        source_id: str, document_id: str, sha: str, relatives: list[str]
    ) -> None:
        with store.transaction() as connection:
            for relative in relatives:
                path = raw / relative
                stat_result = os.lstat(path)
                fixture["sequence"] += 1
                _insert(
                    connection,
                    "locations",
                    {
                        "location_id": f"urn:loc:{fixture['sequence']:04d}",
                        "root_id": ROOT_ID,
                        "relative_path": relative,
                        "absolute_path": str(path),
                        "source_id": source_id,
                        "document_id": document_id,
                        "role": "original_primary",
                        "location_status": "active",
                        "observed_size": stat_result.st_size,
                        "observed_mtime_ns": stat_result.st_mtime_ns,
                        "last_seen_run": "run:fixture",
                        "metadata_json": "{}",
                    },
                )

    def register(
        relative: str,
        data: bytes,
        title: str,
        *,
        sha: str | None = None,
        relatives: list[str] | None = None,
    ) -> Path:
        path = _write(raw / relative, data)
        fixture["files"].append(path)
        digest = sha or hashlib.sha256(data).hexdigest()
        source_id, document_id = add_source(digest, len(data), title)
        add_locations(source_id, document_id, digest, relatives or [relative])
        return path

    if with_duplicates:
        # Case 1: one physical file, three location references.
        (raw / "same" / "sub").mkdir(parents=True, exist_ok=True)
        register(
            "same/same.bin",
            b"A" * SIZE_SAME_PATH,
            "same-path",
            relatives=["same/same.bin", "same/./same.bin", "same/sub/../same.bin"],
        )

        # Case 2: two names, one physical file.
        link_a = _write(raw / "hard" / "a.bin", b"B" * SIZE_HARDLINK)
        link_b = raw / "hard" / "b.bin"
        fixture["files"].extend([link_a, link_b])
        try:
            os.link(link_a, link_b)
            fixture["hardlink"] = True
        except OSError:
            fixture["hardlink"] = False
        if fixture["hardlink"]:
            digest = hashlib.sha256(b"B" * SIZE_HARDLINK).hexdigest()
            source_id, document_id = add_source(digest, SIZE_HARDLINK, "hardlink")
            add_locations(
                source_id,
                document_id,
                digest,
                ["hard/a.bin", "hard/b.bin"],
            )

        # Case 3: two distinct physical copies, identical bytes.
        register("copy/a.bin", b"C" * SIZE_COPIES, "copies-a")
        register("copy/b.bin", b"C" * SIZE_COPIES, "copies-b")

    # Case 4: same size, different bytes -> never a duplicate.
    register("sim/a.bin", b"D" * SIZE_SIMILAR, "similar-a")
    register("sim/b.bin", b"E" * (SIZE_SIMILAR - 1) + b"F", "similar-b")

    if with_duplicates:
        # Case 5: registered digest does not match the file bytes.
        register("wrong/a.bin", b"W" * SIZE_WRONG_SHA, "wrong-a", sha=WRONG_SHA)
        register("wrong/b.bin", b"W" * SIZE_WRONG_SHA, "wrong-b", sha=WRONG_SHA)
        # Case 6: changes between the scan phase and verification.
        register("chg/a.bin", b"X" * SIZE_CHANGING, "chg-a")
        register("chg/b.bin", b"X" * SIZE_CHANGING, "chg-b")
        # Case 7: read access denied during verification.
        register("acl/a.bin", b"Y" * SIZE_ACL, "acl-a")
        register("acl/b.bin", b"Y" * SIZE_ACL, "acl-b")

    return fixture


def _by_size(report: dict) -> dict[int, dict]:
    return {int(entry["byte_size"]): entry for entry in report["duplicate_groups"]}


def _run(fixture: dict, mode: str, **kwargs) -> dict:
    options = {
        "mode": mode,
        "config_path": fixture["config_path"],
        "output_path": fixture["out_dir"] / f"report_{mode}.json",
        "max_groups": 100,
        "max_read_bytes": 512 * 1024 * 1024,
        "deadline_seconds": 300.0,
    }
    options.update(kwargs)
    return run_assessment(**options)


def test_scan_mode_accounts_every_shape_without_reading_bytes(tmp_path):
    fixture = build_fixture(tmp_path)
    report = _run(fixture, "scan")

    assert report["status"] == "succeeded"
    assert report["read_bytes"] == 0
    assert report["read_files"] == 0
    assert report["deleted_bytes"] == 0
    assert report["counts"]["candidate_groups"] == (6 if fixture["hardlink"] else 5)
    assert report["logical_duplicate_bytes_upper_bound"] == EXPECTED_UPPER_BOUND

    rows = _by_size(report)
    assert rows[SIZE_SAME_PATH]["classification"] == "same_path_references"
    assert rows[SIZE_SAME_PATH]["logical_duplicate_bytes"] == 0
    assert rows[SIZE_SAME_PATH]["reference_counts"]["locations"] == 3
    if fixture["hardlink"]:
        assert rows[SIZE_HARDLINK]["classification"] == "shared_physical_file"
        assert rows[SIZE_HARDLINK]["logical_duplicate_bytes"] == 0
        assert rows[SIZE_HARDLINK]["distinct_physical_copies"] == 1
    assert rows[SIZE_COPIES]["classification"] == "distinct_physical_copies"
    assert rows[SIZE_COPIES]["logical_duplicate_bytes"] == SIZE_COPIES
    assert rows[SIZE_WRONG_SHA]["logical_duplicate_bytes"] == SIZE_WRONG_SHA
    assert rows[SIZE_CHANGING]["logical_duplicate_bytes"] == SIZE_CHANGING
    assert rows[SIZE_ACL]["logical_duplicate_bytes"] == SIZE_ACL

    assert {int(item["byte_size"]) for item in report["similar_groups"]} == {
        SIZE_SIMILAR
    }
    assert report["similar_groups"][0]["logical_duplicate_bytes"] == 0
    assert report_contains_forbidden_claims(report) == []


def test_hardlink_two_names_is_one_physical_copy(tmp_path):
    fixture = build_fixture(tmp_path)
    if not fixture["hardlink"]:
        pytest.skip("hardlink unsupported on this platform")

    report = _run(fixture, "scan")
    row = _by_size(report)[SIZE_HARDLINK]

    assert row["classification"] == "shared_physical_file"
    assert row["distinct_paths"] == 2
    assert row["distinct_physical_copies"] == 1
    assert row["logical_duplicate_bytes"] == 0
    assert row["physical_allocated_bytes"] == 0
    assert row["reference_counts"]["locations"] == 2


def test_verify_mode_confirms_only_real_duplicates(tmp_path):
    fixture = build_fixture(tmp_path)
    report = _run(fixture, "verify")

    assert report["status"] == "succeeded"
    assert report["deleted_bytes"] == 0
    assert report["logical_duplicate_bytes_upper_bound"] == EXPECTED_UPPER_BOUND
    assert report["verified_duplicate_bytes"] == (
        SIZE_COPIES + SIZE_CHANGING + SIZE_ACL
    )
    assert report["counts"]["verified_groups"] == 3
    assert report["read_files"] == 8
    assert report["read_bytes"] == 2 * (
        SIZE_COPIES + SIZE_WRONG_SHA + SIZE_CHANGING + SIZE_ACL
    )
    assert report["physical_allocated_bytes_available"] is True
    assert report["physical_allocated_bytes"] > 0

    rows = _by_size(report)
    assert rows[SIZE_COPIES]["verification"]["status"] == "verified_identical"
    assert rows[SIZE_WRONG_SHA]["verification"]["status"] == "metadata_sha_mismatch"
    assert rows[SIZE_SAME_PATH]["verification"]["status"] == (
        "not_applicable_zero_logical_bytes"
    )
    assert report_contains_forbidden_claims(report) == []


def test_no_candidates_is_a_legal_result(tmp_path):
    fixture = build_fixture(tmp_path, with_duplicates=False)
    report = _run(fixture, "verify")

    assert report["status"] == "succeeded"
    assert report["counts"]["candidate_groups"] == 0
    assert report["logical_duplicate_bytes_upper_bound"] == 0
    assert report["verified_duplicate_bytes"] == 0
    assert report["deleted_bytes"] == 0
    assert report["read_bytes"] == 0
    assert report["recommendations"]["verdict"] == "keep_as_is"


def test_changing_file_is_never_verified(tmp_path):
    fixture = build_fixture(tmp_path)
    inputs = load_inputs(fixture["config_path"])
    reader = open_reader(inputs)
    try:
        records = read_locations(reader)
    finally:
        reader.close()
    members, _ = observe(records, inputs.roots)
    groups, _ = build_groups(members)
    enforce_containment(groups, inputs.roots)
    for group in groups:
        group.account = account_group(group)
    fill_allocations(groups)
    for group in groups:
        group.account = account_group(group)
    target = next(group for group in groups if group.byte_size == SIZE_CHANGING)

    _write(fixture["raw"] / "chg" / "b.bin", b"Z" * (SIZE_CHANGING + 17))

    budget = Budget(max_read_bytes=1 << 30, deadline_seconds=60.0)
    abort = verify_group(target, budget)

    assert abort is None
    assert target.verification["status"] == "changed"
    statuses = {item["status"] for item in target.verification["files"]}
    assert "changed" in statuses


def _deny_read(path: Path):
    if os.name == "nt":
        user = os.environ.get("USERNAME") or os.environ.get("USER")
        if not user:
            pytest.skip("no USERNAME for ACL denial")
        denied = subprocess.run(
            ["icacls", str(path), "/deny", f"{user}:(R)"],
            capture_output=True,
            text=True,
        )
        if denied.returncode != 0:
            pytest.skip(f"icacls deny unavailable: {denied.stderr.strip()}")

        def restore() -> None:
            subprocess.run(
                ["icacls", str(path), "/remove:d", user],
                capture_output=True,
                text=True,
            )

        return restore

    mode = os.stat(path).st_mode
    os.chmod(path, 0o000)

    def restore() -> None:
        os.chmod(path, mode)

    return restore


def test_acl_denied_file_is_reported_separately(tmp_path):
    fixture = build_fixture(tmp_path)
    victim = fixture["raw"] / "acl" / "b.bin"
    restore = _deny_read(victim)
    try:
        try:
            victim.open("rb").read(1)
        except PermissionError:
            pass
        else:
            pytest.skip("ACL denial not effective on this filesystem")
        report = _run(fixture, "verify", output_path=fixture["out_dir"] / "acl.json")
    finally:
        restore()

    assert report["deleted_bytes"] == 0
    assert report["status"] == "succeeded"
    rows = _by_size(report)
    assert rows[SIZE_ACL]["verification"]["status"] == "acl_denied"
    assert rows[SIZE_ACL]["logical_duplicate_bytes"] == SIZE_ACL
    assert report["verified_duplicate_bytes"] == SIZE_COPIES + SIZE_CHANGING
    assert report["counts"]["unresolved_groups"] >= 1


def test_read_budget_stops_the_run_and_keeps_a_partial_report(tmp_path):
    fixture = build_fixture(tmp_path)
    report = _run(fixture, "verify", max_read_bytes=1000)

    assert report["status"] == "partial"
    assert "read_bytes" in report["limits_hit"]
    assert report["written"] is True
    assert report["deleted_bytes"] == 0
    assert report["counts"]["duplicate_groups_listed"] > 0
    on_disk = json.loads(
        (fixture["out_dir"] / "report_verify.json").read_text(encoding="utf-8")
    )
    assert on_disk["status"] == "partial"


def test_deadline_stops_observation_and_keeps_a_partial_report(tmp_path):
    fixture = build_fixture(tmp_path)
    report = _run(fixture, "verify", deadline_seconds=0.0)

    assert report["status"] == "partial"
    assert "deadline" in report["limits_hit"]
    assert report["written"] is True
    assert report["counts"]["location_rows_observed"] == 0


def test_unknown_previous_report_is_never_overwritten(tmp_path):
    fixture = build_fixture(tmp_path)
    target = fixture["out_dir"] / "report_verify.json"
    target.write_text('{"hello": "world"}', encoding="utf-8")

    report = _run(fixture, "verify", output_path=target)

    assert report["status"] == "refused"
    assert report["error_code"] == "output_exists_unknown"
    assert report["written"] is False
    assert json.loads(target.read_text(encoding="utf-8"))["hello"] == "world"


def test_output_overlapping_a_data_root_is_refused_without_writing(tmp_path):
    fixture = build_fixture(tmp_path)
    target = fixture["raw"] / "report.json"

    report = _run(fixture, "scan", output_path=target)

    assert report["status"] == "refused"
    assert report["error_code"] == "report_path_overlaps_data"
    assert report["written"] is False
    assert not target.exists()


def test_originals_catalog_and_config_are_unchanged(tmp_path):
    fixture = build_fixture(tmp_path)
    watched = list(fixture["files"])
    before = {
        path: (sha256_file(path), path.stat().st_size, path.stat().st_mtime_ns)
        for path in watched
    }
    config_before = sha256_file(fixture["config_path"])
    database = fixture["catalog_dir"] / "catalog.sqlite3"
    db_before = (database.stat().st_size, database.stat().st_mtime_ns)
    side_before = sorted(item.name for item in fixture["catalog_dir"].glob("*"))

    report = _run(fixture, "verify")

    after = {
        path: (sha256_file(path), path.stat().st_size, path.stat().st_mtime_ns)
        for path in watched
    }
    assert before == after
    assert sha256_file(fixture["config_path"]) == config_before
    assert (database.stat().st_size, database.stat().st_mtime_ns) == db_before
    assert sorted(item.name for item in fixture["catalog_dir"].glob("*")) == side_before
    assert report["protected_unchanged"] is True
    assert report["deleted_bytes"] == 0


def test_report_stays_inside_the_git_size_and_row_caps(tmp_path):
    fixture = build_fixture(tmp_path)
    report = _run(fixture, "verify")

    payload = json.dumps(report, ensure_ascii=False).encode("utf-8")
    assert len(payload) <= 1024 * 1024
    assert report["truncated"]["detail_rows"] <= 5000
    assert report["counts"]["detail_rows"] <= 5000
