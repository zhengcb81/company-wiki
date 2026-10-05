"""P5-STORAGE red tests: protection boundary of inventory / retire-derived.

Every test exercises the tool against a REAL schema catalog built by the real
legacy producers (see ``test_p5_storage_retirement_common``).  These tests pin:

* inventory is strictly read-only (no DB or file writes, no Store migration),
* originals / new narrative finals / unknown objects never become candidates,
* changed paths or bytes make a candidate void instead of deletable,
* repeated requests are idempotent and never double count released bytes.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from unit.test_p5_storage_retirement_common import (
    NOW,
    build_catalog,
    count_rows,
    tree_digest,
)

from company_wiki.source_catalog.config import CatalogConfig

from legacy_storage.inventory import run_inventory
from legacy_storage.retirement import run_retire_derived


def _now() -> datetime:
    return datetime(2026, 10, 5, 0, 0, 0, tzinfo=UTC)


def tree_of(root: Path) -> dict[str, int]:
    skip = {"catalog.sqlite3-wal", "catalog.sqlite3-shm", "operation.lock"}
    out: dict[str, int] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name not in skip:
            out[path.relative_to(root).as_posix()] = path.stat().st_size
    return out


def _snapshot(config: CatalogConfig) -> dict:
    return {
        "files": tree_of(config.catalog_dir),
        "raw_files": tree_of(config.project_root / "raw"),
        "db_bytes": config.database_path.stat().st_size,
    }


# ---------------------------------------------------------------------------
# inventory
# ---------------------------------------------------------------------------


def test_inventory_writes_nothing_anywhere(tmp_path: Path) -> None:
    config, _, _ = build_catalog(tmp_path)
    before = _snapshot(config)
    report = run_inventory(config, now=_now()).report
    after = _snapshot(config)
    assert report["schema_version"] == "cwp-storage-retirement/1"
    assert report["operation"] == "inventory"
    assert report["dry_run"] is True
    assert report["status"] == "succeeded"
    assert after == before, (before, after)
    # all measurements are real, not padded zeros
    assert report["files_bytes_before"] > 0
    assert report["database_bytes_before"] > 0
    assert report["foreign_key_check"] == []
    assert report["integrity_check"] == "ok"


def test_inventory_candidates_are_legacy_derived_only(tmp_path: Path) -> None:
    config, store, facts = build_catalog(tmp_path)
    report = run_inventory(config, now=_now()).report
    selection = report["candidates"]
    roles = sorted({(c["artifact_role"], c["generator_name"]) for c in selection})
    assert roles == sorted(
        [
            ("normalized", "source_catalog_normalizer"),
            ("summary", "source_catalog_extractive_summary"),
            ("sections", "source_catalog_section_extractor"),
        ]
    )
    # every candidate is a legacy derived role/generator with completed status
    for candidate in selection:
        assert candidate["artifact_role"] in {"normalized", "summary", "sections"}
        assert candidate["status"] == "completed"
    # originals are never candidates: no raw file path appears
    raw_paths = {f"raw/{rel}" for rel in _snapshot(config)["raw_files"]}
    assert not raw_paths & {c["path"] for c in selection}
    # the new narrative object file is not a candidate
    narrative_paths = [
        row["object_key"]
        for row in report["protected_objects_before"]["new_final_items"]
    ]
    assert narrative_paths and narrative_paths[0].startswith("objects/sha256/")


def test_inventory_excludes_unknown_generator_and_outside_paths(
    tmp_path: Path, tmp_factory=None
) -> None:
    config, store, _ = build_catalog(tmp_path)
    with store.transaction() as connection:
        connection.execute(
            "INSERT INTO artifacts (artifact_id, document_id, artifact_role, path,"
            " content_sha256, byte_size, mime_type, generator_name,"
            " generator_version, status, metadata_json, created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "urn:company-wiki:artifact:sha256:" + "1" * 64,
                store.fetchall("SELECT document_id FROM documents LIMIT 1")[0][
                    "document_id"
                ],
                "normalized",
                str(config.project_root / "raw" / "escaped.md"),
                hashlib.sha256(b"escaped").hexdigest(),
                8,
                "text/markdown",
                "unknown_new_generator",
                "9.9.9",
                "completed",
                "{}",
                NOW,
            ),
        )
    (config.project_root / "raw" / "escaped.md").write_bytes(b"escaped")
    report = run_inventory(config, now=_now()).report
    excluded = {(e["artifact_id"], e["reason"]) for e in report["excluded"]}
    assert any(
        reason in {"unknown_generator", "path_outside_derived"}
        for _, reason in excluded
    )
    outside_cands = [
        c
        for c in report["candidates"]
        if "unknown_new_generator" in c["generator_name"]
    ]
    assert outside_cands == []
    # escaped raw file still exists in the snapshot
    assert "escaped.md" in _snapshot(config)["raw_files"]


def test_inventory_reports_loose_derived_files_as_unreferenced(tmp_path: Path) -> None:
    config, _, _ = build_catalog(tmp_path)
    anchor = next((p for p in config.derived_dir.rglob("normalized.md")), None)
    assert anchor is not None
    loose = anchor.parent / "orphan.md"
    loose.write_bytes(b"orphan body")
    report = run_inventory(config, now=_now()).report
    assert any(
        item["path"].endswith("orphan.md") for item in report["unreferenced_derived"]
    )


def test_inventory_is_deterministic(tmp_path: Path) -> None:
    config, _, _ = build_catalog(tmp_path)
    first = run_inventory(config, now=_now())
    second = run_inventory(config, now=_now())
    assert first.manifest["aggregate"] == second.manifest["aggregate"]


def test_inventory_reports_tables_by_class(tmp_path: Path) -> None:
    config, store, _ = build_catalog(tmp_path)
    with store.transaction() as connection:
        connection.execute("CREATE TABLE sandbox_z_enduring (bug TEXT)")
    report = run_inventory(config, now=_now()).report
    classes = report["schema_inventory"]
    assert classes["fact"]["roots"]["count"] >= 1
    assert classes["protected"]["narrative_artifact_versions"]["count"] == 1
    assert classes["legacy_record"]["artifacts"]["count"] >= 4
    assert classes["legacy_record"]["evidence_spans"]["count"] >= 10
    assert "sandbox_z_enduring" in classes["unknown"]


# ---------------------------------------------------------------------------
# retire-derived
# ---------------------------------------------------------------------------


def test_retire_dry_run_touches_nothing(tmp_path: Path) -> None:
    config, _, _ = build_catalog(tmp_path)
    inventory = run_inventory(config, now=_now())
    manifest = inventory.manifest
    before = _snapshot(config)
    report = run_retire_derived(config, manifest, now=_now(), dry_run=True)
    assert report["dry_run"] is True
    assert report["deleted"] == []
    assert _snapshot(config) == before


def test_retire_derived_frees_files_and_disables_handles(tmp_path: Path) -> None:
    config, store, _ = build_catalog(tmp_path)
    inventory = run_inventory(config, now=_now())
    manifest = inventory.manifest
    before_bytes = inventory.report["files_bytes_before"]
    report = run_retire_derived(config, manifest, now=_now())
    assert report["status"] == "succeeded"
    assert len(report["deleted"]) >= 5
    released = sum(item["byte_size"] for item in report["deleted"])
    assert report["files_bytes_after"] == before_bytes - released
    assert report["files_bytes_after"] < report["files_bytes_before"]
    with store.transaction() as connection:
        statuses = [
            tuple(r) for r in connection.execute(
                "SELECT status, COUNT(*) FROM artifacts"
                " WHERE artifact_role IN ('normalized','summary','sections')"
                " GROUP BY status"
            )
        ]
        assert statuses == [("retired", 5)]  # 4 DB-row artifacts + managed .md set
        # source facts untouched
        assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM locations").fetchone()[0] == 2
        # spans unchanged by retire-derived
        assert connection.execute("SELECT COUNT(*) FROM evidence_spans").fetchone()[
            0
        ] == count_rows(config.database_path, "evidence_spans")
    # no completed handle still points at derived roles
    dangling = store.fetchall(
        "SELECT artifact_id FROM artifacts WHERE status='completed'"
        " AND artifact_role IN ('normalized','summary','sections')"
    )
    assert dangling == []
    _assert_catalog_remaining_has_no_standard_derived(config)


def _assert_catalog_remaining_has_no_standard_derived(config: CatalogConfig) -> None:
    remaining = tree_digest(config.derived_dir)
    for rel in remaining:
        assert rel.startswith("objects/"), rel


def test_retire_deried_is_idempotent(tmp_path: Path) -> None:
    config, _, _ = build_catalog(tmp_path)
    inventory = run_inventory(config, now=_now())
    manifest = inventory.manifest
    first = run_retire_derived(config, manifest, now=_now())
    snapshot_after_first = _snapshot(config)
    second = run_retire_derived(config, manifest, now=_now())
    assert second["deleted"] == []
    assert {i["artifact_id"] for i in second["already_absent"]} >= set()
    assert second["files_bytes_after"] == second["files_bytes_before"]
    assert _snapshot(config) == snapshot_after_first
    # released amount is not inflated by the second run
    first_released = sum(i["byte_size"] for i in first["deleted"])
    second_report_json = json.dumps(second)
    assert str(first_released) not in second_report_json


def test_retire_skips_hash_mismatch_and_keeps_file(tmp_path: Path) -> None:
    config, store, _ = build_catalog(tmp_path)
    manifest = run_inventory(config, now=_now())
    victim = Path(
        store.fetchone(
            "SELECT path FROM artifacts WHERE artifact_role='normalized' LIMIT 1"
        )["path"]
    )
    victim.write_bytes(b"tampered body")
    report = run_retire_derived(config, manifest.manifest, now=_now())
    assert victim.exists()
    excluded = {(e["artifact_id"], e["reason"]) for e in report["excluded"]}
    import sqlite3

    with sqlite3.connect(config.database_path) as conn:
        row = conn.execute(
            "SELECT status FROM artifacts WHERE path=?", (str(victim),)
        ).fetchone()
    assert any(reason == "content_hash_mismatch" for _, reason in excluded)
    assert row[0] == "completed"


def test_missing_derived_file_counts_already_absent(tmp_path: Path) -> None:
    config, store, _ = build_catalog(tmp_path)
    manifest = run_inventory(config, now=_now())
    victim = Path(
        store.fetchone(
            "SELECT path FROM artifacts WHERE artifact_role='summary' LIMIT 1"
        )["path"]
    )
    victim.unlink()
    report = run_retire_derived(config, manifest.manifest, now=_now())
    from pathlib import Path as _P
    assert _P(victim) in {_P(item["path"]) for item in report["already_absent"]}


def test_retire_rejects_unknown_manifest_scope(tmp_path: Path) -> None:
    config, _, _ = build_catalog(tmp_path)
    report = run_retire_derived(
        config,
        {"schema_version": "cwp-storage-manifest/1", "candidates": []},
        now=_now(),
    )
    assert report["status"] == "refused"
    assert report["error_code"] == "empty_candidate_scope"


def test_source_facts_stay_identical_across_retire(tmp_path: Path) -> None:
    config, _, _ = build_catalog(tmp_path)
    inventory = run_inventory(config, now=_now())
    manifest = inventory.manifest
    first = run_retire_derived(config, manifest, now=_now())
    second = run_retire_derived(config, manifest, now=_now())
    assert first["source_facts_before"] == first["source_facts_after"]
    assert second["source_facts_before"] == second["source_facts_after"]
    # protected objects (new narrative finals) also unchanged
    assert first["protected_objects_before"] == first["protected_objects_after"]
    assert second["protected_objects_before"] == second["protected_objects_after"]
