"""Join frozen target evidence, exact budget rows and task membership offline.

This diagnostic does not grade content or infer unseen candidate stages. It
reuses recorded source text, selection and task outputs without reparsing raw.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


HERE = Path(__file__).resolve().parent
INPUTS = HERE.parent
MAX_OUTPUT_BYTES = 128 * 1024


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact(text: str):
    return re.sub(r"\s+", "", text)


def exact_overlap(left: str, right: str):
    a, b = compact(left), compact(right)
    return bool(a and b and min(len(a), len(b)) >= 16 and (a in b or b in a))


def main():
    checklist_path = INPUTS / "annual14/review.json"
    selection_path = INPUTS / "annual14-v5/selection.json"
    task_path = INPUTS / "annual14-v5/model-view.json"
    pages_path = INPUTS / "annual14/audit-original-eight-pages.json"
    checklist, selection, view, source = map(load, (checklist_path, selection_path, task_path, pages_path))
    assert len(checklist["rows"]) == 14
    assert digest(selection_path) == view["selection_sha256"]
    assert source["source_ref"] == selection["source_ref"]
    pages = {page["pdf_page"]: page for page in source["pages"]}
    assert all(hashlib.sha256(row["text"].encode("utf-8")).hexdigest() == row["text_sha256"]
               for row in pages.values())
    spans = selection["selected_spans"]
    tasks_by_span = {}
    for task in view["tasks"]:
        for sid in task["member_span_ids"]:
            tasks_by_span.setdefault(sid, []).append(task["task_key"])

    offset_checks = []
    for span in spans:
        match = re.search(r"page:(\d+)/paragraph:\d+/chars:(\d+)-(\d+)", span["locator"])
        if match and int(match[1]) in pages:
            text = pages[int(match[1])]["text"][int(match[2]):int(match[3])]
            offset_checks.append(text == span["raw_text"])
    assert offset_checks and all(offset_checks)

    budget_rows = []
    for diagnostic in selection["selection_diagnostics"]:
        for target in diagnostic.get("targets", ()):
            match = re.search(r"page:(\d+)/paragraph:\d+/chars:(\d+)-(\d+)", target.get("locator", ""))
            if match and int(match[1]) in pages:
                page, start, end = map(int, match.groups())
                text = pages[page]["text"][start:end]
                budget_rows.append({"code": diagnostic["code"], "target": target, "page": page, "text": text})

    rows = []
    for item in checklist["rows"]:
        supports = item.get("fallback", {}).get("original_support", ())
        selected_ids, task_keys, deferred = set(), set(), {}
        references = []
        for support in supports:
            page = support.get("pdf_page")
            quote = support.get("quote", "")
            refs = []
            for span in spans:
                if span["page_number"] == page and exact_overlap(quote, span["raw_text"]):
                    selected_ids.add(span["span_id"])
                    keys = tasks_by_span.get(span["span_id"], [])
                    task_keys.update(keys)
                    refs.append({"span_id": span["span_id"], "locator": span["locator"], "task_keys": keys})
            references.append({"source_locator": support.get("locator"), "pdf_page": page,
                               "quote_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
                               "selected_exact_containment_matches": refs})
            for entry in budget_rows:
                if entry["page"] == page and exact_overlap(quote, entry["text"]):
                    target = entry["target"]
                    deferred[target["item_id"]] = {
                        "code": entry["code"], "unit_id": target["item_id"],
                        "locator": target["locator"], "used": target["used"],
                        "requested": target["requested"], "limit": target["limit"],
                        "closure_size": target.get("closure_size"),
                        "source_quote_sha256": hashlib.sha256(entry["text"].encode("utf-8")).hexdigest(),
                    }
        rows.append({"target_id": item["target_id"], "source_supported_by_prior_independent_review": item["source_supported"],
                     "source_fragments": references, "selected_span_ids": sorted(selected_ids),
                     "observed_task_keys": sorted(task_keys), "exact_target_budget_deferrals": list(deferred.values()),
                     "candidate_and_admission": "not_observed_for_this_target_in_bounded_frozen_trace",
                     "request_sent_and_response_used": "not_executed", "quality_status": "not_regraded"})

    output = {"schema_version": "w08-frozen-target-map/1",
              "scope": "Frozen V5 only; exact containment is an observation, never complete target coverage or a new quality score.",
              "input_sha256": {str(p.relative_to(INPUTS)): digest(p) for p in (checklist_path, selection_path, task_path, pages_path)},
              "source_ref": selection["source_ref"], "targets": rows,
              "source_offset_crosschecks": {"count": len(offset_checks), "all_byte_text_equal": all(offset_checks)},
              "bounded_public_trace": {k: {"count": v["count"], "limited": v["limited"]}
                                       for k, v in selection["reading_context"]["selection_trace"].items() if isinstance(v, dict)},
              "selected_spans": len(spans), "compiled_tasks": len(view["tasks"]),
              "spans_shorter_than_40_chars": sum(len(row["raw_text"]) < 40 for row in spans),
              "raw_reparse": 0, "external_model_calls": 0, "downloads": 0, "raw_copies": 0}
    blob = (json.dumps(output, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    assert len(blob) <= MAX_OUTPUT_BYTES
    (HERE / "target-map.json").write_bytes(blob)
    print(json.dumps({"offset_checks": len(offset_checks), "targets": len(rows), "bytes": len(blob),
                      "exact_deferred_targets": [r["target_id"] for r in rows if r["exact_target_budget_deferrals"]]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
