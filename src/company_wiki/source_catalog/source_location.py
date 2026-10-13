"""Current registered-root resolution shared by source reads and raw dedup.

Catalog absolute_path is an observation from an earlier scan, never authority
for the current location. The root owner resolves the relative locator again.
"""
from __future__ import annotations

import os
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from .models import RootSpec


class SourceLocationError(ValueError):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def relative_segments(relative_path: str) -> tuple[str, ...] | None:
    """Reject absolute, parent and drive paths before joining a root."""
    normalized = relative_path.replace("\\", "/")
    if (not normalized or any(ord(char) < 32 for char in normalized)
            or PurePosixPath(normalized).is_absolute()
            or PureWindowsPath(relative_path).drive):
        return None
    segments = tuple(normalized.split("/"))
    return None if any(segment in {"", ".", ".."} for segment in segments) else segments


def inside_configured_roots(path: Path, roots: tuple[Any, ...]) -> bool:
    """B03/L05 — a locator may not lead the read path out of the configured
    roots.  Compared on REAL paths (so a symlink or a junction that points
    outside its root is refused before any byte is read) and case-insensitively
    on Windows.

    Containment uses ``commonpath``, not string prefixing: with a root
    configured as a drive root, prefixing compares against ``"C:\\\\"`` and
    refuses every file on that drive.  Hardlinks are NOT distinguished (the path
    is inside the root and the bytes are still verified against the requested
    digest) - recorded as a boundary rather than papered over.
    """
    target = os.path.normcase(os.path.normpath(os.path.realpath(path)))
    for root in roots:
        root_path = getattr(root, "path", None)
        if not root_path:
            continue
        base = os.path.normcase(os.path.normpath(os.path.realpath(root_path)))
        if target == base:
            return True
        try:
            if os.path.commonpath([target, base]) == base:
                return True
        except ValueError:
            continue  # different drives (or mixed absolute/relative): not inside
    return False



def resolve_source_location(root: RootSpec, relative_path: str) -> Path:
    """Resolve an in-root real path, preserving the existing read boundary."""
    segments = relative_segments(relative_path)
    if segments is None:
        raise SourceLocationError("invalid_relative_path")
    resolved = Path(os.path.realpath(root.path.joinpath(*segments)))
    if not inside_configured_roots(resolved, (root,)):
        raise SourceLocationError("artifact_path_outside_allowed_root")
    return resolved


__all__ = ["SourceLocationError", "inside_configured_roots", "relative_segments", "resolve_source_location"]
