"""Worker startup and recovery use the normalization owner's version capability."""

from __future__ import annotations

import hashlib
import io
import json
from xml.sax.saxutils import escape
import zipfile

import pytest

from company_wiki.document_normalization import ReplayError
from company_wiki.document_normalization import units
from company_wiki.source_catalog.narrative_normalization import NarrativeNormalization
from company_wiki.source_contract.evidence_span import EvidenceSpan
from unit import test_narrative_worker_factory as worker_fixture
from unit.test_narrative_worker_factory import run_state as run_state


DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


def _docx():
    lines = (
        "说话人1 00:00 请问新产品何时上线？",
        "说话人2 00:39 我们计划在海外渠道推出新产品。",
        "但具体计划尚未确定，可能会发生变化。",
    )
    xml = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        + "".join(f"<w:p><w:r><w:t>{escape(text)}</w:t></w:r></w:p>" for text in lines)
        + "</w:body></w:document>"
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("word/document.xml", xml.encode("utf-8"))
    return output.getvalue(), lines


def _spans(document):
    return tuple(
        EvidenceSpan.create(
            source_id=unit.source_id,
            coordinates=unit.coordinates,
            raw_text=unit.raw_text,
            structured_value={
                **unit.metadata,
                "unit_kind": unit.unit_kind,
                "source_role": unit.source_role,
                "text_sha256": unit.text_sha256,
            },
            parser_name=unit.parser_name,
            parser_version=unit.parser_version,
            parse_status="parsed",
            quality_flags=unit.quality_flags,
        )
        for unit in document.units
    )


def test_owner_capabilities_cover_current_and_frozen_format_versions():
    expected = {
        "html": frozenset({"1.0.0"}),
        "docx": frozenset({"1.0.0", "1.1.0", "1.2.0"}),
        "pptx": frozenset({"1.0.0", "1.1.0", "2.0.0"}),
    }
    for format_name, versions in expected.items():
        assert units.supported_parser_versions(format_name) == versions
        assert units.parser_version_for_format(format_name) in versions
    assert units.supported_parser_versions() == frozenset().union(*expected.values())


@pytest.mark.parametrize("version", ["1.0.0", "1.1.0", "1.2.0", "2.0.0"])
def test_composition_accepts_any_owner_supported_version_before_mime_is_known(version):
    normalization = NarrativeNormalization(parser_versions={"document": version})
    assert normalization.parser_versions == {"document": version}


@pytest.mark.parametrize(
    "pins",
    [
        {"document": "9.9.9"},
        {"document": ""},
        {"document": 1.2},
        {"": "1.2.0"},
        ["1.2.0"],
    ],
)
def test_invalid_or_unknown_pins_still_fail_at_construction(pins):
    with pytest.raises(ValueError, match="NARRATIVE_NORMALIZATION_OPTIONS_INVALID"):
        NarrativeNormalization(parser_versions=pins)


@pytest.mark.parametrize(
    "mime,version", [(DOCX_MIME, "2.0.0"), (PPTX_MIME, "1.2.0"), ("text/html", "1.2.0")]
)
def test_mime_identity_rejects_supported_but_wrong_format_version(mime, version):
    normalization = NarrativeNormalization(parser_versions={"document": version})
    with pytest.raises(ValueError, match="unsupported normalization parser"):
        normalization.identity(mime, document_id="document")


@pytest.mark.parametrize("version", ["1.0.0", "1.1.0", "1.2.0"])
def test_docx_frozen_versions_normalize_and_replay_exact_source(version):
    data, lines = _docx()
    digest = hashlib.sha256(data).hexdigest()
    kwargs = dict(
        source_id="urn:company-wiki:source:sha256:" + digest,
        source_sha256=digest,
        mime_type=DOCX_MIME,
    )
    normalization = NarrativeNormalization(parser_versions={"document": version})
    document = normalization.normalize(data, document_id="document", **kwargs)
    assert tuple(unit.raw_text for unit in document.units) == lines
    assert {unit.parser_version for unit in document.units} == {version}
    assert normalization.replay(data, evidence_spans=_spans(document), **kwargs) == len(
        lines
    )


def test_actual_worker_options_start_current_docx_and_recover_frozen_selection(
    run_state,
    monkeypatch,
):
    """Real factory and parser ports; no model, socket, original, or production catalog."""
    factory = worker_fixture._factory()
    dependencies = []
    register = factory.register_narrative_handlers

    def capture(executor, ports):
        dependencies.append(ports)
        register(executor, ports)

    def forbidden(*args, **kwargs):
        pytest.fail("compute normalization must not construct a model or paid caller")

    monkeypatch.setattr(factory, "register_narrative_handlers", capture)
    monkeypatch.setattr(factory, "NarrativeHTTPModel", forbidden)
    monkeypatch.setattr(factory, "BudgetedNarrativeCaller", forbidden)
    options = {**run_state.options, "normalization_parsers": {"docx-document": "1.2.0"}}
    spec = worker_fixture._spec(run_state, options=options)
    data, lines = _docx()
    digest = hashlib.sha256(data).hexdigest()
    kwargs = dict(
        source_id="urn:company-wiki:source:sha256:" + digest,
        source_sha256=digest,
        mime_type=DOCX_MIME,
    )
    try:
        first = factory.create_runtime(spec)
        assert first.model_client is None
        port = dependencies[-1].normalization
        document = port.normalize(data, document_id="docx-document", **kwargs)
        assert {unit.parser_version for unit in document.units} == {"1.2.0"}
        assert {unit.source_role for unit in document.units} == {"unknown"}
        assert [
            unit.metadata["native_speaker_turn"]["speaker"] for unit in document.units
        ] == [
            "说话人1",
            "说话人2",
            "说话人2",
        ]
        serialized = json.dumps([span.to_dict() for span in _spans(document)])
        port.close()

        recovered = factory.create_runtime(spec)
        assert recovered.model_client is None
        replay_port = dependencies[-1].normalization
        assert replay_port is not port
        frozen = tuple(EvidenceSpan.from_dict(item) for item in json.loads(serialized))
        assert replay_port.replay(data, evidence_spans=frozen, **kwargs) == len(lines)
        reparsed = replay_port.normalize(data, document_id="docx-document", **kwargs)
        assert [unit.unit_id for unit in reparsed.units] == [
            unit.unit_id for unit in document.units
        ]
        assert (
            replay_port.replay(
                data, evidence_spans=(), parser_version="1.2.0", **kwargs
            )
            == 0
        )
        with pytest.raises(ReplayError, match="source bytes"):
            replay_port.replay(data + b"changed", evidence_spans=frozen, **kwargs)
    finally:
        for ports in dependencies:
            ports.normalization.close()
            ports.projection_catalog.close()
