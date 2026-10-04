"""Shared verified-source guard used by narrative handlers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
from typing import Protocol

from company_wiki.source_catalog.source_reader import (
    SourceRef,
    VerifiedContent,
)

from .narrative_contracts import PromptReviewValue, SourceRevisionEventPayload


class NarrativeSourceReader(Protocol):
    def open_version(
        self,
        ref: SourceRef,
        *,
        purpose: str,
        expected_read_policy_sha256: str | None = None,
    ) -> VerifiedContent: ...

    def describe_version(self, ref: SourceRef) -> Mapping[str, object]: ...


@dataclass
class NarrativeSourceGuardError(Exception):
    code: str
    detail: str


def source_ref(payload: SourceRevisionEventPayload) -> SourceRef:
    value = payload.source_ref
    return SourceRef(
        document_id=value.document_id,
        source_id=value.source_id,
        content_sha256=value.content_sha256,
        byte_size=value.byte_size,
        mime_type=value.mime_type,
        schema_version=value.schema_version,
    )


def validate_opened_identity(
    payload: SourceRevisionEventPayload,
    opened: VerifiedContent,
) -> None:
    validate_opened_source(
        SourceRef(
            document_id=payload.source_ref.document_id,
            source_id=payload.source_ref.source_id,
            content_sha256=payload.source_ref.content_sha256,
            byte_size=payload.source_ref.byte_size,
            mime_type=payload.source_ref.mime_type,
            schema_version=payload.source_ref.schema_version,
        ),
        opened,
        expected_read_policy_sha256=payload.expected_read_policy_sha256,
    )


def validate_opened_source(
    source: SourceRef,
    opened: VerifiedContent,
    *,
    expected_read_policy_sha256: str,
) -> None:
    if (
        opened.document_id != source.document_id
        or opened.source_id != source.source_id
        or opened.content_sha256 != source.content_sha256
        or opened.byte_size != source.byte_size
        or len(opened.data) != source.byte_size
        or hashlib.sha256(opened.data).hexdigest() != source.content_sha256
    ):
        raise NarrativeSourceGuardError(
            "SOURCE_HASH_MISMATCH",
            "verified source identity differs from the event pin",
        )
    if opened.source_read_policy_sha256 != expected_read_policy_sha256:
        raise NarrativeSourceGuardError(
            "POLICY_DENIED",
            "source read policy differs from the event pin",
        )


def validate_source_metadata(
    payload: SourceRevisionEventPayload,
    metadata: Mapping[str, object],
) -> None:
    source = payload.source_ref
    expected = {
        "document_id": source.document_id,
        "source_id": source.source_id,
        "content_sha256": source.content_sha256,
        "byte_size": source.byte_size,
        "mime_type": source.mime_type,
        "title": payload.source_metadata.title,
        "document_kind": payload.source_metadata.document_kind,
    }
    if {key: metadata.get(key) for key in expected} != expected:
        raise NarrativeSourceGuardError(
            "INPUT_SCHEMA_INVALID",
            "current source metadata differs from the event pin",
        )
    current_language = metadata.get("language")
    if current_language not in (None, "") and current_language != payload.source_metadata.language:
        raise NarrativeSourceGuardError(
            "INPUT_SCHEMA_INVALID",
            "current source language differs from the event pin",
        )


def prompt_review_value(opened: VerifiedContent) -> PromptReviewValue:
    if opened.review is None:
        return PromptReviewValue.from_dict(
            {
                "status": "not_reviewed",
                "source_sha256": None,
                "evidence_sha256": None,
                "policy_hash": None,
                "reviewed_at": None,
            }
        )
    review = opened.review
    return PromptReviewValue.from_dict(
        {
            "status": review.status,
            "source_sha256": review.source_sha256,
            "evidence_sha256": review.evidence_sha256,
            "policy_hash": review.policy_hash,
            "reviewed_at": review.reviewed_at,
        }
    )


__all__ = [
    "NarrativeSourceGuardError",
    "NarrativeSourceReader",
    "prompt_review_value",
    "source_ref",
    "validate_opened_identity",
    "validate_opened_source",
    "validate_source_metadata",
]
