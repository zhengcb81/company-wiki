"""Source metadata guards with sparse, byte-pinned narrative language."""

from __future__ import annotations

import hashlib

import pytest

from company_wiki.automation.narrative_contracts import SourceRevisionEventPayload
from company_wiki.automation.narrative_source_guard import (
    NarrativeSourceGuardError,
    validate_source_metadata,
)
from company_wiki.source_contract.source_manifest import source_id_for_sha256


def _payload() -> SourceRevisionEventPayload:
    data = b"verified source bytes"
    digest = hashlib.sha256(data).hexdigest()
    return SourceRevisionEventPayload.from_dict({
        "schema_version": "source-revision-event/2.0",
        "source_ref": {
            "schema_version": "2.0",
            "document_id": "doc-ir",
            "source_id": source_id_for_sha256(digest),
            "content_sha256": digest,
            "byte_size": len(data),
            "mime_type": "text/plain",
        },
        "expected_read_policy_sha256": "b" * 64,
        "source_metadata": {
            "source_class": "filing",
            "title": None,
            "document_kind": "investor_relations",
            "language": "zh",
        },
    })


def _sparse_manifest(payload: SourceRevisionEventPayload) -> dict[str, object]:
    source = payload.source_ref
    return {
        "document_id": source.document_id,
        "source_id": source.source_id,
        "content_sha256": source.content_sha256,
        "byte_size": source.byte_size,
        "mime_type": source.mime_type,
        "title": None,
        "document_kind": "investor_relations",
        "language": None,
    }


def test_inferred_language_is_accepted_when_catalog_language_is_unavailable():
    payload = _payload()
    validate_source_metadata(payload, _sparse_manifest(payload))


def test_changed_catalog_language_is_auxiliary_to_byte_pinned_language():
    payload = _payload()
    manifest = _sparse_manifest(payload)
    manifest["language"] = "en"
    validate_source_metadata(payload, manifest)


@pytest.mark.parametrize("field,value", [("title", "Corrected title"), ("language", "en")])
def test_auxiliary_declaration_drift_does_not_deny_byte_pinned_processing(field, value):
    payload = _payload()
    manifest = _sparse_manifest(payload)
    manifest[field] = value
    validate_source_metadata(payload, manifest)


def test_generation_read_fingerprint_is_not_a_worker_permission():
    from company_wiki.automation.narrative_source_guard import validate_opened_identity
    from company_wiki.source_catalog.source_reader import VerifiedContent
    payload = _payload()
    opened = VerifiedContent(document_id=payload.source_ref.document_id,
        source_id=payload.source_ref.source_id, content_sha256=payload.source_ref.content_sha256,
        data=b"verified source bytes", byte_size=payload.source_ref.byte_size,
        read_at="2026-10-08T00:00:00Z", policy_sha256="a" * 64, source_read_policy_sha256="c" * 64)
    validate_opened_identity(payload, opened)
    from dataclasses import replace
    with pytest.raises(NarrativeSourceGuardError, match="SOURCE_HASH_MISMATCH"):
        validate_opened_identity(payload, replace(opened, data=b"X" * len(opened.data)))
