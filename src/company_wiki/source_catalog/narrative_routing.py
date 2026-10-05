"""Document-level routing policy for selective narrative extraction."""

from __future__ import annotations

from dataclasses import dataclass
import re


DEFAULT_SELECTION_LIMIT = 96
PROSPECTUS_SELECTION_LIMIT = 160

_DOCUMENT_KIND_PATTERNS = (
    (r"可转换公司债券|可转债", "convertible_bond_prospectus"),
    (r"向特定对象发行股票|定向增发|增发新股|非公开发行股票", "equity_offering_prospectus"),
    (r"投资者关系管理办法|投资者关系管理制度", "ir_policy"),
    (r"关于召开.*(?:业绩说明会|投资者说明会)|会议通知", "meeting_notice"),
    (r"招股说明书", "prospectus"),
    (r"半年度报告|半年报", "semi_annual_report"),
    (r"年度报告|年报", "annual_report"),
    (r"季度报告|季报", "quarterly_report"),
    (r"投资者关系|活动记录", "investor_relations"),
    (r"earnings_call|transcript", "investor_call_transcript"),
)
_PROSPECTUS_KINDS = frozenset(
    {"prospectus", "convertible_bond_prospectus", "equity_offering_prospectus"}
)
# Only administrative IR policies and meeting notices may skip an empty result
# based on document kind. Business-bearing filings remain reviewable because a
# complete scan does not prove the selector vocabulary covers every narrative.
_EMPTY_SKIP_KINDS = frozenset({"ir_policy", "meeting_notice"})


@dataclass(frozen=True)
class DocumentRoute:
    """Stable document policy decided before candidate extraction."""

    document_kind: str
    selection_limit: int
    empty_result_may_skip: bool


def classify_document_kind(title: str, existing_kind: str = "unknown") -> str:
    """Classify by the most specific title rule, preserving a known fallback."""
    folded = title.casefold()
    for pattern, document_kind in _DOCUMENT_KIND_PATTERNS:
        if re.search(pattern, folded):
            return document_kind
    return existing_kind


def route_document(
    title: str,
    *,
    existing_kind: str = "unknown",
    max_selected: int | None = None,
) -> DocumentRoute:
    """Return document kind, evidence budget, and empty-result policy."""
    document_kind = classify_document_kind(title, existing_kind)
    selection_limit = max_selected
    if selection_limit is None:
        selection_limit = (
            PROSPECTUS_SELECTION_LIMIT
            if document_kind in _PROSPECTUS_KINDS
            else DEFAULT_SELECTION_LIMIT
        )
    if selection_limit < 1:
        raise ValueError("max_selected must be positive")
    return DocumentRoute(
        document_kind=document_kind,
        selection_limit=selection_limit,
        empty_result_may_skip=document_kind in _EMPTY_SKIP_KINDS,
    )


__all__ = [
    "DEFAULT_SELECTION_LIMIT",
    "DocumentRoute",
    "PROSPECTUS_SELECTION_LIMIT",
    "classify_document_kind",
    "route_document",
]
