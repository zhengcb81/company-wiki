"""The transport consumes an injected normalization port, not its reader's config.

A source implementation that satisfies the read protocol carries no catalog
and no project layout.  Whether a PPTX replay can use OCR is therefore bound
once by the composition root and is identical for every protocol-conformant
source; a missing configuration is a named refusal, never a silent downgrade.
"""
from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path

import pytest

from company_wiki.automation.narrative_transport import NarrativeTransportReader
from company_wiki.automation.narrative_transport_contracts import (
    NarrativeReadRequest,
    NarrativeTransportError,
)
from company_wiki.document_normalization.units import PPTX_PARSER_VERSION
from company_wiki.source_catalog.narrative_normalization import (
    NarrativeNormalization,
    PPTX_MIME,
)
from support.narrative_transport_fixture import published_fixture


BUSINESS = "Company launched a new product and expanded overseas capacity for new customers."


def _pptx_bytes() -> bytes:
    from pptx import Presentation
    from pptx.util import Inches

    deck = Presentation()
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    slide.shapes.add_textbox(0, 0, Inches(7), Inches(2)).text = BUSINESS
    buffer = BytesIO()
    deck.save(buffer)
    return buffer.getvalue()


class _ProtocolOnlySource:
    """Delegate the three protocol members; refuse any runtime discovery."""

    def __init__(self, inner):
        self._inner = inner

    def query_ref(self, document_id, source_id, expected_sha256):
        return self._inner.query_ref(document_id, source_id, expected_sha256)

    def open_described_version(self, ref, *, purpose, **kwargs):
        return self._inner.open_described_version(ref, purpose=purpose, **kwargs)

    def availability_evidence(self, ref):
        return self._inner.availability_evidence(ref)

    def __getattr__(self, name):
        if name in {"catalog", "config"}:
            raise AttributeError(
                "protocol-only source has no %s" % name
            )
        raise AttributeError(name)


def _read(transport, fixture):
    reference = transport.reference(fixture.source_ref)
    request = fixture.read_request(reference)
    return transport.read(NarrativeReadRequest.from_dict(request))


def test_transport_replays_ocr_capable_source_with_protocol_only_reader(
    tmp_path: Path,
) -> None:
    """One injected normalization serves the real reader and a protocol stub."""
    with published_fixture(tmp_path, source_spec={
        "name": "source.pptx", "data": _pptx_bytes(), "language": "en",
        "title": "Company annual business update", "document_kind": "annual_report",
    }) as fixture:
        assert fixture.source_ref.mime_type == PPTX_MIME
        # The composition-root pattern: bind the project's OCR location once,
        # without the reader being involved at all.
        normalization = NarrativeNormalization.deferred_from_project(
            fixture.catalog.config.project_root,
        )
        real = NarrativeTransportReader(
            fixture.artifacts, fixture.reader, normalization=normalization,
        )
        stub = NarrativeTransportReader(
            fixture.artifacts, _ProtocolOnlySource(fixture.reader),
            normalization=normalization,
        )
        from_real = _read(real, fixture)
        from_stub = _read(stub, fixture)
        assert from_stub.data == from_real.data == fixture.payload
        payload = json.loads(from_stub.data)
        assert payload["versions"]["parser"] == PPTX_PARSER_VERSION
        assert from_stub.receipt["status"] == from_real.receipt["status"] == "ok"
        assert from_stub.receipt["replay_status"] == "verified"
        assert from_stub.receipt["locator_count"] == from_real.receipt["locator_count"]


def test_unbound_normalization_is_identical_for_both_reader_shapes(
    tmp_path: Path,
) -> None:
    """Without injection both shapes get the same neutral, config-free port."""
    with published_fixture(tmp_path, source_spec={
        "name": "source.pptx", "data": _pptx_bytes(), "language": "en",
        "title": "Company annual business update", "document_kind": "annual_report",
    }) as fixture:
        real = NarrativeTransportReader(fixture.artifacts, fixture.reader)
        stub = NarrativeTransportReader(
            fixture.artifacts, _ProtocolOnlySource(fixture.reader),
        )
        from_real = _read(real, fixture)
        from_stub = _read(stub, fixture)
        assert from_stub.data == from_real.data == fixture.payload
        assert from_stub.receipt["replay_status"] == "verified"
        assert json.loads(from_stub.data)["versions"]["parser"] == PPTX_PARSER_VERSION


def test_ocr_demanding_replay_without_config_is_a_named_refusal() -> None:
    """A PPTX generation that needs OCR fails by name when no config is bound."""
    from company_wiki.document_normalization import LocalOCRError

    with pytest.raises(LocalOCRError) as refused:
        NarrativeNormalization().identity(PPTX_MIME, parser_version="2.0.0")
    assert refused.value.args[0] == "OCR_ADAPTER_REQUIRED"


def test_bound_config_replays_the_ocr_generation_without_reader_discovery(
    tmp_path: Path,
) -> None:
    """An explicitly bound config answers the OCR generation's identity."""
    normalization = NarrativeNormalization.deferred_from_project(
        Path(__file__).resolve().parents[2],
    )
    identity = normalization.identity(PPTX_MIME, parser_version="2.0.0")
    assert identity["parser_version"] == "2.0.0"
    # The deferred loader opened the config exactly once, on demand.
    assert normalization.config is not None
    assert normalization.config is normalization.config
