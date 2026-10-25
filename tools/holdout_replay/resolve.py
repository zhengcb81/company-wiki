"""Source resolution: bindings file or SHA-indexed source root (never substitute)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


class ResolveError(RuntimeError):
    """The original could not be resolved; the sample becomes unavailable."""


def load_bindings(path: Path) -> dict[str, str]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in data.items()
    ):
        raise ResolveError("bindings must be a {sample_id: absolute_path} JSON object")
    return data


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_source_root_index(source_root: Path, wanted: Mapping[str, int]) -> dict[str, Path]:
    """Index a tree by SHA-256 for the wanted samples.

    Only files whose size matches a wanted byte size are hashed, so indexing a
    large library stays cheap. Read-only; nothing is copied or moved.
    """
    root = Path(source_root)
    sizes: dict[int, list[str]] = {}
    for sha, size in wanted.items():
        sizes.setdefault(size, []).append(sha)
    index: dict[str, Path] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        candidates = sizes.get(size)
        if not candidates:
            continue
        try:
            sha = _sha256(path)
        except OSError:
            continue
        for wanted_sha in candidates:
            if sha == wanted_sha:
                index[wanted_sha] = path
    return index


def resolve_original(
    sample: Mapping[str, Any],
    *,
    bindings: Mapping[str, str] | None = None,
    source_index: Mapping[str, Path] | None = None,
) -> tuple[Path, str]:
    """Return (path, actual_sha) for one sample, or raise ResolveError.

    A missing binding, an unreadable file, or a SHA mismatch is an honest
    unavailable reason; a different file is never substituted.
    """
    sample_id = sample["sample_id"]
    expected = sample["source_ref"]["content_sha256"]
    size = int(sample["source_ref"]["byte_size"])
    candidates: list[Path] = []
    if bindings is not None and bindings.get(sample_id):
        candidates.append(Path(bindings[sample_id]))
    if source_index is not None and expected in source_index:
        candidates.append(Path(source_index[expected]))
    if not candidates:
        raise ResolveError("no binding and no source-root match for this sample")
    errors = []
    for path in candidates:
        try:
            actual_size = path.stat().st_size
        except OSError as exc:
            errors.append(f"{path}: {exc.strerror or 'unreadable'}")
            continue
        if actual_size != size:
            errors.append(f"{path}: byte size {actual_size} != manifest {size}")
            continue
        actual = _sha256(path)
        if actual != expected:
            errors.append(f"{path}: sha {actual[:12]} != manifest {expected[:12]}")
            continue
        return path, actual
    raise ResolveError("; ".join(errors) or "no candidate original")
