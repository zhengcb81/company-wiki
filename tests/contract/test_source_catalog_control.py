"""Contracts for convenient and safe source-catalog worker controls."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

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
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    config = project / "config" / "source_catalog.yaml"
    worker_config = project / "config" / "source_catalog_worker.yaml"
    config.parent.mkdir(exist_ok=True)
    config.write_text("schema_version: '1.0'\n", encoding="utf-8")
    worker_config.write_text("schema_version: '1.0'\n", encoding="utf-8")
    return WorkerController(
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


@pytest.mark.skipif(os.name != "nt", reason="Windows supervisor startup contract")
def test_start_launches_the_supervisor_instead_of_a_bare_worker(tmp_path):
    processes = _FakeProcesses()
    calls = []

    class _ExitedProcess:
        pid = 4242

        @staticmethod
        def poll():
            return 7

    def fake_popen(command, **kwargs):
        calls.append((command, kwargs))
        return _ExitedProcess()

    launcher = (
        Path(__file__).resolve().parents[2] / "scripts" / "source_catalog_worker.ps1"
    )
    controller = _controller(
        tmp_path,
        processes,
        popen=fake_popen,
        launcher_path=launcher,
    )

    result = controller.start(wait_seconds=0)

    assert result["started"] is False
    command = calls[0][0]
    assert Path(command[0]).name.lower() == "powershell.exe"
    assert "-File" in command
    launcher = Path(command[command.index("-File") + 1])
    assert launcher.name == "source_catalog_worker.ps1"
    assert "company_wiki.source_catalog.cli" not in command
    assert calls[0][1]["creationflags"] & 0x00000008 == 0


def test_pause_is_persistent_and_prevents_a_worker_session(tmp_path):
    processes = _FakeProcesses()
    controller = _controller(tmp_path, processes)

    result = controller.pause(graceful_timeout_seconds=0, force=False)

    assert result["desired_state"] == "paused"
    reloaded = _controller(tmp_path, processes)
    assert reloaded.status()["desired_state"] == "paused"
    with pytest.raises(RuntimeError, match="paused"):
        reloaded.open_session()


def test_worker_session_is_single_instance_and_records_heartbeat(tmp_path):
    processes = _FakeProcesses()
    identity = {
        "pid": os.getpid(),
        "executable": "C:/Python/python.exe",
        "creation_time": 123456,
    }
    processes.alive[os.getpid()] = identity
    first = _controller(tmp_path, processes).open_session()
    first.heartbeat(
        "waiting",
        detail="waiting for next cycle",
        cycle_productive=True,
        next_wait_seconds=2,
        next_wake_reason="productive_cycle",
        next_wake_at=123458,
    )

    status = _controller(tmp_path, processes).status()
    assert status["runtime_state"] == "running"
    assert status["pid"] == os.getpid()
    assert status["worker_status"] == "waiting"
    assert status["cycle_productive"] is True
    assert status["next_wait_seconds"] == 2
    assert status["next_wake_reason"] == "productive_cycle"
    assert status["next_wake_at"] == 123458
    with pytest.raises(RuntimeError, match="already running"):
        _controller(tmp_path, processes).open_session()

    first.close()
    assert _controller(tmp_path, processes).status()["runtime_state"] == "stopped"


def test_stale_runtime_does_not_report_historical_waiting_as_current(tmp_path):
    processes = _FakeProcesses()
    identity = {
        "pid": os.getpid(),
        "executable": "C:/Python/python.exe",
        "creation_time": 123456,
    }
    processes.alive[os.getpid()] = identity
    session = _controller(tmp_path, processes).open_session()
    session.heartbeat(
        "waiting",
        cycle_productive=False,
        next_wait_seconds=30,
        next_wake_reason="no_output",
        next_wake_at=123486,
    )
    processes.alive.pop(os.getpid())

    status = _controller(tmp_path, processes).status()

    assert status["runtime_state"] == "stopped"
    assert status["stale_runtime"] is True
    assert status["worker_status"] == "stopped"
    assert status["last_worker_status"] == "waiting"
    assert status["next_wait_seconds"] is None

    session.close()


def test_runtime_progress_is_exposed_then_cleared_by_waiting_heartbeat(tmp_path):
    processes = _FakeProcesses()
    processes.alive[os.getpid()] = {
        "pid": os.getpid(),
        "executable": "C:/Python/python.exe",
        "creation_time": 123456,
    }
    controller = _controller(tmp_path, processes)
    session = controller.open_session()

    session.heartbeat(
        "normalizing",
        current_path="C:/incoming/report.pdf",
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

    session.heartbeat("waiting")
    waiting = controller.status()
    assert waiting["current_path"] is None
    assert waiting["progress_current"] == 0
    assert waiting["progress_total"] == 0
    assert waiting["progress_percent"] is None
    assert waiting["progress_detail"] is None
    assert waiting["parser_pid"] is None
    session.close()


def test_stop_polling_does_not_write_a_heartbeat_every_half_second(tmp_path):
    processes = _FakeProcesses()
    processes.alive[os.getpid()] = {
        "pid": os.getpid(),
        "executable": "C:/Python/python.exe",
        "creation_time": 123456,
    }
    controller = _controller(tmp_path, processes)
    session = controller.open_session()
    before = controller.status()["heartbeat_at"]

    assert session.wait(2) is True

    assert controller.status()["heartbeat_at"] == before
    session.close()


def test_long_poll_wait_reports_waiting_instead_of_input_idle(tmp_path):
    processes = _FakeProcesses()
    processes.alive[os.getpid()] = {
        "pid": os.getpid(),
        "executable": "C:/Python/python.exe",
        "creation_time": 123456,
    }
    controller = _controller(tmp_path, processes)
    session = controller.open_session()

    assert session.wait(11) is True

    assert controller.status()["worker_status"] == "waiting"
    session.close()


def test_long_poll_heartbeat_preserves_the_current_next_wake_plan(tmp_path):
    processes = _FakeProcesses()
    processes.alive[os.getpid()] = {
        "pid": os.getpid(),
        "executable": "C:/Python/python.exe",
        "creation_time": 123456,
    }
    controller = _controller(tmp_path, processes)
    session = controller.open_session()
    session.heartbeat(
        "waiting",
        cycle_productive=False,
        next_wait_seconds=30,
        next_wake_reason="no_output",
        next_wake_at=123486,
    )

    assert session.wait(11) is True

    status = controller.status()
    assert status["cycle_productive"] is False
    assert status["next_wait_seconds"] == 30
    assert status["next_wake_reason"] == "no_output"
    assert status["next_wake_at"] == 123486
    session.close()


def test_stop_forces_only_the_exact_recorded_process_identity(tmp_path):
    processes = _FakeProcesses()
    identity = {
        "pid": os.getpid(),
        "executable": "C:/Python/python.exe",
        "creation_time": 123456,
    }
    processes.alive[os.getpid()] = identity
    controller = _controller(tmp_path, processes)
    session = controller.open_session()

    result = controller.stop(graceful_timeout_seconds=0, force=True)

    assert result["runtime_state"] == "stopped"
    assert result["forced"] is True
    assert processes.terminated == [identity]
    assert controller.status()["desired_state"] == "enabled"
    session.close()


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
    session = controller.open_session()

    result = controller.stop(graceful_timeout_seconds=0, force=True)

    assert result["runtime_state"] == "stopped"
    assert result["forced"] is True
    assert attempts == [identity, identity]
    assert processes.terminated == [identity]
    session.close()


def test_stop_refuses_to_terminate_a_reused_pid(tmp_path):
    processes = _FakeProcesses()
    original = {
        "pid": os.getpid(),
        "executable": "C:/Python/python.exe",
        "creation_time": 123456,
    }
    processes.alive[os.getpid()] = original
    controller = _controller(tmp_path, processes)
    session = controller.open_session()
    processes.alive[os.getpid()] = {**original, "creation_time": 999999}

    result = controller.stop(graceful_timeout_seconds=0, force=True)

    assert result["runtime_state"] == "stopped"
    assert result["forced"] is False
    assert processes.terminated == []
    session.close()


def test_cli_pause_and_status_are_lightweight_and_report_startup_state(
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

    assert (
        cli.main(
            [
                "--config",
                str(config_path),
                "worker-pause",
                "--worker-config",
                str(worker_config_path),
                "--graceful-timeout-seconds",
                "0",
            ]
        )
        == 0
    )
    paused = __import__("json").loads(capsys.readouterr().out)
    assert paused["desired_state"] == "paused"

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
    session = controller.open_session()
    session.heartbeat(
        "normalizing",
        current_path="C:/incoming/large.pdf",
        progress_current=2,
        progress_total=5,
        progress_percent=40.0,
        progress_detail="extracting Markdown",
    )
    processes.alive.pop(os.getpid())

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

    session.close()


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
    session = controller.open_session()
    real_identity = controller.process_identity
    calls = 0

    def transient_identity(pid):
        nonlocal calls
        calls += 1
        if calls == 1:
            return None
        return real_identity(pid)

    controller.process_identity = transient_identity
    try:
        assert controller.status()["runtime_state"] == "running"
        assert calls == 2
    finally:
        session.close()


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
    session = controller.open_session()
    try:
        session.heartbeat("normalizing", current_path="C:/source/report.pdf")
        controller.clock = lambda: 1_190.0

        status = controller.status()

        assert status["runtime_state"] == "running"
        assert status["current_path_elapsed_seconds"] == 190.0
        assert status["long_running_document_warning"] is True
    finally:
        session.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows background-process integration")
def test_real_background_worker_can_start_heartbeat_and_stop_in_a_temp_catalog(
    tmp_path,
):
    from company_wiki.source_catalog.control import (
        WorkerController,
        process_identity,
        terminate_matching_process,
    )

    workspace = Path(__file__).resolve().parents[2]
    project = tmp_path / "project"
    source = tmp_path / "source"
    source.mkdir()
    (source / "tiny.txt").write_text("source-only test document", encoding="utf-8")
    config_path = project / "config" / "source_catalog.yaml"
    worker_config_path = project / "config" / "source_catalog_worker.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        f"""
schema_version: '1.0'
catalog_dir: '{project.as_posix()}/.source_catalog'
roots:
  - root_id: temp
    kind: directory
    path: '{source.as_posix()}'
""".strip(),
        encoding="utf-8",
    )
    worker_config_path.write_text(
        f"""
schema_version: '1.2'
runtime_config: '{workspace.as_posix()}/config.yaml'
scan_interval_minutes: 60
export_interval_minutes: 60
poll_interval_seconds: 30
active_poll_interval_seconds: 2
idle_seconds_required: 600
require_user_idle: false
normalize_batch_size: 1
llm_summary_batch_size: 1
llm_max_input_chars: 1000
llm_max_output_tokens: 100
llm_retry_backoff_minutes: 60
allow_processing_on_battery: false
fingerprint_backfill_batch_size: 3
fingerprint_retry_limit: 3
fingerprint_retry_backoff_seconds: 900
""".strip(),
        encoding="utf-8",
    )
    (project / "config.yaml").write_text("llm: {}\n", encoding="utf-8")
    controller = WorkerController(
        catalog_dir=project / ".source_catalog",
        project_root=workspace,
        config_path=config_path,
        worker_config_path=worker_config_path,
        python_executable=Path(os.sys.executable),
    )

    owned_identities = []
    residual_identities = []
    started = None
    try:
        environment = os.environ.copy()
        environment["PYTHONUTF8"] = "1"
        environment["PYTHONIOENCODING"] = "utf-8"
        completed = subprocess.run(
            [
                os.sys.executable,
                "-m",
                "company_wiki.source_catalog.cli",
                "--config",
                str(config_path),
                "worker-start",
                "--worker-config",
                str(worker_config_path),
                "--wait-seconds",
                "10",
                "--startup-delay-seconds",
                "120",
            ],
            cwd=workspace,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        started = json.loads(completed.stdout)
        assert started["started"] is True
        started_identity = process_identity(started["spawned_pid"])
        assert started_identity is not None
        owned_identities.append(started_identity)
        assert controller.status()["runtime_state"] == "running"
        paused = controller.pause(graceful_timeout_seconds=5, force=True)
        assert paused["desired_state"] == "paused"
        assert paused["runtime_state"] == "stopped"
        blocked = controller.start(wait_seconds=0)
        assert blocked["started"] is False
        assert "paused" in blocked["reason"]
        resumed = controller.resume(wait_seconds=10, startup_delay_seconds=120)
        assert resumed["started"] is True
        resumed_identity = process_identity(resumed["spawned_pid"])
        assert resumed_identity is not None
        owned_identities.append(resumed_identity)
        assert controller.status()["runtime_state"] == "running"
    finally:
        stopped = controller.stop(graceful_timeout_seconds=5, force=True)
        for identity in owned_identities:
            current = process_identity(identity["pid"])
            if current == identity:
                residual_identities.append(identity)
                terminate_matching_process(identity)
    assert stopped["runtime_state"] == "stopped"
    assert residual_identities == []
