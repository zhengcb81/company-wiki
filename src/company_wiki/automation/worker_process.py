"""Spawn-safe automation worker process entry point and runtime boundary."""

from __future__ import annotations

import importlib
import io
import json
import multiprocessing
import os
import threading
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol, cast

from .models import ClaimedWork
from .registry import HandlerRegistry
from .store import AutomationStore
from .worker import HandlerExecutor, Worker


@dataclass(frozen=True)
class WorkerRuntime:
    """Objects constructed inside one child process by an importable factory."""

    registry: HandlerRegistry
    executor: HandlerExecutor
    model_client: object | None = None
    lifecycle_callback: Callable[[str, ClaimedWork], None] | None = None


class StopEvent(Protocol):
    def is_set(self) -> bool: ...

    def wait(self, timeout: float | None = None) -> bool: ...


@dataclass(frozen=True)
class WorkerProcessSpec:
    worker_id: str
    role: str
    db_path: str
    log_dir: str
    runtime_factory_path: str
    runtime_options_json: str
    allowed_job_types: tuple[str, ...]
    lease_seconds: float
    heartbeat_interval_seconds: float
    idle_sleep_seconds: float
    child_log_max_bytes: int

    def __post_init__(self) -> None:
        if self.role not in {"mixed", "compute", "model"}:
            raise ValueError(f"unknown worker role: {self.role}")
        if not self.worker_id or not self.runtime_factory_path:
            raise ValueError("worker_id and runtime_factory_path are required")
        if not self.allowed_job_types:
            raise ValueError("allowed_job_types must not be empty")
        parsed = json.loads(self.runtime_options_json)
        if not isinstance(parsed, dict):
            raise ValueError("runtime_options_json must contain a JSON object")
        if self.lease_seconds <= self.heartbeat_interval_seconds:
            raise ValueError("lease_seconds must exceed heartbeat_interval_seconds")
        if self.idle_sleep_seconds <= 0 or self.child_log_max_bytes <= 0:
            raise ValueError("sleep and log limits must be positive")


class BoundedLogWriter(io.TextIOBase):
    """UTF-8 tail log that never persists more than ``max_bytes``."""

    def __init__(self, path: Path, *, max_bytes: int) -> None:
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        self._path = path
        self._max_bytes = max_bytes
        self._lock = threading.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
        if path.stat().st_size > max_bytes:
            path.write_bytes(path.read_bytes()[-max_bytes:])

    def writable(self) -> bool:
        return True

    def write(self, value: str) -> int:
        if not isinstance(value, str):
            raise TypeError("log value must be text")
        incoming = value.encode("utf-8", errors="replace")
        with self._lock:
            with self._path.open("r+b") as stream:
                stream.seek(0, 2)
                size = stream.tell()
                if size + len(incoming) <= self._max_bytes:
                    stream.write(incoming)
                    return len(value)
                if len(incoming) >= self._max_bytes:
                    retained = incoming[-self._max_bytes :]
                else:
                    keep = self._max_bytes - len(incoming)
                    stream.seek(max(0, size - keep))
                    retained = stream.read(keep) + incoming
                retained = retained.decode("utf-8", errors="ignore").encode("utf-8")
                stream.seek(0)
                stream.write(retained)
                stream.truncate()
        return len(value)

    def flush(self) -> None:
        return None


def validate_runtime(
    runtime: WorkerRuntime, *, role: str, allowed_job_types: tuple[str, ...]
) -> None:
    """Enforce the process-level LLM isolation contract before claiming work."""

    specs = tuple(runtime.registry.get(job_type) for job_type in allowed_job_types)
    if role == "compute":
        if runtime.model_client is not None:
            raise ValueError("compute worker must not hold a model client")
        if any(spec.llm for spec in specs):
            raise ValueError("compute worker cannot accept an LLM job type")
    elif role == "model":
        if runtime.model_client is None:
            raise ValueError("model worker requires a child-local model client")
        if any(not spec.llm for spec in specs):
            raise ValueError("model worker cannot accept a non-LLM job type")
    elif role != "mixed":
        raise ValueError(f"unknown worker role: {role}")


def run_worker_process(
    spec: WorkerProcessSpec, stop_event: StopEvent, parent_pid: int
) -> None:
    """Build child-local dependencies and poll the shared database for work."""

    log_dir = Path(spec.log_dir)
    stdout = BoundedLogWriter(
        log_dir / f"{spec.worker_id}.stdout.log",
        max_bytes=spec.child_log_max_bytes,
    )
    stderr = BoundedLogWriter(
        log_dir / f"{spec.worker_id}.stderr.log",
        max_bytes=spec.child_log_max_bytes,
    )
    with redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            _start_parent_watchdog(parent_pid)
            factory = _resolve_factory(spec.runtime_factory_path)
            runtime = factory(spec)
            if not isinstance(runtime, WorkerRuntime):
                raise TypeError("runtime factory must return WorkerRuntime")
            validate_runtime(
                runtime, role=spec.role, allowed_job_types=spec.allowed_job_types
            )
            store = AutomationStore(Path(spec.db_path))
            worker = Worker(
                store,
                runtime.registry,
                runtime.executor,
                worker_id=spec.worker_id,
                lease_seconds=spec.lease_seconds,
                heartbeat_interval_seconds=spec.heartbeat_interval_seconds,
                allowed_job_types=spec.allowed_job_types,
                lifecycle_callback=runtime.lifecycle_callback,
            )
            while not stop_event.is_set() and os.getppid() == parent_pid:
                if not worker.process_one():
                    stop_event.wait(spec.idle_sleep_seconds)
        except BaseException:
            traceback.print_exc()
            raise


def _start_parent_watchdog(parent_pid: int) -> threading.Thread:
    thread = threading.Thread(
        target=_watch_parent,
        args=(parent_pid,),
        name="automation-parent-watchdog",
        daemon=True,
    )
    thread.start()
    return thread


def _watch_parent(parent_pid: int) -> None:
    while True:
        # Do not wait on the multiprocessing stop Event here.  A hard-killed
        # worker could otherwise die while holding the Event semaphore and
        # wedge the parent's bounded shutdown path.
        time.sleep(0.1)
        parent = multiprocessing.parent_process()
        alive = parent.is_alive() if parent is not None else os.getppid() == parent_pid
        if not alive or os.getppid() != parent_pid:
            os._exit(73)


def _resolve_factory(path: str) -> Callable[[WorkerProcessSpec], WorkerRuntime]:
    module_name, separator, attribute = path.partition(":")
    if not separator or not module_name or not attribute:
        raise ValueError("runtime factory path must use 'module:callable'")
    module = importlib.import_module(module_name)
    factory = getattr(module, attribute)
    if not callable(factory):
        raise TypeError(f"runtime factory is not callable: {path}")
    return cast(Callable[[WorkerProcessSpec], WorkerRuntime], factory)


__all__ = [
    "BoundedLogWriter",
    "WorkerProcessSpec",
    "WorkerRuntime",
    "run_worker_process",
    "validate_runtime",
]

