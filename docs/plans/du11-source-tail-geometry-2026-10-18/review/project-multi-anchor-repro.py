"""Pure, bounded four-anchor project -> real source owner -> typed task plan.

No PDF/filesystem fixtures, model/client/network/environment reads. Import
make_case in a formal test or run this with ROOT minimal-system environment.
Before correction actual owner emits three citation views; typed planner
rejects. Corrected owner must retain the project and every original anchor,
expand the measured pair as one support scope, then pass unchanged max2 wire.
"""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]

from unit.du11_tail_integration.test_tail_source_wiring import rows
from unit.document_understanding_selection.test_reading_native_continuity import native, source_case
from company_wiki.source_catalog.narrative_reading import _prose_reading_packages
from company_wiki.document_understanding.summary_tasks import build_summary_task_plan


def make_case():
    values = rows() + [
        native("公司完成新设备客户验证。", 2, box=[89.88, 140.8, 530.76, 151.25]),
        native("公司新产线已经投产。", 3, box=[89.88, 161.2, 530.76, 171.65]),
    ]
    for wire, _metadata, _profile in values:
        wire["layout"]["column"] = "observed-main"
        wire["hints"]["font_runs"][0]["font_size"] = 10.45
    parsed, pipeline = source_case([], native_rows=values)
    package = pipeline["packages"]["packages"][0]
    package["kind"] = "project"
    package["anchor_unit_ids"] = package["member_unit_ids"][:]
    return parsed, pipeline


def exercise():
    parsed, pipeline = make_case()
    packages, _facts, audit, blocked = _prose_reading_packages(parsed, pipeline)
    project = next(p for p in packages if p["kind"] == "project")
    spans = [u.to_evidence_span(topics=(), selection_reasons=()) for u in parsed.units]
    mapping = {u.unit_id: span.span_id for u, span in zip(parsed.units, spans)}
    views = [{
        "support_evidence_ids": [mapping[u] for u in view],
        "context_evidence_ids": [mapping[u] for u in project["member_unit_ids"] if u not in view],
    } for view in project["citation_support_views"]]
    reading_context = {"schema_version": "du-production-reading/2", "groups": [{
        "group_id": "project-multiple-anchors", "kind": "project", "section_role": "business",
        "evidence_ids": [span.span_id for span in spans], "citation_views": views,
    }]}
    result = {"anchors": 4, "citation_view_count": len(views),
              "physical_windows": len(audit["windows"]), "blocked_count": len(blocked),
              "members_retained": project["member_unit_ids"] == pipeline["packages"]["packages"][0]["member_unit_ids"],
              "required_context_retained": project["required_context_unit_ids"] == pipeline["packages"]["packages"][0]["required_context_unit_ids"]}
    try:
        plan = build_summary_task_plan(spans, reading_context=reading_context, max_claims=8)
        result.update(accepted=True, tasks=len(plan.tasks),
                      all_anchor_support_retained=set().union(*(set(t.support_ids) for t in plan.tasks)) == set(mapping.values()))
    except ValueError as exc:
        result.update(accepted=False, error_type=type(exc).__name__, error=str(exc))
    return result


if __name__ == "__main__":
    output = exercise()
    print(json.dumps(output))
    raise SystemExit(0 if output["accepted"] else 1)
