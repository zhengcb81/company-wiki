"""Real spawn-process acceptance tests for the Phase E3 automation runtime."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from company_wiki.automation import models
from company_wiki.automation.store import AutomationStore
from company_wiki.automation.supervisor import AutomationSupervisor, SupervisorConfig


FACTORY = "support.automation_worker_fixture:create_runtime"
INPUT_HASH = hashlib.sha256(b"m3-e3-input").hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _seed_job(
    store: AutomationStore,
    *,
    suffix: str,
    job_type: str,
    subject_id: str,
    status: models.JobStatus = models.JobStatus.READY,
    depends_on: str | None = None,
) -> str:
    timestamp = _now()
    job_id = f"job-{suffix}"
    if depends_on is None:
        event = models.Event(
            event_id=f"event-{suffix}",
            event_type="source.revision_registered",
            subject_type="source_revision",
            subject_id=subject_id,
            input_hash=INPUT_HASH,
            payload_json=models.canonical_json({"suffix": suffix}),
            policy_version="narrative-v1",
            occurred_at=timestamp,
            observed_at=timestamp,
        )
        store.put_event(event)
    else:
        parent = store.get_job(depends_on)
        assert parent is not None
        event = store.get_event(parent.created_from_event_id)
        assert event is not None
    store.put_job(
        models.Job(
            job_id=job_id,
            job_key=models.make_job_key(
                job_type,
                event.subject_type,
                event.subject_id,
                event.input_hash,
                event.policy_version,
                "1.0.0",
            ),
            job_type=job_type,
            subject_type=event.subject_type,
            subject_id=event.subject_id,
            input_hash=event.input_hash,
            policy_version=event.policy_version,
            handler_version="1.0.0",
            risk_class=models.RiskClass.LOW,
            status=status,
            priority=10,
            not_before=timestamp,
            max_attempts=3,
            created_from_event_id=event.event_id,
            created_at=timestamp,
            updated_at=timestamp,
            last_error_code=None,
            last_error_detail=None,
        )
    )
    if depends_on is not None:
        store.add_job_dependency(job_id, depends_on)
    return job_id


def _config(
    root: Path,
    *,
    options: dict,
    profile: str = "P2",
    lease_seconds: float = 3.0,
    heartbeat_interval_seconds: float = 0.25,
    child_log_max_bytes: int = 4096,
) -> SupervisorConfig:
    return SupervisorConfig(
        db_path=root / "automation.db",
        log_dir=root / "process-logs",
        profile=profile,
        runtime_factory_path=FACTORY,
        runtime_options_json=json.dumps(options, sort_keys=True),
        compute_job_types=("test.compute",),
        model_job_types=("test.model",),
        lease_seconds=lease_seconds,
        heartbeat_interval_seconds=heartbeat_interval_seconds,
        idle_sleep_seconds=0.03,
        maintenance_interval_seconds=0.05,
        stop_grace_seconds=0.4,
        child_log_max_bytes=child_log_max_bytes,
    )


def _markers(trace_dir: Path, phase: str, job_id: str) -> list[dict]:
    values = []
    for path in trace_dir.glob(f"{phase}--{job_id}--*.json"):
        values.append(json.loads(path.read_text(encoding="utf-8")))
    return values


def _wait_until(predicate, *, timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.03)
    raise AssertionError("condition did not become true before timeout")


def _run_supervisor_parent(config: SupervisorConfig, pid_path: str) -> None:
    supervisor = AutomationSupervisor(config)
    supervisor.start()
    Path(pid_path).write_text(
        json.dumps([child.pid for child in supervisor.children()]), encoding="utf-8"
    )
    while True:
        time.sleep(0.1)


def _pid_is_alive(pid: int) -> bool:
    import ctypes

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(0x1000, False, pid)
    if not handle:
        return False
    try:
        exit_code = ctypes.c_ulong()
        return bool(kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))) and (
            exit_code.value == 259
        )
    finally:
        kernel32.CloseHandle(handle)


def _terminate_pid(pid: int) -> None:
    import ctypes

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(0x0001, False, pid)
    if not handle:
        return
    try:
        kernel32.TerminateProcess(handle, 91)
    finally:
        kernel32.CloseHandle(handle)


@pytest.fixture
def process_root(tmp_path: Path):
    root = tmp_path / "m3-e3-process"
    root.mkdir()
    yield root
    assert not [child for child in root.glob("*.tmp")]


def test_p2_processes_two_sources_concurrently_and_preserves_same_source_dependency(
    process_root: Path,
) -> None:
    store = AutomationStore(process_root / "automation.db")
    compute = _seed_job(
        store, suffix="compute", job_type="test.compute", subject_id="source-a"
    )
    model = _seed_job(
        store, suffix="model", job_type="test.model", subject_id="source-b"
    )
    downstream = _seed_job(
        store,
        suffix="downstream",
        job_type="test.model",
        subject_id="source-a",
        status=models.JobStatus.PLANNED,
        depends_on=compute,
    )
    store.set_runtime_gate(models.RuntimeState.ENABLED, updated_at=_now())
    trace_dir = process_root / "trace"
    options = {
        "trace_dir": str(trace_dir),
        "delay_by_job": {compute: 0.7, model: 0.7, downstream: 0.05},
    }

    supervisor = AutomationSupervisor(_config(process_root, options=options))
    try:
        supervisor.start()
        supervisor.wait_for_terminal((compute, model, downstream), timeout_seconds=20)
    finally:
        supervisor.stop()

    compute_start = _markers(trace_dir, "handler_started", compute)[0]["monotonic_ns"]
    compute_end = _markers(trace_dir, "handler_finished", compute)[0]["monotonic_ns"]
    model_start = _markers(trace_dir, "handler_started", model)[0]["monotonic_ns"]
    model_end = _markers(trace_dir, "handler_finished", model)[0]["monotonic_ns"]
    downstream_start = _markers(trace_dir, "handler_started", downstream)[0][
        "monotonic_ns"
    ]
    assert max(compute_start, model_start) < min(compute_end, model_end)
    assert downstream_start >= compute_end
    assert all(
        store.get_job(job_id).status is models.JobStatus.SUCCEEDED
        for job_id in (compute, model, downstream)
    )
    runtime_records = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in trace_dir.glob("runtime--*.json")
    ]
    assert sum(record["role"] == "model" for record in runtime_records) == 1
    assert all(
        not record["has_model_client"]
        for record in runtime_records
        if record["role"] == "compute"
    )


@pytest.mark.parametrize("kill_phase", ["claimed", "handler_started", "before_finish"])
def test_killed_child_is_reaped_and_job_is_recovered_after_supervisor_restart(
    process_root: Path, kill_phase: str
) -> None:
    store = AutomationStore(process_root / "automation.db")
    job_id = _seed_job(
        store, suffix=kill_phase, job_type="test.compute", subject_id="source-crash"
    )
    store.set_runtime_gate(models.RuntimeState.ENABLED, updated_at=_now())
    trace_dir = process_root / "trace"
    blocked = {job_id: kill_phase}
    options = {"trace_dir": str(trace_dir), "block_phase_by_job": blocked}
    supervisor = AutomationSupervisor(
        _config(
            process_root,
            options=options,
            profile="P1",
            lease_seconds=1.0,
            heartbeat_interval_seconds=0.2,
        )
    )
    supervisor.start()
    _wait_until(lambda: bool(_markers(trace_dir, kill_phase, job_id)))
    first_pid = supervisor.children()[0].pid
    supervisor.terminate_worker(supervisor.children()[0].worker_id)
    supervisor.stop()

    _wait_until(
        lambda: store.list_attempts(job_id)
        and store.list_attempts(job_id)[0].lease_until < _now(),
        timeout=5,
    )
    recovery_options = {"trace_dir": str(trace_dir), "delay_by_job": {job_id: 0.01}}
    restarted = AutomationSupervisor(
        _config(
            process_root,
            options=recovery_options,
            profile="P1",
            lease_seconds=1.0,
            heartbeat_interval_seconds=0.2,
        )
    )
    try:
        restarted.start()
        restarted.wait_for_terminal((job_id,), timeout_seconds=15)
    finally:
        restarted.stop()

    attempts = store.list_attempts(job_id)
    assert len(attempts) == 2
    assert attempts[0].error_code == "LEASE_EXPIRED"
    assert attempts[1].outcome is models.HandlerOutcome.SUCCEEDED
    assert store.get_job(job_id).status is models.JobStatus.SUCCEEDED
    assert all(
        marker["pid"] != first_pid
        for marker in _markers(trace_dir, "attempt_finished", job_id)
    )


def test_active_heartbeat_prevents_reap_then_stopped_process_becomes_reclaimable(
    process_root: Path,
) -> None:
    store = AutomationStore(process_root / "automation.db")
    job_id = _seed_job(
        store, suffix="heartbeat", job_type="test.compute", subject_id="source-heartbeat"
    )
    store.set_runtime_gate(models.RuntimeState.ENABLED, updated_at=_now())
    trace_dir = process_root / "trace"
    options = {
        "trace_dir": str(trace_dir),
        "block_phase_by_job": {job_id: "handler_started"},
    }
    supervisor = AutomationSupervisor(
        _config(
            process_root,
            options=options,
            profile="P1",
            lease_seconds=1.0,
            heartbeat_interval_seconds=0.15,
        )
    )
    try:
        supervisor.start()
        _wait_until(lambda: bool(_markers(trace_dir, "handler_started", job_id)))
        time.sleep(1.4)
        attempt = store.list_attempts(job_id)[0]
        assert attempt.heartbeat_at > attempt.started_at
        assert store.reap_expired_attempts(now=_now()) == ()
        supervisor.terminate_worker(supervisor.children()[0].worker_id)
    finally:
        supervisor.stop()

    _wait_until(
        lambda: store.list_attempts(job_id)[0].lease_until < _now(), timeout=5
    )
    assert store.reap_expired_attempts(now=_now()) == (attempt.attempt_id,)
    assert store.get_job(job_id).status is models.JobStatus.RETRY_WAIT


def test_context_exit_reaps_owned_children_and_child_logs_are_bounded(
    process_root: Path,
) -> None:
    store = AutomationStore(process_root / "automation.db")
    job_id = _seed_job(
        store, suffix="logs", job_type="test.compute", subject_id="source-logs"
    )
    store.set_runtime_gate(models.RuntimeState.ENABLED, updated_at=_now())
    trace_dir = process_root / "trace"
    config = _config(
        process_root,
        options={"trace_dir": str(trace_dir), "print_bytes": 10000},
        profile="P1",
        child_log_max_bytes=512,
    )
    with AutomationSupervisor(config) as supervisor:
        supervisor.wait_for_terminal((job_id,), timeout_seconds=15)
        snapshots = supervisor.children()
        assert snapshots and all(snapshot.alive for snapshot in snapshots)
    assert all(not snapshot.alive for snapshot in supervisor.children())
    logs = list((process_root / "process-logs").glob("*.log"))
    assert logs
    assert all(path.stat().st_size <= 512 for path in logs)


def test_workers_self_terminate_when_supervisor_parent_is_abruptly_killed(
    process_root: Path,
) -> None:
    store = AutomationStore(process_root / "automation.db")
    job_id = _seed_job(
        store, suffix="orphan", job_type="test.compute", subject_id="source-orphan"
    )
    store.set_runtime_gate(models.RuntimeState.ENABLED, updated_at=_now())
    trace_dir = process_root / "trace"
    config = _config(
        process_root,
        options={
            "trace_dir": str(trace_dir),
            "block_phase_by_job": {job_id: "handler_started"},
        },
        profile="P1",
    )
    pid_path = process_root / "child-pids.json"
    context = multiprocessing.get_context("spawn")
    parent = context.Process(target=_run_supervisor_parent, args=(config, str(pid_path)))
    parent.start()
    _wait_until(pid_path.is_file)
    child_pids = json.loads(pid_path.read_text(encoding="utf-8"))
    assert child_pids and all(_pid_is_alive(pid) for pid in child_pids)
    _wait_until(lambda: bool(_markers(trace_dir, "handler_started", job_id)))

    parent.terminate()
    parent.join(timeout=5)
    try:
        _wait_until(
            lambda: all(not _pid_is_alive(pid) for pid in child_pids), timeout=5
        )
    finally:
        for pid in child_pids:
            if _pid_is_alive(pid):
                _terminate_pid(pid)

    assert all(not _pid_is_alive(pid) for pid in child_pids)
