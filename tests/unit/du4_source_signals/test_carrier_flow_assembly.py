"""Small synthetic carrier-stream assembly for the source-signal collector.

The producer side below is a hand-written carrier stream in the shape ROOT's
single HTML walk will emit; this test verifies input -> signal completeness
over that stream only.  It is explicitly NOT a native parser acceptance and
NOT a production route/selector E2E: no HTML is parsed, no router runs, and
no owner original is opened here.
"""

from __future__ import annotations

from .builders import budget, carrier, code_set, observation, ref, unit, whole_ref

from company_wiki.document_understanding.source_signals import collect_source_signals

MAIN = "urn:company-wiki:source:sha256:assembly-main"
ATTACH = "urn:company-wiki:source:sha256:assembly-attachment"


def test_carrier_stream_produces_complete_scoped_signals():
    units = [
        unit("u-toc", "Table of Contents", parent_id=MAIN, locator="loc:v1/paragraph:0"),
        unit("u-form", "FORM 8-K", parent_id=MAIN, locator="loc:v1/paragraph:1"),
        unit("u-date", "Date of Report: May 2, 2025", parent_id=MAIN, locator="loc:v1/paragraph:2"),
        unit("u-cell-label", "Revenues:", parent_id=MAIN, kind="html_table_cell",
             locator="loc:v1/table:0/row:1/column:0"),
        unit("u-cell-value", "1,203", parent_id=MAIN, kind="html_table_cell",
             locator="loc:v1/table:0/row:1/column:1"),
        unit("u-prep-spk", "Jane Roe — CEO:", parent_id=MAIN, role="management",
             locator="loc:v1/paragraph:3"),
        unit("u-prep-body", "Good morning and welcome.", parent_id=MAIN, role="management",
             locator="loc:v1/paragraph:4"),
        unit("u-an-spk", "Analyst:", parent_id=MAIN, role="investor_question",
             locator="loc:v1/paragraph:5"),
        unit("u-an-body", "How do you see demand evolving?", parent_id=MAIN,
             role="investor_question", locator="loc:v1/paragraph:6"),
        unit("u-att-form", "FORM 10-K", parent_id=ATTACH, locator="loc:v1/paragraph:0"),
    ]
    carriers = [
        carrier("visible_own_form_label", ["u-form"], [ref("u-form", 0, 8)], parent_id=MAIN),
        carrier(
            "visible_inline_xbrl_document_type",
            ["u-form"],
            [ref("u-form", 5, 8)],
            parent_id=MAIN,
            attributes={"concept": "dei:DocumentType", "visibility": "visible"},
        ),
        carrier(
            "native_speaker_turn",
            ["u-prep-spk", "u-prep-body"],
            [ref("u-prep-spk", 0, 9)],
            parent_id=MAIN,
            attributes={
                "speaker": "Jane Roe — CEO",
                "turn_id": "turn-1",
                "turn_role": "prepared_remarks",
            },
        ),
        carrier(
            "native_speaker_turn",
            ["u-an-spk", "u-an-body"],
            [ref("u-an-spk", 0, 7)],
            parent_id=MAIN,
            attributes={"speaker": "Analyst", "turn_id": "turn-2", "turn_role": "analyst"},
        ),
        carrier(
            "visible_own_form_label",
            ["u-att-form"],
            [ref("u-att-form", 0, 9)],
            parent_id=ATTACH,
        ),
    ]
    obs = observation(units, carriers)
    result = collect_source_signals(obs, work_budget=budget())

    forms = result["source_form_evidence"]
    assert [(entry["parent_id"], entry["value"]) for entry in forms] == [
        (MAIN, "FORM 8-K"),
        (MAIN, "8-K"),
        (ATTACH, "FORM 10-K"),
    ]
    turns = result["turn_evidence"]
    assert [(turn["parent_id"], turn["turn_id"], turn["turn_role"]) for turn in turns] == [
        (MAIN, "turn-1", "prepared_remarks"),
        (MAIN, "turn-2", "analyst"),
    ]
    assert turns[0]["speaker_refs"] == [ref("u-prep-spk", 0, 9)]
    assert turns[0]["body_refs"] == [whole_ref("u-prep-body", "Good morning and welcome.")]
    assert turns[1]["body_refs"] == [whole_ref("u-an-body", "How do you see demand evolving?")]

    assert result["reserved_unit_ids"] == [
        "u-form",
        "u-prep-spk",
        "u-prep-body",
        "u-an-spk",
        "u-an-body",
        "u-att-form",
    ]
    # The financial label is not a turn; the TOC is not a form carrier.
    assert "u-cell-label" not in result["reserved_unit_ids"]
    assert "u-toc" not in result["reserved_unit_ids"]
    assert "DECLARED_FORM_CONFLICT" not in code_set(result)
    assert result["status"] == "complete"
    # 10 unit-index charges + 5 carrier charges + per-carrier unit ids and refs
    assert result["work_used"] == 10 + 5 + 2 + 2 + 3 + 3 + 2
