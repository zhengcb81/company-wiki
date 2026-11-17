"""Project selected, verified summary scopes as business evidence quotations."""

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from company_wiki.source_contract import EvidenceSpan

from .narrative_business_focus import business_summary_context_only
from .narrative_claims import SummaryClaim
from .narrative_reading_admission import CONTEXT_ROLES, is_financial_only
from .narrative_source_purpose import NON_OPERATING_PURPOSES, source_purpose
from .narrative_summary_material import compile_scoped_material_view
from .narrative_summary_protocols import ATOMIC_SCOPED


__all__ = ["project_business_quotes", "project_automatic_business_quotes"]


def project_business_quotes(
    evidence_spans: Sequence[EvidenceSpan],
    claims: Sequence[SummaryClaim],
    claim_ids: Sequence[str],
) -> list[dict[str, Any]]:
    """Keep original support, the separate context, and each original locator.

    The caller selects from a verified, pinned summary. A claim contributes
    its scope only. Its generated wording and modality cannot enter the view.
    """
    claims_by_id = {claim.claim_id: claim for claim in claims}
    scopes = ((claim_id, None, claims_by_id[claim_id].evidence_ids, claims_by_id[claim_id].context_evidence_ids)
              for claim_id in claim_ids)
    return _quotes({span.span_id: span for span in evidence_spans}, scopes)


def project_automatic_business_quotes(
    evidence_spans: Sequence[EvidenceSpan],
    claims: Sequence[SummaryClaim],
    reading_context: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """Use source-admitted scopes, including those omitted by the model draft."""
    spans = {span.span_id: span for span in evidence_spans}
    plan = compile_scoped_material_view(evidence_spans, reading_context, max_claims=ATOMIC_SCOPED.plan_max_claims)
    by_scope = {(claim.evidence_ids, claim.context_evidence_ids): claim.claim_id for claim in reversed(claims)}
    scopes = []
    for task in plan.model_tasks:
        if CONTEXT_ROLES.intersection(task.support_roles) or "analyst_question" in task.support_roles:
            continue
        if task.kind != "operating_table":
            source = "\n".join(spans[sid].raw_text or "" for sid in task.support_ids)
            if (business_summary_context_only(source)
                    or source_purpose(source) in NON_OPERATING_PURPOSES or is_financial_only(source)):
                continue
        scope = (task.support_ids, task.context_ids)
        scopes.append((by_scope.get(scope), task.key, *scope))
    return _quotes(spans, scopes)


def _quotes(
    spans_by_id: Mapping[str, EvidenceSpan],
    scopes: Iterable[tuple[str | None, str | None, tuple[str, ...], tuple[str, ...]]],
) -> list[dict[str, Any]]:

    def part(span_id: str) -> dict[str, Any]:
        span = spans_by_id[span_id]
        result: dict[str, Any] = {
            "source_id": span.source_id,
            "span_id": span.span_id,
            "locator": span.locator,
            "text": span.raw_text,
            "parse_status": span.parse_status.value,
            "quality_flags": list(span.quality_flags),
        }
        if isinstance(span.structured_value, Mapping):
            for name in ("source_role", "speaker", "turn_id"):
                value = span.structured_value.get(name)
                if isinstance(value, str) and value:
                    result[name] = value
            printed_turn = span.structured_value.get("printed_turn")
            if isinstance(printed_turn, Mapping):
                result["printed_turn"] = {
                    name: printed_turn[name]
                    for name in ("speaker", "title", "role", "turn_id", "label_locator")
                    if isinstance(printed_turn.get(name), str)
                }
        return result

    rows: list[dict[str, Any]] = []
    emitted_scopes: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()
    for claim_id, task_key, support, context in scopes:
        scope = (support, context)
        if scope in emitted_scopes:
            continue
        emitted_scopes.add(scope)
        rows.append({
            "claim_id": claim_id,
            **({"task_key": task_key} if task_key is not None else {}),
            "support": [part(span_id) for span_id in support],
            "context": [part(span_id) for span_id in context],
        })
    return rows
