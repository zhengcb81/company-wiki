"""Staging-only acquisition contracts and explicit market routing."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date, datetime
from enum import Enum
import hashlib
import json
from pathlib import Path
import re
import shutil
from typing import Any, Protocol, runtime_checkable

from .authorization import DownloadAuthorization
from .download_budget import AcquisitionBudget, AcquisitionBudgetExceeded
from .gap_plan import GapPlan, build_gap_plan
from .resolver import (
    ResolutionResult,
    ResolutionStatus,
    SourceRequest,
    SourceResolver,
)
from .service import SourceCatalog


ACQUISITION_SCHEMA_VERSION = "1.0"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?"
    r"(?:\+[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?$"
)


class AcquisitionError(RuntimeError):
    """Raised when an adapter or staged asset violates the acquisition contract."""


class MarketRoutingError(AcquisitionError):
    """Raised when a security market has no explicitly configured adapter."""


class AcquisitionStatus(str, Enum):
    REUSED = "reused"
    MISSING = "missing"
    AMBIGUOUS = "ambiguous"
    STAGED = "staged"
    GAP = "gap"  # WU-4.2: metadata-only plan returned, nothing downloaded
    SELECTED = "selected"  # internal preparation, never a completed ensure


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{name} must be non-empty trimmed text")
    return value


def _optional_text(value: Any, name: str) -> str | None:
    if value is None:
        return None
    return _text(value, name)


def _date(value: Any, name: str) -> str:
    value = _text(value, name)
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a valid YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{name} must be canonical YYYY-MM-DD")
    return value


def _optional_date(value: Any, name: str) -> str | None:
    if value is None:
        return None
    return _date(value, name)


@dataclass(frozen=True)
class DownloadCandidate:
    candidate_id: str
    provider: str
    provider_document_id: str
    market: str
    entity: str
    title: str
    source_url: str
    document_kind: str
    filing_date: str | None
    fiscal_year: int
    form_type: str | None = None
    fiscal_period: str | None = None
    language: str | None = None
    amended: bool = False
    etag: str | None = None
    last_modified: str | None = None
    remote_size: int | None = None
    adapter_payload_json: str | None = None
    schema_version: str = ACQUISITION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != ACQUISITION_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {ACQUISITION_SCHEMA_VERSION}")
        for name in (
            "candidate_id",
            "provider",
            "provider_document_id",
            "market",
            "entity",
            "title",
            "source_url",
            "document_kind",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "provider", self.provider.lower())
        object.__setattr__(self, "market", self.market.upper())
        object.__setattr__(self, "document_kind", self.document_kind.lower())
        if self.market not in {"CN", "HK", "US"}:
            raise ValueError("market must be CN, HK, or US")
        if not self.source_url.startswith("https://"):
            raise ValueError("source_url must be HTTPS")
        if self.document_kind == "investor_call_transcript":
            object.__setattr__(self, "filing_date", _optional_date(self.filing_date, "filing_date"))
        else:
            object.__setattr__(self, "filing_date", _date(self.filing_date, "filing_date"))
        for name in (
            "form_type",
            "fiscal_period",
            "language",
            "etag",
            "last_modified",
            "adapter_payload_json",
        ):
            object.__setattr__(self, name, _optional_text(getattr(self, name), name))
        if self.adapter_payload_json is not None:
            try:
                adapter_payload = json.loads(self.adapter_payload_json)
            except json.JSONDecodeError as exc:
                raise ValueError("adapter_payload_json must be valid JSON") from exc
            if not isinstance(adapter_payload, dict):
                raise ValueError("adapter_payload_json must contain a JSON object")
        if isinstance(self.fiscal_year, bool) or not isinstance(self.fiscal_year, int):
            raise TypeError("fiscal_year must be an integer")
        if not 1900 <= self.fiscal_year <= 2200:
            raise ValueError("fiscal_year is outside the supported range")
        if not isinstance(self.amended, bool):
            raise TypeError("amended must be boolean")
        if self.remote_size is not None and (
            isinstance(self.remote_size, bool)
            or not isinstance(self.remote_size, int)
            or self.remote_size <= 0
        ):
            raise ValueError("remote_size must be a positive integer or null")

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class DownloadReceipt:
    candidate_id: str
    provider: str
    provider_document_id: str
    source_url: str
    staged_path: str
    content_sha256: str
    byte_size: int
    mime_type: str
    retrieved_at: str
    http_status: int
    adapter_name: str
    adapter_version: str
    etag: str | None = None
    last_modified: str | None = None
    schema_version: str = ACQUISITION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != ACQUISITION_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {ACQUISITION_SCHEMA_VERSION}")
        for name in (
            "candidate_id",
            "provider",
            "provider_document_id",
            "source_url",
            "staged_path",
            "mime_type",
            "retrieved_at",
            "adapter_name",
            "adapter_version",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "provider", self.provider.lower())
        if not self.source_url.startswith("https://"):
            raise ValueError("source_url must be HTTPS")
        if not _SHA256_RE.fullmatch(self.content_sha256):
            raise ValueError("content_sha256 must be lowercase SHA-256")
        if (
            isinstance(self.byte_size, bool)
            or not isinstance(self.byte_size, int)
            or self.byte_size <= 0
        ):
            raise ValueError("byte_size must be a positive integer")
        if (
            isinstance(self.http_status, bool)
            or not isinstance(self.http_status, int)
            or not 100 <= self.http_status <= 599
        ):
            raise ValueError("http_status must be an HTTP status integer")
        if not _UTC_RE.fullmatch(self.retrieved_at):
            raise ValueError("retrieved_at must be UTC YYYY-MM-DDTHH:MM:SSZ")
        try:
            datetime.strptime(self.retrieved_at, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError as exc:
            raise ValueError("retrieved_at must be a valid UTC timestamp") from exc
        object.__setattr__(self, "etag", _optional_text(self.etag, "etag"))
        object.__setattr__(
            self, "last_modified", _optional_text(self.last_modified, "last_modified")
        )
        if not _SEMVER_RE.fullmatch(self.adapter_version):
            raise ValueError("adapter_version must be semantic version text")

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@runtime_checkable
class DownloadAdapter(Protocol):
    name: str
    version: str

    def discover(self, request: SourceRequest) -> tuple[DownloadCandidate, ...]: ...

    def fetch(
        self,
        candidate: DownloadCandidate,
        staging_dir: Path,
    ) -> DownloadReceipt: ...


def _validate_adapter(adapter: Any, name: str) -> DownloadAdapter:
    if not isinstance(adapter, DownloadAdapter):
        raise TypeError(f"{name} must implement DownloadAdapter")
    _text(adapter.name, f"{name}.name")
    _text(adapter.version, f"{name}.version")
    return adapter


@dataclass(frozen=True)
class AdapterRegistry:
    cn: DownloadAdapter
    hk: DownloadAdapter
    us: DownloadAdapter

    def __post_init__(self) -> None:
        object.__setattr__(self, "cn", _validate_adapter(self.cn, "cn"))
        object.__setattr__(self, "hk", _validate_adapter(self.hk, "hk"))
        object.__setattr__(self, "us", _validate_adapter(self.us, "us"))

    def for_market(self, market: str) -> DownloadAdapter:
        normalized = _text(market, "market").upper()
        if normalized == "CN":
            return self.cn
        if normalized == "HK":
            return self.hk
        if normalized == "US":
            return self.us
        raise MarketRoutingError(f"unsupported market: {market}")


@dataclass(frozen=True)
class AcquisitionResult:
    schema_version: str
    status: AcquisitionStatus
    resolution: ResolutionResult
    adapter_name: str | None = None
    candidate: DownloadCandidate | None = None
    receipt: DownloadReceipt | None = None
    reason: str | None = None
    gap_plan: GapPlan | None = None  # WU-4.2: metadata-only plan (status GAP)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status.value,
            "resolution": self.resolution.to_dict(),
            "adapter_name": self.adapter_name,
            "candidate": self.candidate.to_dict() if self.candidate else None,
            "receipt": self.receipt.to_dict() if self.receipt else None,
            "reason": self.reason,
            "gap_plan": self.gap_plan.to_dict() if self.gap_plan else None,
        }


def acquisition_target_sha256(request: SourceRequest, candidate: DownloadCandidate) -> str:
    """Stable target/staging lock identity, excluding modes, limits and TTLs."""
    target = {"market": candidate.market, "security": (request.security_id or request.entity).upper(),
              "document_kind": candidate.document_kind, "provider": candidate.provider,
              "accession": candidate.provider_document_id, "fiscal_year": candidate.fiscal_year,
              "fiscal_period": candidate.fiscal_period, "form_type": candidate.form_type}
    return hashlib.sha256(json.dumps(target, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


class AcquisitionCoordinator:
    """Reuse catalog sources first; otherwise permit only validated staging writes."""

    def __init__(
        self,
        *,
        catalog: SourceCatalog,
        adapters: AdapterRegistry,
        staging_root: Path,
    ):
        if not isinstance(catalog, SourceCatalog):
            raise TypeError("catalog must be SourceCatalog")
        if not isinstance(adapters, AdapterRegistry):
            raise TypeError("adapters must be AdapterRegistry")
        if not isinstance(staging_root, Path):
            raise TypeError("staging_root must be pathlib.Path")
        self.catalog = catalog
        self.adapters = adapters
        self.staging_root = staging_root
        staging = staging_root.resolve()
        for original_root in catalog.config.roots:
            original = original_root.path.resolve()
            if staging.is_relative_to(original) or original.is_relative_to(staging):
                raise AcquisitionError("staging root must not overlap configured original roots")
        # ZR-203: this coordinator is a WRITE flow — the writer initializer
        # may create the catalog, so the resolver's read-only reader then
        # opens an existing database (read paths never create it).
        _ = self.catalog.store

    def resolve_or_stage(
        self,
        request: SourceRequest,
        *,
        authorization: DownloadAuthorization | None = None,
        budget: AcquisitionBudget | None = None,
    ) -> AcquisitionResult:
        """Compatibility staging API; production transactions use select/stage.

        Legacy authorization objects describe requested target/caps only.
        Their unsigned policy/gap digests and expiry are not permissions.
        """
        scope = None
        if authorization is not None:
            if not isinstance(authorization, DownloadAuthorization):
                raise TypeError("authorization must be DownloadAuthorization")
            def scope(c):
                return (c.provider == authorization.provider
                        and c.provider_document_id in authorization.allowed_accessions)
            if authorization.max_items < 1:
                raise AcquisitionError("candidate scope allows no items")
            if budget is None:
                budget = AcquisitionBudget.from_limits(max_response_bytes=authorization.max_bytes,
                    max_seconds=30, max_cost_usd="0")
            else:
                budget.max_response_bytes = min(budget.max_response_bytes, authorization.max_bytes)
                if budget.response_bytes_used > budget.max_response_bytes:
                    raise AcquisitionError("candidate byte scope already exceeded")
        selected = self.select(request, budget=budget, candidate_scope=scope)
        if selected.status is not AcquisitionStatus.SELECTED:
            return selected
        return self.stage_selected(request, selected, budget=budget)

    def select(
        self, request: SourceRequest, *, budget: AcquisitionBudget | None = None,
        candidate_scope: Callable[[DownloadCandidate], bool] | None = None,
    ) -> AcquisitionResult:
        """Resolve or discover one target without fetching any original bytes."""
        if not isinstance(request, SourceRequest):
            raise TypeError("request must be SourceRequest")
        if budget is not None and not isinstance(budget, AcquisitionBudget):
            raise TypeError("budget must be AcquisitionBudget")
        if budget is not None:
            budget.ensure_open()
        resolution = SourceResolver(self.catalog).resolve(request)
        if resolution.status in {
            ResolutionStatus.REUSED_EXACT,
            ResolutionStatus.REUSED_EQUIVALENT,
        }:
            if request.mode == "latest_as_of":
                # WU-4.2: a local reuse is not proof of being up-to-date —
                # the provider must be consulted (metadata only) to decide
                # reuse vs gap. Fall through to the gap-plan path.
                pass
            elif candidate_scope is None:
                return AcquisitionResult(
                    schema_version=ACQUISITION_SCHEMA_VERSION,
                    status=AcquisitionStatus.REUSED,
                    resolution=resolution,
                    reason="existing_catalog_source_reused_before_adapter",
                )
        if resolution.status is ResolutionStatus.AMBIGUOUS:
            return AcquisitionResult(
                schema_version=ACQUISITION_SCHEMA_VERSION,
                status=AcquisitionStatus.AMBIGUOUS,
                resolution=resolution,
                reason=resolution.reason,
            )
        if resolution.status is ResolutionStatus.IDENTITY_CONFLICT:
            return AcquisitionResult(
                schema_version=ACQUISITION_SCHEMA_VERSION,
                status=AcquisitionStatus.MISSING,
                resolution=resolution,
                reason="identity_conflict_no_download",
            )
        if request.mode == "latest_as_of":
            return self._gap_plan_result(request, resolution, budget=budget,
                                         candidate_scope=candidate_scope)
        if not request.allow_download:
            return AcquisitionResult(
                schema_version=ACQUISITION_SCHEMA_VERSION,
                status=AcquisitionStatus.MISSING,
                resolution=resolution,
                reason="download_required_but_not_allowed",
            )
        if request.market is None:
            raise MarketRoutingError("market is required before adapter discovery")
        adapter = self.adapters.for_market(request.market)
        if budget is None:
            candidates = tuple(adapter.discover(request))
        else:
            self._require_bounded_adapter(adapter)
            budget.ensure_open()
            candidates = tuple(adapter.discover_bounded(request, budget))
        self._validate_candidates(request, candidates)
        candidates = tuple(c for c in candidates
                           if (candidate_scope is None or candidate_scope(c))
                           and (c.filing_date is None or c.filing_date <= request.as_of_date))
        if not candidates:
            return AcquisitionResult(
                schema_version=ACQUISITION_SCHEMA_VERSION,
                status=AcquisitionStatus.MISSING, resolution=resolution,
                adapter_name=adapter.name, reason="adapter_discovery_returned_no_candidate",
            )
        if len(candidates) != 1:
            return AcquisitionResult(
                schema_version=ACQUISITION_SCHEMA_VERSION,
                status=AcquisitionStatus.AMBIGUOUS, resolution=resolution,
                adapter_name=adapter.name, reason="adapter_discovery_returned_multiple_candidates",
            )
        return AcquisitionResult(schema_version=ACQUISITION_SCHEMA_VERSION,
            status=AcquisitionStatus.SELECTED, resolution=resolution,
            adapter_name=adapter.name, candidate=candidates[0], reason="candidate_selected")

    @staticmethod
    def _validate_candidates(request: SourceRequest, candidates: tuple[DownloadCandidate, ...]) -> None:
        for candidate in candidates:
            if not isinstance(candidate, DownloadCandidate):
                raise AcquisitionError("adapter returned a non-DownloadCandidate value")
            if candidate.market != request.market:
                raise AcquisitionError(
                    "adapter candidate market does not match request"
                )
            if candidate.document_kind != request.document_kind:
                raise AcquisitionError(
                    "adapter candidate document_kind does not match request"
                )
            if candidate.entity.casefold() != request.entity.casefold():
                raise AcquisitionError("adapter candidate entity does not match request")
            if request.provider and candidate.provider != request.provider:
                raise AcquisitionError("adapter candidate provider does not match request")
            if request.provider_document_id and candidate.provider_document_id != request.provider_document_id:
                raise AcquisitionError("adapter candidate accession does not match request")
            for field in ("fiscal_period", "form_type", "language"):
                requested = getattr(request, field)
                actual = getattr(candidate, field)
                if requested and actual and requested.casefold() != actual.casefold():
                    raise AcquisitionError(f"adapter candidate {field} does not match request")
            if (
                request.fiscal_year is not None
                and candidate.fiscal_year != request.fiscal_year
            ):
                raise AcquisitionError(
                    "adapter candidate fiscal_year does not match request"
                )

    def stage_selected(
        self, request: SourceRequest, selection: AcquisitionResult, *,
        budget: AcquisitionBudget | None = None,
    ) -> AcquisitionResult:
        """Recheck local identity, then stage the chosen target without rediscovery.

        The transaction service holds the target lock across this and import.
        """
        candidate = selection.candidate
        if selection.status is not AcquisitionStatus.SELECTED or candidate is None:
            raise AcquisitionError("staging requires a selected candidate")
        if not request.allow_download:
            raise AcquisitionError("staging requires a download request")
        self._validate_candidates(request, (candidate,))
        if candidate.filing_date and candidate.filing_date > request.as_of_date:
            raise AcquisitionError("candidate publication exceeds as-of")
        adapter = self.adapters.for_market(candidate.market)
        discovered_request = self.target_request(request, candidate)
        discovered_resolution = SourceResolver(self.catalog).resolve(discovered_request)
        if discovered_resolution.status in {
            ResolutionStatus.REUSED_EXACT,
            ResolutionStatus.REUSED_EQUIVALENT,
        }:
            return AcquisitionResult(
                schema_version=ACQUISITION_SCHEMA_VERSION,
                status=AcquisitionStatus.REUSED,
                resolution=replace(discovered_resolution, request_id=request.request_id),
                adapter_name=adapter.name,
                candidate=candidate,
                reason="existing_catalog_source_reused_after_discovery",
                gap_plan=selection.gap_plan,
            )
        if discovered_resolution.status in {
            ResolutionStatus.AMBIGUOUS, ResolutionStatus.IDENTITY_CONFLICT,
        }:
            return AcquisitionResult(
                schema_version=ACQUISITION_SCHEMA_VERSION,
                status=(AcquisitionStatus.AMBIGUOUS
                        if discovered_resolution.status is ResolutionStatus.AMBIGUOUS
                        else AcquisitionStatus.MISSING),
                resolution=replace(discovered_resolution, request_id=request.request_id),
                adapter_name=adapter.name, candidate=candidate,
                reason=discovered_resolution.reason,
                gap_plan=selection.gap_plan,
            )
        request_directory = self.staging_root / acquisition_target_sha256(request, candidate)
        request_directory.mkdir(parents=True, exist_ok=True)
        if budget is None:
            receipt = adapter.fetch(candidate, request_directory)
        else:
            self._require_bounded_adapter(adapter)
            budget.ensure_open()
            bytes_before_fetch = budget.response_bytes_used
            receipt = adapter.fetch_bounded(candidate, request_directory, budget)
            budget.ensure_open()
            bytes_charged_during_fetch = (
                budget.response_bytes_used - bytes_before_fetch
            )
            if receipt.byte_size > bytes_charged_during_fetch:
                raise AcquisitionError(
                    "bounded adapter did not charge the staged response bytes"
                )
            if receipt.byte_size > budget.max_response_bytes - bytes_before_fetch:
                raise AcquisitionError(
                    "staged response exceeds remaining acquisition byte budget"
                )
        self._validate_receipt(candidate, receipt, request_directory)
        return AcquisitionResult(
            schema_version=ACQUISITION_SCHEMA_VERSION,
            status=AcquisitionStatus.STAGED,
            resolution=selection.resolution,
            adapter_name=adapter.name,
            candidate=candidate,
            receipt=receipt,
            reason="missing_source_downloaded_to_staging_pending_canonical_import",
            gap_plan=selection.gap_plan,
        )

    @staticmethod
    def target_request(request: SourceRequest, candidate: DownloadCandidate) -> SourceRequest:
        """Pin the verified selection for lock recheck and final byte resolution."""
        return replace(request, mode="exact", provider=candidate.provider,
            provider_document_id=candidate.provider_document_id,
            fiscal_year=request.fiscal_year or candidate.fiscal_year,
            fiscal_period=request.fiscal_period or candidate.fiscal_period,
            form_type=request.form_type or candidate.form_type,
            language=request.language or candidate.language)

    def cleanup_target(self, request: SourceRequest, candidate: DownloadCandidate) -> None:
        """Remove only this transaction's scratch while its target lock is held."""
        target = self.staging_root / acquisition_target_sha256(request, candidate)
        if not target.exists() and not target.is_symlink():
            return
        root = self.staging_root.resolve(strict=True)
        try:
            target.resolve(strict=True).relative_to(root)
        except ValueError as exc:
            raise AcquisitionError("staging cleanup target escapes configured root") from exc
        if not target.is_dir():
            raise AcquisitionError("staging cleanup target is not a directory")
        for path in (target, *target.rglob("*")):
            if path.is_symlink() or getattr(path.lstat(), "st_file_attributes", 0) & 0x400:
                raise AcquisitionError("staging cleanup refuses reparse or symbolic paths")
        shutil.rmtree(target)

    def _gap_plan_result(
        self,
        request: SourceRequest,
        resolution: ResolutionResult,
        *,
        budget: AcquisitionBudget | None = None,
        candidate_scope: Callable[[DownloadCandidate], bool] | None = None,
    ) -> AcquisitionResult:
        """Discover once and align periods; an explicit intent can select a target."""
        if request.market is None:
            raise MarketRoutingError("market is required before adapter discovery")
        adapter = self.adapters.for_market(request.market)
        # Latest discovery belongs to the provider, including its bounded
        # completeness window. Never guess a fiscal year from the cutoff.
        discovery_request = request
        provider_error: str | None = None
        try:
            if budget is None:
                discovered = tuple(adapter.discover(discovery_request))
            else:
                if not callable(getattr(adapter, "discover_bounded", None)):
                    raise AcquisitionError(
                        f"adapter {adapter.name} does not support bounded acquisition"
                    )
                if not getattr(adapter, "supports_acquisition_budget", False):
                    raise AcquisitionError(
                        f"adapter {adapter.name} does not support bounded acquisition"
                    )
                budget.ensure_open()
                discovered = tuple(
                    adapter.discover_bounded(discovery_request, budget)
                )
                budget.ensure_open()
        except AcquisitionBudgetExceeded:
            raise
        except Exception as exc:  # offline / rate-limit / adapter failure
            provider_error = f"{type(exc).__name__}: {exc}"
            discovered = ()
        self._validate_candidates(request, discovered)
        discovered = tuple(c for c in discovered if candidate_scope is None or candidate_scope(c))
        plan = build_gap_plan(
            request_id=request.request_id,
            as_of_date=request.as_of_date,
            document_kind=request.document_kind,
            entity=request.entity,
            market=request.market,
            local_handles=list(resolution.matches),
            remote_candidates=list(discovered),
            provider_error=provider_error,
        )
        candidate = None
        status = AcquisitionStatus.GAP
        reason = "metadata_only_gap_plan" if provider_error is None else "metadata_only_gap_plan_provider_unavailable"
        if request.allow_download and provider_error is None:
            eligible = tuple(c for c in discovered if c.filing_date and c.filing_date <= request.as_of_date)
            if eligible:
                period_order = {"Q1": 1, "H1": 2, "Q2": 2, "Q3": 3, "H2": 4, "Q4": 4, "FY": 4}
                ranks = {c: (c.fiscal_year, period_order.get((c.fiscal_period or "").upper(), 0),
                             c.filing_date, c.amended) for c in eligible}
                top = tuple(c for c in dict.fromkeys(eligible) if ranks[c] == max(ranks.values()))
                if len(top) == 1:
                    candidate, status, reason = top[0], AcquisitionStatus.SELECTED, "latest_candidate_selected"
                else:
                    status, reason = AcquisitionStatus.AMBIGUOUS, "latest_candidate_identity_ambiguous"
            elif candidate_scope is None and resolution.status in {
                ResolutionStatus.REUSED_EXACT, ResolutionStatus.REUSED_EQUIVALENT,
            }:
                status, reason = AcquisitionStatus.REUSED, "local_source_latest_as_of_provider_metadata"
        return AcquisitionResult(
            schema_version=ACQUISITION_SCHEMA_VERSION,
            status=status,
            resolution=resolution,
            adapter_name=adapter.name,
            gap_plan=plan,
            candidate=candidate,
            reason=reason,
        )

    @staticmethod
    def _require_bounded_adapter(adapter: Any) -> None:
        if not callable(getattr(adapter, "discover_bounded", None)) or not callable(
            getattr(adapter, "fetch_bounded", None)
        ) or not getattr(adapter, "supports_acquisition_budget", False):
            raise AcquisitionError(
                f"adapter {adapter.name} does not support bounded acquisition"
            )

    @staticmethod
    def _validate_receipt(
        candidate: DownloadCandidate,
        receipt: DownloadReceipt,
        staging_directory: Path,
    ) -> None:
        if not isinstance(receipt, DownloadReceipt):
            raise AcquisitionError("adapter returned a non-DownloadReceipt value")
        if receipt.candidate_id != candidate.candidate_id:
            raise AcquisitionError("receipt candidate_id does not match candidate")
        if receipt.provider != candidate.provider:
            raise AcquisitionError("receipt provider does not match candidate")
        if receipt.provider_document_id != candidate.provider_document_id:
            raise AcquisitionError(
                "receipt provider_document_id does not match candidate"
            )
        if receipt.source_url != candidate.source_url:
            raise AcquisitionError("receipt source_url does not match candidate")
        path = Path(receipt.staged_path).resolve(strict=True)
        allocated = staging_directory.resolve(strict=True)
        try:
            path.relative_to(allocated)
        except ValueError as exc:
            raise AcquisitionError("receipt path is outside allocated staging") from exc
        if not path.is_file():
            raise AcquisitionError("receipt staged_path is not a regular file")
        stat = path.stat()
        if stat.st_size != receipt.byte_size:
            raise AcquisitionError("receipt byte_size does not match staged file")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != receipt.content_sha256:
            raise AcquisitionError("receipt SHA-256 does not match staged file")
        if (
            receipt.mime_type == "application/pdf"
        ):
            with path.open("rb") as stream:
                if stream.read(5) != b"%PDF-":
                    raise AcquisitionError("staged PDF does not have PDF magic")
        if not 200 <= receipt.http_status < 300:
            raise AcquisitionError("receipt HTTP status is not successful")


__all__ = [
    "ACQUISITION_SCHEMA_VERSION",
    "AcquisitionCoordinator",
    "AcquisitionError",
    "AcquisitionResult",
    "AcquisitionStatus",
    "AdapterRegistry",
    "DownloadAdapter",
    "DownloadCandidate",
    "DownloadReceipt",
    "MarketRoutingError",
]
