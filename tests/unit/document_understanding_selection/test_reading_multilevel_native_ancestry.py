"""Numbered business, bullet service and roman fact retain their actual tree."""
from __future__ import annotations

import pytest

from company_wiki.document_understanding.narrative_continuity import NativeSourceContext
from unit.document_understanding_selection.test_reading_guidance_condition_scope import _model, _spans_for
from unit.document_understanding_selection.test_reading_native_list_ancestry import _run_public, _source


def _tree(mode):
    cross = mode != "same_page"
    page = 3 if mode == "page_gap" else 2 if cross else 1
    rows = [(1, "一、经营情况", 0, (90, 100, 550, 112)),
            (1, "(1) 仪器业务实现收入12亿元。", 1, (90, 640, 550, 672)),
            (1, "报告期内：", 1, (90, 640, 550, 672)),
            (1, "- 维护服务保持增长。", 2, (110, 690, 550, 702)),
            (1, "i. 服务客户数量增长15%。", 3, (125, 720, 550, 732))]
    if mode in {"page_counter", "bad_counter"}:
        rows.append((1, "1 / 2" if mode == "page_counter" else "7 / 2", 4, (280, 780, 330, 792)))
    if mode == "body_interruption":
        rows.append((1, "未经证明的其他事项。", 4, (90, 750, 550, 762)))
    y = 740 if not cross else 70
    rows.extend([(page, "- 制造服务保持增长。", 5, (110, y, 550, y + 12)),
                 (page, "i. 服务收入达到8亿元，同比增长18%。", 6, (125, y + 20, 550, y + 32)),
                 (page, "- 软件服务保持增长。", 7, (110, y + 40, 550, y + 52)),
                 (page, "i. 客户订单增长20%。", 8, (125, y + 60, 550, y + 72)),
                 (page, "(2) 消费业务实现收入9亿元。", 9, (90, y + 80, 550, y + 112)),
                 (page, "报告期内：", 9, (90, y + 80, 550, y + 112)),
                 (page, "- 订阅用户数量增长12%。", 10, (110, y + 130, 550, y + 142))])
    if mode in {"page_counter", "bad_counter"}:
        rows.append((page, "2 / 2", 11, (280, 780, 330, 792)))
    # Keep same-page controls inside a real page rather than outside its frame.
    if not cross:
        rows = [(p, text, b, (box[0], box[1] - 450 if i else box[1], box[2],
                 box[3] - 450 if i else box[3])) for i, (p, text, b, box) in enumerate(rows)]
    parsed = _source(rows, known_column=mode != "unknown_column")
    by_text = {u.raw_text: u for u in parsed.units}
    return parsed, by_text


def _ancestors(pipeline, target):
    sections = {s["section_id"]: s for s in pipeline["structure"]["sections"]}
    section = next(s for s in sections.values() if target.unit_id in
                   [*s["heading_unit_ids"], *s["body_unit_ids"]])
    ids = set()
    visited = set()
    while section is not None:
        assert section["section_id"] not in visited
        visited.add(section["section_id"])
        ids.update(section["heading_unit_ids"])
        section = sections.get(section.get("parent_id"))
    return ids


@pytest.mark.parametrize("mode", ["same_page", "cross_page", "page_counter"])
def test_multilevel_original_parent_chain_survives_citation_and_model_compilation(mode):
    parsed, units = _tree(mode)
    pipeline, selected, _work = _run_public(parsed)
    root = units["(1) 仪器业务实现收入12亿元。"]
    intro = parsed.units[2]
    sibling = units["(2) 消费业务实现收入9亿元。"]
    view, texts = _model(selected)
    for target_text, parent_text in [("i. 服务客户数量增长15%。", "- 维护服务保持增长。"),
        ("i. 服务收入达到8亿元，同比增长18%。", "- 制造服务保持增长。"),
        ("i. 客户订单增长20%。", "- 软件服务保持增长。")]:
        target, parent = units[target_text], units[parent_text]
        own = [root, intro, parent]
        ancestors = _ancestors(pipeline, target)
        assert {u.unit_id for u in own} <= ancestors
        assert sibling.unit_id not in ancestors
        support = {s.span_id for s in _spans_for(selected, target)}
        assert support
        contexts = [{s.span_id for s in _spans_for(selected, u)} for u in own]
        foreign = {s.span_id for u in (sibling, *[v for k, v in units.items()
                    if k.startswith("- ") and v != parent]) for s in _spans_for(selected, u)}
        citations = [c for g in selected.reading_context["groups"] for c in g["citation_views"]
                     if support.intersection(c["support_evidence_ids"])]
        tasks = [t for t in view.plan.tasks if support.intersection(t.support_ids)]
        assert citations and tasks
        assert all(ids.intersection(c["context_evidence_ids"]) for c in citations for ids in contexts)
        assert all(ids.intersection(t.member_ids) for t in tasks for ids in contexts)
        assert all(not foreign.intersection(c["context_evidence_ids"]) for c in citations)
        assert all(not foreign.intersection(t.member_ids) for t in tasks)
        assert all(any(u.raw_text in text for text in texts[t.key]) for t in tasks for u in [*own, target])


@pytest.mark.parametrize("mode", ["page_gap", "unknown_column", "body_interruption", "bad_counter"])
def test_multilevel_tree_does_not_carry_outer_business_through_unproven_boundary(mode):
    parsed, units = _tree(mode)
    pipeline, selected, _work = _run_public(parsed)
    target = units["i. 服务收入达到8亿元，同比增长18%。"]
    root = units["(1) 仪器业务实现收入12亿元。"]
    assert root.unit_id not in _ancestors(pipeline, target)
    support = {s.span_id for s in _spans_for(selected, target)}
    root_spans = {s.span_id for s in _spans_for(selected, root)}
    citations = [c for g in selected.reading_context["groups"] for c in g["citation_views"]
                 if support.intersection(c["support_evidence_ids"])]
    assert all(not root_spans.intersection(c["context_evidence_ids"]) for c in citations)


def test_nested_lists_share_one_physical_observation_for_the_same_page_edge(monkeypatch):
    rows = [(1, "一、经营情况", 0, (90, 100, 550, 112)),
            (1, "(1) 仪器业务实现收入12亿元。", 1, (90, 640, 550, 672)),
            (1, "报告期内：", 1, (90, 640, 550, 672)),
            (1, "- 维护服务保持增长。", 2, (110, 690, 550, 702)),
            (1, "i. 服务客户数量增长15%。", 3, (125, 720, 550, 732)),
            (2, "ii. 客户复购率超过85%。", 0, (125, 70, 550, 82)),
            (2, "(2) 消费业务实现收入9亿元。", 1, (90, 130, 550, 162))]
    parsed = _source(rows)
    observations = {}
    actual = NativeSourceContext.page_neighbour

    def observe(self, left, right, **kwargs):
        key = (id(self), left, right)
        observations[key] = observations.get(key, 0) + 1
        return actual(self, left, right, **kwargs)

    monkeypatch.setattr(NativeSourceContext, "page_neighbour", observe)
    pipeline, selected, _work = _run_public(parsed)
    target = parsed.units[5]
    assert {u.unit_id for u in parsed.units[1:4]} <= _ancestors(pipeline, target)
    support = {s.span_id for s in _spans_for(selected, target)}
    view, _texts = _model(selected)
    assert support and any(support.intersection(t.support_ids) for t in view.plan.tasks)
    assert observations
    assert max(observations.values()) == 1
