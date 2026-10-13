"""Independent semantic review: drive ``semantics.entailment`` past NOT_EVALUATED.

The oracle can prove *absence* and *contradiction* deterministically, but it can
never prove that a sentence is *entailed* by its evidence. That judgement needs a
reviewer. This module is the review side of that contract:

- a review record is plain JSON, one verdict per claim;
- without a review the check stays ``NOT_EVALUATED`` (never a silent PASS);
- with a review, a claim the reviewer did not confirm as entailed fails.

The native baseline currently emits **zero claims**, so there is nothing to
review end to end. The mechanism is therefore exercised against the synthetic
fixtures, and the review-supplied path is what ROOT enables once a real summary
producer is wired in.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REVIEW_SCHEMA_VERSION = "du-review/1"

# Verdicts that mean "the evidence entails the claim as written".
ENTAILED_VERDICTS = frozenset({"ENTAILED", "PASS"})
# Verdicts that mean "the claim is not supported by its evidence".
UNSUPPORTED_VERDICTS = frozenset({"NOT_ENTAILED", "FAIL", "CONTRADICTED", "UNSUPPORTED"})
# Verdicts that mean the reviewer could not decide.
UNDECIDED_VERDICTS = frozenset({"UNCLEAR", "UNDECIDED", "DEFERRED"})


class ReviewError(ValueError):
    """A review record is structurally wrong (a refused run, not a FAIL)."""


def validate_review(review: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one review record."""

    if not isinstance(review, Mapping):
        raise ReviewError("review must be a mapping")
    version = review.get("schema_version")
    if version != REVIEW_SCHEMA_VERSION:
        raise ReviewError(f"review schema_version must be {REVIEW_SCHEMA_VERSION}")
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(review.get("claims") or []):
        if not isinstance(raw, Mapping):
            raise ReviewError(f"review.claims[{index}] must be a mapping")
        verdict = raw.get("verdict")
        if not isinstance(verdict, str) or not verdict:
            raise ReviewError(f"review.claims[{index}].verdict must be a non-empty string")
        rows.append(
            {
                "claim_index": raw.get("claim_index", index),
                "verdict": verdict.upper(),
                "reviewer": raw.get("reviewer"),
                "note": raw.get("note") or "",
                "evidence_locators": list(raw.get("evidence_locators") or []),
            }
        )
    return {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "sample_id": review.get("sample_id"),
        "reviewer": review.get("reviewer"),
        "claims": rows,
    }


def load_review(path: Path) -> dict[str, Any]:
    import json

    try:
        raw = json.loads(Path(path).read_text(encoding="utf8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewError(f"cannot read review {path}: {exc}") from exc
    return validate_review(raw)


def build_review(
    observed: Mapping[str, Any],
    *,
    verdicts: Sequence[str],
    reviewer: str = "independent",
) -> dict[str, Any]:
    """Build a review from an observation and one verdict per claim, in order."""

    claims = list(observed.get("claims") or [])
    if len(verdicts) != len(claims):
        raise ReviewError(
            f"need one verdict per claim: got {len(verdicts)} for {len(claims)} claims"
        )
    return validate_review(
        {
            "schema_version": REVIEW_SCHEMA_VERSION,
            "sample_id": observed.get("sample_id"),
            "reviewer": reviewer,
            "claims": [
                {
                    "claim_index": index,
                    "verdict": verdict,
                    "evidence_locators": list(claim.get("evidence_locators") or []),
                }
                for index, (claim, verdict) in enumerate(zip(claims, verdicts))
            ],
        }
    )


def review_summary(review: Mapping[str, Any] | None) -> dict[str, Any]:
    if not review:
        return {"supplied": False, "claims": 0}
    rows = review.get("claims") or []
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
    return {
        "supplied": True,
        "reviewer": review.get("reviewer"),
        "claims": len(rows),
        "verdicts": dict(sorted(counts.items())),
    }
