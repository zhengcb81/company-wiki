"""One final real selection after cache-closure/structure-guard follow-ups.

Bind the final source bytes, and only reuse the content review when every
selected source span, task-local group and compiled task member is identical.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

from company_wiki.automation.narrative_model_scoped import MAX_SUMMARY_CLAIMS, compile_scoped_model_view
from company_wiki.source_contract.evidence_span import EvidenceSpan


HERE = Path(__file__).resolve().parent
ROOT = next(parent for parent in HERE.parents if (parent / "pyproject.toml").exists())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output = HERE / "final-source-selection.json"
    if output.exists():
        raise FileExistsError(output)
    old_receipt = json.loads((HERE / "replay-receipt.json").read_text(encoding="utf-8"))
    args = list(old_receipt["argv"])
    for flag in ("--trace-output",):
        index = args.index(flag)
        del args[index:index + 2]
    args[args.index("--output") + 1] = str(output)
    runner_path = ROOT / ".planning/r1-w08-real-20261023/run_real_selection_prose_quality_20261023.py"
    files = sorted((ROOT / "src/company_wiki").rglob("*.py"))
    before = {path.relative_to(ROOT).as_posix(): digest(path) for path in files}
    spec = importlib.util.spec_from_file_location("final_real_source_runner", runner_path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    sys.argv = [str(runner_path), *args]
    runner.main()
    assert before == {path.relative_to(ROOT).as_posix(): digest(path) for path in files}
    old = json.loads((HERE / "selection.json").read_text(encoding="utf-8"))
    current = json.loads(output.read_text(encoding="utf-8"))
    spans = tuple(EvidenceSpan.from_dict(item) for item in current["selected_evidence"])
    view = compile_scoped_model_view(SimpleNamespace(evidence_spans=spans,
        reading_context=current["reading_context"]), max_claims=MAX_SUMMARY_CLAIMS)
    tasks = [{"task_key": task.key, "kind": task.kind, "section_role": task.section_role,
              "support_span_ids": list(task.support_ids), "context_span_ids": list(task.context_ids),
              "member_span_ids": list(task.member_ids)} for task in view.plan.tasks]
    old_view = json.loads((HERE / "model-view.json").read_text(encoding="utf-8"))
    equal = {"source_ref": old["source_ref"] == current["source_ref"],
             "selected_spans": old["selected_spans"] == current["selected_spans"],
             "selected_evidence": old["selected_evidence"] == current["selected_evidence"],
             "task_local_groups": old["reading_context"]["groups"] == current["reading_context"]["groups"],
             "compiled_tasks": old_view["tasks"] == tasks}
    # Formatting only: keep complete current observation without duplicated
    # indentation bytes. No fields or rejected outcomes are removed.
    output.write_text(json.dumps(current, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    receipt = {"schema_version": "w08-final-source-content-equivalence/1", "argv": args,
               "source_stable": True, "source_count": len(before),
               "source_digest": hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest(),
               "changed_source_sha256": {name: value for name, value in before.items() if name.endswith(
                   ("narrative_business_meaning.py", "narrative_source_purpose.py", "narrative_reporting_rules.py",
                    "document_understanding/decision_inventory.py"))},
               "final_selection_sha256": digest(output), "prior_selection_sha256": digest(HERE / "selection.json"),
               "prior_content_review_sha256": digest(HERE / "content-review/report.json"),
               "source_and_task_equalities": equal, "content_review_reusable": all(equal.values()),
               "compiled_task_count": len(tasks), "model_binding_sha256": view.binding_sha256,
               "metrics": {key: current[key] for key in ("physical_pages", "candidate_count", "selected_count",
                                                         "selected_chars", "work_budget", "checkpoint_pass")},
               "external_model_calls": 0, "downloads": 0, "raw_copies": 0, "protected_unchanged": current["protected_unchanged"]}
    (HERE / "final-source-receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                                                   encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False))
    if not all(equal.values()):
        raise SystemExit("Changed content must receive a new independent review")


if __name__ == "__main__":
    main()
