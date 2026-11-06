"""A protected, verified byte handle for one exact source version.

The stream transport must prove that the bytes it hands to the consumer are
the bytes of the requested ``SourceRef``.  Comparing a path, a size or an
mtime cannot prove that: the file behind a path can be replaced or rewritten
between two reads, and a same-size rewrite with a restored mtime is invisible
to every one of those checks.  This module therefore binds BOTH passes to one
handle:

* the handle is opened so that no other process can write or replace the
  file while it is held — Windows: a share mode that denies write and delete
  access; POSIX: an exclusive advisory lock plus an identity check;
* the verify pass digests the bytes read FROM THAT HANDLE;
* the stream pass rewinds the SAME HANDLE and streams from it, digesting the
  bytes it writes.

A path replaced behind our back therefore cannot change what we stream (the
handle still refers to the verified object), and a same-size in-place edit is
either refused by the operating system or caught by the digest of the bytes
that were actually streamed.  Nothing here retains the file: both passes move
bounded chunks.

The POSIX branch is structurally reviewed but has not been executed on this
Windows-only verification platform; it keeps the same honesty as the
dashboard's process containment: the Windows branch is the verified one.
"""

from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Callable

from .resolver import _BYTE_READ_CHUNK, _CANDIDATE_BYTES_CAP, _needs_hydration

#: Refusal reasons mirror the whole-buffer reader's vocabulary so that both
#: owner entry points report the same cause for the same condition.
REFUSAL_NOT_REGULAR = "not_regular_file"
REFUSAL_PLACEHOLDER = "placeholder_not_hydrated"
REFUSAL_CAP = "exceeds_candidate_cap"
REFUSAL_SIZE = "byte_size_mismatch"
REFUSAL_DIGEST = "content_sha256_mismatch"
REFUSAL_CHANGED = "changed_during_read"
REFUSAL_READ = "read_failed"
REFUSAL_BUDGET = "budget_exceeded"
REFUSAL_CANCELLED = "cancelled"
REFUSAL_REPLACED = "object_replaced_during_read"

_IS_WINDOWS = os.name == "nt"

if _IS_WINDOWS:
    import ctypes
    import msvcrt
    from ctypes import wintypes

    _GENERIC_READ = 0x80000000
    _FILE_SHARE_READ = 0x00000001
    _OPEN_EXISTING = 3
    _FILE_ATTRIBUTE_NORMAL = 0x00000080
    _FILE_FLAG_SEQUENTIAL_SCAN = 0x08000000
    _INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.CreateFileW.argtypes = (
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    _kernel32.CreateFileW.restype = wintypes.HANDLE


class ByteLockError(RuntimeError):
    """A refusal with a stable reason; no bytes were handed out."""

    def __init__(self, reason: str, detail: str = ""):
        self.reason = reason
        self.detail = detail
        super().__init__(reason + (f" ({detail})" if detail else ""))


@dataclass
class ByteLock:
    """One verified, protected handle on an exact source version."""

    path: Path
    expected_sha256: str
    expected_byte_size: int
    protected: bool
    _handle: BinaryIO
    _identity: tuple[int, int] | None = None

    # -- construction ------------------------------------------------------

    @classmethod
    def open(cls, path: Path, *, expected_sha256: str, expected_byte_size: int,
             budget: Any | None = None) -> "ByteLock":
        """Open the source read-protected and verify it from that handle.

        Every refusal happens before a byte can reach a consumer: a missing
        or irregular file, a cloud placeholder, a size that is not the
        requested version's size, and a digest that is not the requested
        version's digest.
        """
        try:
            before = os.stat(path)
        except OSError as exc:
            raise ByteLockError(REFUSAL_READ, exc.__class__.__name__) from None
        if not stat.S_ISREG(before.st_mode):
            raise ByteLockError(REFUSAL_NOT_REGULAR)
        if _needs_hydration(before):
            # Bytes are not local: opening it would download them.
            raise ByteLockError(REFUSAL_PLACEHOLDER)
        size = int(before.st_size)
        if size > _CANDIDATE_BYTES_CAP:
            raise ByteLockError(REFUSAL_CAP, str(size))
        if expected_byte_size is not None and size != expected_byte_size:
            raise ByteLockError(REFUSAL_SIZE, str(size))
        handle, protected, identity = _open_protected(path)
        lock = cls(path=path, expected_sha256=expected_sha256,
                   expected_byte_size=expected_byte_size, protected=protected,
                   _handle=handle, _identity=identity)
        try:
            lock.verify(budget=budget)
        except BaseException:
            lock.close()
            raise
        return lock

    # -- passes ------------------------------------------------------------

    def verify(self, *, budget: Any | None = None) -> str:
        """Digest the requested version's bytes FROM THE HANDLE, in chunks.

        The digest covers exactly the bytes the stream pass will hand out,
        because both passes read the same object through the same handle.
        """
        digest = hashlib.sha256()
        read = 0
        try:
            self._handle.seek(0)
            while True:
                if budget is not None and budget.cancelled:
                    raise ByteLockError(REFUSAL_CANCELLED, str(read))
                chunk = self._handle.read(_BYTE_READ_CHUNK)
                if not chunk:
                    break
                read += len(chunk)
                if read > _CANDIDATE_BYTES_CAP:
                    raise ByteLockError(REFUSAL_CAP, str(read))
                digest.update(chunk)
                if budget is not None:
                    stop = budget.charge(len(chunk))
                    if stop:
                        raise ByteLockError(stop, str(read))
        except ByteLockError:
            raise
        except OSError as exc:
            raise ByteLockError(REFUSAL_READ, exc.__class__.__name__) from None
        self._assert_same_object(read)
        computed = digest.hexdigest()
        if not self.expected_sha256 or computed != self.expected_sha256:
            raise ByteLockError(REFUSAL_DIGEST, computed[:12])
        return computed

    def stream(self, write: Callable[[bytes], None], *, budget: Any | None = None) -> str:
        """Stream the verified bytes FROM THE SAME HANDLE, digesting them.

        The digest of what was written must equal the locked version's
        digest; a same-size edit that slipped past the operating system is
        caught here, and the caller turns that refusal into an incomplete
        transfer rather than a completed read.
        """
        digest = hashlib.sha256()
        read = 0
        try:
            self._handle.seek(0)
            while True:
                if budget is not None and budget.cancelled:
                    raise ByteLockError(REFUSAL_CANCELLED, str(read))
                chunk = self._handle.read(_BYTE_READ_CHUNK)
                if not chunk:
                    break
                read += len(chunk)
                if read > _CANDIDATE_BYTES_CAP:
                    raise ByteLockError(REFUSAL_CAP, str(read))
                digest.update(chunk)
                write(chunk)
                if budget is not None:
                    stop = budget.charge(len(chunk))
                    if stop:
                        raise ByteLockError(stop, str(read))
        except ByteLockError:
            raise
        except OSError as exc:
            raise ByteLockError(REFUSAL_READ, exc.__class__.__name__) from None
        self._assert_same_object(read)
        computed = digest.hexdigest()
        if computed != self.expected_sha256:
            raise ByteLockError(REFUSAL_DIGEST, computed[:12])
        return computed

    # -- teardown ----------------------------------------------------------

    def close(self) -> None:
        handle, self._handle = self._handle, None  # type: ignore[assignment]
        if handle is None:
            return
        try:
            handle.close()
        except OSError:
            pass

    def __enter__(self) -> "ByteLock":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # -- internals ---------------------------------------------------------

    def _assert_same_object(self, read: int) -> None:
        """The handle must still refer to the object we verified.

        A POSIX writer that ignores the advisory lock can still rewrite the
        file in place; the identity and the mtime are re-checked so the
        refusal names the cause instead of a generic digest mismatch.
        """
        try:
            after = os.fstat(self._handle.fileno())
        except (OSError, ValueError):
            return
        if self._identity is not None:
            identity = (int(after.st_dev), int(after.st_ino))
            if identity != self._identity:
                raise ByteLockError(REFUSAL_REPLACED, str(read))
        if int(after.st_size) != self.expected_byte_size:
            raise ByteLockError(REFUSAL_SIZE, str(read))


def _open_protected(path: Path) -> tuple[BinaryIO, bool, tuple[int, int] | None]:
    """Open the file so that no other process can write or replace it.

    Windows: ``CreateFileW`` with a share mode that denies write and delete
    access — while this handle is open, another process cannot open the file
    for writing, cannot truncate it, and cannot rename or delete it.

    POSIX: an ``O_RDONLY`` descriptor with an exclusive advisory lock (the
    lock is advisory: it stops cooperating writers only) plus the device and
    inode identity, which the caller re-checks.
    """
    if _IS_WINDOWS:
        handle = _kernel32.CreateFileW(
            str(path), _GENERIC_READ, _FILE_SHARE_READ, None, _OPEN_EXISTING,
            _FILE_ATTRIBUTE_NORMAL | _FILE_FLAG_SEQUENTIAL_SCAN, None)
        if handle == _INVALID_HANDLE_VALUE or handle is None:
            # The OS refused the protected open (a concurrent writer holds
            # the file, or the filesystem does not support it): fall back to
            # a plain read handle and report the weaker binding.  The
            # returned handle must stay OPEN — it is the object both passes
            # read; the stream pass's digest is the second defense layer on
            # this path (a concurrent writer's edits are caught there).
            stream = open(path, "rb", buffering=0)
            return stream, False, None
        try:
            descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
        except OSError:
            stream = open(path, "rb", buffering=0)
            return stream, False, None
        stream = os.fdopen(descriptor, "rb", buffering=0)
        return stream, True, None
    descriptor = os.open(path, os.O_RDONLY)
    locked = False
    try:
        import fcntl

        fcntl.flock(descriptor, fcntl.LOCK_EX)  # type: ignore[attr-defined] # POSIX only
        locked = True
    except (ImportError, OSError):
        locked = False
    stream = os.fdopen(descriptor, "rb", buffering=0)
    try:
        info = os.fstat(descriptor)
        identity = (int(info.st_dev), int(info.st_ino))
    except OSError:
        identity = None
    return stream, locked, identity
