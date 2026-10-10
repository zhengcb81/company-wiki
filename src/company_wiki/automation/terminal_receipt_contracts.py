"""Small neutral identities shared by terminal storage and its application."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from company_wiki._id_scope import normalize_id_scope
from company_wiki.narrative_subject import NarrativeSubject

from .models import require_sha256


TERMINAL_RECEIPT_SCHEMA = "narrative-terminal-receipt/1.0"
PROJECTED_TERMINAL_RECEIPT_SCHEMA = "narrative-terminal-receipt/2.0"


@dataclass(frozen=True)
class FinalArtifactPin:
    effect_id: str
    artifact_version_id: str
    artifact_sha256: str
    byte_size: int
    document_id: str
    source_id: str
    source_sha256: str
    subject_binding: NarrativeSubject | None = None
    generation_sha256: str | None = None

    def __post_init__(self) -> None:
        for name in ("effect_id", "artifact_version_id", "document_id", "source_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value or value != value.strip():
                raise ValueError(f"{name} must be a nonempty, unpadded identifier")
        require_sha256(self.artifact_sha256, field_name="artifact_sha256")
        require_sha256(self.source_sha256, field_name="source_sha256")
        if type(self.byte_size) is not int or not 0 < self.byte_size <= 2 * 1024 * 1024:
            raise ValueError("byte_size must be a positive bounded final artifact size")

        if self.subject_binding is not None:
            if not isinstance(self.subject_binding, NarrativeSubject) or self.subject_binding.kind != "official_json":
                raise ValueError("projected final pin requires an official JSON subject")
            if self.generation_sha256 is None:
                raise ValueError("projected final pin requires a generation SHA")
            require_sha256(self.generation_sha256, field_name="generation_sha256")
            anchor = self.subject_binding.anchor_ref
            if (self.document_id, self.source_id, self.source_sha256) != (
                    anchor["document_id"], anchor["source_id"], anchor["content_sha256"]):
                raise ValueError("final pin anchor differs from its actual parent")
        elif self.generation_sha256 is not None:
            raise ValueError("generation SHA requires a projected final subject")

    def to_dict(self) -> dict[str, Any]:
        if self.subject_binding is not None:
            return {"effect_id": self.effect_id, "artifact_version_id": self.artifact_version_id,
                    "artifact_sha256": self.artifact_sha256, "byte_size": self.byte_size,
                    "subject_binding": self.subject_binding.to_dict(),
                    "generation_sha256": self.generation_sha256}
        value = asdict(self)
        value.pop("subject_binding")
        value.pop("generation_sha256")
        return value


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
    return result.get("schema_version") in {TERMINAL_RECEIPT_SCHEMA, PROJECTED_TERMINAL_RECEIPT_SCHEMA}


__all__ = ["FinalArtifactPin", "TerminalCompactionResult", "TERMINAL_RECEIPT_SCHEMA", "PROJECTED_TERMINAL_RECEIPT_SCHEMA"]
