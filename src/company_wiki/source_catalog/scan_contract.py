"""Typed contract shared by adapter dispatch and the catalog scanner."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import math
from pathlib import Path
from types import MappingProxyType
from typing import Any

from .admission import AdmissionDecision
from .models import RootSpec


def _freeze_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("scan candidate metadata keys must be strings")
        return MappingProxyType(
            {key: _freeze_json_value(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json_value(item) for item in value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("scan candidate metadata must contain finite JSON numbers")
        return value
    if value is None or isinstance(value, (str, bool, int)):
        return value
    raise TypeError(
        f"scan candidate metadata must contain JSON values, got {type(value).__name__}"
    )


def _thaw_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json_value(item) for item in value]
    return value


@dataclass(frozen=True)
class ScanCandidate:
    """A normalized adapter candidate resolved to its configured physical root."""

    root: RootSpec
    path: Path
    relative_path: str
    group_key: str
    role: str
    entity_name: str | None
    group_metadata: Mapping[str, Any]
    source_status: str
    admission: AdmissionDecision | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.group_metadata, Mapping):
            raise TypeError("group_metadata must be a mapping")
        object.__setattr__(self, "group_metadata", _freeze_json_value(self.group_metadata))

    def group_metadata_payload(self) -> dict[str, Any]:
        """Return a detached JSON-ready copy for the scanner's storage owner."""
        return _thaw_json_value(self.group_metadata)


def infer_company_name(relative_path: str, names: tuple[str, ...]) -> str | None:
    """Match one configured company-name directory within a relative locator."""
    folded = relative_path.casefold()
    matches = [name for name in names if name.casefold() in folded]
    return matches[0] if len(matches) == 1 else None


__all__ = ["ScanCandidate", "infer_company_name"]
