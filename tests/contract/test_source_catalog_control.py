"""Contracts for convenient and safe source-catalog worker controls."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


class _FakeProcesses:
    def __init__(self):
        self.alive: dict[int, dict[str, object]] = {}
        self.terminated: list[dict[str, object]] = []

    def identity(self, pid: int):
        value = self.alive.get(pid)
        return dict(value) if value else None

    def terminate(self, expected):
        current = self.identity(int(expected["pid"]))
        if current != expected:
            return False
        self.terminated.append(dict(expected))
        self.alive.pop(int(expected["pid"]), None)
        return True


def _controller(tmp_path: Path, processes: _FakeProcesses, **extra):
    from company_wiki.source_catalog.control import WorkerController

    terminate_process = extra.pop("terminate_process", processes.terminate)
    initialize_control = extra.pop("initialize_control", True)
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    config = project / "config" / "source_catalog.yaml"
    worker_config = project / "config" / "source_catalog_worker.yaml"
    config.parent.mkdir(exist_ok=True)
    config.write_text("schema_version: '1.0'\n", encoding="utf-8")
    worker_config.write_text("schema_version: '1.0'\n", encoding="utf-8")
    controller = WorkerController(
        catalog_dir=project / ".source_catalog",
        project_root=project,
        config_path=config,
        worker_config_path=worker_config,
        python_executable=Path("C:/Python/python.exe"),
        process_identity=processes.identity,
        terminate_process=terminate_process,
        sleeper=lambda _seconds: None,
        **extra,
    )
    # Tests that exercise a running legacy worker opt in explicitly.  The
    # production default for a missing control file is tested separately and
    # must remain fail-closed.
    if initialize_control and not controller.control_path.exists():
        controller._write_control(desired_state="enabled", stop_requested_for=None)
    return controller


def _write_legacy_runtime(
    controller, identity: dict[str, object], **details: object
) -> None:
    """Seed a pre-upgrade runtime receipt without using a retired launcher."""
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "token": "legacy-runtime-token",
        **identity,
        "project_root": str(controller.project_root),
        "started_at": 123450,
        "heartbeat_at": 123456,
        "updated_at": 123456,
        "worker_status": "normalizing",
        "current_path": None,
        "current_path_started_at": None,
        "current_path_elapsed_seconds": None,
        "progress_current": 0,
        "progress_total": 0,
        "progress_percent": None,
        "progress_detail": None,
        "parser_pid": None,
        "parser_elapsed_seconds": None,
        "parser_timeout_seconds": None,
        "parser_ownership": None,
        "cycle_productive": None,
        "next_wait_seconds": None,
        "next_wake_reason": None,
        "next_wake_at": None,
    }
    payload.update(details)
    payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
    controller.runtime_path.parent.mkdir(parents=True, exist_ok=True)
    controller.runtime_path.write_bytes(payload_bytes)
    controller.lock_path.write_bytes(payload_bytes)


@pytest.mark.parametrize(
    "payload",
    (
        None,
        "{",
        json.dumps({"schema_version": "1.0", "desired_state": "unknown"}),
    ),
)
def test_missing_or_invalid_control_defaults_to_paused(tmp_path, payload):
    processes = _FakeProcesses()
    controller = _controller(
        tmp_path,
        processes,
        initialize_control=False,
    )
    if payload is not None:
        controller.control_path.parent.mkdir(parents=True, exist_ok=True)
        controller.control_path.write_text(payload, encoding="utf-8")

    assert controller.interlock_state()["desired_state"] == "paused"
    assert not hasattr(controller, "open_session")


def test_interlock_state_distinguishes_valid_pause_from_missing_control(tmp_path):
    processes = _FakeProcesses()
    controller = _controller(
        tmp_path,
        processes,
        initialize_control=False,
    )

    missing = controller.interlock_state()
    controller.persist_pause_intent()
    persisted = controller.interlock_state()

    assert missing == {
        "automation_enabled": False,
        "control_valid": False,
        "desired_state": "paused",
        "runtime_state": "stopped",
    }
    assert persisted == {
        "automation_enabled": False,
        "control_valid": True,
        "desired_state": "paused",
        "runtime_state": "stopped",
    }


def test_interlock_state_treats_corrupt_runtime_as_unknown(tmp_path):
    processes = _FakeProcesses()
    controller = _controller(tmp_path, processes)
    controller.persist_pause_intent()
    controller.runtime_path.write_text("{", encoding="utf-8")

    assert controller.interlock_state() == {
        "automation_enabled": False,
        "control_valid": True,
        "desired_state": "paused",
        "runtime_state": "unknown",
    }


def test_automation_interlock_blocks_legacy_worker_session(tmp_path):
    processes = _FakeProcesses()
    controller = _controller(tmp_path, processes)
    controller.persist_automation_interlock(True)

    controller._write_control(desired_state="enabled", automation_enabled=True)
    assert controller.interlock_state()["automation_enabled"] is True
    assert not hasattr(controller, "open_session")


def test_atomic_json_write_retries_a_transient_windows_permission_error(
    tmp_path, monkeypatch
):
    import company_wiki.source_catalog.control as control

    destination = tmp_path / "worker_control.json"
    real_replace = control.os.replace
    attempts: list[int] = []
    sleeps: list[float] = []

    def transient_replace(source, target):
        attempts.append(1)
        if len(attempts) < 3:
            raise PermissionError(5, "transient sharing violation")
        return real_replace(source, target)

    monkeypatch.setattr(control.os, "replace", transient_replace)
    monkeypatch.setattr(control.time, "sleep", sleeps.append)

    control._atomic_write_json(destination, {"desired_state": "enabled"})

    assert len(attempts) == 3
    assert sleeps == [0.02, 0.04]
    assert __import__("json").loads(destination.read_text(encoding="utf-8")) == {
        "desired_state": "enabled"
    }


@pytest.mark.parametrize("error_type", [PermissionError, FileNotFoundError])
def test_json_read_retries_transient_windows_failures(
    tmp_path, monkeypatch, error_type
):
    import company_wiki.source_catalog.control as control

    destination = tmp_path / "worker_runtime.json"
    destination.write_text('{"pid": 123}\n', encoding="utf-8")
    real_read_text = Path.read_text
    attempts: list[int] = []
    sleeps: list[float] = []

    def transient_read_text(path, *args, **kwargs):
        if path == destination:
            attempts.append(1)
            if len(attempts) < 3:
                raise error_type("transient runtime read failure")
        return real_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", transient_read_text)
    monkeypatch.setattr(control.time, "sleep", sleeps.append)

    assert control._read_json(destination) == {"pid": 123}
    assert len(attempts) == 3
    assert sleeps == [0.01, 0.02]


def test_json_read_returns_none_after_bounded_malformed_json_retries(
    tmp_path, monkeypatch
):
    import company_wiki.source_catalog.control as control

    destination = tmp_path / "worker_runtime.json"
    destination.write_text("{", encoding="utf-8")
    sleeps: list[float] = []
    monkeypatch.setattr(control.time, "sleep", sleeps.append)

    assert control._read_json(destination) is None
    assert sleeps == [0.01, 0.02, 0.04]


def test_status_survives_transient_runtime_sharing_violation(tmp_path, monkeypatch):
    import company_wiki.source_catalog.control as control

    processes = _FakeProcesses()
    controller = _controller(tmp_path, processes)
    identity = {
        "pid": 321,
        "executable": "C:/Python/python.exe",
        "creation_time": 456,
    }
    processes.alive[321] = identity
    controller._write_control(desired_state="enabled", stop_requested_for=None)
    controller.runtime_path.parent.mkdir(parents=True, exist_ok=True)
    controller.runtime_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                **identity,
                "token": "runtime-token",
                "heartbeat_at": 1000,
            }
        ),
        encoding="utf-8",
    )
    real_read_text = Path.read_text
    attempts: list[int] = []

    def transient_runtime_read(path, *args, **kwargs):
        if path == controller.runtime_path:
            attempts.append(1)
            if len(attempts) < 3:
                raise PermissionError("transient sharing violation")
        return real_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", transient_runtime_read)
    monkeypatch.setattr(control.time, "sleep", lambda _seconds: None)
    controller.clock = lambda: 1001

    status = controller.status()

    assert len(attempts) == 3
    assert status["runtime_state"] == "running"
    assert status["pid"] == 321


def test_status_compares_loaded_and_current_code_fingerprints(tmp_path, monkeypatch):
    import company_wiki.source_catalog.control as control

    processes = _FakeProcesses()
    controller = _controller(tmp_path, processes)
    identity = {
        "pid": 654,
        "executable": "C:/Python/python.exe",
        "creation_time": 789,
    }
    processes.alive[654] = identity
    controller.runtime_path.parent.mkdir(parents=True, exist_ok=True)
    controller.runtime_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                **identity,
                "token": "runtime-token",
                "heartbeat_at": 1000,
                "loaded_code_fingerprint": "a" * 64,
                "loaded_code_fingerprint_error": None,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        control,
        "source_bundle_fingerprint",
        lambda _root: {
            "fingerprint": "b" * 64,
            "error": None,
            "files": [{"path": "worker.py", "sha256": "c" * 64}],
        },
        raising=False,
    )
    controller.clock = lambda: 1001

    status = controller.status()

    assert status["loaded_code_fingerprint"] == "a" * 64
    assert status["current_code_fingerprint"] == "b" * 64
    assert status["code_match"] is False
    assert status["code_fingerprint_error"] is None






def test_stale_runtime_does_not_report_historical_waiting_as_current(tmp_path):
    processes = _FakeProcesses()
    identity = {
        "pid": os.getpid(),
        "executable": "C:/Python/python.exe",
        "creation_time": 123456,
    }
    processes.alive[os.getpid()] = identity
    processes.alive.pop(os.getpid())
    controller = _controller(tmp_path, processes)
    _write_legacy_runtime(
        controller,
        identity,
        worker_status="waiting",
        cycle_productive=False,
        next_wait_seconds=30,
        next_wake_reason="no_output",
        next_wake_at=123486,
    )

    status = controller.status()

    assert status["runtime_state"] == "stopped"
    assert status["stale_runtime"] is True
    assert status["worker_status"] == "stopped"
    assert status["last_worker_status"] == "waiting"
    assert status["next_wait_seconds"] is None

def test_live_legacy_status_exposes_recorded_progress(tmp_path):
    processes = _FakeProcesses()
    identity = {
        "pid": os.getpid(),
        "executable": "C:/Python/python.exe",
        "creation_time": 123456,
    }
    processes.alive[os.getpid()] = identity
    controller = _controller(tmp_path, processes)
    _write_legacy_runtime(
        controller,
        identity,
        worker_status="normalizing",
        current_path="C:/incoming/report.pdf",
        current_path_started_at=123450,
        progress_current=1,
        progress_total=4,
        progress_percent=25.0,
        progress_detail="extracting Markdown",
        parser_pid=4321,
        parser_elapsed_seconds=12.5,
        parser_timeout_seconds=3600,
        parser_ownership="windows_job",
    )
    active = controller.status()
    assert active["current_path"] == "C:/incoming/report.pdf"
    assert active["progress_current"] == 1
    assert active["progress_total"] == 4
    assert active["progress_percent"] == 25.0
    assert active["progress_detail"] == "extracting Markdown"
    assert active["parser_pid"] == 4321
    assert active["parser_elapsed_seconds"] == 12.5
    assert active["parser_timeout_seconds"] == 3600
    assert active["parser_ownership"] == "windows_job"
    assert active["updated_at"] == active["heartbeat_at"]


def test_stop_forces_only_the_exact_recorded_process_identity(tmp_path):
    processes = _FakeProcesses()
    identity = {
        "pid": os.getpid(),
        "executable": "C:/Python/python.exe",
        "creation_time": 123456,
    }
    processes.alive[os.getpid()] = identity
    controller = _controller(tmp_path, processes)
    _write_legacy_runtime(controller, identity)

    result = controller.stop(graceful_timeout_seconds=0, force=True)

    assert result["runtime_state"] == "stopped"
    assert result["forced"] is True
    assert processes.terminated == [identity]
    assert controller.status()["desired_state"] == "enabled"


def test_stop_retries_a_transient_identity_checked_termination_failure(tmp_path):
    processes = _FakeProcesses()
    identity = {
        "pid": os.getpid(),
        "executable": "C:/Python/python.exe",
        "creation_time": 123456,
    }
    processes.alive[os.getpid()] = identity
    attempts = []

    def flaky_terminate(expected):
        attempts.append(dict(expected))
        if len(attempts) == 1:
            return False
        return processes.terminate(expected)

    controller = _controller(
        tmp_path,
        processes,
        terminate_process=flaky_terminate,
    )
    _write_legacy_runtime(controller, identity)

    result = controller.stop(graceful_timeout_seconds=0, force=True)

    assert result["runtime_state"] == "stopped"
    assert result["forced"] is True
    assert attempts == [identity, identity]
    assert processes.terminated == [identity]


def test_stop_refuses_to_terminate_a_reused_pid(tmp_path):
    processes = _FakeProcesses()
    original = {
        "pid": os.getpid(),
        "executable": "C:/Python/python.exe",
        "creation_time": 123456,
    }
    processes.alive[os.getpid()] = original
    controller = _controller(tmp_path, processes)
    _write_legacy_runtime(controller, original)
    processes.alive[os.getpid()] = {**original, "creation_time": 999999}

    result = controller.stop(graceful_timeout_seconds=0, force=True)

    assert result["runtime_state"] == "stopped"
    assert result["forced"] is False
    assert processes.terminated == []


def test_cli_worker_status_is_lightweight_and_reports_startup_state(
    tmp_path, monkeypatch, capsys
):
    import company_wiki.source_catalog.cli as cli

    project = tmp_path / "project"
    config_path = project / "config" / "source_catalog.yaml"
    worker_config_path = project / "config" / "source_catalog_worker.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        """
schema_version: '1.0'
catalog_dir: '${PROJECT_ROOT}/.source_catalog'
roots:
  - root_id: unused
    kind: directory
    path: '${PROJECT_ROOT}/unused'
""".strip(),
        encoding="utf-8",
    )
    worker_config_path.write_text("schema_version: '1.0'\n", encoding="utf-8")
    monkeypatch.setattr(
        cli,
        "SourceCatalog",
        lambda _config: (_ for _ in ()).throw(AssertionError("catalog opened")),
    )
    monkeypatch.setattr(
        cli,
        "startup_task_status",
        lambda **_kwargs: {"installed": True, "method": "current_user_run_registry"},
    )

    retry_after = __import__("time").time() + 3600
    state_path = project / ".source_catalog" / "worker_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "last_error": "CatalogOperationLockedError: stale historical error",
                "llm_retry_after": retry_after,
                "last_llm_summary_report": {
                    "failed": 1,
                    "failure_scope": "global",
                    "error": "LLMProviderError: HTTP 429 quota exhausted",
                },
            }
        ),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "--config",
                str(config_path),
                "worker-status",
                "--worker-config",
                str(worker_config_path),
            ]
        )
        == 0
    )
    status = __import__("json").loads(capsys.readouterr().out)
    assert status["desired_state"] == "paused"
    assert status["runtime_state"] == "stopped"
    assert status["startup"]["installed"] is True
    assert status["pipeline"]["available"] is False
    summary = status["pipeline"]["llm_summary"]
    assert summary["global_deferred"] is True
    assert summary["global_retry_after"] == retry_after
    assert summary["global_error"] == "LLMProviderError: HTTP 429 quota exhausted"


def test_read_pipeline_status_reports_scan_index_and_processing_queues(tmp_path):
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
    from company_wiki.source_catalog.store import read_pipeline_status

    project = tmp_path / "project"
    source = tmp_path / "source"
    source.mkdir()
    (source / "new-document.txt").write_text(
        "A source-only document for pipeline status.", encoding="utf-8"
    )
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("source", source, "directory"),),
        )
    )

    scan_progress: list[dict] = []
    catalog.scan(progress=lambda **details: scan_progress.append(details))
    before = read_pipeline_status(catalog.config.database_path)

    assert before["available"] is True
    assert before["last_scan"]["files_seen"] == 1
    assert before["last_scan"]["new_documents"] == 1
    assert before["last_scan"]["new_sources"] == 1
    assert before["index"]["physical_locations"] == 1
    assert before["index"]["documents"] == 1
    assert before["index"]["duplicate_copies"] == 0
    assert before["markdown"]["pending"] == 1
    assert before["markdown"]["blocked"] == 0
    assert before["markdown"]["completed"] == 0
    assert scan_progress[-1]["current_path"] == str(source / "new-document.txt")
    assert scan_progress[-1]["current"] == 1
    assert scan_progress[-1]["total"] == 1
    assert any(item["detail"] == "enumerating root source" for item in scan_progress)

    normalize_progress: list[dict] = []
    catalog.normalize(progress=lambda **details: normalize_progress.append(details))
    after = read_pipeline_status(catalog.config.database_path)

    assert after["markdown"]["pending"] == 0
    assert after["markdown"]["completed"] == 1
    assert after["llm_summary"]["eligible"] == 1
    assert after["llm_summary"]["pending"] == 1
    assert after["llm_summary"]["completed"] == 0
    assert normalize_progress[0] == {
        "current_path": str(source / "new-document.txt"),
        "current": 1,
        "total": 1,
        "detail": "extracting Markdown",
    }
    parser_progress = next(
        item for item in normalize_progress if item["detail"] == "parser_alive"
    )
    assert parser_progress["current_path"] == str(source / "new-document.txt")
    assert parser_progress["current"] == 1
    assert parser_progress["total"] == 1
    assert parser_progress["parser_pid"] > 0
    assert parser_progress["parser_elapsed_seconds"] >= 0
    assert parser_progress["parser_timeout_seconds"] > 0
    assert parser_progress["parser_ownership"] in {
        "windows_job",
        "parent_monitor",
        "process_group",
        "posix_process_group",
    }


def test_pipeline_status_separates_retryable_permanent_and_legacy_failures(tmp_path):
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
    from company_wiki.source_catalog.store import read_pipeline_status

    project = tmp_path / "project"
    source = tmp_path / "source"
    source.mkdir()
    for index in range(3):
        (source / f"doc-{index}.txt").write_text(
            f"source document {index}", encoding="utf-8"
        )
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("source", source, "directory"),),
        )
    )
    catalog.scan()
    catalog.normalize()
    documents = catalog.store.fetchall(
        "SELECT document_id FROM documents ORDER BY document_id"
    )
    now = __import__("time").time()
    rows = (
        (
            documents[0]["document_id"],
            "document",
            "LLMSummaryError: temporary source read error",
            now + 120,
            now + 10,
        ),
        (
            documents[1]["document_id"],
            "document",
            "LLMSummaryError: LLM response contains a forbidden investment conclusion",
            now + 86400 * 365,
            now + 20,
        ),
        (
            documents[2]["document_id"],
            "permanent_document",
            "LLMSummaryError: LLM response is not valid JSON",
            now + 86400 * 365,
            now + 30,
        ),
    )
    with catalog.store.transaction() as connection:
        connection.executemany(
            """INSERT INTO llm_summary_failures(
            document_id,generator_name,generator_version,failure_scope,error,
            attempt_count,retry_after,first_failed_at,last_failed_at
            ) VALUES(?,?,?,?,?,1,?,?,?)""",
            [
                (
                    document_id,
                    "source_catalog_llm_summary",
                    "test",
                    scope,
                    error,
                    retry_after,
                    failed_at,
                    failed_at,
                )
                for document_id, scope, error, retry_after, failed_at in rows
            ],
        )

    status = read_pipeline_status(catalog.config.database_path)["llm_summary"]

    assert status["failed"] == 3
    assert status["retryable_failed"] == 1
    assert status["permanent"] == 2
    assert status["legacy_scope_mismatch"] == 1
    assert status["next_document_retry_after"] == rows[0][3]
    assert status["last_failed_document_id"] == rows[0][0]
    assert status["last_permanent_document_id"] == rows[2][0]


def test_read_pipeline_status_is_read_only_and_handles_a_missing_database(tmp_path):
    from company_wiki.source_catalog.store import read_pipeline_status

    database = tmp_path / "missing" / "catalog.sqlite3"

    status = read_pipeline_status(database)

    assert status["available"] is False
    assert status["index"]["documents"] == 0
    assert not database.exists()


def test_read_pipeline_status_uses_long_busy_timeout_read_connection(
    tmp_path, monkeypatch
):
    """read_pipeline_status opens a read-only connection that must tolerate
    worker write bursts: busy_timeout matches the main store read connection
    (30s), not a shorter legacy 5s value (ADR-008 portfolio E2E follow-up)."""
    import sqlite3

    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
    from company_wiki.source_catalog import store
    from company_wiki.source_catalog.store import read_pipeline_status

    project = tmp_path / "project"
    source = tmp_path / "source"
    source.mkdir()
    (source / "doc.txt").write_text("test document", encoding="utf-8")
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("source", source, "directory"),),
        )
    )
    catalog.scan()

    statements: list[str] = []
    real_connect = sqlite3.connect

    def traced_connect(database, *args, **kwargs):
        connection = real_connect(database, *args, **kwargs)
        connection.set_trace_callback(statements.append)
        return connection

    monkeypatch.setattr(store.sqlite3, "connect", traced_connect)
    status = read_pipeline_status(catalog.config.database_path)

    assert status["available"] is True
    assert any("busy_timeout=30000" in s for s in statements)


def test_pipeline_status_includes_explanations_and_health(tmp_path):
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
    from company_wiki.source_catalog.store import read_pipeline_status

    project = tmp_path / "project"
    source = tmp_path / "source"
    source.mkdir()
    (source / "doc.txt").write_text("test document", encoding="utf-8")
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("source", source, "directory"),),
        )
    )
    catalog.scan()

    status = read_pipeline_status(catalog.config.database_path)

    assert "explanations" in status
    assert "markdown_pending_reason" in status["explanations"]
    assert "health" in status
    assert "artifacts" in status["health"]
    assert "artifact_rows" in status["health"]["artifacts"]
    assert status["health"]["artifacts"]["artifact_index_empty"] is True
    assert status["health"]["artifacts"]["reconciliation_needed"] is False


def test_worker_status_stale_runtime_has_converting_zero_and_last_details(tmp_path):
    processes = _FakeProcesses()
    identity = {
        "pid": os.getpid(),
        "executable": "C:/Python/python.exe",
        "creation_time": 123456,
    }
    processes.alive[os.getpid()] = identity
    controller = _controller(tmp_path, processes)
    processes.alive.pop(os.getpid())
    _write_legacy_runtime(
        controller,
        identity,
        worker_status="normalizing",
        current_path="C:/incoming/large.pdf",
        progress_current=2,
        progress_total=5,
        progress_percent=40.0,
        progress_detail="extracting Markdown",
    )

    status = controller.status()

    assert status["runtime_state"] == "stopped"
    assert status["stale_runtime"] is True
    assert status["worker_status"] == "stopped"
    assert status["last_worker_status"] == "normalizing"
    assert status["last_current_path"] == "C:/incoming/large.pdf"
    assert status["last_progress_detail"] == "extracting Markdown"
    assert status["progress_current"] == 0
    assert status["progress_total"] == 0
    assert status["current_path"] is None


def test_worker_status_json_includes_status_generated_at(tmp_path):
    processes = _FakeProcesses()
    controller = _controller(tmp_path, processes)

    status = controller.status()

    assert "status_generated_at" in status
    assert isinstance(status["status_generated_at"], (int, float))


def test_empty_pipeline_status_has_explanations_and_health():
    from company_wiki.source_catalog.store import read_pipeline_status

    missing = Path("/nonexistent/catalog.sqlite3")
    status = read_pipeline_status(missing)

    assert "explanations" in status
    assert status["explanations"]["markdown_pending_reason"] == "database unavailable"
    assert "health" in status
    assert status["health"]["artifacts"]["artifact_index_empty"] is True
    assert status["health"]["locks"]["operation_lock_identity_verification"] == "absent"


def test_process_inventory_categorizes_production_vs_test_workers(tmp_path):
    processes = _FakeProcesses()
    fake_inventory = {
        "production_workers": [{"pid": 100}],
        "foreign_workers": [{"pid": 200}],
        "pytest_temp_workers": [{"pid": 300}],
    }
    controller = _controller(
        tmp_path,
        processes,
        process_inventory_provider=lambda: fake_inventory,
    )

    status = controller.status()

    assert "process_inventory" in status
    inv = status["process_inventory"]
    assert inv["production_workers"] == [{"pid": 100}]
    assert inv["foreign_workers"] == [{"pid": 200}]
    assert inv["pytest_temp_workers"] == [{"pid": 300}]


def test_process_inventory_returns_empty_lists_when_no_workers_found(tmp_path):
    processes = _FakeProcesses()
    controller = _controller(
        tmp_path,
        processes,
        process_inventory_provider=lambda: {
            "production_workers": [],
            "foreign_workers": [],
            "pytest_temp_workers": [],
        },
    )

    status = controller.status()

    inv = status["process_inventory"]
    assert inv["production_workers"] == []
    assert inv["foreign_workers"] == []
    assert inv["pytest_temp_workers"] == []


def test_status_retries_a_transient_process_identity_read_failure(tmp_path):
    processes = _FakeProcesses()
    controller = _controller(tmp_path, processes)
    current = {
        "pid": os.getpid(),
        "executable": str(Path(os.sys.executable).resolve()),
        "creation_time": "current-process",
    }
    processes.alive[os.getpid()] = current
    _write_legacy_runtime(controller, current)
    real_identity = controller.process_identity
    calls = 0

    def transient_identity(pid):
        nonlocal calls
        calls += 1
        if calls == 1:
            return None
        return real_identity(pid)

    controller.process_identity = transient_identity
    assert controller.status()["runtime_state"] == "running"
    assert calls == 2


def test_live_status_computes_current_path_elapsed_from_snapshot_time(tmp_path):
    processes = _FakeProcesses()
    controller = _controller(tmp_path, processes)
    current = {
        "pid": os.getpid(),
        "executable": str(Path(os.sys.executable).resolve()),
        "creation_time": "current-process",
    }
    processes.alive[os.getpid()] = current
    controller.clock = lambda: 1_000.0
    _write_legacy_runtime(
        controller,
        current,
        worker_status="normalizing",
        current_path="C:/source/report.pdf",
        current_path_started_at=1_000.0,
    )
    controller.clock = lambda: 1_190.0

    status = controller.status()

    assert status["runtime_state"] == "running"
    assert status["current_path_elapsed_seconds"] == 190.0
    assert status["long_running_document_warning"] is True
