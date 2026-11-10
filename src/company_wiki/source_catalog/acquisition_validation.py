"""Shared request-scope and receipt comparisons at acquisition boundaries.

These comparisons identify concrete conflicting values, not access rights.
Storage and orchestration reuse them instead of maintaining different rules.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from .security_identity import _normalize_text

if TYPE_CHECKING:
    from .acquisition import DownloadCandidate, DownloadReceipt
    from .resolver import SourceRequest


def candidate_scope_problem(
    request: SourceRequest,
    candidate: DownloadCandidate,
    *,
    issuer_link_lookup: Callable[[str, str], str | None] | None = None,
) -> str | None:
    if request.market and candidate.market != request.market:
        return "market"
    if candidate.document_kind != request.document_kind:
        return "document_kind"
    if _normalize_text(candidate.entity) != _normalize_text(request.entity):
        return "entity"
    for field in ("provider", "provider_document_id", "fiscal_period", "form_type", "language"):
        requested, actual = getattr(request, field), getattr(candidate, field)
        if requested and actual and requested.casefold() != actual.casefold():
            return "accession" if field == "provider_document_id" else field
        if requested and not actual:
            return "accession" if field == "provider_document_id" else field
    if request.fiscal_year is not None and candidate.fiscal_year != request.fiscal_year:
        return "fiscal_year"
    candidate_security_id = candidate.security_id
    if request.security_id is not None or request.identity_scope in {"listing", "issuer"}:
        if not candidate_security_id:
            return "security_id"
        if request.security_id is not None:
            from .security_code import security_codes_equivalent

            if not security_codes_equivalent(
                request.security_id,
                candidate_security_id,
                left_market=request.market,
                right_market=candidate.market,
            ):
                return "security_id"
        elif request.identity_scope == "listing":
            return "security_id"
    if request.identity_scope in {"listing", "issuer"}:
        if request.issuer_link_id is not None:
            if issuer_link_lookup is None:
                return "issuer_link_unverifiable"
            if candidate_security_id is None:
                return "security_id"
            try:
                actual_link = issuer_link_lookup(candidate.market, candidate_security_id)
            except (OSError, ValueError):
                actual_link = None
            if actual_link != request.issuer_link_id:
                return "issuer_link_id"
    return None


def receipt_binding_problem(candidate: DownloadCandidate, receipt: DownloadReceipt) -> str | None:
    for field in ("candidate_id", "provider", "provider_document_id", "source_url"):
        if getattr(receipt, field) != getattr(candidate, field):
            return field
    return None
