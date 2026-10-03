"""Content snapshots of small isolated test fixtures, with no runtime gate."""

from __future__ import annotations

import hashlib
from pathlib import Path


def snapshot_files(root: Path) -> dict[str, str]:
    """Detect fixture additions, removals and same-stat content rewrites."""
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }
