"""RED tests for the frozen benchmark interfaces.

These tests exist before the oracle is implemented. They encode the required
contract from INTERFACES.md §5 and the DU-BENCH card: a healthy observation
passes, every deliberate defect fails, and anything the oracle cannot prove is
reported as NOT_EVALUATED rather than PASS.
"""

from __future__ import annotations

import pytest

from tools.document_understanding_benchmark import evaluate
from tools.document_understanding_benchmark.records import (
    validate_gold,
    validate_observed,
)
from tools.document_understanding_benchmark.schema import BenchmarkSchemaError
from tools.document_understanding_benchmark.tests.synthetic import GOLD, good_observed


def _status(result: dict) -> str:
    return result["status"]


def _check(result: dict, check_id: str) -> dict:
    for row in result["checks"]:
        if row["check_id"] == check_id:
            return row
    raise AssertionError(f"missing check {check_id}: {[c['check_id'] for c in result['checks']]}")


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------


def test_gold_validates_and_keeps_all_facts():
    gold = validate_gold(GOLD)
    assert gold["schema_version"] == "du-gold/1"
    assert len(gold["facts"]) == 4
    assert gold["scope"] == "development"


def test_gold_rejects_duplicate_fact_ids():
    broken = dict(GOLD, facts=[GOLD["facts"][0], dict(GOLD["facts"][0])])
    with pytest.raises(BenchmarkSchemaError):
        validate_gold(broken)


def test_gold_rejects_wrong_schema_version():
    with pytest.raises(BenchmarkSchemaError):
        validate_gold(dict(GOLD, schema_version="du-gold/2"))


def test_gold_rejects_anchor_without_quote():
    broken = {
        **GOLD,
        "facts": [
            {
                "id": "f",
                "importance": "normal",
                "any_support_sets": [[{"page": 1, "exact_quote": ""}]],
            }
        ],
    }
    with pytest.raises(BenchmarkSchemaError):
        validate_gold(broken)


def test_gold_rejects_anchor_without_page_or_line():
    broken = {
        **GOLD,
        "facts": [
            {
                "id": "f",
                "importance": "normal",
                "any_support_sets": [[{"exact_quote": "x"}]],
            }
        ],
    }
    with pytest.raises(BenchmarkSchemaError):
        validate_gold(broken)


def test_observed_rejects_wrong_schema_version():
    with pytest.raises(BenchmarkSchemaError):
        validate_observed(dict(good_observed(), schema_version="du-observed/2"))


def test_observed_rejects_unknown_modality():
    observed = good_observed()
    observed["claims"][0]["modality"] = "certainly-true"
    with pytest.raises(BenchmarkSchemaError):
        validate_observed(observed)


def test_observed_allows_missing_optional_fields():
    """Field absence means unknown; it must not be an error or a review gate."""

    observed = good_observed()
    for key in ("route", "coverage", "semantic_units", "metrics"):
        observed.pop(key)
    validated = validate_observed(observed)
    assert validated["route"] is None
    assert validated["coverage"]["native_scan"] is None


# ---------------------------------------------------------------------------
# positive baseline
# ---------------------------------------------------------------------------


def test_healthy_observation_passes():
    result = evaluate(good_observed(), GOLD)
    assert result["schema_version"] == "du-evaluation/1"
    assert _status(result) == "PASS"
    assert result["metrics"]["critical_fact_recall"] == 1.0


def test_result_is_json_serializable_and_ordered():
    import json

    result = evaluate(good_observed(), GOLD)
    text = json.dumps(result, ensure_ascii=False, sort_keys=True)
    assert "du-evaluation/1" in text
    again = evaluate(good_observed(), GOLD)
    assert json.dumps(again, ensure_ascii=False, sort_keys=True) == text


# ---------------------------------------------------------------------------
# route
# ---------------------------------------------------------------------------


def test_wrong_route_family_fails_route_check_only():
    observed = good_observed()
    observed["route"]["family"] = "results_release"
    result = evaluate(observed, GOLD)
    assert _check(result, "route.family")["status"] == "FAIL"
    assert _status(result) == "FAIL"


def test_missing_route_is_not_evaluated_not_failed():
    observed = good_observed()
    observed["route"] = None
    result = evaluate(observed, GOLD)
    assert _check(result, "route.family")["status"] == "NOT_EVALUATED"
    assert result["not_evaluated"]


# ---------------------------------------------------------------------------
# recall / omission
# ---------------------------------------------------------------------------


def test_dropped_critical_fact_fails():
    observed = good_observed()
    observed["claims"] = [c for c in observed["claims"] if "不生产VC" not in c["text"]]
    observed["selected_locators"] = [
        loc for loc in observed["selected_locators"] if loc != "loc:v1/page:3/paragraph:12"
    ]
    observed["selected_text"] = observed["selected_text"].replace("公司不生产VC。", "")
    result = evaluate(observed, GOLD)
    assert _check(result, "recall.f-no-vc")["status"] == "FAIL"
    assert _status(result) == "FAIL"
    assert result["metrics"]["critical_fact_recall"] < 1.0


def test_fact_present_only_as_selected_text_anchor_still_counts():
    """A fact carried by replayed selection text is recall, not omission."""

    observed = good_observed()
    observed["claims"] = [
        c for c in observed["claims"] if c["evidence_locators"] != ["loc:v1/page:3/paragraph:12"]
    ]
    result = evaluate(observed, GOLD)
    assert _check(result, "recall.f-no-vc")["status"] == "PASS"


def test_missing_page_in_coverage_makes_recall_unavailable():
    """A page the parser never read cannot prove recall either way."""

    observed = good_observed()
    observed["coverage"]["native_scan"] = "partial"
    observed["coverage"]["opaque_pages"] = [12]
    observed["claims"] = [c for c in observed["claims"] if "门店总数" not in c["text"]]
    result = evaluate(observed, GOLD)
    assert _check(result, "recall.f-stores-total")["status"] == "UNAVAILABLE"


# ---------------------------------------------------------------------------
# hallucination
# ---------------------------------------------------------------------------


def test_invented_fact_fails_hallucination_check():
    observed = good_observed()
    observed["claims"].append(
        {
            "text": "公司2024年赣锋锂业门店收入增长120%。",
            "evidence_locators": ["loc:v1/page:99/paragraph:1"],
            "role": "company_filing",
            "modality": "actual",
            "quantities": [],
        }
    )
    result = evaluate(observed, GOLD)
    assert _check(result, "integrity.unsupported_claims")["status"] == "FAIL"
    assert _status(result) == "FAIL"


def test_claim_citing_locator_never_selected_fails_replay():
    observed = good_observed()
    observed["claims"][0]["evidence_locators"] = ["loc:v1/page:77/paragraph:1"]
    result = evaluate(observed, GOLD)
    assert _check(result, "replay.evidence_locators")["status"] == "FAIL"


def test_must_not_assert_violation_fails_basis_check():
    """门店总数 must not be restated as net additions."""

    observed = good_observed()
    for claim in observed["claims"]:
        if "门店总数" in claim["text"]:
            claim["text"] = "净新增门店7,504家。"
    result = evaluate(observed, GOLD)
    assert _check(result, "basis.f-stores-total")["status"] == "FAIL"


def test_negation_flipped_to_positive_fails():
    observed = good_observed()
    for claim in observed["claims"]:
        if "不生产VC" in claim["text"]:
            claim["text"] = "公司生产VC并与提问方合作。"
            claim["modality"] = "actual"
    result = evaluate(observed, GOLD)
    assert _check(result, "basis.f-no-vc")["status"] == "FAIL"


def test_question_premise_promoted_to_company_fact_fails():
    observed = good_observed()
    observed["claims"].append(
        {
            "text": "公司与提问方就VC开展合作。",
            "evidence_locators": ["loc:v1/page:3/paragraph:12"],
            "role": "analyst_question",
            "modality": "question",
            "quantities": [],
        }
    )
    result = evaluate(observed, GOLD)
    assert _check(result, "basis.f-no-vc")["status"] == "FAIL"


def test_unit_error_wan_to_yi_fails_quantity_check():
    observed = good_observed()
    for claim in observed["claims"]:
        for quantity in claim["quantities"]:
            if quantity.get("value") == 28000:
                quantity["value"] = 280000000
                quantity["unit"] = "元"
    result = evaluate(observed, GOLD)
    assert _check(result, "basis.f-project-capex")["status"] == "FAIL"


def test_investment_restated_as_revenue_fails_quantity_basis():
    observed = good_observed()
    for claim in observed["claims"]:
        for quantity in claim["quantities"]:
            if quantity.get("value") == 28000:
                quantity["basis"] = "period_flow"
    result = evaluate(observed, GOLD)
    assert _check(result, "basis.f-project-capex")["status"] == "FAIL"


# ---------------------------------------------------------------------------
# bilingual redundancy / derived space
# ---------------------------------------------------------------------------


def test_bilingual_duplicate_summary_fails():
    observed = good_observed()
    observed["claims"].append(
        {
            "text": "门店总数7,504家。",
            "evidence_locators": ["loc:v1/page:14/paragraph:5"],
            "role": "company_filing",
            "modality": "actual",
            "quantities": [{"value": 7504, "unit": "家", "basis": "total"}],
            "language": "zh",
        }
    )
    result = evaluate(observed, GOLD)
    assert _check(result, "bilingual.duplicate_summary")["status"] == "FAIL"


def test_derived_space_over_budget_fails():
    observed = good_observed()
    observed["metrics"] = dict(observed["metrics"], derived_bytes=300 * 1024)
    result = evaluate(observed, GOLD, limits={"max_derived_bytes": 200 * 1024})
    assert _check(result, "derived_space.budget")["status"] == "FAIL"


# ---------------------------------------------------------------------------
# honesty
# ---------------------------------------------------------------------------


def test_entailment_is_not_evaluated_without_independent_review():
    result = evaluate(good_observed(), GOLD)
    assert _check(result, "semantics.entailment")["status"] == "NOT_EVALUATED"
    assert any(row["check_id"] == "semantics.entailment" for row in result["not_evaluated"])
    assert result["spot_read_list"]


def test_sha_mismatch_is_unavailable_not_fail():
    observed = good_observed()
    observed["source_sha256"] = "b" * 64
    result = evaluate(observed, GOLD)
    assert _status(result) == "UNAVAILABLE"
    assert _check(result, "integrity.source_identity")["status"] == "UNAVAILABLE"


def test_coverage_complete_alone_does_not_pass():
    """coverage_complete must never substitute for business recall."""

    observed = good_observed()
    observed["claims"] = []
    observed["selected_text"] = ""
    observed["coverage"]["complete"] = True
    result = evaluate(observed, GOLD)
    assert _status(result) == "FAIL"
    assert result["metrics"]["critical_fact_recall"] < 1.0
