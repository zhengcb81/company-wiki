"""FMP /2 transcript producer contract and date provenance."""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from company_wiki.source_catalog.acquisition import DownloadCandidate
from company_wiki.source_catalog.resolver import SourceRequest
from company_wiki.source_catalog.transcript_tool_contract import (
    TranscriptToolContractError,
    parse_transcript_tool_result,
)


GOLDEN = Path(__file__).parents[1] / "fixtures" / "transcript_fmp" / "fmp_v2.fetched.json"


def _inputs():
    envelope = json.loads(GOLDEN.read_text(encoding="utf-8"))
    request = SourceRequest(
        entity="Microsoft Corporation", market="US", security_id="MSFT",
        document_kind="investor_call_transcript", fiscal_year=2026,
        fiscal_period="Q3", language="en", as_of_date="2026-09-30",
        allow_download=True,
    )
    candidate = DownloadCandidate(
        candidate_id="fmp-msft-2026-q3", provider="fmp",
        provider_document_id=envelope["provider_document_id"], market="US",
        entity=request.entity, title=envelope["title"], source_url=envelope["source_url"],
        document_kind="investor_call_transcript", filing_date=None,
        fiscal_year=2026, fiscal_period="Q3", language="en",
        adapter_payload_json=json.dumps({"market":"US","security_id":"MSFT","exchange":"nasdaq"}),
    )
    return envelope, request, candidate


def _parse(payload=None, request=None, candidate=None):
    golden, default_request, default_candidate = _inputs()
    payload = payload or golden
    request = request or default_request
    candidate = candidate or default_candidate
    payload["request_id"] = request.request_id
    return parse_transcript_tool_result(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        request=request, candidate=candidate,
    )


def test_fmp_golden_preserves_call_date_and_unknown_publication():
    payload, _, _ = _inputs()
    accepted = _parse()
    assert accepted.original == base64.b64decode(payload["provider_payload_base64"])
    assert accepted.call_date == "2026-07-22"
    assert accepted.publication_date is None
    assert accepted.as_of_cutoff_verified is False
    assert accepted.canonical_content_sha256 == payload["canonical_content_sha256"]
    assert accepted.content_bytes == payload["content_bytes"]


@pytest.mark.parametrize("field,value", [
    ("provider_payload_sha256", "0" * 64),
    ("canonical_content_sha256", "0" * 64),
    ("content_bytes", 1),
    ("call_date", "2026-10-01"),
    ("as_of_cutoff_verified", True),
])
def test_fmp_inconsistent_dates_or_hashes_are_rejected(field, value):
    payload, _, _ = _inputs()
    payload[field] = value
    with pytest.raises(TranscriptToolContractError):
        _parse(payload)


@pytest.mark.parametrize("url", [
    "https://financialmodelingprep.com/stable/earning-call-transcript?symbol=MSFT&year=2026&quarter=3&apikey=secret",
    "https://financialmodelingprep.com/stable/earning-call-transcript?symbol=MSFT&symbol=MSFT&year=2026&quarter=3",
    "https://financialmodelingprep.com/stable/earning-call-transcript?symbol=MSFT&year=2026&quarter=4",
    "https://evil.invalid/stable/earning-call-transcript?symbol=MSFT&year=2026&quarter=3",
    "https://financialmodelingprep.com/other?symbol=MSFT&year=2026&quarter=3",
])
def test_fmp_source_url_is_exact_and_secret_free(url):
    payload, _, candidate = _inputs()
    payload["source_url"] = url
    payload["effective_url"] = url
    candidate = replace(candidate, source_url=url)
    with pytest.raises(TranscriptToolContractError):
        _parse(payload, candidate=candidate)


def test_fmp_json_record_identity_is_bound_to_envelope():
    payload, _, _ = _inputs()
    original = json.loads(base64.b64decode(payload["provider_payload_base64"]))
    original[0]["symbol"] = "OTHER"
    encoded = json.dumps(original).encode()
    payload["provider_payload_base64"] = base64.b64encode(encoded).decode()
    payload["provider_payload_sha256"] = hashlib.sha256(encoded).hexdigest()
    with pytest.raises(TranscriptToolContractError):
        _parse(payload)


@pytest.mark.parametrize("extra", [{"padding": "x" * 20000},
                                  {"provider_metadata": {"revision": 2, "optional": None}}])
def test_fmp_extra_provider_fields_preserve_raw_and_do_not_change_content(extra):
    payload, _, _ = _inputs()
    records = json.loads(base64.b64decode(payload["provider_payload_base64"]))
    records[0].update(extra)
    original = json.dumps(records, ensure_ascii=False).encode("utf-8")
    payload["provider_payload_base64"] = base64.b64encode(original).decode()
    payload["provider_payload_sha256"] = hashlib.sha256(original).hexdigest()
    accepted = _parse(payload)
    assert accepted.original == original
    assert accepted.content_bytes == payload["content_bytes"]
    assert accepted.canonical_content_sha256 == payload["canonical_content_sha256"]


@pytest.mark.parametrize("field,value", [("symbol", "OTHER"), ("year", True),
                                        ("period", "Q4"), ("content", "other text")])
def test_fmp_extra_metadata_never_hides_changed_required_content(field, value):
    payload, _, _ = _inputs()
    records = json.loads(base64.b64decode(payload["provider_payload_base64"]))
    records[0].update({"provider_metadata": {}, field: value})
    original = json.dumps(records).encode()
    payload["provider_payload_base64"] = base64.b64encode(original).decode()
    payload["provider_payload_sha256"] = hashlib.sha256(original).hexdigest()
    with pytest.raises(TranscriptToolContractError):
        _parse(payload)
