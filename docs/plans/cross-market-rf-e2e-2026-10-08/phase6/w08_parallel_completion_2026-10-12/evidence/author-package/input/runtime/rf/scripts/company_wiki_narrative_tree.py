"""Contain only the producer tree created by the narrative subprocess port."""
from __future__ import annotations

import ctypes
import os
import signal
import sys
from typing import Any, Protocol
import threading


class _ProcessHandle(Protocol):
    pid: int


class ProcessTree:
    def __init__(self) -> None:
        self._pid: int | None = None
        self._job: Any = None
        if sys.platform == "win32":
            self._job = _WindowsJob()

    @property
    def creationflags(self) -> int:
        # CREATE_NO_WINDOW | CREATE_SUSPENDED. Assignment precedes user code.
        return 0x08000004 if self._job is not None else 0

    @property
    def start_new_session(self) -> bool:
        return self._job is None

    def attach(self, process: _ProcessHandle) -> None:
        self._pid = process.pid
        if self._job is not None:
            self._job.assign_and_resume(process.pid)

    def terminate(self) -> None:
        if self._job is not None:
            self._job.terminate()
        elif sys.platform != "win32":
            if self._pid is not None:
                try:
                    os.killpg(self._pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    def close(self) -> None:
        if self._job is not None:
            self._job.close()


if sys.platform == "win32":
    class _WindowsJob:
        """Assign before user code runs; descendants inherit the anonymous job."""

        def __init__(self) -> None:
            from ctypes import wintypes as wt

            class BasicLimits(ctypes.Structure):
                _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64),
                            ("flags", wt.DWORD), ("min_ws", ctypes.c_size_t),
                            ("max_ws", ctypes.c_size_t), ("active_limit", wt.DWORD),
                            ("affinity", ctypes.c_size_t), ("priority", wt.DWORD),
                            ("scheduling", wt.DWORD)]

            class IoCounters(ctypes.Structure):
                _fields_ = [(name, ctypes.c_uint64) for name in
                            ("read_ops", "write_ops", "other_ops", "read_bytes", "write_bytes", "other_bytes")]

            class ExtendedLimits(ctypes.Structure):
                _fields_ = [("basic", BasicLimits), ("io", IoCounters),
                            ("process_memory", ctypes.c_size_t), ("job_memory", ctypes.c_size_t),
                            ("peak_process", ctypes.c_size_t), ("peak_job", ctypes.c_size_t)]

            class ThreadEntry(ctypes.Structure):
                _fields_ = [("size", wt.DWORD), ("usage", wt.DWORD), ("tid", wt.DWORD),
                            ("pid", wt.DWORD), ("priority", wt.LONG), ("delta", wt.LONG),
                            ("flags", wt.DWORD)]

            self._thread_entry = ThreadEntry
            self._api = ctypes.WinDLL("kernel32", use_last_error=True)
            signatures = {
                "CreateJobObjectW": ([wt.LPVOID, wt.LPCWSTR], wt.HANDLE),
                "SetInformationJobObject": ([wt.HANDLE, ctypes.c_int, wt.LPVOID, wt.DWORD], wt.BOOL),
                "AssignProcessToJobObject": ([wt.HANDLE, wt.HANDLE], wt.BOOL),
                "TerminateJobObject": ([wt.HANDLE, wt.UINT], wt.BOOL),
                "OpenProcess": ([wt.DWORD, wt.BOOL, wt.DWORD], wt.HANDLE),
                "CreateToolhelp32Snapshot": ([wt.DWORD, wt.DWORD], wt.HANDLE),
                "Thread32First": ([wt.HANDLE, ctypes.POINTER(ThreadEntry)], wt.BOOL),
                "Thread32Next": ([wt.HANDLE, ctypes.POINTER(ThreadEntry)], wt.BOOL),
                "OpenThread": ([wt.DWORD, wt.BOOL, wt.DWORD], wt.HANDLE),
                "ResumeThread": ([wt.HANDLE], wt.DWORD),
                "CloseHandle": ([wt.HANDLE], wt.BOOL),
            }
            for name, (arguments, result) in signatures.items():
                function = getattr(self._api, name)
                function.argtypes, function.restype = arguments, result
            self._lock = threading.Lock()
            self._handle = self._api.CreateJobObjectW(None, None)
            if not self._handle:
                raise ctypes.WinError(ctypes.get_last_error())
            limits = ExtendedLimits()
            limits.basic.flags = 0x00002000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not self._api.SetInformationJobObject(self._handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
                error = ctypes.WinError(ctypes.get_last_error())
                self.close()
                raise error

        def assign_and_resume(self, pid: int) -> None:
            # PROCESS_SET_QUOTA | PROCESS_TERMINATE, never an unrelated PID.
            process_handle = self._api.OpenProcess(0x0101, False, pid)
            if not process_handle:
                raise ctypes.WinError(ctypes.get_last_error())
            try:
                if not self._api.AssignProcessToJobObject(self._handle, process_handle):
                    raise ctypes.WinError(ctypes.get_last_error())
            finally:
                self._api.CloseHandle(process_handle)
            # Popen closes its initial thread handle; reopen only this suspended PID's
            # thread through public Win32 APIs, after containment is established.
            snapshot = self._api.CreateToolhelp32Snapshot(0x00000004, 0)
            if snapshot == ctypes.c_void_p(-1).value:
                raise ctypes.WinError(ctypes.get_last_error())
            resumed = False
            try:
                entry = self._thread_entry()
                entry.size = ctypes.sizeof(entry)
                valid = self._api.Thread32First(snapshot, ctypes.byref(entry))
                while valid:
                    if entry.pid == pid:
                        thread_handle = self._api.OpenThread(0x0002, False, entry.tid)
                        if not thread_handle:
                            raise ctypes.WinError(ctypes.get_last_error())
                        try:
                            if self._api.ResumeThread(thread_handle) == 0xFFFFFFFF:
                                raise ctypes.WinError(ctypes.get_last_error())
                            resumed = True
                        finally:
                            self._api.CloseHandle(thread_handle)
                    valid = self._api.Thread32Next(snapshot, ctypes.byref(entry))
                if not resumed:
                    raise OSError("producer suspended thread unavailable")
            finally:
                self._api.CloseHandle(snapshot)

        def terminate(self) -> None:
            with self._lock:
                if self._handle and not self._api.TerminateJobObject(self._handle, 1):
                    raise ctypes.WinError(ctypes.get_last_error())

        def close(self) -> None:
            with self._lock:
                if self._handle:
                    self._api.CloseHandle(self._handle)
                    self._handle = None
