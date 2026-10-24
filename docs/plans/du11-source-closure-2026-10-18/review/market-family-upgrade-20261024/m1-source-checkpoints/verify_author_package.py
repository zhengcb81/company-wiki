"""Compatibility and positive/negative source-fixture QA using DU-BENCH itself.

These observations are deliberately synthetic source-quote fixtures. They are
never presented as product selections, summaries, or independent acceptance.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from tools.document_understanding_benchmark.checkers import _support_set_status
from tools.document_understanding_benchmark.evaluate import evaluate
from tools.document_understanding_benchmark.gold import load_gold_dir

HERE = Path(__file__).resolve().parent


def fixture(gold, fact):
    rows = []
    for i, anchor in enumerate(fact["any_support_sets"][0]):
        rows.append({"locator": f"loc:fixture/m1/{i}", "page": anchor.get("page"),
                     "text": anchor["exact_quote"], "scope_id": fact["id"]})
    return {"schema_version": "du-observed/1", "sample_id": gold["sample_id"],
            "source_sha256": gold["source_sha256"], "route": None,
            "selected_locators": [r["locator"] for r in rows],
            "selected_evidence": rows, "context_evidence": rows,
            "selected_text": "\n".join(r["text"] for r in rows),
            "semantic_units": [], "claims": [],
            "coverage": {"native_scan": "complete", "complete": False,
                         "opaque_pages": [], "deferred_unit_ids": [], "unassigned_unit_ids": []},
            "metrics": {}, "execution": {"mode": "offline_fixture", "calls": 0}}


def main():
    cases = []
    for gold in load_gold_dir(HERE / "gold"):
        for fact in gold["facts"]:
            observation = fixture(gold, fact)
            status, _ = _support_set_status(fact["any_support_sets"][0], observation,
                require_same_scope=bool(fact.get("require_same_scope")),
                context=fact["target_kind"] == "disposition_context")
            assert status == "PASS", (gold["sample_id"], fact["id"], status)
            evaluated = evaluate(observation, {**gold, "facts": [fact]})
            basis = next(c for c in evaluated["checks"] if c["check_id"] == "basis." + fact["id"])
            assert basis["status"] in {"PASS", "NOT_EVALUATED"}, (gold["sample_id"], fact["id"], basis)
            negative = []
            for forbidden in fact["must_not_assert"]:
                bad = copy.deepcopy(observation)
                # True source introduction plus the precise false assertion:
                # ensures existing related-claim detection knows this subject.
                bad["claims"] = [{"text": fact["any_support_sets"][0][0]["exact_quote"] + "\n" + forbidden,
                                  "role": "unknown", "modality": "unknown",
                                  "evidence_locators": bad["selected_locators"], "quantities": []}]
                result = evaluate(bad, {**gold, "facts": [fact]})
                basis_bad = next(c for c in result["checks"] if c["check_id"] == "basis." + fact["id"])
                caught = any("must_not_assert" in s for s in basis_bad["observed"] if isinstance(s, str))
                assert basis_bad["status"] == "FAIL" and caught, (gold["sample_id"], fact["id"], forbidden, basis_bad)
                negative.append({"forbidden": forbidden, "caught_by_existing_evaluator": True})
            drop_checks = []
            if fact["target_kind"] != "correctness_if_emitted":
                for i in range(len(fact["any_support_sets"][0])):
                    bad = copy.deepcopy(observation)
                    bad["selected_evidence"].pop(i)
                    bad["context_evidence"] = bad["selected_evidence"]
                    status, _ = _support_set_status(fact["any_support_sets"][0], bad,
                        require_same_scope=bool(fact.get("require_same_scope")),
                        context=fact["target_kind"] == "disposition_context")
                    drop_checks.append({"omitted_anchor_index": i, "support_status": status})
                    assert status != "PASS", (gold["sample_id"], fact["id"], "redundant anchor", i)
            cases.append({"sample_id": gold["sample_id"], "fact_id": fact["id"],
                          "full_source_support_status": status if not drop_checks else "PASS",
                          "positive_basis_status": basis["status"], "negative_cases": negative,
                          "missing_joint_anchor_cases": drop_checks})
    result = {"schema_version": "m1-author-evaluator-compatibility/1", "scope": "synthetic_source_quote_fixtures_only",
              "independent_acceptance": False, "fact_count": len(cases),
              "forbidden_assertion_cases": sum(len(c["negative_cases"]) for c in cases),
              "joint_anchor_omission_cases": sum(len(c["missing_joint_anchor_cases"]) for c in cases),
              "existing_evaluator_only": True, "cases": cases}
    (HERE / "author-compatibility.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("fact_count", "forbidden_assertion_cases", "joint_anchor_omission_cases")}))


if __name__ == "__main__":
    main()
