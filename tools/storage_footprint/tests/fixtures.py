"""Deterministic fixture-tree helpers for the N6-FOOTPRINT tests.

Trees are built inside the pytest basetemp only; every helper is pure file
metadata and never touches the production repository.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Mapping

Spec = Mapping[str, object]


def make_dir_link(link: Path, target: Path) -> bool:
    """Create a directory link (symlink, else Windows junction); False if refused."""
    try:
        link.symlink_to(target, target_is_directory=True)
        return True
    except (OSError, NotImplementedError):
        pass
    if os.name == "nt":
        try:
            completed = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(target)],
                capture_output=True,
                check=False,
            )
        except OSError:
            return False
        return completed.returncode == 0
    return False


def write_tree(base: Path, spec: Spec) -> Path:
    base.mkdir(parents=True, exist_ok=True)
    for rel, content in spec.items():
        target = base / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(str(content), encoding="utf-8", newline="")
    return base


def snapshot_tree(base: Path) -> dict[str, tuple[int, int]]:
    """rel POSIX path -> (size, mtime_ns) for every regular file under base."""
    snapshot: dict[str, tuple[int, int]] = {}
    for path in sorted(base.rglob("*")):
        if path.is_dir() or path.is_symlink():
            continue
        stat_result = path.stat()
        rel = path.relative_to(base).as_posix()
        snapshot[rel] = (int(stat_result.st_size), int(stat_result.st_mtime_ns))
    return snapshot


def file_count(base: Path) -> int:
    return sum(
        1 for path in base.rglob("*") if path.is_file() and not path.is_symlink()
    )


def category_bytes(report: dict, category: str) -> int:
    for item in report["categories"]:
        if item["category"] == category:
            return int(item["logical_path_bytes"])
    raise KeyError(category)


def category_files(report: dict, category: str) -> int:
    for item in report["categories"]:
        if item["category"] == category:
            return int(item["files"])
    raise KeyError(category)


def bucket_of(report: dict, category: str) -> str:
    matches = [
        str(note["bucket"])
        for note in report["retention_notes"]
        if note["category"] == category
    ]
    if len(matches) != 1:
        raise KeyError((category, matches))
    return matches[0]


def buckets_of(report: dict, category: str) -> set[str]:
    return {
        str(note["bucket"])
        for note in report["retention_notes"]
        if note["category"] == category
    }


def limits(max_files: int = 100000, max_seconds: float = 60.0) -> dict[str, object]:
    return {"max_files": int(max_files), "max_seconds": float(max_seconds)}


def is_relative_path(text: str) -> bool:
    return not text.startswith("/") and "://" not in text and ":" not in text[:3]


def walk_rel_paths(base: Path) -> set[str]:
    found: set[str] = set()
    for root, _dirs, files in os.walk(base):
        for name in files:
            found.add(Path(root, name).relative_to(base).as_posix())
    return found
