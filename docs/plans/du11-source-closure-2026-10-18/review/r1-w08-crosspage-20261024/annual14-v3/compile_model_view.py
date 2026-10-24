"""Compile the frozen local selection to the current scoped model-task view.

This is an offline, read-only audit: it sends no provider request and stores no
selected prose. The result binds the exact task membership and payload hash.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from company_wiki.automation.narrative_model_scoped import (
    MAX_SUMMARY_CLAIMS,
    compile_scoped_model_view,
)
from company_wiki.source_contract.evidence_span import EvidenceSpan


HERE = Path(__file__).resolve().parent
SELECTION = HERE / "selection.json"
OUTPUT = HERE / "model-view.json"


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_json(value: Any) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":")).encode("utf-8"))


def main() -> None:
    selected = json.loads(SELECTION.read_text(encoding="utf-8"))
    spans = tuple(EvidenceSpan.from_dict(item) for item in selected["selected_evidence"])
    package = SimpleNamespace(
        evidence_spans=spans,
        reading_context=selected["reading_context"],
    )
    view = compile_scoped_model_view(package, max_claims=MAX_SUMMARY_CLAIMS)
    payload = view.to_model_dict()
    span_by_id = {span.span_id: span for span in spans}

    a12_forecasts = {
        span.span_id for span in spans
        if span.coordinates.page_number == 14
        and "预计2026年公司整体收入达到" in (span.raw_text or "")
    }
    a12_premises = {
        span.span_id for span in spans
        if span.coordinates.page_number == 14
        and "上述提及的2026年全年经营业绩展望" in (span.raw_text or "")
    }
    a12_tasks = [task for task in view.plan.tasks if a12_forecasts.intersection(task.support_ids)]
    a12_closure = bool(a12_forecasts and a12_premises and a12_tasks) and all(
        a12_premises.intersection(task.member_ids) for task in a12_tasks
    )

    a13_policy_terms = (
        "履行了合同中的履约义务",
        "某一时段内履行的履约义务",
        "某一时点履行的履约义务",
        "预收销售商品或服务款项",
        "待履行了相关履约义务时再转为收入",
    )
    a13_policy_spans = [
        span for span in spans
        if span.coordinates.page_number in {119, 120, 184}
        and any(term in (span.raw_text or "") for term in a13_policy_terms)
    ]
    a13_amount_needles = (
        "12,125,518,838.35",
        "31,295,304,900.48",
    )
    a13_amounts_selected = any(
        needle in (span.raw_text or "")
        for needle in a13_amount_needles for span in spans
    )

    tasks = []
    for task in view.plan.tasks:
        tasks.append({
            "task_key": task.key,
            "kind": task.kind,
            "section_role": task.section_role,
            "support_span_ids": list(task.support_ids),
            "context_span_ids": list(task.context_ids),
            "member_span_ids": list(task.member_ids),
        })

    result = {
        "schema_version": "w08-annual14-v3-model-view-audit/1",
        "selection_path": "selection.json",
        "selection_sha256": sha256(SELECTION.read_bytes()),
        "source_id": selected["source_ref"]["source_id"],
        "source_sha256": selected["source_ref"]["content_sha256"],
        "oracle_sha256": selected["oracle_sha256"],
        "max_claims": MAX_SUMMARY_CLAIMS,
        "compiled_task_count": len(view.plan.tasks),
        "model_binding_sha256": view.binding_sha256,
        "model_payload_sha256": digest_json(payload),
        "external_model_calls": 0,
        "downloads": 0,
        "raw_copies": 0,
        "a12": {
            "forecast_span_ids": sorted(a12_forecasts),
            "premise_span_ids": sorted(a12_premises),
            "forecast_task_keys": [task.key for task in a12_tasks],
            "explicit_premise_in_every_forecast_task": a12_closure,
        },
        "a13": {
            "policy_span_ids": [span.span_id for span in a13_policy_spans],
            "policy_locators": [span.locator for span in a13_policy_spans],
            "exact_segment_revenue_amounts_selected": a13_amounts_selected,
        },
        "tasks": tasks,
        "span_locator_count": len(span_by_id),
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "compiled_task_count": result["compiled_task_count"],
        "model_binding_sha256": result["model_binding_sha256"],
        "model_payload_sha256": result["model_payload_sha256"],
        "a12_task_keys": result["a12"]["forecast_task_keys"],
        "a12_explicit_premise_in_every_forecast_task": a12_closure,
        "a13_policy_span_count": len(a13_policy_spans),
        "a13_exact_segment_revenue_amounts_selected": a13_amounts_selected,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
