"""Bounded, read-only depth-first scan of one explicit project root.

Traversal is deterministic (sorted entries per directory), never follows a
reparse point, never opens a file, and stops exactly at the file budget or the
wall-clock deadline. Directory traversal failures are recorded as errors and
make the result partial instead of silently skipped.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import classify as classify_module
from .core import (
    BudgetExceeded,
    MAX_ERROR_ITEMS,
    MAX_SKIPPED_SAMPLES,
    ScanBudget,
    entry_state,
    error_label,
    file_identity,
    truncate_path,
    utc_now_text,
)
from .classify import CATEGORIES, retention_bucket

_AUTO_MARKER_PREFIX = "automation."


@dataclass
class ScanResult:
    started_at: str
    finished_at: str = ""
    stop_reason: str = "complete"
    complete: bool = False
    entries_seen: int = 0
    directories_seen: int = 0
    files_measured: int = 0
    logical_path_bytes: int = 0
    unknown_files: int = 0
    skipped_files: int = 0
    skipped_links: int = 0
    skipped_cloud: int = 0
    unknown_identity_files: int = 0
    errors_total: int = 0
    category_files: dict[str, int] = field(
        default_factory=lambda: {name: 0 for name in CATEGORIES}
    )
    category_bytes: dict[str, int] = field(
        default_factory=lambda: {name: 0 for name in CATEGORIES}
    )
    bucket_files: dict[tuple[str, str], int] = field(default_factory=dict)
    bucket_bytes: dict[tuple[str, str], int] = field(default_factory=dict)
    dir_files: dict[str, int] = field(default_factory=dict)
    dir_bytes: dict[str, int] = field(default_factory=dict)
    duplicates: dict[tuple[int, int], list[int]] = field(default_factory=dict)
    errors: list[dict] = field(default_factory=list)
    skipped_samples: list[dict] = field(default_factory=list)


def _scandir(path: Path) -> list:
    with os.scandir(path) as iterator:
        entries = list(iterator)
    entries.sort(key=lambda entry: entry.name)
    return entries


def _record_error(result: ScanResult, rel_path: str, error: BaseException) -> None:
    result.errors_total += 1
    if len(result.errors) < MAX_ERROR_ITEMS:
        result.errors.append(
            {"path": truncate_path(rel_path), "error": error_label(error)}
        )


def _open_dir(
    result: ScanResult, path: Path, dir_rel: str, auto_dirs: set[str]
) -> list | None:
    try:
        entries = _scandir(path)
    except OSError as error:
        _record_error(result, dir_rel or ".", error)
        return None
    for entry in entries:
        if entry.name.startswith(_AUTO_MARKER_PREFIX):
            auto_dirs.add(dir_rel)
            break
    return entries


def _join(dir_rel: str, name: str) -> str:
    return f"{dir_rel}/{name}" if dir_rel else name


def _record_skip(result: ScanResult, rel: str, kind: str) -> None:
    result.skipped_files += 1
    if kind == "cloud":
        result.skipped_cloud += 1
    else:
        result.skipped_links += 1
    if len(result.skipped_samples) < MAX_SKIPPED_SAMPLES:
        result.skipped_samples.append({"path": truncate_path(rel), "kind": kind})


def _finish(result: ScanResult, *, budget_stop: bool) -> ScanResult:
    if budget_stop:
        result.stop_reason = "budget"
    elif result.errors_total:
        result.stop_reason = "errors"
    else:
        result.stop_reason = "complete"
    result.complete = result.stop_reason == "complete"
    result.finished_at = utc_now_text()
    return result


def scan_tree(
    project_root: Path,
    *,
    max_files: int,
    max_seconds: float,
    clock=time.monotonic,
) -> ScanResult:
    """Scan ``project_root`` with metadata only under file/time budgets."""
    root = Path(project_root)
    budget = ScanBudget(max_files=max_files, max_seconds=max_seconds, clock=clock)
    result = ScanResult(started_at=utc_now_text())
    auto_dirs: set[str] = set()
    budget_stop = False

    root_entries = _open_dir(result, root, "", auto_dirs)
    if root_entries is None:
        return _finish(result, budget_stop=False)

    stack: list[list] = [[root_entries, 0, ""]]
    try:
        while stack:
            frame = stack[-1]
            entries, index, dir_rel = frame[0], frame[1], frame[2]
            if index >= len(entries):
                stack.pop()
                continue
            frame[1] = index + 1
            budget.check_deadline()
            entry = entries[index]
            result.entries_seen += 1
            rel = _join(dir_rel, entry.name)
            try:
                st = entry.stat(follow_symlinks=False)
            except OSError as error:
                _record_error(result, rel, error)
                continue
            state = entry_state(st, entry.name)
            if state is not None:
                budget.consume_file()
                _record_skip(result, rel, state)
                continue
            if entry.is_dir(follow_symlinks=False):
                result.directories_seen += 1
                child_entries = _open_dir(result, Path(entry.path), rel, auto_dirs)
                if child_entries is not None:
                    stack.append([child_entries, 0, rel])
                continue
            budget.consume_file()
            try:
                measured = os.lstat(entry.path)
            except OSError as error:
                _record_error(result, rel, error)
                continue
            measured_state = entry_state(measured, entry.name)
            if measured_state is not None:
                _record_skip(result, rel, measured_state)
                continue
            size = int(measured.st_size)
            category, _rule = classify_module.classify_file(rel, auto_dirs=auto_dirs)
            bucket = retention_bucket(category, rel)
            result.files_measured += 1
            result.logical_path_bytes += size
            result.category_files[category] += 1
            result.category_bytes[category] += size
            result.bucket_files[(category, bucket)] = (
                result.bucket_files.get((category, bucket), 0) + 1
            )
            result.bucket_bytes[(category, bucket)] = (
                result.bucket_bytes.get((category, bucket), 0) + size
            )
            if category == "unknown":
                result.unknown_files += 1
            for frame_for_dir in stack:
                dir_key = frame_for_dir[2]
                result.dir_files[dir_key] = result.dir_files.get(dir_key, 0) + 1
                result.dir_bytes[dir_key] = result.dir_bytes.get(dir_key, 0) + size
            identity = file_identity(measured)
            if identity is None:
                result.unknown_identity_files += 1
            else:
                record = result.duplicates.get(identity)
                if record is None:
                    result.duplicates[identity] = [1, size]
                else:
                    record[0] += 1
    except BudgetExceeded:
        budget_stop = True
    return _finish(result, budget_stop=budget_stop)
