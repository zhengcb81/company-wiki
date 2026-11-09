"""Reviewed source/identity changes across synthetic TXT transport snapshots."""
from copy import deepcopy

from company_wiki.automation.narrative_contracts import NarrativeBundle
from company_wiki.source_catalog.narrative_business_policy import detect_business_fact
from company_wiki.source_catalog.narrative_evidence import verify_transcript_evidence_spans
from company_wiki.source_contract import EvidenceCoordinates, EvidenceSpan
from support.narrative_transport_fixture import TXT


OLD_TOPICS = ["new_business", "overseas", "capacity_projects", "products_rd"]
OLD_REASONS = ["business_narrative_signal", "progress_or_change_language", "specific_business_event", "management_statement"]
NEW_REASONS = ["business_narrative_signal", "specific_business_event", "progress_or_change_language", "management_statement"]


def assert_reviewed_transcript_evolution(old, current):
    """Allow only the 12 inspected provenance/tagging/derived identity changes."""
    assert len(old["evidence_spans"]) == len(current["evidence_spans"]) == 1
    prior = old["evidence_spans"][0]
    assert prior["structured_value"]["topics"] == OLD_TOPICS
    assert prior["structured_value"]["selection_reasons"] == OLD_REASONS
    assert old["versions"]["parser"] == "0.1.1"
    assert old["versions"]["prompt"] == "1.6.0"
    assert old["versions"]["selector"] == "0.4.2"
    expected = deepcopy(old)
    structured = deepcopy(prior["structured_value"])
    structured["topics"] = [*OLD_TOPICS, "core_business"]
    structured["selection_reasons"] = NEW_REASONS
    span = EvidenceSpan.create(
        source_id=prior["source_id"], coordinates=EvidenceCoordinates.from_dict(prior["coordinates"]),
        raw_text=prior["raw_text"], structured_value=structured,
        parser_name=prior["parser_name"], parser_version="0.3.1",
        parse_status=prior["parse_status"], quality_flags=prior["quality_flags"],
    )
    expected["evidence_spans"] = [span.to_dict()]
    expected["versions"].update(parser="0.3.1", prompt="1.7.0", selector="0.8.0")
    expected["summary"]["model"]["prompt_version"] = "1.7.0"
    expected["summary"]["draft"]["claims"][0]["evidence_ids"] = [span.span_id]
    expected["transcript_byte_bindings"][0]["evidence_id"] = span.span_id
    assert current == expected, "unreviewed source, fact, unit, citation, or metadata change"
    assert span.span_id != prior["span_id"]
    assert "core_business" in detect_business_fact(span.raw_text).topics
    # The new tag classifies the exact same launched-product/expanded-capacity
    # sentence. It neither adds an operating claim nor supplies a new number.
    _assert_transcript_replays(old, current, prior["raw_text"])


def assert_reviewed_transcript_evolution_v2_to_v3(old, current):
    """Allow only the reviewed parser and operating-tag update from v2 to v3."""
    assert len(old["evidence_spans"]) == len(current["evidence_spans"]) == 1
    prior = old["evidence_spans"][0]
    assert old["versions"]["parser"] == "0.3.1"
    assert old["versions"]["selector"] == "0.8.0"
    assert old["versions"]["prompt"] == "1.7.0"
    assert prior["parser_version"] == "0.3.1"
    assert prior["structured_value"]["topics"] == [
        "new_business", "overseas", "capacity_projects", "products_rd", "core_business",
    ]
    assert prior["structured_value"]["selection_reasons"] == [
        "business_narrative_signal", "specific_business_event",
        "progress_or_change_language", "management_statement",
    ]

    expected = deepcopy(old)
    structured = deepcopy(prior["structured_value"])
    structured["topics"] = [
        *structured["topics"], "operating_mechanism", "business_progress",
    ]
    structured["selection_reasons"] = [
        "business_narrative_signal", "specific_business_event", "operating_mechanism",
        "operating_activity", "progress_or_change_language", "management_statement",
    ]
    span = EvidenceSpan.create(
        source_id=prior["source_id"], coordinates=EvidenceCoordinates.from_dict(prior["coordinates"]),
        raw_text=prior["raw_text"], structured_value=structured,
        parser_name=prior["parser_name"], parser_version="0.4.0",
        parse_status=prior["parse_status"], quality_flags=prior["quality_flags"],
    )
    expected["evidence_spans"] = [span.to_dict()]
    expected["versions"]["parser"] = "0.4.0"
    expected["summary"]["draft"]["claims"][0]["evidence_ids"] = [span.span_id]
    expected["transcript_byte_bindings"][0]["evidence_id"] = span.span_id
    assert current == expected, "unreviewed source, fact, unit, citation, or metadata change"
    assert span.span_id != prior["span_id"]
    _assert_transcript_replays(old, current, prior["raw_text"])


def _assert_transcript_replays(old, current, raw_text):
    for value in (old, current):
        bundle = NarrativeBundle.from_dict(value)
        verified, failed = verify_transcript_evidence_spans(
            TXT.decode("utf-8"), source_id=bundle.source_ref.source_id,
            source_sha256=bundle.source_ref.content_sha256, evidence_spans=bundle.evidence_spans,
        )
        assert not failed and verified == (bundle.evidence_spans[0].span_id,)
        claim = value["summary"]["draft"]["claims"][0]
        assert claim["text"] == raw_text
        assert claim["evidence_ids"] == [bundle.evidence_spans[0].span_id]
        binding = value["transcript_byte_bindings"][0]
        bound = b"".join(TXT[item["start"]:item["end"]] for item in binding["source_byte_ranges"])
        assert raw_text.encode("utf-8") in bound
