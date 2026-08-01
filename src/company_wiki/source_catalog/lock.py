"""Cross-process single-writer lock for source-catalog operations."""

from __future__ import annotations

from contextlib import AbstractContextManager
import ctypes
import json
import os
from pathlib import Path
import uuid


class CatalogOperationLockedError(RuntimeError):
    """Raised when another live catalog writer owns the operation lock."""


def _pid_is_live(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        process_query_limited_information = 0x1000
        still_active = 259
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = (ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32)
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.GetExitCodeProcess.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32))
        kernel32.GetExitCodeProcess.restype = ctypes.c_int
        kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
        kernel32.CloseHandle.restype = ctypes.c_int
        handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
        if not handle:
            return ctypes.get_last_error() == 5  # Access denied still implies a live process.
        try:
            exit_code = ctypes.c_uint32()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return True
            return exit_code.value == still_active
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def operation_lock_status(catalog_dir: Path) -> dict[str, object]:
    """Describe the operation lock without changing or exposing its token."""

    path = catalog_dir / "operation.lock"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"state": "absent", "pid": None, "operation": None}
    except (OSError, json.JSONDecodeError):
        return {"state": "invalid", "pid": None, "operation": None}
    try:
        pid = int(payload.get("pid", 0))
    except (TypeError, ValueError):
        pid = 0
    operation = payload.get("operation")
    if not isinstance(operation, str) or not operation:
        operation = None
    return {
        "state": "live" if _pid_is_live(pid) else "stale",
        "pid": pid or None,
        "operation": operation,
    }


class CatalogOperationLock(AbstractContextManager["CatalogOperationLock"]):
    def __init__(self, catalog_dir: Path, *, operation: str):
        self.path = catalog_dir / "operation.lock"
        self.operation = operation
        self.token = uuid.uuid4().hex
        self._owned = False

    def __enter__(self) -> "CatalogOperationLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "pid": os.getpid(),
            "operation": self.operation,
            "token": self.token,
        }
        for attempt in range(2):
            try:
                descriptor = os.open(
                    self.path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                )
            except FileExistsError:
                try:
                    existing = json.loads(self.path.read_text(encoding="utf-8"))
                    owner_pid = int(existing.get("pid", 0))
                except (OSError, ValueError, TypeError, json.JSONDecodeError):
                    owner_pid = 0
                if _pid_is_live(owner_pid):
                    raise CatalogOperationLockedError(
                        f"catalog operation already running: pid={owner_pid}"
                    )
                if attempt == 0:
                    try:
                        self.path.unlink()
                    except FileNotFoundError:
                        pass
                    continue
                raise CatalogOperationLockedError("unable to replace stale catalog lock")
            else:
                with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                    json.dump(payload, stream, ensure_ascii=False, sort_keys=True)
                    stream.write("\n")
                self._owned = True
                return self
        raise CatalogOperationLockedError("unable to acquire catalog lock")

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if not self._owned:
            return None
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
