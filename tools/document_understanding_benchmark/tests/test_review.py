"""Tests for the independent semantic-review mechanism.

``semantics.entailment`` must never silently PASS. Its four states are
distinct and all covered here:

- no review -> NOT_EVALUATED (the honest default);
- review, all entailed -> PASS;
- review found an unsupported claim -> FAIL;
- review could not decide -> PARTIAL.
"""

from __future__ import annotations

import json

import pytest

from tools.document_understanding_benchmark import evaluate
from tools.document_understanding_benchmark.records import validate_gold, validate_observed
from tools.document_understanding_benchmark.review import (
    REVIEW_SCHEMA_VERSION,
    ReviewError,
    build_review,
    load_review,
    review_summary,
    validate_review,
)
from tools.document_understanding_benchmark.tests.synthetic import GOLD, good_observed


def _check(result: dict, check_id: str) -> dict:
    for row in result["checks"]:
        if row["check_id"] == check_id:
            return row
    raise AssertionError(f"missing {check_id}")


# ---------------------------------------------------------------------------
# without a review
# ---------------------------------------------------------------------------


def test_without_review_entailment_is_not_evaluated():
    result = evaluate(good_observed(), GOLD)
    assert _check(result, "semantics.entailment")["status"] == "NOT_EVALUATED"
    assert result["review"]["supplied"] is False


def test_spot_read_list_is_offered_when_no_review():
    """ROOT needs a review worklist even when no review has happened yet."""

    result = evaluate(good_observed(), GOLD)
    assert result["spot_read_list"], "the independent review list must not be empty"
    row = result["spot_read_list"][0]
    assert row["review_question"]
    assert "claim_text" in row
    assert "evidence_locators" in row


# ---------------------------------------------------------------------------
# with a review
# ---------------------------------------------------------------------------


def _review_with(verdicts):
    return build_review(good_observed(), verdicts=verdicts, reviewer="test-reviewer")


def test_all_entailed_review_passes():
    observed = good_observed()
    verdicts = ["ENTAILED"] * len(observed["claims"])
    result = evaluate(observed, GOLD, review=_review_with(verdicts))
    assert _check(result, "semantics.entailment")["status"] == "PASS"


def test_unsupported_claim_fails_entailment():
    observed = good_observed()
    verdicts = ["ENTAILED"] * len(observed["claims"])
    verdicts[1] = "NOT_ENTAILED"
    result = evaluate(observed, GOLD, review=_review_with(verdicts))
    row = _check(result, "semantics.entailment")
    assert row["status"] == "FAIL"
    assert row["observed"]["unsupported"]
    assert result["status"] == "FAIL"


def test_undecided_claim_is_partial_not_fail():
    """A reviewer being unsure is not evidence that the claim is wrong."""

    observed = good_observed()
    verdicts = ["ENTAILED"] * len(observed["claims"])
    verdicts[0] = "UNCLEAR"
    result = evaluate(observed, GOLD, review=_review_with(verdicts))
    assert _check(result, "semantics.entailment")["status"] == "PARTIAL"


def test_unrecognized_verdict_is_partial_not_pass():
    """An unknown verdict must never be treated as entailed."""

    observed = good_observed()
    verdicts = ["ENTAILED"] * len(observed["claims"])
    verdicts[0] = "PROBABLY_FINE"
    result = evaluate(observed, GOLD, review=_review_with(verdicts))
    row = _check(result, "semantics.entailment")
    assert row["status"] == "PARTIAL"
    assert row["observed"]["unrecognized_verdicts"]


def test_supplied_review_is_reported_in_result():
    observed = good_observed()
    result = evaluate(
        observed, GOLD, review=_review_with(["ENTAILED"] * len(observed["claims"]))
    )
    assert result["review"]["supplied"] is True
    assert result["review"]["reviewer"] == "test-reviewer"
    assert result["metrics"]["review_supplied"] is True


# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------


def test_validate_review_rejects_wrong_schema_version():
    with pytest.raises(ReviewError):
        validate_review({"schema_version": "du-review/9", "claims": []})


def test_validate_review_rejects_claim_without_verdict():
    with pytest.raises(ReviewError):
        validate_review(
            {"schema_version": REVIEW_SCHEMA_VERSION, "claims": [{"claim_index": 0}]}
        )


def test_build_review_requires_one_verdict_per_claim():
    observed = good_observed()
    with pytest.raises(ReviewError):
        build_review(observed, verdicts=["ENTAILED"])


def test_review_round_trips_through_disk(tmp_path):
    observed = good_observed()
    review = _review_with(["ENTAILED"] * len(observed["claims"]))
    path = tmp_path / "review.json"
    path.write_text(json.dumps(review, ensure_ascii=False), encoding="utf8")
    loaded = load_review(path)
    assert loaded["schema_version"] == REVIEW_SCHEMA_VERSION
    assert len(loaded["claims"]) == len(observed["claims"])


def test_load_review_refuses_a_missing_file(tmp_path):
    with pytest.raises(ReviewError):
        load_review(tmp_path / "nope.json")


def test_review_summary_counts_verdicts():
    summary = review_summary(
        validate_review(
            {
                "schema_version": REVIEW_SCHEMA_VERSION,
                "claims": [
                    {"verdict": "ENTAILED"},
                    {"verdict": "ENTAILED"},
                    {"verdict": "NOT_ENTAILED"},
                ],
            }
        )
    )
    assert summary["claims"] == 3
    assert summary["verdicts"] == {"ENTAILED": 2, "NOT_ENTAILED": 1}


def test_review_summary_of_none_is_unsupplied():
    assert review_summary(None)["supplied"] is False


# ---------------------------------------------------------------------------
# the review mechanism must not change deterministic verdicts
# ---------------------------------------------------------------------------


def test_review_cannot_turn_a_missing_fact_into_a_pass():
    """A reviewer cannot substitute for measurement."""

    observed = good_observed()
    observed["claims"] = [c for c in observed["claims"] if "不生产VC" not in c["text"]]
    observed["selected_text"] = observed["selected_text"].replace("公司不生产VC。", "")
    result = evaluate(
        observed,
        GOLD,
        review=build_review(observed, verdicts=["ENTAILED"] * len(observed["claims"])),
    )
    assert _check(result, "recall.f-no-vc")["status"] == "FAIL"
    assert result["status"] == "FAIL"


def test_review_does_not_excuse_a_source_mismatch():
    observed = good_observed()
    observed["source_sha256"] = "b" * 64
    result = evaluate(
        observed,
        GOLD,
        review=build_review(observed, verdicts=["ENTAILED"] * len(observed["claims"])),
    )
    assert result["status"] == "UNAVAILABLE"


def test_gold_and_observed_still_validate_with_review_present():
    observed = good_observed()
    validate_gold(GOLD)
    validate_observed(observed)
    evaluate(observed, GOLD, review=_review_with(["ENTAILED"] * len(observed["claims"])))
