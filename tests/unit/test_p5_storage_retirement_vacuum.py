"""P5-STORAGE red tests: vacuum real-space accounting and safety."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from unit.test_p5_storage_retirement_common import build_catalog

from legacy_storage.retirement import run_retire_derived
from legacy_storage.inventory import run_inventory
from legacy_storage.shrink import run_vacuum


def _now() -> datetime:
    return datetime(2026, 10, 5, 0, 0, 0, tzinfo=UTC)


def _facts() -> tuple:
    return (
        "sources",
        "documents",
        "locations",
        "roots",
        "narrative_artifact_versions",
    )


def test_vacuum_measures_real_physical_release(tmp_path: Path) -> None:
    config, _, _ = build_catalog(tmp_path)
    manifest = run_inventory(config, now=_now()).manifest
    run_retire_derived(config, manifest, now=_now())
    # generate logical free pages for a measurable release
    conn = sqlite3.connect(config.database_path)
    with conn:
        for _ in range(50):
            conn.execute(
                "INSERT OR REPLACE INTO entities (entity_id, name, entity_kind)"
                " VALUES (?, ?, ?)",
                (f"e-{_now().timestamp()}", "x", "company"),
            )
        for _ in range(50):
            conn.execute("DELETE FROM entities WHERE name='x'")
    conn.close()
    report = run_vacuum(config, now=_now())
    assert report["status"] == "succeeded"
    assert report["operation"] == "vacuum"
    assert report["freelist_after"] == 0
    assert report["freelist_before"] >= 0
    assert report["database_bytes_after"] <= report["database_bytes_before"]
    assert report["page_count_before"] >= report["page_count_after"]
    assert report["foreign_key_check"] == []
    assert report["integrity_check"] == "ok"
    # every number is real: file bytes after match filesystem
    assert report["database_bytes_after"] == config.database_path.stat().st_size


def test_vacuum_preserves_source_facts_and_raw_files(tmp_path: Path) -> None:
    config, _, _ = build_catalog(tmp_path)
    report = run_vacuum(config, now=_now())
    with sqlite3.connect(config.database_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 2
    assert report["source_facts_after"]["sources"]["count"] == 2


def test_vacuum_is_idempotent(tmp_path: Path) -> None:
    config, _, _ = build_catalog(tmp_path)
    first = run_vacuum(config, now=_now())
    second = run_vacuum(config, now=_now())
    assert first["status"] == "succeeded"
    assert second["status"] == "succeeded"
    assert second["database_bytes_after"] == second["database_bytes_before"]


def test_vacuum_refuses_missing_db(tmp_path: Path) -> None:
    config = build_catalog(tmp_path)[0]
    conn = sqlite3.connect(config.database_path)
    conn.close()
    Path(config.database_path).unlink()
    report = run_vacuum(config, now=_now())
    assert report["status"] == "refused"
    assert report["error_code"] == "database_missing"


def test_vacuum_after_prune_keeps_keep_and_facts(tmp_path: Path) -> None:
    """End-to-end small chain: retire, prune, vacuum; facts & spans-kept survive."""
    from legacy_storage.spans import run_prune_spans

    config, store, _ = build_catalog(tmp_path)
    manifest = run_inventory(config, now=_now()).manifest
    run_retire_derived(config, manifest, now=_now())
    selection = {
        "schema_version": "cwp-span-selection/1",
        "parser_name": "plain_text",
        "parser_version": "1.0.0",
        "source_ids": [],
        "document_ids": [],
    }
    with store.transaction() as connection:
        keep = connection.execute(
            "SELECT source_id, locator FROM evidence_spans LIMIT 1"
        ).fetchone()
    keep_refs = [{"source_id": keep[0], "locator": keep[1]}]
    run_prune_spans(config, selection, keep_refs=keep_refs, now=_now(), dry_run=False)
    report = run_vacuum(config, now=_now())
    assert report["status"] == "succeeded"
    with store.transaction() as connection:
        assert (
            connection.execute("SELECT COUNT(*) FROM evidence_spans").fetchone()[0] == 1
        )
        assert connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0] == 2
