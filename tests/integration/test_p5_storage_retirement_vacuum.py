"""P5-STORAGE red tests: vacuum real-space accounting and safety."""

from __future__ import annotations

from contextlib import closing
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from support.p5_storage_catalog_fixture import build_catalog

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
        for number in range(200):
            conn.execute(
                "INSERT OR REPLACE INTO entities (entity_id, name, entity_kind)"
                " VALUES (?, ?, ?)",
                (f"e-{number}", "x" * 2048, "company"),
            )
        for _ in range(50):
            conn.execute("DELETE FROM entities WHERE entity_id LIKE 'e-%'")
    conn.close()
    report = run_vacuum(config, now=_now())
    assert report["status"] == "succeeded"
    assert report["operation"] == "vacuum"
    assert report["freelist_after"] == 0
    assert report["freelist_before"] > 0
    assert report["database_bytes_after"] < report["database_bytes_before"]
    assert report["database_file_bytes_released"] > 0
    assert report["page_count_before"] >= report["page_count_after"]
    assert report["foreign_key_check"] == []
    assert report["integrity_check"] == "ok"
    # every number is real: file bytes after match filesystem
    assert report["database_bytes_after"] == config.database_path.stat().st_size


def test_vacuum_preserves_source_facts_and_raw_files(tmp_path: Path) -> None:
    config, _, _ = build_catalog(tmp_path)
    report = run_vacuum(config, now=_now())
    with closing(sqlite3.connect(config.database_path)) as conn:
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


def test_vacuum_preserves_every_current_span(tmp_path: Path) -> None:
    """Current maintenance may compact but never runs the retired span DELETE."""
    config, store, _ = build_catalog(tmp_path)
    before = store.fetchone("SELECT COUNT(*) AS n FROM evidence_spans")["n"]
    report = run_vacuum(config, now=_now())
    assert report["status"] == "succeeded"
    assert store.fetchone("SELECT COUNT(*) AS n FROM evidence_spans")["n"] == before
    assert report["source_facts_before"] == report["source_facts_after"]
