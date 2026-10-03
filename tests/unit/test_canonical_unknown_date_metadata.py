"""Malformed rows cannot crash or satisfy unknown-date original verification."""

from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace

import pytest

from company_wiki.source_catalog import DownloadCandidate, SourceRequest
from company_wiki.source_catalog.canonical_writer import (
    CanonicalImportError,
    CanonicalSourceWriter,
)
from company_wiki.source_contract import source_id_for_sha256


CONTENT_SHA = hashlib.sha256(b"original transcript bytes").hexdigest()
MALFORMED_METADATA = ('["not an object"]', '{"acquisition":["not an object"]}')


def _case(metadata_values: tuple[str, ...]):
    request = SourceRequest(
        entity="Acme Inc.", market="US", security_id="ACME",
        document_kind="investor_call_transcript", fiscal_year=2026,
        fiscal_period="Q2", as_of_date="2026-09-27", provider="fixture",
        provider_document_id="acme-2026-q2",
    )
    candidate = DownloadCandidate(
        candidate_id="candidate-1", provider="fixture",
        provider_document_id="acme-2026-q2", market="US", entity=request.entity,
        title="Acme 2026 Q2 Earnings Call",
        source_url="https://fixtures.invalid/call.json",
        document_kind="investor_call_transcript", filing_date=None,
        fiscal_year=2026, fiscal_period="Q2",
    )
    rows = [
        {
            "document_id": f"doc-{index}",
            "metadata_json": value,
            "published_date": None,
            "source_status": "active",
            "primary_source_id": source_id_for_sha256(CONTENT_SHA),
        }
        for index, value in enumerate(metadata_values)
    ]
    # Exercise the verifier against its read port; no original or catalog is written.
    writer = CanonicalSourceWriter.__new__(CanonicalSourceWriter)
    writer.catalog = SimpleNamespace(
        reader=SimpleNamespace(
            query=lambda **kwargs: rows,
            source_sha=lambda source_id: CONTENT_SHA,
        )
    )
    return writer, request, candidate


@pytest.mark.parametrize("metadata_json", MALFORMED_METADATA)
def test_unknown_date_original_rejects_malformed_metadata_without_crashing(metadata_json):
    writer, request, candidate = _case((metadata_json,))
    with pytest.raises(CanonicalImportError, match="not indexed to its verified bytes"):
        writer._verify_unknown_date_index(request, candidate, CONTENT_SHA)


@pytest.mark.parametrize("metadata_json", MALFORMED_METADATA)
def test_unknown_date_original_can_match_a_valid_row_after_malformed_metadata(metadata_json):
    valid = json.dumps({
        "acquisition": {
            "provider_document_id": "acme-2026-q2", "provider": "fixture",
            "company_name": "Acme Inc.", "security_id": "ACME", "market": "US",
        }
    })
    writer, request, candidate = _case((metadata_json, valid))
    assert writer._verify_unknown_date_index(request, candidate, CONTENT_SHA) == "doc-1"
