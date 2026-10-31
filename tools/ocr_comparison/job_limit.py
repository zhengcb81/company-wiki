"""Windows Job Object memory limit for one experiment child process.

The limit is the card's definition of memory: committed (private) bytes of the
child process (JOB_OBJECT_LIMIT_PROCESS_MEMORY).  The operating system refuses
allocations past the limit, so a bound violation is an observed failure, never
a prediction.  The peak is read back from the job object after the run.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes

GIB = 1024 ** 3

_JobObjectExtendedLimitInformation = 9
_JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
_PROCESS_SET_QUOTA = 0x0100
_PROCESS_TERMINATE = 0x0001
_PROCESS_QUERY_INFORMATION = 0x0400

_HANDLE = ctypes.c_void_p


class _IOCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in (
        "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
        "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
    )]


class _BasicLimitInformation(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _ExtendedLimitInformation(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _BasicLimitInformation),
        ("IoInfo", _IOCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class _ProcessMemoryCounters(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
    ]


class _MemoryStatusEx(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
_k32.CreateJobObjectW.restype = _HANDLE
_k32.SetInformationJobObject.argtypes = [_HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
_k32.SetInformationJobObject.restype = wintypes.BOOL
_k32.QueryInformationJobObject.argtypes = [_HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
_k32.QueryInformationJobObject.restype = wintypes.BOOL
_k32.AssignProcessToJobObject.argtypes = [_HANDLE, _HANDLE]
_k32.AssignProcessToJobObject.restype = wintypes.BOOL
_k32.TerminateJobObject.argtypes = [_HANDLE, wintypes.UINT]
_k32.TerminateJobObject.restype = wintypes.BOOL
_k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
_k32.OpenProcess.restype = _HANDLE
_k32.CloseHandle.argtypes = [_HANDLE]
_k32.CloseHandle.restype = wintypes.BOOL
_k32.GetCurrentProcess.restype = _HANDLE
_k32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(_MemoryStatusEx)]
_k32.GlobalMemoryStatusEx.restype = wintypes.BOOL

_psapi = ctypes.WinDLL("psapi", use_last_error=True)
_psapi.GetProcessMemoryInfo.argtypes = [_HANDLE, ctypes.POINTER(_ProcessMemoryCounters), wintypes.DWORD]
_psapi.GetProcessMemoryInfo.restype = wintypes.BOOL


def _check(ok: bool, what: str) -> None:
    if not ok:
        raise OSError(ctypes.get_last_error(), f"{what} failed")


def host_memory_snapshot() -> dict:
    status = _MemoryStatusEx()
    status.dwLength = ctypes.sizeof(_MemoryStatusEx)
    _check(_k32.GlobalMemoryStatusEx(ctypes.byref(status)), "GlobalMemoryStatusEx")
    return {
        "memory_load_pct": int(status.dwMemoryLoad),
        "total_phys_bytes": int(status.ullTotalPhys),
        "avail_phys_bytes": int(status.ullAvailPhys),
        "commit_free_bytes": int(status.ullAvailPageFile),
    }


def card_memory_cap_bytes(avail_phys_bytes: int) -> int:
    """Card bound: min(8 GiB committed, available RAM / 2), taken at run start."""
    return min(8 * GIB, avail_phys_bytes // 2)


def self_peak_commit_bytes() -> int:
    counters = _ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(_ProcessMemoryCounters)
    _check(_psapi.GetProcessMemoryInfo(_k32.GetCurrentProcess(), ctypes.byref(counters), counters.cb),
           "GetProcessMemoryInfo")
    return int(counters.PeakPagefileUsage)


class JobMemoryLimit:
    """A job object whose member processes may not commit more than limit_bytes."""

    def __init__(self, limit_bytes: int):
        if limit_bytes <= 0:
            raise ValueError("limit_bytes must be positive")
        self.limit_bytes = int(limit_bytes)
        handle = _k32.CreateJobObjectW(None, None)
        if not handle:
            raise OSError(ctypes.get_last_error(), "CreateJobObjectW failed")
        self._job = handle
        info = _ExtendedLimitInformation()
        info.BasicLimitInformation.LimitFlags = (
            _JOB_OBJECT_LIMIT_PROCESS_MEMORY | _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        )
        info.ProcessMemoryLimit = self.limit_bytes
        _check(
            _k32.SetInformationJobObject(self._job, _JobObjectExtendedLimitInformation,
                                         ctypes.byref(info), ctypes.sizeof(info)),
            "SetInformationJobObject",
        )

    def assign(self, pid: int) -> None:
        process = _k32.OpenProcess(_PROCESS_SET_QUOTA | _PROCESS_TERMINATE | _PROCESS_QUERY_INFORMATION,
                                   False, int(pid))
        if not process:
            raise OSError(ctypes.get_last_error(), "OpenProcess failed")
        try:
            _check(_k32.AssignProcessToJobObject(self._job, process), "AssignProcessToJobObject")
        finally:
            _k32.CloseHandle(process)

    def peak_process_bytes(self) -> int:
        info = _ExtendedLimitInformation()
        returned = wintypes.DWORD(0)
        _check(
            _k32.QueryInformationJobObject(self._job, _JobObjectExtendedLimitInformation,
                                           ctypes.byref(info), ctypes.sizeof(info), ctypes.byref(returned)),
            "QueryInformationJobObject",
        )
        return int(info.PeakProcessMemoryUsed)

    def terminate(self) -> None:
        _k32.TerminateJobObject(self._job, 1)

    def close(self) -> None:
        if self._job:
            _k32.CloseHandle(self._job)
            self._job = None
