"""Import-safe resource observations and explicit Windows-only job memory limit.

Actual inference requires the existing shared WindowsJob owner. Pure metrics,
cache and argument-validation tools remain usable without Windows DLLs.
"""
from __future__ import annotations

import ctypes
import sys
from pathlib import Path
from typing import Any

GIB = 1024 ** 3


class MemoryLimitUnavailable(RuntimeError):
    """The host cannot enforce this experiment's committed-memory contract."""


def memory_limit_capability() -> dict:
    supported = sys.platform == "win32"
    return {"supported": supported,
            "mechanism": "windows-job-total-commit" if supported else None,
            "reason": None if supported else "committed-memory enforcement requires Windows Job Objects"}


def require_memory_limit() -> None:
    capability = memory_limit_capability()
    if not capability["supported"]:
        raise MemoryLimitUnavailable(capability["reason"])


def _unknown_snapshot(reason: str) -> dict:
    return {"memory_load_pct": None, "total_phys_bytes": None,
            "avail_phys_bytes": None, "commit_free_bytes": None,
            "observation_source": None, "reason": reason}


def _linux_memory_snapshot(path: Path) -> dict:
    """Observe /proc/meminfo; no memory enforcement is implied."""
    try:
        values = {}
        for line in path.read_text(encoding="ascii").splitlines():
            key, _, value = line.partition(":")
            fields = value.split()
            if len(fields) == 2 and fields[1] == "kB":
                values[key] = int(fields[0]) * 1024
        total, available = values.get("MemTotal"), values.get("MemAvailable")
        limit, committed = values.get("CommitLimit"), values.get("Committed_AS")
        return {"memory_load_pct": 100 * (total - available) / total
                if total and available is not None else None,
                "total_phys_bytes": total, "avail_phys_bytes": available,
                "commit_free_bytes": max(0, limit - committed)
                if limit is not None and committed is not None else None,
                "observation_source": "/proc/meminfo",
                "reason": None if available is not None else "MemAvailable not reported"}
    except (OSError, ValueError):
        return _unknown_snapshot("/proc/meminfo unavailable or malformed")


def host_memory_snapshot() -> dict:
    if sys.platform == "linux":
        return _linux_memory_snapshot(Path("/proc/meminfo"))
    if sys.platform != "win32":
        return _unknown_snapshot(f"memory observation unavailable on {sys.platform}")

    # DLL loading belongs to this Windows observation call, never module import.
    class MemoryStatusEx(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    query = kernel.GlobalMemoryStatusEx
    query.argtypes, query.restype = [ctypes.POINTER(MemoryStatusEx)], ctypes.c_int
    status = MemoryStatusEx()
    status.dwLength = ctypes.sizeof(status)
    if not query(ctypes.byref(status)):
        raise OSError(ctypes.get_last_error(), "GlobalMemoryStatusEx failed")
    return {"memory_load_pct": int(status.dwMemoryLoad),
            "total_phys_bytes": int(status.ullTotalPhys),
            "avail_phys_bytes": int(status.ullAvailPhys),
            "commit_free_bytes": int(status.ullAvailPageFile),
            "observation_source": "GlobalMemoryStatusEx", "reason": None}


def card_memory_cap_bytes(avail_phys_bytes: int | None) -> int:
    if type(avail_phys_bytes) is not int or avail_phys_bytes <= 0:
        raise MemoryLimitUnavailable("available physical memory is unknown or zero; cannot derive card cap")
    return min(8 * GIB, avail_phys_bytes // 2)


def self_peak_commit_bytes() -> int | None:
    if sys.platform != "win32":
        return None
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise OSError(ctypes.get_last_error(), "GetProcessMemoryInfo failed")
    return int(counters.PeakPagefileUsage)


class JobMemoryLimit:
    """Adapt the shared process-tree owner; aggregate job cap is stricter.

    No fallback to an unbounded process is provided on unsupported platforms.
    The original Popen handle is assigned, avoiding PID-reopen ownership races.
    """
    def __init__(self, limit_bytes: int):
        if type(limit_bytes) is not int or limit_bytes <= 0:
            raise ValueError("limit_bytes must be a positive integer")
        require_memory_limit()
        self.limit_bytes = limit_bytes
        self._owner: Any = None

    def assign(self, process) -> None:
        from company_wiki._process_tree import WindowsJob

        self._owner = WindowsJob(int(process._handle), memory_limit_bytes=self.limit_bytes)

    def peak_process_bytes(self) -> int:
        if self._owner is None:
            raise RuntimeError("no process assigned to memory owner")
        return self._owner.peak_commit_bytes()

    def terminate(self) -> None:
        if self._owner is not None:
            self._owner.terminate()

    def close(self) -> None:
        if self._owner is not None:
            self._owner.close()
            self._owner = None
