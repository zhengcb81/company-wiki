"""Section stack: headings, parents, bodies, and bounded cross-page carry.

The legacy selector reset its section context on every page, so a project
whose text ran past a page break lost its subject.  The opposite failure -- an
unbounded carry that merges everything after a heading -- is equally wrong.
This module therefore carries context forward under an explicit bound and stops
at the first new heading at the same or a shallower level.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from copy import copy
import re
from typing import cast
from ..observation_adapter import _is_item_label, _is_item_heading, _part_heading_level

from . import layout as layout_mod
from .contract import (
    MAX_CONTINUATION_PAGES,
    MAX_CONTINUATION_UNITS,
)
from .contract import ObservationUnit

_SECTION_ROLE_HINTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("募集资金", "募投", "发行", "可转债", "资金用途", "本次发行"), "fundraising"),
    (
        (
            "管理层讨论",
            "经营情况讨论",
            "董事会报告",
            "业务回顾",
            "business review",
            "management discussion",
            "md&a",
        ),
        "management_discussion",
    ),
    (("风险", "risk factor", "risk factors"), "risk"),
    (("行业", "industry", "competition", "竞争"), "industry"),
    (("展望", "outlook", "future plan", "未来", "发展战略"), "outlook"),
    (("业务", "主营业务", "产品", "经营模式", "business", "products"), "business"),
    (("投资者关系", "问答", "问题", "questions and answers", "q&a"), "questions"),
    (
        ("财务报表", "财务报告", "附注", "financial statements", "notes to"),
        "financial_notes",
    ),
    (
        (
            "释义",
            "目录",
            "公司治理",
            "环境",
            "社会",
            "责任",
            "签字",
            "确认意见",
            "definitions",
            "corporate governance",
        ),
        "administrative",
    ),
    (
        (
            "产能",
            "产量",
            "销量",
            "门店",
            "客户",
            "订单",
            "operating metrics",
            "kpi",
            "key metrics",
        ),
        "operating_metrics",
    ),
)


@dataclass
class SectionDraft:
    section_id: str
    heading_ids: list[str] = field(default_factory=list)
    body_ids: list[str] = field(default_factory=list)
    parent_id: str | None = None
    depth: int | None = None
    language: str | None = None
    column: int | None = None
    section_role: str = "unknown"
    basis: list[str] = field(default_factory=list)
    confidence: str = "unknown"
    pages: list[int] = field(default_factory=list)
    continuation_events: int = 0


@dataclass(frozen=True)
class SectionBuild:
    sections: tuple[SectionDraft, ...]
    diagnostics: tuple[dict, ...]
    unit_section: dict[str, str]


def _role_for_heading(text: str, fallback: str) -> str:
    lowered = text.casefold()
    for needles, role in _SECTION_ROLE_HINTS:
        if any(needle in lowered for needle in needles):
            return role
    return fallback


def _dominant_language(
    index: dict[str, ObservationUnit], member_ids: Sequence[str]
) -> str | None:
    counts: dict[str, int] = {}
    for unit_id in member_ids:
        unit = index.get(unit_id)
        if unit is None or not unit.language:
            continue
        counts[unit.language] = counts.get(unit.language, 0) + 1
    if not counts:
        return None
    return max(sorted(counts), key=lambda key: counts[key])


def _display_heading_groups(units, excluded):
    tables: dict[str, list[ObservationUnit]] = {}
    for unit in units:
        if unit.table_id and unit.unit_id not in excluded:
            tables.setdefault(unit.table_id, []).append(unit)
    groups = {}
    for members in tables.values():
        if (
            len(members) < 2
            or len({u.row for u in members}) != 1
            or any(u.row is None or u.column_index is None for u in members)
        ):
            continue
        labels = [u for u in members if _is_item_label(u.text)]
        if len(labels) != 1:
            continue
        label = labels[0]
        titles = [u for u in members if u is not label]
        if any(
            cast(int, u.column_index) <= cast(int, label.column_index)
            or not any(ch.isalpha() for ch in u.text)
            or re.match(
                r"^(?:USD|RMB|CNY|HKD|EUR|GBP|JPY|US\$|HK\$|人民币)\s*[\d$€£¥.,%+-]",
                u.text,
                re.IGNORECASE,
            )
            or u.text.strip().casefold()
            in {"usd", "rmb", "cny", "hkd", "eur", "gbp", "jpy", "page", "page number"}
            for u in titles
        ):
            continue
        groups[label.unit_id] = [label] + sorted(titles, key=lambda u: cast(int, u.column_index))
    return groups


def build_sections(
    units: Sequence[ObservationUnit],
    ordering: layout_mod.Ordering,
    *,
    limits: dict[str, int],
) -> SectionBuild:
    """Build the logical section tree over the ordered units.

    TOC entries and repeated running headers are excluded from the body and
    reported through diagnostics by the caller.  Body units stay in original
    reading order and a section may span pages.
    """
    diagnostics: list[dict] = []
    toc_ids = ordering.toc_ids
    furniture = ordering.running_header_ids
    has_heading_evidence = any(
        unit.heading_level is not None or unit.dom_path is not None
        for unit in ordering.ordered
    )

    sections: list[SectionDraft] = []
    unit_section: dict[str, str] = {}
    stack: list[SectionDraft] = []
    counter = 0
    last_page: int | None = None
    carry_units = 0
    display_headings = _display_heading_groups(
        ordering.ordered, set(toc_ids) | set(furniture)
    )
    display_title_ids = {
        unit.unit_id for group in display_headings.values() for unit in group[1:]
    }
    active_part_depth = None
    active_item = None
    previous_source: str | None = None
    source_seen = False

    def open_section(
        unit: ObservationUnit,
        heading_units=None,
        depth_override=None,
        contextual_outline=False,
    ) -> SectionDraft:
        nonlocal counter
        counter += 1
        depth = (
            depth_override
            if contextual_outline and (unit.dom_path is None or unit.heading_level_source == "numbering")
            else unit.heading_level
            if unit.heading_level is not None
            else (
                depth_override
                if depth_override is not None
                else layout_mod.heading_depth(unit)
            )
        )
        heading_units = heading_units or [unit]
        basis = ["reading_order"]
        if unit.heading_level is not None:
            basis.append("heading_level")
        elif unit.dom_path:
            basis.append("dom_path")
        elif depth is not None:
            basis.append("heading_numbering")
        if unit.column is not None:
            basis.append("layout_column")

        while stack and depth is not None and stack[-1].depth is not None:
            if stack[-1].depth < depth:
                break
            stack.pop()
        parent = stack[-1] if stack and depth is not None else None

        draft = SectionDraft(
            section_id=f"s{counter}",
            heading_ids=[heading.unit_id for heading in heading_units],
            parent_id=parent.section_id if parent is not None else None,
            depth=depth,
            language=unit.language,
            column=unit.column,
            basis=basis,
            pages=[unit.page] if unit.page is not None else [],
        )
        heading_text = " ".join(heading.text for heading in heading_units)
        draft.section_role = _role_for_heading(heading_text, "unknown")
        if len(heading_units) > 1:
            draft.basis.append("single_row_display_heading")
        sections.append(draft)
        stack.append(draft)
        return draft

    for unit in ordering.ordered:
        if source_seen and unit.source_id != previous_source:
            # Attribution changes are real boundaries even on a pageless
            # projection. A prior parent's heading cannot classify this body.
            stack.clear()
            active_part_depth = None
            active_item = None
            last_page = None
            carry_units = 0
        previous_source = unit.source_id
        source_seen = True
        if unit.unit_id in toc_ids:
            continue
        if unit.unit_id in furniture or unit.unit_id in display_title_ids:
            continue
        compound = display_headings.get(unit.unit_id)
        is_heading = layout_mod.is_heading(unit, toc_ids=toc_ids)
        if (
            unit.table_id
            and compound is None
            and unit.heading_level is None
            and unit.kind not in {"heading", "html_heading"}
        ):
            is_heading = False  # numeric/TOC/multi-row tables are not display headings
        if compound is not None or is_heading:
            part = _part_heading_level(unit.text)
            item = _is_item_heading(unit.text)
            relative_outline = False
            if part is not None:
                active_part_depth = unit.heading_level or part
                active_item = None
            override = (
                (active_part_depth + 1 if active_part_depth is not None else 1)
                if item
                else None
            )
            if not item and part is None and active_part_depth is not None:
                # Notes/numbered sub-outlines are relative to the explicit Item,
                # never new document roots. Actual DOM heading levels win.
                if active_item is not None and active_item in stack:
                    numbered = copy(unit)
                    numbered.heading_level = None
                    own_depth = layout_mod.heading_depth(numbered)
                    if own_depth is not None and active_item.depth is not None:
                        override = active_item.depth + own_depth
                        relative_outline = True
            current = open_section(
                unit,
                heading_units=compound,
                depth_override=override,
                contextual_outline=relative_outline,
            )
            if relative_outline:
                current.basis.append("relative_item_numbering")
            if item:
                active_item = current
            last_page = unit.page if unit.page is not None else last_page
            carry_units = 0
            continue

        if not stack:
            # A body unit before any heading: keep it addressable so it is
            # never silently dropped, and flag the gap.
            counter += 1
            draft = SectionDraft(
                section_id=f"s{counter}",
                heading_ids=[],
                depth=None,
                basis=["reading_order", "no_preceding_heading"],
                confidence="low",
                section_role="unknown",
            )
            sections.append(draft)
            stack.append(draft)

        current = stack[-1]
        if unit.page is not None and last_page is not None and unit.page != last_page:
            gap = unit.page - last_page
            if gap > MAX_CONTINUATION_PAGES:
                # Too far to still be the same body of text; start a fresh
                # anonymous section rather than silently adopting the old
                # subject across a large gap.
                diagnostics.append(
                    {
                        "code": "CONTINUATION_GAP",
                        "unit_ids": [unit.unit_id],
                        "detail": (
                            f"page gap {gap} exceeds MAX_CONTINUATION_PAGES="
                            f"{MAX_CONTINUATION_PAGES}; previous section context not carried"
                        ),
                    }
                )
                counter += 1
                draft = SectionDraft(
                    section_id=f"s{counter}",
                    heading_ids=[],
                    depth=None,
                    parent_id=None,
                    basis=["reading_order", "continuation_limit"],
                    confidence="low",
                    section_role="unknown",
                    pages=[unit.page],
                )
                sections.append(draft)
                stack.append(draft)
                carry_units = 0
                current = draft
            else:
                current.continuation_events += 1
        if carry_units >= MAX_CONTINUATION_UNITS and not current.heading_ids:
            diagnostics.append(
                {
                    "code": "CONTINUATION_LIMIT",
                    "unit_ids": [unit.unit_id],
                    "detail": "bounded carry exhausted for an unheaded section",
                }
            )
        current.body_ids.append(unit.unit_id)
        if unit.page is not None and unit.page not in current.pages:
            current.pages.append(unit.page)
        unit_section[unit.unit_id] = current.section_id
        carry_units += 1
        if unit.page is not None:
            last_page = unit.page

    if not has_heading_evidence and sections:
        diagnostics.append(
            {
                "code": "NO_HEADING_EVIDENCE",
                "unit_ids": [sections[0].section_id],
                "detail": "no heading_level, heading kind, or heading numbering present",
            }
        )

    by_id = {unit.unit_id: unit for unit in units}
    for draft in sections:
        if draft.language is None:
            draft.language = _dominant_language(
                by_id, draft.heading_ids + draft.body_ids
            )
        inconsistent = _layout_inconsistency(by_id, draft)
        if inconsistent is not None:
            draft.basis.append("layout_inconsistent")
            diagnostics.append(
                {
                    "code": "LAYOUT_INCONSISTENT",
                    "unit_ids": list(draft.heading_ids),
                    "detail": inconsistent,
                }
            )
        draft.confidence = _section_confidence(draft, has_heading_evidence)
        if len(draft.pages) > 1:
            draft.basis.append("spans_pages")
        deduped: list[str] = []
        seen: set[str] = set()
        for basis in draft.basis:
            if basis not in seen:
                seen.add(basis)
                deduped.append(basis)
        draft.basis = deduped
        if (
            limits["max_group_members"]
            and len(draft.body_ids) > limits["max_group_members"]
        ):
            diagnostics.append(
                {
                    "code": "SECTION_OVERSIZED",
                    "unit_ids": [draft.section_id],
                    "detail": (
                        f"{len(draft.body_ids)} body units exceed "
                        f"max_group_members={limits['max_group_members']}"
                    ),
                }
            )

    _inherit_parent_role(sections)

    return SectionBuild(
        sections=tuple(sections),
        diagnostics=tuple(diagnostics),
        unit_section=unit_section,
    )


def _inherit_parent_role(sections: Sequence[SectionDraft]) -> None:
    """Give an unresolved sub-section its parent's role.

    A sub-heading such as ``（一）项目投资计划`` names no chapter topic on its
    own; what it is about is decided by the chapter it sits in.  Without
    inheritance every sub-section of a fundraising chapter stayed ``unknown``,
    which then ranked behind every known role and buried the project tables
    that chapter exists to carry.  A role that was positively recognised is
    never overwritten, and the inheritance is recorded in the section's basis
    so a consumer can tell an inherited role from a matched one.
    """
    by_id = {section.section_id: section for section in sections}
    for section in sections:
        if section.section_role != "unknown" or section.parent_id is None:
            continue
        parent = by_id.get(section.parent_id)
        if parent is None or parent.section_role == "unknown":
            continue
        section.section_role = parent.section_role
        if "role_inherited" not in section.basis:
            section.basis.append("role_inherited")


def _layout_inconsistency(
    index: dict[str, ObservationUnit], draft: SectionDraft
) -> str | None:
    """Return a reason when a heading's own layout evidence contradicts itself.

    A heading may only be ``high`` confidence when nothing about its declared
    layout disagrees.  A box with ``x1 <= x0``, a box that falls outside its
    page, or a lane index that contradicts the box's position all count.
    """
    flagged = [
        index[unit_id]
        for unit_id in draft.heading_ids
        if unit_id in index and index[unit_id].layout_inconsistent
    ]
    if not flagged:
        return None
    return "declared layout contradicts itself for " + ", ".join(
        unit.unit_id for unit in flagged
    )


def _section_confidence(draft: SectionDraft, has_heading_evidence: bool) -> str:
    if "layout_inconsistent" in draft.basis:
        # The heading still exists, but its own layout evidence is unusable,
        # so nothing above ``low`` may be claimed.
        return "low"
    if not draft.heading_ids and draft.confidence == "low":
        return "low"
    if not draft.heading_ids:
        return "unknown"
    if "heading_level" in draft.basis or "dom_path" in draft.basis:
        return "high"
    if "heading_numbering" in draft.basis:
        return "medium"
    if not has_heading_evidence:
        return "low"
    return "medium"


__all__ = ["SectionBuild", "SectionDraft", "build_sections"]
