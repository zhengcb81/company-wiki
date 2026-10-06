"""Typed PDF visual-group enrichment for narrative candidates."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import re
from types import MappingProxyType

from .n6_candidate_completion import (
    BUSINESS_CHARACTER_WINDOW,
    PROJECT_CHARACTER_WINDOW,
    completion_indices,
    members_linkable,
)
from .n6_candidate_operating_facts import (
    OPERATING_FACT_JOIN,
    OperatingFact,
    detect_operating_fact,
)
from .narrative_candidates import EvidenceCandidate
from .narrative_context import PdfContextGroup
from .narrative_document import NarrativeUnit


TopicClassifier = Callable[[str], tuple[str, ...]]
OperatingFactDetector = Callable[[str], OperatingFact]
WindowFinder = Callable[
    [Sequence[NarrativeUnit], re.Pattern[str]], tuple[tuple[int, int], ...]
]
_NEVER = re.compile(r"(?!x)x")
_EXCLUDED_ROLES = frozenset(
    {"analyst", "investor_question", "operator", "editorial", "qa_text_shadow"}
)
_ENDS_SENTENCE = re.compile(r"[。！？!?；;]$")
_EMPTY_FACT = OperatingFact()


def _no_topics(_text: str) -> tuple[str, ...]:
    return ()


def _no_windows(
    _members: Sequence[NarrativeUnit], _pattern: re.Pattern[str]
) -> tuple[tuple[int, int], ...]:
    return ()


@dataclass(frozen=True)
class GroupCandidateRules:
    topics: TopicClassifier = _no_topics
    window_finder: WindowFinder = _no_windows
    operating_facts: OperatingFactDetector = detect_operating_fact
    project_heading: re.Pattern[str] = _NEVER
    business_heading: re.Pattern[str] = _NEVER
    high_value_event: re.Pattern[str] = _NEVER
    positioning: re.Pattern[str] = _NEVER
    business_risk: re.Pattern[str] = _NEVER
    direct_capacity_constraint: re.Pattern[str] = _NEVER
    long_customer_qualification: re.Pattern[str] = _NEVER
    project_certification_timeline: re.Pattern[str] = _NEVER
    quantified_market_coverage_target: re.Pattern[str] = _NEVER
    permit_milestone: re.Pattern[str] = _NEVER
    new_product_milestone: re.Pattern[str] = _NEVER
    project_rationale: re.Pattern[str] = _NEVER
    downstream_extension: re.Pattern[str] = _NEVER
    project_plan: re.Pattern[str] = _NEVER
    strategic_plan: re.Pattern[str] = _NEVER
    table_of_contents: re.Pattern[str] = _NEVER
    accounting_context: re.Pattern[str] = _NEVER
    static_definition: re.Pattern[str] = _NEVER
    progress: re.Pattern[str] = _NEVER
    recency: re.Pattern[str] = _NEVER
    downstream_center_timeline: re.Pattern[str] = _NEVER


@dataclass(frozen=True)
class GroupEnrichmentResult:
    candidates: tuple[EvidenceCandidate, ...]
    group_ids: Mapping[str, str]


@dataclass(frozen=True)
class _GroupSignals:
    event: bool
    positioning: bool
    business_risk: bool
    direct_capacity_constraint: bool
    long_customer_qualification: bool
    certification_timeline: bool
    market_coverage_target: bool
    permit_milestone: bool
    new_product_milestone: bool
    project_rationale: bool
    downstream_extension: bool
    project: bool
    progress: bool
    current_industry: bool


@dataclass
class _CandidateStore:
    candidates: list[EvidenceCandidate]
    group_ids: dict[str, str]

    def index(self, unit_id: str) -> int | None:
        return next(
            (
                index
                for index, candidate in enumerate(self.candidates)
                if candidate.unit.unit_id == unit_id
            ),
            None,
        )

    def assign_group(self, unit_id: str, group_id: str) -> bool:
        """Record one membership; an existing different group is never replaced."""
        existing = self.group_ids.get(unit_id)
        if existing is not None and existing != group_id:
            return False
        self.group_ids[unit_id] = group_id
        return True

    def add(
        self,
        unit: NarrativeUnit,
        topics: tuple[str, ...],
        reasons: tuple[str, ...],
        score: int,
        group_id: str | None = None,
    ) -> None:
        if group_id is not None:
            self.assign_group(unit.unit_id, group_id)
        if self.index(unit.unit_id) is not None:
            return
        self.candidates.append(EvidenceCandidate(unit, topics, reasons, score))

    def boost(self, unit_id: str, reason: str, score: int) -> bool:
        index = self.index(unit_id)
        if index is None:
            return False
        existing = self.candidates[index]
        reasons = tuple(dict.fromkeys((*existing.reasons, reason)))
        self.candidates[index] = EvidenceCandidate(
            existing.unit, existing.topics, reasons, existing.score + score
        )
        return True


def _match(pattern: re.Pattern[str], text: str) -> bool:
    return pattern.search(text) is not None


def _signals(
    text: str, topics: tuple[str, ...], rules: GroupCandidateRules
) -> _GroupSignals:
    return _GroupSignals(
        event=_match(rules.high_value_event, text),
        positioning=_match(rules.positioning, text),
        business_risk=_match(rules.business_risk, text),
        direct_capacity_constraint=_match(rules.direct_capacity_constraint, text),
        long_customer_qualification=_match(rules.long_customer_qualification, text),
        certification_timeline=_match(rules.project_certification_timeline, text),
        market_coverage_target=_match(rules.quantified_market_coverage_target, text),
        permit_milestone=_match(rules.permit_milestone, text),
        new_product_milestone=_match(rules.new_product_milestone, text),
        project_rationale=_match(rules.project_rationale, text),
        downstream_extension=_match(rules.downstream_extension, text),
        project=any(
            (_match(rules.project_plan, text), _match(rules.strategic_plan, text))
        ),
        progress=_match(rules.progress, text),
        current_industry=(
            "industry_dynamics" in topics and _match(rules.recency, text)
        ),
    )


def _usable_unit(unit: NarrativeUnit, rules: GroupCandidateRules) -> bool:
    if unit.source_role in _EXCLUDED_ROLES:
        return False
    return not _match(rules.table_of_contents, unit.raw_text)


def _unit_topics(
    unit: NarrativeUnit,
    group_topics: tuple[str, ...],
    fallback: tuple[str, ...],
    rules: GroupCandidateRules,
) -> tuple[str, ...]:
    return rules.topics(unit.raw_text) or group_topics or fallback


def _expand_timeline_range(
    members: Sequence[NarrativeUnit], start: int, end: int
) -> tuple[int, int]:
    if start == 0:
        return start, end
    prefix = members[start - 1]
    prefix_text = prefix.raw_text.strip()
    if prefix.source_role != members[start].source_role:
        return start, end
    if len(prefix_text) > 12 or _ENDS_SENTENCE.search(prefix_text):
        return start, end
    return start - 1, end


def _timeline_reasons(unit: NarrativeUnit, downstream: bool) -> tuple[str, ...]:
    reasons = [
        "business_narrative_signal",
        "project_certification_timeline",
        "project_plan_or_status",
        "pdf_visual_context_group",
    ]
    if downstream:
        reasons.append("downstream_center_certification_timeline")
    if len(unit.raw_text.strip()) <= 12:
        reasons.append("short_fragment_continuation")
    if unit.source_role == "management":
        reasons.append("management_statement")
    return tuple(reasons)


def _add_timeline_window(
    store: _CandidateStore,
    *,
    group_id: str,
    window_index: int,
    members: Sequence[NarrativeUnit],
    group_topics: tuple[str, ...],
    rules: GroupCandidateRules,
) -> set[str]:
    selection_id = f"{group_id}:certification-timeline:{window_index}"
    window_text = "".join(unit.raw_text for unit in members)
    downstream = _match(rules.downstream_center_timeline, window_text)
    added: set[str] = set()
    for unit in members:
        if not _usable_unit(unit, rules):
            continue
        if not store.assign_group(unit.unit_id, selection_id):
            continue
        added.add(unit.unit_id)
        if store.index(unit.unit_id) is not None:
            if downstream:
                store.boost(unit.unit_id, "downstream_center_certification_timeline", 2)
            continue
        topics = _unit_topics(unit, group_topics, ("capacity_projects",), rules)
        store.add(
            unit,
            topics,
            _timeline_reasons(unit, downstream),
            len(topics) + 4,
            selection_id,
        )
    return added


def _add_timeline_windows(
    store: _CandidateStore,
    group_id: str,
    members: Sequence[NarrativeUnit],
    topics: tuple[str, ...],
    signals: _GroupSignals,
    rules: GroupCandidateRules,
) -> set[str]:
    if not signals.certification_timeline:
        return set()
    added: set[str] = set()
    windows = rules.window_finder(members, rules.project_certification_timeline)
    for index, (start, end) in enumerate(windows):
        start, end = _expand_timeline_range(members, start, end)
        added.update(
            _add_timeline_window(
                store,
                group_id=group_id,
                window_index=index,
                members=members[start : end + 1],
                group_topics=topics,
                rules=rules,
            )
        )
    return added


def _expand_extension_range(
    members: Sequence[NarrativeUnit], start: int, end: int
) -> tuple[int, int]:
    return (
        _extension_start(members, start),
        _extension_end(members, end),
    )


def _extension_start(members: Sequence[NarrativeUnit], start: int) -> int:
    if start == 0:
        return start
    prefix = members[start - 1]
    if prefix.source_role != members[start].source_role:
        return start
    text = prefix.raw_text.strip()
    return start - 1 if len(text) <= 160 and not _ENDS_SENTENCE.search(text) else start


def _extension_end(members: Sequence[NarrativeUnit], end: int) -> int:
    if end + 1 >= len(members):
        return end
    continuation = members[end + 1]
    if continuation.source_role != members[end].source_role:
        return end
    if len(continuation.raw_text.strip()) > 160:
        return end
    return end if _ENDS_SENTENCE.search(members[end].raw_text.strip()) else end + 1


def _add_extension_window(
    store: _CandidateStore,
    *,
    group_id: str,
    window_index: int,
    members: Sequence[NarrativeUnit],
    topics: tuple[str, ...],
    rules: GroupCandidateRules,
) -> set[str]:
    selection_id = f"{group_id}:downstream-extension:{window_index}"
    added: set[str] = set()
    for unit in members:
        if not _usable_unit(unit, rules):
            continue
        if not store.assign_group(unit.unit_id, selection_id):
            continue
        added.add(unit.unit_id)
        if store.boost(unit.unit_id, "downstream_business_extension", 3):
            continue
        unit_topics = _unit_topics(unit, topics, ("capacity_projects",), rules)
        store.add(
            unit,
            unit_topics,
            (
                "business_narrative_signal",
                "downstream_business_extension",
                "project_plan_or_status",
                "pdf_visual_context_group",
            ),
            len(unit_topics) + 3,
            selection_id,
        )
    return added


def _add_extension_windows(
    store: _CandidateStore,
    group_id: str,
    members: Sequence[NarrativeUnit],
    topics: tuple[str, ...],
    signals: _GroupSignals,
    rules: GroupCandidateRules,
) -> set[str]:
    if not signals.downstream_extension:
        return set()
    added: set[str] = set()
    windows = rules.window_finder(members, rules.downstream_extension)
    for index, (start, end) in enumerate(windows):
        start, end = _expand_extension_range(members, start, end)
        added.update(
            _add_extension_window(
                store,
                group_id=group_id,
                window_index=index,
                members=members[start : end + 1],
                topics=topics,
                rules=rules,
            )
        )
    return added


def _coverage_reasons(unit: NarrativeUnit) -> tuple[str, ...]:
    reasons = [
        "business_narrative_signal",
        "quantified_market_coverage_target",
        "project_plan_or_status",
        "pdf_visual_context_group",
    ]
    if len(unit.raw_text.strip()) <= 12:
        reasons.append("short_fragment_continuation")
    return tuple(reasons)


def _add_coverage_window(
    store: _CandidateStore,
    *,
    group_id: str,
    window_index: int,
    members: Sequence[NarrativeUnit],
    topics: tuple[str, ...],
    rules: GroupCandidateRules,
) -> set[str]:
    selection_id = f"{group_id}:market-coverage-target:{window_index}"
    added: set[str] = set()
    for unit in members:
        if not _usable_unit(unit, rules):
            continue
        if not store.assign_group(unit.unit_id, selection_id):
            continue
        added.add(unit.unit_id)
        if store.boost(unit.unit_id, "quantified_market_coverage_target", 4):
            continue
        unit_topics = _unit_topics(unit, topics, ("core_business",), rules)
        store.add(
            unit,
            unit_topics,
            _coverage_reasons(unit),
            len(unit_topics) + 4,
            selection_id,
        )
    return added


def _add_coverage_windows(
    store: _CandidateStore,
    group_id: str,
    members: Sequence[NarrativeUnit],
    topics: tuple[str, ...],
    signals: _GroupSignals,
    rules: GroupCandidateRules,
) -> set[str]:
    if not signals.market_coverage_target:
        return set()
    added: set[str] = set()
    windows = rules.window_finder(members, rules.quantified_market_coverage_target)
    for index, (start, end) in enumerate(windows):
        added.update(
            _add_coverage_window(
                store,
                group_id=group_id,
                window_index=index,
                members=members[start : end + 1],
                topics=topics,
                rules=rules,
            )
        )
    return added


def _merge_fact_windows(
    windows: Sequence[tuple[int, int]],
) -> tuple[tuple[int, int], ...]:
    """Union overlapping minimal windows so one fact locus stays one group."""
    merged: list[tuple[int, int]] = []
    for start, end in sorted(windows):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return tuple(merged)


def _add_operating_fact_windows(
    store: _CandidateStore,
    group_id: str,
    members: Sequence[NarrativeUnit],
    topics: tuple[str, ...],
    rules: GroupCandidateRules,
) -> set[str]:
    """Select minimal unit windows whose joined text expresses one fact."""
    added: set[str] = set()
    windows = _merge_fact_windows(rules.window_finder(members, OPERATING_FACT_JOIN))
    for index, (start, end) in enumerate(windows):
        window_members = members[start : end + 1]
        window_text = "".join(unit.raw_text for unit in window_members)
        if len(window_text) > PROJECT_CHARACTER_WINDOW:
            continue
        if _invalid_group(window_text, rules):
            continue
        fact = detect_operating_fact(window_text)
        if not fact.eligible or not fact.reasons:
            continue
        selection_id = f"{group_id}:operating-fact:{index}"
        for unit in window_members:
            if not _usable_unit(unit, rules):
                continue
            if not store.assign_group(unit.unit_id, selection_id):
                continue
            added.add(unit.unit_id)
            if store.boost(unit.unit_id, fact.reasons[0], fact.score):
                continue
            unit_topics = _unit_topics(
                unit, topics, fact.topics or ("core_business",), rules
            )
            store.add(
                unit,
                unit_topics,
                _member_reasons(
                    unit,
                    (
                        "business_narrative_signal",
                        "pdf_visual_context_group",
                        *fact.reasons,
                    ),
                ),
                len(unit_topics) + fact.score,
                selection_id,
            )
    return added


def _general_relevant(signals: _GroupSignals, in_context: bool) -> bool:
    return any(
        (
            signals.event,
            signals.positioning,
            signals.business_risk,
            signals.project_rationale,
            signals.new_product_milestone,
            signals.project,
            signals.market_coverage_target,
            signals.progress and signals.current_industry,
            in_context,
        )
    )


def _section_barrier(unit: NarrativeUnit, rules: GroupCandidateRules) -> bool:
    return (
        _match(rules.project_heading, unit.raw_text)
        or _match(rules.business_heading, unit.raw_text)
        or _match(rules.table_of_contents, unit.raw_text)
    )


def _invalid_group(text: str, rules: GroupCandidateRules) -> bool:
    if len(text) < 12:
        return True
    if _match(rules.table_of_contents, text):
        return True
    if _match(rules.accounting_context, text):
        return True
    return _match(rules.static_definition, text)


def _general_topics(
    topics: tuple[str, ...],
    signals: _GroupSignals,
    in_project: bool,
    in_business: bool,
    fact: OperatingFact,
) -> tuple[str, ...]:
    if topics:
        return topics
    if fact.eligible and fact.topics:
        return fact.topics
    if any(
        (
            in_project,
            signals.project,
            signals.business_risk,
            signals.market_coverage_target,
        )
    ):
        return ("capacity_projects",)
    if in_business:
        return ("core_business",)
    return ("new_business",)


def _general_reasons(
    signals: _GroupSignals,
    in_project: bool,
    in_business: bool,
    fact: OperatingFact,
) -> tuple[str, ...]:
    choices = (
        (signals.progress, "progress_or_change_language"),
        (signals.event, "specific_business_event"),
        (signals.positioning, "specific_emerging_business_positioning"),
        (signals.business_risk, "business_risk_or_constraint"),
        (signals.direct_capacity_constraint, "direct_capacity_constraint"),
        (signals.long_customer_qualification, "long_customer_qualification_cycle"),
        (signals.market_coverage_target, "quantified_market_coverage_target"),
        (signals.permit_milestone, "permit_acquired_milestone"),
        (signals.new_product_milestone, "new_product_commercialization_milestone"),
        (signals.project_rationale, "specific_project_rationale"),
        (signals.project or in_project, "project_plan_or_status"),
        (in_project, "project_section_context"),
        (in_business, "business_section_context"),
        (signals.current_industry, "current_industry_context"),
    )
    return tuple(
        dict.fromkeys(
            (
                "business_narrative_signal",
                "pdf_visual_context_group",
                *fact.reasons,
                *(reason for enabled, reason in choices if enabled),
            )
        )
    )


def _general_score(
    topics: tuple[str, ...],
    signals: _GroupSignals,
    project_score: int | None,
    business_score: int | None,
    fact: OperatingFact,
) -> int:
    weights = (
        (signals.progress, 2),
        (signals.event, 3),
        (signals.positioning, 2),
        (signals.business_risk, 2),
        (signals.direct_capacity_constraint, 2),
        (signals.long_customer_qualification, 2),
        (signals.permit_milestone, 2),
        (signals.new_product_milestone, 2),
        (signals.project_rationale, 4),
        (signals.market_coverage_target, 4),
    )
    return (
        8
        + len(topics)
        + sum(weight for enabled, weight in weights if enabled)
        + (project_score or 0)
        + (business_score or 0)
        + fact.score
    )


def _outside_page_body(unit: NarrativeUnit) -> bool:
    bbox = unit.metadata.get("bbox")
    if not isinstance(bbox, Sequence) or len(bbox) != 4:
        return False
    y = float(bbox[1])
    return y < 60.0 or y > 750.0


def _member_reasons(unit: NarrativeUnit, reasons: tuple[str, ...]) -> tuple[str, ...]:
    if unit.source_role == "management":
        return (*reasons, "management_statement")
    return reasons


def _add_general_members(
    store: _CandidateStore,
    *,
    group_id: str | None,
    members: Sequence[NarrativeUnit],
    excluded_ids: set[str],
    topics: tuple[str, ...],
    reasons: tuple[str, ...],
    score: int,
    rules: GroupCandidateRules,
    character_budget: int,
) -> None:
    remaining = character_budget
    for unit in members:
        if not _usable_unit(unit, rules):
            continue
        if unit.unit_id in excluded_ids:
            # Window-selected text still occupies the group's reading window.
            remaining -= len(unit.raw_text)
            continue
        if _outside_page_body(unit):
            continue
        size = len(unit.raw_text)
        if size > remaining:
            break
        remaining -= size
        member_topics = rules.topics(unit.raw_text) or topics
        store.add(unit, member_topics, _member_reasons(unit, reasons), score, group_id)


def _add_completion_members(
    store: _CandidateStore,
    *,
    group_id: str,
    linkable: bool,
    members: Sequence[NarrativeUnit],
    hit_indices: Sequence[int],
    excluded_ids: set[str],
    topics: tuple[str, ...],
    reasons: tuple[str, ...],
    score: int,
    rules: GroupCandidateRules,
) -> None:
    remaining = PROJECT_CHARACTER_WINDOW
    assigned: set[int] = set()
    for hit in hit_indices:
        anchor: str | None = None
        if linkable:
            anchor = store.group_ids.get(members[hit].unit_id) or group_id
        indices = completion_indices(
            members,
            hit,
            barrier=lambda unit: _section_barrier(unit, rules),
        )
        for index in indices:
            if index in assigned:
                continue
            unit = members[index]
            if not _usable_unit(unit, rules) or unit.unit_id in excluded_ids:
                continue
            if _outside_page_body(unit):
                continue
            size = len(unit.raw_text)
            if size > remaining:
                return
            remaining -= size
            assigned.add(index)
            member_topics = rules.topics(unit.raw_text) or topics
            store.add(
                unit, member_topics, _member_reasons(unit, reasons), score, anchor
            )


def _enrich_group(
    store: _CandidateStore,
    group: PdfContextGroup,
    initial_ids: frozenset[str],
    project_scores: Mapping[str, int],
    business_scores: Mapping[str, int],
    rules: GroupCandidateRules,
) -> None:
    group_id, members, text = group
    if not members:
        return
    topics = rules.topics(text)
    signals = _signals(text, topics, rules)
    fact = rules.operating_facts(text)
    in_project = group_id in project_scores
    in_business = group_id in business_scores
    in_context = in_project or in_business
    special_ids = _special_ids(
        store, group_id, members, topics, signals, rules, in_context=in_context
    )
    base_relevant = _general_relevant(signals, in_context)
    if not _expand_general(text, topics, signals, in_context, rules, fact):
        return
    earned = fact if fact.eligible and not base_relevant else _EMPTY_FACT
    topics = _general_topics(topics, signals, in_project, in_business, earned)
    reasons = _general_reasons(signals, in_project, in_business, earned)
    score = _general_score(
        topics,
        signals,
        project_scores.get(group_id),
        business_scores.get(group_id),
        earned,
    )
    linkable = members_linkable(members)
    hit_indices = [
        index for index, unit in enumerate(members) if unit.unit_id in initial_ids
    ]
    if hit_indices and not in_context:
        _add_completion_members(
            store,
            group_id=group_id,
            linkable=linkable,
            members=members,
            hit_indices=hit_indices,
            excluded_ids=special_ids,
            topics=topics,
            reasons=reasons,
            score=score,
            rules=rules,
        )
        return
    _add_general_members(
        store,
        group_id=group_id if linkable else None,
        members=members,
        excluded_ids=special_ids,
        topics=topics,
        reasons=reasons,
        score=score,
        rules=rules,
        character_budget=(
            BUSINESS_CHARACTER_WINDOW if in_business else PROJECT_CHARACTER_WINDOW
        ),
    )


def _special_ids(
    store: _CandidateStore,
    group_id: str,
    members: Sequence[NarrativeUnit],
    topics: tuple[str, ...],
    signals: _GroupSignals,
    rules: GroupCandidateRules,
    *,
    in_context: bool,
) -> set[str]:
    if not members_linkable(members):
        return set()
    ids = _add_timeline_windows(store, group_id, members, topics, signals, rules)
    ids.update(_add_extension_windows(store, group_id, members, topics, signals, rules))
    ids.update(_add_coverage_windows(store, group_id, members, topics, signals, rules))
    if not in_context:
        # Section-context groups are added as one atomic unit below; carving
        # fact windows out of them would split an existing context bundle.
        ids.update(_add_operating_fact_windows(store, group_id, members, topics, rules))
    return ids


def _expand_general(
    text: str,
    topics: tuple[str, ...],
    signals: _GroupSignals,
    in_context: bool,
    rules: GroupCandidateRules,
    fact: OperatingFact,
) -> bool:
    base_relevant = _general_relevant(signals, in_context)
    if not topics and not in_context and not base_relevant and not fact.eligible:
        return False
    if _invalid_group(text, rules) or not (base_relevant or fact.eligible):
        return False
    return True


def enrich_context_groups(
    groups: Sequence[PdfContextGroup],
    *,
    initial_candidates: Sequence[EvidenceCandidate],
    initial_group_ids: Mapping[str, str],
    project_scores: Mapping[str, int],
    business_scores: Mapping[str, int],
    rules: GroupCandidateRules,
) -> GroupEnrichmentResult:
    """Add joined visual context while retaining replayable member locators."""
    store = _CandidateStore(list(initial_candidates), dict(initial_group_ids))
    initial_ids = frozenset(candidate.unit.unit_id for candidate in initial_candidates)
    for group in groups:
        text = group[2]
        if _match(rules.project_heading, text) or _match(rules.business_heading, text):
            continue
        _enrich_group(store, group, initial_ids, project_scores, business_scores, rules)
    return GroupEnrichmentResult(
        candidates=tuple(store.candidates),
        group_ids=MappingProxyType(store.group_ids),
    )


__all__ = [
    "GroupCandidateRules",
    "GroupEnrichmentResult",
    "enrich_context_groups",
]
