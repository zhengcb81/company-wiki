"""A byte-range OS mutex shared by catalog and finite runtime owners."""

from contextlib import contextmanager
import math
import os
from pathlib import Path
import sys
import time
from typing import Iterator


class FileMutexLockedError(RuntimeError):
    """Another process holds this mutex; process death releases it automatically."""


@contextmanager
def os_file_mutex(path: Path, *, timeout_seconds: float = 10.0) -> Iterator[None]:
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError("mutex timeout must be finite and positive")
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    acquired = False
    try:
        if os.fstat(descriptor).st_size < 1:
            os.write(descriptor, b"\0")
            os.fsync(descriptor)
        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                os.lseek(descriptor, 0, os.SEEK_SET)
                if sys.platform == "win32":
                    import msvcrt
                    msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except OSError as exc:
                if time.monotonic() >= deadline:
                    raise FileMutexLockedError("runtime mutex is held") from exc
                time.sleep(min(0.05, max(0, deadline - time.monotonic())))
        yield
    finally:
        if acquired:
            try:
                os.lseek(descriptor, 0, os.SEEK_SET)
                if sys.platform == "win32":
                    import msvcrt
                    msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
            except OSError:
                pass
        os.close(descriptor)


__all__ = ["FileMutexLockedError", "os_file_mutex"]
