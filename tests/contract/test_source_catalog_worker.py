"""Contracts for periodic scanning and low-priority source processing."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path

import pytest


def _catalog(tmp_path: Path):
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog

    project = tmp_path / "project"
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "meeting.txt").write_text(
        "2025年公司收入增长20%，新增客户12家，产能达到100万台。",
        encoding="utf-8",
    )
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("sources", sources, "directory"),),
        )
    )
    catalog.scan()
    catalog.normalize()
    return catalog, sources


def test_worker_config_is_versioned_and_resolves_project_paths(tmp_path):
    from company_wiki.source_catalog.worker import load_worker_config

    project = tmp_path / "project"
    path = project / "config" / "source_catalog_worker.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        """
schema_version: '1.1'
runtime_config: '${PROJECT_ROOT}/config.yaml'
scan_interval_minutes: 60
export_interval_minutes: 60
poll_interval_seconds: 30
idle_seconds_required: 600
require_user_idle: false
normalize_batch_size: 1
llm_summary_batch_size: 1
llm_max_input_chars: 120000
llm_max_output_tokens: 1200
llm_retry_backoff_minutes: 60
allow_processing_on_battery: false
""".strip(),
        encoding="utf-8",
    )

    config = load_worker_config(path, project_root=project)

    assert config.runtime_config == project / "config.yaml"
    assert config.scan_interval_seconds == 3600
    assert config.active_poll_interval_seconds == 30
    assert config.idle_seconds_required == 600
    assert config.require_user_idle is False
    assert config.normalize_batch_size == 1
    assert config.allow_processing_on_battery is False


def test_worker_config_1_0_preserves_the_historical_user_idle_gate(tmp_path):
    from company_wiki.source_catalog.worker import load_worker_config

    project = tmp_path / "project"
    path = project / "config" / "source_catalog_worker.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        """
schema_version: '1.0'
runtime_config: '${PROJECT_ROOT}/config.yaml'
scan_interval_minutes: 60
export_interval_minutes: 60
poll_interval_seconds: 30
idle_seconds_required: 600
normalize_batch_size: 1
llm_summary_batch_size: 1
llm_max_input_chars: 120000
llm_max_output_tokens: 1200
llm_retry_backoff_minutes: 60
allow_processing_on_battery: false
""".strip(),
        encoding="utf-8",
    )

    config = load_worker_config(path, project_root=project)

    assert config.require_user_idle is True
    assert config.active_poll_interval_seconds == 30


def test_worker_config_1_2_requires_an_explicit_positive_active_poll_interval(tmp_path):
    from company_wiki.source_catalog.worker import load_worker_config

    project = tmp_path / "project"
    path = project / "config" / "source_catalog_worker.yaml"
    path.parent.mkdir(parents=True)
    payload = """
schema_version: '1.2'
runtime_config: '${PROJECT_ROOT}/config.yaml'
scan_interval_minutes: 60
export_interval_minutes: 60
poll_interval_seconds: 30
active_poll_interval_seconds: 2
idle_seconds_required: 600
require_user_idle: false
normalize_batch_size: 1
llm_summary_batch_size: 1
llm_max_input_chars: 120000
llm_max_output_tokens: 1200
llm_retry_backoff_minutes: 60
allow_processing_on_battery: false
fingerprint_backfill_batch_size: 3
fingerprint_retry_limit: 3
fingerprint_retry_backoff_seconds: 900
""".strip()
    path.write_text(payload, encoding="utf-8")

    config = load_worker_config(path, project_root=project)

    assert config.poll_interval_seconds == 30
    assert config.active_poll_interval_seconds == 2

    path.write_text(
        payload.replace(
            "active_poll_interval_seconds: 2", "active_poll_interval_seconds: 0"
        ),
        encoding="utf-8",
    )
    with pytest.raises(
        ValueError, match="active_poll_interval_seconds must be a positive integer"
    ):
        load_worker_config(path, project_root=project)


def test_worker_config_1_3_requires_bounded_parser_liveness_settings(tmp_path):
    from company_wiki.source_catalog.worker import load_worker_config

    project = tmp_path / "project"
    path = project / "config" / "source_catalog_worker.yaml"
    path.parent.mkdir(parents=True)
    payload = """
schema_version: '1.3'
runtime_config: '${PROJECT_ROOT}/config.yaml'
scan_interval_minutes: 60
export_interval_minutes: 60
poll_interval_seconds: 30
active_poll_interval_seconds: 2
idle_seconds_required: 600
require_user_idle: false
normalize_batch_size: 1
llm_summary_batch_size: 1
llm_max_input_chars: 120000
llm_max_output_tokens: 1200
llm_retry_backoff_minutes: 60
allow_processing_on_battery: false
fingerprint_backfill_batch_size: 3
fingerprint_retry_limit: 3
fingerprint_retry_backoff_seconds: 900
document_parse_timeout_seconds: 3600
parser_heartbeat_interval_seconds: 15
parser_result_max_bytes: 268435456
normalization_retry_limit: 3
normalization_retry_backoff_seconds: 900
""".strip()
    path.write_text(payload, encoding="utf-8")

    config = load_worker_config(path, project_root=project)

    assert config.document_parse_timeout_seconds == 3600
    assert config.parser_heartbeat_interval_seconds == 15
    assert config.parser_result_max_bytes == 268_435_456
    assert config.normalization_retry_limit == 3

    path.write_text(
        payload.replace(
            "parser_heartbeat_interval_seconds: 15",
            "parser_heartbeat_interval_seconds: 3600",
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="parser_heartbeat_interval_seconds"):
        load_worker_config(path, project_root=project)


@dataclass
class _Report:
    completed: int = 1
    failed: int = 0
    error: str | None = None
    failed_document_id: str | None = None
    failure_scope: str | None = None
    retry_after: float | None = None
    retry_count: int | None = None

    def to_dict(self):
        return dict(self.__dict__)


class _FakeCatalog:
    def __init__(self):
        self.calls: list[tuple[str, int | None]] = []
        self.summary_report = _Report()
        self.normalize_options: dict = {}
        self.fingerprint_options: dict = {}

    def scan(self, *, progress=None):
        self.calls.append(("scan", None))
        return _Report()

    def normalize(self, *, limit, progress=None, **kwargs):
        self.normalize_options = dict(kwargs)
        self.calls.append(("normalize", limit))
        return _Report()

    def backfill_text_fingerprints(
        self,
        *,
        limit,
        progress=None,
        should_stop=None,
        retry_limit=3,
        retry_backoff_seconds=900,
        **kwargs,
    ):
        del progress, should_stop
        self.fingerprint_options = {
            "retry_limit": retry_limit,
            "retry_backoff_seconds": retry_backoff_seconds,
            **kwargs,
        }
        self.calls.append(("backfill_text_fingerprints", limit))
        return _Report()

    def extract_sections(self, *, limit, progress=None, should_stop=None, **kwargs):
        del progress, should_stop, kwargs
        self.calls.append(("extract_sections", limit))
        return _Report()

    def summarize_with_llm(self, **kwargs):
        self.calls.append(("summarize_with_llm", kwargs["limit"]))
        return self.summary_report

    def export_indexes(self, *, progress=None):
        self.calls.append(("export", None))
        return {"index": Path("index.md")}


class _StopAwareFingerprintCatalog(_FakeCatalog):
    def __init__(self):
        super().__init__()
        self.fingerprint_stop_requested: bool | None = None

    def backfill_text_fingerprints(
        self,
        *,
        limit,
        progress=None,
        should_stop=None,
        retry_limit=3,
        retry_backoff_seconds=900,
        **kwargs,
    ):
        del kwargs
        assert should_stop is not None
        self.fingerprint_stop_requested = should_stop()
        return super().backfill_text_fingerprints(
            limit=limit,
            progress=progress,
            should_stop=should_stop,
            retry_limit=retry_limit,
            retry_backoff_seconds=retry_backoff_seconds,
        )


class _ProgressCatalog(_FakeCatalog):
    def scan(self, *, progress=None):
        self.calls.append(("scan", None))
        assert progress is not None
        for current in range(1, 21):
            progress(
                current_path=f"C:/incoming/report-{current}.pdf",
                current=current,
                total=20,
                detail="scanning root company_raw",
            )
        return _Report()

    def normalize(self, *, limit, progress=None, **kwargs):
        del kwargs
        self.calls.append(("normalize", limit))
        assert progress is not None
        progress(
            current_path="C:/incoming/current-report.pdf",
            current=1,
            total=3,
            detail="parser_alive",
            parser_pid=4321,
            parser_elapsed_seconds=12.5,
            parser_timeout_seconds=3600,
            parser_ownership="windows_job",
        )
        return _Report()

    def summarize_with_llm(self, **kwargs):
        self.calls.append(("summarize_with_llm", kwargs["limit"]))
        progress = kwargs.get("progress")
        assert progress is not None
        progress(
            current_path="C:/incoming/current-report.pdf",
            current=1,
            total=2,
            detail="calling LLM summary",
        )
        return self.summary_report

    def export_indexes(self, *, progress=None):
        self.calls.append(("export", None))
        assert progress is not None
        progress(
            current_path="C:/catalog/index",
            current=12,
            total=12,
            detail="wrote source catalog index",
        )
        return {"index": Path("index.md")}


class _Idle:
    def __init__(self, seconds: float, on_battery: bool = False):
        self.seconds = seconds
        self.battery = on_battery
        self.idle_calls = 0

    def idle_seconds(self) -> float:
        self.idle_calls += 1
        return self.seconds

    def on_battery(self) -> bool:
        return self.battery


def test_worker_passes_parser_liveness_and_retry_limits_to_both_paths(tmp_path):
    from company_wiki.source_catalog.worker import SourceCatalogWorker, WorkerConfig

    catalog = _FakeCatalog()
    worker = SourceCatalogWorker(
        catalog,
        WorkerConfig(
            runtime_config=tmp_path / "config.yaml",
            scan_interval_seconds=3600,
            export_interval_seconds=3600,
            poll_interval_seconds=30,
            idle_seconds_required=600,
            normalize_batch_size=1,
            llm_summary_batch_size=1,
            llm_max_input_chars=120000,
            llm_max_output_tokens=1200,
            llm_retry_backoff_seconds=3600,
            allow_processing_on_battery=False,
            document_parse_timeout_seconds=4200,
            parser_heartbeat_interval_seconds=20,
            parser_result_max_bytes=134_217_728,
            normalization_retry_limit=4,
            normalization_retry_backoff_seconds=1200,
        ),
        state_path=tmp_path / "state.json",
        idle_detector=_Idle(700),
        llm_client_factory=lambda: object(),
    )

    worker.run_cycle(now=10_000)

    assert catalog.normalize_options["parser_timeout_seconds"] == 4200
    assert catalog.normalize_options["parser_heartbeat_interval_seconds"] == 20
    assert catalog.normalize_options["parser_result_max_bytes"] == 134_217_728
    assert catalog.normalize_options["retry_limit"] == 4
    assert catalog.normalize_options["retry_backoff_seconds"] == 1200
    assert catalog.fingerprint_options["parser_timeout_seconds"] == 4200
    assert catalog.fingerprint_options["parser_heartbeat_interval_seconds"] == 20
    assert catalog.fingerprint_options["parser_result_max_bytes"] == 134_217_728


def test_worker_persists_stable_parse_timeout_counters(tmp_path):
    from company_wiki.source_catalog.models import ProcessingReport
    from company_wiki.source_catalog.normalizer import DOCUMENT_PARSE_TIMEOUT_CODE
    from company_wiki.source_catalog.worker import SourceCatalogWorker, WorkerConfig

    class TimeoutCatalog(_FakeCatalog):
        def normalize(self, *, limit, progress=None, **kwargs):
            del progress, kwargs
            self.calls.append(("normalize", limit))
            return ProcessingReport(
                "normalize",
                failed=1,
                eligible=1,
                terminal_reasons={DOCUMENT_PARSE_TIMEOUT_CODE: 1},
                last_failure_code=DOCUMENT_PARSE_TIMEOUT_CODE,
                last_failed_document_id="document-timeout",
                last_failed_path="C:/sources/timeout.pdf",
            )

    state_path = tmp_path / "state.json"
    worker = SourceCatalogWorker(
        TimeoutCatalog(),
        WorkerConfig(
            runtime_config=tmp_path / "config.yaml",
            scan_interval_seconds=3600,
            export_interval_seconds=3600,
            poll_interval_seconds=30,
            idle_seconds_required=600,
            normalize_batch_size=1,
            llm_summary_batch_size=1,
            llm_max_input_chars=120000,
            llm_max_output_tokens=1200,
            llm_retry_backoff_seconds=3600,
            allow_processing_on_battery=False,
        ),
        state_path=state_path,
        idle_detector=_Idle(700),
        llm_client_factory=lambda: object(),
    )

    worker.run_cycle(now=10_000)
    persisted = json.loads(state_path.read_text(encoding="utf-8"))

    assert persisted["parse_timeout_total"] == 1
    assert persisted["last_parse_timeout_document_id"] == "document-timeout"
    assert persisted["last_parse_timeout_path"] == "C:/sources/timeout.pdf"


def test_worker_processes_while_the_user_is_active_when_idle_is_not_required(tmp_path):
    from company_wiki.source_catalog.worker import SourceCatalogWorker, WorkerConfig

    catalog = _FakeCatalog()
    config = WorkerConfig(
        runtime_config=tmp_path / "config.yaml",
        scan_interval_seconds=3600,
        export_interval_seconds=3600,
        poll_interval_seconds=30,
        idle_seconds_required=600,
        normalize_batch_size=1,
        llm_summary_batch_size=1,
        llm_max_input_chars=120000,
        llm_max_output_tokens=1200,
        llm_retry_backoff_seconds=3600,
        allow_processing_on_battery=False,
        require_user_idle=False,
    )
    state_path = tmp_path / "state.json"
    idle_detector = _Idle(20)
    worker = SourceCatalogWorker(
        catalog,
        config,
        state_path=state_path,
        idle_detector=idle_detector,
        llm_client_factory=lambda: object(),
    )

    stages: list[str] = []
    first = worker.run_cycle(
        now=10_000,
        activity=lambda status, **_details: stages.append(status),
    )
    assert first["scan"] is not None
    assert first["background_processing"] is True
    assert first["processing_blocked_reason"] is None
    assert first["idle_seconds"] is None
    assert idle_detector.idle_calls == 0
    assert catalog.calls == [
        ("scan", None),
        ("normalize", 1),
        ("backfill_text_fingerprints", 3),
        ("extract_sections", 5),
        ("summarize_with_llm", 1),
        ("export", None),
    ]
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["last_scan_at"] == 10_000
    assert state["normalized_total"] == 1
    assert state["llm_summarized_total"] == 1
    assert state["last_scan_report"]["completed"] == 1
    assert state["last_normalize_report"]["completed"] == 1
    assert state["last_fingerprint_report"]["completed"] == 1
    assert state["last_llm_summary_report"]["completed"] == 1
    assert stages == [
        "scanning",
        "normalizing",
        "fingerprinting",
        "section_extracting",
        "summarizing",
        "exporting",
    ]


def test_worker_can_explicitly_keep_the_historical_user_idle_gate(tmp_path):
    from company_wiki.source_catalog.worker import SourceCatalogWorker, WorkerConfig

    catalog = _FakeCatalog()
    config = WorkerConfig(
        runtime_config=tmp_path / "config.yaml",
        scan_interval_seconds=3600,
        export_interval_seconds=3600,
        poll_interval_seconds=30,
        idle_seconds_required=600,
        normalize_batch_size=1,
        llm_summary_batch_size=1,
        llm_max_input_chars=120000,
        llm_max_output_tokens=1200,
        llm_retry_backoff_seconds=3600,
        allow_processing_on_battery=False,
        require_user_idle=True,
    )
    worker = SourceCatalogWorker(
        catalog,
        config,
        state_path=tmp_path / "state.json",
        idle_detector=_Idle(20),
        llm_client_factory=lambda: object(),
    )

    active = worker.run_cycle(now=10_000)
    assert active["background_processing"] is False
    assert active["processing_blocked_reason"] == "user_active"
    assert [name for name, _ in catalog.calls] == ["scan", "export"]

    worker.idle_detector = _Idle(700)
    inactive = worker.run_cycle(now=10_030)
    assert inactive["background_processing"] is True
    assert inactive["processing_blocked_reason"] is None
    # CW-3.5 / Phase 10: export throttled in cycle 2 (dirty=3 < threshold=5).
    # CW-2.28 Phase 2R: fingerprint stage runs between normalize and summarize.
    assert [name for name, _ in catalog.calls[-4:]] == [
        "normalize",
        "backfill_text_fingerprints",
        "extract_sections",
        "summarize_with_llm",
    ]


def test_worker_still_respects_the_battery_gate_when_user_idle_is_not_required(
    tmp_path,
):
    from company_wiki.source_catalog.worker import SourceCatalogWorker, WorkerConfig

    catalog = _FakeCatalog()
    worker = SourceCatalogWorker(
        catalog,
        WorkerConfig(
            runtime_config=tmp_path / "config.yaml",
            scan_interval_seconds=3600,
            export_interval_seconds=3600,
            poll_interval_seconds=30,
            idle_seconds_required=600,
            normalize_batch_size=1,
            llm_summary_batch_size=1,
            llm_max_input_chars=120000,
            llm_max_output_tokens=1200,
            llm_retry_backoff_seconds=3600,
            allow_processing_on_battery=False,
            require_user_idle=False,
        ),
        state_path=tmp_path / "state.json",
        idle_detector=_Idle(20, on_battery=True),
        llm_client_factory=lambda: object(),
    )

    result = worker.run_cycle(now=10_000)

    assert result["background_processing"] is False
    assert result["processing_blocked_reason"] == "on_battery"
    assert [name for name, _ in catalog.calls] == ["scan", "export"]


def test_worker_reports_document_paths_percentages_and_throttles_scan_updates(tmp_path):
    from company_wiki.source_catalog.worker import SourceCatalogWorker, WorkerConfig

    catalog = _ProgressCatalog()
    worker = SourceCatalogWorker(
        catalog,
        WorkerConfig(
            runtime_config=tmp_path / "config.yaml",
            scan_interval_seconds=3600,
            export_interval_seconds=3600,
            poll_interval_seconds=30,
            idle_seconds_required=600,
            normalize_batch_size=3,
            llm_summary_batch_size=2,
            llm_max_input_chars=120000,
            llm_max_output_tokens=1200,
            llm_retry_backoff_seconds=3600,
            allow_processing_on_battery=False,
        ),
        state_path=tmp_path / "state.json",
        idle_detector=_Idle(700),
        llm_client_factory=lambda: object(),
    )
    events: list[tuple[str, dict]] = []

    worker.run_cycle(
        now=10_000,
        activity=lambda status, **details: events.append((status, details)),
    )

    scanning = [details for stage, details in events if stage == "scanning"]
    assert len(scanning) <= 2
    assert scanning[-1]["current_path"] == "C:/incoming/report-20.pdf"
    assert scanning[-1]["progress_current"] == 20
    assert scanning[-1]["progress_percent"] == 100.0
    normalizing = [details for stage, details in events if stage == "normalizing"][-1]
    assert normalizing["current_path"] == "C:/incoming/current-report.pdf"
    assert normalizing["progress_current"] == 1
    assert normalizing["progress_total"] == 3
    assert normalizing["progress_percent"] == 33.3
    assert normalizing["progress_detail"] == "parser_alive"
    assert normalizing["parser_pid"] == 4321
    assert normalizing["parser_elapsed_seconds"] == 12.5
    assert normalizing["parser_timeout_seconds"] == 3600
    assert normalizing["parser_ownership"] == "windows_job"
    summarizing = [details for stage, details in events if stage == "summarizing"][-1]
    assert summarizing["progress_percent"] == 50.0
    assert summarizing["progress_detail"] == "calling LLM summary"
    assert worker.state["last_export_progress_total"] == 12
    assert worker.state["last_export_progress_detail"] == "wrote source catalog index"
    assert worker.state["last_export_duration_seconds"] >= 0


def test_worker_defers_llm_retries_after_a_global_provider_failure(tmp_path):
    from company_wiki.source_catalog.worker import SourceCatalogWorker, WorkerConfig

    catalog = _FakeCatalog()
    catalog.summary_report = _Report(
        completed=0,
        failed=1,
        error="LLMProviderError: HTTP 429 rate limited",
        failed_document_id="urn:company-wiki:document:sha256:abc",
        failure_scope="global",
    )
    config = WorkerConfig(
        runtime_config=tmp_path / "config.yaml",
        scan_interval_seconds=3600,
        export_interval_seconds=3600,
        poll_interval_seconds=30,
        idle_seconds_required=600,
        normalize_batch_size=1,
        llm_summary_batch_size=1,
        llm_max_input_chars=120000,
        llm_max_output_tokens=1200,
        llm_retry_backoff_seconds=3600,
        allow_processing_on_battery=False,
    )
    worker = SourceCatalogWorker(
        catalog,
        config,
        state_path=tmp_path / "state.json",
        idle_detector=_Idle(700),
        llm_client_factory=lambda: object(),
    )

    first = worker.run_cycle(now=20_000)
    assert first["summarize_llm"]["failed"] == 1
    assert worker.state["llm_retry_after"] == 23_600
    assert worker.state["last_error"] == ("LLMProviderError: HTTP 429 rate limited")

    catalog.calls.clear()
    second = worker.run_cycle(now=20_030)
    assert second["summarize_llm"]["status"] == "deferred"
    assert "summarize_with_llm" not in [name for name, _ in catalog.calls]
    assert worker.state["last_error"] == "LLMProviderError: HTTP 429 rate limited"
    assert worker.state["last_error_scope"] == "llm_global"


def test_successful_local_cycle_replaces_stale_cycle_error_with_active_llm_error(
    tmp_path,
):
    from company_wiki.source_catalog.worker import SourceCatalogWorker, WorkerConfig

    class FailNormalizeOnce(_FakeCatalog):
        def __init__(self):
            super().__init__()
            self.fail_once = True

        def normalize(self, *, limit, progress=None, **kwargs):
            if self.fail_once:
                self.fail_once = False
                raise OSError("synthetic disk I/O error")
            return super().normalize(limit=limit, progress=progress, **kwargs)

    catalog = FailNormalizeOnce()
    config = WorkerConfig(
        runtime_config=tmp_path / "config.yaml",
        scan_interval_seconds=3600,
        export_interval_seconds=3600,
        poll_interval_seconds=30,
        idle_seconds_required=600,
        normalize_batch_size=1,
        llm_summary_batch_size=1,
        llm_max_input_chars=120000,
        llm_max_output_tokens=1200,
        llm_retry_backoff_seconds=3600,
        allow_processing_on_battery=False,
    )
    worker = SourceCatalogWorker(
        catalog,
        config,
        state_path=tmp_path / "state.json",
        idle_detector=_Idle(700),
        llm_client_factory=lambda: object(),
    )
    retry_after = __import__("time").time() + 3600
    global_error = "LLMProviderError: HTTP 429 quota exhausted"
    worker.state.update(
        {
            "llm_retry_after": retry_after,
            "last_error": global_error,
            "last_llm_summary_report": {
                "failed": 1,
                "failure_scope": "global",
                "error": global_error,
            },
        }
    )

    failed = worker._run_cycle_guarded()
    assert failed["status"] == "failed"
    assert worker.state["last_error"] == "OSError: synthetic disk I/O error"

    recovered = worker.run_cycle(now=retry_after - 1800)

    assert recovered["summarize_llm"]["status"] == "deferred"
    assert worker.state["last_cycle_status"] == "completed"
    assert worker.state["last_error"] == global_error
    assert worker.state["last_error_scope"] == "llm_global"


def test_successful_cycle_without_llm_work_clears_a_stale_cycle_error(tmp_path):
    from company_wiki.source_catalog.worker import SourceCatalogWorker, WorkerConfig

    worker = SourceCatalogWorker(
        _FakeCatalog(),
        WorkerConfig(
            runtime_config=tmp_path / "config.yaml",
            scan_interval_seconds=3600,
            export_interval_seconds=3600,
            poll_interval_seconds=30,
            idle_seconds_required=600,
            normalize_batch_size=1,
            llm_summary_batch_size=1,
            llm_max_input_chars=120000,
            llm_max_output_tokens=1200,
            llm_retry_backoff_seconds=3600,
            allow_processing_on_battery=False,
            require_user_idle=True,
        ),
        state_path=tmp_path / "state.json",
        idle_detector=_Idle(0),
        llm_client_factory=lambda: object(),
    )
    worker.state.update(
        {
            "last_error": "OSError: recovered disk I/O error",
            "last_error_scope": "cycle",
        }
    )

    result = worker.run_cycle(now=20_000)

    assert result["summarize_llm"] is None
    assert worker.state["last_cycle_status"] == "completed"
    assert worker.state["last_error"] is None
    assert worker.state["last_error_scope"] is None


def test_worker_continues_after_a_document_scoped_llm_failure(tmp_path):
    from company_wiki.source_catalog.worker import SourceCatalogWorker, WorkerConfig

    catalog = _FakeCatalog()
    catalog.summary_report = _Report(
        completed=0,
        failed=1,
        error="LLMSummaryError: forbidden investment conclusion",
        failed_document_id="urn:company-wiki:document:sha256:abc",
        failure_scope="document",
        retry_after=23_600,
        retry_count=1,
    )
    config = WorkerConfig(
        runtime_config=tmp_path / "config.yaml",
        scan_interval_seconds=3600,
        export_interval_seconds=3600,
        poll_interval_seconds=30,
        idle_seconds_required=600,
        normalize_batch_size=1,
        llm_summary_batch_size=1,
        llm_max_input_chars=120000,
        llm_max_output_tokens=1200,
        llm_retry_backoff_seconds=3600,
        allow_processing_on_battery=False,
    )
    worker = SourceCatalogWorker(
        catalog,
        config,
        state_path=tmp_path / "state.json",
        idle_detector=_Idle(700),
        llm_client_factory=lambda: object(),
    )

    first = worker.run_cycle(now=20_000)

    assert first["summarize_llm"]["failure_scope"] == "document"
    assert worker.state["llm_retry_after"] is None
    assert (
        worker.state["last_error"] == "LLMSummaryError: forbidden investment conclusion"
    )

    catalog.calls.clear()
    worker.run_cycle(now=20_030)

    assert "summarize_with_llm" in [name for name, _ in catalog.calls]


def test_worker_clears_a_legacy_unscoped_llm_retry_on_upgrade(tmp_path):
    from company_wiki.source_catalog.worker import SourceCatalogWorker, WorkerConfig

    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "llm_retry_after": 23_600,
                "last_llm_summary_report": {
                    "completed": 0,
                    "failed": 1,
                    "error": "LLMSummaryError: forbidden investment conclusion",
                },
            }
        ),
        encoding="utf-8",
    )
    config = WorkerConfig(
        runtime_config=tmp_path / "config.yaml",
        scan_interval_seconds=3600,
        export_interval_seconds=3600,
        poll_interval_seconds=30,
        idle_seconds_required=600,
        normalize_batch_size=1,
        llm_summary_batch_size=1,
        llm_max_input_chars=120000,
        llm_max_output_tokens=1200,
        llm_retry_backoff_seconds=3600,
        allow_processing_on_battery=False,
    )

    worker = SourceCatalogWorker(
        _FakeCatalog(),
        config,
        state_path=state_path,
        idle_detector=_Idle(700),
        llm_client_factory=lambda: object(),
    )

    assert worker.state["llm_retry_after"] is None


class _StoppingSession:
    def __init__(self):
        self.heartbeats: list[str] = []
        self.heartbeat_details: list[tuple[str, dict]] = []
        self.waits: list[float] = []
        self.closed = False
        self.should_stop_calls = 0

    def heartbeat(self, status: str, **details):
        self.heartbeats.append(status)
        self.heartbeat_details.append((status, details))

    def should_stop(self):
        self.should_stop_calls += 1
        return False

    def wait(self, seconds: float):
        self.waits.append(seconds)
        return False

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


class _ControlStub:
    def __init__(self, session=None, *, desired_state="enabled"):
        self.session = session
        self.desired_state = desired_state

    def status(self):
        return {"desired_state": self.desired_state}

    def open_session(self):
        if self.desired_state == "paused":
            raise RuntimeError("source-catalog worker is paused")
        return self.session


def test_forever_worker_exits_without_catalog_work_when_persistently_paused(tmp_path):
    from company_wiki.source_catalog.worker import SourceCatalogWorker, WorkerConfig

    catalog = _FakeCatalog()
    config = WorkerConfig(
        runtime_config=tmp_path / "config.yaml",
        scan_interval_seconds=3600,
        export_interval_seconds=3600,
        poll_interval_seconds=30,
        idle_seconds_required=600,
        normalize_batch_size=1,
        llm_summary_batch_size=1,
        llm_max_input_chars=120000,
        llm_max_output_tokens=1200,
        llm_retry_backoff_seconds=3600,
        allow_processing_on_battery=False,
    )
    worker = SourceCatalogWorker(
        catalog,
        config,
        state_path=tmp_path / "state.json",
        idle_detector=_Idle(20),
        llm_client_factory=lambda: object(),
    )

    result = worker.run_forever(control=_ControlStub(desired_state="paused"))

    assert result["status"] == "paused"
    assert catalog.calls == []


def test_forever_worker_uses_interruptible_wait_and_releases_session(tmp_path):
    from company_wiki.source_catalog.worker import SourceCatalogWorker, WorkerConfig

    catalog = _FakeCatalog()
    config = WorkerConfig(
        runtime_config=tmp_path / "config.yaml",
        scan_interval_seconds=3600,
        export_interval_seconds=3600,
        poll_interval_seconds=30,
        idle_seconds_required=600,
        normalize_batch_size=1,
        llm_summary_batch_size=1,
        llm_max_input_chars=120000,
        llm_max_output_tokens=1200,
        llm_retry_backoff_seconds=3600,
        allow_processing_on_battery=False,
        require_user_idle=True,
    )
    worker = SourceCatalogWorker(
        catalog,
        config,
        state_path=tmp_path / "state.json",
        idle_detector=_Idle(20),
        llm_client_factory=lambda: object(),
    )
    session = _StoppingSession()

    result = worker.run_forever(control=_ControlStub(session))

    assert result["status"] == "stopped"
    assert session.closed is True
    assert session.heartbeats[:2] == ["starting", "running"]
    assert "waiting" in session.heartbeats
    assert session.heartbeats[-1] == "stopping"
    assert [name for name, _ in catalog.calls] == ["scan", "export"]


def test_forever_worker_freezes_loaded_code_fingerprint_at_session_start(
    tmp_path, monkeypatch
):
    import company_wiki.source_catalog.worker as worker_module
    from company_wiki.source_catalog.worker import SourceCatalogWorker, WorkerConfig

    monkeypatch.setattr(
        worker_module,
        "source_bundle_fingerprint",
        lambda _root: {
            "fingerprint": "a" * 64,
            "error": None,
            "files": [{"path": "worker.py", "sha256": "b" * 64}],
        },
        raising=False,
    )
    session = _StoppingSession()
    worker = SourceCatalogWorker(
        _FakeCatalog(),
        WorkerConfig(
            runtime_config=tmp_path / "config.yaml",
            scan_interval_seconds=3600,
            export_interval_seconds=3600,
            poll_interval_seconds=30,
            idle_seconds_required=600,
            normalize_batch_size=1,
            llm_summary_batch_size=1,
            llm_max_input_chars=120000,
            llm_max_output_tokens=1200,
            llm_retry_backoff_seconds=3600,
            allow_processing_on_battery=False,
            require_user_idle=True,
        ),
        state_path=tmp_path / "state.json",
        project_root=tmp_path,
        idle_detector=_Idle(20),
        llm_client_factory=lambda: object(),
    )

    worker.run_forever(control=_ControlStub(session))

    starting = next(
        details for status, details in session.heartbeat_details if status == "starting"
    )
    assert starting["loaded_code_fingerprint"] == "a" * 64
    assert starting["loaded_code_fingerprint_error"] is None


def test_forever_worker_uses_active_wait_and_reports_next_wake_after_productive_cycle(
    tmp_path,
):
    from company_wiki.source_catalog.worker import SourceCatalogWorker, WorkerConfig

    session = _StoppingSession()
    worker = SourceCatalogWorker(
        _FakeCatalog(),
        WorkerConfig(
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
        ),
        state_path=tmp_path / "state.json",
        idle_detector=_Idle(20),
        llm_client_factory=lambda: object(),
    )

    result = worker.run_forever(control=_ControlStub(session))

    assert result["status"] == "stopped"
    assert session.waits == [2]
    waiting = [
        details for status, details in session.heartbeat_details if status == "waiting"
    ][-1]
    assert waiting["cycle_productive"] is True
    assert waiting["next_wait_seconds"] == 2
    assert waiting["next_wake_reason"] == "productive_cycle"
    assert waiting["next_wake_at"] >= worker.state["last_cycle_at"]


def test_forever_worker_passes_session_stop_callback_to_fingerprint_backfill(
    tmp_path,
):
    from company_wiki.source_catalog.worker import SourceCatalogWorker, WorkerConfig

    catalog = _StopAwareFingerprintCatalog()
    session = _StoppingSession()
    worker = SourceCatalogWorker(
        catalog,
        WorkerConfig(
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
        ),
        state_path=tmp_path / "state.json",
        idle_detector=_Idle(20),
        llm_client_factory=lambda: object(),
    )

    result = worker.run_forever(control=_ControlStub(session))

    assert result["status"] == "stopped"
    assert catalog.fingerprint_stop_requested is False
    assert session.should_stop_calls >= 2


@pytest.mark.parametrize(
    ("summary_report", "on_battery", "expected_reason"),
    [
        (
            _Report(
                completed=0,
                failed=1,
                error="LLMProviderError: HTTP 429 rate limited",
                failure_scope="global",
            ),
            False,
            "llm_global_failure",
        ),
        (_Report(completed=0), True, "on_battery"),
    ],
)
def test_forever_worker_keeps_normal_poll_for_global_failure_or_battery_gate(
    tmp_path, summary_report, on_battery, expected_reason
):
    from company_wiki.source_catalog.worker import SourceCatalogWorker, WorkerConfig

    catalog = _FakeCatalog()
    catalog.summary_report = summary_report
    session = _StoppingSession()
    worker = SourceCatalogWorker(
        catalog,
        WorkerConfig(
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
        ),
        state_path=tmp_path / "state.json",
        idle_detector=_Idle(20, on_battery=on_battery),
        llm_client_factory=lambda: object(),
    )

    worker.run_forever(control=_ControlStub(session))

    assert session.waits == [30]
    waiting = [
        details for status, details in session.heartbeat_details if status == "waiting"
    ][-1]
    assert waiting["cycle_productive"] is False
    assert waiting["next_wait_seconds"] == 30
    assert waiting["next_wake_reason"] == expected_reason


class _Response:
    def __init__(self, content: str, *, success: bool = True, error: str = ""):
        self.content = content
        self.success = success
        self.error = error
        self.model = "MiniMax-M3"
        self.usage = {"total_tokens": 321}


class _FakeLLM:
    provider = "minimax"
    model = "MiniMax-M3"

    def __init__(self, content: str):
        self.content = content
        self.prompts: list[str] = []
        self.generate_kwargs: list[dict] = []

    def generate(self, prompt: str, **kwargs):
        self.prompts.append(prompt)
        self.generate_kwargs.append(kwargs)
        return _Response(self.content)


class _ProviderFailingLLM(_FakeLLM):
    def generate(self, prompt: str, **kwargs):
        self.prompts.append(prompt)
        self.generate_kwargs.append(kwargs)
        response = _Response("", success=False, error="HTTP 429 rate limited")
        response.provider = "mimo"
        response.model = "mimo-v2.5-pro"
        return response


def test_llm_summary_is_source_bound_auditable_and_replaces_extractive_summary(
    tmp_path,
):
    catalog, source_root = _catalog(tmp_path)
    before = source_root.joinpath("meeting.txt").read_bytes()
    catalog.summarize()
    client = _FakeLLM(
        json.dumps(
            {
                "overview": "文档记录了2025年的经营进展。",
                "key_facts": [
                    "公司收入增长20%。",
                    "新增客户12家。",
                    "产能达到100万台。",
                ],
                "topics": ["收入", "客户", "产能"],
                "limitations": ["仅依据当前规范化文本。"],
            },
            ensure_ascii=False,
        )
    )

    progress_events: list[dict] = []
    report = catalog.summarize_with_llm(
        limit=1,
        llm_client_factory=lambda: client,
        max_input_chars=120000,
        max_output_tokens=1200,
        progress=lambda **details: progress_events.append(details),
    )

    assert report.completed == 1
    row = catalog.query(limit=1)[0]
    content = Path(row["summary_path"]).read_text(encoding="utf-8")
    assert "summary_method: llm" in content
    assert "llm_provider: minimax" in content
    assert "llm_model: MiniMax-M3" in content
    assert "公司收入增长20%" in content
    assert row["source_id"] in content
    assert source_root.joinpath("meeting.txt").read_bytes() == before
    summary_artifacts = [a for a in row["artifacts"] if a["artifact_role"] == "summary"]
    assert len(summary_artifacts) == 1
    assert summary_artifacts[0]["generator_name"] == "source_catalog_llm_summary"
    assert len(client.generate_kwargs) == 1
    assert client.generate_kwargs[0]["max_tokens"] == 1200
    assert client.generate_kwargs[0]["json_mode"] is True
    assert progress_events == [
        {
            "current_path": str(source_root.joinpath("meeting.txt")),
            "current": 1,
            "total": 1,
            "detail": "calling LLM summary",
        }
    ]


def test_llm_summary_deterministically_bounds_overlong_lists(tmp_path):
    catalog, _ = _catalog(tmp_path)
    client = _FakeLLM(
        json.dumps(
            {
                "overview": "文档记录了可核对的经营数据。",
                "key_facts": [f"事实{i}" for i in range(10)],
                "topics": [f"主题{i}" for i in range(10)],
                "limitations": [f"局限{i}" for i in range(6)],
            },
            ensure_ascii=False,
        )
    )

    report = catalog.summarize_with_llm(
        limit=1,
        llm_client_factory=lambda: client,
        max_input_chars=120000,
        max_output_tokens=2400,
    )

    assert report.completed == 1
    assert report.failed == 0
    content = Path(catalog.query(limit=1)[0]["summary_path"]).read_text(
        encoding="utf-8"
    )
    assert "事实7" in content and "事实8" not in content
    assert "主题7" in content and "主题8" not in content
    assert "局限3" in content and "局限4" not in content


def test_llm_summary_rejects_generated_investment_conclusions(tmp_path):
    catalog, _ = _catalog(tmp_path)
    client = _FakeLLM(
        json.dumps(
            {
                "overview": "建议买入评级，目标价100元。",
                "key_facts": ["公司收入增长20%。"],
                "topics": [],
                "limitations": [],
            },
            ensure_ascii=False,
        )
    )

    report = catalog.summarize_with_llm(
        limit=1,
        llm_client_factory=lambda: client,
        max_input_chars=120000,
        max_output_tokens=1200,
    )

    assert report.completed == 0
    assert report.failed == 1
    assert (
        report.error
        == "LLMSummaryError: LLM response contains a forbidden investment conclusion"
    )
    assert report.failed_document_id
    assert report.failure_scope == "permanent_document"
    # CW-3.5 / Phase 10: permanent_document errors still get recorded
    # in the failure table with a long retry window, but the report's
    # retry_after/retry_count fields are None (no immediate backoff needed).
    assert report.retry_after is not None or report.retry_count is None
    assert catalog.query(limit=1)[0]["summary_path"] is None

    failure = catalog.store.fetchone(
        "SELECT * FROM llm_summary_failures WHERE document_id=?",
        (report.failed_document_id,),
    )
    assert failure is not None
    assert failure["failure_scope"] == "permanent_document"
    assert failure["attempt_count"] >= 1
    assert failure["retry_after"] == report.retry_after


def test_document_scoped_llm_failure_does_not_block_the_next_document(tmp_path):
    from company_wiki.source_catalog.store import read_pipeline_status

    catalog, source_root = _catalog(tmp_path)
    bad_client = _FakeLLM(
        json.dumps(
            {
                "overview": "建议买入评级。",
                "key_facts": ["公司收入增长20%。"],
                "topics": [],
                "limitations": [],
            },
            ensure_ascii=False,
        )
    )
    first = catalog.summarize_with_llm(
        limit=1,
        llm_client_factory=lambda: bad_client,
        max_input_chars=120000,
        max_output_tokens=1200,
    )
    assert first.failure_scope in ("document", "permanent_document")

    (source_root / "second.txt").write_text(
        "2026年新增订单20亿元，交付产品1000台。", encoding="utf-8"
    )
    catalog.scan()
    catalog.normalize()
    good_client = _FakeLLM(
        json.dumps(
            {
                "overview": "文档记录新增订单与产品交付。",
                "key_facts": ["新增订单20亿元。", "交付产品1000台。"],
                "topics": ["订单", "交付"],
                "limitations": [],
            },
            ensure_ascii=False,
        )
    )

    second = catalog.summarize_with_llm(
        limit=1,
        llm_client_factory=lambda: good_client,
        max_input_chars=120000,
        max_output_tokens=1200,
    )

    assert second.completed == 1
    assert second.failed == 0
    assert len(good_client.prompts) == 1
    status = read_pipeline_status(catalog.config.database_path)
    assert status["llm_summary"]["completed"] == 1
    assert status["llm_summary"]["failed"] == 1
    assert status["llm_summary"]["pending"] == 0

    no_retry_client = _FakeLLM(good_client.content)
    deferred_document = catalog.summarize_with_llm(
        limit=1,
        llm_client_factory=lambda: no_retry_client,
        max_input_chars=120000,
        max_output_tokens=1200,
    )
    assert deferred_document.completed == 0
    assert deferred_document.failed == 0
    assert no_retry_client.prompts == []


def test_provider_failure_requests_global_retry_without_document_quarantine(tmp_path):
    catalog, _ = _catalog(tmp_path)
    client = _ProviderFailingLLM("")

    report = catalog.summarize_with_llm(
        limit=1,
        llm_client_factory=lambda: client,
        max_input_chars=120000,
        max_output_tokens=1200,
    )

    assert report.completed == 0
    assert report.failed == 1
    assert report.failure_scope == "global"
    assert report.retry_after is None
    assert report.retry_count is None
    assert "mimo/mimo-v2.5-pro" in report.error
    assert (
        catalog.store.fetchone("SELECT COUNT(*) AS count FROM llm_summary_failures")[
            "count"
        ]
        == 0
    )


def test_configured_llm_uses_mimo_when_primary_credentials_are_absent(monkeypatch):
    from company_wiki.source_catalog.llm_summarizer import build_configured_llm_client

    project = Path(__file__).resolve().parents[2]
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.setenv("MIMO_API_KEY", "test-only-placeholder")
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")

    client = build_configured_llm_client(project, project / "config.yaml")

    assert client.provider == "mimo"
    assert client.model == "mimo-v2.5-pro"
    assert client.available is True
    assert client.workload == "source"


def test_configured_llm_uses_project_dotenv_over_stale_inherited_keys(
    tmp_path, monkeypatch
):
    import config as config_module
    from company_wiki.source_catalog.llm_summarizer import build_configured_llm_client

    project = Path(__file__).resolve().parents[2]
    runtime_config = tmp_path / "config.yaml"
    runtime_config.write_text(
        """
llm:
  provider: minimax
  model: MiniMax-M3
  base_url: https://api.minimaxi.com/v1
  fallback:
    provider: mimo
    model: mimo-v2.5-pro
    base_url: https://token-plan-cn.xiaomimimo.com/v1
    enabled: true
    usage_scope: general
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text(
        "MINIMAX_API_KEY=file-primary-test-only\n"
        "MIMO_API_KEY=file-fallback-test-only\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config_module, "WIKI_ROOT", tmp_path)
    monkeypatch.delenv("PYTHON_DOTENV_DISABLED", raising=False)
    monkeypatch.setenv("MINIMAX_API_KEY", "stale-primary-test-only")
    monkeypatch.setenv("MIMO_API_KEY", "stale-fallback-test-only")

    client = build_configured_llm_client(project, runtime_config)

    assert client.api_key == "file-primary-test-only"
    assert client.workload == "source"
    assert client.fallback_client is not None
    assert client.fallback_client.api_key == "file-fallback-test-only"
    assert client.fallback_client.workload == "source"


def test_windows_startup_spec_is_logon_triggered_and_does_not_start_task(tmp_path):
    from company_wiki.source_catalog.startup import build_startup_task_args

    project = tmp_path / "project with spaces"
    launcher = project / "scripts" / "source_catalog_worker.ps1"
    args = build_startup_task_args(
        project_root=project,
        launcher_path=launcher,
        python_executable=Path("C:/Python/python.exe"),
        task_name="CompanyWiki Source Catalog",
    )

    assert args[0].lower().endswith("schtasks.exe")
    assert "/Create" in args
    assert "/SC" in args and "ONLOGON" in args
    assert "/DELAY" in args
    assert "/Run" not in args
    assert "wscript.exe" in args[args.index("/TR") + 1].lower()
    assert "//B //Nologo" in args[args.index("/TR") + 1]
    assert "source_catalog_worker_at_logon.vbs" in args[args.index("/TR") + 1]


def test_logon_delay_is_worker_interruptible_and_double_click_controls_exist():
    project = Path(__file__).resolve().parents[2]
    logon_launcher = (
        project / "scripts" / "source_catalog_worker_at_logon.ps1"
    ).read_text(encoding="utf-8")
    hidden_host = (
        project / "scripts" / "source_catalog_worker_at_logon.vbs"
    ).read_text(encoding="utf-8")
    worker_launcher = (project / "scripts" / "source_catalog_worker.ps1").read_text(
        encoding="utf-8"
    )
    control = (project / "scripts" / "source_catalog_control.ps1").read_text(
        encoding="utf-8"
    )
    double_click = project / "scripts" / "source_catalog_control.cmd"

    assert "Start-Sleep" not in logon_launcher
    assert "Start-Process" in logon_launcher
    assert "shell.Run(command, 0, False)" in hidden_host
    assert "& (Join-Path" not in logon_launcher
    assert "-StartupDelaySeconds 120" in logon_launcher
    assert "--startup-delay-seconds" in worker_launcher
    assert all(
        action in control
        for action in ("worker-status", "worker-pause", "worker-resume", "worker-stop")
    )
    assert double_click.is_file()


def test_worker_launcher_records_output_and_exit_events_for_logon_startup():
    project = Path(__file__).resolve().parents[2]
    worker_launcher = (project / "scripts" / "source_catalog_worker.ps1").read_text(
        encoding="utf-8"
    )

    assert "worker_stdout-" in worker_launcher
    assert "worker_stderr-" in worker_launcher
    assert "worker_launcher.lock" in worker_launcher
    assert "worker_launcher_events.jsonl" in worker_launcher
    assert "function Write-LauncherEvent" in worker_launcher
    assert "Write-LauncherEvent -Status 'starting'" in worker_launcher
    assert "-Status 'child_started'" in worker_launcher
    assert "-Status 'restarting'" in worker_launcher
    assert "-Status 'launcher_exception'" in worker_launcher
    assert "Start-Process" in worker_launcher
    assert "RedirectStandardOutput" in worker_launcher
    assert "RedirectStandardError" in worker_launcher
    assert "*>>" not in worker_launcher
    assert "exit_code" in worker_launcher


def test_control_center_survives_startup_status_failures_and_marks_stale_runtime():
    project = Path(__file__).resolve().parents[2]
    control = (project / "scripts" / "source_catalog_control.ps1").read_text(
        encoding="utf-8"
    )

    assert "function Show-WorkerStatusSafely" in control
    assert "Unable to read worker status" in control
    assert "if ($Status.runtime_state -eq 'running' -and $Status.pid)" in control
    assert "if ($Status.stale_runtime -and $Status.pid)" in control
    assert "Window title could not be set" in control
    assert "control_center.log" in control
    assert "[Console]::InputEncoding = $Utf8NoBom" in control
    assert "[Console]::OutputEncoding = $Utf8NoBom" in control
    assert "$OutputEncoding = $Utf8NoBom" in control
    assert "Pipeline inventory" in control
    assert "Last scan" in control
    assert "Markdown" in control
    assert "LLM summary" in control
    assert "function Read-ControlChoiceWithLiveProgress" in control
    assert "[Console]::KeyAvailable" in control
    assert "Write-Progress" in control
    assert "worker_runtime.json" in control
    assert "$RuntimeStaleAfterSeconds = 60" in control
    assert "Stale heartbeat; last beat" in control
    assert "if ($Stage -eq 'idle') { $Stage = 'waiting' }" in control
    assert "waiting for next cycle" in control
    assert "Next wake" in control
    assert "next_wait_seconds" in control
    assert "next_wake_reason" in control
    assert "next_wake_at" in control
    assert "Start-Sleep -Milliseconds 500" in control


class _Response:
    def __init__(self, content: str, *, success: bool = True, error: str = ""):
        self.content = content
        self.success = success
        self.error = error
        self.model = "MiniMax-M3"
        self.usage = {"total_tokens": 321}


class _FakeLLM:
    provider = "minimax"
    model = "MiniMax-M3"

    def __init__(self, content: str):
        self.content = content
        self.prompts: list[str] = []
        self.generate_kwargs: list[dict] = []

    def generate(self, prompt: str, **kwargs):
        self.prompts.append(prompt)
        self.generate_kwargs.append(kwargs)
        return _Response(self.content)


class _ProviderFailingLLM(_FakeLLM):
    def generate(self, prompt: str, **kwargs):
        self.prompts.append(prompt)
        self.generate_kwargs.append(kwargs)
        response = _Response("", success=False, error="HTTP 429 rate limited")
        response.provider = "mimo"
        response.model = "mimo-v2.5-pro"
        return response


def test_llm_summary_is_source_bound_auditable_and_replaces_extractive_summary(
    tmp_path,
):
    catalog, source_root = _catalog(tmp_path)
    before = source_root.joinpath("meeting.txt").read_bytes()
    catalog.summarize()
    client = _FakeLLM(
        json.dumps(
            {
                "overview": "文档记录了2025年的经营进展。",
                "key_facts": [
                    "公司收入增长20%。",
                    "新增客户12家。",
                    "产能达到100万台。",
                ],
                "topics": ["收入", "客户", "产能"],
                "limitations": ["仅依据当前规范化文本。"],
            },
            ensure_ascii=False,
        )
    )

    progress_events: list[dict] = []
    report = catalog.summarize_with_llm(
        limit=1,
        llm_client_factory=lambda: client,
        max_input_chars=120000,
        max_output_tokens=1200,
        progress=lambda **details: progress_events.append(details),
    )

    assert report.completed == 1
    row = catalog.query(limit=1)[0]
    content = Path(row["summary_path"]).read_text(encoding="utf-8")
    assert "summary_method: llm" in content
    assert "llm_provider: minimax" in content
    assert "llm_model: MiniMax-M3" in content
    assert "公司收入增长20%" in content
    assert row["source_id"] in content
    assert source_root.joinpath("meeting.txt").read_bytes() == before
    summary_artifacts = [a for a in row["artifacts"] if a["artifact_role"] == "summary"]
    assert len(summary_artifacts) == 1
    assert summary_artifacts[0]["generator_name"] == "source_catalog_llm_summary"
    assert len(client.generate_kwargs) == 1
    assert client.generate_kwargs[0]["max_tokens"] == 1200
    assert client.generate_kwargs[0]["json_mode"] is True
    assert progress_events == [
        {
            "current_path": str(source_root.joinpath("meeting.txt")),
            "current": 1,
            "total": 1,
            "detail": "calling LLM summary",
        }
    ]


def test_llm_summary_deterministically_bounds_overlong_lists(tmp_path):
    catalog, _ = _catalog(tmp_path)
    client = _FakeLLM(
        json.dumps(
            {
                "overview": "文档记录了可核对的经营数据。",
                "key_facts": [f"事实{i}" for i in range(10)],
                "topics": [f"主题{i}" for i in range(10)],
                "limitations": [f"局限{i}" for i in range(6)],
            },
            ensure_ascii=False,
        )
    )

    report = catalog.summarize_with_llm(
        limit=1,
        llm_client_factory=lambda: client,
        max_input_chars=120000,
        max_output_tokens=2400,
    )

    assert report.completed == 1
    assert report.failed == 0
    content = Path(catalog.query(limit=1)[0]["summary_path"]).read_text(
        encoding="utf-8"
    )
    assert "事实7" in content and "事实8" not in content
    assert "主题7" in content and "主题8" not in content
    assert "局限3" in content and "局限4" not in content


def test_llm_summary_rejects_generated_investment_conclusions(tmp_path):
    catalog, _ = _catalog(tmp_path)
    client = _FakeLLM(
        json.dumps(
            {
                "overview": "建议买入评级，目标价100元。",
                "key_facts": ["公司收入增长20%。"],
                "topics": [],
                "limitations": [],
            },
            ensure_ascii=False,
        )
    )

    report = catalog.summarize_with_llm(
        limit=1,
        llm_client_factory=lambda: client,
        max_input_chars=120000,
        max_output_tokens=1200,
    )

    assert report.completed == 0
    assert report.failed == 1
    assert (
        report.error
        == "LLMSummaryError: LLM response contains a forbidden investment conclusion"
    )
    assert report.failed_document_id
    assert report.failure_scope == "permanent_document"
    # CW-3.5 / Phase 10: permanent_document errors still get recorded
    # in the failure table with a long retry window, but the report's
    # retry_after/retry_count fields are None (no immediate backoff needed).
    assert report.retry_after is not None or report.retry_count is None
    assert catalog.query(limit=1)[0]["summary_path"] is None

    failure = catalog.store.fetchone(
        "SELECT * FROM llm_summary_failures WHERE document_id=?",
        (report.failed_document_id,),
    )
    assert failure is not None
    assert failure["failure_scope"] == "permanent_document"
    assert failure["attempt_count"] >= 1
    assert failure["retry_after"] == report.retry_after


def test_document_scoped_llm_failure_does_not_block_the_next_document(tmp_path):
    from company_wiki.source_catalog.store import read_pipeline_status

    catalog, source_root = _catalog(tmp_path)
    bad_client = _FakeLLM(
        json.dumps(
            {
                "overview": "建议买入评级。",
                "key_facts": ["公司收入增长20%。"],
                "topics": [],
                "limitations": [],
            },
            ensure_ascii=False,
        )
    )
    first = catalog.summarize_with_llm(
        limit=1,
        llm_client_factory=lambda: bad_client,
        max_input_chars=120000,
        max_output_tokens=1200,
    )
    assert first.failure_scope in ("document", "permanent_document")

    (source_root / "second.txt").write_text(
        "2026年新增订单20亿元，交付产品1000台。", encoding="utf-8"
    )
    catalog.scan()
    catalog.normalize()
    good_client = _FakeLLM(
        json.dumps(
            {
                "overview": "文档记录新增订单与产品交付。",
                "key_facts": ["新增订单20亿元。", "交付产品1000台。"],
                "topics": ["订单", "交付"],
                "limitations": [],
            },
            ensure_ascii=False,
        )
    )

    second = catalog.summarize_with_llm(
        limit=1,
        llm_client_factory=lambda: good_client,
        max_input_chars=120000,
        max_output_tokens=1200,
    )

    assert second.completed == 1
    assert second.failed == 0
    assert len(good_client.prompts) == 1
    status = read_pipeline_status(catalog.config.database_path)
    assert status["llm_summary"]["completed"] == 1
    assert status["llm_summary"]["failed"] == 1
    assert status["llm_summary"]["pending"] == 0

    no_retry_client = _FakeLLM(good_client.content)
    deferred_document = catalog.summarize_with_llm(
        limit=1,
        llm_client_factory=lambda: no_retry_client,
        max_input_chars=120000,
        max_output_tokens=1200,
    )
    assert deferred_document.completed == 0
    assert deferred_document.failed == 0
    assert no_retry_client.prompts == []


def test_provider_failure_requests_global_retry_without_document_quarantine(tmp_path):
    catalog, _ = _catalog(tmp_path)
    client = _ProviderFailingLLM("")

    report = catalog.summarize_with_llm(
        limit=1,
        llm_client_factory=lambda: client,
        max_input_chars=120000,
        max_output_tokens=1200,
    )

    assert report.completed == 0
    assert report.failed == 1
    assert report.failure_scope == "global"
    assert report.retry_after is None
    assert report.retry_count is None
    assert "mimo/mimo-v2.5-pro" in report.error
    assert (
        catalog.store.fetchone("SELECT COUNT(*) AS count FROM llm_summary_failures")[
            "count"
        ]
        == 0
    )


def test_configured_llm_uses_mimo_when_primary_credentials_are_absent(monkeypatch):
    from company_wiki.source_catalog.llm_summarizer import build_configured_llm_client

    project = Path(__file__).resolve().parents[2]
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.setenv("MIMO_API_KEY", "test-only-placeholder")
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")

    client = build_configured_llm_client(project, project / "config.yaml")

    assert client.provider == "mimo"
    assert client.model == "mimo-v2.5-pro"
    assert client.available is True
    assert client.workload == "source"


def test_configured_llm_uses_project_dotenv_over_stale_inherited_keys(
    tmp_path, monkeypatch
):
    import config as config_module
    from company_wiki.source_catalog.llm_summarizer import build_configured_llm_client

    project = Path(__file__).resolve().parents[2]
    runtime_config = tmp_path / "config.yaml"
    runtime_config.write_text(
        """
llm:
  provider: minimax
  model: MiniMax-M3
  base_url: https://api.minimaxi.com/v1
  fallback:
    provider: mimo
    model: mimo-v2.5-pro
    base_url: https://token-plan-cn.xiaomimimo.com/v1
    enabled: true
    usage_scope: general
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text(
        "MINIMAX_API_KEY=file-primary-test-only\n"
        "MIMO_API_KEY=file-fallback-test-only\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config_module, "WIKI_ROOT", tmp_path)
    monkeypatch.delenv("PYTHON_DOTENV_DISABLED", raising=False)
    monkeypatch.setenv("MINIMAX_API_KEY", "stale-primary-test-only")
    monkeypatch.setenv("MIMO_API_KEY", "stale-fallback-test-only")

    client = build_configured_llm_client(project, runtime_config)

    assert client.api_key == "file-primary-test-only"
    assert client.workload == "source"
    assert client.fallback_client is not None
    assert client.fallback_client.api_key == "file-fallback-test-only"
    assert client.fallback_client.workload == "source"


def test_windows_startup_spec_is_logon_triggered_and_does_not_start_task(tmp_path):
    from company_wiki.source_catalog.startup import build_startup_task_args

    project = tmp_path / "project with spaces"
    launcher = project / "scripts" / "source_catalog_worker.ps1"
    args = build_startup_task_args(
        project_root=project,
        launcher_path=launcher,
        python_executable=Path("C:/Python/python.exe"),
        task_name="CompanyWiki Source Catalog",
    )

    assert args[0].lower().endswith("schtasks.exe")
    assert "/Create" in args
    assert "/SC" in args and "ONLOGON" in args
    assert "/DELAY" in args
    assert "/Run" not in args
    assert "wscript.exe" in args[args.index("/TR") + 1].lower()
    assert "//B //Nologo" in args[args.index("/TR") + 1]
    assert "source_catalog_worker_at_logon.vbs" in args[args.index("/TR") + 1]


@pytest.mark.skipif(os.name != "nt", reason="startup task installation is Windows-only")
def test_startup_install_falls_back_to_current_user_registry_without_running(tmp_path):
    from types import SimpleNamespace

    from company_wiki.source_catalog.startup import install_startup_task

    project = tmp_path / "project"
    scripts = project / "scripts"
    scripts.mkdir(parents=True)
    launcher = scripts / "source_catalog_worker.ps1"
    launcher.write_text("# worker", encoding="utf-8")
    (scripts / "source_catalog_worker_at_logon.ps1").write_text(
        "# delayed worker", encoding="utf-8"
    )
    (scripts / "source_catalog_worker_at_logon.vbs").write_text(
        "' hidden host", encoding="utf-8"
    )
    calls: list[list[str]] = []

    def runner(args, **kwargs):
        calls.append(args)
        if len(calls) == 1:
            return SimpleNamespace(returncode=1, stdout="", stderr="Access is denied")
        return SimpleNamespace(
            returncode=0, stdout="The operation completed", stderr=""
        )

    result = install_startup_task(
        project_root=project,
        launcher_path=launcher,
        python_executable=Path("C:/Python/python.exe"),
        runner=runner,
    )

    assert result["success"] is True
    assert result["started"] is False
    assert result["method"] == "current_user_run_registry"
    assert calls[0][1] == "/Create"
    assert calls[1][1] == "ADD"
    assert "/Run" not in calls[0]


def test_logon_delay_is_worker_interruptible_and_double_click_controls_exist():
    project = Path(__file__).resolve().parents[2]
    logon_launcher = (
        project / "scripts" / "source_catalog_worker_at_logon.ps1"
    ).read_text(encoding="utf-8")
    hidden_host = (
        project / "scripts" / "source_catalog_worker_at_logon.vbs"
    ).read_text(encoding="utf-8")
    worker_launcher = (project / "scripts" / "source_catalog_worker.ps1").read_text(
        encoding="utf-8"
    )
    control = (project / "scripts" / "source_catalog_control.ps1").read_text(
        encoding="utf-8"
    )
    double_click = project / "scripts" / "source_catalog_control.cmd"

    assert "Start-Sleep" not in logon_launcher
    assert "shell.Run(command, 0, False)" in hidden_host
    assert "-StartupDelaySeconds 120" in logon_launcher
    assert "--startup-delay-seconds" in worker_launcher
    assert all(
        action in control
        for action in ("worker-status", "worker-pause", "worker-resume", "worker-stop")
    )
    assert double_click.is_file()


def test_worker_launcher_records_output_and_exit_events_for_logon_startup():
    project = Path(__file__).resolve().parents[2]
    worker_launcher = (project / "scripts" / "source_catalog_worker.ps1").read_text(
        encoding="utf-8"
    )

    assert "worker_stdout-" in worker_launcher
    assert "worker_stderr-" in worker_launcher
    assert "worker_launcher.lock" in worker_launcher
    assert "worker_launcher_events.jsonl" in worker_launcher
    assert "function Write-LauncherEvent" in worker_launcher
    assert "Write-LauncherEvent -Status 'starting'" in worker_launcher
    assert "-Status 'child_started'" in worker_launcher
    assert "-Status 'restarting'" in worker_launcher
    assert "-Status 'launcher_exception'" in worker_launcher
    assert "Start-Process" in worker_launcher
    assert "RedirectStandardOutput" in worker_launcher
    assert "RedirectStandardError" in worker_launcher
    assert "*>>" not in worker_launcher
    assert "exit_code" in worker_launcher


def test_control_center_survives_startup_status_failures_and_marks_stale_runtime():
    project = Path(__file__).resolve().parents[2]
    control = (project / "scripts" / "source_catalog_control.ps1").read_text(
        encoding="utf-8"
    )

    assert "function Show-WorkerStatusSafely" in control
    assert "Unable to read worker status" in control
    assert "if ($Status.runtime_state -eq 'running' -and $Status.pid)" in control
    assert "if ($Status.stale_runtime -and $Status.pid)" in control
    assert "Window title could not be set" in control
    assert "control_center.log" in control
    assert "[Console]::InputEncoding = $Utf8NoBom" in control
    assert "[Console]::OutputEncoding = $Utf8NoBom" in control
    assert "$OutputEncoding = $Utf8NoBom" in control
    assert "Pipeline inventory" in control
    assert "Last scan" in control
    assert "Markdown" in control
    assert "LLM summary" in control
    assert "function Read-ControlChoiceWithLiveProgress" in control
    assert "[Console]::KeyAvailable" in control
    assert "Write-Progress" in control
    assert "worker_runtime.json" in control
    assert "$RuntimeStaleAfterSeconds = 60" in control
    assert "Stale heartbeat; last beat" in control
    assert "if ($Stage -eq 'idle') { $Stage = 'waiting' }" in control
    assert "waiting for next cycle" in control
    assert "Next wake" in control
    assert "next_wait_seconds" in control
    assert "next_wake_reason" in control
    assert "next_wake_at" in control
    assert "Start-Sleep -Milliseconds 500" in control


class TestExportThrottle:
    """CW-3.5 / Phase 10: per-doc export replaced by dirty-counter throttle."""

    def test_export_fires_first_cycle_then_throttled_until_threshold(self, tmp_path):
        from company_wiki.source_catalog.worker import SourceCatalogWorker, WorkerConfig

        catalog = _FakeCatalog()
        config = WorkerConfig(
            runtime_config=tmp_path / "config.yaml",
            scan_interval_seconds=3600,
            export_interval_seconds=3600,
            poll_interval_seconds=30,
            idle_seconds_required=600,
            normalize_batch_size=1,
            llm_summary_batch_size=1,
            llm_max_input_chars=1,
            llm_max_output_tokens=1,
            llm_retry_backoff_seconds=3600,
            allow_processing_on_battery=False,
            require_user_idle=False,
            dirty_export_threshold=3,
        )
        worker = SourceCatalogWorker(
            catalog,
            config,
            state_path=tmp_path / "state.json",
            idle_detector=_Idle(700),
            llm_client_factory=lambda: object(),
        )
        # Cycle 1: first export fires (last_export_at=None)
        worker.run_cycle(now=1000)
        c1 = [n for n, _ in catalog.calls]
        assert c1.count("export") == 1  # first export fires
        assert c1.count("normalize") == 1

        # Cycle 2: dirty=2 < threshold=3 → no export
        worker.run_cycle(now=1100)
        c2 = [n for n, _ in catalog.calls]
        assert c2.count("export") == 1  # still 1, throttled

        # Cycle 3: dirty=4 >= 3 → export fires
        worker.run_cycle(now=1200)
        c3 = [n for n, _ in catalog.calls]
        assert c3.count("export") == 2

        # Cycle 4: dirty reset, dirty=2 < 3 → no export
        worker.run_cycle(now=1300)
        c4 = [n for n, _ in catalog.calls]
        assert c4.count("export") == 2  # throttled again
