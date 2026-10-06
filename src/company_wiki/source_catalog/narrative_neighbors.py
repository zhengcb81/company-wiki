"""Adjacent subject, continuation, and Q&A context enrichment."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import re
from types import MappingProxyType
from typing import Literal

from .narrative_candidates import EvidenceCandidate
from .narrative_document import NarrativeUnit


TopicClassifier = Callable[[str], tuple[str, ...]]
_NEVER = re.compile(r"(?!x)x")


def _no_topics(_text: str) -> tuple[str, ...]:
    return ()


@dataclass(frozen=True)
class NeighborRules:
    topics: TopicClassifier = _no_topics
    high_value_event: re.Pattern[str] = _NEVER
    named_product_context: re.Pattern[str] = _NEVER
    accounting_context: re.Pattern[str] = _NEVER
    project_rationale: re.Pattern[str] = _NEVER
    table_of_contents: re.Pattern[str] = _NEVER


@dataclass(frozen=True)
class NeighborEnrichmentResult:
    candidates: tuple[EvidenceCandidate, ...]
    group_ids: Mapping[str, str]


@dataclass
class _Store:
    candidates: list[EvidenceCandidate]
    group_ids: dict[str, str]

    def ids(self) -> set[str]:
        return {candidate.unit.unit_id for candidate in self.candidates}

    def index(self, unit_id: str) -> int | None:
        return next(
            (
                index
                for index, candidate in enumerate(self.candidates)
                if candidate.unit.unit_id == unit_id
            ),
            None,
        )

    def add(self, candidate: EvidenceCandidate, group_id: str | None = None) -> None:
        if group_id is not None:
            self.group_ids[candidate.unit.unit_id] = group_id
        self.candidates.append(candidate)

    def add_reason(self, unit_id: str, reason: str, score_bonus: int = 0) -> None:
        index = self.index(unit_id)
        if index is None:
            return
        candidate = self.candidates[index]
        reasons = tuple(dict.fromkeys((*candidate.reasons, reason)))
        self.candidates[index] = EvidenceCandidate(
            candidate.unit,
            candidate.topics,
            reasons,
            candidate.score + score_bonus,
        )


def _match(pattern: re.Pattern[str], text: str) -> bool:
    return pattern.search(text) is not None


def _unit_by_location(
    units: Sequence[NarrativeUnit],
) -> dict[tuple[str, int | None, int | None], NarrativeUnit]:
    return {
        (
            unit.source_id,
            unit.coordinates.page_number,
            unit.coordinates.paragraph_index,
        ): unit
        for unit in units
        if unit.unit_kind == "pdf_text_block"
    }


def _subject_signal(unit: NarrativeUnit, rules: NeighborRules) -> bool:
    topics = set(rules.topics(unit.raw_text))
    if topics & {"new_business", "products_rd", "core_business"}:
        return True
    return _match(rules.named_product_context, unit.raw_text)


def _valid_previous(
    previous: NarrativeUnit | None,
    event: NarrativeUnit,
    selected_ids: set[str],
    rules: NeighborRules,
) -> bool:
    if previous is None or previous.unit_id in selected_ids:
        return False
    if previous.source_role != event.source_role:
        return False
    if previous.language != event.language:
        return False
    if not _subject_signal(previous, rules) or len(previous.raw_text) < 12:
        return False
    return not _match(rules.accounting_context, previous.raw_text)


def _pair_group_id(source_id: str, role: str, *unit_ids: str) -> str:
    pair_key = "|".join(sorted(unit_ids))
    digest = hashlib.sha256(
        f"{source_id}:{role}:{pair_key}".encode("utf-8")
    ).hexdigest()
    return f"urn:company-wiki:context-group:sha256:{digest}"


def _compatible_group(
    group_ids: Mapping[str, str], first_id: str, second_id: str
) -> str | None | Literal[False]:
    first = group_ids.get(first_id)
    second = group_ids.get(second_id)
    if first is not None and second is not None and first != second:
        return False
    return first or second


def _add_adjacent_subjects(
    store: _Store,
    units: Sequence[NarrativeUnit],
    rules: NeighborRules,
) -> None:
    by_location = _unit_by_location(units)
    selected_ids = store.ids()
    for candidate in tuple(store.candidates):
        _add_adjacent_subject(store, candidate, by_location, selected_ids, rules)


def _add_adjacent_subject(
    store: _Store,
    candidate: EvidenceCandidate,
    by_location: Mapping[tuple[str, int | None, int | None], NarrativeUnit],
    selected_ids: set[str],
    rules: NeighborRules,
) -> None:
    event = candidate.unit
    if event.unit_kind != "pdf_text_block":
        return
    if not _match(rules.high_value_event, event.raw_text):
        return
    key = (
        event.source_id,
        event.coordinates.page_number,
        (event.coordinates.paragraph_index or 0) - 1,
    )
    previous = by_location.get(key)
    if not _valid_previous(previous, event, selected_ids, rules):
        return
    assert previous is not None
    group = _compatible_group(store.group_ids, event.unit_id, previous.unit_id)
    if group is False:
        return
    group_id = group or _pair_group_id(
        event.source_id, "adjacent-context", event.unit_id, previous.unit_id
    )
    store.group_ids[event.unit_id] = group_id
    reasons = _adjacent_reasons_and_boost(
        store, event.unit_id, previous.raw_text, rules
    )
    store.add(
        EvidenceCandidate(previous, rules.topics(previous.raw_text), reasons, 0),
        group_id,
    )
    selected_ids.add(previous.unit_id)


def _adjacent_reasons_and_boost(
    store: _Store, event_id: str, subject_text: str, rules: NeighborRules
) -> tuple[str, ...]:
    if not _match(rules.named_product_context, subject_text):
        return ("adjacent_subject_context",)
    store.add_reason(event_id, "named_product_milestone_context", 4)
    return ("adjacent_subject_context", "named_product_milestone_context")


def _valid_continuation(
    continuation: NarrativeUnit | None,
    heading: NarrativeUnit,
    selected_ids: set[str],
    rules: NeighborRules,
) -> bool:
    if continuation is None or continuation.unit_id in selected_ids:
        return False
    if continuation.source_role != heading.source_role:
        return False
    if continuation.language != heading.language:
        return False
    if not 1 <= len(continuation.raw_text) < 12:
        return False
    if not re.search(r"[\u3400-\u9fffA-Za-z0-9]", continuation.raw_text):
        return False
    if _match(rules.table_of_contents, continuation.raw_text):
        return False
    return not _match(rules.accounting_context, continuation.raw_text)


def _add_heading_continuations(
    store: _Store,
    units: Sequence[NarrativeUnit],
    rules: NeighborRules,
) -> None:
    by_location = _unit_by_location(units)
    selected_ids = store.ids()
    for candidate in tuple(store.candidates):
        _add_heading_continuation(store, candidate, by_location, selected_ids, rules)


def _add_heading_continuation(
    store: _Store,
    candidate: EvidenceCandidate,
    by_location: Mapping[tuple[str, int | None, int | None], NarrativeUnit],
    selected_ids: set[str],
    rules: NeighborRules,
) -> None:
    heading = candidate.unit
    if heading.unit_kind != "pdf_text_block":
        return
    if not _match(rules.project_rationale, heading.raw_text):
        return
    key = (
        heading.source_id,
        heading.coordinates.page_number,
        (heading.coordinates.paragraph_index or 0) + 1,
    )
    continuation = by_location.get(key)
    if not _valid_continuation(continuation, heading, selected_ids, rules):
        return
    assert continuation is not None
    group = _compatible_group(store.group_ids, heading.unit_id, continuation.unit_id)
    if group is False:
        return
    group_id = group or _pair_group_id(
        heading.source_id,
        "heading-continuation",
        heading.unit_id,
        continuation.unit_id,
    )
    store.group_ids[heading.unit_id] = group_id
    store.add_reason(heading.unit_id, "short_fragment_continuation")
    store.add(
        EvidenceCandidate(
            continuation,
            rules.topics(continuation.raw_text),
            ("adjacent_subject_context", "short_fragment_continuation"),
            0,
        ),
        group_id,
    )
    selected_ids.add(continuation.unit_id)


def _qa_linked(question_group: object, answer_groups: set[object]) -> bool:
    for answer_group in answer_groups:
        if question_group == answer_group:
            return True
        if question_group is None or answer_group is None:
            continue
        if str(question_group).startswith(f"{answer_group}:q"):
            return True
    return False


def _question_has_context(unit: NarrativeUnit, rules: NeighborRules) -> bool:
    if rules.topics(unit.raw_text):
        return True
    if _match(rules.high_value_event, unit.raw_text):
        return True
    return "?" in unit.raw_text or "？" in unit.raw_text


def _add_linked_questions(
    store: _Store,
    units: Sequence[NarrativeUnit],
    rules: NeighborRules,
) -> None:
    selected_ids = store.ids()
    answer_groups = {
        candidate.unit.metadata.get("qa_group_id")
        for candidate in store.candidates
        if candidate.unit.metadata.get("qa_group_id") is not None
    }
    for unit in units:
        if unit.source_role not in {"analyst", "investor_question"}:
            continue
        if unit.unit_id in selected_ids:
            continue
        if not _qa_linked(unit.metadata.get("qa_group_id"), answer_groups):
            continue
        if not _question_has_context(unit, rules):
            continue
        store.add(EvidenceCandidate(unit, (), ("linked_question_context",), 0))
        selected_ids.add(unit.unit_id)


def enrich_neighbor_context(
    units: Sequence[NarrativeUnit],
    *,
    initial_candidates: Sequence[EvidenceCandidate],
    initial_group_ids: Mapping[str, str],
    rules: NeighborRules,
) -> NeighborEnrichmentResult:
    """Attach only the minimum neighboring context needed to interpret facts."""
    store = _Store(list(initial_candidates), dict(initial_group_ids))
    _add_adjacent_subjects(store, units, rules)
    _add_heading_continuations(store, units, rules)
    _add_linked_questions(store, units, rules)
    return NeighborEnrichmentResult(
        candidates=tuple(store.candidates),
        group_ids=MappingProxyType(store.group_ids),
    )


__all__ = ["NeighborEnrichmentResult", "NeighborRules", "enrich_neighbor_context"]
