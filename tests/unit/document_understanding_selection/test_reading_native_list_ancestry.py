"""Public native-list ancestry TDD; source observations, never injected sections.

A physical page neighbour is not an unfinished sentence. All fixtures carry
original native IDs/locators, per-page native views and font/frame observations;
structure, selection, citation closure and scoped model compilation run normally.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest

from company_wiki.document_understanding.narrative_continuity import SourcePageFlow, build_native_continuity
from company_wiki.resource_budget import new_document_work_budget
from company_wiki.source_catalog import narrative_reading as reading
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_evidence import _make_unit
from company_wiki.source_catalog.narrative_native_ranges import build_native_page_view
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256
from unit.document_understanding_selection.test_reading_guidance_condition_scope import _model, _spans_for

# Bounded in-memory observations are collected by the independent RED runner.
# The ordinary unit test never writes reports, changes source or calls a model.
_OBSERVATIONS: list[dict] = []


def _source(rows, *, known_column=True):
    digest = sha256("\n".join(row[1] for row in rows).encode()).hexdigest()
    source_id = source_id_for_sha256(digest)
    pages = sorted({row[0] for row in rows})
    page_views = {}
    for page in pages:
        page_rows = [row for row in rows if row[0] == page]
        blocks = {}
        for _page, text, block, box in page_rows:
            if block not in blocks:
                blocks[block] = (box, [])
            blocks[block][1].append(text)
        page_views[page] = build_native_page_view([
            (block, box, "\n".join(texts)) for block, (box, texts) in blocks.items()
        ])
    units, offsets, page_ordinals = [], {}, {}
    for page, text, block, box in rows:
        key = (page, block)
        start = offsets.get(key, 0)
        block_text = "\n".join(row[1] for row in rows if (row[0], row[2]) == key)
        layout = {"bbox": list(box), "page_width": 600, "page_height": 800,
                  "coordinate_frame": "dict", "rotation": 0}
        if known_column:
            layout["column"] = 0
        font = {"char_start": 0, "char_end": len(text), "font_size": 12,
                "font_weight": "regular", "coordinate_frame": "dict",
                "source": "pdf_native_single_textpage", "char_alignment": "exact"}
        metadata = {"pdf_block": block, "block_sha256": sha256(block_text.encode()).hexdigest(),
                    "block_char_start": start, "block_char_end": start + len(text),
                    "native_source_view": page_views[page],
                    "reading_layout": {"layout": layout, "upstream_hints": {"font_runs": [font]}}}
        paragraph = page_ordinals.get(page, 0)
        units.append(_make_unit(source_id=source_id, parser_version="0.1.1",
            coordinates=EvidenceCoordinates(page_number=page, paragraph_index=paragraph),
            raw_text=text, unit_kind="pdf_text_block", source_role="company_filing",
            language="zh", metadata=metadata))
        offsets[key] = start + len(text) + 1
        page_ordinals[page] = paragraph + 1
    return DocumentStructure(source_id, digest, "zh", tuple(units), page_count=len(pages),
                             pages_read=len(pages), mime_type="application/pdf")


def _list_source(mode):
    cross = mode.startswith("cross_page")
    roman = mode.endswith("roman")
    furniture = mode.endswith("furniture")
    parent = "(1) 检测服务实现收入12亿元。"
    intro = "报告期内："
    first = "- 新产品收入占比超过30%。"
    second = ("ii. " if roman else "- ") + "客户订单同比增长20%。"
    sibling = "(2) 技术服务实现收入9亿元。"
    sibling_body = "- 客户数量同比增长21%。"
    if cross:
        rows = [(1, "一、经营情况", 0, (90, 100, 550, 112)),
                (1, parent, 1, (90, 640, 550, 672)),
                (1, intro, 1, (90, 640, 550, 672)),
                (1, first, 2, (110, 720, 550, 732))]
        if furniture:
            rows.append((1, "Neutral Annual Report", 3, (90, 780, 550, 792)))
            rows.append((2, "Neutral Annual Report", 0, (90, 12, 550, 24)))
        first_block = 1 if furniture else 0
        rows.extend([(2, second, first_block, (110, 70, 550, 82)),
                     (2, sibling, first_block + 1, (90, 130, 550, 162)),
                     (2, intro, first_block + 1, (90, 130, 550, 162)),
                     (2, sibling_body, first_block + 2, (110, 190, 550, 202)),
                     (2, "公司整体计划仍受市场变化影响。", first_block + 3, (90, 240, 550, 252))])
    else:
        rows = [(1, "一、经营情况", 0, (90, 100, 550, 112)),
                (1, parent, 1, (90, 200, 550, 232)),
                (1, intro, 1, (90, 200, 550, 232)),
                (1, first, 2, (110, 260, 550, 272)),
                (1, second, 3, (110, 290, 550, 302)),
                (1, sibling, 4, (90, 340, 550, 372)),
                (1, intro, 4, (90, 340, 550, 372)),
                (1, sibling_body, 5, (110, 400, 550, 412)),
                (1, "公司整体计划仍受市场变化影响。", 6, (90, 450, 550, 462))]
    parsed = _source(rows)
    def at(text):
        return next(unit for unit in parsed.units if unit.raw_text == text)
    return parsed, {"parent": at(parent), "intro": parsed.units[2], "first": at(first),
                    "second": at(second), "sibling": at(sibling), "sibling_body": at(sibling_body)}


def _run_public(parsed):
    original = [(u.unit_id, u.source_id, u.raw_text, u.coordinates, repr(u.metadata), u.quality_flags)
                for u in parsed.units]
    budget = new_document_work_budget()
    assert budget.max_work_units == 16_000_000
    pipeline = reading._understand(parsed, title="中性年度报告", kind="annual_report",
                                  mime_type="application/pdf", work_budget=budget)
    used_by_structure = budget.used
    selected = reading.select_reading_evidence(parsed, title="中性年度报告",
        existing_kind="annual_report", max_selected=96, max_chars=48000, work_budget=budget)
    assert 0 < used_by_structure < budget.used <= budget.max_work_units and not budget.exhausted
    assert [(u.unit_id, u.source_id, u.raw_text, u.coordinates, repr(u.metadata), u.quality_flags)
            for u in parsed.units] == original
    assert parsed.coverage_complete and len(selected.evidence_spans) <= 96
    assert sum(len(span.raw_text or "") for span in selected.evidence_spans) <= 48000
    assert reading.MAX_READING_CHARS == 48000
    _assert_original_envelopes(parsed, selected)
    return pipeline, selected, budget.used


def _assert_original_envelopes(parsed, selected):
    by_span = {span.span_id: {unit.unit_id for unit in parsed.units
                             if span in _spans_for(selected, unit)}
               for span in selected.evidence_spans}
    originals = {unit.unit_id: unit for unit in parsed.units}
    for group in selected.reading_context["groups"]:
        for citation in group["citation_views"]:
            evidence = set(citation["support_evidence_ids"]) | set(citation["context_evidence_ids"])
            assert all(by_span[span] for span in evidence)
            ids = {uid for span in evidence for uid in by_span[span]}
            assert len(ids) <= 8
            assert len({(originals[uid].source_id, originals[uid].coordinates.page_number,
                         originals[uid].metadata["pdf_block"]) for uid in ids}) <= 4
            assert sum(len(originals[uid].raw_text) for uid in ids) <= 2048


def _own_context(parsed, pipeline, selected, target, own, sibling):
    sections = {unit: section for section in pipeline["structure"]["sections"]
                for unit in section.get("body_unit_ids", ())}
    heads = set(sections[target.unit_id]["heading_unit_ids"])
    supports = {span.span_id for span in _spans_for(selected, target)}
    context_sets = [{span.span_id for span in _spans_for(selected, unit)} for unit in own]
    sibling_ids = {span.span_id for span in _spans_for(selected, sibling)}
    citations = [citation for group in selected.reading_context["groups"]
                 for citation in group["citation_views"] if supports.intersection(citation["support_evidence_ids"])]
    view, texts = _model(selected)
    tasks = [task for task in view.plan.tasks if supports.intersection(task.support_ids)]
    observation = {"target": target.unit_id, "target_locator": target.coordinates.to_dict(),
        "own_heading_ids": sorted(heads), "expected_own": [u.unit_id for u in own],
        "support_ids": sorted(supports), "citations": citations,
        "tasks": [{"support_ids": list(t.support_ids), "member_ids": list(t.member_ids),
                   "texts": texts[t.key]} for t in tasks]}
    failures = []
    if not supports:
        failures.append("original useful child is missing as selected evidence")
    if not {u.unit_id for u in own} <= heads or sibling.unit_id in heads:
        failures.append("actual structure lost own parent/intro or borrowed sibling")
    if not citations or any(not ids.intersection(c["context_evidence_ids"]) for c in citations for ids in context_sets):
        failures.append("parent/intro missing from own target citation context")
    if any(sibling_ids.intersection([*c["support_evidence_ids"], *c["context_evidence_ids"]]) for c in citations):
        failures.append("sibling contaminates target citation")
    if not tasks or any(not ids.intersection(t.member_ids) for t in tasks for ids in context_sets):
        failures.append("parent/intro missing from actual model task")
    if any(sibling_ids.intersection(t.member_ids) for t in tasks):
        failures.append("sibling contaminates target model task")
    if tasks and any(not any(target.raw_text in text for text in texts[t.key]) for t in tasks):
        failures.append("model lost exact original child text")
    for unit in own:
        if tasks and any(not any(unit.raw_text in text for text in texts[t.key]) for t in tasks):
            failures.append("model lost exact own parent/intro text")
    observation["failures"] = failures
    return observation


@pytest.mark.parametrize("mode", ("same_page", "cross_page", "cross_page_furniture",
                                  "cross_page_roman", "same_page_roman"))
def test_native_list_child_keeps_own_source_ancestry_through_public_selection_and_model(mode):
    assert Path(reading.__file__).resolve().is_relative_to(Path(__file__).resolve().parents[3] / "src")
    parsed, units = _list_source(mode)
    pipeline, selected, used = _run_public(parsed)
    first = _own_context(parsed, pipeline, selected, units["first"],
                         (units["parent"], units["intro"]), units["sibling"])
    second = _own_context(parsed, pipeline, selected, units["second"],
                          (units["parent"], units["intro"]), units["sibling"])
    sibling_intro = parsed.units[parsed.units.index(units["sibling"]) + 1]
    sibling = _own_context(parsed, pipeline, selected, units["sibling_body"],
                          (units["sibling"], sibling_intro), units["parent"])
    furniture_ids = [uid for diagnostic in pipeline["structure"].get("diagnostics", ())
                     if diagnostic["code"] == "REPEATED_RUNNING_HEADER" for uid in diagnostic.get("unit_ids", ())]
    if mode.endswith("furniture"):
        assert len(furniture_ids) == 2, "Furniture must be positively detected by public structure."
        assert not any(span.raw_text == "Neutral Annual Report" for span in selected.evidence_spans)
    observation = {"case": mode, "work_used": used, "furniture_ids": furniture_ids,
                   "structure": pipeline["structure"]["sections"], "children": [first, second, sibling]}
    _OBSERVATIONS.append(observation)
    assert not any(child["failures"] for child in observation["children"]), observation


def _flow_source(mode):
    terminal = mode == "terminal"
    left = "公司已交付27台设备至客户完成生产验证。" if terminal else "公司已交付27台设备至客户开展生产验"
    right = "证，尚未完成量产认证。"
    rows = [(1, "一、经营情况", 0, (90, 100, 550, 112)),
            (1, left, 1, (90, 720, 550, 732))]
    if mode == "unfinished_furniture":
        rows += [(1, "Neutral Annual Report", 2, (90, 780, 550, 792)),
                 (2, "Neutral Annual Report", 0, (90, 12, 550, 24))]
    rows.append((2, right, 1 if mode == "unfinished_furniture" else 0, (90, 70, 550, 82)))
    parsed = _source(rows, known_column=mode != "unknown_column")
    return parsed, parsed.units[1], parsed.units[-1]


@pytest.mark.parametrize("mode", ("unfinished", "unfinished_furniture", "terminal", "unknown_column"))
def test_existing_sentence_page_flow_is_not_replaced_by_list_continuation(mode):
    parsed, left, right = _flow_source(mode)
    pipeline, selected, used = _run_public(parsed)
    observation = pipeline["observation"]["units"]
    furniture = frozenset(uid for d in pipeline["structure"].get("diagnostics", ())
                          if d["code"] == "REPEATED_RUNNING_HEADER" for uid in d.get("unit_ids", ()))
    provenance = {unit.unit_id: {"source_id": unit.source_id,
        "paragraph_index": unit.coordinates.paragraph_index,
        **{key: unit.metadata[key] for key in ("pdf_block", "block_sha256", "block_char_start", "block_char_end")}}
        for unit in parsed.units}
    budget = new_document_work_budget()
    flow = build_native_continuity(observation, provenance=provenance,
        sections=pipeline["structure"]["sections"], unit_profiles=pipeline["reading_plan"]["unit_profiles"],
        work_budget=budget, source_page_flow=SourcePageFlow(furniture, reading.independent_statement_start,
                                                     coarse_complete=parsed.coverage_complete))
    pair_windows = [window for window in flow["windows"]
                    if {left.unit_id, right.unit_id} <= set(window["member_unit_ids"])]
    expected = mode in {"unfinished", "unfinished_furniture"}
    view, texts = _model(selected)
    support = {span.span_id for unit in (left, right) for span in _spans_for(selected, unit)}
    tasks = [task for task in view.plan.tasks if support.intersection(task.support_ids)]
    rows = {unit["unit_id"]: unit for unit in observation}
    result = {"case": mode, "expected_sentence_window": expected, "flow": flow,
              "left_page_paragraph": left.coordinates.paragraph_index,
              "right_page_paragraph": right.coordinates.paragraph_index,
              "left_global_ordinal": rows[left.unit_id]["ordinal"],
              "right_global_ordinal": rows[right.unit_id]["ordinal"],
              "work_used": used, "tasks": [{"members": list(t.member_ids), "texts": texts[t.key]} for t in tasks]}
    _OBSERVATIONS.append(result)
    assert rows[right.unit_id]["ordinal"] > rows[left.unit_id]["ordinal"]
    assert right.coordinates.paragraph_index <= left.coordinates.paragraph_index
    assert bool(pair_windows) is expected, result
    assert flow["complete"] is (mode != "unknown_column"), result
    if mode == "unknown_column":
        assert any(d["code"] == "CONTINUITY_PAGE_COLUMN_UNPROVEN" for d in flow["diagnostics"])
    if mode == "unfinished_furniture":
        assert len(furniture) == 2
        assert set(pair_windows[0]["proof"][0]["furniture_unit_ids"]) == furniture
    if expected:
        left_spans, right_spans = _spans_for(selected, left), _spans_for(selected, right)
        left_ids, right_ids = {s.span_id for s in left_spans}, {s.span_id for s in right_spans}
        assert left_ids and right_ids and tasks
        assert all(left_ids.intersection(t.member_ids) and right_ids.intersection(t.member_ids) for t in tasks)
        assert all(any(left.raw_text in text for text in texts[t.key]) and
                   any(right.raw_text in text for text in texts[t.key]) for t in tasks)
    assert 0 < budget.used <= budget.max_work_units and not budget.exhausted
