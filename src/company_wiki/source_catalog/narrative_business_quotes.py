"""Project selected, verified summary scopes as business evidence quotations."""

from collections.abc import Mapping, Sequence
from typing import Any

from company_wiki.source_contract import EvidenceSpan

from .narrative_claims import SummaryClaim


__all__ = ["project_business_quotes"]


def project_business_quotes(
    evidence_spans: Sequence[EvidenceSpan],
    claims: Sequence[SummaryClaim],
    claim_ids: Sequence[str],
) -> list[dict[str, Any]]:
    """Keep original support, the separate context, and each original locator.

    The caller selects from a verified, pinned summary. A claim contributes
    its scope only. Its generated wording and modality cannot enter the view.
    """
    spans_by_id = {span.span_id: span for span in evidence_spans}
    claims_by_id = {claim.claim_id: claim for claim in claims}

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
    for claim_id in claim_ids:
        claim = claims_by_id[claim_id]
        scope = (claim.evidence_ids, claim.context_evidence_ids)
        if scope in emitted_scopes:
            continue
        emitted_scopes.add(scope)
        rows.append({
            "claim_id": claim_id,
            "support": [part(span_id) for span_id in claim.evidence_ids],
            "context": [part(span_id) for span_id in claim.context_evidence_ids],
        })
    return rows
