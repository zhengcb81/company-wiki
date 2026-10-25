"""Check real compiled input, unchanged source checkpoints and bounded replay."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    label = sys.argv[1]
    if not label.isalnum():
        raise ValueError("alphanumeric attempt required")
    attempt = HERE / label
    output = attempt / "parent-input-check.json"
    if output.exists():
        raise FileExistsError(output)
    selection, model, receipt = [load(attempt / name) for name in
        ("selection.json", "model-view.json", "replay-receipt.json")]
    baseline = load(HERE.parent / "annual14-current-source-review-20261025/independent/report.json")
    selected = {r["span_id"]: r for r in selection["selected_spans"]}
    used = {sid for task in model["tasks"] for sid in task["member_span_ids"]}
    old_pass = [r for r in baseline["targets"] if r["source_input_status"] == "PASS"]
    require(len(old_pass) == 10, "baseline count changed")
    preserved = []
    for target in old_pass:
        missing = set(target["selected_span_ids"]) - (set(selected) & used)
        if target["target_id"] == "ST-A03":
            # The independently reviewed ambiguous numeric row is not the
            # business geography fact. The complete parent-location note and
            # actual regional revenue disclosure must still reach the payload.
            ambiguous = {r["span_id"] for r in target["evidence"]
                         if "table_structure_ambiguous" in r.get("quality_flags", [])}
            require(missing <= ambiguous, "A03 nonambiguous evidence lost")
            require(any("客户母公司所在地" in selected[i]["raw_text"] for i in used if i in selected),
                    "A03 exact geographic basis missing from payload")
        else:
            require(not missing, "prior PASS evidence lost: " + target["target_id"])
        preserved.append(target["target_id"])
    parent = next(r for r in selected.values() if r["locator"].startswith("loc:v1/page:13/paragraph:21"))
    intro = next(r for r in selected.values() if r["locator"].startswith("loc:v1/page:13/paragraph:22"))
    checked = []
    for paragraph in (3, 12, 14):
        fact = next(r for r in selected.values()
                    if r["locator"].startswith(f"loc:v1/page:14/paragraph:{paragraph}")
                    and (r["locator"].endswith(str(paragraph)) or "/chars:" in r["locator"]))
        tasks = [t for t in model["tasks"] if fact["span_id"] in t["support_span_ids"]]
        require(tasks, "actual descendant task missing")
        for task in tasks:
            require({parent["span_id"], intro["span_id"]} <= set(task["context_span_ids"]),
                    "Chemistry parent/period absent from own descendant context")
            texts = [selected[i]["raw_text"] for i in task["member_span_ids"]]
            require(not any("(2) 测试业务" in text or "(3) 生物学业务" in text for text in texts),
                    "sibling business leaked into Chemistry task")
        checked.append({"fact_locator": fact["locator"], "task_keys": [t["task_key"] for t in tasks],
                        "chemistry_and_period_in_own_context": True, "sibling_leak": False})
    old_a13 = load(HERE.parent / "st-a05-parent-investigation-20261025/attempt02/model-view.json")["a13"]
    require(set(old_a13["policy_span_ids"]) == set(model["a13"]["policy_span_ids"]), "A13 input changed")
    require(set(model["a13"]["policy_span_ids"]) <= used, "A13 input absent from actual payload")
    require(selection["source_original_sha_verified"] and selection["protected_unchanged"]
            and receipt["source_stable"], "source/config/code stability unproven")
    require(selection["coverage_complete"] is False, "whole source silently promoted")
    require(receipt["selected_count"] <= 112 and receipt["work_budget"]["limit"] == 16_000_000
            and not receipt["work_budget"]["exhausted"], "original resource caps changed")
    require(receipt["external_model_calls"] == receipt["downloads"] == receipt["raw_copies"] == 0,
            "unexpected external spend or original copy")
    result = {"status": "PASS_SOURCE_CONTEXT_ENGINEERING_ONLY", "attempt": label,
        "previous_pass_targets_retained": preserved, "chemistry_descendants": checked,
        "a13_seven_inputs_retained": True, "global_partial_retained": True,
        "formal_summary": "NOT_REVIEWED", "RF_adoption": "OPEN",
        "artifact_sha256": {name: sha256((attempt / name).read_bytes()).hexdigest()
            for name in ("selection.json", "model-view.json", "replay-receipt.json")}}
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
