"""WU-601: pure helpers shared by scanner v1 and adapters.

Mechanically moved out of scanner.py (with their dependencies) so adapters
never import the scanner module (ARC-FIT-02).  Behavior is unchanged.
"""

from __future__ import annotations

import json
import os
import unicodedata
from collections.abc import Iterable
from pathlib import Path

from ..models import DOCUMENT_EXTENSIONS

_SKIP_DIRS = frozenset(
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
_ACQUISITION_SIDECAR_SUFFIX = ".source.json"


def _walk_files(root: Path) -> Iterable[Path]:
    for current, directories, files in os.walk(root):
        directories[:] = [name for name in directories if name not in _SKIP_DIRS]
        current_path = Path(current)
        for name in files:
            path = current_path / name
            if path.suffix.lower() in DOCUMENT_EXTENSIONS:
                yield path


def _relative(path: Path, root: Path) -> str:
    return unicodedata.normalize("NFC", path.relative_to(root).as_posix())


def _load_acquisition_metadata(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {"meta_parse_error": True}
    if not isinstance(value, dict):
        return {"meta_parse_error": True}
    return value

