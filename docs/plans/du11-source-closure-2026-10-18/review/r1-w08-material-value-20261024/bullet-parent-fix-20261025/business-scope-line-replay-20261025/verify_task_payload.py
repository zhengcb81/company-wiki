"""Verify page-119 business scope survives the production scoped payload offline."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from company_wiki.automation.narrative_model_scoped import (
    MAX_SUMMARY_CLAIMS,
    compile_scoped_model_view,
)
from company_wiki.source_contract.evidence_span import EvidenceSpan


HERE = Path(__file__).resolve().parent
SELECTION = HERE / "selection.json"
MODEL_VIEW = HERE / "model-view.json"
RECEIPT = HERE / "task-model-view-receipt.json"
TARGET_LOCATOR = "loc:v1/page:119/paragraph:4/chars:72-240"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_sha(value: object) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":")).encode("utf-8"))


def main() -> None:
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    stored_view = json.loads(MODEL_VIEW.read_text(encoding="utf-8"))
    spans = tuple(EvidenceSpan.from_dict(item) for item in selection["selected_evidence"])
    target = next((span for span in spans if span.locator == TARGET_LOCATOR), None)
    if target is None:
        raise AssertionError("ST-A01 scope span is absent from selected evidence")
    topics = target.structured_value.get("topics", ())
    if "business_scope" not in topics:
        raise AssertionError("selected span lost its business_scope topic")

    package = SimpleNamespace(evidence_spans=spans, reading_context=selection["reading_context"])
    view = compile_scoped_model_view(package, max_claims=MAX_SUMMARY_CLAIMS)
    payload = view.to_model_dict()
    payload_sha256 = canonical_sha(payload)
    if payload_sha256 != stored_view["model_payload_sha256"]:
        raise AssertionError("recompiled production model payload differs from the frozen model-view receipt")

    task = next((item for item in view.plan.tasks if target.span_id in item.support_ids), None)
    if task is None:
        raise AssertionError("selected scope is not support in any production summary task")
    model_task = next(item for item in payload["tasks"] if item["key"] == task.key)
    source_key = view._source_keys[target.span_id]
    part_key = next(key for key, span_id in view._parts[task.key].items()
                    if span_id == target.span_id)
    part = next((item for item in model_task["parts"] if item["key"] == part_key), None)
    if part is not None and "shared_ref" in part:
        part = next((item for item in payload["shared_fragments"]
                     if item["source_key"] == part["shared_ref"]), None)
    text_visible = part is not None and part.get("text") == target.raw_text
    support_parts = model_task.get("support_parts", payload["task_defaults"].get("support_parts"))
    support_visible = support_parts == "all_parts" or part_key in support_parts
    task_topics = model_task.get("topics", payload["task_defaults"].get("topics", ()))
    if not text_visible or not support_visible or "business_scope" not in task_topics:
        raise AssertionError("scope text, support role, or topic is absent from the actual model payload")

    group = next((item for item in selection["reading_context"]["groups"]
                  if target.span_id in item["evidence_ids"]), None)
    if group is None:
        raise AssertionError("selected scope has no native reading-context group")

    receipt = {
        "schema_version": "annual14-st-a01-scoped-payload-check/1",
        "status": "PASS_PAYLOAD_VISIBLE_NO_MODEL_REQUEST",
        "source_id": selection["source_ref"]["source_id"],
        "source_sha256": selection["source_ref"]["content_sha256"],
        "selection_sha256": sha256(SELECTION.read_bytes()),
        "stored_model_view_sha256": sha256(MODEL_VIEW.read_bytes()),
        "model_payload_sha256": payload_sha256,
        "compiler_sources": {
            "src/company_wiki/automation/narrative_model_scoped.py": sha256(
                Path("src/company_wiki/automation/narrative_model_scoped.py").read_bytes()),
            "src/company_wiki/document_understanding/summary_tasks.py": sha256(
                Path("src/company_wiki/document_understanding/summary_tasks.py").read_bytes()),
        },
        "target": {
            "span_id": target.span_id,
            "locator": target.locator,
            "topics": list(topics),
            "reading_group_id": group["group_id"],
            "reading_group_kind": group["kind"],
            "reading_group_section_role": group["section_role"],
            "task_key": task.key,
            "task_kind": task.kind,
            "task_section_role": task.section_role,
            "task_topics": list(task.topics),
            "support_visible": support_visible,
            "full_scope_text_visible": text_visible,
        },
        "request_sent": False,
        "response_reviewed": False,
        "raw_text_stored_in_receipt": False,
    }
    RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": receipt["status"],
        "task_key": task.key,
        "task_kind": task.kind,
        "task_section_role": task.section_role,
        "task_topics": list(task.topics),
        "support_visible": support_visible,
        "full_scope_text_visible": text_visible,
        "model_payload_sha256": payload_sha256,
        "request_sent": False,
    }, ensure_ascii=True))


if __name__ == "__main__":
    main()
