"""RF period semantics: only financial-report kinds require a fiscal year."""
from __future__ import annotations
from typing import Any

FINANCIAL_REPORT_KINDS = frozenset({"annual_report", "semi_annual_report", "quarterly_report"})


def valid_fiscal_year(document_kind: str, value: Any) -> bool:
    if value is None:
        return document_kind not in FINANCIAL_REPORT_KINDS
    return type(value) is int and value > 0
