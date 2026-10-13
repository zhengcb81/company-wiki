"""Negative controls for the semantic-review layer.

The packaged fixtures contain the *correct* observations, so they cannot show
that the review stage discriminates. This module injects defects that the
deterministic checkers are **blind to by design**, and asserts that:

1. without a review, such a claim is not caught (so the layer is not redundant);
2. with a review calling it NOT_ENTAILED, the run fails;
3. a review can never rescue a defect the deterministic checkers *do* catch.

Point 1 is the reason the review layer exists, and it is stated as a measured
fact rather than an assertion of value.
"""

from __future__ import annotations

import copy
from typing import Any

from .evaluate import evaluate
from .review import REVIEW_SCHEMA_VERSION, validate_review

# Each control is a claim that passes every deterministic check because its
# wording, numbers, unit and locator are all consistent with the gold, yet it
# asserts something the evidence does not carry. Only meaning-level review can
# separate these.
SEMANTIC_ONLY_DEFECTS: tuple[dict[str, Any], ...] = (
    {
        "control_id": "quoting-as-company-view",
        "note": (
            "Attaches an interpretation to a correct number without changing "
            "the number, unit, or basis."
        ),
        "rewrite": lambda claim: {
            **claim,
            "text": claim["text"].rstrip("。") + "，表明公司经营质量显著改善。",
        },
    },
    {
        "control_id": "omitted-qualifier",
        "note": (
            "Keeps the number and basis but drops a qualifier that limited the "
            "statement's scope."
        ),
        "rewrite": lambda claim: {
            **claim,
            "text": claim["text"].replace("截至2024年12月31日，", ""),
        },
    },
    {
        "control_id": "causal-attribution",
        "note": (
            "Adds a cause the evidence never states, leaving all numbers intact."
        ),
        "rewrite": lambda claim: {
            **claim,
            "text": claim["text"].rstrip("。") + "，主要由于海外市场放量。",
        },
    },
)


def _first_claim_index(observed: dict[str, Any], needle: str) -> int | None:
    for index, claim in enumerate(observed.get("claims") or []):
        if needle in (claim.get("text") or ""):
            return index
    return None


def run_review_controls(observed: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    """Measure which injected defects the deterministic layer catches unaided."""

    rows: list[dict[str, Any]] = []
    for control in SEMANTIC_ONLY_DEFECTS:
        index = _first_claim_index(observed, "门店总数")
        if index is None:
            continue
        mutated = copy.deepcopy(observed)
        mutated["claims"][index] = control["rewrite"](mutated["claims"][index])

        # (1) deterministic verdict with no review
        unaided = evaluate(mutated, gold)
        unaided_caught = unaided["status"] == "FAIL"

        # (2) a review that notices the meaning-level defect
        verdicts = ["ENTAILED"] * len(mutated["claims"])
        verdicts[index] = "NOT_ENTAILED"
        review = validate_review(
            {
                "schema_version": REVIEW_SCHEMA_VERSION,
                "sample_id": gold["sample_id"],
                "reviewer": "negative-control",
                "claims": [
                    {"claim_index": i, "verdict": v}
                    for i, v in enumerate(verdicts)
                ],
            }
        )
        reviewed = evaluate(mutated, gold, review=review)
        review_caught = reviewed["status"] == "FAIL"

        rows.append(
            {
                "control_id": control["control_id"],
                "note": control["note"],
                "claim_index": index,
                "mutated_text": mutated["claims"][index]["text"],
                "deterministic_caught": unaided_caught,
                "deterministic_status": unaided["status"],
                "review_caught": review_caught,
                "review_status": reviewed["status"],
            }
        )

    blind = [row["control_id"] for row in rows if not row["deterministic_caught"]]
    return {
        "controls_total": len(rows),
        "deterministic_blind_count": len(blind),
        "deterministic_blind": blind,
        "review_caught_all": all(row["review_caught"] for row in rows),
        "rows": rows,
        "interpretation": (
            "deterministic_blind lists defects no deterministic check catches; "
            "for exactly those, the review layer is the only detector. "
            "review_caught_all shows the review path closes them."
        ),
    }


def run_rescue_controls(observed: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    """A review must never turn a deterministically caught defect into a pass."""

    mutated = copy.deepcopy(observed)
    index = _first_claim_index(mutated, "门店总数")
    results: list[dict[str, Any]] = []
    if index is not None:
        mutated["claims"][index]["text"] = "净新增门店7,504家。"
        for quantity in mutated["claims"][index].get("quantities") or []:
            quantity["basis"] = "incremental"

        unaided = evaluate(mutated, gold)
        review = validate_review(
            {
                "schema_version": REVIEW_SCHEMA_VERSION,
                "sample_id": gold["sample_id"],
                "reviewer": "rescue-attempt",
                "claims": [
                    {"claim_index": i, "verdict": "ENTAILED"}
                    for i in range(len(mutated["claims"]))
                ],
            }
        )
        reviewed = evaluate(mutated, gold, review=review)
        results.append(
            {
                "defect": "total_restated_as_increment",
                "unaided_status": unaided["status"],
                "with_review_status": reviewed["status"],
                "review_cannot_rescue": reviewed["status"] == "FAIL",
            }
        )
    return {
        "controls": results,
        "all_rescues_blocked": all(row["review_cannot_rescue"] for row in results),
        "interpretation": (
            "an all-ENTAILED review cannot upgrade a deterministic FAIL; "
            "the review layer can only add scrutiny, never remove it."
        ),
    }
