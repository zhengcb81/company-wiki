"""Persistence and query for financial statement versions/values.

Publishing is idempotent by business identity: same normalized content reuses
the stored version and only refreshes provider freshness observations; changed
content keeps the old version and adds a new one. Query paths never create or
migrate a catalog — the read-only helper opens ``mode=ro`` and returns named
gaps when the database or the long tables are missing.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from ..store import CatalogStore
from .contracts import STATEMENT_TYPES
from .normalize import NormalizedReport
from .sina_provider import SINA_PROVIDER_ID

_STATEMENT_TYPE_SET = frozenset(STATEMENT_TYPES)


@dataclass(frozen=True)
class StatementSecurity:
    """One resolved issuer identity; no directory or file semantics."""

    entity: str
    market: str
    security_id: str
    exchange: str
    code: str


@dataclass(frozen=True)
class StatementSource:
    """The committed provider page backing a set of statement versions."""

    source_id: str
    document_id: str
    content_sha256: str
    page_number: int
    url: str
    provider: str = SINA_PROVIDER_ID


@dataclass(frozen=True)
class PublishOutcome:
    new_version_ids: tuple[str, ...] = ()
    reused_version_ids: tuple[str, ...] = ()


def statement_version_id(
    *, security_id: str, provider: str, report: NormalizedReport
) -> str:
    key = canonical_json_bytes(
        {
            "security_id": security_id,
            "provider": provider,
            "statement_type": report.statement_type,
            "period_end": report.period_end,
            "consolidation": report.consolidation,
            "canonical_report_sha256": report.report_hash,
        }
    )
    return "fsv-" + hashlib.sha256(key).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


class FinancialStatementRepository:
    """One publisher and one query owner over the two long tables."""

    def __init__(self, store: CatalogStore):
        if not isinstance(store, CatalogStore):
            raise TypeError("store must be CatalogStore")
        self.store = store

    # -- publish -----------------------------------------------------------

    def publish_reports(
        self,
        *,
        security: StatementSecurity,
        source: StatementSource,
        reports: Sequence[NormalizedReport],
        retrieved_at: str,
    ) -> PublishOutcome:
        if not reports:
            return PublishOutcome()
        with self.store.transaction() as connection:
            self._require_source(connection, source)
            new_ids: list[str] = []
            reused_ids: list[str] = []
            for report in reports:
                version_id = statement_version_id(
                    security_id=security.security_id,
                    provider=source.provider,
                    report=report,
                )
                existing = connection.execute(
                    """
                    SELECT statement_version_id FROM financial_statement_versions
                    WHERE security_id=? AND provider=? AND statement_type=?
                      AND period_end=? AND consolidation=?
                      AND canonical_report_sha256=?
                    """,
                    (
                        security.security_id,
                        source.provider,
                        report.statement_type,
                        report.period_end,
                        report.consolidation,
                        report.report_hash,
                    ),
                ).fetchone()
                if existing is not None:
                    # Same business content: refresh provider observations only.
                    connection.execute(
                        """
                        UPDATE financial_statement_versions
                        SET last_checked_at=?, provider_update_time=?, source_id=?,
                            document_id=?, source_url=?
                        WHERE statement_version_id=?
                        """,
                        (
                            retrieved_at,
                            report.provider_update_time,
                            source.source_id,
                            source.document_id,
                            source.url,
                            existing["statement_version_id"],
                        ),
                    )
                    reused_ids.append(existing["statement_version_id"])
                    continue
                connection.execute(
                    """
                    INSERT INTO financial_statement_versions (
                        statement_version_id, entity, market, security_id, exchange,
                        code, provider, statement_type, period_end, period_kind,
                        period_start, consolidation, currency, provider_rType,
                        provider_publish_date, provider_update_time, provider_is_audit,
                        provider_data_source, provider_date_description,
                        provider_report_date_type, canonical_report_sha256,
                        normalizer_version, source_id, document_id, source_url,
                        row_count, quality_flags_json, captured_at, first_seen_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        version_id,
                        security.entity,
                        security.market,
                        security.security_id,
                        security.exchange,
                        security.code,
                        source.provider,
                        report.statement_type,
                        report.period_end,
                        report.period_kind,
                        report.period_start,
                        report.consolidation,
                        report.currency,
                        report.provider_rType,
                        report.provider_publish_date,
                        report.provider_update_time,
                        report.provider_is_audit,
                        report.provider_data_source,
                        report.provider_date_description,
                        report.provider_report_date_type,
                        report.report_hash,
                        report.normalizer_version,
                        source.source_id,
                        source.document_id,
                        source.url,
                        len(report.rows),
                        canonical_json_bytes(list(report.quality_flags)).decode("utf-8"),
                        retrieved_at,
                        retrieved_at,
                    ),
                )
                connection.executemany(
                    """
                    INSERT INTO financial_statement_values (
                        statement_version_id, row_ordinal, provider_field, label,
                        raw_value, value_decimal, value_kind, unit, scale,
                        provider_precision, json_pointer, item_group_no,
                        item_display_type, quality_flags_json
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    [
                        (
                            version_id,
                            row.row_ordinal,
                            row.provider_field,
                            row.label,
                            row.raw_value,
                            row.value_decimal,
                            row.value_kind,
                            row.unit,
                            row.scale,
                            row.provider_precision,
                            row.json_pointer,
                            row.item_group_no,
                            row.item_display_type,
                            canonical_json_bytes(list(row.quality_flags)).decode("utf-8"),
                        )
                        for row in report.rows
                    ],
                )
                new_ids.append(version_id)
            return PublishOutcome(
                new_version_ids=tuple(new_ids), reused_version_ids=tuple(reused_ids)
            )

    @staticmethod
    def _require_source(connection: sqlite3.Connection, source: StatementSource) -> None:
        source_row = connection.execute(
            "SELECT content_sha256, byte_size FROM sources WHERE source_id=?",
            (source.source_id,),
        ).fetchone()
        if source_row is None:
            raise ValueError(
                "provider page source is not registered in the catalog"
            )
        if source_row["content_sha256"] != source.content_sha256:
            raise ValueError("provider page source SHA does not match registration")

    # -- query ------------------------------------------------------------

    def query_statement_rows(
        self,
        *,
        security_id: str,
        statement_type: str,
        period_end_from: str | None = None,
        period_end_to: str | None = None,
        fields: Iterable[str] | None = None,
        max_rows: int | None = None,
        continuation: str | None = None,
    ) -> dict[str, Any]:
        if statement_type not in _STATEMENT_TYPE_SET:
            raise ValueError(f"unknown statement_type: {statement_type!r}")
        field_filter = tuple(fields) if fields is not None else None
        if field_filter is not None and not field_filter:
            raise ValueError("fields filter must not be empty")
        resume_version: str | None = None
        resume_ordinal: int | None = None
        if continuation:
            try:
                resume_version, ordinal_text = continuation.split(":", 1)
                resume_ordinal = int(ordinal_text)
            except ValueError as exc:
                raise ValueError("malformed continuation token") from exc
        versions = self.store.fetchall(
            """
            SELECT * FROM financial_statement_versions
            WHERE security_id=? AND statement_type=?
              AND (? IS NULL OR period_end>=?)
              AND (? IS NULL OR period_end<=?)
            ORDER BY period_end DESC, consolidation, canonical_report_sha256
            """,
            (
                security_id,
                statement_type,
                period_end_from,
                period_end_from,
                period_end_to,
                period_end_to,
            ),
        )
        emitted: list[dict[str, Any]] = []
        remaining_budget = max_rows
        next_continuation: str | None = None
        skipping = resume_version is not None
        for version in versions:
            if skipping and version["statement_version_id"] != resume_version:
                continue
            rows = self.store.fetchall(
                """
                SELECT * FROM financial_statement_values
                WHERE statement_version_id=?
                  AND (? IS NULL OR provider_field IN (SELECT value FROM json_each(?)))
                ORDER BY row_ordinal
                """,
                (
                    version["statement_version_id"],
                    None if field_filter is None else 1,
                    None if field_filter is None
                    else canonical_json_bytes(list(field_filter)).decode("utf-8"),
                ),
            )
            version_payload = _version_public(version, rows=[_row_public(r) for r in rows])
            if skipping:
                # resume strictly after the saved position within this version
                version_payload["rows"] = [
                    row
                    for row in version_payload["rows"]
                    if row["row_ordinal"] > resume_ordinal
                ]
                skipping = False
            if remaining_budget is None:
                emitted.append(version_payload)
                continue
            kept = version_payload["rows"][: remaining_budget]
            remaining_budget -= len(kept)
            if kept or not version_payload["rows"]:
                partial = dict(version_payload)
                partial["rows"] = kept
                partial["truncated"] = len(kept) < len(version_payload["rows"])
                emitted.append(partial)
            if remaining_budget == 0:
                last_ordinal = kept[-1]["row_ordinal"] if kept else resume_ordinal
                next_continuation = (
                    f"{version['statement_version_id']}:{last_ordinal}"
                )
                break
        return {
            "security_id": security_id,
            "statement_type": statement_type,
            "versions": emitted,
            "continuation": next_continuation,
            "truncated": next_continuation is not None,
        }

    def local_coverage(self, *, security_id: str, statement_type: str) -> dict[str, Any]:
        rows = self.store.fetchall(
            """
            SELECT period_end, COUNT(*) AS version_count
            FROM financial_statement_versions
            WHERE security_id=? AND statement_type=?
            GROUP BY period_end ORDER BY period_end
            """,
            (security_id, statement_type),
        )
        return {
            "period_ends": [row["period_end"] for row in rows],
            "periods": len(rows),
        }

    def coverage_observation(
        self, *, security_id: str, provider: str, statement_type: str
    ) -> dict[str, Any] | None:
        row = self.store.fetchone(
            """
            SELECT * FROM financial_statement_coverage
            WHERE security_id=? AND provider=? AND statement_type=?
            """,
            (security_id, provider, statement_type),
        )
        return dict(row) if row is not None else None

    def record_coverage_observation(
        self,
        *,
        security_id: str,
        provider: str,
        statement_type: str,
        advertised_report_count: int | None,
        observed_periods: int,
        first_period_end: str | None,
        last_period_end: str | None,
        terminal_reason: str,
        http_requests: int,
        response_bytes: int,
        observed_at: str,
    ) -> None:
        with self.store.transaction() as connection:
            connection.execute(
                """
                INSERT INTO financial_statement_coverage (
                    security_id, provider, statement_type, advertised_report_count,
                    observed_periods, first_period_end, last_period_end,
                    terminal_reason, last_http_requests, last_response_bytes, observed_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(security_id, provider, statement_type) DO UPDATE SET
                    advertised_report_count=excluded.advertised_report_count,
                    observed_periods=excluded.observed_periods,
                    first_period_end=excluded.first_period_end,
                    last_period_end=excluded.last_period_end,
                    terminal_reason=excluded.terminal_reason,
                    last_http_requests=excluded.last_http_requests,
                    last_response_bytes=excluded.last_response_bytes,
                    observed_at=excluded.observed_at
                """,
                (
                    security_id,
                    provider,
                    statement_type,
                    advertised_report_count,
                    observed_periods,
                    first_period_end,
                    last_period_end,
                    terminal_reason,
                    http_requests,
                    response_bytes,
                    observed_at,
                ),
            )


_VERSION_COLUMNS: dict[str, str] = {
    key: key for key in (
        "statement_version_id", "entity", "market", "security_id", "exchange",
        "code", "provider", "statement_type", "period_end", "period_kind",
        "period_start", "consolidation", "currency", "provider_rType",
        "provider_publish_date", "provider_update_time", "provider_is_audit",
        "provider_data_source", "provider_date_description",
        "provider_report_date_type", "canonical_report_sha256",
        "normalizer_version", "source_id", "document_id", "source_url",
        "row_count", "captured_at", "first_seen_at", "last_checked_at",
    )
}


def _version_public(version: sqlite3.Row, *, rows: list[dict[str, Any]]) -> dict[str, Any]:
    payload = {key: version[key] for key in _VERSION_COLUMNS}
    payload["report_hash"] = payload["canonical_report_sha256"]
    try:
        payload["quality_flags"] = json.loads(version["quality_flags_json"])
    except (json.JSONDecodeError, TypeError):
        payload["quality_flags"] = []
    payload["rows"] = rows
    return payload


def _row_public(row: sqlite3.Row) -> dict[str, Any]:
    payload = {
        "row_ordinal": row["row_ordinal"],
        "provider_field": row["provider_field"],
        "label": row["label"],
        "raw_value": row["raw_value"],
        "value_decimal": row["value_decimal"],
        "value_kind": row["value_kind"],
        "unit": row["unit"],
        "scale": row["scale"],
        "provider_precision": row["provider_precision"],
        "json_pointer": row["json_pointer"],
        "item_group_no": row["item_group_no"],
        "item_display_type": row["item_display_type"],
    }
    try:
        payload["quality_flags"] = json.loads(row["quality_flags_json"])
    except (json.JSONDecodeError, TypeError):
        payload["quality_flags"] = []
    return payload


def query_financial_statements_readonly(
    database_path: Path,
    *,
    security_id: str,
    statement_type: str,
    period_end_from: str | None = None,
    period_end_to: str | None = None,
    fields: Iterable[str] | None = None,
    max_rows: int | None = None,
    continuation: str | None = None,
) -> dict[str, Any]:
    """Read-only query: never creates, migrates or writes the catalog.

    Returns a named gap when the database or the long tables are absent.
    """
    if not isinstance(database_path, Path):
        raise TypeError("database_path must be pathlib.Path")
    if not database_path.is_file():
        return {
            "available": False,
            "reason": "catalog_database_missing",
            "security_id": security_id,
            "statement_type": statement_type,
            "versions": [],
        }
    uri = database_path.resolve().as_uri() + "?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True, timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        try:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            if "financial_statement_versions" not in tables or (
                "financial_statement_values" not in tables
            ):
                return {
                    "available": False,
                    "reason": "financial_statements_unavailable",
                    "security_id": security_id,
                    "statement_type": statement_type,
                    "versions": [],
                }
            versions = connection.execute(
                """
                SELECT * FROM financial_statement_versions
                WHERE security_id=? AND statement_type=?
                  AND (? IS NULL OR period_end>=?)
                  AND (? IS NULL OR period_end<=?)
                ORDER BY period_end DESC, consolidation, canonical_report_sha256
                """,
                (
                    security_id,
                    statement_type,
                    period_end_from,
                    period_end_from,
                    period_end_to,
                    period_end_to,
                ),
            ).fetchall()
            field_filter = tuple(fields) if fields is not None else None
            emitted = []
            for version in versions:
                rows = connection.execute(
                    """
                    SELECT * FROM financial_statement_values
                    WHERE statement_version_id=?
                      AND (? IS NULL OR provider_field IN
                          (SELECT value FROM json_each(?)))
                    ORDER BY row_ordinal
                    """,
                    (
                        version["statement_version_id"],
                        None if field_filter is None else 1,
                        None if field_filter is None
                        else canonical_json_bytes(list(field_filter)).decode("utf-8"),
                    ),
                ).fetchall()
                version_payload = _version_public(
                    version, rows=[_row_public(r) for r in rows]
                )
                if max_rows is not None:
                    version_payload["rows"] = version_payload["rows"][:max_rows]
                    version_payload["truncated"] = len(rows) > max_rows
                emitted.append(version_payload)
            return {
                "available": True,
                "security_id": security_id,
                "statement_type": statement_type,
                "versions": emitted,
                "continuation": None,
            }
        finally:
            connection.close()
    except (OSError, sqlite3.Error) as exc:
        return {
            "available": False,
            "reason": f"catalog_read_failed:{type(exc).__name__}",
            "security_id": security_id,
            "statement_type": statement_type,
            "versions": [],
        }


__all__ = [
    "FinancialStatementRepository",
    "PublishOutcome",
    "StatementSecurity",
    "StatementSource",
    "query_financial_statements_readonly",
    "statement_version_id",
]
