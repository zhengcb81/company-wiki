"""Whole original support scopes, without paraphrases or inferred business facts.

The source task planner owns membership. This view never cuts sentences, repairs
referents, converts tables to numbers, or borrows another task's predicates.
Quality and ambiguous modality remain observations, not publication permissions.
"""
from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass

from company_wiki.source_contract import EvidenceSpan
from .summary_tasks import SourceSummaryTask, SummaryTaskPlan


@dataclass(frozen=True)
class SourceCard:
    task: SourceSummaryTask
    support: tuple[EvidenceSpan, ...]
    available: bool
    reason: str

    @property
    def text(self) -> str | None:
        """Only admitted bounded cards need a materialized original quote."""
        return '\n'.join(span.raw_text for span in self.support) if self.available else None


def source_cards(plan: SummaryTaskPlan, spans: Mapping[str, EvidenceSpan]) -> Iterator[SourceCard]:
    """Use every native support part, retaining context separately by reference."""
    for task in plan.tasks:
        if any(spans[sid].parse_status != 'parsed' or not spans[sid].raw_text.strip()
               for sid in task.member_ids):
            yield SourceCard(task, (), False, 'source_not_parsed')
            continue
        yield SourceCard(task, tuple(spans[sid] for sid in task.support_ids), True, 'source_card')
