"""Operational actions must survive without company or product-name rules."""
from __future__ import annotations

import hashlib

import pytest

from company_wiki.source_catalog.narrative_evidence import (
    parse_transcript_text,
    select_narrative_evidence,
    verify_transcript_evidence_spans,
)
from company_wiki.source_contract import source_id_for_sha256


def _select(statement: str, speaker: str = "CEO"):
    text = f"Full Conference Call Transcript\n{speaker}: {statement}\n"
    digest = hashlib.sha256(text.encode()).hexdigest()
    source_id = source_id_for_sha256(digest)
    parsed = parse_transcript_text(text, source_id=source_id, source_sha256=digest)
    return text, source_id, digest, select_narrative_evidence(parsed, title="earnings_call.txt")


@pytest.mark.parametrize("statement", [
    "We added 31 new data centers across 5 continents this quarter.",
    "We announced more than a dozen new models across image, voice and coding this year.",
    "We now have over 40,000 paid customers, up more than 60% year-over-year.",
    "The number of customers using our platform increased 80% this year.",
    "We increased the throughput for production workloads fourfold this quarter.",
    "We expanded the manufacturing site with two production lines this quarter.",
    "We introduced an insurance service for small businesses this year.",
    "We deployed a new logistics platform across three countries this quarter.",
    "We reduced dock-to-live times for new GPUs by nearly 50% this year.",
    "Our paid subscription seats surpassed 30 million this quarter.",
    "We now have over 30 million paid Microsoft 365 Copilot seats, with net seat adds more than doubling quarter-over-quarter.",
    "We are transitioning our business model to seat plus consumption.",
    "We now have this per seat business model, and also a usage business model, so it is seat plus usage.",
])
def test_concrete_english_operating_updates_are_selected_and_replay(statement):
    text, source_id, digest, package = _select(statement)
    assert any(statement == span.raw_text for span in package.evidence_spans)
    assert all(span.structured_value["source_role"] == "management" for span in package.evidence_spans)
    verified, failed = verify_transcript_evidence_spans(
        text, source_id=source_id, source_sha256=digest, evidence_spans=package.evidence_spans,
    )
    assert len(verified) == len(package.evidence_spans) and failed == ()


@pytest.mark.parametrize("statement", [
    "We announced quarterly earnings per share increased 45% this year.",
    "Revenue grew 18% and net income increased 20% this quarter.",
    "We thank our customers and remain committed to innovation.",
    "Our platform has great potential for future growth.",
    "We have great customers and a strong product portfolio.",
    "We added ten new shareholders this quarter.",
    "Customer revenue grew 20% this quarter.",
    "We increased revenue from customers by 18% this year.",
    "We announced platform earnings per share increased 45% this quarter.",
])
def test_financial_only_or_vague_english_updates_are_not_business_events(statement):
    assert _select(statement)[3].evidence_spans == ()


def test_operator_updates_stay_excluded_and_negated_milestones_keep_the_negation():
    assert _select("We added 31 new data centers this quarter.", speaker="Operator")[3].evidence_spans == ()
    statement = "We have not yet launched the new service; customer validation is still underway."
    text, source_id, digest, package = _select(statement)
    assert any("not yet launched" in span.raw_text for span in package.evidence_spans)
    verified, failed = verify_transcript_evidence_spans(
        text, source_id=source_id, source_sha256=digest, evidence_spans=package.evidence_spans,
    )
    assert len(verified) == len(package.evidence_spans) and failed == ()
