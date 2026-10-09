"""Deduplicate, budget, and package selected narrative evidence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
import re
from typing import Literal

from company_wiki.source_contract import EvidenceSpan

from .n6_budget_dedup import deduplicate_candidates
from .narrative_budget import BudgetItem, select_budget_items
from .narrative_candidates import EvidenceCandidate
from .narrative_document import DocumentStructure, NarrativeEvidencePackage
from .narrative_routing import DocumentRoute


SelectionStatus = Literal[
    "selected", "partial", "skipped_no_narrative", "needs_review", "blocked"
]


def _page_key(candidate: EvidenceCandidate) -> tuple[str, int | str]:
    page = candidate.unit.coordinates.page_number
    if page is not None:
        return ("page", page)
    return (
        "locator",
        json.dumps(candidate.unit.coordinates.locator(), sort_keys=True),
    )


def _order_key(candidate: EvidenceCandidate) -> tuple[int, ...]:
    coordinates = candidate.unit.coordinates
    values = (
        coordinates.page_number,
        coordinates.paragraph_index,
        coordinates.table_index,
        coordinates.row_index,
        coordinates.column_index,
        coordinates.char_start,
        coordinates.char_end,
    )
    return tuple(-1 if value is None else value for value in values)


def _budget_item(
    candidate: EvidenceCandidate,
    group_ids: Mapping[str, str],
    heading_pattern: re.Pattern[str],
) -> BudgetItem[EvidenceCandidate]:
    unit = candidate.unit
    return BudgetItem(
        item_id=unit.unit_id,
        group_id=group_ids.get(unit.unit_id),
        page_key=_page_key(candidate),
        locator=unit.coordinates.locator(),
        order_key=_order_key(candidate),
        reasons=candidate.reasons,
        score=candidate.score,
        is_heading=heading_pattern.search(unit.raw_text) is not None,
        payload=candidate,
    )


def _evidence_spans(
    candidates: Sequence[EvidenceCandidate], group_ids: Mapping[str, str]
) -> tuple[EvidenceSpan, ...]:
    return tuple(
        candidate.unit.to_evidence_span(
            topics=candidate.topics,
            selection_reasons=candidate.reasons,
            selection_group_id=group_ids.get(candidate.unit.unit_id),
        )
        for candidate in candidates
    )


def _status(
    structure: DocumentStructure,
    route: DocumentRoute,
    spans: tuple[EvidenceSpan, ...],
    omitted: int,
    dropped_financial_count: int,
) -> SelectionStatus:
    if spans and any("locator_unstable" in span.quality_flags for span in spans):
        return "needs_review"
    if spans:
        return "selected" if structure.coverage_complete and omitted == 0 else "partial"
    if structure.errors:
        return "blocked"
    if omitted:
        # A quota that fits none of the complete groups is still partial
        # processing, rather than absence of business narrative.
        return "partial"
    if not structure.coverage_complete:
        return "needs_review"
    if structure.units and dropped_financial_count == len(structure.units):
        return "skipped_no_narrative"
    return "skipped_no_narrative" if route.empty_result_may_skip else "needs_review"


def finalize_selection(
    structure: DocumentStructure,
    route: DocumentRoute,
    candidates: Sequence[EvidenceCandidate],
    *,
    group_ids: Mapping[str, str],
    heading_pattern: re.Pattern[str],
    dropped_financial_count: int,
    excluded_context_unit_ids: frozenset[str] = frozenset(),
) -> NarrativeEvidencePackage:
    """Create the compact package after deterministic candidate enrichment.

    ``candidate_count`` counts every candidate handed in, and
    ``omitted_candidate_count`` is exactly ``candidate_count - selected``, so
    both conservative deduplication and budget refusal stay visible instead of
    shrinking the counters after the fact.
    """
    excluded_groups = {group_ids[uid] for uid in excluded_context_unit_ids if uid in group_ids}
    complete = tuple(candidate for candidate in candidates
                     if candidate.unit.unit_id not in excluded_context_unit_ids
                     and group_ids.get(candidate.unit.unit_id) not in excluded_groups)
    deduplicated = deduplicate_candidates(complete, group_ids)
    budget_items = tuple(
        _budget_item(candidate, deduplicated.group_ids, heading_pattern)
        for candidate in deduplicated.candidates
    )
    selected = [
        item.payload
        for item in select_budget_items(budget_items, limit=route.selection_limit)
    ]
    omitted = max(0, len(candidates) - len(selected))
    selected.sort(key=lambda item: (item.unit.coordinates.locator(), item.unit.unit_id))
    spans = _evidence_spans(selected, deduplicated.group_ids)
    return NarrativeEvidencePackage(
        source_id=structure.source_id,
        source_sha256=structure.source_sha256,
        document_kind=route.document_kind,
        status=_status(structure, route, spans, omitted, dropped_financial_count),
        evidence_spans=spans,
        selection_limit=route.selection_limit,
        candidate_count=len(candidates),
        dropped_financial_count=dropped_financial_count,
        source_units=len(structure.units),
        omitted_candidate_count=omitted,
        coverage_complete=structure.coverage_complete,
    )


__all__ = ["finalize_selection"]
