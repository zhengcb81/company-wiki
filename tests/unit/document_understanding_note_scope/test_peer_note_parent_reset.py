"""Peer source notes must not inherit an unrecognized prior note's local title."""

import pytest

from .fixtures import Row, inherited_heading_ids, run_pipeline, source


@pytest.mark.parametrize("note_page", [1, 2])
def test_first_recognized_peer_note_keeps_shared_parent_but_drops_old_local_heading(note_page):
    parsed, owned = source((
        Row("shared_chapter", "一、主营业务及经营情况", kind="heading"),
        Row("old_local_heading", "（4）股份减持的信息披露"),
        Row("old_local_body", "承诺人按规定履行相关披露义务。"),
        Row("new_note_intro", "备注37：乙方就新业务合作作出独立承诺：", page=note_page),
        Row("new_note_body", "“1、乙方计划在项目建成后为工厂提供产能保障。", page=note_page),
    ))

    result, _contexts = run_pipeline(parsed)
    context = inherited_heading_ids(result, owned["new_note_body"])

    assert owned["shared_chapter"].unit_id in context
    assert owned["new_note_intro"].unit_id in context, result["structure"]["sections"]
    rendered = [
        (section["section_id"], section["parent_id"], [
            key for key, unit in owned.items()
            if unit.unit_id in section["heading_unit_ids"]
        ])
        for section in result["structure"]["sections"]
    ]
    assert owned["old_local_heading"].unit_id not in context, rendered


def test_unclassified_document_still_keeps_outer_section_when_reanchoring_note():
    parsed, owned = source((
        Row("outer_section", "一、其他事项", kind="heading"),
        Row("old_local_heading", "（4）有关安排的补充说明"),
        Row("old_local_body", "本项安排按约定继续执行。"),
        Row("note_intro", "备注5：另一事项的独立说明："),
        Row("note_body", "“1、相关安排仍需满足约定条件。"),
    ))

    result, _contexts = run_pipeline(parsed)
    context = inherited_heading_ids(result, owned["note_body"])

    assert owned["outer_section"].unit_id in context, result["structure"]["sections"]
    assert owned["note_intro"].unit_id in context
    assert owned["old_local_heading"].unit_id not in context


def test_financial_note_remains_attached_to_its_financial_section():
    parsed, owned = source((
        Row("financial_section", "四、财务报告及附注", kind="heading"),
        Row("note_intro", "备注18：现金流量表项目说明："),
        Row("note_body", "本项目金额为期末余额，口径见财务报表。"),
    ))

    result, _contexts = run_pipeline(parsed)
    context = inherited_heading_ids(result, owned["note_body"])
    note_sections = [
        section for section in result["structure"]["sections"]
        if owned["note_intro"].unit_id in section["heading_unit_ids"]
    ]
    financial_sections = [
        section for section in result["structure"]["sections"]
        if owned["financial_section"].unit_id in section["heading_unit_ids"]
    ]

    assert len(note_sections) == len(financial_sections) == 1
    assert note_sections[0]["parent_id"] == financial_sections[0]["section_id"]
    assert owned["financial_section"].unit_id in context
