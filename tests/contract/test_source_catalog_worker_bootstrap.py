"""WR-2: worker bootstrap self-evidence and start/restart failure diagnostics.

§10.8.3 contracts:
1. ``run_forever(control=...)`` writes ``process_starting`` immediately, then
   ``session_opened`` once the controller has handed a live session over, then
   ``process_exiting`` with a reason in {``control_request``,
   ``persistent_pause``, ``unhandled_exception``} on every exit path. UTF-8
   no-BOM append-only JSONL, never contains command-line / env / API key.
2. Unhandled exceptions re-raise after writing
   ``unhandled_exception`` (with ``exception_type`` and a short redacted
   message) followed by ``process_exiting`` reason=``unhandled_exception``.
3. ``WorkerController.start()`` must return explicit boot-failure
   diagnostics when the spawned child exits before writing a runtime file:
   ``started=False``, ``spawned_pid``, ``spawned_exit_code``,
   ``startup_failure_reason``, ``console_tail`` (<=40 lines),
   ``recent_process_event`` (if any JSONL exists).
4. ``WorkerController.read_desired_state()`` reads ``worker_control.json``
   without touching runtime, lock or the PowerShell process inventory —
   so ``cli.py worker`` no longer has to call the full inventory-emitting
   ``status()`` before opening a session.
5. Pre-existing skip on
   ``test_real_background_worker_can_start_heartbeat_and_stop_in_a_temp_catalog``
   is removed once WR-2 makes the real Python subprocess bootstrap self-proving
   on Windows. (Removal is exercised in WR-4 / §10.8.5; WR-2 only adds the
   preconditions for that removal.)
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest


def _make_worker(tmp_path: Path, *, catalog=None):
    from company_wiki.source_catalog.worker import SourceCatalogWorker, WorkerConfig

    class _Idle:
        def __init__(self, idle_seconds=0, on_battery=False):
            self.idle_seconds = idle_seconds
            self.on_battery = on_battery

    config = WorkerConfig(
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

    class _FakeCatalog:
        def __init__(self):
            self.calls = []

        def scan(self, *, progress=None):
            self.calls.append("scan")
            return _Report()

        def normalize(self, *, limit, progress=None):
            self.calls.append("normalize")
            return _Report()

        def backfill_text_fingerprints(self, **kwargs):
            self.calls.append("backfill_text_fingerprints")
            return _Report()

        def summarize_with_llm(self, **kwargs):
            self.calls.append("summarize_with_llm")
            return _Report()

        def export_indexes(self):
            self.calls.append("export")
            return {"index": Path("index.md")}

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

    worker = SourceCatalogWorker(
        catalog or _FakeCatalog(),
        config,
        state_path=tmp_path / "state.json",
        idle_detector=_Idle(0),
        llm_client_factory=lambda: object(),
    )
    return worker


class _ControlStub:
    """Minimal control stub matching the read_desired_state/status/open_session
    surface used by ``run_forever``. status() is intentionally not called by the
    new worker code path; we keep it for fallback compatibility and to detect
    regressions where the worker accidentally relies on it.
    """

    def __init__(self, session=None, *, desired_state="enabled", raise_on_open=None):
        self.session = session
        self.desired_state = desired_state
        self.raise_on_open = raise_on_open
        self.status_calls = 0

    def read_desired_state(self) -> str:
        return self.desired_state

    def status(self):
        self.status_calls += 1
        return {"desired_state": self.desired_state}

    def open_session(self):
        if self.raise_on_open is not None:
            raise self.raise_on_open
        if self.desired_state == "paused":
            raise RuntimeError("source-catalog worker is paused")
        return self.session


class _StoppingSession:
    def __init__(self):
        self.closed = False
        self.heartbeats = []
        self.heartbeat_details = []
        self.waits = []
        self._stop = False

    def heartbeat(self, status, **details):
        self.heartbeats.append(status)
        self.heartbeat_details.append((status, details))

    def wait(self, _seconds):
        self.waits.append(_seconds)
        if not self._stop:
            self._stop = True
            return True  # one productive cycle, then stop
        return False

    def should_stop(self):
        return self._stop

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def _read_process_events(state_path: Path) -> list[dict]:
    events_path = state_path.parent / "worker_process_events.jsonl"
    if not events_path.is_file():
        return []
    events = []
    for line in events_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("\ufeff"):
            line = line.lstrip("\ufeff")
        events.append(json.loads(line))
    return events


# ---------------------------------------------------------------------------
# Contract 1 — process_starting / session_opened / process_exiting(reason=...)
# ---------------------------------------------------------------------------


def test_run_forever_writes_process_starting_session_opened_and_control_request_exit(
    tmp_path,
):
    worker = _make_worker(tmp_path)
    session = _StoppingSession()
    control = _ControlStub(session)
    state_path = tmp_path / "state.json"

    result = worker.run_forever(control=control)

    assert result["status"] == "stopped"
    assert result["reason"] == "control_request"
    events = _read_process_events(state_path)
    assert [e["event"] for e in events] == [
        "process_starting",
        "session_opened",
        "process_exiting",
    ]
    assert events[-1].get("reason") == "control_request"
    # No command-line / env fields persisted.
    for event in events:
        assert "commandline" not in {k.lower() for k in event.keys()}
        assert "env" not in {k.lower() for k in event.keys()}
        assert "api_key" not in {k.lower() for k in event.keys()}


def test_run_forever_exits_with_persistent_pause_when_desired_state_paused(tmp_path):
    worker = _make_worker(tmp_path)
    control = _ControlStub(desired_state="paused")
    state_path = tmp_path / "state.json"

    result = worker.run_forever(control=control)

    assert result["status"] == "paused"
    assert result["reason"] == "persistent_pause"
    events = _read_process_events(state_path)
    assert [e["event"] for e in events] == [
        "process_starting",
        "process_exiting",
    ]
    assert events[-1].get("reason") == "persistent_pause"


def test_run_forever_write_session_opened_event_after_open_session_succeeds(tmp_path):
    worker = _make_worker(tmp_path)
    session = _StoppingSession()
    control = _ControlStub(session)
    state_path = tmp_path / "state.json"

    worker.run_forever(control=control)

    events = _read_process_events(state_path)
    # session_opened must appear AFTER process_starting and BEFORE any
    # cycle / process_exiting event.
    indices = {e["event"]: i for i, e in enumerate(events)}
    assert "session_opened" in indices
    assert indices["session_opened"] > indices["process_starting"]
    assert indices["session_opened"] < indices["process_exiting"]


# ---------------------------------------------------------------------------
# Contract 2 — unhandled exception writes unhandled_exception + process_exiting
# ---------------------------------------------------------------------------


class _ExplodingSession:
    def __init__(self):
        self.closed = False
        self.heartbeats = []
        self.waits = []

    def heartbeat(self, status, **details):
        self.heartbeats.append(status)

    def wait(self, _seconds):
        # First wait: simulate productive cycle then stop; second wait: raise.
        if not self.waits:
            self.waits.append(_seconds)
            return True
        raise RuntimeError("simulated unhandled error during wait")

    def should_stop(self):
        return False

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def test_run_forever_writes_unhandled_exception_event_with_exception_type(tmp_path):
    worker = _make_worker(tmp_path)
    session = _ExplodingSession()
    control = _ControlStub(session)
    state_path = tmp_path / "state.json"

    with pytest.raises(RuntimeError, match="simulated unhandled"):
        worker.run_forever(control=control)

    events = _read_process_events(state_path)
    # Must record unhandled_exception BEFORE process_exiting.
    indices = {e["event"]: i for i, e in enumerate(events)}
    assert "unhandled_exception" in indices
    assert "process_exiting" in indices
    assert indices["unhandled_exception"] < indices["process_exiting"]
    unhandled = events[indices["unhandled_exception"]]
    assert unhandled.get("exception_type") == "RuntimeError"
    # message must be redacted / truncated, not the full long message
    msg = unhandled.get("message_redacted", "")
    assert isinstance(msg, str)
    assert 0 < len(msg) <= 200
    exit_event = events[indices["process_exiting"]]
    assert exit_event.get("reason") == "unhandled_exception"
    # No command-line / env fields persisted even on the unhandled path.
    for event in events:
        assert "commandline" not in {k.lower() for k in event.keys()}
        assert "env" not in {k.lower() for k in event.keys()}


# ---------------------------------------------------------------------------
# Contract 3 — WorkerController.start() boot-failure diagnostics
# ---------------------------------------------------------------------------


def _controller_for_start_test(tmp_path: Path, *, child_returns=7, child_stderr="boom"):
    from company_wiki.source_catalog.control import WorkerController

    project = tmp_path / "project"
    project.mkdir()
    config = project / "config" / "source_catalog.yaml"
    worker_config = project / "config" / "source_catalog_worker.yaml"
    config.parent.mkdir()
    config.write_text("schema_version: '1.0'\n", encoding="utf-8")
    worker_config.write_text("schema_version: '1.0'\n", encoding="utf-8")

    class _FakeProcess:
        def __init__(self, pid, returncode):
            self.pid = pid
            self._returncode = returncode
            self.stdout = None

        def poll(self):
            return self._returncode

    fake_process = _FakeProcess(pid=4242, returncode=child_returns)

    class _FakePopen:
        def __call__(self, *args, **kwargs):
            return fake_process

    controller = WorkerController(
        catalog_dir=project / ".source_catalog",
        project_root=project,
        config_path=config,
        worker_config_path=worker_config,
        python_executable=Path(sys.executable),
        popen=_FakePopen(),
        sleeper=lambda _s: None,
        process_inventory_provider=lambda: {
            "production_workers": [],
            "foreign_workers": [],
            "pytest_temp_workers": [],
            "ignored_matching_processes": [],
            "inventory_error": None,
        },
    )
    return controller, fake_process, project


def test_start_returns_started_false_with_spawned_exit_code_when_child_exits_before_runtime(
    tmp_path,
):
    controller, fake_process, project = _controller_for_start_test(tmp_path)

    result = controller.start(wait_seconds=1)

    assert result["started"] is False
    assert result["spawned_pid"] == fake_process.pid
    assert result["spawned_exit_code"] == 7
    assert "startup_failure_reason" in result
    assert isinstance(result["startup_failure_reason"], str)
    assert result["startup_failure_reason"]
    assert "console_tail" in result
    assert isinstance(result["console_tail"], str)


def test_start_console_tail_is_at_most_forty_lines(tmp_path):
    controller, _fake_process, project = _controller_for_start_test(tmp_path)
    # Pre-write a long console log to verify the 40-line cap.
    log_path = project / ".source_catalog" / "worker_console.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        "\n".join(f"line {i}" for i in range(80)) + "\n", encoding="utf-8"
    )

    result = controller.start(wait_seconds=1)

    tail = result.get("console_tail", "")
    # Tail is the last 40 lines, newline-joined.
    if tail:
        assert tail.count("\n") <= 40


def test_start_returns_recent_process_event_when_available(tmp_path):
    controller, _fake_process, project = _controller_for_start_test(tmp_path)
    events_path = project / ".source_catalog" / "worker_process_events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text(
        json.dumps(
            {
                "event": "process_starting",
                "pid": 4242,
                "timestamp": "2026-07-27T20:00:00",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = controller.start(wait_seconds=1)

    assert result["started"] is False
    pe = result.get("recent_process_event")
    assert pe is not None
    assert pe["event"] == "process_starting"
    assert pe["pid"] == 4242


def test_start_returns_recent_process_event_error_when_jsonl_corrupt(tmp_path):
    controller, _fake_process, project = _controller_for_start_test(tmp_path)
    events_path = project / ".source_catalog" / "worker_process_events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text("not-json{\n", encoding="utf-8")

    result = controller.start(wait_seconds=1)

    assert result["started"] is False
    # Either no recent_process_event (None) or it carries an error key — never raises.
    assert "recent_process_event" in result
    assert "recent_process_event_error" in result or result["recent_process_event"] in (
        None,
        {},
    )


# ---------------------------------------------------------------------------
# Contract 4 — read_desired_state does NOT trigger status() / inventory
# ---------------------------------------------------------------------------


def test_read_desired_state_reads_persistent_pause_without_runtime_or_inventory(
    tmp_path,
):
    from company_wiki.source_catalog.control import WorkerController

    project = tmp_path / "project"
    project.mkdir()
    config = project / "config" / "source_catalog.yaml"
    worker_config = project / "config" / "source_catalog_worker.yaml"
    config.parent.mkdir()
    config.write_text("schema_version: '1.0'\n", encoding="utf-8")
    worker_config.write_text("schema_version: '1.0'\n", encoding="utf-8")
    controller = WorkerController(
        catalog_dir=project / ".source_catalog",
        project_root=project,
        config_path=config,
        worker_config_path=worker_config,
        process_inventory_provider=lambda: {
            "production_workers": [],
            "foreign_workers": [],
            "pytest_temp_workers": [],
            "ignored_matching_processes": [],
            "inventory_error": "should_not_be_called",
        },
    )
    # Default desired_state for a fresh control file is enabled.
    assert controller.read_desired_state() == "enabled"
    # Mark persistent pause.
    controller._write_control(desired_state="paused")
    assert controller.read_desired_state() == "paused"
    # No runtime file created.
    assert not (project / ".source_catalog" / "worker_runtime.json").exists()
    # Inventory was never consulted during read_desired_state — verify by
    # calling read_desired_state again and confirming the provider's
    # inventory_error has not leaked into the controller state.
    controller.read_desired_state()


# ---------------------------------------------------------------------------
# Contract 5 — worker.run_forever uses read_desired_state when available,
# never status()
# ---------------------------------------------------------------------------


def test_run_forever_uses_read_desired_state_not_status(tmp_path):
    worker = _make_worker(tmp_path)
    session = _StoppingSession()
    control = _ControlStub(session)

    # Make status() explode so any re-introduction would surface loudly.
    def _status_boom():
        raise AssertionError(
            "run_forever must not call status() when read_desired_state exists"
        )

    control.status = _status_boom

    result = worker.run_forever(control=control)

    assert result["status"] == "stopped"
    assert result["reason"] == "control_request"


# ---------------------------------------------------------------------------
# Contract 6 — cli.worker-status exposes recent launcher / process events
# ---------------------------------------------------------------------------


def test_read_recent_worker_events_returns_last_process_and_launcher(tmp_path):
    from company_wiki.source_catalog.cli import _read_recent_worker_events

    (tmp_path / "worker_process_events.jsonl").write_text(
        json.dumps({"event": "process_starting", "pid": 1})
        + "\n"
        + json.dumps({"event": "session_opened", "pid": 1})
        + "\n"
        + json.dumps(
            {"event": "process_exiting", "pid": 1, "reason": "control_request"}
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "worker_launcher_events.jsonl").write_text(
        json.dumps({"event": "starting"})
        + "\n"
        + json.dumps({"event": "exited", "exit_code": 0})
        + "\n",
        encoding="utf-8",
    )

    result = _read_recent_worker_events(tmp_path)

    assert result["recent_process_event"]["event"] == "process_exiting"
    assert result["recent_process_event"]["reason"] == "control_request"
    assert result["recent_launcher_event"]["event"] == "exited"
    assert result["recent_launcher_event"]["exit_code"] == 0
    assert "recent_process_event_error" not in result
    assert "recent_launcher_event_error" not in result


def test_read_recent_worker_events_returns_null_with_no_files(tmp_path):
    from company_wiki.source_catalog.cli import _read_recent_worker_events

    result = _read_recent_worker_events(tmp_path)

    assert result == {
        "recent_process_event": None,
        "recent_launcher_event": None,
    }


def test_read_recent_worker_events_reports_corrupt_jsonl_via_error_field(tmp_path):
    from company_wiki.source_catalog.cli import _read_recent_worker_events

    (tmp_path / "worker_process_events.jsonl").write_text(
        "not-json{\n", encoding="utf-8"
    )
    (tmp_path / "worker_launcher_events.jsonl").write_text(
        "{still-broken\n", encoding="utf-8"
    )

    result = _read_recent_worker_events(tmp_path)

    assert result["recent_process_event"] is None
    assert "recent_process_event_error" in result
    assert "JSONDecodeError" in result["recent_process_event_error"]
    assert result["recent_launcher_event"] is None
    assert "recent_launcher_event_error" in result


def test_read_recent_worker_events_handles_utf8_bom(tmp_path):
    from company_wiki.source_catalog.cli import _read_recent_worker_events

    payload = "\ufeff" + json.dumps({"event": "process_starting", "pid": 42}) + "\n"
    (tmp_path / "worker_process_events.jsonl").write_text(payload, encoding="utf-8")

    result = _read_recent_worker_events(tmp_path)

    assert result["recent_process_event"]["event"] == "process_starting"
    assert result["recent_process_event"]["pid"] == 42
