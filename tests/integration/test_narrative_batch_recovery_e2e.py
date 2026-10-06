"""Hard-killed formal coordinators leave recoverable work and charged uncertainty."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from threading import Event, Thread
import time
from types import SimpleNamespace

import pytest

from company_wiki._file_mutex import os_file_mutex
from company_wiki.automation.models import RuntimeState
from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from company_wiki.automation.policy import PolicyConfig
from company_wiki.automation.registry import create_default_registry
from company_wiki.automation.scheduler import AutomationScheduler
from company_wiki.automation.store import AutomationStore
from company_wiki.source_catalog.narrative_artifact_store import (
    LocalNarrativeObjectStore, NarrativeArtifactStore,
)

from support.narrative_batch_fixtures import (
    KEY, KEY_ENV, T0, assert_originals_and_foreign_jobs_untouched,
    foreign_ready_jobs, isolated_batch_directory, prepare_source_catalog,
)


def _wait_until(predicate, *, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    pytest.fail("Observed process/ledger condition did not become true before timeout")


def _child_pids(parent_pid):
    """Read actual OS ancestry, without replacing the production runtime factory."""
    if os.name != "nt":
        return [pid for pid, parent, _state, _started in _posix_process_table() if parent == parent_pid]
    import ctypes
    from ctypes import wintypes

    class ProcessEntry(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = (wintypes.DWORD, wintypes.DWORD)
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = (wintypes.HANDLE, ctypes.POINTER(ProcessEntry))
    kernel.Process32NextW.argtypes = (wintypes.HANDLE, ctypes.POINTER(ProcessEntry))
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    assert snapshot and snapshot != ctypes.c_void_p(-1).value
    entry = ProcessEntry()
    entry.dwSize = ctypes.sizeof(entry)
    found = []
    try:
        present = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        while present:
            if entry.th32ParentProcessID == parent_pid:
                found.append(int(entry.th32ProcessID))
            present = kernel.Process32NextW(snapshot, ctypes.byref(entry))
        return found
    finally:
        kernel.CloseHandle(snapshot)


def _posix_process_table():
    result = subprocess.run(
        ["ps", "-eo", "pid=,ppid=,stat=,lstart="],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        pytest.fail("Cannot inspect private test process ancestry")
    processes = []
    for line in result.stdout.splitlines():
        fields = line.strip().split(maxsplit=3)
        if len(fields) == 4:
            processes.append((int(fields[0]), int(fields[1]), fields[2], fields[3]))
    return processes


class _ObservedProcess:
    """Keep Windows handles or POSIX creation identity so PID reuse is harmless."""

    def __init__(self, pid):
        self.pid = pid
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            self.kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
            self.kernel.OpenProcess.restype = wintypes.HANDLE
            self.kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
            self.kernel.TerminateProcess.argtypes = (wintypes.HANDLE, wintypes.UINT)
            self.kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
            self.handle = self.kernel.OpenProcess(0x00100000 | 0x1000 | 0x0001, False, pid)
            assert self.handle, "Cannot observe a private test child process"
        else:
            self.started = self._posix_state()[1]

    def _posix_state(self):
        for pid, _parent, state, started in _posix_process_table():
            if pid == self.pid:
                return state, started
        return None, None

    def exited(self):
        if os.name == "nt":
            return self.kernel.WaitForSingleObject(self.handle, 0) == 0
        state, started = self._posix_state()
        return state in {None, "Z", "X"} or started != self.started

    def close(self):
        try:
            if not self.exited():
                if os.name == "nt":
                    self.kernel.TerminateProcess(self.handle, 91)
                else:
                    os.kill(self.pid, signal.SIGKILL)
                _wait_until(self.exited, timeout=5)
        finally:
            if os.name == "nt":
                self.kernel.CloseHandle(self.handle)


@pytest.fixture
def interrupted_model_server(monkeypatch, hermetic_runtime):
    """Withhold the first response until the caller has actually been killed."""
    state = SimpleNamespace(requests=[], errors=[], first_received=Event(), release_first=Event())

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            try:
                assert self.path == "/v1/chat/completions"
                assert self.headers["Authorization"] == f"Bearer {KEY}"
                body = self.rfile.read(int(self.headers["Content-Length"]))
                assert KEY.encode() not in body
                request = json.loads(body)
                assert [message["role"] for message in request["messages"]] == ["system", "user"]
                data = json.loads(request["messages"][1]["content"])
                from support.narrative_model_request_fixture import response_draft

                assert "No translation" in request["messages"][0]["content"]
                draft = response_draft(data)
                assert draft is not None and draft["draft"]["language"] == "en"
                state.requests.append(data)
                if len(state.requests) == 1:
                    state.first_received.set()
                    assert state.release_first.wait(timeout=30)
                reply = json.dumps({
                    "model": "stub-model", "choices": [{
                        "message": {"content": json.dumps(draft, ensure_ascii=False)},
                        "finish_reason": "stop",
                    }], "usage": {"prompt_tokens": 73, "completion_tokens": 19},
                }, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
            except Exception as exc:
                state.errors.append(type(exc).__name__)
                reply = b'{"error":"invalid local test request"}'
                self.send_response(500)
            try:
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(reply)))
                self.end_headers()
                self.wfile.write(reply)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                # This is the intentionally killed caller, not a fabricated
                # successful model response or permission to refund its cost.
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = False
    thread = Thread(target=lambda: server.serve_forever(poll_interval=0.01))
    thread.start()
    monkeypatch.setenv(KEY_ENV, KEY)
    state.endpoint = f"http://127.0.0.1:{server.server_port}/v1/chat/completions"
    try:
        yield state
    finally:
        state.release_first.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        assert not thread.is_alive()


def _command(state, endpoint):
    ref, _language, _kind = next(iter(state.indexed.values()))
    request = NarrativeBatchRequest.from_dict({
        "schema_version": "narrative-batch-request/1", "run_id": "parent-kill",
        "sources": [{
            "schema_version": ref.schema_version, "document_id": ref.document_id,
            "source_id": ref.source_id, "content_sha256": ref.content_sha256,
            "byte_size": ref.byte_size, "mime_type": ref.mime_type,
        }], "profile": "P2", "max_seconds": 30, "max_tokens": 200_000, "max_cost_usd": "2",
        "model": {
            "model_id": "stub-model", "endpoint": endpoint, "api_key_env": KEY_ENV,
            "max_output_tokens": 400, "timeout_seconds": 30, "allow_local_http": True,
        }, "pricing": {
            "version": "fixture-price/1", "input_micro_usd_per_million_tokens": 1_000_000,
            "output_micro_usd_per_million_tokens": 2_000_000,
        },
    })
    request_path = state.root / "request.json"
    request_path.write_text(json.dumps(request.to_dict()), encoding="utf-8")
    assert KEY not in request_path.read_text(encoding="utf-8")
    env = dict(os.environ)
    env.update(PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"),
               PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHON_DOTENV_DISABLED="1")
    return [
        sys.executable, "-m", "company_wiki.automation.narrative_batch_cli",
        "--project-root", str(state.root), "--catalog-config", str(state.config_path),
        "--automation-db", str(state.store.db_path), "--work-dir", str(state.root / "run-work"),
        "--request", str(request_path),
    ], env


def test_killed_coordinator_releases_owner_and_resumes_without_refunding_unknown_request(
    tmp_path_factory, interrupted_model_server,
):
    with isolated_batch_directory(tmp_path_factory) as root:
        state = prepare_source_catalog(root, one_source=True)
        coordinator = None
        children = []
        try:
            state.store = AutomationStore(root / "automation.db")
            state.store.set_runtime_gate(RuntimeState.ENABLED, updated_at=T0)
            scheduler = AutomationScheduler(state.store, create_default_registry(),
                                            PolicyConfig(allow_llm=True, allow_network=True))
            state.outside = foreign_ready_jobs(state, state.store, scheduler)
            state.store.set_runtime_gate(RuntimeState.PAUSED, updated_at=T0)
            originals = {path: path.read_bytes() for path in (root / "companies").rglob("*") if path.is_file()}
            originals[state.config_path] = state.config_path.read_bytes()
            command, env = _command(state, interrupted_model_server.endpoint)
            coordinator = subprocess.Popen(command, cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            assert interrupted_model_server.first_received.wait(timeout=25), "Formal CLI never reached the first HTTP POST"
            assert coordinator.poll() is None
            runs = NarrativeRunStore(state.store.db_path)
            reserved = runs.reservations_for_run("parent-kill")
            assert len(reserved) == 1 and reserved[0].usage_status == "reserved"
            uncertain = reserved[0]
            assert uncertain.usage_settled_at is None and uncertain.response_sha256 is None
            initial_budget = runs.budget_snapshot("parent-kill")
            assert initial_budget.charged_tokens == uncertain.reserved_tokens > 0
            assert initial_budget.charged_micro_usd == uncertain.reserved_micro_usd > 0
            attempt = state.store.get_attempt(uncertain.attempt_id)
            assert attempt is not None and attempt.finished_at is None
            children = [_ObservedProcess(pid) for pid in _child_pids(coordinator.pid)]
            assert len(children) >= 2 and all(not child.exited() for child in children)
            assert len(list((root / "run-work" / "logs").glob("*.stdout.log"))) == 2
            coordinator.kill()
            coordinator.wait(timeout=5)
            _wait_until(lambda: all(child.exited() for child in children), timeout=8)
            killed_stdout, killed_stderr = coordinator.communicate(timeout=5)
            assert coordinator.returncode != 0 and KEY.encode() not in killed_stdout + killed_stderr
            # Acquire the actual OS mutex after death, rather than deleting a
            # lock file or forging an ownership receipt.
            with os_file_mutex(state.store.db_path.with_name("automation.db.batch-owner.lock"), timeout_seconds=0.2):
                pass
            assert runs.reservations_for_run("parent-kill") == reserved
            assert_originals_and_foreign_jobs_untouched(state, originals)
            interrupted_model_server.release_first.set()
            resumed = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, encoding="utf-8", timeout=45)
            assert KEY not in resumed.stdout + resumed.stderr
            assert resumed.stdout.strip(), resumed.stderr
            result = json.loads(resumed.stdout)
            assert result["schema_version"] == "narrative-batch-result/1" and result["run_id"] == "parent-kill"
            assert result["status"] in {"completed", "budget_exhausted"}, result
            assert resumed.returncode == (0 if result["status"] == "completed" else 2)
            assert interrupted_model_server.errors == []
            assert len(interrupted_model_server.requests) in {1, 2}
            reservations = runs.reservations_for_run("parent-kill")
            retained = next(item for item in reservations if item.attempt_id == uncertain.attempt_id)
            completed_attempt = state.store.get_attempt(uncertain.attempt_id)
            assert completed_attempt is not None and completed_attempt.finished_at is not None
            assert retained.usage_status == "unknown" and retained.usage_settled_at is not None, {
                "status": retained.usage_status, "attempt_error": completed_attempt.error_code,
                "charged_tokens": retained.charged_tokens, "charged_micro_usd": retained.charged_micro_usd,
                "receipt_budget": result["budget"],
            }
            assert retained.request_sha256 == uncertain.request_sha256
            assert retained.charged_tokens == uncertain.reserved_tokens
            assert retained.charged_micro_usd == uncertain.reserved_micro_usd
            assert retained.response_sha256 is None
            budget = runs.budget_snapshot("parent-kill")
            assert budget.charged_tokens >= initial_budget.charged_tokens
            assert budget.charged_micro_usd >= initial_budget.charged_micro_usd
            assert result["budget"] == {
                "tokens": budget.charged_tokens, "estimated_micro_usd": budget.charged_micro_usd,
                "unknown_reservations": budget.unknown_reservations,
                "unsettled_reservations": budget.unsettled_reservations,
            }
            assert budget.unknown_reservations == 1 and budget.unsettled_reservations == 0
            assert len(result["documents"]) == 1
            document = result["documents"][0]
            assert document["document_id"] == next(iter(state.indexed))
            if result["status"] == "completed":
                assert len(interrupted_model_server.requests) == 2
                assert budget.charged_tokens == uncertain.reserved_tokens + 92
                assert budget.charged_micro_usd == uncertain.reserved_micro_usd + 111
                pin = document["artifact_ref"]
                artifacts = NarrativeArtifactStore(state.catalog.store, LocalNarrativeObjectStore(state.catalog.config.catalog_dir))
                version, payload = artifacts.read_exact(
                    artifact_version_id=pin["artifact_version_id"], document_id=pin["document_id"],
                    source_id=pin["source_id"], source_sha256=pin["source_sha256"],
                    expected_sha256=pin["content_sha256"], expected_size=pin["byte_size"],
                )
                assert version.byte_size == len(payload) > 0
                assert len(list((state.catalog.config.catalog_dir / "objects").rglob("*.json"))) == 1
            else:
                assert document["artifact_ref"] is None
                assert result["budget"]["tokens"] > 0 and result["budget"]["estimated_micro_usd"] > 0
            assert_originals_and_foreign_jobs_untouched(state, originals, output=resumed.stdout + resumed.stderr)
            assert state.store.list_outbox_entries(status="pending") == ()
        finally:
            if coordinator is not None and coordinator.poll() is None:
                coordinator.kill()
                coordinator.wait(timeout=5)
            interrupted_model_server.release_first.set()
            for child in children:
                child.close()
            state.catalog.close()
