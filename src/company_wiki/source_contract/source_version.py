"""Pure pathless source identities and verified-read port; no storage runtime."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

SOURCE_REF_SCHEMA_VERSION = "2.0"
_ERROR_STATUSES = frozenset({"not_found", "not_indexed", "unavailable", "blocked", "ambiguous"})

class SourceReadError(RuntimeError):
    """A named refusal with no bytes or physical path in its public detail."""

    def __init__(self, status: str, reason: str, detail: str = ""):
        if status not in _ERROR_STATUSES:
            raise ValueError(f"unknown read status: {status}")
        self.status = status
        self.reason = reason
        self.detail = detail
        super().__init__(f"{status}: {reason}" + (f" ({detail})" if detail else ""))


@dataclass(frozen=True)
class SourceRef:
    document_id: str
    source_id: str
    content_sha256: str
    byte_size: int
    mime_type: str
    schema_version: str = SOURCE_REF_SCHEMA_VERSION


@dataclass(frozen=True)
class ReviewSnapshot:
    """Review state observed after the exact source bytes were verified."""

    status: str
    source_sha256: str | None
    evidence_sha256: str | None
    policy_hash: str | None
    reviewed_at: str | None


@dataclass(frozen=True)
class VerifiedContent:
    document_id: str
    source_id: str
    content_sha256: str
    data: bytes
    byte_size: int
    read_at: str
    policy_sha256: str
    source_read_policy_sha256: str
    review: ReviewSnapshot | None = None
    schema_version: str = SOURCE_REF_SCHEMA_VERSION


@dataclass(frozen=True)
class VerifiedVersionReceipt:
    """Verified source identity without source bytes or a physical location."""

    document_id: str
    source_id: str
    content_sha256: str
    byte_size: int
    read_at: str
    policy_sha256: str
    source_read_policy_sha256: str
    review: ReviewSnapshot | None = None
    schema_version: str = SOURCE_REF_SCHEMA_VERSION


@runtime_checkable
class SourceVersionPort(Protocol):
    """Narrow source-owner interface. Serialization still verifies input bytes."""

    def open_version(self, ref: SourceRef, *, purpose: str) -> VerifiedContent: ...
    def verify_version(self, ref: SourceRef, *, purpose: str) -> VerifiedVersionReceipt: ...
    def describe_version(self, ref: SourceRef) -> dict[str, str | int | None]: ...
