"""Pure normalization of Sina CompanyFinanceService JSON into typed rows.

Provider responses are normalized without any I/O: exact decimal strings are
preserved, null/empty/group/non-numeric values stay distinct, every value
carries a JSON Pointer back into the original page, and the business report
hash excludes provider update timestamps so an HTTP refresh with unchanged
content reuses the stored version.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

NORMALIZER_VERSION = "financial-statements-normalizer/1.0.0"

_PERIOD_MONTH_DAY = {
    "0331": "q1",
    "0630": "semi_annual",
    "0930": "q3",
    "1231": "annual",
}

#: Field-level unit evidence. Sina precision markers (f2/ps4) are display
#: settings, never units; only these per-share fields carry proven units.
UNIT_EVIDENCE: dict[str, tuple[str, int]] = {
    "BASICEPS": ("CNY/share", 1),
    "DILUTEDEPS": ("CNY/share", 1),
}

_VALUE_NUMERIC = "numeric"
_VALUE_NULL = "null"
_VALUE_EMPTY = "empty"
_VALUE_NON_NUMERIC = "non_numeric"
_VALUE_GROUP = "group"


class NormalizeProtocolError(RuntimeError):
    """The provider payload does not match the observed response protocol."""


def parse_period_kind(period_end_compact: str) -> str:
    if not isinstance(period_end_compact, str) or len(period_end_compact) != 8:
        raise NormalizeProtocolError(f"period must be YYYYMMDD: {period_end_compact!r}")
    try:
        date.fromisoformat(
            f"{period_end_compact[:4]}-{period_end_compact[4:6]}-{period_end_compact[6:]}"
        )
    except ValueError as exc:
        raise NormalizeProtocolError(
            f"period must be a valid date: {period_end_compact!r}"
        ) from exc
    month_day = period_end_compact[4:]
    kind = _PERIOD_MONTH_DAY.get(month_day)
    if kind is None:
        raise NormalizeProtocolError(
            f"unsupported reporting period end {period_end_compact!r}"
        )
    return kind


def parse_consolidation(r_type: Any) -> str:
    if not isinstance(r_type, str) or not r_type.strip():
        return "unknown"
    text = r_type.strip()
    if "母公司" in text:
        return "parent"
    if "合并" in text:
        return "consolidated"
    return "unknown"


def iso_period(period_end_compact: str) -> str:
    return (
        f"{period_end_compact[:4]}-{period_end_compact[4:6]}-{period_end_compact[6:]}"
    )


@dataclass(frozen=True)
class NormalizedRow:
    row_ordinal: int
    provider_field: str
    label: str
    raw_value: str | None
    value_decimal: str | None
    value_kind: str
    unit: str | None
    scale: int | None
    provider_precision: str | None
    json_pointer: str
    item_group_no: int | None = None
    item_display_type: int | None = None
    quality_flags: tuple[str, ...] = ()

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "row_ordinal": self.row_ordinal,
            "provider_field": self.provider_field,
            "label": self.label,
            "raw_value": self.raw_value,
            "value_decimal": self.value_decimal,
            "value_kind": self.value_kind,
            "unit": self.unit,
            "scale": self.scale,
            "provider_precision": self.provider_precision,
            "json_pointer": self.json_pointer,
            "item_group_no": self.item_group_no,
            "item_display_type": self.item_display_type,
            "quality_flags": list(self.quality_flags),
        }


def _classify_value(raw: Any, provider_field: str) -> tuple[str, str | None, tuple[str, ...], str | None, int | None]:
    """Return (value_kind, value_decimal, quality_flags, unit, scale)."""
    if raw is None:
        return _VALUE_NULL, None, (), None, None
    if not isinstance(raw, str):
        # Numbers occasionally arrive as JSON numbers; keep exact text form.
        raw = str(raw)
    if raw == "":
        return _VALUE_EMPTY, None, (), None, None
    try:
        parsed = Decimal(raw)
    except InvalidOperation:
        return _VALUE_NON_NUMERIC, None, ("invalid_numeric_value",), None, None
    if not parsed.is_finite():
        return _VALUE_NON_NUMERIC, None, ("invalid_numeric_value",), None, None
    evidence = UNIT_EVIDENCE.get(provider_field)
    unit, scale = evidence if evidence is not None else (None, None)
    return _VALUE_NUMERIC, format(parsed, "f"), (), unit, scale


@dataclass(frozen=True)
class NormalizedReport:
    statement_type: str
    period_end: str
    period_end_compact: str
    period_kind: str
    period_start: None
    consolidation: str
    currency: str | None
    provider_rType: str | None
    provider_publish_date: str | None
    provider_update_time: str | None
    provider_is_audit: str | None
    provider_data_source: str | None
    provider_date_description: str | None
    provider_report_date_type: int | None
    rows: tuple[NormalizedRow, ...]
    report_hash: str = ""
    normalizer_version: str = NORMALIZER_VERSION
    quality_flags: tuple[str, ...] = field(default=())

    def __post_init__(self) -> None:
        if not self.report_hash:
            object.__setattr__(self, "report_hash", report_hash_for(self))

    def row_by_field(self, provider_field: str) -> NormalizedRow | None:
        for row in self.rows:
            if row.provider_field == provider_field:
                return row
        return None

    def business_identity(self) -> dict[str, Any]:
        """The content that defines a business version.

        Deliberately excludes provider update_time and retrieval timestamps:
        those are provider freshness observations, not statement content.
        """
        return {
            "statement_type": self.statement_type,
            "period_end": self.period_end_compact,
            "period_kind": self.period_kind,
            "consolidation": self.consolidation,
            "currency": self.currency,
            "provider_publish_date": self.provider_publish_date,
            "provider_is_audit": self.provider_is_audit,
            "provider_data_source": self.provider_data_source,
            "normalizer_version": self.normalizer_version,
            "rows": [
                {
                    "row_ordinal": row.row_ordinal,
                    "provider_field": row.provider_field,
                    "label": row.label,
                    "raw_value": row.raw_value,
                    "value_decimal": row.value_decimal,
                    "value_kind": row.value_kind,
                    "unit": row.unit,
                    "scale": row.scale,
                }
                for row in self.rows
            ],
        }

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "statement_type": self.statement_type,
            "period_end": self.period_end,
            "period_kind": self.period_kind,
            "period_start": self.period_start,
            "consolidation": self.consolidation,
            "currency": self.currency,
            "provider_rType": self.provider_rType,
            "provider_publish_date": self.provider_publish_date,
            "provider_update_time": self.provider_update_time,
            "provider_is_audit": self.provider_is_audit,
            "provider_data_source": self.provider_data_source,
            "provider_date_description": self.provider_date_description,
            "report_hash": self.report_hash,
            "normalizer_version": self.normalizer_version,
            "rows": [row.to_public_dict() for row in self.rows],
            "quality_flags": list(self.quality_flags),
        }


@dataclass(frozen=True)
class NormalizedPage:
    page_number: int
    page_had_data: bool
    report_count: int | None
    reports: tuple[NormalizedReport, ...]
    statement_type: str
    quality_flags: tuple[str, ...] = ()

    def report_by_period(self, period: str) -> NormalizedReport | None:
        needle = period.replace("-", "")
        for report in self.reports:
            if report.period_end_compact == needle or report.period_end == period:
                return report
        return None


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def report_hash_for(report: NormalizedReport) -> str:
    return hashlib.sha256(canonical_json_bytes(report.business_identity())).hexdigest()


def _row_from_item(
    item: Any, index: int, period_compact: str, statement_type: str
) -> NormalizedRow:
    if not isinstance(item, dict):
        raise NormalizeProtocolError("report data rows must be objects")
    provider_field = item.get("item_field")
    label = item.get("item_title")
    if not isinstance(provider_field, str):
        provider_field = "" if provider_field is None else str(provider_field)
    if not isinstance(label, str):
        label = "" if label is None else str(label)
    raw = item.get("item_value")
    pointer = f"/result/data/report_list/{period_compact}/data/{index}/item_value"
    group_no = item.get("item_group_no")
    display_type = item.get("item_display_type")
    if isinstance(group_no, bool) or not isinstance(group_no, int):
        group_no = None
    if isinstance(display_type, bool) or not isinstance(display_type, int):
        display_type = None
    precision = item.get("item_precision")
    if not isinstance(precision, str):
        precision = None
    if not provider_field.strip():
        kind, decimal_text, flags, unit, scale = _VALUE_GROUP, None, (), None, None
    else:
        kind, decimal_text, flags, unit, scale = _classify_value(raw, provider_field)
    return NormalizedRow(
        row_ordinal=index + 1,
        provider_field=provider_field,
        label=label,
        raw_value=raw if isinstance(raw, (str, type(None))) else str(raw),
        value_decimal=decimal_text,
        value_kind=kind,
        unit=unit,
        scale=scale,
        provider_precision=precision,
        json_pointer=pointer,
        item_group_no=group_no,
        item_display_type=display_type,
        quality_flags=flags,
    )


def _report_from_entry(
    *, period_compact: str, entry: Any, statement_type: str,
    date_description: str | None, date_type: int | None,
) -> NormalizedReport:
    if not isinstance(entry, dict):
        raise NormalizeProtocolError("report_list entries must be objects")
    rows_payload = entry.get("data")
    if rows_payload is None:
        rows: tuple[NormalizedRow, ...] = ()
    elif isinstance(rows_payload, list):
        rows = tuple(
            _row_from_item(item, index, period_compact, statement_type)
            for index, item in enumerate(rows_payload)
        )
    else:
        raise NormalizeProtocolError("report data must be a list")
    period_kind = parse_period_kind(period_compact)
    r_type = entry.get("rType")
    currency = entry.get("rCurrency")
    publish_date = entry.get("publish_date")
    update_time = entry.get("update_time")
    if isinstance(update_time, bool) or not isinstance(update_time, (int, str)):
        update_text = None
    else:
        update_text = str(update_time)
    quality_flags: list[str] = []
    if not rows:
        quality_flags.append("no_rows")
    report = NormalizedReport(
        statement_type=statement_type,
        period_end=iso_period(period_compact),
        period_end_compact=period_compact,
        period_kind=period_kind,
        period_start=None,
        consolidation=parse_consolidation(r_type),
        currency=currency if isinstance(currency, str) and currency else None,
        provider_rType=r_type if isinstance(r_type, str) else None,
        provider_publish_date=(
            publish_date if isinstance(publish_date, str) and publish_date else None
        ),
        provider_update_time=update_text,
        provider_is_audit=entry.get("is_audit") if isinstance(entry.get("is_audit"), str) else None,
        provider_data_source=(
            entry.get("data_source") if isinstance(entry.get("data_source"), str) else None
        ),
        provider_date_description=date_description,
        provider_report_date_type=date_type,
        rows=rows,
        report_hash="",
        quality_flags=tuple(quality_flags),
    )
    return report


def normalize_page(raw: bytes | str, *, statement_type: str, page_number: int) -> NormalizedPage:
    if isinstance(raw, bytes):
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise NormalizeProtocolError(f"response is not valid JSON: {exc}") from exc
    elif isinstance(raw, str):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise NormalizeProtocolError(f"response is not valid JSON: {exc}") from exc
    else:
        raise NormalizeProtocolError("response must be bytes or text")
    if not isinstance(payload, dict):
        raise NormalizeProtocolError("response must be a JSON object")
    result = payload.get("result")
    if not isinstance(result, dict):
        raise NormalizeProtocolError("response lacks result object")
    status = result.get("status")
    code = status.get("code") if isinstance(status, dict) else None
    if code != 0:
        raise NormalizeProtocolError(f"provider status code {code!r} is not success")
    data = result.get("data")
    if data is None:
        return NormalizedPage(
            page_number=page_number,
            page_had_data=False,
            report_count=None,
            reports=(),
            statement_type=statement_type,
        )
    if not isinstance(data, dict):
        raise NormalizeProtocolError("result.data must be an object or null")
    report_list = data.get("report_list")
    if not isinstance(report_list, dict):
        raise NormalizeProtocolError("result.data lacks report_list object")
    count_raw = data.get("report_count")
    try:
        report_count = int(str(count_raw))
    except (TypeError, ValueError) as exc:
        raise NormalizeProtocolError(
            f"report_count is not an integer: {count_raw!r}"
        ) from exc
    descriptions: dict[str, tuple[str, int | None]] = {}
    for item in data.get("report_date") or []:
        if isinstance(item, dict) and isinstance(item.get("date_value"), str):
            descriptions[item["date_value"]] = (
                item.get("date_description")
                if isinstance(item.get("date_description"), str)
                else None,
                item.get("date_type") if isinstance(item.get("date_type"), int) else None,
            )
    reports: list[NormalizedReport] = []
    page_flags: list[str] = []
    for period_compact, entry in report_list.items():
        if not isinstance(period_compact, str):
            raise NormalizeProtocolError("report_list keys must be period text")
        description, date_type = descriptions.get(period_compact, (None, None))
        report = _report_from_entry(
            period_compact=period_compact,
            entry=entry,
            statement_type=statement_type,
            date_description=description,
            date_type=date_type,
        )
        reports.append(report)
        if description is None:
            page_flags.append(f"missing_date_description:{period_compact}")
    reports.sort(key=lambda report: report.period_end_compact, reverse=True)
    return NormalizedPage(
        page_number=page_number,
        page_had_data=True,
        report_count=report_count,
        reports=tuple(reports),
        statement_type=statement_type,
        quality_flags=tuple(page_flags),
    )


__all__ = [
    "NORMALIZER_VERSION",
    "NormalizeProtocolError",
    "NormalizedPage",
    "NormalizedReport",
    "NormalizedRow",
    "normalize_page",
    "parse_consolidation",
    "parse_period_kind",
    "report_hash_for",
]
