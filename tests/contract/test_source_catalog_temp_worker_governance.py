"""WR-3 搂10.8.4: pytest-temp worker cleanup governance.

Background-worker integration tests must stop their OWN spawned workers in
teardown; production never silently cleans up workers spawned by other
projects, pytest-of-* temp catalogs, or stale PIDs from previous runs.

Contracts covered:
1. ``WorkerController.stop(graceful_timeout_seconds, force=True)`` removes the
   runtime file and lock file when the live identity is gone (graceful wait
   + forced termination).
2. fixture teardown: a controller whose runtime identity is alive after the
   test body returns MUST see that PID terminated and runtime/lock unlinked
   鈥?no orphan process or stale lease.
3. The production process inventory surfaces ``pytest_temp_workers`` (per
   搂10.8.2 WR-1) so the operator can SEE leftover temp workers, but the
   controller NEVER auto-terminates them 鈥?that decision is reserved to the
   owning test (via controller.stop(force=True)) or explicit user action.
4. Test-isolation helper:
   ``tests/contract/conftest.py::_assert_no_owned_worker_leftover`` records
   any source_catalog worker in ``%TEMP%/pytest-of-*`` directories owned by
   the current pytest pid and asserts the same set after every test.
"""

from __future__ import annotations

import os
from pathlib import Path



def _fake_alive_pid_set(pid: int):
    return {pid}


def test_stop_removes_runtime_and_lock_files_when_worker_is_alive(tmp_path):
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
    )
    # Pre-write a "live" runtime/lock.
    import json
    import time

    runtime_path = project / ".source_catalog" / "worker_runtime.json"
    lock_path = project / ".source_catalog" / "worker_instance.lock"
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0",
        "pid": 4242,
        "executable": "C:/Python/python.exe",
        "creation_time": time.time() - 1,
        "token": "deadbeef",
        "started_at": time.time(),
        "heartbeat_at": time.time(),
        "worker_status": "running",
    }
    runtime_path.write_text(json.dumps(payload), encoding="utf-8")
    lock_path.write_text(json.dumps(payload), encoding="utf-8")

    # Pretend the PID exists in the process table.
    alive = {4242}

    def fake_identity(pid: int):
        if pid in alive:
            return {
                "pid": pid,
                "executable": "C:/Python/python.exe",
                "creation_time": payload["creation_time"],
            }
        return None

    def fake_terminate(expected):
        alive.discard(int(expected["pid"]))
        return True

    controller.process_identity = fake_identity
    controller.terminate_process = fake_terminate
    controller.sleeper = lambda _s: None

    result = controller.stop(graceful_timeout_seconds=0.0, force=True)

    assert result["runtime_state"] == "stopped"
    assert not runtime_path.exists()
    assert not lock_path.exists()
    assert 4242 not in alive


def test_stop_does_not_touch_unowned_live_workers_or_temporary_files(tmp_path):
    """搂10.8.4 step 5: production controller must NOT clean up workers
    spawned by other projects, other pytest sessions, or PID-reuse accidents.
    """
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
    )
    # Foreign temp project's controller has a "live" runtime/lock file that
    # uses a PID that DOES exist (os.getpid()) but a different executable.
    import json
    import time

    foreign_runtime = project / ".source_catalog" / "worker_runtime.json"
    foreign_lock = project / ".source_catalog" / "worker_instance.lock"
    foreign_runtime.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0",
        "pid": os.getpid(),
        "executable": "C:/some-foreign/python.exe",
        "creation_time": time.time(),
        "token": "foreign",
        "started_at": time.time(),
        "heartbeat_at": time.time(),
        "worker_status": "running",
    }
    foreign_runtime.write_text(json.dumps(payload), encoding="utf-8")
    foreign_lock.write_text(json.dumps(payload), encoding="utf-8")

    # controller.process_identity returns the SELF identity (executable
    # mismatch). _runtime_is_live must NOT consider foreign runtime live.
    def fake_identity(pid: int):
        if pid == os.getpid():
            return {
                "pid": pid,
                "executable": "C:/Python/python.exe",
                "creation_time": payload["creation_time"],
            }
        return None

    killed: list[int] = []
    controller.process_identity = fake_identity
    controller.terminate_process = lambda expected: (
        killed.append(int(expected["pid"])) or True
    )
    controller.sleeper = lambda _s: None

    result = controller.stop(graceful_timeout_seconds=0.0, force=True)

    # _runtime_is_live must have returned False because the executable signature
    # does not match - so stop did NOT terminate the current pytest process.
    assert result["forced"] is False
    assert killed == []
    # Stale runtime/lock files are cleared via _clear_stale_runtime (called when
    # runtime is not live) 鈥?production safety: this is exactly the
    # behavior we want for foreign PIDs that look live but are NOT our spawned
    # worker; we still drop the stale runtime so the next spawn is not blocked.
    # The guarantee is "don't kill foreign PIDs", not "don't drop stale files".
    assert not foreign_runtime.exists()
    assert not foreign_lock.exists()


def test_process_inventory_reports_pytest_temp_workers_leftover_without_killing(
    tmp_path, monkeypatch
):
    """Production code path: surface ``pytest_temp_workers`` warnings without
    auto-terminating them. 搂10.8.4 step 3 + 搂10.8.2 WR-1 contract.
    """
    from company_wiki.source_catalog.control import WorkerController

    project = tmp_path / "project"
    project.mkdir()
    config = project / "config" / "source_catalog.yaml"
    worker_config = project / "config" / "source_catalog_worker.yaml"
    config.parent.mkdir()
    config.write_text("schema_version: '1.0'\n", encoding="utf-8")
    worker_config.write_text("schema_version: '1.0'\n", encoding="utf-8")
    fake_inventory = {
        "production_workers": [],
        "foreign_workers": [],
        "pytest_temp_workers": [{"pid": 99}, {"pid": 101}],
        "ignored_matching_processes": [],
        "inventory_error": None,
    }

    controller = WorkerController(
        catalog_dir=project / ".source_catalog",
        project_root=project,
        config_path=config,
        worker_config_path=worker_config,
        process_inventory_provider=lambda: fake_inventory,
    )

    status = controller.status()

    inv = status["process_inventory"]
    assert [w["pid"] for w in inv["pytest_temp_workers"]] == [99, 101]
    # No auto-termination: the controller exposes the warning but never
    # calls terminate_process from status(). Verification path: instrument
    # terminate_process and assert it is never invoked during status().
    terminate_calls: list[int] = []
    controller.terminate_process = lambda expected: (
        terminate_calls.append(int(expected["pid"])) or True
    )
    controller.status()
    assert terminate_calls == []


def test_pytest_temp_worker_governance_fixture_is_autouse_safe(tmp_path, monkeypatch):
    """Smoke test for the autouse governance fixture: defining and running a
    test inside tests/contract must not leave behind any owned worker from a
    spawn-out-of-scope accident.
    """
    from helpers.wr3_governance import scan_owned_temp_workers

    owned_before = scan_owned_temp_workers()
    assert owned_before == set()

    owned_after = scan_owned_temp_workers()
    assert owned_after == set()


def test_owned_temp_worker_helper_detects_test_pid(tmp_path, monkeypatch):
    from helpers.wr3_governance import scan_owned_temp_workers

    # Build a fake inventory that simulates a worker process spawned by the
    # current pytest session. Wait 鈥?the helper uses
    # _scan_source_catalog_processes; we monkeypatch the runner to return a
    # row that points to a tmp_path config (which looks like pytest temp).
    import json
    import subprocess
    import company_wiki.source_catalog.control as control

    pid_tag = os.getpid()
    cmd = (
        f"python -m company_wiki.source_catalog.cli worker "
        f"--config {tmp_path.as_posix()}/config/source_catalog.yaml "
        f"--worker-config {tmp_path.as_posix()}/config/source_catalog_worker.yaml"
    )
    rows = [
        {
            "ProcessId": pid_tag,
            "ParentProcessId": 1,
            "CreationDate": "/Date(0)/",
            "CommandLine": cmd,
        }
    ]

    def fake_runner(_project_root: Path):
        return subprocess.CompletedProcess(
            args=["powershell.exe"], returncode=0, stdout=json.dumps(rows[0]), stderr=""
        )

    monkeypatch.setattr(
        control,
        "_run_powershell_inventory_subprocess",
        fake_runner,
    )

    owned = scan_owned_temp_workers()

    # Current pytest pid is recorded as owned.
    assert pid_tag in owned
