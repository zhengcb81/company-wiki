"""Restoration and resource accounting for benchmark runs.

Every run that touches the filesystem must be able to prove it left the world
as it found it:

- originals and production config: same SHA-256 and same mtime;
- any pre-existing sentinel file in the owned container: restored byte-identical
  with its mtime;
- files the run itself created: removed, except one small summary.

Nothing here deletes a directory the run did not create.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

SENTINEL_NAME = ".du-bench-sentinel.json"
OWNED_MARKER = ".du-bench-owned"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_fingerprint(path: Path) -> dict[str, Any]:
    target = Path(path)
    try:
        stat = target.stat()
    except OSError:
        return {"path": str(target), "exists": False}
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "path": str(target),
        "exists": True,
        "sha256": digest.hexdigest(),
        "mtime_ns": stat.st_mtime_ns,
        "size": stat.st_size,
    }


def fingerprint_many(paths: Iterable[Path]) -> dict[str, dict[str, Any]]:
    return {str(Path(path).resolve()): file_fingerprint(Path(path)) for path in paths}


def compare_fingerprints(
    before: Mapping[str, Mapping[str, Any]],
    after: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    changed: list[dict[str, Any]] = []
    for key, prior in before.items():
        current = after.get(key)
        if current is None:
            changed.append({"path": key, "reason": "missing_after"})
            continue
        if prior.get("exists") != current.get("exists"):
            changed.append({"path": key, "reason": "existence_changed"})
            continue
        if not prior.get("exists"):
            continue
        if prior.get("sha256") != current.get("sha256"):
            changed.append({"path": key, "reason": "sha256_changed"})
        if prior.get("mtime_ns") != current.get("mtime_ns"):
            changed.append({"path": key, "reason": "mtime_changed"})
    return {"unchanged": not changed, "changes": changed, "count": len(before)}


def install_sentinel(
    container: Path,
    payload: Mapping[str, Any] | None = None,
    *,
    preserve_existing: bool = False,
) -> dict[str, Any]:
    """Write a sentinel into a container the benchmark owns.

    With ``preserve_existing`` the current bytes and mtime of an existing
    sentinel are captured first and reported in ``preexisting``; the caller is
    then responsible for calling :func:`restore_sentinel`, which puts the
    original bytes and mtime back. Without it the sentinel is simply written.
    """

    root = Path(container)
    root.mkdir(parents=True, exist_ok=True)
    sentinel = root / SENTINEL_NAME

    preexisting: dict[str, Any] = {"exists": False}
    if preserve_existing and sentinel.is_file():
        prior = sentinel.read_bytes()
        preexisting = {
            "exists": True,
            "bytes": prior,
            "mtime_ns": sentinel.stat().st_mtime_ns,
            "sha256": sha256_bytes(prior),
        }

    body = json.dumps(dict(payload or {"purpose": "du-bench restoration check"}), ensure_ascii=False)
    sentinel.write_text(body, encoding="utf8")
    return {
        "path": str(sentinel),
        "sha256": sha256_bytes(body.encode("utf8")),
        "preexisting": preexisting,
    }


def restore_sentinel(container: Path, sentinel: Mapping[str, Any]) -> dict[str, Any]:
    """Put a preserved sentinel back byte-identical, mtime included.

    A run that created the sentinel itself has no prior content to restore, so
    the check is reported as ``created`` and counts as stable when the file is
    still the one this run wrote.
    """

    path = Path(sentinel["path"])
    preexisting = sentinel.get("preexisting") or {}

    if not preexisting.get("exists"):
        current = read_sentinel(container)
        stable = current.get("exists") and current.get("sha256") == sentinel.get("sha256")
        return {
            "unchanged": bool(stable),
            "reason": "created_by_this_run",
            "preexisting": False,
            "sha256": current.get("sha256"),
        }

    if not path.is_file():
        return {
            "unchanged": False,
            "reason": "sentinel_missing_after_run",
            "preexisting": True,
            "sha256": None,
        }

    original = preexisting["bytes"]
    path.write_bytes(original)
    try:
        os.utime(path, ns=(preexisting["mtime_ns"], preexisting["mtime_ns"]))
    except OSError:  # pragma: no cover - filesystem dependent
        pass
    restored = file_fingerprint(path)
    unchanged = (
        restored.get("sha256") == preexisting.get("sha256")
        and restored.get("mtime_ns") == preexisting.get("mtime_ns")
    )
    return {
        "unchanged": bool(unchanged),
        "reason": "restored" if unchanged else "content_or_mtime_changed",
        "preexisting": True,
        "sha256": restored.get("sha256"),
    }


def read_sentinel(container: Path) -> dict[str, Any]:
    sentinel = Path(container) / SENTINEL_NAME
    if not sentinel.is_file():
        return {"exists": False}
    data = sentinel.read_bytes()
    return {"exists": True, "sha256": sha256_bytes(data), "text": data.decode("utf8", "replace")}


def mark_owned(container: Path) -> Path:
    """Declare a container as created by this run, so cleanup may delete it."""

    root = Path(container)
    root.mkdir(parents=True, exist_ok=True)
    marker = root / OWNED_MARKER
    marker.write_text("owned by du-bench run\n", encoding="utf8")
    return marker


def cleanup_owned(container: Path, *, keep: Iterable[str] = ()) -> dict[str, Any]:
    """Remove only a container this run marked as owned; never an unknown dir."""

    root = Path(container)
    if not (root / OWNED_MARKER).is_file():
        return {
            "removed": False,
            "reason": "container is not marked owned; refusing to delete",
            "path": str(root),
        }
    kept = set(keep)
    removed: list[str] = []
    for child in sorted(root.iterdir()):
        if child.name in kept:
            continue
        if child.is_dir():
            shutil.rmtree(child, ignore_errors=True)
        else:
            try:
                child.unlink()
            except OSError:
                continue
        removed.append(child.name)
    return {"removed": True, "children_removed": removed, "path": str(root)}


def directory_size(path: Path) -> int:
    total = 0
    target = Path(path)
    if not target.exists():
        return 0
    for candidate in target.rglob("*"):
        if candidate.is_file():
            try:
                total += candidate.stat().st_size
            except OSError:
                continue
    return total


def peak_rss_bytes() -> int | None:
    """Return this process's peak RSS when the platform exposes it."""

    try:
        import resource  # type: ignore[import-not-found]
    except ImportError:
        pass
    else:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        # ru_maxrss is KiB on Linux, bytes on macOS.
        return int(usage.ru_maxrss) * (1024 if os.name != "nt" else 1)

    if os.name == "nt":  # pragma: no cover - Windows only
        try:
            import ctypes
            from ctypes import wintypes

            class _ProcessMemoryCounters(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            counters = _ProcessMemoryCounters()
            counters.cb = ctypes.sizeof(_ProcessMemoryCounters)
            size = counters.cb
            handle = ctypes.windll.kernel32.GetCurrentProcess()

            # Without explicit prototypes ctypes truncates the 64-bit HANDLE to
            # a 32-bit int, and both entry points fail with rc=0.
            def _probe(function: Any) -> int | None:
                function.argtypes = [
                    wintypes.HANDLE,
                    ctypes.POINTER(_ProcessMemoryCounters),
                    wintypes.DWORD,
                ]
                function.restype = wintypes.BOOL
                counters.cb = size
                if function(handle, ctypes.byref(counters), size):
                    return int(counters.PeakWorkingSetSize)
                return None

            try:
                measured = _probe(ctypes.windll.psapi.GetProcessMemoryInfo)
            except (AttributeError, OSError):  # pragma: no cover - platform dependent
                measured = None
            if measured is not None:
                return measured

            # psapi may be unavailable in constrained hosts; fall back to the
            # K32 entry point exported by kernel32 on Windows 7+.
            try:
                measured = _probe(ctypes.windll.kernel32.K32GetProcessMemoryInfo)
            except (AttributeError, OSError):  # pragma: no cover - platform dependent
                measured = None
            if measured is not None:
                return measured

            # Last resort: the Win32 process counter (peak paged pool is not the
            # working set, but GetProcessMemoryInfo is authoritative and the
            # caller records peak_rss_measured=False if all probes fail).
            return None
        except Exception:  # pragma: no cover - best effort only
            return None
    return None


def resource_report(
    *,
    elapsed_seconds: float,
    derived_bytes: int,
    scratch_bytes: int,
    raw_bytes: int,
    model_calls: int,
    peak_rss: int | None,
    measured: bool = True,
) -> dict[str, Any]:
    return {
        "elapsed_seconds": round(float(elapsed_seconds), 3),
        "derived_bytes": int(derived_bytes),
        "scratch_bytes": int(scratch_bytes),
        "raw_bytes": int(raw_bytes),
        "raw_copies": 0,
        "model_calls": int(model_calls),
        "paid_calls": 0,
        "peak_rss_bytes": peak_rss,
        "peak_rss_measured": peak_rss is not None,
        "measured": measured,
    }
