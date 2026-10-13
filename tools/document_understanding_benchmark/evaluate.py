"""Public ``evaluate(observed, gold)`` entry point (INTERFACES.md §5).

Overall status rules:

- ``UNAVAILABLE`` when the observation cannot be tied to the gold source, so
  nothing about quality is provable.
- ``FAIL`` when any check fails.
- ``PARTIAL`` when nothing failed but recall is incomplete or checks are
  unavailable.
- ``PASS`` only when nothing failed, nothing important is unavailable, and all
  critical facts were recalled.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from . import checkers
from .records import validate_gold, validate_observed
from .review import review_summary
from .schema import (
    DOCUMENT_META,
    EVALUATION_SCHEMA_VERSION,
    FAIL,
    NARRATIVE,
    NOT_EVALUATED,
    PASS,
    PARTIAL,
    UNAVAILABLE,
)


def _overall(checks: list[dict[str, Any]], metrics: Mapping[str, Any]) -> str:
    """Derive the overall status.

    ``NOT_EVALUATED`` on the semantic-entailment check is the *expected* state
    for an unaudited run and must not, by itself, downgrade a healthy result:
    the card requires honest ``NOT_EVALUATED`` reporting, not a permanently
    PARTIAL benchmark. Unavailability of anything the benchmark claims to
    measure (source identity, recall, route, replay) still downgrades.
    """

    if any(
        row["check_id"] == "integrity.source_identity" and row["status"] == UNAVAILABLE
        for row in checks
    ):
        return UNAVAILABLE
    statuses = {row["check_id"]: row["status"] for row in checks}
    if FAIL in statuses.values():
        return FAIL
    meaningfully_unavailable = any(
        status == UNAVAILABLE and check_id != "semantics.entailment"
        for check_id, status in statuses.items()
    )
    if meaningfully_unavailable:
        return PARTIAL
    if metrics.get("critical_fact_recall") not in (None, 1.0):
        return PARTIAL
    return PASS


def evaluate(
    observed: Mapping[str, Any],
    gold: Mapping[str, Any],
    *,
    limits: Mapping[str, Any] | None = None,
    review: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare one observation against independently authored gold."""

    effective_limits = dict(checkers.DEFAULT_LIMITS)
    if limits:
        effective_limits.update(limits)

    checked_gold = validate_gold(gold)
    checked_observed = validate_observed(observed)

    checks: list[dict[str, Any]] = [
        checkers.check_source_identity(checked_observed, checked_gold),
        checkers.check_route(checked_observed, checked_gold),
        checkers.check_text_legibility(checked_observed, checked_gold),
    ]

    facts = checkers.collect_recall_facts(checked_gold)
    recall_rows = [checkers.check_recall_fact(fact, checked_observed) for fact in facts]
    checks.extend(recall_rows)
    checks.extend(checkers.check_basis_fact(fact, checked_observed) for fact in facts)

    checks.append(checkers.check_replay(checked_observed, checked_gold))
    checks.append(checkers.check_unsupported_claims(checked_observed, checked_gold))
    checks.append(checkers.check_context(checked_observed, checked_gold))
    checks.append(checkers.check_coverage_honesty(checked_observed, checked_gold))
    checks.append(checkers.check_quantity_provenance(checked_observed, checked_gold))
    checks.append(checkers.check_bilingual(checked_observed, checked_gold))
    checks.append(checkers.check_derived_space(checked_observed, checked_gold, effective_limits))
    checks.append(checkers.check_resource(checked_observed, checked_gold, effective_limits))
    checks.append(checkers.check_semantics_entailment(checked_observed, checked_gold, review))

    critical_rows = [
        row for row, fact in zip(recall_rows, facts) if checkers.is_critical(fact)
    ]
    critical_pass = sum(1 for row in critical_rows if row["status"] == PASS)
    critical_declared = len(critical_rows)
    critical_unavailable = sum(1 for row in critical_rows if row["status"] == UNAVAILABLE)
    # UNAVAILABLE means "could not be read", not "was searched and not found".
    # It must therefore leave the denominator, exactly as it does for
    # fact_recall below; otherwise an unreadable document is reported as a
    # recall of 0.000, which reads as a total miss rather than a gap in
    # coverage. Unavailable facts are reported in their own counter, and the
    # overall status still degrades to PARTIAL, so nothing is excused by this.
    critical_total = critical_declared - critical_unavailable
    all_pass = sum(1 for row in recall_rows if row["status"] == PASS)
    effective_total = len(recall_rows) - sum(1 for row in recall_rows if row["status"] == UNAVAILABLE)
    # Narrative facts are what the evidence selection is answerable for;
    # document_meta facts belong to a front-end/metadata layer. Reported apart
    # so neither denominator is read as the other's score.
    narrative_rows = [
        (row, fact)
        for row, fact in zip(recall_rows, facts)
        if (fact.get("fact_scope") or NARRATIVE) == NARRATIVE
    ]
    meta_rows = [
        (row, fact)
        for row, fact in zip(recall_rows, facts)
        if (fact.get("fact_scope") or NARRATIVE) == DOCUMENT_META
    ]

    def _scope_recall(pairs):
        evaluable = [
            row for row, _fact in pairs if row["status"] != UNAVAILABLE
        ]
        passed = sum(1 for row in evaluable if row["status"] == PASS)
        return {
            "passed": passed,
            "total": len(evaluable),
            "declared": len(pairs),
            "unavailable": sum(1 for row, _f in pairs if row["status"] == UNAVAILABLE),
            "recall": (passed / len(evaluable)) if evaluable else None,
        }

    narrative_stats = _scope_recall(narrative_rows)
    meta_stats = _scope_recall(meta_rows)
    evidence_rows = [row for row in checks if row["check_id"] in {"replay.evidence_locators", "integrity.unsupported_claims"}]
    evidence_ok = sum(1 for row in evidence_rows if row["status"] == PASS)

    metrics = {
        "critical_fact_recall": (critical_pass / critical_total) if critical_total else None,
        "critical_fact_recall_denominator": critical_total,
        "critical_fact_recall_denominator_declared": critical_declared,
        "critical_fact_unavailable": critical_unavailable,
        "critical_fact_coverage": (
            critical_total / critical_declared if critical_declared else None
        ),
        "narrative_fact_recall": narrative_stats["recall"],
        "narrative_facts_passed": narrative_stats["passed"],
        "narrative_facts_total": narrative_stats["total"],
        "document_meta_fact_recall": meta_stats["recall"],
        "document_meta_facts_passed": meta_stats["passed"],
        "document_meta_facts_total": meta_stats["total"],
        "fact_recall": (all_pass / effective_total) if effective_total else None,
        "fact_recall_denominator": effective_total,
        "fact_recall_denominator_declared": len(recall_rows),
        "route_accuracy": (
            1.0 if any(row["check_id"] == "route.family" and row["status"] == PASS for row in checks)
            else (0.0 if any(row["check_id"] == "route.family" and row["status"] == FAIL for row in checks) else None)
        ),
        "evidence_validity": (evidence_ok / len(evidence_rows)) if evidence_rows else None,
        "basis_pass_rate": (
            sum(1 for row in checks if row["check_id"].startswith("basis.") and row["status"] == PASS)
            / max(1, sum(1 for row in checks if row["check_id"].startswith("basis.")))
        ),
        "context_completeness": next(
            (1.0 if row["status"] == PASS else 0.0 for row in checks if row["check_id"] == "context.semantic_units"),
            None,
        ),
        "selected_span_count": len(checked_observed.get("selected_locators") or []),
        "claim_count": len(checked_observed.get("claims") or []),
        "semantic_unit_count": len(checked_observed.get("semantic_units") or []),
        "review_supplied": bool(review),
        "reviewed_claims": len((review or {}).get("claims") or []),
    }
    metrics.update(
        {
            key: value
            for key, value in (checked_observed.get("metrics") or {}).items()
            if key not in metrics
        }
    )

    not_evaluated = [row for row in checks if row["status"] == NOT_EVALUATED]
    status = _overall(checks, metrics)

    return {
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "sample_id": checked_gold["sample_id"],
        "source_sha256": checked_gold["source_sha256"],
        "scope": checked_gold["scope"],
        "status": status,
        "checks": checks,
        "metrics": metrics,
        "dimensions": checkers.summarize_dimensions(checks),
        "not_evaluated": not_evaluated,
        "spot_read_list": checkers.spot_read_list(checked_observed, checked_gold),
        "review": review_summary(review),
        "execution": {
            "entry_point": (checked_observed.get("execution") or {}).get("entry_point"),
            "parser_version": (checked_observed.get("execution") or {}).get("parser_version"),
            "selector_version": (checked_observed.get("execution") or {}).get("selector_version"),
            "mode": (checked_observed.get("execution") or {}).get("mode"),
            "limits": effective_limits,
        },
    }
