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


def test_nonempty_catalog_language_must_match_the_byte_pinned_language():
    payload = _payload()
    manifest = _sparse_manifest(payload)
    manifest["language"] = "en"

    with pytest.raises(NarrativeSourceGuardError) as error:
        validate_source_metadata(payload, manifest)

    assert error.value.code == "INPUT_SCHEMA_INVALID"
