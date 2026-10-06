"""Document-section context boundaries for narrative selection."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import re
from types import MappingProxyType

from .n6_candidate_completion import BUSINESS_CHARACTER_WINDOW, PROJECT_CHARACTER_WINDOW
from .narrative_document import NarrativeUnit


PdfContextGroup = tuple[str, tuple[NarrativeUnit, ...], str]
ScorePolicy = Callable[[str], int]


@dataclass(frozen=True)
class ContextRules:
    project_heading: re.Pattern[str]
    business_heading: re.Pattern[str]
    heading_only: re.Pattern[str]


@dataclass(frozen=True)
class SectionContext:
    project_scores: Mapping[str, int]
    business_scores: Mapping[str, int]


def _groups_by_page(
    groups: Sequence[PdfContextGroup],
) -> dict[int, list[PdfContextGroup]]:
    by_page: dict[int, list[PdfContextGroup]] = {}
    for group in groups:
        page = group[1][0].coordinates.page_number
        if page is not None:
            by_page.setdefault(page, []).append(group)
    return by_page


def _project_score(text: str) -> int:
    return 120 if re.search(r"项目建设.{0,8}必要性|项目建设必要性", text) else 80


def _business_score(_text: str) -> int:
    return 140


def _scan_page(
    groups: Sequence[PdfContextGroup],
    *,
    start_pattern: re.Pattern[str],
    heading_pattern: re.Pattern[str],
    character_budget: int,
    score_policy: ScorePolicy,
) -> dict[str, int]:
    scores: dict[str, int] = {}
    active = False
    remaining = 0
    score = 0
    for group_id, _members, text in groups:
        if start_pattern.search(text):
            active = True
            remaining = character_budget
            score = score_policy(text)
            continue
        if active and heading_pattern.search(text):
            active = False
            continue
        if not active:
            continue
        if remaining <= 0:
            active = False
            continue
        if len(text) > remaining:
            # A group that does not fit the bounded window would otherwise
            # swallow a whole page into the section context.
            active = False
            continue
        scores[group_id] = score
        remaining -= len(text)
    return scores


def _scan_pages(
    groups: Sequence[PdfContextGroup],
    *,
    start_pattern: re.Pattern[str],
    heading_pattern: re.Pattern[str],
    character_budget: int,
    score_policy: ScorePolicy,
) -> dict[str, int]:
    scores: dict[str, int] = {}
    for page_groups in _groups_by_page(groups).values():
        scores.update(
            _scan_page(
                page_groups,
                start_pattern=start_pattern,
                heading_pattern=heading_pattern,
                character_budget=character_budget,
                score_policy=score_policy,
            )
        )
    return scores


def build_section_context(
    document_kind: str,
    groups: Sequence[PdfContextGroup],
    rules: ContextRules,
) -> SectionContext:
    """Return bounded context scores for offering document sections."""
    project: dict[str, int] = {}
    business: dict[str, int] = {}
    if document_kind in {
        "convertible_bond_prospectus",
        "equity_offering_prospectus",
    }:
        project = _scan_pages(
            groups,
            start_pattern=rules.project_heading,
            heading_pattern=rules.heading_only,
            character_budget=PROJECT_CHARACTER_WINDOW,
            score_policy=_project_score,
        )
    if document_kind == "prospectus":
        business = _scan_pages(
            groups,
            start_pattern=rules.business_heading,
            heading_pattern=rules.heading_only,
            character_budget=BUSINESS_CHARACTER_WINDOW,
            score_policy=_business_score,
        )
    return SectionContext(
        project_scores=MappingProxyType(project),
        business_scores=MappingProxyType(business),
    )


__all__ = [
    "ContextRules",
    "PdfContextGroup",
    "SectionContext",
    "build_section_context",
]
