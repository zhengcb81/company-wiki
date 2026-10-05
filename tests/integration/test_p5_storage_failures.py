"""Maintenance failures must preserve rows and report actual operation state."""
from contextlib import closing
import sqlite3

from support.p5_storage_catalog_fixture import build_catalog
from company_wiki.source_catalog.lock import CatalogOperationLock
from legacy_storage.shrink import run_vacuum
from legacy_storage.spans import run_prune_spans


def selection():
    return {"schema_version": "cwp-span-selection/1", "parser_name": "plain_text"}


def test_current_catalog_writer_refuses_both_mutations(tmp_path):
    config, store, _ = build_catalog(tmp_path)
    count = store.fetchone("SELECT COUNT(*) AS n FROM evidence_spans")["n"]
    with CatalogOperationLock(config.catalog_dir, operation="fixture-current-writer"):
        reports = [run_prune_spans(config, selection(), dry_run=False), run_vacuum(config)]
    assert all(r["status"] == "refused" and r["error_code"] == "catalog_busy" for r in reports)
    assert store.fetchone("SELECT COUNT(*) AS n FROM evidence_spans")["n"] == count


def test_prune_sql_failure_rolls_back_without_claiming_deleted_rows(tmp_path, monkeypatch):
    config, store, _ = build_catalog(tmp_path)
    count = store.fetchone("SELECT COUNT(*) AS n FROM evidence_spans")["n"]
    connect = sqlite3.connect

    class DeleteThenFailure(sqlite3.Connection):
        def execute(self, sql, *args):
            result = super().execute(sql, *args)
            if sql.startswith("DELETE FROM evidence_spans"):
                raise sqlite3.OperationalError("injected after delete before commit")
            return result

    def injected(database, *args, **kwargs):
        return connect(database, *args, factory=DeleteThenFailure, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", injected)
    report = run_prune_spans(config, selection(), dry_run=False)
    assert report["status"] == "failed"
    assert report["deleted"] == 0
    with closing(connect(config.database_path)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM evidence_spans").fetchone()[0] == count
