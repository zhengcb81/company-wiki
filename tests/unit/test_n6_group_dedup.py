"""N6-BUDGET group dedup: conservative, whole-group, role-safe."""

from __future__ import annotations

import builtins
import hashlib
import re

import pytest

from company_wiki.source_catalog.n6_budget_dedup import (
    deduplicate_candidates,
)
from company_wiki.source_catalog.narrative_candidates import EvidenceCandidate
from company_wiki.source_catalog.narrative_document import NarrativeUnit
from company_wiki.source_catalog.narrative_evidence import _make_unit
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256


SOURCE_SHA = "a" * 64
SOURCE_ID = source_id_for_sha256(SOURCE_SHA)


def _unit(
    text: str,
    *,
    page: int = 1,
    paragraph: int = 0,
    role: str = "company_filing",
    kind: str = "pdf_text_block",
    table: int | None = None,
    row: int | None = None,
    column: int | None = None,
) -> NarrativeUnit:
    return _make_unit(
        source_id=SOURCE_ID,
        parser_version="0.1.0",
        coordinates=EvidenceCoordinates(
            page_number=page,
            paragraph_index=None if table is not None else paragraph,
            table_index=table,
            row_index=row,
            column_index=column,
        ),
        raw_text=text,
        unit_kind=kind,
        source_role=role,
        language="zh",
        metadata={},
    )


def _candidate(
    unit: NarrativeUnit,
    *,
    reasons: tuple[str, ...] = ("specific_business_event",),
    score: int = 6,
    topics: tuple[str, ...] = ("core_business",),
) -> EvidenceCandidate:
    return EvidenceCandidate(unit, topics, reasons, score)


def _normalized(text: str) -> str:
    return re.sub(r"\s+", "", text.replace("|", " ")).casefold()


def _text_sha256(unit: NarrativeUnit) -> str:
    return hashlib.sha256(unit.raw_text.encode("utf-8")).hexdigest()


def test_cross_page_repeat_of_one_event_costs_one_quota() -> None:
    first = _candidate(
        _unit("本次募投项目达产后预计新增产能50万件。", page=3, paragraph=7)
    )
    second = _candidate(
        _unit("本次募投项目达产后预计新增产能50万件。", page=43, paragraph=25)
    )

    result = deduplicate_candidates((first, second), {})

    assert len(result.candidates) == 1
    survivor = result.candidates[0]
    assert survivor.unit.coordinates.page_number in {3, 43}
    assert len(result.drops) == 1
    drop = result.drops[0]
    assert drop.unit_id in {first.unit.unit_id, second.unit.unit_id}
    assert drop.locator
    assert drop.kept_unit_id == survivor.unit.unit_id


def test_whitespace_and_table_separator_variants_collapse_to_the_table_row() -> None:
    text_block = _candidate(_unit("产能利用率 | 98.5%", page=12, paragraph=4), score=6)
    table_row = _candidate(
        _unit(
            "产能利用率|98.5%",
            page=12,
            paragraph=4,
            kind="pdf_table_row",
            table=1,
            row=3,
            column=2,
        ),
        score=7,
    )

    result = deduplicate_candidates((text_block, table_row), {})

    assert len(result.candidates) == 1
    survivor = result.candidates[0]
    assert survivor.unit.unit_kind == "pdf_table_row"
    assert survivor.unit.unit_id == table_row.unit.unit_id


@pytest.mark.parametrize(
    ("left", "right"),
    (
        ("中微公司刻蚀设备已通过验证。", "北方华创刻蚀设备已通过验证。"),
        ("2025年产能利用率达到98%。", "2024年产能利用率达到98%。"),
        ("募投项目已取得环评批复。", "募投项目未取得环评批复。"),
        ("公司已完成客户验证。", "公司尚未完成客户验证。"),
        ("该项目由子公司实施。", "该项目由母公司实施。"),
    ),
)
def test_similar_but_different_content_is_never_merged(left: str, right: str) -> None:
    first = _candidate(_unit(left, page=1, paragraph=1))
    second = _candidate(_unit(right, page=1, paragraph=2))

    result = deduplicate_candidates((first, second), {})

    assert len(result.candidates) == 2
    assert result.drops == ()


def test_different_roles_are_never_merged_even_with_identical_text() -> None:
    text = "新产品已通过客户验证并开始批量交付。"
    answer = _candidate(_unit(text, page=5, paragraph=1, role="management"))
    question = _candidate(
        _unit(text, page=5, paragraph=2, role="investor_question"),
        reasons=("linked_question_context",),
        score=0,
    )

    result = deduplicate_candidates((answer, question), {})

    assert len(result.candidates) == 2
    assert result.drops == ()


def test_repeated_event_group_is_kept_whole_or_dropped_whole() -> None:
    texts = (
        "航空数字化集成中心项目属于现有业务的延伸和拓展，",
        "需要进行合格供应商认证和产品认证，",
        "预计需要4-9个月。",
    )
    first_group = tuple(
        _candidate(_unit(text, page=3, paragraph=index))
        for index, text in enumerate(texts)
    )
    second_group = tuple(
        _candidate(_unit(text, page=161, paragraph=index))
        for index, text in enumerate(texts)
    )
    group_ids: dict[str, str] = {}
    for candidate in first_group:
        group_ids[candidate.unit.unit_id] = "urn:group:timeline-a"
    for candidate in second_group:
        group_ids[candidate.unit.unit_id] = "urn:group:timeline-b"

    result = deduplicate_candidates((*first_group, *second_group), group_ids)

    surviving_groups = {
        result.group_ids[candidate.unit.unit_id] for candidate in result.candidates
    }
    assert len(result.candidates) == 3
    assert len(surviving_groups) == 1
    input_groups = set(group_ids.values())
    assert {drop.group_id for drop in result.drops} == input_groups - surviving_groups
    assert {drop.unit_id for drop in result.drops} == (
        {c.unit.unit_id for c in (*first_group, *second_group)}
        - {c.unit.unit_id for c in result.candidates}
    )


def test_partially_overlapping_groups_are_conservatively_kept() -> None:
    shared = _candidate(_unit("公司现有产能约为6,300万片，通过", page=7, paragraph=1))
    only_first = _candidate(
        _unit("募投项目达产后新增刀体产品50万件。", page=7, paragraph=2)
    )
    only_second = _candidate(
        _unit("募投项目达产后新增刀体产品80万件。", page=43, paragraph=9)
    )
    group_ids = {
        shared.unit.unit_id: "urn:group:a",
        only_first.unit.unit_id: "urn:group:a",
        only_second.unit.unit_id: "urn:group:b",
    }

    result = deduplicate_candidates((shared, only_first, only_second), group_ids)

    assert len(result.candidates) == 3
    assert result.drops == ()


def test_group_contained_in_a_richer_group_is_dropped_without_splitting_it() -> None:
    head = "公司具备实施本次募投项目所需的全部资质，包括"
    tail = "武器装备科研生产许可证和装备承制单位资格证书。"
    rich_group = (
        _candidate(_unit(head, page=163, paragraph=1)),
        _candidate(_unit(tail, page=163, paragraph=2)),
    )
    poor_group = (_candidate(_unit(head, page=6, paragraph=4)),)
    group_ids = {
        rich_group[0].unit.unit_id: "urn:group:rich",
        rich_group[1].unit.unit_id: "urn:group:rich",
        poor_group[0].unit.unit_id: "urn:group:poor",
    }

    result = deduplicate_candidates((*rich_group, *poor_group), group_ids)

    kept_groups = {
        result.group_ids[candidate.unit.unit_id] for candidate in result.candidates
    }
    assert kept_groups == {"urn:group:rich"}
    assert len(result.candidates) == 2
    assert {drop.group_id for drop in result.drops} == {"urn:group:poor"}
    assert [drop.unit_id for drop in result.drops] == [poor_group[0].unit.unit_id]


def test_group_ids_are_never_dangling_and_never_newly_merged() -> None:
    first = _candidate(_unit("第一段业务进展说明文字。", page=1, paragraph=1))
    second = _candidate(_unit("第二段业务进展说明文字。", page=1, paragraph=2))
    third = _candidate(_unit("第三段业务进展说明文字。", page=2, paragraph=1))
    group_ids = {first.unit.unit_id: "urn:group:one"}

    result = deduplicate_candidates((first, second, third), group_ids)

    kept_ids = {candidate.unit.unit_id for candidate in result.candidates}
    assert kept_ids == {
        first.unit.unit_id,
        second.unit.unit_id,
        third.unit.unit_id,
    }
    assert set(result.group_ids) <= kept_ids
    assert result.group_ids == {first.unit.unit_id: "urn:group:one"}


def test_statement_and_question_never_share_a_group_id() -> None:
    answer = _candidate(
        _unit(
            "答：新产品已通过客户验证并取得首批订单。",
            page=5,
            paragraph=1,
            role="management",
        )
    )
    question = _candidate(
        _unit(
            "问：新产品什么时候通过客户验证？",
            page=5,
            paragraph=0,
            role="investor_question",
        ),
        reasons=("linked_question_context",),
        score=0,
    )
    shared = "urn:company-wiki:context-group:sha256:" + "c" * 64
    group_ids = {answer.unit.unit_id: shared, question.unit.unit_id: shared}

    result = deduplicate_candidates((answer, question), group_ids)

    answer_group = result.group_ids[answer.unit.unit_id]
    question_group = result.group_ids[question.unit.unit_id]
    assert answer_group != question_group
    assert answer_group.startswith(shared)
    assert question_group.startswith(shared)


def test_canonical_member_keeps_its_real_identity_and_locator() -> None:
    kept_unit = _unit("公司EPI 设备已进入客户端量产验证阶段。", page=40, paragraph=8)
    kept = _candidate(kept_unit)
    duplicate = _candidate(
        _unit("公司EPI 设备已进入客户端量产验证阶段。", page=180, paragraph=3)
    )

    result = deduplicate_candidates((duplicate, kept), {})

    survivor = result.candidates[0]
    assert survivor.unit.unit_id == kept_unit.unit_id
    assert survivor.unit.coordinates.locator() == kept_unit.coordinates.locator()
    assert result.drops[0].unit_id == duplicate.unit.unit_id
    assert result.drops[0].kept_unit_id == kept_unit.unit_id
    assert result.group_ids == {}


def test_a_unit_recorded_twice_is_emitted_once() -> None:
    unit = _unit("本次募集资金拟投资于两条生产线建设项目。", page=43, paragraph=10)
    weak = _candidate(unit, reasons=("project_plan_or_status",), score=3)
    strong = _candidate(unit, reasons=("specific_business_event",), score=94)
    group_ids = {unit.unit_id: "urn:group:raise"}

    result = deduplicate_candidates((weak, strong), group_ids)

    assert len(result.candidates) == 1
    survivor = result.candidates[0]
    assert survivor.unit.unit_id == unit.unit_id
    assert survivor.score == 94
    assert len(result.drops) == 1
    assert result.drops[0].reason == "same_unit_repeat"


def test_drops_keep_locator_and_text_identity_for_audit() -> None:
    first = _unit("落后产能行业为炼铁、炼钢、焦炭。", page=128, paragraph=3)
    second = _unit("落后产能行业为炼铁、炼钢、焦炭。", page=146, paragraph=3)

    result = deduplicate_candidates((_candidate(second), _candidate(first)), {})

    drop = result.drops[0]
    dropped_unit = first if drop.unit_id == first.unit_id else second
    survivor = result.candidates[0].unit
    assert drop.locator == dropped_unit.coordinates.locator()
    assert drop.text_sha256 == _text_sha256(dropped_unit)
    assert _normalized(survivor.raw_text) == _normalized(dropped_unit.raw_text)
    assert drop.reason in {
        "duplicate_event_group",
        "contained_group",
        "intra_group_repeat",
    }


def test_dedup_uses_only_the_current_in_memory_inputs(monkeypatch) -> None:
    candidates = (
        _candidate(_unit("公司已完成海外客户验证。", page=1, paragraph=1)),
        _candidate(_unit("公司已完成海外客户验证。", page=9, paragraph=1)),
    )

    def blocked(*_args, **_kwargs):
        raise AssertionError("dedup must not touch the filesystem or network")

    monkeypatch.setattr(builtins, "open", blocked)

    result = deduplicate_candidates(candidates, {})

    assert len(result.candidates) == 1
