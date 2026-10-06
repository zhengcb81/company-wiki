"""N6-CANDIDATE minimal-context boundaries: completion, links, windows."""

from __future__ import annotations

import re
from pathlib import Path

from company_wiki.source_catalog import (
    narrative_candidates,
    narrative_context,
    narrative_evidence,
    narrative_group_candidates,
    narrative_neighbors,
)
from company_wiki.source_catalog.narrative_candidates import assess_unit
from company_wiki.source_catalog.narrative_context import (
    ContextRules,
    build_section_context,
)
from company_wiki.source_catalog.narrative_document import NarrativeUnit
from company_wiki.source_catalog.narrative_evidence import _make_unit
from company_wiki.source_catalog.narrative_group_candidates import (
    GroupCandidateRules,
    enrich_context_groups,
)
from company_wiki.source_catalog.narrative_neighbors import (
    NeighborRules,
    enrich_neighbor_context,
)
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256


_SOURCE_ID = source_id_for_sha256("6b" + "c" * 62)
_OTHER_SOURCE_ID = source_id_for_sha256("6b" + "d" * 62)


def _unit(
    text: str,
    *,
    source_id: str = _SOURCE_ID,
    page: int = 1,
    paragraph: int = 0,
    role: str = "company_filing",
    language: str = "zh",
    kind: str = "pdf_text_block",
    block: int | None = None,
    metadata: dict | None = None,
) -> NarrativeUnit:
    values: dict = dict(metadata or {})
    if block is not None:
        values.setdefault("pdf_block", block)
    return _make_unit(
        source_id=source_id,
        parser_version="0.1.0",
        coordinates=EvidenceCoordinates(page_number=page, paragraph_index=paragraph),
        raw_text=text,
        unit_kind=kind,
        source_role=role,
        language=language,
        metadata=values,
    )


def _context_rules() -> ContextRules:
    return ContextRules(
        project_heading=re.compile(r"项目建设的必要性|项目建设必要性"),
        business_heading=re.compile(
            r"(?:第[一二三四五六七八九十\d]+节\s*)?业务与技术|主营业务情况"
        ),
        heading_only=re.compile(r"^[一二三四五六七八九十\d]+、"),
    )


def _group_rules() -> GroupCandidateRules:
    return GroupCandidateRules(
        topics=narrative_evidence._topics,
        window_finder=narrative_evidence._minimal_matching_unit_windows,
        project_heading=narrative_evidence._PROJECT_SECTION_HEADING,
        business_heading=narrative_evidence._BUSINESS_SECTION_HEADING,
        high_value_event=narrative_evidence._HIGH_VALUE_EVENT,
        positioning=narrative_evidence._SPECIFIC_BUSINESS_POSITIONING,
        business_risk=narrative_evidence._BUSINESS_RISK_SIGNAL,
        direct_capacity_constraint=narrative_evidence._DIRECT_CAPACITY_CONSTRAINT,
        long_customer_qualification=narrative_evidence._LONG_CUSTOMER_QUALIFICATION,
        project_certification_timeline=narrative_evidence._PROJECT_CERTIFICATION_TIMELINE,
        quantified_market_coverage_target=narrative_evidence._QUANTIFIED_MARKET_COVERAGE_TARGET,
        permit_milestone=narrative_evidence._PERMIT_ACQUIRED_MILESTONE,
        new_product_milestone=narrative_evidence._NEW_PRODUCT_COMMERCIALIZATION,
        project_rationale=narrative_evidence._PROJECT_RATIONALE_SIGNAL,
        downstream_extension=narrative_evidence._DOWNSTREAM_BUSINESS_EXTENSION,
        project_plan=narrative_evidence._PROJECT_PLAN,
        strategic_plan=narrative_evidence._STRATEGIC_PLAN,
        table_of_contents=narrative_evidence._TABLE_OF_CONTENTS,
        accounting_context=narrative_evidence._EXCLUDED_NARRATIVE_CONTEXT,
        static_definition=narrative_evidence._STATIC_DEFINITION,
        progress=narrative_evidence._PROGRESS,
        recency=narrative_evidence._RECENCY,
        downstream_center_timeline=narrative_evidence._DOWNSTREAM_CENTER_CERTIFICATION_TIMELINE,
    )


def _neighbor_rules() -> NeighborRules:
    return NeighborRules(
        topics=narrative_evidence._topics,
        high_value_event=narrative_evidence._HIGH_VALUE_EVENT,
        named_product_context=narrative_evidence._NAMED_PRODUCT_CONTEXT,
        accounting_context=narrative_evidence._EXCLUDED_NARRATIVE_CONTEXT,
        project_rationale=narrative_evidence._PROJECT_RATIONALE_SIGNAL,
        table_of_contents=narrative_evidence._TABLE_OF_CONTENTS,
    )


def _candidate_rules():
    return narrative_evidence._candidate_rules()


def test_boundary_modules_come_from_this_worktree_src() -> None:
    root = Path(__file__).resolve().parents[2] / "src"
    for module in (
        narrative_candidates,
        narrative_context,
        narrative_group_candidates,
        narrative_neighbors,
        narrative_evidence,
    ):
        location = module.__file__
        assert location is not None
        assert Path(location).resolve().is_relative_to(root)


def _completion_group(source_id: str = _SOURCE_ID, page: int = 1):
    unrelated = _unit(
        "公司总部位于上海市浦东新区。",
        source_id=source_id,
        page=page,
        paragraph=0,
        block=11,
    )
    subject = _unit(
        "公司新一代刻蚀设备", source_id=source_id, page=page, paragraph=1, block=11
    )
    hit = _unit(
        "已通过国际一线客户验证，",
        source_id=source_id,
        page=page,
        paragraph=2,
        block=11,
    )
    tail = _unit(
        "并开始在5纳米产线批量交付。",
        source_id=source_id,
        page=page,
        paragraph=3,
        block=11,
    )
    members = (unrelated, subject, hit, tail)
    group = ("g-completion", members, "".join(unit.raw_text for unit in members))
    return group, members


def _initial_hit(hit: NarrativeUnit):
    candidate = assess_unit(hit, _candidate_rules()).candidate
    assert candidate is not None, "fixture hit must already be a baseline candidate"
    return (candidate,)


def test_completion_adds_sentence_fragments_around_existing_hit() -> None:
    group, (unrelated, subject, hit, tail) = _completion_group()
    initial = _initial_hit(hit)

    result = enrich_context_groups(
        (group,),
        initial_candidates=initial,
        initial_group_ids={},
        project_scores={},
        business_scores={},
        rules=_group_rules(),
    )

    candidate_ids = [candidate.unit.unit_id for candidate in result.candidates]
    assert subject.unit_id in candidate_ids
    assert tail.unit_id in candidate_ids
    assert unrelated.unit_id not in candidate_ids
    group_id = result.group_ids.get(hit.unit_id)
    assert group_id is not None
    assert result.group_ids.get(subject.unit_id) == group_id
    assert result.group_ids.get(tail.unit_id) == group_id
    assert unrelated.unit_id not in result.group_ids


def test_completion_keeps_original_units_byte_identical() -> None:
    group, (unrelated, subject, hit, tail) = _completion_group()
    initial = _initial_hit(hit)

    result = enrich_context_groups(
        (group,),
        initial_candidates=initial,
        initial_group_ids={},
        project_scores={},
        business_scores={},
        rules=_group_rules(),
    )

    originals = {unit.unit_id: unit for unit in (unrelated, subject, hit, tail)}
    for candidate in result.candidates:
        original = originals[candidate.unit.unit_id]
        assert candidate.unit is original
        assert candidate.unit.raw_text == original.raw_text
        assert candidate.unit.coordinates == original.coordinates


def test_completion_is_deterministic_across_runs() -> None:
    group, (_, _, hit, _) = _completion_group()
    initial = _initial_hit(hit)

    first = enrich_context_groups(
        (group,),
        initial_candidates=initial,
        initial_group_ids={},
        project_scores={},
        business_scores={},
        rules=_group_rules(),
    )
    second = enrich_context_groups(
        (group,),
        initial_candidates=initial,
        initial_group_ids={},
        project_scores={},
        business_scores={},
        rules=_group_rules(),
    )

    assert [c.unit.unit_id for c in first.candidates] == [
        c.unit.unit_id for c in second.candidates
    ]
    assert dict(first.group_ids) == dict(second.group_ids)


def test_completion_never_links_across_sources() -> None:
    subject = _unit(
        "公司新一代刻蚀设备", source_id=_SOURCE_ID, page=1, paragraph=1, block=21
    )
    hit = _unit(
        "已通过国际一线客户验证，",
        source_id=_OTHER_SOURCE_ID,
        page=1,
        paragraph=2,
        block=21,
    )
    group = ("g-cross-source", (subject, hit), subject.raw_text + hit.raw_text)
    initial = _initial_hit(hit)

    result = enrich_context_groups(
        (group,),
        initial_candidates=initial,
        initial_group_ids={},
        project_scores={},
        business_scores={},
        rules=_group_rules(),
    )

    subject_group = result.group_ids.get(subject.unit_id)
    hit_group = result.group_ids.get(hit.unit_id)
    assert not (subject_group is not None and subject_group == hit_group)


def test_completion_never_links_across_languages() -> None:
    subject = _unit(
        "New product series for advanced packaging",
        source_id=_SOURCE_ID,
        page=1,
        paragraph=1,
        block=22,
        language="en",
    )
    hit = _unit(
        "已通过国际一线客户验证，", source_id=_SOURCE_ID, page=1, paragraph=2, block=22
    )
    group = ("g-cross-language", (subject, hit), subject.raw_text + " " + hit.raw_text)

    result = enrich_context_groups(
        (group,),
        initial_candidates=(),
        initial_group_ids={},
        project_scores={},
        business_scores={},
        rules=_group_rules(),
    )

    subject_group = result.group_ids.get(subject.unit_id)
    hit_group = result.group_ids.get(hit.unit_id)
    assert not (subject_group is not None and subject_group == hit_group)


def test_completion_never_links_across_pages() -> None:
    subject = _unit(
        "公司新一代刻蚀设备", source_id=_SOURCE_ID, page=1, paragraph=1, block=23
    )
    hit = _unit(
        "已通过国际一线客户验证，", source_id=_SOURCE_ID, page=2, paragraph=2, block=23
    )
    group = ("g-cross-page", (subject, hit), subject.raw_text + hit.raw_text)

    result = enrich_context_groups(
        (group,),
        initial_candidates=(),
        initial_group_ids={},
        project_scores={},
        business_scores={},
        rules=_group_rules(),
    )

    subject_group = result.group_ids.get(subject.unit_id)
    hit_group = result.group_ids.get(hit.unit_id)
    assert not (subject_group is not None and subject_group == hit_group)


def test_question_units_are_never_grouped_with_answers() -> None:
    question = _unit(
        "请问产能利用率如何？",
        source_id=_SOURCE_ID,
        page=1,
        paragraph=1,
        block=24,
        role="investor_question",
    )
    answer = _unit(
        "目前产能利用率已达到85%。",
        source_id=_SOURCE_ID,
        page=1,
        paragraph=2,
        block=24,
        role="management",
    )
    group = ("g-qa", (question, answer), question.raw_text + answer.raw_text)

    result = enrich_context_groups(
        (group,),
        initial_candidates=(),
        initial_group_ids={},
        project_scores={},
        business_scores={},
        rules=_group_rules(),
    )

    assert question.unit_id not in {
        candidate.unit.unit_id for candidate in result.candidates
    }
    answer_group = result.group_ids.get(answer.unit_id)
    question_group = result.group_ids.get(question.unit_id)
    assert not (question_group is not None and question_group == answer_group)


def test_existing_group_assignment_is_not_silently_overridden() -> None:
    first = _unit(
        "公司新一代刻蚀设备", source_id=_SOURCE_ID, page=1, paragraph=1, block=25
    )
    second = _unit(
        "已通过国际一线客户验证并开始批量交付。",
        source_id=_SOURCE_ID,
        page=1,
        paragraph=2,
        block=25,
    )
    group = ("g-conflict", (first, second), first.raw_text + second.raw_text)

    result = enrich_context_groups(
        (group,),
        initial_candidates=(),
        initial_group_ids={first.unit_id: "urn:company-wiki:context-group:existing"},
        project_scores={},
        business_scores={},
        rules=_group_rules(),
    )

    assert result.group_ids[first.unit_id] == "urn:company-wiki:context-group:existing"
    assert second.unit_id in result.group_ids


def test_whole_visual_group_is_bounded_by_character_window() -> None:
    lead = "公司特种传感器产品已通过客户验证，并交付头部客户使用。"
    members = (
        _unit(lead + "甲" * (700 - len(lead)), page=1, paragraph=1, block=31),
        _unit("乙" * 700, page=1, paragraph=2, block=31),
        _unit("丙" * 700, page=1, paragraph=3, block=31),
    )
    group = ("g-giant", members, "".join(unit.raw_text for unit in members))

    result = enrich_context_groups(
        (group,),
        initial_candidates=(),
        initial_group_ids={},
        project_scores={},
        business_scores={},
        rules=_group_rules(),
    )

    candidate_ids = {candidate.unit.unit_id for candidate in result.candidates}
    assert members[0].unit_id in candidate_ids
    assert members[1].unit_id in candidate_ids
    assert members[2].unit_id not in candidate_ids
    added = sum(
        len(candidate.unit.raw_text)
        for candidate in result.candidates
        if candidate.unit.unit_id in {members[0].unit_id, members[1].unit_id}
    )
    assert added <= 1_600


def test_business_section_context_window_bounds_member_addition() -> None:
    members = (
        _unit("甲" * 800, page=1, paragraph=1, block=32),
        _unit("乙" * 800, page=1, paragraph=2, block=32),
    )
    group = ("g-business-window", members, "".join(unit.raw_text for unit in members))

    result = enrich_context_groups(
        (group,),
        initial_candidates=(),
        initial_group_ids={},
        project_scores={},
        business_scores={"g-business-window": 140},
        rules=_group_rules(),
    )

    candidate_ids = [candidate.unit.unit_id for candidate in result.candidates]
    assert candidate_ids == [members[0].unit_id]


def test_group_facts_are_recognized_on_joined_text_only() -> None:
    members = (
        _unit(
            "从克重口径看，目前达到一个稳定的状态，一口价黄金占比",
            page=1,
            paragraph=1,
            block=33,
        ),
        _unit("在15%-20%，其中高端产品占比", page=1, paragraph=2, block=33),
        _unit("在30%左右", page=1, paragraph=3, block=33),
    )
    group = ("g-fact-join", members, "".join(unit.raw_text for unit in members))

    result = enrich_context_groups(
        (group,),
        initial_candidates=(),
        initial_group_ids={},
        project_scores={},
        business_scores={},
        rules=_group_rules(),
    )

    candidate_ids = [candidate.unit.unit_id for candidate in result.candidates]
    assert candidate_ids == [unit.unit_id for unit in members]
    group_id = result.group_ids.get(members[0].unit_id)
    assert group_id is not None
    assert all(result.group_ids.get(unit.unit_id) == group_id for unit in members)


def _context_fixture(groups):
    return build_section_context("equity_offering_prospectus", groups, _context_rules())


def test_section_context_does_not_score_a_group_larger_than_the_window() -> None:
    heading = _unit("项目建设的必要性", page=1, paragraph=0, block=41)
    body_small = _unit(
        "本项目用于新产品产业化。" + "甲" * 270, page=1, paragraph=1, block=42
    )
    body_oversized = _unit("乙" * 1_800, page=1, paragraph=2, block=43)
    groups = (
        ("h", (heading,), heading.raw_text),
        ("small", (body_small,), body_small.raw_text),
        ("oversized", (body_oversized,), body_oversized.raw_text),
    )

    context = _context_fixture(groups)

    assert "small" in context.project_scores
    assert "oversized" not in context.project_scores
    assert "h" not in context.project_scores


def test_section_context_window_closes_before_would_be_overflow_group() -> None:
    heading = _unit("项目建设的必要性", page=1, paragraph=0, block=51)
    body_units = tuple(
        _unit(
            f"第{index}段项目说明内容。" + "甲" * (300 - 12),
            page=1,
            paragraph=index,
            block=51 + index,
        )
        for index in range(1, 7)
    )
    groups = (("h", (heading,), heading.raw_text),) + tuple(
        (f"b{index}", (unit,), unit.raw_text)
        for index, unit in enumerate(body_units, start=1)
    )

    context = _context_fixture(groups)

    assert sorted(context.project_scores) == ["b1", "b2", "b3", "b4", "b5"]


def test_business_section_context_window_is_1200_characters() -> None:
    heading = _unit("业务与技术", page=1, paragraph=0, block=61)
    first = _unit("甲" * 300, page=1, paragraph=1, block=62)
    second = _unit("乙" * 1_000, page=1, paragraph=2, block=63)
    groups = (
        ("bh", (heading,), heading.raw_text),
        ("b1", (first,), first.raw_text),
        ("b2", (second,), second.raw_text),
    )

    context = build_section_context("prospectus", groups, _context_rules())

    assert sorted(context.business_scores) == ["b1"]
    assert context.project_scores == {}


def _neighbor_pair(
    prev_source: str = _SOURCE_ID, prev_language: str = "zh", prev_page: int = 1
):
    if prev_language == "zh":
        prev = _unit(
            "新一代高纯电子特气产品系列",
            source_id=prev_source,
            page=prev_page,
            paragraph=0,
            block=71,
            language=prev_language,
        )
    else:
        prev = _unit(
            "New product series for advanced packaging",
            source_id=prev_source,
            page=prev_page,
            paragraph=0,
            block=71,
            language=prev_language,
        )
    event = _unit(
        "上述产品已经取得客户验证并开始批量交付。",
        source_id=_SOURCE_ID,
        page=prev_page,
        paragraph=1,
        block=71,
    )
    return prev, event


def _neighbor_initial(event: NarrativeUnit):
    candidate = assess_unit(event, narrative_evidence._candidate_rules()).candidate
    assert candidate is not None, "neighbor fixture event must be a baseline candidate"
    return (candidate,)


def test_neighbor_adjacency_never_crosses_sources() -> None:
    prev, event = _neighbor_pair(prev_source=_OTHER_SOURCE_ID)
    initial = _neighbor_initial(event)

    result = enrich_neighbor_context(
        (prev, event),
        initial_candidates=initial,
        initial_group_ids={},
        rules=_neighbor_rules(),
    )

    added_ids = {candidate.unit.unit_id for candidate in result.candidates}
    assert added_ids == {event.unit_id}


def test_neighbor_adjacency_never_crosses_languages() -> None:
    prev, event = _neighbor_pair(prev_language="en")
    initial = _neighbor_initial(event)

    result = enrich_neighbor_context(
        (prev, event),
        initial_candidates=initial,
        initial_group_ids={},
        rules=_neighbor_rules(),
    )

    added_ids = {candidate.unit.unit_id for candidate in result.candidates}
    assert added_ids == {event.unit_id}


def test_neighbor_group_conflict_is_not_overridden() -> None:
    prev, event = _neighbor_pair()
    initial = _neighbor_initial(event)
    initial_group_ids = {
        event.unit_id: "urn:company-wiki:context-group:event",
        prev.unit_id: "urn:company-wiki:context-group:prev",
    }

    result = enrich_neighbor_context(
        (prev, event),
        initial_candidates=initial,
        initial_group_ids=initial_group_ids,
        rules=_neighbor_rules(),
    )

    assert result.group_ids[event.unit_id] == "urn:company-wiki:context-group:event"
    assert result.group_ids[prev.unit_id] == "urn:company-wiki:context-group:prev"
    assert prev.unit_id not in {c.unit.unit_id for c in result.candidates}


def test_linked_question_never_shares_the_answer_group() -> None:
    answer = _unit(
        "We added 31 new data centers across 5 continents this quarter.",
        page=1,
        paragraph=0,
        role="management",
        language="en",
        kind="transcript_line",
        metadata={"qa_group_id": "qa:1"},
    )
    question = _unit(
        "Can you share more about capacity constraints this quarter?",
        page=1,
        paragraph=2,
        role="investor_question",
        language="en",
        kind="transcript_line",
        metadata={"qa_group_id": "qa:1"},
    )
    candidate = assess_unit(answer, narrative_evidence._candidate_rules()).candidate
    assert candidate is not None

    result = enrich_neighbor_context(
        (answer, question),
        initial_candidates=(candidate,),
        initial_group_ids={answer.unit_id: "urn:company-wiki:context-group:answer"},
        rules=_neighbor_rules(),
    )

    question_ids = {
        item.unit.unit_id
        for item in result.candidates
        if item.unit.source_role == "investor_question"
    }
    assert question_ids == {question.unit_id}
    assert question.unit_id not in result.group_ids
    assert result.group_ids[answer.unit_id] == "urn:company-wiki:context-group:answer"
