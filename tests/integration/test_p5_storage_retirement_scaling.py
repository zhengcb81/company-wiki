"""Storage maintenance must remain readonly, bounded and honestly measured."""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3

import pytest

from support import p5_storage_catalog_fixture as fixture
from legacy_storage.core import protected_objects, read_connection, source_facts
from legacy_storage.inventory import run_inventory
from legacy_storage.shrink import run_vacuum
from legacy_storage.spans import run_prune_spans


def selection() -> dict:
    return {"schema_version": "cwp-span-selection/1", "parser_name": "plain_text",
            "parser_version": "1.0.0", "source_ids": [], "document_ids": []}


def snapshot(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def test_static_wal_catalog_read_never_creates_sidecars(tmp_path):
    config, _, _ = fixture.build_catalog(tmp_path)
    before = snapshot(tmp_path)
    assert not Path(str(config.database_path) + "-wal").exists()
    with read_connection(config.database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0] == 2
        assert snapshot(tmp_path) == before
    assert snapshot(tmp_path) == before


def test_all_previews_work_with_write_connections_disabled(tmp_path, monkeypatch):
    config, _, _ = fixture.build_catalog(tmp_path)
    manifest = run_inventory(config).manifest
    before = snapshot(tmp_path)
    connect = sqlite3.connect

    def readonly_only(database, *args, **kwargs):
        if not kwargs.get("uri") or "mode=ro" not in str(database):
            raise sqlite3.OperationalError("fixture denies every write connection")
        return connect(database, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", readonly_only)
    from legacy_storage.retirement import run_retire_derived
    reports = [run_inventory(config).report,
               run_retire_derived(config, manifest, dry_run=True),
               run_prune_spans(config, selection(), dry_run=True),
               run_vacuum(config, dry_run=True)]
    assert all(report["status"] == "succeeded" for report in reports)
    assert snapshot(tmp_path) == before


def test_large_span_preview_has_bounded_report(tmp_path, monkeypatch):
    monkeypatch.setattr(fixture, "ANNUAL_BODY", "\n\n".join(
        f"第{i}项业务进展：公司研发新产品并拓展海外市场，客户验证取得进展。"
        for i in range(1200)))
    config, store, _ = fixture.build_catalog(tmp_path)
    count = store.fetchone("SELECT COUNT(*) AS n FROM evidence_spans")["n"]
    assert count > 1000
    report = run_prune_spans(config, selection(), dry_run=True)
    assert report["status"] == "succeeded"
    assert report["selection"]["candidate_pairs"] == count
    assert len(json.dumps(report, ensure_ascii=False).encode("utf-8")) < 32_768
    assert report["candidates"] == []
    assert store.fetchone("SELECT COUNT(*) AS n FROM evidence_spans")["n"] == count


def test_kept_rows_are_not_reported_as_absent(tmp_path):
    config, store, _ = fixture.build_catalog(tmp_path)
    keep = store.fetchone("SELECT source_id, locator FROM evidence_spans LIMIT 1")
    count = store.fetchone("SELECT COUNT(*) AS n FROM evidence_spans")["n"]
    report = run_prune_spans(config, selection(), keep_refs=[dict(keep)], dry_run=False)
    assert report["status"] == "succeeded"
    assert report["deleted"] == count - 1
    assert report["already_absent"] == 0
    assert report["selection"]["kept_pairs"] == 1
    assert report["selection"]["keep_verified"] is True


@pytest.mark.parametrize("invalid", [
    {"source_ids": None}, {"document_ids": [None]},
    {"parser_version": ""}, {"schema_version": "unknown/99"},
])
def test_invalid_scope_never_broadens_to_all_spans(tmp_path, invalid):
    config, store, _ = fixture.build_catalog(tmp_path)
    count = store.fetchone("SELECT COUNT(*) AS n FROM evidence_spans")["n"]
    report = run_prune_spans(config, {**selection(), **invalid}, dry_run=False)
    assert report["status"] == "refused"
    assert store.fetchone("SELECT COUNT(*) AS n FROM evidence_spans")["n"] == count


def test_vacuum_compares_actual_pre_operation_facts(tmp_path, monkeypatch):
    config, _, _ = fixture.build_catalog(tmp_path)
    before = source_facts(config.database_path)
    connect = sqlite3.connect

    class ChangedDuringVacuum(sqlite3.Connection):
        def execute(self, sql, *args):
            result = super().execute(sql, *args)
            if sql == "VACUUM":
                super().execute("UPDATE documents SET title='changed during fixture vacuum'")
            return result

    def injected(database, *args, **kwargs):
        return connect(database, *args, factory=ChangedDuringVacuum, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", injected)
    report = run_vacuum(config)
    assert report["source_facts_before"] == before
    assert report["source_facts_after"] != before
    assert report["status"] == "failed"
    assert report["error_code"] == "protected_facts_changed"


def test_vacuum_checks_real_available_scratch_space(tmp_path, monkeypatch):
    config, _, _ = fixture.build_catalog(tmp_path)
    before = snapshot(tmp_path)
    usage = shutil.disk_usage(tmp_path)
    monkeypatch.setattr(shutil, "disk_usage", lambda _: type(usage)(usage.total, usage.total, 0))
    report = run_vacuum(config)
    assert report["status"] == "refused"
    assert report["error_code"] == "insufficient_disk_space"
    assert report["disk_free_bytes_before"] == 0
    assert report["scratch_required_bytes"] >= 2 * config.database_path.stat().st_size
    assert snapshot(tmp_path) == before


def test_new_objects_in_runtime_root_are_measured(tmp_path):
    config, _, _ = fixture.build_catalog(tmp_path)
    objects = config.catalog_dir / "objects"
    actual_root = config.catalog_dir / "artifacts" / "objects"
    actual_root.parent.mkdir()
    objects.rename(actual_root)
    size = sum(p.stat().st_size for p in actual_root.rglob("*") if p.is_file())
    report = protected_objects(config.database_path, config.catalog_dir)
    assert size > 0
    assert report["object_bytes"] == size
    assert report["object_file_count"] == 1


def test_fact_digest_is_independent_of_rowid_order(tmp_path):
    config, _, _ = fixture.build_catalog(tmp_path)
    with closing(sqlite3.connect(config.database_path)) as connection, connection:
        connection.execute('CREATE TABLE "future facts" (id TEXT PRIMARY KEY, value TEXT)')
        connection.executemany('INSERT INTO "future facts" VALUES (?,?)', [("b", "2"), ("a", "1")])
    before = source_facts(config.database_path)
    with closing(sqlite3.connect(config.database_path)) as connection, connection:
        connection.execute('DELETE FROM "future facts"')
        connection.executemany('INSERT INTO "future facts" VALUES (?,?)', [("a", "1"), ("b", "2")])
    assert source_facts(config.database_path) == before
