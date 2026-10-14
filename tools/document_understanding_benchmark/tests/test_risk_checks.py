"""§3 full-chain risk checks: one counterexample per named failure mode.

The DU3-QUALITY card lists the defects the benchmark must be able to catch:
dropped negation / stage / period / unit, currency and magnitude errors,
question-or-editorial wording restated as management fact, cross-subject and
parent-source packaging, shared-body duplication, bad aliases, unread reported
as ``no_value``, and a shrunken denominator or inflated budget faking an
improvement.

The assembly-level ones (bad alias, cross-subject, shared body, unread-as-absence)
live in ``test_final_material``; the comparison-level ones (denominator, budget)
live in ``test_paired_comparison``. This module proves the *claim-level* checks
fire deterministically, so each named risk has an explicit, executable
counterexample and none is left to a hand-wave.
"""

from __future__ import annotations

import pytest

from tools.document_understanding_benchmark.checkers import (
    check_basis_fact,
    check_quantity_provenance,
)


def _fact(**overrides):
    fact = {
        "id": "f-x",
        "importance": "critical",
        "target_kind": "required_business",
        "quantity_basis": "investment",
        "modality": "actual",
        "role": "company_filing",
        "any_support_sets": [[{"page": 62, "exact_quote": "本项目总投资为28,000万元"}]],
        "must_preserve": ["总投资", "28000"],
        "must_not_assert": [],
    }
    fact.update(overrides)
    return fact


def _observed(*, claim_text="本项目总投资为28,000万元。",
              role="company_filing", modality="actual",
              quantities=None, source_text="本项目总投资为28,000万元。",
              source_role="company_filing", page=62):
    quantities = quantities if quantities is not None else [
        {"value": 28000, "unit": "万元", "period": "2020", "basis": "investment"}
    ]
    locator = f"loc:v1/page:{page}/table:2/row:1"
    return {
        "schema_version": "du-observed/1",
        "sample_id": "s",
        "source_sha256": "1" * 64,
        "selected_locators": [locator],
        "selected_evidence": [
            {"locator": locator, "page": page,
             "text": source_text, "source_role": source_role}
        ],
        "selected_text": source_text,
        "claims": [
            {"text": claim_text, "evidence_locators": [locator],
             "role": role, "modality": modality, "quantities": quantities}
        ],
        "semantic_units": [],
        "coverage": {"native_scan": "complete", "complete": True},
        "metrics": {},
        "execution": {"calls": 0},
    }


def _problems(result):
    return result["observed"] if result["status"] == "FAIL" else []


def _gold(*facts):
    return {
        "schema_version": "du-gold/1",
        "sample_id": "s",
        "source_sha256": "1" * 64,
        "scope": "development",
        "expected_route_families": ["offering"],
        "facts": list(facts),
    }


# ---------------------------------------------------------------------------
# currency / magnitude
# ---------------------------------------------------------------------------


def test_currency_mismatch_against_evidence_is_a_basis_failure():
    fact = _fact()
    claim_quantities = [
        {"value": 28000, "unit": "万元", "currency": "USD", "period": "2020",
         "basis": "investment"}
    ]
    result = check_basis_fact(fact, _observed(quantities=claim_quantities))
    assert result["status"] == "FAIL"
    assert any("currency_mismatch" in problem for problem in _problems(result))


def test_matching_currency_is_not_flagged():
    fact = _fact()
    claim_quantities = [
        {"value": 28000, "unit": "万元", "currency": "CNY", "period": "2020",
         "basis": "investment"}
    ]
    result = check_basis_fact(fact, _observed(quantities=claim_quantities))
    assert result["status"] == "PASS"


def test_magnitude_rescale_万元_to_亿元_is_caught_by_the_unit_check():
    fact = _fact(must_preserve=["总投资", "28000", "万元"])
    claim_quantities = [
        {"value": 2.8, "unit": "亿元", "period": "2020", "basis": "investment"}
    ]
    result = check_basis_fact(
        fact,
        _observed(claim_text="本项目总投资为2.8亿元。",
                  quantities=claim_quantities, source_text="本项目总投资为28,000万元。"),
    )
    assert result["status"] == "FAIL"


# ---------------------------------------------------------------------------
# question / editorial wording as management fact
# ---------------------------------------------------------------------------


def test_editorial_voice_re_voiced_as_management_fact_is_caught():
    fact = _fact(role="editorial_summary")
    result = check_basis_fact(
        fact, _observed(role="management_answer", modality="actual")
    )
    assert result["status"] == "FAIL"
    assert any("noncompany_voice_carried_as_management_fact" in problem
               for problem in _problems(result))


def test_third_party_voice_re_voiced_as_company_fact_is_caught():
    fact = _fact(role="third_party")
    result = check_basis_fact(fact, _observed(role="company_statement", modality="plan"))
    assert result["status"] == "FAIL"


def test_company_fact_kept_in_company_voice_is_not_flagged():
    fact = _fact(role="company_filing")
    assert check_basis_fact(fact, _observed())["status"] == "PASS"


# ---------------------------------------------------------------------------
# negation / stage / period / unit
# ---------------------------------------------------------------------------


def test_dropped_negation_is_a_basis_failure():
    fact = _fact(
        modality="negation",
        role="management_answer",
        any_support_sets=[[{"page": 3, "exact_quote": "公司现无生产VC"}]],
        must_preserve=["无生产VC"],
    )
    observed = _observed(
        claim_text="公司已生产VC。", modality="actual", role="management_answer",
        source_text="公司现无生产VC", page=3,
    )
    result = check_basis_fact(fact, observed)
    assert result["status"] == "FAIL"


def test_stage_collapse_verification_to_mass_production_is_caught():
    fact = _fact(
        modality="actual",
        any_support_sets=[[{"page": 3, "exact_quote": "已进入量产验证阶段"}]],
        must_preserve=["量产验证阶段"],
        quantity_basis="unknown",
        must_not_assert=["已实现量产"],
    )
    result = check_basis_fact(
        fact, _observed(claim_text="设备已实现量产。", source_text="已进入量产验证阶段",
                        quantities=[], page=3)
    )
    assert result["status"] == "FAIL"


def test_dropped_period_header_is_a_quantity_provenance_failure():
    observed = _observed(
        quantities=[{"value": 28000, "unit": "万元", "period": None, "basis": "investment"}]
    )
    result = check_quantity_provenance(observed, _fact())
    assert result["status"] == "FAIL"
    assert any(row["missing"] == "period" for row in result["observed"])


def test_dropped_unit_is_a_quantity_provenance_failure():
    observed = _observed(
        quantities=[{"value": 28000, "unit": None, "period": "2020", "basis": "investment"}]
    )
    result = check_quantity_provenance(observed, _fact())
    assert result["status"] == "FAIL"
    assert any(row["missing"] == "unit" for row in result["observed"])


# ---------------------------------------------------------------------------
# every named risk is wired, so nothing in the card's list is unchecked
# ---------------------------------------------------------------------------


def test_every_card_named_risk_has_a_wired_check():
    """The card's §3 risk register maps to a real check id, not just prose.

    This is a *wiring* assertion that the expected dimensions are present in an
    actual ``evaluate``/``compare_runs`` result. Each named risk additionally has
    an executable behaviour counterexample elsewhere in this package:

      negation / stage / period / unit / currency / magnitude  -> this file
      question + editorial as management fact                  -> this file
      cross-subject / parent-source, shared body, bad alias,
        unread-as-no_value                                     -> test_final_material
      shrunk denominator / inflated budget                     -> test_paired_comparison

    So a risk cannot disappear from the report without a behaviour test failing.
    """

    from tools.document_understanding_benchmark.evaluate import evaluate

    result = evaluate(_observed(), _gold(_fact()))
    check_ids = {row["check_id"] for row in result["checks"]}
    # currency / magnitude / question-as-fact / negation / stage -> basis.*
    assert any(cid.startswith("basis.") for cid in check_ids)
    # period / unit / header -> basis.quantity_provenance
    assert "basis.quantity_provenance" in check_ids
    # unread must not read as absence -> coverage / recall gating exists
    assert "coverage.no_false_complete" in check_ids
    # shared body / bilingual duplication
    assert "bilingual.duplicate_summary" in check_ids
    # denominator / budget integrity is checked at comparison time
    from tools.document_understanding_benchmark.comparison import compare_runs

    comparison = compare_runs(
        {"runs": [{"sample_id": "s", "source_sha256": "1" * 64, "gold_digest": "a" * 64,
                   "status": "FAIL", "checks": [], "not_evaluated": [],
                   "metrics": {"critical_fact_recall": 0.0,
                               "critical_fact_recall_denominator": 8,
                               "critical_fact_recall_denominator_declared": 8,
                               "critical_fact_pass_count": 0}}]},
        {"runs": [{"sample_id": "s", "source_sha256": "1" * 64, "gold_digest": "a" * 64,
                   "status": "PASS", "checks": [], "not_evaluated": [],
                   "metrics": {"critical_fact_recall": 1.0,
                               "critical_fact_recall_denominator": 2,
                               "critical_fact_recall_denominator_declared": 2,
                               "critical_fact_pass_count": 2}}]},
        frozen_suite={"schema_version": "du-frozen-suite/1", "suite_id": "r",
                      "samples": [{"sample_id": "s", "source_sha256": "1" * 64,
                                   "read_scope": {}, "budget": {},
                                   "gold": {"facts": 8, "digest": "a" * 64,
                                            "thresholds": {}}}]},
    )
    # A shrunken denominator is INCOMPARABLE, never a clean pass.
    assert comparison["status"] == "INCOMPARABLE"
