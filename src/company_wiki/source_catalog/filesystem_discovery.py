"""Shared filesystem traversal policy owned by the source-catalog boundary."""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from .models import DOCUMENT_EXTENSIONS

SKIP_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        "node_modules",
        ".venv",
        "venv",
    }
)


def walk_document_files(root: Path) -> Iterable[Path]:
    """Yield supported source documents while applying the shared skip policy."""
    for current, directories, files in os.walk(root):
        directories[:] = [name for name in directories if name not in SKIP_DIRS]
        current_path = Path(current)
        for name in files:
            path = current_path / name
            if path.suffix.lower() in DOCUMENT_EXTENSIONS:
                yield path


__all__ = ["SKIP_DIRS", "walk_document_files"]
