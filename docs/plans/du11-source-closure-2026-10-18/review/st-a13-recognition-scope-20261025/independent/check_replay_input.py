"""Read-only frozen replay/input verification; writes only a new review receipt."""
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import sys
import pymupdf
from company_wiki.automation.narrative_model_scoped import compile_scoped_model_view, MAX_SUMMARY_CLAIMS
from company_wiki.source_contract.evidence_span import EvidenceSpan

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
HERE = Path(__file__).resolve().parent
PLAN = ROOT / "docs/plans/du11-source-closure-2026-10-18"
OLD = PLAN / "review/annual14-current-source-review-20261025/independent/report.json"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def text_sha(text):
    return hashlib.sha256(text.encode("utf8")).hexdigest()

def read(path):
    return json.loads(path.read_text(encoding="utf8"))

def signature(members):
    return text_sha(json.dumps([(x["role"], x["full_quote"]) for x in members], ensure_ascii=False))

def main():
    if len(sys.argv) != 2 or not sys.argv[1].isalnum():
        raise SystemExit("usage: check_replay_input.py ATTEMPT")
    attempt = HERE.parent / sys.argv[1]
    output = HERE / (sys.argv[1] + "-input-review.json")
    if output.exists():
        raise FileExistsError(output)
    selection = read(attempt / "selection.json")
    model = read(attempt / "model-view.json")
    receipt = read(attempt / "replay-receipt.json")
    old = read(OLD)
    spans = {e["span_id"]: e for e in selection["selected_evidence"]}
    view = compile_scoped_model_view(SimpleNamespace(
        evidence_spans=tuple(EvidenceSpan.from_dict(e) for e in spans.values()),
        reading_context=selection["reading_context"]), max_claims=MAX_SUMMARY_CLAIMS)
    material = view.to_model_dict()
    payload_sha = text_sha(json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    shared = {x["source_key"]: x for x in material.get("shared_fragments", [])}
    actual_tasks = {x["key"]: x for x in material["tasks"]}
    task_views = []
    errors = []
    for task in view.plan.tasks:
        model_task = actual_tasks[task.key]
        parts = {x["key"]: x for x in model_task["parts"]}
        support = model_task.get("support_parts", material["task_defaults"].get("support_parts"))
        context = model_task.get("context_parts", material["task_defaults"].get("context_parts", []))
        members = []
        for part_key, sid in view._parts[task.key].items():
            part = parts[part_key]
            resolved = shared[part["shared_ref"]] if "shared_ref" in part else part
            expected = spans[sid]
            role = "support" if sid in task.support_ids else "context"
            actual_role = "support" if support == "all_parts" or part_key in support else "context" if part_key in context else "unknown"
            if role != actual_role or resolved["text"] != expected["raw_text"] or resolved.get("quality_flags", []) != expected["quality_flags"]:
                errors.append([task.key, part_key, "payload_text_or_role_or_flags"])
            members.append({"span_id": sid, "locator": expected["locator"], "role": role, "full_quote": resolved["text"]})
        task_views.append({"task_key": task.key, "members": members})
    source = ROOT / "companies/药明康德/raw/financial_reports/药明康德：2025年年度报告.pdf"
    source_checks = []
    block_count = 0
    with pymupdf.open(source) as document:
        pages = {e["coordinates"]["page_number"] for e in spans.values()}
        blocks = {p: {i: "\n".join("".join(x.get("text", "") for x in line.get("spans", [])) for line in b.get("lines", [])).strip()
                     for i, b in enumerate(document[p - 1].get_text("dict", sort=False)["blocks"]) if b.get("type") == 0} for p in pages}
        for e in spans.values():
            md = e["structured_value"]
            page = e["coordinates"]["page_number"]
            native = md.get("native_range")
            valid = True
            if native:
                assembled = ["\n"] * (e["coordinates"]["char_end"] - e["coordinates"]["char_start"])
                for m in native["members"]:
                    raw = blocks[page][m["pdf_block"]]
                    piece = raw[m["block_char_start"]:m["block_char_end"]]
                    block_count += 1
                    valid = valid and text_sha(raw) == m["block_sha256"] and text_sha(piece) == m["text_sha256"]
                    start = m["view_char_start"] - e["coordinates"]["char_start"]
                    assembled[start:start + len(piece)] = piece
                valid = valid and "".join(assembled) == e["raw_text"]
            else:
                raw = blocks[page][md["pdf_block"]]
                piece = raw[md["block_char_start"]:md["block_char_end"]]
                block_count += 1
                valid = text_sha(raw) == md["block_sha256"] and piece == e["raw_text"]
            source_checks.append({"span_id": e["span_id"], "locator": e["locator"], "exact_original_match": valid})
            if not valid:
                errors.append([e["locator"], "original_text"])
    actual_signatures = {signature(t["members"]) for t in task_views}
    old_evidence = {e["span_id"]: e for t in old["targets"] for e in t["evidence"]}
    current_texts = {e["raw_text"] for e in spans.values()}
    prior_pass = []
    for target in old["targets"]:
        if target["source_input_status"] != "PASS":
            continue
        target_ids = set(target["selected_span_ids"])
        relevant_tasks = [t for t in old["reviewed_actual_task_views"] if any(m["span_id"] in target_ids and m["role"] == "support" for m in t["members"])]
        quotes_kept = all(e["full_quote"] in current_texts for e in target["evidence"])
        tasks_kept = all(signature(t["members"]) in actual_signatures for t in relevant_tasks)
        prior_pass.append({"target_id": target["target_id"], "all_quotes_retained": quotes_kept,
                           "all_support_task_local_context_retained": tasks_kept})
        if not quotes_kept or not tasks_kept:
            errors.append([target["target_id"], "old_pass_content_or_context_changed"])
    mechanism = [t for t in task_views if any(m["locator"] == "loc:v1/page:184/paragraph:8/chars:269-473" and m["role"] == "support" for m in t["members"])]
    if len(mechanism) != 1:
        errors.append(["A13", "mechanism_task_count"])
    checks = {"selection_receipt_match": sha(attempt / "selection.json") == receipt["selection_sha256"],
              "model_view_receipt_match": sha(attempt / "model-view.json") == receipt["model_view_sha256"],
              "exact_current_payload_match": payload_sha == model["model_payload_sha256"],
              "source_hash_match": sha(source) == selection["source_ref"]["content_sha256"],
              "all_112_original_spans_exact": len(source_checks) == 112 and all(x["exact_original_match"] for x in source_checks),
              "all_10_prior_passes_content_and_context_retained": len(prior_pass) == 10 and all(x["all_quotes_retained"] and x["all_support_task_local_context_retained"] for x in prior_pass)}
    result = {"schema_version": "recognition-scope-independent-replay-input-check/1", "attempt": sys.argv[1],
              "artifact_sha256": {str((attempt / n).relative_to(ROOT)): sha(attempt / n) for n in ("selection.json", "model-view.json", "trace.json", "replay-receipt.json")},
              "source_sha256": sha(source), "recompiled_payload_sha256": payload_sha,
              "checks": checks, "errors": errors, "old_pass_targets": prior_pass,
              "a13_mechanism_task": mechanism, "source_span_checks": source_checks,
              "original_block_member_checks": block_count, "task_count": len(task_views),
              "model_response_semantics": "NOT_REVIEWED", "current_rf_consumption": "OPEN",
              "external_calls": 0, "downloads": 0}
    with output.open("x", encoding="utf8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"output": str(output), "checks": checks, "errors": errors}, ensure_ascii=False))
    return 0 if all(checks.values()) and not errors else 1

if __name__ == "__main__":
    raise SystemExit(main())
