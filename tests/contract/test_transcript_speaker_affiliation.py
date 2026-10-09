"""Source-independent speaker/QA contract; immutable old parser replay."""
from __future__ import annotations

import hashlib
import json

import pytest

from company_wiki.source_catalog.narrative_evidence import (
    parse_transcript_text, select_narrative_evidence, verify_transcript_evidence_spans,
)
from company_wiki.source_contract import source_id_for_sha256

PEOPLE = (
    ("Alex Rivera", "Westshore Research"),
    ("Priya Shah", "NORTHBANK"),
    ("Jordan Lee", "Independent Research"),
    ("Chris Jones", "Southgate Capital"),
    ("Robin Khan", "Regional Markets"),
    ("Dana Morris", "Longview Partners"),
)
OLD_TEXT = 'Full Conference Call Transcript\nJane Doe -- CEO: We launched a new product overseas.\nQuestions and Answers\nOperator: The next question is from Alex Rivera.\nAlex Rivera, Westshore Research: Has the new sensor completed validation?\nJane Doe: Customer validation is not completed.\nAlex Rivera: Thank you.\nEND'
OLD_FINGERPRINT = "690f5b6c448bf6dd63951b1f8b6c0a1fd51dc53b37459045c41c465866d5aa2f"


def parse(text, version=None):
    sha = hashlib.sha256(text.encode()).hexdigest()
    kwargs = {} if version is None else {"parser_version": version}
    return parse_transcript_text(text, source_id=source_id_for_sha256(sha),
                                 source_sha256=sha, **kwargs)


def call(qa):
    return ("Full Conference Call Transcript\n"
            "Jane Doe -- CEO: We launched a new sensor and expanded overseas supply.\n"
            "Questions and Answers\n" + qa + "\nEND")


def containing(parsed, text):
    units = [u for u in parsed.units if text in u.raw_text]
    assert len(units) == 1
    return units[0]


@pytest.mark.parametrize("name,affiliation", PEOPLE)
def test_comma_affiliation_first_question_retains_actual_analyst(name, affiliation):
    d = parse(call(f"Operator: Our next question is from {name}.\n"
                   f"{name}, {affiliation}: Has the new sensor completed validation?\n"
                   "Jane Doe: Customer validation is not completed."))
    q = containing(d, "Has the new sensor completed validation?")
    answer = containing(d, "Customer validation is not completed.")
    assert q.source_role == "analyst"
    assert q.metadata["speaker"] == name
    assert q.metadata["speaker_title"] == affiliation
    assert q.metadata["qa_group_id"] is not None
    assert q.metadata["qa_group_id"] == answer.metadata["qa_group_id"]
    assert answer.source_role == "management"


def test_six_questions_and_closing_courtesies_keep_six_parent_groups():
    rows = []
    for i, (name, firm) in enumerate(PEOPLE):
        rows += [f"Operator: The next question is from {name}.",
                 f"{name}, {firm}: When will new product {i} complete validation?",
                 f"Jane Doe: Product {i} validation is planned, not complete.",
                 f"{name}: Thank you for that answer {i}."]
    d = parse(call("\n".join(rows)))
    groups = []
    for i, (name, _) in enumerate(PEOPLE):
        q = containing(d, f"When will new product {i} complete validation?")
        a = containing(d, f"Product {i} validation is planned, not complete.")
        thanks = containing(d, f"Thank you for that answer {i}.")
        assert q.metadata["speaker"] == name and q.source_role == "analyst"
        assert a.source_role == "management"
        assert q.metadata["qa_group_id"] == a.metadata["qa_group_id"] == thanks.metadata["qa_group_id"]
        groups.append(q.metadata["qa_group_id"])
    assert len(set(groups)) == 6
    assert {u.metadata["qa_group_id"] for u in d.units if u.metadata["qa_group_id"] is not None} == set(groups)
    selection = select_narrative_evidence(d, title="New company earnings call",
                                        existing_kind="investor_call_transcript")
    assert selection.evidence_spans
    verified, failed = verify_transcript_evidence_spans(
        call("\n".join(rows)), source_id=d.source_id,
        source_sha256=d.source_sha256, evidence_spans=selection.evidence_spans,
    )
    assert len(verified) == len(selection.evidence_spans) and not failed


def test_prepared_management_identity_is_case_insensitive_without_changing_display():
    d = parse(call("Alex Rivera, Westshore Research: Is customer validation completed?\n"
                   "JANE DOE: The new product has not yet completed validation."))
    answer = containing(d, "The new product has not yet completed validation.")
    assert answer.source_role == "management"
    assert answer.metadata["speaker"] == "JANE DOE"


def test_comma_title_can_start_a_real_prepared_management_turn():
    text = ("Full Conference Call Transcript\n"
            "Jane Doe, Chief Executive Officer: We launched a new sensor overseas.\n"
            "END")
    d = parse(text)
    assert not d.errors
    assert containing(d, "We launched a new sensor overseas.").source_role == "management"


@pytest.mark.parametrize("label", ["Revenue, Europe", "Financial Results, Europe", "Contact, Relations"])
def test_comma_does_not_promote_metrics_or_contact_into_speakers(label):
    d = parse(f"Earnings Call Transcript\n{label}: Our new products expanded overseas.\nEND")
    assert d.errors and not d.units


def test_legacy_natural_parser_fingerprint_is_frozen_and_replayable():
    old = parse(OLD_TEXT, "0.2.0")
    actual = [(u.unit_id, u.raw_text, u.source_role, dict(u.metadata)) for u in old.units]
    fingerprint = hashlib.sha256(json.dumps(actual, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert fingerprint == OLD_FINGERPRINT
    new = parse(OLD_TEXT)
    assert old.units[0].unit_id != new.units[0].unit_id
    selected = select_narrative_evidence(old, title="Old earnings call",
                                       existing_kind="investor_call_transcript")
    verified, failed = verify_transcript_evidence_spans(
        OLD_TEXT, source_id=old.source_id, source_sha256=old.source_sha256,
        evidence_spans=selected.evidence_spans,
    )
    assert len(verified) == len(selected.evidence_spans) and not failed
