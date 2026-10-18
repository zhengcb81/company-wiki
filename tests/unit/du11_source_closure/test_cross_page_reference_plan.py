"""Original-page support is atomic; a page break cannot certify a new fact."""
from copy import deepcopy
from dataclasses import replace

import pytest

from company_wiki.source_catalog import narrative_reading as reading
from unit.document_understanding_selection.test_reading_native_continuity import native, source_case


def page_case(texts=None, *, kind="background"):
    texts = texts or ["公司向客户交付样机开展生产验", "证，尚未获准量产。"]
    rows = [native(texts[0], 0, page=7, box=[90, 720, 550, 732], column=0),
            native(texts[1], 1, page=8, box=[90, 80, 550, 92], column=0)]
    parsed, pipeline = source_case([], native_rows=rows)
    parsed = replace(parsed, page_count=8, pages_read=8)
    pipeline["packages"]["packages"][0]["kind"] = kind
    return parsed, pipeline


@pytest.mark.parametrize("kind", ["background", "paragraph_event", "risk"])
@pytest.mark.parametrize("texts", [None, ["Our platform received repeat",
    "orders from customers, but commercial rollout is not yet approved."]])
def test_proven_adjacent_page_parts_share_original_support_without_a_fake_page_view(kind, texts):
    parsed, pipeline = page_case(texts, kind=kind)
    before = deepcopy(pipeline)
    packages, _, audit, blocked = reading._prose_reading_packages(parsed, pipeline)
    ids = [u.unit_id for u in parsed.units]
    complete = [p for p in packages if p["member_unit_ids"] == ids]
    assert len(complete) == 1
    assert complete[0]["anchor_unit_ids"] == ids
    assert not blocked
    proofs = [p for w in audit["windows"] for p in w["proof"]]
    assert any(p.get("left_page") == 7 and p.get("right_page") == 8 for p in proofs)
    # Each quote still reopens on its actual original page and coordinates.
    assert [u.coordinates.page_number for u in parsed.units] == [7, 8]
    assert all(not u.metadata.get("native_range") for u in parsed.units)
    assert pipeline == before


@pytest.mark.parametrize("boundary", ["column_unknown", "column_changed", "page_gap", "section", "font", "heading", "table"])
def test_page_carry_requires_actual_column_scope_and_original_reading_flow(boundary):
    parsed, pipeline = page_case()
    left, right = pipeline["observation"]["units"]
    if boundary == "column_unknown":
        left["layout"].pop("column")
        right["layout"].pop("column")
    elif boundary == "column_changed":
        right["layout"]["column"] = 1
    elif boundary == "page_gap":
        right["page"] = 9
    elif boundary == "section":
        right["hints"]["section_key"] = "different-section"
    elif boundary == "font":
        right["hints"]["font_runs"][0]["font_size"] = 14
    else:
        right["kind"] = boundary
    packages, _, _, _ = reading._prose_reading_packages(parsed, pipeline)
    assert not any(len(p["member_unit_ids"]) > 1 for p in packages)


def test_cross_page_original_blocks_cannot_hide_over_limit_by_restarting_numbers():
    texts = ["公司计划", "向多个客户", "交付新型生", "产验证用", "样机。"]
    rows = [native(text, i, page=7 if i < 3 else 8,
                   block=i if i < 3 else i - 3, column=0,
                   box=[90, 660 + 20 * i, 550, 672 + 20 * i] if i < 3
                   else [90, 80 + 20 * (i - 3), 550, 92 + 20 * (i - 3)])
            for i, text in enumerate(texts)]
    parsed, pipeline = source_case([], native_rows=rows)
    parsed = replace(parsed, page_count=8, pages_read=8)
    packages, _, _, blocked = reading._prose_reading_packages(parsed, pipeline)
    assert {u.unit_id for u in parsed.units} <= blocked
    assert not any(p["member_unit_ids"] for p in packages)


def test_source_span_budget_cannot_export_only_one_half_of_a_page_carry():
    from company_wiki.source_catalog.narrative_finalize import finalize_selection
    from company_wiki.source_catalog.narrative_routing import DocumentRoute

    parsed, pipeline = page_case()
    candidates, metadata, _, _, _ = reading._candidates(parsed, pipeline)
    result = finalize_selection(parsed, DocumentRoute("semi_annual", 1, False), candidates,
        group_ids={}, heading_pattern=reading._NEVER_HEADING, dropped_financial_count=0,
        budget_policy=reading.READING_BUDGET_POLICY, reading_metadata=metadata, max_chars=48000)
    assert not result.evidence_spans


@pytest.mark.parametrize("proven_furniture", [True, False])
def test_only_actual_running_furniture_can_be_skipped_at_the_page_boundary(proven_furniture):
    rows = [native("公司向客户交付样机开展生产验", 0, page=7,
                   box=[90, 720, 550, 732], column=0),
            native("8", 1, page=7, kind="footer", box=[290, 770, 310, 782]),
            native("公司半年报", 2, page=8, kind="header", box=[90, 10, 180, 22]),
            native("证，尚未获准量产。", 3, page=8,
                   box=[90, 80, 550, 92], column=0)]
    parsed, pipeline = source_case([], native_rows=rows)
    parsed = replace(parsed, page_count=8, pages_read=8)
    furniture = [u.unit_id for u in parsed.units[1:3]]
    pipeline["non_selectable_unit_ids"] = furniture
    pipeline["structure"]["coverage"] = {"excluded_furniture_unit_ids": furniture}
    pipeline["structure"]["diagnostics"] = ([{"code": "REPEATED_RUNNING_HEADER", "unit_ids": furniture}]
                                              if proven_furniture else [])
    packages, _, audit, blocked = reading._prose_reading_packages(parsed, pipeline)
    ids = [parsed.units[0].unit_id, parsed.units[-1].unit_id]
    joined = [p for p in packages if p["member_unit_ids"] == ids]
    assert bool(joined) is proven_furniture
    if proven_furniture:
        proofs = [p for w in audit["windows"] for p in w["proof"]]
        assert any(p.get("furniture_unit_ids") == furniture for p in proofs)
        assert all(not set(p["member_unit_ids"]) & set(furniture) for p in joined)
    else:
        assert set(ids) <= blocked
        assert not any(set(p["member_unit_ids"]) & set(ids) for p in packages)


@pytest.mark.parametrize("right", ["公司另一个项目已开始量产。", "本集團另一項目已開始量產。",
    "Our new platform has begun production."])
def test_new_independent_statement_on_next_page_is_not_forced_under_previous_subject(right):
    parsed, pipeline = page_case(["公司的第一种设备尚在开展生产验", right])
    packages, _, _, blocked = reading._prose_reading_packages(parsed, pipeline)
    assert not any(len(p["member_unit_ids"]) > 1 for p in packages)
    assert parsed.units[1].unit_id not in blocked
    assert any(p["member_unit_ids"] == [parsed.units[1].unit_id] for p in packages)


def test_possessive_continuation_without_its_own_predicate_is_not_a_new_subject():
    parsed, pipeline = page_case(["The company plans to deliver the devices to", "our customers next year."])
    packages, _, _, blocked = reading._prose_reading_packages(parsed, pipeline)
    assert not blocked
    assert any(p["member_unit_ids"] == [u.unit_id for u in parsed.units] for p in packages)


def test_direct_native_api_remains_same_page_without_observed_source_flow():
    from company_wiki.document_understanding.narrative_continuity import build_native_continuity

    rows = [native("公司向客户交付样机开展生产验", 0, page=7, box=[90, 720, 550, 732], column=0),
            native("证，尚未量产。", 1, page=8, box=[90, 80, 550, 92], column=0)]
    result = build_native_continuity([r[0] for r in rows],
        provenance={r[0]["unit_id"]: r[1] for r in rows},
        unit_profiles={r[0]["unit_id"]: r[2] for r in rows})
    assert not result["windows"]


@pytest.mark.parametrize("change", ["unread", "opaque", "error", "bool_column", "blank_column"])
def test_source_flow_requires_complete_observation_and_real_column_id(change):
    parsed, pipeline = page_case()
    if change == "unread":
        parsed = replace(parsed, pages_read=7)
    elif change == "opaque":
        parsed = replace(parsed, opaque_pages=(7,))
    elif change == "error":
        parsed = replace(parsed, errors=("layout_incomplete",))
    else:
        for unit in pipeline["observation"]["units"]:
            unit["layout"]["column"] = False if change == "bool_column" else " "
    packages, _, _, blocked = reading._prose_reading_packages(parsed, pipeline)
    assert not any(len(p["member_unit_ids"]) > 1 for p in packages)
    assert {u.unit_id for u in parsed.units} <= blocked


@pytest.mark.parametrize("deferred,joined", [((7,), False), ((8,), False), ((9,), True)])
def test_fine_geometry_unread_pages_apply_to_the_actual_pair_not_the_entire_source(deferred, joined):
    parsed, pipeline = page_case()
    parsed = replace(parsed, page_count=9, pages_read=9, deferred_table_pages=deferred)
    packages, _, _, blocked = reading._prose_reading_packages(parsed, pipeline)
    assert any(len(p["member_unit_ids"]) > 1 for p in packages) is joined
    assert bool(blocked) is not joined




