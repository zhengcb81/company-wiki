"""The catalog's exact-byte observation survives native locator replay."""

from dataclasses import replace
import hashlib

import pytest

from company_wiki.automation.models import HandlerOutcome
from company_wiki.automation.narrative_contracts import SourceRevisionEventPayload
from company_wiki.automation.narrative_select import NarrativeSelectHandler
from company_wiki.automation.narrative_transport import NarrativeTransportReader
from company_wiki.automation.narrative_transport_contracts import NarrativeReadRequest
from company_wiki.automation.narrative_verify import NarrativeVerifyHandler
from company_wiki.source_catalog.narrative_evidence import verify_pdf_evidence_spans_bytes
from company_wiki.source_catalog.narrative_pdf_reading import NativePdfBackend, PdfReading
from support.narrative_transport_fixture import published_fixture
from unit import test_narrative_verify_handler as verify_fixture


def _count_original_hashes(monkeypatch, original):
    checks = []
    sha256 = hashlib.sha256

    class ObservedHash:
        def __init__(self, digest):
            self._digest = digest

        def update(self, data):
            if data == original:
                checks.append("stream")
            self._digest.update(data)

        def __getattr__(self, name):
            return getattr(self._digest, name)

    def counted(data=b"", **kwargs):
        if data == original:
            checks.append("buffer")
        return ObservedHash(sha256(data, **kwargs))

    monkeypatch.setattr(hashlib, "sha256", counted)
    return checks


@pytest.mark.parametrize("entry", ["transport", "verify"])
def test_native_pdf_entry_hashes_the_original_once(tmp_path, monkeypatch, entry):
    with published_fixture(tmp_path, kind="pdf") as fixture:
        if entry == "transport":
            transport = NarrativeTransportReader(fixture.artifacts, fixture.reader)
            reference = transport.reference(fixture.source_ref)
            request = NarrativeReadRequest.from_dict(fixture.read_request(reference))
            checks = _count_original_hashes(monkeypatch, fixture.raw_bytes)
            result = transport.read(request)
            assert result.data == fixture.payload
            assert result.receipt["locator_count"] > 0
        else:
            payload = SourceRevisionEventPayload.from_dict({
                "schema_version": "source-revision-event/2.0",
                "source_ref": fixture.source_ref.to_dict(),
                "expected_read_policy_sha256": fixture.reader.read_policy_sha256(),
                "source_metadata": {
                    "source_class": "filing", "title": "ACME business update",
                    "document_kind": "annual_report", "language": "en",
                },
            })
            selected = NarrativeSelectHandler(reader=fixture.reader).select_source(payload, checkpoint=lambda: None)
            summary = verify_fixture._summary(selected)
            handler = NarrativeVerifyHandler(reader=fixture.reader)
            checks = _count_original_hashes(monkeypatch, fixture.raw_bytes)
            result = handler(verify_fixture._context(selected, summary))
            assert result.outcome is HandlerOutcome.SUCCEEDED, result.error
            assert len(result.effects) == 1
        assert checks == ["stream"]


def test_standalone_pdf_replay_hashes_supplied_bytes_once(monkeypatch):
    data, selected = verify_fixture._selected()
    arguments = dict(source_id=selected.source_ref.source_id,
                     source_sha256=selected.source_ref.content_sha256,
                     evidence_spans=selected.evidence_spans, language=selected.source_metadata.language)
    checks = _count_original_hashes(monkeypatch, data)
    verified, failed = verify_pdf_evidence_spans_bytes(data, **arguments)
    assert verified == tuple(span.span_id for span in selected.evidence_spans) and not failed
    assert checks == ["buffer"]
    with pytest.raises(ValueError, match="changed"):
        verify_pdf_evidence_spans_bytes(data + b"different", **arguments)


@pytest.mark.parametrize("entry", ["transport", "select"])
def test_native_html_entry_hashes_the_original_once(tmp_path, monkeypatch, entry):
    html = (b"<html><body><h1>Annual report</h1><h2>Business review</h2>"
            b"<p>Our company launched a new product and expanded overseas capacity for customers.</p>"
            b"</body></html>")
    with published_fixture(tmp_path, kind="pdf", source_spec={
        "name": "results.html", "data": html, "document_kind": "annual_report",
    }) as fixture:
        if entry == "transport":
            reader = NarrativeTransportReader(fixture.artifacts, fixture.reader)
            request = NarrativeReadRequest.from_dict(fixture.read_request(reader.reference(fixture.source_ref)))
            checks = _count_original_hashes(monkeypatch, html)
            result = reader.read(request)
            assert result.data == fixture.payload
            assert result.receipt["locator_count"] > 0
        else:
            payload = SourceRevisionEventPayload.from_dict({
                "schema_version": "source-revision-event/2.0",
                "source_ref": fixture.source_ref.to_dict(),
                "expected_read_policy_sha256": fixture.reader.read_policy_sha256(),
                "source_metadata": {
                    "source_class": "filing", "title": "ACME business update",
                    "document_kind": "annual_report", "language": "en",
                },
            })
            checks = _count_original_hashes(monkeypatch, html)
            result = NarrativeSelectHandler(reader=fixture.reader).select_source(
                payload, checkpoint=lambda: None,
            )
            assert result.evidence_spans
        assert checks == ["stream"]


@pytest.mark.parametrize("port", ["callback", "backend"])
def test_verified_replay_still_invokes_custom_pdf_replay(port):
    from company_wiki.source_catalog.narrative_material_replay import replay_verified_narrative_evidence

    data, selected = verify_fixture._selected()
    opened = verify_fixture.FakeReader(selected, data).opened
    calls = []

    def replay(raw, **arguments):
        calls.append((raw, arguments))
        return tuple(span.span_id for span in selected.evidence_spans), ()

    class CustomBackend(NativePdfBackend):
        def replay(self, raw, **arguments):
            return replay(raw, **arguments)

    reading = PdfReading(replayer=replay) if port == "callback" else PdfReading(CustomBackend())
    assert replay_verified_narrative_evidence(opened, selected, pdf_reading=reading) == len(selected.evidence_spans)
    assert len(calls) == 1 and calls[0][0] is data
    assert calls[0][1]["source_id"] == selected.source_ref.source_id
    assert calls[0][1]["source_sha256"] == selected.source_ref.content_sha256


@pytest.mark.parametrize("field,value", [
    ("document_id", "wrong-document"), ("source_id", "wrong-source"),
    ("content_sha256", "0" * 64), ("byte_size", 1),
])
def test_verified_replay_rejects_a_different_source_identity(field, value):
    from company_wiki.source_catalog.narrative_material_replay import (
        NarrativeReplayError, replay_verified_narrative_evidence,
    )

    data, selected = verify_fixture._selected()
    opened = verify_fixture.FakeReader(selected, data).opened
    with pytest.raises(NarrativeReplayError, match="verified source"):
        replay_verified_narrative_evidence(replace(opened, **{field: value}), selected)
