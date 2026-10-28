"""Whole original support scopes, without paraphrases or inferred business facts.

The source task planner owns membership. This view never cuts sentences, repairs
referents, converts tables to numbers, or borrows another task's predicates.
Quality and ambiguous modality remain observations, not publication permissions.
"""
from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any

from company_wiki.source_contract import EvidenceSpan
from .summary_tasks import SourceSummaryTask, SummaryTaskPlan

SourceCardScope = tuple[str, tuple[str, ...], tuple[str, ...], tuple[str, ...], str, str]


@dataclass(frozen=True)
class SourceCard:
    task: SourceSummaryTask
    support: tuple[EvidenceSpan, ...]
    available: bool
    reason: str

    @property
    def text(self) -> str | None:
        """Only admitted bounded cards need a materialized original quote."""
        return '\n'.join(span.raw_text or '' for span in self.support) if self.available else None

    def reading_hint(self) -> dict[str, Any]:
        """Project existing support-owned reading decisions, never classify text."""
        observed = []
        purposes = []
        for span in self.support:
            value = span.structured_value
            priority, band, score = (value.get(name) for name in (
                'reading_priority', 'reading_value_band', 'reading_score'))
            if (type(priority) is int and priority >= 0
                    and band in ('meaningful_fact', 'description')
                    and type(score) is int and score >= 0):
                observed.append((priority, 0 if band == 'meaningful_fact' else 1, -score))
            purpose = value.get('reading_fact_purpose')
            if isinstance(purpose, str) and purpose and len(purpose) <= 80:
                purposes.append(purpose)
        result: dict[str, Any] = {}
        if observed:
            priority, band_index, inverse_score = min(observed)
            result.update(priority=priority, value_band=('meaningful_fact', 'description')[band_index],
                          score=-inverse_score)
        if purposes:
            result['purposes'] = list(dict.fromkeys(purposes))
        return result


def source_card_scope(task: SourceSummaryTask) -> SourceCardScope:
    """Only identical factual support, context and source role views duplicate."""
    return (task.source_id, task.support_ids, task.context_ids, task.support_roles,
            task.kind, task.section_role)


def source_card_generation_reason(card: SourceCard) -> str | None:
    """Consume the source's scope use; do not mistake readable text for support."""
    if not card.available:
        return card.reason
    use = card.task.support_use
    if use is not None and use != 'support':
        return 'source_' + use
    return None


def source_task_admission(cards: tuple[SourceCard, ...]) -> dict[str, dict[str, str]]:
    """Record source availability without shrinking the canonical source plan."""
    seen: dict[SourceCardScope, str] = {}
    result: dict[str, dict[str, str]] = {}
    for card in cards:
        key = card.task.key
        reason = source_card_generation_reason(card)
        if reason is not None:
            result[key] = {'status': 'unavailable', 'reason': reason}
            continue
        scope = source_card_scope(card.task)
        if scope in seen:
            result[key] = {'status': 'duplicate', 'reason': 'duplicate_scope',
                           'representative': seen[scope]}
        else:
            seen[scope] = key
            result[key] = {'status': 'admitted', 'reason': 'source_card'}
    return result


def source_cards(plan: SummaryTaskPlan, spans: Mapping[str, EvidenceSpan]) -> Iterator[SourceCard]:
    """Use every native support part, retaining context separately by reference."""
    for task in plan.tasks:
        if any(spans[sid].parse_status != 'parsed' or not (spans[sid].raw_text or '').strip()
               for sid in task.member_ids):
            yield SourceCard(task, (), False, 'source_not_parsed')
            continue
        closure_ids = task.member_ids if task.kind == 'operating_table' else task.support_ids
        if any('table_structure_ambiguous' in spans[sid].quality_flags for sid in closure_ids):
            yield SourceCard(task, (), False, 'source_table_unresolved')
            continue
        yield SourceCard(task, tuple(spans[sid] for sid in task.support_ids), True, 'source_card')
