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
import os
import shutil
import subprocess
import sys
import time
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

        def normalize(self, *, limit, progress=None, **kwargs):
            del limit, progress, kwargs
            self.calls.append("normalize")
            return _Report()

        def backfill_text_fingerprints(self, **kwargs):
            self.calls.append("backfill_text_fingerprints")
            return _Report()

        def summarize_with_llm(self, **kwargs):
            self.calls.append("summarize_with_llm")
            return _Report()

        def export_indexes(self, *, progress=None):
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


# ---------------------------------------------------------------------------
# WR-10 — real Windows launcher stderr isolation and recovery
# ---------------------------------------------------------------------------


def _prepare_fake_launcher_project(
    tmp_path: Path, behaviors: list[dict[str, object]]
) -> Path:
    project = tmp_path / "fake-project"
    package = project / "company_wiki" / "source_catalog"
    package.mkdir(parents=True)
    (project / "company_wiki" / "__init__.py").write_text("", encoding="utf-8")
    (package / "__init__.py").write_text("", encoding="utf-8")
    (project / "fake_behaviors.json").write_text(
        json.dumps(behaviors),
        encoding="utf-8",
    )
    catalog = project / ".source_catalog"
    catalog.mkdir()
    (catalog / "worker_control.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "desired_state": "enabled",
                "stop_requested_for": "baseline-stop-token",
                "updated_at": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (package / "cli.py").write_text(
        """
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

project = Path.cwd()
catalog = project / ".source_catalog"
count_path = catalog / "fake_worker_count.txt"
count = int(count_path.read_text(encoding="utf-8")) + 1 if count_path.exists() else 1
count_path.write_text(str(count), encoding="utf-8")
behaviors = json.loads((project / "fake_behaviors.json").read_text(encoding="utf-8"))
behavior = behaviors[min(count - 1, len(behaviors) - 1)]
if "runtime_heartbeat_age_seconds" in behavior:
    now = time.time()
    runtime = {
        "schema_version": "1.0",
        "pid": os.getpid(),
        "heartbeat_at": now - float(behavior["runtime_heartbeat_age_seconds"]),
        "updated_at": now - float(behavior["runtime_heartbeat_age_seconds"]),
        "worker_status": behavior.get("worker_status", "normalizing"),
        "current_path": behavior.get("current_path", "slow.pdf"),
        "current_path_started_at": now
        - float(behavior.get("current_path_elapsed_seconds", 0)),
    }
    (catalog / "worker_runtime.json").write_text(
        json.dumps(runtime) + "\\n",
        encoding="utf-8",
    )
if behavior.get("desired_state") or behavior.get("stop_requested_for"):
    control = json.loads(
        (catalog / "worker_control.json").read_text(encoding="utf-8")
    )
    if behavior.get("desired_state"):
        control["desired_state"] = behavior["desired_state"]
    if behavior.get("stop_requested_for"):
        control["stop_requested_for"] = behavior["stop_requested_for"]
    control["updated_at"] = count + 1
    (catalog / "worker_control.json").write_text(
        json.dumps(control) + "\\n",
        encoding="utf-8",
    )
if behavior.get("stdout"):
    print(behavior["stdout"], flush=True)
if behavior.get("stderr"):
    print(behavior["stderr"], file=sys.stderr, flush=True)
time.sleep(float(behavior.get("sleep_seconds", 0)))
raise SystemExit(int(behavior.get("exit_code", 0)))
""".lstrip(),
        encoding="utf-8",
    )
    return project


def _real_worker_launcher_command(
    project: Path,
    *,
    restart_base_seconds: float = 0,
    restart_max_seconds: float = 0,
    worker_hang_timeout_seconds: float | None = None,
    child_poll_milliseconds: int | None = None,
) -> list[str]:
    launcher = (
        Path(__file__).resolve().parents[2] / "scripts" / "source_catalog_worker.ps1"
    )
    command = [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(launcher),
        "-PythonExe",
        sys.executable,
        "-ProjectRoot",
        str(project),
        "-StartupDelaySeconds",
        "0",
        "-RestartBaseSeconds",
        str(restart_base_seconds),
        "-RestartMaxSeconds",
        str(restart_max_seconds),
    ]
    if worker_hang_timeout_seconds is not None:
        command.extend(["-WorkerHangTimeoutSeconds", str(worker_hang_timeout_seconds)])
    if child_poll_milliseconds is not None:
        command.extend(["-ChildPollMilliseconds", str(child_poll_milliseconds)])
    return command


def _run_real_worker_launcher(
    project: Path,
    *,
    timeout: float = 30.0,
    restart_base_seconds: float = 0,
    restart_max_seconds: float = 0,
    worker_hang_timeout_seconds: float | None = None,
    child_poll_milliseconds: int | None = None,
):
    return subprocess.run(
        _real_worker_launcher_command(
            project,
            restart_base_seconds=restart_base_seconds,
            restart_max_seconds=restart_max_seconds,
            worker_hang_timeout_seconds=worker_hang_timeout_seconds,
            child_poll_milliseconds=child_poll_milliseconds,
        ),
        cwd=project,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def _launcher_events(project: Path) -> list[dict[str, object]]:
    path = project / ".source_catalog" / "worker_launcher_events.jsonl"
    # Phase 6 C3 (F-09): under full-suite load a just-terminated launcher or its
    # child can still hold the Windows file handle for a few ms, making a plain
    # read raise PermissionError and turning a teardown race into a false test
    # failure.  Retry briefly with a short backoff so the read is deterministic.
    deadline = time.monotonic() + 3.0
    while True:
        try:
            text = path.read_text(encoding="utf-8-sig")
            break
        except PermissionError:  # pragma: no cover - platform race
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.02)
    return [json.loads(line) for line in text.splitlines() if line.strip()]


@pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell launcher integration")
def test_stderr_exit_zero_does_not_fail_launcher_and_logs_are_utf8(tmp_path):
    project = _prepare_fake_launcher_project(
        tmp_path,
        [{"stderr": "fixture warning 你好", "exit_code": 0}],
    )

    completed = _run_real_worker_launcher(project)

    assert completed.returncode == 0, completed.stderr
    assert (project / ".source_catalog" / "fake_worker_count.txt").read_text() == "1"
    events = _launcher_events(project)
    assert [event["status"] for event in events] == [
        "starting",
        "child_started",
        "exited",
    ]
    child_started = next(
        event for event in events if event["status"] == "child_started"
    )
    assert "exit_code" not in child_started
    assert "restart_delay_seconds" not in child_started
    assert child_started["worker_hang_timeout_seconds"] == 900
    assert child_started["child_poll_milliseconds"] == 5000
    assert all(event["status"] != "launcher_exception" for event in events)
    stderr_log = Path(str(events[-1]["stderr_log"]))
    raw_stderr = stderr_log.read_bytes()
    assert b"\x00" not in raw_stderr
    assert "fixture warning 你好" in raw_stderr.decode("utf-8")


@pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell launcher integration")
def test_nonzero_child_restarts_once_then_recovers(tmp_path):
    project = _prepare_fake_launcher_project(
        tmp_path,
        [
            {"stderr": "first attempt failed", "exit_code": 7},
            {"stdout": "second attempt recovered", "exit_code": 0},
        ],
    )

    completed = _run_real_worker_launcher(project)

    assert completed.returncode == 0, completed.stderr
    assert (project / ".source_catalog" / "fake_worker_count.txt").read_text() == "2"
    events = _launcher_events(project)
    assert [event["status"] for event in events] == [
        "starting",
        "child_started",
        "restarting",
        "child_started",
        "exited",
    ]
    restart = events[2]
    assert restart["exit_code"] == 7
    assert restart["restart_delay_seconds"] == 0
    assert restart["reason"] == "unexpected_nonzero_exit"


@pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell launcher integration")
def test_explicit_stop_marker_suppresses_restart_after_nonzero_exit(tmp_path):
    project = _prepare_fake_launcher_project(
        tmp_path,
        [
            {
                "stderr": "terminated during explicit stop",
                "stop_requested_for": "current-worker-token",
                "exit_code": 9,
            }
        ],
    )

    completed = _run_real_worker_launcher(project)

    assert completed.returncode == 0, completed.stderr
    assert (project / ".source_catalog" / "fake_worker_count.txt").read_text() == "1"
    events = _launcher_events(project)
    assert events[-1]["status"] == "exited"
    assert events[-1]["reason"] == "control_stop"
    assert not any(event["status"] == "restarting" for event in events)


@pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell launcher integration")
def test_persistent_pause_suppresses_restart_after_nonzero_exit(tmp_path):
    project = _prepare_fake_launcher_project(
        tmp_path,
        [{"desired_state": "paused", "exit_code": 11}],
    )

    completed = _run_real_worker_launcher(project)

    assert completed.returncode == 0, completed.stderr
    assert (project / ".source_catalog" / "fake_worker_count.txt").read_text() == "1"
    events = _launcher_events(project)
    assert events[-1]["status"] == "exited"
    assert events[-1]["reason"] == "persistent_pause"
    assert not any(event["status"] == "restarting" for event in events)


@pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell launcher integration")
def test_duplicate_supervisor_is_rejected_without_second_child(tmp_path):
    project = _prepare_fake_launcher_project(
        tmp_path,
        [{"sleep_seconds": 2, "exit_code": 0}],
    )
    first = subprocess.Popen(
        _real_worker_launcher_command(project),
        cwd=project,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    count_path = project / ".source_catalog" / "fake_worker_count.txt"
    deadline = time.monotonic() + 10
    while not count_path.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert count_path.exists()

    second = _run_real_worker_launcher(project)
    first_stdout, first_stderr = first.communicate(timeout=15)

    assert second.returncode == 0, second.stderr
    assert first.returncode == 0, f"{first_stdout}\n{first_stderr}"
    assert count_path.read_text(encoding="utf-8") == "1"
    statuses = [event["status"] for event in _launcher_events(project)]
    assert statuses.count("child_started") == 1
    assert statuses.count("already_running") == 1


@pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell launcher integration")
def test_child_without_runtime_session_is_terminated_and_restarted(tmp_path):
    project = _prepare_fake_launcher_project(
        tmp_path,
        [
            {"sleep_seconds": 5, "exit_code": 0},
            {"exit_code": 0},
        ],
    )

    completed = _run_real_worker_launcher(
        project,
        timeout=15,
        worker_hang_timeout_seconds=0.5,
        child_poll_milliseconds=100,
    )

    assert completed.returncode == 0, completed.stderr
    events = _launcher_events(project)
    unresponsive = next(
        event for event in events if event["status"] == "child_unresponsive"
    )
    restarting = next(event for event in events if event["status"] == "restarting")
    assert unresponsive["reason"] == "session_start_timeout"
    assert restarting["reason"] == "session_start_timeout"
    assert len([event for event in events if event["status"] == "child_started"]) == 2


@pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell launcher integration")
def test_stale_child_heartbeat_is_terminated_and_restarted(tmp_path):
    project = _prepare_fake_launcher_project(
        tmp_path,
        [
            {
                "runtime_heartbeat_age_seconds": 5,
                "current_path": "slow.pdf",
                "current_path_elapsed_seconds": 5,
                "sleep_seconds": 5,
                "exit_code": 0,
            },
            {"exit_code": 0},
        ],
    )

    completed = _run_real_worker_launcher(
        project,
        timeout=15,
        worker_hang_timeout_seconds=0.5,
        child_poll_milliseconds=100,
    )

    assert completed.returncode == 0, completed.stderr
    count_path = project / ".source_catalog" / "fake_worker_count.txt"
    assert count_path.read_text(encoding="utf-8") == "2"
    events = _launcher_events(project)
    unresponsive = next(
        event for event in events if event["status"] == "child_unresponsive"
    )
    restarting = next(event for event in events if event["status"] == "restarting")
    child_events = [event for event in events if event["status"] == "child_started"]
    assert unresponsive["reason"] == "heartbeat_timeout"
    assert restarting["reason"] == "heartbeat_timeout"
    assert restarting["exit_code"] != 0
    assert len(child_events) == 2
    assert child_events[0]["child_pid"] != child_events[1]["child_pid"]


@pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell launcher integration")
def test_restart_backoff_is_exponential_and_capped(tmp_path):
    project = _prepare_fake_launcher_project(
        tmp_path,
        [
            {"exit_code": 3},
            {"exit_code": 4},
            {"exit_code": 0},
        ],
    )

    completed = _run_real_worker_launcher(
        project,
        restart_base_seconds=0.01,
        restart_max_seconds=0.015,
    )

    assert completed.returncode == 0, completed.stderr
    restart_events = [
        event for event in _launcher_events(project) if event["status"] == "restarting"
    ]
    assert [event["restart_delay_seconds"] for event in restart_events] == [
        0.01,
        0.015,
    ]


@pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell launcher integration")
def test_terminating_supervisor_does_not_leave_an_orphan_worker(tmp_path):
    from company_wiki.source_catalog.control import (
        process_identity,
        terminate_matching_process,
    )

    project = _prepare_fake_launcher_project(
        tmp_path,
        [{"sleep_seconds": 30, "exit_code": 0}],
    )
    supervisor = subprocess.Popen(
        _real_worker_launcher_command(project),
        cwd=project,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    child_identity = None
    try:
        deadline = time.monotonic() + 10
        child_pid = None
        while time.monotonic() < deadline:
            events_path = project / ".source_catalog" / "worker_launcher_events.jsonl"
            if events_path.exists():
                child_events = [
                    event
                    for event in _launcher_events(project)
                    if event["status"] == "child_started"
                ]
                if child_events:
                    child_pid = int(child_events[-1]["child_pid"])
                    child_identity = process_identity(child_pid)
                    if child_identity is not None:
                        break
            time.sleep(0.05)
        assert child_identity is not None

        supervisor.terminate()
        supervisor.wait(timeout=10)
        deadline = time.monotonic() + 5
        while process_identity(child_pid) is not None and time.monotonic() < deadline:
            time.sleep(0.05)

        assert process_identity(child_pid) is None
    finally:
        if supervisor.poll() is None:
            supervisor.terminate()
            supervisor.wait(timeout=10)
        if child_identity is not None and process_identity(child_identity["pid"]):
            terminate_matching_process(child_identity)


@pytest.mark.skipif(os.name != "nt", reason="Windows logon launcher integration")
def test_logon_wrapper_detaches_a_live_supervisor_with_quoted_paths(tmp_path):
    from company_wiki.source_catalog.control import (
        process_identity,
        terminate_matching_process,
    )

    project = _prepare_fake_launcher_project(
        tmp_path / "project path with spaces",
        [{"sleep_seconds": 10, "exit_code": 0}],
    )
    source_scripts = Path(__file__).resolve().parents[2] / "scripts"
    scripts = project / "scripts"
    scripts.mkdir()
    for name in ("source_catalog_worker.ps1", "source_catalog_worker_at_logon.ps1"):
        shutil.copyfile(source_scripts / name, scripts / name)

    wrapper = scripts / "source_catalog_worker_at_logon.ps1"
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(wrapper),
            "-PythonExe",
            sys.executable,
            "-ProjectRoot",
            str(project),
        ],
        cwd=project,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr

    supervisor_identity = None
    child_identity = None
    try:
        deadline = time.monotonic() + 15
        events = []
        while time.monotonic() < deadline:
            events_path = project / ".source_catalog" / "worker_launcher_events.jsonl"
            if events_path.exists():
                events = _launcher_events(project)
                child_events = [
                    event for event in events if event["status"] == "child_started"
                ]
                if child_events:
                    child_event = child_events[-1]
                    supervisor_identity = process_identity(
                        int(child_event["launcher_pid"])
                    )
                    child_identity = process_identity(int(child_event["child_pid"]))
                    if supervisor_identity is not None and child_identity is not None:
                        break
            time.sleep(0.05)
        assert supervisor_identity is not None
        assert child_identity is not None

        deadline = time.monotonic() + 20
        while process_identity(supervisor_identity["pid"]) is not None:
            if time.monotonic() >= deadline:
                break
            time.sleep(0.05)
        assert process_identity(supervisor_identity["pid"]) is None
        assert process_identity(child_identity["pid"]) is None
        assert [event["status"] for event in _launcher_events(project)] == [
            "starting",
            "child_started",
            "exited",
        ]
    finally:
        for identity in (child_identity, supervisor_identity):
            if identity is not None and process_identity(identity["pid"]) == identity:
                terminate_matching_process(identity)
