"""Operating-table semantic units.

A business table row carries numbers that are meaningless without its unit
caption, its period header, and its footnote.  This module binds those
dependencies and refuses to merge a financial-only table with an operating one
even when both sit on the same page.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import re

from . import layout as layout_mod
from .contract import ObservationUnit

_CAPTION = re.compile(r"^\s*[（(]?\s*(?:单位|單位|币种|幣種|units?|currency)\s*[:：]\s*(?P<unit>.+)$", re.IGNORECASE)
_YEAR = re.compile(r"(20\d{2})\s*年?")
_BALANCE_ACCOUNT = re.compile(
    r"cash and cash equivalents|accounts? (?:receivable|payable)|total assets|total liabilities|"
    r"lease liabilities|right[ -]of[ -]use assets|货币资金|貨幣資金|应收[账帳]款|應收[賬帳]款|"
    r"应付[账帳]款|應付[賬帳]款|资产总计|資產總計|负债合计|負債合計|租赁负债|租賃負債|"
    r"使用权资产|使用權資產", re.IGNORECASE,
)
_FINANCIAL_HEADER = re.compile(
    r"货币资金|应收账款|存货|资产总计|负债合计|营业收入|营业成本|净利润|"
    r"归属于母公司|现金流量|所有者权益|每股收益|"
    r"cash and cash equivalents|total assets|total liabilities|net income|"
    r"revenue|operating income|eps\b|營業收入|營業成本|淨利潤|現金流量|所有者權益|"
    + _BALANCE_ACCOUNT.pattern,
    re.IGNORECASE,
)
_OPERATING_HEADER = re.compile(
    r"产能|產能|产量|產量|销量|銷量|门店|門店|客户|客戶|订单|訂單|交付|用户|用戶|留存|每店|利用率|"
    r"capacity|stores|outlets|customers|users|orders|subscribers|retention|utilization|"
    r"average revenue per",
    re.IGNORECASE,
)
_FOOTNOTE = re.compile(r"^\s*(?:注\s*[:：]|Note\s*[:：]?|\*|\(\d+\)|（\d+）)")
_PERIOD = re.compile(r"\b(?:as of|period|year|month|quarter|ended)\b|截至|年度|季度|月[末底]?|半年", re.IGNORECASE)
_NUMBER = re.compile(r"\d[\d,.]*(?:\s*[%％])?")


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
        required = list(dict.fromkeys(self.header_ids + self.caption_ids + self.footnote_ids))
        context = set(required)
        return {
            "semantic_id": self.semantic_id,
            "kind": "operating_table",
            "section_ids": list(self.section_ids),
            "member_unit_ids": list(self.member_ids),
            "anchor_unit_ids": [uid for uid in self.member_ids if uid not in context],
            "required_context_unit_ids": required,
            "completeness": self.completeness,
            "diagnostics": list(self.diagnostics),
        }


def _table_key(unit: ObservationUnit) -> str:
    if unit.table_id:
        # Frontends commonly number tables locally on each page. Equal local
        # IDs do not prove continuation, even when the next page has rows only.
        return f"page:{unit.page}:table:{unit.table_id}"
    if unit.page is not None:
        # Without a table id, only an explicitly typed row/header counts, and
        # the page alone is too coarse to group on -- fall back to the section.
        return f"loose:{unit.page}"
    return "loose:unknown"


def _operating_header(text: str) -> bool:
    if _BALANCE_ACCOUNT.search(text):
        return False
    if _FINANCIAL_HEADER.search(text):
        # "门店营业收入" style mixes: operating wins only when no financial term
        # dominates the header.  Anything with 货币资金/资产总计 is financial.
        if not _OPERATING_HEADER.search(text):
            return False
        financial_hits = len(_FINANCIAL_HEADER.findall(text))
        operating_hits = len(_OPERATING_HEADER.findall(text))
        return operating_hits > financial_hits
    return bool(_OPERATING_HEADER.search(text))


def _is_caption(unit: ObservationUnit) -> bool:
    return unit.kind == "table_caption" or _CAPTION.match(unit.text) is not None


def _is_note(unit: ObservationUnit) -> bool:
    return unit.is_footnote or (unit.kind != "table_header" and _FOOTNOTE.match(unit.text) is not None)


def _period_row(text: str) -> bool:
    """Actual date labels and year columns are headers, not operating values."""
    without_years = _YEAR.sub("", text)
    if _YEAR.search(text) and not re.search(r"\w", without_years):
        return True
    if not _PERIOD.search(text):
        return False
    remainder = re.sub(
        r"\b(?:as|of|period|year|years|month|months|quarter|ended|ending|the|"
        r"first|second|third|fourth|half|three|six|nine|twelve|to|from|and|"
        r"january|february|march|april|may|june|july|august|september|october|november|december)\b|"
        r"截至|年度|季度|半年|年|月|日|末|底",
        "", without_years, flags=re.IGNORECASE,
    )
    remainder = re.sub(r"\d{1,2}", "", remainder)
    return re.search(r"\w", remainder) is None


def _scopes(ordering: layout_mod.Ordering) -> dict[str, list[ObservationUnit]]:
    """Index actual typed table scopes once; no page-wide caption/footnote join."""
    scopes: dict[str, list[ObservationUnit]] = {}
    loose_key: str | None = None
    loose_page: int | None = None
    loose_index = 0
    pending: list[ObservationUnit] = []
    for unit in ordering.ordered:
        if unit.unit_id in ordering.toc_ids or unit.unit_id in ordering.running_header_ids:
            continue
        belongs = unit.kind in {"table_header", "table_row", "html_table_cell"} or _is_caption(unit) or _is_note(unit)
        if unit.table_id is not None:
            if belongs:
                scopes.setdefault(_table_key(unit), []).append(unit)
            continue
        if unit.page != loose_page:
            loose_key, loose_page, pending = None, unit.page, []
        if not belongs:
            loose_key, pending = None, []
            continue
        if _is_caption(unit) and loose_key is None:
            pending.append(unit)
            continue
        if unit.kind == "table_header" or loose_key is None:
            loose_index += 1
            loose_key = f"{_table_key(unit)}:scope:{loose_index}"
            scopes[loose_key] = list(pending)
            pending = []
        scopes[loose_key].append(unit)
    return scopes


def build_operating_tables(
    units: Sequence[ObservationUnit],
    ordering: layout_mod.Ordering,
    unit_section: dict[str, str],
    *,
    limits: Mapping[str, int],
    consumed: set[str],
) -> tuple[tuple[TableDraft, ...], tuple[dict, ...]]:
    diagnostics: list[dict] = []
    drafts: list[TableDraft] = []
    work = 0

    def flush(draft: TableDraft) -> None:
        context = set(draft.header_ids + draft.caption_ids + draft.footnote_ids)
        rows = [uid for uid in draft.member_ids if uid not in context]
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
                    "detail": "no original unit/currency caption was available for this table",
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
        consumed.update(draft.member_ids)

    for scope in _scopes(ordering).values():
        # Only actual typed rows and their explicitly scoped qualifiers carry
        # table meaning. An operating word in a note cannot certify a balance
        # sheet, and a neighbouring table cannot provide missing purpose.
        rows = [unit for unit in scope if not _is_caption(unit) and not _is_note(unit)]
        cost = sum(1 + len(unit.text) for unit in rows)
        if work + cost > limits["max_work_units"]:
            diagnostics.append({"code": "TABLE_WORK_BUDGET_EXCEEDED",
                                "unit_ids": [unit.unit_id for unit in scope[:128]],
                                "detail": "operating table purpose scan exceeded the caller's work budget"})
            break
        work += cost
        purposes = {unit.unit_id: _operating_header(unit.text) for unit in rows}
        if not any(purposes.values()):
            continue
        if any(_FINANCIAL_HEADER.search(unit.text) and not purposes[unit.unit_id] for unit in rows):
            # A mixed/financial purpose is not permission to import all account
            # balances as operating facts. Leave it unassigned for the reader.
            continue
        headers: list[str] = []
        body: list[str] = []
        purpose_seen = False
        for unit in rows:
            purpose = purposes[unit.unit_id]
            neutral_period = _period_row(unit.text) and (
                not purpose_seen or _PERIOD.search(unit.text) is not None
            )
            if unit.kind == "table_header" or neutral_period or (
                purpose and (not purpose_seen or _NUMBER.search(unit.text) is None)
            ):
                headers.append(unit.unit_id)
            else:
                body.append(unit.unit_id)
            purpose_seen = purpose_seen or purpose
        captions = [unit.unit_id for unit in scope if _is_caption(unit)]
        notes = [unit.unit_id for unit in scope if _is_note(unit)]
        relevant = set(headers + captions + notes + body)
        header_set = set(headers)
        draft = TableDraft(
            semantic_id=f"m{len(drafts) + 1}",
            member_ids=[unit.unit_id for unit in scope if unit.unit_id in relevant],
            header_ids=headers,
            caption_ids=captions,
            footnote_ids=notes,
            section_ids=list(dict.fromkeys(unit_section[unit.unit_id] for unit in scope
                                          if unit.unit_id in unit_section)),
            periods=tuple(dict.fromkeys(year for unit in rows if unit.unit_id in header_set
                                        for year in _YEAR.findall(unit.text))),
        )
        caption = next((match.group("unit") for unit in scope
                        if (match := _CAPTION.match(unit.text)) is not None), None)
        draft.unit_label = caption
        flush(draft)
    return tuple(drafts), tuple(diagnostics)


__all__ = ["TableDraft", "build_operating_tables"]
