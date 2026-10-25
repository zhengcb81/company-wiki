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

_STATEMENT_BY_PROVIDER_SOURCE = {
    "lrb": "income_statement",
    "fzb": "balance_sheet",
    "llb": "cash_flow",
}


def _detect_statement_source(raw: bytes) -> str | None:
    """Read the provider's own ``item_source`` marker from committed bytes."""
    import json as _json

    try:
        payload = _json.loads(raw.decode("utf-8"))
        data = payload["result"]["data"]
        for entry in (data.get("report_list") or {}).values():
            for row in entry.get("data") or []:
                value = row.get("item_source")
                if isinstance(value, str) and value in _STATEMENT_BY_PROVIDER_SOURCE:
                    return value
    except (ValueError, KeyError, TypeError, AttributeError):
        return None
    return None


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

    def _identify(
        self, request: StatementsRequest
    ) -> tuple[dict[str, Any] | None, Any]:
        store = SecurityMasterStore(self.catalog.config.catalog_dir / "security_master")
        master = load_identity_master(store, market="CN")
        result = SecurityIdentityResolver(master).identify(
            request.company_query, market="CN"
        )
        if result.status is not IdentityStatus.RESOLVED or result.resolved is None:
            return None, result
        resolved = result.resolved
        return {
            "canonical_name": resolved.canonical_name,
            "market": resolved.market,
            "exchange": resolved.exchange,
            "security_id": resolved.security_id,
            "code": resolved.ticker,
            "match_basis": resolved.match_basis,
        }, result

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
        identity, identity_result = self._identify(request)
        if identity is None:
            response["status"] = "not_found"
            _apply_identity_gap(response, identity_result)
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
        if all(status == "unavailable" for status in statuses):
            return "unavailable"
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
                        fetch_from=period_from, fetch_to=period_to,
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
        continuation = request.continuation
        if continuation is not None:
            # A continuation token names one version of one statement; other
            # statements in the same request start from their first version
            # instead of being silently skipped (W19-R12).
            head = continuation.split(":", 1)[0]
            if self.repository.statement_type_of_version(head) != statement_type:
                continuation = None
        query = self.repository.query_statement_rows(
            security_id=security.security_id,
            statement_type=statement_type,
            period_end_from=period_from,
            period_end_to=period_to,
            fields=request.fields,
            max_rows=DEFAULT_MAX_ROWS,
            continuation=continuation,
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
            "continuation": query.get("continuation"),
            "truncated": bool(query.get("truncated")),
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
        """fetch_if_missing reuse decision, per pagination direction (W19-R10).

        The stored observation records the exhausted fetch envelope:
        ``fetched_from`` NULL means the provider's older history is exhausted
        (terminating null page reached), covering any older or unbounded
        request; ``fetched_to`` is the upper bound that this exhausted
        envelope already answered. budget_stopped / max_pages / count_changed
        / duplicate_page / no_progress always re-fetch.
        """
        if request.intent == "reuse_only":
            return False
        if request.intent == "refresh":
            return True
        if observation is None or not selected:
            return True
        stored_periods = len(local["period_ends"])
        if observation.get("observed_periods") != stored_periods:
            return True
        terminal = observation.get("terminal_reason")
        last_period_end = observation.get("last_period_end") or ""
        fetched_from = observation.get("fetched_from")
        fetched_to = observation.get("fetched_to")
        want_from = request.effective_period_from
        want_to = request.period_end_to
        if terminal == "end_of_data":
            # Exhausted envelope: older direction covered only when the fetch
            # itself was unbounded older (fetched_from NULL).
            if want_from is not None and fetched_from is not None and want_from < fetched_from:
                return True
            if (
                want_to is not None
                and last_period_end
                and want_to > last_period_end
                and (fetched_to is None or want_to > fetched_to)
            ):
                # Beyond both the captured newest period and every exhausted
                # envelope: the provider may have newer data since capture.
                return True
            return False
        if terminal == "period_boundary":
            # Reuse only strictly inside the previously fetched envelope.
            if fetched_from is None:
                return True
            if want_from is None or want_from < fetched_from:
                return True
            if want_to is not None and want_to > last_period_end and (
                fetched_to is None or want_to > fetched_to
            ):
                return True
            return False
        # Incomplete terminations: re-fetch.
        return True

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

    def _commit_and_publish_page(
        self,
        *,
        security: StatementSecurity,
        statement_type: str,
        raw_bytes: bytes,
        sha256: str,
        page_number: int,
        url: str | None,
        paper_code: str,
        source_key: str,
        retrieved_at: str,
    ):
        """One page: commit original bytes once, then publish its reports.

        Shared by the fetch path and the offline replay path (W19-R8), so a
        normalization failure can be replayed from the committed SourceRef
        without any network access.
        """
        staged = self.writer.staging_root / (
            f"{security.security_id}-{statement_type}-page{page_number}.json"
        )
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_bytes(raw_bytes)
        original = ThirdPartyDatasetOriginal(
            entity=security.entity,
            market=security.market,
            security_id=security.security_id,
            title=f"Sina {source_key} {paper_code} page {page_number}",
            source_url=url,
            document_kind="financial_statement_dataset",
            publisher="新浪财经",
            provider=SINA_PROVIDER_ID,
            provider_document_id=(
                f"sina:{paper_code}:{source_key}:page{page_number}"
            ),
        )
        result = self.writer.import_third_party_dataset_staged(
            request_id=f"{security.security_id}-{statement_type}-{page_number}",
            original=original,
            staged_path=staged,
            content_sha256=sha256,
            byte_size=len(raw_bytes),
            mime_type="application/json",
            retrieved_at=retrieved_at,
            capture_receipt={
                "http_status": 200 if url else None,
                "url": url,
                "statement_type": statement_type,
                "page_number": page_number,
                "replayed": url is None,
            },
        )
        normalized = normalize.normalize_page(
            raw_bytes, statement_type=statement_type, page_number=page_number
        )
        publish = self.repository.publish_reports(
            security=security,
            source=StatementSource(
                source_id=result.source_id,
                document_id=result.source_ref.document_id,
                content_sha256=result.content_sha256,
                page_number=page_number,
                url=url or "",
            ),
            reports=normalized.reports,
            retrieved_at=retrieved_at,
        )
        return result, publish

    def _persist_statement(
        self,
        *,
        security: StatementSecurity,
        statement_type: str,
        fetched: StatementFetchResult,
        retrieved_at: str,
        fetch_from: str | None,
        fetch_to: str | None,
    ) -> None:
        published_new: list[str] = []
        for page in fetched.pages:
            result, _ = self._commit_and_publish_page(
                security=security,
                statement_type=statement_type,
                raw_bytes=page.raw_bytes,
                sha256=page.sha256,
                page_number=page.page_number,
                url=page.url,
                paper_code=fetched.paper_code,
                source_key=page.statement_source,
                retrieved_at=retrieved_at,
            )
            if result.status is CanonicalImportStatus.IMPORTED_NEW:
                published_new.append(result.source_id)
        periods = fetched.unique_periods_list
        # Exhausted older direction (terminating null page reached) covers
        # ANY future older/unbounded request; a boundary stop records the
        # boundary it actually stopped at (W19-R10).
        fetched_from = None if fetched.terminal_reason == "end_of_data" else fetch_from
        self.repository.record_coverage_observation(
            security_id=security.security_id,
            provider=SINA_PROVIDER_ID,
            statement_type=statement_type,
            advertised_report_count=fetched.observed_period_count,
            observed_periods=len(periods),
            first_period_end=normalize.iso_period(periods[-1]) if periods else None,
            last_period_end=normalize.iso_period(periods[0]) if periods else None,
            terminal_reason=fetched.terminal_reason,
            fetched_from=fetched_from,
            fetched_to=fetch_to,
            http_requests=fetched.http_exchanges,
            response_bytes=fetched.response_bytes,
            observed_at=retrieved_at,
        )

    def _source_owner_security(self, source_id: str) -> str | None:
        """Who owns this committed page: published versions, else sidecar.

        Returns None when ownership cannot be verified (never published and
        no readable provenance sidecar) so callers can refuse fail-closed.
        """
        import json as _json

        row = self.catalog.store.fetchone(
            "SELECT DISTINCT security_id FROM financial_statement_versions "
            "WHERE source_id=? LIMIT 1",
            (source_id,),
        )
        if row is not None:
            return row["security_id"]
        location = self.catalog.store.fetchone(
            "SELECT relative_path FROM locations WHERE source_id=? "
            "AND role='original_primary' AND location_status='active' "
            "ORDER BY location_id LIMIT 1",
            (source_id,),
        )
        if location is None:
            return None
        from ..source_location import resolve_source_location

        company_root = next(
            (r for r in self.catalog.config.roots if r.kind == "company_raw"), None
        )
        if company_root is None:
            return None
        try:
            original = resolve_source_location(company_root, location["relative_path"])
            sidecar = original.with_name(original.name + ".source.json")
            payload = _json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        value = payload.get("security_id")
        return value if isinstance(value, str) and value else None

    def replay_source(
        self, *, request: StatementsRequest, source_id: str
    ) -> dict[str, Any]:
        """W19-R8: re-normalize one committed provider page with zero network.

        The statement type is detected from the provider's own ``item_source``
        marker inside the committed bytes (lrb/fzb/llb); no caller guess.
        """
        from ..source_reader import SourceReadError, SourceVersionReader

        prefix = SOURCE_ID_PREFIX
        if not isinstance(source_id, str) or not source_id.startswith(prefix):
            raise ValueError("source_id must be a canonical company-wiki source id")
        sha256 = source_id[len(prefix):]
        identity, _ = self._identify(request)
        if identity is None:
            return {"status": "not_found", "reason": "company_identity_not_resolved"}
        document_row = self.catalog.store.fetchone(
            "SELECT document_id FROM documents WHERE primary_source_id=? "
            "AND source_status='active' ORDER BY document_id LIMIT 1",
            (source_id,),
        )
        if document_row is None:
            raise ValueError("source is not an active document primary source")
        owner = self._source_owner_security(source_id)
        if owner is None:
            # Fail closed: an unverifiable owner must never be re-published
            # under the requesting company (W19-R11).
            raise ValueError("cannot verify source ownership; refusing replay")
        if owner != identity["security_id"]:
            raise ValueError(
                "committed source belongs to a different security; refusing replay"
            )
        reader = SourceVersionReader(self.catalog)
        try:
            ref = reader.query_ref(document_row["document_id"], source_id, sha256)
            content = reader.open_version(ref, purpose="source_export")
        except SourceReadError:
            raise ValueError("committed source bytes are unreadable") from None
        source_key = _detect_statement_source(content.data)
        if source_key is None:
            raise ValueError("committed page carries no provider statement marker")
        statement_type = _STATEMENT_BY_PROVIDER_SOURCE[source_key]
        # Protocol guard before touching storage: a malformed committed page
        # must refuse replay before any bytes are re-committed.
        normalize.normalize_page(
            content.data, statement_type=statement_type, page_number=0
        )
        security = StatementSecurity(
            entity=identity["canonical_name"],
            market=identity["market"],
            security_id=identity["security_id"],
            exchange=identity["exchange"],
            code=identity["code"],
        )
        paper_code = f"{identity['exchange'].lower()}{identity['code']}"
        result, publish = self._commit_and_publish_page(
            security=security,
            statement_type=statement_type,
            raw_bytes=content.data,
            sha256=sha256,
            page_number=0,
            url=None,
            paper_code=paper_code,
            source_key=source_key,
            retrieved_at=_utc_now(),
        )
        return {
            "status": "complete",
            "company_identity": {
                key: identity[key]
                for key in ("canonical_name", "market", "exchange", "security_id")
            },
            "statements": [
                {
                    "statement_type": statement_type,
                    "status": "complete",
                    "provider": SINA_PROVIDER_ID,
                    "replayed_source_id": source_id,
                    "new_version_ids": list(publish.new_version_ids),
                    "reused_version_ids": list(publish.reused_version_ids),
                    "usage": {
                        "http_requests": 0, "response_bytes": 0, "cost_usd": "0.00",
                    },
                }
            ],
            "usage": {"http_requests": 0, "response_bytes": 0, "cost_usd": "0.00"},
            "retrieved_at": _utc_now(),
        }

    @staticmethod
    def _point_in_time_quality(request: StatementsRequest) -> str:
        if request.knowledge_mode == "point_in_time":
            return "historical_asof_unverifiable"
        return "current_snapshot"


def _apply_identity_gap(response: dict[str, Any], identity_result: Any) -> None:
    """Name the identity gap honestly instead of collapsing every failure.

    ``missing`` stays the generic not-resolved refusal; ``ambiguous`` carries
    the verified candidates so callers can disambiguate by ticker/security_id
    (e.g. BSE companies carrying both legacy 4xxxxx and 92xxxx codes).
    """
    status = getattr(identity_result, "status", None)
    if status is IdentityStatus.AMBIGUOUS:
        response["reason"] = "company_identity_ambiguous"
        response["candidates"] = [
            {
                "canonical_name": candidate.canonical_name,
                "market": candidate.market,
                "exchange": candidate.exchange,
                "ticker": candidate.ticker,
                "security_id": candidate.security_id,
                "match_basis": candidate.match_basis,
            }
            for candidate in getattr(identity_result, "candidates", ())[:10]
        ]
    elif status is IdentityStatus.CONFLICT:
        response["reason"] = "company_identity_conflict"
    else:
        response["reason"] = "company_identity_not_resolved"


def _report_payload(version: dict[str, Any], request: StatementsRequest) -> dict[str, Any]:
    """One public report — the single builder shared by service and reuse-only."""
    # Compare by DATE only: a version captured on as_of_date itself (even a
    # later clock time that same day) is point-in-time-valid.
    if (
        request.knowledge_mode == "point_in_time"
        and version["captured_at"][:10] > request.as_of_date
    ):
        pit_verified = False
    else:
        pit_verified = True if request.knowledge_mode == "point_in_time" else None
    period_semantics = (
        "instant" if version["statement_type"] == "balance_sheet" else "duration"
    )
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
        "period_semantics": period_semantics,
        "retrieved_at": version["captured_at"],
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
        _apply_identity_gap(response, identity_result)
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
            fields=request.fields,
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
                "continuation": None,
                "truncated": False,
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
            "continuation": None,
            "truncated": any(version.get("truncated") for version in versions),
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
