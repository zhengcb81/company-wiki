"""Deduplicate, budget, and package selected narrative evidence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
import json
import re
from typing import Any, Literal

from company_wiki.source_contract import EvidenceSpan

from .n6_budget_dedup import deduplicate_candidates
from .narrative_budget import (BudgetItem, LEGACY_BUDGET_POLICY, READING_BUDGET_POLICY,
                               REPLAY_READING_BUDGET_POLICY, REPLAY_VALUE_READING_BUDGET_POLICY,
                               plan_budget_items)
from .narrative_semantic_coverage import CoverageSignature, group_coverage_signature
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
    *, signature: CoverageSignature | None = None,
    reading: Mapping[str, Any] | None = None,
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
        evidence_chars=len(unit.raw_text),
        semantic_tokens=signature.tokens if signature is not None else (),
        coverage_signature=signature,
        reading_priority=(reading or {}).get("priority", 2),
        reading_topics=tuple((reading or {}).get("topics", ())),
        required_item_ids=tuple((reading or {}).get("required", ())),
        is_context_only=(reading or {}).get("context_only", False),
        value_band=(reading or {}).get("value_band", "description"),
    )


def _group_signatures(
    candidates: Sequence[EvidenceCandidate], group_ids: Mapping[str, str]
) -> dict[str, CoverageSignature]:
    """Join native source order once; per-span bags cannot bind quantities."""
    groups: dict[str, list[EvidenceCandidate]] = {}
    for candidate in candidates:
        key = group_ids.get(candidate.unit.unit_id, candidate.unit.unit_id)
        groups.setdefault(key, []).append(candidate)
    signatures: dict[str, CoverageSignature] = {}
    by_text: dict[tuple[str, ...], CoverageSignature] = {}
    for members in groups.values():
        ordered = sorted(members, key=lambda item: (_order_key(item), item.unit.unit_id))
        texts = tuple(candidate.unit.raw_text for candidate in ordered)
        signature = by_text.get(texts)
        if signature is None:
            signature = group_coverage_signature(texts)
            if len(by_text) < 4096:
                by_text[texts] = signature
        for candidate in members:
            signatures[candidate.unit.unit_id] = signature
    return signatures


def _evidence_spans(
    candidates: Sequence[EvidenceCandidate], group_ids: Mapping[str, str],
    reading_metadata: Mapping[str, Mapping[str, Any]] | None = None,
) -> tuple[EvidenceSpan, ...]:
    spans = []
    for candidate in candidates:
        unit = candidate.unit
        reading = (reading_metadata or {}).get(unit.unit_id)
        if reading is not None:
            unit = replace(unit, metadata={**unit.metadata,
                "reading_priority": reading["priority"],
                "reading_value_band": reading.get("value_band", "description"),
                "reading_score": candidate.score})
        spans.append(unit.to_evidence_span(
            topics=candidate.topics,
            selection_reasons=candidate.reasons,
            selection_group_id=group_ids.get(unit.unit_id),
        ))
    return tuple(spans)


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
    budget_policy: str = LEGACY_BUDGET_POLICY,
    reading_metadata: Mapping[str, Mapping[str, Any]] | None = None,
    max_chars: int | None = None,
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
    # New reading packages share original context across independent anchors.
    # Text-level deduplication cannot rewrite these dependency identities.
    if budget_policy in {READING_BUDGET_POLICY, REPLAY_READING_BUDGET_POLICY, REPLAY_VALUE_READING_BUDGET_POLICY}:
        survivors = tuple({item.unit.unit_id: item for item in complete}.values())
        effective_groups = group_ids
    else:
        deduplicated = deduplicate_candidates(complete, group_ids)
        survivors, effective_groups = deduplicated.candidates, deduplicated.group_ids
    signatures = (_group_signatures(survivors, effective_groups)
        if budget_policy != LEGACY_BUDGET_POLICY else {})
    budget_items = tuple(
        _budget_item(candidate, effective_groups, heading_pattern,
            signature=signatures.get(candidate.unit.unit_id),
            reading=(reading_metadata or {}).get(candidate.unit.unit_id))
        for candidate in survivors
    )
    planned, diagnostics = plan_budget_items(budget_items, limit=route.selection_limit,
                                            policy=budget_policy, max_chars=max_chars)
    selected = [item.payload for item in planned]
    counts: dict[str, int] = {}
    for diagnostic in diagnostics:
        counts[diagnostic.reason] = counts.get(diagnostic.reason, 0) + 1
    omitted = max(0, len(candidates) - len(selected))
    native_order = {unit.unit_id: index for index, unit in enumerate(structure.units)}
    if budget_policy in {READING_BUDGET_POLICY, REPLAY_READING_BUDGET_POLICY, REPLAY_VALUE_READING_BUDGET_POLICY}:
        selected.sort(key=lambda item: native_order[item.unit.unit_id])
    else:
        selected.sort(key=lambda item: (item.unit.coordinates.locator(), item.unit.unit_id))
    spans = _evidence_spans(selected, effective_groups,
        reading_metadata if budget_policy == READING_BUDGET_POLICY else None)
    diagnostic_rows = []
    for reason, count in sorted(counts.items()):
        row: dict[str, Any] = {"code": reason, "count": count,
                               "phase": "selection", "external_model_cost": False}
        if reason == "budget_full":
            row.update(dimension="selection_spans", used=len(spans), limit=route.selection_limit)
        elif reason == "character_budget":
            row.update(dimension="selection_characters",
                       used=sum(len(span.raw_text or "") for span in spans), limit=max_chars)
        else:
            row["dimension"] = "selection_work" if reason == "work_budget_exhausted" else "selection_policy"
        diagnostic_rows.append(row)
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
        selection_diagnostics=(tuple(diagnostic_rows)
                               if budget_policy in {READING_BUDGET_POLICY, REPLAY_READING_BUDGET_POLICY,
                                                    REPLAY_VALUE_READING_BUDGET_POLICY} else ()),
    )


__all__ = ["finalize_selection"]
