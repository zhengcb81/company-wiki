"""Cross-process single-writer lock for source-catalog operations."""

from __future__ import annotations

from contextlib import AbstractContextManager, contextmanager
import ctypes
from ctypes import wintypes
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Iterator
import uuid


class CatalogOperationLockedError(RuntimeError):
    """Raised when another live catalog writer owns the operation lock."""


@contextmanager
def _acquisition_mutex(path: Path, *, timeout_seconds: float = 10.0) -> Iterator[None]:
    """Serialize lock-file create/takeover without introducing another PID lock."""

    guard_path = path.with_name(path.name + ".acquire")
    descriptor = os.open(guard_path, os.O_CREAT | os.O_RDWR, 0o600)
    acquired = False
    try:
        if os.fstat(descriptor).st_size < 1:
            os.write(descriptor, b"\0")
            os.fsync(descriptor)
        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                os.lseek(descriptor, 0, os.SEEK_SET)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except OSError as exc:
                if time.monotonic() >= deadline:
                    raise CatalogOperationLockedError(
                        "timed out serializing catalog lock acquisition"
                    ) from exc
                time.sleep(0.05)
        yield
    finally:
        if acquired:
            try:
                os.lseek(descriptor, 0, os.SEEK_SET)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(descriptor, fcntl.LOCK_UN)
            except OSError:
                pass
        os.close(descriptor)


def _windows_creation_time_via_cim(pid: int) -> float | None:
    powershell = (
        Path(os.environ.get("WINDIR", r"C:\Windows"))
        / "System32"
        / "WindowsPowerShell"
        / "v1.0"
        / "powershell.exe"
    )
    command = (
        f"$p=Get-CimInstance Win32_Process -Filter 'ProcessId = {int(pid)}' "
        "-ErrorAction Stop; if($null -ne $p.CreationDate){"
        "[Console]::Out.Write($p.CreationDate.ToUniversalTime().ToString('o'))}"
    )
    try:
        result = subprocess.run(
            [
                str(powershell),
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                command,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8-sig",
            errors="replace",
            timeout=5,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    value = result.stdout.strip()
    if result.returncode != 0 or not value:
        return None
    try:
        return round(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp(), 6)
    except ValueError:
        return None


def _process_identity(pid: int) -> dict[str, object]:
    if pid <= 0:
        return {
            "live": False,
            "creation_time": None,
            "executable": None,
            "verification": "not_live",
        }
    if os.name == "nt":
        process_query_limited_information = 0x1000
        still_active = 259
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = (ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32)
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.GetExitCodeProcess.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32))
        kernel32.GetExitCodeProcess.restype = ctypes.c_int
        kernel32.GetProcessTimes.argtypes = (
            ctypes.c_void_p,
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
        )
        kernel32.GetProcessTimes.restype = ctypes.c_int
        kernel32.QueryFullProcessImageNameW.argtypes = (
            ctypes.c_void_p,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        )
        kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
        kernel32.CloseHandle.restype = ctypes.c_int
        handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
        if not handle:
            live = ctypes.get_last_error() == 5
            creation_time = _windows_creation_time_via_cim(pid) if live else None
            return {
                "live": live,
                "creation_time": creation_time,
                "executable": None,
                "verification": (
                    "verified_cim"
                    if creation_time is not None
                    else "unavailable"
                    if live
                    else "not_live"
                ),
            }
        try:
            exit_code = ctypes.c_uint32()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return {
                    "live": True,
                    "creation_time": None,
                    "executable": None,
                    "verification": "unavailable",
                }
            if exit_code.value != still_active:
                return {
                    "live": False,
                    "creation_time": None,
                    "executable": None,
                    "verification": "not_live",
                }
            creation = wintypes.FILETIME()
            exit_time = wintypes.FILETIME()
            kernel_time = wintypes.FILETIME()
            user_time = wintypes.FILETIME()
            creation_time: float | None = None
            if kernel32.GetProcessTimes(
                handle,
                ctypes.byref(creation),
                ctypes.byref(exit_time),
                ctypes.byref(kernel_time),
                ctypes.byref(user_time),
            ):
                ticks = (int(creation.dwHighDateTime) << 32) | int(
                    creation.dwLowDateTime
                )
                creation_time = round(
                    (ticks - 116_444_736_000_000_000) / 10_000_000,
                    6,
                )
            size = wintypes.DWORD(32768)
            buffer = ctypes.create_unicode_buffer(size.value)
            executable = None
            if kernel32.QueryFullProcessImageNameW(
                handle, 0, buffer, ctypes.byref(size)
            ):
                executable = os.path.normcase(os.path.abspath(buffer.value))
            return {
                "live": True,
                "creation_time": creation_time,
                "executable": executable,
                "verification": (
                    "verified" if creation_time is not None else "unavailable"
                ),
            }
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return {
            "live": False,
            "creation_time": None,
            "executable": None,
            "verification": "not_live",
        }
    except PermissionError:
        return {
            "live": True,
            "creation_time": None,
            "executable": None,
            "verification": "unavailable",
        }
    creation_time = None
    executable = None
    try:
        stat_text = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        fields = stat_text[stat_text.rfind(")") + 2 :].split()
        start_ticks = int(fields[19])
        clock_ticks = int(os.sysconf("SC_CLK_TCK"))
        boot_line = next(
            line
            for line in Path("/proc/stat").read_text(encoding="utf-8").splitlines()
            if line.startswith("btime ")
        )
        creation_time = round(
            float(boot_line.split()[1]) + start_ticks / clock_ticks,
            6,
        )
        executable = os.path.normcase(os.path.abspath(os.readlink(f"/proc/{pid}/exe")))
    except (OSError, StopIteration, ValueError, IndexError):
        pass
    return {
        "live": True,
        "creation_time": creation_time,
        "executable": executable,
        "verification": "verified" if creation_time is not None else "unavailable",
    }


def _pid_is_live(pid: int) -> bool:
    return bool(_process_identity(pid)["live"])


def _owner_status(path: Path, payload: dict[str, object]) -> dict[str, object]:
    try:
        pid = int(payload.get("pid", 0))
    except (TypeError, ValueError):
        pid = 0
    identity = _process_identity(pid)
    if not identity["live"]:
        state = "stale"
        verification = "not_live"
    elif "process_creation_time" in payload:
        try:
            recorded_creation = float(payload["process_creation_time"])
        except (TypeError, ValueError):
            recorded_creation = None
        observed_creation = identity.get("creation_time")
        if recorded_creation is None:
            state = "live"
            verification = "invalid_recorded_identity"
        elif observed_creation is None:
            state = "live"
            verification = "unavailable"
        elif abs(recorded_creation - float(observed_creation)) <= 0.001:
            state = "live"
            verification = "matched"
        else:
            state = "stale"
            verification = "mismatch"
    else:
        observed_creation = identity.get("creation_time")
        try:
            lock_created_at = path.stat().st_mtime
        except OSError:
            lock_created_at = None
        if observed_creation is None or lock_created_at is None:
            state = "live"
            verification = "legacy_unverified"
        elif float(observed_creation) > float(lock_created_at) + 0.001:
            state = "stale"
            verification = "legacy_pid_reused"
        else:
            state = "live"
            verification = "legacy_consistent"
    return {
        "state": state,
        "pid": pid or None,
        "identity_verification": verification,
        "process_creation_time": payload.get("process_creation_time"),
        "observed_process_creation_time": identity.get("creation_time"),
    }


def _remove_if_unchanged(path: Path, expected_text: str) -> bool:
    try:
        if path.read_text(encoding="utf-8") != expected_text:
            return False
        path.unlink()
        return True
    except FileNotFoundError:
        return True
    except OSError:
        return False


def operation_lock_status(catalog_dir: Path) -> dict[str, object]:
    """Describe the operation lock without changing or exposing its token."""

    path = catalog_dir / "operation.lock"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {
            "state": "absent",
            "pid": None,
            "operation": None,
            "identity_verification": "absent",
            "process_creation_time": None,
            "observed_process_creation_time": None,
        }
    except (OSError, json.JSONDecodeError):
        return {
            "state": "invalid",
            "pid": None,
            "operation": None,
            "identity_verification": "invalid",
            "process_creation_time": None,
            "observed_process_creation_time": None,
        }
    operation = payload.get("operation")
    if not isinstance(operation, str) or not operation:
        operation = None
    return {**_owner_status(path, payload), "operation": operation}


class CatalogOperationLock(AbstractContextManager["CatalogOperationLock"]):
    def __init__(self, catalog_dir: Path, *, operation: str):
        self.path = catalog_dir / "operation.lock"
        self.operation = operation
        self.token = uuid.uuid4().hex
        self._owned = False

    def __enter__(self) -> "CatalogOperationLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        identity = _process_identity(os.getpid())
        payload = {
            "pid": os.getpid(),
            "operation": self.operation,
            "token": self.token,
        }
        if identity.get("creation_time") is not None:
            payload["process_creation_time"] = identity["creation_time"]
        if identity.get("executable"):
            payload["executable"] = identity["executable"]
        with _acquisition_mutex(self.path):
            for attempt in range(3):
                try:
                    descriptor = os.open(
                        self.path,
                        os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    )
                except FileExistsError:
                    try:
                        existing_text = self.path.read_text(encoding="utf-8")
                        existing = json.loads(existing_text)
                    except (OSError, ValueError, TypeError, json.JSONDecodeError):
                        try:
                            existing_text = self.path.read_text(encoding="utf-8")
                        except OSError:
                            existing_text = ""
                        existing = {}
                    owner = _owner_status(self.path, existing)
                    if owner["state"] == "live":
                        raise CatalogOperationLockedError(
                            f"catalog operation already running: pid={owner['pid']}"
                        )
                    if attempt < 2 and _remove_if_unchanged(
                        self.path, existing_text
                    ):
                        continue
                    raise CatalogOperationLockedError(
                        "unable to replace stale catalog lock"
                    )
                else:
                    with os.fdopen(
                        descriptor, "w", encoding="utf-8", newline="\n"
                    ) as stream:
                        json.dump(payload, stream, ensure_ascii=False, sort_keys=True)
                        stream.write("\n")
                    self._owned = True
                    return self
        raise CatalogOperationLockedError("unable to acquire catalog lock")

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if not self._owned:
            return None
        with _acquisition_mutex(self.path):
            try:
                existing = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                existing = {}
            if existing.get("token") == self.token:
                self.path.unlink(missing_ok=True)
        self._owned = False
        return None


__all__ = [
    "CatalogOperationLock",
    "CatalogOperationLockedError",
    "operation_lock_status",
]
