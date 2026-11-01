"""Storage maintenance must remain readonly, bounded and honestly measured."""
from __future__ import annotations

from contextlib import closing
import hashlib
from pathlib import Path
import shutil
import sqlite3


from support import p5_storage_catalog_fixture as fixture
from legacy_storage.core import protected_objects, read_connection, source_facts
from legacy_storage.inventory import run_inventory
from legacy_storage.shrink import run_vacuum


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
               run_vacuum(config, dry_run=True)]
    assert all(report["status"] == "succeeded" for report in reports)
    assert snapshot(tmp_path) == before


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
