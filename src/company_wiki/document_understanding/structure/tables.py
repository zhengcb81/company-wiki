"""Operating-table semantic units.

A business table row carries numbers that are meaningless without its unit
caption, its period header, and its footnote.  This module binds those
dependencies and refuses to merge a financial-only table with an operating one
even when both sit on the same page.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
import re

from . import layout as layout_mod
from .contract import ObservationUnit

_CAPTION = re.compile(r"^\s*[（(]?\s*(?:单位|币种)\s*[:：]\s*(?P<unit>.+)$")
_YEAR = re.compile(r"(20\d{2})\s*年?")
_FINANCIAL_HEADER = re.compile(
    r"货币资金|应收账款|存货|资产总计|负债合计|营业收入|营业成本|净利润|"
    r"归属于母公司|现金流量|所有者权益|每股收益|"
    r"cash and cash equivalents|total assets|total liabilities|net income|"
    r"revenue|operating income|eps\b",
    re.IGNORECASE,
)
_OPERATING_HEADER = re.compile(
    r"产能|产量|销量|门店|客户|订单|交付|用户|留存|每店|利用率|"
    r"capacity|stores|users|orders|subscribers|retention|utilization|"
    r"average revenue per",
    re.IGNORECASE,
)
_FOOTNOTE = re.compile(r"^\s*(?:注\s*[:：]|Note\s*[:：]?|\*|\(\d+\)|（\d+）)")
_TABLE_ROW_SEP = "|"


@dataclass
class TableDraft:
    semantic_id: str
    member_ids: list[str]
    header_ids: list[str]
    caption_ids: list[str]
    footnote_ids: list[str]
    section_ids: list[str] = field(default_factory=list)
    completeness: str = "complete"
    diagnostics: list[dict] = field(default_factory=list)
    periods: tuple[str, ...] = ()
    unit_label: str | None = None

    def as_wire(self) -> dict:
        return {
            "semantic_id": self.semantic_id,
            "kind": "operating_table",
            "section_ids": list(self.section_ids),
            "member_unit_ids": list(self.member_ids),
            "anchor_unit_ids": list(self.header_ids),
            "required_context_unit_ids": list(
                dict.fromkeys(self.header_ids + self.caption_ids)
            ),
            "completeness": self.completeness,
            "diagnostics": list(self.diagnostics),
        }


def _cells(text: str) -> list[str] | None:
    if _TABLE_ROW_SEP not in text:
        return None
    parts = [cell.strip() for cell in text.split(_TABLE_ROW_SEP)]
    return parts if len(parts) >= 2 else None


def _table_key(unit: ObservationUnit) -> str:
    if unit.table_id:
        return f"table:{unit.table_id}"
    if unit.page is not None:
        # Without a table id, only an explicitly typed row/header counts, and
        # the page alone is too coarse to group on -- fall back to the section.
        return f"loose:{unit.page}"
    return "loose:unknown"


def _operating_header(text: str) -> bool:
    if _FINANCIAL_HEADER.search(text):
        # "门店营业收入" style mixes: operating wins only when no financial term
        # dominates the header.  Anything with 货币资金/资产总计 is financial.
        if not _OPERATING_HEADER.search(text):
            return False
        financial_hits = len(_FINANCIAL_HEADER.findall(text))
        operating_hits = len(_OPERATING_HEADER.findall(text))
        return operating_hits > financial_hits
    return bool(_OPERATING_HEADER.search(text))


def build_operating_tables(
    units: Sequence[ObservationUnit],
    ordering: layout_mod.Ordering,
    unit_section: dict[str, str],
    *,
    limits: dict[int, int] | dict[str, int],
    consumed: set[str],
) -> tuple[tuple[TableDraft, ...], tuple[dict, ...]]:
    diagnostics: list[dict] = []
    drafts: list[TableDraft] = []
    counter = 0

    captions_by_table: dict[str, list[str]] = {}
    footnotes_by_table: dict[str, list[str]] = {}
    for unit in ordering.ordered:
        key = _table_key(unit)
        if _CAPTION.match(unit.text) or unit.kind == "table_caption":
            captions_by_table.setdefault(key, []).append(unit.unit_id)
        if unit.is_footnote or _FOOTNOTE.match(unit.text):
            footnotes_by_table.setdefault(key, []).append(unit.unit_id)

    current_key: str | None = None
    current: TableDraft | None = None
    header_cells: list[str] = []

    def flush(draft: TableDraft | None) -> None:
        if draft is None:
            return
        rows = [uid for uid in draft.member_ids if uid not in set(draft.header_ids)]
        if not rows:
            diagnostics.append(
                {
                    "code": "TABLE_HEADER_WITHOUT_ROWS",
                    "unit_ids": list(draft.header_ids),
                    "detail": "operating header recognized without any data row",
                }
            )
            return
        if not draft.caption_ids:
            draft.completeness = "partial"
            draft.diagnostics.append(
                {
                    "code": "TABLE_UNIT_MISSING",
                    "unit_ids": list(draft.member_ids),
                    "detail": "no 单位/币种 caption was available for this table",
                }
            )
        if not draft.periods:
            draft.completeness = "partial"
            draft.diagnostics.append(
                {
                    "code": "TABLE_PERIOD_MISSING",
                    "unit_ids": list(draft.member_ids),
                    "detail": "no year or period was stated in the table header",
                }
            )
        if len(draft.member_ids) > limits["max_group_members"]:
            draft.completeness = "partial"
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
        drafts.append(draft)

    for unit in ordering.ordered:
        if unit.unit_id in ordering.toc_ids or unit.unit_id in ordering.running_header_ids:
            continue
        section_ids = [unit_section[unit.unit_id]] if unit.unit_id in unit_section else []
        key = _table_key(unit)

        if unit.kind == "table_header":
            cells = _cells(unit.text)
            if cells is None:
                continue
            if not _operating_header(unit.text):
                # A financial header closes any open operating table and is
                # never merged into it.
                flush(current)
                current = None
                current_key = key
                header_cells = []
                continue
            flush(current)
            counter += 1
            header_cells = cells
            current_key = key
            current = TableDraft(
                semantic_id=f"m{counter}",
                member_ids=[unit.unit_id],
                header_ids=[unit.unit_id],
                caption_ids=list(captions_by_table.get(key, [])),
                footnote_ids=list(footnotes_by_table.get(key, [])),
                section_ids=section_ids,
                periods=tuple(dict.fromkeys(_YEAR.findall(unit.text))),
            )
            for unit_id in current.caption_ids:
                if unit_id not in current.member_ids:
                    current.member_ids.append(unit_id)
            for unit_id in current.footnote_ids:
                if unit_id not in current.member_ids:
                    current.member_ids.append(unit_id)
            for unit_id in current.member_ids:
                consumed.add(unit_id)
            continue

        if unit.kind == "table_row":
            if current is None or key != current_key or not header_cells:
                continue
            if _FINANCIAL_HEADER.search(unit.text) and not _OPERATING_HEADER.search(unit.text):
                continue
            current.member_ids.append(unit.unit_id)
            if not current.periods:
                current.periods = tuple(dict.fromkeys(_YEAR.findall(unit.text)))
            consumed.add(unit.unit_id)
            continue

        if _CAPTION.match(unit.text) or unit.is_footnote or _FOOTNOTE.match(unit.text):
            continue

        if unit.is_table_furniture:
            continue

    flush(current)
    return tuple(drafts), tuple(diagnostics)


__all__ = ["TableDraft", "build_operating_tables"]
