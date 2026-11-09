"""Source-bound claim values, citation/role rules and quality projection."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Literal

from company_wiki.source_contract import EvidenceSpan


@dataclass(frozen=True)
class SummaryClaim:
    claim_id: str
    text: str
    evidence_ids: tuple[str, ...]
    claim_type: Literal[
        "company_statement", "analyst_question", "editorial", "uncertain"
    ]
    modality: Literal[
        "actual", "planned", "forecast", "question", "negation", "uncertain"
    ]
    needs_review: bool = False
    context_evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceSummaryDraft:
    source_id: str
    source_sha256: str
    language: str
    claims: tuple[SummaryClaim, ...]
    status: Literal["draft", "needs_review"] = "draft"


class SummaryValidationError(ValueError):
    """Raised when a summary draft violates source, role, or citation rules."""


def validate_summary_draft(
    draft: SourceSummaryDraft,
    *,
    source_id: str,
    source_sha256: str,
    language: str,
    evidence_spans: Sequence[EvidenceSpan],
) -> None:
    """Validate citations and roles; this is not a semantic truth review."""
    validate_summary_identity(
        draft,
        source_id=source_id,
        source_sha256=source_sha256,
        language=language,
    )
    known = {span.span_id: span for span in evidence_spans}
    if not draft.claims:
        raise SummaryValidationError("summary draft must contain at least one claim")
    for claim in draft.claims:
        validate_summary_claim(claim, known, draft.status)
    # A citation-valid draft remains a draft. Semantic entailment, contradictory
    # evidence, modality, negation, and speaker accuracy remain quality questions,
    # not permission to publish or read a source-oriented draft.


def validate_summary_identity(
    draft: SourceSummaryDraft,
    *,
    source_id: str,
    source_sha256: str,
    language: str,
) -> None:
    """Check the whole-draft binding before inspecting recoverable claims."""
    if draft.source_id != source_id or draft.source_sha256 != source_sha256:
        raise SummaryValidationError("summary source identity/hash does not match")
    if draft.language != language:
        raise SummaryValidationError("summary language must match the source language")


def validate_summary_claim(
    claim: SummaryClaim, known: Mapping[str, EvidenceSpan], draft_status: str
) -> None:
    """Validate content binding; the legacy status argument is diagnostic only."""
    if not claim.text.strip():
        raise SummaryValidationError("summary claim text must not be blank")
    if not claim.evidence_ids:
        raise SummaryValidationError("every summary claim requires evidence IDs")
    if set(claim.evidence_ids) - set(known):
        raise SummaryValidationError("summary claim refers to unknown evidence IDs")
    context = claim.context_evidence_ids
    if (len(context) != len(set(context)) or set(context) & set(claim.evidence_ids)
            or set(context) - set(known)):
        raise SummaryValidationError("summary context requires unique separate known evidence IDs")
    support_sources = {known[ref].source_id for ref in claim.evidence_ids}
    if any(known[ref].source_id not in support_sources for ref in context):
        raise SummaryValidationError("summary context cannot cross unsupported original parents")
    _validate_claim_roles(claim, known)


def summary_claim_type_for_roles(roles: Sequence[str]) -> Literal[
    "company_statement", "analyst_question", "uncertain"
]:
    """One role-family policy for source validation and program-owned claims."""
    observed = set(roles)
    if observed and observed <= {"company_filing", "management"}:
        return "company_statement"
    if observed and observed <= {"analyst", "investor_question"}:
        return "analyst_question"
    return "uncertain"


def _validate_claim_roles(
    claim: SummaryClaim, known: Mapping[str, EvidenceSpan]
) -> None:
    roles = {
        known[evidence_id].structured_value.get("source_role", "unknown")
        for evidence_id in claim.evidence_ids
    }
    family = summary_claim_type_for_roles(tuple(roles))
    if claim.claim_type == "company_statement" and roles and family != "company_statement":
        raise SummaryValidationError(
            "non-company evidence cannot support a company statement"
        )
    if claim.claim_type == "analyst_question" and family != "analyst_question":
        raise SummaryValidationError(
            "analyst-question claims must cite question evidence only"
        )
    if claim.claim_type == "analyst_question" and claim.modality != "question":
        raise SummaryValidationError(
            "analyst-question claims must preserve question modality"
        )


def project_summary_quality(
    draft: SourceSummaryDraft,
    *,
    evidence_spans: Sequence[EvidenceSpan],
    discarded_claims: bool = False,
) -> SourceSummaryDraft:
    """Project source-oriented quality without adding permission or truth claims."""
    claims, status = project_summary_claim_quality(
        draft.claims, evidence_spans=evidence_spans, discarded_claims=discarded_claims
    )
    return replace(draft, claims=claims, status=status)


def project_summary_claim_quality(
    claims: Sequence[SummaryClaim],
    *,
    evidence_spans: Sequence[EvidenceSpan],
    discarded_claims: bool = False,
) -> tuple[tuple[SummaryClaim, ...], Literal["draft", "needs_review"]]:
    """Shared evidence/claim quality, independent of raw or projected draft identity."""
    known = {span.span_id: span for span in evidence_spans}
    projected = []
    for claim in claims:
        validate_summary_claim(claim, known, "draft")
        cited = [known[evidence_id] for evidence_id in (*claim.evidence_ids, *claim.context_evidence_ids)]
        needs_review = (
            claim.claim_type == "uncertain"
            or claim.modality == "uncertain"
            or any(
                span.quality_flags or span.parse_status != "parsed" for span in cited
            )
            or any(
                span.structured_value.get("source_role", "unknown") == "unknown"
                for span in cited
            )
        )
        projected.append(replace(claim, needs_review=needs_review))
    # All selected spans remain in the exported bundle and are replayed, even
    # when the compact summary does not repeat each span as a separate claim.
    review_required = (
        discarded_claims
        or any(claim.needs_review for claim in projected)
        or any(
            span.quality_flags or span.parse_status != "parsed"
            for span in evidence_spans
        )
    )
    return tuple(projected), "needs_review" if review_required else "draft"


def summary_claims_sha256(*, universal_newlines: bool = False) -> str:
    """Identify the installed citation, role and quality rules."""
    from company_wiki.implementation_identity import code_sha256

    return code_sha256(__file__, universal_newlines=universal_newlines)


__all__ = [
    "SourceSummaryDraft",
    "SummaryClaim",
    "SummaryValidationError",
    "project_summary_claim_quality",
    "project_summary_quality",
    "summary_claim_type_for_roles",
    "summary_claims_sha256",
    "validate_summary_claim",
    "validate_summary_draft",
    "validate_summary_identity",
]
