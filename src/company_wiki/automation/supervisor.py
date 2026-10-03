"""Bounded spawn-process supervisor for database-backed automation workers."""

from __future__ import annotations

import multiprocessing
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from multiprocessing.process import BaseProcess
from pathlib import Path
from types import TracebackType
from typing import Protocol

from company_wiki._id_scope import normalize_id_scope

from .models import JobStatus
from .store import AutomationStore
from .worker_process import WorkerProcessSpec, run_worker_process


class StopEvent(Protocol):
    def is_set(self) -> bool: ...

    def set(self) -> None: ...

    def wait(self, timeout: float | None = None) -> bool: ...


@dataclass(frozen=True)
class WorkerSlot:
    role: str
    ordinal: int

    @property
    def worker_id(self) -> str:
        return f"{self.role}-{self.ordinal}"


@dataclass(frozen=True)
class ChildSnapshot:
    worker_id: str
    role: str
    pid: int | None
    alive: bool
    exitcode: int | None


@dataclass(frozen=True)
class SupervisorConfig:
    db_path: Path
    log_dir: Path
    profile: str
    runtime_factory_path: str
    runtime_options_json: str
    compute_job_types: tuple[str, ...]
    model_job_types: tuple[str, ...]
    lease_seconds: float = 300.0
    heartbeat_interval_seconds: float = 30.0
    idle_sleep_seconds: float = 0.25
    maintenance_interval_seconds: float = 0.25
    stop_grace_seconds: float = 5.0
    child_log_max_bytes: int = 1_048_576
    max_restarts_per_slot: int = 3
    allowed_job_ids: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "allowed_job_ids", normalize_id_scope(
            self.allowed_job_ids, name="allowed_job_ids",
        ))
        profile_slots(self.profile)
        if not isinstance(self.db_path, Path) or not isinstance(self.log_dir, Path):
            raise TypeError("db_path and log_dir must be pathlib.Path values")
        if not self.compute_job_types or not self.model_job_types:
            raise ValueError("compute_job_types and model_job_types must not be empty")
        if set(self.compute_job_types) & set(self.model_job_types):
            raise ValueError("compute and model job types must be disjoint")
        if self.lease_seconds <= self.heartbeat_interval_seconds:
            raise ValueError("lease_seconds must exceed heartbeat interval")
        for value in (
            self.idle_sleep_seconds,
            self.maintenance_interval_seconds,
            self.stop_grace_seconds,
        ):
            if value <= 0:
                raise ValueError("supervisor timing values must be positive")
        if self.child_log_max_bytes <= 0 or self.max_restarts_per_slot < 0:
            raise ValueError("supervisor bounds are invalid")


@dataclass
class _Child:
    slot: WorkerSlot
    process: BaseProcess
    stop_event: StopEvent


class ChildProcessFailedError(RuntimeError):
    """Raised after a worker slot exceeds its bounded restart budget."""


def profile_slots(profile: str) -> tuple[WorkerSlot, ...]:
    if profile == "P1":
        return (WorkerSlot("mixed", 1),)
    if profile == "P2":
        return (WorkerSlot("compute", 1), WorkerSlot("model", 1))
    if profile == "P4":
        return (
            WorkerSlot("compute", 1),
            WorkerSlot("compute", 2),
            WorkerSlot("compute", 3),
            WorkerSlot("model", 1),
        )
    raise ValueError(f"unknown worker profile: {profile}")


class AutomationSupervisor:
    """Own child processes while jobs, leases and recovery remain in SQLite."""

    def __init__(self, config: SupervisorConfig) -> None:
        self._config = config
        self._context = multiprocessing.get_context("spawn")
        self._store = AutomationStore(config.db_path)
        self._children: dict[str, _Child] = {}
        self._restart_counts: dict[str, int] = {}
        self._started = False
        self._stopping = False

    def __enter__(self) -> AutomationSupervisor:
        self.start()
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        self.stop()

    def start(self) -> None:
        if self._started:
            return
        self._config.log_dir.mkdir(parents=True, exist_ok=True)
        self._started = True
        self._stopping = False
        for slot in profile_slots(self._config.profile):
            self._spawn(slot)

    def stop(self) -> None:
        if not self._started:
            return
        self._stopping = True
        for child in self._children.values():
            child.stop_event.set()
        deadline = time.monotonic() + self._config.stop_grace_seconds
        for child in self._children.values():
            remaining = max(0.0, deadline - time.monotonic())
            child.process.join(timeout=remaining)
        for child in self._children.values():
            if child.process.is_alive():
                child.process.terminate()
                child.process.join(timeout=self._config.stop_grace_seconds)
            if child.process.is_alive():
                child.process.kill()
                child.process.join(timeout=self._config.stop_grace_seconds)
        self._started = False

    def children(self) -> tuple[ChildSnapshot, ...]:
        return tuple(
            ChildSnapshot(
                worker_id=worker_id,
                role=child.slot.role,
                pid=child.process.pid,
                alive=child.process.is_alive(),
                exitcode=child.process.exitcode,
            )
            for worker_id, child in sorted(self._children.items())
        )

    def terminate_worker(self, worker_id: str) -> None:
        child = self._children[worker_id]
        if child.process.is_alive():
            child.process.terminate()
            child.process.join(timeout=self._config.stop_grace_seconds)

    def maintain(self) -> None:
        if not self._started or self._stopping:
            return
        now = _now()
        self._store.reap_expired_attempts(now=now, allowed_job_ids=self._config.allowed_job_ids)
        self._store.promote_ready_jobs(now=now, allowed_job_ids=self._config.allowed_job_ids)
        for slot in profile_slots(self._config.profile):
            worker_id = slot.worker_id
            child = self._children.get(worker_id)
            if child is None or not child.process.is_alive():
                count = self._restart_counts.get(worker_id, 0)
                if count >= self._config.max_restarts_per_slot:
                    raise ChildProcessFailedError(
                        f"worker {worker_id} exceeded restart budget"
                    )
                self._restart_counts[worker_id] = count + 1
                self._spawn(slot)

    def wait_for_terminal(
        self, job_ids: tuple[str, ...], *, timeout_seconds: float
    ) -> None:
        terminal = {
            JobStatus.SUCCEEDED,
            JobStatus.DEAD_LETTER,
            JobStatus.BLOCKED_HUMAN,
            JobStatus.CANCELLED,
        }
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            self.maintain()
            jobs = tuple(self._store.get_job(job_id) for job_id in job_ids)
            if all(job is not None and job.status in terminal for job in jobs):
                return
            time.sleep(self._config.maintenance_interval_seconds)
        states = {
            job_id: (self._store.get_job(job_id).status.value if self._store.get_job(job_id) else None)
            for job_id in job_ids
        }
        raise TimeoutError(f"jobs did not become terminal: {states}")

    def run_forever(self, stop_event: StopEvent | None = None) -> None:
        """Run the maintenance loop until an external event requests shutdown."""

        self.start()
        try:
            while stop_event is None or not stop_event.is_set():
                self.maintain()
                if stop_event is None:
                    time.sleep(self._config.maintenance_interval_seconds)
                else:
                    stop_event.wait(self._config.maintenance_interval_seconds)
        finally:
            self.stop()

    def _spawn(self, slot: WorkerSlot) -> None:
        allowed = (
            self._config.model_job_types
            if slot.role == "model"
            else self._config.compute_job_types
            if slot.role == "compute"
            else self._config.compute_job_types + self._config.model_job_types
        )
        spec = WorkerProcessSpec(
            worker_id=slot.worker_id,
            role=slot.role,
            db_path=str(self._config.db_path),
            log_dir=str(self._config.log_dir),
            runtime_factory_path=self._config.runtime_factory_path,
            runtime_options_json=self._config.runtime_options_json,
            allowed_job_types=allowed,
            lease_seconds=self._config.lease_seconds,
            heartbeat_interval_seconds=self._config.heartbeat_interval_seconds,
            idle_sleep_seconds=self._config.idle_sleep_seconds,
            child_log_max_bytes=self._config.child_log_max_bytes,
            allowed_job_ids=self._config.allowed_job_ids,
        )
        stop_event = self._context.Event()
        process = self._context.Process(
            name=f"company-wiki-{slot.worker_id}",
            target=run_worker_process,
            args=(spec, stop_event, os.getpid()),
            daemon=True,
        )
        process.start()
        self._children[slot.worker_id] = _Child(slot, process, stop_event)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = [
    "AutomationSupervisor",
    "ChildProcessFailedError",
    "ChildSnapshot",
    "SupervisorConfig",
    "WorkerSlot",
    "profile_slots",
]

