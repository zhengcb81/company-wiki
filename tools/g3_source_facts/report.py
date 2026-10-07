"""Validated JSON report writing for this lane's proposals.

A report is the only artefact this package produces: no apply switch, no
receipt, no authorization/token/expiry surface, and no machine-absolute paths.
Rewriting our own previous report is recovery; touching any other file is a
refusal that leaves the original bytes in place.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
from typing import Any

_WINDOWS_ABSOLUTE = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z]:[\\/]")
_POSIX_ABSOLUTE = re.compile(
    r"(^|[\s\"'(\[])/(?:home|Users|var|tmp|workspace|mnt|root|api|data|projects)(?:/|\b)"
)
_FORBIDDEN_KEYS = frozenset(
    {
        "authorization",
        "authorisation",
        "token",
        "expiry",
        "expires_at",
        "receipt",
        "approval",
        "approved",
        "grant",
        "permission",
        "apply",
    }
)


class ReportWriteError(RuntimeError):
    """Raised before any byte is written when a report would be unsafe."""


def _walk(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def _validate(payload: Any) -> str:
    if not isinstance(payload, dict):
        raise ReportWriteError("report payload must be a JSON object")
    schema = payload.get("schema_version")
    if not isinstance(schema, str) or not schema.strip():
        raise ReportWriteError("report payload needs a schema_version")
    for key, item in _walk(payload):
        lowered = str(key).casefold()
        if lowered in _FORBIDDEN_KEYS:
            raise ReportWriteError(f"report must not carry a {lowered!r} field")
        if isinstance(item, str):
            if _WINDOWS_ABSOLUTE.search(item) or _POSIX_ABSOLUTE.search(item):
                raise ReportWriteError("report must not carry machine-absolute paths")
    return schema


def _existing_schema(path: Path) -> str | None:
    try:
        previous = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ReportWriteError(
            f"existing output {path.name} is not a readable report"
        ) from exc
    if not isinstance(previous, dict):
        raise ReportWriteError(f"existing output {path.name} is not a report object")
    schema = previous.get("schema_version")
    return schema if isinstance(schema, str) else None


def write_json_report(path: str | Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Validate first, then replace only our own previous report atomically."""
    target = Path(path)
    schema = _validate(payload)

    if target.exists():
        previous_schema = _existing_schema(target)
        if previous_schema != schema:
            raise ReportWriteError(
                f"refusing to overwrite {target.name}: existing schema "
                f"{previous_schema!r} != {schema!r}"
            )

    text = json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=False)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    try:
        temporary.write_text(text + "\n", encoding="utf-8")
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            try:
                temporary.unlink()
            except OSError:  # pragma: no cover - platform specific
                pass
    return payload


__all__ = ["ReportWriteError", "write_json_report"]
