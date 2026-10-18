"""Strict JSON readers shared by the P4 lane.

Implements the INTERFACES.md section 1 data norms the lane depends on: UTF-8
without BOM, duplicate keys refused, ``NaN``/``Infinity`` refused, and a bounded
read so a 16 MiB receipt limit is enforced before the bytes are parsed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class JsonRejected(ValueError):
    """A bounded, strict JSON read failed; ``reason`` is a shared error code."""

    def __init__(self, reason: str, detail: str = ""):
        self.reason = reason
        self.detail = detail
        super().__init__(reason + (f": {detail}" if detail else ""))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_bounded_bytes(path: Path, *, limit: int) -> bytes:
    """Read at most ``limit`` bytes; over-limit is a named refusal, never a truncation."""
    data = path.read_bytes()
    if len(data) > limit:
        raise JsonRejected("limit_exceeded", f"{path.name} exceeds {limit} bytes")
    return data


def _no_constant(value: str) -> None:
    raise JsonRejected("invalid_json", f"nonfinite number {value}")


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise JsonRejected("invalid_json", f"duplicate key {key!r}")
        result[key] = value
    return result


def loads_strict(raw: bytes, *, label: str = "json") -> Any:
    """Parse UTF-8 JSON with duplicate keys and nonfinite numbers refused."""
    if raw.startswith(b"\xef\xbb\xbf"):
        raise JsonRejected("invalid_json", f"{label} starts with a UTF-8 BOM")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise JsonRejected("invalid_json", f"{label} is not UTF-8") from exc
    try:
        return json.loads(
            text, object_pairs_hook=_unique_pairs, parse_constant=_no_constant
        )
    except JsonRejected:
        raise
    except json.JSONDecodeError as exc:
        raise JsonRejected("invalid_json", f"{label} is not JSON") from exc


def load_strict_file(path: Path, *, limit: int, label: str = "json") -> Any:
    return loads_strict(read_bounded_bytes(path, limit=limit), label=label)


def canonical_dumps(value: Any) -> str:
    """INTERFACES.md section 1: single-line, key-sorted, ASCII-only JSON."""
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )


def sha256_json(value: Any) -> str:
    return sha256_text(canonical_dumps(value))
