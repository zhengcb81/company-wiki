#!/usr/bin/env python3
"""Fail-closed path policy separating immutable sources from derived output."""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path


class ContentPathKind(str, Enum):
    ORIGINAL_SOURCE = "original_source"
    DERIVED_ARTIFACT = "derived_artifact"
    CONTROL_FILE = "control_file"
    EXTERNAL = "external"
    ESCAPE = "escape"


class SourceMutationError(PermissionError):
    """Raised before an attempted write could mutate an original source."""


_CONTENT_ROOTS = {"companies", "sectors", "themes"}
_DERIVED_DIRS = {"wiki", "extracts", "segments", "archive", ".derived"}


def _absolute_without_resolving(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def classify_content_path(path: Path, repository_root: Path) -> ContentPathKind:
    """Classify a target using both lexical and resolved paths.

    Unknown content below an entity fails closed as source data. Hidden project
    metadata directories (for example ``companies/.obsidian``) are control
    files, not company entities.
    """

    root = repository_root.resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    lexical = _absolute_without_resolving(candidate)
    try:
        lexical.relative_to(root)
    except ValueError:
        return ContentPathKind.EXTERNAL

    resolved = lexical.resolve(strict=False)
    try:
        relative = resolved.relative_to(root)
    except ValueError:
        return ContentPathKind.ESCAPE

    parts = relative.parts
    if not parts or parts[0] not in _CONTENT_ROOTS:
        return ContentPathKind.CONTROL_FILE
    if len(parts) < 2 or parts[1].startswith("."):
        return ContentPathKind.CONTROL_FILE
    if len(parts) < 3:
        return ContentPathKind.CONTROL_FILE

    entity_parts = parts[2:]
    if "raw" in entity_parts:
        return ContentPathKind.ORIGINAL_SOURCE
    if entity_parts[0] in _DERIVED_DIRS:
        return ContentPathKind.DERIVED_ARTIFACT

    # Files/directories at an entity root, and unknown subdirectories, may be
    # direct-download source material. Ambiguity is resolved toward immutability.
    return ContentPathKind.ORIGINAL_SOURCE


def assert_content_writable(path: Path, repository_root: Path) -> None:
    """Raise before writes to original data or paths escaping the repository."""

    kind = classify_content_path(path, repository_root)
    if kind is ContentPathKind.ORIGINAL_SOURCE:
        raise SourceMutationError(
            f"Refusing to mutate immutable original source: {Path(path)}"
        )
    if kind is ContentPathKind.ESCAPE:
        raise SourceMutationError(
            f"Refusing content-path escape through symlink or traversal: {Path(path)}"
        )


def is_original_source(path: Path, repository_root: Path) -> bool:
    return classify_content_path(path, repository_root) is ContentPathKind.ORIGINAL_SOURCE

