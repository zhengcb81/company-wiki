"""ROOT integration tests: observation adapter and dependency packages.

These lock the integration contract only.  They run against synthetic units and
against the frozen lane fixtures; the real-original cross-check lives in
``test_du_root_real_samples.py`` and is marked so it can be deselected when the
owner's originals are absent.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SOURCE = REPO / "src"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

STRUCTURE_FIXTURES = (
    REPO / "tests" / "fixtures" / "document_understanding_structure"
)
if str(STRUCTURE_FIXTURES) not in sys.path:
    sys.path.insert(0, str(STRUCTURE_FIXTURES))

from company_wiki.document_understanding.observation_adapter import (  # noqa: E402
    _detect_gutter_x,
    _heading_level,
    _lane_for,
    build_observation,
)
from company_wiki.document_understanding.orchestration import (  # noqa: E402
    build_dependency_packages,
    package_units_for_prompt,
)
from company_wiki.document_understanding.structure import build_structure  # noqa: E402


class _Coords:
    def __init__(self, page=None, table_index=None, row_index=None, column_index=None):
        self.page_number = page
        self.table_index = table_index
        self.row_index = row_index
        self.column_index = column_index


class _Unit:
    """Minimal stand-in for NarrativeUnit with the fields the adapter reads."""

    def __init__(
        self,
        unit_id,
        text,
        *,
        kind="pdf_text_block",
        role="company_filing",
        language="zh",
        page=1,
        bbox=None,
        metadata=None,
        coords=None,
    ):
        self.unit_id = unit_id
        self.raw_text = text
        self.unit_kind = kind
        self.source_role = role
        self.language = language
        self.coordinates = coords or _Coords(page=page)
        self.metadata = dict(metadata or {})
        if bbox is not None:
            self.metadata["bbox"] = list(bbox)


# ------------------------------------------------------------ heading levels


def test_numbered_headings_get_their_level() -> None:
    cases = {
        "第三节 管理层讨论与分析": 1,
        "第一节 释义": 1,
        "一、主营业务情况": 2,
        "（一）项目基本情况": 3,
        "Item 1. Business": 1,
        "1.2 经营情况讨论": 3,
    }
    for text, expected in cases.items():
        assert _heading_level(text, {}) == expected, text


def test_prose_that_merely_starts_with_digits_is_not_a_heading() -> None:
    """A date or a quantity at the start of a sentence is not a section."""
    for text in (
        "2020 年5 月14 日中央政治局常委会会议上提出加快形成以国内大循环为主体",
        "公司2024年度实现营业收入100亿元，同比增长12%。",
        "3,926家门店分布在多个市场。",
    ):
        assert _heading_level(text, {}) is None, text


def test_long_or_terminal_text_is_not_a_heading() -> None:
    assert _heading_level("一、本项目的情况说明如下所示，具体内容请参见后文详细描述以及相关附件材料。", {}) is None
    assert _heading_level("一、项目基本情况：", {}) is None
    assert _heading_level("", {}) is None


def test_explicit_parser_heading_level_is_respected() -> None:
    assert _heading_level("Store Network", {"heading_level": 2}) == 2
    assert _heading_level("Store Network", {"heading_level": True}) is None


def test_unnumbered_heading_is_not_guessed_from_geometry() -> None:
    """Without font evidence a short block is not promoted to a section."""
    assert _heading_level("Store Network", {}) is None


# ------------------------------------------------------------------ gutters


def _box(x0, y0, x1, y1):
    return (x0, y0, x1, y1)


def test_two_column_page_yields_a_gutter() -> None:
    blocks = [
        _box(56, 100, 331, 130),
        _box(56, 140, 331, 170),
        _box(56, 180, 331, 210),
        _box(348, 100, 552, 130),
        _box(348, 140, 552, 170),
        _box(348, 180, 552, 210),
    ]
    gutter = _detect_gutter_x(blocks)
    assert gutter is not None
    assert 331 <= gutter <= 348


def test_single_column_page_has_no_gutter() -> None:
    blocks = [_box(60, 100 + 40 * i, 530, 130 + 40 * i) for i in range(8)]
    assert _detect_gutter_x(blocks) is None


def test_full_width_table_does_not_create_a_false_gutter() -> None:
    """A table spanning both columns must not be read as two lanes."""
    blocks = [_box(60, 100 + 40 * i, 530, 130 + 40 * i) for i in range(6)]
    blocks.append(_box(62, 400, 547, 500))
    assert _detect_gutter_x(blocks) is None


def test_full_width_block_belongs_to_no_lane() -> None:
    gutter = 340.0
    assert _lane_for(56, 331, gutter, (56, 552)) == 0
    assert _lane_for(348, 552, gutter, (56, 552)) == 1
    assert _lane_for(62, 547, gutter, (56, 552)) is None


# ------------------------------------------------------------- observation


def test_observation_is_du_input_wire() -> None:
    units = [
        _Unit("u1", "第一节 释义", bbox=(60, 90, 300, 115)),
        _Unit("u2", "本公司指示例股份有限公司。", bbox=(60, 130, 530, 175)),
    ]
    observation = build_observation(units, source_id="s", source_sha256="d")
    assert observation["schema_version"] == "du-input/1"
    assert observation["source_ref"] == {"source_id": "s", "source_sha256": "d"}
    assert len(observation["units"]) == 2
    assert observation["units"][0]["kind"] == "heading"
    assert observation["units"][0]["hints"]["heading_level"] == 1


def test_adapter_never_mutates_the_units_it_reads() -> None:
    units = [
        _Unit("u1", "一、主营业务", bbox=(60, 90, 300, 115), metadata={"pdf_block": 3}),
        _Unit("u2", "公司主营产品为沸石系列。", bbox=(60, 130, 530, 175)),
    ]
    before = [("u1", units[0].raw_text, dict(units[0].metadata)), ("u2", units[1].raw_text, dict(units[1].metadata))]
    build_observation(units, source_id="s", source_sha256="d")
    after = [("u1", units[0].raw_text, dict(units[0].metadata)), ("u2", units[1].raw_text, dict(units[1].metadata))]
    assert before == after


def test_adapter_is_deterministic() -> None:
    units = [
        _Unit(f"u{i}", f"一、第{i}节内容", bbox=(60, 90 + 10 * i, 300, 115 + 10 * i))
        for i in range(6)
    ]
    first = json.dumps(build_observation(units, source_id="s", source_sha256="d"), sort_keys=True)
    second = json.dumps(build_observation(copy.copy(units), source_id="s", source_sha256="d"), sort_keys=True)
    assert first == second


def test_locator_and_unit_id_are_passed_through_untouched() -> None:
    units = [
        _Unit(
            "urn:company-wiki:narrative-unit:sha256:abc",
            "一、业务",
            bbox=(60, 90, 300, 115),
            metadata={"source_locator": "cwp-pdf-block/1|p=1|b=0|sha=deadbeef"},
        )
    ]
    observation = build_observation(units, source_id="s", source_sha256="d")
    assert observation["units"][0]["unit_id"] == "urn:company-wiki:narrative-unit:sha256:abc"
    assert observation["units"][0]["locator"] == "cwp-pdf-block/1|p=1|b=0|sha=deadbeef"


def test_table_row_zero_becomes_the_header_and_rows_share_a_table_id() -> None:
    units = [
        _Unit(
            "r0",
            "项目名称 | 投资总额 | 建设期",
            kind="pdf_table_row",
            coords=_Coords(page=10, table_index=0, row_index=0),
            bbox=(60, 185, 530, 205),
        ),
        _Unit(
            "r1",
            "高端刀具扩产项目 | 28000 | 24 个月",
            kind="pdf_table_row",
            coords=_Coords(page=10, table_index=0, row_index=1),
            bbox=(60, 210, 530, 230),
        ),
    ]
    observation = build_observation(units, source_id="s", source_sha256="d")
    assert observation["units"][0]["kind"] == "table_header"
    assert observation["units"][1]["kind"] == "table_row"
    assert observation["units"][0]["hints"]["table_id"] == observation["units"][1]["hints"]["table_id"]


def test_unit_caption_is_recognized() -> None:
    units = [_Unit("c1", "单位：万元", kind="pdf_text_block", bbox=(60, 160, 200, 178))]
    observation = build_observation(units, source_id="s", source_sha256="d")
    assert observation["units"][0]["kind"] == "table_caption"


def test_qa_speaker_role_is_mapped_from_parser_state() -> None:
    units = [
        _Unit(
            "q1",
            "问：公司是否生产VC？",
            role="qa_text_shadow",
            metadata={"qa_state": "question_paired", "qa_group_id": "g1"},
            bbox=(60, 100, 530, 140),
        ),
        _Unit(
            "a1",
            "答：公司现无生产VC的情况。",
            role="qa_text_shadow",
            metadata={"qa_state": "answer_paired", "qa_group_id": "g1"},
            bbox=(60, 150, 530, 190),
        ),
    ]
    observation = build_observation(units, source_id="s", source_sha256="d")
    assert observation["units"][0]["hints"]["speaker"] == "investor"
    assert observation["units"][1]["hints"]["speaker"] == "management"
    assert observation["units"][0]["hints"]["turn_id"] == "g1"


def test_coverage_carries_through_native_scan_and_pages() -> None:
    units = [_Unit("u1", "一、业务", bbox=(60, 90, 300, 115))]
    observation = build_observation(
        units,
        source_id="s",
        source_sha256="d",
        native_scan="partial",
        opaque_pages=[2],
        deferred_pages=[4],
    )
    assert observation["coverage"]["native_scan"] == "partial"
    assert observation["coverage"]["opaque_pages"] == [2]
    assert observation["coverage"]["deferred_pages"] == [4]


def test_unknown_native_scan_is_not_invented() -> None:
    units = [_Unit("u1", "一、业务", bbox=(60, 90, 300, 115))]
    observation = build_observation(units, source_id="s", source_sha256="d", native_scan="bogus")
    assert observation["coverage"]["native_scan"] == "unavailable"


# ---------------------------------------------------- end-to-end adapter use


def test_adapted_observation_drives_the_structure_lane() -> None:
    units = [
        _Unit("h1", "第三节 募集资金运用", bbox=(60, 90, 300, 115)),
        _Unit("i1", "本次募集资金拟投资于以下项目：", bbox=(60, 130, 530, 155)),
        _Unit("c1", "单位：万元", kind="table_caption", bbox=(60, 160, 200, 178)),
        _Unit(
            "r0",
            "项目名称 | 投资总额 | 募集资金投入额 | 建设期",
            kind="pdf_table_row",
            coords=_Coords(page=62, table_index=0, row_index=0),
            bbox=(60, 185, 530, 205),
        ),
        _Unit(
            "r1",
            "高端精密刀具扩产项目 | 28000 | 20000 | 24 个月",
            kind="pdf_table_row",
            coords=_Coords(page=62, table_index=0, row_index=1),
            bbox=(60, 210, 530, 230),
        ),
        _Unit("p2", "项目建设期为 24 个月，其中前 12 个月完成土建，", page=62, bbox=(60, 300, 530, 345)),
        _Unit("p3", "后 12 个月完成设备安装调试并试生产。", page=63, bbox=(60, 95, 530, 140)),
    ]
    observation = build_observation(units, source_id="s", source_sha256="d")
    structure = build_structure(observation)
    kinds = {unit["kind"] for unit in structure["semantic_units"]}
    assert "project" in kinds, "the adapted observation must yield a project package"
    projects = [u for u in structure["semantic_units"] if u["kind"] == "project"]
    members = set(projects[0]["member_unit_ids"])
    assert "c1" in members, "the unit caption must travel with the project"
    assert "r0" in members, "the table header must travel with the project row"


# ---------------------------------------------------- dependency packages


def _structure_with(semantic_units, sections=None):
    return {
        "schema_version": "du-structure/1",
        "source_ref": {"source_id": "s", "source_sha256": "d"},
        "sections": sections or [],
        "semantic_units": semantic_units,
        "relations": [],
        "coverage": {"complete": True},
        "diagnostics": [],
    }


def test_packages_keep_required_context_when_members_are_bounded() -> None:
    structure = _structure_with(
        [
            {
                "semantic_id": "m1",
                "kind": "operating_table",
                "section_ids": [],
                "member_unit_ids": [f"u{i}" for i in range(10)],
                "anchor_unit_ids": ["u0"],
                "required_context_unit_ids": ["u1", "u2"],
                "completeness": "complete",
                "diagnostics": [],
            }
        ]
    )
    result = build_dependency_packages(structure, max_members=4)
    package = result["packages"][0]
    assert package["truncated"] is True
    assert {"u0", "u1", "u2"} <= set(package["member_unit_ids"])
    assert any(item["code"] == "PACKAGE_TRUNCATED" for item in result["diagnostics"])


def test_packages_never_exceed_the_member_bound() -> None:
    structure = _structure_with(
        [
            {
                "semantic_id": "m1",
                "kind": "project",
                "section_ids": [],
                "member_unit_ids": [f"u{i}" for i in range(50)],
                "anchor_unit_ids": ["u0"],
                "required_context_unit_ids": ["u1"],
                "completeness": "complete",
                "diagnostics": [],
            }
        ]
    )
    result = build_dependency_packages(structure, max_members=8)
    assert len(result["packages"][0]["member_unit_ids"]) <= 8


def test_route_priorities_reorder_but_never_drop_a_package() -> None:
    structure = _structure_with(
        [
            {
                "semantic_id": "m1",
                "kind": "background",
                "section_ids": ["s1"],
                "member_unit_ids": ["u1"],
                "anchor_unit_ids": ["u1"],
                "required_context_unit_ids": [],
                "completeness": "complete",
                "diagnostics": [],
            },
            {
                "semantic_id": "m2",
                "kind": "project",
                "section_ids": ["s2"],
                "member_unit_ids": ["u2"],
                "anchor_unit_ids": ["u2"],
                "required_context_unit_ids": [],
                "completeness": "complete",
                "diagnostics": [],
            },
        ],
        sections=[
            {"section_id": "s1", "section_role": "administrative"},
            {"section_id": "s2", "section_role": "fundraising"},
        ],
    )
    plain = build_dependency_packages(structure)
    routed = build_dependency_packages(
        structure,
        route={
            "section_priorities": [
                {"section_role": "administrative", "aliases": [], "priority": 1},
                {"section_role": "fundraising", "aliases": [], "priority": 3},
            ]
        },
    )
    assert len(plain["packages"]) == len(routed["packages"]) == 2
    assert routed["packages"][0]["section_role"] == "administrative"


def test_packages_without_a_route_still_produce_output() -> None:
    structure = _structure_with(
        [
            {
                "semantic_id": "m1",
                "kind": "paragraph_event",
                "section_ids": [],
                "member_unit_ids": ["u1"],
                "anchor_unit_ids": ["u1"],
                "required_context_unit_ids": [],
                "completeness": "complete",
                "diagnostics": [],
            }
        ]
    )
    result = build_dependency_packages(structure)
    assert result["package_count"] == 1
    assert result["packages"][0]["section_role"] == "unknown"


def test_prompt_materialisation_drops_empty_packages_and_keeps_order() -> None:
    structure = _structure_with(
        [
            {
                "semantic_id": "m1",
                "kind": "project",
                "section_ids": [],
                "member_unit_ids": ["u1", "u2"],
                "anchor_unit_ids": ["u1"],
                "required_context_unit_ids": ["u1"],
                "completeness": "complete",
                "diagnostics": [],
            },
            {
                "semantic_id": "m2",
                "kind": "background",
                "section_ids": [],
                "member_unit_ids": ["u9"],
                "anchor_unit_ids": ["u9"],
                "required_context_unit_ids": [],
                "completeness": "complete",
                "diagnostics": [],
            },
        ]
    )
    packages = build_dependency_packages(structure)
    selected = package_units_for_prompt(packages, {"u1": "项目名称", "u2": "投资总额"})
    assert [item["package_id"] for item in selected] == ["m1"]
    assert [member["unit_id"] for member in selected[0]["members"]] == ["u1", "u2"]


def test_packages_are_json_serialisable() -> None:
    structure = _structure_with(
        [
            {
                "semantic_id": "m1",
                "kind": "risk",
                "section_ids": [],
                "member_unit_ids": ["u1"],
                "anchor_unit_ids": ["u1"],
                "required_context_unit_ids": [],
                "completeness": "complete",
                "diagnostics": [],
            }
        ]
    )
    json.dumps(build_dependency_packages(structure))
