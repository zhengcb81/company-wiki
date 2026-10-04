"""WR-4 §10.8.5: background reliability contracts — all GREEN, no xfail."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path


class _IdleStub:
    on_battery = staticmethod(lambda: False)
    idle_seconds = staticmethod(lambda: 0)


@dataclass
class _FakeReport:
    completed: int = 1
    failed: int = 0
    error: str | None = None
    failure_scope: str | None = None

    def to_dict(self):
        return dict(self.__dict__)


class _FakeCatalog:
    def __init__(self):
        self.calls = []

    def scan(self, *, progress=None):
        self.calls.append(("scan", None))
        return _FakeReport()

    def normalize(self, *, limit, progress=None, **kwargs):
        del progress, kwargs
        self.calls.append(("normalize", limit))
        return _FakeReport()

    def backfill_text_fingerprints(self, **kw):
        self.calls.append(("backfill", None))
        return _FakeReport()

    def extract_sections(self, *, limit, progress=None, should_stop=None, **kw):
        del progress, should_stop, kw
        self.calls.append(("sections", limit))
        return _FakeReport()

    def summarize_with_llm(self, **kw):
        self.calls.append(("summarize", kw["limit"]))
        return _FakeReport()

    def export_indexes(self, *, progress=None):
        self.calls.append(("export", None))
        return {"index": Path("index.md")}


def _temp_pipeline_status(tmp_path, *, operation_lock=None):
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
    from company_wiki.source_catalog.store import read_pipeline_status

    source = tmp_path / "source"
    source.mkdir()
    (source / "document.txt").write_text(
        "source-only reliability fixture", encoding="utf-8"
    )
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path / "project",
            catalog_dir=tmp_path / "project" / ".source_catalog",
            roots=(RootSpec("fixture", source, "directory"),),
        )
    )
    catalog.scan()
    if operation_lock is not None:
        lock_path = catalog.config.catalog_dir / "operation.lock"
        lock_path.write_text(
            json.dumps(operation_lock, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return read_pipeline_status(catalog.config.database_path)


def test_worker_status_has_scan_health_fields(tmp_path):
    s = _temp_pipeline_status(tmp_path)
    assert s["available"] is True
    sc = s.get("health", {}).get("scan", {})
    for k in [
        "latest_running_scan",
        "stale_running_scan",
        "last_completed_scan",
        "recent_interrupted_count",
        "interrupted_total",
    ]:
        assert k in sc


def test_worker_status_exposes_running_scan_identity(tmp_path):
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
    from company_wiki.source_catalog.store import read_pipeline_status

    source = tmp_path / "source"
    source.mkdir()
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path / "project",
            catalog_dir=tmp_path / "project" / ".source_catalog",
            roots=(RootSpec("fixture", source, "directory"),),
        )
    )
    catalog.scan()
    with sqlite3.connect(catalog.config.database_path) as connection:
        connection.execute(
            """INSERT INTO scan_runs(run_id,started_at,status)
            VALUES('scan-visible-fixture','2099-01-01T00:00:00Z','running')"""
        )

    scan_health = read_pipeline_status(catalog.config.database_path)["health"]["scan"]

    assert scan_health["latest_running_scan"] == {
        "run_id": "scan-visible-fixture",
        "started_at": "2099-01-01T00:00:00Z",
        "status": "running",
    }
    assert scan_health["last_completed_scan"]["run_id"].startswith("scan-")
    assert scan_health["last_completed_scan"]["completed_at"]


def test_completed_with_errors_counts_as_a_completed_scan(tmp_path):
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
    from company_wiki.source_catalog.store import read_pipeline_status

    source = tmp_path / "source"
    source.mkdir()
    (source / "document.txt").write_text("fixture", encoding="utf-8")
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path / "project",
            catalog_dir=tmp_path / "project" / ".source_catalog",
            roots=(RootSpec("fixture", source, "directory"),),
        )
    )
    catalog.scan()
    with sqlite3.connect(catalog.config.database_path) as connection:
        connection.execute("UPDATE scan_runs SET status='completed_with_errors'")

    pipeline = read_pipeline_status(catalog.config.database_path)
    completed_scan = pipeline["health"]["scan"]["last_completed_scan"]
    assert completed_scan["run_id"].startswith("scan-")
    assert completed_scan["completed_at"]
    assert completed_scan["status"] == "completed_with_errors"
    scan_health = catalog.store.scan_health()
    assert scan_health["last_completed_scan"]["status"] == "completed_with_errors"
    assert scan_health["stale_running_scan"] is False


def test_stale_operation_lock_in_health(tmp_path):
    s = _temp_pipeline_status(
        tmp_path,
        operation_lock={
            "pid": 2_147_483_647,
            "operation": "normalize",
            "token": "fixture-token",
        },
    )
    assert s["available"] is True
    lock = s["health"]["locks"]
    assert lock["operation_lock"] == "stale"
    assert lock["operation_lock_pid"] == 2_147_483_647
    assert lock["operation_lock_operation"] == "normalize"
    assert lock["operation_lock_identity_verification"] == "not_live"
    assert lock["operation_lock_process_creation_time"] is None
    assert lock["operation_lock_observed_process_creation_time"] is None


def test_artifacts_zero_reports_detached_status(tmp_path):
    s = _temp_pipeline_status(tmp_path)
    assert s["available"] is True
    a = s.get("health", {}).get("artifacts", {})
    assert "artifact_index_empty" in a
    assert "reconciliation_needed" in a
    assert "derived_detached_count" in a
