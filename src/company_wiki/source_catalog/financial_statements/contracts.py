"""Frozen request/response contracts for A-share historical financial statements.

The wire formats are ``financial-statements-request/1`` and
``financial-statements-response/1`` shared by the CWP CLI/service and the
filing-fetch thin client. Validation here is the single owner: both sides
import these rules instead of re-implementing them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

STATEMENTS_REQUEST_SCHEMA_VERSION = "financial-statements-request/1"
STATEMENTS_RESPONSE_SCHEMA_VERSION = "financial-statements-response/1"

STATEMENT_TYPES = ("income_statement", "balance_sheet", "cash_flow")
REPORT_TYPES = ("annual", "semi_annual", "q1", "q3")
INTENTS = ("reuse_only", "fetch_if_missing", "refresh")
KNOWLEDGE_MODES = ("current_snapshot", "point_in_time")

RESPONSE_STATUSES = ("complete", "partial", "not_found", "unavailable")

#: provider keys on the Sina wire (lrb/fzb/llb) per statement type
STATEMENT_PROVIDER_SOURCES = {
    "income_statement": "lrb",
    "balance_sheet": "fzb",
    "cash_flow": "llb",
}


class RequestValidationError(ValueError):
    """Invalid statements request; ``code`` names the caller-facing bucket."""

    def __init__(self, message: str, *, code: str = "request_error"):
        super().__init__(message)
        self.code = code


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RequestValidationError(f"{name} must be non-empty text")
    if value != value.strip():
        raise RequestValidationError(f"{name} must be trimmed text")
    return value


def _date(value: Any, name: str) -> date:
    if not isinstance(value, str):
        raise RequestValidationError(f"{name} must be YYYY-MM-DD text")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise RequestValidationError(f"{name} must be a valid YYYY-MM-DD date") from exc


@dataclass(frozen=True)
class AcquisitionLimits:
    max_bytes: int
    timeout_seconds: float
    max_cost_usd: str

    @classmethod
    def from_payload(cls, payload: Any) -> "AcquisitionLimits":
        if not isinstance(payload, dict):
            raise RequestValidationError("acquisition_limits must be an object")
        allowed = {"max_bytes", "timeout_seconds", "max_cost_usd"}
        if set(payload) != allowed:
            raise RequestValidationError(
                "acquisition_limits must contain exactly max_bytes/timeout_seconds/max_cost_usd"
            )
        max_bytes = payload["max_bytes"]
        if (
            isinstance(max_bytes, bool)
            or not isinstance(max_bytes, int)
            or max_bytes <= 0
        ):
            raise RequestValidationError("max_bytes must be a positive integer")
        timeout = payload["timeout_seconds"]
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
            raise RequestValidationError("timeout_seconds must be a number")
        if timeout != timeout or timeout in (float("inf"), float("-inf")) or timeout <= 0:
            raise RequestValidationError("timeout_seconds must be finite and positive")
        cost = payload["max_cost_usd"]
        if isinstance(cost, bool) or not isinstance(cost, (str, int, Decimal)):
            raise RequestValidationError("max_cost_usd must be a decimal string")
        try:
            amount = Decimal(str(cost))
        except InvalidOperation as exc:
            raise RequestValidationError("max_cost_usd must be a decimal") from exc
        if not amount.is_finite() or amount < 0:
            raise RequestValidationError("max_cost_usd must be finite and non-negative")
        return cls(max_bytes=max_bytes, timeout_seconds=float(timeout), max_cost_usd=str(cost))


@dataclass(frozen=True)
class StatementsRequest:
    company_query: str
    market: str = "CN"
    statements: tuple[str, ...] = STATEMENT_TYPES
    report_types: tuple[str, ...] = REPORT_TYPES
    period_end_from: str | None = None
    period_end_to: str | None = None
    all_history: bool = False
    knowledge_mode: str = "current_snapshot"
    as_of_date: str | None = None
    intent: str = "fetch_if_missing"
    acquisition_limits: AcquisitionLimits | None = None
    fields: tuple[str, ...] | None = None
    continuation: str | None = None
    schema_version: str = STATEMENTS_REQUEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.market != "CN":
            raise RequestValidationError("only market=CN is supported")
        for name in ("statements", "report_types"):
            values = getattr(self, name)
            known = STATEMENT_TYPES if name == "statements" else REPORT_TYPES
            if not values:
                raise RequestValidationError(f"{name} must not be empty")
            unknown = [value for value in values if value not in known]
            if unknown:
                raise RequestValidationError(f"unsupported {name}: {unknown}")
            if len(set(values)) != len(values):
                raise RequestValidationError(f"{name} must not repeat values")
        if self.all_history and self.period_end_from:
            raise RequestValidationError(
                "all_history and period_end_from are mutually exclusive"
            )
        if self.knowledge_mode not in KNOWLEDGE_MODES:
            raise RequestValidationError("unsupported knowledge_mode")
        if self.intent not in INTENTS:
            raise RequestValidationError("unsupported intent")
        if self.intent != "reuse_only" and self.acquisition_limits is None:
            raise RequestValidationError(
                "acquisition_limits are required for fetching intents"
            )
        if self.as_of_date is None:
            raise RequestValidationError("as_of_date is required")
        _date(self.as_of_date, "as_of_date")

    @property
    def effective_period_from(self) -> str | None:
        return None if self.all_history else self.period_end_from

    @classmethod
    def from_payload(cls, payload: Any) -> "StatementsRequest":
        if not isinstance(payload, dict):
            raise RequestValidationError("request must be a JSON object")
        allowed = {
            "schema_version", "company_query", "market", "statements",
            "report_types", "period_end_from", "period_end_to", "all_history",
            "knowledge_mode", "as_of_date", "intent", "acquisition_limits",
            "fields", "continuation",
        }
        unknown = set(payload) - allowed
        if unknown:
            raise RequestValidationError(f"unknown request fields: {sorted(unknown)}")
        if payload.get("schema_version") != STATEMENTS_REQUEST_SCHEMA_VERSION:
            raise RequestValidationError(
                f"schema_version must be {STATEMENTS_REQUEST_SCHEMA_VERSION}"
            )
        company_query = _text(payload.get("company_query"), "company_query")
        market = payload.get("market", "CN")
        if market != "CN":
            raise RequestValidationError("only market=CN is supported")
        statements = tuple(payload.get("statements", STATEMENT_TYPES))
        report_types = tuple(payload.get("report_types", REPORT_TYPES))
        period_from = payload.get("period_end_from")
        if period_from is not None:
            _date(period_from, "period_end_from")
        period_to = payload.get("period_end_to")
        if period_to is not None:
            _date(period_to, "period_end_to")
        if period_from and period_to and period_from > period_to:
            raise RequestValidationError("period_end_from must not exceed period_end_to")
        all_history = payload.get("all_history", False)
        if not isinstance(all_history, bool):
            raise RequestValidationError("all_history must be a boolean")
        as_of = payload.get("as_of_date")
        _date(as_of, "as_of_date")
        intent = payload.get("intent", "fetch_if_missing")
        knowledge_mode = payload.get("knowledge_mode", "current_snapshot")
        limits_payload = payload.get("acquisition_limits")
        limits = (
            AcquisitionLimits.from_payload(limits_payload)
            if limits_payload is not None
            else None
        )
        fields_payload = payload.get("fields")
        fields: tuple[str, ...] | None = None
        if fields_payload is not None:
            if not isinstance(fields_payload, list) or not fields_payload:
                raise RequestValidationError("fields must be a non-empty list")
            if not all(isinstance(item, str) and item.strip() for item in fields_payload):
                raise RequestValidationError("fields items must be non-empty text")
            fields = tuple(fields_payload)
        continuation_payload = payload.get("continuation")
        continuation: str | None = None
        if continuation_payload is not None:
            continuation = _text(continuation_payload, "continuation")
        if continuation is not None and intent == "reuse_only":
            raise RequestValidationError(
                "continuation is not supported with reuse_only"
            )
        return cls(
            company_query=company_query,
            market=market,
            statements=statements,
            report_types=report_types,
            period_end_from=period_from,
            period_end_to=period_to,
            all_history=all_history,
            knowledge_mode=knowledge_mode,
            as_of_date=as_of,
            intent=intent,
            acquisition_limits=limits,
            fields=fields,
            continuation=continuation,
        )

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "company_query": self.company_query,
            "market": self.market,
            "statements": list(self.statements),
            "report_types": list(self.report_types),
            "period_end_from": self.period_end_from,
            "period_end_to": self.period_end_to,
            "all_history": self.all_history,
            "knowledge_mode": self.knowledge_mode,
            "as_of_date": self.as_of_date,
            "intent": self.intent,
            "acquisition_limits": (
                {
                    "max_bytes": self.acquisition_limits.max_bytes,
                    "timeout_seconds": self.acquisition_limits.timeout_seconds,
                    "max_cost_usd": self.acquisition_limits.max_cost_usd,
                }
                if self.acquisition_limits
                else None
            ),
            "fields": list(self.fields) if self.fields is not None else None,
            "continuation": self.continuation,
        }


__all__ = [
    "AcquisitionLimits",
    "INTENTS",
    "KNOWLEDGE_MODES",
    "REPORT_TYPES",
    "RequestValidationError",
    "RESPONSE_STATUSES",
    "STATEMENT_PROVIDER_SOURCES",
    "STATEMENT_TYPES",
    "STATEMENTS_REQUEST_SCHEMA_VERSION",
    "STATEMENTS_RESPONSE_SCHEMA_VERSION",
    "StatementsRequest",
]
