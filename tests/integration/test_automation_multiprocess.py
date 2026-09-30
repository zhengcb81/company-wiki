"""Real spawn-process acceptance tests for the Phase E3 automation runtime."""

from __future__ import annotations

import hashlib
import json
import math
import multiprocessing
import os
import statistics
import threading
import time
from datetime import datetime, timedelta, timezone
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


def _timestamp_after(value: str, seconds: int) -> str:
    parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )
    return (parsed + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _claim_ready_job_in_process(
    db_path: str,
    worker_id: str,
    generation: int,
    now: str,
    barrier,
    results,
) -> None:
    candidate = AutomationStore(Path(db_path))
    barrier.wait(timeout=15)
    claimed = candidate.claim_next_ready(
        worker_id=worker_id,
        attempt_id=f"attempt-{worker_id}",
        lease_token=f"lease-{worker_id}",
        now=now,
        lease_until=_timestamp_after(now, 30),
        expected_generation=generation,
        allowed_job_types=("test.compute",),
    )
    results.put((worker_id, claimed is not None))


class _FrozenClock:
    def __init__(self, value: str) -> None:
        self._value = value

    def now(self) -> str:
        return self._value


def _run_direct_worker_once(
    db_path: str,
    trace_dir: str,
    worker_id: str,
    now: str,
    blocked_job_id: str | None = None,
    release_path: str | None = None,
) -> None:
    from company_wiki.automation.store import LeaseLostError
    from company_wiki.automation.worker import Worker
    from company_wiki.automation.worker_process import WorkerProcessSpec
    from support.automation_worker_fixture import create_runtime

    options: dict[str, object] = {"trace_dir": trace_dir}
    if blocked_job_id is not None:
        options["block_phase_by_job"] = {blocked_job_id: "handler_started"}
        if release_path is not None:
            options["release_file_by_job"] = {blocked_job_id: release_path}
    spec = WorkerProcessSpec(
        worker_id=worker_id,
        role="compute",
        db_path=db_path,
        log_dir=str(Path(trace_dir).parent / "logs"),
        runtime_factory_path=FACTORY,
        runtime_options_json=json.dumps(options, sort_keys=True),
        allowed_job_types=("test.compute",),
        lease_seconds=3.0,
        heartbeat_interval_seconds=0.25,
        idle_sleep_seconds=0.03,
        child_log_max_bytes=4096,
    )
    runtime = create_runtime(spec)
    worker = Worker(
        AutomationStore(Path(db_path)),
        runtime.registry,
        runtime.executor,
        clock=_FrozenClock(now),
        lease_seconds=3,
        worker_id=worker_id,
        heartbeat_interval_seconds=None,
        allowed_job_types=("test.compute",),
        lifecycle_callback=runtime.lifecycle_callback,
    )
    try:
        worker.process_one()
    except LeaseLostError:
        Path(trace_dir, f"late-finish-rejected--{worker_id}.json").write_text(
            json.dumps({"worker_id": worker_id, "pid": os.getpid()}),
            encoding="utf-8",
        )


@pytest.mark.parametrize("run_number", [1, 2, 3])
def test_e7_r01_spawned_processes_claim_one_ready_job_exactly_once(
    process_root: Path, run_number: int
) -> None:
    store = AutomationStore(process_root / f"r01-{run_number}.db")
    job_id = _seed_job(
        store,
        suffix=f"r01-{run_number}",
        job_type="test.compute",
        subject_id=f"source-r01-{run_number}",
    )
    generation = store.set_runtime_gate(
        models.RuntimeState.ENABLED, updated_at=_now()
    ).control_generation
    context = multiprocessing.get_context("spawn")
    barrier = context.Barrier(2)
    results = context.Queue()
    workers = [
        context.Process(
            target=_claim_ready_job_in_process,
            args=(str(store.db_path), f"r01-{index}", generation, _now(), barrier, results),
        )
        for index in range(2)
    ]
    try:
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=15)
        assert all(not worker.is_alive() for worker in workers)
        assert all(worker.exitcode == 0 for worker in workers)
        claims = [results.get(timeout=3) for _ in workers]
    finally:
        for worker in workers:
            if worker.is_alive():
                worker.terminate()
                worker.join(timeout=3)
        results.close()
        results.join_thread()

    assert sum(claimed for _worker_id, claimed in claims) == 1
    assert len(store.list_attempts(job_id)) == 1
    assert store.get_job(job_id).status is models.JobStatus.RUNNING


@pytest.mark.parametrize("run_number", [1, 2, 3])
def test_e7_r04_late_old_process_cannot_overwrite_retried_attempt(
    process_root: Path, run_number: int
) -> None:
    store = AutomationStore(process_root / f"r04-{run_number}.db")
    job_id = _seed_job(
        store,
        suffix=f"r04-{run_number}",
        job_type="test.compute",
        subject_id=f"source-r04-{run_number}",
    )
    store.set_runtime_gate(models.RuntimeState.ENABLED, updated_at=_now())
    start_time = _now()
    trace_dir = process_root / f"r04-trace-{run_number}"
    release_path = process_root / f"release-{run_number}.signal"
    old_worker = multiprocessing.get_context("spawn").Process(
        target=_run_direct_worker_once,
        args=(
            str(store.db_path),
            str(trace_dir),
            f"slow-old-{run_number}",
            start_time,
            job_id,
            str(release_path),
        ),
    )
    old_worker.start()
    try:
        _wait_until(lambda: bool(_markers(trace_dir, "handler_started", job_id)))
        first = store.list_attempts(job_id)[0]
        reap_time = _timestamp_after(start_time, 4)
        assert store.reap_expired_attempts(now=reap_time) == (first.attempt_id,)
        retry_time = _timestamp_after(reap_time, 90)
        assert store.promote_ready_jobs(now=retry_time) == (job_id,)

        new_worker = multiprocessing.get_context("spawn").Process(
            target=_run_direct_worker_once,
            args=(
                str(store.db_path),
                str(trace_dir),
                f"retry-new-{run_number}",
                retry_time,
            ),
        )
        new_worker.start()
        new_worker.join(timeout=15)
        assert not new_worker.is_alive()
        assert new_worker.exitcode == 0
        assert store.get_job(job_id).status is models.JobStatus.SUCCEEDED

        release_path.touch()
        old_worker.join(timeout=15)
        assert not old_worker.is_alive()
        assert old_worker.exitcode == 0
    finally:
        release_path.touch(exist_ok=True)
        if old_worker.is_alive():
            old_worker.terminate()
            old_worker.join(timeout=3)

    attempts = store.list_attempts(job_id)
    assert len(attempts) == 2
    assert attempts[0].error_code == "LEASE_EXPIRED"
    assert attempts[1].outcome is models.HandlerOutcome.SUCCEEDED
    assert store.get_job(job_id).status is models.JobStatus.SUCCEEDED
    assert list(trace_dir.glob("late-finish-rejected--*.json"))
    assert len(_markers(trace_dir, "attempt_finished", job_id)) == 1


def _process_rss_bytes(pid: int) -> int:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        open_process = kernel.OpenProcess
        open_process.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        open_process.restype = ctypes.c_void_p
        close_handle = kernel.CloseHandle
        close_handle.argtypes = (ctypes.c_void_p,)
        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        get_memory = psapi.GetProcessMemoryInfo
        get_memory.argtypes = (
            ctypes.c_void_p,
            ctypes.POINTER(ProcessMemoryCounters),
            wintypes.DWORD,
        )
        get_memory.restype = wintypes.BOOL
        handle = open_process(0x0400 | 0x0010, False, pid)
        if not handle:
            return 0
        try:
            return (
                int(counters.WorkingSetSize)
                if get_memory(handle, ctypes.byref(counters), counters.cb)
                else 0
            )
        finally:
            close_handle(handle)

    status = Path(os.sep) / "proc" / str(pid) / "status"
    if not status.is_file():
        return 0
    for line in status.read_text(encoding="utf-8").splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1]) * 1024
    return 0


def _sample_supervisor_rss(
    supervisor: AutomationSupervisor,
    stop: threading.Event,
    peak_values: list[int],
) -> None:
    peak = 0
    while not stop.is_set():
        pids = {os.getpid()}
        pids.update(
            child.pid
            for child in supervisor.children()
            if child.alive and child.pid is not None
        )
        peak = max(peak, sum(_process_rss_bytes(pid) for pid in pids))
        stop.wait(0.05)
    peak_values.append(peak)


def _percentile95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def _profile_max_concurrency(intervals: list[tuple[int, int]]) -> int:
    events = sorted(
        [(start, 1) for start, _end in intervals]
        + [(end, -1) for _start, end in intervals],
        key=lambda event: (event[0], event[1]),
    )
    active = 0
    maximum = 0
    for _time_ns, delta in events:
        active += delta
        maximum = max(maximum, active)
    return maximum


def _run_profile_trial(
    parent_root: Path, *, profile: str, round_number: int
) -> dict[str, object]:
    trial_root = parent_root / f"{profile.lower()}-{round_number}"
    trial_root.mkdir()
    database = trial_root / "automation.db"
    store = AutomationStore(database)
    seeded_at: dict[str, int] = {}
    job_ids: list[str] = []
    for index in range(45):
        job_id = _seed_job(
            store,
            suffix=f"e7-{profile.lower()}-{round_number}-{index:02d}",
            job_type="test.compute" if index < 30 else "test.model",
            subject_id=f"source-e7-{profile.lower()}-{round_number}-{index:02d}",
        )
        job_ids.append(job_id)
        seeded_at[job_id] = time.monotonic_ns()
    store.set_runtime_gate(models.RuntimeState.ENABLED, updated_at=_now())
    trace_dir = trial_root / "trace"
    delay_by_job = {job_id: 0.18 for job_id in job_ids}
    supervisor = AutomationSupervisor(
        _config(
            trial_root,
            options={"trace_dir": str(trace_dir), "delay_by_job": delay_by_job},
            profile=profile,
            lease_seconds=10.0,
            heartbeat_interval_seconds=1.0,
            child_log_max_bytes=4096,
        )
    )
    stop_sampling = threading.Event()
    peak_values: list[int] = []
    sampler = threading.Thread(
        target=_sample_supervisor_rss,
        args=(supervisor, stop_sampling, peak_values),
        daemon=True,
    )
    started = time.perf_counter()
    supervisor.start()
    sampler.start()
    try:
        supervisor.wait_for_terminal(tuple(job_ids), timeout_seconds=60)
    finally:
        supervisor.stop()
        stop_sampling.set()
        sampler.join(timeout=3)
    wall_seconds = time.perf_counter() - started

    wait_ms: list[float] = []
    run_ms: list[float] = []
    intervals: list[tuple[int, int]] = []
    for job_id in job_ids:
        starts = _markers(trace_dir, "handler_started", job_id)
        finishes = _markers(trace_dir, "handler_finished", job_id)
        assert len(starts) == len(finishes) == 1
        start_ns = int(starts[0]["monotonic_ns"])
        finish_ns = int(finishes[0]["monotonic_ns"])
        wait_ms.append((start_ns - seeded_at[job_id]) / 1_000_000)
        run_ms.append((finish_ns - start_ns) / 1_000_000)
        intervals.append((start_ns, finish_ns))
        attempts = store.list_attempts(job_id)
        assert len(attempts) == 1
        assert attempts[0].outcome is models.HandlerOutcome.SUCCEEDED

    database_bytes = database.stat().st_size
    wal = Path(f"{database}-wal")
    wal_bytes = wal.stat().st_size if wal.exists() else 0
    log_paths = tuple((trial_root / "process-logs").glob("*.log"))
    assert all(path.stat().st_size <= 4096 for path in log_paths)
    busy_errors = sum(
        1
        for job_id in job_ids
        for attempt in store.list_attempts(job_id)
        if attempt.error_code
        and any(term in attempt.error_code.upper() for term in ("BUSY", "LOCKED"))
    )
    result: dict[str, object] = {
        "profile": profile,
        "round": round_number,
        "jobs": len(job_ids),
        "wall_seconds": round(wall_seconds, 3),
        "jobs_per_hour": round(len(job_ids) * 3600 / wall_seconds, 1),
        "p95_queue_wait_ms": round(_percentile95(wait_ms), 1),
        "p95_handler_ms": round(_percentile95(run_ms), 1),
        "max_concurrency": _profile_max_concurrency(intervals),
        "peak_process_tree_rss_bytes": max(peak_values, default=0),
        "automation_db_bytes": database_bytes,
        "automation_wal_bytes": wal_bytes,
        "sqlite_busy_errors": busy_errors,
        "retry_count": 0,
        "catalog_lock_wait_ms": None,
    }
    assert result["peak_process_tree_rss_bytes"] > 0
    assert result["sqlite_busy_errors"] == 0
    if profile == "P1":
        assert result["max_concurrency"] == 1
    else:
        assert result["max_concurrency"] >= 2
    return result


@pytest.mark.skipif(
    os.environ.get("COMPANY_WIKI_RUN_E7_BENCHMARK") != "1",
    reason="set COMPANY_WIKI_RUN_E7_BENCHMARK=1 to run the bounded profile benchmark",
)
def test_e7_profiles_measure_bounded_worker_throughput_and_space(
    process_root: Path,
) -> None:
    trial_root = process_root / "e7-profile-benchmark"
    trial_root.mkdir()
    results = [
        _run_profile_trial(trial_root, profile=profile, round_number=round_number)
        for round_number, profile in enumerate(
            ("P1", "P2", "P4", "P4", "P2", "P1"), start=1
        )
    ]
    medians = {
        profile: statistics.median(
            float(result["wall_seconds"])
            for result in results
            if result["profile"] == profile
        )
        for profile in ("P1", "P2", "P4")
    }
    p2_improvement = medians["P1"] / medians["P2"] - 1
    p4_improvement = medians["P2"] / medians["P4"] - 1
    rss_medians = {
        profile: statistics.median(
            int(result["peak_process_tree_rss_bytes"])
            for result in results
            if result["profile"] == profile
        )
        for profile in ("P2", "P4")
    }
    p2_eligible = p2_improvement >= 0.25
    p4_speed_rss_candidate = (
        p4_improvement >= 0.15
        and rss_medians["P4"] <= rss_medians["P2"] * 1.8
    )
    recommendation = "P2" if p2_eligible else "P1"
    print(
        "E7_PROFILE_RECEIPT "
        + json.dumps(
            {
                "trials": results,
                "median_wall_seconds": medians,
                "p2_improvement": round(p2_improvement, 3),
                "p4_improvement": round(p4_improvement, 3),
                "peak_rss_medians": rss_medians,
                "recommended_profile_before_real_sample_and_lock_gates": recommendation,
                "p4_speed_and_rss_candidate": p4_speed_rss_candidate,
                "sqlite_busy_p95_ms": None,
                "catalog_lock_wait_ms": None,
                "unmeasured_gates": [
                    "sqlite busy-wait p95",
                    "catalog lock contention",
                    "real E6 sample profile",
                ],
            },
            sort_keys=True,
        )
    )


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
