"""Meaning-preserving relation planning must not expand impossible pairs."""
from __future__ import annotations

from company_wiki.document_understanding.layout_hints.contract import WorkBudget
from company_wiki.document_understanding.structure.contract import ObservationUnit
from company_wiki.document_understanding.structure.layout import Ordering
from company_wiki.document_understanding.structure.relations import (
    RelationBuilder,
    language_lane_relations,
)


def unit(index, *, page=1, lane=0, language="zh", source="original-a", y=10, dom=None):
    hints = {"source_id": source}
    if dom is not None:
        hints["dom_path"] = dom
    layout = {}
    if lane is not None:
        layout = {"column": lane, "bbox": [lane * 200, y, lane * 200 + 120, y + 8]}
    return ObservationUnit({"unit_id": f"u{index}", "ordinal": index, "page": page,
        "text": "Company operating narrative", "kind": "paragraph", "language": language,
        "layout": layout, "hints": hints}, index)


def observe(units, cap=16_000_000):
    budget = WorkBudget(cap)
    builder = RelationBuilder({u.unit_id for u in units}, max_relations=100_000,
                              work_budget=budget)
    ordering = Ordering(tuple(units), frozenset(), frozenset(), frozenset(), ())
    language_lane_relations(builder, units, ordering)
    return builder.relations(), budget.used


def test_one_lane_per_page_does_not_rescan_all_other_pages():
    small, small_work = observe([unit(i, page=i + 1) for i in range(64)])
    large, large_work = observe([unit(i, page=i + 1) for i in range(128)])
    assert small == large == ()
    assert large_work < 3 * small_work


def test_same_language_dom_siblings_do_not_reserve_a_cartesian_expansion():
    relations, work = observe([unit(i, page=None, lane=None, dom=f"0.1.{i}")
                               for i in range(400)], cap=5_000)
    assert relations == ()
    assert 400 <= work < 5_000


def test_same_language_unequal_lanes_do_not_reserve_impossible_pairs():
    units = [unit(i, lane=0) for i in range(80)]
    units += [unit(i + 80, lane=1) for i in range(81)]
    relations, work = observe(units, cap=4_000)
    assert relations == ()
    assert 161 <= work < 4_000


def test_foreign_originals_are_not_counterparts_even_on_the_same_page():
    relations, _ = observe([unit(0, language="en", source="one"),
                            unit(1, lane=1, language="zh", source="another")])
    assert relations == ()


def test_geometric_counterparts_require_the_same_block_kind():
    left = unit(0, lane=None, language="en")
    right = unit(1, lane=None, language="zh")
    left.bbox = (0, 10, 120, 18)
    right.bbox = (200, 10, 320, 18)
    left.kind = "heading"
    right.text = "公司业务发展情况"
    relations, _ = observe([left, right])
    assert relations == ()


def test_bilingual_equal_lanes_keep_positional_matches():
    relations, _ = observe([unit(0, language="en", y=10), unit(1, language="en", y=40),
                            unit(2, lane=1, language="zh-hant", y=10),
                            unit(3, lane=1, language="zh-hans", y=40)])
    assert [(r["from_unit_ids"], r["to_unit_ids"]) for r in relations] == [
        (["u0"], ["u2"]), (["u1"], ["u3"])]


def test_bilingual_unequal_lanes_keep_nearest_and_original_tie_order():
    units = [unit(0, language="en", y=20), unit(1, language="en", y=70),
             unit(2, lane=1, language="zh", y=10), unit(3, lane=1, language="zh", y=30),
             unit(4, lane=1, language="zh", y=70)]
    relations, _ = observe(units)
    assert [(r["from_unit_ids"], r["to_unit_ids"]) for r in relations] == [
        (["u0"], ["u2"]), (["u1"], ["u4"])]


def test_unknown_languages_and_same_language_family_do_not_become_parallel():
    assert observe([unit(0, language=None), unit(1, lane=1, language="en")])[0] == ()
    assert observe([unit(0, language="zh-hant"), unit(1, lane=1, language="zh-hans")])[0] == ()


def test_monoscript_geometric_rows_do_not_expand_a_same_height_cartesian_set():
    units = [unit(i, lane=None) for i in range(400)]
    for u in units:
        u.bbox = (0, 10, 120, 18)
    relations, work = observe(units, cap=5_000)
    assert relations == ()
    assert 400 <= work < 5_000


def test_native_writing_system_counterparts_work_even_with_same_language_label():
    left, right = unit(0, lane=None), unit(1, lane=None)
    left.text, right.text = "Operating developments", "經營情況與業務發展"
    left.bbox, right.bbox = (0, 10, 120, 18), (200, 10, 320, 18)
    relations, _ = observe([left, right])
    assert [(r["from_unit_ids"], r["to_unit_ids"]) for r in relations] == [(["u0"], ["u1"])]


def test_dom_and_geometric_pairing_also_respect_original_boundaries():
    left = unit(0, lane=None, language="en", source="one", dom="0.1.0")
    right = unit(1, lane=None, language="zh", source="other", dom="0.1.1")
    assert observe([left, right])[0] == ()
    left.dom_path = right.dom_path = None
    left.text, right.text = "Operating developments", "經營情況與業務發展"
    left.bbox, right.bbox = (0, 10, 120, 18), (200, 10, 320, 18)
    assert observe([left, right])[0] == ()
