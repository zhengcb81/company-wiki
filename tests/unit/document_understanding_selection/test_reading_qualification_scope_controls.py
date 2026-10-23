"""Independent public source-scope controls for local restrictive statements.

Synthetic native observations only; real package builders, selector, dependency
closure and source citation views run without patched phases or parsed files.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from hashlib import sha256

import pytest

from company_wiki.resource_budget import DEFAULT_DOCUMENT_WORK_LIMIT, WorkBudget
from company_wiki.source_catalog import narrative_reading as reading
from company_wiki.source_catalog.narrative_native_ranges import build_native_page_view
from unit.document_understanding_selection.test_reading_native_carriers import source_fixture

LEFT = "报告期内，公司已交付27台专用设备至客户进行生产验证。"
FUTURE = "未来公司计划改善内部管理。"
HEADING = "一、设备生产线扩建项目"

TRUE_RESTRICTIONS = (
    "该设备尚未完成量产认证，不代表已经形成批量销售。",
    "该设备仍需客户完成认证，预计下一期才能进入量产。",
    "该设备已完成客户验证，但尚未获得量产认证。",
)
NOT_SAME_OBJECT_RESTRICTIONS = (
    "该设备供应商的另一设备尚未完成量产认证。",
    "该设备尚未完成量产认证的说法并不成立。",
    "该设备尚未完成认证是竞争对手的说法，公司已澄清该说法不实。",
    "该设备的供应商尚未完成量产认证。",
    "该设备的客户尚未完成量产认证。",
    "该设备是否尚未完成量产认证？",
    "该平台尚未完成客户认证。",
)


@pytest.fixture(autouse=True)
def imports_are_current_checkout():
    assert Path(reading.__file__).resolve().is_relative_to(Path(__file__).resolve().parents[3] / "src")


def _source(texts, *, source_sha="c" * 64):
    parsed, _ = source_fixture([(text,) for text in texts], source_sha=source_sha)
    return parsed


def _select(parsed, *, max_selected=96, max_chars=48000):
    before = [(u.unit_id, u.source_id, u.raw_text, u.coordinates, repr(u.metadata)) for u in parsed.units]
    budget = WorkBudget(DEFAULT_DOCUMENT_WORK_LIMIT)
    selected = reading.select_reading_evidence(parsed, title="Neutral annual report",
        existing_kind="annual_report", max_selected=max_selected, max_chars=max_chars, work_budget=budget)
    assert before == [(u.unit_id, u.source_id, u.raw_text, u.coordinates, repr(u.metadata)) for u in parsed.units]
    assert not budget.exhausted and 0 < budget.used <= 16_000_000
    assert selected.selection_limit == max_selected
    assert len(selected.evidence_spans) <= max_selected
    assert sum(len(s.raw_text) for s in selected.evidence_spans) <= max_chars
    return selected


def _support_views(selected, unit, *, required=True):
    matches = [s for s in selected.evidence_spans if s.raw_text == unit.raw_text
               and s.source_id == unit.source_id and s.coordinates == unit.coordinates]
    if required:
        assert len(matches) == 1, "The original independent source fact must remain usable."
    ids = {s.span_id for s in matches}
    by_id = {s.span_id: s for s in selected.evidence_spans}
    return [[by_id[sid].raw_text for sid in [*view["support_evidence_ids"], *view["context_evidence_ids"]]]
            for group in selected.reading_context["groups"] for view in group["citation_views"]
            if ids.intersection(view["support_evidence_ids"])]


@pytest.mark.parametrize("right", TRUE_RESTRICTIONS)
def test_real_same_object_restriction_is_required_from_both_selected_directions(right):
    parsed = _source([HEADING, LEFT, right, FUTURE])
    selected = _select(parsed)
    fact_views = _support_views(selected, parsed.units[1])
    assert fact_views and all(right in view for view in fact_views)
    qualifier_views = _support_views(selected, parsed.units[2], required=False)
    assert all(LEFT in view for view in qualifier_views)
    assert all(FUTURE not in view for view in [*fact_views, *qualifier_views])
    tight = _select(parsed, max_selected=2)
    tight_views = _support_views(tight, parsed.units[1], required=False)
    assert all(right in view for view in tight_views)
    qualifier_views = _support_views(tight, parsed.units[2], required=False)
    assert all(LEFT in view for view in qualifier_views)


@pytest.mark.parametrize("right", NOT_SAME_OBJECT_RESTRICTIONS)
def test_other_object_denied_claim_and_question_do_not_certify_a_restriction(right):
    parsed = _source([HEADING, LEFT, right, FUTURE])
    selected = _select(parsed)
    views = _support_views(selected, parsed.units[1])
    assert views and all(right not in view for view in views), (
        "A deictic inside a different subject or denied/quoted assertion cannot restrict this issuer device."
    )
    assert all(FUTURE not in view for view in views)


@pytest.mark.parametrize("left", (
    "公司已交付甲型设备和乙型设备至客户进行生产验证。",
    "供应商已交付27台专用设备至客户进行生产验证。",
))
def test_competing_or_nonissuer_device_objects_do_not_donate_a_unique_identity(left):
    right = "该设备尚未完成量产认证。"
    parsed = _source([HEADING, left, right, FUTURE])
    selected = _select(parsed)
    views = _support_views(selected, parsed.units[1], required=False)
    assert all(right not in view for view in views)


@pytest.mark.parametrize("barrier", ("二、另一项目基本情况", "二、经营风险"))
def test_native_section_or_project_boundary_prevents_local_object_borrowing(barrier):
    right = "该设备尚未完成量产认证。"
    parsed = _source([HEADING, LEFT, barrier, right, FUTURE])
    selected = _select(parsed)
    assert all(right not in view for view in _support_views(selected, parsed.units[1]))


def test_another_original_parent_cannot_supply_a_local_qualification():
    first = _source([HEADING, LEFT])
    second = _source(["该设备尚未完成量产认证。", FUTURE], source_sha="d" * 64)
    parsed = replace(first, units=first.units + second.units)
    selected = _select(parsed)
    assert all(second.units[0].raw_text not in view for view in _support_views(selected, first.units[1]))
    by_id = {span.span_id: span for span in selected.evidence_spans}
    for group in selected.reading_context["groups"]:
        assert len({by_id[sid].source_id for sid in group["evidence_ids"]}) == 1


def test_true_qualifier_and_subject_do_not_split_at_the_actual_character_limit():
    right = TRUE_RESTRICTIONS[0]
    parsed = _source([HEADING, LEFT, right, FUTURE])
    selected = _select(parsed, max_chars=len(HEADING) + len(LEFT) + len(right) - 1)
    assert all(right in view for view in _support_views(selected, parsed.units[1], required=False))
    assert all(LEFT in view for view in _support_views(selected, parsed.units[2], required=False))

CHAIN = (LEFT, "该设备尚未完成量产认证。", "该设备仍未开始量产。")


def test_proved_same_object_restriction_chain_has_one_complete_bounded_citation():
    parsed = _source([HEADING, *CHAIN, FUTURE])
    selected = _select(parsed)
    for unit in parsed.units[1:4]:
        views = _support_views(selected, unit)
        assert views and all(set(CHAIN) <= set(view) and FUTURE not in view for view in views)
    # Three slots cannot contain a heading plus all three source bodies. No
    # positive prefix or bare final deictic may become a cheaper complete fact.
    for cap in (2, 3):
        tight = _select(parsed, max_selected=cap)
        assert not set(CHAIN).intersection(s.raw_text for s in tight.evidence_spans)


@pytest.mark.parametrize("limit", ("blocks", "characters"))
def test_long_same_object_chain_is_deferred_as_a_whole_original_envelope(limit):
    qualifiers = ["该设备尚未完成量产认证。", "该设备仍未开始量产。", "该设备尚未商业化。"]
    if limit == "characters":
        # Every neighbouring pair fits 2048, but the real three-restriction
        # component does not. Its individual source blocks remain unchanged.
        suffix = ("检测适用范围保持原有技术口径。" * 80)[:1008] + "。"
        qualifiers = [text + suffix for text in qualifiers[:2]]
        assert all(len(a) + len(b) < 2048 for a, b in zip([LEFT, *qualifiers], qualifiers))
        assert sum(map(len, [HEADING, LEFT, *qualifiers])) > 2048
        assert len([HEADING, LEFT, *qualifiers]) == 4  # isolate characters from the four-block bound
    parsed = _source([HEADING, LEFT, *qualifiers, FUTURE])
    selected = _select(parsed)
    unsafe = {LEFT, *qualifiers}
    assert not unsafe.intersection(span.raw_text for span in selected.evidence_spans), (
        "One source component cannot evade 8 units/4 blocks/2048 chars by passing only pairwise limits."
    )
    assert any(item["reason"] == "REFERENCE_ENVELOPE" for item in selected.reading_context["deferred"])



def _three_body_members_per_native_block(texts):
    """Same immutable paragraph IDs, with exact synthetic native block ranges.

    This makes the original unit bound independently testable: title plus
    nine body units occupy four blocks and fewer than 2048 characters. The
    public pipeline, rather than this fixture, chooses its actual carriers.
    """
    parsed = _source(texts)
    body_stop = len(texts) - 1
    groups = [[0], *[list(range(start, min(start + 3, body_stop)))
                      for start in range(1, body_stop, 3)], [body_stop]]
    blocks, y = [], 100
    for block, indices in enumerate(groups):
        height = 12 * len(indices)
        blocks.append((block, (90, y, 550, y + height), "\n".join(texts[i] for i in indices)))
        y += height + 8
    view = build_native_page_view(blocks)
    units = []
    for block, indices in enumerate(groups):
        start, full = 0, blocks[block][2]
        for i in indices:
            original = parsed.units[i]
            metadata = dict(original.metadata)
            metadata.update(pdf_block=block, block_sha256=sha256(full.encode()).hexdigest(),
                            block_char_start=start, block_char_end=start + len(original.raw_text),
                            native_source_view=view)
            layout = {**metadata["reading_layout"]["layout"], "bbox": list(blocks[block][1])}
            metadata["reading_layout"] = {**metadata["reading_layout"], "layout": layout}
            units.append(replace(original, metadata=metadata))
            start += len(original.raw_text) + 1
    return replace(parsed, units=tuple(units))


def test_multiple_original_qualifiers_inside_carriers_do_not_evade_eight_unit_bound():
    qualifiers = ("该设备尚未完成客户认证。", "该设备尚未开始量产。", "该设备尚未商业化。")
    texts = [HEADING, LEFT, *[qualifiers[i % 3] for i in range(8)], FUTURE]
    parsed = _three_body_members_per_native_block(texts)
    actual = parsed.units[:-1]
    assert len(actual) == 10 > 8
    assert len({unit.metadata["pdf_block"] for unit in actual}) == 4
    assert sum(len(unit.raw_text) for unit in actual) < 2048
    selected = _select(parsed)
    unsafe_ids = {unit.unit_id for unit in parsed.units[1:-1]}
    for span in selected.evidence_spans:
        native = span.structured_value.get("native_range", {})
        assert not unsafe_ids.intersection(native.get("source_unit_ids", ())), (
            "Material compression cannot turn a greater-than-eight-original restriction chain into cheap independent carriers."
        )
        assert span.raw_text not in {LEFT, *qualifiers}
    assert any(item["reason"] == "REFERENCE_ENVELOPE" for item in selected.reading_context["deferred"])
