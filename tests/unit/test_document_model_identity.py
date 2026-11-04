"""D4-03: the legacy catalog path exposes the neutral model, not a copy.

``source_catalog.narrative_document`` / ``source_catalog.transcript_layout`` are
compatibility re-exports of ``company_wiki.document_model``.  Consumers must not
split into two DTO families: the same class object, the same ``isinstance``
answer, the same frozen semantics and the same serialized evidence identity.
"""

from __future__ import annotations

import dataclasses
import hashlib

import pytest

from company_wiki.document_model import narrative as neutral_model
from company_wiki.document_model import turns as neutral_turns
from company_wiki.source_catalog import narrative_document as legacy_model
from company_wiki.source_catalog import transcript_layout as legacy_turns
from company_wiki.source_contract.evidence_span import EvidenceCoordinates

UNIT_ID = "urn:company-wiki:narrative-unit:sha256:" + hashlib.sha256(b"unit").hexdigest()


def _coordinates():
    return EvidenceCoordinates(page_number=3, paragraph_index=7, char_start=0, char_end=24)


def _unit(cls):
    return cls(
        unit_id=UNIT_ID,
        source_id="urn:company-wiki:source:sha256:" + "a" * 64,
        parser_name="cwp_document_normalization",
        parser_version="1.0.0",
        coordinates=_coordinates(),
        raw_text="营业收入为 12.3 亿元，同比增长 8%。",
        unit_kind="html_paragraph",
        source_role="company_filing",
        language="zh",
        quality_flags=("unit_inferred",),
        metadata={"native_index": 4},
    )


@pytest.mark.parametrize(
    "name",
    [
        "DocumentStructure",
        "NarrativeEvidencePackage",
        "NarrativeParseResult",
        "NarrativeUnit",
        "selected_summary_input",
    ],
)
def test_legacy_document_names_are_the_neutral_objects(name):
    assert getattr(legacy_model, name) is getattr(neutral_model, name)


@pytest.mark.parametrize(
    "name",
    [
        "END",
        "NATURAL_START",
        "QA_HEADING",
        "AnonymousTurnObserver",
        "body_start",
        "legacy_speaker_fields",
        "speaker_fields",
        "valid_speaker",
    ],
)
def test_legacy_turn_names_are_the_neutral_objects(name):
    assert getattr(legacy_turns, name) is getattr(neutral_turns, name)


def test_neutral_owner_defines_the_classes():
    assert neutral_model.NarrativeUnit.__module__ == "company_wiki.document_model.narrative"
    assert (
        neutral_model.DocumentStructure.__module__
        == "company_wiki.document_model.narrative"
    )
    assert neutral_turns.AnonymousTurnObserver.__module__ == "company_wiki.document_model.turns"


def test_construction_and_isinstance_do_not_split_across_paths():
    from_legacy = _unit(legacy_model.NarrativeUnit)
    from_neutral = _unit(neutral_model.NarrativeUnit)

    assert isinstance(from_legacy, neutral_model.NarrativeUnit)
    assert isinstance(from_neutral, legacy_model.NarrativeUnit)
    assert type(from_legacy) is type(from_neutral)
    assert from_legacy == from_neutral

    legacy_structure = legacy_model.DocumentStructure(
        source_id=from_legacy.source_id,
        source_sha256=from_legacy.source_id.rsplit(":", 1)[1],
        language="zh",
        units=(from_legacy,),
        line_count=1,
    )
    assert isinstance(legacy_structure, neutral_model.DocumentStructure)
    assert isinstance(legacy_structure, legacy_model.NarrativeParseResult)
    assert legacy_structure.coverage_complete is True


def test_legacy_path_keeps_frozen_and_serialized_identity():
    unit = _unit(legacy_model.NarrativeUnit)

    with pytest.raises(dataclasses.FrozenInstanceError):
        unit.raw_text = "tampered"  # type: ignore[misc]
    with pytest.raises(TypeError):
        unit.metadata["native_index"] = 5  # type: ignore[index]

    span = unit.to_evidence_span(topics=("revenue",), selection_reasons=("numeric",))
    neutral_span = _unit(neutral_model.NarrativeUnit).to_evidence_span(
        topics=("revenue",), selection_reasons=("numeric",)
    )
    assert span.span_id == neutral_span.span_id
    assert span.raw_text == neutral_span.raw_text
    assert span.parser_name == neutral_span.parser_name
    assert dict(span.structured_value) == dict(neutral_span.structured_value)

    package = legacy_model.NarrativeEvidencePackage(
        source_id=unit.source_id,
        source_sha256=span.structured_value["text_sha256"],
        document_kind="annual_report",
        status="selected",
        evidence_spans=(span,),
        selection_limit=10,
        candidate_count=1,
        dropped_financial_count=0,
        source_units=1,
        omitted_candidate_count=0,
        coverage_complete=True,
    )
    assert package.summary_input() == neutral_model.selected_summary_input(
        source_id=unit.source_id,
        source_sha256=span.structured_value["text_sha256"],
        document_kind="annual_report",
        evidence_spans=(span,),
    )


def test_anonymous_turn_observer_keeps_saved_txt_and_native_turn_semantics():
    observer = legacy_turns.AnonymousTurnObserver()
    expected_turn_id = "native-speaker:" + hashlib.sha256(
        "\0".join(("src-1", "line:7", "Speaker 1", "00:00:05")).encode()
    ).hexdigest()

    first = observer.observe("Speaker 1 00:00:05", source_id="src-1", locator="line:7")
    assert first == {
        "speaker": "Speaker 1",
        "timestamp": "00:00:05",
        "turn_id": expected_turn_id,
    }
    # The active turn carries over to continuation paragraphs until a new label.
    assert observer.observe("Revenue grew 8% year on year.", source_id="src-1", locator="line:8") == first

    # A plain speaker label is a structural boundary, not a native turn.
    observer.clear()
    assert observer.observe("Jane Doe:", source_id="src-1", locator="line:9") is None
    assert observer.observe("We expanded capacity.", source_id="src-1", locator="line:10") is None

    # The end control closes the source once and stays closed.
    assert observer.observe("End of transcript", source_id="src-1", locator="line:11") is None
    assert observer.closed is True
    assert observer.observe("Speaker 2 00:09:00", source_id="src-1", locator="line:12") is None


def test_legacy_grammar_still_parses_saved_label_forms():
    assert legacy_turns.legacy_speaker_fields("Jane Doe: hello") == ("Jane Doe", "", "hello")
    assert legacy_turns.legacy_speaker_fields("Jane Doe -- CFO") == ("Jane Doe", "CFO", "")
    assert legacy_turns.valid_speaker("Jane Doe") is True
    assert legacy_turns.valid_speaker("Revenue") is False
    assert legacy_turns.QA_HEADING.fullmatch("Q&A Session")
    assert legacy_turns.NATURAL_START.fullmatch("Acme Fourth Quarter Earnings Conference Call")
    assert legacy_turns.END.fullmatch("End of transcript")
