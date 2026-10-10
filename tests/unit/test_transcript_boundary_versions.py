"""Call body/end boundary fixes are versioned and replay original bytes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from company_wiki.automation.narrative_formats import parser_component
from company_wiki.source_catalog.narrative_evidence import (
    parse_transcript_text,
    select_narrative_evidence,
    transcript_parser_contract,
    verify_transcript_evidence_spans,
)
from company_wiki.source_catalog.transcript_text_extract import extract_transcript_material
from company_wiki.source_contract import source_id_for_sha256

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/narrative_real_transcript/MSFT_Q4_2026_earnings_call.txt"
FIXTURE_SHA = "4ac3b4f0fa1be928b56b4ef9775cac694a1712d46785bb1fa28d2a6a68d7852a"
OLD_030_UNITS_SHA = "2acb887d51d0aa1ffeab9bb775419624ef68a9d63c83700402c8f20c0ffa238b"
NEW_VERSION = "0.3.1"
BUSINESS = "We launched a new product and expanded overseas capacity."
FOOTER = "Website Editor: We launched invented editorial products."


def parsed(text, version=NEW_VERSION, *, source_sha256=None):
    digest = source_sha256 or hashlib.sha256(text.encode("utf-8")).hexdigest()
    return parse_transcript_text(text, source_id=source_id_for_sha256(digest),
                                 source_sha256=digest, parser_version=version)


def unit_snapshot(value):
    rows = [{"unit_id": unit.unit_id, "parser_version": unit.parser_version,
             "role": unit.source_role, "coordinates": unit.coordinates.to_dict(),
             "text": unit.raw_text, "metadata": dict(unit.metadata)} for unit in value.units]
    return hashlib.sha256(json.dumps(rows, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def test_current_parser_identity_and_public_imports_agree():
    assert transcript_parser_contract().parser_version == NEW_VERSION
    assert parser_component("text/plain", "transcript")[1] == NEW_VERSION
    result = parse_transcript_text("Full Conference Call Transcript\nCEO: " + BUSINESS,
                                   source_id=source_id_for_sha256("a" * 64),
                                   source_sha256="a" * 64)
    assert {unit.parser_version for unit in result.units} == {NEW_VERSION}


def test_generation_manifest_binds_the_actual_current_transcript_parser():
    from types import SimpleNamespace
    from company_wiki.automation.narrative_contracts import SourceRevisionEventPayload
    from company_wiki.automation.narrative_generation import generation_manifest

    payload = SourceRevisionEventPayload.from_dict({
        "schema_version": "source-revision-event/2.0",
        "source_ref": {"schema_version": "2.0", "document_id": "fixture-transcript",
                       "source_id": source_id_for_sha256(FIXTURE_SHA),
                       "content_sha256": FIXTURE_SHA, "byte_size": 66324,
                       "mime_type": "text/plain"},
        "expected_read_policy_sha256": "a" * 64,
        "source_metadata": {"source_class": "transcript", "title": "MSFT Q4 2026 earnings call",
                            "document_kind": "investor_call_transcript", "language": "en"},
    })
    manifest = generation_manifest(SimpleNamespace(model_options={}, profile="P4"), payload,
                                   execution_versions={"prompt": "fixture"})
    assert manifest["parser_component"] == {
        "name": "selective_narrative_parser", "version": NEW_VERSION}
    assert manifest["parser_component"]["version"] == transcript_parser_contract().parser_version


def test_real_fixture_excludes_editorial_roster_and_footer_and_replays_every_span():
    original = FIXTURE.read_bytes()
    assert hashlib.sha256(original).hexdigest() == FIXTURE_SHA
    material = extract_transcript_material(original, mime_type="text/plain")
    material.verify(original)
    result = parsed(material.text_utf8, source_sha256=FIXTURE_SHA)
    lines = material.text_utf8.splitlines()
    heading = lines.index("Full Conference Call Transcript") + 1
    end = next(i + 1 for i, line in enumerate(lines) if line.startswith("Operator:Ladies and gentlemen"))
    assert result.errors == () and result.coverage_complete
    assert result.units and all(heading < unit.metadata["line_start"] <= end for unit in result.units)
    assert all(unit.metadata["line_end"] <= end for unit in result.units)
    assert not any("Revenue-- $90.0 billion" in unit.raw_text or
                   "This article is a transcript" in unit.raw_text or
                   "Average returns" in unit.raw_text for unit in result.units)
    selected = select_narrative_evidence(result, title="MSFT Q4 2026 earnings call",
                                         existing_kind="investor_call_transcript")
    assert selected.status == "selected" and selected.coverage_complete
    assert selected.evidence_spans and any("Azure" in span.raw_text for span in selected.evidence_spans)
    verified, failed = verify_transcript_evidence_spans(
        material.text_utf8, source_id=result.source_id, source_sha256=result.source_sha256,
        evidence_spans=selected.evidence_spans)
    assert not failed
    assert verified == tuple(span.span_id for span in selected.evidence_spans)
    assert FIXTURE.read_bytes() == original


def test_saved_030_real_fixture_is_not_reinterpreted():
    original = FIXTURE.read_bytes()
    material = extract_transcript_material(original, mime_type="text/plain")
    result = parsed(material.text_utf8, "0.3.0", source_sha256=FIXTURE_SHA)
    assert result.errors == ("transcript_end_missing",)
    assert not result.coverage_complete and len(result.units) == 550
    assert unit_snapshot(result) == OLD_030_UNITS_SHA
    assert FIXTURE.read_bytes() == original


def test_explicit_body_takes_precedence_over_roster_like_speaker_labels():
    text = ("Earnings Call Transcript\nCALL PARTICIPANTS\n"
            "Chief Executive Officer - Jane Roe\nChief Financial Officer - Amy Doe\n"
            "Revenue-- Editorial growth metrics and commentary.\n"
            "Full Conference Call Transcript\nJane Roe, CEO: " + BUSINESS + "\n"
            "Alex Host, Operator: You may now disconnect.\n" + FOOTER)
    result = parsed(text)
    assert result.errors == () and result.coverage_complete
    assert result.units[0].metadata["line_start"] == 7
    assert result.units[0].source_role == "management"
    assert not any("Editorial" in unit.raw_text or "invented" in unit.raw_text for unit in result.units)


@pytest.mark.parametrize("ending", [
    "Alex Host, Operator: This concludes today's conference call. You may disconnect.",
    "Alex Host — Operator\nThis concludes today's conference call. You may disconnect.",
    "CEO: You may now disconnect your lines.",
])
def test_natural_body_end_marker_stops_on_any_recognized_speaker_line(ending):
    text = "Transcript\nCEO: " + BUSINESS + "\n" + ending + "\n" + FOOTER
    result = parsed(text)
    assert result.errors == () and result.coverage_complete
    assert any(BUSINESS in unit.raw_text for unit in result.units)
    assert not any("invented" in unit.raw_text for unit in result.units)


def test_natural_fallback_without_end_is_still_incomplete():
    result = parsed("Transcript\nCEO: " + BUSINESS + "\nCFO: Customer demand continues to exceed supply.")
    assert result.units
    assert result.errors == ("transcript_end_missing",)
    assert not result.coverage_complete


@pytest.mark.parametrize("version", ["0.1.0", "0.1.1", "0.2.0", "0.3.0", NEW_VERSION])
def test_explicit_legacy_format_retains_its_existing_eof_semantics(version):
    # Format coverage does not independently prove the provider captured the whole call.
    result = parsed("Full Conference Call Transcript\nCEO: " + BUSINESS, version)
    assert result.errors == () and result.coverage_complete
    assert result.units[0].raw_text == BUSINESS
    assert result.units[0].coordinates.paragraph_index == 1
    assert result.units[0].parser_version == version
