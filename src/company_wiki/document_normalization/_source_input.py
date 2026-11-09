"""Bind one immutable source input before dispatch to a format parser."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib

from company_wiki.source_contract.source_version import VerifiedContent

from .limits import NormalizationLimits


class _SourceDigestMismatch(ValueError):
    """The supplied raw bytes differ from the claimed source."""


@dataclass(frozen=True)
class _NormalizationSource:
    data: bytes
    source_id: str
    source_sha256: str

    @classmethod
    def from_bytes(
        cls, data: bytes, *, source_id: str, source_sha256: str, limits: NormalizationLimits,
    ) -> _NormalizationSource:
        _check_input(data, source_id, limits)
        if hashlib.sha256(data).hexdigest() != source_sha256:
            raise _SourceDigestMismatch("source bytes do not match source_sha256")
        return cls(data, source_id, source_sha256)

    @classmethod
    def from_verified(
        cls, content: VerifiedContent, *, limits: NormalizationLimits,
    ) -> _NormalizationSource:
        if not isinstance(content, VerifiedContent):
            raise TypeError("content must be a source-owner VerifiedContent")
        _check_input(content.data, content.source_id, limits)
        verified = VerifiedContent.verified_observation(content)
        return cls(verified.data, verified.source_id, verified.content_sha256)


def _check_input(data: bytes, source_id: str, limits: NormalizationLimits) -> None:
    if not isinstance(data, bytes):
        raise TypeError("original must be bytes")
    if not isinstance(source_id, str) or not source_id:
        raise TypeError("source_id must be non-empty text")
    if not isinstance(limits, NormalizationLimits):
        raise TypeError("limits must be a NormalizationLimits")
    limits.require_within("max_source_bytes", len(data))
    limits.check_deadline("source input")
