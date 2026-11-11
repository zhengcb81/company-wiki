"""Source-acquisition sidecar file contract and tolerant parser."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ACQUISITION_SIDECAR_SUFFIX = ".source.json"


def read_acquisition_sidecar(path: Path) -> dict[str, Any]:
    """Read a sidecar object; malformed optional metadata stays diagnostic."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {"meta_parse_error": True}
    if not isinstance(value, dict):
        return {"meta_parse_error": True}
    return value


__all__ = ["ACQUISITION_SIDECAR_SUFFIX", "read_acquisition_sidecar"]
