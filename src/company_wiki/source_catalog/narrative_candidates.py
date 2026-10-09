"""Typed, deterministic candidate assessment for one narrative unit."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
import re

from .n6_candidate_operating_facts import OperatingFact, detect_operating_fact
from .narrative_document import NarrativeUnit
from .narrative_visual_units import is_ocr_unit, ocr_identity


TopicClassifier = Callable[[str], tuple[str, ...]]
FinancialClassifier = Callable[[NarrativeUnit, Sequence[str]], bool]
OperatingFactDetector = Callable[[str], OperatingFact]
_NEVER = re.compile(r"(?!x)x")
_EXCLUDED_ROLES = frozenset(
    {"analyst", "investor_question", "operator", "editorial", "qa_text_shadow"}
)
_CURRENT_BUSINESS_TOPICS = frozenset(
    {
        "core_business",
        "new_business",
        "overseas",
        "products_rd",
        "capacity_projects",
        "orders_customers",
    }
)


def _no_topics(_text: str) -> tuple[str, ...]:
    return ()


def _not_financial(_unit: NarrativeUnit, _topics: Sequence[str]) -> bool:
    return False


@dataclass(frozen=True)
class CandidateRules:
    topics: TopicClassifier = _no_topics
    financial_table: FinancialClassifier = _not_financial
    operating_facts: OperatingFactDetector = detect_operating_fact
    high_value_event: re.Pattern[str] = _NEVER
    project_plan: re.Pattern[str] = _NEVER
    strategic_plan: re.Pattern[str] = _NEVER
    downstream_extension: re.Pattern[str] = _NEVER
    positioning: re.Pattern[str] = _NEVER
    business_risk: re.Pattern[str] = _NEVER
    project_rationale: re.Pattern[str] = _NEVER
    progress: re.Pattern[str] = _NEVER
    business_progress_action: re.Pattern[str] = _NEVER
    direct_capacity_constraint: re.Pattern[str] = _NEVER
    long_customer_qualification: re.Pattern[str] = _NEVER
    project_certification_timeline: re.Pattern[str] = _NEVER
    permit_milestone: re.Pattern[str] = _NEVER
    new_product_milestone: re.Pattern[str] = _NEVER
    recency: re.Pattern[str] = _NEVER
    table_of_contents: re.Pattern[str] = _NEVER
    accounting_context: re.Pattern[str] = _NEVER
    heading_only: re.Pattern[str] = _NEVER
    static_definition: re.Pattern[str] = _NEVER


@dataclass(frozen=True)
class EvidenceCandidate:
    unit: NarrativeUnit
    topics: tuple[str, ...]
    reasons: tuple[str, ...]
    score: int


@dataclass(frozen=True)
class CandidateAssessment:
    candidate: EvidenceCandidate | None
    dropped_financial: bool = False


@dataclass(frozen=True)
class _Signals:
    progress: bool
    event: bool
    positioning: bool
    business_risk: bool
    direct_capacity_constraint: bool
    long_customer_qualification: bool
    project_certification_timeline: bool
    permit_milestone: bool
    new_product_milestone: bool
    project_rationale: bool
    downstream_extension: bool
    current_industry: bool
    current_business_progress: bool
    project: bool


def _match(pattern: re.Pattern[str], text: str) -> bool:
    return pattern.search(text) is not None


def _signals(text: str, topics: tuple[str, ...], rules: CandidateRules) -> _Signals:
    certification = _match(rules.project_certification_timeline, text)
    return _Signals(
        progress=_match(rules.progress, text),
        event=_match(rules.high_value_event, text),
        positioning=_match(rules.positioning, text),
        business_risk=_match(rules.business_risk, text),
        direct_capacity_constraint=_match(rules.direct_capacity_constraint, text),
        long_customer_qualification=_match(rules.long_customer_qualification, text),
        project_certification_timeline=certification,
        permit_milestone=_match(rules.permit_milestone, text),
        new_product_milestone=_match(rules.new_product_milestone, text),
        project_rationale=_match(rules.project_rationale, text),
        downstream_extension=_match(rules.downstream_extension, text),
        current_industry=(
            "industry_dynamics" in topics and _match(rules.recency, text)
        ),
        current_business_progress=(
            bool(_CURRENT_BUSINESS_TOPICS.intersection(topics))
            and _match(rules.progress, text)
            and _match(rules.recency, text)
            and _match(rules.business_progress_action, text)
        ),
        project=any(
            (
                _match(rules.project_plan, text),
                _match(rules.strategic_plan, text),
                certification,
            )
        ),
    )


def _pre_signal(text: str, rules: CandidateRules) -> bool:
    return any(
        _match(pattern, text)
        for pattern in (
            rules.high_value_event,
            rules.project_plan,
            rules.strategic_plan,
            rules.downstream_extension,
            rules.positioning,
            rules.business_risk,
            rules.project_rationale,
            rules.project_certification_timeline,
        )
    )


def _excluded(unit: NarrativeUnit, rules: CandidateRules) -> bool:
    if len(unit.raw_text) < 12:
        return True
    if _match(rules.table_of_contents, unit.raw_text):
        return True
    if _match(rules.accounting_context, unit.raw_text):
        return True
    return _match(rules.heading_only, unit.raw_text)


def _eligible(signals: _Signals) -> bool:
    core = (
        signals.event,
        signals.project,
        signals.positioning,
        signals.business_risk,
        signals.project_rationale,
        signals.project_certification_timeline,
        signals.progress and signals.current_industry,
        signals.current_business_progress,
    )
    return any(core)


def _fallback_topics(
    topics: tuple[str, ...], signals: _Signals, fact: OperatingFact
) -> tuple[str, ...]:
    if topics:
        return topics
    if fact.eligible and fact.topics:
        return fact.topics
    if signals.event or signals.positioning:
        return ("new_business",)
    return ("capacity_projects",)


def _reasons(
    signals: _Signals, source_role: str, fact: OperatingFact
) -> tuple[str, ...]:
    choices = (
        (signals.progress, "progress_or_change_language"),
        (signals.event, "specific_business_event"),
        (signals.positioning, "specific_emerging_business_positioning"),
        (signals.business_risk, "business_risk_or_constraint"),
        (signals.direct_capacity_constraint, "direct_capacity_constraint"),
        (signals.long_customer_qualification, "long_customer_qualification_cycle"),
        (signals.project_certification_timeline, "project_certification_timeline"),
        (signals.permit_milestone, "permit_acquired_milestone"),
        (signals.new_product_milestone, "new_product_commercialization_milestone"),
        (signals.project_rationale, "specific_project_rationale"),
        (signals.downstream_extension, "downstream_business_extension"),
        (signals.project, "project_plan_or_status"),
        (signals.current_industry, "current_industry_context"),
        (signals.current_business_progress, "current_business_progress"),
        (source_role == "management", "management_statement"),
    )
    return tuple(
        dict.fromkeys(
            (
                "business_narrative_signal",
                *fact.reasons,
                *(reason for enabled, reason in choices if enabled),
            )
        )
    )


def _score(
    unit: NarrativeUnit, topics: tuple[str, ...], signals: _Signals, fact: OperatingFact
) -> int:
    weighted = (
        (signals.progress, 2),
        (signals.event, 3),
        (signals.positioning, 2),
        (signals.business_risk, 2),
        (signals.direct_capacity_constraint, 2),
        (signals.long_customer_qualification, 2),
        (signals.project_certification_timeline, 4),
        (signals.permit_milestone, 2),
        (signals.new_product_milestone, 2),
        (signals.project_rationale, 4),
        (signals.downstream_extension, 3),
    )
    table_bonus = 1 if unit.unit_kind == "pdf_table_row" else 0
    return (
        len(topics)
        + sum(weight for enabled, weight in weighted if enabled)
        + table_bonus
        + fact.score
    )


_EMPTY_FACT = OperatingFact()


def assess_unit(unit: NarrativeUnit, rules: CandidateRules) -> CandidateAssessment:
    """Classify one unit without mutating selection or storage state."""
    if is_ocr_unit(unit) and ocr_identity(unit) is None:
        return CandidateAssessment(None)
    if unit.source_role in _EXCLUDED_ROLES:
        return CandidateAssessment(None)
    text = unit.raw_text
    fact = rules.operating_facts(text)
    topics = rules.topics(text)
    if rules.financial_table(unit, topics) and not fact.financial_exempt:
        return CandidateAssessment(None, dropped_financial=True)
    if not topics and not _pre_signal(text, rules) and not fact.eligible:
        return CandidateAssessment(None)
    signals = _signals(text, topics, rules)
    if _excluded(unit, rules):
        return CandidateAssessment(None)
    baseline_eligible = _eligible(signals)
    if not (baseline_eligible or fact.eligible):
        return CandidateAssessment(None)
    # Specific operating meaning remains useful even when generic progress
    # already made the unit eligible. Preserve both reasons for budget policy.
    earned = fact if fact.eligible else _EMPTY_FACT
    topics = _fallback_topics(topics, signals, fact)
    scope_change = any(
        reason in fact.reasons
        for reason in ("business_scope_change", "reporting_definition_change", "reporting_rename")
    )
    if _match(rules.static_definition, text) and not scope_change:
        return CandidateAssessment(None)
    return CandidateAssessment(
        EvidenceCandidate(
            unit=unit,
            topics=topics,
            reasons=_reasons(signals, unit.source_role, earned),
            score=_score(unit, topics, signals, earned),
        )
    )


__all__ = [
    "CandidateAssessment",
    "CandidateRules",
    "EvidenceCandidate",
    "assess_unit",
]
