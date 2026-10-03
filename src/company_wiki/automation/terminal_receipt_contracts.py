"""Small neutral identities shared by terminal storage and its application."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from company_wiki._id_scope import normalize_id_scope

from .models import require_sha256


TERMINAL_RECEIPT_SCHEMA = "narrative-terminal-receipt/1.0"


@dataclass(frozen=True)
class FinalArtifactPin:
    effect_id: str
    artifact_version_id: str
    artifact_sha256: str
    byte_size: int
    document_id: str
    source_id: str
    source_sha256: str

    def __post_init__(self) -> None:
        for name in ("effect_id", "artifact_version_id", "document_id", "source_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value or value != value.strip():
                raise ValueError(f"{name} must be a nonempty, unpadded identifier")
        require_sha256(self.artifact_sha256, field_name="artifact_sha256")
        require_sha256(self.source_sha256, field_name="source_sha256")
        if type(self.byte_size) is not int or not 0 < self.byte_size <= 2 * 1024 * 1024:
            raise ValueError("byte_size must be a positive bounded final artifact size")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TerminalCompactionResult:
    job_ids: tuple[str, ...]
    attempts_compacted: int
    logical_bytes_before: int
    logical_bytes_after: int
    already_compacted: bool = False


def terminal_job_scope(job_ids: tuple[str, ...]) -> tuple[str, ...]:
    scope = normalize_id_scope(job_ids, name="job_ids")
    if scope is None:
        raise TypeError("job_ids must be an explicit tuple")
    if scope and (len(job_ids) != 3 or len(scope) != 3):
        raise ValueError("job_ids must contain exactly three distinct jobs")
    return tuple(sorted(scope))


def is_terminal_receipt(result: Mapping[str, Any]) -> bool:
    return result.get("schema_version") == TERMINAL_RECEIPT_SCHEMA


__all__ = ["FinalArtifactPin", "TerminalCompactionResult", "TERMINAL_RECEIPT_SCHEMA"]
