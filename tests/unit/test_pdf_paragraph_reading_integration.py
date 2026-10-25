"""The PDF owner carries exact original members to real summary tasks and replay."""
from hashlib import sha256
import json

import pymupdf as fitz
import pytest

from company_wiki.document_understanding.summary_tasks import build_summary_task_plan
from company_wiki.resource_budget import WorkBudget
from company_wiki.source_catalog import narrative_evidence as native
from company_wiki.source_catalog.narrative_pdf_enhancement import ParagraphEnhancement
from company_wiki.source_catalog.narrative_pdf_reading import NativePdfBackend, PdfReading, PdfReadingRequest
from company_wiki.source_contract import source_id_for_sha256
from unit.test_pdf_paragraph_runtime import config
from unit.document_understanding_selection.test_reading_native_continuity import native as wire_unit, run as continuity


@pytest.mark.parametrize("barrier", [None, "scope", "column", "heading", "role", "font", "missing_font", "page"])
def test_membership_does_not_override_source_or_semantic_counterevidence(barrier):
    rows = [wire_unit("公司的新设备已完成客户生产验证并获得", 0, box=[90, 100, 550, 112]),
            wire_unit("重复订单，但尚未达到量产要求。", 1, box=[130, 120, 500, 132])]
    for index, (unit, _, _) in enumerate(rows):
        unit["hints"]["paragraph_membership"] = {"version": "pdf-paragraph-membership/1", "group": "a"*64,
            "count": 2, "position": index, "previous": rows[0][0]["unit_id"] if index else None,
            "next": rows[1][0]["unit_id"] if not index else None}
    right = rows[1][0]
    if barrier == "scope":
        right["hints"]["section_key"] = "other-project"
    elif barrier == "column":
        right["layout"]["column"] = "other-lane"
    elif barrier == "heading":
        right["kind"] = "heading"
    elif barrier == "role":
        right["role"] = "management"
    elif barrier == "font":
        right["hints"]["font_runs"][0]["font_size"] = 14
    elif barrier == "missing_font":
        right["hints"]["font_runs"] = []
    elif barrier == "page":
        right["page"] += 1
    result = continuity(rows)
    assert bool(result["windows"]) == (barrier is None)
    if barrier is None:
        assert result["windows"][0]["proof"][0]["basis"] == "source_exact_paragraph_membership"


def test_one_read_select_then_original_member_task_and_native_only_replay():
    with fitz.open() as document:
        page = document.new_page(width=600, height=800)
        page.insert_text((60, 100), "报告期内，公司自主研发的新型光刻设备已在多家客户的实际生产线完成工艺验证，并获得", fontsize=9, fontname="china-s")
        page.insert_text((83, 114), "新的生产订单，但尚未实现大规模量产。", fontsize=9, fontname="china-s")
        raw = document.tobytes()
    digest = sha256(raw).hexdigest()
    sid = source_id_for_sha256(digest)
    request = PdfReadingRequest(sid, digest, "zh", "年度报告", "annual_report")
    calls, originals = [], []
    def parser(data, **kwargs):
        calls.append("parse")
        parsed = native.parse_pdf_bytes(data, **kwargs)
        originals.extend(parsed.units)
        return parsed
    def runner(command, **kwargs):
        calls.append("enhance")
        body = json.loads(kwargs["input_bytes"])
        boxes = [u.metadata["reading_layout"]["layout"]["bbox"] for u in originals]
        box = {"l": min(b[0] for b in boxes), "r": max(b[2] for b in boxes),
               "t": 800 - min(b[1] for b in boxes), "b": 800 - max(b[3] for b in boxes), "coord_origin": "BOTTOMLEFT"}
        return {"stdout": json.dumps({"schema_version": "pdf-paragraph-response/1", "source_sha256": digest,
            "pages": body["pages"], "docling_version": "2.96.0", "model_sha256": "b"*64,
            "model_config_sha256": "c"*64, "runtime_versions": body["runtime_versions"], "converter_instances": 1,
            "environment_sha256": "d"*64,
            "items": [{"label": "text", "text": " ".join(u.raw_text for u in originals),
                       "provenance": [{"page_no": 1, "bbox": box}]}]}).encode()}
    reading = PdfReading(NativePdfBackend(parser=parser, paragraph_enhancement=ParagraphEnhancement(config(), runner=runner)))
    recipe = reading.describe_recipe()
    def selector(parsed, **kwargs):
        calls.append("select")
        return native.select_narrative_evidence(parsed, selector_version="0.9.0", **kwargs)
    selector.selector_version = "0.9.0"
    budget = WorkBudget(1_000_000)
    parsed, selected = reading.select(raw, request, selector=selector, work_budget=budget, checkpoint=lambda: None)
    assert calls == ["parse", "enhance", "select"]
    assert parsed.layout_diagnostics[-1]["accepted_groups"] == 1
    execution = selected.reading_context["layout_coverage"]["native_frontend"]["reading_execution"]
    assert execution["status"] == "enhanced" and execution["actual_engine"] == "docling"
    from company_wiki.automation.narrative_contracts import _reading_context, _to_plain
    restored = _reading_context(json.loads(json.dumps(selected.reading_context)), selected.evidence_spans)
    assert _to_plain(restored["layout_coverage"]["native_frontend"]["reading_execution"]) == execution
    assert reading.describe_recipe() == recipe
    reading.verify_material(parsed, selected.evidence_spans)
    plan = build_summary_task_plan(selected.evidence_spans, reading_context=selected.reading_context, max_claims=64)
    spans = {s.span_id: s for s in selected.evidence_spans}
    candidates = [t for t in plan.tasks if len(t.member_ids) == len(originals)]
    assert candidates, ([u.raw_text for u in originals], [t.to_binding() for t in plan.tasks], selected.reading_context)
    task = candidates[0]
    assert [spans[s].raw_text for s in task.member_ids] == [u.raw_text for u in originals]
    assert [spans[s].coordinates for s in task.member_ids] == [u.coordinates for u in originals]
    assert all("native_range" not in spans[s].structured_value for s in task.member_ids)
    verified, failed = reading.replay(raw, source_id=sid, source_sha256=digest,
        evidence_spans=selected.evidence_spans, language="zh")
    assert not failed and len(verified) == len(selected.evidence_spans)
    assert calls == ["parse", "enhance", "select"], "replay must not start a layout model"
