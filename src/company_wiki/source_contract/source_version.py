"""Pure pathless source identities and verified-read port; no storage runtime."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
import hashlib
from typing import ClassVar, Protocol, runtime_checkable

from .source_manifest import SourceManifestError, source_id_for_sha256

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

    @classmethod
    def from_dict(cls, value: object) -> "SourceRef":
        """Parse the public pathless source-reference contract."""
        fields = {
            "schema_version", "document_id", "source_id", "content_sha256",
            "byte_size", "mime_type",
        }
        if not isinstance(value, Mapping) or set(value) != fields:
            raise SourceRefError("source_ref has an invalid field set")

        schema_version = value["schema_version"]
        if schema_version != SOURCE_REF_SCHEMA_VERSION:
            raise SourceRefError("unsupported source_ref schema")
        document_id = _required_text(value["document_id"], "document_id")
        source_id = _required_text(value["source_id"], "source_id")
        content_sha256 = _required_text(value["content_sha256"], "content_sha256")
        try:
            expected_source_id = source_id_for_sha256(content_sha256)
        except SourceManifestError as exc:
            raise SourceRefError("source_ref content hash is invalid") from exc
        if source_id != expected_source_id:
            raise SourceRefMismatchError("source_ref identity does not match its content hash")
        byte_size = value["byte_size"]
        if type(byte_size) is not int or byte_size <= 0:
            raise SourceRefError("source_ref byte_size must be a positive integer")
        mime_type = _required_text(value["mime_type"], "mime_type")
        return cls(
            document_id=document_id,
            source_id=source_id,
            content_sha256=content_sha256,
            byte_size=byte_size,
            mime_type=mime_type,
            schema_version=schema_version,
        )

    def to_dict(self) -> dict[str, str | int]:
        return {
            "schema_version": self.schema_version,
            "document_id": self.document_id,
            "source_id": self.source_id,
            "content_sha256": self.content_sha256,
            "byte_size": self.byte_size,
            "mime_type": self.mime_type,
        }


class SourceRefError(ValueError):
    """The serialized source-reference contract is malformed or inconsistent."""


class SourceRefMismatchError(SourceRefError):
    """Two well-formed source-reference identity fields contradict each other."""


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise SourceRefError(f"source_ref {field} must be non-empty text")
    return value


@dataclass(frozen=True)
class ReviewSnapshot:
    """Review state observed after the exact source bytes were verified."""

    status: str
    source_sha256: str | None
    evidence_sha256: str | None
    policy_hash: str | None
    reviewed_at: str | None


@dataclass(frozen=True, init=False)
class SourceByteObservation:
    """One stream's actual byte count and digest, with optional retained bytes."""

    data: bytes | None
    content_sha256: str
    byte_size: int

    def __init__(self) -> None:
        raise TypeError("observe source bytes through SourceByteVerifier")


class SourceByteVerifier:
    """Bind the retained bytes to the same stream that produced their digest."""

    def __init__(self, *, retain_bytes: bool) -> None:
        self._digest = hashlib.sha256()
        self._chunks: list[bytes] | None = [] if retain_bytes else None
        self._byte_size = 0

    def update(self, chunk: bytes) -> None:
        if type(chunk) is not bytes:
            raise TypeError("source chunks must be immutable bytes")
        self._digest.update(chunk)
        self._byte_size += len(chunk)
        if self._chunks is not None:
            self._chunks.append(chunk)

    def hexdigest(self) -> str:
        return self._digest.hexdigest()

    def observe(self) -> SourceByteObservation:
        observation = object.__new__(SourceByteObservation)
        data = b"".join(self._chunks) if self._chunks is not None else None
        object.__setattr__(observation, "data", data)
        object.__setattr__(observation, "byte_size", self._byte_size)
        object.__setattr__(observation, "content_sha256", self._digest.hexdigest())
        return observation


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
    _observation: ClassVar[SourceByteObservation | None] = None

    @classmethod
    def from_observation(
        cls, ref: SourceRef, observation: SourceByteObservation, *, read_at: str,
        policy_sha256: str, source_read_policy_sha256: str, review: ReviewSnapshot | None = None,
    ) -> "VerifiedContent":
        """Bind a retained stream observation to its requested source version."""
        if (
            type(observation) is not SourceByteObservation
            or observation.data is None
            or observation.byte_size != ref.byte_size
            or observation.content_sha256 != ref.content_sha256
        ):
            raise SourceRefMismatchError("source bytes do not match source ref")
        content = cls(
            ref.document_id, ref.source_id, ref.content_sha256, observation.data, ref.byte_size,
            read_at, policy_sha256, source_read_policy_sha256, review, ref.schema_version,
        )
        object.__setattr__(content, "_observation", observation)
        return content

    def verified_observation(self) -> "VerifiedContent":
        """Reuse an exact observation, or verify bytes supplied by a compatible backend."""
        if type(self.data) is not bytes or len(self.data) != self.byte_size:
            raise SourceRefMismatchError("source bytes do not match source ref")
        observation = self._observation
        if (
            observation is not None and observation.data is self.data
            and observation.content_sha256 == self.content_sha256
        ):
            return self
        verifier = SourceByteVerifier(retain_bytes=True)
        verifier.update(self.data)
        if verifier.hexdigest() != self.content_sha256:
            raise SourceRefMismatchError("source bytes do not match source ref")
        verified = replace(self)
        object.__setattr__(verified, "_observation", verifier.observe())
        return verified


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

__all__ = [
    'ReviewSnapshot',
    'SOURCE_REF_SCHEMA_VERSION',
    'SourceByteObservation',
    'SourceByteVerifier',
    'SourceReadError',
    'SourceRef',
    'SourceRefMismatchError',
    'VerifiedContent',
    'VerifiedVersionReceipt',
]
