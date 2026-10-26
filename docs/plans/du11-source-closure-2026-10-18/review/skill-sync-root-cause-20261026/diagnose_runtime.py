"""Read-only Windows MIC diagnostic; never changes permissions or launches a writer."""
from __future__ import annotations

import ctypes as C
from ctypes import wintypes as W
import json
from pathlib import Path
import sys


def observe() -> dict:
    if sys.platform != "win32":
        return {"status": "not_windows", "executable": sys.executable}
    kernel = C.WinDLL("kernel32", use_last_error=True)
    security = C.WinDLL("advapi32", use_last_error=True)
    kernel.GetCurrentProcess.restype = W.HANDLE
    kernel.CloseHandle.argtypes = [W.HANDLE]
    kernel.LocalFree.argtypes = [C.c_void_p]
    security.OpenProcessToken.argtypes = [W.HANDLE, W.DWORD, C.POINTER(W.HANDLE)]
    security.GetTokenInformation.argtypes = [W.HANDLE, C.c_int, C.c_void_p, W.DWORD, C.POINTER(W.DWORD)]
    security.ConvertSidToStringSidW.argtypes = [C.c_void_p, C.POINTER(W.LPWSTR)]
    security.GetNamedSecurityInfoW.argtypes = [W.LPWSTR, W.DWORD, W.DWORD, C.c_void_p, C.c_void_p, C.c_void_p, C.c_void_p, C.POINTER(C.c_void_p)]
    security.GetNamedSecurityInfoW.restype = W.DWORD
    security.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = [C.c_void_p, W.DWORD, W.DWORD, C.POINTER(W.LPWSTR), C.POINTER(W.DWORD)]

    token = W.HANDLE()
    if not security.OpenProcessToken(kernel.GetCurrentProcess(), 8, C.byref(token)):
        raise C.WinError(C.get_last_error())
    try:
        length = W.DWORD()
        security.GetTokenInformation(token, 25, None, 0, C.byref(length))
        buffer = C.create_string_buffer(length.value)
        if not security.GetTokenInformation(token, 25, buffer, length, C.byref(length)):
            raise C.WinError(C.get_last_error())
        sid = C.cast(buffer, C.POINTER(C.c_void_p))[0]
        text = W.LPWSTR()
        if not security.ConvertSidToStringSidW(sid, C.byref(text)):
            raise C.WinError(C.get_last_error())
        try:
            integrity = text.value
        finally:
            kernel.LocalFree(text)
    finally:
        kernel.CloseHandle(token)

    labels = {}
    for path in [Path(sys.executable), Path(sys._base_executable), Path.home() / ".agents/skills/filing-fetch", Path.home() / ".codex/skills/filing-fetch"]:
        descriptor = C.c_void_p()
        error = security.GetNamedSecurityInfoW(str(path), 1, 0x10, None, None, None, None, C.byref(descriptor))
        if error:
            labels[str(path)] = {"query_error": error}
            continue
        try:
            text, length = W.LPWSTR(), W.DWORD()
            if not security.ConvertSecurityDescriptorToStringSecurityDescriptorW(descriptor, 1, 0x10, C.byref(text), C.byref(length)):
                raise C.WinError(C.get_last_error())
            try:
                labels[str(path)] = text.value or "implicit_medium"
            finally:
                kernel.LocalFree(text)
        finally:
            kernel.LocalFree(descriptor)
    return {"schema_version": "skill-sync-mic-observation/1", "executable": sys.executable, "base_executable": sys._base_executable, "process_integrity_sid": integrity, "labels": labels, "read_only": True}


if __name__ == "__main__":
    print(json.dumps(observe(), ensure_ascii=True, indent=2))
