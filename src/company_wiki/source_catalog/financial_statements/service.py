"""Orchestration: identify once, reuse local versions, else bounded provider fetch.

One acquisition operation shares a single budget across every statement of the
request. Each fetched page is committed once as an immutable third-party
dataset original and publishes its normalized reports idempotently. Public
responses never contain database or filesystem paths.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ..canonical_writer import (
    CanonicalImportStatus,
    CanonicalSourceWriter,
    ThirdPartyDatasetOriginal,
)
from ..download_budget import AcquisitionBudget
from ..security_identity import (
    IdentityStatus,
    SecurityIdentityResolver,
    SecurityMasterStore,
    load_identity_master,
)
from ...source_contract.source_manifest import SOURCE_ID_PREFIX
from ..service import SourceCatalog
from . import normalize
from .contracts import (
    STATEMENTS_RESPONSE_SCHEMA_VERSION,
    StatementsRequest,
)
from .repository import (
    FinancialStatementRepository,
    StatementSecurity,
    StatementSource,
)
from .sina_provider import (
    SINA_PROVIDER_ID,
    SinaProviderError,
    SinaStatementsProvider,
    StatementFetchResult,
)

DEFAULT_MAX_PAGES = 64
DEFAULT_PAGE_SIZE = 10
#: response row/byte bounds so one bounded stdout cannot be flooded by a
#: whole-market statement export; callers page with continuations.
DEFAULT_MAX_ROWS = 20000

_TERMINAL_EXHAUSTED = frozenset({"end_of_data", "period_boundary", "no_data"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class _StatementOutcome:
    status: str
    payload: dict[str, Any]


class FinancialStatementsService:
    def __init__(
        self,
        *,
        catalog: SourceCatalog,
        writer: CanonicalSourceWriter,
        provider: SinaStatementsProvider | None,
        max_pages: int = DEFAULT_MAX_PAGES,
        page_size: int = DEFAULT_PAGE_SIZE,
        clock=time.time,
    ):
        self.catalog = catalog
        self.writer = writer
        self.provider = provider
        self.max_pages = max_pages
        self.page_size = page_size
        self.repository = FinancialStatementRepository(catalog.store)

    # -- identity ----------------------------------------------------------

    def _identify(self, request: StatementsRequest) -> dict[str, Any] | None:
        store = SecurityMasterStore(self.catalog.config.catalog_dir / "security_master")
        master = load_identity_master(store, market="CN")
        result = SecurityIdentityResolver(master).identify(
            request.company_query, market="CN"
        )
        if result.status is not IdentityStatus.RESOLVED or result.resolved is None:
            return None
        resolved = result.resolved
        return {
            "canonical_name": resolved.canonical_name,
            "market": resolved.market,
            "exchange": resolved.exchange,
            "security_id": resolved.security_id,
            "code": resolved.ticker,
            "match_basis": resolved.match_basis,
        }

    # -- request entry -----------------------------------------------------

    def handle_request(self, request: StatementsRequest) -> dict[str, Any]:
        retrieved_at = _utc_now()
        response: dict[str, Any] = {
            "schema_version": STATEMENTS_RESPONSE_SCHEMA_VERSION,
            "request": request.to_public_dict(),
            "retrieved_at": retrieved_at,
            "company_identity": None,
            "status": "not_found",
            "statements": [],
            "usage": {"http_requests": 0, "response_bytes": 0, "cost_usd": "0.00"},
        }
        identity = self._identify(request)
        if identity is None:
            response["status"] = "not_found"
            response["reason"] = "company_identity_not_resolved"
            return response
        response["company_identity"] = {
            key: identity[key]
            for key in ("canonical_name", "market", "exchange", "security_id")
        }
        security = StatementSecurity(
            entity=identity["canonical_name"],
            market=identity["market"],
            security_id=identity["security_id"],
            exchange=identity["exchange"],
            code=identity["code"],
        )
        budget = self._budget(request)
        outcomes: list[_StatementOutcome] = []
        for statement_type in request.statements:
            outcomes.append(
                self._handle_statement(
                    request=request,
                    security=security,
                    statement_type=statement_type,
                    budget=budget,
                    retrieved_at=retrieved_at,
                )
            )
        response["statements"] = [outcome.payload for outcome in outcomes]
        response["status"] = self._overall_status(outcomes)
        response["usage"] = {
            "http_requests": budget.http_exchanges_used,
            "response_bytes": budget.response_bytes_used,
            "cost_usd": str(budget.cost_usd_used) if budget.cost_usd_used else "0.00",
        }
        return response

    def _budget(self, request: StatementsRequest) -> AcquisitionBudget:
        limits = request.acquisition_limits
        if limits is None:
            # reuse-only request: no network budget is ever needed; a shared
            # inert ceiling still keeps the aggregate usage honest.
            return AcquisitionBudget.from_limits(
                max_response_bytes=1, max_seconds=1.0, max_cost_usd="0.00"
            )
        return AcquisitionBudget.from_limits(
            max_response_bytes=limits.max_bytes,
            max_seconds=limits.timeout_seconds,
            max_cost_usd=limits.max_cost_usd,
        )

    @staticmethod
    def _overall_status(outcomes: list[_StatementOutcome]) -> str:
        statuses = [outcome.status for outcome in outcomes]
        if all(status == "complete" for status in statuses):
            return "complete"
        if all(status == "not_found" for status in statuses):
            return "not_found"
        return "partial"

    # -- one statement ----------------------------------------------------

    def _handle_statement(
        self,
        *,
        request: StatementsRequest,
        security: StatementSecurity,
        statement_type: str,
        budget: AcquisitionBudget,
        retrieved_at: str,
    ) -> _StatementOutcome:
        provider = SINA_PROVIDER_ID
        observation = self.repository.coverage_observation(
            security_id=security.security_id, provider=provider,
            statement_type=statement_type,
        )
        local = self.repository.local_coverage(
            security_id=security.security_id, statement_type=statement_type
        )
        period_from = request.effective_period_from
        period_to = request.period_end_to
        selected = self._selected_periods(
            local["period_ends"], request, period_from, period_to
        )
        coverage = {
            "observed_periods": len(selected),
            "pages": 0,
            "first_period_end": selected[0] if selected else None,
            "last_period_end": selected[-1] if selected else None,
            "advertised_report_count": (
                observation["advertised_report_count"] if observation else None
            ),
            "terminal_reason": (
                observation["terminal_reason"] if observation else None
            ),
        }
        usage = {"http_requests": 0, "response_bytes": 0, "cost_usd": "0.00"}
        error_code: str | None = None
        fetched = None
        if self._needs_fetch(request, selected, observation, local):
            exchange_before = budget.http_exchanges_used
            bytes_before = budget.response_bytes_used
            fetched = self._fetch_statement(
                request=request, security=security,
                statement_type=statement_type, budget=budget,
            )
            if fetched is not None:
                usage = {
                    "http_requests": fetched.http_exchanges - exchange_before,
                    "response_bytes": fetched.response_bytes - bytes_before,
                    "cost_usd": fetched.cost_usd,
                }
                if fetched.terminal_reason == "provider_error":
                    status = "unavailable"
                    error_code = fetched.error_code
                    fetched_pages = 0
                elif fetched.terminal_reason == "no_data":
                    status = "not_found"
                    fetched_pages = len(fetched.pages)
                else:
                    self._persist_statement(
                        security=security, statement_type=statement_type,
                        fetched=fetched, retrieved_at=retrieved_at,
                    )
                    local = self.repository.local_coverage(
                        security_id=security.security_id,
                        statement_type=statement_type,
                    )
                    selected = self._selected_periods(
                        local["period_ends"], request, period_from, period_to
                    )
                    fetched_pages = len(fetched.pages)
                    status = (
                        "complete"
                        if fetched.terminal_reason in _TERMINAL_EXHAUSTED
                        and selected
                        else "partial"
                    )
                coverage.update(
                    {
                        "observed_periods": len(selected),
                        "pages": fetched_pages,
                        "first_period_end": selected[0] if selected else None,
                        "last_period_end": selected[-1] if selected else None,
                        "advertised_report_count": fetched.observed_period_count,
                        "terminal_reason": fetched.terminal_reason,
                    }
                )
            else:  # provider unavailable object or fetch not possible
                status = "unavailable"
                error_code = "provider_unavailable"
        elif selected:
            status = "complete"
        else:
            status = "not_found"
        if fetched is None and observation is not None:
            coverage["advertised_report_count"] = observation["advertised_report_count"]
            coverage["terminal_reason"] = observation["terminal_reason"]

        point_in_time_quality = self._point_in_time_quality(request)
        query = self.repository.query_statement_rows(
            security_id=security.security_id,
            statement_type=statement_type,
            period_end_from=period_from,
            period_end_to=period_to,
            max_rows=DEFAULT_MAX_ROWS,
        )
        reports = [
            _report_payload(version, request)
            for version in query["versions"]
            if version["period_kind"] in request.report_types
        ]
        if request.knowledge_mode == "point_in_time":
            if reports and all(
                report["pit_verified"] is True for report in reports
            ):
                point_in_time_quality = "pit_verified"
            else:
                point_in_time_quality = "historical_asof_unverifiable"
        payload = {
            "statement_type": statement_type,
            "status": status,
            "provider": provider,
            "knowledge_mode": request.knowledge_mode,
            "point_in_time_quality": point_in_time_quality,
            "coverage": coverage,
            "usage": usage,
            "reports": reports,
        }
        if error_code:
            payload["error_code"] = error_code
        return _StatementOutcome(status=status, payload=payload)

    @staticmethod
    def _selected_periods(
        period_ends: list[str],
        request: StatementsRequest,
        period_from: str | None,
        period_to: str | None,
    ) -> list[str]:
        selected = [
            period
            for period in period_ends
            if (period_from is None or period >= period_from)
            and (period_to is None or period <= period_to)
        ]
        kinds = set(request.report_types)
        compact_kinds = {}
        for period in selected:
            compact = period.replace("-", "")
            try:
                compact_kinds[period] = normalize.parse_period_kind(compact)
            except normalize.NormalizeProtocolError:
                compact_kinds[period] = None
        return [p for p in selected if compact_kinds[p] in kinds]

    @staticmethod
    def _needs_fetch(
        request: StatementsRequest,
        selected: list[str],
        observation: dict[str, Any] | None,
        local: dict[str, Any],
    ) -> bool:
        if request.intent == "reuse_only":
            return False
        if request.intent == "refresh":
            return True
        # fetch_if_missing: a full local hit serves without any HTTP.
        if observation is None or not selected:
            return True
        stored_periods = len(local["period_ends"])
        if observation.get("observed_periods") != stored_periods:
            return True
        if observation.get("terminal_reason") not in _TERMINAL_EXHAUSTED:
            return True
        return False

    def _fetch_statement(
        self,
        *,
        request: StatementsRequest,
        security: StatementSecurity,
        statement_type: str,
        budget: AcquisitionBudget,
    ) -> StatementFetchResult | None:
        if self.provider is None:
            return None
        try:
            return self.provider.fetch_statement(
                exchange=security.exchange,
                code=security.code,
                statement_type=statement_type,
                report_types=request.report_types,
                max_pages=self.max_pages,
                page_size=self.page_size,
                budget=budget,
                stop_before_period=(
                    request.effective_period_from.replace("-", "")
                    if request.effective_period_from
                    else None
                ),
            )
        except SinaProviderError:
            return None

    def _persist_statement(
        self,
        *,
        security: StatementSecurity,
        statement_type: str,
        fetched: StatementFetchResult,
        retrieved_at: str,
    ) -> None:
        published_new: list[str] = []
        for page in fetched.pages:
            staged = self.writer.staging_root / (
                f"{security.security_id}-{statement_type}-page{page.page_number}.json"
            )
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_bytes(page.raw_bytes)
            original = ThirdPartyDatasetOriginal(
                entity=security.entity,
                market=security.market,
                security_id=security.security_id,
                title=(
                    f"Sina {page.statement_source} {fetched.paper_code} "
                    f"page {page.page_number}"
                ),
                source_url=page.url,
                document_kind="financial_statement_dataset",
                publisher="新浪财经",
                provider=SINA_PROVIDER_ID,
                provider_document_id=(
                    f"sina:{fetched.paper_code}:{page.statement_source}:"
                    f"page{page.page_number}"
                ),
            )
            result = self.writer.import_third_party_dataset_staged(
                request_id=(
                    f"{security.security_id}-{statement_type}-{page.page_number}"
                ),
                original=original,
                staged_path=staged,
                content_sha256=page.sha256,
                byte_size=len(page.raw_bytes),
                mime_type="application/json",
                retrieved_at=retrieved_at,
                capture_receipt={
                    "http_status": 200,
                    "url": page.url,
                    "statement_type": statement_type,
                    "page_number": page.page_number,
                },
            )
            if result.status is CanonicalImportStatus.IMPORTED_NEW:
                published_new.append(result.source_id)
            normalized = page.normalized(statement_type)
            self.repository.publish_reports(
                security=security,
                source=StatementSource(
                    source_id=result.source_id,
                    document_id=result.source_ref.document_id,
                    content_sha256=result.content_sha256,
                    page_number=page.page_number,
                    url=page.url,
                ),
                reports=normalized.reports,
                retrieved_at=retrieved_at,
            )
        periods = fetched.unique_periods_list
        self.repository.record_coverage_observation(
            security_id=security.security_id,
            provider=SINA_PROVIDER_ID,
            statement_type=statement_type,
            advertised_report_count=fetched.observed_period_count,
            observed_periods=len(periods),
            first_period_end=normalize.iso_period(periods[-1]) if periods else None,
            last_period_end=normalize.iso_period(periods[0]) if periods else None,
            terminal_reason=fetched.terminal_reason,
            http_requests=fetched.http_exchanges,
            response_bytes=fetched.response_bytes,
            observed_at=retrieved_at,
        )

    @staticmethod
    def _point_in_time_quality(request: StatementsRequest) -> str:
        if request.knowledge_mode == "point_in_time":
            return "historical_asof_unverifiable"
        return "current_snapshot"


def _report_payload(version: dict[str, Any], request: StatementsRequest) -> dict[str, Any]:
    """One public report — the single builder shared by service and reuse-only."""
    if (
        request.knowledge_mode == "point_in_time"
        and version["captured_at"] > request.as_of_date
    ):
        pit_verified = False
    else:
        pit_verified = True if request.knowledge_mode == "point_in_time" else None
    rows = [
        {
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
            "quality_flags": row["quality_flags"],
        }
        for row in version["rows"]
    ]
    source_id = version["source_id"]
    prefix = SOURCE_ID_PREFIX
    content_sha = source_id[len(prefix):] if source_id.startswith(prefix) else None
    return {
        "statement_version_id": version["statement_version_id"],
        "statement_type": version["statement_type"],
        "period_end": version["period_end"],
        "period_kind": version["period_kind"],
        "period_start": version["period_start"],
        "consolidation": version["consolidation"],
        "currency": version["currency"],
        "provider_rType": version["provider_rType"],
        "provider_publish_date": version["provider_publish_date"],
        "provider_update_time": version["provider_update_time"],
        "provider_is_audit": version["provider_is_audit"],
        "report_hash": version["report_hash"],
        "normalizer_version": version["normalizer_version"],
        "quality_flags": version["quality_flags"],
        "captured_at": version["captured_at"],
        "pit_verified": pit_verified,
        "source_ref": {
            "document_id": version["document_id"],
            "source_id": source_id,
            "content_sha256": content_sha,
            "byte_size": None,
            "mime_type": "application/json",
            "schema_version": "2.0",
        },
        "source_locator": (
            "/result/data/report_list/" + version["period_end"].replace("-", "")
        ),
        "rows": rows,
    }


def handle_reuse_only_request(request: StatementsRequest, config) -> dict[str, Any]:
    """Zero-write reuse-only response: no CatalogStore, no database creation.

    Identity comes from the security master snapshots; statement data from
    the read-only query helper that reports named gaps instead of creating
    or migrating anything.
    """
    from ..models import CatalogConfig  # noqa: F401 - type reference only
    from .repository import query_financial_statements_readonly

    retrieved_at = _utc_now()
    response: dict[str, Any] = {
        "schema_version": STATEMENTS_RESPONSE_SCHEMA_VERSION,
        "request": request.to_public_dict(),
        "retrieved_at": retrieved_at,
        "company_identity": None,
        "status": "not_found",
        "statements": [],
        "usage": {"http_requests": 0, "response_bytes": 0, "cost_usd": "0.00"},
    }
    try:
        store = SecurityMasterStore(config.catalog_dir / "security_master")
        master = load_identity_master(store, market="CN")
        identity_result = SecurityIdentityResolver(master).identify(
            request.company_query, market="CN"
        )
    except Exception:  # noqa: BLE001 - identity gap, not a crash
        response["reason"] = "company_identity_not_resolved"
        return response
    if identity_result.status is not IdentityStatus.RESOLVED or not identity_result.resolved:
        response["reason"] = "company_identity_not_resolved"
        return response
    resolved = identity_result.resolved
    response["company_identity"] = {
        key: getattr(resolved, key)
        for key in ("canonical_name", "market", "exchange", "security_id")
    }
    outcomes: list[_StatementOutcome] = []
    for statement_type in request.statements:
        view = query_financial_statements_readonly(
            config.database_path,
            security_id=resolved.security_id,
            statement_type=statement_type,
            period_end_from=request.effective_period_from,
            period_end_to=request.period_end_to,
        )
        if not view.get("available"):
            payload = {
                "statement_type": statement_type,
                "status": "not_found",
                "provider": SINA_PROVIDER_ID,
                "knowledge_mode": request.knowledge_mode,
                "point_in_time_quality": "current_snapshot"
                if request.knowledge_mode == "current_snapshot"
                else "historical_asof_unverifiable",
                "coverage": {
                    "observed_periods": 0,
                    "pages": 0,
                    "first_period_end": None,
                    "last_period_end": None,
                    "advertised_report_count": None,
                    "terminal_reason": None,
                },
                "usage": {"http_requests": 0, "response_bytes": 0, "cost_usd": "0.00"},
                "reports": [],
                "gap_reason": view.get("reason"),
            }
            outcomes.append(_StatementOutcome(status="not_found", payload=payload))
            continue
        versions = [
            version
            for version in view["versions"]
            if version["period_kind"] in request.report_types
        ]
        reports = [_report_payload(version, request) for version in versions]
        period_ends = [version["period_end"] for version in versions]
        point_quality = "current_snapshot"
        if request.knowledge_mode == "point_in_time":
            point_quality = (
                "pit_verified"
                if reports and all(r["pit_verified"] is True for r in reports)
                else "historical_asof_unverifiable"
            )
        payload = {
            "statement_type": statement_type,
            "status": "complete" if reports else "not_found",
            "provider": SINA_PROVIDER_ID,
            "knowledge_mode": request.knowledge_mode,
            "point_in_time_quality": point_quality,
            "coverage": {
                "observed_periods": len(period_ends),
                "pages": 0,
                "first_period_end": period_ends[-1] if period_ends else None,
                "last_period_end": period_ends[0] if period_ends else None,
                "advertised_report_count": None,
                "terminal_reason": None,
            },
            "usage": {"http_requests": 0, "response_bytes": 0, "cost_usd": "0.00"},
            "reports": reports,
        }
        outcomes.append(
            _StatementOutcome(status=payload["status"], payload=payload)
        )
    response["statements"] = [outcome.payload for outcome in outcomes]
    response["status"] = FinancialStatementsService._overall_status(outcomes)
    return response


__all__ = [
    "DEFAULT_MAX_PAGES",
    "DEFAULT_MAX_ROWS",
    "DEFAULT_PAGE_SIZE",
    "FinancialStatementsService",
    "handle_reuse_only_request",
]
