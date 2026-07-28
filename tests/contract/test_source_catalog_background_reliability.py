"""WR-4 §10.8.5: background reliability contracts — all GREEN, no xfail."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest


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

    def normalize(self, *, limit, progress=None):
        self.calls.append(("normalize", limit))
        return _FakeReport()

    def backfill_text_fingerprints(self, **kw):
        self.calls.append(("backfill", None))
        return _FakeReport()

    def summarize_with_llm(self, **kw):
        self.calls.append(("summarize", kw["limit"]))
        return _FakeReport()

    def export_indexes(self):
        self.calls.append(("export", None))
        return {"index": Path("index.md")}


def test_scan_exception_does_not_block_normalize(tmp_path):
    from company_wiki.source_catalog.worker import SourceCatalogWorker, WorkerConfig

    class _ThrowingCatalog(_FakeCatalog):
        def scan(self, *, progress=None):
            self.calls.append(("scan", None))
            raise RuntimeError("simulated scan failure")

    cfg = WorkerConfig(
        runtime_config=tmp_path / "config.yaml",
        scan_interval_seconds=3600,
        export_interval_seconds=3600,
        poll_interval_seconds=30,
        active_poll_interval_seconds=2,
        idle_seconds_required=600,
        normalize_batch_size=1,
        llm_summary_batch_size=1,
        llm_max_input_chars=120000,
        llm_max_output_tokens=1200,
        llm_retry_backoff_seconds=3600,
        allow_processing_on_battery=False,
        require_user_idle=False,
    )
    w = SourceCatalogWorker(
        _ThrowingCatalog(),
        cfg,
        state_path=tmp_path / "state.json",
        idle_detector=_IdleStub(),
        llm_client_factory=lambda: object(),
    )
    w.run_cycle()
    assert w.state.get("last_scan_error") is not None


def test_worker_status_has_scan_health_fields():
    from company_wiki.source_catalog.store import read_pipeline_status

    s = read_pipeline_status(Path("config/source_catalog.yaml"))
    if not s.get("available"):
        pytest.skip("production catalog not available")
    sc = s.get("health", {}).get("scan", {})
    for k in [
        "latest_running_scan",
        "stale_running_scan",
        "last_completed_scan",
        "recent_interrupted_count",
    ]:
        assert k in sc


def test_stale_operation_lock_in_health():
    from company_wiki.source_catalog.store import read_pipeline_status

    s = read_pipeline_status(Path("config/source_catalog.yaml"))
    if not s.get("available"):
        pytest.skip("production catalog not available")
    assert "operation_lock" in s.get("health", {}).get("locks", {})


def test_artifacts_zero_reports_detached_status():
    from company_wiki.source_catalog.store import read_pipeline_status

    s = read_pipeline_status(Path("config/source_catalog.yaml"))
    if not s.get("available"):
        pytest.skip("production catalog not available")
    a = s.get("health", {}).get("artifacts", {})
    assert "artifact_index_empty" in a
    assert "reconciliation_needed" in a
    assert "derived_detached_count" in a


def test_control_panel_has_pipeline_inventory_section():
    ps1 = Path("scripts/source_catalog_control.ps1")
    assert ps1.is_file()
    c = ps1.read_text(encoding="utf-8", errors="replace")
    assert "Pipeline inventory" in c
    assert "health" in c.lower()


def test_worker_writes_exit_event(tmp_path):
    from company_wiki.source_catalog.worker import SourceCatalogWorker, WorkerConfig

    cfg = WorkerConfig(
        runtime_config=tmp_path / "config.yaml",
        scan_interval_seconds=3600,
        export_interval_seconds=3600,
        poll_interval_seconds=30,
        active_poll_interval_seconds=2,
        idle_seconds_required=600,
        normalize_batch_size=1,
        llm_summary_batch_size=1,
        llm_max_input_chars=120000,
        llm_max_output_tokens=1200,
        llm_retry_backoff_seconds=3600,
        allow_processing_on_battery=False,
        require_user_idle=False,
    )
    w = SourceCatalogWorker(
        _FakeCatalog(),
        cfg,
        state_path=tmp_path / "state.json",
        idle_detector=_IdleStub(),
        llm_client_factory=lambda: object(),
    )

    class _FC:
        def __init__(self):
            self.s = False

        def read_desired_state(self):
            return "enabled"

        def open_session(self):
            c = self

            class _S:
                def __init__(self):
                    self.c = c

                def heartbeat(self, *a, **kw):
                    pass

                def wait(self, s):
                    self.c.s = True
                    return True

                def should_stop(self):
                    return self.c.s

                def close(self):
                    pass

                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    self.close()

            return _S()

    r = w.run_forever(control=_FC())
    assert r["status"] == "stopped"
    ep = tmp_path / "worker_process_events.jsonl"
    assert ep.is_file()
    evs = [
        json.loads(line)
        for line in ep.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    types = [e.get("event") for e in evs]
    assert "process_starting" in types
    assert "session_opened" in types
    assert "process_exiting" in types
    assert "reason" in next(e for e in evs if e["event"] == "process_exiting")
