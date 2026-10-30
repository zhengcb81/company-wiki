"""Independent pure-assessment probe. Only captured JSON and local fixtures.

No source originals/PDFs, providers, production config, model or network calls.
"""
from __future__ import annotations
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from company_wiki.automation.narrative_contracts import NarrativeSelectResult
from company_wiki.automation.narrative_model_scoped import compile_scoped_model_view, MAX_SUMMARY_CLAIMS
from company_wiki.automation.narrative_summary_assessment import assess_summary, prose_diagnostics, assessment_identity
from company_wiki.source_catalog.narrative_evidence import summary_claim_type_for_roles
from unit.test_narrative_extractive_runtime import selected

CASES = [
    ("narrow_actual_en", "The company will apply to resume review. The company received second-round inquiry.",
     "The company received second-round inquiry.", "actual", []),
    ("narrow_actual_report_en", "According to news reports, the company lost revenue. The company employs 120 people.",
     "The company employs 120 people.", "actual", []),
    ("actual_disposal_cn", "公司已将设备转入商业化生产。", "公司已将设备转入商业化生产。", "actual", []),
    ("actual_plan_completion_cn", "公司本年计划完成率达到100%。", "公司本年计划完成率达到100%。", "actual", []),
    ("correct_narrow_denial_cn", "据报道，所述情况涉及家电产品，该事项未对子公司经营构成重大影响。",
     "该事项未对子公司经营构成重大影响。", "negation", []),
    ("actual_narrow_received_cn", "公司将申请恢复审核。公司已收到问询函。", "公司已收到问询函。", "actual", []),
    # Exact future proposition with an incorrect machine modality: supported diagnostic,
    # not a demand that the guard infer arbitrary paraphrase entailment.
    ("true_future_en", "The company will apply to resume review.",
     "The company will apply to resume review.", "actual", ["possible_modality_mismatch"]),
    ("future_preserved_en", "The company will apply to resume review.",
     "The company will apply to resume review.", "planned", []),
    ("degree_retained_en", "The incident did not materially affect operations.",
     "The incident did not materially affect operations.", "negation", []),
    ("degree_missing_en", "The incident did not materially affect operations.",
     "The incident did not affect operations.", "negation", ["possible_negation_degree_loss"]),
    ("degree_hidden_unrelated_en", "The incident did not materially affect operations.",
     "The incident did not affect operations; a material facility began construction.", "negation",
     ["possible_negation_degree_loss"]),
    ("report_hidden_unrelated_en", "According to news reports, the event involves home appliances.",
     "According to reports, a plant opened. The event involves home appliances.", "actual",
     ["possible_attribution_loss"]),
]


def collision():
    source = selected(1)
    wire = source.to_dict()
    ids = [span.span_id for span in source.evidence_spans]
    wire["reading_context"]["groups"] = [
        {"group_id": group, "kind": "business_progress", "section_role": role, "evidence_ids": ids}
        for group, role in [("native-a", "business"), ("native-b", "risk")]
    ]
    source = NarrativeSelectResult.from_dict(wire)
    view = compile_scoped_model_view(source, max_claims=MAX_SUMMARY_CLAIMS)
    task = view.plan.tasks[0]
    claim = {"claim_id": "arbitrary", "text": source.evidence_spans[0].raw_text,
             "evidence_ids": list(task.support_ids), "context_evidence_ids": list(task.context_ids),
             "claim_type": summary_claim_type_for_roles(task.support_roles), "modality": "actual",
             "needs_review": False}
    return {
        "admission": view.to_binding()["source_admission"],
        "requested_first": assess_summary(source, [claim], requested_task_keys=["t1"], plan_max_claims=MAX_SUMMARY_CLAIMS),
        "requested_both": assess_summary(source, [claim], requested_task_keys=["t1", "t2"], plan_max_claims=MAX_SUMMARY_CLAIMS),
    }


def bounds_identity():
    source = selected(33)
    spans = []
    text = "According to reports, Orion will open a factory."
    for span in source.evidence_spans:
        spans.append(type(span).create(
            source_id=span.source_id, coordinates=span.coordinates, raw_text=text,
            structured_value={**span.structured_value, "text_sha256": hashlib.sha256(text.encode()).hexdigest()},
            parser_name=span.parser_name, parser_version=span.parser_version,
            parse_status=span.parse_status, quality_flags=span.quality_flags))
    wire = source.to_dict()
    wire["evidence_spans"] = [span.to_dict() for span in spans]
    wire["reading_context"]["groups"] = [{"group_id": "cap-probe", "kind": "business_progress",
        "section_role": "business", "evidence_ids": [span.span_id for span in spans]}]
    source = NarrativeSelectResult.from_dict(wire)
    task = compile_scoped_model_view(source, max_claims=MAX_SUMMARY_CLAIMS).plan.tasks[0]
    claim = {"claim_id": "c1", "text": "Orion will open a factory.", "evidence_ids": list(task.support_ids),
             "context_evidence_ids": list(task.context_ids),
             "claim_type": summary_claim_type_for_roles(task.support_roles), "modality": "actual",
             "needs_review": False}
    report = assess_summary(source, [claim, {**claim, "claim_id": "c2"}],
                            requested_task_keys=["t1"], plan_max_claims=MAX_SUMMARY_CLAIMS)
    return {"identity": assessment_identity(), "valid_two_clauses_one_task_33spans": True,
            "retained_diagnostics": len(report["diagnostics"]), "diagnostic_count": report["diagnostic_count"],
            "diagnostics_limited": report["diagnostics_limited"], "emitted_tasks": report["emitted_task_keys"],
            "diagnostic_claim_ids": report.get("diagnostic_claim_ids"),
            "semantic_status": report["semantic_status"], "subfact_status": report["subfact_coverage_status"]}


def main():
    capture = ROOT / ".planning/source-description-20261030/real-summary-v3"
    source = NarrativeSelectResult.from_dict(json.loads(gzip.open(
        next((capture / "materials").glob("*.selection.json.gz")), "rt", encoding="utf-8").read()))
    bundle = json.loads(gzip.open(next(capture.glob("*.bundle.json.gz")), "rt", encoding="utf-8").read())
    captured_request = json.loads(gzip.open(next((capture / "materials").glob("*.input.json.gz")),
                                            "rt", encoding="utf-8").read())
    captured_payload = json.loads(captured_request["messages"][1]["content"])
    captured_plan_cap = captured_payload["material"]["max_claims"]
    view = compile_scoped_model_view(source, max_claims=captured_plan_cap)
    claims = bundle["summary"]["draft"]["claims"]
    report = assess_summary(source, claims, requested_task_keys=[task.key for task in view.model_tasks],
                            plan_max_claims=captured_plan_cap)
    prospective_view = compile_scoped_model_view(source, max_claims=MAX_SUMMARY_CLAIMS)
    prospective_report = assess_summary(source, claims,
        requested_task_keys=[task.key for task in prospective_view.model_tasks], plan_max_claims=MAX_SUMMARY_CLAIMS)
    rows = []
    for name, original, prose, modality, expected in CASES:
        actual = [row["rule_code"] for row in prose_diagnostics(original, prose, modality)]
        rows.append({"name": name, "source": original, "claim": prose, "modality": modality,
                     "expected_codes": expected, "actual_codes": actual,
                     "match": set(actual) == set(expected)})
    result = {
        "schema_version": "independent-summary-assessment-probe/1", "no_paid_no_pdf_parse": True,
        "module_sha256": hashlib.sha256((ROOT / "src/company_wiki/automation/narrative_summary_assessment.py").read_bytes()).hexdigest(),
        "real_v3": report, "actual_request_plan_sha256": view.plan.binding_sha256,
        "actual_captured_material_max_claims": captured_plan_cap,
        "captured_output_plan_max_claims": captured_payload["output_plan"]["max_claims"],
        "plan_matches_request": report["source_plan_sha256"] == view.plan.binding_sha256,
        "explicit_40_marker_matches": prospective_report["source_plan_sha256"] == prospective_view.plan.binding_sha256,
        "neutral_cases": rows, "scope_collision": collision(), "bounds_identity": bounds_identity(),
    }
    (Path(__file__).parent / "probe-result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("plan_matches_request", result["plan_matches_request"])
    print("real_missing", report["missing_requested_task_keys"])
    print("real_diagnostics", [(row["task_key"], row["rule_code"]) for row in report["diagnostics"]])
    for row in rows:
        print(row["name"], row["match"], row["actual_codes"])
    print("collision requested_first", result["scope_collision"]["requested_first"]["emitted_task_keys"])
    print("collision requested_both", result["scope_collision"]["requested_both"]["emitted_task_keys"],
          result["scope_collision"]["requested_both"]["diagnostics"])


if __name__ == "__main__":
    main()
