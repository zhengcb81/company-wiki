"""Import receives a per-original limit, independent of already consumed network bytes."""
from __future__ import annotations

from dataclasses import replace
import io
import json

import pytest

from company_wiki.source_catalog.canonical_writer import CanonicalSourceWriter
from company_wiki.source_catalog.transcript_import import import_transcript_tool_result
from company_wiki.source_catalog.transcript_import_cli import _read_envelope
from company_wiki.source_catalog.transcript_tool_contract import (
    TranscriptToolContractError, parse_transcript_tool_result,
)
from test_transcript_original_import import _fixture, _result


def test_explicit_original_budget_survives_import_and_verified_reuse(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    catalog, request, candidate, _ = _fixture(root)
    # Non-provider-specific HTML exercises the same pure bytes/import owner.
    body = b"<html><body><p>CEO: " + b"new products " * 1400000 + b"</p></body></html>"
    assert 16 * 1024 * 1024 < len(body) < 22 * 1024 * 1024
    try:
        writer = CanonicalSourceWriter(catalog)
        raw = _result(request, candidate, body)
        imported = import_transcript_tool_result(raw, request=request, candidate=candidate,
            writer=writer, now="2026-09-27T12:01:00Z", max_original_bytes=22 * 1024 * 1024)
        from pathlib import Path
        assert Path(imported.canonical_import.canonical_path).read_bytes() == body
        again = import_transcript_tool_result(raw, request=request, candidate=candidate,
            writer=writer, now="2026-09-27T12:01:00Z", max_original_bytes=22 * 1024 * 1024)
        assert again.canonical_import.source_id == imported.canonical_import.source_id
        assert not list(writer.staging_root.glob("transcript-*"))
    finally:
        catalog.close()


def test_budget_is_not_a_second_network_charge_and_bad_core_still_fails(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    catalog, request, candidate, body = _fixture(root)
    try:
        raw = _result(request, candidate, body)
        assert parse_transcript_tool_result(raw, request=request, candidate=candidate,
            max_bytes=22 * 1024 * 1024).original == body
        with pytest.raises(TranscriptToolContractError, match="byte cap"):
            parse_transcript_tool_result(raw, request=request, candidate=candidate, max_bytes=2)
        with pytest.raises(TranscriptToolContractError, match="SHA-256"):
            parse_transcript_tool_result(_result(request, candidate, body, provider_payload_sha256="0"*64),
                request=request, candidate=candidate, max_bytes=22 * 1024 * 1024)
        with pytest.raises(TranscriptToolContractError, match="request_id|security|ticker"):
            parse_transcript_tool_result(raw, request=replace(request, security_id="OTHER"),
                candidate=candidate, max_bytes=22 * 1024 * 1024)
    finally:
        catalog.close()


def test_envelope_size_is_an_explicit_transport_allocation():
    # JSON representation is not the original document byte budget.
    request = {"schema_version": "company-wiki-transcript-import-request/2",
        "source_request": {}, "candidate": {}, "transcript_result": {}}
    raw = json.dumps(request).encode() + b" " * (26 * 1024 * 1024)
    assert _read_envelope(io.BytesIO(raw)) == request
    with pytest.raises(ValueError, match="oversized"):
        _read_envelope(io.BytesIO(raw), max_bytes=100)
