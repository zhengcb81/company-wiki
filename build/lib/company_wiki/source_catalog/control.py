"""Persistent, single-instance controls for the Windows source-catalog worker."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Callable
from uuid import uuid4


CONTROL_SCHEMA_VERSION = "1.0"
RUNTIME_SCHEMA_VERSION = "1.0"
HEARTBEAT_INTERVAL_SECONDS = 10.0


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        for attempt in range(6):
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                if attempt == 5:
                    raise
                time.sleep(0.02 * (attempt + 1))
    finally:
        temporary.unlink(missing_ok=True)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _normal_executable(value: object) -> str:
    return os.path.normcase(os.path.abspath(str(value))).replace("\\", "/")


def _same_identity(left: dict[str, Any] | None, right: dict[str, Any] | None) -> bool:
    if not left or not right:
        return False
    return (
        int(left.get("pid", -1)) == int(right.get("pid", -2))
        and str(left.get("creation_time")) == str(right.get("creation_time"))
        and _normal_executable(left.get("executable", ""))
        == _normal_executable(right.get("executable", ""))
    )


def _windows_process_identity(pid: int) -> dict[str, Any] | None:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.GetProcessTimes.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
    ]
    kernel32.GetProcessTimes.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    process_query_limited_information = 0x1000
    handle = kernel32.OpenProcess(process_query_limited_information, False, int(pid))
    if not handle:
        return None
    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return None
        creation = wintypes.FILETIME()
        exit_time = wintypes.FILETIME()
        kernel = wintypes.FILETIME()
        user = wintypes.FILETIME()
        if not kernel32.GetProcessTimes(
            handle,
            ctypes.byref(creation),
            ctypes.byref(exit_time),
            ctypes.byref(kernel),
            ctypes.byref(user),
        ):
            return None
        creation_ticks = (int(creation.dwHighDateTime) << 32) | int(creation.dwLowDateTime)
        return {
            "pid": int(pid),
            "executable": buffer.value,
            "creation_time": creation_ticks,
        }
    finally:
        kernel32.CloseHandle(handle)


def _portable_process_identity(pid: int) -> dict[str, Any] | None:
    try:
        os.kill(int(pid), 0)
    except (OSError, ProcessLookupError, ValueError):
        return None
    executable = sys.executable
    creation_time: str | int = "unknown"
    proc = Path("/proc") / str(pid)
    try:
        executable = str((proc / "exe").resolve(strict=True))
        creation_time = (proc / "stat").read_text(encoding="utf-8").split()[21]
    except (OSError, IndexError):
        if int(pid) != os.getpid():
            return None
    return {"pid": int(pid), "executable": executable, "creation_time": creation_time}


def process_identity(pid: int) -> dict[str, Any] | None:
    """Return identity fields strong enough to detect Windows PID reuse."""

    if os.name == "nt":
        return _windows_process_identity(pid)
    return _portable_process_identity(pid)


def terminate_matching_process(expected: dict[str, Any]) -> bool:
    """Terminate only when PID, executable and creation time still match."""

    pid = int(expected["pid"])
    if not _same_identity(process_identity(pid), expected):
        return False
    if os.name != "nt":
        return False
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.TerminateProcess.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    process_terminate = 0x0001
    process_query_limited_information = 0x1000
    handle = kernel32.OpenProcess(
        process_terminate | process_query_limited_information, False, pid
    )
    if not handle:
        return False
    try:
        if not _same_identity(process_identity(pid), expected):
            return False
        return bool(kernel32.TerminateProcess(handle, 2))
    finally:
        kernel32.CloseHandle(handle)


class WorkerSession:
    """The owned runtime lease used by one worker process."""

    def __init__(self, controller: "WorkerController", token: str, identity: dict[str, Any]):
        self.controller = controller
        self.token = token
        self.identity = identity
        self.closed = False

    def heartbeat(self, status: str, **details: Any) -> None:
        if self.closed:
            return
        current = _read_json(self.controller.runtime_path)
        if not current or current.get("token") != self.token:
            return
        heartbeat_at = self.controller.clock()
        update = {
            "heartbeat_at": heartbeat_at,
            "updated_at": heartbeat_at,
            "worker_status": status,
            "current_path": None,
            "progress_current": 0,
            "progress_total": 0,
            "progress_percent": None,
            "progress_detail": None,
        }
        if status != "waiting":
            update.update(
                {
                    "cycle_productive": None,
                    "next_wait_seconds": None,
                    "next_wake_reason": None,
                    "next_wake_at": None,
                }
            )
        update.update(details)
        current.update(update)
        _atomic_write_json(self.controller.runtime_path, current)

    def should_stop(self) -> bool:
        control = self.controller._read_control()
        return control["desired_state"] == "paused" or control.get(
            "stop_requested_for"
        ) == self.token

    def wait(self, seconds: float) -> bool:
        """Wait in small slices; return False as soon as stop is requested."""

        remaining = max(0.0, float(seconds))
        until_heartbeat = HEARTBEAT_INTERVAL_SECONDS
        while remaining > 0:
            if self.should_stop():
                return False
            step = min(0.5, remaining)
            self.controller.sleeper(step)
            remaining -= step
            until_heartbeat -= step
            if until_heartbeat <= 0:
                self.heartbeat("waiting", progress_detail="waiting for next cycle")
                until_heartbeat = HEARTBEAT_INTERVAL_SECONDS
        return not self.should_stop()

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        runtime = _read_json(self.controller.runtime_path)
        if runtime and runtime.get("token") == self.token:
            self.controller.runtime_path.unlink(missing_ok=True)
        lock = _read_json(self.controller.lock_path)
        if lock and lock.get("token") == self.token:
            self.controller.lock_path.unlink(missing_ok=True)

    def __enter__(self) -> "WorkerSession":
        return self

    def __exit__(self, _exc_type: Any, _exc: Any, _traceback: Any) -> None:
        self.close()


class WorkerController:
    """Persist user intent and manage one safe background worker instance."""

    def __init__(
        self,
        *,
        catalog_dir: Path,
        project_root: Path,
        config_path: Path,
        worker_config_path: Path,
        python_executable: Path = Path(sys.executable),
        process_identity: Callable[[int], dict[str, Any] | None] = process_identity,
        terminate_process: Callable[[dict[str, Any]], bool] = terminate_matching_process,
        popen: Callable[..., Any] = subprocess.Popen,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.time,
    ):
        self.catalog_dir = catalog_dir.resolve(strict=False)
        self.project_root = project_root.resolve(strict=False)
        self.config_path = config_path.resolve(strict=False)
        self.worker_config_path = worker_config_path.resolve(strict=False)
        self.python_executable = python_executable.resolve(strict=False)
        self.control_path = self.catalog_dir / "worker_control.json"
        self.runtime_path = self.catalog_dir / "worker_runtime.json"
        self.lock_path = self.catalog_dir / "worker_instance.lock"
        self.console_log_path = self.catalog_dir / "worker_console.log"
        self.process_identity = process_identity
        self.terminate_process = terminate_process
        self.popen = popen
        self.sleeper = sleeper
        self.clock = clock

    def _read_control(self) -> dict[str, Any]:
        loaded = _read_json(self.control_path)
        if not loaded or loaded.get("schema_version") != CONTROL_SCHEMA_VERSION:
            return {
                "schema_version": CONTROL_SCHEMA_VERSION,
                "desired_state": "enabled",
                "updated_at": None,
                "stop_requested_for": None,
            }
        desired = loaded.get("desired_state")
        if desired not in {"enabled", "paused"}:
            loaded["desired_state"] = "enabled"
        return loaded

    def _write_control(self, **changes: Any) -> dict[str, Any]:
        value = self._read_control()
        value.update(changes)
        value["schema_version"] = CONTROL_SCHEMA_VERSION
        value["updated_at"] = self.clock()
        _atomic_write_json(self.control_path, value)
        return value

    @staticmethod
    def _runtime_identity(runtime: dict[str, Any] | None) -> dict[str, Any] | None:
        if not runtime:
            return None
        try:
            return {
                "pid": int(runtime["pid"]),
                "executable": str(runtime["executable"]),
                "creation_time": runtime["creation_time"],
            }
        except (KeyError, TypeError, ValueError):
            return None

    def _runtime_is_live(self, runtime: dict[str, Any] | None) -> bool:
        expected = self._runtime_identity(runtime)
        return bool(
            expected
            and _same_identity(self.process_identity(int(expected["pid"])), expected)
        )

    def _clear_stale_runtime(self) -> None:
        runtime = _read_json(self.runtime_path)
        if not self._runtime_is_live(runtime):
            self.runtime_path.unlink(missing_ok=True)
        lock = _read_json(self.lock_path)
        if not self._runtime_is_live(lock):
            self.lock_path.unlink(missing_ok=True)

    def status(self) -> dict[str, Any]:
        control = self._read_control()
        runtime = _read_json(self.runtime_path)
        live = self._runtime_is_live(runtime)
        result: dict[str, Any] = {
            "schema_version": "1.0",
            "desired_state": control["desired_state"],
            "runtime_state": "running" if live else "stopped",
            "control_path": str(self.control_path),
            "runtime_path": str(self.runtime_path),
        }
        if runtime:
            result.update(
                {
                    "pid": runtime.get("pid"),
                    "started_at": runtime.get("started_at"),
                    "heartbeat_at": runtime.get("heartbeat_at"),
                    "updated_at": runtime.get("updated_at", runtime.get("heartbeat_at")),
                    "worker_status": runtime.get("worker_status"),
                    "current_path": runtime.get("current_path"),
                    "progress_current": runtime.get("progress_current", 0),
                    "progress_total": runtime.get("progress_total", 0),
                    "progress_percent": runtime.get("progress_percent"),
                    "progress_detail": runtime.get("progress_detail"),
                    "cycle_productive": runtime.get("cycle_productive"),
                    "next_wait_seconds": runtime.get("next_wait_seconds"),
                    "next_wake_reason": runtime.get("next_wake_reason"),
                    "next_wake_at": runtime.get("next_wake_at"),
                    "stale_runtime": not live,
                }
            )
        return result

    def open_session(self) -> WorkerSession:
        if self._read_control()["desired_state"] == "paused":
            raise RuntimeError("source-catalog worker is paused")
        self._clear_stale_runtime()
        existing = _read_json(self.lock_path)
        if self._runtime_is_live(existing):
            raise RuntimeError("source-catalog worker is already running")
        token = uuid4().hex
        identity = self.process_identity(os.getpid())
        if not identity:
            raise RuntimeError("could not identify the worker process")
        started_at = self.clock()
        payload = {
            "schema_version": RUNTIME_SCHEMA_VERSION,
            "token": token,
            **identity,
            "project_root": str(self.project_root),
            "started_at": started_at,
            "heartbeat_at": started_at,
            "updated_at": started_at,
            "worker_status": "starting",
            "current_path": None,
            "progress_current": 0,
            "progress_total": 0,
            "progress_percent": None,
            "progress_detail": None,
            "cycle_productive": None,
            "next_wait_seconds": None,
            "next_wake_reason": None,
            "next_wake_at": None,
        }
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        try:
            descriptor = os.open(self.lock_path, flags)
        except FileExistsError as exc:
            raise RuntimeError("source-catalog worker is already running") from exc
        try:
            os.write(
                descriptor,
                (json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n").encode(
                    "utf-8"
                ),
            )
        finally:
            os.close(descriptor)
        try:
            _atomic_write_json(self.runtime_path, payload)
        except Exception:
            self.lock_path.unlink(missing_ok=True)
            raise
        return WorkerSession(self, token, identity)

    def stop(
        self, *, graceful_timeout_seconds: float = 5.0, force: bool = True
    ) -> dict[str, Any]:
        runtime = _read_json(self.runtime_path)
        if not self._runtime_is_live(runtime):
            self._clear_stale_runtime()
            return {**self.status(), "forced": False, "stop_requested": False}
        expected = self._runtime_identity(runtime)
        assert expected is not None
        self._write_control(stop_requested_for=runtime.get("token"))
        deadline = time.monotonic() + max(0.0, graceful_timeout_seconds)
        while time.monotonic() < deadline:
            if not self._runtime_is_live(runtime):
                break
            self.sleeper(min(0.2, max(0.0, deadline - time.monotonic())))
        forced = False
        if self._runtime_is_live(runtime) and force:
            current = self.process_identity(int(expected["pid"]))
            if _same_identity(current, expected):
                forced = bool(self.terminate_process(expected))
                if forced:
                    for _ in range(20):
                        if not self._runtime_is_live(runtime):
                            break
                        self.sleeper(0.1)
        if not self._runtime_is_live(runtime):
            self.runtime_path.unlink(missing_ok=True)
            self.lock_path.unlink(missing_ok=True)
        return {**self.status(), "forced": forced, "stop_requested": True}

    def pause(
        self, *, graceful_timeout_seconds: float = 5.0, force: bool = True
    ) -> dict[str, Any]:
        self._write_control(desired_state="paused")
        return self.stop(
            graceful_timeout_seconds=graceful_timeout_seconds,
            force=force,
        )

    def start(self, *, wait_seconds: float = 5.0, startup_delay_seconds: int = 0) -> dict[str, Any]:
        if self._read_control()["desired_state"] == "paused":
            return {**self.status(), "started": False, "reason": "paused; use resume"}
        current = self.status()
        if current["runtime_state"] == "running":
            return {**current, "started": False, "reason": "already_running"}
        self._clear_stale_runtime()
        command = [
            str(self.python_executable),
            "-m",
            "company_wiki.source_catalog.cli",
            "--config",
            str(self.config_path),
            "worker",
            "--worker-config",
            str(self.worker_config_path),
        ]
        if startup_delay_seconds > 0:
            command.extend(["--startup-delay-seconds", str(startup_delay_seconds)])
        self.console_log_path.parent.mkdir(parents=True, exist_ok=True)
        environment = os.environ.copy()
        environment["PYTHONUTF8"] = "1"
        creationflags = 0
        if os.name == "nt":
            creationflags = 0x08000000 | 0x00000008 | 0x00000200
        with self.console_log_path.open("a", encoding="utf-8", newline="\n") as log:
            process = self.popen(
                command,
                cwd=self.project_root,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                close_fds=True,
                creationflags=creationflags,
            )
        deadline = time.monotonic() + max(0.0, wait_seconds)
        status = self.status()
        while status["runtime_state"] != "running" and time.monotonic() < deadline:
            if getattr(process, "poll", lambda: None)() is not None:
                break
            self.sleeper(0.1)
            status = self.status()
        return {
            **status,
            "started": status["runtime_state"] == "running",
            "spawned_pid": getattr(process, "pid", None),
        }

    def resume(self, *, wait_seconds: float = 5.0) -> dict[str, Any]:
        self._write_control(desired_state="enabled", stop_requested_for=None)
        return self.start(wait_seconds=wait_seconds)


__all__ = [
    "WorkerController",
    "WorkerSession",
    "process_identity",
    "terminate_matching_process",
]
