"""Semantic counterexamples for native speaker/turn evidence (DU4-FORM card §A).

The class of error is structural: no colon/caps shape and no forbidden-word
blacklist may create or reject a turn.  Only natively associated carriers with
real content or a source-owned turn association are evidence.
"""

from __future__ import annotations

import pytest

from builders import (
    DEFAULT_PARENT,
    budget,
    carrier,
    code_set,
    observation,
    ref,
    unit,
    whole_ref,
)

from company_wiki.document_understanding.source_signals import collect_source_signals


def _turn_carrier(
    speaker_unit: str,
    speaker_text: str,
    body_unit: str,
    body_text: str,
    *,
    attributes: dict,
    parent_id: str = DEFAULT_PARENT,
) -> tuple[dict, dict, dict]:
    speaker = unit(
        speaker_unit,
        speaker_text,
        role="management",
        kind="html_paragraph",
        locator="loc:v1/paragraph:1",
    )
    body = unit(
        body_unit,
        body_text,
        role="management",
        kind="html_paragraph",
        locator="loc:v1/paragraph:2",
    )
    entry = carrier(
        "native_speaker_turn",
        [speaker_unit, body_unit],
        [ref(speaker_unit, 0, len(speaker_text))],
        parent_id=parent_id,
        attributes=attributes,
    )
    return speaker, body, entry


@pytest.mark.parametrize(
    "label",
    ["Revenues:", "Headcount:", "Utilization:", "Gross margin:", "Widgets:"],
)
def test_financial_labels_never_become_turns_by_shape(label):
    # No native_speaker_turn carrier exists; the colon shape must not create
    # one, and no blacklist of these words exists in the implementation.
    units = [
        unit("u-cell", label, kind="html_table_cell", locator="loc:v1/table:1/row:2/column:0"),
        unit("u-value", "1,234", kind="html_table_cell", locator="loc:v1/table:1/row:2/column:1"),
    ]
    obs = observation(units, [])
    result = collect_source_signals(obs, work_budget=budget())
    assert result["turn_evidence"] == []
    assert result["reserved_unit_ids"] == []


def test_caption_furniture_shape_is_not_a_turn():
    units = [unit("u-caption", "Table 3: Revenues by segment", kind="table_caption")]
    result = collect_source_signals(observation(units, []), work_budget=budget())
    assert result["turn_evidence"] == []


def test_label_only_carrier_without_body_or_association_is_rejected():
    speaker, body, entry = _turn_carrier(
        "u-label",
        "Revenues:",
        "u-body",
        "1,234",
        attributes={},
    )
    # Only the label unit belongs to the carrier: no body, no turn association.
    entry["unit_ids"] = ["u-label"]
    obs = observation([speaker, body], [entry])
    result = collect_source_signals(obs, work_budget=budget())
    assert result["turn_evidence"] == []
    assert "TURN_WITHOUT_BODY_OR_ASSOCIATION" in code_set(result)


def test_empty_label_carrier_is_rejected():
    entry = carrier(
        "native_speaker_turn",
        ["u-empty"],
        [],
        attributes={},
    )
    obs = observation([unit("u-empty", "")], [entry])
    result = collect_source_signals(obs, work_budget=budget())
    assert result["turn_evidence"] == []
    assert code_set(result)


@pytest.mark.parametrize("turn_role", ["cfo", "operator", "analyst", "management"])
def test_named_prose_turns_with_body_are_evidence(turn_role):
    speaker_text = "Sarah Chen — Chief Financial Officer:"
    body_text = "We delivered 12% revenue growth for the quarter."
    speaker, body, entry = _turn_carrier(
        "u-spk",
        speaker_text,
        "u-speech",
        body_text,
        attributes={
            "speaker": "Sarah Chen — Chief Financial Officer",
            "turn_id": f"turn-{turn_role}",
            "turn_role": turn_role,
        },
    )
    obs = observation([speaker, body], [entry])
    result = collect_source_signals(obs, work_budget=budget())
    turns = result["turn_evidence"]
    assert len(turns) == 1
    turn = turns[0]
    assert turn["parent_id"] == DEFAULT_PARENT
    assert turn["origin"] == "native_speaker_turn"
    assert turn["turn_id"] == f"turn-{turn_role}"
    assert turn["turn_role"] == turn_role
    assert turn["speaker"] == "Sarah Chen — Chief Financial Officer"
    assert turn["speaker_refs"] == [ref("u-spk", 0, len(speaker_text))]
    assert turn["body_refs"] == [whole_ref("u-speech", body_text)]
    assert result["reserved_unit_ids"] == ["u-spk", "u-speech"]


def test_native_attributed_table_turn_is_not_excluded_by_table_shape():
    name = unit(
        "u-tbl-name",
        "John Smith",
        role="management",
        kind="html_table_cell",
        locator="loc:v1/table:3/row:1/column:0",
    )
    speech = unit(
        "u-tbl-speech",
        "Our backlog remains strong across all regions.",
        role="management",
        kind="html_table_cell",
        locator="loc:v1/table:3/row:1/column:1",
    )
    entry = carrier(
        "native_speaker_turn",
        ["u-tbl-name", "u-tbl-speech"],
        [ref("u-tbl-name", 0, 10)],
        attributes={
            "speaker": "John Smith",
            "turn_id": "tbl-turn-7",
            "turn_role": "management",
        },
    )
    obs = observation([name, speech], [entry])
    result = collect_source_signals(obs, work_budget=budget())
    turns = result["turn_evidence"]
    assert len(turns) == 1
    assert turns[0]["body_refs"] == [
        whole_ref("u-tbl-speech", "Our backlog remains strong across all regions.")
    ]
    assert turns[0]["turn_id"] == "tbl-turn-7"


def test_prepared_remarks_do_not_fabricate_qa():
    speaker, body, entry = _turn_carrier(
        "u-prep-spk",
        "Maria Lopez — Chief Executive Officer:",
        "u-prep-body",
        "Good morning everyone, thank you for joining us.",
        attributes={
            "speaker": "Maria Lopez — Chief Executive Officer",
            "turn_id": "turn-prep-1",
            "turn_role": "prepared_remarks",
        },
    )
    obs = observation([speaker, body], [entry])
    result = collect_source_signals(obs, work_budget=budget())
    turns = result["turn_evidence"]
    assert len(turns) == 1
    assert turns[0]["turn_role"] == "prepared_remarks"
    joined = repr(result)
    for invented in ("question", "answer", "qa_pair", "investor_question"):
        assert invented not in joined.lower().replace("prepared_remarks", "")


def test_rhetorical_question_body_is_not_an_investor_question():
    speaker, body, entry = _turn_carrier(
        "u-spk",
        "Sarah Chen — CFO:",
        "u-speech",
        "What does this mean for our margins? We are confident in the plan.",
        attributes={
            "speaker": "Sarah Chen — CFO",
            "turn_id": "turn-9",
            "turn_role": "management",
        },
    )
    obs = observation([speaker, body], [entry])
    result = collect_source_signals(obs, work_budget=budget())
    turns = result["turn_evidence"]
    assert len(turns) == 1
    assert turns[0]["turn_role"] == "management"
    assert turns[0]["speaker"] == "Sarah Chen — CFO"


def test_cross_parent_carrier_is_not_paired():
    other_parent = "urn:company-wiki:source:sha256:other-original"
    speaker, body, entry = _turn_carrier(
        "u-spk",
        "Jane Doe:",
        "u-speech",
        "Our statement on the matter.",
        attributes={"speaker": "Jane Doe", "turn_id": "turn-x", "turn_role": "management"},
    )
    body["parent_id"] = other_parent
    obs = observation([speaker, body], [entry])
    result = collect_source_signals(obs, work_budget=budget())
    assert result["turn_evidence"] == []
    assert "CARRIER_PARENT_MISMATCH" in code_set(result)


def test_distinct_turn_ids_are_never_paired():
    s1, b1, c1 = _turn_carrier(
        "u-op",
        "Operator:",
        "u-op-body",
        "The question-and-answer session is now open.",
        attributes={"speaker": "Operator", "turn_id": "turn-1", "turn_role": "operator"},
    )
    s2, b2, c2 = _turn_carrier(
        "u-an",
        "Analyst:",
        "u-an-body",
        "Could you discuss the drivers?",
        attributes={"speaker": "Analyst", "turn_id": "turn-2", "turn_role": "analyst"},
    )
    s3, b3, c3 = _turn_carrier(
        "u-mgmt",
        "Sarah Chen:",
        "u-mgmt-body",
        "The drivers were volume and price.",
        attributes={"speaker": "Sarah Chen", "turn_id": "turn-2", "turn_role": "management"},
    )
    obs = observation([s1, b1, s2, b2, s3, b3], [c1, c2, c3])
    result = collect_source_signals(obs, work_budget=budget())
    turns = result["turn_evidence"]
    assert len(turns) == 3
    assert [turn["turn_id"] for turn in turns] == ["turn-1", "turn-2", "turn-2"]
    assert [turn["turn_role"] for turn in turns] == ["operator", "analyst", "management"]


def test_same_turn_id_across_parents_stays_scoped():
    child_parent = "urn:company-wiki:source:sha256:attachment"
    s1, b1, c1 = _turn_carrier(
        "u-a-spk",
        "Host:",
        "u-a-body",
        "Welcome to the call.",
        attributes={"speaker": "Host", "turn_id": "turn-1", "turn_role": "operator"},
    )
    s2, b2, c2 = _turn_carrier(
        "u-b-spk",
        "Host:",
        "u-b-body",
        "Welcome to the breakout session.",
        attributes={"speaker": "Host", "turn_id": "turn-1", "turn_role": "operator"},
        parent_id=child_parent,
    )
    s2["parent_id"] = child_parent
    b2["parent_id"] = child_parent
    obs = observation([s1, b1, s2, b2], [c1, c2])
    result = collect_source_signals(obs, work_budget=budget())
    turns = result["turn_evidence"]
    assert len(turns) == 2
    assert [turn["parent_id"] for turn in turns] == [DEFAULT_PARENT, child_parent]


def test_unknown_turn_fields_are_none_not_empty_strings():
    speaker, body, entry = _turn_carrier(
        "u-spk",
        "Voice:",
        "u-speech",
        "A statement without role metadata.",
        attributes={"speaker": "Voice"},
    )
    entry["unit_ids"] = ["u-spk", "u-speech"]
    obs = observation([speaker, body], [entry])
    result = collect_source_signals(obs, work_budget=budget())
    turns = result["turn_evidence"]
    assert len(turns) == 1
    assert turns[0]["turn_id"] is None
    assert turns[0]["turn_role"] is None
