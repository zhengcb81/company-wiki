"""Current material requests are explicit; invalid dates are never a fallback."""
from __future__ import annotations

import pytest

from company_wiki.automation.narrative_contracts import NarrativeContractError
from company_wiki.automation.narrative_transport_contracts import NarrativeReadRequest


def _request(cutoff):
    digest = "a" * 64
    return {"schema_version": "narrative-read-request/1", "as_of_date": cutoff,
            "narrative_ref": {"schema_version": "narrative-ref/1",
                "artifact_version_id": "artifact-1", "artifact_sha256": "b" * 64,
                "byte_size": 1, "source_ref": {"schema_version": "2.0",
                    "document_id": "urn:company-wiki:document:sha256:" + digest,
                    "source_id": "urn:company-wiki:source:sha256:" + digest,
                    "content_sha256": digest, "byte_size": 1, "mime_type": "text/plain"}},
            "expected_source": dict.fromkeys(("canonical_entity_id", "market", "security_id",
                "document_kind", "fiscal_year", "fiscal_period"))}


@pytest.mark.parametrize("cutoff", [None, "2026-10-08"])
def test_explicit_current_or_historical_request_round_trips(cutoff):
    request = _request(cutoff)
    assert NarrativeReadRequest.from_dict(request).to_dict() == request


@pytest.mark.parametrize("cutoff", ["", "2026-02-30", "2026-1-01", 0, False, [], {}])
def test_malformed_date_cannot_select_current_mode(cutoff):
    with pytest.raises(NarrativeContractError):
        NarrativeReadRequest.from_dict(_request(cutoff))


def test_missing_cutoff_does_not_implicitly_select_current_mode():
    request = _request(None)
    del request["as_of_date"]
    with pytest.raises(NarrativeContractError):
        NarrativeReadRequest.from_dict(request)
