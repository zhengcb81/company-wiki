"""ROOT: the dependency closure must actually be applied, not merely available.

A regression lock for the second instance of the same defect this layer keeps
producing: ``dependency_closure`` existed and was unit-tested, and **nothing in
the chain called it**.  So the two guarantees it exists to provide -- a unit
caption restored for a selected number, and a negation kept with the package it
belongs to -- held only inside its own tests, never in a request that would
reach a model.

The rule enforced here: when the caller supplies what the selector chose,
``build_summary_input`` applies the closure and reports it; when no selection is
supplied, the request says so, because "closure not applied" and "closure found
nothing to add" are different states and must not look alike.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SOURCE = REPO / "src"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from company_wiki.document_understanding import (  # noqa: E402
    build_summary_input,
    understand_units,
)


class _Coords:
    def __init__(self, page=1, row_index=None, table_index=None):
        self.page_number = page
        self.row_index = row_index
        self.table_index = table_index
        self.column_index = None


class _Unit:
    def __init__(self, unit_id, text, *, kind="pdf_text_block", page=1, metadata=None,
                 row_index=None, table_index=None):
        self.unit_id = unit_id
        self.raw_text = text
        self.unit_kind = kind
        self.source_role = "company_filing"
        self.language = "zh"
        self.coordinates = _Coords(page, row_index=row_index, table_index=table_index)
        self.metadata = {"source_locator": f"loc:v1/page:{page}/paragraph:{unit_id}"}
        if metadata:
            self.metadata.update(metadata)


def _project_document():
    """A募集资金 table: the row's numbers need the caption and the header."""
    return [
        _Unit("h1", "第三节 募集资金运用", page=61),
        _Unit("cap", "单位：万元", page=61),
        _Unit(
            "hdr",
            "项目名称 | 投资总额 | 募集资金投入额 | 建设期",
            kind="pdf_table_row",
            page=61,
            row_index=0,
            table_index=0,
        ),
        _Unit(
            "row",
            "高端精密刀具扩产项目 | 28000 | 20000 | 24 个月",
            kind="pdf_table_row",
            page=61,
            row_index=1,
            table_index=0,
        ),
    ]


def _pipeline():
    return understand_units(
        _project_document(),
        source_id="s",
        source_sha256="d",
        title="示例：向特定对象发行A股股票募集说明书",
        declared_kind="unknown",
        language="zh",
    )


def test_closure_is_not_applied_when_no_selection_is_supplied() -> None:
    """The absent state must be visible, not implied."""
    request = build_summary_input(_pipeline())
    assert request["closure"]["applied"] is False
    assert request["closure"]["reason"]
    assert request["closure"]["added_unit_ids"] == []


def test_closure_restores_the_unit_caption_and_header_for_a_selected_row() -> None:
    """Selecting only the row must pull its unit and its header back in."""
    request = build_summary_input(_pipeline(), selected_unit_ids=["row"])
    assert request["closure"]["applied"] is True
    added = set(request["closure"]["added_unit_ids"])
    assert added, "the closure added nothing for a bare project row"
    assert {"cap", "hdr"} & added, (
        f"neither the unit caption nor the table header came back: {sorted(added)}"
    )


def test_closure_diagnostics_reach_the_request() -> None:
    request = build_summary_input(_pipeline(), selected_unit_ids=["row"])
    codes = {item["code"] for item in request["closure"]["diagnostics"]}
    assert "CONTEXT_RESTORED" in codes


def test_the_restored_evidence_is_actually_sent_to_the_model() -> None:
    """Applying the closure is not enough; its result must reach the members."""
    request = build_summary_input(_pipeline(), selected_unit_ids=["row"])
    members = {
        member["unit_id"]
        for package in request["evidence_packages"]
        for member in package["members"]
    }
    assert "row" in members
    assert "cap" in members, "the unit caption was restored but not sent"
    assert "hdr" in members, "the table header was restored but not sent"


def test_a_selection_outside_every_package_is_not_silently_expanded() -> None:
    """A unit nobody packaged must not drag unrelated packages in."""
    request = build_summary_input(_pipeline(), selected_unit_ids=["not-in-any-package"])
    assert request["closure"]["applied"] is True
    assert request["closure"]["added_unit_ids"] == []


def test_closure_keeps_a_negation_with_its_package() -> None:
    """The 万润 shape: the answer denies the premise of the question."""
    units = [
        _Unit("q1", "问：公司有没有与下游客户合作建设VC产能的设想？", page=3),
        _Unit("a1", "答：公司现无生产VC的情况，也未与下游客户合作建设产能。", page=3),
    ]
    result = understand_units(
        units,
        source_id="s",
        source_sha256="d",
        title="投资者关系活动记录表",
        declared_kind="investor_relations",
        language="zh",
    )
    request = build_summary_input(result, selected_unit_ids=["q1"])
    texts = [
        member["text"]
        for package in request["evidence_packages"]
        for member in package["members"]
    ]
    assert any("无生产VC" in text for text in texts), (
        "the denial must reach the request when only the question was selected"
    )
    codes = {item["code"] for item in request["closure"]["diagnostics"]}
    assert "NEGATION_PROTECTED" in codes
