"""Project semantic units: fundraising/expansion projects as bounded packages.

A project row is not usable evidence on its own.  ``投资总额 28000`` means
nothing without the project subject, the unit caption, the period, and the
sentence that continues onto the next page.  This module therefore binds a
project package from explicit members:

* the introduction sentence (``募集资金拟投资于以下项目``),
* the unit/currency caption,
* the table header carrying 项目名称 / 建设期 / 投资总额,
* the project's own row(s),
* the narrative paragraphs that belong to that project.

Subject switching is the failure this must avoid: when a new project heading
appears, or a new project row starts, the previous package is closed.  Nothing
is inferred about realisation status -- a plan stays written as a plan.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
import re

from . import layout as layout_mod
from .contract import ObservationUnit

_INTRO = re.compile(
    r"(?:募集资金|募投)[^。；]{0,180}(?:投资于|用于|投向)(?:以下|下列|这些).{0,12}项目"
)
_PURPOSE = re.compile(r"运用方向|投资方向|投资项目|募投项目|项目名称|资金用途")
_PROJECT_WORD = re.compile(
    r"(?:设备|装备|生产线|车间|基地|研发|材料|工厂|厂房|产业园|产品|软件|系统|平台|"
    r"中心|仓储|物流|产能|门店)"
    r".{0,30}(?:项目|建设|扩建|扩产|技改|升级|改造)"
)
_FINANCE_ONLY = re.compile(r"补充流动资金|补充营运资金|偿还|还贷|合计|总计")
_CAPTION = re.compile(r"^\s*[（(]?\s*(?:单位|币种)\s*[:：]")
_PROJECT_HEADING = re.compile(
    r"^\s*(?:第[一二三四五六七八九十百]+[节章])?\s*"
    r"(?:[一二三四五六七八九十]+[、．.]|（[一二三四五六七八九十]+）|"
    r"\([一二三四五六七八九十]+\)|\d+(?:\.\d+){0,2}[、．.]?\s)"
    r".{0,60}(?:项目|建设|扩建|扩产|技改|升级)"
)
_TABLE_ROW_SEP = "|"


@dataclass
class ProjectDraft:
    semantic_id: str
    member_ids: list[str]
    anchor_ids: list[str]
    required_context_ids: list[str]
    section_ids: list[str] = field(default_factory=list)
    completeness: str = "complete"
    diagnostics: list[dict] = field(default_factory=list)
    subject: str | None = None
    depth: int | None = None

    def as_wire(self) -> dict:
        return {
            "semantic_id": self.semantic_id,
            "kind": "project",
            "section_ids": list(self.section_ids),
            "member_unit_ids": list(self.member_ids),
            "anchor_unit_ids": list(self.anchor_ids),
            "required_context_unit_ids": list(self.required_context_ids),
            "completeness": self.completeness,
            "diagnostics": list(self.diagnostics),
        }


def _row_cells(text: str) -> list[str] | None:
    if _TABLE_ROW_SEP not in text:
        return None
    cells = [cell.strip() for cell in text.split(_TABLE_ROW_SEP)]
    if len(cells) < 2:
        return None
    return cells


def _header_cells(text: str) -> list[str] | None:
    cells = _row_cells(text)
    if not cells:
        return None
    if sum(1 for cell in cells if _PURPOSE.search(cell)) != 1:
        return None
    return cells


def _project_row(text: str, header_cells: Sequence[str]) -> bool:
    cells = _row_cells(text)
    if not cells:
        return False
    columns = [index for index, cell in enumerate(header_cells) if _PURPOSE.search(cell)]
    if len(columns) != 1 or columns[0] >= len(cells):
        return False
    purpose = cells[columns[0]]
    if not purpose or _FINANCE_ONLY.search(purpose):
        return False
    return bool(_PROJECT_WORD.search(purpose)) or bool(
        re.search(r"(?:项目|建设|扩建|扩产|技改|升级)$", purpose)
    )


def _is_project_heading(unit: ObservationUnit) -> bool:
    if unit.kind in {"table_caption", "table_header", "table_row", "header", "footer"}:
        return False
    if not (layout_mod.is_heading(unit) or _PROJECT_HEADING.match(unit.text)):
        return False
    return bool(_PROJECT_HEADING.match(unit.text))


def _project_subject(text: str) -> str | None:
    cells = _row_cells(text)
    if cells:
        for cell in cells:
            if _PROJECT_WORD.search(cell) or re.search(r"(?:项目|建设)$", cell):
                return cell
        return None
    match = re.match(r"^\s*(?:[一二三四五六七八九十]+[、．.]|（[一二三四五六七八九十]+）)\s*(.+)$", text)
    if match:
        return match.group(1).strip()
    return None


def build_projects(
    units: Sequence[ObservationUnit],
    ordering: layout_mod.Ordering,
    unit_section: dict[str, str],
    *,
    limits: dict[str, int],
    consumed: set[str],
) -> tuple[tuple[ProjectDraft, ...], tuple[dict, ...]]:
    """Return project packages plus global diagnostics.

    ``consumed`` accumulates unit ids that already belong to a package so the
    later paragraph/table builders do not duplicate them.
    """
    by_id = {unit.unit_id: unit for unit in units}
    diagnostics: list[dict] = []
    drafts: list[ProjectDraft] = []
    counter = 0

    intro_ids: list[str] = []
    caption_ids: list[str] = []
    header_ids: list[str] = []
    active_header: list[str] = []

    def flush(draft: ProjectDraft | None) -> None:
        nonlocal counter
        if draft is None:
            return
        if len(draft.member_ids) < 2 and draft.subject is None:
            diagnostics.append(
                {
                    "code": "PROJECT_SUBJECT_ONLY",
                    "unit_ids": list(draft.member_ids),
                    "detail": "project anchored without supporting rows or narrative",
                }
            )
            draft.completeness = "partial"
        if len(draft.member_ids) > limits["max_group_members"]:
            draft.diagnostics.append(
                {
                    "code": "GROUP_BUDGET_EXCEEDED",
                    "unit_ids": list(draft.member_ids[: limits["max_group_members"]]),
                    "detail": (
                        f"{len(draft.member_ids)} members exceed "
                        f"max_group_members={limits['max_group_members']}"
                    ),
                }
            )
            draft.completeness = "partial"
        drafts.append(draft)

    current: ProjectDraft | None = None
    pending_context: list[str] = []

    for unit in ordering.ordered:
        if unit.unit_id in ordering.toc_ids or unit.unit_id in ordering.running_header_ids:
            continue
        text = unit.text

        if unit.kind == "table_caption" or _CAPTION.match(text):
            caption_ids = [unit.unit_id]
            continue

        if unit.kind == "table_header":
            cells = _header_cells(text)
            if cells is not None:
                header_ids = [unit.unit_id]
                active_header = list(cells)
            continue

        if unit.kind == "table_row" or _row_cells(text) is not None:
            if active_header and _project_row(text, active_header):
                subject = _project_subject(text)
                section_ids = [unit_section[unit.unit_id]] if unit.unit_id in unit_section else []
                counter += 1
                flush(current)
                members: list[str] = []
                for candidate in (intro_ids, caption_ids, header_ids):
                    members.extend(candidate)
                members.append(unit.unit_id)
                members = list(dict.fromkeys(members))
                current = ProjectDraft(
                    semantic_id=f"m{counter}",
                    member_ids=members,
                    anchor_ids=[unit.unit_id],
                    required_context_ids=list(dict.fromkeys(caption_ids + header_ids)),
                    section_ids=section_ids,
                    subject=subject,
                )
                for unit_id in members:
                    consumed.add(unit_id)
                pending_context = []
                continue

        if _is_project_heading(unit):
            depth = layout_mod.heading_depth(unit)
            starts_new_project = _starts_new_project(current, depth)
            if starts_new_project or current is None:
                section_ids = (
                    [unit_section[unit.unit_id]] if unit.unit_id in unit_section else []
                )
                counter += 1
                flush(current)
                current = ProjectDraft(
                    semantic_id=f"m{counter}",
                    member_ids=[unit.unit_id],
                    anchor_ids=[unit.unit_id],
                    required_context_ids=[],
                    section_ids=section_ids,
                    subject=_project_subject(text),
                )
                current.depth = depth
            else:
                # A sub-heading of the project already open (for example
                # "（一）项目基本情况" under "一、…项目") stays inside it.
                current.member_ids.append(unit.unit_id)
                if unit.unit_id in unit_section:
                    section_id = unit_section[unit.unit_id]
                    if section_id not in current.section_ids:
                        current.section_ids.append(section_id)
            consumed.add(unit.unit_id)
            pending_context = []
            continue

        if _INTRO.search(text):
            intro_ids = [unit.unit_id]
            pending_context = []
            continue

        if current is not None:
            if layout_mod.is_heading(unit):
                # A real heading ends the narrative part of the project.
                flush(current)
                current = None
                pending_context = []
                continue
            if unit.kind in {"table_header"}:
                continue
            if not unit.is_table_furniture:
                current.member_ids.append(unit.unit_id)
                consumed.add(unit.unit_id)
                if unit_is_cross_page(unit, by_id, current):
                    if "CONTINUATION" not in {
                        item["code"] for item in current.diagnostics
                    }:
                        current.diagnostics.append(
                            {
                                "code": "CROSS_PAGE_CONTINUATION",
                                "unit_ids": [unit.unit_id],
                                "detail": "project narrative continues past a page break",
                            }
                        )
                continue

        if not unit.is_table_furniture and not layout_mod.is_heading(unit):
            pending_context.append(unit.unit_id)

    flush(current)

    if not drafts and header_ids:
        diagnostics.append(
            {
                "code": "PROJECT_HEADER_WITHOUT_ROWS",
                "unit_ids": list(header_ids),
                "detail": "a project table header was found but no project row matched",
            }
        )

    del pending_context
    return tuple(drafts), tuple(diagnostics)


def _starts_new_project(current: ProjectDraft | None, depth: int | None) -> bool:
    """A heading opens a new project unless it is a sub-heading of the open one.

    Without depth evidence the heading is treated as new: silently absorbing an
    unrelated sibling into the previous project is the worse failure.
    """
    if current is None:
        return True
    if depth is None or current.depth is None:
        return True
    return depth <= current.depth


def unit_is_cross_page(
    unit: ObservationUnit,
    by_id: dict[str, ObservationUnit],
    draft: ProjectDraft,
) -> bool:
    """True when this member continues the previous member across a page break."""
    if unit.page is None or len(draft.member_ids) < 2:
        return False
    previous = by_id.get(draft.member_ids[-2])
    if previous is None or previous.page is None:
        return False
    return previous.page != unit.page


__all__ = ["ProjectDraft", "build_projects"]
