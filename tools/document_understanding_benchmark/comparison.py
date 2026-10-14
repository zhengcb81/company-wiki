"""Compare two benchmark runs under a frozen suite, or refuse to.

A quality comparison is only meaningful when the two runs measured the same
thing. This module makes that condition explicit and mechanical: it compares the
source identity, the read scope, the assembly budget and the gold denominator,
and answers ``INCOMPARABLE`` when any of them differ. Nothing here "adjusts for"
a difference, because the adjustment is how a shrunken denominator gets reported
as an improvement.

The frozen suite is the caller's declaration of what the comparison is over. It
is verified, not trusted:

* a sample in the suite that one side did not measure is ``INCOMPARABLE``;
* a gold denominator that changed is ``INCOMPARABLE``, and the direction is
  reported so a removal is visible rather than merely disallowed;
* a fact that moved from ``FAIL`` to ``NOT_EVALUATED`` is named in
  ``moved_to_not_evaluated`` — the overall ratio may rise while a real gap is
  being hidden, and a reader must be able to see it.

The four statuses are the card's: ``PASS``, ``FAIL``, ``PARTIAL``,
``INCOMPARABLE``. ``PARTIAL`` exists for "comparable and not worse, but a
dimension is unmeasured" — typically ``semantics.entailment`` without an
independent review. It is never upgraded to ``PASS``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

COMPARISON_SCHEMA_VERSION = "du-quality-comparison/1"
FROZEN_SUITE_SCHEMA_VERSION = "du-frozen-suite/1"

PASS = "PASS"
FAIL = "FAIL"
PARTIAL = "PARTIAL"
INCOMPARABLE = "INCOMPARABLE"

_STATUS_RANK = {"PASS": 0, "NOT_EVALUATED": 0, "PARTIAL": 1, "UNAVAILABLE": 1, "FAIL": 2}


class ComparisonError(ValueError):
    """The comparison inputs are structurally wrong (a refused run)."""


def _require_mapping(value: Any, what: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ComparisonError(f"{what} must be a mapping")
    return value


def _require_sequence(value: Any, what: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ComparisonError(f"{what} must be an array")
    return value


def _runs(side: Mapping[str, Any], what: str) -> dict[str, Mapping[str, Any]]:
    block = _require_mapping(side, what)
    rows = _require_sequence(block.get("runs", ()), f"{what}.runs")
    table: dict[str, Mapping[str, Any]] = {}
    for index, raw in enumerate(rows):
        run = _require_mapping(raw, f"{what}.runs[{index}]")
        sample_id = run.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise ComparisonError(f"{what}.runs[{index}].sample_id must be a non-empty string")
        if sample_id in table:
            raise ComparisonError(f"{what} measures {sample_id} more than once")
        table[sample_id] = run
    return table


def _suite_samples(suite: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    block = _require_mapping(suite, "frozen_suite")
    if block.get("schema_version") != FROZEN_SUITE_SCHEMA_VERSION:
        raise ComparisonError(
            f"frozen_suite.schema_version must be {FROZEN_SUITE_SCHEMA_VERSION}"
        )
    table: dict[str, Mapping[str, Any]] = {}
    for index, raw in enumerate(_require_sequence(block.get("samples"), "frozen_suite.samples")):
        sample = _require_mapping(raw, f"frozen_suite.samples[{index}]")
        sample_id = sample.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise ComparisonError(
                f"frozen_suite.samples[{index}].sample_id must be a non-empty string"
            )
        if sample_id in table:
            raise ComparisonError(f"frozen_suite repeats {sample_id}")
        table[sample_id] = sample
    if not table:
        raise ComparisonError("frozen_suite declares no samples")
    return table


def _metrics(run: Mapping[str, Any]) -> Mapping[str, Any]:
    return _require_mapping(run.get("metrics") or {}, "run.metrics")


def _pass_count(run: Mapping[str, Any]) -> int:
    metrics = _metrics(run)
    explicit = metrics.get("critical_fact_pass_count")
    if type(explicit) is int:
        return explicit
    recall = metrics.get("critical_fact_recall")
    denominator = metrics.get("critical_fact_recall_denominator") or 0
    if recall is None or not denominator:
        return 0
    return int(round(float(recall) * denominator))


def _check_statuses(run: Mapping[str, Any]) -> dict[str, str]:
    return {
        str(row.get("check_id")): str(row.get("status"))
        for row in (run.get("checks") or ())
        if isinstance(row, Mapping)
    }


def _not_evaluated_ids(run: Mapping[str, Any]) -> set[str]:
    ids = set()
    for row in run.get("not_evaluated") or ():
        if isinstance(row, Mapping) and row.get("check_id"):
            ids.add(str(row["check_id"]))
    for check_id, status in _check_statuses(run).items():
        if status == "NOT_EVALUATED":
            ids.add(check_id)
    return ids


def _unmeasured(run: Mapping[str, Any]) -> list[str]:
    """Dimensions this run could not measure, from its checks and status.

    An empty ``not_evaluated`` list with a ``PARTIAL`` status is not "everything
    measured": it means the grader degraded for a reason it recorded in
    ``metrics``/``dimensions`` rather than as a check row. Both shapes are
    reported, so a caller cannot read an unmeasured dimension as a pass.
    """

    rows = {f"check:{check_id}" for check_id in _not_evaluated_ids(run)}
    if run.get("status") == "PARTIAL":
        rows.add("overall:PARTIAL")
    if not (run.get("review") or {}).get("supplied"):
        rows.add("dimension:semantics.entailment")
    return sorted(rows)


def compare_runs(
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    frozen_suite: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare two runs over one frozen suite.

    ``baseline``/``candidate`` are mappings with a ``runs`` array of
    ``du-evaluation/1`` results, plus the optional ``read_scope`` and ``budget``
    each side actually ran with. ``frozen_suite`` declares the sample set, its
    source SHA, read scope, budget and gold.

    Returns ``schema_version=du-quality-comparison/1`` with a per-sample row and
    an overall ``PASS``/``FAIL``/``PARTIAL``/``INCOMPARABLE`` status. An input is
    never mutated.
    """

    suite = _require_mapping(frozen_suite, "frozen_suite")
    suite_samples = _suite_samples(suite)
    baseline_runs = _runs(baseline, "baseline")
    candidate_runs = _runs(candidate, "candidate")
    baseline_block = _require_mapping(baseline, "baseline")
    candidate_block = _require_mapping(candidate, "candidate")

    baseline_scope = baseline_block.get("read_scope")
    candidate_scope = candidate_block.get("read_scope")
    baseline_budget = baseline_block.get("budget")
    candidate_budget = candidate_block.get("budget")

    rows: list[dict[str, Any]] = []
    for sample_id, sample in suite_samples.items():
        rows.append(
            _compare_sample(
                sample_id,
                sample,
                baseline_runs.get(sample_id),
                candidate_runs.get(sample_id),
                baseline_scope=baseline_scope,
                candidate_scope=candidate_scope,
                baseline_budget=baseline_budget,
                candidate_budget=candidate_budget,
            )
        )

    extra = sorted((set(baseline_runs) | set(candidate_runs)) - set(suite_samples))
    overall = _overall(rows)
    return {
        "schema_version": COMPARISON_SCHEMA_VERSION,
        "suite_id": suite.get("suite_id"),
        "status": overall,
        "samples": rows,
        "samples_total": len(rows),
        "samples_comparable": sum(1 for row in rows if row["comparable"]),
        "samples_incomparable": sum(1 for row in rows if not row["comparable"]),
        "samples_outside_suite": extra,
        "note": (
            "Only same-source, same-scope, same-budget, same-gold comparisons are "
            "scored. Denominators are never resized to produce an improvement."
        ),
    }


def _compare_sample(
    sample_id: str,
    sample: Mapping[str, Any],
    baseline: Mapping[str, Any] | None,
    candidate: Mapping[str, Any] | None,
    *,
    baseline_scope: Any,
    candidate_scope: Any,
    baseline_budget: Any,
    candidate_budget: Any,
) -> dict[str, Any]:
    reasons: list[str] = []
    row_unverified_gold: list[str] = []
    gold = _require_mapping(sample.get("gold") or {}, f"suite sample {sample_id}.gold")
    suite_facts = gold.get("facts")

    if baseline is None:
        reasons.append(f"sample {sample_id} has no baseline run")
    if candidate is None:
        reasons.append(f"sample {sample_id} has no candidate run")

    if baseline is not None and candidate is not None:
        baseline_sha = baseline.get("source_sha256")
        candidate_sha = candidate.get("source_sha256")
        suite_sha = sample.get("source_sha256")
        if baseline_sha != candidate_sha:
            reasons.append(
                f"source differs: baseline {baseline_sha} vs candidate {candidate_sha}"
            )
        if suite_sha is not None and baseline_sha != suite_sha:
            reasons.append(
                f"baseline source {baseline_sha} is not the frozen suite source {suite_sha}"
            )
        if suite_sha is not None and candidate_sha != suite_sha:
            reasons.append(
                f"candidate source {candidate_sha} is not the frozen suite source {suite_sha}"
            )

        # The gold denominator is FROZEN. Both the *declared* count and the
        # *effective* evaluable count must match across the two runs and equal the
        # frozen suite's gold facts. Moving a fact out of the denominator (a FAIL
        # relabelled NOT_EVALUATED, or coverage quietly dropped) is the exact
        # "shrink the denominator to fake an improvement" abuse, so it is never
        # scored as a quality change.
        def _denominators(run: Mapping[str, Any]) -> tuple[Any, Any]:
            m = _metrics(run)
            declared = m.get("critical_fact_recall_denominator_declared")
            if declared is None:
                declared = m.get("critical_fact_recall_denominator")
            effective = m.get("critical_fact_recall_denominator")
            return declared, effective

        base_declared, base_effective = _denominators(baseline)
        cand_declared, cand_effective = _denominators(candidate)
        if base_declared != cand_declared:
            reasons.append(
                f"declared gold denominator changed: {base_declared} -> {cand_declared}; "
                "a changed denominator is not a quality change"
            )
        if base_effective != cand_effective:
            direction = (
                "shrunk" if (cand_effective or 0) < (base_effective or 0) else "grew"
            )
            reasons.append(
                f"effective gold denominator {direction}: {base_effective} -> "
                f"{cand_effective}; facts left the evaluable denominator"
            )
        if type(suite_facts) is int:
            for label, declared in (("baseline", base_declared), ("candidate", cand_declared)):
                if type(declared) is int and declared != suite_facts:
                    reasons.append(
                        f"{label} was measured on {declared} declared facts, not the frozen "
                        f"suite's {suite_facts} gold facts"
                    )

    if baseline_scope != candidate_scope:
        reasons.append(
            f"read scope differs: baseline {baseline_scope!r} vs candidate {candidate_scope!r}"
        )
    if baseline_budget != candidate_budget:
        reasons.append(
            f"assembly budget differs: baseline {baseline_budget!r} vs "
            f"candidate {candidate_budget!r}"
        )

    declared_digest = gold.get("digest")
    if declared_digest is not None:
        for label, run in (("baseline", baseline), ("candidate", candidate)):
            if run is None:
                continue
            actual = run.get("gold_digest")
            # Only a *declared* mismatch is disqualifying. A run that does not
            # attest its gold is recorded as unverified rather than silently
            # assumed to match, but it is not an outright incomparability: the
            # denominator check above is the load-bearing guard against a
            # swapped gold, and this catches the explicit lie.
            if actual is not None and actual != declared_digest:
                reasons.append(
                    f"{label} was scored against gold {actual}, not the frozen "
                    f"suite gold {declared_digest}"
                )
            elif actual is None:
                row_unverified_gold.append(label)

    comparable = not reasons
    row: dict[str, Any] = {
        "sample_id": sample_id,
        "comparable": comparable,
        "incomparable_reasons": reasons,
        "baseline": _side(baseline),
        "candidate": _side(candidate),
        "delta": {},
        "notes": [],
        "unmeasured": [],
        "moved_to_not_evaluated": [],
        "weakened_gold": False,
        "unverified_gold": list(row_unverified_gold),
        "thresholds": dict(gold.get("thresholds") or {}),
    }

    # Diagnostics are computed even for an incomparable row: a reader must see
    # that a fact was moved to NOT_EVALUATED, that gold is unverified, or that
    # checks regressed, even when the pair is not scored.
    if baseline is not None and candidate is not None:
        baseline_metrics = _metrics(baseline)
        candidate_metrics = _metrics(candidate)
        baseline_recall = baseline_metrics.get("critical_fact_recall")
        candidate_recall = candidate_metrics.get("critical_fact_recall")
        row["delta"] = {
            "critical_fact_recall": (
                None if baseline_recall is None or candidate_recall is None
                else float(candidate_recall) - float(baseline_recall)
            ),
            "critical_fact_pass_count": _pass_count(candidate) - _pass_count(baseline),
            "denominator": (
                (candidate_metrics.get("critical_fact_recall_denominator") or 0)
                - (baseline_metrics.get("critical_fact_recall_denominator") or 0)
            ),
            "selected_span_count": (
                (candidate_metrics.get("selected_span_count") or 0)
                - (baseline_metrics.get("selected_span_count") or 0)
            ),
        }

        baseline_checks = _check_statuses(baseline)
        candidate_checks = _check_statuses(candidate)
        candidate_ne = _not_evaluated_ids(candidate)
        baseline_ne = _not_evaluated_ids(baseline)
        moved = sorted(
            check_id for check_id in candidate_ne - baseline_ne
            if baseline_checks.get(check_id) in {"FAIL", "PARTIAL"}
        )
        row["moved_to_not_evaluated"] = moved
        row["weakened_gold"] = bool(moved)
        row["unmeasured"] = _unmeasured(candidate)
        row["newly_adverse_checks"] = sorted(
            check_id for check_id, status in candidate_checks.items()
            if _STATUS_RANK.get(status, 0) > _STATUS_RANK.get(baseline_checks.get(check_id, "NOT_EVALUATED"), 0)
        )

        thresholds = row["thresholds"]
        recall_threshold = thresholds.get("critical_fact_recall")
        if recall_threshold is not None and candidate_recall is not None:
            if float(candidate_recall) < float(recall_threshold):
                row["notes"].append(
                    f"critical_fact_recall {float(candidate_recall):.3f} is below the frozen "
                    f"threshold {recall_threshold}"
                )
        if candidate.get("status") == "FAIL" and baseline.get("status") == "FAIL":
            row["notes"].append("both sides FAIL; an unchanged failure is not a pass")

    if not comparable:
        row["outcome"] = INCOMPARABLE
        return row

    assert baseline is not None and candidate is not None
    row["outcome"] = _sample_outcome(baseline, candidate, row)
    return row


def _side(run: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if run is None:
        return None
    metrics = _metrics(run)
    return {
        "status": run.get("status"),
        "critical_fact_recall": metrics.get("critical_fact_recall"),
        "critical_fact_pass_count": _pass_count(run),
        "denominator": metrics.get("critical_fact_recall_denominator"),
        "selected_span_count": metrics.get("selected_span_count"),
    }


def _sample_outcome(
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
    row: Mapping[str, Any],
) -> str:
    thresholds = row.get("thresholds") or {}
    recall_threshold = thresholds.get("critical_fact_recall")
    candidate_metrics = _metrics(candidate)
    candidate_recall = candidate_metrics.get("critical_fact_recall")
    delta_recall = (row.get("delta") or {}).get("critical_fact_recall")

    # Moving an evaluated gap into NOT_EVALUATED is the candidate hiding a known
    # failure to shrink the denominator. That is a defect in its own right and can
    # never read as an improvement, whatever the ratio says.
    if row.get("moved_to_not_evaluated"):
        return FAIL
    # A candidate that introduced an adverse check, or is still a hard FAIL, has
    # not improved anything whatever its ratio says.
    if row.get("newly_adverse_checks") or candidate.get("status") == FAIL:
        return FAIL
    # A regression on the same denominator is a real loss, not a wash.
    if delta_recall is not None and delta_recall < 0:
        return FAIL
    if recall_threshold is not None and candidate_recall is not None:
        if float(candidate_recall) < float(recall_threshold):
            return FAIL
    # Comparable and not worse, but unverified: the gold identity was not
    # attested, or the summary's semantics are unmeasured without an independent
    # review. Without a real model the benchmark must not emit a summary-fidelity
    # PASS, so this is PARTIAL and never an unqualified PASS.
    if row.get("unverified_gold") or row.get("unmeasured"):
        return PARTIAL
    if candidate.get("status") == PARTIAL:
        return PARTIAL
    return PASS


def _overall(rows: Sequence[Mapping[str, Any]]) -> str:
    if any(not row["comparable"] for row in rows):
        return INCOMPARABLE
    if any(row.get("outcome") == FAIL for row in rows):
        return FAIL
    if any(row.get("outcome") == PARTIAL for row in rows):
        return PARTIAL
    return PASS


__all__ = [
    "COMPARISON_SCHEMA_VERSION",
    "ComparisonError",
    "FAIL",
    "FROZEN_SUITE_SCHEMA_VERSION",
    "INCOMPARABLE",
    "PASS",
    "PARTIAL",
    "compare_runs",
]
