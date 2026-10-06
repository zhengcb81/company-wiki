"""Read-only measurement primitives for the N6-FOOTPRINT storage scan.

Everything here is metadata-only with respect to the scanned tree: entries are
observed through ``lstat``-style calls, never opened. Physical (allocated) byte
counts stay ``None`` because this lane has no evidenced metadata-only
allocation API; logical sizes are never relabelled as disk allocation.
"""

from __future__ import annotations

import json
import os
import stat as stat_module
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

REPORT_SCHEMA = "cwp-storage-footprint/1"
MAX_REPORT_BYTES = 256 * 1024
MAX_ERROR_ITEMS = 200
MAX_SKIPPED_SAMPLES = 20
MAX_PATH_CHARS = 300
MAX_TOP_DIRECTORIES = 25
MAX_REASON_CHARS = 500

PATH_TRUNCATION_MARKER = "...[truncated]"

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
    """Raised when the file budget or the wall-clock deadline is exhausted."""

    def __init__(self, reason: str, message: str = "") -> None:
        super().__init__(message or reason)
        self.reason = reason


class ReportTooLarge(RuntimeError):
    """Raised when a report still exceeds the byte budget after truncation."""


def error_label(error: BaseException) -> str:
    """Static diagnostic: type name plus errno, never an OS filename."""
    number = getattr(error, "errno", None)
    suffix = f"(errno={number})" if isinstance(number, int) else ""
    return type(error).__name__ + suffix


class ScanBudget:
    """File-count cap plus deadline, checked at operation boundaries."""

    def __init__(
        self,
        *,
        max_files: int,
        max_seconds: float,
        clock=time.monotonic,
    ) -> None:
        self.max_files = int(max_files)
        self.max_seconds = float(max_seconds)
        self._clock = clock
        self._started = clock()
        self.files_seen = 0

    def check_deadline(self) -> None:
        if self._clock() - self._started >= self.max_seconds:
            raise BudgetExceeded("max_seconds")

    def consume_file(self) -> None:
        if self.files_seen >= self.max_files:
            raise BudgetExceeded("max_files")
        self.files_seen += 1


def entry_state(st: object, name: str) -> str | None:
    """``None`` for an ordinary entry, ``reparse``/``cloud`` when skipped.

    Reparse points (symlinks, junctions) and cloud placeholders are never
    followed and never hydrated: the caller records them as unmeasured
    skipped entries instead of stat-ing or reading the target.
    """
    del name
    attributes = getattr(st, "st_file_attributes", None)
    if attributes is None:
        if stat_module.S_ISLNK(getattr(st, "st_mode", 0)):
            return "reparse"
        return None
    if attributes & HYDRATE_RISK_MASK:
        return "cloud"
    if attributes & FILE_ATTRIBUTE_REPARSE_POINT:
        return "reparse"
    return None


def file_identity(st: object) -> tuple[int, int] | None:
    """Metadata file identity ``(st_dev, st_ino)``, or ``None`` when unknown."""
    inode = getattr(st, "st_ino", 0) or 0
    if not inode:
        return None
    device = getattr(st, "st_dev", 0) or 0
    return (int(device), int(inode))


def normalized(path: Path) -> Path:
    return Path(os.path.normcase(os.path.realpath(str(path))))


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


def utc_now_text(moment: datetime | None = None) -> str:
    stamp = moment if moment is not None else datetime.now(UTC)
    return stamp.strftime("%Y-%m-%dT%H:%M:%SZ")


def truncate_path(text: str) -> str:
    if len(text) <= MAX_PATH_CHARS:
        return text
    keep = MAX_PATH_CHARS - len(PATH_TRUNCATION_MARKER)
    return text[:keep] + PATH_TRUNCATION_MARKER


def serialize(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=1).encode("utf-8")


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


def write_report(path: Path, payload: dict, *, max_bytes: int | None = None) -> Path:
    """Atomic write that never clobbers an unknown pre-existing file."""
    limit = MAX_REPORT_BYTES if max_bytes is None else int(max_bytes)
    target = Path(path)
    if target.exists() and not report_is_ours(target):
        raise FileExistsError(str(target))
    data = serialize(payload)
    if len(data) > limit:
        raise ReportTooLarge(f"report is {len(data)} bytes, budget is {limit}")
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=target.parent,
            prefix=".n6-footprint-",
            suffix=".tmp",
            delete=False,
        ) as handle:
            tmp = Path(handle.name)
            handle.write(data)
        os.replace(tmp, target)
    finally:
        if tmp is not None and tmp.exists():
            tmp.unlink()
    return target
