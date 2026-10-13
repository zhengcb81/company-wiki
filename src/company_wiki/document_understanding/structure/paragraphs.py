"""Remaining semantic kinds: paragraph_event, risk, background.

The rule that matters here is restraint.  A paragraph whose discourse is not
positively recognizable becomes ``background`` with ``unknown`` completeness --
the module never invents a causal reading, and never promotes an uncertain
paragraph to a confident event.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
import re

from . import layout as layout_mod
from .contract import ObservationUnit

_RISK = re.compile(
    r"风险|可能导致|不确定性|受到限制|罚款|处罚|诉讼|"
    r"risk|uncertaint|may be adversely|penalt|litigation",
    re.IGNORECASE,
)
_EVENT = re.compile(
    r"报告期内|本报告期|本期|年内|截至|已完成|已签署|已投产|已取得|新增|同比增长|"
    r"同比下降|发生|完成|签署|投产|中标|通过|获得|同比|环比|"
    r"during the (?:year|period)|completed|signed|launched|increased|decreased",
    re.IGNORECASE,
)
_BACKGROUND = re.compile(
    r"本公司|集团|公司成立于|主营业务为|主要产品|所属行业|基本情况|"
    r"the company|the group|we are|our business",
    re.IGNORECASE,
)


@dataclass
class ParagraphDraft:
    semantic_id: str
    kind: str
    member_ids: list[str]
    anchor_ids: list[str]
    section_ids: list[str] = field(default_factory=list)
    completeness: str = "unknown"
    diagnostics: list[dict] = field(default_factory=list)

    def as_wire(self) -> dict:
        return {
            "semantic_id": self.semantic_id,
            "kind": self.kind,
            "section_ids": list(self.section_ids),
            "member_unit_ids": list(self.member_ids),
            "anchor_unit_ids": list(self.anchor_ids),
            "required_context_unit_ids": list(self.anchor_ids),
            "completeness": self.completeness,
            "diagnostics": list(self.diagnostics),
        }


def classify_paragraph(text: str, section_role: str) -> tuple[str, str]:
    """Return ``(kind, completeness)`` using positive signals only."""
    if _RISK.search(text) or section_role == "risk":
        return "risk", "complete"
    if _EVENT.search(text):
        return "paragraph_event", "complete"
    if _BACKGROUND.search(text):
        return "background", "complete"
    return "background", "unknown"


def build_paragraph_units(
    units: Sequence[ObservationUnit],
    ordering: layout_mod.Ordering,
    unit_section: dict[str, str],
    section_roles: dict[str, str],
    *,
    limits: dict[str, int],
    consumed: set[str],
    start_index: int,
) -> tuple[tuple[ParagraphDraft, ...], tuple[dict, ...]]:
    """Emit one package per remaining prose unit, grouped by contiguous run.

    Grouping is by adjacency inside one section so a paragraph keeps its
    immediately continuing sentences (including across a page break) without
    merging unrelated parts of the chapter.
    """
    diagnostics: list[dict] = []
    drafts: list[ParagraphDraft] = []
    counter = start_index

    current: ParagraphDraft | None = None
    current_section: str | None = None
    previous: ObservationUnit | None = None

    def flush() -> None:
        nonlocal current
        if current is not None:
            if len(current.member_ids) > limits["max_group_members"]:
                current.completeness = "partial"
                current.diagnostics.append(
                    {
                        "code": "GROUP_BUDGET_EXCEEDED",
                        "unit_ids": list(current.member_ids[: limits["max_group_members"]]),
                        "detail": (
                            f"{len(current.member_ids)} members exceed "
                            f"max_group_members={limits['max_group_members']}"
                        ),
                    }
                )
            drafts.append(current)
        current = None

    for unit in ordering.ordered:
        if unit.unit_id in ordering.toc_ids or unit.unit_id in ordering.running_header_ids:
            continue
        if unit.unit_id in consumed or unit.is_table_furniture:
            continue
        if layout_mod.is_heading(unit):
            flush()
            previous = unit
            current_section = None
            continue

        section_id = unit_section.get(unit.unit_id)
        continues = (
            current is not None
            and previous is not None
            and section_id == current_section
            and _continues(previous, unit)
        )
        if not continues:
            flush()
            counter += 1
            role = section_roles.get(section_id or "", "unknown")
            kind, completeness = classify_paragraph(unit.text, role)
            current = ParagraphDraft(
                semantic_id=f"m{counter}",
                kind=kind,
                member_ids=[unit.unit_id],
                anchor_ids=[unit.unit_id],
                section_ids=[section_id] if section_id else [],
                completeness=completeness,
            )
            current_section = section_id
        else:
            assert current is not None
            current.member_ids.append(unit.unit_id)
        consumed.add(unit.unit_id)
        previous = unit

    flush()
    if drafts and all(draft.completeness == "unknown" for draft in drafts):
        diagnostics.append(
            {
                "code": "NO_RECOGNIZED_DISCOURSE",
                "unit_ids": [draft.member_ids[0] for draft in drafts],
                "detail": "no paragraph matched an event, risk, or background signal",
            }
        )
    return tuple(drafts), tuple(diagnostics)


def _continues(previous: ObservationUnit, current: ObservationUnit) -> bool:
    """Two prose units continue when the layout says so or the sentence does."""
    if layout_mod.continues_visually(previous, current):
        return True
    if previous.page != current.page:
        return layout_mod.continues_visually(previous, current)
    return False


__all__ = ["ParagraphDraft", "build_paragraph_units", "classify_paragraph"]
