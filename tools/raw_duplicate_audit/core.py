"""Read-only measurement primitives for the N5-RAW-DUP duplicate audit.

Everything in this package is read-only with respect to catalog, configuration
and raw originals: the tool streams bytes only to compute SHA-256 digests and
never writes, moves, links or deletes an original file.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Iterator

REPORT_SCHEMA = "raw-duplicate-assessment/1"
LOCAL_PATHS_SCHEMA = "raw-duplicate-assessment-local-paths/1"

MAX_GROUPS_DEFAULT = 100
MAX_READ_BYTES_DEFAULT = 512 * 1024 * 1024
DEADLINE_SECONDS_DEFAULT = 300.0
MAX_DETAIL_ROWS_DEFAULT = 5000
MAX_REPORT_BYTES = 1024 * 1024
HASH_CHUNK_BYTES = 1 << 20
RECOMMENDATION_MIN_BENEFIT_BYTES = 256 * 1024 * 1024

LIMIT_HIT_READ_BYTES = "read_bytes"
LIMIT_HIT_DEADLINE = "deadline"
LIMIT_HIT_MAX_GROUPS = "max_groups"
LIMIT_HIT_DETAIL_ROWS = "detail_rows"
LIMIT_HIT_REPORT_BYTES = "report_bytes"

FILE_ATTRIBUTE_REPARSE_POINT = 0x400
FILE_ATTRIBUTE_OFFLINE = 0x1000
FILE_ATTRIBUTE_RECALL_ON_OPEN = 0x40000
FILE_ATTRIBUTE_UNPINNED = 0x100000
FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x400000
HYDRATE_RISK_MASK = (
    FILE_ATTRIBUTE_OFFLINE
    | FILE_ATTRIBUTE_RECALL_ON_OPEN
    | FILE_ATTRIBUTE_UNPINNED
    | FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS
)


class BudgetExceeded(RuntimeError):
    """Raised when the read budget or the wall-clock deadline is exhausted."""

    def __init__(self, reason: str, message: str = "") -> None:
        super().__init__(message or reason)
        self.reason = reason


class Budget:
    """Streaming read budget: byte cap plus deadline, checked while reading."""

    def __init__(
        self,
        *,
        max_read_bytes: int,
        deadline_seconds: float,
        clock=time.monotonic,
    ) -> None:
        self.max_read_bytes = int(max_read_bytes)
        self.deadline_seconds = float(deadline_seconds)
        self._clock = clock
        self._started = clock()
        self.read_bytes = 0
        self.read_files = 0
        self._hits: list[str] = []

    def elapsed_seconds(self) -> float:
        return self._clock() - self._started

    def remaining_seconds(self) -> float:
        return max(0.0, self.deadline_seconds - self.elapsed_seconds())

    def mark_hit(self, reason: str) -> None:
        if reason not in self._hits:
            self._hits.append(reason)

    def limits_hit(self) -> list[str]:
        return list(self._hits)

    def consume_deadline(self) -> None:
        if self.elapsed_seconds() >= self.deadline_seconds:
            self.mark_hit(LIMIT_HIT_DEADLINE)
            raise BudgetExceeded(LIMIT_HIT_DEADLINE)

    def consume(self, nbytes: int) -> None:
        self.read_bytes += int(nbytes)
        if self.read_bytes > self.max_read_bytes:
            self.mark_hit(LIMIT_HIT_READ_BYTES)
            raise BudgetExceeded(LIMIT_HIT_READ_BYTES)

    def guard_remaining(self) -> None:
        if self.read_bytes >= self.max_read_bytes:
            self.mark_hit(LIMIT_HIT_READ_BYTES)
            raise BudgetExceeded(LIMIT_HIT_READ_BYTES)


def iter_chunks(
    handle: IO[bytes], chunk_size: int = HASH_CHUNK_BYTES
) -> Iterator[bytes]:
    while True:
        data = handle.read(chunk_size)
        if not data:
            return
        yield data


def hash_file(path: Path, budget: Budget, *, chunk_size: int = HASH_CHUNK_BYTES) -> str:
    """Stream SHA-256 over ``path`` in ``chunk_size`` pieces under ``budget``."""
    budget.consume_deadline()
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            budget.consume_deadline()
            budget.guard_remaining()
            data = handle.read(chunk_size)
            if not data:
                break
            budget.consume(len(data))
            digest.update(data)
    budget.read_files += 1
    return digest.hexdigest()


def sha256_file(path: Path, *, chunk_size: int = HASH_CHUNK_BYTES) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for data in iter_chunks(handle, chunk_size):
            digest.update(data)
    return digest.hexdigest()


def utc_now_text(moment: datetime | None = None) -> str:
    stamp = moment if moment is not None else datetime.now(UTC)
    return stamp.strftime("%Y-%m-%dT%H:%M:%SZ")


def normalized(path: Path) -> Path:
    """Case- and reparse-normalized absolute identity (Windows-safe)."""
    return Path(os.path.normcase(os.path.realpath(str(path))))


def directed_inside(child: Path, root: Path) -> bool:
    child_real, root_real = normalized(child), normalized(root)
    try:
        child_real.relative_to(root_real)
    except ValueError:
        return False
    return child_real != root_real


def paths_overlap(left: Path, right: Path) -> bool:
    left_real, right_real = normalized(left), normalized(right)
    if left_real == right_real:
        return True
    for candidate, other in ((left_real, right_real), (right_real, left_real)):
        try:
            candidate.relative_to(other)
        except ValueError:
            continue
        else:
            return True
    return False


def file_attributes(path: Path) -> int | None:
    try:
        return getattr(os.lstat(path), "st_file_attributes", None)
    except OSError:
        return None


def hydrate_risk(path: Path) -> bool:
    """True when reading the file could trigger a cloud placeholder download."""
    attributes = file_attributes(path)
    if attributes is None:
        return False
    return bool(attributes & HYDRATE_RISK_MASK)


def physical_identity(path: Path) -> tuple[int, int] | None:
    try:
        stat_result = os.stat(path)
    except OSError:
        return None
    inode = getattr(stat_result, "st_ino", 0) or 0
    if not inode:
        return None
    return (int(stat_result.st_dev), int(inode))


def allocation_size(path: Path) -> int | None:
    """On-disk allocated bytes, or None when the platform cannot report them."""
    text = str(Path(path))
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            high = wintypes.DWORD(0)
            kernel32 = ctypes.windll.kernel32
            low = kernel32.GetCompressedFileSizeW(
                ctypes.c_wchar_p(text), ctypes.byref(high)
            )
            if low == 0xFFFFFFFF:
                error = kernel32.GetLastError()
                if error:
                    return None
            return (int(high.value) << 32) | int(low)
        except Exception:  # pragma: no cover - platform specific best effort
            return None
    try:
        stat_result = os.stat(text)
    except OSError:
        return None
    blocks = getattr(stat_result, "st_blocks", None)
    if blocks is None:
        return None
    return int(blocks) * 512


def write_json(path: Path, payload: dict, *, overwrite: bool = False) -> Path:
    """Atomic write; refuses to clobber an unknown pre-existing file."""
    target = Path(path)
    if target.exists() and not overwrite:
        raise FileExistsError(str(target))
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_bytes(
        json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True).encode(
            "utf-8"
        )
    )
    os.replace(tmp, target)
    return target


def report_is_ours(path: Path, schema: str = REPORT_SCHEMA) -> bool:
    """True when ``path`` already holds a report written by this tool."""
    target = Path(path)
    if not target.is_file():
        return False
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(payload, dict):
        return False
    return payload.get("schema_version") == schema
